"""
Health check router.
"""

from fastapi import APIRouter, Response, status
from datetime import datetime, timezone
from app.config import settings
from app.database import check_db_connection

router = APIRouter(tags=["health"])


@router.get("/api/health/")
def health_check(response: Response):
    """Health endpoint — checks API and database connectivity."""
    db_connected = check_db_connection()

    if db_connected:
        health_status = "healthy"
        storage_type = "postgresql"
    elif settings.is_in_memory_allowed:
        health_status = "degraded"
        storage_type = "in-memory (development/test)"
    else:
        health_status = "unhealthy"
        storage_type = "unavailable"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": health_status,
        "environment": settings.environment,
        "database": "connected" if db_connected else "disconnected",
        "storage": storage_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
