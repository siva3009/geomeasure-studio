"""
Rate Limiting, Quota Enforcement, and Usage Analytics Service.
Concurrency-safe with PostgreSQL row locking in production,
and thread-safe in-memory sliding-window fallback for test environments.
"""

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
import uuid

from app.config import settings
from app.database import get_db
from app.services.db_service import DatabaseError, _db_is_available, _trigger_db_breaker

logger = logging.getLogger(__name__)

# Thread-safe lock for in-memory test/development operations
_RATE_LIMITER_LOCK = threading.RLock()

# In-memory storage of usage events for test/development environments
_IN_MEMORY_USAGE_EVENTS: List[Dict[str, Any]] = []


@dataclass
class RateLimitCheckResult:
    """Outcome of a rate limit and quota evaluation."""
    allowed: bool
    limit_rpm: int
    remaining: int
    reset_epoch: int
    retry_after: int = 0
    blocked_reason: Optional[str] = None  # None, 'rate_limit', or 'quota'
    detail: Optional[str] = None
    tier: str = "development"
    monthly_quota: int = 1000
    monthly_used: int = 0
    event_id: Optional[UUID] = None


def _get_utc_now(test_now: Optional[datetime] = None) -> datetime:
    """Return current UTC datetime or a deterministic test clock."""
    if test_now is not None:
        return test_now if test_now.tzinfo else test_now.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _get_month_start_utc(now: datetime) -> datetime:
    """Return the UTC midnight timestamp for the first day of the current month."""
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _get_next_month_start_utc(now: datetime) -> datetime:
    """Return the UTC midnight timestamp for the first day of the following month."""
    if now.month == 12:
        return now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)


