"""
Core geospatial processing service.
Reads KML and Shapefile data, detects CRS, reprojects, and computes measurements.
"""

import geopandas as gpd
import pandas as pd
import json
import logging
import os
import tempfile
import zipfile
from typing import Dict, Any, List, Optional, Tuple

from shapely.geometry import mapping, shape
from shapely import wkt

from app.utils.crs_utils import get_utm_crs_string, is_geographic_crs, crs_to_string, validate_crs
from app.services.file_validator import validate_zip_archive

logger = logging.getLogger(__name__)

# Geometry types we can measure
POLYGON_TYPES = {"Polygon", "MultiPolygon"}
LINE_TYPES = {"LineString", "MultiLineString"}
POINT_TYPES = {"Point", "MultiPoint"}
SUPPORTED_TYPES = POLYGON_TYPES | LINE_TYPES | POINT_TYPES


class GeoProcessingError(Exception):
    """Raised when geospatial processing fails."""
    pass


def process_kml_file(file_path: str) -> Tuple[gpd.GeoDataFrame, str]:
    """
    Read a KML file using GeoPandas/Fiona.

    Args:
        file_path: Path to the .kml file.

    Returns:
        Tuple of (GeoDataFrame, source_crs_string).

    Raises:
        GeoProcessingError: If the file cannot be read.
    """
    try:
        # Fiona uses the GDAL KML driver — needs to specify driver explicitly
        gdf = gpd.read_file(file_path, driver="KML")

        if gdf.empty:
            raise GeoProcessingError("KML file contains no features.")

        # KML is always WGS84 (EPSG:4326) by specification
        source_crs = "EPSG:4326"
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")

        return gdf, source_crs

    except GeoProcessingError:
        raise
    except Exception as e:
        raise GeoProcessingError(f"Failed to read KML file: {str(e)}")


def process_shapefile_zip(file_path: str) -> Tuple[gpd.GeoDataFrame, str]:
    """
    Extract and read a zipped Shapefile.

    Args:
        file_path: Path to the .zip file.

    Returns:
        Tuple of (GeoDataFrame, source_crs_string).

    Raises:
        GeoProcessingError: If extraction or reading fails.
    """
    try:
        # Validate archive first
        validate_zip_archive(file_path)

        # Extract to a temporary directory with guaranteed cleanup
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(file_path, "r") as zf:
                zf.extractall(tmpdir)

            # Find the .shp file(s) in extracted content
            shp_files = []
            for root, dirs, files in os.walk(tmpdir):
                for f in files:
                    if f.lower().endswith(".shp"):
                        shp_files.append(os.path.join(root, f))

            if not shp_files:
                raise GeoProcessingError(
                    "No .shp file found in the ZIP archive."
                )

            # Use the first .shp file found
            shp_path = shp_files[0]
            if len(shp_files) > 1:
                logger.warning(
                    f"Multiple .shp files found in archive, using: {os.path.basename(shp_path)}"
                )

            gdf = gpd.read_file(shp_path)

            if gdf.empty:
                raise GeoProcessingError("Shapefile contains no features.")

            # Detect CRS
            if gdf.crs is not None:
                source_crs = crs_to_string(gdf.crs)
            else:
                # Shapefile has no .prj file or identifiable CRS metadata
                logger.warning(
                    "Shapefile has no identifiable CRS metadata (.prj file is missing). "
                    "Geometry and attributes are preserved, but measurements cannot be reliably computed without a known CRS."
                )
                source_crs = "Unknown (missing .prj)"

            return gdf, source_crs

    except GeoProcessingError:
        raise
    except Exception as e:
        raise GeoProcessingError(f"Failed to process shapefile: {str(e)}")


