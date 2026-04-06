"""
Build Body DNA profile from pose (first analysis) and reconstruct PoseResult for reuse.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from services.tryon.vision.pose import LANDMARK_NAMES, PoseResult

logger = logging.getLogger(__name__)

BODY_PROFILE_VERSION = 1


def _dist(a: tuple, b: tuple) -> float:
    return float(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5)


def build_body_profile(pose: PoseResult) -> Dict[str, Any]:
    """
    Extract measurements-only body DNA (no image pixels).
    Landmarks stored normalized [0,1] for scaling to any working resolution.
    """
    w, h = max(1, pose.image_width), max(1, pose.image_height)
    lm = pose.landmarks or {}
    joints_norm: Dict[str, Dict[str, float]] = {}
    for name in LANDMARK_NAMES:
        if name not in lm:
            continue
        px, py, vis = lm[name]
        joints_norm[name] = {
            "x": float(px) / w,
            "y": float(py) / h,
            "v": float(vis),
        }

    ls = lm.get("left_shoulder")
    rs = lm.get("right_shoulder")
    lh = lm.get("left_hip")
    rh = lm.get("right_hip")
    le = lm.get("left_elbow")
    re = lm.get("right_elbow")
    lw = lm.get("left_wrist")
    rw = lm.get("right_wrist")

    shoulder_width_px = abs(rs[0] - ls[0]) if ls and rs else 0.0
    hip_width_px = abs(rh[0] - lh[0]) if lh and rh else 0.0
    shoulder_y = (ls[1] + rs[1]) / 2 if ls and rs else h * 0.25
    hip_y = (lh[1] + rh[1]) / 2 if lh and rh else h * 0.55
    torso_length_px = abs(hip_y - shoulder_y)

    arm_l = _dist(ls, le) + _dist(le, lw) if ls and le and lw else 0.0
    arm_r = _dist(rs, re) + _dist(re, rw) if rs and re and rw else 0.0
    arm_length_px = (arm_l + arm_r) / 2.0 if arm_l and arm_r else max(arm_l, arm_r)

    measurements = {
        "shoulder_width_norm": float(shoulder_width_px / w),
        "torso_length_norm": float(torso_length_px / h),
        "hip_width_norm": float(hip_width_px / w),
        "arm_length_norm": float(arm_length_px / h),
        "hip_ratio": float(shoulder_width_px / (hip_width_px + 1e-6)),
    }

    # Lightweight parametric mesh: ratios only (privacy-safe).
    mesh = {
        "shoulder_to_image_width": float(shoulder_width_px / w),
        "torso_to_image_height": float(torso_length_px / h),
        "limb_to_torso": float(arm_length_px / (torso_length_px + 1e-6)),
        "shoulder_to_hip_width_ratio": measurements["hip_ratio"],
    }

    proportions = dict(pose.body_proportions or {})
    return {
        "version": BODY_PROFILE_VERSION,
        "image_ref_width": w,
        "image_ref_height": h,
        "measurements": measurements,
        "mesh": mesh,
        "landmarks_norm": joints_norm,
        "body_proportions": proportions,
        "pose_confidence": float(pose.confidence),
    }


def pose_from_body_profile(profile: Dict[str, Any], width: int, height: int) -> PoseResult:
    """Rehydrate PoseResult from stored normalized landmarks (scaled to current image size)."""
    w, h = max(1, width), max(1, height)
    raw = profile.get("landmarks_norm") or {}
    landmarks: Dict[str, tuple] = {}
    for name in LANDMARK_NAMES:
        entry = raw.get(name)
        if not entry:
            continue
        x = float(entry.get("x", 0)) * w
        y = float(entry.get("y", 0)) * h
        v = float(entry.get("v", entry.get("visibility", 0.7)))
        landmarks[name] = (x, y, v)

    # Ensure core keys exist for quad builder (silhouette-like fill)
    if "left_shoulder" not in landmarks or "right_shoulder" not in landmarks:
        logger.warning("Body DNA profile missing shoulders; pose reuse may be weak")
        return PoseResult(
            success=False,
            landmarks={},
            body_regions={},
            body_proportions={},
            image_width=w,
            image_height=h,
            confidence=0.0,
            error_message="Incomplete Body DNA landmarks",
        )

    for name in LANDMARK_NAMES:
        if name not in landmarks:
            # Low-visibility placeholder — downstream uses sparse keys
            landmarks[name] = (w * 0.5, h * 0.5, 0.05)

    conf = float(profile.get("pose_confidence", 0.75))
    proportions = dict(profile.get("body_proportions") or {})

    return PoseResult(
        success=True,
        landmarks=landmarks,
        body_regions={},
        body_proportions=proportions,
        image_width=w,
        image_height=h,
        confidence=min(1.0, max(0.5, conf)),
        torso_region=None,
        upper_body_region=None,
        lower_body_region=None,
        full_body_region=None,
    )


def body_profile_to_public_json(profile: Dict[str, Any]) -> str:
    """JSON suitable for clients (no encryption)."""
    return json.dumps(profile, indent=2)
