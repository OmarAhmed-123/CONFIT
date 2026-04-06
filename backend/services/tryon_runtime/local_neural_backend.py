from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, Tuple

import torch


class LocalNeuralBackend:
    """
    Local neural backend skeleton for CatVTON/IDM-VTON.
    - Lazy model init
    - Health state
    - Batching hook (single-flight lock + batch config placeholders)
    """

    def __init__(self) -> None:
        self.model_path = (os.getenv("TRYON_LOCAL_MODEL_PATH") or "").strip()
        self.model_type = (os.getenv("TRYON_LOCAL_MODEL_TYPE") or "catvton").strip().lower()
        self.batch_size = max(1, int(os.getenv("TRYON_LOCAL_BATCH_SIZE", "1")))
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._init_lock = asyncio.Lock()
        self._initialized = False
        self._init_error: str | None = None
        self._model: Any = None

    def probe_sync(self) -> Tuple[bool, str]:
        if self.device != "cuda":
            return False, "CUDA unavailable"
        if not self.model_path:
            return False, "TRYON_LOCAL_MODEL_PATH is not configured"
        if not Path(self.model_path).exists():
            return False, f"Model path not found: {self.model_path}"
        if self.model_type not in ("catvton", "idm-vton", "idmvton"):
            return False, f"Unsupported TRYON_LOCAL_MODEL_TYPE: {self.model_type}"
        return True, "configured"

    async def _lazy_init(self) -> Tuple[bool, str]:
        if self._initialized:
            return True, "ready"
        async with self._init_lock:
            if self._initialized:
                return True, "ready"
            ok, msg = self.probe_sync()
            if not ok:
                self._init_error = msg
                return False, msg
            # Skeleton: reserve place for real loader.
            # Replace with actual CatVTON/IDM-VTON pipeline loader.
            self._model = {
                "model_type": self.model_type,
                "model_path": self.model_path,
                "device": self.device,
                "batch_size": self.batch_size,
            }
            self._initialized = True
            self._init_error = None
            return True, "ready"

    async def render(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        ok, msg = await self._lazy_init()
        if not ok:
            return {
                "success": False,
                "error_code": "LOCAL_NEURAL_UNAVAILABLE",
                "message": msg,
            }

        # Skeleton behavior: no fake final image.
        return {
            "success": False,
            "error_code": "LOCAL_NEURAL_NOT_IMPLEMENTED",
            "message": (
                "Local neural backend is configured and initialized, "
                "but inference implementation is not wired yet."
            ),
        }

