"""
Pydantic schemas for API key management and external v1 geometry measurements.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class CreateApiKeyRequest(BaseModel):
    """Request payload for creating a new API key."""
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Friendly human-readable identifier for the key (e.g., 'Production GIS Integration')",
        examples=["Production Integration"],
    )
    expires_in_days: Optional[int] = Field(
        None,
        ge=1,
        le=365,
        description="Optional lifetime in days. If omitted, the key will not expire automatically.",
        examples=[30],
    )


class CreateApiKeyResponse(BaseModel):
    """
    Response returned ONLY upon API key creation.
    The complete plaintext `api_key` is revealed here once and never again.
    """
    id: UUID
    name: str
    prefix: str
    api_key: str = Field(
        ...,
        description="Plaintext API key. Store securely; this value cannot be retrieved again.",
    )
    created_at: datetime
    expires_at: Optional[datetime] = None


class ApiKeyMetadataResponse(BaseModel):
    """Public metadata for an API key. Excludes secret hash and raw key."""
    id: UUID
    name: str
    prefix: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool
    request_count: int


class ApiKeyUsageResponse(BaseModel):
    """Detailed usage metrics for an individual API key."""
    id: UUID
    name: str
    prefix: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool
    request_count: int


class GeometryMeasurementRequest(BaseModel):
    """Request payload for external geometry measurement."""
    geometry: Dict[str, Any] = Field(
        ...,
        description="Valid GeoJSON geometry object (Point, MultiPoint, LineString, MultiLineString, Polygon, MultiPolygon)",
        examples=[
            {
                "type": "Polygon",
                "coordinates": [
                    [[77.2090, 28.6139], [77.2190, 28.6139], [77.2190, 28.6239], [77.2090, 28.6239], [77.2090, 28.6139]]
                ]
            }
        ]
    )
    crs: str = Field(
        "EPSG:4326",
        description="Coordinate Reference System of input coordinates (e.g. 'EPSG:4326', 'EPSG:32643'). Unknown CRS must not be used.",
        examples=["EPSG:4326"],
    )
    properties: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional feature properties or metadata to preserve with the result.",
    )


class GeometryMeasurementResponse(BaseModel):
    """Structured metric measurement result."""
    geometry_type: str
    source_crs: str
    measurement_crs: Optional[str] = None
    area_sq_meters: Optional[float] = None
    length_meters: Optional[float] = None
    area_hectares: Optional[float] = None
    area_sq_km: Optional[float] = None
    length_km: Optional[float] = None
    measurement_unit: str = "meters"
    properties: Optional[Dict[str, Any]] = None
