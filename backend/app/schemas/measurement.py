"""
Pydantic schemas for measurement results.
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Dict, List
from uuid import UUID


class MeasurementResult(BaseModel):
    """Single feature measurement result."""
    feature_index: int
    feature_id: Optional[str] = None
    geometry_type: str
    source_crs: Optional[str] = None
    measurement_crs: Optional[str] = None
    area_sq_meters: Optional[float] = None
    length_meters: Optional[float] = None
    measurement_unit: str = "meters"
    properties: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class MeasurementsResponse(BaseModel):
    """All measurements for a given file."""
    file_id: UUID
    measurements: List[MeasurementResult]
