"""
CONFIT Backend — Garment Processing Module
=========================================
Processes garment images for virtual try-on:
- Background removal/segmentation
- Garment warping to fit body pose
- Size and proportion adjustment
- Shadow and lighting extraction

Features:
- Category-aware processing
- Perspective warping
- Fabric texture preservation
- Edge refinement
"""

import logging
import asyncio
import os
import numpy as np
from typing import TYPE_CHECKING, Optional, Dict, List, Tuple, Any

if TYPE_CHECKING:
    from services.tryon.physics.material_engine import MaterialProperties
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import cv2

try:
    from PIL import Image, ImageFilter, ImageDraw, ImageTransform
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

logger = logging.getLogger(__name__)

# Thread pool for image processing
_executor = ThreadPoolExecutor(max_workers=4)


def detect_category_from_name(garment_name: str, garment_metadata: Optional[Dict[str, Any]] = None) -> str:
    """String category for affine pipeline: tops, bottoms, dresses, outerwear."""
    if garment_metadata:
        gc = garment_metadata.get("category") or garment_metadata.get("garment_category")
        if isinstance(gc, str) and gc.strip():
            return gc.strip().lower()
    name_lower = garment_name.lower()
    dress_keywords = ("dress", "gown", "romper", "jumpsuit")
    outer_keywords = ("jacket", "coat", "blazer", "cardigan", "vest")
    bottoms_keywords = ("pants", "jeans", "shorts", "skirt", "trousers", "leggings")
    for kw in dress_keywords:
        if kw in name_lower:
            return "dresses"
    for kw in outer_keywords:
        if kw in name_lower:
            return "outerwear"
    for kw in bottoms_keywords:
        if kw in name_lower:
            return "bottoms"
    return "tops"


def compute_garment_target_region(
    body_landmarks: Dict[str, Tuple[float, float, float]],
    category: str,
    image_shape: Tuple[int, int],
) -> Tuple[int, int, int, int]:
    """
    Torso placement bbox (x, y, width, height) in pixels from pose landmarks.
    ``image_shape`` is (height, width).
    """
    h_img, w_img = image_shape[0], image_shape[1]
    ls = body_landmarks.get("left_shoulder")
    rs = body_landmarks.get("right_shoulder")
    lh = body_landmarks.get("left_hip")
    rh = body_landmarks.get("right_hip")
    if not ls or not rs:
        return 0, 0, w_img, h_img
    shoulder_width = abs(float(ls[0]) - float(rs[0]))
    shoulder_width = max(shoulder_width, 40.0)
    pad = 0.25
    target_width = int(shoulder_width * (1.0 + 2.0 * pad))
    top_y = int(min(float(ls[1]), float(rs[1])) - shoulder_width * 0.15)
    center_x = (float(ls[0]) + float(rs[0])) * 0.5
    cat = (category or "tops").lower()
    if lh and rh:
        hip_y = max(float(lh[1]), float(rh[1]))
        if cat == "tops":
            target_height = int(hip_y - top_y + shoulder_width * 0.1)
        elif cat == "dresses":
            torso_len = hip_y - top_y
            target_height = int(max(torso_len * 2.0, hip_y - top_y + shoulder_width * 0.15))
        else:
            target_height = int(hip_y - top_y + shoulder_width * 0.1)
    else:
        target_height = int(shoulder_width * 2.2)
    x = int(center_x - target_width / 2)
    y = int(top_y)
    x = max(0, min(x, w_img - 1))
    y = max(0, min(y, h_img - 1))
    target_width = min(target_width, w_img - x)
    target_height = min(target_height, h_img - y)
    return x, y, max(1, target_width), max(1, target_height)


