import asyncio
import base64
import json
import os
import re
import sys
from typing import Tuple

import cv2
import numpy as np
import requests
from PIL import Image

from services.tryon.segmentation.body import UnifiedBodySegmenter
from services.tryon.vision.pose import PoseDetector
from services.tryon.warping.garment import GarmentProcessor, GarmentCategory
from services.tryon.warping.tps import warp_rgba_to_body_quad
from services.tryon.tryon_service import (
    _build_dst_quad,
    _enforce_min_quad_width_from_torso,
    _shoulder_width_px,
    _scale_garment_rgba_to_shoulder,
)


def _decode_data_uri(data_uri: str) -> bytes:
    m = re.match(r"^data:([^;]+);base64,(.*)$", data_uri)
    if not m:
        return base64.b64decode(data_uri)
    return base64.b64decode(m.group(2))


def _save_mask(path: str, mask_u8: np.ndarray) -> None:
    m = mask_u8
    if m.dtype != np.uint8:
        m = np.clip(m, 0, 255).astype(np.uint8)
    cv2.imwrite(path, m)


def _alpha_stats(alpha: np.ndarray, thr: int = 25) -> Tuple[int, int, float]:
    m = alpha > thr
    ys, xs = np.where(m)
    if len(ys) == 0:
        return (0, 0, 0.0)
    return int(ys.min()), int(ys.max()), float(np.mean(m))


async def main_async() -> None:
    req_path = os.path.join(os.path.dirname(__file__), "tmp_tryon_request.json")
    with open(req_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    user_b64 = data["userImageBase64"]
    garment_url = data["garmentImageUrl"]
    garment_name = data.get("garmentName", "garment")

    img_bytes = _decode_data_uri(user_b64)
    img = Image.open(os.path.join(os.path.dirname(__file__), "tmp_user_img.jpg")) if False else None
    pil_user = Image.open(__import__("io").BytesIO(img_bytes)).convert("RGB")  # type: ignore[name-defined]

    # Download garment image.
    r = requests.get(garment_url, timeout=120)
    r.raise_for_status()
    pil_garment = Image.open(__import__("io").BytesIO(r.content)).convert("RGB")  # type: ignore[name-defined]

    pose_detector = PoseDetector()
    pose = await pose_detector.detect_from_pil(pil_user)

    seg = UnifiedBodySegmenter().build(img_bytes, pose)

    gp = GarmentProcessor()
    cat = gp.detect_category(garment_name)
    # Process garment -> RGBA with alpha.
    processed = await gp.process(pil_garment, garment_name=garment_name)
    if not processed.success or processed.image is None:
        raise RuntimeError("Garment processing failed")
    g_rgba = np.array(processed.image, dtype=np.uint8)

    # Build destination quad.
    w, h = pil_user.size
    dst = _build_dst_quad(pose, cat, w, h)
    torso = seg.torso_mask
    if cat in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR, GarmentCategory.DRESSES):
        min_ratio = 1.05 if cat in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR) else 0.95
        dst = _enforce_min_quad_width_from_torso(dst, torso, min_ratio=min_ratio)

    shoulder_px = _shoulder_width_px(pose)
    g_rgba = _scale_garment_rgba_to_shoulder(g_rgba, shoulder_px, cat, torso_mask=torso)

    warped = warp_rgba_to_body_quad(g_rgba, dst, (w, h), use_strip_mesh=False)

    alpha = warped[:, :, 3]
    y0, y1, frac = _alpha_stats(alpha, thr=25)
    print("alpha stats after warp (thr=25): y_min", y0, "y_max", y1, "frac_gt", frac)

    out_dir = os.path.dirname(__file__)
    _save_mask(os.path.join(out_dir, "local_warp_alpha_after_warp.png"), alpha)
    _save_mask(os.path.join(out_dir, "local_warp_alpha_thr25.png"), (alpha > 25).astype(np.uint8) * 255)

    # Replicate tryon_service torso-only clip mask for tops.
    # (uses defaults; env override not read here)
    clip_mask = None
    if cat in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR):
        m = (torso > 80).astype(np.uint8) * 255
        m = cv2.dilate(m, np.ones((9, 9), np.uint8), iterations=1)
        clip_mask = cv2.GaussianBlur(m, (21, 21), 0)

    if clip_mask is not None:
        c = np.clip(clip_mask.astype(np.float32) / 255.0, 0.0, 1.0)
        new_a = np.clip(alpha.astype(np.float32) * c, 0.0, 255.0).astype(np.uint8)
        y0c, y1c, frac_c = _alpha_stats(new_a, thr=25)
        print("alpha stats after clip (thr=25): y_min", y0c, "y_max", y1c, "frac_gt", frac_c)
        _save_mask(os.path.join(out_dir, "local_warp_alpha_after_clip.png"), new_a)
        _save_mask(
            os.path.join(out_dir, "local_warp_clip_mask_used.png"),
            np.clip(clip_mask, 0, 255).astype(np.uint8),
        )


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

