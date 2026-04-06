from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
from PIL import Image

import os

from services.tryon.vision.pose import POSE_CONFIDENCE_MIN, PoseDetector, PoseResult


Landmark = Tuple[float, float, float]


@dataclass
class PoseMap:
    left_shoulder: Landmark
    right_shoulder: Landmark
    neck: Landmark
    left_hip: Landmark
    right_hip: Landmark
    confidence: float
    image_width: int
    image_height: int

    def to_json(self) -> str:
        return json.dumps(
            {
                "confidence": float(self.confidence),
                "image_width": int(self.image_width),
                "image_height": int(self.image_height),
                "left_shoulder": _lm_to_dict(self.left_shoulder),
                "right_shoulder": _lm_to_dict(self.right_shoulder),
                "neck": _lm_to_dict(self.neck),
                "left_hip": _lm_to_dict(self.left_hip),
                "right_hip": _lm_to_dict(self.right_hip),
            }
        )


def _lm_to_dict(lm: Landmark) -> Dict[str, float]:
    return {"x": float(lm[0]), "y": float(lm[1]), "visibility": float(lm[2])}


def _safe_landmark(pose: PoseResult, name: str, fallback_xy: Tuple[float, float]) -> Landmark:
    lm = pose.landmarks.get(name)
    if lm is None:
        return (float(fallback_xy[0]), float(fallback_xy[1]), 0.0)
    return (float(lm[0]), float(lm[1]), float(lm[2]))


class PoseService:
    """Reusable pose service built on top of MediaPipe PoseDetector."""

    def __init__(self) -> None:
        use_gpu = os.getenv("TRYON_FORCE_CPU", "").strip().lower() not in ("1", "true", "yes")
        self._detector = PoseDetector(use_gpu=use_gpu)

    async def detect(self, image: Image.Image) -> PoseResult:
        # Fast path first: avoid re-instantiating multiple PoseDetector objects
        # on CPU previews. Retry path is used only when the first pass fails.
        first = await self._detector.detect_from_pil(image)
        if first.success and first.confidence >= POSE_CONFIDENCE_MIN:
            return first
        return await self._detector.detect_from_pil_with_retry(image)

    def build_pose_map(self, pose: PoseResult, image_width: int, image_height: int) -> Optional[PoseMap]:
        if not pose.success or not pose.landmarks:
            return None

        ls = _safe_landmark(pose, "left_shoulder", (image_width * 0.35, image_height * 0.25))
        rs = _safe_landmark(pose, "right_shoulder", (image_width * 0.65, image_height * 0.25))
        lh = _safe_landmark(pose, "left_hip", (image_width * 0.4, image_height * 0.58))
        rh = _safe_landmark(pose, "right_hip", (image_width * 0.6, image_height * 0.58))

        neck = (
            float((ls[0] + rs[0]) * 0.5),
            float((ls[1] + rs[1]) * 0.5),
            float(min(ls[2], rs[2])),
        )
        confidence = float(np.mean([ls[2], rs[2], lh[2], rh[2]]))
        return PoseMap(
            left_shoulder=ls,
            right_shoulder=rs,
            neck=neck,
            left_hip=lh,
            right_hip=rh,
            confidence=confidence,
            image_width=image_width,
            image_height=image_height,
        )

    @staticmethod
    def mediapipe_pose_ok(pose: PoseResult) -> bool:
        return bool(pose.success and pose.confidence >= POSE_CONFIDENCE_MIN)

    def health_check(self) -> Dict[str, object]:
        return self._detector.health_check()

    def close(self) -> None:
        self._detector.close()
