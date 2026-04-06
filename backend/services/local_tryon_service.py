"""
CONFIT Backend — Local Virtual Try-On Service
==============================================
Self-contained try-on processing using PIL for image manipulation.
No external API dependencies - works entirely locally.

Features:
- Garment overlay with smart positioning
- Edge feathering for natural blending
- Category-aware placement (tops, bottoms, dresses, etc.)
- Luminance matching for seamless integration
"""

import logging
import asyncio
import tempfile
import os
from typing import Any, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import base64

try:
    from PIL import Image, ImageFilter, ImageChops
    import numpy as np
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False
    Image = None
    np = None

logger = logging.getLogger(__name__)

# Thread pool for image processing
_executor = ThreadPoolExecutor(max_workers=4)

# Garment category keywords
CATEGORY_KEYWORDS = {
    'dresses': ['dress', 'gown', 'jumpsuit', 'romper', 'overall', 'suit', 'onesie', 'bodysuit'],
    'outerwear': ['jacket', 'coat', 'blazer', 'cardigan', 'hoodie', 'parka', 'windbreaker', 'bomber'],
    'bottoms': ['pants', 'trousers', 'jeans', 'shorts', 'skirt', 'leggings', 'chinos', 'joggers'],
    'tops': ['shirt', 't-shirt', 'tshirt', 'top', 'blouse', 'sweater', 'polo', 'vest', 'tank', 'tee'],
    'shoes': ['shoe', 'boot', 'sneaker', 'heel', 'loafer', 'flat', 'sandal'],
    'accessories': ['scarf', 'belt', 'hat', 'sunglasses', 'watch'],
}


def detect_category(name: str) -> str:
    """Detect garment category from name."""
    name_lower = name.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return category
    return 'tops'


def decode_base64_image(data: str) -> Optional["Image.Image"]:
    """Decode base64 string to PIL Image."""
    if not DEPS_AVAILABLE:
        return None
    
    # Remove data URI prefix if present
    if ',' in data:
        data = data.split(',', 1)[1]
    
    try:
        img_bytes = base64.b64decode(data)
        return Image.open(BytesIO(img_bytes)).convert('RGBA')
    except Exception as e:
        logger.error(f"Failed to decode base64 image: {e}")
        return None


def encode_image_base64(img: "Image.Image", format: str = "PNG") -> str:
    """Encode PIL Image to base64 data URI."""
    buffer = BytesIO()
    img = img.convert('RGBA') if format == 'PNG' else img.convert('RGB')
    img.save(buffer, format=format, quality=92)
    b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/{format.lower()};base64,{b64}"


def download_image(url: str) -> Optional["Image.Image"]:
    """Download image from URL."""
    import urllib.request
    
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            img_data = response.read()
            return Image.open(BytesIO(img_data)).convert('RGBA')
    except Exception as e:
        logger.error(f"Failed to download image from {url}: {e}")
        return None


def get_placement_for_category(
    category: str,
    person_width: int,
    person_height: int,
    garment_width: int,
    garment_height: int,
    subject_bbox: Optional[Tuple[int, int, int, int]] = None,
) -> Tuple[int, int, int, int]:
    """
    Calculate placement position based on garment category.
    Returns (x, y, scaled_width, scaled_height).
    """
    if subject_bbox:
        sx, sy, sw, sh = subject_bbox
    else:
        sx, sy, sw, sh = (
            int(person_width * 0.25),
            int(person_height * 0.15),
            int(person_width * 0.5),
            int(person_height * 0.75),
        )

    # Position & scale by category — bottoms need full leg coverage (not a hip patch)
    if category == 'bottoms':
        target_w = max(1, int(sw * 0.94))
        target_h = max(1, int(sh * 0.62))
        scale = min(target_w / garment_width, target_h / garment_height)
        scale = min(scale, 1.35)  # allow modest upscale for small product shots
        new_width = max(1, int(garment_width * scale))
        new_height = max(1, int(garment_height * scale))
        x = sx + (sw - new_width) // 2
        y = sy + int(sh * 0.34)  # waist / upper hip downward
    else:
        scale = min(sw * 0.82 / garment_width, sh * 0.6 / garment_height)
        scale = min(scale, 1.0)
        new_width = int(garment_width * scale)
        new_height = int(garment_height * scale)

        if category == 'tops':
            x = sx + (sw - new_width) // 2
            y = sy + int(sh * 0.18)
        elif category == 'dresses':
            x = sx + (sw - new_width) // 2
            y = sy + int(sh * 0.20)
            new_height = int(new_height * 1.2)
        elif category == 'outerwear':
            x = sx + (sw - new_width) // 2
            y = sy + int(sh * 0.14)
        elif category == 'shoes':
            x = sx + (sw - new_width) // 2
            y = sy + int(sh * 0.82)
        else:
            x = sx + (sw - new_width) // 2
            y = sy + int(sh * 0.2)

    # Keep the garment inside canvas bounds
    x = max(0, min(x, person_width - new_width))
    y = max(0, min(y, person_height - new_height))

    return x, y, new_width, new_height


