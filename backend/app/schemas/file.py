"""
Pydantic schemas for file upload metadata.
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Dict, List
from datetime import datetime
from uuid import UUID


class FileUploadResponse(BaseModel):
    """Response returned after a successful file upload and processing."""
    id: UUID
    original_filename: str
    file_type: str
    file_size_bytes: int
    source_crs: Optional[str] = None
    feature_count: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FileDetailResponse(BaseModel):
    """Detailed file response including GeoJSON for map rendering."""
    id: UUID
    original_filename: str
    file_type: str
    file_size_bytes: int
    source_crs: Optional[str] = None
    feature_count: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    geojson: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FileListResponse(BaseModel):
    """Compact file info for the file history list."""
    id: UUID
    original_filename: str
    file_type: str
    file_size_bytes: int
    feature_count: Optional[int] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
