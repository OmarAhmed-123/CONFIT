from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Tuple

import torch

from services.tryon_runtime.backends.huggingface_space import HuggingFaceSpaceBackend
from services.tryon_runtime.backends.local_catvton import LocalCatVtonBackend
from services.tryon_runtime.backends.local_idmvton import LocalIdmVtonBackend
from services.tryon_runtime.backends.remote_gpu import RemoteGPUBackend
from services.tryon_runtime.backends.replicate_backend import ReplicateBackend
from services.tryon_runtime.backends.fashn_backend import FashnBackend

DEFAULT_BACKEND_PRIORITY: List[str] = [
    "local_catvton",
    "local_idmvton",
    "remote_gpu",
    "replicate",
    "fashn",
    "huggingface_space",
    "preview_only",
]


@dataclass(frozen=True)
class TryOnCapabilities:
    preview_available: bool
    final_render_available: bool
    active_backend: str
    backend_priority: List[str]
    failure_reason: str | None
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CapabilityRegistry:
    """Authoritative capability source for preview/final routing decisions."""

    def __init__(self) -> None:
        self._catvton = LocalCatVtonBackend()
        self._idmvton = LocalIdmVtonBackend()
        self._remote = RemoteGPUBackend()
        self._replicate = ReplicateBackend()
        self._fashn = FashnBackend()
        self._hf_space = HuggingFaceSpaceBackend()

    @staticmethod
    def _resolve_priority() -> List[str]:
        raw = (os.getenv("TRYON_BACKEND_PRIORITY") or "").strip()
        if not raw:
            return list(DEFAULT_BACKEND_PRIORITY)
        parsed = [p.strip() for p in raw.split(",") if p.strip()]
        out: List[str] = []
        for p in parsed:
            if p in DEFAULT_BACKEND_PRIORITY and p not in out:
                out.append(p)
        for p in DEFAULT_BACKEND_PRIORITY:
            if p not in out:
                out.append(p)
        return out

    def _snapshot_backend_health(self) -> Dict[str, Tuple[bool, Dict[str, Any]]]:
        checks: Dict[str, Tuple[bool, Dict[str, Any]]] = {}
        for name, backend in (
            ("local_catvton", self._catvton),
            ("local_idmvton", self._idmvton),
            ("remote_gpu", self._remote),
            ("replicate", self._replicate),
            ("fashn", self._fashn),
            ("huggingface_space", self._hf_space),
        ):
            healthy, meta = backend.probe_sync()
            checks[name] = (healthy, meta)
        return checks

    def snapshot(self) -> TryOnCapabilities:
        priority = self._resolve_priority()
        cuda_available = bool(torch.cuda.is_available())
        vram_gb = None
        if cuda_available:
            try:
                vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
            except Exception:
                vram_gb = None

        checks = self._snapshot_backend_health()
        active_backend = "preview_only"
        final_render_available = False
        for name in priority:
            if name == "preview_only":
                break
            if checks.get(name, (False, {}))[0]:
                active_backend = name
                final_render_available = True
                break

        failure_reason = None
        if not final_render_available:
            failure_reason = "GPU_NOT_AVAILABLE" if not cuda_available else "FINAL_RENDER_UNAVAILABLE"

        details = {
            "cuda_available": cuda_available,
            "gpu_vram_gb": vram_gb,
            "health": {k: {"healthy": v[0], **v[1]} for k, v in checks.items()},
            "policy": "free_first",
        }

        return TryOnCapabilities(
            preview_available=True,
            final_render_available=final_render_available,
            active_backend=active_backend,
            backend_priority=priority,
            failure_reason=failure_reason,
            details=details,
        )

