"""
External v1 API Router (/api/v1/).
Protected by API Key authentication (X-API-Key header).
Provides external programmatic access to GeoMeasure Studio geospatial measurement engine.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.api_key import (
    GeometryMeasurementRequest,
    GeometryMeasurementResponse,
)
from app.services.auth import get_api_key_auth, ApiKeyIdentity
from app.services.geo_processor import measure_single_geometry, GeoProcessingError

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
        "Requires authentication via the 'X-API-Key' header."
    ),
)
async def compute_geometry_measurement(
    req: GeometryMeasurementRequest,
    caller: ApiKeyIdentity = Depends(get_api_key_auth),
):
    try:
        result = measure_single_geometry(
            geometry_dict=req.geometry,
            source_crs=req.crs,
            properties=req.properties,
        )
        return GeometryMeasurementResponse(**result)
    except GeoProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error processing measurement: {str(e)}",
        )
