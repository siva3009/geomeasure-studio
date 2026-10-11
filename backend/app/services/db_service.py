"""
Database service — CRUD operations for files and measurements.
Enforces real PostgreSQL persistence in production.
In-memory fallback is strictly restricted to explicitly configured local/test environments.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID

import psycopg2
import psycopg2.extras

from app.config import settings
from app.database import get_db

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Raised when a database operation fails and in-memory fallback is disallowed."""
    pass


# In-memory storage: only accessible if settings.is_in_memory_allowed is True
_IN_MEMORY_FILES: Dict[UUID, Dict[str, Any]] = {}
_IN_MEMORY_MEASUREMENTS: Dict[UUID, List[Dict[str, Any]]] = {}

# Circuit breaker to prevent repeated connection hangs in local development/test
_db_circuit_broken_until: float = 0.0


def _db_is_available() -> bool:
    return time.time() >= _db_circuit_broken_until


def _trigger_db_breaker(err: Exception):
    global _db_circuit_broken_until
    _db_circuit_broken_until = time.time() + 60.0  # Cooldown for 60s
    logger.warning(f"Database unavailable ({err}), activating in-memory fallback for local/test.")


def create_file_record(
    original_filename: str,
    file_type: str,
    file_size_bytes: int,
) -> UUID:
    """
    Insert a new file record with 'processing' status.
    Requires real PostgreSQL connection in production.
    """
    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO uploaded_files (original_filename, file_type, file_size_bytes, status)
                        VALUES (%s, %s, %s, 'processing')
                        RETURNING id
                        """,
                        (original_filename, file_type, file_size_bytes),
                    )
                    result = cur.fetchone()
                    return result[0]
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL required but failed during create_file_record: {e}")
                raise DatabaseError(f"Database connection failed: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database is currently unavailable and in-memory storage is disallowed.")

    file_id = uuid.uuid4()
    _IN_MEMORY_FILES[file_id] = {
        "id": file_id,
        "original_filename": original_filename,
        "file_type": file_type,
        "file_size_bytes": file_size_bytes,
        "source_crs": None,
        "feature_count": None,
        "status": "processing",
        "error_message": None,
        "geojson": None,
        "created_at": datetime.now(timezone.utc),
    }
    return file_id


def update_file_record_success(
    file_id: UUID,
    source_crs: str,
    feature_count: int,
    geojson: Dict[str, Any],
) -> None:
    """
    Update a file record after successful processing.
    """
    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE uploaded_files
                        SET source_crs = %s,
                            feature_count = %s,
                            status = 'completed',
                            geojson = %s
                        WHERE id = %s
                        """,
                        (source_crs, feature_count, json.dumps(geojson), file_id),
                    )
                    return
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL required but failed during update_file_record_success: {e}")
                raise DatabaseError(f"Database connection failed: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database is currently unavailable and in-memory storage is disallowed.")

    if file_id in _IN_MEMORY_FILES:
        _IN_MEMORY_FILES[file_id].update({
            "source_crs": source_crs,
            "feature_count": feature_count,
            "status": "completed",
            "geojson": geojson,
        })


def update_file_record_error(file_id: UUID, error_message: str) -> None:
    """
    Update a file record after processing failure.
    """
    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE uploaded_files
                        SET status = 'error', error_message = %s
                        WHERE id = %s
                        """,
                        (error_message, file_id),
                    )
                    return
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL required but failed during update_file_record_error: {e}")
                raise DatabaseError(f"Database connection failed: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database is currently unavailable and in-memory storage is disallowed.")

    if file_id in _IN_MEMORY_FILES:
        _IN_MEMORY_FILES[file_id].update({
            "status": "error",
            "error_message": error_message,
        })


def insert_measurements(file_id: UUID, measurements: List[Dict[str, Any]]) -> None:
    """
    Bulk insert measurement records for a file.
    """
    if not measurements:
        return

    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    for m in measurements:
                        cur.execute(
                            """
                            INSERT INTO measurements (
                                file_id, feature_index, feature_id, geometry_type,
                                geometry_wkt, source_crs, measurement_crs,
                                area_sq_meters, length_meters, measurement_unit, properties
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                file_id,
                                m["feature_index"],
                                m.get("feature_id"),
                                m["geometry_type"],
                                m.get("geometry_wkt"),
                                m.get("source_crs"),
                                m.get("measurement_crs"),
                                m.get("area_sq_meters"),
                                m.get("length_meters"),
                                m.get("measurement_unit", "meters"),
                                json.dumps(m.get("properties", {})),
                            ),
                        )
                    return
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL required but failed during insert_measurements: {e}")
                raise DatabaseError(f"Database connection failed: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database is currently unavailable and in-memory storage is disallowed.")

    _IN_MEMORY_MEASUREMENTS[file_id] = measurements


def get_file_by_id(file_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Retrieve a single file record by ID.
    """
    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM uploaded_files WHERE id = %s", (file_id,))
                    row = cur.fetchone()
                    if row:
                        return dict(row)
                    return None
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL required but failed during get_file_by_id: {e}")
                raise DatabaseError(f"Database connection failed: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database is currently unavailable and in-memory storage is disallowed.")

    return _IN_MEMORY_FILES.get(file_id)


def get_all_files() -> List[Dict[str, Any]]:
    """
    Retrieve all uploaded file records, ordered by most recent first.
    """
    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM uploaded_files ORDER BY created_at DESC"
                    )
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL required but failed during get_all_files: {e}")
                raise DatabaseError(f"Database connection failed: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database is currently unavailable and in-memory storage is disallowed.")

    files = list(_IN_MEMORY_FILES.values())
    files.sort(key=lambda x: x.get("created_at") or datetime.min, reverse=True)
    return files


def get_measurements_by_file_id(file_id: UUID) -> List[Dict[str, Any]]:
    """
    Retrieve all measurements for a given file.
    """
    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT feature_index, feature_id, geometry_type,
                               source_crs, measurement_crs, area_sq_meters,
                               length_meters, measurement_unit, properties
                        FROM measurements
                        WHERE file_id = %s
                        ORDER BY feature_index
                        """,
                        (file_id,),
                    )
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL required but failed during get_measurements_by_file_id: {e}")
                raise DatabaseError(f"Database connection failed: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database is currently unavailable and in-memory storage is disallowed.")

    return _IN_MEMORY_MEASUREMENTS.get(file_id, [])


def delete_file_by_id(file_id: UUID) -> bool:
    """
    Delete a file and its measurements.
    """
    if _db_is_available():
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM uploaded_files WHERE id = %s RETURNING id", (file_id,)
                    )
                    return cur.fetchone() is not None
        except Exception as e:
            if not settings.is_in_memory_allowed:
                logger.error(f"PostgreSQL required but failed during delete_file_by_id: {e}")
                raise DatabaseError(f"Database connection failed: {e}") from e
            _trigger_db_breaker(e)
    elif not settings.is_in_memory_allowed:
        raise DatabaseError("Database is currently unavailable and in-memory storage is disallowed.")

    existed = file_id in _IN_MEMORY_FILES
    _IN_MEMORY_FILES.pop(file_id, None)
    _IN_MEMORY_MEASUREMENTS.pop(file_id, None)
    return existed
