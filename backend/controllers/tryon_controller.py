"""
CONFIT Backend — Try-On Controller
====================================
Orchestrates virtual try-on requests by validating input,
delegating to the MCP Orchestrator, and formatting responses.

Uses the Model Control Pipeline (MCP) for model routing,
caching, and GPU scheduling — replaces direct service calls.
"""

import logging
import os
import json
from typing import Optional, Dict, Any

from models.tryon_models import (
    TryOnRequest,
    TryOnResponse,
    TryOnOptions,
    QualityMetrics,
)
from utils.image_utils import validate_base64_image

logger = logging.getLogger(__name__)


class TryOnController:
    """Controller for the virtual try-on feature.

    Delegates all inference to the MCP TryOnOrchestrator,
    which handles model routing, caching, and fallback chains.
    """

    _instance: Optional["TryOnController"] = None

    def __init__(self) -> None:
        self._hf_token = os.getenv("HF_TOKEN")
        self._orchestrator = None  # Lazy init to avoid import cycles
        logger.info("TryOnController initialized")

    @classmethod
    def get_instance(cls) -> "TryOnController":
        """Return a singleton controller instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_orchestrator(self):
        """Lazy-load orchestrator to avoid circular imports at module load."""
        if self._orchestrator is None:
            from services.mcp.orchestrator import TryOnOrchestrator
            self._orchestrator = TryOnOrchestrator.get_instance()
        return self._orchestrator

    async def process(self, request: TryOnRequest) -> TryOnResponse:
        """Validate the incoming request and run try-on via MCP.

        The MCP pipeline handles:
        1. Cache check → return cached result if available
        2. Model selection → advanced AI / HuggingFace / local
        3. GPU scheduling → priority queue with memory management
        4. Fallback chain → automatic retry with next backend
        """
        # Validate base64 image
        is_valid, validation_msg = validate_base64_image(request.userImageBase64)
        if not is_valid:
            raise ValueError(validation_msg)

        logger.info("Processing try-on request for garment: %s", request.garmentName)

        # Build options
        options = self._build_options(request.options)
        if getattr(request, "garmentCategory", None):
            options["garment_category"] = request.garmentCategory

        # Delegate to orchestrator
        orchestrator = self._get_orchestrator()
        result = await orchestrator.process(
            user_image_base64=request.userImageBase64,
            garment_image_url=request.garmentImageUrl,
            garment_name=request.garmentName,
            options=options,
        )

        # Format response
        return self._build_response(result)

    async def process_live_update(
        self,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str = "garment",
    ) -> TryOnResponse:
        """Optimized path for live preview — higher priority."""
        orchestrator = self._get_orchestrator()
        result = await orchestrator.process_live_update(
            user_image_base64=user_image_base64,
            garment_image_url=garment_image_url,
            garment_name=garment_name,
        )
        return self._build_response(result)

    def _build_options(self, request_options: Optional[TryOnOptions]) -> Dict[str, Any]:
        """Build options dict from request options."""
        if request_options is None:
            return {
                "fit_type": "regular",
                "quality_threshold": 0.65,
                "validate": True,
                "return_validation_details": False,
                "fabric_physics_enabled": True,
                "fabric_low_power": False,
                # Cache-busting: bump this whenever the try-on pipeline changes.
                "pipeline_version": os.getenv(
                    "TRYON_PIPELINE_VERSION",
                    "2026-03-23-idm-vton-mask-identity-v2",
                ),
            }
        out: Dict[str, Any] = {
            "fit_type": request_options.fitType,
            "quality_threshold": request_options.qualityThreshold,
            "validate": request_options.enableValidation,
            "return_validation_details": request_options.returnValidationDetails,
            "fabric_physics_enabled": request_options.fabricPhysicsEnabled,
            "fabric_low_power": request_options.fabricLowPower,
            "pipeline_version": os.getenv(
                "TRYON_PIPELINE_VERSION",
                "2026-03-23-idm-vton-mask-identity-v2",
            ),
        }
        if request_options.userId:
            out["user_id"] = request_options.userId
        out["learn_body_dna"] = request_options.learnBodyDna
        out["use_stored_body_dna"] = request_options.useStoredBodyDna
        out["skip_pose_detection"] = request_options.skipPoseDetection
        if request_options.bodyProfileJson:
            out["body_profile"] = request_options.bodyProfileJson
        if request_options.garmentColorHex:
            out["garment_color_hex"] = request_options.garmentColorHex
        out["force_refresh_body_dna"] = request_options.forceRefreshBodyDna
        out["no_persist_body_dna"] = request_options.noPersistBodyDna
        if request_options.minOutputQuality is not None:
            out["min_output_quality"] = request_options.minOutputQuality
        out["allow_low_quality_output"] = request_options.allowLowQualityOutput
        return out

    def _build_response(self, result) -> TryOnResponse:
        """Build TryOnResponse from orchestrator TryOnResult."""
        diagnostics_obj = None
        qd = getattr(result, "quality_diagnostics_json", None)
        if isinstance(qd, str) and qd.strip():
            try:
                diagnostics_obj = json.loads(qd)
            except Exception:
                diagnostics_obj = None

        quality_metrics = None
        if hasattr(result, "validation") and result.validation is not None:
            quality_metrics = QualityMetrics(
                overallScore=result.validation.overall_score,
                realismScore=result.validation.realism_score,
                edgeQualityScore=result.validation.edge_quality_score,
                colorConsistencyScore=result.validation.color_consistency_score,
                proportionScore=result.validation.proportion_score,
                artifactScore=result.validation.artifact_score,
                issues=result.validation.issues,
                suggestions=result.validation.suggestions,
            )

        backend_msg = f" (via {result.backend_used})" if hasattr(result, "backend_used") else ""
        cache_note = " [cached]" if getattr(result, "cache_hit", False) else ""

        return TryOnResponse(
            success=result.success,
            resultImage=result.result_image,
            message=(
                f"Virtual try-on completed{backend_msg}{cache_note}!"
                if result.success
                else (result.error_message or "Processing failed")
            ),
            error=result.error_message if not result.success else None,
            failureKind=getattr(result, "failure_kind", None),
            qualityScore=result.quality_score,
            poseDetected=result.pose_detected,
            garmentCategory=result.garment_category,
            processingTimeMs=result.processing_time_ms,
            warnings=result.warnings or [],
            qualityMetrics=quality_metrics,
            poseKeypointsJson=getattr(result, "pose_keypoints_json", None),
            bodyDnaPoseReused=getattr(result, "body_dna_pose_reused", False),
            fitPreviewJson=getattr(result, "fit_preview_json", None),
            bodyProfileJson=getattr(result, "body_profile_json", None),
            qualityDiagnosticsJson=getattr(result, "quality_diagnostics_json", None),
            qualityDiagnostics=diagnostics_obj,
        )

    @staticmethod
    def health() -> dict:
        """Return service health status including MCP stats."""
        try:
            from services.mcp.pipeline import ModelControlPipeline
            mcp = ModelControlPipeline.get_instance()
            return {
                "status": "ok",
                "service": "virtual-try-on",
                "mcp": mcp.stats(),
            }
        except Exception as e:
            return {"status": "degraded", "service": "virtual-try-on", "error": str(e)}
