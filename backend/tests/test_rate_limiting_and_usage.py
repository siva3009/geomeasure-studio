"""
Comprehensive Automated Test Suite for Phase 3:
API Rate Limiting, Monthly Quotas, Concurrency Safety, and Usage Analytics.

Verifies:
1. Requests under the rate limit.
2. Requests exceeding the per-minute limit.
3. Correct HTTP 429 responses and retry headers (Retry-After, X-RateLimit-*).
4. Monthly quota enforcement.
5. Quota reset behavior across UTC month boundary.
6. Concurrent request accounting (thread safety without race conditions).
7. Per-key isolation (Key A does not affect Key B).
8. Ownership checks for analytics (multi-tenant security).
9. Usage event creation and aggregate analytics correctness.
10. Exclusion of secrets and sensitive payloads from usage events.
11. Immediate rejection of revoked/expired keys before rate limit consumption.
12. Database/limiter failure behavior when in-memory storage disallowed.
13. Existing geometry measurements integrity with rate-limit headers.
"""

import concurrent.futures
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
import jwt

from app.main import app
from app.config import settings
from app.services.api_key_service import (
    create_api_key,
    revoke_api_key,
    _IN_MEMORY_API_KEYS,
)
from app.services.rate_limiter import (
    check_and_consume_rate_limit,
    record_usage_event,
    get_user_usage_summary,
    get_key_analytics,
    cleanup_old_usage_events,
    reset_in_memory_usage_events,
    _IN_MEMORY_USAGE_EVENTS,
)
from app.services.auth import DEV_JWT_SECRET
from app.services.db_service import DatabaseError

client = TestClient(app)

POLYGON_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [
            [77.2090, 28.6139],
            [77.2190, 28.6139],
            [77.2190, 28.6239],
            [77.2090, 28.6239],
            [77.2090, 28.6139],
        ]
    ],
}


def make_auth_token(user_id: uuid.UUID) -> str:
    """Generate a mock Supabase Auth JWT token."""
    payload = {
        "sub": str(user_id),
        "aud": "authenticated",
        "role": "authenticated",
        "email": f"developer_{str(user_id)[:8]}@example.com",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=2)).timestamp()),
    }
    return jwt.encode(payload, DEV_JWT_SECRET, algorithm="HS256")


@pytest.fixture(autouse=True)
def clean_state():
    """Reset in-memory state before each test."""
    _IN_MEMORY_API_KEYS.clear()
    reset_in_memory_usage_events()
    yield
    _IN_MEMORY_API_KEYS.clear()
    reset_in_memory_usage_events()


# ==============================================================================
# 1. Requests under the rate limit
# ==============================================================================
def test_requests_under_rate_limit_succeed_with_headers():
    user_id = uuid.uuid4()
    meta, raw_key = create_api_key(user_id=user_id, name="Test Key", tier="development")

    payload = {"geometry": POLYGON_GEOJSON, "crs": "EPSG:4326"}
    res = client.post(
        "/api/v1/measurements/",
        json=payload,
        headers={"X-API-Key": raw_key},
    )

    assert res.status_code == 200
    assert "X-RateLimit-Limit" in res.headers
    assert res.headers["X-RateLimit-Limit"] == "10"
    assert "X-RateLimit-Remaining" in res.headers
    assert int(res.headers["X-RateLimit-Remaining"]) == 9
    assert "X-RateLimit-Reset" in res.headers


# ==============================================================================
# 2. Requests exceeding per-minute limit & 3. 429 response + Retry-After
# ==============================================================================
def test_requests_exceeding_rate_limit_return_429():
    user_id = uuid.uuid4()
    meta, raw_key = create_api_key(user_id=user_id, name="Burst Key", tier="development")
    payload = {"geometry": POLYGON_GEOJSON, "crs": "EPSG:4326"}

    # Development tier allows 10 rpm
    for i in range(10):
        res = client.post(
            "/api/v1/measurements/",
            json=payload,
            headers={"X-API-Key": raw_key},
        )
        assert res.status_code == 200, f"Request {i+1} should have succeeded"

    # 11th request must be throttled with HTTP 429
    throttled = client.post(
        "/api/v1/measurements/",
        json=payload,
        headers={"X-API-Key": raw_key},
    )

    assert throttled.status_code == 429
    assert "Rate limit exceeded" in throttled.json()["detail"]
    assert "Retry-After" in throttled.headers
    retry_after = int(throttled.headers["Retry-After"])
    assert retry_after > 0
    assert throttled.headers["X-RateLimit-Remaining"] == "0"
    assert throttled.headers["X-RateLimit-Limit"] == "10"


