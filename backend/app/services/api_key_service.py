"""
API Key Service — Cryptographic key generation, storage, and validation.
Enforces real PostgreSQL persistence in production.
In-memory fallback is strictly restricted to explicitly configured local/test environments.
"""

import hashlib
import logging
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID

from app.config import settings
from app.database import get_db
from app.services.db_service import DatabaseError, _db_is_available, _trigger_db_breaker

logger = logging.getLogger(__name__)

# In-memory storage for test/development environments without PostgreSQL
_IN_MEMORY_API_KEYS: Dict[UUID, Dict[str, Any]] = {}


def generate_api_key_credentials() -> Tuple[str, str, str]:
    """
    Generate cryptographically secure API key credentials.

    Returns:
        Tuple of (plaintext_key, non_secret_prefix, key_hash):
        - plaintext_key: 'gm_live_<urlsafe_random_32_bytes>'
        - non_secret_prefix: 'gm_live_<first_8_chars>'
        - key_hash: SHA-256 hex digest of the plaintext key
    """
    raw_secret = secrets.token_urlsafe(32)
    plaintext_key = f"gm_live_{raw_secret}"
    prefix = f"gm_live_{raw_secret[:8]}"
    key_hash = hashlib.sha256(plaintext_key.encode("utf-8")).hexdigest()
    return plaintext_key, prefix, key_hash


def hash_api_key(api_key: str) -> str:
    """Compute the SHA-256 hex digest of an API key string."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def create_api_key(
    user_id: UUID,
    name: str,
    expires_in_days: Optional[int] = None,
) -> Tuple[Dict[str, Any], str]:
    """
    Create a new API key record.
    The complete plaintext key is returned ONCE alongside the persisted metadata.
    """
    plaintext_key, prefix, key_hash = generate_api_key_credentials()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=expires_in_days) if expires_in_days else None

    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO api_keys (user_id, name, key_hash, prefix, expires_at, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id, user_id, name, prefix, created_at, last_used_at, revoked_at, expires_at, request_count
                        """,
                        (user_id, name, key_hash, prefix, expires_at, now),
                    )
                    row = cur.fetchone()
                    record = {
                        "id": row[0],
                        "user_id": row[1],
                        "name": row[2],
                        "prefix": row[3],
                        "created_at": row[4],
                        "last_used_at": row[5],
                        "revoked_at": row[6],
                        "expires_at": row[7],
                        "request_count": row[8],
                        "is_active": True,
                    }
                    return record, plaintext_key
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL required but failed during create_api_key: {e}")
                raise DatabaseError(f"Database connection failed: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database is currently unavailable and in-memory storage is disallowed.")

    # In-memory storage for test/development
    key_id = uuid.uuid4()
    record = {
        "id": key_id,
        "user_id": user_id,
        "name": name,
        "key_hash": key_hash,
        "prefix": prefix,
        "created_at": now,
        "last_used_at": None,
        "revoked_at": None,
        "expires_at": expires_at,
        "request_count": 0,
        "is_active": True,
    }
    _IN_MEMORY_API_KEYS[key_id] = record
    return {k: v for k, v in record.items() if k != "key_hash"}, plaintext_key


