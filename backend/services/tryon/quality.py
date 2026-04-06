"""
Professional composite quality evaluation for classical try-on.

Weighted components (defaults; face/hair excluded from edge/lighting/texture ROIs):
  pose_alignment 30%, mask_accuracy 25%, edge_blending 20%,
  lighting_match 15%, texture_preserved 10%

When segmentation confidence is low, mask weight is reduced and pose/lighting
weights absorb the difference (no arbitrary global threshold bypass).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

from services.tryon.segmentation.body import SegmentationPack, _ensure_hw
from services.tryon.vision.pose import PoseResult

# Default weights (sum = 1.0)
W_POSE = 0.30
W_MASK = 0.25
W_EDGE = 0.20
W_LIGHT = 0.15
W_TEX = 0.10


@dataclass
class QualityEvaluation:
    overall: float
    pose_alignment: float
    mask_accuracy: float
    edge_blending: float
    lighting_match: float
    texture_preserved: float
    segmentation_confidence: float
    weights_used: Dict[str, float] = field(default_factory=dict)
    notes: Tuple[str, ...] = ()

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "status": "evaluated",
            "final_score": round(self.overall, 4),
            "pose_alignment": round(self.pose_alignment, 4),
            "mask_accuracy": round(self.mask_accuracy, 4),
            "edge_blending": round(self.edge_blending, 4),
            "lighting_match": round(self.lighting_match, 4),
            "texture_preserved": round(self.texture_preserved, 4),
            "segmentation_confidence": round(self.segmentation_confidence, 4),
            "weights": {k: round(v, 4) for k, v in self.weights_used.items()},
        }


def _dilated_protected(face: np.ndarray, hair: np.ndarray, h: int, w: int) -> np.ndarray:
    p = np.maximum(_ensure_hw(face, h, w), _ensure_hw(hair, h, w))
    p = (p > 80).astype(np.uint8) * 255
    if np.max(p) < 1:
        return np.zeros((h, w), dtype=np.uint8)
    return cv2.dilate(p, np.ones((11, 11), np.uint8), iterations=2)


def evaluate_pose_alignment(pose: PoseResult, torso_mask: np.ndarray, h: int, w: int) -> float:
    """Landmark confidence + plausible torso placement (face not used)."""
    if pose.success and pose.confidence >= 0.6:
        base = 0.52 + 0.48 * float(min(1.0, pose.confidence))
    elif pose.success:
        base = 0.38 + 0.45 * float(pose.confidence)
    else:
        base = 0.40
    m = (torso_mask > 80).astype(np.uint8)
    M = cv2.moments(m)
    if M["m00"] > 1e-6:
        cy = M["m01"] / M["m00"]
        if 0.15 * h < cy < 0.92 * h:
            base = min(1.0, base + 0.07)
    return float(np.clip(base, 0.0, 1.0))


def evaluate_lighting_match_person_local(
    blended: np.ndarray,
    original: np.ndarray,
    garment_alpha: np.ndarray,
    person_mask: np.ndarray,
    exclude_face: np.ndarray,
    h: int,
    w: int,
) -> float:
    """
    Compare luminance in garment region vs same pixels on original — not
    'blend vs background' (which punishes busy step-and-repeat banners).
    """
    ga = _ensure_hw(garment_alpha, h, w).astype(np.float32) / 255.0
    pm = (_ensure_hw(person_mask, h, w) > 80).astype(np.float32)
    ex = (_ensure_hw(exclude_face, h, w) > 80).astype(np.float32)
    m = (ga > 0.08) & (pm > 0.5) & (ex < 0.5)
    if not np.any(m):
        m = (ga > 0.05) & (pm > 0.5)
    if not np.any(m):
        return 0.65
    yb = cv2.cvtColor(blended, cv2.COLOR_RGB2YUV)[:, :, 0].astype(np.float32)
    yo = cv2.cvtColor(original, cv2.COLOR_RGB2YUV)[:, :, 0].astype(np.float32)
    b0, b1 = float(np.mean(yb[m])), float(np.mean(yo[m]))
    diff = abs(b0 - b1) / 255.0
    return float(np.clip(1.0 - min(1.0, diff * 2.2), 0.0, 1.0))


def evaluate_edge_blending(
    blended: np.ndarray,
    original: np.ndarray,
    garment_alpha: np.ndarray,
    person_mask: np.ndarray,
    exclude_face: np.ndarray,
    h: int,
    w: int,
) -> float:
    """Gradient smoothness along garment boundary inside person, excluding face."""
    ga = (_ensure_hw(garment_alpha, h, w) > 30).astype(np.uint8) * 255
    pm = (_ensure_hw(person_mask, h, w) > 80).astype(np.uint8) * 255
    ex = (_ensure_hw(exclude_face, h, w) > 80).astype(np.uint8) * 255
    k = np.ones((5, 5), np.uint8)
    edge = cv2.dilate(ga, k, iterations=1) - cv2.erode(ga, k, iterations=1)
    eff = cv2.bitwise_and(edge, pm)
    eff = cv2.bitwise_and(eff, cv2.bitwise_not(ex))
    ring = (eff > 0).astype(np.float32)
    if float(np.sum(ring)) < 80:
        return 0.72
    bb = cv2.cvtColor(blended, cv2.COLOR_RGB2GRAY).astype(np.float32)
    bp = cv2.cvtColor(original, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx = cv2.Sobel(bb, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(bb, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy)
    rm = ring > 0
    var = float(np.var(mag[rm]))
    # moderate variance = natural edges; huge variance = harsh halos
    score = 1.0 / (1.0 + var / 2500.0)
    return float(np.clip(score, 0.0, 1.0))


def evaluate_texture_preserved(
    blended: np.ndarray,
    original: np.ndarray,
    torso_mask: np.ndarray,
    exclude_face: np.ndarray,
    h: int,
    w: int,
) -> float:
    """High-frequency energy ratio in torso excluding face (not face texture)."""
    t = (_ensure_hw(torso_mask, h, w) > 40).astype(np.uint8)
    ex = (_ensure_hw(exclude_face, h, w) > 80).astype(np.uint8)
    roi = (t > 0) & (ex < 1)
    if not np.any(roi):
        return 0.7
    o = cv2.cvtColor(original, cv2.COLOR_RGB2GRAY)
    b = cv2.cvtColor(blended, cv2.COLOR_RGB2GRAY)
    lo = cv2.Laplacian(o, cv2.CV_64F)
    lb = cv2.Laplacian(b, cv2.CV_64F)
    mo = float(np.mean(np.abs(lo[roi])) + 1e-6)
    mb = float(np.mean(np.abs(lb[roi])) + 1e-6)
    ratio = mb / mo
    dev = abs(1.0 - ratio)
    return float(np.clip(1.0 - min(1.0, dev * 0.85), 0.0, 1.0))


def evaluate_background_speckle_artifacts(
    blended: np.ndarray,
    original: np.ndarray,
    garment_alpha_u8: np.ndarray,
    person_mask: np.ndarray,
    protected_mask: np.ndarray,
    h: int,
    w: int,
) -> float:
    """
    Penalize "sparkle specks" appearing on background where garment alpha should be ~0.
    """
    ga = (_ensure_hw(garment_alpha_u8, h, w)).astype(np.float32)
    pm = (_ensure_hw(person_mask, h, w) > 80).astype(np.uint8)
    prot = (_ensure_hw(protected_mask, h, w) > 80).astype(np.uint8)

    # Background region: outside person silhouette and outside protected zones,
    # and also outside strong garment alpha footprints.
    bg = (pm == 0) & (prot == 0) & (ga < 8.0)
    if not np.any(bg):
        return 0.75

    bg_idx = np.where(bg)
    bgray = cv2.cvtColor(blended, cv2.COLOR_RGB2GRAY).astype(np.float32)
    ogray = cv2.cvtColor(original, cv2.COLOR_RGB2GRAY).astype(np.float32)

    diff = np.abs(bgray[bg_idx] - ogray[bg_idx])  # 0..255
    mean_diff = float(np.mean(diff)) if diff.size else 0.0

    # Convert to a severity score: mean_diff above threshold => artifacts likely.
    thr = float(os.getenv("TRYON_BG_SPECKLE_DIFF_THR", "9.0"))
    # mean_diff = thr => severity 0.5; mean_diff = 2*thr => severity 1.0
    sev = float(np.clip((mean_diff - thr) / max(thr, 1e-6), 0.0, 1.0))

    # Score is higher when artifacts are lower.
    return float(np.clip(1.0 - sev, 0.0, 1.0))


def _dynamic_weights(seg_conf: float) -> Tuple[float, float, float, float, float]:
    """Reduce mask penalty when segmentation is uncertain."""
    low = float(os.getenv("TRYON_SEG_CONF_LOW", "0.5"))
    if seg_conf >= low:
        return W_POSE, W_MASK, W_EDGE, W_LIGHT, W_TEX
    damp = max(0.35, seg_conf / low)
    wm = W_MASK * damp
    delta = W_MASK - wm
    wp = W_POSE + delta * 0.55
    wl = W_LIGHT + delta * 0.35
    we = W_EDGE + delta * 0.10
    wt = W_TEX
    s = wp + wm + we + wl + wt
    return wp / s, wm / s, we / s, wl / s, wt / s


def evaluate_tryon_quality(
    blended_rgb: np.ndarray,
    original_rgb: np.ndarray,
    garment_alpha_u8: np.ndarray,
    pose: PoseResult,
    seg: SegmentationPack,
) -> QualityEvaluation:
    h, w = blended_rgb.shape[:2]
    face = seg.face_mask
    hair = seg.hair_mask
    prot = _dilated_protected(face, hair, h, w)

    pa = evaluate_pose_alignment(pose, seg.torso_mask, h, w)
    seg_conf = float(getattr(seg, "segmentation_confidence", 0.65))
    ma = float(np.clip(seg_conf, 0.12, 1.0))

    eb = evaluate_edge_blending(
        blended_rgb, original_rgb, garment_alpha_u8, seg.person_mask, prot, h, w
    )
    lm = evaluate_lighting_match_person_local(
        blended_rgb,
        original_rgb,
        garment_alpha_u8,
        seg.person_mask,
        prot,
        h,
        w,
    )
    tp = evaluate_texture_preserved(
        blended_rgb, original_rgb, seg.torso_mask, prot, h, w
    )

    wp, wm, we, wl, wt = _dynamic_weights(seg_conf)
    overall = wp * pa + wm * ma + we * eb + wl * lm + wt * tp
    overall = float(np.clip(overall, 0.0, 1.0))

    # Extra background artifact penalty (speckle / sparkle).
    artifact_score = evaluate_background_speckle_artifacts(
        blended_rgb,
        original_rgb,
        garment_alpha_u8,
        seg.person_mask,
        prot,
        h,
        w,
    )
    # If background artifacts are bad (artifact_score ~ 0), halve the score.
    overall = float(np.clip(overall * (0.5 + 0.5 * artifact_score), 0.0, 1.0))

    # ====================================================================
    # CONFIT STABLE GARMENT ALIGNMENT - FACE PRESERVATION CHECK
    # Penalize if face region was modified (ghost overlay / melting)
    # ====================================================================
    face_score = _evaluate_face_preservation(blended_rgb, original_rgb, face, h, w)
    if face_score < 0.85:
        # Face was modified - significant penalty
        overall = overall * (0.7 + 0.3 * face_score)
        overall = float(np.clip(overall, 0.0, 1.0))

    weights = {
        "pose_alignment": wp,
        "mask_accuracy": wm,
        "edge_blending": we,
        "lighting_match": wl,
        "texture_preserved": wt,
        "face_preservation": face_score,
    }
    notes: Tuple[str, ...] = ()
    if seg_conf < float(os.getenv("TRYON_SEG_CONF_LOW", "0.5")):
        notes = ("reduced_mask_weight_low_segmentation_confidence",)
    if face_score < 0.85:
        notes = notes + ("face_region_modified_penalty_applied",)

    return QualityEvaluation(
        overall=overall,
        pose_alignment=pa,
        mask_accuracy=ma,
        edge_blending=eb,
        lighting_match=lm,
        texture_preserved=tp,
        segmentation_confidence=seg_conf,
        weights_used=weights,
        notes=notes,
    )


def _evaluate_face_preservation(
    blended: np.ndarray,
    original: np.ndarray,
    face_mask: np.ndarray,
    h: int,
    w: int,
) -> float:
    """
    Evaluate if face region was preserved (not modified by garment blending).
    
    Returns score 0-1 where 1 = face perfectly preserved, 0 = face heavily modified.
    """
    face = _ensure_hw(face_mask, h, w)
    face_region = face > 80
    
    if not np.any(face_region):
        return 1.0  # No face detected, no penalty
    
    # Compare pixel values in face region
    blended_face = blended[face_region]
    original_face = original[face_region]
    
    if blended_face.size == 0 or original_face.size == 0:
        return 1.0
    
    # Calculate mean absolute difference
    diff = np.abs(blended_face.astype(np.float32) - original_face.astype(np.float32))
    mean_diff = np.mean(diff)
    
    # Normalize to 0-1 score (threshold: 15 pixel difference = 0.5 score)
    score = 1.0 - min(1.0, mean_diff / 30.0)
    
    return float(np.clip(score, 0.0, 1.0))
