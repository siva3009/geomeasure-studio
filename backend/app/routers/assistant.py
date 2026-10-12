"""
AI Assistant Router for GeoMeasure Studio.
Exposes:
- POST /api/assistant/analyze: Web workspace route (Supabase Auth / Session).
- GET  /api/assistant/status: Provider readiness and configuration.
- POST /api/v1/assistant/analyze: External developer API route (API Key Auth with AI quotas).
"""

import time
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Response, status

from app.config import settings
from app.schemas.ai import AIAssistantRequest, AIAssistantResponse
from app.services.ai.service import ai_copilot_service
from app.services.ai.gateway import ai_gateway
from app.services.ai.providers import ProviderError
from app.services.auth import (
    get_api_key_auth,
    get_current_user,
    ApiKeyIdentity,
    AuthenticatedUser,
)
from app.services.rate_limiter import (
    check_and_consume_rate_limit,
    update_usage_event,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Copilot"])


async def get_optional_current_user(
    authorization: Optional[str] = Header(None)
) -> Optional[AuthenticatedUser]:
    """Allow optional authentication for the interactive web workspace canvas."""
    if not authorization:
        return None
    try:
        from fastapi.security import HTTPAuthorizationCredentials
        token = authorization.replace("Bearer ", "").strip()
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        return await get_current_user(creds)
    except Exception:
        # Non-blocking for unauthenticated public demo users on web
        return None


@router.get(
    "/api/assistant/status",
    summary="Get AI inference provider health and readiness",
    description="Check the active AI model, latency configuration, and provider connectivity.",
)
async def get_assistant_status():
    health = await ai_gateway.get_health_status()
    return {
        "status": "ready",
        "provider_mode": settings.effective_ai_provider_mode,
        "privacy_mode": settings.ai_privacy_mode,
        "ollama_model": settings.ollama_model,
        "groq_model": settings.groq_model,
        "ai_rate_limit_rpm": settings.ai_rate_limit_rpm,
        "ai_monthly_quota": settings.ai_monthly_quota,
        "details": health,
    }


@router.post(
    "/api/assistant/analyze",
    response_model=AIAssistantResponse,
    summary="Analyze dataset with AI Copilot (Web Workspace)",
    description=(
        "Execute natural language geospatial queries, parcel rankings, geometry validations, "
        "and CRS explanations on active datasets with sub-50ms deterministic fast-path."
    ),
)
async def analyze_workspace(
    req: AIAssistantRequest,
    user: Optional[AuthenticatedUser] = Depends(get_optional_current_user),
):
    try:
        user_id_str = str(user.user_id) if user else None
        file_id_str = str(req.file_id) if req.file_id else None

        result = await ai_copilot_service.analyze(
            task=req.task,
            file_id=file_id_str,
            geometry_payload=req.geometry_payload,
            user_id=user_id_str,
            privacy_mode=req.privacy_mode,
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI Provider Error: {str(e)}"
        )
    except Exception as e:
        logger.error("Unhandled error in AI assistant analyze: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal assistant processing error: {str(e)}"
        )


@router.post(
    "/api/v1/assistant/analyze",
    response_model=AIAssistantResponse,
    summary="Programmatic AI Copilot analysis (API Key required)",
    description=(
        "External API access to the GeoMeasure AI Copilot. Requires 'X-API-Key' authentication. "
        "Enforces dedicated AI request quotas and rate limits."
    ),
    responses={
        429: {
            "description": "Too Many Requests — AI Rate limit exceeded or monthly AI quota exhausted.",
        }
    },
)
async def analyze_external_v1(
    req: AIAssistantRequest,
    response: Response,
    caller: ApiKeyIdentity = Depends(get_api_key_auth),
):
    # 1. Rate Limit & Monthly AI Quota Check
    rate_result = check_and_consume_rate_limit(
        key_id=caller.key_id,
        tier=caller.tier,
        endpoint="/api/v1/assistant/analyze",
        method="POST",
        custom_rpm_limit=settings.ai_rate_limit_rpm,
        custom_monthly_quota=settings.ai_monthly_quota,
    )

    if not rate_result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=rate_result.detail,
            headers={
                "Retry-After": str(rate_result.retry_after),
                "X-RateLimit-Limit": str(rate_result.limit_rpm),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(rate_result.reset_epoch),
            },
        )

    # Attach standard rate limit headers
    response.headers["X-RateLimit-Limit"] = str(rate_result.limit_rpm)
    response.headers["X-RateLimit-Remaining"] = str(rate_result.remaining)
    response.headers["X-RateLimit-Reset"] = str(rate_result.reset_epoch)

    start_time = time.perf_counter()
    try:
        file_id_str = str(req.file_id) if req.file_id else None
        result = await ai_copilot_service.analyze(
            task=req.task,
            file_id=file_id_str,
            geometry_payload=req.geometry_payload,
            api_key_id=str(caller.key_id),
            privacy_mode=req.privacy_mode,
        )
        duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))
        update_usage_event(
            event_id=rate_result.event_id,
            status_code=status.HTTP_200_OK,
            duration_ms=duration_ms,
        )
        return result
    except FileNotFoundError as e:
        duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))
        update_usage_event(
            event_id=rate_result.event_id,
            status_code=status.HTTP_404_NOT_FOUND,
            duration_ms=duration_ms,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))
        update_usage_event(
            event_id=rate_result.event_id,
            status_code=status.HTTP_403_FORBIDDEN,
            duration_ms=duration_ms,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))
        update_usage_event(
            event_id=rate_result.event_id,
            status_code=status.HTTP_400_BAD_REQUEST,
            duration_ms=duration_ms,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ProviderError as e:
        duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))
        update_usage_event(
            event_id=rate_result.event_id,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            duration_ms=duration_ms,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI Provider Error: {str(e)}"
        )
    except Exception as e:
        duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))
        update_usage_event(
            event_id=rate_result.event_id,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            duration_ms=duration_ms,
        )
        logger.error("Unhandled external assistant analyze error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal assistant processing error: {str(e)}"
        )
