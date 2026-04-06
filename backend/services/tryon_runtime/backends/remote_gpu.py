from __future__ import annotations

import os
import time
from typing import Any, Dict, Tuple

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import TryOnBackendBase


class RemoteGPUBackend(TryOnBackendBase):
    backend_name = "remote_gpu"

    def __init__(self) -> None:
        self.url = (os.getenv("TRYON_REMOTE_URL") or "").strip()
        self.key = (os.getenv("TRYON_REMOTE_API_KEY") or "").strip()
        self.timeout_sec = float(os.getenv("TRYON_REMOTE_TIMEOUT_SEC", "180"))
        self.health_timeout_sec = float(os.getenv("TRYON_HEALTHCHECK_TIMEOUT_SEC", "5"))

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        return headers

    def probe_sync(self) -> Tuple[bool, Dict[str, Any]]:
        if not self.url:
            return False, {"reason": "REMOTE_BACKEND_UNHEALTHY", "message": "TRYON_REMOTE_URL not configured"}
        health_url = self.url.rstrip("/") + "/health" if not self.url.endswith("/render") else self.url.replace("/render", "/health")
        try:
            with httpx.Client(timeout=self.health_timeout_sec, headers=self._headers()) as client:
                resp = client.get(health_url)
            if resp.status_code >= 400:
                return False, {"reason": "REMOTE_BACKEND_UNHEALTHY", "message": f"Health HTTP {resp.status_code}"}
            return True, {"reason": None, "health_url": health_url}
        except Exception as exc:
            return False, {"reason": "REMOTE_BACKEND_UNHEALTHY", "message": str(exc)}

    @retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=6), stop=stop_after_attempt(3), reraise=True)
    async def _do_render(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_sec, headers=self._headers()) as client:
            resp = await client.post(self.url, json=payload)
        if resp.status_code == 429:
            return {"success": False, "error_code": "QUOTA_EXHAUSTED", "message": "Remote backend quota exhausted"}
        if resp.status_code >= 400:
            return {"success": False, "error_code": "REMOTE_BACKEND_UNHEALTHY", "message": f"Remote HTTP {resp.status_code}"}
        data = resp.json()
        image = data.get("resultImage") or data.get("result_image")
        if not image:
            return {"success": False, "error_code": "REMOTE_BACKEND_UNHEALTHY", "message": "Remote returned no image"}
        return {
            "success": True,
            "render_kind": "final",
            "backend_name": self.backend_name,
            "image_url": image,
            "quality_score": float(data.get("quality_score", 0.0) or 0.0),
            "alignment_diagnostics_json": data.get("alignment_diagnostics_json"),
        }

    async def render(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        started = time.time()
        ok, meta = self.probe_sync()
        if not ok:
            return {"success": False, "error_code": meta.get("reason"), "message": meta.get("message")}
        try:
            out = await self._do_render(payload)
            out["latency_ms"] = round((time.time() - started) * 1000, 1)
            return out
        except httpx.TimeoutException:
            return {"success": False, "error_code": "TIMEOUT", "message": "Remote render timed out"}
        except Exception as exc:
            return {"success": False, "error_code": "REMOTE_BACKEND_UNHEALTHY", "message": str(exc)}

