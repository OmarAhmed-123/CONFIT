from __future__ import annotations

import os
from typing import Any, Dict

from services.tryon_runtime.backends.fashn_backend import FashnBackend
from services.tryon_runtime.backends.huggingface_space import HuggingFaceSpaceBackend
from services.tryon_runtime.backends.local_catvton import LocalCatVtonBackend
from services.tryon_runtime.backends.local_idmvton import LocalIdmVtonBackend
from services.tryon_runtime.backends.remote_gpu import RemoteGPUBackend
from services.tryon_runtime.backends.replicate_backend import ReplicateBackend


class NeuralRenderPipeline:
    def __init__(self) -> None:
        self._catvton = LocalCatVtonBackend()
        self._idmvton = LocalIdmVtonBackend()
        self._remote = RemoteGPUBackend()
        self._replicate = ReplicateBackend()
        self._fashn = FashnBackend()
        self._hf_space = HuggingFaceSpaceBackend()

    """
    High-quality render entry.
    - local_neural path can be implemented against local CatVTON/IDM-VTON loader.
    - remote_neural path uses TRYON_REMOTE_URL when configured.
    """

    async def render(
        self,
        *,
        backend: str,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str,
        garment_category: str | None,
    ) -> Dict[str, Any]:
        return await self.render_with_fallback(
            backends=[backend],
            user_image_base64=user_image_base64,
            garment_image_url=garment_image_url,
            garment_name=garment_name,
            garment_category=garment_category,
        )

    async def render_with_fallback(
        self,
        *,
        backends: list[str],
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str,
        garment_category: str | None,
    ) -> Dict[str, Any]:
        warnings: list[str] = []
        for b in backends:
            payload = {
                "userImageBase64": user_image_base64,
                "garmentImageUrl": garment_image_url,
                "garmentName": garment_name,
                "garmentCategory": garment_category,
            }
            adapters = {
                "local_catvton": self._catvton,
                "local_idmvton": self._idmvton,
                "remote_gpu": self._remote,
                "replicate": self._replicate,
                "fashn": self._fashn,
                "huggingface_space": self._hf_space,
            }
            adapter = adapters.get(b)
            if not adapter:
                out = {"success": False, "error_code": "FINAL_RENDER_UNAVAILABLE", "message": f"Unknown backend: {b}"}
            else:
                out = await adapter.render(payload)

            if out.get("success"):
                if warnings:
                    out["warnings"] = list(out.get("warnings", [])) + warnings
                return out
            warnings.append(f"{b}_failed:{out.get('error_code') or 'unknown'}")

        return {
            "success": False,
            "error_code": "FINAL_RENDER_UNAVAILABLE",
            "message": "All final render backends failed or are unavailable.",
            "warnings": warnings,
        }

