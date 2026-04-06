"""
Deterministic input normalization for classical try-on (no crop; preserves dimensions).

CLAHE on luminance + light denoising helps GrabCut / edge stability on noisy backgrounds
without changing resolution or aspect ratio.
"""

from __future__ import annotations

import os

import cv2
import numpy as np
from PIL import Image


def preprocess_person_for_tryon(pil: Image.Image) -> Image.Image:
    """Full-frame exposure/contrast help + mild noise reduction."""
    if os.getenv("TRYON_INPUT_PREPROCESS", "1").lower() in ("0", "false", "no"):
        return pil
    arr = np.array(pil.convert("RGB"))
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    l_ch, a_ch, b_ch = cv2.split(lab)
    clip = float(os.getenv("TRYON_PREPROCESS_CLAHE_CLIP", "2.0"))
    grid = int(os.getenv("TRYON_PREPROCESS_CLAHE_GRID", "8"))
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(max(2, grid), max(2, grid)))
    l2 = clahe.apply(l_ch)
    merged = cv2.merge([l2, a_ch, b_ch])
    rgb = cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)
    h, w = rgb.shape[:2]
    # fastNlMeans scales with resolution; cap working size for speed
    max_side = int(os.getenv("TRYON_PREPROCESS_DENOISE_MAX_SIDE", "640"))
    if max(h, w) > max_side:
        r = max_side / float(max(h, w))
        small = cv2.resize(rgb, (int(w * r), int(h * r)), interpolation=cv2.INTER_AREA)
        den = cv2.fastNlMeansDenoisingColored(small, None, 3, 3, 7, 21)
        rgb = cv2.resize(den, (w, h), interpolation=cv2.INTER_LINEAR)
    else:
        rgb = cv2.fastNlMeansDenoisingColored(rgb, None, 3, 3, 7, 21)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
