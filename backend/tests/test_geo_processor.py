"""
Tests for geospatial processing service.
"""

import os
import pytest
from app.services.geo_processor import (
    process_kml_file,
    process_shapefile_zip,
    compute_measurements,
    GeoProcessingError,
)


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestProcessKmlFile:
    """Tests for KML file reading."""

    def test_read_sample_kml(self, sample_kml_path):
        """Should successfully read the sample KML and return 3 features."""
        gdf, crs = process_kml_file(sample_kml_path)
        assert len(gdf) == 3
        assert crs == "EPSG:4326"

    def test_kml_has_correct_geometry_types(self, sample_kml_path):
        """Should detect Point, LineString, and Polygon."""
        gdf, _ = process_kml_file(sample_kml_path)
        geom_types = set(gdf.geometry.geom_type)
        assert "Point" in geom_types
        assert "LineString" in geom_types
        assert "Polygon" in geom_types


class TestComputeMeasurements:
    """Tests for measurement computation."""

    def test_polygon_has_area(self, sample_kml_path):
        """Polygon features should have area_sq_meters populated."""
        gdf, crs = process_kml_file(sample_kml_path)
        measurements, geojson = compute_measurements(gdf, crs)

        polygon_measurements = [
            m for m in measurements if m["geometry_type"] == "Polygon"
        ]
        assert len(polygon_measurements) > 0
        for m in polygon_measurements:
            assert m["area_sq_meters"] is not None
            assert m["area_sq_meters"] > 0
            assert m["measurement_crs"] is not None
            assert m["measurement_crs"].startswith("EPSG:")

    def test_linestring_has_length(self, sample_kml_path):
        """LineString features should have length_meters populated."""
        gdf, crs = process_kml_file(sample_kml_path)
        measurements, _ = compute_measurements(gdf, crs)

        line_measurements = [
            m for m in measurements if m["geometry_type"] == "LineString"
        ]
        assert len(line_measurements) > 0
        for m in line_measurements:
            assert m["length_meters"] is not None
            assert m["length_meters"] > 0

    def test_point_has_no_measurement(self, sample_kml_path):
        """Point features should have null area and length."""
        gdf, crs = process_kml_file(sample_kml_path)
        measurements, _ = compute_measurements(gdf, crs)

        point_measurements = [
            m for m in measurements if m["geometry_type"] == "Point"
        ]
        assert len(point_measurements) > 0
        for m in point_measurements:
            assert m["area_sq_meters"] is None
            assert m["length_meters"] is None

    def test_polygon_area_reasonable(self, sample_kml_path):
        """
        The test polygon is ~0.01° x 0.01° near lat 28°.
        At that latitude, 0.01° longitude ≈ 982m, 0.01° latitude ≈ 1105m.
        Expected area ≈ ~1,085,000 m² (roughly 1 km²).
        We check it's within a reasonable range (0.5 to 2.0 km²).
        """
        gdf, crs = process_kml_file(sample_kml_path)
        measurements, _ = compute_measurements(gdf, crs)

        polygon_m = [m for m in measurements if m["geometry_type"] == "Polygon"]
        assert len(polygon_m) == 1
        area = polygon_m[0]["area_sq_meters"]
        # Should be roughly 1 km² = 1,000,000 m²
        assert 500_000 < area < 2_000_000, f"Area {area} m² is outside expected range"

    def test_measurement_crs_is_utm(self, sample_kml_path):
        """Measurement CRS should be a UTM zone."""
        gdf, crs = process_kml_file(sample_kml_path)
        measurements, _ = compute_measurements(gdf, crs)

        for m in measurements:
            if m["measurement_crs"] is not None:
                epsg_code = int(m["measurement_crs"].split(":")[1])
                # UTM north: 32601-32660, UTM south: 32701-32760
                assert (32601 <= epsg_code <= 32660) or (32701 <= epsg_code <= 32760)

    def test_geojson_output_valid(self, sample_kml_path):
        """Should produce a valid GeoJSON FeatureCollection."""
        gdf, crs = process_kml_file(sample_kml_path)
        _, geojson = compute_measurements(gdf, crs)

        assert geojson["type"] == "FeatureCollection"
        assert len(geojson["features"]) == 3
        for feature in geojson["features"]:
            assert "geometry" in feature
            assert "properties" in feature

    def test_source_crs_preserved(self, sample_kml_path):
        """Source CRS should be preserved in each measurement."""
        gdf, crs = process_kml_file(sample_kml_path)
        measurements, _ = compute_measurements(gdf, crs)

        for m in measurements:
            assert m["source_crs"] == "EPSG:4326"


