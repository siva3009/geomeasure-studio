"""
Upload router — POST /api/files/
Handles file upload, validation, geospatial processing, and persistence.
"""

import os
import tempfile
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.schemas.file import FileUploadResponse
from app.services.file_validator import (
    validate_file_extension,
    validate_file_size,
    get_safe_filename,
    FileValidationError,
)
from app.services.geo_processor import process_uploaded_file, GeoProcessingError
from app.services.db_service import (
    create_file_record,
    update_file_record_success,
    update_file_record_error,
    insert_measurements,
    get_file_by_id,
    DatabaseError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["files"])


@router.post("/api/files/", response_model=FileUploadResponse, status_code=201)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a .kml or .zip (shapefile) file for geospatial processing.

    Steps:
    1. Validate file type and size.
    2. Write to a temporary file.
    3. Run geospatial processing (CRS detection, measurement).
    4. Persist results to the database.
    5. Return metadata.
    """
    # Step 1: Validate extension
    try:
        ext = validate_file_extension(file.filename or "")
    except FileValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    # Step 2: Read and validate size
    try:
        content = await file.read()
        file_size = validate_file_size(content)
    except FileValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    safe_filename = get_safe_filename(file.filename or "upload")
    file_type = ext.lstrip(".")

    # Step 3: Create initial DB record
    try:
        file_id = create_file_record(
            original_filename=safe_filename,
            file_type=file_type,
            file_size_bytes=file_size,
        )
    except DatabaseError as e:
        logger.error(f"Database unavailable creating file record: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database service unavailable. File upload and persistence failed.",
        )
    except Exception as e:
        logger.error(f"Error creating file record: {e}")
        raise HTTPException(status_code=500, detail="Failed to create file record.")

    # Step 4: Write to temp file and process
    try:
        with tempfile.NamedTemporaryFile(
            suffix=ext, delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            source_crs, feature_count, measurements, geojson = process_uploaded_file(
                tmp_path, ext
            )

            # Persist results
            update_file_record_success(file_id, source_crs, feature_count, geojson)
            insert_measurements(file_id, measurements)

        finally:
            # Guaranteed cleanup of temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except DatabaseError as e:
        logger.error(f"Database error during result persistence: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database failed to persist geospatial measurements.",
        )
    except GeoProcessingError as e:
        update_file_record_error(file_id, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except FileValidationError as e:
        update_file_record_error(file_id, e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected processing error: {e}")
        update_file_record_error(file_id, str(e))
        raise HTTPException(
            status_code=500, detail=f"Processing failed: {str(e)}"
        )

    # Step 5: Return the completed record
    record = get_file_by_id(file_id)
    if not record:
        raise HTTPException(status_code=500, detail="Record not found after creation.")

    return FileUploadResponse(**record)
