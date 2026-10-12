"""
Deterministic Intent Handler for GeoMeasure Studio AI Copilot.
Enables sub-50ms latency for supported deterministic geospatial operations
without incurring LLM provider round-trips, network latency, or token costs.
"""

import re
import time
import logging
from typing import Dict, Any, List, Optional, Tuple

from app.services.ai.tools import (
    tool_inspect_dataset,
    tool_measure_features,
    tool_validate_geometries,
    tool_export_results,
)

logger = logging.getLogger(__name__)


class DeterministicIntentResult:
    """Result from a deterministically executed intent."""
    def __init__(
        self,
        intent: str,
        explanation: str,
        actions_executed: List[str],
        feature_summary: Optional[Dict[str, Any]] = None,
        top_features: Optional[List[Dict[str, Any]]] = None,
        highlighted_indices: Optional[List[int]] = None,
        validation_warnings: Optional[List[str]] = None,
        export_artifact: Optional[Dict[str, Any]] = None,
        latency_ms: float = 0.0,
    ):
        self.intent = intent
        self.explanation = explanation
        self.actions_executed = actions_executed
        self.feature_summary = feature_summary
        self.top_features = top_features or []
        self.highlighted_indices = highlighted_indices or []
        self.validation_warnings = validation_warnings or []
        self.export_artifact = export_artifact
        self.latency_ms = latency_ms


