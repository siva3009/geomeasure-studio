"""
CSV and GeoJSON export utilities.
"""

import csv
import io
import json
from typing import List, Dict, Any


def measurements_to_csv(measurements: List[Dict[str, Any]]) -> str:
    """
    Convert a list of measurement dicts to CSV string.

    Args:
        measurements: List of measurement result dictionaries.

    Returns:
        CSV-formatted string.
    """
    if not measurements:
        return ""

    output = io.StringIO()
    fieldnames = [
        "feature_index",
        "feature_id",
        "geometry_type",
        "source_crs",
        "measurement_crs",
        "area_sq_meters",
        "length_meters",
        "measurement_unit",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for m in measurements:
        row = {k: m.get(k, "") for k in fieldnames}
        writer.writerow(row)

    return output.getvalue()


def measurements_to_geojson(
    measurements: List[Dict[str, Any]], file_geojson: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge measurement data into a GeoJSON FeatureCollection.
    Adds measurement values as properties on each feature.

    Args:
        measurements: List of measurement result dictionaries.
        file_geojson: Original GeoJSON FeatureCollection from the file.

    Returns:
        Enhanced GeoJSON FeatureCollection with measurement properties.
    """
    if not file_geojson or "features" not in file_geojson:
        return {"type": "FeatureCollection", "features": []}

    features = file_geojson.get("features", [])
    index_lookup = {m["feature_index"]: m for m in measurements if "feature_index" in m}
    id_lookup = {str(m.get("feature_id")): m for m in measurements if m.get("feature_id")}

    enhanced_features = []
    for i, feature in enumerate(features):
        enhanced_feature = json.loads(json.dumps(feature))  # Deep copy
        m = index_lookup.get(i)
        if not m and feature.get("id") is not None:
            m = id_lookup.get(str(feature["id"]))
        if not m and len(features) == 1 and len(measurements) == 1:
            m = measurements[0]

        if m:
            props = dict(enhanced_feature.get("properties") or {})
            props["_measurement_crs"] = m.get("measurement_crs")
            props["_area_sq_meters"] = m.get("area_sq_meters")
            props["_length_meters"] = m.get("length_meters")
            props["_measurement_unit"] = m.get("measurement_unit")
            enhanced_feature["properties"] = props
        enhanced_features.append(enhanced_feature)

    return {"type": "FeatureCollection", "features": enhanced_features}
