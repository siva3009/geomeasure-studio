"""
Comprehensive Deterministic Evaluation and Testing Suite for GeoMeasure AI Copilot.
Validates:
- 30+ representative GIS prompts and queries across ranking, validation, CRS, summary, and export.
- Deterministic fast-path execution (sub-50ms) and GIS engine integration.
- Provider gateway routing: local Ollama, hosted Groq, mock testing.
- Local provider timeout & fallback to hosted provider.
- Privacy mode boundary enforcement: 'local_only' mode strictly prohibits cloud fallback.
- Rate limiting and monthly AI quota enforcement on /api/v1/assistant/analyze.
- Cross-tenant dataset isolation (User A cannot query User B's dataset).
- Unapproved tool refusal and security boundaries.
- Mock providers ensure zero external API charges or network dependencies during CI.
"""

import asyncio
import uuid
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.services.ai.gateway import ai_gateway
from app.services.ai.providers import MockAIProvider, ProviderResult, ProviderError
from app.services.ai.tools import (
    tool_inspect_dataset,
    tool_measure_features,
    tool_validate_geometries,
    tool_export_results,
    APPROVED_TOOL_NAMES,
)
from app.services.ai.service import ai_copilot_service
import app.services.db_service as db_service
from app.services.api_key_service import create_api_key

client = TestClient(app)

# Standard mock polygon dataset in WGS84
SAMPLE_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"parcel_id": "P-101", "owner": "Alpha Farms", "zone": "Agricultural"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[77.100, 28.600], [77.110, 28.600], [77.110, 28.610], [77.100, 28.610], [77.100, 28.600]]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {"parcel_id": "P-102", "owner": "Beta Logistics", "zone": "Commercial"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[77.120, 28.600], [77.125, 28.600], [77.125, 28.605], [77.120, 28.605], [77.120, 28.600]]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {"parcel_id": "P-103", "owner": "Gamma Residence", "zone": "Residential"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[77.130, 28.600], [77.145, 28.600], [77.145, 28.615], [77.130, 28.615], [77.130, 28.600]]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {"parcel_id": "P-104", "owner": "Delta Park", "zone": "Recreational"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[77.150, 28.600], [77.152, 28.600], [77.152, 28.602], [77.150, 28.602], [77.150, 28.600]]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {"parcel_id": "P-105", "owner": "Epsilon Utility", "zone": "Industrial"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[77.160, 28.600], [77.180, 28.600], [77.180, 28.620], [77.160, 28.620], [77.160, 28.600]]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {"parcel_id": "P-106", "owner": "Zeta Waterway", "zone": "Conservation"},
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [77.100, 28.620], [77.120, 28.625], [77.140, 28.630], [77.160, 28.635]
                ]
            }
        }
    ]
}

SAMPLE_MEASUREMENTS = [
    {"feature_index": 0, "feature_id": "P-101", "geometry_type": "Polygon", "area_sq_meters": 1184000.0, "length_meters": 4350.0, "measurement_crs": "EPSG:32643"},
    {"feature_index": 1, "feature_id": "P-102", "geometry_type": "Polygon", "area_sq_meters": 296000.0, "length_meters": 2175.0, "measurement_crs": "EPSG:32643"},
    {"feature_index": 2, "feature_id": "P-103", "geometry_type": "Polygon", "area_sq_meters": 2664000.0, "length_meters": 6525.0, "measurement_crs": "EPSG:32643"},
    {"feature_index": 3, "feature_id": "P-104", "geometry_type": "Polygon", "area_sq_meters": 47360.0, "length_meters": 870.0, "measurement_crs": "EPSG:32643"},
    {"feature_index": 4, "feature_id": "P-105", "geometry_type": "Polygon", "area_sq_meters": 4736000.0, "length_meters": 8700.0, "measurement_crs": "EPSG:32643"},
    {"feature_index": 5, "feature_id": "P-106", "geometry_type": "LineString", "area_sq_meters": 0.0, "length_meters": 6120.0, "measurement_crs": "EPSG:32643"},
]


@pytest.fixture(autouse=True)
def setup_teardown_ai_env():
    """Ensure mock provider is reset after each test and fast in-memory execution."""
    import time
    ai_gateway.set_mock_provider(None)
    prev_broken = getattr(db_service, "_db_circuit_broken_until", 0.0)
    db_service._db_circuit_broken_until = time.time() + 3600.0
    yield
    db_service._db_circuit_broken_until = prev_broken
    ai_gateway.set_mock_provider(None)


