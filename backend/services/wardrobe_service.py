"""
CONFIT Backend — Wardrobe Service
===================================
Image-based clothing category detection and auto-tagging.
Wardrobe items are persisted in the database; use via Depends with get_db.
"""

import io
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict

from sqlalchemy.orm import Session

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from database.models import WardrobeItem as WardrobeItemModel

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────

COLOR_MAP = {
    "Black": ((0, 0, 0), (60, 60, 60)),
    "White": ((220, 220, 220), (255, 255, 255)),
    "Navy": ((0, 0, 80), (30, 30, 130)),
    "Red": ((150, 0, 0), (255, 60, 60)),
    "Blue": ((0, 60, 150), (80, 130, 255)),
    "Green": ((0, 100, 0), (80, 180, 80)),
    "Beige": ((180, 160, 120), (230, 210, 170)),
    "Brown": ((80, 50, 20), (160, 110, 60)),
    "Gray": ((100, 100, 100), (180, 180, 180)),
    "Pink": ((200, 100, 120), (255, 180, 200)),
    "Yellow": ((200, 180, 0), (255, 240, 80)),
    "Purple": ((80, 0, 120), (160, 60, 200)),
}

CATEGORIES = ["tops", "bottoms", "dresses", "outerwear", "shoes", "accessories", "bags"]

CATEGORY_KEYWORDS = {
    "tops": ["shirt", "blouse", "tee", "sweater", "top", "polo", "tank", "turtleneck", "hoodie"],
    "bottoms": ["pants", "trousers", "jeans", "shorts", "skirt", "legging", "culottes"],
    "dresses": ["dress", "gown", "romper", "jumpsuit"],
    "outerwear": ["coat", "jacket", "blazer", "cardigan", "puffer", "trench", "vest"],
    "shoes": ["shoe", "boot", "sneaker", "heel", "loafer", "sandal", "flat", "oxford", "slipper"],
    "accessories": ["scarf", "belt", "earring", "watch", "sunglasses", "hat", "glove", "necklace", "bracelet", "ring"],
    "bags": ["bag", "purse", "clutch", "backpack", "tote", "satchel", "wallet"],
}


# ── Service ────────────────────────────────────────────────────────

