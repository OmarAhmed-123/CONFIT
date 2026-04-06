"""Self-healing checks for classical try-on."""

from __future__ import annotations

from typing import Tuple

import numpy as np

from services.tryon.cv_compat import erode_binary_mask, laplacian_variance_mask


class TryOnSelfCheck:
    """Floating garment detection, edge harshness, and alignment helpers."""

    @staticmethod
    def alpha_mass_outside_mask(alpha: np.ndarray, mask: np.ndarray) -> float:
        """Fraction of alpha energy outside mask (high => floating card / misaligned quad)."""
        if alpha.size == 0 or mask.shape[:2] != alpha.shape[:2]:
            return 0.0
        m = (mask > 80).astype(np.float32)
        a = np.clip(alpha.astype(np.float32) / 255.0, 0.0, 1.0)
        outside = float(np.sum(a * (1.0 - m)))
        tot = float(np.sum(a)) + 1e-6
        return outside / tot

    @staticmethod
    def garment_centroid(alpha: np.ndarray) -> Tuple[float, float]:
        m = alpha > 40
        ys, xs = np.where(m)
        if len(xs) == 0:
            return -1.0, -1.0
        return float(np.mean(xs)), float(np.mean(ys))

    @staticmethod
    def center_inside_mask(
        cx: float,
        cy: float,
        mask: np.ndarray,
        erode_px: int = 12,
    ) -> bool:
        if cx < 0 or cy < 0:
            return False
        if mask.size == 0:
            return True
        m = (mask > 80).astype(np.uint8) * 255
        if erode_px > 0:
            m = erode_binary_mask(m, erode_px)
        xi, yi = int(cx), int(cy)
        if yi < 0 or xi < 0 or yi >= m.shape[0] or xi >= m.shape[1]:
            return False
        return m[yi, xi] > 0

    @staticmethod
    def edge_sharpness_harsh(mask: np.ndarray, threshold: float = 650.0) -> bool:
        """True if edges look too sharp (needs more feather)."""
        if mask.size == 0:
            return False
        v = laplacian_variance_mask(mask)
        return v > threshold

    @staticmethod
    def nudge_quad_toward_torso(
        quad: np.ndarray,
        torso_cx: float,
        torso_cy: float,
        step: float = 0.02,
    ) -> np.ndarray:
        """Shift quad corners slightly toward torso centroid (fraction of image diagonal)."""
        out = quad.copy().astype(np.float32)
        center = np.mean(out, axis=0)
        tgt = np.array([torso_cx, torso_cy], dtype=np.float32)
        delta = (tgt - center) * step
        out += delta
        return out
