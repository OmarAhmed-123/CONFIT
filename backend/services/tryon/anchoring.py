from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Tuple

import numpy as np

from services.tryon.pose import PoseMap
from services.tryon.warping.garment import GarmentCategory

if TYPE_CHECKING:
    from services.tryon.vision.pose import PoseResult


def estimate_body_angle_deg(pose) -> float:
    """Rough in-plane rotation from shoulder line (degrees).
    
    Moved from tps.py for better module organization.
    Accepts either PoseResult or PoseMap.
    """
    from services.tryon.vision.pose import PoseResult
    
    if isinstance(pose, PoseResult):
        if not pose.success:
            return 0.0
        ls = pose.landmarks.get("left_shoulder")
        rs = pose.landmarks.get("right_shoulder")
        if not ls or not rs or ls[2] < 0.2 or rs[2] < 0.2:
            return 0.0
        dx = rs[0] - ls[0]
        dy = rs[1] - ls[1]
    elif isinstance(pose, PoseMap):
        ls = pose.left_shoulder
        rs = pose.right_shoulder
        dx = rs[0] - ls[0]
        dy = rs[1] - ls[1]
    else:
        return 0.0
    return float(np.degrees(np.arctan2(dy, dx)))


Point = Tuple[float, float]


@dataclass
class BodyAnchors:
    neck_anchor: Point
    torso_width: float
    torso_height: float
    shoulder_angle_rad: float
    shoulder_mid: Point
    hip_mid: Point


def _dist(a: Point, b: Point) -> float:
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


def compute_body_anchors(pose_map: PoseMap) -> BodyAnchors:
    ls = (pose_map.left_shoulder[0], pose_map.left_shoulder[1])
    rs = (pose_map.right_shoulder[0], pose_map.right_shoulder[1])
    lh = (pose_map.left_hip[0], pose_map.left_hip[1])
    rh = (pose_map.right_hip[0], pose_map.right_hip[1])
    neck = (pose_map.neck[0], pose_map.neck[1])

    shoulder_mid = ((ls[0] + rs[0]) * 0.5, (ls[1] + rs[1]) * 0.5)
    hip_mid = ((lh[0] + rh[0]) * 0.5, (lh[1] + rh[1]) * 0.5)
    torso_width = max(30.0, _dist(ls, rs))
    torso_height = max(40.0, _dist(neck, hip_mid))
    shoulder_angle_rad = float(np.arctan2(rs[1] - ls[1], rs[0] - ls[0]))
    return BodyAnchors(
        neck_anchor=neck,
        torso_width=torso_width,
        torso_height=torso_height,
        shoulder_angle_rad=shoulder_angle_rad,
        shoulder_mid=shoulder_mid,
        hip_mid=hip_mid,
    )


def build_anchored_dst_quad(
    anchors: BodyAnchors,
    category: GarmentCategory,
    image_width: int,
    image_height: int,
) -> np.ndarray:
    width_mult = 1.08
    height_mult = 1.0
    if category in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR):
        height_mult = 1.12 if category == GarmentCategory.OUTERWEAR else 0.98
    elif category in (GarmentCategory.DRESSES, GarmentCategory.FULL_BODY):
        height_mult = 1.75
        width_mult = 1.05
    elif category == GarmentCategory.BOTTOMS:
        height_mult = 1.25
        width_mult = 0.95

    half_w = anchors.torso_width * width_mult * 0.5
    top_y = anchors.neck_anchor[1]
    bottom_y = anchors.neck_anchor[1] + anchors.torso_height * height_mult

    # Create quad in anchor local space then rotate by shoulder tilt.
    local = np.array(
        [
            [-half_w, 0.0],
            [half_w, 0.0],
            [half_w * 0.95, bottom_y - top_y],
            [-half_w * 0.95, bottom_y - top_y],
        ],
        dtype=np.float32,
    )
    ca, sa = np.cos(anchors.shoulder_angle_rad), np.sin(anchors.shoulder_angle_rad)
    rot = np.array([[ca, -sa], [sa, ca]], dtype=np.float32)
    quad = (local @ rot.T) + np.array([anchors.neck_anchor[0], anchors.neck_anchor[1]], dtype=np.float32)
    quad[:, 0] = np.clip(quad[:, 0], 1, image_width - 2)
    quad[:, 1] = np.clip(quad[:, 1], 1, image_height - 2)
    return quad.astype(np.float32)