class TestProcessShapefileZip:
    """Tests for zipped Shapefile reading."""

    def test_read_sample_shapefile_zip(self, sample_shapefile_zip_path):
        """Should read zipped shapefile and extract features."""
        gdf, crs = process_shapefile_zip(sample_shapefile_zip_path)
        assert len(gdf) == 1
        assert "EPSG:4326" in crs
        assert gdf.geometry.iloc[0].geom_type == "Polygon"

    def test_shapefile_measurements_computed(self, sample_shapefile_zip_path):
        """Should compute polygon area correctly for shapefile."""
        gdf, crs = process_shapefile_zip(sample_shapefile_zip_path)
        measurements, geojson = compute_measurements(gdf, crs)
        assert len(measurements) == 1
        assert measurements[0]["geometry_type"] == "Polygon"
        assert measurements[0]["area_sq_meters"] is not None
        assert measurements[0]["area_sq_meters"] > 0
        assert geojson["type"] == "FeatureCollection"
        # Verify source_crs and measurement_crs are recorded separately
        assert measurements[0]["source_crs"] is not None
        assert measurements[0]["measurement_crs"] is not None
        assert measurements[0]["measurement_crs"].startswith("EPSG:326")

    def test_missing_prj_coordinates_within_180_not_assumed_epsg4326(self, tmp_path):
        """
        Requirements: For Shapefiles without identifiable CRS metadata,
        preserve geometry and attributes, set CRS status to unknown,
        add a clear warning, and do NOT report area or length as trustworthy measurements.
        Do NOT silently assign EPSG:4326 merely because coordinates fall within [-180, 180].
        """
        import zipfile
        import geopandas as gpd
        from shapely.geometry import Polygon

        poly = Polygon([(77.0, 28.0), (77.01, 28.0), (77.01, 28.01), (77.0, 28.01)])
        gdf_geo = gpd.GeoDataFrame({"parcel": ["Lot A"]}, geometry=[poly])
        shp_dir = tmp_path / "shp_noprj_geo"
        shp_dir.mkdir()
        shp_path = shp_dir / "test_geo.shp"
        gdf_geo.to_file(shp_path)

        # Remove .prj if created
        prj_path = shp_dir / "test_geo.prj"
        if prj_path.exists():
            prj_path.unlink()

        zip_path = tmp_path / "test_geo_noprj.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for ext in [".shp", ".shx", ".dbf"]:
                f = shp_dir / f"test_geo{ext}"
                if f.exists():
                    zf.write(f, f"test_geo{ext}")

        gdf_read, detected_crs = process_shapefile_zip(str(zip_path))
        # Must NOT silently assume EPSG:4326
        assert detected_crs == "Unknown (missing .prj)"
        assert "EPSG:4326" not in detected_crs

        measurements, geojson = compute_measurements(gdf_read, detected_crs)
        assert len(measurements) == 1
        # Geometry and attributes must be preserved
        assert measurements[0]["geometry_type"] == "Polygon"
        assert measurements[0]["properties"]["parcel"] == "Lot A"
        assert geojson["type"] == "FeatureCollection"
        assert len(geojson["features"]) == 1

        # CRS must be set to unknown
        assert measurements[0]["source_crs"] == "Unknown (missing .prj)"
        assert measurements[0]["measurement_crs"] is None

        # Area and length must NOT be reported as trustworthy measurements
        assert measurements[0]["area_sq_meters"] is None
        assert measurements[0]["length_meters"] is None

    def test_missing_prj_projected_coordinates_withholds_measurements(self, tmp_path):
        """
        Shapefiles with projected coordinates and missing .prj must have CRS set to unknown
        and measurements withheld, with geometry and attributes preserved.
        """
        import zipfile
        import geopandas as gpd
        from shapely.geometry import Polygon

        poly = Polygon([(500000, 4200000), (501000, 4200000), (501000, 4201000), (500000, 4201000)])
        gdf_proj = gpd.GeoDataFrame({"id": [99]}, geometry=[poly])
        shp_dir = tmp_path / "shp_noprj_proj"
        shp_dir.mkdir()
        shp_path = shp_dir / "projected.shp"
        gdf_proj.to_file(shp_path)

        prj_path = shp_dir / "projected.prj"
        if prj_path.exists():
            prj_path.unlink()

        zip_path = tmp_path / "projected_noprj.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for ext in [".shp", ".shx", ".dbf"]:
                f = shp_dir / f"projected{ext}"
                if f.exists():
                    zf.write(f, f"projected{ext}")

        gdf_read, detected_crs = process_shapefile_zip(str(zip_path))
        assert detected_crs == "Unknown (missing .prj)"

        measurements, geojson = compute_measurements(gdf_read, detected_crs)
        assert len(measurements) == 1
        assert measurements[0]["properties"]["id"] == 99
        assert measurements[0]["source_crs"] == "Unknown (missing .prj)"
        assert measurements[0]["measurement_crs"] is None
        assert measurements[0]["area_sq_meters"] is None
        assert measurements[0]["length_meters"] is None

    def test_valid_projected_crs_shapefile_measured_accurately(self, tmp_path):
        """Shapefiles WITH a valid projected CRS .prj calculate accurate measurements."""
        import zipfile
        import geopandas as gpd
        from shapely.geometry import Polygon

        # 1000m x 1000m square in UTM zone 43N (EPSG:32643)
        poly = Polygon([(500000, 3100000), (501000, 3100000), (501000, 3101000), (500000, 3101000)])
        gdf_utm = gpd.GeoDataFrame({"zone": ["43N"]}, geometry=[poly], crs="EPSG:32643")
        shp_dir = tmp_path / "shp_valid_utm"
        shp_dir.mkdir()
        shp_path = shp_dir / "valid_utm.shp"
        gdf_utm.to_file(shp_path)

        zip_path = tmp_path / "valid_utm.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
                f = shp_dir / f"valid_utm{ext}"
                if f.exists():
                    zf.write(f, f"valid_utm{ext}")

        gdf_read, detected_crs = process_shapefile_zip(str(zip_path))
        assert "32643" in detected_crs

        measurements, _ = compute_measurements(gdf_read, detected_crs)
        assert len(measurements) == 1
        assert measurements[0]["geometry_type"] == "Polygon"
        assert measurements[0]["source_crs"] is not None
        assert measurements[0]["measurement_crs"] is not None
        # ~1,000,000 m²
        assert 990_000 <= measurements[0]["area_sq_meters"] <= 1_010_000



