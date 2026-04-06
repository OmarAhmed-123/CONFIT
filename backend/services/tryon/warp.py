from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np

from services.tryon.anchoring import BodyAnchors


@dataclass
class DepthMatch:
    perspective_strength: float
    vertical_compression: float
    rotation_angle_deg: float


def estimate_depth_match(anchors: BodyAnchors, image_height: int) -> DepthMatch:
    # Estimate pseudo depth from body proportions: farther subject -> smaller torso in frame.
    frame_ratio = anchors.torso_height / max(float(image_height), 1.0)
    depth = float(np.clip(1.0 - frame_ratio * 1.7, 0.0, 1.0))
    perspective_strength = float(np.clip(0.03 + depth * 0.15, 0.03, 0.18))
    vertical_compression = float(np.clip(1.0 - depth * 0.12, 0.84, 1.04))
    rotation_angle_deg = float(np.degrees(anchors.shoulder_angle_rad))
    return DepthMatch(
        perspective_strength=perspective_strength,
        vertical_compression=vertical_compression,
        rotation_angle_deg=rotation_angle_deg,
    )


def compute_intelligent_scale(
    garment_rgba: np.ndarray,
    torso_width: float,
    scale_min: float = 0.55,
    scale_max: float = 2.8,
) -> Tuple[np.ndarray, float]:
    alpha = garment_rgba[:, :, 3]
    coords = cv2.findNonZero((alpha > 25).astype(np.uint8))
    if coords is None:
        return garment_rgba, 1.0
    x, y, w, h = cv2.boundingRect(coords)
    crop = garment_rgba[y : y + h, x : x + w].copy()
    ref_w = max(float(w), 1.0)
    scale_factor = float(np.clip(torso_width / ref_w, scale_min, scale_max))
    out_w = max(1, int(round(w * scale_factor)))
    out_h = max(1, int(round(h * scale_factor)))
    scaled = cv2.resize(crop, (out_w, out_h), interpolation=cv2.INTER_LANCZOS4)
    return scaled, scale_factor


def apply_pose_aware_mesh_warp(
    rgba: np.ndarray,
    dst_quad: np.ndarray,
    out_wh: Tuple[int, int],
    depth: Optional[DepthMatch] = None,
    strips: int = 24,
) -> np.ndarray:
    gh, gw = rgba.shape[:2]
    ow, oh = out_wh
    strips = max(10, min(48, int(strips)))
    canvas = np.zeros((oh, ow, 4), dtype=np.float32)
    q = dst_quad.astype(np.float32).copy()

    if depth is not None:
        span_y = float(np.mean(q[2:, 1]) - np.mean(q[:2, 1]))
        q[2, 1] = q[0, 1] + span_y * depth.vertical_compression
        q[3, 1] = q[1, 1] + span_y * depth.vertical_compression
        # Slight perspective taper at lower torso.
        taper = depth.perspective_strength * float(np.linalg.norm(q[1] - q[0]))
        q[2, 0] -= taper
        q[3, 0] += taper

    for i in range(strips - 1, -1, -1):
        v0 = i / strips
        v1 = (i + 1) / strips
        y0 = int(round(v0 * (gh - 1)))
        y1 = int(round(v1 * (gh - 1)))
        if y1 <= y0:
            y1 = min(gh - 1, y0 + 1)
        strip = rgba[y0:y1, :, :]
        sh = strip.shape[0]
        src = np.array([[0, 0], [gw - 1, 0], [gw - 1, sh - 1], [0, sh - 1]], dtype=np.float32)
        le0 = (1 - v0) * q[0] + v0 * q[3]
        ri0 = (1 - v0) * q[1] + v0 * q[2]
        le1 = (1 - v1) * q[0] + v1 * q[3]
        ri1 = (1 - v1) * q[1] + v1 * q[2]
        # Vertical deformation: slight inward pull around waist line.
        mid = 0.5
        bend = np.sin((v0 + v1) * 0.5 * np.pi) * 0.04
        le0[0] += (ri0[0] - le0[0]) * bend * (1.0 - abs(v0 - mid))
        ri0[0] -= (ri0[0] - le0[0]) * bend * (1.0 - abs(v0 - mid))
        le1[0] += (ri1[0] - le1[0]) * bend * (1.0 - abs(v1 - mid))
        ri1[0] -= (ri1[0] - le1[0]) * bend * (1.0 - abs(v1 - mid))

        dst = np.array([le0, ri0, ri1, le1], dtype=np.float32)
        m = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(
            strip,
            m,
            (ow, oh),
            flags=cv2.INTER_LANCZOS4,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0),
        ).astype(np.float32)
        sr = warped[:, :, :3] / 255.0
        sa = np.clip(warped[:, :, 3:4] / 255.0, 0.0, 1.0)
        dr = canvas[:, :, :3] / 255.0
        da = np.clip(canvas[:, :, 3:4] / 255.0, 0.0, 1.0)
        a_out = sa + da * (1.0 - sa)
        rgb_out = (sr * sa + dr * da * (1.0 - sa)) / np.clip(a_out, 1e-4, 1.0)
        canvas[:, :, :3] = rgb_out * 255.0
        canvas[:, :, 3] = np.clip(a_out[:, :, 0] * 255.0, 0.0, 255.0)

    return np.clip(canvas, 0, 255).astype(np.uint8)
