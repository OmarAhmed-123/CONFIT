from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from .base import TryOnBackendBase


class ReplicateBackend(TryOnBackendBase):
    backend_name = "replicate"

    def probe_sync(self) -> Tuple[bool, Dict[str, Any]]:
        token = (os.getenv("REPLICATE_API_TOKEN") or "").strip()
        if not token:
            return False, {"reason": "FINAL_RENDER_UNAVAILABLE", "message": "Replicate token not configured"}
        return True, {"reason": None}

    async def render(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": False,
            "error_code": "FINAL_RENDER_UNAVAILABLE",
            "message": "Replicate adapter not implemented yet.",
        }

