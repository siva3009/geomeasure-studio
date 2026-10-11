"""
API Key Management router (/api/keys/).
Requires user authentication via Supabase Auth JWT.
API keys alone MUST NOT grant access to these management endpoints.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import settings
from app.schemas.api_key import (
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    ApiKeyMetadataResponse,
    ApiKeyUsageResponse,
    UsageSummaryResponse,
    KeyAnalyticsResponse,
    RetentionCleanupResponse,
)
from app.services.api_key_service import (
    create_api_key,
    list_keys_for_user,
    get_key_by_id,
    revoke_api_key,
)
from app.services.rate_limiter import (
    get_user_usage_summary,
    get_key_analytics,
    cleanup_old_usage_events,
)
from app.services.auth import get_current_user, AuthenticatedUser

router = APIRouter(prefix="/api/keys", tags=["API Keys"])


@router.post(
    "/",
    response_model=CreateApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    description=(
        "Generates a cryptographically random API key with format 'gm_live_<secret>'. "
        "The plaintext key is returned ONCE upon creation and never stored or returned again. "
        "Requires authenticated user ownership. Configurable tier governs rate limits and quotas."
    ),
)
async def create_key(
    req: CreateApiKeyRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    record, plaintext_key = create_api_key(
        user_id=user.user_id,
        name=req.name.strip(),
        expires_in_days=req.expires_in_days,
        tier=req.tier,
    )
    return CreateApiKeyResponse(
        id=record["id"],
        name=record["name"],
        prefix=record["prefix"],
        tier=record.get("tier", "development"),
        api_key=plaintext_key,
        created_at=record["created_at"],
        expires_at=record["expires_at"],
    )


@router.get(
    "/",
    response_model=List[ApiKeyMetadataResponse],
    summary="List API keys",
    description="List all API keys owned by the authenticated user. Excludes hashes and secret values.",
)
async def list_keys(
    user: AuthenticatedUser = Depends(get_current_user),
):
    keys = list_keys_for_user(user_id=user.user_id)
    response_items = []
    for k in keys:
        limits = settings.get_tier_limits(k.get("tier", "development"))
        response_items.append(
            ApiKeyMetadataResponse(
                **k,
                rate_limit_rpm=limits["rpm"],
                monthly_quota_limit=limits["monthly"],
            )
        )
    return response_items


@router.get(
    "/usage/summary/",
    response_model=UsageSummaryResponse,
    summary="Get user aggregate usage analytics",
    description=(
        "Retrieve aggregate request telemetry, monthly quota consumption, "
        "rate-limit statistics, and recent activity for all keys owned by the authenticated user."
    ),
)
async def get_aggregate_usage_summary(
    user: AuthenticatedUser = Depends(get_current_user),
):
    summary = get_user_usage_summary(user_id=user.user_id)
    return UsageSummaryResponse(**summary)


@router.post(
    "/usage/cleanup/",
    response_model=RetentionCleanupResponse,
    summary="Prune expired usage events",
    description="Remove historical usage telemetry events older than the retention threshold (default 90 days).",
)
async def trigger_usage_cleanup(
    retention_days: int = Query(90, ge=1, le=365),
    user: AuthenticatedUser = Depends(get_current_user),
):
    deleted = cleanup_old_usage_events(retention_days=retention_days)
    return RetentionCleanupResponse(
        deleted_count=deleted,
        retention_days=retention_days,
    )


@router.get(
    "/{key_id}/",
    response_model=ApiKeyMetadataResponse,
    summary="Get API key metadata",
    description="Retrieve non-sensitive metadata for an API key owned by the authenticated user.",
)
async def get_key_metadata(
    key_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
):
    key = get_key_by_id(key_id=key_id, user_id=user.user_id)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )
    limits = settings.get_tier_limits(key.get("tier", "development"))
    return ApiKeyMetadataResponse(
        **key,
        rate_limit_rpm=limits["rpm"],
        monthly_quota_limit=limits["monthly"],
    )


@router.delete(
    "/{key_id}/",
    response_model=ApiKeyMetadataResponse,
    summary="Revoke an API key",
    description=(
        "Immediately revokes an API key. Soft revocation preserves audit history "
        "while instantly rejecting subsequent external requests."
    ),
)
async def revoke_key(
    key_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
):
    key = revoke_api_key(key_id=key_id, user_id=user.user_id)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )
    limits = settings.get_tier_limits(key.get("tier", "development"))
    return ApiKeyMetadataResponse(
        **key,
        rate_limit_rpm=limits["rpm"],
        monthly_quota_limit=limits["monthly"],
    )


@router.get(
    "/{key_id}/usage/",
    response_model=ApiKeyUsageResponse,
    summary="Get API key usage",
    description="Retrieve request count and last-used timestamp for an API key owned by the authenticated user.",
)
async def get_key_usage(
    key_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
):
    key = get_key_by_id(key_id=key_id, user_id=user.user_id)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )
    return ApiKeyUsageResponse(**key)


@router.get(
    "/{key_id}/analytics/",
    response_model=KeyAnalyticsResponse,
    summary="Get granular API key analytics",
    description="Retrieve detailed request metrics, error rates, and recent activity for a specific key.",
)
async def get_key_analytics_endpoint(
    key_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
):
    analytics = get_key_analytics(key_id=key_id, user_id=user.user_id)
    if not analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )
    return KeyAnalyticsResponse(**analytics)
