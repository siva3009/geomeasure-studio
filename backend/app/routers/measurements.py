"""
Measurements router — GET /api/files/{id}/measurements/
Supports optional ?format=csv and ?format=geojson query parameters.
"""

from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.schemas.measurement import MeasurementsResponse, MeasurementResult
from app.services.db_service import (
    get_file_by_id,
    get_measurements_by_file_id,
    DatabaseError,
)
from app.utils.export import measurements_to_csv, measurements_to_geojson

router = APIRouter(tags=["measurements"])


@router.get("/api/files/{file_id}/measurements/")
def get_measurements(
    file_id: UUID,
    format: str = Query(default="json", description="Response format: json, csv, geojson"),
):
    """
    Get all measurements for a file.
    Supports ?format=csv for CSV download and ?format=geojson for GeoJSON download.
    """
    try:
        # Verify file exists
        file_record = get_file_by_id(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found.")

        measurements = get_measurements_by_file_id(file_id)
    except DatabaseError as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")

    if format == "csv":
        csv_content = measurements_to_csv(measurements)
        filename = file_record["original_filename"].rsplit(".", 1)[0] + "_measurements.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if format == "geojson":
        geojson = measurements_to_geojson(
            measurements, file_record.get("geojson", {})
        )
        filename = file_record["original_filename"].rsplit(".", 1)[0] + "_measurements.geojson"
        return Response(
            content=__import__("json").dumps(geojson, indent=2),
            media_type="application/geo+json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Default: JSON response
    return MeasurementsResponse(
        file_id=file_id,
        measurements=[MeasurementResult(**m) for m in measurements],
    )
