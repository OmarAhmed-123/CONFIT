"""
Unified pose detection for virtual try-on (MediaPipe).
Merged from services/ai and services/tryon pose modules — single source of truth.

Coordinate convention (MediaPipe pose):
- Landmark indices follow the MediaPipe pose topology (e.g. 11 = left_shoulder,
  12 = right_shoulder). Names refer to the **subject's** left/right (anatomical),
  not the camera's left/right.
- Normalized image coordinates (lm.x, lm.y) are converted to pixel (x, y) with
  origin at the **top-left** of the image. For a person facing the camera, the
  subject's left shoulder often appears on the **right** side of the image
  (larger x). That ordering is expected; do not treat it as a horizontal flip.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore

#
# Silence noisy TensorFlow/MediaPipe C++ logs (these are glog/absl messages).
# Must be set before importing mediapipe/tasks.
#
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("GLOG_minloglevel", "3")
os.environ.setdefault("ABSL_MIN_LOG_LEVEL", "2")

try:
    import mediapipe as mp

    # Keep `mp` even when `solutions` is missing (Tasks API still needs mp.Image).
    MEDIAPIPE_AVAILABLE = bool(
        hasattr(mp, "solutions") and hasattr(mp.solutions, "pose")
    )
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None  # type: ignore

try:
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision

    MEDIAPIPE_TASKS_AVAILABLE = True
except ImportError:
    mp_python = None  # type: ignore
    mp_vision = None  # type: ignore
    MEDIAPIPE_TASKS_AVAILABLE = False

from services.tryon.vision.mediapipe_tasks_models import (
    ensure_pose_landmarker_path,
    ensure_pose_landmarker_full_path,
    ensure_pose_landmarker_heavy_path,
    get_gpu_delegate_options,
    set_mediapipe_gpu_delegate_unavailable,
)
from core.log_suppression import suppress_native_output

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None  # type: ignore

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)

# Minimum mean landmark visibility to accept MediaPipe pose (self-healing retries below this).
POSE_CONFIDENCE_MIN = 0.6
# Reject try-on if mean visibility of all returned landmarks is below this (safeguard).
TRYON_MIN_MEAN_LANDMARK_VISIBILITY = float(os.getenv("TRYON_MIN_MEAN_LANDMARK_VISIBILITY", "0.4"))
# Key landmarks for try-on must exceed this visibility (MediaPipe visibility/presence 0–1).
TRYON_KEY_LANDMARK_MIN_VISIBILITY = float(os.getenv("TRYON_KEY_LANDMARK_MIN_VISIBILITY", "0.5"))
_MAX_POSE_ATTEMPTS = 4

def validate_pose_for_tryon(pose: PoseResult) -> tuple[bool, Optional[str]]:
    """
    Enforce confidence on anchors used for warp and compositing.

    Mean visibility is computed only over core try-on joints (not every padded landmark),
    so silhouette/synthetic poses with many low-vis placeholders are not rejected spuriously.
    """
    if not pose.success or not pose.landmarks:
        return False, "Pose detection failed or no landmarks"
    core_names = (
        "nose",
        "left_shoulder",
        "right_shoulder",
        "left_elbow",
        "right_elbow",
        "left_wrist",
        "right_wrist",
        "left_hip",
        "right_hip",
    )
    core_vis = [float(pose.landmarks[n][2]) for n in core_names if n in pose.landmarks]
    if not core_vis:
        return False, "Pose missing core landmarks"
    mean_vis = float(sum(core_vis) / len(core_vis))
    if mean_vis < TRYON_MIN_MEAN_LANDMARK_VISIBILITY:
        return (
            False,
            f"Pose visibility too low (core mean {mean_vis:.2f} < {TRYON_MIN_MEAN_LANDMARK_VISIBILITY}); use a clearer full-body photo",
        )
    for name in ("left_shoulder", "right_shoulder", "left_hip", "right_hip"):
        lm = pose.landmarks.get(name)
        if lm is None or float(lm[2]) < TRYON_KEY_LANDMARK_MIN_VISIBILITY:
            return (
                False,
                f"Unreliable pose anchors ({name} visibility below {TRYON_KEY_LANDMARK_MIN_VISIBILITY})",
            )
    nose = pose.landmarks.get("nose")
    if nose is not None and float(nose[2]) < 0.2:
        # Front view can still work; only fail if shoulders also weak (already checked)
        pass
    return True, None


@dataclass
class BodyRegion:
    name: str
    x: int
    y: int
    width: int
    height: int
    confidence: float = 1.0
    landmarks: List[Tuple[int, int]] = field(default_factory=list)


@dataclass
class PoseResult:
    success: bool
    landmarks: Dict[str, Tuple[float, float, float]]
    body_regions: Dict[str, BodyRegion]
    body_proportions: Dict[str, float]
    image_width: int
    image_height: int
    confidence: float
    error_message: Optional[str] = None
    torso_region: Optional[BodyRegion] = None
    upper_body_region: Optional[BodyRegion] = None
    lower_body_region: Optional[BodyRegion] = None
    full_body_region: Optional[BodyRegion] = None


LANDMARK_NAMES = [
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


def pose_to_skeleton_json(pose: PoseResult) -> str:
    """Normalized skeleton as JSON (pixel coords + visibilities)."""
    if not pose.success:
        return json.dumps({"success": False, "error": pose.error_message or "no_pose"})
    w, h = float(pose.image_width), float(pose.image_height)
    joints = []
    for name, (px, py, vis) in pose.landmarks.items():
        joints.append(
            {
                "name": name,
                "x_norm": px / w if w else 0,
                "y_norm": py / h if h else 0,
                "x_px": px,
                "y_px": py,
                "visibility": vis,
            }
        )
    return json.dumps({"success": True, "joints": joints, "confidence": pose.confidence})


def synthetic_pose_from_person_mask(mask: np.ndarray, image_width: int, image_height: int) -> PoseResult:
    """
    Estimate shoulder / torso / hip anchors from a binary person mask when MediaPipe is unavailable
    or confidence is low. Aligns garment to the largest foreground blob (not image center).
    """
    if cv2 is None:
        return PoseResult(
            success=False,
            landmarks={},
            body_regions={},
            body_proportions={},
            image_width=image_width,
            image_height=image_height,
            confidence=0.0,
            error_message="OpenCV required for silhouette pose",
        )
    h, w = image_height, image_width
    m = (mask > 127).astype(np.uint8) * 255
    if int(m.sum()) < 500:
        return PoseResult(
            success=False,
            landmarks={},
            body_regions={},
            body_proportions={},
            image_width=w,
            image_height=h,
            confidence=0.0,
            error_message="Person mask too small",
        )
    contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return PoseResult(
            success=False,
            landmarks={},
            body_regions={},
            body_proportions={},
            image_width=w,
            image_height=h,
            confidence=0.0,
            error_message="No contour in person mask",
        )
    c = max(contours, key=cv2.contourArea)
    x, y, bw, bh = cv2.boundingRect(c)
    cx = float(x + bw * 0.5)
    # Upper torso: typical shirt region in upright photos
    shoulder_y = float(y + bh * 0.14)
    hip_y = float(y + bh * 0.52)
    knee_y = float(y + bh * 0.78)
    ankle_y = float(min(h - 2.0, y + bh * 0.96))
    sw = max(24.0, float(bw) * 0.44)

    def _lm(px: float, py: float, vis: float) -> Tuple[float, float, float]:
        return (float(np.clip(px, 0, w - 1)), float(np.clip(py, 0, h - 1)), vis)

    landmarks: Dict[str, Tuple[float, float, float]] = {
        "nose": _lm(cx, y + bh * 0.06, 0.45),
        "left_eye": _lm(cx - sw * 0.15, y + bh * 0.05, 0.35),
        "right_eye": _lm(cx + sw * 0.15, y + bh * 0.05, 0.35),
        "left_shoulder": _lm(cx - sw * 0.5, shoulder_y, 0.55),
        "right_shoulder": _lm(cx + sw * 0.5, shoulder_y, 0.55),
        "left_elbow": _lm(cx - sw * 0.75, shoulder_y + bh * 0.18, 0.4),
        "right_elbow": _lm(cx + sw * 0.75, shoulder_y + bh * 0.18, 0.4),
        "left_wrist": _lm(cx - sw * 0.85, shoulder_y + bh * 0.32, 0.35),
        "right_wrist": _lm(cx + sw * 0.85, shoulder_y + bh * 0.32, 0.35),
        "left_hip": _lm(cx - sw * 0.38, hip_y, 0.5),
        "right_hip": _lm(cx + sw * 0.38, hip_y, 0.5),
        "left_knee": _lm(cx - sw * 0.35, knee_y, 0.4),
        "right_knee": _lm(cx + sw * 0.35, knee_y, 0.4),
        "left_ankle": _lm(cx - sw * 0.3, ankle_y, 0.35),
        "right_ankle": _lm(cx + sw * 0.3, ankle_y, 0.35),
    }
    # Fill remaining names with low-visibility placeholders (callers use sparse keys)
    for name in LANDMARK_NAMES:
        if name not in landmarks:
            landmarks[name] = (cx, hip_y, 0.05)

    conf = float(np.mean([landmarks[k][2] for k in ("left_shoulder", "right_shoulder", "left_hip", "right_hip")]))

    return PoseResult(
        success=True,
        landmarks=landmarks,
        body_regions={},
        body_proportions={"torso_length": abs(hip_y - shoulder_y), "shoulder_width": sw},
        image_width=w,
        image_height=h,
        confidence=conf,
        torso_region=None,
        upper_body_region=None,
        lower_body_region=None,
        full_body_region=None,
    )


def pose_result_to_legacy_keypoints_dict(pose: PoseResult) -> Dict[int, Dict[str, Any]]:
    """Legacy orchestrator format: index -> {x,y,z,visibility} normalized 0-1."""
    out: Dict[int, Dict[str, Any]] = {}
    if not pose.success or not pose.landmarks:
        return out
    w, h = pose.image_width, pose.image_height
    for i, name in enumerate(LANDMARK_NAMES):
        if name not in pose.landmarks:
            continue
        px, py, vis = pose.landmarks[name]
        out[i] = {
            "x": px / w if w else 0,
            "y": py / h if h else 0,
            "z": 0.0,
            "visibility": vis,
            "name": name,
        }
    return out


def pose_pose_backend_available() -> bool:
    """True if MediaPipe pose can run (legacy `solutions` or Tasks PoseLandmarker)."""
    return MEDIAPIPE_AVAILABLE or MEDIAPIPE_TASKS_AVAILABLE


class PoseDetector:
    """MediaPipe pose — configurable thresholds for self-healing retry.
    
    Supports GPU delegate when available. Set MEDIAPIPE_USE_GPU=0 to force CPU.
    For higher accuracy without GPU, use model_complexity=2.
    """

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        model_complexity: int = 2,
        use_gpu: bool = True,
    ):
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.model_complexity = model_complexity
        force_cpu = os.getenv("TRYON_FORCE_CPU", "").strip().lower() in ("1", "true", "yes")
        self._use_gpu_requested = bool(use_gpu) and not force_cpu
        if force_cpu:
            logger.info("PoseDetector: TRYON_FORCE_CPU=1 — GPU delegate disabled for pose")
        self._pose = None
        self._landmarker = None
        self._use_tasks = False
        self._initialized = False
        self._init_error: Optional[str] = None
        self._gpu_enabled = False

        if not PIL_AVAILABLE:
            self._init_error = "PIL not installed"
            return

        # 1) Legacy solutions API (full Python wheels)
        if MEDIAPIPE_AVAILABLE and mp is not None:
            try:
                self._pose = mp.solutions.pose.Pose(
                    static_image_mode=True,
                    model_complexity=self.model_complexity,
                    enable_segmentation=False,
                    min_detection_confidence=self.min_detection_confidence,
                    min_tracking_confidence=self.min_tracking_confidence,
                )
                self._initialized = True
                logger.info("PoseDetector (MediaPipe solutions) initialized, model_complexity=%d", self.model_complexity)
                return
            except Exception as e:
                self._init_error = str(e)
                logger.error("Pose init (solutions) failed: %s", e)

        # 2) Tasks API (PoseLandmarker) — works when `mediapipe.solutions` is missing
        if MEDIAPIPE_TASKS_AVAILABLE and mp_python is not None and mp_vision is not None:
            # Select model based on model_complexity
            if self.model_complexity >= 2:
                path = ensure_pose_landmarker_heavy_path() or ensure_pose_landmarker_full_path()
                if not path:
                    path = ensure_pose_landmarker_path()
            elif self.model_complexity == 1:
                path = ensure_pose_landmarker_full_path() or ensure_pose_landmarker_path()
            else:
                path = ensure_pose_landmarker_path()
            
            if path:
                try:
                    # Configure GPU delegate - get actual enum value
                    gpu_opts = get_gpu_delegate_options() if self._use_gpu_requested else {}  # TRYON_FORCE_CPU clears delegate
                    delegate = gpu_opts.get("delegate")  # This is now Delegate.GPU enum, not string
                    
                    base_opts_dict = {"model_asset_path": path}
                    if delegate is not None:
                        base_opts_dict["delegate"] = delegate
                        self._gpu_enabled = True
                        logger.info("PoseDetector: GPU delegate enabled")
                    
                    base = mp_python.BaseOptions(**base_opts_dict)
                    opts = mp_vision.PoseLandmarkerOptions(
                        base_options=base,
                        running_mode=mp_vision.RunningMode.IMAGE,
                        num_poses=1,
                        min_pose_detection_confidence=self.min_detection_confidence,
                        min_pose_presence_confidence=self.min_tracking_confidence,
                        min_tracking_confidence=self.min_tracking_confidence,
                        output_segmentation_masks=False,
                    )
                    with suppress_native_output():
                        self._landmarker = mp_vision.PoseLandmarker.create_from_options(opts)
                    self._use_tasks = True
                    self._initialized = True
                    logger.info(
                        "PoseDetector (MediaPipe Tasks PoseLandmarker) initialized, "
                        "model_complexity=%d, gpu=%s",
                        self.model_complexity,
                        self._gpu_enabled,
                    )
                    return
                except Exception as e:
                    logger.error("Pose init (Tasks) failed: %s", e)
                    err_l = str(e).lower()
                    if any(
                        s in err_l
                        for s in ("gpu", "delegate", "build flag", "imageclone", "validatedgraphconfig")
                    ):
                        set_mediapipe_gpu_delegate_unavailable("pose_landmarker")
                    # Try again without GPU delegate as fallback
                    try:
                        base = mp_python.BaseOptions(model_asset_path=path)
                        opts = mp_vision.PoseLandmarkerOptions(
                            base_options=base,
                            running_mode=mp_vision.RunningMode.IMAGE,
                            num_poses=1,
                            min_pose_detection_confidence=self.min_detection_confidence,
                            min_pose_presence_confidence=self.min_tracking_confidence,
                            min_tracking_confidence=self.min_tracking_confidence,
                            output_segmentation_masks=False,
                        )
                        with suppress_native_output():
                            self._landmarker = mp_vision.PoseLandmarker.create_from_options(opts)
                        self._use_tasks = True
                        self._initialized = True
                        logger.info(
                            "PoseDetector (MediaPipe Tasks PoseLandmarker) initialized on CPU fallback, "
                            "model_complexity=%d",
                            self.model_complexity,
                        )
                        return
                    except Exception as e2:
                        logger.error("Pose init (Tasks CPU fallback) also failed: %s", e2)
                        self._init_error = (self._init_error or "") + f"; Tasks: {e}; CPU: {e2}"

        if not self._initialized:
            self._init_error = "MediaPipe pose unavailable (install mediapipe; first run downloads models)"
            logger.warning("%s", self._init_error)

    def _detect_sync(self, image_array: np.ndarray) -> PoseResult:
        if not self._initialized:
            h, w = (image_array.shape[0], image_array.shape[1]) if image_array.ndim >= 2 else (0, 0)
            return PoseResult(
                success=False,
                landmarks={},
                body_regions={},
                body_proportions={},
                image_width=w,
                image_height=h,
                confidence=0.0,
                error_message=self._init_error or "pose unavailable",
            )
        h, w = image_array.shape[:2]

        if self._use_tasks and self._landmarker is not None and mp is not None:
            try:
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_array)
                with suppress_native_output():
                    result = self._landmarker.detect(mp_image)
                return _tasks_pose_result_to_pose_result(result, w, h)
            except Exception as e:
                logger.error("Pose detection (Tasks) failed: %s", e)
                return PoseResult(
                    success=False,
                    landmarks={},
                    body_regions={},
                    body_proportions={},
                    image_width=w,
                    image_height=h,
                    confidence=0.0,
                    error_message=str(e),
                )

        if self._pose is None:
            return PoseResult(
                success=False,
                landmarks={},
                body_regions={},
                body_proportions={},
                image_width=w,
                image_height=h,
                confidence=0.0,
                error_message=self._init_error or "pose unavailable",
            )
        try:
            results = self._pose.process(image_array)
            if not results.pose_landmarks:
                return PoseResult(
                    success=False,
                    landmarks={},
                    body_regions={},
                    body_proportions={},
                    image_width=w,
                    image_height=h,
                    confidence=0.0,
                    error_message="No person detected in image",
                )
            landmarks: Dict[str, Tuple[float, float, float]] = {}
            landmark_list = results.pose_landmarks.landmark
            for i, name in enumerate(LANDMARK_NAMES):
                lm = landmark_list[i]
                landmarks[name] = (lm.x * w, lm.y * h, lm.visibility)
            confidence = sum(lm[2] for lm in landmarks.values()) / max(len(landmarks), 1)
            body_regions = self._compute_body_regions(landmarks, w, h)
            body_proportions = self._compute_body_proportions(landmarks)
            return PoseResult(
                success=True,
                landmarks=landmarks,
                body_regions=body_regions,
                body_proportions=body_proportions,
                image_width=w,
                image_height=h,
                confidence=confidence,
                torso_region=self._compute_torso_region(landmarks, w, h),
                upper_body_region=self._compute_upper_body_region(landmarks, w, h),
                lower_body_region=self._compute_lower_body_region(landmarks, w, h),
                full_body_region=self._compute_full_body_region(landmarks, w, h),
            )
        except Exception as e:
            logger.error("Pose detection failed: %s", e)
            h, w = image_array.shape[:2]
            return PoseResult(
                success=False,
                landmarks={},
                body_regions={},
                body_proportions={},
                image_width=w,
                image_height=h,
                confidence=0.0,
                error_message=str(e),
            )

    async def detect(self, image_array: np.ndarray) -> PoseResult:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._detect_sync, image_array)

    async def detect_from_pil(self, pil_image: Image.Image) -> PoseResult:
        if not PIL_AVAILABLE:
            return PoseResult(
                success=False,
                landmarks={},
                body_regions={},
                body_proportions={},
                image_width=0,
                image_height=0,
                confidence=0.0,
                error_message="PIL not available",
            )
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
        return await self.detect(np.array(pil_image))

    async def detect_from_pil_with_retry(self, pil_image: Image.Image) -> PoseResult:
        """Run MediaPipe pose with up to four attempts until confidence >= POSE_CONFIDENCE_MIN."""
        if not PIL_AVAILABLE or pil_image is None:
            return PoseResult(
                success=False,
                landmarks={},
                body_regions={},
                body_proportions={},
                image_width=0,
                image_height=0,
                confidence=0.0,
                error_message="PIL not available",
            )
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        if not pose_pose_backend_available():
            w, h = pil_image.size
            return PoseResult(
                success=False,
                landmarks={},
                body_regions={},
                body_proportions={},
                image_width=w,
                image_height=h,
                confidence=0.0,
                error_message="MediaPipe not installed",
            )

        configs: List[Tuple[float, float, int]] = [
            (0.55, 0.55, self.model_complexity),
            (0.45, 0.45, min(2, max(0, self.model_complexity))),
            (0.35, 0.35, 1),
            (0.25, 0.25, 0),
        ]

        best: Optional[PoseResult] = None
        best_conf = -1.0
        last: Optional[PoseResult] = None

        force_cpu = os.getenv("TRYON_FORCE_CPU", "").strip().lower() in ("1", "true", "yes")
        use_gpu_retry = not force_cpu
        for conf_d, conf_t, comp in configs[:_MAX_POSE_ATTEMPTS]:
            det = PoseDetector(
                min_detection_confidence=conf_d,
                min_tracking_confidence=conf_t,
                model_complexity=comp,
                use_gpu=use_gpu_retry,
            )
            if not det._initialized:
                break
            try:
                r = await det.detect_from_pil(pil_image)
            finally:
                det.close()
            last = r
            if r.success and r.confidence >= POSE_CONFIDENCE_MIN:
                return r
            if r.success and r.confidence > best_conf:
                best = r
                best_conf = r.confidence

        if best is not None:
            return best
        if last is not None:
            return last
        return await self.detect_from_pil(pil_image)

    def _compute_body_regions(
        self,
        landmarks: Dict[str, Tuple[float, float, float]],
        width: int,
        height: int,
    ) -> Dict[str, BodyRegion]:
        regions: Dict[str, BodyRegion] = {}
        nose = landmarks.get("nose", (0, 0, 0))
        left_eye = landmarks.get("left_eye", (0, 0, 0))
        right_eye = landmarks.get("right_eye", (0, 0, 0))
        if nose[2] > 0.5:
            head_width = abs(left_eye[0] - right_eye[0]) * 2.5
            head_height = head_width * 1.2
            regions["head"] = BodyRegion(
                name="head",
                x=int(nose[0] - head_width / 2),
                y=int(nose[1] - head_height / 2),
                width=int(head_width),
                height=int(head_height),
                confidence=min(left_eye[2], right_eye[2], nose[2]),
                landmarks=[(int(nose[0]), int(nose[1]))],
            )
        ls, rs = landmarks.get("left_shoulder", (0, 0, 0)), landmarks.get("right_shoulder", (0, 0, 0))
        if ls[2] > 0.5 and rs[2] > 0.5:
            sw = abs(rs[0] - ls[0])
            sy = (ls[1] + rs[1]) / 2
            regions["shoulders"] = BodyRegion(
                name="shoulders",
                x=int(min(ls[0], rs[0])),
                y=int(sy - sw * 0.15),
                width=int(sw),
                height=int(sw * 0.3),
                confidence=min(ls[2], rs[2]),
                landmarks=[(int(ls[0]), int(ls[1])), (int(rs[0]), int(rs[1]))],
            )
        return regions

    def _compute_body_proportions(self, landmarks: Dict[str, Tuple[float, float, float]]) -> Dict[str, float]:
        proportions: Dict[str, float] = {}
        ls, rs = landmarks.get("left_shoulder", (0, 0, 0)), landmarks.get("right_shoulder", (0, 0, 0))
        lh, rh = landmarks.get("left_hip", (0, 0, 0)), landmarks.get("right_hip", (0, 0, 0))
        if all(lm[2] > 0.5 for lm in [ls, rs, lh, rh]):
            proportions["shoulder_to_hip_ratio"] = abs(rs[0] - ls[0]) / (abs(rh[0] - lh[0]) + 1e-6)
        shoulder_y = (ls[1] + rs[1]) / 2
        hip_y = (lh[1] + rh[1]) / 2
        proportions["torso_length"] = abs(hip_y - shoulder_y)
        return proportions

    def _compute_torso_region(
        self,
        landmarks: Dict[str, Tuple[float, float, float]],
        width: int,
        height: int,
    ) -> Optional[BodyRegion]:
        req = ["left_shoulder", "right_shoulder", "left_hip", "right_hip"]
        if not all(k in landmarks for k in req):
            return None
        ls, rs, lh, rh = (landmarks[k] for k in req)
        if any(lm[2] < 0.3 for lm in [ls, rs, lh, rh]):
            return None
        x_min = min(ls[0], rs[0], lh[0], rh[0])
        x_max = max(ls[0], rs[0], lh[0], rh[0])
        y_min = min(ls[1], rs[1])
        y_max = max(lh[1], rh[1])
        pad_x = (x_max - x_min) * 0.1
        pad_y = (y_max - y_min) * 0.05
        return BodyRegion(
            name="torso",
            x=int(max(0, x_min - pad_x)),
            y=int(max(0, y_min - pad_y)),
            width=int(min(width, x_max - x_min + 2 * pad_x)),
            height=int(min(height, y_max - y_min + 2 * pad_y)),
            confidence=min(ls[2], rs[2], lh[2], rh[2]),
        )

    def _compute_upper_body_region(
        self,
        landmarks: Dict[str, Tuple[float, float, float]],
        width: int,
        height: int,
    ) -> Optional[BodyRegion]:
        torso = self._compute_torso_region(landmarks, width, height)
        if not torso:
            return None
        nose = landmarks.get("nose", (0, 0, 0))
        if nose[2] > 0.3:
            new_y = min(torso.y, int(nose[1] + torso.height * 0.1))
            new_h = torso.y + torso.height - new_y
            return BodyRegion(
                name="upper_body",
                x=torso.x,
                y=new_y,
                width=torso.width,
                height=int(new_h * 1.1),
                confidence=torso.confidence,
            )
        return torso

    def _compute_lower_body_region(
        self,
        landmarks: Dict[str, Tuple[float, float, float]],
        width: int,
        height: int,
    ) -> Optional[BodyRegion]:
        req = ["left_hip", "right_hip", "left_knee", "right_knee"]
        if not all(k in landmarks for k in req):
            return None
        lh, rh, lk, rk = (landmarks[k] for k in req)
        if any(lm[2] < 0.3 for lm in [lh, rh, lk, rk]):
            return None

        x_min = min(lh[0], rh[0], lk[0], rk[0])
        x_max = max(lh[0], rh[0], lk[0], rk[0])
        y_min = min(lh[1], rh[1])
        y_max = max(lk[1], rk[1])
        la, ra = landmarks.get("left_ankle", (0, 0, 0)), landmarks.get("right_ankle", (0, 0, 0))
        if la[2] > 0.3 and ra[2] > 0.3:
            y_max = max(la[1], ra[1])
        pad_x = (x_max - x_min) * 0.15
        pad_y = (y_max - y_min) * 0.05
        return BodyRegion(
            name="lower_body",
            x=int(max(0, x_min - pad_x)),
            y=int(max(0, y_min - pad_y * 0.5)),
            width=int(min(width, x_max - x_min + 2 * pad_x)),
            height=int(min(height, y_max - y_min + pad_y)),
            confidence=min(lh[2], rh[2], lk[2], rk[2]),
        )

    def _compute_full_body_region(
        self,
        landmarks: Dict[str, Tuple[float, float, float]],
        width: int,
        height: int,
    ) -> Optional[BodyRegion]:
        upper = self._compute_upper_body_region(landmarks, width, height)
        lower = self._compute_lower_body_region(landmarks, width, height)
        if not upper and not lower:
            return None
        if upper and lower:
            x = min(upper.x, lower.x)
            y = upper.y
            rw = max(upper.x + upper.width, lower.x + lower.width) - x
            rh = max(upper.y + upper.height, lower.y + lower.height) - y
            return BodyRegion(
                name="full_body",
                x=int(max(0, x)),
                y=int(max(0, y)),
                width=int(min(width, rw * 1.1)),
                height=int(min(height, rh * 1.05)),
                confidence=min(upper.confidence, lower.confidence),
            )
        return upper or lower

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "ok" if self._initialized else "degraded",
            "service": "pose-detector",
            "mediapipe_solutions_pose": MEDIAPIPE_AVAILABLE,
            "mediapipe_tasks_pose": MEDIAPIPE_TASKS_AVAILABLE,
            "initialized": self._initialized,
            "use_tasks": self._use_tasks,
            "model_complexity": self.model_complexity,
            "gpu_enabled": self._gpu_enabled,
            "error": self._init_error,
        }

    def close(self) -> None:
        if self._pose:
            self._pose.close()
            self._pose = None
        if self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None
        self._initialized = False


def _pose_result_from_landmarks_dict(
    landmarks: Dict[str, Tuple[float, float, float]],
    w: int,
    h: int,
) -> PoseResult:
    """Build PoseResult from landmark dict (shared by solutions + Tasks paths)."""
    _inst = object.__new__(PoseDetector)
    confidence = sum(lm[2] for lm in landmarks.values()) / max(len(landmarks), 1)
    body_regions = PoseDetector._compute_body_regions(_inst, landmarks, w, h)
    body_proportions = PoseDetector._compute_body_proportions(_inst, landmarks)
    return PoseResult(
        success=True,
        landmarks=landmarks,
        body_regions=body_regions,
        body_proportions=body_proportions,
        image_width=w,
        image_height=h,
        confidence=confidence,
        torso_region=PoseDetector._compute_torso_region(_inst, landmarks, w, h),
        upper_body_region=PoseDetector._compute_upper_body_region(_inst, landmarks, w, h),
        lower_body_region=PoseDetector._compute_lower_body_region(_inst, landmarks, w, h),
        full_body_region=PoseDetector._compute_full_body_region(_inst, landmarks, w, h),
    )


def _tasks_pose_result_to_pose_result(result: Any, w: int, h: int) -> PoseResult:
    """Convert MediaPipe Tasks PoseLandmarkerResult → PoseResult."""
    if result is None or not getattr(result, "pose_landmarks", None):
        return PoseResult(
            success=False,
            landmarks={},
            body_regions={},
            body_proportions={},
            image_width=w,
            image_height=h,
            confidence=0.0,
            error_message="No person detected in image",
        )
    pose_list = result.pose_landmarks[0]
    landmarks: Dict[str, Tuple[float, float, float]] = {}
    for i, name in enumerate(LANDMARK_NAMES):
        if i >= len(pose_list):
            break
        lm = pose_list[i]
        vis = float(getattr(lm, "visibility", None) or getattr(lm, "presence", None) or 0.0)
        landmarks[name] = (float(lm.x) * w, float(lm.y) * h, vis)
    return _pose_result_from_landmarks_dict(landmarks, w, h)
