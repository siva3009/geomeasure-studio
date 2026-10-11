"""
API Key Management router (/api/keys/).
Requires user authentication via Supabase Auth JWT.
API keys alone MUST NOT grant access to these management endpoints.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.api_key import (
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    ApiKeyMetadataResponse,
    ApiKeyUsageResponse,
)
from app.services.api_key_service import (
    create_api_key,
    list_keys_for_user,
    get_key_by_id,
    revoke_api_key,
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
        "Requires authenticated user ownership."
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
    )
    return CreateApiKeyResponse(
        id=record["id"],
        name=record["name"],
        prefix=record["prefix"],
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
    return [ApiKeyMetadataResponse(**k) for k in keys]


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
    return ApiKeyMetadataResponse(**key)


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
    return ApiKeyMetadataResponse(**key)


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
