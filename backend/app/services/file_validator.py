"""
File validation service.
Validates uploaded files for type, size, archive safety, and content.
"""

import os
import zipfile
import logging
from typing import Tuple, Optional

from app.config import settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".kml", ".zip"}
# Required shapefile components
SHAPEFILE_REQUIRED = {".shp", ".shx", ".dbf"}


class FileValidationError(Exception):
    """Raised when file validation fails."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def validate_file_extension(filename: str) -> str:
    """
    Validate and return the file extension.

    Args:
        filename: Original filename from the upload.

    Returns:
        Lowercase extension string (e.g., '.kml', '.zip').

    Raises:
        FileValidationError: If the extension is not supported.
    """
    if not filename:
        raise FileValidationError("No filename provided.")

    # Use only the basename to prevent path traversal in the name itself
    safe_name = os.path.basename(filename)
    _, ext = os.path.splitext(safe_name)
    ext = ext.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            status_code=415,
        )

    return ext


def validate_file_size(content: bytes) -> int:
    """
    Validate file size against the configured maximum.

    Args:
        content: Raw file bytes.

    Returns:
        Size in bytes.

    Raises:
        FileValidationError: If the file exceeds the maximum size.
    """
    size = len(content)
    if size == 0:
        raise FileValidationError("Uploaded file is empty.")
    if size > settings.max_upload_size_bytes:
        raise FileValidationError(
            f"File size ({size / 1024 / 1024:.1f} MB) exceeds "
            f"maximum allowed ({settings.max_upload_size_mb} MB)."
        )
    return size


def validate_zip_archive(zip_path: str) -> None:
    """
    Validate a ZIP archive for:
    - Valid ZIP format
    - No path traversal (.. in filenames)
    - Total decompressed size within limits
    - Contains required shapefile components (.shp, .shx, .dbf)

    Args:
        zip_path: Path to the ZIP file on disk.

    Raises:
        FileValidationError: If any validation check fails.
    """
    # Check it's actually a valid zip
    if not zipfile.is_zipfile(zip_path):
        raise FileValidationError("Uploaded .zip file is not a valid ZIP archive.")

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Check for path traversal attacks
            for entry in zf.namelist():
                # Normalize and check for directory traversal
                if ".." in entry or entry.startswith("/") or entry.startswith("\\"):
                    raise FileValidationError(
                        f"ZIP archive contains unsafe path: '{entry}'. "
                        "Path traversal is not allowed."
                    )

            # Check total decompressed size
            total_size = sum(info.file_size for info in zf.infolist())
            if total_size > settings.max_decompressed_size_bytes:
                raise FileValidationError(
                    f"Decompressed archive size ({total_size / 1024 / 1024:.1f} MB) "
                    f"exceeds maximum ({settings.max_decompressed_size_mb} MB)."
                )

            # Check for required shapefile components
            extensions_found = set()
            for name in zf.namelist():
                _, ext = os.path.splitext(name.lower())
                extensions_found.add(ext)

            missing = SHAPEFILE_REQUIRED - extensions_found
            if missing:
                raise FileValidationError(
                    f"ZIP archive is missing required shapefile components: "
                    f"{', '.join(missing)}. "
                    f"A valid shapefile requires at least: {', '.join(SHAPEFILE_REQUIRED)}"
                )

    except zipfile.BadZipFile:
        raise FileValidationError("Uploaded file is a corrupted or invalid ZIP archive.")


def get_safe_filename(filename: str) -> str:
    """
    Sanitize a filename for display purposes.
    Strips path components, keeps only the basename.

    Args:
        filename: Raw filename from upload.

    Returns:
        Safe basename string.
    """
    return os.path.basename(filename).strip()
