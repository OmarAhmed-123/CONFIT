from __future__ import annotations

import time
from typing import Any, Dict

from services.tryon.alignment_config import merge_alignment_identity, preview_classical_options
from services.tryon.tryon_service import TryOnService


class PreviewPipeline:
    """Fast local preview path; CPU-safe and explicitly non-final."""

    def __init__(self) -> None:
        self._svc = TryOnService()

    async def generate_preview(
        self,
        *,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str,
        garment_category: str | None,
    ) -> Dict[str, Any]:
        t0 = time.time()
        attempts = [
            {
                "fit_type": "regular",
                "quality_threshold": 0.50,
                "min_output_quality": 0.45,
                "allow_low_quality_output": True,
                "fabric_physics_enabled": False,
                "fabric_intelligence": False,
                "fabric_low_power": True,
                "return_validation_details": False,
                "preview_mode": True,
                "disable_input_preprocess": True,
            },
            # Fallback 2: allow looser fit and skip heavy preprocess.
            {
                "fit_type": "loose",
                "quality_threshold": 0.42,
                "min_output_quality": 0.35,
                "allow_low_quality_output": True,
                "fabric_physics_enabled": False,
                "fabric_intelligence": False,
                "fabric_low_power": True,
                "return_validation_details": False,
                "preview_mode": True,
                "disable_input_preprocess": True,
            },
            # Fallback 3: emergency preview with minimal constraints.
            {
                "fit_type": "loose",
                "quality_threshold": 0.35,
                "min_output_quality": 0.25,
                "allow_low_quality_output": True,
                "fabric_physics_enabled": False,
                "fabric_intelligence": False,
                "fabric_low_power": True,
                "return_validation_details": False,
                "preview_mode": True,
                "disable_input_preprocess": True,
                "skip_pose_detection": False,
            },
        ]
        result = None
        preview_warnings: list[str] = []
        base_preview = merge_alignment_identity(preview_classical_options())
        for idx, opts in enumerate(attempts, start=1):
            merged = {**base_preview, **opts}
            merged["garment_category"] = garment_category
            result = await self._svc.process_classical(
                user_image_base64=user_image_base64,
                garment_image_url=garment_image_url,
                garment_name=garment_name,
                options=merged,
            )
            if result.success and result.result_image:
                if idx > 1:
                    preview_warnings.append(f"preview_fallback_attempt_{idx}")
                break
            preview_warnings.append(
                f"preview_attempt_{idx}_failed:{(result.error_message or 'unknown_error')}"
            )
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        return {
            "success": bool(result and result.success and result.result_image),
            "render_kind": "preview",
            "backend_name": "preview_local",
            "result_image": (result.result_image if result else None),
            "timing_ms": elapsed_ms,
            "warnings": list((result.warnings if result else []) or []) + preview_warnings,
            "error_message": (result.error_message if result else "Preview pipeline failed"),
            "failure_kind": getattr(result, "failure_kind", None) if result else "preview_failed",
            "alignment_diagnostics_json": getattr(result, "alignment_diagnostics_json", None) if result else None,
        }

