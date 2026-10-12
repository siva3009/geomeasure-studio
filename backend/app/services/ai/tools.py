"""
Approved GIS Tool Registry for GeoMeasure Studio AI Copilot.
All numerical computations come strictly from the deterministic GIS engine (GeoPandas, Shapely, PyProj).
Arbitrary SQL, shell, Python execution, or file-system paths are strictly prohibited.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from shapely.geometry import shape
from shapely.validation import explain_validity

from app.utils.export import measurements_to_csv, measurements_to_geojson

logger = logging.getLogger(__name__)

# Strict allowlist of tool names
APPROVED_TOOL_NAMES = {
    "inspect_dataset",
    "measure_features",
    "validate_geometries",
    "export_results",
}

# Tool schemas exposed to the AI model
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "inspect_dataset",
            "description": "Inspect dataset feature counts, geometry types, attributes, bounding box, and CRS metadata.",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_attributes": {
                        "type": "boolean",
                        "description": "Whether to include attribute property schema summary."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "measure_features",
            "description": "Calculate planar metric measurements, rank top features by area or length, and highlight them.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rank_by": {
                        "type": "string",
                        "enum": ["area", "length"],
                        "description": "Measurement metric to rank features by ('area' for polygons, 'length' for linestrings)."
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "description": "Maximum number of top features to return (default: 5)."
                    },
                    "ascending": {
                        "type": "boolean",
                        "description": "True for smallest first, False for largest first (default: False)."
                    }
                },
                "required": ["rank_by"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_geometries",
            "description": "Validate geometries for self-intersections, topological errors, null coordinates, and overlapping polygons.",
            "parameters": {
                "type": "object",
                "properties": {
                    "check_overlaps": {
                        "type": "boolean",
                        "description": "Whether to run pairwise overlap checks for polygons (default: true)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "export_results",
            "description": "Generate an export artifact (CSV or GeoJSON) of measured features for download.",
            "parameters": {
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["csv", "geojson"],
                        "description": "Export format ('csv' or 'geojson')."
                    }
                },
                "required": ["format"]
            }
        }
    }
]


def tool_inspect_dataset(
    file_record: Dict[str, Any],
    measurements: List[Dict[str, Any]],
    include_attributes: bool = True
) -> Dict[str, Any]:
    """Inspect dataset metadata, feature counts, and geometry distribution."""
    total_features = len(measurements)
    type_counts: Dict[str, int] = {}
    total_area_sq_m = 0.0
    total_length_m = 0.0
    crs_list = set()

    for m in measurements:
        gtype = m.get("geometry_type") or "Unknown"
        type_counts[gtype] = type_counts.get(gtype, 0) + 1
        if m.get("area_sq_meters"):
            total_area_sq_m += m["area_sq_meters"]
        if m.get("length_meters"):
            total_length_m += m["length_meters"]
        if m.get("measurement_crs"):
            crs_list.add(m["measurement_crs"])

    # Extract sample properties keys
    sample_attributes = []
    if include_attributes and measurements:
        props = measurements[0].get("properties") or {}
        sample_attributes = list(props.keys())[:15]

    source_crs = file_record.get("source_crs") or "EPSG:4326"

    return {
        "dataset_id": str(file_record.get("id")),
        "original_filename": file_record.get("original_filename"),
        "total_features": total_features,
        "geometry_type_breakdown": type_counts,
        "source_crs": source_crs,
        "measurement_crs": list(crs_list) or [None],
        "total_area_sq_meters": round(total_area_sq_m, 2),
        "total_area_hectares": round(total_area_sq_m / 10000.0, 4),
        "total_length_meters": round(total_length_m, 2),
        "total_length_km": round(total_length_m / 1000.0, 4),
        "attribute_fields": sample_attributes,
        "status": file_record.get("status", "completed"),
    }


def tool_measure_features(
    measurements: List[Dict[str, Any]],
    rank_by: str = "area",
    limit: int = 5,
    ascending: bool = False
) -> Dict[str, Any]:
    """Rank features by metric area or length and return highlights."""
    metric_field = "area_sq_meters" if rank_by.lower() == "area" else "length_meters"
    
    # Filter only features with valid metric
    measurable = [m for m in measurements if m.get(metric_field) is not None]
    measurable.sort(key=lambda x: x.get(metric_field) or 0.0, reverse=not ascending)

    top_items = measurable[:limit]
    highlighted_indices = [item["feature_index"] for item in top_items if "feature_index" in item]

    formatted_features = []
    for item in top_items:
        area_sq_m = item.get("area_sq_meters")
        length_m = item.get("length_meters")
        formatted_features.append({
            "feature_index": item.get("feature_index"),
            "feature_id": item.get("feature_id") or f"Feature #{item.get('feature_index')}",
            "geometry_type": item.get("geometry_type"),
            "area_sq_meters": area_sq_m,
            "area_hectares": round(area_sq_m / 10000.0, 4) if area_sq_m is not None else None,
            "length_meters": length_m,
            "measurement_crs": item.get("measurement_crs"),
            "properties": {k: v for k, v in (item.get("properties") or {}).items() if k not in ("geometry_wkt",)}
        })

    return {
        "metric_ranked": rank_by,
        "total_measurable_features": len(measurable),
        "returned_count": len(top_items),
        "top_features": formatted_features,
        "highlighted_indices": highlighted_indices,
    }


def tool_validate_geometries(
    file_record: Dict[str, Any],
    check_overlaps: bool = True
) -> Dict[str, Any]:
    """Validate GeoJSON geometries for topological correctness and self-intersections."""
    geojson = file_record.get("geojson") or {}
    features = geojson.get("features", [])
    
    valid_count = 0
    invalid_count = 0
    warnings = []
    invalid_indices = []
    overlapping_indices = set()

    shapely_polygons = []

    for idx, f in enumerate(features):
        geom_json = f.get("geometry")
        if not geom_json or not geom_json.get("coordinates"):
            invalid_count += 1
            invalid_indices.append(idx)
            warnings.append(f"Feature {idx}: Empty or null coordinates.")
            continue

        try:
            geom_obj = shape(geom_json)
            if not geom_obj.is_valid:
                invalid_count += 1
                invalid_indices.append(idx)
                reason = explain_validity(geom_obj)
                warnings.append(f"Feature {idx} ({geom_obj.geom_type}): Invalid geometry — {reason}")
            else:
                valid_count += 1
                if geom_obj.geom_type in ("Polygon", "MultiPolygon"):
                    shapely_polygons.append((idx, geom_obj))
        except Exception as e:
            invalid_count += 1
            invalid_indices.append(idx)
            warnings.append(f"Feature {idx}: Failed to parse geometry ({str(e)})")

    # Check pairwise polygon overlaps (bounded to first 250 polygons to preserve low latency)
    overlaps_found = []
    if check_overlaps and len(shapely_polygons) > 1:
        poly_sample = shapely_polygons[:250]
        for i in range(len(poly_sample)):
            idx_a, poly_a = poly_sample[i]
            for j in range(i + 1, len(poly_sample)):
                idx_b, poly_b = poly_sample[j]
                try:
                    if poly_a.intersects(poly_b):
                        intersection = poly_a.intersection(poly_b)
                        if intersection.area > 1e-7:  # Meaningful areal overlap
                            overlapping_indices.add(idx_a)
                            overlapping_indices.add(idx_b)
                            overlaps_found.append({
                                "feature_a": idx_a,
                                "feature_b": idx_b,
                                "overlap_area_approx": round(intersection.area, 6)
                            })
                            if len(overlaps_found) >= 15:
                                break
                except Exception:
                    pass
            if len(overlaps_found) >= 15:
                break

    if overlaps_found:
        warnings.append(f"Detected {len(overlaps_found)} overlapping polygon pairs.")

    all_flagged_indices = sorted(list(set(invalid_indices) | overlapping_indices))

    return {
        "total_evaluated": len(features),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "overlaps_count": len(overlaps_found),
        "overlaps": overlaps_found[:10],
        "warnings": warnings[:20],
        "highlighted_indices": all_flagged_indices,
    }


def tool_export_results(
    file_record: Dict[str, Any],
    measurements: List[Dict[str, Any]],
    export_format: str = "csv"
) -> Dict[str, Any]:
    """Generate an export artifact from measurements."""
    fmt = export_format.lower().strip()
    if fmt not in ("csv", "geojson"):
        fmt = "csv"

    filename = file_record.get("original_filename") or "dataset"
    base_name = filename.rsplit(".", 1)[0]
    out_filename = f"{base_name}_copilot_export.{fmt}"
    file_id = str(file_record.get("id"))

    download_url = f"/api/files/{file_id}/measurements/export/{fmt}"

    preview = ""
    if fmt == "csv":
        csv_str = measurements_to_csv(measurements)
        lines = csv_str.strip().split("\n")
        preview = "\n".join(lines[:4])
    else:
        file_geojson = file_record.get("geojson") or {}
        enhanced = measurements_to_geojson(measurements, file_geojson)
        features_sample = enhanced.get("features", [])[:2]
        preview = json.dumps({"type": "FeatureCollection", "features": features_sample}, indent=2)

    return {
        "format": fmt,
        "filename": out_filename,
        "record_count": len(measurements),
        "download_url": download_url,
        "content_preview": preview,
    }
