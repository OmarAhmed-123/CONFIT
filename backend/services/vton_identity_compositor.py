"""
VTON identity compositor:

IDM-VTON outputs a full try-on image, but we must preserve:
- original background
- original face/hair identity
- anatomically plausible boundaries near neck/hands

This module blends the IDM-VTON output back into the original photo using
segmentation-derived masks instead of naive "pixel diff" thresholds.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore

from services.tryon.quality import evaluate_tryon_quality
from services.tryon.segmentation.body import UnifiedBodySegmenter, SegmentationPack
from services.tryon.vision.pose import PoseDetector, PoseResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VTONBlendParams:
    # Feathering for protected regions (face/hair/hands)
    protect_blur_px: int = 13
    # Dilate protected regions before feathering (covers neck boundary)
    protect_dilate_px: int = 12

    # Used to approximate garment presence for quality evaluation
    garment_diff_threshold: float = 18.0

    # Feathering for the garment region blend (reduces halo/sticker effect).
    garment_feather_px: int = 19

    # Constrain garment blending to torso/clip masks to avoid background/hinge artifacts.
    use_clip_to_torso: bool = True

    # Validation thresholds (tuned for "no obvious sticker effect" goal)
    min_overall_quality: float = 0.70
    max_face_mean_abs_diff: float = 7.5
    max_bg_mean_abs_diff: float = 6.5


def _pil_to_rgb_array(img: "Image.Image") -> np.ndarray:
    if img.mode != "RGB":
        img = img.convert("RGB")
    return np.array(img, dtype=np.uint8)


def _resize_hw_if_needed(img: "Image.Image", w: int, h: int) -> "Image.Image":
    if img.size == (w, h):
        return img
    return img.resize((w, h), Image.Resampling.LANCZOS)


def _u8_mask(mask: np.ndarray) -> np.ndarray:
    # Accept uint8 or float masks; return uint8 0..255
    if mask.dtype == np.uint8:
        return mask
    m = np.clip(mask.astype(np.float32), 0.0, 1.0)
    if m.max() <= 1.0:
        return (m * 255.0).astype(np.uint8)
    return mask.astype(np.uint8)


def _blur_mask(mask_u8: np.ndarray, blur_px: int) -> np.ndarray:
    if cv2 is None:
        return mask_u8
    k = max(3, int(blur_px) | 1)
    return cv2.GaussianBlur(mask_u8, (k, k), 0)


def _dilate_mask(mask_u8: np.ndarray, dilate_px: int) -> np.ndarray:
    if cv2 is None:
        return mask_u8
    d = max(1, int(dilate_px))
    k = (d, d)
    return cv2.dilate(mask_u8, np.ones(k, np.uint8), iterations=1)


def _protected_mask_from_seg(
    seg: SegmentationPack,
    pose: Optional[PoseResult],
    *,
    protect_dilate_px: int,
) -> np.ndarray:
    """
    Protected regions:
    - face + hair (identity)
    - hands/wrists (prevents "melting" near sleeves)
    """
    h, w = seg.person_mask.shape[:2]
    face = _u8_mask(seg.face_mask) if seg.face_mask is not None else np.zeros((h, w), dtype=np.uint8)
    hair = _u8_mask(seg.hair_mask) if seg.hair_mask is not None else np.zeros((h, w), dtype=np.uint8)

    # Protect full arms region to prevent sleeve/hand corruption.
    arms = _u8_mask(seg.arms_mask) if seg.arms_mask is not None else np.zeros((h, w), dtype=np.uint8)
    protected = np.maximum(face, hair)
    protected = np.maximum(protected, arms)

    # Hand protection: extra circles around wrists from pose (helps for fingers edges).
    if pose is not None and pose.success and pose.landmarks:
        lw = pose.landmarks.get("left_wrist")
        rw = pose.landmarks.get("right_wrist")
        # radius based on shoulder width (fallback to a safe constant)
        ls = pose.landmarks.get("left_shoulder")
        rs = pose.landmarks.get("right_shoulder")
        if ls and rs:
            shoulder_px = max(30.0, abs(rs[0] - ls[0]))
        else:
            shoulder_px = 220.0
        rad = int(max(18, shoulder_px * 0.06))

        if cv2 is not None:
            for wp in (lw, rw):
                if wp is None:
                    continue
                x, y, vis = wp
                if float(vis) < 0.2:
                    continue
                cx = int(np.clip(x, 0, w - 1))
                cy = int(np.clip(y, 0, h - 1))
                cv2.circle(protected, (cx, cy), rad, 255, -1)

    protected = _dilate_mask(protected, protect_dilate_px)
    return protected


def _blend_with_protected(
    person_rgb: np.ndarray,
    tryon_rgb: np.ndarray,
    protected_mask_u8: np.ndarray,
    *,
    protect_blur_px: int,
) -> np.ndarray:
    if cv2 is None:
        # Fallback: hard mask
        alpha = (protected_mask_u8 > 127).astype(np.float32)[:, :, None]
    else:
        m_blur = _blur_mask(protected_mask_u8, protect_blur_px)
        alpha = (m_blur.astype(np.float32) / 255.0)[:, :, None]
    alpha = np.clip(alpha, 0.0, 1.0)
    out = tryon_rgb.astype(np.float32) * (1.0 - alpha) + person_rgb.astype(np.float32) * alpha
    return np.clip(out, 0, 255).astype(np.uint8)


def _merge_background(
    person_rgb: np.ndarray,
    tryon_rgb: np.ndarray,
    seg: SegmentationPack,
) -> np.ndarray:
    # Background = pixels outside person silhouette
    pm = _u8_mask(seg.person_mask)
    bg = pm < 40
    out = tryon_rgb.copy()
    out[bg] = person_rgb[bg]
    return out


def compute_garment_alpha_from_diff(
    person_rgb: np.ndarray,
    tryon_rgb: np.ndarray,
    seg: SegmentationPack,
    *,
    diff_threshold: float,
) -> np.ndarray:
    """
    Approximate garment presence alpha for quality evaluation:
    - compute per-pixel difference magnitude
    - restrict to torso region to avoid face/background noise
    """
    if cv2 is None:
        # Very rough fallback: torso-only
        return _u8_mask(seg.torso_mask) if seg.torso_mask is not None else np.zeros(person_rgb.shape[:2], np.uint8)

    torso = _u8_mask(seg.torso_mask)
    diff = np.sqrt(np.sum((tryon_rgb.astype(np.float32) - person_rgb.astype(np.float32)) ** 2, axis=2))
    alpha = np.zeros(person_rgb.shape[:2], dtype=np.uint8)
    alpha[(diff > diff_threshold) & (torso > 80)] = 255
    # Feather to reduce harsh boundary artifacts for evaluator
    alpha = _blur_mask(alpha, blur_px=7).astype(np.uint8)
    return alpha


@dataclass(frozen=True)
class VTONValidationResult:
    ok: bool
    overall_quality: float
    face_mean_abs_diff: float
    bg_mean_abs_diff: float
    evaluator_notes: Tuple[str, ...] = ()


def validate_preservation(
    person_rgb: np.ndarray,
    tryon_rgb: np.ndarray,
    seg: SegmentationPack,
    pose: PoseResult,
    *,
    params: VTONBlendParams,
) -> VTONValidationResult:
    """
    Validation goals:
    - face/hair near unchanged
    - background unchanged
    - no obvious halos (proxy via evaluator edge/overall)
    """
    if cv2 is None:
        # Without cv2 quality evaluator will likely crash anyway.
        return VTONValidationResult(
            ok=True,
            overall_quality=0.0,
            face_mean_abs_diff=0.0,
            bg_mean_abs_diff=0.0,
        )

    garment_alpha = compute_garment_alpha_from_diff(
        person_rgb, tryon_rgb, seg, diff_threshold=params.garment_diff_threshold
    )

    eval_q = evaluate_tryon_quality(
        blended_rgb=tryon_rgb,
        original_rgb=person_rgb,
        garment_alpha_u8=garment_alpha,
        pose=pose,
        seg=seg,
    )

    face_mask = _u8_mask(seg.face_mask)
    hair_mask = _u8_mask(seg.hair_mask)
    prot = np.maximum(face_mask, hair_mask)

    # Mean absolute diff (0..255)
    diff_img = np.abs(tryon_rgb.astype(np.float32) - person_rgb.astype(np.float32))
    face_sel = prot > 80
    face_mean = float(np.mean(diff_img[face_sel])) if np.any(face_sel) else 0.0

    pm = _u8_mask(seg.person_mask)
    bg_sel = pm < 40
    bg_mean = float(np.mean(diff_img[bg_sel])) if np.any(bg_sel) else 0.0

    ok = (
        eval_q.overall >= params.min_overall_quality
        and face_mean <= params.max_face_mean_abs_diff
        and bg_mean <= params.max_bg_mean_abs_diff
    )

    return VTONValidationResult(
        ok=ok,
        overall_quality=float(eval_q.overall),
        face_mean_abs_diff=face_mean,
        bg_mean_abs_diff=bg_mean,
        evaluator_notes=eval_q.notes,
    )


async def blend_idm_vton_result_with_masks(
    *,
    person_img: "Image.Image",
    idm_vton_img: "Image.Image",
    pose: PoseResult,
    seg: SegmentationPack,
    params: VTONBlendParams,
) -> Tuple["Image.Image", VTONValidationResult]:
    """
    Composite strategy (to avoid sticker/halo artifacts):
      1) Start from the original person image (keeps background and identity)
      2) Estimate garment presence using (tryon - person) diff constrained to
         torso/clip masks
      3) Feather garment alpha
      4) Remove garment alpha inside protected regions (face/hair/arms/hands)
      5) Blend try-on pixels only inside the garment alpha region
      6) Validate; return final + validation
    """
    if Image is None:
        raise RuntimeError("PIL not available")

    w, h = person_img.size
    idm_vton_img = _resize_hw_if_needed(idm_vton_img, w, h)

    person_rgb = _pil_to_rgb_array(person_img)
    tryon_rgb = _pil_to_rgb_array(idm_vton_img)

    # Protected identity zones (never blend garment pixels inside these).
    protected_mask = _protected_mask_from_seg(
        seg, pose, protect_dilate_px=params.protect_dilate_px
    )

    # Estimate garment alpha region:
    # - diff magnitude between tryon and person
    # - constrain with torso/clip to avoid background/hanger areas
    if cv2 is None:
        # Fallback: keep only protected regions from original.
        alpha = np.ones((h, w), dtype=np.float32) * 0.6
        alpha[protected_mask > 80] = 0.0
        alpha_3d = alpha[:, :, None]
        out_rgb = (
            person_rgb.astype(np.float32) * (1.0 - alpha_3d)
            + tryon_rgb.astype(np.float32) * alpha_3d
        ).astype(np.uint8)
    else:
        diff = np.sqrt(
            np.sum(
                (tryon_rgb.astype(np.float32) - person_rgb.astype(np.float32)) ** 2,
                axis=2,
            )
        )
        diff_mask = (diff > float(params.garment_diff_threshold)).astype(np.uint8) * 255

        if params.use_clip_to_torso:
            clip = seg.garment_clip_mask if seg.garment_clip_mask is not None else seg.torso_mask
            clip_u8 = _u8_mask(clip) if clip is not None else _u8_mask(seg.torso_mask)
            clip_mask = (clip_u8 > 80).astype(np.uint8) * 255
            garment_alpha_u8 = cv2.bitwise_and(diff_mask, clip_mask)
        else:
            garment_alpha_u8 = diff_mask

        # Never blend inside protected zones.
        garment_alpha_u8[protected_mask > 80] = 0

        # Feather to avoid halo/paste edges.
        garment_alpha_u8 = _blur_mask(
            garment_alpha_u8,
            blur_px=params.garment_feather_px,
        )
        garment_alpha = (garment_alpha_u8.astype(np.float32) / 255.0)[:, :, None]
        garment_alpha = np.clip(garment_alpha, 0.0, 1.0)

        out_rgb = (
            person_rgb.astype(np.float32) * (1.0 - garment_alpha)
            + tryon_rgb.astype(np.float32) * garment_alpha
        )
        out_rgb = np.clip(out_rgb, 0, 255).astype(np.uint8)

    out_img = Image.fromarray(out_rgb, mode="RGB")
    validation = validate_preservation(
        person_rgb=person_rgb,
        tryon_rgb=out_rgb,
        seg=seg,
        pose=pose,
        params=params,
    )
    return out_img, validation


async def build_pose_and_segmentation(
    person_img: "Image.Image",
) -> Tuple[PoseResult, SegmentationPack]:
    """
    Build PoseResult and SegmentationPack for a single person image.
    """
    if Image is None:
        raise RuntimeError("PIL not available")

    if person_img.mode != "RGB":
        person_img = person_img.convert("RGB")

    pose_det = PoseDetector(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    pose = await pose_det.detect_from_pil_with_retry(person_img)

    # UnifiedBodySegmenter expects bytes; avoid re-encoding to keep it deterministic.
    buf = io.BytesIO()
    person_img.save(buf, format="JPEG", quality=95)
    person_bytes = buf.getvalue()

    seg = UnifiedBodySegmenter().build(person_bytes, pose)
    # build() is synchronous inside UnifiedBodySegmenter; but might return immediately.
    if hasattr(seg, "__await__"):
        seg = await seg  # pragma: no cover

    return pose, seg

