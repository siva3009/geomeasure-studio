"""
External v1 API Router (/api/v1/).
Protected by API Key authentication (X-API-Key header).
Provides external programmatic access to GeoMeasure Studio geospatial measurement engine.
Enforces per-minute rate limits, monthly usage quotas, and records analytics events.
"""

import time
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.schemas.api_key import (
    GeometryMeasurementRequest,
    GeometryMeasurementResponse,
)
from app.services.auth import get_api_key_auth, ApiKeyIdentity
from app.services.geo_processor import measure_single_geometry, GeoProcessingError
from app.services.rate_limiter import (
    check_and_consume_rate_limit,
    record_usage_event,
    update_usage_event,
)

router = APIRouter(prefix="/api/v1", tags=["External API v1"])


@router.post(
    "/measurements/",
    response_model=GeometryMeasurementResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute geometry measurements (API Key required)",
    description=(
        "Submit an individual GeoJSON geometry (Polygon, MultiPolygon, LineString, MultiLineString, Point) "
        "with an explicit Coordinate Reference System (default 'EPSG:4326') to compute accurate metric area and length. "
        "Features are automatically reprojected to their optimal local UTM zone. "
        "Requires authentication via the 'X-API-Key' header. "
        "Enforces server-side rate limiting and monthly request quotas based on the key's tier."
    ),
    responses={
        429: {
            "description": "Too Many Requests — Rate limit exceeded or monthly quota exhausted.",
        }
    },
)
async def compute_geometry_measurement(
    req: GeometryMeasurementRequest,
    response: Response,
    caller: ApiKeyIdentity = Depends(get_api_key_auth),
):
    # 1. Evaluate rate limit and monthly quota
    rate_result = check_and_consume_rate_limit(
        key_id=caller.key_id,
        tier=caller.tier,
        endpoint="/api/v1/measurements/",
        method="POST",
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

    # 2. Attach standard rate-limit headers to permitted responses
    response.headers["X-RateLimit-Limit"] = str(rate_result.limit_rpm)
    response.headers["X-RateLimit-Remaining"] = str(rate_result.remaining)
    response.headers["X-RateLimit-Reset"] = str(rate_result.reset_epoch)

    # 3. Execute geospatial measurement and update telemetry duration/status
    start_time = time.perf_counter()
    try:
        result = measure_single_geometry(
            geometry_dict=req.geometry,
            source_crs=req.crs,
            properties=req.properties,
        )
        duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))
        update_usage_event(
            event_id=rate_result.event_id,
            status_code=status.HTTP_200_OK,
            duration_ms=duration_ms,
        )
        return GeometryMeasurementResponse(**result)
    except GeoProcessingError as e:
        duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))
        update_usage_event(
            event_id=rate_result.event_id,
            status_code=status.HTTP_400_BAD_REQUEST,
            duration_ms=duration_ms,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))
        update_usage_event(
            event_id=rate_result.event_id,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            duration_ms=duration_ms,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error processing measurement: {str(e)}",
        )
