from __future__ import annotations

import logging
import os
import hashlib
from typing import Any, Dict

from .cache_service import RuntimeCacheService
from .capability_registry import CapabilityRegistry
from .diagnostics_service import DiagnosticsService
from .job_scheduler import TryOnJobScheduler
from .neural_render_pipeline import NeuralRenderPipeline
from .preview_pipeline import PreviewPipeline
from .quality_guard import QualityGuard

logger = logging.getLogger(__name__)


class TryOnRuntimeManager:
    _instance: "TryOnRuntimeManager | None" = None

    def __init__(self) -> None:
        self.capabilities = CapabilityRegistry()
        self.diagnostics = DiagnosticsService()
        self.cache = RuntimeCacheService()
        self._preview: PreviewPipeline | None = None
        self._neural: NeuralRenderPipeline | None = None
        self._quality_guard = QualityGuard()
        self.jobs = TryOnJobScheduler()
        # Warm preview pipeline early so first user request does not pay model init cost.
        eager_preview = str(os.getenv("TRYON_PREVIEW_PREWARM", "1")).strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if eager_preview:
            try:
                _ = self.preview
            except Exception as ex:
                logger.warning("Preview prewarm skipped: %s", ex)

    @property
    def preview(self) -> PreviewPipeline:
        if self._preview is None:
            self._preview = PreviewPipeline()
        return self._preview

    @property
    def neural(self) -> NeuralRenderPipeline:
        if self._neural is None:
            self._neural = NeuralRenderPipeline()
        return self._neural

    @classmethod
    def get_instance(cls) -> "TryOnRuntimeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_capabilities(self) -> Dict[str, Any]:
        return self.capabilities.snapshot().to_dict()

    def get_diagnostics(self) -> Dict[str, Any]:
        return self.diagnostics.snapshot()

    async def generate_preview(
        self,
        *,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str,
        garment_category: str | None,
    ) -> Dict[str, Any]:
        key = self.cache.make_key(
            user_image_b64=user_image_base64,
            garment_image_url=garment_image_url,
            garment_name=garment_name,
            mode="preview",
        )
        cached = self.cache.get(key)
        if cached:
            out = dict(cached)
            out["cache_hit"] = True
            return out

        result = await self.preview.generate_preview(
            user_image_base64=user_image_base64,
            garment_image_url=garment_image_url,
            garment_name=garment_name,
            garment_category=garment_category,
        )
        if result.get("success"):
            self.cache.set(key, result, ttl_sec=180)
        result["cache_hit"] = False
        return result

    def _render_cache_key(self, *, user_image_base64: str, garment_image_url: str, garment_name: str, garment_category: str | None) -> str:
        src = "|".join(
            [
                hashlib.sha256(user_image_base64.encode("utf-8")).hexdigest(),
                hashlib.sha256(garment_image_url.encode("utf-8")).hexdigest(),
                garment_name,
                garment_category or "",
            ]
        )
        return "final:" + hashlib.sha256(src.encode("utf-8")).hexdigest()

    def enqueue_final_render(
        self,
        *,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str,
        garment_category: str | None,
    ) -> Dict[str, Any]:
        caps = self.capabilities.snapshot()
        if not caps.final_render_available:
            return {
                "success": False,
                "error_code": "FINAL_RENDER_UNAVAILABLE",
                "message": "High-fidelity final render requires a healthy GPU backend.",
                "details": caps.to_dict(),
            }

        backend_order = [b for b in caps.backend_priority if b != "preview_only"]
        cache_key = self._render_cache_key(
            user_image_base64=user_image_base64,
            garment_image_url=garment_image_url,
            garment_name=garment_name,
            garment_category=garment_category,
        )
        cached = self.cache.get(cache_key)
        if cached and cached.get("image_url"):
            job = self.jobs.create_job({"cache_hit": True, "backend_order": backend_order})
            job.status = "completed"
            job.result_image = cached.get("image_url")
            job.backend_name = cached.get("backend_name")
            job.quality_score = cached.get("quality_score")
            job.alignment_diagnostics_json = cached.get("alignment_diagnostics_json")
            return {"success": True, "render_kind": "final", "job_id": job.id, "status": job.status}

        job = self.jobs.create_job(
            {
                "garment_name": garment_name,
                "backend_order": backend_order,
                "cache_key": cache_key,
            }
        )
        self.jobs.run_background(
            job.id,
            self._render_job(
                backends=backend_order,
                user_image_base64=user_image_base64,
                garment_image_url=garment_image_url,
                garment_name=garment_name,
                garment_category=garment_category,
                cache_key=cache_key,
            ),
        )
        logger.info(
            "tryon_final_job_enqueued job_id=%s backend=%s",
            job.id,
            caps.active_backend,
        )
        return {
            "success": True,
            "render_kind": "final",
            "job_id": job.id,
            "status": job.status,
        }

    async def _render_job(
        self,
        *,
        backends: list[str],
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str,
        garment_category: str | None,
        cache_key: str,
    ) -> Dict[str, Any]:
        result = await self.neural.render_with_fallback(
            backends=backends,
            user_image_base64=user_image_base64,
            garment_image_url=garment_image_url,
            garment_name=garment_name,
            garment_category=garment_category,
        )
        if not result.get("success"):
            return result
        image = result.get("image_url") or result.get("result_image")
        if not image:
            return {"success": False, "error_code": "FINAL_RENDER_UNAVAILABLE", "message": "Backend did not return image"}

        guard_ok, guard_meta = self._quality_guard.evaluate(
            user_image_base64=user_image_base64,
            garment_image_base64=None,
            result_image_base64=image,
        )
        if not guard_ok:
            return {
                "success": False,
                "error_code": "QUALITY_REJECTED",
                "failure_kind": guard_meta.get("failure_kind", "QUALITY_REJECTED"),
                "message": guard_meta.get("message", "Output rejected by quality guard"),
            }
        out = {
            "success": True,
            "render_kind": "final",
            "backend_name": result.get("backend_name"),
            "image_url": image,
            "quality_score": guard_meta.get("quality_score", result.get("quality_score", 0.0)),
            "alignment_diagnostics_json": result.get("alignment_diagnostics_json"),
        }
        self.cache.set(cache_key, out, ttl_sec=max(60, int(os.getenv("TRYON_FINAL_CACHE_TTL_SEC", "3600"))))
        return out

