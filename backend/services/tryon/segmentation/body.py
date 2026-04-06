"""
Unified body segmentation: MediaPipe Selfie Segmentation + pose-guided torso/arms.
Optional SAM when TRYON_USE_SAM=1 and segment_anything is installed.
"""

from __future__ import annotations

import io
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# Silence noisy TensorFlow/MediaPipe C++ logs (glog/absl messages).
# Safe to set at import time before mediapipe/tasks are imported.
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("GLOG_minloglevel", "3")
os.environ.setdefault("ABSL_MIN_LOG_LEVEL", "2")

import cv2
import numpy as np
from PIL import Image

from services.tryon.vision.pose import LANDMARK_NAMES, PoseResult
from services.tryon.vision.mediapipe_tasks_models import (
    ensure_selfie_segmenter_path,
    get_gpu_delegate_options,
    set_mediapipe_gpu_delegate_unavailable,
)
from core.log_suppression import suppress_native_output
from services.tryon.stable_alignment import harden_segmentation

logger = logging.getLogger(__name__)


def create_clothing_mask(
    person_mask: np.ndarray,
    pose: PoseResult,
    category: str,
) -> np.ndarray:
    """
    Soft mask over torso / upper-body clothing region for inpaint+composite.
    Removes head (above shoulders) from replacement; for tops, trims below hips.
    """
    if person_mask is None or person_mask.size == 0:
        return np.zeros((1, 1), dtype=np.uint8)
    h, w = person_mask.shape[:2]
    clothing_mask = person_mask.astype(np.float32)
    if not pose.success or not pose.landmarks:
        out = cv2.GaussianBlur(clothing_mask, (21, 21), 10)
        return np.clip(out, 0, 255).astype(np.uint8)

    ls = pose.landmarks.get("left_shoulder")
    rs = pose.landmarks.get("right_shoulder")
    if ls and rs:
        top_shoulder_y = min(float(ls[1]), float(rs[1]))
        head_cutoff_y = int(max(0, top_shoulder_y - top_shoulder_y * 0.05))
        clothing_mask[:head_cutoff_y, :] = 0

    cat = (category or "tops").lower()
    if cat == "tops":
        lh = pose.landmarks.get("left_hip")
        rh = pose.landmarks.get("right_hip")
        if lh and rh:
            hip_y = int(max(float(lh[1]), float(rh[1])) + 20)
            clothing_mask[hip_y:, :] = 0

    clothing_mask = cv2.GaussianBlur(clothing_mask, (21, 21), 10)
    return np.clip(clothing_mask, 0, 255).astype(np.uint8)


@dataclass
class SegmentationPack:
    person_mask: np.ndarray  # uint8 0-255
    torso_mask: np.ndarray
    arms_mask: np.ndarray
    face_mask: np.ndarray
    hair_mask: np.ndarray  # uint8, region above face — protected in compositing
    garment_clip_mask: Optional[np.ndarray] = None  # soft uint8, torso ∪ upper body (set in build)
    segmentation_confidence: float = 0.65
    segmentation_source: str = "unknown"


def _ensure_hw(mask: np.ndarray, h: int, w: int) -> np.ndarray:
    if mask.shape[:2] == (h, w):
        return mask
    return cv2.resize(mask, (w, h), interpolation=cv2.INTER_LINEAR)


def _largest_component_mask(mask_u8: np.ndarray) -> np.ndarray:
    """Keep only largest connected foreground blob and fill small holes."""
    m = (mask_u8 > 80).astype(np.uint8)
    if int(m.sum()) == 0:
        return mask_u8
    num, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if num <= 1:
        out = (m * 255).astype(np.uint8)
    else:
        areas = stats[1:, cv2.CC_STAT_AREA]
        idx = int(np.argmax(areas)) + 1
        out = ((labels == idx).astype(np.uint8) * 255)
    # Fill interior holes on clothing shadows/prints.
    k = np.ones((9, 9), np.uint8)
    out = cv2.morphologyEx(out, cv2.MORPH_CLOSE, k, iterations=2)
    return out


