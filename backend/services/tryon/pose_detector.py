"""
Legacy adapter: bytes API + dict keypoints for services.tryon.orchestrator.
Delegates to services.tryon.vision.PoseDetector.
"""

import io
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

from services.tryon.vision.pose import (
    PoseDetector as VisionPoseDetector,
    pose_result_to_legacy_keypoints_dict,
)

logger = logging.getLogger(__name__)

MEDIAPIPE_LANDMARKS = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear", "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_pinky", "right_pinky",
    "left_index", "right_index", "left_thumb", "right_thumb",
    "left_hip", "right_hip", "left_knee", "right_knee",
    "left_ankle", "right_ankle", "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
]


class PoseDetector:
    """Wraps unified vision PoseDetector; exposes async detect(image_bytes) for legacy code."""

    def __init__(
        self,
        model_complexity: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        use_gpu: bool = True,
    ):
        self._inner = VisionPoseDetector(
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            model_complexity=model_complexity,
        )
        self._initialized = self._inner._initialized
        self.model_complexity = model_complexity

    async def detect(self, image_bytes: bytes) -> Dict[str, Any]:
        if not self._inner._initialized:
            return {
                "keypoints": None,
                "score": 0.0,
                "is_valid": False,
                "error": self._inner._init_error or "Pose unavailable",
            }
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            return {"keypoints": None, "score": 0.0, "is_valid": False, "error": str(e)}

        pr = await self._inner.detect_from_pil(img)
        if not pr.success:
            return {
                "keypoints": None,
                "score": 0.0,
                "is_valid": False,
                "error": pr.error_message or "No pose",
            }

        kp_dict = pose_result_to_legacy_keypoints_dict(pr)
        score = float(pr.confidence)
        is_valid = score >= 0.35 and len(kp_dict) >= 8

        return {
            "keypoints": kp_dict,
            "score": score,
            "is_valid": is_valid,
            "num_landmarks": len(kp_dict),
        }

    def get_body_bbox(
        self,
        keypoints: Dict[int, Dict],
        image_shape: Tuple[int, int],
        padding: float = 0.1,
    ) -> Tuple[int, int, int, int]:
        h, w = image_shape
        visible = []
        for _k, kp in keypoints.items():
            if kp.get("visibility", 0) > 0.3:
                visible.append((kp["x"] * w, kp["y"] * h))
        if not visible:
            return (0, 0, w, h)
        xs = [p[0] for p in visible]
        ys = [p[1] for p in visible]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        pad_x = (x_max - x_min) * padding
        pad_y = (y_max - y_min) * padding
        return (
            int(max(0, x_min - pad_x)),
            int(max(0, y_min - pad_y)),
            int(min(w, x_max + pad_x)),
            int(min(h, y_max + pad_y)),
        )

    def estimate_pose_angle(self, keypoints: Dict[int, Dict]) -> float:
        if 11 not in keypoints or 12 not in keypoints:
            return 0.0
        ls, rs = keypoints[11], keypoints[12]
        dx = rs["x"] - ls["x"]
        dy = rs["y"] - ls["y"]
        return float(np.degrees(np.arctan2(dy, dx)))

    def close(self) -> None:
        self._inner.close()


class MMPoseDetector(PoseDetector):
    """Stub — falls back to MediaPipe wrapper."""

    def __init__(self, config_path: Optional[str] = None):
        super().__init__()