def list_keys_for_user(user_id: UUID) -> List[Dict[str, Any]]:
    """
    List all API keys belonging to a specific authenticated user.
    Never exposes key hashes or secrets.
    """
    now = datetime.now(timezone.utc)
    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, name, prefix, created_at, last_used_at, revoked_at, expires_at, request_count
                        FROM api_keys
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        """,
                        (user_id,),
                    )
                    rows = cur.fetchall()
                    keys = []
                    for row in rows:
                        revoked_at = row[6]
                        expires_at = row[7]
                        is_active = (revoked_at is None) and (expires_at is None or expires_at > now)
                        keys.append({
                            "id": row[0],
                            "user_id": row[1],
                            "name": row[2],
                            "prefix": row[3],
                            "created_at": row[4],
                            "last_used_at": row[5],
                            "revoked_at": revoked_at,
                            "expires_at": expires_at,
                            "request_count": row[8],
                            "is_active": is_active,
                        })
                    return keys
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL required but failed during list_keys_for_user: {e}")
                raise DatabaseError(f"Database connection failed: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database is currently unavailable and in-memory storage is disallowed.")

    # In-memory storage for test/development
    results = []
    for k in _IN_MEMORY_API_KEYS.values():
        if k["user_id"] == user_id:
            revoked_at = k["revoked_at"]
            expires_at = k["expires_at"]
            is_active = (revoked_at is None) and (expires_at is None or expires_at > now)
            results.append({
                "id": k["id"],
                "user_id": k["user_id"],
                "name": k["name"],
                "prefix": k["prefix"],
                "created_at": k["created_at"],
                "last_used_at": k["last_used_at"],
                "revoked_at": revoked_at,
                "expires_at": expires_at,
                "request_count": k["request_count"],
                "is_active": is_active,
            })
    results.sort(key=lambda x: x["created_at"], reverse=True)
    return results


def get_key_by_id(key_id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Retrieve metadata for an API key owned by the specified user.
    Prevents cross-user key access.
    """
    now = datetime.now(timezone.utc)
    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, name, prefix, created_at, last_used_at, revoked_at, expires_at, request_count
                        FROM api_keys
                        WHERE id = %s AND user_id = %s
                        """,
                        (key_id, user_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    revoked_at = row[6]
                    expires_at = row[7]
                    is_active = (revoked_at is None) and (expires_at is None or expires_at > now)
                    return {
                        "id": row[0],
                        "user_id": row[1],
                        "name": row[2],
                        "prefix": row[3],
                        "created_at": row[4],
                        "last_used_at": row[5],
                        "revoked_at": revoked_at,
                        "expires_at": expires_at,
                        "request_count": row[8],
                        "is_active": is_active,
                    }
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL required but failed during get_key_by_id: {e}")
                raise DatabaseError(f"Database connection failed: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database is currently unavailable and in-memory storage is disallowed.")

    # In-memory storage for test/development
    record = _IN_MEMORY_API_KEYS.get(key_id)
    if not record or record["user_id"] != user_id:
        return None
    revoked_at = record["revoked_at"]
    expires_at = record["expires_at"]
    is_active = (revoked_at is None) and (expires_at is None or expires_at > now)
    return {
        "id": record["id"],
        "user_id": record["user_id"],
        "name": record["name"],
        "prefix": record["prefix"],
        "created_at": record["created_at"],
        "last_used_at": record["last_used_at"],
        "revoked_at": revoked_at,
        "expires_at": expires_at,
        "request_count": record["request_count"],
        "is_active": is_active,
    }


def revoke_api_key(key_id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Soft-revoke an API key owned by the specified user.
    Takes effect immediately for subsequent requests.
    """
    now = datetime.now(timezone.utc)
    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE api_keys
                        SET revoked_at = %s
                        WHERE id = %s AND user_id = %s AND revoked_at IS NULL
                        RETURNING id, user_id, name, prefix, created_at, last_used_at, revoked_at, expires_at, request_count
                        """,
                        (now, key_id, user_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        # Check if it exists but is already revoked or belongs to another user
                        return get_key_by_id(key_id, user_id)
                    return {
                        "id": row[0],
                        "user_id": row[1],
                        "name": row[2],
                        "prefix": row[3],
                        "created_at": row[4],
                        "last_used_at": row[5],
                        "revoked_at": row[6],
                        "expires_at": row[7],
                        "request_count": row[8],
                        "is_active": False,
                    }
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL required but failed during revoke_api_key: {e}")
                raise DatabaseError(f"Database connection failed: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database is currently unavailable and in-memory storage is disallowed.")

    # In-memory storage for test/development
    record = _IN_MEMORY_API_KEYS.get(key_id)
    if not record or record["user_id"] != user_id:
        return None
    if record["revoked_at"] is None:
        record["revoked_at"] = now
    return {
        "id": record["id"],
        "user_id": record["user_id"],
        "name": record["name"],
        "prefix": record["prefix"],
        "created_at": record["created_at"],
        "last_used_at": record["last_used_at"],
        "revoked_at": record["revoked_at"],
        "expires_at": record["expires_at"],
        "request_count": record["request_count"],
        "is_active": False,
    }


def get_key_by_hash(key_hash: str) -> Optional[Dict[str, Any]]:
    """
    Look up an API key by its SHA-256 hash for request authentication.
    """
    now = datetime.now(timezone.utc)
    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, name, prefix, created_at, last_used_at, revoked_at, expires_at, request_count
                        FROM api_keys
                        WHERE key_hash = %s
                        """,
                        (key_hash,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    revoked_at = row[6]
                    expires_at = row[7]
                    is_active = (revoked_at is None) and (expires_at is None or expires_at > now)
                    return {
                        "id": row[0],
                        "user_id": row[1],
                        "name": row[2],
                        "prefix": row[3],
                        "created_at": row[4],
                        "last_used_at": row[5],
                        "revoked_at": revoked_at,
                        "expires_at": expires_at,
                        "request_count": row[8],
                        "is_active": is_active,
                    }
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL required but failed during get_key_by_hash: {e}")
                raise DatabaseError(f"Database connection failed: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database is currently unavailable and in-memory storage is disallowed.")

    # In-memory storage for test/development
    for record in _IN_MEMORY_API_KEYS.values():
        if record.get("key_hash") == key_hash:
            revoked_at = record["revoked_at"]
            expires_at = record["expires_at"]
            is_active = (revoked_at is None) and (expires_at is None or expires_at > now)
            return {
                "id": record["id"],
                "user_id": record["user_id"],
                "name": record["name"],
                "prefix": record["prefix"],
                "created_at": record["created_at"],
                "last_used_at": record["last_used_at"],
                "revoked_at": revoked_at,
                "expires_at": expires_at,
                "request_count": record["request_count"],
                "is_active": is_active,
            }
    return None


def record_key_usage(key_id: UUID) -> None:
    """
    Increment request count and update last_used_at timestamp.
    """
    now = datetime.now(timezone.utc)
    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE api_keys
                        SET request_count = request_count + 1,
                            last_used_at = %s
                        WHERE id = %s
                        """,
                        (now, key_id),
                    )
                    return
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL required but failed during record_key_usage: {e}")
                raise DatabaseError(f"Database connection failed: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database is currently unavailable and in-memory storage is disallowed.")

    # In-memory storage for test/development
    if key_id in _IN_MEMORY_API_KEYS:
        _IN_MEMORY_API_KEYS[key_id]["request_count"] += 1
        _IN_MEMORY_API_KEYS[key_id]["last_used_at"] = now
