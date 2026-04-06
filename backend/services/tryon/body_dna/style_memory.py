"""
Progressive style memory merged into Body DNA (fits, sizes, color tendencies).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def merge_style_memory(
    profile: Dict[str, Any],
    *,
    preferred_fit: Optional[str] = None,
    size_label: Optional[str] = None,
    garment_category: Optional[str] = None,
    color_hex: Optional[str] = None,
) -> Dict[str, Any]:
    """Update profile['style_memory'] in place and return profile."""
    sm: Dict[str, Any] = dict(profile.get("style_memory") or {})
    fits: Dict[str, float] = dict(sm.get("preferred_fits") or {})
    sizes: Dict[str, int] = dict(sm.get("sizes_chosen") or {})
    colors: Dict[str, float] = dict(sm.get("color_tendencies") or {})

    if preferred_fit and garment_category:
        k = f"{garment_category}:{preferred_fit.lower()}"
        fits[k] = fits.get(k, 0.0) + 1.0

    if size_label and garment_category:
        sk = f"{garment_category}:{size_label}"
        sizes[sk] = sizes.get(sk, 0) + 1

    if color_hex:
        c = color_hex.strip().lstrip("#").lower()[:6]
        if c:
            colors[c] = colors.get(c, 0.0) + 1.0

    sm["preferred_fits"] = fits
    sm["sizes_chosen"] = sizes
    sm["color_tendencies"] = colors
    profile["style_memory"] = sm
    return profile


def top_style_signals(style_memory: Dict[str, Any], n: int = 5) -> Dict[str, List[str]]:
    """Summarize top keys for API responses."""
    sm = style_memory or {}
    def top_keys(d: Dict[str, float], n2: int) -> List[str]:
        return [k for k, _ in sorted(d.items(), key=lambda x: -x[1])[:n2]]

    return {
        "fits": top_keys({k: float(v) for k, v in (sm.get("preferred_fits") or {}).items()}, n),
        "colors": top_keys({k: float(v) for k, v in (sm.get("color_tendencies") or {}).items()}, n),
    }
