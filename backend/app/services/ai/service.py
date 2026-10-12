"""
AI Copilot Orchestration Service for GeoMeasure Studio.
Orchestrates fast-path deterministic intent execution, LLM-based reasoning,
approved GIS tool execution, latency tracking, and privacy boundary enforcement.
"""

import copy
import json
import logging
import time
from typing import Dict, Any, List, Optional
from uuid import UUID

from app.config import settings
from app.schemas.ai import (
    AIAssistantResponse,
    GISFeatureItem,
    ExportArtifact,
    ProviderMetadata,
    LatencyBreakdown,
)
from app.services.ai.gateway import ai_gateway
from app.services.ai.intent_handler import try_handle_deterministic_intent
from app.services.ai.tools import (
    APPROVED_TOOL_NAMES,
    TOOL_DEFINITIONS,
    tool_inspect_dataset,
    tool_measure_features,
    tool_validate_geometries,
    tool_export_results,
)
from app.services.ai.providers import ProviderError
import app.services.db_service as db_service

logger = logging.getLogger(__name__)


def _build_bounded_dataset_context(
    file_record: Optional[Dict[str, Any]],
    measurements: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Build a safe, token-bounded metadata summary of the active dataset.
    Never sends full multi-megabyte coordinate arrays to the LLM.
    """
    if not file_record:
        return {"has_dataset": False}

    geojson = file_record.get("geojson") or {}
    features = geojson.get("features", [])
    total_features = len(features)

    geom_types: Dict[str, int] = {}
    property_keys = set()
    sample_features = []

    for idx, f in enumerate(features[: total_features]):
        gt = (f.get("geometry") or {}).get("type", "Unknown")
        geom_types[gt] = geom_types.get(gt, 0) + 1
        props = f.get("properties") or {}
        property_keys.update(props.keys())

        # Include first 3 features with bounded geometry preview
        if idx < 3:
            sample_copy = {
                "feature_index": idx,
                "geometry_type": gt,
                "properties": {k: props[k] for k in list(props.keys())[:5]},
            }
            sample_features.append(sample_copy)

    total_area_m2 = sum((m.get("area_sq_meters") or 0.0) for m in measurements)
    total_length_m = sum((m.get("length_meters") or 0.0) for m in measurements)

    return {
        "has_dataset": True,
        "filename": file_record.get("original_filename", "active_dataset.geojson"),
        "total_features": total_features,
        "geometry_types": geom_types,
        "property_keys": sorted(list(property_keys))[:15],
        "source_crs": file_record.get("source_crs") or "EPSG:4326",
        "total_area_sq_meters": round(total_area_m2, 2),
        "total_length_meters": round(total_length_m, 2),
        "sample_features": sample_features,
    }


class AICopilotService:
    """Core coordinator for AI GIS inquiries, tool calling, and execution."""

    async def analyze(
        self,
        task: str,
        file_id: Optional[str] = None,
        geometry_payload: Optional[Dict[str, Any]] = None,
        dataset_context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        privacy_mode: Optional[str] = None,
        provider_mode: Optional[str] = None,
    ) -> AIAssistantResponse:
        """
        Execute geospatial AI analysis with sub-50ms deterministic fast-path
        and low-latency hybrid LLM fallback.
        """
        overall_start = time.perf_counter()
        clean_task = task.strip()
        if not clean_task:
            raise ValueError("Task prompt cannot be empty.")

        # -------------------------------------------------------------------
        # 1. Resolve Dataset & Geometries with Ownership Verification
        # -------------------------------------------------------------------
        file_record: Optional[Dict[str, Any]] = None
        measurements: List[Dict[str, Any]] = []

        if file_id:
            raw_file = db_service.get_file_by_id(file_id)
            if not raw_file:
                raise FileNotFoundError(f"Dataset with ID '{file_id}' not found.")
            if user_id and raw_file.get("user_id") and str(raw_file.get("user_id")) != str(user_id):
                raise PermissionError(f"Access denied: Dataset '{file_id}' does not belong to authenticated user.")

            file_record = {
                "id": raw_file.get("id"),
                "original_filename": raw_file.get("original_filename", "dataset.geojson"),
                "source_crs": raw_file.get("source_crs", "EPSG:4326"),
                "geojson": raw_file.get("geojson", {}),
            }
            measurements = db_service.get_measurements_by_file_id(file_id)

        elif geometry_payload:
            # Ephemeral / in-memory geometry payload from API playground or active web canvas
            file_record = {
                "id": "ephemeral_dataset",
                "original_filename": "uploaded_dataset.geojson",
                "source_crs": "EPSG:4326",
                "geojson": geometry_payload,
            }
            # Measurements might be provided in dataset_context
            if dataset_context and "measurements" in dataset_context:
                measurements = dataset_context["measurements"]

        # -------------------------------------------------------------------
        # 2. Layer 1: Sub-50ms Deterministic Intent Fast-Path
        # -------------------------------------------------------------------
        det_result = try_handle_deterministic_intent(clean_task, file_record, measurements)
        if det_result is not None:
            total_duration_ms = (time.perf_counter() - overall_start) * 1000.0
            return AIAssistantResponse(
                status="completed",
                task=clean_task,
                intent=det_result.intent,
                explanation=det_result.explanation,
                actions_executed=det_result.actions_executed,
                feature_summary=det_result.feature_summary,
                top_features=[GISFeatureItem(**f) for f in det_result.top_features],
                highlighted_indices=det_result.highlighted_indices,
                validation_warnings=det_result.validation_warnings,
                export_artifact=ExportArtifact(**det_result.export_artifact) if det_result.export_artifact else None,
                provider_metadata=ProviderMetadata(
                    provider="deterministic_engine",
                    model="rule-engine-v1",
                    is_local=True,
                    latency_ms=round(det_result.latency_ms, 2),
                    routed_via="deterministic_intent",
                ),
                latency_breakdown=LatencyBreakdown(
                    total_ms=round(total_duration_ms, 2),
                    intent_ms=round(det_result.latency_ms, 2),
                    provider_ms=0.0,
                    tool_execution_ms=round(det_result.latency_ms, 2),
                ),
            )

        # -------------------------------------------------------------------
        # 3. Layer 2: LLM Inference via Provider Gateway
        # -------------------------------------------------------------------
        bounded_summary = _build_bounded_dataset_context(file_record, measurements)

        system_prompt = (
            "You are GeoMeasure AI Copilot, a high-performance GIS assistant for GeoMeasure Studio.\n"
            "You provide accurate spatial analysis and coordinate reference explanations.\n"
            "You have access to approved GIS tools for measurements, validation, and exports.\n"
            "CRITICAL RULES:\n"
            "1. When the user asks to measure, rank, inspect, validate, or export features, propose the corresponding tool call.\n"
            "2. Never invent fake numerical measurements; rely on the tool output.\n"
            "3. Keep explanations concise, professional, and directly focused on geospatial properties."
        )

        user_content = f"Dataset Summary:\n{json.dumps(bounded_summary, indent=2)}\n\nUser Question:\n{clean_task}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        provider_start = time.perf_counter()
        provider_res = await ai_gateway.complete(
            messages=messages,
            tools=TOOL_DEFINITIONS,
            mode_override=provider_mode,
            privacy_override=privacy_mode,
        )
        provider_inference_ms = (time.perf_counter() - provider_start) * 1000.0

        # -------------------------------------------------------------------
        # 4. Tool Execution (Approved GIS Tool Registry)
        # -------------------------------------------------------------------
        tool_start = time.perf_counter()
        actions_executed: List[str] = []
        top_features: List[Dict[str, Any]] = []
        highlighted_indices: List[int] = []
        validation_warnings: List[str] = []
        export_artifact: Optional[Dict[str, Any]] = None
        feature_summary: Optional[Dict[str, Any]] = None

        if provider_res.tool_calls:
            for tc in provider_res.tool_calls:
                fn_name = tc.get("name")
                args = tc.get("arguments") or {}

                if fn_name not in APPROVED_TOOL_NAMES:
                    logger.warning("Model requested unapproved tool: %s. Ignoring.", fn_name)
                    continue

                actions_executed.append(fn_name)

                if fn_name == "inspect_dataset":
                    feature_summary = tool_inspect_dataset(
                        file_record or {},
                        measurements,
                        include_attributes=args.get("include_attributes", True),
                    )

                elif fn_name == "measure_features":
                    rank_by = args.get("rank_by", "area")
                    limit_raw = args.get("limit")
                    try:
                        limit = min(50, max(1, int(limit_raw))) if limit_raw is not None else 5
                    except (ValueError, TypeError):
                        limit = 5
                    meas_res = tool_measure_features(measurements, rank_by=rank_by, limit=limit)
                    top_features.extend(meas_res.get("top_features", []))
                    highlighted_indices.extend(meas_res.get("highlighted_indices", []))

                elif fn_name == "validate_geometries":
                    check_overlaps = bool(args.get("check_overlaps", True))
                    val_res = tool_validate_geometries(file_record or {}, check_overlaps=check_overlaps)
                    validation_warnings.extend(val_res.get("warnings", []))
                    highlighted_indices.extend(val_res.get("highlighted_indices", []))

                elif fn_name == "export_results":
                    export_fmt = args.get("format", "csv")
                    export_artifact = tool_export_results(
                        file_record or {},
                        measurements,
                        export_format=export_fmt,
                    )

        tool_execution_ms = (time.perf_counter() - tool_start) * 1000.0

        # Construct explanation
        explanation = provider_res.content or ""
        if not explanation and actions_executed:
            explanation = f"Executed {', '.join(actions_executed)} using GeoMeasure deterministic GIS engine."

        total_duration_ms = (time.perf_counter() - overall_start) * 1000.0

        return AIAssistantResponse(
            status="completed",
            task=clean_task,
            intent="geospatial_inquiry",
            explanation=explanation,
            actions_executed=actions_executed,
            feature_summary=feature_summary,
            top_features=[GISFeatureItem(**f) for f in top_features],
            highlighted_indices=sorted(list(set(highlighted_indices))),
            validation_warnings=validation_warnings,
            export_artifact=ExportArtifact(**export_artifact) if export_artifact else None,
            provider_metadata=ProviderMetadata(
                provider=provider_res.provider,
                model=provider_res.model,
                is_local=provider_res.is_local,
                latency_ms=round(provider_inference_ms, 2),
                prompt_tokens=provider_res.prompt_tokens,
                completion_tokens=provider_res.completion_tokens,
                total_tokens=provider_res.total_tokens,
                routed_via="ai_gateway",
            ),
            latency_breakdown=LatencyBreakdown(
                total_ms=round(total_duration_ms, 2),
                intent_ms=0.0,
                provider_ms=round(provider_inference_ms, 2),
                tool_execution_ms=round(tool_execution_ms, 2),
            ),
            prompt_tokens=provider_res.prompt_tokens,
            completion_tokens=provider_res.completion_tokens,
            total_tokens=provider_res.total_tokens,
        )


# Global copilot service singleton
ai_copilot_service = AICopilotService()