def estimate_subject_bbox(person_img: "Image.Image") -> Optional[Tuple[int, int, int, int]]:
    """
    Estimate subject region using robust color/luminance heuristics.
    Works reasonably for full-body and street-scene photos.
    Returns (x, y, w, h) or None.
    """
    if not DEPS_AVAILABLE or np is None:
        return None

    arr = np.array(person_img.convert('RGB'), dtype=np.uint8)
    h, w, _ = arr.shape

    # Focus on where subjects usually are in camera photos
    x0, x1 = int(w * 0.2), int(w * 0.8)
    y0, y1 = int(h * 0.2), h
    roi = arr[y0:y1, x0:x1]
    if roi.size == 0:
        return None

    # Luminance + saturation proxy (max-min)
    lum = (0.299 * roi[:, :, 0] + 0.587 * roi[:, :, 1] + 0.114 * roi[:, :, 2]).astype(np.float32)
    sat = (roi.max(axis=2) - roi.min(axis=2)).astype(np.float32)

    # Subject-like mask: non-sky / non-flat background and darker/clothed regions
    mask = ((lum < 150) & (sat > 18)) | (lum < 95)
    ys, xs = np.where(mask)
    if ys.size < 250:
        return None

    # Robust percentiles to avoid outliers
    rx0 = int(np.percentile(xs, 8)) + x0
    rx1 = int(np.percentile(xs, 92)) + x0
    ry0 = int(np.percentile(ys, 6)) + y0
    ry1 = int(np.percentile(ys, 96)) + y0

    bw = max(1, rx1 - rx0)
    bh = max(1, ry1 - ry0)

    # Expand a bit for garment coverage
    pad_x = int(bw * 0.18)
    pad_y = int(bh * 0.08)
    bx0 = max(0, rx0 - pad_x)
    by0 = max(0, ry0 - pad_y)
    bx1 = min(w, rx1 + pad_x)
    by1 = min(h, ry1 + pad_y)

    if bx1 - bx0 < w * 0.12 or by1 - by0 < h * 0.2:
        return None
    return (bx0, by0, bx1 - bx0, by1 - by0)


