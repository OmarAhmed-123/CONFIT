"""
Optional clothing catalog enrichment via DummyJSON (public demo API).
Maps responses to CONFIT ProductResponse-compatible dicts so list/detail stay consistent.
"""

from __future__ import annotations

import logging
import os
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

# Fashion-oriented categories available on DummyJSON
_FASHION_CATEGORIES = [
    ("mens-shirts", "tops", "men"),
    ("womens-dresses", "dresses", "women"),
    ("mens-shoes", "shoes", "men"),
    ("womens-shoes", "shoes", "women"),
]


def _normalize_category_and_gender(raw: dict[str, Any]) -> tuple[str, str]:
    cat = str(raw.get("category", "")).lower()
    gender = "unisex"
    if "women" in cat or "womens" in cat:
        gender = "women"
    elif "men" in cat or "mens" in cat:
        gender = "men"
    if "shoe" in cat:
        return "shoes", gender
    if "dress" in cat:
        return "dresses", gender
    if "bag" in cat or "handbag" in cat:
        return "bags", gender
    if "shirt" in cat or "top" in cat or "t-shirt" in cat:
        return "tops", gender
    if "jean" in cat or "pant" in cat or "trouser" in cat:
        return "bottoms", gender
    if "jacket" in cat or "coat" in cat:
        return "outerwear", gender
    return "tops", gender


def _map_dummyjson_item(raw: dict[str, Any], category: str, gender: str) -> dict[str, Any]:
    pid = str(raw.get("id", ""))
    images = raw.get("images") or []
    if not images and raw.get("thumbnail"):
        images = [str(raw["thumbnail"])]
    title = str(raw.get("title", "Product"))
    desc = raw.get("description")
    price = float(raw.get("price", 49.0))
    return {
        "id": f"dj-{pid}",
        "name": title,
        "description": (desc or "")[:2000] if desc else f"{title} — fashion catalog item",
        "category": category,
        "gender": gender,
        "color": None,
        "size": None,
        "price": price,
        "brand": None,
        "brandId": None,
        "store_id": None,
        "images": [str(u) for u in images if str(u).startswith("http")],
        "image_url": str(images[0]) if images else None,
        "tags": ["external", gender, category],
        "inStock": True,
        "is_active": True,
        "styleCompatibility": 85,
        "created_at": "2024-01-01T00:00:00Z",
        "_source": "dummyjson",
        "_numeric_id": pid,
    }


def fetch_dummyjson_fashion_sync(limit_total: int = 48) -> List[dict[str, Any]]:
    """
    Synchronous fetch (safe for FastAPI sync route or called via asyncio.to_thread).
    Respects FASHION_EXTERNAL_CATALOG=1 (default on when unset in development).
    """
    if os.getenv("FASHION_EXTERNAL_CATALOG", "1").lower() not in ("1", "true", "yes"):
        return []

    try:
        import httpx
    except ImportError:
        logger.warning("httpx not available; skipping external fashion catalog")
        return []

    per_cat = max(4, min(20, limit_total // len(_FASHION_CATEGORIES)))
    out: list[dict[str, Any]] = []

    try:
        with httpx.Client(timeout=12.0) as client:
            for slug, cat, gender in _FASHION_CATEGORIES:
                if len(out) >= limit_total:
                    break
                url = f"https://dummyjson.com/products/category/{slug}"
                r = client.get(url, params={"limit": per_cat})
                r.raise_for_status()
                data = r.json()
                for item in data.get("products") or []:
                    out.append(_map_dummyjson_item(item, cat, gender))
                    if len(out) >= limit_total:
                        break
    except Exception as e:
        logger.warning("External fashion catalog fetch failed: %s", e)
        return []

    return out[:limit_total]


def is_dummyjson_product_id(product_id: str) -> bool:
    return bool(product_id) and product_id.startswith("dj-") and product_id.replace("dj-", "").isdigit()


def fetch_dummyjson_product_by_id_sync(product_id: str) -> Optional[dict[str, Any]]:
    if not is_dummyjson_product_id(product_id):
        return None
    numeric = product_id.replace("dj-", "", 1)
    if os.getenv("FASHION_EXTERNAL_CATALOG", "1").lower() not in ("1", "true", "yes"):
        return None
    try:
        import httpx
    except ImportError:
        return None
    try:
        with httpx.Client(timeout=12.0) as client:
            r = client.get(f"https://dummyjson.com/products/{numeric}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            raw = r.json()
    except Exception as e:
        logger.warning("DummyJSON product %s fetch failed: %s", product_id, e)
        return None

    cat, gender = _normalize_category_and_gender(raw)
    return _map_dummyjson_item(raw, cat, gender)