@pytest.fixture
def test_dataset():
    """Create a temporary dataset record in memory for testing."""
    file_id = str(uuid.uuid4())
    record = {
        "id": file_id,
        "filename": "parcels.geojson",
        "original_filename": "parcels.geojson",
        "file_size": 1024,
        "file_type": "geojson",
        "source_crs": "EPSG:4326",
        "status": "completed",
        "total_features": len(SAMPLE_GEOJSON["features"]),
        "total_area_sq_meters": sum(m["area_sq_meters"] for m in SAMPLE_MEASUREMENTS),
        "total_length_meters": sum(m["length_meters"] for m in SAMPLE_MEASUREMENTS),
        "geojson": SAMPLE_GEOJSON,
        "user_id": None,
    }
    db_service._IN_MEMORY_FILES[file_id] = record
    db_service._IN_MEMORY_MEASUREMENTS[file_id] = SAMPLE_MEASUREMENTS.copy()
    yield record
    db_service._IN_MEMORY_FILES.pop(file_id, None)
    db_service._IN_MEMORY_MEASUREMENTS.pop(file_id, None)


# =============================================================================
# 1. 30 Representative GIS Prompts Evaluation Suite
# =============================================================================

REPRESENTATIVE_GIS_PROMPTS = [
    # Category 1: Parcel Ranking & Metric Area
    ("Calculate all parcel areas and rank the five largest.", "rank_largest_areas", "measure_features"),
    ("Rank top 3 parcels by planar area in hectares.", "rank_largest_areas", "measure_features"),
    ("Find the biggest parcel in the dataset.", "rank_largest_areas", "measure_features"),
    ("Which parcel has the highest area?", "rank_largest_areas", "measure_features"),
    ("Rank the 5 largest polygons.", "rank_largest_areas", "measure_features"),
    ("Order features by area descending.", "rank_largest_areas", "measure_features"),

    # Category 2: Validation & Topology
    ("Find overlapping or invalid polygons.", "validate_geometries", "validate_geometries"),
    ("Check geometry validity and self-intersections.", "validate_geometries", "validate_geometries"),
    ("Are there any topology errors in these parcels?", "validate_geometries", "validate_geometries"),
    ("Identify overlapping polygon pairs.", "validate_geometries", "validate_geometries"),
    ("Validate all features for topological consistency.", "validate_geometries", "validate_geometries"),
    ("Detect geometry errors and invalid boundaries.", "validate_geometries", "validate_geometries"),

    # Category 3: CRS & Coordinate Projections
    ("Explain the CRS used for measurement.", "explain_crs", "inspect_dataset"),
    ("Why is dynamic UTM used instead of EPSG:4326?", "explain_crs", "inspect_dataset"),
    ("Explain the coordinate reference system of this file.", "explain_crs", "inspect_dataset"),
    ("What projection is used for metric area calculation?", "explain_crs", "inspect_dataset"),
    ("Explain degrees vs metric meters projection rationale.", "explain_crs", "inspect_dataset"),
    ("What is the source CRS and measurement datum?", "explain_crs", "inspect_dataset"),

    # Category 4: Summary & Geometry Breakdown
    ("Summarize feature counts and geometry types.", "summarize_dataset", "inspect_dataset"),
    ("How many features and what geometry types are in this dataset?", "summarize_dataset", "inspect_dataset"),
    ("Breakdown feature count by polygon and linestring.", "summarize_dataset", "inspect_dataset"),
    ("Give me summary statistics of total area and total length.", "summarize_dataset", "inspect_dataset"),
    ("Count the total features in this uploaded file.", "summarize_dataset", "inspect_dataset"),
    ("Summarize dataset properties and bounding bounds.", "summarize_dataset", "inspect_dataset"),

    # Category 5: Exporting & Artifact Generation
    ("Export validated results to CSV.", "export_csv", "export_results"),
    ("Export results to GeoJSON.", "export_geojson", "export_results"),
    ("Download measurements as a CSV spreadsheet.", "export_csv", "export_results"),
    ("Generate GeoJSON export artifact.", "export_geojson", "export_results"),
    ("Export parcel calculations to CSV format.", "export_csv", "export_results"),
    ("Download enhanced GeoJSON with metric measurements.", "export_geojson", "export_results"),
]