def _soften_alpha_channel(img: "Image.Image", blur_radius: float = 2.5) -> "Image.Image":
    """Soften garment edges without circular/oval masks (avoids 'bubble' artifacts)."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    r, g, b, a = img.split()
    a_soft = a.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    out = Image.merge("RGBA", (r, g, b, a_soft))
    return out


def blend_images(
    person_img: "Image.Image",
    garment_img: "Image.Image",
    category: str,
    opacity: float = 0.92
) -> "Image.Image":
    """
    Blend garment onto person image with natural positioning.
    Uses alpha compositing with feathered edges.
    """
    if not DEPS_AVAILABLE:
        return person_img
    
    # Ensure RGBA mode
    if person_img.mode != 'RGBA':
        person_img = person_img.convert('RGBA')
    if garment_img.mode != 'RGBA':
        garment_img = garment_img.convert('RGBA')
    
    # Get dimensions
    pw, ph = person_img.size
    gw, gh = garment_img.size
    
    subject_bbox = estimate_subject_bbox(person_img)

    # Calculate placement anchored to estimated subject
    x, y, new_w, new_h = get_placement_for_category(
        category,
        pw,
        ph,
        gw,
        gh,
        subject_bbox=subject_bbox,
    )
    
    # Resize garment
    garment_resized = garment_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    # Soft edges only — do NOT multiply by an oval mask (that caused the circular "patch" bug)
    garment_resized = _soften_alpha_channel(garment_resized, blur_radius=2.8 if category == "bottoms" else 2.0)
    if opacity < 1.0:
        r, g, b, a = garment_resized.split()
        a = a.point(lambda p: int(p * opacity))
        garment_resized.putalpha(a)
    
    # Create composite
    result = person_img.copy()
    result.paste(garment_resized, (x, y), garment_resized)
    
    # Apply subtle color matching
    result = match_luminance(person_img, result, blend_factor=0.3)
    
    return result


def match_luminance(
    original: "Image.Image",
    result: "Image.Image",
    blend_factor: float = 0.3
) -> "Image.Image":
    """Match luminance of result to original for natural blending."""
    if not DEPS_AVAILABLE or np is None:
        return result
    
    orig_arr = np.array(original.convert('RGB'), dtype=np.float32)
    res_arr = np.array(result.convert('RGB'), dtype=np.float32)
    
    # Calculate luminance
    lum_orig = 0.299 * orig_arr[:,:,0] + 0.587 * orig_arr[:,:,1] + 0.114 * orig_arr[:,:,2]
    lum_res = 0.299 * res_arr[:,:,0] + 0.587 * res_arr[:,:,1] + 0.114 * res_arr[:,:,2]
    
    # Adjust result luminance toward original in transition areas
    lum_ratio = np.clip(lum_orig / (lum_res + 1e-6), 0.8, 1.2)
    lum_ratio_3d = np.stack([lum_ratio] * 3, axis=2)
    
    # Blend only where there's difference (garment area)
    diff = np.abs(res_arr - orig_arr).sum(axis=2)
    mask = (diff > 30).astype(np.float32) * blend_factor
    mask_3d = np.stack([mask] * 3, axis=2)
    
    adjusted = res_arr * (1 - mask_3d) + (res_arr * lum_ratio_3d) * mask_3d
    adjusted = np.clip(adjusted, 0, 255).astype(np.uint8)
    
    return Image.fromarray(adjusted).convert('RGBA')


class LocalTryOnService:
    """
    Self-contained virtual try-on service using PIL.
    No external API dependencies.
    """
    
    def __init__(self):
        self._initialized = DEPS_AVAILABLE
        if self._initialized:
            logger.info("LocalTryOnService initialized with PIL")
        else:
            logger.warning("LocalTryOnService: PIL/numpy not available")
    
    async def process(
        self,
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str = "garment",
        garment_category: Optional[str] = None,
    ) -> str:
        """
        Process virtual try-on using the unified classical TryOnService pipeline.
        """
        if not self._initialized:
            logger.warning("Dependencies not available, returning original image")
            return user_image_base64

        try:
            from services.tryon.tryon_service import TryOnService

            opts: Dict[str, Any] = {}
            category = (garment_category or "").strip().lower()
            valid = {"tops", "bottoms", "dresses", "outerwear", "shoes", "accessories", "bags"}
            if category in valid:
                opts["garment_category"] = category

            core = await TryOnService().process_classical(
                user_image_base64,
                garment_image_url,
                garment_name,
                opts,
            )
            if core.success and core.result_image:
                logger.info("Local try-on completed (TryOnService)")
                return core.result_image
            logger.warning("TryOnService failed: %s", core.error_message)
            return user_image_base64
        except Exception as e:
            logger.error(f"Local try-on failed: {e}")
            return user_image_base64
    
    def health_check(self) -> dict:
        """Return service health status."""
        return {
            "status": "ok" if self._initialized else "degraded",
            "service": "local-virtual-try-on",
            "dependencies": {
                "pil": DEPS_AVAILABLE,
                "numpy": np is not None
            }
        }
