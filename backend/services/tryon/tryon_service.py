"""
Single classical virtual try-on pipeline: pose → segmentation → warp → blend → self-check.
Used by MCP advanced/local backends and thin service wrappers.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

import os

from services.tryon.blending.compositor import BlendResult, ImageBlender, composite_tryon_professional
from services.tryon.image_preprocess import preprocess_person_for_tryon
from services.tryon.quality import evaluate_tryon_quality
from services.tryon.segmentation.body import UnifiedBodySegmenter, create_clothing_mask
from services.tryon.validation import TryOnSelfCheck
from services.tryon.vision.pose import (
    POSE_CONFIDENCE_MIN,
    PoseResult,
    pose_to_skeleton_json,
    synthetic_pose_from_person_mask,
    validate_pose_for_tryon,
)
from services.tryon.pose import PoseService
from services.tryon.anchoring import build_anchored_dst_quad, compute_body_anchors
from services.tryon.compositor import extract_torso_lighting_stats, match_garment_to_torso_lighting
from services.tryon.warp import apply_pose_aware_mesh_warp, estimate_depth_match
from services.tryon.alignment_config import alignment_identity
from services.tryon.stable_alignment import (
    apply_stable_alignment,
    build_alignment_diagnostics_payload,
    compute_alignment,
    detect_body_orientation,
    normalize_garment_orientation,
    generate_face_exclusion_mask,
    harden_segmentation,
    compute_torso_anchors,
    build_constrained_dst_quad,
    blend_inside_torso_only,
    check_quality_and_enhance,
    enforce_realism,
    MIN_ORIENTATION_CONFIDENCE,
    MIN_POSE_CONFIDENCE,
    maybe_save_tryon_debug_bundle,
    save_pose_overlay,
)
from services.tryon.warping.garment import (
    GarmentCategory,
    GarmentProcessor,
    align_garment_to_body,
    compute_garment_target_region,
    match_lighting_warped_garment,
)
from services.tryon.cv_compat import gaussian_blur_alpha_feather
from services.tryon.warping.tps import warp_rgba_to_body_quad
from services.tryon.physics import apply_fabric_physics_to_warp
from services.tryon.physics.material_engine import MaterialProperties, to_fabric_type_json
from services.tryon.body_dna import (
    BodyDNAStore,
    build_body_profile,
    merge_style_memory,
    pose_from_body_profile,
    predict_fit_preview,
)
from utils.image_utils import (
    GarmentImageDownloadError,
    base64_to_pil,
    download_image_to_temp,
    pil_to_base64,
    resize_image,
)

logger = logging.getLogger(__name__)


async def _download_garment_with_fallback(primary_url: str, suffix: str) -> str:
    """Download garment image; optional TRYON_FALLBACK_GARMENT_IMAGE_URL if the catalog URL is dead."""
    try:
        return await download_image_to_temp(primary_url, suffix=suffix)
    except GarmentImageDownloadError as e:
        fb = os.getenv("TRYON_FALLBACK_GARMENT_IMAGE_URL", "").strip()
        if fb and fb.rstrip("/") != primary_url.rstrip("/"):
            logger.warning(
                "Garment URL failed (%s); retrying with TRYON_FALLBACK_GARMENT_IMAGE_URL",
                e,
            )
            return await download_image_to_temp(fb, suffix=suffix)
        raise


def _fabric_physics_env_enabled() -> bool:
    """Default off on CPU-only hosts (saves minutes per request); set TRYON_FABRIC_PHYSICS=1 to force on."""
    v = os.getenv("TRYON_FABRIC_PHYSICS", "").strip().lower()
    if v in ("0", "false", "no"):
        return False
    if v in ("1", "true", "yes"):
        return True
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _coerce_body_profile(opts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    bp = opts.get("body_profile")
    if isinstance(bp, str):
        try:
            return json.loads(bp)
        except Exception:
            return None
    if isinstance(bp, dict):
        return bp
    return None


def _effective_min_output_quality(opts: Dict[str, Any], quality_threshold: float) -> float:
    """Reject catastrophic outputs (glitches / failed warp) instead of returning HTTP 200.
    
    Production-grade minimum: 0.60+ to prevent "sticker" effects from passing.
    """
    if opts.get("allow_low_quality_output"):
        return 0.0
    v = opts.get("min_output_quality")
    if v is not None:
        return float(v)
    env = os.getenv("TRYON_MIN_OUTPUT_QUALITY")
    if env:
        return float(env)
    # Raised floor: at least 60% quality required for production output
    return max(0.60, min(0.70, float(quality_threshold) - 0.08))


def _validate_tryon_image_dims(width: int, height: int) -> Optional[str]:
    """Reject unusable sizes before heavy CV work."""
    for d in (width, height):
        if d < 200 or d > 4096:
            return f"Image must be between 200 and 4096 px on each side (got {width}x{height})"
    return None


def _affine_inpaint_pipeline_enabled(category: GarmentCategory) -> bool:
    """Default-on affine + inpaint compositor; set TRYON_LEGACY_MESH_PIPELINE=1 for quad/mesh path."""
    if os.getenv("TRYON_LEGACY_MESH_PIPELINE", "").strip().lower() in ("1", "true", "yes"):
        return False
    return category in (
        GarmentCategory.TOPS,
        GarmentCategory.OUTERWEAR,
        GarmentCategory.DRESSES,
        GarmentCategory.FULL_BODY,
        GarmentCategory.BOTTOMS,
    )


def _category_from_options(gc: Optional[str], garment_name: str, processor: GarmentProcessor) -> GarmentCategory:
    if gc:
        g = gc.strip().lower()
        mapping = {
            "tops": GarmentCategory.TOPS,
            "bottoms": GarmentCategory.BOTTOMS,
            "dresses": GarmentCategory.DRESSES,
            "outerwear": GarmentCategory.OUTERWEAR,
            "shoes": GarmentCategory.SHOES,
            "accessories": GarmentCategory.ACCESSORIES,
            "bags": GarmentCategory.BAGS,
        }
        if g in mapping:
            return mapping[g]
    return processor.detect_category(garment_name)


def _shoulder_width_px(pose: PoseResult) -> float:
    if not pose.success:
        return 100.0
    ls = pose.landmarks.get("left_shoulder")
    rs = pose.landmarks.get("right_shoulder")
    if not ls or not rs:
        return 100.0
    return max(40.0, abs(rs[0] - ls[0]))


def _apply_shoulder_tilt_to_quad(quad: np.ndarray, pose: PoseResult) -> np.ndarray:
    """Rotate quad around its centroid to match shoulder-line tilt."""
    ang = _shoulder_line_angle_rad(pose)
    if abs(ang) <= 0.02:
        return quad.astype(np.float32)
    cx = float(np.mean(quad[:, 0]))
    cy = float(np.mean(quad[:, 1]))
    ca, sa = np.cos(ang), np.sin(ang)
    r = quad - np.array([cx, cy], dtype=np.float32)
    rot = np.stack([r[:, 0] * ca - r[:, 1] * sa, r[:, 0] * sa + r[:, 1] * ca], axis=1)
    return (rot + np.array([cx, cy], dtype=np.float32)).astype(np.float32)


def _shoulder_line_angle_rad(pose: PoseResult) -> float:
    """In-plane rotation from left shoulder → right shoulder."""
    if not pose.success or not pose.landmarks:
        return 0.0
    ls = pose.landmarks.get("left_shoulder")
    rs = pose.landmarks.get("right_shoulder")
    if not ls or not rs or ls[2] < 0.1 or rs[2] < 0.1:
        return 0.0
    # MediaPipe left/right are anatomical, which can appear swapped on camera views.
    # Sort by x so tilt stays near horizontal instead of ~180° flip.
    p0, p1 = (ls, rs) if ls[0] <= rs[0] else (rs, ls)
    return float(np.arctan2(p1[1] - p0[1], p1[0] - p0[0]))


def _build_dst_quad(
    pose: PoseResult,
    category: GarmentCategory,
    w: int,
    h: int,
) -> np.ndarray:
    """Return 4x2 float32 quad TL,TR,BR,BL in pixel coords."""
    pad = 0.08
    if pose.success and pose.landmarks:
        ls = pose.landmarks.get("left_shoulder", (w * 0.35, h * 0.25, 1))
        rs = pose.landmarks.get("right_shoulder", (w * 0.65, h * 0.25, 1))
        lh = pose.landmarks.get("left_hip", (w * 0.38, h * 0.55, 1))
        rh = pose.landmarks.get("right_hip", (w * 0.62, h * 0.55, 1))
        sw = abs(rs[0] - ls[0]) + 1e-6
        if category == GarmentCategory.BOTTOMS:
            lk = pose.landmarks.get("left_knee", (lh[0], lh[1] + sw, 1))
            rk = pose.landmarks.get("right_knee", (rh[0], rh[1] + sw, 1))
            return np.array(
                [
                    [lh[0] - sw * pad, lh[1]],
                    [rh[0] + sw * pad, rh[1]],
                    [rk[0] + sw * 0.05, rk[1] + sw * 0.1],
                    [lk[0] - sw * 0.05, lk[1] + sw * 0.1],
                ],
                dtype=np.float32,
            )
        if category in (GarmentCategory.DRESSES, GarmentCategory.FULL_BODY):
            la = pose.landmarks.get("left_ankle", (lh[0], h * 0.92, 0.3))
            ra = pose.landmarks.get("right_ankle", (rh[0], h * 0.92, 0.3))
            quad = np.array(
                [
                    [ls[0] - sw * pad, ls[1]],
                    [rs[0] + sw * pad, rs[1]],
                    [ra[0] + sw * 0.05, min(h - 2, ra[1])],
                    [la[0] - sw * 0.05, min(h - 2, la[1])],
                ],
                dtype=np.float32,
            )
            return _apply_shoulder_tilt_to_quad(quad, pose)
        quad = np.array(
            [
                [ls[0] - sw * pad, ls[1]],
                [rs[0] + sw * pad, rs[1]],
                [rh[0] + sw * 0.04, rh[1]],
                [lh[0] - sw * 0.04, lh[1]],
            ],
            dtype=np.float32,
        )
        # For tops/outerwear, lift the quad bottom a bit.
        # Hip landmarks can land slightly low on some photos, causing the
        # warped shirt hem to extend too far downward and "leak" into the
        # background/ground.
        if category in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR):
            top_y = float((ls[1] + rs[1]) * 0.5)
            bot_y = float((lh[1] + rh[1]) * 0.5)
            span = bot_y - top_y
            if span > 1.0:
                lift = span * (0.08 if category == GarmentCategory.TOPS else 0.05)
                quad[2, 1] -= lift
                quad[3, 1] -= lift
        return _apply_shoulder_tilt_to_quad(quad, pose)
    return np.array(
        [
            [w * 0.28, h * 0.22],
            [w * 0.72, h * 0.22],
            [w * 0.68, h * 0.58],
            [w * 0.32, h * 0.58],
        ],
        dtype=np.float32,
    )


def _scale_garment_rgba_to_shoulder(
    rgba: np.ndarray,
    shoulder_px: float,
    category: GarmentCategory,
    torso_mask: Optional[np.ndarray] = None,
    torso_height: Optional[float] = None,
) -> np.ndarray:
    """Scale garment to body proportions using shoulder width and torso height.
    
    Uses body-anchored fitting instead of fixed multipliers:
    - Tops/Outerwear: width = shoulder * 1.15, height from torso
    - Dresses/Full body: width = shoulder * 1.08, extended height
    - Bottoms: width = hip estimate, height from torso
    """
    alpha = rgba[:, :, 3]
    coords = cv2.findNonZero((alpha > 25).astype(np.uint8))
    if coords is None:
        return rgba
    x, y, cw, ch = cv2.boundingRect(coords)
    crop = rgba[y : y + ch, x : x + cw].copy()
    
    # Body-anchored scaling: adapt to actual body proportions
    if category in (GarmentCategory.DRESSES, GarmentCategory.FULL_BODY):
        width_mult = 1.08  # Slightly wider for dresses
        height_mult = 1.85 if torso_height else 1.5
    elif category == GarmentCategory.BOTTOMS:
        width_mult = 0.95  # Hips are narrower than shoulders
        height_mult = 1.25
    elif category == GarmentCategory.OUTERWEAR:
        width_mult = 1.12  # Outerwear slightly oversized
        height_mult = 1.15 if torso_height else 1.0
    else:  # TOPS
        width_mult = 1.15  # Cover shoulders comfortably
        height_mult = 1.0 if torso_height else 0.95
    
    target_w = max(48, int(shoulder_px * width_mult))
    # Guard against tiny shoulder estimates on full-frame photos where the person is far away.
    if torso_mask is not None and torso_mask.shape[:2] != (0, 0):
        t_coords = cv2.findNonZero((torso_mask > 80).astype(np.uint8))
        if t_coords is not None:
            _, _, tw, th = cv2.boundingRect(t_coords)
            # Use torso width as minimum bound for garment width
            torso_width_mult = 0.92 if category in (GarmentCategory.DRESSES, GarmentCategory.FULL_BODY) else 0.88
            target_w = max(target_w, int(max(24, tw) * torso_width_mult))
            # Use torso height to inform garment height scaling
            if torso_height is None:
                torso_height = float(th)
    
    scale = target_w / max(cw, 1)
    nh, nw = max(1, int(ch * scale)), max(1, int(cw * scale))
    
    # Additional height adjustment based on torso proportions
    if torso_height and torso_height > 0 and category in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR):
        # Ensure garment height covers torso appropriately
        target_h = max(nh, int(torso_height * height_mult))
        if target_h > nh:
            h_scale = target_h / max(nh, 1)
            nw = max(1, int(nw * min(1.15, h_scale)))  # Slight width increase to maintain proportions
            nh = target_h
    
    return cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_LANCZOS4)


def _torso_centroid(torso_mask: np.ndarray) -> Tuple[float, float]:
    m = (torso_mask > 80).astype(np.uint8)
    M = cv2.moments(m)
    if M["m00"] < 1e-6:
        return 0.0, 0.0
    return M["m10"] / M["m00"], M["m01"] / M["m00"]


def _shoulder_line_clip_mask(pose: PoseResult, w: int, h: int) -> np.ndarray:
    """
    Soft mask around the shoulder line (anatomical L/R). Used when torso-only clips would
    otherwise zero warped garment alpha at the shoulders / upper chest (common on
    front-facing photos where the shirt quad spans wider than the pose torso polygon).
    """
    out = np.zeros((h, w), dtype=np.uint8)
    if not pose.success or not pose.landmarks:
        return out
    ls = pose.landmarks.get("left_shoulder")
    rs = pose.landmarks.get("right_shoulder")
    if not ls or not rs or ls[2] < 0.1 or rs[2] < 0.1:
        return out
    sw = max(40.0, float(abs(rs[0] - ls[0])))
    cx = int((ls[0] + rs[0]) * 0.5)
    cy = int((ls[1] + rs[1]) * 0.5)
    ax = int(max(48.0, sw * 0.98))
    ay = int(max(32.0, sw * 0.42))
    cv2.ellipse(out, (cx, cy), (ax, ay), 0, 0, 360, 255, -1)
    out = cv2.dilate(out, np.ones((31, 31), np.uint8), iterations=1)
    return cv2.GaussianBlur(out, (47, 47), 0)


def _enforce_min_quad_width_from_torso(
    quad: np.ndarray,
    torso_mask: np.ndarray,
    min_ratio: float = 0.82,
) -> np.ndarray:
    """
    Widen destination quad when pose shoulders are underestimated.
    Keeps garment from collapsing to a vertical strip on far-camera photos.
    """
    coords = cv2.findNonZero((torso_mask > 80).astype(np.uint8))
    if coords is None or quad.shape != (4, 2):
        return quad
    _, _, tw, _ = cv2.boundingRect(coords)
    if tw < 8:
        return quad
    q = quad.astype(np.float32).copy()
    top_w = float(np.linalg.norm(q[1] - q[0]))
    bot_w = float(np.linalg.norm(q[2] - q[3]))
    cur_w = max(top_w, bot_w, 1.0)
    target_w = max(cur_w, float(tw) * float(min_ratio))
    if target_w <= cur_w * 1.04:
        return q
    cx = float(np.mean(q[:, 0]))
    sx = target_w / cur_w
    q[:, 0] = (q[:, 0] - cx) * sx + cx
    return q


def _anchored_quad_looks_degenerate(
    quad: np.ndarray,
    torso_mask: np.ndarray,
    category: GarmentCategory,
) -> bool:
    """
    Detect anchor quads that are clearly inconsistent with torso segmentation.
    Typical failure: tiny/raised quad near neck due unstable shoulder/hip landmarks.
    """
    if quad.shape != (4, 2):
        return True
    coords = cv2.findNonZero((torso_mask > 80).astype(np.uint8))
    if coords is None:
        return False
    tx, ty, tw, th = cv2.boundingRect(coords)
    if tw < 8 or th < 8:
        return False
    q = quad.astype(np.float32)
    qx0, qx1 = float(np.min(q[:, 0])), float(np.max(q[:, 0]))
    qy0, qy1 = float(np.min(q[:, 1])), float(np.max(q[:, 1]))
    q_w = max(1.0, qx1 - qx0)
    q_h = max(1.0, qy1 - qy0)
    # Expect substantial overlap with torso region and non-tiny size.
    ix0, iy0 = max(qx0, tx), max(qy0, ty)
    ix1, iy1 = min(qx1, tx + tw), min(qy1, ty + th)
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    torso_area = float(tw * th)
    overlap_ratio = inter / max(1.0, torso_area)
    too_narrow = q_w < tw * 0.55
    too_short = q_h < th * 0.38
    too_high = qy1 < (ty + th * (0.40 if category in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR) else 0.52))
    weak_overlap = overlap_ratio < 0.12
    return bool(too_narrow or too_short or too_high or weak_overlap)


def _build_torso_guided_dst_quad(
    torso_mask: np.ndarray,
    category: GarmentCategory,
    image_width: int,
    image_height: int,
    pose: Optional[PoseResult] = None,
) -> np.ndarray:
    """Fallback destination quad from torso bbox when pose-map anchors are unstable."""
    coords = cv2.findNonZero((torso_mask > 80).astype(np.uint8))
    if coords is None:
        return np.array(
            [[image_width * 0.30, image_height * 0.18], [image_width * 0.70, image_height * 0.18],
             [image_width * 0.67, image_height * 0.62], [image_width * 0.33, image_height * 0.62]],
            dtype=np.float32,
        )
    tx, ty, tw, th = cv2.boundingRect(coords)
    cx = float(tx + tw * 0.5)
    if category in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR):
        top = float(ty - th * 0.06)
        bot = float(ty + th * (0.62 if category == GarmentCategory.OUTERWEAR else 0.56))
        half = float(tw * (0.62 if category == GarmentCategory.OUTERWEAR else 0.58))
    elif category in (GarmentCategory.DRESSES, GarmentCategory.FULL_BODY):
        top = float(ty - th * 0.04)
        bot = float(ty + th * 1.05)
        half = float(tw * 0.56)
    elif category == GarmentCategory.BOTTOMS:
        top = float(ty + th * 0.38)
        bot = float(ty + th * 1.15)
        half = float(tw * 0.50)
    else:
        top = float(ty)
        bot = float(ty + th * 0.72)
        half = float(tw * 0.56)
    quad = np.array(
        [
            [cx - half, top],
            [cx + half, top],
            [cx + half * 0.94, bot],
            [cx - half * 0.94, bot],
        ],
        dtype=np.float32,
    )
    quad[:, 0] = np.clip(quad[:, 0], 1, image_width - 2)
    quad[:, 1] = np.clip(quad[:, 1], 1, image_height - 2)
    if pose is not None:
        quad = _apply_shoulder_tilt_to_quad(quad, pose)
    return quad.astype(np.float32)


def _feather_alpha(rgba: np.ndarray, radius: int = 21) -> np.ndarray:
    out = rgba.copy()
    k = max(3, (radius | 1))
    out[:, :, 3] = gaussian_blur_alpha_feather(out[:, :, 3], (k, k))
    return out


def _apply_garment_clip_mask(warped_rgba: np.ndarray, clip_u8: Optional[np.ndarray]) -> np.ndarray:
    """Multiply warped alpha by body clip mask (torso ∪ upper silhouette). Removes floating catalog panels."""
    if clip_u8 is None or clip_u8.shape[:2] != warped_rgba.shape[:2]:
        return warped_rgba
    c = np.clip(clip_u8.astype(np.float32) / 255.0, 0.0, 1.0)
    out = warped_rgba.astype(np.float32)
    old_a = np.clip(out[:, :, 3], 1e-3, 255.0)
    new_a = out[:, :, 3] * c
    fac = np.clip(new_a / old_a, 0.0, 1.0)
    out[:, :, :3] *= fac[:, :, np.newaxis]
    out[:, :, 3] = new_a
    return np.clip(out, 0, 255).astype(np.uint8)


def _cleanup_alpha_speckles(
    warped_rgba: np.ndarray,
    *,
    clip_u8: Optional[np.ndarray] = None,
    alpha_thr: int = 25,
    min_component_ratio: float = 0.02,
) -> np.ndarray:
    """
    Remove tiny detached alpha components that create "sparkle specks" after warping.

    This is intentionally conservative: keep only components that are large enough
    compared to the maximum connected component area.
    """
    if warped_rgba.size == 0:
        return warped_rgba
    alpha = warped_rgba[:, :, 3]
    fg = (alpha > alpha_thr).astype(np.uint8)
    if fg.max() == 0:
        return warped_rgba

    num, labels, stats, _centroids = cv2.connectedComponentsWithStats(fg, connectivity=8)
    if num <= 1:
        return warped_rgba

    areas = stats[1:, cv2.CC_STAT_AREA].astype(np.float32)
    max_area = float(np.max(areas)) if areas.size else 0.0
    if max_area <= 0:
        return warped_rgba

    keep_ids = set()
    for i, a in enumerate(areas, start=1):
        if float(a) < max_area * float(min_component_ratio):
            continue
        if clip_u8 is not None and clip_u8.shape[:2] == warped_rgba.shape[:2]:
            # Keep only if the component centroid overlaps the clip.
            x = int(stats[i, cv2.CC_STAT_LEFT] + stats[i, cv2.CC_STAT_WIDTH] / 2)
            y = int(stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT] / 2)
            x = max(0, min(x, clip_u8.shape[1] - 1))
            y = max(0, min(y, clip_u8.shape[0] - 1))
            if clip_u8[y, x] <= 0:
                continue
        keep_ids.add(i)

    if not keep_ids:
        # Fallback: keep the largest component to avoid removing the garment entirely.
        keep_ids = {int(np.argmax(areas) + 1)}

    mask_keep = np.isin(labels, list(keep_ids))
    out = warped_rgba.copy()
    out[:, :, 3] = (out[:, :, 3].astype(np.uint16) * mask_keep.astype(np.uint16)).astype(np.uint8)
    return out


@dataclass
class ClassicalTryOnResult:
    success: bool
    result_image: Optional[str] = None
    quality_score: float = 0.0
    pose_detected: bool = False
    garment_category: str = "tops"
    warnings: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    failure_kind: Optional[str] = None
    processing_time_ms: float = 0.0
    pose_keypoints_json: Optional[str] = None
    # Body DNA (measurements-only; no raw image stored server-side in profile)
    body_dna_pose_reused: bool = False
    fit_preview_json: Optional[str] = None
    body_profile_json: Optional[str] = None
    quality_diagnostics_json: Optional[str] = None
    fabric_intelligence_json: Optional[str] = None
    pose_map_json: Optional[str] = None
    alignment_diagnostics_json: Optional[str] = None


class TryOnService:
    """Unified classical (non-diffusion) try-on."""

    def __init__(self) -> None:
        self._pose = PoseService()
        self._segmenter = UnifiedBodySegmenter()
        self._garment = GarmentProcessor()
        self._blender = ImageBlender()

    async def process_classical(
        self,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str = "garment",
        options: Optional[Dict[str, Any]] = None,
    ) -> ClassicalTryOnResult:
        opts = options or {}
        opts = {**alignment_identity(), **opts}
        t0 = time.time()
        warnings: List[str] = []
        garment_path: Optional[str] = None
        request_id = str(opts.get("request_id") or f"tryon_{int(time.time() * 1000)}")
        last_orientation = None
        garment_corrections_tracked: List[str] = []
        normalization_ran = False

        try:
            person_pil = base64_to_pil(user_image_base64)
            if person_pil is None:
                return ClassicalTryOnResult(success=False, error_message="Invalid person image")

            original_size = person_pil.size
            if os.getenv("TRYON_PRESERVE_UPLOAD_RESOLUTION", "1").strip().lower() in (
                "1",
                "true",
                "yes",
            ):
                person_work = person_pil.convert("RGB")
            else:
                mw = int(os.getenv("TRYON_PERSON_MAX_SIDE", "1024"))
                person_work = resize_image(person_pil.convert("RGB"), max_width=mw, max_height=mw)
            if not opts.get("disable_input_preprocess"):
                person_work = preprocess_person_for_tryon(person_work)
            person_bytes = self._pil_to_bytes_jpeg(person_work)
            w, h = person_work.size
            dim_err = _validate_tryon_image_dims(w, h)
            if dim_err:
                return ClassicalTryOnResult(
                    success=False,
                    error_message=dim_err,
                    failure_kind="invalid_image_size",
                    processing_time_ms=(time.time() - t0) * 1000,
                )

            category = _category_from_options(opts.get("garment_category"), garment_name, self._garment)
            use_affine_pipeline = _affine_inpaint_pipeline_enabled(category)
            try:
                garment_path = await _download_garment_with_fallback(garment_image_url, suffix=".png")
            except GarmentImageDownloadError as e:
                return ClassicalTryOnResult(
                    success=False,
                    error_message=str(e),
                    failure_kind="garment_fetch",
                    garment_category=category.value,
                    processing_time_ms=(time.time() - t0) * 1000,
                )

            logger.info("tryon stage: pose_detection")
            user_id = opts.get("user_id") or opts.get("body_dna_user_id")
            body_profile = _coerce_body_profile(opts)
            store = BodyDNAStore()
            if opts.get("use_stored_body_dna") and user_id and body_profile is None:
                body_profile = store.load(user_id)

            skip_pose = bool(opts.get("skip_pose_detection")) or (
                bool(opts.get("use_stored_body_dna")) and body_profile is not None
            )
            body_dna_pose_reused = False
            if skip_pose and body_profile:
                cached_pose = pose_from_body_profile(body_profile, w, h)
                if cached_pose.success:
                    pose_raw = cached_pose
                    body_dna_pose_reused = True
                    mediapipe_pose_ok = False
                    warnings.append("Pose reused from Body DNA (pose detection skipped)")
                else:
                    pose_raw = await self._pose.detect(person_work)
                    mediapipe_pose_ok = bool(
                        pose_raw.success and pose_raw.confidence >= POSE_CONFIDENCE_MIN
                    )
                    warnings.append("Body DNA landmarks incomplete; ran pose detection")
            else:
                pose_raw = await self._pose.detect(person_work)
                mediapipe_pose_ok = bool(
                    pose_raw.success and pose_raw.confidence >= POSE_CONFIDENCE_MIN
                )
            pose = pose_raw
            pose_map = self._pose.build_pose_map(pose, w, h)
            pose_map_json = pose_map.to_json() if pose_map is not None else None
            pose_map_output_path = opts.get("pose_map_output_path")
            if pose_map_json and isinstance(pose_map_output_path, str) and pose_map_output_path.strip():
                try:
                    with open(pose_map_output_path, "w", encoding="utf-8") as f:
                        f.write(pose_map_json)
                except Exception as ex:
                    warnings.append(f"pose_map.json write skipped: {ex}")

            g_pil = Image.open(garment_path).convert("RGBA")

            logger.info("tryon stage: garment_preprocess")
            processed = await self._garment.process(g_pil, garment_name)
            if not processed.success or processed.image is None:
                return ClassicalTryOnResult(
                    success=False,
                    error_message=processed.error_message or "Garment processing failed",
                    processing_time_ms=(time.time() - t0) * 1000,
                )

            # ====================================================================
            # CONFIT STABLE GARMENT ALIGNMENT MODE - ORIENTATION NORMALIZATION
            # Fix for inverted/flipped t-shirts: normalize garment orientation BEFORE warp
            # ====================================================================
            stable_alignment_enabled = os.getenv("TRYON_STABLE_ALIGNMENT", "1").lower() in ("1", "true", "yes")
            g_rgba = np.array(processed.image, dtype=np.uint8)
            g_rgba_before_align = g_rgba.copy()
            g_rgba_after_align = g_rgba.copy()

            if stable_alignment_enabled and pose.success and pose.landmarks and not use_affine_pipeline:
                orientation = detect_body_orientation(pose.landmarks, w, h)
                last_orientation = orientation
                if (
                    orientation.confidence >= MIN_ORIENTATION_CONFIDENCE
                    and pose.confidence >= MIN_POSE_CONFIDENCE
                ):
                    g_rgba, corrections = normalize_garment_orientation(
                        g_rgba,
                        orientation,
                        category.value,
                        pose_landmarks=pose.landmarks,
                        pose_confidence=pose.confidence,
                    )
                    g_rgba_after_align = g_rgba.copy()
                    garment_corrections_tracked = list(corrections)
                    normalization_ran = True
                    if corrections:
                        logger.info("Stable alignment: garment corrections applied: %s", corrections)
                        warnings.extend([f"Garment orientation: {c}" for c in corrections])
                else:
                    if orientation.confidence < MIN_ORIENTATION_CONFIDENCE:
                        warnings.append(
                            f"Orientation confidence low ({orientation.confidence:.2f}); using default orientation"
                        )
                        logger.warning("Stable alignment: low orientation confidence %.2f", orientation.confidence)
                    if pose.confidence < MIN_POSE_CONFIDENCE:
                        warnings.append(
                            f"Pose confidence low ({pose.confidence:.2f}); skipped garment orientation normalization"
                        )
                        logger.warning("Stable alignment: low pose confidence %.2f", pose.confidence)

            logger.info("tryon stage: human_segmentation")
            seg = self._segmenter.build(person_bytes, pose)
            torso = seg.torso_mask

            if (not pose.success or pose.confidence < POSE_CONFIDENCE_MIN) or np.max(torso) < 40:
                if body_dna_pose_reused:
                    warnings.append(
                        "Thin segmentation with Body DNA pose; consider a clearer full-body photo if alignment looks off"
                    )
                else:
                    logger.info("tryon stage: pose_fallback_silhouette")
                    syn = synthetic_pose_from_person_mask(seg.person_mask, w, h)
                    if syn.success:
                        pose = syn
                        # Reuse person mask — avoids a second expensive GrabCut pass (~30–60s on CPU).
                        seg = self._segmenter.build(
                            person_bytes,
                            pose,
                            reuse_person_mask_u8=seg.person_mask,
                        )
                        torso = seg.torso_mask
                        warnings.append(
                            "Body alignment from silhouette; ensure mediapipe is installed so pose uses Tasks API or solutions"
                        )

            pose_ok = pose.success and bool(pose.landmarks)
            fit_preview_json: Optional[str] = None
            prof_for_fit = body_profile if body_profile else (build_body_profile(pose) if pose.success else None)
            if prof_for_fit:
                fit_preview_json = json.dumps(
                    predict_fit_preview(
                        prof_for_fit,
                        category.value,
                        str(opts.get("fit_type", "regular")),
                    )
                )
            if np.max(torso) < 10:
                warnings.append("Weak torso segmentation")

            person_rgb = np.array(person_work.convert("RGB"))
            material = None
            fabric_intelligence_json = None

            if use_affine_pipeline and pose_ok:
                dim_e2 = _validate_tryon_image_dims(w, h)
                if dim_e2:
                    return ClassicalTryOnResult(
                        success=False,
                        error_message=dim_e2,
                        failure_kind="invalid_image_size",
                        garment_category=category.value,
                        processing_time_ms=(time.time() - t0) * 1000,
                    )
                pv_ok, pv_err = validate_pose_for_tryon(pose)
                if not pv_ok:
                    return ClassicalTryOnResult(
                        success=False,
                        error_message=pv_err or "Pose is not clear enough for try-on",
                        failure_kind="pose_validation",
                        garment_category=category.value,
                        processing_time_ms=(time.time() - t0) * 1000,
                    )
                logger.info("tryon stage: affine_inpaint_pipeline")
                if pose.landmarks:
                    last_orientation = detect_body_orientation(pose.landmarks, w, h)
                normalization_ran = True
                g_af = g_rgba.copy()
                g_af, garment_corrections_tracked = compute_alignment(
                    pose.landmarks, g_af, pose_confidence=pose.confidence
                )
                g_rgba_after_align = g_af.copy()
                if garment_corrections_tracked:
                    logger.info("Affine alignment corrections: %s", garment_corrections_tracked)
                    warnings.extend([f"Garment orientation: {c}" for c in garment_corrections_tracked])
                torso_height_val = None
                torso_width_val = None
                if np.max(torso) > 80:
                    t_coords = cv2.findNonZero((torso > 80).astype(np.uint8))
                    if t_coords is not None:
                        _, _, tw, th = cv2.boundingRect(t_coords)
                        torso_width_val = float(tw)
                        torso_height_val = float(th)
                shoulder_px_af = _shoulder_width_px(pose)
                if torso_width_val is not None and category in (
                    GarmentCategory.TOPS,
                    GarmentCategory.OUTERWEAR,
                    GarmentCategory.DRESSES,
                ):
                    min_shoulder_from_torso = torso_width_val * (
                        0.88 if category in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR) else 0.82
                    )
                    shoulder_px_af = max(float(shoulder_px_af), float(min_shoulder_from_torso))
                g_af = _scale_garment_rgba_to_shoulder(g_af, shoulder_px_af, category, torso, torso_height_val)
                fabric_intel_af = opts.get("fabric_intelligence", True)
                if os.getenv("TRYON_FABRIC_INTELLIGENCE", "1").lower() in ("0", "false", "no"):
                    fabric_intel_af = False
                if fabric_intel_af:
                    material = self._garment.analyze_fabric_material(g_af, garment_name, use_cache=True)
                    fabric_intelligence_json = to_fabric_type_json(material)
                    warnings.append(
                        f"Fabric intelligence: {material.fabric.value} "
                        f"(conf={material.classification_confidence:.2f})"
                    )
                bbox_af = compute_garment_target_region(pose.landmarks, category.value, (h, w))
                warped_af = align_garment_to_body(g_af, pose.landmarks, (w, h), category.value)
                warped_af = match_lighting_warped_garment(person_rgb, warped_af, bbox_af)
                clothing_u8 = create_clothing_mask(seg.person_mask, pose, category.value)
                out_np_af = composite_tryon_professional(person_rgb, warped_af, clothing_u8, pose)
                out_work = Image.fromarray(out_np_af, "RGB")
                w_try = warped_af
                blend_res = BlendResult(
                    success=True,
                    image=out_work,
                    mask=warped_af[:, :, 3].copy(),
                    blend_quality_score=0.72,
                    lighting_match_score=0.72,
                    edge_quality_score=0.72,
                )
                seg_work = seg
                thresh = float(opts.get("quality_threshold", 0.72))
                min_out = _effective_min_output_quality(opts, thresh)
                recovery_max = 0
                q_eval = evaluate_tryon_quality(
                    out_np_af,
                    person_rgb,
                    blend_res.mask if blend_res.mask is not None else np.zeros((h, w), np.uint8),
                    pose,
                    seg_work,
                )
                q = q_eval.overall
                retries_used = 0
                logger.info("tryon stage: affine_inpaint_done quality=%.3f", q)

                if os.getenv("DEBUG_TRYON", "").strip() == "1":
                    from pathlib import Path as _Path

                    from services.tryon.stable_alignment import save_image_rgba_or_rgb as _save_rgba

                    root = _Path(os.getenv("DEBUG_TRYON_DIR", "debug_output"))
                    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in request_id)[:128]
                    d = root / safe_id
                    d.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(d / "01_user_input.png"), cv2.cvtColor(person_rgb, cv2.COLOR_RGB2BGR))
                    save_pose_overlay(person_rgb, pose.landmarks, d / "02_pose_overlay.png")
                    _save_rgba(g_af, d / "03_garment_aligned.png")
                    cv2.imwrite(str(d / "04_person_mask.png"), seg.person_mask.astype(np.uint8))
                    cv2.imwrite(str(d / "05_clothing_mask.png"), clothing_u8)
                    _save_rgba(warped_af, d / "06_warped_garment.png")
                    _save_rgba(warped_af, d / "07_lighting_matched.png")
                    cv2.imwrite(
                        str(d / "08_final_result.png"),
                        cv2.cvtColor(out_np_af, cv2.COLOR_RGB2BGR),
                    )
            else:
                if use_affine_pipeline and stable_alignment_enabled and pose.success and pose.landmarks:
                    orientation = detect_body_orientation(pose.landmarks, w, h)
                    last_orientation = orientation
                    if (
                        orientation.confidence >= MIN_ORIENTATION_CONFIDENCE
                        and pose.confidence >= MIN_POSE_CONFIDENCE
                    ):
                        g_rgba, corrections = normalize_garment_orientation(
                            g_rgba,
                            orientation,
                            category.value,
                            pose_landmarks=pose.landmarks,
                            pose_confidence=pose.confidence,
                        )
                        g_rgba_after_align = g_rgba.copy()
                        garment_corrections_tracked = list(corrections)
                        normalization_ran = True
                        if corrections:
                            logger.info("Stable alignment (deferred for mesh path): %s", corrections)
                            warnings.extend([f"Garment orientation: {c}" for c in corrections])
                logger.info("tryon stage: body_alignment_quad")
                if pose_map is not None:
                    anchors = compute_body_anchors(pose_map)
                    dst = build_anchored_dst_quad(anchors, category, w, h)
                    shoulder_px = anchors.torso_width
                else:
                    dst = _build_dst_quad(pose, category, w, h)
                    shoulder_px = _shoulder_width_px(pose)
                preview_mode = bool(opts.get("preview_mode"))
                if category in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR, GarmentCategory.DRESSES):
                    min_ratio = 1.05 if category in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR) else 0.95
                    if preview_mode and category in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR):
                        # Preview-only UX: slightly widen garment placement to avoid undersized center "sticker".
                        min_ratio = max(min_ratio, 1.22)
                    dst = _enforce_min_quad_width_from_torso(dst, torso, min_ratio=min_ratio)
                if pose_map is not None and _anchored_quad_looks_degenerate(dst, torso, category):
                    warnings.append("Pose-map anchors unstable; using torso-guided placement fallback")
                    dst = _build_torso_guided_dst_quad(torso, category, w, h, pose=pose)
                # g_rgba already set above with orientation normalization
                # Compute torso stats for body-anchored scaling
                torso_height_val: Optional[float] = None
                torso_width_val: Optional[float] = None
                if np.max(torso) > 80:
                    t_coords = cv2.findNonZero((torso > 80).astype(np.uint8))
                    if t_coords is not None:
                        _, _, tw, th = cv2.boundingRect(t_coords)
                        torso_width_val = float(tw)
                        torso_height_val = float(th)

                # Guard against underestimated shoulders (common on distant / low-contrast upper body photos):
                # if shoulders are too small, warp degenerates to a tiny collar-like patch near neck.
                if torso_width_val is not None and category in (
                    GarmentCategory.TOPS,
                    GarmentCategory.OUTERWEAR,
                    GarmentCategory.DRESSES,
                ):
                    min_shoulder_from_torso = torso_width_val * (
                        0.88 if category in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR) else 0.82
                    )
                    shoulder_px = max(float(shoulder_px), float(min_shoulder_from_torso))

                # Use category + torso-aware scaling for all paths (pose_map and fallback).
                # Previous pose_map-only scaling used shoulder width alone and could collapse garments.
                g_rgba = _scale_garment_rgba_to_shoulder(g_rgba, shoulder_px, category, torso, torso_height_val)
                lighting_stats = extract_torso_lighting_stats(np.array(person_work.convert("RGB")), torso)
                g_rgba = match_garment_to_torso_lighting(g_rgba, lighting_stats)

                fabric_intel = opts.get("fabric_intelligence", True)
                if os.getenv("TRYON_FABRIC_INTELLIGENCE", "1").lower() in ("0", "false", "no"):
                    fabric_intel = False
                material: Optional[MaterialProperties] = None
                fabric_intelligence_json: Optional[str] = None
                if fabric_intel:
                    material = self._garment.analyze_fabric_material(g_rgba, garment_name, use_cache=True)
                    fabric_intelligence_json = to_fabric_type_json(material)
                    warnings.append(
                        f"Fabric intelligence: {material.fabric.value} "
                        f"(conf={material.classification_confidence:.2f})"
                    )

                tcx, tcy = _torso_centroid(torso)
                max_retries = max(0, min(3, int(os.getenv("TRYON_WARP_ALIGN_MAX_RETRIES", "0"))))
                attempt = 0
                warped = None
                alpha_for_check = None

                clip_mask = getattr(seg, "garment_clip_mask", None)
                if clip_mask is None or clip_mask.shape[:2] != (h, w):
                    clip_mask = np.maximum(torso, (seg.person_mask > 80).astype(np.uint8) * 255)
                    clip_mask = cv2.GaussianBlur(clip_mask, (41, 41), 0)
                wide_garment_clip = np.clip(clip_mask, 0, 255).astype(np.uint8)
                # For tops/outerwear: start from a torso-tight mask to reduce "floating panel"
                # artifacts, then UNION with the segmenter's wide clip + shoulder band.
                # Torso-only clipping was erasing almost all warped alpha (shirt only visible as a
                # thin line at the neck) because the warp maps the garment to shoulders, which
                # often lie outside a tight torso polygon.
                if category in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR):
                    m = (torso > 80).astype(np.uint8) * 255
                    torso_clip_dilate = int(os.getenv("TRYON_TORSO_CLIP_DILATE_PX", "40"))
                    torso_clip_blur = int(os.getenv("TRYON_TORSO_CLIP_BLUR_PX", "35"))
                    torso_clip_dilate = max(1, torso_clip_dilate)
                    torso_clip_blur = max(3, torso_clip_blur)
                    k_d = (torso_clip_dilate, torso_clip_dilate)
                    k_b = (torso_clip_blur, torso_clip_blur)
                    m = cv2.dilate(m, np.ones(k_d, np.uint8), iterations=1)
                    torso_tight = cv2.GaussianBlur(m, k_b, 0)
                    shoulder_sup = _shoulder_line_clip_mask(pose, w, h)
                    clip_mask = np.maximum(np.maximum(torso_tight, wide_garment_clip), shoulder_sup)
                    clip_mask = cv2.GaussianBlur(clip_mask, (5, 5), 0)

                while attempt <= max_retries:
                    # Strip mesh (TPS-like) warp follows body curvature for realistic fitting.
                    # Set TRYON_USE_STRIP_MESH=0 to fallback to simple perspective warp.
                    use_mesh = os.getenv("TRYON_USE_STRIP_MESH", "1").lower() in ("1", "true", "yes")
                    logger.info("tryon stage: garment_warp_%s", "mesh" if use_mesh else "perspective")
                    if pose_map is not None:
                        anchors = compute_body_anchors(pose_map)
                        depth = estimate_depth_match(anchors, h)
                        warped = apply_pose_aware_mesh_warp(g_rgba, dst, (w, h), depth=depth)
                    else:
                        warped = warp_rgba_to_body_quad(g_rgba, dst, (w, h), use_strip_mesh=use_mesh)
                    fabric_env_on = _fabric_physics_env_enabled()
                    if fabric_env_on and opts.get("fabric_physics_enabled", True):
                        try:
                            low_power = bool(opts.get("fabric_low_power", False))
                            warped, fab_meta = apply_fabric_physics_to_warp(
                                g_rgba,
                                dst.astype(np.float64),
                                pose,
                                (w, h),
                                low_power=low_power,
                                material=material,
                            )
                            warnings.append(
                                "Fabric PBD: "
                                f"{fab_meta.get('fabricPhysics', '?')} "
                                f"grid={fab_meta.get('grid')} "
                                f"iters={fab_meta.get('iterations')}"
                            )
                        except Exception as ex:
                            logger.warning("Fabric physics skipped: %s", ex)
                            warnings.append("Fabric physics unavailable; using geometric warp only")
                    alpha_for_check = warped[:, :, 3]
                    # If warped garment is extremely small relative to torso area, upscale once and retry.
                    torso_area = float(np.count_nonzero(torso > 80))
                    garment_area = float(np.count_nonzero(alpha_for_check > 25))
                    min_cover = float(os.getenv("TRYON_MIN_TORSO_COVERAGE", "0.18"))
                    if torso_area > 1.0 and garment_area / torso_area < min_cover:
                        g_rgba = cv2.resize(
                            g_rgba,
                            (max(1, int(g_rgba.shape[1] * 1.2)), max(1, int(g_rgba.shape[0] * 1.2))),
                            interpolation=cv2.INTER_LANCZOS4,
                        )
                        warnings.append("Auto-upscaled garment to avoid tiny torso coverage")
                        attempt += 1
                        if max_retries == 0 and attempt > 0:
                            # Even with zero configured retries, allow one real re-warp after auto-upscale.
                            max_retries = 1
                        continue
                    cx, cy = TryOnSelfCheck.garment_centroid(alpha_for_check)
                    inside = TryOnSelfCheck.center_inside_mask(cx, cy, torso, erode_px=10)
                    loose = TryOnSelfCheck.alpha_mass_outside_mask(alpha_for_check, torso)
                    # Reject "mostly inside torso but still misaligned" cases.
                    # Previous loose threshold (0.55) was too permissive and allowed
                    # visible misplacement to pass without further nudging.
                    loose_max = float(os.getenv("TRYON_TORSO_LOOSE_MAX", "0.25"))
                    if inside and loose < loose_max:
                        break
                    # Nudge quad toward torso centroid, but bias Y upward a bit for tops.
                    # Centroid can sit slightly below where a T-shirt hem/warp should align.
                    tcy_target = tcy
                    if category in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR):
                        coords = cv2.findNonZero((torso > 80).astype(np.uint8))
                        if coords is not None:
                            _x, _y, _w, th = cv2.boundingRect(coords)
                            # Move target toward "upper torso center" by ~8% torso height.
                            tcy_target = tcy - float(th) * 0.08

                    # IMPORTANT: if max_retries == 0, the loop will exit after this nudge.
                    # We must re-warp immediately so the output actually uses the adjusted quad.
                    dst = TryOnSelfCheck.nudge_quad_toward_torso(dst, tcx, tcy_target, step=0.10)
                    attempt += 1
                    warnings.append("Adjusted garment alignment toward torso")
                    if attempt > max_retries:
                        if pose_map is not None:
                            anchors = compute_body_anchors(pose_map)
                            depth = estimate_depth_match(anchors, h)
                            warped = apply_pose_aware_mesh_warp(g_rgba, dst, (w, h), depth=depth)
                        else:
                            warped = warp_rgba_to_body_quad(g_rgba, dst, (w, h), use_strip_mesh=use_mesh)
                        if fabric_env_on and opts.get("fabric_physics_enabled", True):
                            try:
                                warped, _fab_meta = apply_fabric_physics_to_warp(
                                    g_rgba,
                                    dst.astype(np.float64),
                                    pose,
                                    (w, h),
                                    low_power=bool(opts.get("fabric_low_power", False)),
                                    material=material,
                                )
                            except Exception as ex:
                                logger.warning("Fabric physics skipped after nudge: %s", ex)
                        alpha_for_check = warped[:, :, 3]

                warped = _apply_garment_clip_mask(warped, clip_mask)
                # Final, conservative cleanup: remove tiny detached alpha components
                # that otherwise "sparkle" after warp/blend (common on outdoor photos).
                if category in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR):
                    min_ratio = float(os.getenv("TRYON_ALPHA_MIN_COMPONENT_RATIO", "0.02"))
                    warped = _cleanup_alpha_speckles(
                        warped,
                        clip_u8=clip_mask,
                        min_component_ratio=min_ratio,
                        alpha_thr=25,
                    )
                # Optional debug artifacts for diagnosing "garment on background" issues.
                if os.getenv("TRYON_DEBUG_SAVE", "0").strip().lower() in ("1", "true", "yes"):
                    dbg_dir = os.getenv("TRYON_DEBUG_DIR", "backend")
                    os.makedirs(dbg_dir, exist_ok=True)
                    ts = int(time.time() * 1000)
                    try:
                        cv2.imwrite(
                            os.path.join(dbg_dir, f"dbg_{ts}_seg_torso.png"),
                            seg.torso_mask.astype(np.uint8),
                        )
                        if seg.garment_clip_mask is not None:
                            cv2.imwrite(
                                os.path.join(dbg_dir, f"dbg_{ts}_seg_clip.png"),
                                seg.garment_clip_mask.astype(np.uint8),
                            )
                        cv2.imwrite(
                            os.path.join(dbg_dir, f"dbg_{ts}_tryon_clip_mask.png"),
                            clip_mask.astype(np.uint8),
                        )
                        cv2.imwrite(
                            os.path.join(dbg_dir, f"dbg_{ts}_warped_alpha_after_clip.png"),
                            warped[:, :, 3].astype(np.uint8),
                        )
                    except Exception as e:
                        logger.warning("Debug save failed: %s", e)
                if np.mean(warped[:, :, 3]) < 6.0:
                    warnings.append("Garment visibility low after body clip; check garment photo background")

                if TryOnSelfCheck.edge_sharpness_harsh(warped[:, :, 3]):
                    edge_r = 25
                    if material is not None:
                        edge_r = max(9, min(35, int(12 + material.edge_feather_px * 1.2)))
                    warped = _feather_alpha(warped, radius=edge_r)
                    warnings.append("Softened harsh garment edges")

                # Raised quality thresholds for production-grade output
                # Reject obvious "sticker" effects and misaligned garments
                thresh = float(opts.get("quality_threshold", 0.72))
                min_out = _effective_min_output_quality(opts, thresh)
                recovery_max = int(os.getenv("TRYON_QUALITY_RECOVERY_MAX", "2"))
                if bool(opts.get("preview_mode")):
                    # Preview endpoint must be latency-first on CPU.
                    recovery_max = min(recovery_max, 0)
                person_rgb = np.array(person_work.convert("RGB"))
                base_feather = int(os.getenv("TRYON_BLEND_FEATHER_PX", "5"))

                logger.info("tryon stage: depth_blend_light_match")
                seg_work = seg
                blend_res = None
                q_eval = None
                q = 0.0
                retries_used = 0
                out_work: Optional[Image.Image] = None

                for recovery in range(recovery_max + 1):
                    if recovery > 0:
                        seg_work = self._segmenter.refine_for_recovery(seg, pose, person_rgb, recovery - 1)
                        retries_used = recovery
                        warnings.append(f"Quality recovery attempt {recovery}/{recovery_max}")

                    if category in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR):
                        # Same union logic as main warp path (torso-tight ∪ wide clip ∪ shoulders).
                        cm_m = (seg_work.torso_mask > 80).astype(np.uint8) * 255
                        torso_clip_dilate = int(os.getenv("TRYON_TORSO_CLIP_DILATE_PX", "40"))
                        torso_clip_blur = int(os.getenv("TRYON_TORSO_CLIP_BLUR_PX", "35"))
                        torso_clip_dilate = max(1, torso_clip_dilate)
                        torso_clip_blur = max(3, torso_clip_blur)
                        k_d = (torso_clip_dilate, torso_clip_dilate)
                        k_b = (torso_clip_blur, torso_clip_blur)
                        cm_m = cv2.dilate(cm_m, np.ones(k_d, np.uint8), iterations=1)
                        torso_tight = cv2.GaussianBlur(cm_m, k_b, 0)
                        wide_ref = seg_work.garment_clip_mask
                        if wide_ref is None or wide_ref.shape[:2] != (h, w):
                            wide_ref = np.maximum(
                                seg_work.torso_mask,
                                (seg_work.person_mask > 80).astype(np.uint8) * 255,
                            )
                            wide_ref = cv2.GaussianBlur(wide_ref, (41, 41), 0)
                        wide_ref = np.clip(wide_ref, 0, 255).astype(np.uint8)
                        shoulder_sup = _shoulder_line_clip_mask(pose, w, h)
                        cm = np.maximum(np.maximum(torso_tight, wide_ref), shoulder_sup)
                        cm = cv2.GaussianBlur(cm, (5, 5), 0)
                    else:
                        cm = seg_work.garment_clip_mask
                        if cm is None or cm.shape[:2] != (h, w):
                            cm = np.maximum(seg_work.torso_mask, (seg_work.person_mask > 80).astype(np.uint8) * 255)
                            cm = cv2.GaussianBlur(cm, (41, 41), 0)
                    w_try = _apply_garment_clip_mask(warped, cm)
                    if category in (GarmentCategory.TOPS, GarmentCategory.OUTERWEAR):
                        min_ratio = float(os.getenv("TRYON_ALPHA_MIN_COMPONENT_RATIO", "0.02"))
                        w_try = _cleanup_alpha_speckles(
                            w_try,
                            clip_u8=cm,
                            min_component_ratio=min_ratio,
                            alpha_thr=25,
                        )
                    if os.getenv("TRYON_DEBUG_SAVE", "0").strip().lower() in ("1", "true", "yes") and recovery == 0:
                        dbg_dir = os.getenv("TRYON_DEBUG_DIR", "backend")
                        os.makedirs(dbg_dir, exist_ok=True)
                        ts = int(time.time() * 1000)
                        try:
                            cv2.imwrite(
                                os.path.join(dbg_dir, f"dbg_{ts}_w_try_alpha_r{recovery}.png"),
                                w_try[:, :, 3].astype(np.uint8),
                            )
                        except Exception as e:
                            logger.warning("Debug save failed (w_try): %s", e)
                    feather_px = base_feather + recovery * 2

                    blend_res = await self._blender.blend_fullframe(
                        person_work,
                        w_try,
                        pose,
                        seg_work,
                        feather_px=feather_px,
                        material=material,
                    )

                    if not blend_res.success or blend_res.image is None:
                        return ClassicalTryOnResult(
                            success=False,
                            error_message=blend_res.error_message or "Blend failed",
                            processing_time_ms=(time.time() - t0) * 1000,
                            fabric_intelligence_json=fabric_intelligence_json,
                        )

                    out_work = blend_res.image
                    q_eval = evaluate_tryon_quality(
                        np.array(out_work.convert("RGB")),
                        person_rgb,
                        blend_res.mask if blend_res.mask is not None else np.zeros((h, w), np.uint8),
                        pose,
                        seg_work,
                    )
                    q = q_eval.overall
                    if q >= min_out:
                        break

            if out_work is None or blend_res is None or q_eval is None:
                return ClassicalTryOnResult(
                    success=False,
                    error_message="Blend produced no output",
                    processing_time_ms=(time.time() - t0) * 1000,
                    fabric_intelligence_json=fabric_intelligence_json,
                )

            if q < thresh and opts.get("auto_refine", True) is not False:
                logger.info("tryon stage: self_heal_refine_once (quality %.2f < %.2f)", q, thresh)
                protected = np.maximum(seg_work.face_mask, seg_work.hair_mask)
                refined = await self._blender.refine_blend_once(
                    person_work,
                    out_work,
                    blend_res.mask,
                    protected_mask=protected,
                )
                if refined is not None:
                    out_work = refined
                    q_eval = evaluate_tryon_quality(
                        np.array(out_work.convert("RGB")),
                        person_rgb,
                        blend_res.mask if blend_res.mask is not None else np.zeros((h, w), np.uint8),
                        pose,
                        seg_work,
                    )
                    q = q_eval.overall
                    warnings.append("Applied one automatic blend refinement")

            # ====================================================================
            # CONFIT STABLE GARMENT ALIGNMENT - QUALITY SCORE OVERRIDE LOGIC
            # If composite score < 0.5: auto-enhance segmentation clarity and retry
            # ====================================================================
            quality_override_threshold = float(os.getenv("TRYON_QUALITY_OVERRIDE_THRESHOLD", "0.5"))
            if stable_alignment_enabled and q < quality_override_threshold and q > 0:
                logger.info("tryon stage: quality_override_enhancement (quality %.2f < %.2f)", q, quality_override_threshold)
                
                # Apply local contrast enhancement to garment region
                from services.tryon.stable_alignment import check_quality_and_enhance
                
                out_array = np.array(out_work.convert("RGB"))
                enhanced, new_q, enhance_warnings = check_quality_and_enhance(
                    q,
                    out_array,
                    person_rgb,
                    seg_work.torso_mask,
                    w_try,
                    pose.landmarks if pose.success else {},
                    min_threshold=quality_override_threshold,
                    max_retries=1,
                )
                warnings.extend(enhance_warnings)
                
                if new_q > q:
                    out_work = Image.fromarray(enhanced, "RGB")
                    q = new_q
                    logger.info("Quality override: enhanced from %.3f to %.3f", q_eval.overall, new_q)

            if TryOnSelfCheck.edge_sharpness_harsh(blend_res.mask) if blend_res.mask is not None else False:
                warnings.append("Edge quality refinement suggested")

            diag = {
                "status": "auto_corrected" if retries_used > 0 else "passed",
                "retries_used": retries_used,
                "recovery_max": recovery_max,
                "final_score": round(q, 4),
                "minimum_required": round(min_out, 4),
                "threshold_auto_refine": round(thresh, 4),
                "segmentation_source": getattr(seg_work, "segmentation_source", "unknown"),
                "components": q_eval.to_public_dict() if q_eval else {},
            }
            if material is not None:
                diag["fabric_intelligence"] = {
                    "fabric_type": material.fabric.value,
                    "confidence": round(material.classification_confidence, 4),
                }
            quality_diagnostics_json = json.dumps(diag)

            if q < min_out:
                elapsed = (time.time() - t0) * 1000
                logger.warning("tryon rejected: composite quality %.3f < floor %.3f", q, min_out)
                diag_fail = dict(diag)
                diag_fail["status"] = "below_minimum"
                return ClassicalTryOnResult(
                    success=False,
                    error_message=(
                        "We couldn't reach the minimum quality bar for this try-on. "
                        "A clearer, front-facing photo and a garment image with a clean background usually work best."
                    ),
                    quality_score=q,
                    garment_category=category.value,
                    warnings=warnings,
                    processing_time_ms=elapsed,
                    pose_keypoints_json=pose_to_skeleton_json(pose) if pose_ok else None,
                    body_dna_pose_reused=body_dna_pose_reused,
                    fit_preview_json=fit_preview_json,
                    quality_diagnostics_json=json.dumps(diag_fail),
                    fabric_intelligence_json=fabric_intelligence_json,
                    pose_map_json=pose_map_json,
                )

            out_pil = out_work
            if out_pil.size != original_size:
                out_pil = out_pil.resize(original_size, Image.Resampling.LANCZOS)

            # ====================================================================
            # CONFIT STABLE GARMENT ALIGNMENT - REALISM ENFORCEMENT
            # Preserve fabric structure, prevent texture melting, maintain wrinkles
            # ====================================================================
            if stable_alignment_enabled and material is not None:
                out_array = np.array(out_pil.convert("RGB"))
                out_enhanced = enforce_realism(
                    out_array,
                    w_try,
                    seg_work.torso_mask,
                    preserve_fabric_structure=True,
                    preserve_wrinkles=True,
                    match_perspective=True,
                )
                out_pil = Image.fromarray(out_enhanced, "RGB")
                logger.debug("Stable alignment: realism enforcement applied")

            ident_align = alignment_identity()
            alignment_diagnostics_json = json.dumps(
                build_alignment_diagnostics_payload(
                    pose_landmarks=pose.landmarks if pose.success else {},
                    pose_confidence=float(pose.confidence),
                    orientation=last_orientation,
                    garment_corrections_applied=garment_corrections_tracked,
                    pipeline_version=str(opts.get("alignment_pipeline_version", ident_align["alignment_pipeline_version"])),
                    alignment_code_id=str(opts.get("alignment_code_id", ident_align["alignment_code_id"])),
                    preview_mode=bool(opts.get("preview_mode")),
                    stable_alignment_enabled=stable_alignment_enabled,
                    normalization_ran=normalization_ran,
                    category=category.value,
                )
            )

            if os.getenv("DEBUG_TRYON", "").strip() == "1":
                meta = json.loads(alignment_diagnostics_json)
                maybe_save_tryon_debug_bundle(
                    request_id,
                    person_rgb,
                    pose.landmarks if pose.success else {},
                    g_rgba_before_align,
                    g_rgba_after_align,
                    np.array(out_pil.convert("RGB")),
                    torso_mask=seg_work.torso_mask,
                    warped_garment_rgba=w_try,
                    alignment_metadata=meta,
                )

            elapsed = (time.time() - t0) * 1000
            pose_json = pose_to_skeleton_json(pose) if pose_ok else None

            learned_json: Optional[str] = None
            if user_id and pose.success and not opts.get("no_persist_body_dna"):
                if not body_dna_pose_reused:
                    should_save = (
                        not store.exists(user_id)
                        or bool(opts.get("learn_body_dna"))
                        or bool(opts.get("force_refresh_body_dna"))
                    )
                    if should_save:
                        prof = build_body_profile(pose)
                        merge_style_memory(
                            prof,
                            preferred_fit=str(opts.get("fit_type", "regular")),
                            garment_category=category.value,
                            color_hex=opts.get("garment_color_hex"),
                        )
                        store.save(user_id, prof)
                        learned_json = json.dumps(prof)
                    elif store.exists(user_id):
                        prof = store.load(user_id)
                        if prof:
                            merge_style_memory(
                                prof,
                                preferred_fit=str(opts.get("fit_type", "regular")),
                                garment_category=category.value,
                                color_hex=opts.get("garment_color_hex"),
                            )
                            store.save(user_id, prof)
                elif store.exists(user_id):
                    prof = store.load(user_id)
                    if prof:
                        merge_style_memory(
                            prof,
                            preferred_fit=str(opts.get("fit_type", "regular")),
                            garment_category=category.value,
                            color_hex=opts.get("garment_color_hex"),
                        )
                        store.save(user_id, prof)

            return ClassicalTryOnResult(
                success=True,
                result_image=pil_to_base64(out_pil, format="JPEG", quality=92),
                quality_score=q,
                pose_detected=mediapipe_pose_ok,
                garment_category=category.value,
                warnings=warnings,
                processing_time_ms=elapsed,
                pose_keypoints_json=pose_json,
                body_dna_pose_reused=body_dna_pose_reused,
                fit_preview_json=fit_preview_json,
                body_profile_json=learned_json,
                quality_diagnostics_json=quality_diagnostics_json,
                fabric_intelligence_json=fabric_intelligence_json,
                pose_map_json=pose_map_json,
                alignment_diagnostics_json=alignment_diagnostics_json,
            )

        except GarmentImageDownloadError as e:
            return ClassicalTryOnResult(
                success=False,
                error_message=str(e),
                failure_kind="garment_fetch",
                processing_time_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            logger.exception("Classical try-on failed: %s", e)
            return ClassicalTryOnResult(
                success=False,
                error_message=str(e),
                processing_time_ms=(time.time() - t0) * 1000,
            )
        finally:
            if garment_path:
                try:
                    os.unlink(garment_path)
                except OSError:
                    pass

    @staticmethod
    def _pil_to_bytes_jpeg(img: Image.Image) -> bytes:
        import io

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92)
        return buf.getvalue()

    def health(self) -> Dict[str, Any]:
        return {
            "pose": self._pose.health_check(),
            "garment": self._garment.health_check(),
            "blender": self._blender.health_check(),
        }