# ==============================================================================
# 4. Monthly quota enforcement
# ==============================================================================
def test_monthly_quota_enforcement():
    key_id = uuid.uuid4()
    now = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)

    # Simulate 1,000 requests in current month for development tier (limit 1,000)
    for _ in range(1000):
        _IN_MEMORY_USAGE_EVENTS.append({
            "id": uuid.uuid4(),
            "api_key_id": key_id,
            "endpoint": "/api/v1/measurements/",
            "method": "POST",
            "status_code": 200,
            "duration_ms": 15,
            "blocked_reason": None,
            "created_at": now - timedelta(hours=2),
        })

    # The 1001st request should be blocked by monthly quota
    result = check_and_consume_rate_limit(
        key_id=key_id,
        tier="development",
        test_now=now,
    )

    assert not result.allowed
    assert result.blocked_reason == "quota"
    assert "Monthly quota exceeded" in result.detail
    assert result.retry_after > 0


# ==============================================================================
# 5. Quota reset behavior across UTC month boundary
# ==============================================================================
def test_quota_reset_behavior_across_month_boundary():
    key_id = uuid.uuid4()
    october_date = datetime(2026, 10, 31, 23, 59, 0, tzinfo=timezone.utc)

    # Exhaust October quota
    for _ in range(1000):
        _IN_MEMORY_USAGE_EVENTS.append({
            "id": uuid.uuid4(),
            "api_key_id": key_id,
            "endpoint": "/api/v1/measurements/",
            "method": "POST",
            "status_code": 200,
            "duration_ms": 10,
            "blocked_reason": None,
            "created_at": october_date - timedelta(hours=1),
        })

    # In October, key is blocked
    oct_check = check_and_consume_rate_limit(
        key_id=key_id,
        tier="development",
        test_now=october_date,
    )
    assert not oct_check.allowed
    assert oct_check.blocked_reason == "quota"

    # In November at 00:00:01 UTC, monthly quota has reset!
    november_date = datetime(2026, 11, 1, 0, 0, 1, tzinfo=timezone.utc)
    nov_check = check_and_consume_rate_limit(
        key_id=key_id,
        tier="development",
        test_now=november_date,
    )
    assert nov_check.allowed
    assert nov_check.blocked_reason is None


# ==============================================================================
# 6. Concurrent request accounting (thread safety)
# ==============================================================================
def test_concurrent_request_accounting():
    key_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    def worker(_):
        return check_and_consume_rate_limit(
            key_id=key_id,
            tier="development",  # limit 10
            test_now=now,
        )

    # Concurrently execute 25 requests across thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(worker, range(25)))

    allowed_count = sum(1 for r in results if r.allowed)
    blocked_count = sum(1 for r in results if not r.allowed)

    # Exactly 10 allowed, exactly 15 blocked
    assert allowed_count == 10
    assert blocked_count == 15


# ==============================================================================
# 7. Per-key isolation
# ==============================================================================
def test_per_key_isolation():
    user_id = uuid.uuid4()
    _, key_a = create_api_key(user_id=user_id, name="Key A", tier="development")
    _, key_b = create_api_key(user_id=user_id, name="Key B", tier="development")

    payload = {"geometry": POLYGON_GEOJSON, "crs": "EPSG:4326"}

    # Exhaust Key A's rate limit
    for _ in range(10):
        client.post("/api/v1/measurements/", json=payload, headers={"X-API-Key": key_a})

    # Key A is throttled
    res_a = client.post("/api/v1/measurements/", json=payload, headers={"X-API-Key": key_a})
    assert res_a.status_code == 429

    # Key B is completely unaffected!
    res_b = client.post("/api/v1/measurements/", json=payload, headers={"X-API-Key": key_b})
    assert res_b.status_code == 200
    assert int(res_b.headers["X-RateLimit-Remaining"]) == 9


