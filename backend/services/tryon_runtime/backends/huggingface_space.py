from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from .base import TryOnBackendBase


class HuggingFaceSpaceBackend(TryOnBackendBase):
    backend_name = "huggingface_space"

    def probe_sync(self) -> Tuple[bool, Dict[str, Any]]:
        enable = (os.getenv("TRYON_ENABLE_HF_SPACE_BACKEND") or "").strip().lower() in ("1", "true", "yes")
        if not enable:
            return False, {"reason": "FINAL_RENDER_UNAVAILABLE", "message": "HF Space backend disabled by policy"}
        return True, {"reason": None}

    async def render(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": False,
            "error_code": "QUOTA_EXHAUSTED",
            "message": "HuggingFace Space is best-effort only and currently unavailable.",
        }

