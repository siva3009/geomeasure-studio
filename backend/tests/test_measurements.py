"""
Tests for measurement results and export utilities.
"""

import pytest
from app.utils.export import measurements_to_csv, measurements_to_geojson


SAMPLE_MEASUREMENTS = [
    {
        "feature_index": 0,
        "feature_id": "point_1",
        "geometry_type": "Point",
        "source_crs": "EPSG:4326",
        "measurement_crs": None,
        "area_sq_meters": None,
        "length_meters": None,
        "measurement_unit": "meters",
    },
    {
        "feature_index": 1,
        "feature_id": "line_1",
        "geometry_type": "LineString",
        "source_crs": "EPSG:4326",
        "measurement_crs": "EPSG:32643",
        "area_sq_meters": None,
        "length_meters": 1500.0,
        "measurement_unit": "meters",
    },
    {
        "feature_index": 2,
        "feature_id": "poly_1",
        "geometry_type": "Polygon",
        "source_crs": "EPSG:4326",
        "measurement_crs": "EPSG:32643",
        "area_sq_meters": 1050000.0,
        "length_meters": None,
        "measurement_unit": "meters",
    },
]


class TestMeasurementsToCsv:
    def test_csv_has_header(self):
        csv = measurements_to_csv(SAMPLE_MEASUREMENTS)
        lines = csv.strip().split("\n")
        assert "feature_index" in lines[0]
        assert "geometry_type" in lines[0]

    def test_csv_has_correct_row_count(self):
        csv = measurements_to_csv(SAMPLE_MEASUREMENTS)
        lines = csv.strip().split("\n")
        # 1 header + 3 data rows
        assert len(lines) == 4

    def test_empty_list_returns_empty(self):
        assert measurements_to_csv([]) == ""


class TestMeasurementsToGeojson:
    def test_returns_feature_collection(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": {"type": "Point"}, "properties": {"name": "A"}},
                {"type": "Feature", "geometry": {"type": "LineString"}, "properties": {"name": "B"}},
                {"type": "Feature", "geometry": {"type": "Polygon"}, "properties": {"name": "C"}},
            ],
        }
        result = measurements_to_geojson(SAMPLE_MEASUREMENTS, geojson)
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 3

    def test_measurements_merged_into_properties(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": {"type": "Polygon"}, "properties": {}},
            ],
        }
        m = [SAMPLE_MEASUREMENTS[2]]  # Polygon measurement
        result = measurements_to_geojson(m, geojson)
        props = result["features"][0]["properties"]
        assert props["_area_sq_meters"] == 1050000.0
        assert props["_measurement_unit"] == "meters"

    def test_empty_geojson_handled(self):
        result = measurements_to_geojson(SAMPLE_MEASUREMENTS, None)
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 0