def match_lighting_warped_garment(
    user_image_rgb: np.ndarray,
    warped_garment_rgba: np.ndarray,
    clothing_bbox: Tuple[int, int, int, int],
) -> np.ndarray:
    """Subtle LAB L-channel match; person and garment RGB (e.g. PIL / try-on pipeline)."""
    x, y, w_r, h_r = clothing_bbox
    h, w = user_image_rgb.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(w, x + w_r), min(h, y + h_r)
    roi = user_image_rgb[y0:y1, x0:x1]
    if roi.size == 0 or warped_garment_rgba.shape[2] < 4:
        return warped_garment_rgba
    garment_lab = cv2.cvtColor(warped_garment_rgba[:, :, :3], cv2.COLOR_RGB2LAB).astype(np.float32)
    roi_lab = cv2.cvtColor(roi, cv2.COLOR_RGB2LAB).astype(np.float32)
    a = (warped_garment_rgba[:, :, 3].astype(np.float32) / 255.0) > 0.08
    if not np.any(a):
        return warped_garment_rgba
    roi_l_mean = float(np.mean(roi_lab[:, :, 0]))
    roi_l_std = float(np.std(roi_lab[:, :, 0])) + 1e-6
    gar_l = garment_lab[:, :, 0]
    gar_mask = warped_garment_rgba[:, :, 3].astype(np.float32) / 255.0
    gar_l_mean = float(np.sum(gar_l * gar_mask) / (np.sum(gar_mask) + 1e-6))
    gar_l_std = float(
        np.sqrt(np.sum(((gar_l - gar_l_mean) ** 2) * gar_mask) / (np.sum(gar_mask) + 1e-6))
    ) + 1e-6
    blend_factor = 0.3
    transferred = (gar_l - gar_l_mean) * (roi_l_std / gar_l_std) + roi_l_mean
    garment_lab[:, :, 0] = np.clip(
        gar_l * (1.0 - blend_factor) + transferred * blend_factor,
        0.0,
        255.0,
    )
    out_rgb = cv2.cvtColor(garment_lab.astype(np.uint8), cv2.COLOR_LAB2RGB)
    result = warped_garment_rgba.copy()
    result[:, :, :3] = out_rgb
    return result


