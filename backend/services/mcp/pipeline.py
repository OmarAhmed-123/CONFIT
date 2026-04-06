"""
CONFIT Backend — Model Control Pipeline
=========================================
Central coordination layer between API requests and AI model inference.

Ties together: ModelRouter, TryOnCache, GPUScheduler.
Single entry point for all try-on inference operations.
"""

import logging
import os
from typing import Any, Dict, Optional

from .model_router import ModelRouter, ModelBackend
from .cache_layer import TryOnCache
from .gpu_scheduler import GPUScheduler, Priority

logger = logging.getLogger(__name__)

HF_QUOTA_PATTERNS = (
    "zerogpu quota",
    "running out of daily zerogpu quotas",
    "quota",
)


class ModelControlPipeline:
    """Central pipeline coordinating model routing, caching, and GPU scheduling.

    Usage:
        mcp = ModelControlPipeline.get_instance()
        await mcp.initialize()

        result = await mcp.run_inference(
            user_image_base64="...",
            garment_image_url="...",
            garment_name="Classic T-Shirt",
        )
    """

    _instance: Optional["ModelControlPipeline"] = None

    def __init__(self) -> None:
        self.router = ModelRouter()
        self.cache = TryOnCache()
        self.scheduler = GPUScheduler()
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "ModelControlPipeline":
        """Singleton access."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def initialize(self) -> None:
        """Initialize pipeline components (call once at startup)."""
        if self._initialized:
            return
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            await self.cache.connect(redis_url)
        else:
            logger.info("Redis cache disabled (REDIS_URL not set); using in-memory fallback")
        self._initialized = True
        logger.info(
            "ModelControlPipeline initialized (device=%s, backends=%s)",
            self.scheduler.device,
            self.router.available_backends(),
        )

    async def run_inference(
        self,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str = "garment",
        options: Optional[Dict[str, Any]] = None,
        priority: Priority = Priority.STANDARD,
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """Run full try-on inference through the pipeline.

        Steps:
        1. Check cache
        2. Select model backend via router
        3. Schedule inference via GPU scheduler
        4. Cache result
        5. Return result

        Returns:
            Dict with keys: success, result_image, quality_score,
            pose_detected, garment_category, processing_time_ms,
            cache_hit, backend_used
        """
        if not self._initialized:
            await self.initialize()

        # Build cache key
        img_hash = TryOnCache.hash_image(user_image_base64)
        opts_hash = TryOnCache.hash_options(options)
        cache_key = TryOnCache.make_result_key(img_hash, garment_name, opts_hash)

        # 1. Check cache
        if not skip_cache:
            cached = await self.cache.get_result(cache_key)
            if cached:
                logger.info("Cache HIT for %s", cache_key[:16])
                return {
                    "success": True,
                    "result_image": cached,
                    "cache_hit": True,
                    "backend_used": "cache",
                    "quality_score": 0.7,
                    "pose_detected": False,
                    "garment_category": "tops",
                    "processing_time_ms": 0,
                }

        # 2. Select backend
        opts = options or {}
        # Runtime refresh so env/key updates are picked up without restart.
        self.router.refresh()
        quality = opts.get("quality", "auto")
        force_backend = opts.get("force_backend")
        backend = self.router.select(quality=quality, force_backend=force_backend)
        logger.info("Using backend: %s for garment '%s'", backend.value, garment_name)

        # 3. Schedule and run inference
        import time
        start = time.time()

        try:
            result = await self.scheduler.submit(
                job_id=f"tryon_{img_hash}_{int(start)}",
                func=self._execute_backend,
                args=(backend.value, user_image_base64, garment_image_url, garment_name, options),
                priority=priority,
            )
        except Exception as e:
            # On failure, try next backend depending on failure policy.
            err_msg = str(e or "")
            logger.warning("Backend %s failed: %s, trying fallback", backend.value, err_msg)

            # Quota failures on HF are transient/account-related, not module health.
            # Do not globally mark HF unavailable, or all next requests degrade to classical.
            is_hf_quota = (
                backend == ModelBackend.HUGGINGFACE
                and any(p in err_msg.lower() for p in HF_QUOTA_PATTERNS)
            )
            if not is_hf_quota:
                self.router.mark_unavailable(backend)

            # Professional safety policy:
            # by default we do NOT silently downgrade to classical compositing when
            # neural VTON is unavailable. Return a structured failure instead.
            allow_classical_fallback = str(
                opts.get("allow_classical_fallback", os.getenv("TRYON_ALLOW_CLASSICAL_FALLBACK", "0"))
            ).strip().lower() in ("1", "true", "yes")

            fallback = self.router.select(quality=quality, force_backend=None)
            if fallback == backend:
                # No fallback available
                if is_hf_quota:
                    return {
                        "success": False,
                        "result_image": None,
                        "error": (
                            "IDM-VTON quota is exhausted on HuggingFace right now. "
                            "Configure FASHN_API_KEY for production-grade neural try-on, "
                            "or retry later when HF quota resets."
                        ),
                        "failure_kind": "neural_quota_exhausted",
                        "cache_hit": False,
                        "backend_used": backend.value,
                        "quality_score": 0,
                        "pose_detected": False,
                        "garment_category": (opts.get("garment_category") or "tops"),
                        "processing_time_ms": (time.time() - start) * 1000,
                        "warnings": ["huggingface_quota_exhausted"],
                    }
                return {
                    "success": False,
                    "result_image": None,
                    "error": err_msg,
                    "cache_hit": False,
                    "backend_used": backend.value,
                    "quality_score": 0,
                    "pose_detected": False,
                    "garment_category": "tops",
                    "processing_time_ms": (time.time() - start) * 1000,
                }

            # If fallback is classical while classical fallback is disabled, fail safely.
            if (fallback in (ModelBackend.ADVANCED, ModelBackend.LOCAL)) and not allow_classical_fallback:
                return {
                    "success": False,
                    "result_image": None,
                    "error": (
                        "Neural try-on backend is unavailable right now "
                        f"({backend.value} failed: {err_msg}). "
                        "Classical fallback is disabled to avoid unrealistic composited output. "
                        "Please configure FASHN_API_KEY or retry later."
                    ),
                    "failure_kind": "neural_backend_unavailable",
                    "cache_hit": False,
                    "backend_used": backend.value,
                    "quality_score": 0,
                    "pose_detected": False,
                    "garment_category": (opts.get("garment_category") or "tops"),
                    "processing_time_ms": (time.time() - start) * 1000,
                    "warnings": ["classical_fallback_blocked_for_quality"],
                }

            result = await self.scheduler.submit(
                job_id=f"tryon_fallback_{img_hash}_{int(start)}",
                func=self._execute_backend,
                args=(fallback.value, user_image_base64, garment_image_url, garment_name, options),
                priority=priority,
            )

        elapsed_ms = (time.time() - start) * 1000

        # Quality-based backend fallback:
        # The classical "advanced" pipeline can sometimes return visually degraded
        # results (e.g., sparkle artifacts) while still passing the internal min-output bar.
        # If that happens, retry on HuggingFace when available.
        try:
            min_quality_for_fallback = float(os.getenv("TRYON_FALLBACK_MIN_QUALITY", "0.75"))
            backend_used = result.get("backend_used")
            if (
                isinstance(backend_used, str)
                and backend_used == "advanced"
                and result.get("success")
                and float(result.get("quality_score", 0.0) or 0.0) < min_quality_for_fallback
            ):
                if self.router.is_available(ModelBackend.HUGGINGFACE):
                    logger.warning(
                        "Quality fallback: advanced quality %.3f < %.3f; retrying on HuggingFace",
                        float(result.get("quality_score", 0.0) or 0.0),
                        min_quality_for_fallback,
                    )
                    fallback = ModelBackend.HUGGINGFACE
                    start2 = time.time()
                    result2 = await self.scheduler.submit(
                        job_id=f"tryon_hf_fallback_{img_hash}_{int(start2)}",
                        func=self._execute_backend,
                        args=(fallback.value, user_image_base64, garment_image_url, garment_name, options),
                        priority=priority,
                    )
                    if result2.get("success") and result2.get("result_image"):
                        result = result2
        except Exception as e:
            logger.warning("Fallback retry failed: %s", e)

        # 4. Cache result
        if result.get("success") and result.get("result_image"):
            await self.cache.set_result(cache_key, result["result_image"])

        result["cache_hit"] = False
        result["processing_time_ms"] = round(elapsed_ms, 1)
        return result

    async def _execute_backend(
        self,
        backend: str,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str,
        options: Optional[Dict],
    ) -> Dict[str, Any]:
        """Execute try-on on the specified backend."""
        # Normalize incoming backend string to ModelBackend enum for robust comparison
        try:
            backend_enum = ModelBackend(backend)
        except ValueError:
            logger.warning("Unknown backend '%s', falling back to LOCAL", backend)
            backend_enum = ModelBackend.LOCAL

        if backend_enum is ModelBackend.FASHN:
            return await self._run_fashn(
                user_image_base64, garment_image_url, garment_name, options
            )
        if backend_enum is ModelBackend.GATEWAY:
            return await self._run_gateway(user_image_base64, garment_image_url, garment_name, options)
        if backend_enum is ModelBackend.ADVANCED:
            return await self._run_advanced(user_image_base64, garment_image_url, garment_name, options)
        if backend_enum is ModelBackend.HUGGINGFACE:
            return await self._run_huggingface(user_image_base64, garment_image_url, garment_name)

        return await self._run_local(
            user_image_base64, garment_image_url, garment_name, options
        )

    async def _run_fashn(
        self,
        user_b64: str,
        garment_url: str,
        name: str,
        options: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """FASHN tryon-v1.6 — dedicated virtual try-on API (see docs.fashn.ai)."""
        from services.tryon.fashn_tryon_service import FashnTryOnService

        svc = FashnTryOnService()
        gc = (options or {}).get("garment_category")
        mode = (options or {}).get("fashn_mode", "balanced")
        gpt = (options or {}).get("garment_photo_type", "auto")
        raw = await svc.process_tryon(
            user_image_base64=user_b64,
            garment_image_url=garment_url,
            garment_category=gc,
            mode=str(mode),
            garment_photo_type=str(gpt),
        )
        if not raw.get("success"):
            # Trigger pipeline fallback (FASHN → IDM-VTON/HF → local)
            raise RuntimeError(raw.get("error") or "FASHN try-on failed")
        return {
            "success": True,
            "result_image": raw.get("result_image"),
            "quality_score": 0.9,
            "pose_detected": True,
            "garment_category": (options or {}).get("garment_category") or "tops",
            "backend_used": "fashn",
            "warnings": [],
        }

    async def _run_gateway(
        self,
        user_b64: str,
        garment_url: str,
        name: str,
        options: Optional[Dict],
    ) -> Dict[str, Any]:
        """High-quality diffusion try-on via external AI gateway."""
        from services.ai_services.tryon_gateway_service import TryOnGatewayService

        service = TryOnGatewayService()
        # Options allow fine-tuning prompt behavior (e.g., disable_collage_retry)
        strict_single_image = (options or {}).get("strict_single_image", True)
        result = await service.process_tryon(
            user_image_base64=user_b64,
            garment_image_url=garment_url,
            garment_name=name,
            garment_category=(options or {}).get("garment_category"),
            skin_undertone=(options or {}).get("skin_undertone", "natural"),
            strict_single_image=strict_single_image,
        )
        return {
            "success": result.get("success", False),
            "result_image": result.get("result_image"),
            "quality_score": result.get("quality_score", 0.85),
            "pose_detected": result.get("pose_detected", False),
            "garment_category": result.get("garment_category", "tops"),
            "backend_used": "gateway",
            "warnings": result.get("warnings", []),
            "error": result.get("error"),
        }

    async def _run_advanced(self, user_b64: str, garment_url: str, name: str, options: Optional[Dict]) -> Dict:
        from services.tryon.tryon_service import TryOnService

        r = await TryOnService().process_classical(user_b64, garment_url, name, options or {})
        return {
            "success": r.success,
            "result_image": r.result_image,
            "quality_score": r.quality_score,
            "pose_detected": r.pose_detected,
            "garment_category": r.garment_category,
            "backend_used": "advanced",
            "warnings": r.warnings or [],
            "error": r.error_message,
            "failure_kind": getattr(r, "failure_kind", None),
            "pose_keypoints_json": getattr(r, "pose_keypoints_json", None),
            "body_dna_pose_reused": getattr(r, "body_dna_pose_reused", False),
            "fit_preview_json": getattr(r, "fit_preview_json", None),
            "body_profile_json": getattr(r, "body_profile_json", None),
            "quality_diagnostics_json": getattr(r, "quality_diagnostics_json", None),
        }

    async def _run_huggingface(self, user_b64: str, garment_url: str, name: str) -> Dict:
        from services.tryon_service import VirtualTryOnService
        service = VirtualTryOnService(hf_token=os.getenv("HF_TOKEN"))
        detailed = await service.process_tryon_detailed(user_b64, garment_url, name)
        return {
            "success": True,
            "result_image": detailed.get("result_image"),
            "quality_score": float(detailed.get("quality_score") or 0.75),
            "pose_detected": True,
            "garment_category": "tops",
            "backend_used": "huggingface",
            "warnings": list(detailed.get("warnings") or []),
            "quality_diagnostics_json": detailed.get("validation"),
        }

    async def _run_local(
        self,
        user_b64: str,
        garment_url: str,
        name: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        from services.tryon.tryon_service import TryOnService

        r = await TryOnService().process_classical(user_b64, garment_url, name, options or {})
        warns = list(r.warnings or [])
        warns.append(
            "Local classical pipeline (set FASHN_API_KEY / HF_TOKEN for neural try-on)"
        )
        return {
            "success": r.success,
            "result_image": r.result_image,
            "quality_score": r.quality_score,
            "pose_detected": r.pose_detected,
            "garment_category": r.garment_category or (options or {}).get("garment_category") or "tops",
            "backend_used": "local",
            "warnings": warns,
            "error": r.error_message,
            "failure_kind": getattr(r, "failure_kind", None),
            "pose_keypoints_json": getattr(r, "pose_keypoints_json", None),
            "body_dna_pose_reused": getattr(r, "body_dna_pose_reused", False),
            "fit_preview_json": getattr(r, "fit_preview_json", None),
            "body_profile_json": getattr(r, "body_profile_json", None),
            "quality_diagnostics_json": getattr(r, "quality_diagnostics_json", None),
        }

    # ── Health & Stats ──────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "router": self.router.stats(),
            "cache": self.cache.stats(),
            "scheduler": self.scheduler.stats(),
        }
