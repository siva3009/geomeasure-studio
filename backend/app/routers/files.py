"""
Files router — GET /api/files/ and GET /api/files/{id}/
"""

from uuid import UUID
from fastapi import APIRouter, HTTPException
from typing import List

from app.schemas.file import FileDetailResponse, FileListResponse
from app.services.db_service import (
    get_all_files,
    get_file_by_id,
    delete_file_by_id,
    DatabaseError,
)

router = APIRouter(tags=["files"])


@router.get("/api/files/", response_model=List[FileListResponse])
def list_files():
    """List all uploaded files, most recent first."""
    try:
        files = get_all_files()
        return [FileListResponse(**f) for f in files]
    except DatabaseError as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")


@router.get("/api/files/{file_id}/", response_model=FileDetailResponse)
def get_file(file_id: UUID):
    """Get detailed metadata for a single file, including GeoJSON."""
    try:
        record = get_file_by_id(file_id)
        if not record:
            raise HTTPException(status_code=404, detail="File not found.")
        return FileDetailResponse(**record)
    except DatabaseError as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")


@router.delete("/api/files/{file_id}/", status_code=204)
def delete_file(file_id: UUID):
    """Delete an uploaded file and its measurements."""
    try:
        deleted = delete_file_by_id(file_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="File not found.")
        return None
    except DatabaseError as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")
