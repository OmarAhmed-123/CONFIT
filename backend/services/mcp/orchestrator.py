"""
CONFIT Backend — Try-On Orchestrator
======================================
Unified entry point for all virtual try-on requests.

Replaces the fragmented controller logic with a single pipeline:
  validate → detect category → run MCP inference → post-process → respond

The existing services (advanced, HF, local) remain intact as strategy
backends — the orchestrator delegates through the MCP pipeline.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .pipeline import ModelControlPipeline
from .gpu_scheduler import Priority

logger = logging.getLogger(__name__)

# ── Category Detection ──────────────────────────────────────────────────────

_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "dresses": ["dress", "gown", "jumpsuit", "romper", "overall", "onesie", "bodysuit"],
    "outerwear": ["jacket", "coat", "blazer", "cardigan", "hoodie", "parka", "windbreaker", "bomber"],
    "bottoms": ["pants", "trousers", "jeans", "shorts", "skirt", "legging", "jogger", "chino", "cargo", "culottes"],
    "tops": ["shirt", "t-shirt", "tshirt", "top", "blouse", "sweater", "polo", "vest", "tank", "tee"],
    "shoes": ["shoe", "boot", "sneaker", "heel", "loafer", "flat", "sandal"],
    "accessories": ["scarf", "belt", "hat", "sunglasses", "watch", "necklace", "bracelet", "earring", "bag", "purse"],
}


def detect_garment_category(name: str) -> str:
    """Detect garment category from name using keyword matching."""
    lower = name.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return category
    return "tops"  # default


# ── Result DTO ──────────────────────────────────────────────────────────────

@dataclass
class TryOnResult:
    """Unified result from the orchestrator."""
    success: bool
    result_image: Optional[str] = None
    error_message: Optional[str] = None
    failure_kind: Optional[str] = None
    quality_score: float = 0.0
    pose_detected: bool = False
    garment_category: str = "tops"
    processing_time_ms: float = 0.0
    cache_hit: bool = False
    backend_used: str = "local"
    warnings: List[str] = field(default_factory=list)
    validation: Optional[Any] = None
    pose_keypoints_json: Optional[str] = None
    body_dna_pose_reused: bool = False
    fit_preview_json: Optional[str] = None
    body_profile_json: Optional[str] = None
    quality_diagnostics_json: Optional[str] = None


# ── Orchestrator ────────────────────────────────────────────────────────────

class TryOnOrchestrator:
    """Unified try-on entry point.

    Usage:
        orch = TryOnOrchestrator.get_instance()
        result = await orch.process(
            user_image_base64="...",
            garment_image_url="...",
            garment_name="Classic Blazer",
        )
    """

    _instance: Optional["TryOnOrchestrator"] = None

    def __init__(self) -> None:
        self._mcp = ModelControlPipeline.get_instance()

    @classmethod
    def get_instance(cls) -> "TryOnOrchestrator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def process(
        self,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str = "garment",
        options: Optional[Dict[str, Any]] = None,
        priority: Priority = Priority.STANDARD,
        skip_cache: bool = False,
    ) -> TryOnResult:
        """Process a virtual try-on request through the full pipeline.

        Steps:
        1. Validate inputs
        2. Detect garment category
        3. Run inference via MCP pipeline (with caching + routing)
        4. Return unified result
        """
        start = time.time()

        # 1. Basic validation
        if not user_image_base64 or len(user_image_base64) < 100:
            return TryOnResult(success=False, error_message="Invalid user image (too small or empty)")
        if not garment_image_url or not garment_image_url.startswith(("http://", "https://")):
            return TryOnResult(success=False, error_message="Invalid garment image URL")

        # 2. Category: prefer client hint (from catalog), else name keywords
        merged_options = dict(options or {})
        _valid = {"tops", "bottoms", "dresses", "outerwear", "shoes", "accessories", "bags"}
        hint = (merged_options.get("garment_category") or "").strip().lower()
        if hint in _valid:
            category = hint
        else:
            category = detect_garment_category(garment_name)
        merged_options["garment_category"] = category

        # Body DNA reuse requires the classical TryOnService path (advanced/local), not diffusion APIs.
        if merged_options.get("use_stored_body_dna") or merged_options.get("skip_pose_detection"):
            merged_options["force_backend"] = "advanced"

        # 4. Run MCP pipeline
        try:
            mcp_result = await self._mcp.run_inference(
                user_image_base64=user_image_base64,
                garment_image_url=garment_image_url,
                garment_name=garment_name,
                options=merged_options,
                priority=priority,
                skip_cache=skip_cache,
            )
        except Exception as e:
            logger.error("MCP pipeline error: %s", e)
            elapsed = (time.time() - start) * 1000
            return TryOnResult(
                success=False,
                error_message=f"Processing failed: {e}",
                garment_category=category,
                processing_time_ms=round(elapsed, 1),
            )

        elapsed = (time.time() - start) * 1000

        ok = mcp_result.get("success", False)
        err = mcp_result.get("error")
        if not ok and not err:
            err = "Try-on could not produce an acceptable result. Try another photo or garment."

        return TryOnResult(
            success=ok,
            result_image=mcp_result.get("result_image"),
            error_message=err if not ok else None,
            failure_kind=mcp_result.get("failure_kind"),
            quality_score=mcp_result.get("quality_score", 0.0),
            pose_detected=mcp_result.get("pose_detected", False),
            garment_category=category,
            processing_time_ms=round(mcp_result.get("processing_time_ms", elapsed), 1),
            cache_hit=mcp_result.get("cache_hit", False),
            backend_used=mcp_result.get("backend_used", "unknown"),
            warnings=mcp_result.get("warnings", []),
            pose_keypoints_json=mcp_result.get("pose_keypoints_json"),
            body_dna_pose_reused=mcp_result.get("body_dna_pose_reused", False),
            fit_preview_json=mcp_result.get("fit_preview_json"),
            body_profile_json=mcp_result.get("body_profile_json"),
            quality_diagnostics_json=mcp_result.get("quality_diagnostics_json"),
        )

    async def process_live_update(
        self,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str = "garment",
    ) -> TryOnResult:
        """Optimized path for live preview — higher priority, uses cache aggressively."""
        return await self.process(
            user_image_base64=user_image_base64,
            garment_image_url=garment_image_url,
            garment_name=garment_name,
            priority=Priority.LIVE_PREVIEW,
        )

    def stats(self) -> Dict[str, Any]:
        return {"mcp": self._mcp.stats()}
