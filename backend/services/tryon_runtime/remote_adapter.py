from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Tuple
from urllib.parse import urlparse, urlunparse

import httpx


def _build_health_url(render_url: str) -> str:
    explicit = (os.getenv("TRYON_REMOTE_HEALTH_URL") or "").strip()
    if explicit:
        return explicit
    p = urlparse(render_url)
    # Default convention: same host with /health path.
    return urlunparse((p.scheme, p.netloc, "/health", "", "", ""))


def _remote_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    key = (os.getenv("TRYON_REMOTE_API_KEY") or "").strip()
    if key:
        auth_header = (os.getenv("TRYON_REMOTE_AUTH_HEADER") or "Authorization").strip()
        auth_scheme = (os.getenv("TRYON_REMOTE_AUTH_SCHEME") or "Bearer").strip()
        if auth_scheme:
            headers[auth_header] = f"{auth_scheme} {key}"
        else:
            headers[auth_header] = key

    extra = (os.getenv("TRYON_REMOTE_EXTRA_HEADERS_JSON") or "").strip()
    if extra:
        try:
            obj = json.loads(extra)
            if isinstance(obj, dict):
                for k, v in obj.items():
                    headers[str(k)] = str(v)
        except Exception:
            # Ignore malformed extra header JSON; do not break request flow.
            pass
    return headers


class RemoteGPUAdapter:
    """Remote self-hosted neural render adapter with health and retries."""

    def __init__(self) -> None:
        self.render_url = (os.getenv("TRYON_REMOTE_URL") or "").strip()
        self.health_url = _build_health_url(self.render_url) if self.render_url else ""
        self.health_timeout_sec = float(os.getenv("TRYON_REMOTE_HEALTH_TIMEOUT_SEC", "2.5"))
        self.render_timeout_sec = float(os.getenv("TRYON_REMOTE_TIMEOUT_SEC", "180"))
        self.max_retries = max(0, int(os.getenv("TRYON_REMOTE_RETRIES", "2")))
        self.retry_backoff_sec = max(0.05, float(os.getenv("TRYON_REMOTE_RETRY_BACKOFF_SEC", "0.8")))

    def configured(self) -> bool:
        return bool(self.render_url)

    def probe_sync(self) -> Tuple[bool, str]:
        if not self.configured():
            return False, "TRYON_REMOTE_URL is not configured."
        started = time.time()
        try:
            with httpx.Client(timeout=self.health_timeout_sec, headers=_remote_headers()) as client:
                r = client.get(self.health_url)
            if r.status_code >= 400:
                return False, f"Remote health check HTTP {r.status_code}"
            return True, f"ok ({round((time.time() - started) * 1000, 1)} ms)"
        except Exception as exc:
            return False, f"Remote health probe failed: {exc}"

    async def render(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.configured():
            return {
                "success": False,
                "error_code": "FINAL_RENDER_UNAVAILABLE",
                "message": "TRYON_REMOTE_URL is not configured.",
            }

        headers = _remote_headers()
        last_error: str | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.render_timeout_sec, headers=headers) as client:
                    r = await client.post(self.render_url, json=payload)
                if r.status_code >= 500:
                    last_error = f"Remote backend HTTP {r.status_code}"
                elif r.status_code >= 400:
                    return {
                        "success": False,
                        "error_code": "REMOTE_RENDER_FAILED",
                        "message": f"Remote backend HTTP {r.status_code}",
                    }
                else:
                    data = r.json()
                    image = data.get("resultImage") or data.get("result_image")
                    if not image:
                        return {
                            "success": False,
                            "error_code": "REMOTE_RENDER_INVALID_RESPONSE",
                            "message": "Remote backend did not return image payload.",
                        }
                    return {
                        "success": True,
                        "result_image": image,
                        "backend_used": "remote_neural",
                        "warnings": data.get("warnings", []),
                    }
            except Exception as exc:
                last_error = str(exc)

            # Retry on transient errors
            if attempt < self.max_retries:
                await _sleep_backoff(self.retry_backoff_sec * (attempt + 1))

        return {
            "success": False,
            "error_code": "REMOTE_RENDER_EXCEPTION",
            "message": f"Remote render failed after retries: {last_error or 'unknown error'}",
        }


async def _sleep_backoff(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)