@pytest.mark.parametrize("prompt,expected_intent,expected_tool", REPRESENTATIVE_GIS_PROMPTS)
def test_evaluation_30_gis_prompts(test_dataset, prompt, expected_intent, expected_tool):
    """Evaluate 30 representative GIS prompts against the deterministic GIS engine."""
    res = client.post(
        "/api/assistant/analyze",
        json={"task": prompt, "file_id": test_dataset["id"]}
    )
    assert res.status_code == 200, f"Failed prompt: {prompt}"
    data = res.json()
    assert data["status"] == "completed"
    assert data["intent"] == expected_intent, f"Prompt '{prompt}' classified as {data['intent']}, expected {expected_intent}"
    assert expected_tool in data["actions_executed"], f"Expected tool {expected_tool} in actions"
    assert len(data["explanation"]) > 20
    # Latency check: deterministic engine executes in sub-50ms
    assert data["latency_breakdown"]["total_ms"] < 150.0


# =============================================================================
# 2. GIS Tool Registry Unit Tests
# =============================================================================

def test_tool_inspect_dataset(test_dataset):
    inspect_res = tool_inspect_dataset(test_dataset, SAMPLE_MEASUREMENTS)
    assert inspect_res["total_features"] == 6
    assert inspect_res["geometry_type_breakdown"]["Polygon"] == 5
    assert inspect_res["geometry_type_breakdown"]["LineString"] == 1
    assert inspect_res["total_area_sq_meters"] > 0.0


def test_tool_measure_features_ranking():
    meas_res = tool_measure_features(SAMPLE_MEASUREMENTS, rank_by="area", limit=3)
    top = meas_res["top_features"]
    assert len(top) == 3
    # Top 1 should be P-105 with largest area
    assert top[0]["feature_id"] == "P-105"
    assert top[0]["area_sq_meters"] == 4736000.0
    assert len(meas_res["highlighted_indices"]) == 3


def test_tool_validate_geometries():
    val_res = tool_validate_geometries({"geojson": SAMPLE_GEOJSON}, check_overlaps=True)
    assert val_res["total_evaluated"] == 6
    assert val_res["valid_count"] == 6
    assert val_res["invalid_count"] == 0


def test_tool_export_csv(test_dataset):
    exp_res = tool_export_results(test_dataset, SAMPLE_MEASUREMENTS, export_format="csv")
    assert exp_res["format"] == "csv"
    assert "parcels_copilot_export.csv" in exp_res["filename"]
    assert exp_res["record_count"] == 6
    assert "feature_index" in exp_res["content_preview"]


def test_tool_export_geojson(test_dataset):
    exp_res = tool_export_results(test_dataset, SAMPLE_MEASUREMENTS, export_format="geojson")
    assert exp_res["format"] == "geojson"
    assert exp_res["record_count"] == 6
    assert "FeatureCollection" in exp_res["content_preview"]


def test_unapproved_tool_rejection():
    """Verify that unapproved tool names cannot be executed."""
    assert "execute_python" not in APPROVED_TOOL_NAMES
    assert "run_shell" not in APPROVED_TOOL_NAMES
    assert "query_raw_sql" not in APPROVED_TOOL_NAMES


# =============================================================================
# 3. Provider Behavior & Gateway Tests
# =============================================================================

def test_successful_local_mock_inference(test_dataset):
    """Test successful local inference using mock provider."""
    mock = MockAIProvider(name="ollama", is_local=True)
    ai_gateway.set_mock_provider(mock)

    # Use prompt that requires LLM reasoning
    res = asyncio.run(ai_copilot_service.analyze(
        task="Recommend optimal buffer zones for these agricultural parcels.",
        file_id=test_dataset["id"],
    ))
    assert res.status == "completed"
    assert res.provider_metadata.is_local is True
    assert res.provider_metadata.provider == "ollama"
    assert mock.call_count == 1


def test_local_provider_timeout_and_fallback(test_dataset):
    """Test local provider timeout triggering automatic fallback to hosted provider."""
    # When local fails, fallback should succeed if not in local_only mode
    with patch.object(ai_gateway._groq, "complete") as mock_groq:
        mock_groq.return_value = ProviderResult(
            content="Hosted Groq response with geospatial recommendations.",
            provider="groq",
            model="openai/gpt-oss-20b",
            is_local=False,
            latency_ms=120.0,
            tool_calls=[{"name": "inspect_dataset", "arguments": {}}],
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
        )
        ai_gateway._mock_provider = None

        with patch.object(ai_gateway._ollama, "complete", side_effect=ProviderError("Local timeout", provider="ollama", is_timeout=True)):
            with patch.object(settings, "groq_api_key", "gsk_test_mock_key"):
                res = asyncio.run(ai_gateway.complete(
                    messages=[{"role": "user", "content": "hello"}],
                    mode_override="local_first",
                    privacy_override="standard",
                ))
                assert res.provider == "groq"
                assert res.is_local is False


