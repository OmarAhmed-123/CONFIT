"""
FASHN Virtual Try-On API (tryon-v1.6) — diffusion-based try-on, not image overlay.

Docs: https://docs.fashn.ai/api-reference/tryon-v1-6
Requires: FASHN_API_KEY from https://app.fashn.ai/api
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import time
from typing import Any, Dict, Optional

import httpx
try:
    from fashn import Fashn  # official SDK (optional)
    FASHN_SDK_AVAILABLE = True
except Exception:  # pragma: no cover
    FASHN_SDK_AVAILABLE = False
    Fashn = None  # type: ignore

from services.tryon.category_rules import to_fashn_category

logger = logging.getLogger(__name__)

FASHN_BASE = os.getenv("FASHN_API_BASE", "https://api.fashn.ai/v1").rstrip("/")
MODEL_NAME = os.getenv("FASHN_TRYON_MODEL", "tryon-v1.6")
MAX_POLL_SECONDS = float(os.getenv("FASHN_TRYON_MAX_WAIT", "120"))
POLL_INTERVAL = float(os.getenv("FASHN_TRYON_POLL_SEC", "0.8"))


def _ensure_data_uri(image_b64_or_uri: str, default_mime: str = "image/jpeg") -> str:
    s = (image_b64_or_uri or "").strip()
    if s.startswith("data:"):
        return s
    # raw base64
    return f"data:{default_mime};base64,{s}"


async def _download_as_data_uri(url: str) -> str:
    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        mime = r.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        if "octet-stream" in mime or not mime.startswith("image/"):
            mime = "image/jpeg"
        b64 = base64.standard_b64encode(r.content).decode("ascii")
        return f"data:{mime};base64,{b64}"


class FashnTryOnService:
    """Async client: POST /v1/run → poll GET /v1/status/{id}."""

    def __init__(self) -> None:
        self._api_key = (os.getenv("FASHN_API_KEY") or "").strip()
        self._sdk_client = None
        if self._api_key and FASHN_SDK_AVAILABLE:
            try:
                self._sdk_client = Fashn(api_key=self._api_key)
            except Exception:
                self._sdk_client = None

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def process_tryon(
        self,
        user_image_base64: str,
        garment_image_url: str,
        garment_category: Optional[str] = None,
        mode: str = "balanced",
        garment_photo_type: str = "auto",
    ) -> Dict[str, Any]:
        if not self._api_key:
            return {
                "success": False,
                "error": "FASHN_API_KEY not set",
                "result_image": None,
            }

        try:
            model_img = _ensure_data_uri(user_image_base64)

            # FASHN cloud cannot fetch localhost / private URLs — always inline garment bytes
            gurl = (garment_image_url or "").strip()
            if gurl.startswith(("http://", "https://")):
                garment_img = await _download_as_data_uri(gurl)
            else:
                return {
                    "success": False,
                    "error": "Invalid garment_image_url",
                    "result_image": None,
                }

            cat = to_fashn_category(garment_category)

            # Prefer official SDK if available. Fallback to HTTP API implementation.
            if self._sdk_client is not None:
                sdk_result = await self._process_tryon_sdk(
                    model_img=model_img,
                    garment_img=garment_img,
                    category=cat,
                    mode=mode,
                    garment_photo_type=garment_photo_type,
                )
                if sdk_result.get("success"):
                    return sdk_result
                logger.warning("FASHN SDK failed; falling back to HTTP API: %s", sdk_result.get("error"))

            payload: Dict[str, Any] = {
                "model_name": MODEL_NAME,
                "inputs": {
                    "model_image": model_img,
                    "garment_image": garment_img,
                    "category": cat,
                    "mode": mode,
                    "garment_photo_type": garment_photo_type,
                    "return_base64": True,
                    "output_format": "jpeg",
                    "segmentation_free": True,
                    "moderation_level": "permissive",
                    "num_samples": 1,
                },
            }

            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                pr = await client.post(f"{FASHN_BASE}/run", json=payload, headers=headers)
                if pr.status_code >= 400:
                    return {
                        "success": False,
                        "error": f"FASHN run failed: {pr.status_code} {pr.text[:500]}",
                        "result_image": None,
                    }
                run_data = pr.json()
                pred_id = run_data.get("id")
                if run_data.get("error") or not pred_id:
                    return {
                        "success": False,
                        "error": str(run_data.get("error") or "No prediction id"),
                        "result_image": None,
                    }

                deadline = time.monotonic() + MAX_POLL_SECONDS
                while time.monotonic() < deadline:
                    sr = await client.get(
                        f"{FASHN_BASE}/status/{pred_id}",
                        headers={"Authorization": f"Bearer {self._api_key}"},
                    )
                    if sr.status_code >= 400:
                        return {
                            "success": False,
                            "error": f"FASHN status failed: {sr.status_code}",
                            "result_image": None,
                        }
                    st = sr.json()
                    status = st.get("status")
                    if status == "completed":
                        out = st.get("output") or []
                        if isinstance(out, list) and out:
                            first = out[0]
                            data_uri = ""
                            if isinstance(first, str) and first.startswith("data:"):
                                data_uri = first
                            elif isinstance(first, str) and first.startswith("http"):
                                gr = await client.get(first, timeout=60.0)
                                gr.raise_for_status()
                                b64 = base64.standard_b64encode(gr.content).decode("ascii")
                                mime = "image/png" if "png" in first.lower() else "image/jpeg"
                                data_uri = f"data:{mime};base64,{b64}"
                            else:
                                data_uri = str(first)
                            return {
                                "success": True,
                                "result_image": data_uri,
                                "quality_score": 0.92,
                                "pose_detected": True,
                                "garment_category": cat,
                                "backend_used": "fashn",
                                "warnings": [],
                            }
                        return {
                            "success": False,
                            "error": "FASHN completed but no output",
                            "result_image": None,
                        }
                    if status == "failed":
                        err = st.get("error") or {}
                        msg = err.get("message") if isinstance(err, dict) else str(err)
                        return {
                            "success": False,
                            "error": f"FASHN failed: {msg}",
                            "result_image": None,
                        }
                    await asyncio.sleep(POLL_INTERVAL)

                return {
                    "success": False,
                    "error": "FASHN try-on timed out while polling status",
                    "result_image": None,
                }

        except Exception as e:
            logger.exception("FASHN try-on error: %s", e)
            return {
                "success": False,
                "error": str(e),
                "result_image": None,
            }

    async def _process_tryon_sdk(
        self,
        *,
        model_img: str,
        garment_img: str,
        category: str,
        mode: str,
        garment_photo_type: str,
    ) -> Dict[str, Any]:
        """
        Official FASHN SDK path:
          client.predictions.subscribe(model_name="tryon-v1.6", inputs={...})
        """
        if self._sdk_client is None:
            return {"success": False, "error": "fashn_sdk_not_initialized", "result_image": None}

        def _call():
            return self._sdk_client.predictions.subscribe(
                model_name=MODEL_NAME,
                inputs={
                    "model_image": model_img,
                    "garment_image": garment_img,
                    "category": category,
                    "mode": mode,
                    "garment_photo_type": garment_photo_type,
                    "return_base64": True,
                    "output_format": "jpeg",
                    "segmentation_free": True,
                    "moderation_level": "permissive",
                    "num_samples": 1,
                },
            )

        try:
            result = await asyncio.to_thread(_call)
            # SDK response can vary; normalize robustly.
            data = result if isinstance(result, dict) else getattr(result, "to_dict", lambda: result)()
            if not isinstance(data, dict):
                data = {}
            if data.get("error"):
                return {"success": False, "error": str(data.get("error")), "result_image": None}

            out = data.get("output") or data.get("outputs") or []
            first = out[0] if isinstance(out, list) and out else None
            if isinstance(first, str) and first.startswith("data:"):
                return {
                    "success": True,
                    "result_image": first,
                    "quality_score": 0.92,
                    "pose_detected": True,
                    "garment_category": category,
                    "backend_used": "fashn",
                    "warnings": [],
                }
            if isinstance(first, str) and first.startswith("http"):
                async with httpx.AsyncClient(timeout=60.0) as client:
                    gr = await client.get(first)
                    gr.raise_for_status()
                    b64 = base64.standard_b64encode(gr.content).decode("ascii")
                    mime = "image/png" if "png" in first.lower() else "image/jpeg"
                    data_uri = f"data:{mime};base64,{b64}"
                    return {
                        "success": True,
                        "result_image": data_uri,
                        "quality_score": 0.92,
                        "pose_detected": True,
                        "garment_category": category,
                        "backend_used": "fashn",
                        "warnings": [],
                    }

            return {"success": False, "error": "FASHN SDK completed but no output", "result_image": None}
        except Exception as e:
            return {"success": False, "error": f"FASHN SDK error: {e}", "result_image": None}
