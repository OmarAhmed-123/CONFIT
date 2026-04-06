"""
OpenCV 4.1x compatibility helpers.

Some builds (e.g. Windows + AVX2) throw:
  error: (-213) Unsupported combination of source format (=5 CV_32F)
  and destination format (=6 CV_64F) in getLinearFilter
when blurring float32/float64 arrays. Prefer uint8 for separable filters
or normalize to uint8, blur, then map back.
"""

from __future__ import annotations

import cv2
import numpy as np


def gaussian_blur_u8(channel: np.ndarray, ksize: tuple[int, int], sigma: float = 0) -> np.ndarray:
    """Blur a single channel; input clipped to uint8 (0–255)."""
    u8 = np.clip(channel, 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(u8, ksize, sigma)


def gaussian_blur_alpha_feather(alpha: np.ndarray, ksize: tuple[int, int]) -> np.ndarray:
    """Feather RGBA alpha channel; avoids float32 GaussianBlur AVX2 issues."""
    return gaussian_blur_u8(alpha, ksize, 0)


def erode_binary_mask(mask_u8: np.ndarray, erode_px: int) -> np.ndarray:
    """Erode a 0/255 uint8 mask (kernel side length = 2*erode_px+1)."""
    if erode_px <= 0:
        return mask_u8
    k = np.ones((erode_px * 2 + 1, erode_px * 2 + 1), np.uint8)
    return cv2.erode(mask_u8, k, iterations=1)


def laplacian_variance_mask(mask: np.ndarray) -> float:
    """Edge sharpness proxy; uint8 in, float32 Laplacian (avoids CV_32F/CV_64F AVX2 issues on some builds)."""
    if mask.size == 0:
        return 0.0
    u8 = np.clip(mask, 0, 255).astype(np.uint8)
    try:
        lap = cv2.Laplacian(u8, cv2.CV_32F)
        return float(lap.var())
    except cv2.error:
        # Pure NumPy fallback if OpenCV filter path fails on this platform
        f = u8.astype(np.float64)
        lx = np.diff(f, axis=1, prepend=f[:, :1])
        ly = np.diff(f, axis=0, prepend=f[:1, :])
        return float(np.var(lx) + np.var(ly))


def refine_mask_float01(mask: np.ndarray, blur_radius: int) -> np.ndarray:
    """Smooth mask edges; returns values in [0, 1] (same intent as old float blur + normalize)."""
    m = np.asarray(mask, dtype=np.float64)
    if m.size == 0:
        return m
    mn, mx = float(m.min()), float(m.max())
    if mx - mn < 1e-8:
        return np.zeros_like(m)
    n = (m - mn) / (mx - mn)
    u8 = np.clip(n * 255.0, 0, 255).astype(np.uint8)
    k = max(1, blur_radius * 2 + 1) | 1
    b = cv2.GaussianBlur(u8, (k, k), 0).astype(np.float64) / 255.0
    return b