def compute_measurements(
    gdf: gpd.GeoDataFrame, source_crs: str
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Compute measurements for all features in a GeoDataFrame.

    For each feature:
    - Point: No measurement (just properties).
    - LineString: Length in meters (reprojected to UTM).
    - Polygon: Area in square meters (reprojected to UTM).
    - Unsupported: Flagged with geometry_type, no measurement.

    Args:
        gdf: GeoDataFrame with geometries.
        source_crs: Source CRS string for recording.

    Returns:
        Tuple of (measurements_list, geojson_dict).
    """
    measurements = []
    diagnostics = []

    for idx, row in gdf.iterrows():
        geom = row.geometry

        if geom is None or geom.is_empty:
            diagnostics.append(f"Feature {idx}: empty or null geometry, skipping.")
            continue

        geom_type = geom.geom_type
        feature_index = int(idx) if isinstance(idx, (int, float)) else len(measurements)

        # Extract properties (non-geometry columns)
        properties = {}
        for col in gdf.columns:
            if col != "geometry" and col != gdf.geometry.name:
                val = row[col]
                # Convert to JSON-safe types
                if pd.isna(val):
                    val = None
                elif hasattr(val, "isoformat"):
                    val = val.isoformat()
                elif hasattr(val, "item"):  # numpy types
                    val = val.item()
                properties[col] = val

        # Try to get a feature ID from properties
        feature_id = None
        for key in ["id", "ID", "Id", "fid", "FID", "name", "Name", "NAME"]:
            if key in properties and properties[key] is not None:
                feature_id = str(properties[key])
                break

        measurement = {
            "feature_index": feature_index,
            "feature_id": feature_id,
            "geometry_type": geom_type,
            "geometry_wkt": geom.wkt,
            "source_crs": source_crs,
            "measurement_crs": None,
            "area_sq_meters": None,
            "length_meters": None,
            "measurement_unit": "meters",
            "properties": properties,
        }

        if source_crs.startswith("Unknown") or (gdf.crs is None and not source_crs):
            diagnostics.append(
                f"Feature {feature_index}: CRS is unknown (missing .prj file). "
                "Geometry and attributes preserved, but area and length cannot be reliably computed. "
                "Please supply a Shapefile with a valid .prj file."
            )
        elif geom_type in SUPPORTED_TYPES:
            if geom_type in POINT_TYPES:
                # Points: no measurement needed
                pass
            else:
                # Known CRS: reproject to local UTM for accurate measurement
                try:
                    centroid = geom.centroid
                    if not is_geographic_crs(source_crs):
                        import pyproj
                        from shapely.ops import transform

                        project = pyproj.Transformer.from_crs(
                            source_crs, "EPSG:4326", always_xy=True
                        ).transform
                        centroid_4326 = transform(project, centroid)
                        lon, lat = centroid_4326.x, centroid_4326.y
                    else:
                        lon, lat = centroid.x, centroid.y

                    utm_crs = get_utm_crs_string(lon, lat)
                    measurement["measurement_crs"] = utm_crs

                    # Reproject the geometry to UTM for accurate measurement
                    geom_series = gpd.GeoSeries([geom], crs=source_crs)
                    geom_projected = geom_series.to_crs(utm_crs).iloc[0]

                    if geom_type in POLYGON_TYPES:
                        measurement["area_sq_meters"] = round(geom_projected.area, 4)
                    elif geom_type in LINE_TYPES:
                        measurement["length_meters"] = round(geom_projected.length, 4)

                except Exception as e:
                    logger.error(f"Measurement failed for feature {feature_index}: {e}")
                    diagnostics.append(
                        f"Feature {feature_index}: measurement failed — {str(e)}"
                    )
        else:
            diagnostics.append(
                f"Feature {feature_index}: unsupported geometry type '{geom_type}'."
            )

        measurements.append(measurement)

    # Generate GeoJSON from the original GeoDataFrame
    # Ensure it's in WGS84 for Leaflet compatibility
    try:
        if source_crs.startswith("Unknown") or gdf.crs is None:
            geojson = json.loads(gdf.to_json())
        else:
            gdf_4326 = gdf.to_crs("EPSG:4326") if not is_geographic_crs(gdf.crs) else gdf
            geojson = json.loads(gdf_4326.to_json())
    except Exception as e:
        logger.error(f"GeoJSON generation failed: {e}")
        geojson = {"type": "FeatureCollection", "features": []}

    if diagnostics:
        logger.info(f"Processing diagnostics: {diagnostics}")

    return measurements, geojson


def process_uploaded_file(
    file_path: str, file_extension: str
) -> Tuple[str, int, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Main entry point: process an uploaded file and return results.

    Args:
        file_path: Path to the uploaded file on disk.
        file_extension: File extension ('.kml' or '.zip').

    Returns:
        Tuple of (source_crs, feature_count, measurements, geojson).

    Raises:
        GeoProcessingError: If processing fails.
    """
    if file_extension == ".kml":
        gdf, source_crs = process_kml_file(file_path)
    elif file_extension == ".zip":
        gdf, source_crs = process_shapefile_zip(file_path)
    else:
        raise GeoProcessingError(f"Unsupported file extension: {file_extension}")

    feature_count = len(gdf)
    measurements, geojson = compute_measurements(gdf, source_crs)

    return source_crs, feature_count, measurements, geojson


def measure_single_geometry(
    geometry_dict: Dict[str, Any],
    source_crs: str,
    properties: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Measure an individual GeoJSON geometry submitted via the external API.
    Reuses existing UTM projection selection and metric calculation logic.

    Args:
        geometry_dict: GeoJSON geometry dictionary (e.g. {"type": "Polygon", "coordinates": [...]})
        source_crs: Coordinate reference system (e.g. "EPSG:4326").
        properties: Optional feature attributes.

    Returns:
        Structured measurement dictionary with metric area and length.

    Raises:
        GeoProcessingError: On invalid input, unsupported geometry, or unknown CRS.
    """
    # 1. Enforce strict CRS validation - never silently guess unknown CRS
    if not source_crs or source_crs.strip().lower().startswith("unknown"):
        raise GeoProcessingError(
            "An explicit, valid Coordinate Reference System (CRS) is required. Unknown CRS is not permitted."
        )
    if not validate_crs(source_crs):
        raise GeoProcessingError(
            f"Invalid or unrecognized Coordinate Reference System: '{source_crs}'"
        )

    # 2. Parse GeoJSON geometry into Shapely shape
    try:
        geom = shape(geometry_dict)
    except Exception as e:
        raise GeoProcessingError(f"Invalid GeoJSON geometry structure: {str(e)}")

    if geom is None or geom.is_empty:
        raise GeoProcessingError("Geometry is empty or null.")

    geom_type = geom.geom_type
    if geom_type not in SUPPORTED_TYPES:
        raise GeoProcessingError(f"Unsupported geometry type: '{geom_type}'.")

    # 3. Calculate metric measurements via local UTM zone reprojection
    measurement_crs = None
    area_sq_meters = None
    length_meters = None

    if geom_type in POINT_TYPES:
        # Points have no length or area
        pass
    else:
        try:
            centroid = geom.centroid
            if not is_geographic_crs(source_crs):
                import pyproj
                from shapely.ops import transform

                project = pyproj.Transformer.from_crs(
                    source_crs, "EPSG:4326", always_xy=True
                ).transform
                centroid_4326 = transform(project, centroid)
                lon, lat = centroid_4326.x, centroid_4326.y
            else:
                lon, lat = centroid.x, centroid.y

            utm_crs = get_utm_crs_string(lon, lat)
            measurement_crs = utm_crs

            # Reproject geometry to local UTM
            geom_series = gpd.GeoSeries([geom], crs=source_crs)
            geom_projected = geom_series.to_crs(utm_crs).iloc[0]

            if geom_type in POLYGON_TYPES:
                area_sq_meters = round(geom_projected.area, 4)
            elif geom_type in LINE_TYPES:
                length_meters = round(geom_projected.length, 4)

        except Exception as e:
            logger.error(f"Measurement calculation failed: {e}")
            raise GeoProcessingError(f"Measurement calculation failed: {str(e)}")

    return {
        "geometry_type": geom_type,
        "source_crs": source_crs,
        "measurement_crs": measurement_crs,
        "area_sq_meters": area_sq_meters,
        "length_meters": length_meters,
        "area_hectares": round(area_sq_meters / 10000.0, 4) if area_sq_meters is not None else None,
        "area_sq_km": round(area_sq_meters / 1000000.0, 4) if area_sq_meters is not None else None,
        "length_km": round(length_meters / 1000.0, 4) if length_meters is not None else None,
        "measurement_unit": "meters",
        "properties": properties or {},
    }

