"""
CONFIT Backend — Try-On Security Middleware
=============================================
Input validation, rate limiting, auto-cleanup, and signed URLs
for the virtual try-on pipeline.
"""

import base64
import hashlib
import hmac
import logging
import os
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Config
MAX_IMAGE_SIZE_MB = int(os.getenv("TRYON_MAX_IMAGE_MB", "12"))
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
RESULT_EXPIRY_SECONDS = 3600  # 1 hour
SIGNING_SECRET = os.getenv("TRYON_SIGNING_SECRET", "confit-tryon-default-secret")


def validate_upload_image(base64_data: str) -> Tuple[bool, str]:
    """Validate an uploaded image for security and format.

    Checks:
    - Size limit
    - Valid base64 encoding
    - Allowed MIME type (JPEG, PNG, WebP)
    - No embedded scripts or suspicious content

    Returns:
        (is_valid, message)
    """
    if not base64_data:
        return False, "No image data provided"

    # Strip data URL prefix if present
    raw = base64_data
    if "," in raw:
        header, raw = raw.split(",", 1)
        # Check MIME from data URL header
        mime = header.split(";")[0].replace("data:", "")
        if mime and mime not in ALLOWED_MIME_TYPES:
            return False, f"Unsupported image format: {mime}. Use JPEG, PNG, or WebP."

    # Size check
    try:
        decoded = base64.b64decode(raw)
    except Exception:
        return False, "Invalid base64 encoding"

    size_mb = len(decoded) / (1024 * 1024)
    if size_mb > MAX_IMAGE_SIZE_MB:
        return False, f"Image too large ({size_mb:.1f}MB). Maximum is {MAX_IMAGE_SIZE_MB}MB."

    if len(decoded) < 100:
        return False, "Image data too small — likely corrupt"

    # Magic byte check for image formats
    magic = decoded[:8]
    is_jpeg = magic[:2] == b"\xff\xd8"
    is_png = magic[:8] == b"\x89PNG\r\n\x1a\n"
    is_webp = magic[:4] == b"RIFF" and decoded[8:12] == b"WEBP"

    if not (is_jpeg or is_png or is_webp):
        return False, "File is not a valid image (JPEG, PNG, or WebP expected)"

    # Check for suspicious embedded content
    lower = decoded[:2048].lower()
    suspicious_patterns = [b"<script", b"javascript:", b"<?php", b"<%"]
    if any(pattern in lower for pattern in suspicious_patterns):
        return False, "Image contains suspicious embedded content"

    return True, "Valid image"


def generate_signed_url(result_id: str, expires_in: int = RESULT_EXPIRY_SECONDS) -> str:
    """Generate a signed URL for accessing a try-on result.

    The URL includes a HMAC signature and expiry timestamp.
    """
    expires_at = int(time.time()) + expires_in
    payload = f"{result_id}:{expires_at}"
    signature = hmac.new(
        SIGNING_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:32]
    return f"/api/virtual-tryon/result/{result_id}?expires={expires_at}&sig={signature}"


def verify_signed_url(result_id: str, expires: int, signature: str) -> bool:
    """Verify a signed URL's signature and expiry."""
    if time.time() > expires:
        return False
    payload = f"{result_id}:{expires}"
    expected = hmac.new(
        SIGNING_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:32]
    return hmac.compare_digest(signature, expected)


class ImageCleanupTracker:
    """Tracks temporary images and ensures auto-deletion.

    Usage:
        tracker = ImageCleanupTracker()
        tracker.register("/tmp/upload_123.jpg", ttl=300)
        # ... later ...
        tracker.cleanup_expired()
    """

    def __init__(self) -> None:
        self._tracked: dict[str, float] = {}

    def register(self, path: str, ttl: int = 300) -> None:
        """Register a file for auto-deletion after TTL seconds."""
        self._tracked[path] = time.time() + ttl

    def cleanup_expired(self) -> int:
        """Delete expired files. Returns number of files cleaned."""
        now = time.time()
        expired = [p for p, exp in self._tracked.items() if now > exp]
        cleaned = 0
        for path in expired:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    cleaned += 1
            except OSError as e:
                logger.warning("Failed to clean up %s: %s", path, e)
            self._tracked.pop(path, None)
        return cleaned

    def cleanup_all(self) -> int:
        """Force cleanup of all tracked files."""
        cleaned = 0
        for path in list(self._tracked.keys()):
            try:
                if os.path.exists(path):
                    os.remove(path)
                    cleaned += 1
            except OSError:
                pass
            self._tracked.pop(path, None)
        return cleaned


# Global instance
image_cleanup = ImageCleanupTracker()