def check_and_consume_rate_limit(
    key_id: UUID,
    tier: str = "development",
    endpoint: str = "/api/v1/measurements/",
    method: str = "POST",
    test_now: Optional[datetime] = None,
    custom_rpm_limit: Optional[int] = None,
    custom_monthly_quota: Optional[int] = None,
) -> RateLimitCheckResult:
    """
    Atomically verify rate limit (per minute) and monthly quota for an API key.
    
    If permitted, returns allowed=True with remaining window allowance and reset timestamp.
    If throttled (rate limit exceeded or monthly quota exhausted), returns allowed=False,
    records a blocked usage event (HTTP 429), and calculates exact Retry-After delay.
    
    Concurrency Safe:
    - PostgreSQL: Acquires an exclusive row lock on the key (SELECT FOR UPDATE) to eliminate race conditions.
    - In-Memory: Serialized via re-entrant thread lock.
    """
    now = _get_utc_now(test_now)
    tier_limits = settings.get_tier_limits(tier)
    rpm_limit = tier_limits["rpm"]
    monthly_quota = tier_limits["monthly"]
    burst_multiplier = getattr(settings, "rate_limit_burst_multiplier", 1.0)
    effective_rpm = int(rpm_limit * burst_multiplier)

    if custom_rpm_limit is not None:
        effective_rpm = min(effective_rpm, custom_rpm_limit)
    if custom_monthly_quota is not None:
        monthly_quota = min(monthly_quota, custom_monthly_quota)

    month_start = _get_month_start_utc(now)
    minute_start = now - timedelta(seconds=60)

    # -------------------------------------------------------------
    # 1. PostgreSQL Production / Connected Database Path
    # -------------------------------------------------------------
    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    # Acquire row lock on key to guarantee atomic check & increment across concurrent requests
                    cur.execute(
                        "SELECT tier FROM api_keys WHERE id = %s FOR UPDATE",
                        (key_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return RateLimitCheckResult(
                            allowed=False,
                            limit_rpm=rpm_limit,
                            remaining=0,
                            reset_epoch=int(now.timestamp()) + 60,
                            retry_after=60,
                            blocked_reason="invalid_key",
                            detail="API key not found.",
                        )
                    db_tier = row[0] or tier
                    if db_tier != tier:
                        tier_limits = settings.get_tier_limits(db_tier)
                        rpm_limit = tier_limits["rpm"]
                        monthly_quota = tier_limits["monthly"]
                        effective_rpm = int(rpm_limit * burst_multiplier)
                        if custom_rpm_limit is not None:
                            effective_rpm = min(effective_rpm, custom_rpm_limit)
                        if custom_monthly_quota is not None:
                            monthly_quota = min(monthly_quota, custom_monthly_quota)

                    # A. Check Monthly Quota (Count successful/permitted requests this calendar month)
                    cur.execute(
                        """
                        SELECT COUNT(*) FROM api_key_usage_events
                        WHERE api_key_id = %s
                          AND created_at >= %s
                          AND (blocked_reason IS NULL OR blocked_reason = '')
                        """,
                        (key_id, month_start),
                    )
                    monthly_used = cur.fetchone()[0]

                    if monthly_used >= monthly_quota:
                        next_month = _get_next_month_start_utc(now)
                        retry_after = max(1, int((next_month - now).total_seconds()))
                        reset_epoch = int(next_month.timestamp())

                        # Record blocked quota event
                        cur.execute(
                            """
                            INSERT INTO api_key_usage_events 
                                (api_key_id, endpoint, method, status_code, duration_ms, blocked_reason, created_at)
                            VALUES (%s, %s, %s, 429, 0, 'quota', %s)
                            """,
                            (key_id, endpoint, method, now),
                        )
                        return RateLimitCheckResult(
                            allowed=False,
                            limit_rpm=effective_rpm,
                            remaining=0,
                            reset_epoch=reset_epoch,
                            retry_after=retry_after,
                            blocked_reason="quota",
                            tier=tier_limits["tier"],
                            monthly_quota=monthly_quota,
                            monthly_used=monthly_used,
                            detail=(
                                f"Monthly quota exceeded. Limit: {monthly_quota:,} requests for '{tier_limits['tier']}' tier. "
                                f"Quota resets on {next_month.strftime('%Y-%m-%d %H:%M:%S')} UTC."
                            ),
                        )

                    # B. Check Sliding-Window Per-Minute Rate Limit (past 60s)
                    cur.execute(
                        """
                        SELECT created_at FROM api_key_usage_events
                        WHERE api_key_id = %s
                          AND created_at >= %s
                          AND (blocked_reason IS NULL OR blocked_reason = '')
                        ORDER BY created_at ASC
                        """,
                        (key_id, minute_start),
                    )
                    recent_events = cur.fetchall()
                    minute_count = len(recent_events)

                    if minute_count >= effective_rpm:
                        oldest_ts = recent_events[0][0]
                        retry_after = max(1, int(60 - (now - oldest_ts).total_seconds()))
                        reset_epoch = int((oldest_ts + timedelta(seconds=60)).timestamp())

                        # Record blocked rate-limit event
                        cur.execute(
                            """
                            INSERT INTO api_key_usage_events 
                                (api_key_id, endpoint, method, status_code, duration_ms, blocked_reason, created_at)
                            VALUES (%s, %s, %s, 429, 0, 'rate_limit', %s)
                            """,
                            (key_id, endpoint, method, now),
                        )
                        return RateLimitCheckResult(
                            allowed=False,
                            limit_rpm=effective_rpm,
                            remaining=0,
                            reset_epoch=reset_epoch,
                            retry_after=retry_after,
                            blocked_reason="rate_limit",
                            tier=tier_limits["tier"],
                            monthly_quota=monthly_quota,
                            monthly_used=monthly_used,
                            detail=(
                                f"Rate limit exceeded. Maximum {effective_rpm} requests per minute for '{tier_limits['tier']}' tier. "
                                f"Please retry in {retry_after} second{'s' if retry_after != 1 else ''}."
                            ),
                        )

                    # Request is permitted! Record event immediately inside transaction
                    cur.execute(
                        """
                        INSERT INTO api_key_usage_events 
                            (api_key_id, endpoint, method, status_code, duration_ms, blocked_reason, created_at)
                        VALUES (%s, %s, %s, 200, 0, NULL, %s)
                        RETURNING id
                        """,
                        (key_id, endpoint, method, now),
                    )
                    event_id = cur.fetchone()[0]
                    remaining_in_window = max(0, effective_rpm - (minute_count + 1))
                    reset_epoch = int((now + timedelta(seconds=60)).timestamp())
                    return RateLimitCheckResult(
                        allowed=True,
                        limit_rpm=effective_rpm,
                        remaining=remaining_in_window,
                        reset_epoch=reset_epoch,
                        retry_after=0,
                        blocked_reason=None,
                        tier=tier_limits["tier"],
                        monthly_quota=monthly_quota,
                        monthly_used=monthly_used,
                        event_id=event_id,
                    )
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL rate limit check failed: {e}")
                raise DatabaseError(f"Database unavailable for rate limit evaluation: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database unavailable for rate limit evaluation and in-memory storage is disallowed.")

    # -------------------------------------------------------------
    # 2. Concurrency-Safe In-Memory Path (Tests & Local Dev)
    # -------------------------------------------------------------
    with _RATE_LIMITER_LOCK:
        # A. Check Monthly Quota
        month_events = [
            e for e in _IN_MEMORY_USAGE_EVENTS
            if e["api_key_id"] == key_id
            and e["created_at"] >= month_start
            and not e.get("blocked_reason")
        ]
        monthly_used = len(month_events)

        if monthly_used >= monthly_quota:
            next_month = _get_next_month_start_utc(now)
            retry_after = max(1, int((next_month - now).total_seconds()))
            reset_epoch = int(next_month.timestamp())

            _IN_MEMORY_USAGE_EVENTS.append({
                "id": uuid.uuid4(),
                "api_key_id": key_id,
                "endpoint": endpoint,
                "method": method,
                "status_code": 429,
                "duration_ms": 0,
                "blocked_reason": "quota",
                "created_at": now,
            })
            return RateLimitCheckResult(
                allowed=False,
                limit_rpm=effective_rpm,
                remaining=0,
                reset_epoch=reset_epoch,
                retry_after=retry_after,
                blocked_reason="quota",
                tier=tier_limits["tier"],
                monthly_quota=monthly_quota,
                monthly_used=monthly_used,
                detail=(
                    f"Monthly quota exceeded. Limit: {monthly_quota:,} requests for '{tier_limits['tier']}' tier. "
                    f"Quota resets on {next_month.strftime('%Y-%m-%d %H:%M:%S')} UTC."
                ),
            )

        # B. Check Sliding-Window Per-Minute Limit
        minute_events = [
            e for e in _IN_MEMORY_USAGE_EVENTS
            if e["api_key_id"] == key_id
            and e["created_at"] >= minute_start
            and not e.get("blocked_reason")
        ]
        minute_count = len(minute_events)

        if minute_count >= effective_rpm:
            oldest_ts = min(e["created_at"] for e in minute_events)
            retry_after = max(1, int(60 - (now - oldest_ts).total_seconds()))
            reset_epoch = int((oldest_ts + timedelta(seconds=60)).timestamp())

            _IN_MEMORY_USAGE_EVENTS.append({
                "id": uuid.uuid4(),
                "api_key_id": key_id,
                "endpoint": endpoint,
                "method": method,
                "status_code": 429,
                "duration_ms": 0,
                "blocked_reason": "rate_limit",
                "created_at": now,
            })
            return RateLimitCheckResult(
                allowed=False,
                limit_rpm=effective_rpm,
                remaining=0,
                reset_epoch=reset_epoch,
                retry_after=retry_after,
                blocked_reason="rate_limit",
                tier=tier_limits["tier"],
                monthly_quota=monthly_quota,
                monthly_used=monthly_used,
                detail=(
                    f"Rate limit exceeded. Maximum {effective_rpm} requests per minute for '{tier_limits['tier']}' tier. "
                    f"Please retry in {retry_after} second{'s' if retry_after != 1 else ''}."
                ),
            )

        # Allowed! Record event immediately inside lock to serialize concurrent callers
        event_id = uuid.uuid4()
        _IN_MEMORY_USAGE_EVENTS.append({
            "id": event_id,
            "api_key_id": key_id,
            "endpoint": endpoint,
            "method": method,
            "status_code": 200,
            "duration_ms": 0,
            "blocked_reason": None,
            "created_at": now,
        })
        remaining_in_window = max(0, effective_rpm - (minute_count + 1))
        reset_epoch = int((now + timedelta(seconds=60)).timestamp())
        return RateLimitCheckResult(
            allowed=True,
            limit_rpm=effective_rpm,
            remaining=remaining_in_window,
            reset_epoch=reset_epoch,
            retry_after=0,
            blocked_reason=None,
            tier=tier_limits["tier"],
            monthly_quota=monthly_quota,
            monthly_used=monthly_used,
            event_id=event_id,
        )


def update_usage_event(
    event_id: Optional[UUID],
    status_code: int,
    duration_ms: int,
) -> None:
    """
    Update the final response status code and execution duration for a permitted request event.
    """
    if not event_id:
        return

    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE api_key_usage_events
                        SET status_code = %s, duration_ms = %s
                        WHERE id = %s
                        """,
                        (status_code, duration_ms, event_id),
                    )
                    return
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL update_usage_event failed: {e}")
                raise DatabaseError(f"Database error updating usage event: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database unavailable to update usage event.")

    with _RATE_LIMITER_LOCK:
        for e in _IN_MEMORY_USAGE_EVENTS:
            if e["id"] == event_id:
                e["status_code"] = status_code
                e["duration_ms"] = duration_ms
                break


def record_usage_event(
    key_id: UUID,
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: int,
    blocked_reason: Optional[str] = None,
    test_now: Optional[datetime] = None,
) -> None:
    """
    Record an individual usage event for an authenticated API request.
    Never stores API key secrets or geometric coordinate data.
    """
    now = _get_utc_now(test_now)

    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO api_key_usage_events 
                            (api_key_id, endpoint, method, status_code, duration_ms, blocked_reason, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (key_id, endpoint, method, status_code, duration_ms, blocked_reason, now),
                    )
                    return
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL record_usage_event failed: {e}")
                raise DatabaseError(f"Database error recording usage event: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database unavailable to record usage event.")

    with _RATE_LIMITER_LOCK:
        _IN_MEMORY_USAGE_EVENTS.append({
            "id": uuid.uuid4(),
            "api_key_id": key_id,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "blocked_reason": blocked_reason,
            "created_at": now,
        })


def get_user_usage_summary(
    user_id: UUID,
    test_now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Compute aggregate usage analytics for all keys owned by the authenticated user.
    Calculates month-to-date, today (UTC), status distributions, and recent events.
    """
    from app.services.api_key_service import list_keys_for_user

    now = _get_utc_now(test_now)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = _get_month_start_utc(now)

    user_keys = list_keys_for_user(user_id)
    key_ids = [k["id"] for k in user_keys]
    key_map = {k["id"]: k for k in user_keys}

    if not key_ids:
        default_limits = settings.get_tier_limits("development")
        return {
            "total_requests": 0,
            "requests_today": 0,
            "requests_this_month": 0,
            "monthly_quota_limit": default_limits["monthly"],
            "monthly_quota_remaining": default_limits["monthly"],
            "primary_tier": "development",
            "rate_limit_rpm": default_limits["rpm"],
            "successful_requests": 0,
            "error_requests": 0,
            "rate_limited_requests": 0,
            "quota_exceeded_requests": 0,
            "requests_by_endpoint": {},
            "recent_activity": [],
            "daily_usage": [],
        }

    # Determine user's primary tier and combined monthly quota
    active_keys = [k for k in user_keys if k["is_active"]]
    primary_tier = active_keys[0].get("tier", "development") if active_keys else user_keys[0].get("tier", "development")
    tier_limits = settings.get_tier_limits(primary_tier)
    rpm_limit = tier_limits["rpm"]
    monthly_quota_limit = sum(settings.get_tier_limits(k.get("tier", "development"))["monthly"] for k in (active_keys or user_keys))

    # Fetch events
    events: List[Dict[str, Any]] = []

    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, api_key_id, endpoint, method, status_code, duration_ms, blocked_reason, created_at
                        FROM api_key_usage_events
                        WHERE api_key_id = ANY(%s)
                        ORDER BY created_at DESC
                        LIMIT 500
                        """,
                        (key_ids,),
                    )
                    rows = cur.fetchall()
                    for r in rows:
                        events.append({
                            "id": r[0],
                            "api_key_id": r[1],
                            "endpoint": r[2],
                            "method": r[3],
                            "status_code": r[4],
                            "duration_ms": r[5],
                            "blocked_reason": r[6],
                            "created_at": r[7],
                        })
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL fetch events failed: {e}")
                raise DatabaseError(f"Database error querying usage summary: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database unavailable for usage summary query.")

    if not events and settings.is_in_memory_allowed:
        with _RATE_LIMITER_LOCK:
            events = [e for e in _IN_MEMORY_USAGE_EVENTS if e["api_key_id"] in key_ids]
            events.sort(key=lambda x: x["created_at"], reverse=True)

    # Calculate aggregations
    total_requests = sum(k.get("request_count", 0) for k in user_keys)
    # If events exist, ensure total_requests is at least as large as the event count
    total_requests = max(total_requests, len(events))

    requests_today = sum(1 for e in events if e["created_at"] >= today_start)
    requests_this_month = sum(1 for e in events if e["created_at"] >= month_start and not e.get("blocked_reason"))

    successful_requests = sum(1 for e in events if e["status_code"] < 400)
    error_requests = sum(1 for e in events if e["status_code"] >= 400 and not e.get("blocked_reason"))
    rate_limited_requests = sum(1 for e in events if e.get("blocked_reason") == "rate_limit")
    quota_exceeded_requests = sum(1 for e in events if e.get("blocked_reason") == "quota")

    requests_by_endpoint: Dict[str, int] = {}
    for e in events:
        ep = e.get("endpoint", "/api/v1/measurements/")
        requests_by_endpoint[ep] = requests_by_endpoint.get(ep, 0) + 1

    # Daily counts for the last 14 days
    daily_counts: Dict[str, int] = {}
    for i in range(13, -1, -1):
        day_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_counts[day_str] = 0

    for e in events:
        day_str = e["created_at"].strftime("%Y-%m-%d")
        if day_str in daily_counts:
            daily_counts[day_str] += 1

    daily_usage = [{"date": d, "count": count} for d, count in sorted(daily_counts.items())]

    # Recent activity items (up to 20)
    recent_activity = []
    for e in events[:20]:
        k_meta = key_map.get(e["api_key_id"], {})
        recent_activity.append({
            "id": str(e["id"]),
            "api_key_id": str(e["api_key_id"]),
            "key_name": k_meta.get("name", "Unknown Key"),
            "key_prefix": k_meta.get("prefix", "gm_live_"),
            "endpoint": e["endpoint"],
            "method": e["method"],
            "status_code": e["status_code"],
            "duration_ms": e["duration_ms"],
            "blocked_reason": e.get("blocked_reason"),
            "created_at": e["created_at"].isoformat() if hasattr(e["created_at"], "isoformat") else str(e["created_at"]),
        })

    remaining_allowance = max(0, monthly_quota_limit - requests_this_month)

    # Phase 4: AI Telemetry Breakdown
    ai_events = [e for e in events if "assistant" in e.get("endpoint", "")]
    ai_requests = len(ai_events)
    ai_successful = sum(1 for e in ai_events if e["status_code"] < 400)
    ai_rate_limited = sum(1 for e in ai_events if e.get("blocked_reason") == "rate_limit")
    ai_quota_exceeded = sum(1 for e in ai_events if e.get("blocked_reason") == "quota")
    ai_avg_duration = round(sum(e["duration_ms"] for e in ai_events) / max(1, ai_requests), 1) if ai_requests else 0.0

    ai_usage = {
        "total_requests": ai_requests,
        "successful_requests": ai_successful,
        "rate_limited_requests": ai_rate_limited,
        "quota_exceeded_requests": ai_quota_exceeded,
        "avg_duration_ms": ai_avg_duration,
        "monthly_quota_limit": settings.ai_monthly_quota,
        "rate_limit_rpm": settings.ai_rate_limit_rpm,
    }

    return {
        "total_requests": total_requests,
        "requests_today": requests_today,
        "requests_this_month": requests_this_month,
        "monthly_quota_limit": monthly_quota_limit,
        "monthly_quota_remaining": remaining_allowance,
        "primary_tier": primary_tier,
        "rate_limit_rpm": rpm_limit,
        "successful_requests": successful_requests,
        "error_requests": error_requests,
        "rate_limited_requests": rate_limited_requests,
        "quota_exceeded_requests": quota_exceeded_requests,
        "requests_by_endpoint": requests_by_endpoint,
        "recent_activity": recent_activity,
        "daily_usage": daily_usage,
        "ai_usage": ai_usage,
    }


def get_key_analytics(
    key_id: UUID,
    user_id: UUID,
    test_now: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve granular analytics for a specific API key owned by the user.
    """
    from app.services.api_key_service import get_key_by_id

    key = get_key_by_id(key_id, user_id)
    if not key:
        return None

    now = _get_utc_now(test_now)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = _get_month_start_utc(now)

    tier = key.get("tier", "development")
    limits = settings.get_tier_limits(tier)

    events: List[Dict[str, Any]] = []

    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, api_key_id, endpoint, method, status_code, duration_ms, blocked_reason, created_at
                        FROM api_key_usage_events
                        WHERE api_key_id = %s
                        ORDER BY created_at DESC
                        LIMIT 100
                        """,
                        (key_id,),
                    )
                    rows = cur.fetchall()
                    for r in rows:
                        events.append({
                            "id": r[0],
                            "api_key_id": r[1],
                            "endpoint": r[2],
                            "method": r[3],
                            "status_code": r[4],
                            "duration_ms": r[5],
                            "blocked_reason": r[6],
                            "created_at": r[7],
                        })
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL key analytics failed: {e}")
                raise DatabaseError(f"Database error querying key analytics: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database unavailable for key analytics query.")

    if not events and settings.is_in_memory_allowed:
        with _RATE_LIMITER_LOCK:
            events = [e for e in _IN_MEMORY_USAGE_EVENTS if e["api_key_id"] == key_id]
            events.sort(key=lambda x: x["created_at"], reverse=True)

    requests_today = sum(1 for e in events if e["created_at"] >= today_start)
    requests_this_month = sum(1 for e in events if e["created_at"] >= month_start and not e.get("blocked_reason"))

    successful_requests = sum(1 for e in events if e["status_code"] < 400)
    error_requests = sum(1 for e in events if e["status_code"] >= 400 and not e.get("blocked_reason"))
    rate_limited_requests = sum(1 for e in events if e.get("blocked_reason") == "rate_limit")

    # Daily counts for last 7 days
    daily_counts: Dict[str, int] = {}
    for i in range(6, -1, -1):
        day_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_counts[day_str] = 0

    for e in events:
        day_str = e["created_at"].strftime("%Y-%m-%d")
        if day_str in daily_counts:
            daily_counts[day_str] += 1

    daily_usage = [{"date": d, "count": count} for d, count in sorted(daily_counts.items())]

    recent_activity = []
    for e in events[:15]:
        recent_activity.append({
            "id": str(e["id"]),
            "api_key_id": str(key_id),
            "key_name": key["name"],
            "key_prefix": key["prefix"],
            "endpoint": e["endpoint"],
            "method": e["method"],
            "status_code": e["status_code"],
            "duration_ms": e["duration_ms"],
            "blocked_reason": e.get("blocked_reason"),
            "created_at": e["created_at"].isoformat() if hasattr(e["created_at"], "isoformat") else str(e["created_at"]),
        })

    remaining_month = max(0, limits["monthly"] - requests_this_month)

    return {
        "key_id": str(key["id"]),
        "name": key["name"],
        "prefix": key["prefix"],
        "tier": tier,
        "is_active": key["is_active"],
        "rate_limit_rpm": limits["rpm"],
        "monthly_quota_limit": limits["monthly"],
        "monthly_quota_used": requests_this_month,
        "monthly_quota_remaining": remaining_month,
        "total_requests": max(key.get("request_count", 0), len(events)),
        "requests_today": requests_today,
        "successful_requests": successful_requests,
        "error_requests": error_requests,
        "rate_limited_requests": rate_limited_requests,
        "recent_activity": recent_activity,
        "daily_usage": daily_usage,
    }


def cleanup_old_usage_events(retention_days: Optional[int] = None) -> int:
    """
    Remove usage events older than the configured retention threshold.
    Returns the count of purged events.
    """
    days = retention_days if retention_days is not None else getattr(settings, "usage_event_retention_days", 90)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted_count = 0

    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM api_key_usage_events WHERE created_at < %s",
                        (cutoff,),
                    )
                    deleted_count = cur.rowcount
                    logger.info(f"Purged {deleted_count} usage events older than {days} days.")
                    return deleted_count
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL event cleanup failed: {e}")
                raise DatabaseError(f"Database error during event retention cleanup: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database unavailable for event retention cleanup.")

    with _RATE_LIMITER_LOCK:
        initial_len = len(_IN_MEMORY_USAGE_EVENTS)
        _IN_MEMORY_USAGE_EVENTS[:] = [e for e in _IN_MEMORY_USAGE_EVENTS if e["created_at"] >= cutoff]
        deleted_count = initial_len - len(_IN_MEMORY_USAGE_EVENTS)
        return deleted_count


def reset_in_memory_usage_events() -> None:
    """Helper for automated tests to clear in-memory event state."""
    with _RATE_LIMITER_LOCK:
        _IN_MEMORY_USAGE_EVENTS.clear()