def align_garment_to_body(
    garment_rgba: np.ndarray,
    body_landmarks: Dict[str, Tuple[float, float, float]],
    frame_size: Tuple[int, int],
    category: str = "tops",
) -> np.ndarray:
    """
    Map a flat garment image onto body anchors with a single affine transform.

    Uses anatomical shoulder/hip landmarks (pixel x, y + visibility). Garment
    source points are top-left / top-right / bottom-center in garment space;
    destinations use image positions for **left_shoulder** and **right_shoulder**
    (MediaPipe anatomical names) so the garment upright direction matches the
    body without an extra mirror flip based on image x-order.

    Args:
        garment_rgba: RGBA uint8 image.
        body_landmarks: Dict like ``pose.landmarks`` (x, y in pixels, visibility).
        frame_size: (width, height) of the output frame.
        category: ``tops``, ``bottoms``, or ``dresses`` / ``full_body`` for anchor layout.

    Returns:
        Warped RGBA on a canvas of ``frame_size``; unchanged garment on failure.
    """
    if garment_rgba is None or garment_rgba.size == 0:
        return garment_rgba
    fw, fh = frame_size
    if fw < 2 or fh < 2:
        return garment_rgba

    ls = body_landmarks.get("left_shoulder")
    rs = body_landmarks.get("right_shoulder")
    lh = body_landmarks.get("left_hip")
    rh = body_landmarks.get("right_hip")
    if not ls or not rs or ls[2] < 0.15 or rs[2] < 0.15:
        return garment_rgba
    if not lh or not rh:
        lh = (ls[0] * 0.95, ls[1] + abs(rs[0] - ls[0]) * 1.2, min(ls[2], rs[2]))
        rh = (rs[0] * 1.05, rs[1] + abs(rs[0] - ls[0]) * 1.2, min(ls[2], rs[2]))

    def _mid(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float]:
        return ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5)

    body_shoulder_mid = _mid(ls, rs)
    body_hip_mid = _mid(lh, rh)

    gh, gw = garment_rgba.shape[:2]
    src = np.float32(
        [
            [gw * 0.15, gh * 0.05],
            [gw * 0.85, gh * 0.05],
            [gw * 0.5, gh * 0.95],
        ]
    )

    span = max(8.0, float(body_hip_mid[1] - body_shoulder_mid[1]))
    shoulder_width_px = max(8.0, abs(float(ls[0]) - float(rs[0])))
    padding = shoulder_width_px * 0.20
    if category.strip().lower() in ("bottoms",):
        dst = np.float32(
            [
                [lh[0], lh[1]],
                [rh[0], rh[1]],
                [body_hip_mid[0], body_hip_mid[1] + span * 0.35],
            ]
        )
    else:
        dst = np.float32(
            [
                [ls[0] - padding * 0.3, ls[1] - shoulder_width_px * 0.08],
                [rs[0] + padding * 0.3, rs[1] - shoulder_width_px * 0.08],
                [body_hip_mid[0], body_hip_mid[1] + shoulder_width_px * 0.08],
            ]
        )

    m = cv2.getAffineTransform(src, dst)
    out = cv2.warpAffine(
        garment_rgba,
        m,
        (fw, fh),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    return out


def _initial_garment_mask(img_rgb: np.ndarray, threshold: int) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Build coarse foreground mask: white backdrop + largest edge contour."""
    h, w = img_rgb.shape[:2]
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    _, mask_white = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)

    edges = cv2.Canny(gray, 50, 150)
    kernel = np.ones((5, 5), np.uint8)
    edges_dilated = cv2.dilate(edges, kernel, iterations=2)

    contours, _ = cv2.findContours(
        edges_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    mask_contour = np.zeros((h, w), dtype=np.uint8)
    largest_contour = None
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        cv2.drawContours(mask_contour, [largest_contour], -1, 255, -1)

    # Prefer intersection (AND) to avoid including large non-white backgrounds.
    # If intersection is too small (edge failure), fall back to OR.
    mask_combined = cv2.bitwise_and(mask_white, mask_contour)
    if largest_contour is not None and cv2.contourArea(largest_contour) > 200:
        fill = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(fill, [largest_contour], -1, 255, -1)
        mask_combined = cv2.bitwise_and(mask_combined, fill)

    # If intersection produced too little foreground, revert to OR fallback.
    if int(cv2.countNonZero(mask_combined)) < int(h * w * 0.01):
        mask_combined = cv2.bitwise_or(mask_white, mask_contour)

    mask_combined = cv2.morphologyEx(
        mask_combined, cv2.MORPH_CLOSE, kernel, iterations=2
    )
    mask_combined = cv2.morphologyEx(
        mask_combined, cv2.MORPH_OPEN, kernel, iterations=1
    )
    return mask_combined, largest_contour


def _grabcut_refine_mask(img_rgb: np.ndarray, init_mask_u8: np.ndarray) -> np.ndarray:
    """GrabCut refinement from coarse mask (studio / catalog photos)."""
    h, w = img_rgb.shape[:2]
    bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    m = (init_mask_u8 > 127).astype(np.uint8) * 255
    if int(cv2.countNonZero(m)) < 400:
        return init_mask_u8

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    sure_fg = cv2.erode(m, k, iterations=3)
    dil = cv2.dilate(m, k, iterations=10)
    sure_bg = cv2.bitwise_not(dil)

    if int(cv2.countNonZero(sure_fg)) < 150:
        sure_fg = cv2.erode(m, k, iterations=1)

    mask_gc = np.full((h, w), cv2.GC_PR_BGD, dtype=np.uint8)
    mask_gc[m > 127] = cv2.GC_PR_FGD
    mask_gc[sure_bg > 127] = cv2.GC_BGD
    mask_gc[sure_fg > 127] = cv2.GC_FGD

    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    iters = max(1, min(8, int(os.getenv("TRYON_GARMENT_GRABCUT_ITERS", "3"))))
    try:
        cv2.grabCut(bgr, mask_gc, None, bgd, fgd, iters, cv2.GC_INIT_WITH_MASK)
    except cv2.error as e:
        logger.debug("GrabCut garment refine skipped: %s", e)
        return init_mask_u8

    binm = np.where((mask_gc == cv2.GC_BGD) | (mask_gc == cv2.GC_PR_BGD), 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(binm, (3, 3), 0)


def _refine_alpha_guided(img_rgb: np.ndarray, alpha_u8: np.ndarray) -> np.ndarray:
    """Edge-preserving alpha (guided filter when opencv-contrib ximgproc is available)."""
    a = np.clip(alpha_u8.astype(np.float32) / 255.0, 0.0, 1.0)
    bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    try:
        import cv2.ximgproc as xip

        r = max(4, min(16, int(os.getenv("TRYON_GARMENT_GUIDED_RADIUS", "6"))))
        eps = float(os.getenv("TRYON_GARMENT_GUIDED_EPS", "1e-3"))
        a = xip.guidedFilter(bgr, a, r, eps)
    except Exception:
        a_u8 = (a * 255.0).astype(np.uint8)
        a_u8 = cv2.bilateralFilter(a_u8, d=7, sigmaColor=40, sigmaSpace=40)
        a = a_u8.astype(np.float32) / 255.0
    return np.clip(a * 255.0, 0, 255).astype(np.uint8)


def _suppress_studio_background_soft(img_rgb: np.ndarray, alpha_u8: np.ndarray) -> np.ndarray:
    """
    Remove flat gray studio backdrop without wiping low-saturation fabric.
    Only clears pixels that are already low-alpha (likely background bleed).
    """
    r = img_rgb[:, :, 0].astype(np.int16)
    g = img_rgb[:, :, 1].astype(np.int16)
    b = img_rgb[:, :, 2].astype(np.int16)
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = (mx - mn).astype(np.int16)
    flat = sat < 20
    mid = (r + g + b) > 200
    mid &= (r + g + b) < 540
    weak = alpha_u8.astype(np.float32) < 95
    studio = flat & mid & weak
    out = alpha_u8.copy()
    out[studio] = 0
    return out


def _suppress_human_parts_from_garment(
    img_rgb: np.ndarray,
    alpha_u8: np.ndarray,
    category: "GarmentCategory",
) -> np.ndarray:
    """
    Suppress visible body parts from product photos (hands/neck/face) in garment alpha.

    This targets skin-like blobs that leak from mannequin/model photos, especially for tops.
    It avoids aggressive removals for categories where skin-like tones may be valid pixels.
    """
    if category not in (
        GarmentCategory.TOPS,
        GarmentCategory.OUTERWEAR,
        GarmentCategory.DRESSES,
        GarmentCategory.FULL_BODY,
    ):
        return alpha_u8

    h, w = alpha_u8.shape[:2]
    if h < 8 or w < 8:
        return alpha_u8

    # Skin detection (union of YCrCb and HSV heuristics).
    ycrcb = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2YCrCb)
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    skin_y = cv2.inRange(ycrcb, np.array([0, 133, 77], np.uint8), np.array([255, 173, 127], np.uint8))
    skin_h = cv2.inRange(hsv, np.array([0, 30, 45], np.uint8), np.array([25, 185, 255], np.uint8))
    skin = cv2.bitwise_and(cv2.bitwise_or(skin_y, skin_h), (alpha_u8 > 35).astype(np.uint8) * 255)
    if int(cv2.countNonZero(skin)) < int(h * w * 0.001):
        return alpha_u8

    num, labels, stats, cent = cv2.connectedComponentsWithStats((skin > 0).astype(np.uint8), connectivity=8)
    if num <= 1:
        return alpha_u8

    alpha_area = float(np.count_nonzero(alpha_u8 > 20)) + 1.0
    out = alpha_u8.copy()
    for i in range(1, num):
        x, y, cw, ch, area = stats[i]
        cx, cy = cent[i]
        area_ratio = float(area) / alpha_area
        touches_border = x <= 1 or y <= 1 or (x + cw) >= (w - 1) or (y + ch) >= (h - 1)
        side_upper_blob = (cy < h * 0.68) and (cx < w * 0.32 or cx > w * 0.68) and area_ratio < 0.10
        top_center_blob = (cy < h * 0.30) and (w * 0.34 <= cx <= w * 0.66) and area_ratio < 0.14
        if touches_border or side_upper_blob or top_center_blob:
            out[labels == i] = 0

    # Light feather around removed skin regions to avoid harsh holes.
    removed = ((alpha_u8 > 20) & (out == 0)).astype(np.uint8) * 255
    if int(cv2.countNonZero(removed)) > 0:
        soften = cv2.GaussianBlur(removed, (5, 5), 0)
        out = np.where(soften > 18, np.minimum(out, 180), out).astype(np.uint8)

    return out


class GarmentCategory(Enum):
    """Garment categories for placement and processing."""
    TOPS = "tops"
    BOTTOMS = "bottoms"
    DRESSES = "dresses"
    OUTERWEAR = "outerwear"
    SHOES = "shoes"
    ACCESSORIES = "accessories"
    BAGS = "bags"
    FULL_BODY = "full_body"


# Category keywords for detection
CATEGORY_KEYWORDS = {
    GarmentCategory.DRESSES: [
        "dress", "gown", "jumpsuit", "romper", "overall", "suit", "onesie",
        "bodysuit", "caftan", "maxi", "midi", "mini dress"
    ],
    GarmentCategory.OUTERWEAR: [
        "jacket", "coat", "blazer", "cardigan", "hoodie", "parka",
        "windbreaker", "bomber", "trench", "peacoat", "overcoat"
    ],
    GarmentCategory.BOTTOMS: [
        "pants", "trousers", "jeans", "shorts", "skirt", "leggings",
        "chinos", "joggers", "sweatpants", "culottes", "cargo"
    ],
    GarmentCategory.TOPS: [
        "shirt", "t-shirt", "tshirt", "top", "blouse", "sweater", "polo",
        "vest", "tank", "tee", "henley", "pullover", "crop top", "tunic"
    ],
    GarmentCategory.SHOES: [
        "shoe", "boot", "sneaker", "heel", "loafer", "flat", "sandal",
        "pump", "oxford", "trainer"
    ],
    GarmentCategory.ACCESSORIES: [
        "scarf", "belt", "hat", "sunglasses", "watch", "necklace",
        "bracelet", "earring", "glove"
    ],
    GarmentCategory.BAGS: [
        "bag", "purse", "handbag", "backpack", "tote", "clutch",
        "crossbody", "shoulder bag"
    ],
}


@dataclass
class ProcessedGarment:
    """Result of garment processing."""
    success: bool
    image: Optional["Image.Image"] = None
    mask: Optional[np.ndarray] = None
    category: GarmentCategory = GarmentCategory.TOPS
    original_size: Tuple[int, int] = (0, 0)
    processed_size: Tuple[int, int] = (0, 0)
    bounding_box: Tuple[int, int, int, int] = (0, 0, 0, 0)  # x, y, w, h
    dominant_colors: List[Tuple[int, int, int]] = field(default_factory=list)
    texture_type: str = "smooth"
    error_message: Optional[str] = None


@dataclass
class WarpParams:
    """Parameters for garment warping."""
    scale_x: float = 1.0
    scale_y: float = 1.0
    skew_x: float = 0.0
    skew_y: float = 0.0
    perspective_strength: float = 0.0
    rotation: float = 0.0
    offset_x: float = 0.0
    offset_y: float = 0.0


class GarmentProcessor:
    """
    Processes garment images for virtual try-on.
    Handles background removal, warping, and color extraction.
    """

    def __init__(self):
        self._initialized = PIL_AVAILABLE
        if self._initialized:
            logger.info("GarmentProcessor initialized")
        else:
            logger.warning("GarmentProcessor: PIL not available")

    def detect_category(self, garment_name: str) -> GarmentCategory:
        """
        Detect garment category from name.
        
        Args:
            garment_name: Name of the garment
            
        Returns:
            Detected GarmentCategory
        """
        name_lower = garment_name.lower()

        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in name_lower for kw in keywords):
                return category

        return GarmentCategory.TOPS

    def analyze_fabric_material(
        self,
        rgba: np.ndarray,
        garment_name: str = "",
        *,
        use_cache: bool = True,
    ) -> "MaterialProperties":
        """
        Fabric Material Intelligence — classifies garment texture and returns physics/lighting parameters.
        Delegates to the shared material engine (single pipeline; results cached per garment image).
        """
        from services.tryon.physics.material_engine import analyze_garment_material

        return analyze_garment_material(rgba, garment_name, use_cache=use_cache)

    def _remove_background_sync(
        self,
        image: "Image.Image",
        category: "GarmentCategory" = GarmentCategory.TOPS,
        threshold: int = 250
    ) -> Tuple["Image.Image", np.ndarray]:
        """
        Remove background from garment image (synchronous).
        Coarse mask (white + edges) → optional GrabCut → guided alpha → soft studio suppression.
        """
        if not PIL_AVAILABLE:
            return image, np.ones((image.height, image.width), dtype=np.uint8) * 255

        # Convert to RGBA
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        img_array = np.array(image)
        rgb = img_array[:, :, :3].copy()

        mask_combined, _ = _initial_garment_mask(rgb, threshold)

        use_gc = os.getenv("TRYON_GARMENT_GRABCUT", "1").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if use_gc:
            mask_combined = _grabcut_refine_mask(rgb, mask_combined)

        alpha = mask_combined.astype(np.float32)
        alpha = cv2.GaussianBlur(alpha, (5, 5), 0)

        use_guided = os.getenv("TRYON_GARMENT_GUIDED_ALPHA", "1").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if use_guided:
            alpha_u8 = np.clip(alpha, 0, 255).astype(np.uint8)
            alpha_u8 = _refine_alpha_guided(rgb, alpha_u8)
        else:
            alpha_u8 = np.clip(alpha, 0, 255).astype(np.uint8)

        alpha_u8 = _suppress_studio_background_soft(rgb, alpha_u8)
        alpha_u8 = _suppress_human_parts_from_garment(rgb, alpha_u8, category)

        # Final alpha cleanup: remove tiny specks/bleed that would "sparkle" after warping.
        # Keep only significant connected components of the garment foreground.
        try:
            fg = (alpha_u8 > 25).astype(np.uint8)
            num, labels, stats, _centroids = cv2.connectedComponentsWithStats(fg, connectivity=8)
            if num > 1:
                areas = stats[1:, cv2.CC_STAT_AREA]
                max_area = float(np.max(areas)) if areas.size else 0.0
                # Keep components with at least 1% of max area.
                keep = [i + 1 for i, a in enumerate(areas) if a >= max_area * 0.01]
                if keep:
                    cleaned = np.isin(labels, keep)
                    alpha_u8 = np.where(cleaned, alpha_u8, 0).astype(np.uint8)
        except Exception as e:
            logger.debug("Alpha cleanup skipped: %s", e)

        # Hard threshold very low alpha to avoid faint background bleed.
        # Raising this reduces "sparkle specks" after warp/blend.
        hard_thr = int(os.getenv("TRYON_GARMENT_ALPHA_HARD_THR", "20"))
        hard_thr = max(0, min(60, hard_thr))
        alpha_u8[alpha_u8 < hard_thr] = 0

        result = img_array.copy()
        result[:, :, 3] = alpha_u8

        return Image.fromarray(result, "RGBA"), alpha_u8

    def _extract_colors(
        self,
        image: "Image.Image",
        mask: Optional[np.ndarray] = None,
        n_colors: int = 5
    ) -> List[Tuple[int, int, int]]:
        """
        Extract dominant colors from garment.
        
        Args:
            image: PIL Image
            mask: Optional mask for garment region
            n_colors: Number of colors to extract
            
        Returns:
            List of RGB color tuples
        """
        if not PIL_AVAILABLE:
            return []

        img_array = np.array(image.convert("RGB"))

        if mask is not None:
            # Only consider masked pixels
            pixels = img_array[mask > 128]
        else:
            pixels = img_array.reshape(-1, 3)

        if len(pixels) == 0:
            return [(128, 128, 128)]

        # Use k-means clustering for color extraction
        pixels = np.float32(pixels)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.1)
        _, labels, centers = cv2.kmeans(
            pixels, min(n_colors, len(pixels)), None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
        )

        # Get most common colors
        unique, counts = np.unique(labels, return_counts=True)
        sorted_indices = np.argsort(-counts)

        colors = []
        for idx in sorted_indices[:n_colors]:
            center = centers[unique[idx]]
            colors.append(tuple(int(c) for c in center))

        return colors

    def _detect_texture(self, image: "Image.Image", mask: np.ndarray) -> str:
        """
        Detect fabric texture type.
        
        Args:
            image: PIL Image
            mask: Garment mask
            
        Returns:
            Texture type string
        """
        if not PIL_AVAILABLE:
            return "smooth"

        img_array = np.array(image.convert("RGB"))
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        # Apply mask
        masked_gray = gray.copy()
        masked_gray[mask < 128] = 0

        # Compute texture features using Local Binary Patterns
        try:
            # OpenCV migrated SIFT from contrib.xfeatures2d to main.
            # Prefer cv2.SIFT_create when available to avoid deprecation warnings.
            if hasattr(cv2, "SIFT_create"):
                sift = cv2.SIFT_create()
            else:
                from cv2.xfeatures2d import SIFT_create  # type: ignore

                sift = SIFT_create()
            keypoints = sift.detect(masked_gray, None)
            n_keypoints = len(keypoints)
        except Exception:
            # Fallback: use edge density
            edges = cv2.Canny(masked_gray, 50, 150)
            edge_density = np.sum(edges > 0) / (np.sum(mask > 128) + 1e-6)
            n_keypoints = int(edge_density * 1000)

        # Classify texture
        if n_keypoints < 50:
            return "smooth"
        elif n_keypoints < 150:
            return "light_texture"
        elif n_keypoints < 300:
            return "medium_texture"
        else:
            return "heavy_texture"

    def _warp_garment_sync(
        self,
        garment: "Image.Image",
        target_width: int,
        target_height: int,
        params: WarpParams,
        body_angle: float = 0.0
    ) -> "Image.Image":
        """
        Warp garment to fit body pose (synchronous).
        
        Args:
            garment: PIL Image of garment (RGBA)
            target_width: Target width
            target_height: Target height
            params: Warp parameters
            body_angle: Body rotation angle in degrees
            
        Returns:
            Warped PIL Image
        """
        if not PIL_AVAILABLE:
            return garment

        # Apply scaling
        new_width = int(target_width * params.scale_x)
        new_height = int(target_height * params.scale_y)

        # Resize garment
        garment_resized = garment.resize(
            (new_width, new_height), Image.Resampling.LANCZOS
        )

        # Apply perspective transform if needed
        if params.perspective_strength != 0:
            w, h = garment_resized.size
            strength = params.perspective_strength

            # Define perspective transform points
            # Slight taper at bottom for natural look
            src_points = [(0, 0), (w, 0), (w, h), (0, h)]
            dst_points = [
                (w * strength * 0.1, 0),
                (w - w * strength * 0.1, 0),
                (w, h),
                (0, h)
            ]

            # Create perspective transform matrix
            src_array = np.array(src_points, dtype=np.float32)
            dst_array = np.array(dst_points, dtype=np.float32)

            matrix = cv2.getPerspectiveTransform(src_array, dst_array)

            # Apply transform
            img_array = np.array(garment_resized)
            warped = cv2.warpPerspective(
                img_array, matrix, (w, h),
                flags=cv2.INTER_LANCZOS4,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0, 0)
            )
            garment_resized = Image.fromarray(warped, "RGBA")

        # Apply rotation for body angle
        total_rotation = params.rotation + body_angle
        if abs(total_rotation) > 1:
            garment_resized = garment_resized.rotate(
                total_rotation,
                expand=True,
                resample=Image.Resampling.BICUBIC
            )

        return garment_resized

    async def process(
        self,
        garment_image: "Image.Image",
        garment_name: str = "garment"
    ) -> ProcessedGarment:
        """
        Process a garment image for try-on.
        
        Args:
            garment_image: PIL Image of garment
            garment_name: Name for category detection
            
        Returns:
            ProcessedGarment with processed image and metadata
        """
        if not self._initialized:
            return ProcessedGarment(
                success=False,
                error_message="PIL not available"
            )

        loop = asyncio.get_event_loop()

        try:
            # Detect category
            category = self.detect_category(garment_name)
            logger.info(f"Detected category: {category.value} for '{garment_name}'")

            # Store original size
            original_size = garment_image.size

            # Remove background
            processed, mask = await loop.run_in_executor(
                _executor, self._remove_background_sync, garment_image, category
            )

            # Extract colors
            colors = await loop.run_in_executor(
                _executor, self._extract_colors, processed, mask
            )

            # Detect texture
            texture = await loop.run_in_executor(
                _executor, self._detect_texture, processed, mask
            )

            # Find bounding box
            if mask is not None:
                coords = cv2.findNonZero(mask)
                if coords is not None:
                    x, y, w, h = cv2.boundingRect(coords)
                    bounding_box = (x, y, w, h)
                else:
                    bounding_box = (0, 0, *original_size)
            else:
                bounding_box = (0, 0, *original_size)

            return ProcessedGarment(
                success=True,
                image=processed,
                mask=mask,
                category=category,
                original_size=original_size,
                processed_size=processed.size,
                bounding_box=bounding_box,
                dominant_colors=colors,
                texture_type=texture
            )

        except Exception as e:
            logger.error(f"Garment processing failed: {e}")
            return ProcessedGarment(
                success=False,
                error_message=str(e)
            )

    async def warp_to_body(
        self,
        garment: ProcessedGarment,
        target_width: int,
        target_height: int,
        body_angle: float = 0.0,
        fit_type: str = "regular"
    ) -> ProcessedGarment:
        """
        Warp processed garment to fit body dimensions.
        
        Args:
            garment: ProcessedGarment from process()
            target_width: Target width for garment
            target_height: Target height for garment
            body_angle: Body rotation angle
            fit_type: "tight", "regular", or "loose"
            
        Returns:
            New ProcessedGarment with warped image
        """
        if not garment.success or garment.image is None:
            return garment

        loop = asyncio.get_event_loop()

        # Calculate warp parameters based on category and fit
        fit_multipliers = {"tight": 0.92, "regular": 1.0, "loose": 1.08}
        fit_scale = fit_multipliers.get(fit_type, 1.0)

        # Category-specific adjustments
        perspective_strength = 0.0
        if garment.category == GarmentCategory.TOPS:
            perspective_strength = 0.05  # Slight taper for tops
        elif garment.category == GarmentCategory.DRESSES:
            perspective_strength = 0.08  # More taper for dresses
        elif garment.category == GarmentCategory.OUTERWEAR:
            perspective_strength = 0.03  # Minimal taper for outerwear

        params = WarpParams(
            scale_x=fit_scale,
            scale_y=fit_scale,
            perspective_strength=perspective_strength,
            rotation=0.0
        )

        try:
            warped = await loop.run_in_executor(
                _executor,
                self._warp_garment_sync,
                garment.image,
                target_width,
                target_height,
                params,
                body_angle
            )

            return ProcessedGarment(
                success=True,
                image=warped,
                mask=garment.mask,
                category=garment.category,
                original_size=garment.original_size,
                processed_size=warped.size,
                bounding_box=garment.bounding_box,
                dominant_colors=garment.dominant_colors,
                texture_type=garment.texture_type
            )

        except Exception as e:
            logger.error(f"Garment warping failed: {e}")
            return ProcessedGarment(
                success=False,
                error_message=str(e)
            )

    def health_check(self) -> Dict[str, Any]:
        """Return health status."""
        return {
            "status": "ok" if self._initialized else "degraded",
            "service": "garment-processor",
            "pil_available": PIL_AVAILABLE,
            "opencv_available": True  # cv2 is imported at module level
        }
