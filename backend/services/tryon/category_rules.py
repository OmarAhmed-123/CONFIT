"""
Category mapping for external try-on APIs (FASHN, Gemini prompts, etc.).
"""

from __future__ import annotations

from typing import Final

# FASHN Try-On v1.6: 'auto' | 'tops' | 'bottoms' | 'one-pieces'
_CATALOG_TO_FASHN: Final[dict[str, str]] = {
    "tops": "tops",
    "bottoms": "bottoms",
    "dresses": "one-pieces",
    "outerwear": "tops",
    "shoes": "auto",
    "accessories": "auto",
    "bags": "auto",
}


def to_fashn_category(catalog_category: str | None) -> str:
    c = (catalog_category or "tops").strip().lower()
    return _CATALOG_TO_FASHN.get(c, "auto")
