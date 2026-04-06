from __future__ import annotations

import base64
import io
from typing import Any, Dict, Tuple

import numpy as np
from PIL import Image


class QualityGuard:
    """
    Lightweight guardrail checks for final neural output quality.
    This is intentionally conservative to avoid returning obvious failures.
    """

    def evaluate(
        self,
        *,
        user_image_base64: str,
        garment_image_base64: str | None,
        result_image_base64: str,
    ) -> Tuple[bool, Dict[str, Any]]:
        try:
            user = self._decode(user_image_base64)
            result = self._decode(result_image_base64)
        except Exception as exc:
            return False, {"failure_kind": "QUALITY_REJECTED", "message": f"Invalid output image: {exc}"}

        if result.shape[0] < 128 or result.shape[1] < 128:
            return False, {"failure_kind": "QUALITY_REJECTED", "message": "Output resolution is too low"}

        edge_score = self._edge_ratio(result)
        if edge_score > 0.27:
            return False, {"failure_kind": "QUALITY_REJECTED", "message": "Sticker-like hard edges detected"}

        drift = self._identity_drift(user, result)
        if drift > 0.35:
            return False, {"failure_kind": "QUALITY_REJECTED", "message": "Face/body identity drift too high"}

        return True, {
            "quality_score": float(max(0.0, 1.0 - max(drift, edge_score))),
            "checks": {"edge_ratio": edge_score, "identity_drift": drift},
        }

    @staticmethod
    def _decode(b64: str) -> np.ndarray:
        raw = b64.split(",", 1)[1] if "," in b64 else b64
        data = base64.b64decode(raw)
        img = Image.open(io.BytesIO(data)).convert("RGB")
        return np.array(img)

    @staticmethod
    def _edge_ratio(img: np.ndarray) -> float:
        gx = np.abs(np.diff(img.astype(np.float32), axis=1)).mean()
        gy = np.abs(np.diff(img.astype(np.float32), axis=0)).mean()
        return float((gx + gy) / 255.0)

    @staticmethod
    def _identity_drift(user: np.ndarray, result: np.ndarray) -> float:
        h = min(user.shape[0], result.shape[0])
        w = min(user.shape[1], result.shape[1])
        if h < 16 or w < 16:
            return 1.0
        u = user[:h, :w].astype(np.float32) / 255.0
        r = result[:h, :w].astype(np.float32) / 255.0
        return float(np.mean(np.abs(u - r)))