class UnifiedBodySegmenter:
    """Person / torso / arms masks for compositing and self-checks."""

    def __init__(self) -> None:
        self._selfie = None
        self._selfie_tasks = None
        self._sam = None
        self._try_sam = os.getenv("TRYON_USE_SAM", "").lower() in ("1", "true", "yes")
        self._last_seg_source: str = "unknown"
        eager_init = str(os.getenv("TRYON_EAGER_SEGMENTER_INIT", "1")).strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if eager_init:
            try:
                self._init_selfie()
                self._init_selfie_tasks()
            except Exception as ex:
                logger.debug("Segmenter eager init skipped: %s", ex)

    def _init_selfie(self) -> None:
        if self._selfie is not None:
            return
        try:
            import mediapipe as mp

            if not hasattr(mp, "solutions") or not hasattr(mp.solutions, "selfie_segmentation"):
                logger.debug("MediaPipe solutions selfie_segmentation unavailable; will use Tasks ImageSegmenter if possible")
                return
            self._selfie = mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1)
            logger.info("Selfie segmentation initialized")
        except Exception as e:
            logger.warning("Selfie segmentation init failed: %s", e)

    def _init_selfie_tasks(self) -> None:
        """MediaPipe Tasks ImageSegmenter when legacy selfie_segmentation is unavailable.
        
        Supports GPU delegate for faster inference on supported hardware.
        """
        if self._selfie_tasks is not None:
            return
        try:
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision
        except ImportError:
            return
        path = ensure_selfie_segmenter_path()
        if not path:
            return
        try:
            # Configure GPU delegate - get actual enum value
            gpu_opts = get_gpu_delegate_options()
            delegate = gpu_opts.get("delegate")  # This is now Delegate.GPU enum, not string
            
            base_opts_dict = {"model_asset_path": path}
            if delegate is not None:
                base_opts_dict["delegate"] = delegate
                logger.info("ImageSegmenter: GPU delegate enabled")
            
            base = mp_python.BaseOptions(**base_opts_dict)
            opts = mp_vision.ImageSegmenterOptions(
                base_options=base,
                running_mode=mp_vision.RunningMode.IMAGE,
                output_category_mask=True,
            )
            with suppress_native_output():
                self._selfie_tasks = mp_vision.ImageSegmenter.create_from_options(opts)
            logger.info("Selfie segmentation (MediaPipe Tasks ImageSegmenter) initialized")
        except Exception as e:
            logger.warning("Tasks selfie segmentation init failed with GPU: %s, trying CPU", e)
            err_l = str(e).lower()
            if any(
                s in err_l
                for s in ("gpu", "delegate", "build flag", "imageclone", "validatedgraphconfig")
            ):
                set_mediapipe_gpu_delegate_unavailable("image_segmenter")
            # Fallback to CPU
            try:
                base = mp_python.BaseOptions(model_asset_path=path)
                opts = mp_vision.ImageSegmenterOptions(
                    base_options=base,
                    running_mode=mp_vision.RunningMode.IMAGE,
                    output_category_mask=True,
                )
                with suppress_native_output():
                    self._selfie_tasks = mp_vision.ImageSegmenter.create_from_options(opts)
                logger.info("Selfie segmentation (MediaPipe Tasks ImageSegmenter) initialized on CPU fallback")
            except Exception as e2:
                logger.warning("Tasks selfie segmentation init failed on CPU too: %s", e2)

    def _init_sam_if_needed(self, image_rgb: np.ndarray) -> None:
        if not self._try_sam or self._sam is not None:
            return
        try:
            from segment_anything import sam_model_registry, SamPredictor
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            variant = "vit_b"
            ckpt = f"models/sam_{variant}.pth"
            sam = sam_model_registry[variant](checkpoint=ckpt)
            sam.to(device=device)
            self._sam = SamPredictor(sam)
            logger.info("SAM loaded for try-on")
        except Exception as e:
            logger.debug("SAM not used: %s", e)
            self._try_sam = False

    def _fallback_mask_grabcut(self, image_rgb: np.ndarray) -> np.ndarray:
        """Foreground mask when MediaPipe selfie is unavailable (GrabCut + largest blob)."""
        h, w = image_rgb.shape[:2]
        max_side = int(os.getenv("TRYON_GRABCUT_MAX_SIDE", "384"))
        iters = max(1, min(5, int(os.getenv("TRYON_GRABCUT_ITERS", "2"))))
        # GrabCut on full 1024px frames can take 30–60s+ on CPU; downscale then upscale mask.
        small = image_rgb
        sh, sw = h, w
        if max(h, w) > max_side:
            r = max_side / float(max(h, w))
            sw, sh = max(1, int(w * r)), max(1, int(h * r))
            small = cv2.resize(image_rgb, (sw, sh), interpolation=cv2.INTER_AREA)

        bgr = cv2.cvtColor(small, cv2.COLOR_RGB2BGR)
        margin = max(4, min(sh, sw) // 40)
        rect = (margin, margin, max(1, sw - 2 * margin), max(1, sh - 2 * margin))
        mask_gc = np.zeros((sh, sw), np.uint8)
        bgd = np.zeros((1, 65), np.float64)
        fgd = np.zeros((1, 65), np.float64)
        try:
            cv2.grabCut(bgr, mask_gc, rect, bgd, fgd, iters, cv2.GC_INIT_WITH_RECT)
        except cv2.error:
            return self._fallback_mask_otsu(image_rgb)
        binm = np.where((mask_gc == cv2.GC_BGD) | (mask_gc == cv2.GC_PR_BGD), 0, 255).astype(np.uint8)
        contours, _ = cv2.findContours(binm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return self._fallback_mask_otsu(image_rgb)
        c = max(contours, key=cv2.contourArea)
        out = np.zeros((sh, sw), dtype=np.uint8)
        cv2.drawContours(out, [c], -1, 255, -1)
        out = cv2.GaussianBlur(out, (5, 5), 0)
        if out.shape[:2] != (h, w):
            out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
        return out

    def _estimate_mask_confidence_grabcut(self, pm: np.ndarray, image_rgb: np.ndarray) -> float:
        """Heuristic 0–1: solidity, coverage, boundary smoothness (no face logic)."""
        m = (pm > 80).astype(np.uint8)
        h, w = pm.shape[:2]
        area = float(np.sum(m))
        if area < 400:
            return 0.32
        contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return 0.35
        c = max(contours, key=cv2.contourArea)
        hull = cv2.convexHull(c)
        area_c = float(cv2.contourArea(c))
        hull_a = float(cv2.contourArea(hull)) + 1e-6
        solidity = area_c / hull_a
        score_solid = float(np.clip((solidity - 0.5) / 0.45, 0.0, 1.0))
        cov = area / float(h * w)
        score_cov = float(np.clip((cov - 0.04) / 0.38, 0.0, 1.0))
        return float(np.clip(0.34 + 0.38 * score_solid + 0.28 * score_cov, 0.15, 0.9))

    def _confidence_for_source(self, source: str, pm: np.ndarray, image_rgb: np.ndarray) -> float:
        if source == "sam":
            return 0.92
        if source == "mediapipe_selfie":
            return 0.88
        if source == "reuse":
            return min(0.9, self._estimate_mask_confidence_grabcut(pm, image_rgb) + 0.06)
        if source == "grabcut":
            return self._estimate_mask_confidence_grabcut(pm, image_rgb)
        return self._estimate_mask_confidence_grabcut(pm, image_rgb)

    def refine_for_recovery(
        self,
        pack: SegmentationPack,
        pose: PoseResult,
        image_rgb: np.ndarray,
        level: int,
    ) -> SegmentationPack:
        """Morphological cleanup of person mask for recovery attempts (same image size)."""
        h, w = image_rgb.shape[:2]
        pm = _ensure_hw(pack.person_mask, h, w).copy()
        ksz = 3 + min(5, level) * 2
        kernel = np.ones((ksz, ksz), np.uint8)
        pm = cv2.morphologyEx(pm, cv2.MORPH_CLOSE, kernel, iterations=1)
        pm = cv2.morphologyEx(pm, cv2.MORPH_OPEN, kernel, iterations=1)
        pm = cv2.GaussianBlur(pm, (5, 5), 0)
        torso = self._torso_from_pose(pose, w, h)
        if np.max(torso) < 30:
            torso = self._torso_from_person_mask(pm, w, h)
        area_ratio = float(np.mean(torso > 80))
        if area_ratio < 0.004:
            torso2 = self._torso_from_person_mask(pm, w, h)
            if float(np.mean(torso2 > 80)) > area_ratio:
                torso = torso2
        torso = cv2.bitwise_and(torso, pm)
        arms = self._arms_from_pose(pose, w, h)
        face = self._face_from_pose(pose, w, h)
        hair = self._hair_from_face(face, pose, w, h)
        clip = self._build_garment_clip_mask(pm, torso, h, w)
        bump = min(0.12, 0.04 * (level + 1))
        base_conf = float(getattr(pack, "segmentation_confidence", 0.65))
        conf = min(0.95, base_conf + bump)
        return SegmentationPack(
            person_mask=pm,
            torso_mask=torso,
            arms_mask=arms,
            face_mask=face,
            hair_mask=hair,
            garment_clip_mask=clip,
            segmentation_confidence=conf,
            segmentation_source=pack.segmentation_source + "_refined",
        )

    def _fallback_mask_otsu(self, image_rgb: np.ndarray) -> np.ndarray:
        h, w = image_rgb.shape[:2]
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if float(np.mean(th)) > 127:
            th = 255 - th
        contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return np.full((h, w), 255, dtype=np.uint8)
        c = max(contours, key=cv2.contourArea)
        out = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(out, [c], -1, 255, -1)
        return out

    def _selfie_mask(self, image_rgb: np.ndarray) -> np.ndarray:
        self._init_selfie()
        if self._selfie is not None:
            res = self._selfie.process(image_rgb)
            m = res.segmentation_mask
            if m is None:
                self._last_seg_source = "grabcut"
                pm = self._fallback_mask_grabcut(image_rgb)
                return (pm.astype(np.float32) / 255.0).clip(0, 1)
            self._last_seg_source = "mediapipe_selfie"
            return np.asarray(m, dtype=np.float32)

        self._init_selfie_tasks()
        if self._selfie_tasks is not None:
            try:
                import mediapipe as mp

                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
                with suppress_native_output():
                    seg_result = self._selfie_tasks.segment(mp_image)
                cm = seg_result.category_mask
                if cm is None:
                    raise ValueError("no category_mask")
                arr = cm.numpy_view()
                # Multiclass model: 0 = background, >0 = person / parts
                mask = (np.squeeze(arr).astype(np.float32) > 0.0).astype(np.float32)
                self._last_seg_source = "mediapipe_selfie"
                return mask
            except Exception as e:
                logger.warning("Tasks selfie segment failed: %s", e)

        logger.info("Using GrabCut/Otsu fallback for person segmentation (MediaPipe selfie unavailable)")
        self._last_seg_source = "grabcut"
        pm = self._fallback_mask_grabcut(image_rgb)
        return (pm.astype(np.float32) / 255.0).clip(0, 1)

    def _torso_from_pose(self, pose: PoseResult, w: int, h: int) -> np.ndarray:
        mask = np.zeros((h, w), dtype=np.uint8)
        if not pose.success or not pose.landmarks:
            return mask
        pts = []
        for name in ("left_shoulder", "right_shoulder", "right_hip", "left_hip"):
            if name in pose.landmarks:
                x, y, vis = pose.landmarks[name]
                if vis > 0.15:
                    pts.append([int(x), int(y)])
        if len(pts) < 3:
            return mask
        # Inflate polygon outward from centroid by ~22% of shoulder width
        # to cover the actual torso surface (landmarks sit on joints, not body edge).
        # Increased from 18% to 22% for better garment coverage on wider body types.
        poly_np = np.array(pts, dtype=np.float32)
        cx, cy = float(np.mean(poly_np[:, 0])), float(np.mean(poly_np[:, 1]))
        # Estimate shoulder width for proportional expansion
        ls = pose.landmarks.get("left_shoulder")
        rs = pose.landmarks.get("right_shoulder")
        if ls and rs:
            sw = abs(rs[0] - ls[0])
        else:
            sw = max(20.0, float(np.max(poly_np[:, 0]) - np.min(poly_np[:, 0])))
        expand_ratio = float(os.getenv("TRYON_TORSO_POSE_EXPAND", "0.22"))
        expand_px = max(12.0, sw * expand_ratio)
        expanded = []
        for px, py in pts:
            dx = float(px) - cx
            dy = float(py) - cy
            dist = max(1e-6, (dx * dx + dy * dy) ** 0.5)
            expanded.append([int(px + dx / dist * expand_px), int(py + dy / dist * expand_px)])
        poly = np.array([expanded], dtype=np.int32)
        cv2.fillPoly(mask, poly, 255)
        # Dilate generously so garment clip doesn't choke on tight polygon.
        # Increased kernel from 15 to 19 for better coverage on varied body shapes.
        k = np.ones((19, 19), np.uint8)
        mask = cv2.dilate(mask, k, iterations=2)
        # Additional horizontal dilation to cover shoulder width
        k_h = np.ones((1, 25), np.uint8)
        mask = cv2.dilate(mask, k_h, iterations=1)
        return mask

    def _torso_from_person_mask(self, person_mask: np.ndarray, w: int, h: int) -> np.ndarray:
        """Torso blob from silhouette when pose polygon is empty (ellipse / hull, not a screen-centered card)."""
        m = (person_mask > 80).astype(np.uint8) * 255
        contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return np.zeros((h, w), dtype=np.uint8)
        c = max(contours, key=cv2.contourArea)
        x, y, bw, bh = cv2.boundingRect(c)
        pts = c.reshape(-1, 2)
        # Upper-body band: shoulders through hips — widened to cover full torso
        y_top = int(y + bh * 0.06)
        y_bot = int(y + bh * 0.65)
        band_idx = (pts[:, 1] >= y_top) & (pts[:, 1] <= y_bot)
        upper = pts[band_idx] if np.any(band_idx) else pts
        torso = np.zeros((h, w), dtype=np.uint8)
        if len(upper) >= 5:
            hull = cv2.convexHull(upper.astype(np.float32))
            cv2.fillPoly(torso, [hull.astype(np.int32)], 255)
        elif len(upper) >= 3:
            cv2.fillPoly(torso, [upper.astype(np.int32)], 255)
        else:
            y0 = int(y + bh * 0.08)
            y1 = int(y + bh * 0.65)
            x0 = int(x + bw * 0.12)
            x1 = int(x + bw * 0.88)
            cv2.rectangle(torso, (max(0, x0), max(0, y0)), (min(w - 1, x1), min(h - 1, y1)), 255, -1)
        torso = cv2.bitwise_and(torso, m)
        # Dilate to cover nearby body edges the silhouette missed.
        k = np.ones((13, 13), np.uint8)
        torso = cv2.morphologyEx(torso, cv2.MORPH_CLOSE, k, iterations=2)
        return torso

    def _arms_from_pose(self, pose: PoseResult, w: int, h: int) -> np.ndarray:
        mask = np.zeros((h, w), dtype=np.uint8)
        if not pose.success or not pose.landmarks:
            return mask
        # Arms: elbow-wrist only (skip shoulder so garment can cover shoulders)
        left_chain = ("left_elbow", "left_wrist")
        right_chain = ("right_elbow", "right_wrist")
        for chain in (left_chain, right_chain):
            pts = []
            for name in chain:
                if name in pose.landmarks:
                    x, y, vis = pose.landmarks[name]
                    if vis > 0.15:
                        pts.append((int(x), int(y)))
            if len(pts) >= 2:
                for i in range(len(pts) - 1):
                    cv2.line(mask, pts[i], pts[i + 1], 255, thickness=50)
                cv2.circle(mask, pts[-1], 40, 255, -1)
            elif len(pts) == 1:
                cv2.circle(mask, pts[0], 40, 255, -1)
        k = np.ones((13, 13), np.uint8)
        mask = cv2.dilate(mask, k, iterations=1)
        return mask

    def _build_garment_clip_mask(
        self, person_mask_u8: np.ndarray, torso: np.ndarray, h: int, w: int
    ) -> np.ndarray:
        """
        Soft mask for multiplying warped garment alpha: torso ∪ upper person silhouette.
        Prevents catalog gray/hanger rectangles from covering the frame when quad warp is larger than the body.
        
        Enhanced for anti-sticker: tighter blur, wider torso coverage.
        """
        pm = (person_mask_u8 > 80).astype(np.uint8) * 255
        band = np.zeros((h, w), dtype=np.uint8)
        # Extended from 0.82 to 0.88 to cover longer garments (dresses, tunics)
        y_cut = min(h, int(h * 0.88))
        band[:y_cut, :] = 255
        upper = cv2.bitwise_and(pm, band)
        # Ensure torso is well-represented even if upper silhouette is narrow
        torso_boost = cv2.dilate(torso, np.ones((7, 7), np.uint8), iterations=1)
        combined = np.maximum(torso_boost.astype(np.uint8), upper)
        # Tighter blur (reduced from 21 to 15) to prevent alpha "sparkle" on background
        clip_blur = int(os.getenv("TRYON_CLIP_MASK_BLUR_PX", "15"))
        clip_blur = max(3, clip_blur)
        k = (clip_blur, clip_blur)
        combined = cv2.GaussianBlur(combined, k, 0)
        return combined

    def _face_from_pose(self, pose: PoseResult, w: int, h: int) -> np.ndarray:
        mask = np.zeros((h, w), dtype=np.uint8)
        if not pose.success:
            return mask
        indices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        pts = []
        for i in indices:
            if i >= len(LANDMARK_NAMES):
                break
            name = LANDMARK_NAMES[i]
            if name in pose.landmarks:
                x, y, vis = pose.landmarks[name]
                if vis > 0.2:
                    pts.append([int(x), int(y)])
        if len(pts) < 3:
            return mask
        c = np.mean(pts, axis=0)
        rad = max(40, int(np.max(np.linalg.norm(np.array(pts) - c, axis=1)) * 1.8))
        cv2.circle(mask, (int(c[0]), int(c[1])), rad, 255, -1)
        return mask

    def _hair_from_face(self, face: np.ndarray, pose: PoseResult, w: int, h: int) -> np.ndarray:
        """Upper head / hair band above the face ellipse (protected zone, not garment)."""
        hair = np.zeros((h, w), dtype=np.uint8)
        ys, xs = np.where(face > 80)
        if len(ys) == 0:
            return hair
        fy0, fy1 = int(ys.min()), int(ys.max())
        fx0, fx1 = int(xs.min()), int(xs.max())
        fh = max(12, fy1 - fy0)
        fw = max(12, fx1 - fx0)
        y0 = max(0, fy0 - int(fh * 1.35))
        y1 = fy0 + max(3, fh // 5)
        pad = max(8, fw // 6)
        x0, x1 = max(0, fx0 - pad), min(w, fx1 + pad)
        hair[y0:y1, x0:x1] = 255
        hair = np.maximum(hair, (face > 80).astype(np.uint8) * 255)
        hair = cv2.GaussianBlur(hair, (11, 11), 0)
        return hair

    def build(
        self,
        image_bytes: bytes,
        pose: PoseResult,
        reuse_person_mask_u8: Optional[np.ndarray] = None,
    ) -> SegmentationPack:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_rgb = np.array(image)
        h, w = image_rgb.shape[:2]

        self._last_seg_source = "unknown"
        if reuse_person_mask_u8 is not None:
            pm = _ensure_hw(reuse_person_mask_u8, h, w)
            if pm.dtype != np.uint8:
                pm = np.clip(pm, 0, 255).astype(np.uint8)
            self._last_seg_source = "reuse"
        else:
            self._init_sam_if_needed(image_rgb)
            if self._sam is not None:
                self._sam.set_image(image_rgb)
                # center prompt
                cx, cy = w // 2, h // 2
                masks, scores, _ = self._sam.predict(
                    point_coords=np.array([[cx, cy]]),
                    point_labels=np.array([1]),
                    multimask_output=True,
                )
                if len(masks):
                    pm = (masks[np.argmax(scores)] * 255).astype(np.uint8)
                    self._last_seg_source = "sam"
                else:
                    sm = self._selfie_mask(image_rgb)
                    pm = (np.clip(sm, 0, 1) * 255).astype(np.uint8)
            else:
                sm = self._selfie_mask(image_rgb)
                pm = (np.clip(sm, 0, 1) * 255).astype(np.uint8)

        pm = _ensure_hw(pm, h, w)
        pm = _largest_component_mask(pm)
        torso = self._torso_from_pose(pose, w, h)
        if np.max(torso) < 30:
            torso = self._torso_from_person_mask(pm, w, h)
        area_ratio = float(np.mean(torso > 80))
        if area_ratio < 0.004:
            torso2 = self._torso_from_person_mask(pm, w, h)
            if float(np.mean(torso2 > 80)) > area_ratio:
                torso = torso2
                logger.info("Torso mask auto-retry: silhouette torso (pose quad area %.4f)", area_ratio)
        arms = self._arms_from_pose(pose, w, h)
        face = self._face_from_pose(pose, w, h)
        hair = self._hair_from_face(face, pose, w, h)

        # torso constrained to person
        torso = cv2.bitwise_and(torso, pm)
        torso = cv2.morphologyEx(torso, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8), iterations=1)
        
        # ====================================================================
        # CONFIT STABLE GARMENT ALIGNMENT - SEGMENTATION HARDENING
        # Apply edge sharpening and morphological cleanup for better masks
        # ====================================================================
        stable_alignment_enabled = os.getenv("TRYON_STABLE_ALIGNMENT", "1").lower() in ("1", "true", "yes")
        if stable_alignment_enabled:
            pm, torso = harden_segmentation(
                pm, torso,
                edge_sharpen=True,
                morphological_cleanup=True,
            )
            logger.debug("Stable alignment: segmentation hardened")
        
        clip = self._build_garment_clip_mask(pm, torso, h, w)
        src = self._last_seg_source if self._last_seg_source != "unknown" else "grabcut"
        seg_conf = self._confidence_for_source(src, pm, image_rgb)
        return SegmentationPack(
            person_mask=pm,
            torso_mask=torso,
            arms_mask=arms,
            face_mask=face,
            hair_mask=hair,
            garment_clip_mask=clip,
            segmentation_confidence=seg_conf,
            segmentation_source=src,
        )

    def close(self) -> None:
        if self._selfie is not None:
            self._selfie.close()
            self._selfie = None
        if self._selfie_tasks is not None:
            self._selfie_tasks.close()
            self._selfie_tasks = None
        self._sam = None