def _wardrobe_row_to_dict(row: WardrobeItemModel) -> dict:
    """Map ORM row to the dict shape expected by the API."""
    return {
        "id": row.id,
        "owner_user_id": row.owner_user_id,
        "name": row.name,
        "brand": row.brand,
        "category": row.category,
        "color": row.color,
        "size": row.size,
        "price": row.price,
        "currency": row.currency or "USD",
        "image_url": row.image_url,
        "tags": row.tags or [],
        "notes": row.notes,
        "source_product_id": row.source_product_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


class WardrobeService:
    """
    Handles wardrobe item auto-tagging and persistent Virtual Wardrobe storage.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def detect_color_from_image(self, image_bytes: bytes) -> str:
        """Analyze the dominant color region of an uploaded clothing image."""
        if not PIL_AVAILABLE:
            logger.warning("PIL not available, using fallback color detection")
            return random.choice(["Black", "White", "Navy", "Beige", "Gray"])

        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            # Resize for faster processing
            img = img.resize((100, 100), Image.Resampling.LANCZOS)

            # Sample the center region (likely the garment)
            width, height = img.size
            center_box = (
                width // 4,
                height // 4,
                3 * width // 4,
                3 * height // 4,
            )
            center_crop = img.crop(center_box)

            # Get average color
            pixels = list(center_crop.getdata())
            avg_r = sum(p[0] for p in pixels) // len(pixels)
            avg_g = sum(p[1] for p in pixels) // len(pixels)
            avg_b = sum(p[2] for p in pixels) // len(pixels)

            # Match to closest named color
            return self._match_color(avg_r, avg_g, avg_b)

        except Exception as e:
            logger.warning(f"Color detection failed: {e}, using fallback")
            return random.choice(["Black", "White", "Navy", "Beige", "Gray"])

    @staticmethod
    def _match_color(r: int, g: int, b: int) -> str:
        """Match an RGB value to the closest named color."""
        best_match = "Black"
        best_distance = float("inf")

        for name, (low, high) in COLOR_MAP.items():
            # Check if color is within range
            if (low[0] <= r <= high[0] and low[1] <= g <= high[1] and low[2] <= b <= high[2]):
                return name

            # Otherwise measure distance to midpoint
            mid = ((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, (low[2] + high[2]) / 2)
            dist = ((r - mid[0]) ** 2 + (g - mid[1]) ** 2 + (b - mid[2]) ** 2) ** 0.5
            if dist < best_distance:
                best_distance = dist
                best_match = name

        return best_match

    def detect_category_from_filename(self, filename: Optional[str]) -> str:
        """Attempt to detect clothing category from filename."""
        if not filename:
            return random.choice(CATEGORIES)

        lower = filename.lower()
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                return category

        return random.choice(CATEGORIES)

    def generate_tags(self, category: str, color: str) -> list[str]:
        """Generate relevant tags for the item."""
        base_tags = ["auto-tagged", "smart-wardrobe"]

        style_tags = {
            "tops": ["casual", "layering"],
            "bottoms": ["everyday", "versatile"],
            "dresses": ["elegant", "statement"],
            "outerwear": ["layering", "seasonal"],
            "shoes": ["footwear", "essential"],
            "accessories": ["accent", "finishing-touch"],
            "bags": ["carry", "essential"],
        }

        tags = base_tags + style_tags.get(category, [])
        tags.append(color.lower())
        tags.append(category)

        return tags

    async def auto_tag(self, image_bytes: bytes, filename: Optional[str] = None) -> dict:
        """Full auto-tagging pipeline: detect category, color, and generate tags."""
        category = self.detect_category_from_filename(filename)
        color = self.detect_color_from_image(image_bytes)
        tags = self.generate_tags(category, color)

        logger.info(f"Auto-tagged: category={category}, color={color}, tags={tags}")

        return {
            "category": category,
            "color": color,
            "tags": tags,
        }

    # ── Wardrobe CRUD Operations ──────────────────────────────────────

    def list_items(self, user_id: str) -> list[dict]:
        """Return all wardrobe items for a given user."""
        rows = (
            self._db.query(WardrobeItemModel)
            .filter(WardrobeItemModel.owner_user_id == user_id)
            .order_by(WardrobeItemModel.created_at.desc())
            .all()
        )
        return [_wardrobe_row_to_dict(r) for r in rows]

    def add_item(self, user_id: str, item_data: dict) -> dict:
        """Add a new item to the user's wardrobe (persisted)."""
        now = datetime.now(timezone.utc)
        item_id = f"wardrobe-{uuid.uuid4().hex[:8]}"

        category = item_data.get("category") or "tops"
        color = item_data.get("color") or "Unknown"
        tags = list(item_data.get("tags") or [])
        if category not in tags:
            tags.append(category)
        if isinstance(color, str) and color and color.lower() not in [t.lower() for t in tags]:
            tags.append(color.lower())

        row = WardrobeItemModel(
            id=item_id,
            owner_user_id=user_id,
            name=item_data.get("name", "Untitled"),
            brand=item_data.get("brand"),
            category=category,
            color=color,
            size=item_data.get("size"),
            price=item_data.get("price"),
            currency=item_data.get("currency", "USD"),
            image_url=item_data.get("image_url"),
            tags=tags,
            notes=item_data.get("notes"),
            source_product_id=item_data.get("source_product_id"),
            created_at=now,
            updated_at=now,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        logger.info("Wardrobe item added for %s: %s", user_id, item_id)
        return _wardrobe_row_to_dict(row)

    def update_item(self, user_id: str, item_id: str, updates: dict) -> Optional[dict]:
        """Update an existing wardrobe item."""
        row = (
            self._db.query(WardrobeItemModel)
            .filter(WardrobeItemModel.id == item_id, WardrobeItemModel.owner_user_id == user_id)
            .first()
        )
        if not row:
            return None
        allowed = {"name", "brand", "category", "color", "size", "price", "currency", "image_url", "tags", "notes", "source_product_id"}
        for key, value in updates.items():
            if key in allowed and value is not None:
                setattr(row, key, value)
        row.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(row)
        logger.info("Wardrobe item updated for %s: %s", user_id, item_id)
        return _wardrobe_row_to_dict(row)

    def delete_item(self, user_id: str, item_id: str) -> bool:
        """Remove an item from the user's wardrobe."""
        row = (
            self._db.query(WardrobeItemModel)
            .filter(WardrobeItemModel.id == item_id, WardrobeItemModel.owner_user_id == user_id)
            .first()
        )
        if not row:
            return False
        self._db.delete(row)
        self._db.commit()
        logger.info("Wardrobe item removed for %s: %s", user_id, item_id)
        return True

    def find_duplicates(self, user_id: str, probe: dict) -> list[dict]:
        """Detect potential duplicate items by brand, category, color, name."""
        name = (probe.get("name") or "").strip().lower()
        brand = (probe.get("brand") or "").strip().lower()
        category = (probe.get("category") or "").strip().lower()
        color = (probe.get("color") or "").strip().lower()

        rows = (
            self._db.query(WardrobeItemModel)
            .filter(WardrobeItemModel.owner_user_id == user_id)
            .all()
        )
        candidates = []
        for item in rows:
            iname = (item.name or "").strip().lower()
            ibrand = (item.brand or "").strip().lower()
            icategory = (item.category or "").strip().lower()
            icolor = (item.color or "").strip().lower()
            if brand and ibrand and brand != ibrand:
                continue
            if category and icategory and category != icategory:
                continue
            if color and icolor and color != icolor:
                continue
            if name and iname:
                name_tokens = set(name.split())
                iname_tokens = set(iname.split())
                if not name_tokens.intersection(iname_tokens):
                    continue
            candidates.append(_wardrobe_row_to_dict(item))
        return candidates

    def suggest_outfits(self, user_id: str, max_outfits: int = 5) -> list[dict]:
        """Build outfit suggestions from the user's wardrobe (DB)."""
        items = [ _wardrobe_row_to_dict(r) for r in
            self._db.query(WardrobeItemModel).filter(WardrobeItemModel.owner_user_id == user_id).all()
        ]
        if not items:
            return []

        tops = [i for i in items if i.get("category") == "tops"]
        bottoms = [i for i in items if i.get("category") == "bottoms"]
        outers = [i for i in items if i.get("category") == "outerwear"]
        shoes = [i for i in items if i.get("category") == "shoes"]
        accessories = [i for i in items if i.get("category") == "accessories"]

        outfits: list[dict] = []
        for top in tops:
            for bottom in bottoms:
                outfit_items = [top, bottom]

                if outers:
                    outfit_items.append(random.choice(outers))
                if shoes:
                    outfit_items.append(random.choice(shoes))
                if accessories:
                    outfit_items.append(random.choice(accessories))

                total_value = sum(
                    float(i.get("price", 0) or 0) for i in outfit_items
                ) or None

                outfits.append(
                    {
                        "id": f"outfit-{uuid.uuid4().hex[:8]}",
                        "title": f"{top.get('color', '').title()} {top.get('category', 'look')} outfit",
                        "items": outfit_items,
                        "estimated_total_value": total_value,
                        "occasion_hint": "casual",
                    }
                )

                if len(outfits) >= max_outfits:
                    return outfits

        return outfits

