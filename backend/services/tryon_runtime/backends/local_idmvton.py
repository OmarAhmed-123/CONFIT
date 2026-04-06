from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, Tuple

import torch

from .base import TryOnBackendBase


class LocalIdmVtonBackend(TryOnBackendBase):
    backend_name = "local_idmvton"
    model_name = "IDM-VTON"

    def _weights_path(self) -> Path:
        root = Path((os.getenv("TRYON_LOCAL_MODELS_DIR") or "./models").strip())
        return root / "idm-vton"

    def probe_sync(self) -> Tuple[bool, Dict[str, Any]]:
        if not torch.cuda.is_available():
            return False, {"reason": "GPU_NOT_AVAILABLE", "message": "CUDA GPU not available"}
        path = self._weights_path()
        if not path.exists():
            return False, {"reason": "MODEL_WEIGHTS_MISSING", "message": f"Missing IDM-VTON weights at {path}"}
        return True, {"reason": None, "weights_path": str(path)}

    async def render(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        started = time.time()
        ok, meta = self.probe_sync()
        if not ok:
            return {"success": False, "error_code": meta.get("reason"), "message": meta.get("message")}
        return {
            "success": False,
            "error_code": "FINAL_RENDER_UNAVAILABLE",
            "message": "IDM-VTON runtime adapter is ready but model inference is not wired yet.",
            "backend_name": self.backend_name,
            "model_name": self.model_name,
            "latency_ms": round((time.time() - started) * 1000, 1),
            "device": "cuda",
            "render_kind": "final",
        }