def try_handle_deterministic_intent(
    task: str,
    file_record: Optional[Dict[str, Any]],
    measurements: List[Dict[str, Any]]
) -> Optional[DeterministicIntentResult]:
    """
    Attempt to fulfill the user task using deterministic GIS engine routines.
    Returns DeterministicIntentResult if handled, or None if LLM reasoning is required.
    """
    start_time = time.perf_counter()
    clean_task = task.strip().lower()

    # If no dataset or measurements are loaded, handle general queries like CRS explanation
    if not file_record and not measurements:
        if re.search(r"\b(crs|projection|coordinate\s*system|utm|epsg|degrees|datum)\b", clean_task):
            expl = (
                "Coordinate Reference System (CRS) Explanation in GeoMeasure Studio:\n"
                "• Ingestion & Display: Standard WGS 84 (EPSG:4326) coordinates (latitude/longitude in decimal degrees).\n"
                "• Planar Metric Calculations: Universal Transverse Mercator (UTM) dynamic projection.\n\n"
                "Geospatial Projection Rationale:\n"
                "Geographic coordinates (EPSG:4326) represent angular positions on an ellipsoidal Earth surface. "
                "Because degrees of longitude converge toward the poles, computing Euclidean distances or areas on degree coordinates introduces significant distortion.\n"
                "GeoMeasure Studio computes the bounding centroid of your features and dynamically projects them into the appropriate local UTM zone prior to calculating metric areas and lengths."
            )
            latency = (time.perf_counter() - start_time) * 1000.0
            return DeterministicIntentResult(
                intent="explain_crs",
                explanation=expl,
                actions_executed=["inspect_dataset"],
                feature_summary={"source_crs": "EPSG:4326", "measurement_crs": ["Dynamic Local UTM"]},
                latency_ms=latency,
            )
        return None

    # 1. RANK / LARGEST / SMALLEST PARCELS / AREAS
    if re.search(r"\b(rank|ranks|ranking|order|sort|largest|biggest|top\s*\d+|highest\s*area|parcel\s*areas?)\b", clean_task):
        limit = 5
        match_num = re.search(r"\b(?:top|rank)\s*(\d+)\b", clean_task)
        if match_num:
            limit = min(50, max(1, int(match_num.group(1))))

        measure_res = tool_measure_features(measurements, rank_by="area", limit=limit, ascending=False)
        top_feats = measure_res["top_features"]
        indices = measure_res["highlighted_indices"]

        lines = [f"Ranked the {len(top_feats)} largest features by area in the active dataset:"]
        for i, f in enumerate(top_feats, start=1):
            area_m2 = f.get("area_sq_meters") or 0.0
            ha = f.get("area_hectares") or (area_m2 / 10000.0)
            crs = f.get("measurement_crs") or "UTM"
            lines.append(f"{i}. {f['feature_id']} — {area_m2:,.2f} m² ({ha:.4f} ha) [Projected: {crs}]")

        lines.append(f"Highlighted {len(indices)} selected features on the map preview.")
        latency = (time.perf_counter() - start_time) * 1000.0

        return DeterministicIntentResult(
            intent="rank_largest_areas",
            explanation="\n".join(lines),
            actions_executed=["measure_features"],
            top_features=top_feats,
            highlighted_indices=indices,
            latency_ms=latency,
        )

    # 2. VALIDATION / OVERLAPS / TOPOLOGICAL ERRORS
    if re.search(r"\b(overlap|overlapping|invalid|topology|self-intersect|validate|validity|error)\b", clean_task):
        val_res = tool_validate_geometries(file_record or {}, check_overlaps=True)
        total = val_res["total_evaluated"]
        invalid_cnt = val_res["invalid_count"]
        overlaps_cnt = val_res["overlaps_count"]
        warnings = val_res["warnings"]
        highlighted = val_res["highlighted_indices"]

        if invalid_cnt == 0 and overlaps_cnt == 0:
            expl = (
                f"Dataset geometry validation passed successfully across {total} features. "
                "All geometries are topologically valid with zero self-intersections or areal overlaps."
            )
        else:
            expl = (
                f"Geometry validation completed for {total} features:\n"
                f"• Invalid Geometries: {invalid_cnt}\n"
                f"• Overlapping Polygon Pairs: {overlaps_cnt}\n"
                f"• Flagged features have been highlighted on the map ({len(highlighted)} items)."
            )

        latency = (time.perf_counter() - start_time) * 1000.0
        return DeterministicIntentResult(
            intent="validate_geometries",
            explanation=expl,
            actions_executed=["validate_geometries"],
            validation_warnings=warnings,
            highlighted_indices=highlighted,
            latency_ms=latency,
        )

    # 3. EXPLAIN CRS / PROJECTION
    if re.search(r"\b(crs|projection|coordinate\s*(?:reference\s*)?system|utm|epsg|degrees|datum)\b", clean_task):
        src_crs = (file_record or {}).get("source_crs") or "EPSG:4326"
        meas_crs_set = {m.get("measurement_crs") for m in measurements if m.get("measurement_crs")}
        meas_crs_str = ", ".join([str(c) for c in meas_crs_set if c]) or "Dynamic Local UTM"

        expl = (
            f"Coordinate Reference System (CRS) Analysis for {file_record.get('original_filename', 'active dataset')}:\n"
            f"• Source CRS: {src_crs}\n"
            f"• Measurement CRS: {meas_crs_str}\n\n"
            "Geospatial Projection Rationale:\n"
            "Geographic coordinates (such as EPSG:4326 in degrees) are angular and cannot be used directly for planar metric measurements "
            "because the linear length of a degree of longitude shrinks towards the poles.\n"
            "GeoMeasure Studio dynamically computes the centroid of your geometries and reprojects them into the optimal local "
            "Universal Transverse Mercator (UTM) zone prior to planar area and distance calculations, ensuring rigorous metric accuracy."
        )
        latency = (time.perf_counter() - start_time) * 1000.0
        return DeterministicIntentResult(
            intent="explain_crs",
            explanation=expl,
            actions_executed=["inspect_dataset"],
            feature_summary={"source_crs": src_crs, "measurement_crs": list(meas_crs_set)},
            latency_ms=latency,
        )

    # 4. SUMMARIZE / FEATURE COUNTS / GEOMETRY TYPES
    if re.search(r"\b(summar(?:y|ize|ise|ized|izing)?|count|counts|how\s*many|breakdown|feature\s*counts?|geometry\s*types?|stats|statistics)\b", clean_task):
        inspect_res = tool_inspect_dataset(file_record or {}, measurements)
        total = inspect_res["total_features"]
        types_str = ", ".join([f"{k}: {v}" for k, v in inspect_res["geometry_type_breakdown"].items()])
        tot_area_ha = inspect_res["total_area_hectares"]
        tot_len_km = inspect_res["total_length_km"]

        expl = (
            f"Dataset Summary for '{inspect_res['original_filename']}':\n"
            f"• Total Features: {total}\n"
            f"• Geometry Types: {types_str}\n"
            f"• Total Planar Area: {inspect_res['total_area_sq_meters']:,.2f} m² ({tot_area_ha:.4f} ha)\n"
            f"• Total Length: {inspect_res['total_length_meters']:,.2f} m ({tot_len_km:.4f} km)\n"
            f"• Source CRS: {inspect_res['source_crs']}"
        )
        latency = (time.perf_counter() - start_time) * 1000.0
        return DeterministicIntentResult(
            intent="summarize_dataset",
            explanation=expl,
            actions_executed=["inspect_dataset"],
            feature_summary=inspect_res,
            latency_ms=latency,
        )

    # 5. EXPORT TO CSV / GEOJSON
    if re.search(r"\b(export|download|generate\s*(?:csv|geojson))\b", clean_task):
        fmt = "geojson" if "geojson" in clean_task else "csv"
        export_res = tool_export_results(file_record or {}, measurements, export_format=fmt)

        expl = (
            f"Generated {fmt.upper()} export artifact '{export_res['filename']}' "
            f"containing {export_res['record_count']} measured records.\n"
            "Download link and preview are prepared below."
        )
        latency = (time.perf_counter() - start_time) * 1000.0
        return DeterministicIntentResult(
            intent=f"export_{fmt}",
            explanation=expl,
            actions_executed=["export_results"],
            export_artifact=export_res,
            latency_ms=latency,
        )

    # Not a deterministic pattern; fallback to LLM provider
    return None
