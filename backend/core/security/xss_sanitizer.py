"""
CONFIT Backend - XSS Sanitization
==================================
HTML sanitization using bleach for donor messages and other
user-generated content that may contain HTML.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import bleach
    HAS_BLEACH = True
except ImportError:
    HAS_BLEACH = False

# Allowed HTML tags for rich content (donor messages, etc.)
ALLOWED_TAGS = [
    "b", "strong", "i", "em", "u", "p", "br", "ul", "ol", "li",
    "a", "span", "div", "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "code", "pre", "hr",
]

# Allowed HTML attributes
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target"],
    "span": ["class"],
    "div": ["class"],
    "p": ["class"],
    "code": ["class"],
    "pre": ["class"],
}

# Allowed protocols for href attributes
ALLOWED_PROTOCOLS = ["https", "mailto"]


def sanitize_html(html: str, *, extra_tags: Optional[list] = None) -> str:
    """
    Sanitize HTML content to prevent XSS attacks.

    Uses bleach to strip dangerous tags and attributes while
    preserving safe formatting.

    Args:
        html: Raw HTML string from user input
        extra_tags: Additional tags to allow beyond the defaults

    Returns:
        Sanitized HTML string
    """
    if not html:
        return ""

    if not HAS_BLEACH:
        # Fallback: strip all HTML tags if bleach not available
        import re
        clean = re.sub(r"<[^>]+>", "", html)
        logger.warning("bleach not installed — stripped all HTML tags (install bleach for rich content)")
        return clean

    tags = ALLOWED_TAGS + (extra_tags or [])

    cleaned = bleach.clean(
        html,
        tags=tags,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )

    # Also linkify any bare URLs
    cleaned = bleach.linkify(
        cleaned,
        callbacks=[_nofollow_callback],
        skip_tags=["code", "pre"],
    )

    return cleaned


def _nofollow_callback(attrs, new=False):
    """Add rel=nofollow to all generated links."""
    href_key = (None, "href")
    if href_key in attrs:
        attrs[(None, "rel")] = "nofollow noopener"
    return attrs


def strip_all_html(text: str) -> str:
    """Remove all HTML tags from text (for plain-text contexts)."""
    if not text:
        return ""
    if HAS_BLEACH:
        return bleach.clean(text, tags=[], attributes={}, strip=True)
    import re
    return re.sub(r"<[^>]+>", "", text)


__all__ = [
    "sanitize_html",
    "strip_all_html",
    "HAS_BLEACH",
    "ALLOWED_TAGS",
    "ALLOWED_ATTRIBUTES",
]
