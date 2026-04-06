from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from .base import TryOnBackendBase


class FashnBackend(TryOnBackendBase):
    backend_name = "fashn"

    def probe_sync(self) -> Tuple[bool, Dict[str, Any]]:
        key = (os.getenv("FASHN_API_KEY") or "").strip()
        if not key:
            return False, {"reason": "FINAL_RENDER_UNAVAILABLE", "message": "FASHN_API_KEY not configured"}
        return True, {"reason": None}

    async def render(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": False,
            "error_code": "FINAL_RENDER_UNAVAILABLE",
            "message": "FASHN adapter is optional and not enabled in runtime manager.",
        }

