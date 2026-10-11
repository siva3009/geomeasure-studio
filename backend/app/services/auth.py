"""
Authentication and Authorization dependencies.
- get_current_user: Validates Supabase Auth JWT Bearer tokens for key management endpoints.
- get_api_key_auth: Validates X-API-Key header against stored SHA-256 hashes for v1 API endpoints.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import jwt
from fastapi import Header, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.services.api_key_service import get_key_by_hash, hash_api_key, record_key_usage

logger = logging.getLogger(__name__)

# Security scheme for Swagger UI documentation
http_bearer = HTTPBearer(auto_error=False)

# Development fallback secret when running tests or local development without a Supabase project secret
DEV_JWT_SECRET = "dev-supabase-jwt-secret-for-local-testing"


@dataclass
class AuthenticatedUser:
    """Represents an authenticated Supabase user."""
    user_id: UUID
    email: Optional[str]
    role: str = "authenticated"


@dataclass
class ApiKeyIdentity:
    """Represents an authenticated API key caller."""
    key_id: UUID
    user_id: UUID
    name: str
    prefix: str
    created_at: datetime
    request_count: int


def get_jwt_secret() -> str:
    """Return the active JWT secret for verifying Supabase Auth tokens."""
    if settings.supabase_jwt_secret:
        return settings.supabase_jwt_secret
    if settings.environment == "production":
        logger.critical("SUPABASE_JWT_SECRET is missing in production environment!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication server misconfiguration: SUPABASE_JWT_SECRET required.",
        )
    return DEV_JWT_SECRET


async def get_current_user(
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> AuthenticatedUser:
    """
    FastAPI dependency that validates a Supabase Auth JWT from the Authorization header.
    Required for API key management endpoints (/api/keys/).
    API keys alone MUST NOT grant access to management endpoints.
    """
    if not auth_credentials or not auth_credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_credentials.credentials.strip()
    secret = get_jwt_secret()

    try:
        # Verify HS256 signature, expiration, and audience
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate user UUID in 'sub' claim
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing user identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = UUID(str(sub))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: user identifier is not a valid UUID.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthenticatedUser(
        user_id=user_uuid,
        email=payload.get("email"),
        role=payload.get("role", "authenticated"),
    )


async def get_api_key_auth(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> ApiKeyIdentity:
    """
    FastAPI dependency that validates an API key supplied via X-API-Key header
    (or Authorization: Bearer gm_live_...).

    The authentication mechanism:
    - Rejects missing, malformed, unknown, expired, or revoked keys.
    - Validates keys against their stored SHA-256 hashes.
    - Updates last-used timestamp and usage count.
    - Avoids logging plaintext secrets.
    """
    raw_key = None
    if x_api_key:
        raw_key = x_api_key.strip()
    elif authorization:
        auth_val = authorization.strip()
        if auth_val.startswith("Bearer gm_live_"):
            raw_key = auth_val[7:].strip()
        elif auth_val.startswith("gm_live_"):
            raw_key = auth_val

    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide a valid key via the 'X-API-Key' header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate format: must start with gm_live_ and have sufficient entropy
    if not raw_key.startswith("gm_live_") or len(raw_key) < 20:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format. Keys must start with 'gm_live_'.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Hash the candidate key and look up in database
    key_hash = hash_api_key(raw_key)
    record = get_key_by_hash(key_hash)

    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unrecognized API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Check revocation status immediately
    if record.get("revoked_at") is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has been revoked and can no longer be used.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Check expiration status
    expires_at = record.get("expires_at")
    if expires_at is not None:
        now = datetime.now(timezone.utc)
        if expires_at <= now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired.",
                headers={"WWW-Authenticate": "ApiKey"},
            )

    # Safely update usage metrics
    try:
        record_key_usage(record["id"])
    except Exception as e:
        logger.warning(f"Failed to record usage for key {record['prefix']}: {e}")

    return ApiKeyIdentity(
        key_id=record["id"],
        user_id=record["user_id"],
        name=record["name"],
        prefix=record["prefix"],
        created_at=record["created_at"],
        request_count=record.get("request_count", 0) + 1,
    )
