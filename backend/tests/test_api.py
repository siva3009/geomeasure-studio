"""
End-to-end API integration tests using FastAPI TestClient.
"""

import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "GeoMeasure Studio API"
    assert data["docs"] == "/docs"


def test_health_endpoint():
    response = client.get("/api/health/")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "timestamp" in data


def test_upload_kml_and_full_lifecycle(sample_kml_path):
    with open(sample_kml_path, "rb") as f:
        file_bytes = f.read()

    # 1. Upload KML
    upload_res = client.post(
        "/api/files/",
        files={"file": ("sample.kml", io.BytesIO(file_bytes), "application/vnd.google-earth.kml+xml")},
    )
    assert upload_res.status_code == 201
    file_data = upload_res.json()
    file_id = file_data["id"]
    assert file_data["status"] == "completed"
    assert file_data["feature_count"] == 3

    # 2. Get file details
    detail_res = client.get(f"/api/files/{file_id}/")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["id"] == file_id
    assert detail_data["geojson"] is not None
    assert len(detail_data["geojson"]["features"]) == 3

    # 3. Get measurements (JSON format)
    meas_res = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_res.status_code == 200
    meas_data = meas_res.json()
    assert meas_data["file_id"] == file_id
    assert len(meas_data["measurements"]) == 3

    # Check polygon measurement has area
    poly_m = [m for m in meas_data["measurements"] if m["geometry_type"] == "Polygon"]
    assert len(poly_m) == 1
    assert poly_m[0]["area_sq_meters"] is not None
    assert poly_m[0]["area_sq_meters"] > 0

    # 4. Export CSV
    csv_res = client.get(f"/api/files/{file_id}/measurements/?format=csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")
    assert "feature_index" in csv_res.text

    # 5. Export GeoJSON
    geojson_res = client.get(f"/api/files/{file_id}/measurements/?format=geojson")
    assert geojson_res.status_code == 200
    assert "FeatureCollection" in geojson_res.text

    # 6. List files
    list_res = client.get("/api/files/")
    assert list_res.status_code == 200
    all_files = list_res.json()
    assert any(f["id"] == file_id for f in all_files)

    # 7. Delete file
    del_res = client.delete(f"/api/files/{file_id}/")
    assert del_res.status_code == 204

    # 8. Verify deleted
    get_deleted = client.get(f"/api/files/{file_id}/")
    assert get_deleted.status_code == 404


def test_upload_shapefile_zip_lifecycle(sample_shapefile_zip_path):
    with open(sample_shapefile_zip_path, "rb") as f:
        file_bytes = f.read()

    upload_res = client.post(
        "/api/files/",
        files={"file": ("sample_shapefile.zip", io.BytesIO(file_bytes), "application/zip")},
    )
    assert upload_res.status_code == 201
    file_data = upload_res.json()
    file_id = file_data["id"]
    assert file_data["file_type"] == "zip"
    assert file_data["feature_count"] == 1

    # Cleanup
    client.delete(f"/api/files/{file_id}/")


def test_upload_invalid_extension():
    upload_res = client.post(
        "/api/files/",
        files={"file": ("document.txt", io.BytesIO(b"hello world"), "text/plain")},
    )
    assert upload_res.status_code == 415


def test_production_database_safety_upload_fails_when_db_disconnected(sample_kml_path):
    """
    In production mode, if PostgreSQL is disconnected, uploads MUST fail honestly
    with HTTP 503 and never silently accept non-persistent in-memory uploads.
    """
    from app.config import settings

    orig_env = settings.environment
    orig_mem = settings.allow_in_memory_db
    try:
        settings.environment = "production"
        settings.allow_in_memory_db = False

        with open(sample_kml_path, "rb") as f:
            file_bytes = f.read()

        res = client.post(
            "/api/files/",
            files={"file": ("sample.kml", io.BytesIO(file_bytes), "application/vnd.google-earth.kml+xml")},
        )
        # Must return 503 Service Unavailable, not 201 Created!
        assert res.status_code == 503
        assert "Database" in res.json()["detail"]
    finally:
        settings.environment = orig_env
        settings.allow_in_memory_db = orig_mem


def test_production_health_reports_unhealthy_when_db_down():
    """In production mode, health endpoint must return 503 and unhealthy if DB is down."""
    from app.config import settings

    orig_env = settings.environment
    orig_mem = settings.allow_in_memory_db
    try:
        settings.environment = "production"
        settings.allow_in_memory_db = False

        res = client.get("/api/health/")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert data["storage"] == "unavailable"
    finally:
        settings.environment = orig_env
        settings.allow_in_memory_db = orig_mem

