"""
Region-based full-frame try-on compositing.

Root-cause fix for "melted" outputs: no global heavy alpha blur, garment influence
is clipped to torso + garment_clip, face/hair are protected, shadow is masked off
protected zones, and original face pixels are restored last.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from services.tryon.physics.material_engine import MaterialProperties

import cv2
import numpy as np
from PIL import Image

from services.tryon.segmentation.body import SegmentationPack, _ensure_hw
from services.tryon.vision.pose import PoseResult
from services.tryon.stable_alignment import (
    generate_face_exclusion_mask,
    harden_segmentation,
    disable_compositing_over_face,
)

if TYPE_CHECKING:
    from services.tryon.blending.compositor import ImageBlender

logger = logging.getLogger(__name__)


def _laplacian_sharpness(gray_u8: np.ndarray) -> float:
    return float(cv2.Laplacian(gray_u8, cv2.CV_64F).var())


def _gradient_depth_shadow(eff_a: np.ndarray, h: int, w: int) -> np.ndarray:
    """Create a subtle depth shadow gradient at the bottom edge of the garment.

    Returns a single-channel float32 shadow intensity map (0–0.18).
    """
    # Find bottom edge of garment by vertical gradient of alpha
    mask_bin = (eff_a > 0.15).astype(np.uint8)
    # Dilate downward to create shadow below garment
    kernel_down = np.zeros((9, 3), np.uint8)
    kernel_down[5:, :] = 1  # only bottom half of kernel
    shadow_below = cv2.dilate(mask_bin, kernel_down, iterations=2)
    shadow_only = np.clip(shadow_below.astype(np.float32) - mask_bin.astype(np.float32), 0.0, 1.0)
    shadow_only = cv2.GaussianBlur(shadow_only, (21, 21), 0)
    return shadow_only * 0.18  # subtle 18% darkening


def _feather_alpha_u8(alpha_u8: np.ndarray, ksize: int = 17) -> np.ndarray:
    """Feather garment alpha edges for natural blending (anti-sticker).
    
    Enhanced with adaptive erosion based on edge density to prevent
    color bleeding while maintaining natural garment boundaries.
    """
    k = max(3, ksize | 1)
    # Adaptive erosion: stronger for dense edges, lighter for sparse
    edge_density = float(cv2.Canny(alpha_u8, 50, 150).sum()) / max(1, alpha_u8.size)
    erode_px = max(1, int(k // 6 + (3 if edge_density > 0.01 else 0)))
    kernel = np.ones((erode_px, erode_px), np.uint8)
    eroded = cv2.erode(alpha_u8, kernel, iterations=1)
    # Gaussian blur for soft, natural edge transition
    feathered = cv2.GaussianBlur(eroded, (k, k), 0)
    # Restore some edge strength to prevent over-feathering
    feathered = np.clip(feathered.astype(np.float32) * 1.05, 0, 255).astype(np.uint8)
    return feathered


def blend_fullframe_region_safe_sync(
    blender: "ImageBlender",
    person_image: "Image.Image",
    garment_rgba: np.ndarray,
    _pose: PoseResult,
    seg: SegmentationPack,
    feather_px: Optional[int] = None,
    material: Optional["MaterialProperties"] = None,
) -> "BlendResult":
    """
    Synchronous region-safe composite: garment only where allowed, never over face/hair.

    Layer order: base person → shadow (masked) → garment (torso-clipped alpha) → arms → face/hair restore.
    """
    from services.tryon.blending.compositor import BlendResult

    if person_image.mode != "RGB":
        person_image = person_image.convert("RGB")
    person_array = np.array(person_image)
    h, w = person_array.shape[:2]
    if garment_rgba.shape[:2] != (h, w):
        return BlendResult(success=False, error_message="Garment canvas size mismatch")

    person_lighting = blender._extract_lighting_sync(person_image)
    g = garment_rgba.copy()
    g = blender._match_lighting_sync(g, person_lighting)
    g_rgb_matched = blender._match_garment_lab_luma_sync(person_array, g[:, :, :3], g[:, :, 3])
    g[:, :, :3] = g_rgb_matched
    if material is not None:
        from services.tryon.physics.material_engine import apply_material_lighting_rgb

        g[:, :, :3] = apply_material_lighting_rgb(g[:, :, :3], g[:, :, 3], material)

    # Do NOT apply global 13x13 blur on garment alpha (that caused smearing into head/background).

    face = _ensure_hw(seg.face_mask, h, w)
    hair = _ensure_hw(seg.hair_mask, h, w)
    arms = _ensure_hw(seg.arms_mask, h, w)
    torso = _ensure_hw(seg.torso_mask, h, w)
    clip = seg.garment_clip_mask
    if clip is None:
        clip = torso
    else:
        clip = _ensure_hw(clip, h, w)

    # ====================================================================
    # CONFIT STABLE GARMENT ALIGNMENT - FACE PRESERVATION LOCK
    # Generate enhanced face exclusion mask using landmarks
    # This prevents ghost overlay and face melting effects
    # ====================================================================
    stable_alignment_enabled = os.getenv("TRYON_STABLE_ALIGNMENT", "1").lower() in ("1", "true", "yes")
    
    if stable_alignment_enabled and _pose.success and _pose.landmarks:
        # Use landmark-based face exclusion for more accurate protection
        face_exclusion = generate_face_exclusion_mask(_pose.landmarks, w, h, expand_ratio=1.6)
        face_enhanced = face_exclusion.mask
        # Merge with segmentation face mask for maximum protection
        face = np.maximum(face, face_enhanced)
        logger.debug("Stable alignment: enhanced face exclusion mask applied")

    # Protected: union of face + hair, dilated slightly so edges never get garment
    protected_u8 = np.maximum(face, hair)
    dilate_iters = int(os.getenv("TRYON_PROTECT_DILATE_ITERS", "2"))
    k_prot = int(os.getenv("TRYON_PROTECT_KERNEL", "5"))
    if dilate_iters > 0 and np.max(protected_u8) > 10:
        protected_u8 = cv2.dilate(
            (protected_u8 > 80).astype(np.uint8) * 255,
            np.ones((k_prot, k_prot), np.uint8),
            iterations=dilate_iters,
        )
    prot_1ch = (protected_u8 > 80).astype(np.float32)

    # Placement mask: `garment_clip_mask` is already torso ∪ upper-body person silhouette
    # (see SegmentationPack._build_garment_clip_mask). Multiplying again by a torso-only mask
    # zeroed alpha on shoulders / outer chest where the perspective warp is wider than the inner
    # torso quad — the classic “tiny floating shirt” bug on hoodies and layered outfits.
    clip_f = np.clip(clip.astype(np.float32) / 255.0, 0.0, 1.0)
    strict_torso = os.getenv("TRYON_BLEND_STRICT_TORSO_GATE", "0").lower() in (
        "1",
        "true",
        "yes",
    )
    torso_occ = (torso > 30).astype(np.float32)
    torso_occ = cv2.dilate(torso_occ, np.ones((11, 11), np.uint8), iterations=1)
    body_place = clip_f * (torso_occ if strict_torso else 1.0)
    # Gate placement: remove very small clip values on background that cause
    # residual garment alpha to become visible as "sparkle specks".
    body_gate_abs = float(os.getenv("TRYON_BODY_PLACE_GATE_ABS", "0.1"))
    if body_gate_abs > 0:
        body_place = np.where(body_place >= body_gate_abs, body_place, 0.0).astype(np.float32)

    ga_f = np.clip(g[:, :, 3].astype(np.float32) / 255.0, 0.0, 1.0)
    # Effective garment alpha: warped alpha * placement * never on face/hair
    eff_a = ga_f * body_place * (1.0 - prot_1ch)
    eff_a = np.clip(eff_a, 0.0, 1.0)
    # If placement is degenerate (rare pose / bad masks), fall back to clip only
    if float(np.sum(eff_a > 0.02)) < float(h * w) * 0.00015:
        eff_a = ga_f * clip_f * (1.0 - prot_1ch)
        eff_a = np.clip(eff_a, 0.0, 1.0)
        logger.warning(
            "Region compositor: placement alpha nearly empty; using clip ∩ (1-protected) only"
        )

    # Gate very faint alpha values (common source of "sparkle specks" on background).
    # This is conservative: we keep only alpha >= max(abs_min, max*rel).
    eff_max = float(np.max(eff_a)) if eff_a.size else 0.0
    gate_abs = float(os.getenv("TRYON_EFF_ALPHA_GATE_ABS", "0.02"))
    gate_rel = float(os.getenv("TRYON_EFF_ALPHA_GATE_REL", "0.05"))
    thr = max(gate_abs, eff_max * gate_rel)
    if thr > 0:
        eff_a = np.where(eff_a >= thr, eff_a, 0.0).astype(np.float32)

    # Optional: extra multiply by a closed torso mask (shoulders/chest often OUTSIDE this polygon).
    # Default OFF — it was zeroing almost all warped garment alpha (only a sliver near the neck).
    # Use TRYON_BLEND_STRICT_TORSO_GATE=1 only if you need aggressive torso-only gating.
    if stable_alignment_enabled and strict_torso:
        ksz = int(os.getenv("TRYON_SEG_CLOSE_KERNEL", "11"))
        ksz = max(3, ksz | 1)
        torso_hard = cv2.morphologyEx(
            torso,
            cv2.MORPH_CLOSE,
            np.ones((ksz, ksz), np.uint8),
            iterations=1,
        )
        torso_hard_f = (torso_hard > 80).astype(np.float32) / 255.0
        eff_a = eff_a * torso_hard_f
        eff_a = np.clip(eff_a, 0.0, 1.0)

    # Step 5 — blending: feather scales with fabric (denim sharp, knit soft) when caller passes material-driven feather_px
    # Default feather increased from 17 to 21 for smoother anti-sticker edges
    feather = int(feather_px) if feather_px is not None else int(os.getenv("TRYON_BLEND_FEATHER_PX", "21"))
    if material is not None:
        feather = max(5, min(31, int(round(0.45 * feather + 0.55 * material.edge_feather_px))))
    eff_u8 = (eff_a * 255.0).astype(np.uint8)
    eff_u8 = _feather_alpha_u8(eff_u8, ksize=feather)
    eff_a = eff_u8.astype(np.float32) / 255.0
    alpha = eff_a[:, :, np.newaxis]

    # Enhanced shadow from garment footprint; suppress on protected pixels
    shadow = blender._generate_shadow_sync(g, person_array, (0, 0), person_lighting.dominant_light_direction)
    sa = shadow[:, :, 3:4].astype(np.float32) / 255.0
    sa = sa * (1.0 - prot_1ch[:, :, np.newaxis])
    # Add gradient depth shadow along garment bottom edge for 3D appearance
    if float(np.max(eff_a)) > 0.05:
        grad_shadow = _gradient_depth_shadow(eff_a, h, w)
        grad_shadow_3ch = grad_shadow[:, :, np.newaxis] * (1.0 - prot_1ch[:, :, np.newaxis])
        sa = np.maximum(sa, grad_shadow_3ch)
    base = (
        person_array.astype(np.float32) * (1.0 - sa)
        + shadow[:, :, :3].astype(np.float32) * sa
    ).astype(np.uint8)

    comp = (
        base.astype(np.float32) * (1.0 - alpha)
        + g[:, :, :3].astype(np.float32) * alpha
    )
    blended = np.clip(comp, 0, 255).astype(np.uint8)

    # Arms occlusion restore (original sleeves/hands) — depth-aware layering
    # CONFIT Enhancement: Arms should appear OVER the shirt for realistic layering
    # This creates proper depth perception: person → shirt → arms (front layer)
    
    # Detect arm regions that should occlude the shirt
    am_raw = (arms > 80).astype(np.float32)
    
    # Find arm regions that overlap with garment (these should be on top)
    arm_garment_overlap = am_raw * (eff_a > 0.05).astype(np.float32)
    
    # For realistic depth: arms in front of torso should occlude shirt
    # But arms behind torso (low visibility or extreme side) should not
    if _pose.success and _pose.landmarks:
        # Check elbow positions to determine arm depth
        le = _pose.landmarks.get("left_elbow")
        re = _pose.landmarks.get("right_elbow")
        ls = _pose.landmarks.get("left_shoulder")
        rs = _pose.landmarks.get("right_shoulder")
        
        # If elbow is in front of shoulder (z-depth), arm is forward
        # MediaPipe z: smaller values = closer to camera
        left_arm_forward = False
        right_arm_forward = False
        
        if le and ls:
            left_arm_forward = le[2] < ls[2] if (le[2] > 0 and ls[2] > 0) else True
        if re and rs:
            right_arm_forward = re[2] < rs[2] if (re[2] > 0 and rs[2] > 0) else True
        
        # Restore arms only where they should be in front
        if not (left_arm_forward and right_arm_forward):
            # One or both arms are behind - reduce occlusion
            logger.debug("Arm depth: L=%s, R=%s", left_arm_forward, right_arm_forward)
    
    # Create safe arm mask: restore arms where garment is weak OR where arms overlap strongly
    garment_strong = (eff_a > 0.10).astype(np.float32)
    
    # Arms overlapping shirt should be rendered ON TOP of shirt (not erased)
    # This fixes the "sleeves disappear" bug
    arm_on_shirt = arm_garment_overlap * garment_strong
    
    # For arms on shirt: blend original arm pixels on top of shirt
    if float(np.sum(arm_on_shirt)) > 0.01 * h * w:
        # There are significant arm regions overlapping shirt
        # Render these arms on top for realistic layering
        arm_top_mask = arm_on_shirt[:, :, np.newaxis]
        # Blend: original arms on top of shirt
        blended = (blended.astype(np.float32) * (1.0 - arm_top_mask) + 
                   person_array.astype(np.float32) * arm_top_mask).astype(np.uint8)
        logger.debug("Depth layering: arms rendered on top of shirt")
    
    # For arms outside shirt area: restore original (background arms)
    am_safe = np.clip(am_raw * (1.0 - garment_strong), 0.0, 1.0)[:, :, np.newaxis]
    blended = (blended.astype(np.float32) * (1.0 - am_safe) + 
               person_array.astype(np.float32) * am_safe).astype(np.uint8)

    # Final face/hair restore (original photo pixels)
    ph = prot_1ch[:, :, np.newaxis]
    blended = (blended.astype(np.float32) * (1.0 - ph) + person_array.astype(np.float32) * ph).astype(
        np.uint8
    )

    # Anti-melting: if face region sharpness dropped vs original, paste original face bbox
    if np.any(face > 80):
        ys, xs = np.where(face > 80)
        y0, y1 = int(ys.min()), int(ys.max())
        x0, x1 = int(xs.min()), int(xs.max())
        pad = 4
        y0, x0 = max(0, y0 - pad), max(0, x0 - pad)
        y1, x1 = min(h, y1 + pad), min(w, x1 + pad)
        g_before = cv2.cvtColor(person_array[y0:y1, x0:x1], cv2.COLOR_RGB2GRAY)
        g_after = cv2.cvtColor(blended[y0:y1, x0:x1], cv2.COLOR_RGB2GRAY)
        v0, v1 = _laplacian_sharpness(g_before), _laplacian_sharpness(g_after)
        thresh = float(os.getenv("TRYON_FACE_SHARPNESS_MIN_RATIO", "0.82"))
        if v1 < v0 * thresh and v0 > 1e-6:
            logger.info(
                "Region compositor: face sharpness drop (%.4f -> %.4f); restoring face ROI",
                v0,
                v1,
            )
            roi_face = (face[y0:y1, x0:x1] > 80).astype(np.float32)
            if np.any(roi_face > 0):
                for c in range(3):
                    sl = blended[y0:y1, x0:x1, c].astype(np.float32)
                    pr = person_array[y0:y1, x0:x1, c].astype(np.float32)
                    blended[y0:y1, x0:x1, c] = np.clip(
                        sl * (1.0 - roi_face) + pr * roi_face, 0, 255
                    ).astype(np.uint8)

    blend_mask = eff_u8
    edge_score = blender._calculate_edge_quality_score(blend_mask)
    light_score = blender._calculate_lighting_match_score(blended, person_array, blend_mask)
    overall = (edge_score + light_score) / 2.0

    return BlendResult(
        success=True,
        image=Image.fromarray(blended, "RGB"),
        mask=blend_mask,
        blend_quality_score=overall,
        lighting_match_score=light_score,
        edge_quality_score=edge_score,
        warnings=[],
    )
