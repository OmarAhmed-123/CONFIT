"""
CONFIT Backend - Image Processing Utilities
============================================
Provides helper functions for image encoding, decoding, validation,
and downloading from URLs used across the backend services.
"""

import base64
import io
import logging
import re
import tempfile
import os
import time as _time
from typing import Optional, Tuple
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)

# ── Temp file management ──────────────────────────────────────────────
TEMP_DIR = os.path.join(tempfile.gettempdir(), "confit_tryon")
os.makedirs(TEMP_DIR, exist_ok=True)


def cleanup_temp_files(max_age_seconds: int = 3600) -> int:
    """Remove temp files older than *max_age_seconds*. Returns count removed."""
    removed = 0
    now = _time.time()
    try:
        for fname in os.listdir(TEMP_DIR):
            fp = os.path.join(TEMP_DIR, fname)
            if os.path.isfile(fp) and now - os.path.getmtime(fp) > max_age_seconds:
                try:
                    os.remove(fp)
                    removed += 1
                except OSError:
                    pass
    except OSError:
        pass
    return removed


class GarmentImageDownloadError(Exception):
    """Raised when a garment image URL cannot be fetched (HTTP error, timeout, etc.)."""

    def __init__(self, message: str, *, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    class Image:
        class Image: pass  # Dummy for type hinting


# Maximum image dimensions (generous for high-res uploads; pipeline resizes before processing)
MAX_IMAGE_WIDTH = 8192
MAX_IMAGE_HEIGHT = 8192
MAX_FILE_SIZE_MB = 20
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "BMP"}


def validate_base64_image(base64_string: str) -> Tuple[bool, str]:
    """
    Validate that a base64 string is a valid image.
    Accepts any size within MAX_IMAGE_* and MAX_FILE_SIZE_MB; downstream
    services (e.g. try-on) resize as needed for processing.
    Returns (is_valid, error_message).
    """
    if not PIL_AVAILABLE:
        return True, "Valid (PIL check skipped)"

    try:
        image_data = decode_base64_image(base64_string)
        img = Image.open(io.BytesIO(image_data))
        img.verify()

        # Re-open for dimension check (verify() closes the image)
        img = Image.open(io.BytesIO(image_data))

        if img.format and img.format.upper() not in ALLOWED_FORMATS:
            return False, f"Unsupported image format: {img.format}. Allowed: {', '.join(ALLOWED_FORMATS)}"

        width, height = img.size
        if width < 100 or height < 100:
            return False, f"Image too small ({width}x{height}). Minimum size is 100x100 pixels."

        if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
            return False, f"Image too large ({width}x{height}). Maximum size is {MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT} pixels."

        file_size_mb = len(image_data) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            return False, f"Image file too large ({file_size_mb:.1f}MB). Maximum size is {MAX_FILE_SIZE_MB}MB."

        return True, "Valid image"

    except Exception as e:
        return False, f"Invalid image data: {str(e)}"


def decode_base64_image(base64_string: str) -> bytes:
    """
    Decode a base64 image string (with or without data URI prefix) to bytes.
    """
    # Remove data URI prefix if present (e.g., "data:image/jpeg;base64,")
    if "," in base64_string and base64_string.startswith("data:"):
        base64_string = base64_string.split(",", 1)[1]

    return base64.b64decode(base64_string)


