"""
Build a large virtual product dataset from a Hugging Face dataset and export to JSON.

This JSON is compatible with CONFIT's in-memory product catalog shape.

Usage (Windows PowerShell):
  python backend/scripts/build_product_dataset_hf.py --dataset ceyda/fashion-products-small --limit 5000 --out backend/data/products.hf.json

Then set:
  setx PRODUCT_DATASET_PATH "E:\CONFIT\backend\data\products.hf.json"
and restart the backend.

Notes:
- This script uses optional dependencies (huggingface 'datasets'). If missing, it prints install instructions.
- We intentionally use image URLs when available to avoid downloading/embedding large image binaries.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"&", "and", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "brand"


def _norm_gender(v: Any) -> str:
    if not v:
        return "unisex"
    s = str(v).strip().lower()
    if s in {"men", "male", "m", "man", "mens", "men's"}:
        return "men"
    if s in {"women", "female", "f", "woman", "womens", "women's"}:
        return "women"
    if s in {"unisex", "u"}:
        return "unisex"
    # common dataset values
    if "men" in s:
        return "men"
    if "women" in s:
        return "women"
    return "unisex"


def _map_category(master: str, sub: str, article: str) -> str:
    blob = " ".join([master or "", sub or "", article or ""]).lower()
    if any(k in blob for k in ["dress", "gown", "jumpsuit", "romper"]):
        return "dresses"
    if any(k in blob for k in ["coat", "jacket", "outerwear", "blazer", "cardigan", "puffer", "parka"]):
        return "outerwear"
    if any(k in blob for k in ["shoe", "boot", "sneaker", "heel", "loafer", "flat", "sandal"]):
        return "shoes"
    if any(k in blob for k in ["bag", "handbag", "clutch", "backpack", "tote", "satchel", "wallet"]):
        return "bags"
    if any(k in blob for k in ["accessory", "watch", "belt", "scarf", "sunglass", "hat", "jewelry", "earring", "necklace"]):
        return "accessories"
    if any(k in blob for k in ["pant", "trouser", "jean", "bottom", "skirt", "short", "legging"]):
        return "bottoms"
    return "tops"


def _pick_sizes(category: str) -> List[str]:
    if category == "shoes":
        return ["36", "37", "38", "39", "40", "41", "42", "43", "44", "45"]
    return ["XS", "S", "M", "L", "XL", "XXL"]


def _first_non_empty(row: Dict[str, Any], keys: Iterable[str]) -> Optional[str]:
    for k in keys:
        v = row.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return None


def _extract_image_url(row: Dict[str, Any]) -> Optional[str]:
    # Prefer explicit URL fields
    for k in ["link", "image_url", "imageUrl", "url", "img", "image"]:
        v = row.get(k)
        if isinstance(v, str) and v.startswith("http"):
            return v
    # Some datasets store images as dicts (we avoid embedding binaries here)
    return None


def build_items(rows: List[Dict[str, Any]], limit: int, seed: int) -> List[Dict[str, Any]]:
    random.seed(seed)
    brands = [
        "CONFIT Essentials",
        "Maison Élégance",
        "UrbanPulse",
        "Atelier Noir",
        "LuxeLayers",
        "EcoThread",
        "Cairo Cotton Co.",
        "Nordic Minimal",
    ]

    items: List[Dict[str, Any]] = []
    for i, row in enumerate(rows[:limit], start=1):
        gender = _norm_gender(_first_non_empty(row, ["gender", "Gender"]))
        master = _first_non_empty(row, ["masterCategory", "master_category", "master", "category"])
        sub = _first_non_empty(row, ["subCategory", "sub_category", "subcategory"])
        article = _first_non_empty(row, ["articleType", "article_type", "type"])
        category = _map_category(master or "", sub or "", article or "")

        name = _first_non_empty(row, ["productDisplayName", "name", "title", "product_name"]) or f"Product {i}"
        color = _first_non_empty(row, ["baseColour", "base_color", "color", "colour"])
        season = _first_non_empty(row, ["season", "Season"])

        brand = _first_non_empty(row, ["brand", "Brand"]) or random.choice(brands)
        brand_id = f"brand-{_slug(brand)}"

        price = row.get("price")
        if not isinstance(price, (int, float)) or price <= 0:
            base = random.randint(25, 220)
            price = int(base * random.uniform(1.4, 3.2))

        image_url = _extract_image_url(row) or "https://placehold.co/400x500?text=Fashion"

        colors = [color] if color else []
        sizes = _pick_sizes(category)
        tags = [category, brand_id, gender]
        if color:
            tags.append(str(color).lower())
        if season:
            tags.append(str(season).lower())

        items.append(
            {
                "id": f"hf-{i}",
                "name": name,
                "brand": brand,
                "brandId": brand_id,
                "gender": gender,
                "price": float(price),
                "originalPrice": None,
                "currency": "USD",
                "category": category,
                "subcategory": (sub or article or category).lower().replace(" ", "-"),
                "images": [image_url],
                "colors": colors,
                "sizes": sizes,
                "description": f"{name}. Curated for CONFIT preview/testing.",
                "styleCompatibility": random.randint(65, 98),
                "inStock": True,
                "tags": tags,
            }
        )

    return items


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="ceyda/fashion-products-small", help="Hugging Face dataset id")
    parser.add_argument("--split", default=None, help="Split name (defaults to first available)")
    parser.add_argument("--limit", type=int, default=5000, help="Max rows to export")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--out", default="backend/data/products.hf.json", help="Output JSON path")
    args = parser.parse_args()

    try:
        from datasets import load_dataset  # type: ignore
    except Exception:
        print("Missing optional dependency: datasets")
        print("Install with:")
        print("  pip install datasets")
        return 2

    ds = load_dataset(args.dataset)
    split_name = args.split
    if not split_name:
        split_name = next(iter(ds.keys()))

    rows = ds[split_name]
    # Convert to list[dict] without loading images
    dict_rows: List[Dict[str, Any]] = []
    for r in rows:
        # Some datasets include non-serializable objects; keep only JSON-serializable primitives.
        safe: Dict[str, Any] = {}
        for k, v in dict(r).items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                safe[k] = v
        dict_rows.append(safe)

    items = build_items(dict_rows, limit=args.limit, seed=args.seed)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(items)} items to {out_path}")
    print("Set PRODUCT_DATASET_PATH to this file and restart the backend.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

