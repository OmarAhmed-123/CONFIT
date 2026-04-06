"""Pose-aligned perspective warp (quad-to-quad) for garment RGBA.

Includes a multi-strip warp that approximates thin-plate / curvature by mapping each
horizontal band to its corresponding slice of the destination quadrilateral.
"""

from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np

_DEFAULT_STRIPS = 20


def warp_rgba_strip_mesh(
    rgba: np.ndarray,
    dst_quad: np.ndarray,
    out_wh: Tuple[int, int],
    strips: int = _DEFAULT_STRIPS,
) -> np.ndarray:
    """
    Approximate torso curvature: each horizontal strip of the garment maps to the quad
    slice between interpolated left/right edges (piecewise-linear TPS-like behavior).
    Composites with alpha-over (top strips last so shoulders sit above hem).
    """
    gh, gw = rgba.shape[:2]
    ow, oh = out_wh
    strips = max(8, min(48, int(strips)))
    dst_quad = dst_quad.astype(np.float32)
    canvas = np.zeros((oh, ow, 4), dtype=np.float32)

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
        le0 = (1 - v0) * dst_quad[0] + v0 * dst_quad[3]
        ri0 = (1 - v0) * dst_quad[1] + v0 * dst_quad[2]
        le1 = (1 - v1) * dst_quad[0] + v1 * dst_quad[3]
        ri1 = (1 - v1) * dst_quad[1] + v1 * dst_quad[2]
        dst_pts = np.array([le0, ri0, ri1, le1], dtype=np.float32)
        m = cv2.getPerspectiveTransform(src, dst_pts)
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


def warp_rgba_to_quad(
    rgba: np.ndarray,
    dst_quad: np.ndarray,
    out_wh: Tuple[int, int],
) -> np.ndarray:
    """
    Map garment corners (0,0)-(w,0)-(w,h)-(0,h) to dst_quad (TL,TR,BR,BL) in output space.

    Args:
        rgba: HxWx4 uint8 garment
        dst_quad: 4x2 float32 pixel coords on output canvas
        out_wh: (width, height) of output canvas
    """
    gh, gw = rgba.shape[:2]
    src = np.array(
        [[0, 0], [gw - 1, 0], [gw - 1, gh - 1], [0, gh - 1]],
        dtype=np.float32,
    )
    M = cv2.getPerspectiveTransform(src, dst_quad.astype(np.float32))
    ow, oh = out_wh
    return cv2.warpPerspective(
        rgba,
        M,
        (ow, oh),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )


def warp_rgba_to_body_quad(
    rgba: np.ndarray,
    dst_quad: np.ndarray,
    out_wh: Tuple[int, int],
    use_strip_mesh: bool = False,
) -> np.ndarray:
    """Single entry: perspective warp (default) or strip mesh (TPS-like, set use_strip_mesh=True)."""
    if use_strip_mesh:
        return warp_rgba_strip_mesh(rgba, dst_quad, out_wh)
    return warp_rgba_to_quad(rgba, dst_quad, out_wh)