def encode_image_to_base64(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """
    Encode image bytes to a base64 data URI string.
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def base64_to_pil(base64_string: str) -> Optional[Image.Image]:
    """
    Convert a base64 image string to a PIL Image object.
    Returns None if conversion fails.
    """
    if not PIL_AVAILABLE:
        return None
    try:
        image_data = decode_base64_image(base64_string)
        if not image_data:
            return None
        return Image.open(io.BytesIO(image_data))
    except Exception as e:
        logger.warning(f"Failed to decode base64 image: {e}")
        return None


def pil_to_base64(img: Image.Image, format: str = "JPEG", quality: int = 92) -> str:
    """
    Convert a PIL Image to a base64 data URI string.
    """
    if not PIL_AVAILABLE or img is None:
        return ""
    buffer = io.BytesIO()
    if format.upper() == "JPEG":
        # Ensure RGB mode for JPEG
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
    img.save(buffer, format=format, quality=quality)
    buffer.seek(0)
    mime_type = f"image/{format.lower()}"
    return encode_image_to_base64(buffer.read(), mime_type)


def save_base64_to_temp(base64_string: str, suffix: str = ".jpg") -> str:
    """
    Save a base64 image to a temporary file and return the file path.
    Automatically cleans old temp files and caps image size.
    """
    cleanup_temp_files()

    if not PIL_AVAILABLE:
        image_data = decode_base64_image(base64_string)
        fpath = os.path.join(TEMP_DIR, f"{uuid4().hex}{suffix}")
        with open(fpath, "wb") as f:
            f.write(image_data)
        return fpath

    image_data = decode_base64_image(base64_string)
    img = Image.open(io.BytesIO(image_data))

    # Cap image size to reduce disk usage
    max_dim = 1280
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    # Convert to RGB if needed for JPEG
    if suffix.lower() in (".jpg", ".jpeg") and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    fpath = os.path.join(TEMP_DIR, f"{uuid4().hex}{suffix}")
    img.save(fpath, quality=85)
    return fpath


async def download_image(url: str, timeout: float = 30.0) -> bytes:
    """
    Download an image from a URL and return as bytes.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                code = e.response.status_code if e.response is not None else None
                hint = (
                    "The garment image link is broken or was removed (catalog URL may be outdated)."
                    if code in (404, 410)
                    else "The garment image could not be downloaded from the given URL."
                )
                raise GarmentImageDownloadError(
                    f"{hint} (HTTP {code})." if code is not None else hint,
                    status_code=code,
                ) from e

            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                logger.warning(
                    "Downloaded URL has non-image Content-Type %s for %s",
                    content_type,
                    url[:120],
                )

            return response.content
    except GarmentImageDownloadError:
        raise
    except httpx.RequestError as e:
        raise GarmentImageDownloadError(
            f"Could not reach garment image URL (network error): {e}",
        ) from e


async def download_image_to_temp(url: str, suffix: str = ".jpg") -> str:
    """
    Download an image from a URL, resize if large, and save to a temporary file.
    Returns the temporary file path.
    """
    cleanup_temp_files()

    # Allow inline data URIs so try-on can still run when external
    # garment CDNs are unreachable (DNS/network issues).
    if isinstance(url, str) and url.startswith("data:image/"):
        try:
            image_bytes = decode_base64_image(url)
        except Exception as e:
            raise GarmentImageDownloadError(
                f"Invalid inline garment image data: {e}"
            ) from e
    else:
        image_bytes = await download_image(url)

    if not PIL_AVAILABLE:
        fpath = os.path.join(TEMP_DIR, f"{uuid4().hex}{suffix}")
        with open(fpath, "wb") as f:
            f.write(image_bytes)
        return fpath

    img = Image.open(io.BytesIO(image_bytes))

    # Cap size to reduce disk usage
    max_dim = 1280
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    # Convert RGBA to RGB for JPEG
    if suffix.lower() in (".jpg", ".jpeg") and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    fpath = os.path.join(TEMP_DIR, f"{uuid4().hex}{suffix}")
    img.save(fpath, quality=85)
    return fpath


def resize_image(img: Image.Image, max_width: int = 1024, max_height: int = 1024) -> Image.Image:
    """
    Resize image to fit within max dimensions while maintaining aspect ratio.
    """
    if not PIL_AVAILABLE or img is None:
        return img

    width, height = img.size

    if width <= max_width and height <= max_height:
        return img

    ratio = min(max_width / width, max_height / height)
    new_width = int(width * ratio)
    new_height = int(height * ratio)

    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def cleanup_temp_file(filepath: str) -> None:
    """
    Safely remove a temporary file.
    """
    try:
        if filepath and os.path.exists(filepath):
            os.unlink(filepath)
    except OSError:
        pass