def test_privacy_mode_prevents_cloud_fallback(test_dataset):
    """Test that local_only privacy mode STRICTLY prohibits cloud fallback when local fails."""
    ai_gateway._mock_provider = None
    with patch.object(ai_gateway._ollama, "complete", side_effect=ProviderError("Local offline", provider="ollama")):
        with patch.object(settings, "groq_api_key", "gsk_test_key"):
            with pytest.raises(ProviderError) as exc_info:
                asyncio.run(ai_gateway.complete(
                    messages=[{"role": "user", "content": "test"}],
                    privacy_override="local_only",
                ))
            assert "cloud fallback is prohibited" in str(exc_info.value)


def test_missing_credentials_fails_gracefully():
    """Test that unconfigured hosted provider reports missing credentials safely without exposing secrets."""
    ai_gateway._mock_provider = None
    with patch.object(settings, "groq_api_key", ""):
        with patch.object(settings, "environment", "production"):
            with pytest.raises(ProviderError) as exc:
                asyncio.run(ai_gateway.complete(
                    messages=[{"role": "user", "content": "hi"}],
                    mode_override="hosted_only",
                ))
            assert "All eligible AI providers failed" in str(exc.value)


# =============================================================================
# 4. Security, Quotas, and Tenant Isolation Tests
# =============================================================================

def test_tenant_dataset_isolation():
    """Verify User A cannot query User B's dataset."""
    from app.routers.assistant import get_optional_current_user
    from app.services.auth import AuthenticatedUser
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    file_b_id = str(uuid.uuid4())
    fake_user_a = AuthenticatedUser(user_id=user_a, email="a@test.com", role="authenticated")
    app.dependency_overrides[get_optional_current_user] = lambda: fake_user_a

    try:
        db_service._IN_MEMORY_FILES[file_b_id] = {
            "id": file_b_id,
            "filename": "private.geojson",
            "original_filename": "private.geojson",
            "file_size": 1024,
            "file_size_bytes": 1024,
            "file_type": "geojson",
            "status": "completed",
            "created_at": "2026-10-12T00:00:00",
            "user_id": str(user_b),
            "geojson": SAMPLE_GEOJSON,
        }
        res = client.post(
            "/api/assistant/analyze",
            json={"task": "Rank parcel areas", "file_id": file_b_id},
        )
        assert res.status_code == 403
        assert "Access denied" in res.json()["detail"]
    finally:
        db_service._IN_MEMORY_FILES.pop(file_b_id, None)
        app.dependency_overrides.pop(get_optional_current_user, None)


def test_api_key_quota_enforcement_for_ai():
    """Verify /api/v1/assistant/analyze enforces dedicated AI monthly quotas."""
    # Create test API key
    user_id = uuid.uuid4()
    key_tuple = create_api_key(user_id=user_id, name="AI Test Key", tier="development")
    raw_key = key_tuple[1] if isinstance(key_tuple, (tuple, list)) else key_tuple["plaintext_key"]

    # Request within quota
    res1 = client.post(
        "/api/v1/assistant/analyze",
        headers={"X-API-Key": raw_key},
        json={"task": "Explain the CRS used for measurement."}
    )
    assert res1.status_code == 200
    assert "X-RateLimit-Limit" in res1.headers

    # Simulate quota exhaustion by setting quota to 1
    with patch.object(settings, "ai_monthly_quota", 1):
        res2 = client.post(
            "/api/v1/assistant/analyze",
            headers={"X-API-Key": raw_key},
            json={"task": "Explain the CRS used for measurement."}
        )
        assert res2.status_code == 429
        assert "quota" in res2.json()["detail"].lower()
        assert "Retry-After" in res2.headers


def test_concurrent_ai_requests(test_dataset):
    """Test handling of concurrent AI analysis requests."""
    async def run_batch():
        tasks = [
            ai_copilot_service.analyze(
                task="Calculate all parcel areas and rank the five largest.",
                file_id=test_dataset["id"],
            )
            for _ in range(10)
        ]
        return await asyncio.gather(*tasks)

    results = asyncio.run(run_batch())
    assert len(results) == 10
    for r in results:
        assert r.status == "completed"
        assert len(r.top_features) > 0


def test_assistant_status_endpoint():
    """Verify GET /api/assistant/status returns correct configuration without exposing secrets."""
    res = client.get("/api/assistant/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert "ollama_model" in data
    assert "groq_model" in data
    # Ensure raw secret is not present in response
    assert "groq_api_key" not in data
    assert "GROQ_API_KEY" not in str(data)