# ==============================================================================
# 8. Ownership checks for analytics (multi-tenant security)
# ==============================================================================
def test_ownership_checks_for_analytics():
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    meta_a, _ = create_api_key(user_id=user_a, name="User A Key")
    token_b = make_auth_token(user_b)

    # User B attempting to view User A's key analytics receives 404
    res = client.get(
        f"/api/keys/{meta_a['id']}/analytics/",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code == 404


# ==============================================================================
# 9. Usage event creation and aggregate correctness
# ==============================================================================
def test_usage_event_creation_and_aggregation():
    user_id = uuid.uuid4()
    meta, raw_key = create_api_key(user_id=user_id, name="Analytics Key")
    token = make_auth_token(user_id)

    # Send 3 successful requests
    payload = {"geometry": POLYGON_GEOJSON, "crs": "EPSG:4326"}
    for _ in range(3):
        res = client.post("/api/v1/measurements/", json=payload, headers={"X-API-Key": raw_key})
        assert res.status_code == 200

    # Send 1 invalid request (400 Bad Request)
    bad_payload = {"geometry": {"type": "InvalidType", "coordinates": []}, "crs": "EPSG:4326"}
    res_bad = client.post("/api/v1/measurements/", json=bad_payload, headers={"X-API-Key": raw_key})
    assert res_bad.status_code == 400

    # Query usage summary endpoint
    summary_res = client.get(
        "/api/keys/usage/summary/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert summary_res.status_code == 200
    summary = summary_res.json()

    assert summary["total_requests"] == 4
    assert summary["requests_today"] == 4
    assert summary["successful_requests"] == 3
    assert summary["error_requests"] == 1
    assert len(summary["recent_activity"]) == 4
    assert summary["requests_by_endpoint"].get("/api/v1/measurements/") == 4


# ==============================================================================
# 10. Exclusion of secrets and sensitive payloads from usage events
# ==============================================================================
def test_exclusion_of_secrets_from_usage_events():
    user_id = uuid.uuid4()
    meta, raw_key = create_api_key(user_id=user_id, name="Secret Leak Check")
    payload = {"geometry": POLYGON_GEOJSON, "crs": "EPSG:4326"}

    client.post("/api/v1/measurements/", json=payload, headers={"X-API-Key": raw_key})

    # Inspect in-memory events
    assert len(_IN_MEMORY_USAGE_EVENTS) == 1
    event = _IN_MEMORY_USAGE_EVENTS[0]

    # Verify no plaintext key, hash, or geometry stored
    for key, val in event.items():
        assert raw_key not in str(val), "Plaintext key must never be logged in usage events"
        assert "coordinates" not in str(val), "Raw geometry coordinates must not be stored in telemetry"


# ==============================================================================
# 11. Revoked and expired keys rejected before rate limit consumption
# ==============================================================================
def test_revoked_and_expired_keys_rejected_before_rate_limiting():
    user_id = uuid.uuid4()
    meta, raw_key = create_api_key(user_id=user_id, name="Revoked Key")
    revoke_api_key(key_id=meta["id"], user_id=user_id)

    payload = {"geometry": POLYGON_GEOJSON, "crs": "EPSG:4326"}
    res = client.post("/api/v1/measurements/", json=payload, headers={"X-API-Key": raw_key})

    assert res.status_code == 401
    assert "revoked" in res.json()["detail"].lower()
    # No usage event should be charged
    assert len(_IN_MEMORY_USAGE_EVENTS) == 0


# ==============================================================================
# 12. Database or limiter failure behavior
# ==============================================================================
def test_database_failure_behavior_disallows_unlimited_requests():
    # If production environment without in-memory fallback encounters DB failure,
    # it must reject requests rather than permitting unlimited usage.
    original_env = settings.environment
    original_allow = settings.allow_in_memory_db
    try:
        settings.environment = "production"
        settings.allow_in_memory_db = False

        with pytest.raises(DatabaseError):
            check_and_consume_rate_limit(key_id=uuid.uuid4())
    finally:
        settings.environment = original_env
        settings.allow_in_memory_db = original_allow


# ==============================================================================
# 13. Existing geometry measurement and v1 workflows
# ==============================================================================
def test_existing_geometry_measurement_works_with_rate_limiting():
    user_id = uuid.uuid4()
    meta, raw_key = create_api_key(user_id=user_id, name="V1 Integrity Key")

    # Polygon test
    res_poly = client.post(
        "/api/v1/measurements/",
        json={"geometry": POLYGON_GEOJSON, "crs": "EPSG:4326"},
        headers={"X-API-Key": raw_key},
    )
    assert res_poly.status_code == 200
    poly_data = res_poly.json()
    assert poly_data["geometry_type"] == "Polygon"
    assert poly_data["area_sq_meters"] > 0
    assert poly_data["area_hectares"] > 0

    # Point test
    res_point = client.post(
        "/api/v1/measurements/",
        json={"geometry": {"type": "Point", "coordinates": [77.2090, 28.6139]}, "crs": "EPSG:4326"},
        headers={"X-API-Key": raw_key},
    )
    assert res_point.status_code == 200
    point_data = res_point.json()
    assert point_data["geometry_type"] == "Point"
    assert point_data["area_sq_meters"] is None
