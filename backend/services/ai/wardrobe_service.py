"""
CONFIT Backend - MY CLOSET Virtual Wardrobe Service
====================================================
Enhanced wardrobe management with AI features.

Features:
- Auto-tagging via Google Vision API
- CLIP embeddings for similarity
- Duplicate detection alerts
- Outfit suggestions from closet items
- S3 storage with encryption
- Rate limiting
"""

import hashlib
import io
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Configuration
S3_BUCKET = os.getenv("S3_BUCKET", "confit-wardrobe")
GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY", "")
WARDROBE_MAX_ITEMS_FREE = int(os.getenv("WARDROBE_MAX_ITEMS_FREE", "50"))
WARDROBE_MAX_ITEMS_CLUB = int(os.getenv("WARDROBE_MAX_ITEMS_CLUB", "200"))


@dataclass
class WardrobeItem:
    """A wardrobe item."""
    id: str
    user_id: str
    name: str
    category: str
    subcategory: Optional[str] = None
    colors: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    materials: List[str] = field(default_factory=list)
    brands: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    image_url: Optional[str] = None
    image_key: Optional[str] = None
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = None
    times_worn: int = 0
    last_worn: Optional[datetime] = None
    is_favorite: bool = False
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DuplicateAlert:
    """Alert for potential duplicate purchase."""
    existing_item: WardrobeItem
    new_item_data: Dict[str, Any]
    similarity_score: float
    message: str


@dataclass
class OutfitSuggestion:
    """An outfit suggestion from closet items."""
    outfit_id: str
    name: str
    items: List[WardrobeItem]
    occasion: Optional[str] = None
    style_match_score: float = 0.0
    color_harmony_score: float = 0.0
    tips: List[str] = field(default_factory=list)


class WardrobeService:
    """
    MY CLOSET Virtual Wardrobe Service.
    
    Usage:
        service = WardrobeService(db, redis, s3)
        
        # Add item with auto-tagging
        item = await service.add_item(
            user_id="user-123",
            image_bytes=image_data,
            name="Blue Denim Jacket"
        )
        
        # Check for duplicates before purchase
        alerts = await service.check_duplicates(
            user_id="user-123",
            product_sku="JKT-BLUE-001"
        )
        
        # Get outfit suggestions
        outfits = await service.suggest_outfits(
            user_id="user-123",
            occasion="casual"
        )
    """
    
    def __init__(self, db: Session, redis_client=None, s3_client=None):
        self.db = db
        self.redis = redis_client
        self.s3 = s3_client
        self._embedding_model = None
        self._cost_tracker = None
    
    def set_cost_tracker(self, cost_tracker):
        """Set the cost tracker for logging AI calls."""
        self._cost_tracker = cost_tracker
    
    # ==========================================
    # CRUD Operations
    # ==========================================
    
    async def add_item(
        self,
        user_id: str,
        image_bytes: bytes,
        name: Optional[str] = None,
        category: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WardrobeItem:
        """
        Add a new item to user's wardrobe.
        
        Auto-tags using Google Vision API and generates embedding.
        
        Args:
            user_id: User UUID
            image_bytes: Item image
            name: Optional item name
            category: Optional category hint
            metadata: Additional metadata
            
        Returns:
            Created WardrobeItem
        """
        item_id = str(uuid.uuid4())
        
        # 1. Upload image to S3
        image_key = await self._upload_image(user_id, item_id, image_bytes)
        
        # 2. Auto-tag using Google Vision
        tags = await self._auto_tag_image(image_bytes)
        
        # 3. Generate embedding
        embedding = await self._generate_embedding(image_bytes)
        
        # 4. Create item record
        item = WardrobeItem(
            id=item_id,
            user_id=user_id,
            name=name or tags.get("name", "Unknown Item"),
            category=category or tags.get("category", "unknown"),
            subcategory=tags.get("subcategory"),
            colors=tags.get("colors", []),
            patterns=tags.get("patterns", []),
            materials=tags.get("materials", []),
            brands=tags.get("brands", []),
            tags=tags.get("labels", []),
            image_key=image_key,
            embedding=embedding,
        )
        
        # 5. Save to database
        await self._save_item(item)
        
        # 6. Invalidate cache
        await self._invalidate_cache(user_id)
        
        return item
    
    async def get_item(self, item_id: str, user_id: str) -> Optional[WardrobeItem]:
        """Get a specific wardrobe item."""
        try:
            sql = text("""
                SELECT * FROM wardrobe_items 
                WHERE id = :id AND user_id = :user_id
            """)
            
            result = self.db.execute(sql, {"id": item_id, "user_id": user_id})
            row = result.fetchone()
            
            if not row:
                return None
            
            return self._row_to_item(row)
            
        except Exception as e:
            logger.error(f"Failed to get item: {e}")
            return None
    
    async def list_items(
        self,
        user_id: str,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[WardrobeItem]:
        """List user's wardrobe items with optional filtering."""
        try:
            if category:
                sql = text("""
                    SELECT * FROM wardrobe_items 
                    WHERE user_id = :user_id AND category = :category
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """)
                params = {"user_id": user_id, "category": category, "limit": limit, "offset": offset}
            else:
                sql = text("""
                    SELECT * FROM wardrobe_items 
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """)
                params = {"user_id": user_id, "limit": limit, "offset": offset}
            
            result = self.db.execute(sql, params)
            rows = result.fetchall()
            
            return [self._row_to_item(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to list items: {e}")
            return []
    
    async def update_item(
        self,
        item_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Optional[WardrobeItem]:
        """Update a wardrobe item."""
        try:
            # Build update query
            set_clauses = []
            params = {"id": item_id, "user_id": user_id}
            
            for field_name, value in updates.items():
                if field_name in ("name", "category", "subcategory", "is_favorite"):
                    set_clauses.append(f"{field_name} = :{field_name}")
                    params[field_name] = value
                elif field_name in ("colors", "patterns", "materials", "tags"):
                    set_clauses.append(f"{field_name} = :{field_name}")
                    params[field_name] = value  # Will be stored as JSON array
            
            if not set_clauses:
                return await self.get_item(item_id, user_id)
            
            sql = text(f"""
                UPDATE wardrobe_items 
                SET {", ".join(set_clauses)}
                WHERE id = :id AND user_id = :user_id
            """)
            
            self.db.execute(sql, params)
            self.db.commit()
            
            await self._invalidate_cache(user_id)
            
            return await self.get_item(item_id, user_id)
            
        except Exception as e:
            logger.error(f"Failed to update item: {e}")
            self.db.rollback()
            return None
    
    async def delete_item(self, item_id: str, user_id: str) -> bool:
        """Delete a wardrobe item."""
        try:
            # Get item first to delete image
            item = await self.get_item(item_id, user_id)
            if not item:
                return False
            
            # Delete from S3
            if self.s3 and item.image_key:
                try:
                    self.s3.delete_object(Bucket=S3_BUCKET, Key=item.image_key)
                except Exception:
                    pass
            
            # Delete from database
            sql = text("DELETE FROM wardrobe_items WHERE id = :id AND user_id = :user_id")
            self.db.execute(sql, {"id": item_id, "user_id": user_id})
            self.db.commit()
            
            await self._invalidate_cache(user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete item: {e}")
            self.db.rollback()
            return False
    
    # ==========================================
    # Auto-Tagging
    # ==========================================
    
    async def _auto_tag_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Auto-tag image using Google Vision API.
        
        Returns dict with category, colors, patterns, materials, brands, labels.
        """
        if not GOOGLE_VISION_API_KEY:
            return await self._fallback_tagging(image_bytes)
        
        try:
            import httpx
            import base64
            
            encoded_image = base64.b64encode(image_bytes).decode('utf-8')
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_VISION_API_KEY}",
                    json={
                        "requests": [{
                            "image": {"content": encoded_image},
                            "features": [
                                {"type": "LABEL_DETECTION", "maxResults": 15},
                                {"type": "WEB_DETECTION", "maxResults": 5},
                                {"type": "IMAGE_PROPERTIES"},
                            ]
                        }]
                    }
                )
                
                if response.status_code != 200:
                    logger.warning(f"Google Vision API error: {response.text}")
                    return await self._fallback_tagging(image_bytes)
                
                data = response.json()
                resp = data.get("responses", [{}])[0]
                
                # Parse labels
                labels = []
                for label in resp.get("labelAnnotations", []):
                    labels.append(label["description"])
                
                # Parse colors
                colors = []
                color_info = resp.get("imagePropertiesAnnotation", {}).get("dominantColors", {})
                for color in color_info.get("colors", [])[:5]:
                    rgb = color.get("color", {})
                    color_name = self._rgb_to_color_name(
                        rgb.get("red", 0),
                        rgb.get("green", 0),
                        rgb.get("blue", 0)
                    )
                    if color_name not in colors:
                        colors.append(color_name)
                
                # Parse web entities for brands
                brands = []
                for entity in resp.get("webDetection", {}).get("webEntities", []):
                    if entity.get("score", 0) > 0.5:
                        brands.append(entity.get("description", ""))
                
                # Infer category
                category, subcategory = self._infer_category(labels)
                
                # Infer patterns
                patterns = self._infer_patterns(labels)
                
                # Infer materials
                materials = self._infer_materials(labels)
                
                return {
                    "name": labels[0] if labels else "Unknown Item",
                    "category": category,
                    "subcategory": subcategory,
                    "colors": colors,
                    "patterns": patterns,
                    "materials": materials,
                    "brands": brands[:3],
                    "labels": labels,
                }
                
        except Exception as e:
            logger.error(f"Auto-tagging failed: {e}")
            return await self._fallback_tagging(image_bytes)
    
    async def _fallback_tagging(self, image_bytes: bytes) -> Dict[str, Any]:
        """Fallback tagging using local processing."""
        try:
            import cv2
            
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            colors = self._detect_colors(image)
            
            h, w = image.shape[:2]
            aspect = w / h
            
            if aspect < 0.6:
                category = "dresses"
            elif aspect > 1.2:
                category = "tops"
            else:
                category = "unknown"
            
            return {
                "name": "Unknown Item",
                "category": category,
                "colors": colors,
                "patterns": [],
                "materials": [],
                "brands": [],
                "labels": [],
            }
            
        except Exception as e:
            logger.error(f"Fallback tagging failed: {e}")
            return {"name": "Unknown Item", "category": "unknown"}
    
    def _rgb_to_color_name(self, r: int, g: int, b: int) -> str:
        """Convert RGB to color name."""
        color_refs = {
            "black": (0, 0, 0), "white": (255, 255, 255), "gray": (128, 128, 128),
            "red": (255, 0, 0), "blue": (0, 0, 255), "green": (0, 128, 0),
            "yellow": (255, 255, 0), "orange": (255, 165, 0), "purple": (128, 0, 128),
            "pink": (255, 192, 203), "brown": (139, 69, 19), "beige": (245, 245, 220),
            "navy": (0, 0, 128), "teal": (0, 128, 128), "maroon": (128, 0, 0),
        }
        
        min_dist = float('inf')
        closest = "unknown"
        
        for name, (cr, cg, cb) in color_refs.items():
            dist = ((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                closest = name
        
        return closest
    
    def _detect_colors(self, image: np.ndarray, n_colors: int = 3) -> List[str]:
        """Detect dominant colors."""
        try:
            from sklearn.cluster import KMeans
            
            pixels = image.reshape(-1, 3)
            if len(pixels) > 5000:
                indices = np.random.choice(len(pixels), 5000, replace=False)
                pixels = pixels[indices]
            
            kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=3)
            kmeans.fit(pixels)
            
            colors = []
            for center in kmeans.cluster_centers_:
                colors.append(self._rgb_to_color_name(int(center[0]), int(center[1]), int(center[2])))
            
            return colors
            
        except Exception:
            return ["unknown"]
    
    def _infer_category(self, labels: List[str]) -> Tuple[str, Optional[str]]:
        """Infer category from labels."""
        labels_lower = [l.lower() for l in labels]
        
        category_map = {
            ("tops", "t-shirt"): ["t-shirt", "shirt", "blouse", "top", "tee"],
            ("tops", "sweater"): ["sweater", "pullover", "cardigan"],
            ("tops", "jacket"): ["jacket", "coat", "blazer"],
            ("bottoms", "pants"): ["pants", "trousers", "jeans", "denim"],
            ("bottoms", "shorts"): ["shorts"],
            ("bottoms", "skirt"): ["skirt"],
            ("dresses", None): ["dress", "gown"],
            ("shoes", "sneakers"): ["sneakers", "trainers"],
            ("shoes", "heels"): ["heels", "pumps"],
            ("shoes", "boots"): ["boots"],
            ("accessories", "bag"): ["bag", "handbag", "purse"],
        }
        
        for (cat, subcat), keywords in category_map.items():
            for kw in keywords:
                if any(kw in label for label in labels_lower):
                    return cat, subcat
        
        return "unknown", None
    
    def _infer_patterns(self, labels: List[str]) -> List[str]:
        """Infer patterns from labels."""
        patterns = []
        labels_str = " ".join(labels).lower()
        
        pattern_map = {
            "striped": ["stripe", "striped"],
            "plaid": ["plaid", "checkered"],
            "floral": ["floral", "flower"],
            "solid": ["solid", "plain"],
        }
        
        for pattern, keywords in pattern_map.items():
            if any(kw in labels_str for kw in keywords):
                patterns.append(pattern)
        
        return patterns
    
    def _infer_materials(self, labels: List[str]) -> List[str]:
        """Infer materials from labels."""
        materials = []
        labels_str = " ".join(labels).lower()
        
        material_map = {
            "cotton": ["cotton"],
            "silk": ["silk"],
            "wool": ["wool", "knit"],
            "leather": ["leather"],
            "denim": ["denim"],
        }
        
        for material, keywords in material_map.items():
            if any(kw in labels_str for kw in keywords):
                materials.append(material)
        
        return materials
    
    # ==========================================
    # Duplicate Detection
    # ==========================================
    
    async def check_duplicates(
        self,
        user_id: str,
        product_sku: Optional[str] = None,
        product_image_bytes: Optional[bytes] = None,
        product_name: Optional[str] = None,
        similarity_threshold: float = 0.85
    ) -> List[DuplicateAlert]:
        """
        Check if user already owns similar items.
        
        Called before purchase to alert about duplicates.
        
        Args:
            user_id: User UUID
            product_sku: Product SKU to check
            product_image_bytes: Product image for visual comparison
            product_name: Product name for text matching
            similarity_threshold: Threshold for similarity alert
            
        Returns:
            List of DuplicateAlert objects
        """
        alerts = []
        
        try:
            # 1. Check by SKU (exact match)
            if product_sku:
                sql = text("""
                    SELECT wi.* FROM wardrobe_items wi
                    JOIN wardrobe_item_purchases wip ON wi.id = wip.wardrobe_item_id
                    WHERE wi.user_id = :user_id AND wip.product_sku = :sku
                """)
                result = self.db.execute(sql, {"user_id": user_id, "sku": product_sku})
                
                for row in result.fetchall():
                    item = self._row_to_item(row)
                    alerts.append(DuplicateAlert(
                        existing_item=item,
                        new_item_data={"sku": product_sku},
                        similarity_score=1.0,
                        message=f"You already own this exact item: {item.name}"
                    ))
            
            # 2. Check by visual similarity (embedding)
            if product_image_bytes and not alerts:
                query_embedding = await self._generate_embedding(product_image_bytes)
                
                similar_items = await self._find_similar_items(
                    user_id=user_id,
                    embedding=query_embedding,
                    threshold=similarity_threshold,
                    limit=5
                )
                
                for item, similarity in similar_items:
                    alerts.append(DuplicateAlert(
                        existing_item=item,
                        new_item_data={"name": product_name},
                        similarity_score=similarity,
                        message=f"You have a similar item: {item.name} ({similarity:.0%} match)"
                    ))
            
            # 3. Check by name similarity
            if product_name and not alerts:
                sql = text("""
                    SELECT * FROM wardrobe_items 
                    WHERE user_id = :user_id 
                    AND LOWER(name) LIKE :name_pattern
                """)
                result = self.db.execute(sql, {
                    "user_id": user_id,
                    "name_pattern": f"%{product_name.lower()}%"
                })
                
                for row in result.fetchall():
                    item = self._row_to_item(row)
                    alerts.append(DuplicateAlert(
                        existing_item=item,
                        new_item_data={"name": product_name},
                        similarity_score=0.7,
                        message=f"You have a similar item: {item.name}"
                    ))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Duplicate check failed: {e}")
            return []
    
    async def _find_similar_items(
        self,
        user_id: str,
        embedding: List[float],
        threshold: float = 0.85,
        limit: int = 5
    ) -> List[Tuple[WardrobeItem, float]]:
        """Find similar items in user's wardrobe by embedding."""
        try:
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            
            sql = text("""
                SELECT *,
                    1 - (embedding <=> :embedding::vector) as similarity
                FROM wardrobe_items
                WHERE user_id = :user_id AND embedding IS NOT NULL
                ORDER BY embedding <=> :embedding::vector
                LIMIT :limit
            """)
            
            result = self.db.execute(sql, {
                "user_id": user_id,
                "embedding": embedding_str,
                "limit": limit
            })
            
            similar = []
            for row in result.fetchall():
                similarity = float(row.similarity) if row.similarity else 0
                if similarity >= threshold:
                    item = self._row_to_item(row)
                    similar.append((item, similarity))
            
            return similar
            
        except Exception as e:
            logger.error(f"Similar items search failed: {e}")
            return []
    
    # ==========================================
    # Outfit Suggestions
    # ==========================================
    
    async def suggest_outfits(
        self,
        user_id: str,
        occasion: Optional[str] = None,
        limit: int = 5
    ) -> List[OutfitSuggestion]:
        """
        Generate outfit suggestions from user's wardrobe.
        
        Uses style rules and color harmony.
        """
        try:
            # Get user's items
            items = await self.list_items(user_id, limit=100)
            
            if len(items) < 2:
                return []
            
            # Group by category
            by_category = {}
            for item in items:
                cat = item.category
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(item)
            
            outfits = []
            
            # Generate outfit combinations
            # Rule: 1 top + 1 bottom + optional layer + optional shoes
            
            tops = by_category.get("tops", [])
            bottoms = by_category.get("bottoms", []) + by_category.get("dresses", [])
            layers = by_category.get("tops", [])  # Jackets, etc.
            shoes = by_category.get("shoes", [])
            
            for top in tops[:5]:
                for bottom in bottoms[:3]:
                    if bottom.category == "dresses" and top.subcategory != "jacket":
                        continue  # Don't pair tops with dresses unless layer
                    
                    outfit_items = [top, bottom]
                    
                    # Add layer if available
                    if layers and top.subcategory != "jacket":
                        for layer in layers:
                            if layer.subcategory == "jacket" and layer.id != top.id:
                                outfit_items.append(layer)
                                break
                    
                    # Add shoes if available
                    if shoes:
                        outfit_items.append(shoes[0])
                    
                    # Calculate scores
                    color_score = self._calculate_color_harmony(outfit_items)
                    style_score = self._calculate_style_match(outfit_items, occasion)
                    
                    # Generate tips
                    tips = self._generate_outfit_tips(outfit_items, occasion)
                    
                    outfit = OutfitSuggestion(
                        outfit_id=f"outfit-{uuid.uuid4().hex[:8]}",
                        name=self._generate_outfit_name(outfit_items),
                        items=outfit_items,
                        occasion=occasion,
                        color_harmony_score=color_score,
                        style_match_score=style_score,
                        tips=tips,
                    )
                    
                    outfits.append(outfit)
                    
                    if len(outfits) >= limit:
                        break
                
                if len(outfits) >= limit:
                    break
            
            # Sort by combined score
            outfits.sort(key=lambda o: o.color_harmony_score + o.style_match_score, reverse=True)
            
            return outfits[:limit]
            
        except Exception as e:
            logger.error(f"Outfit suggestion failed: {e}")
            return []
    
    def _calculate_color_harmony(self, items: List[WardrobeItem]) -> float:
        """Calculate color harmony score for outfit."""
        if not items:
            return 0.0
        
        # Get all colors
        all_colors = []
        for item in items:
            all_colors.extend(item.colors)
        
        if not all_colors:
            return 0.5  # Neutral score if no colors detected
        
        # Check for complementary colors
        complementary_pairs = [
            ("blue", "orange"), ("red", "green"), ("yellow", "purple"),
            ("black", "white"), ("navy", "beige"),
        ]
        
        score = 0.5
        
        for c1, c2 in complementary_pairs:
            if c1 in all_colors and c2 in all_colors:
                score += 0.2
        
        # Penalize too many colors
        unique_colors = set(all_colors)
        if len(unique_colors) > 4:
            score -= 0.1 * (len(unique_colors) - 4)
        
        return min(1.0, max(0.0, score))
    
    def _calculate_style_match(
        self,
        items: List[WardrobeItem],
        occasion: Optional[str]
    ) -> float:
        """Calculate style match score for occasion."""
        if not occasion:
            return 0.5
        
        # Occasion-style mapping
        occasion_styles = {
            "casual": ["t-shirt", "jeans", "sneakers", "casual"],
            "work": ["blouse", "pants", "blazer", "formal"],
            "formal": ["dress", "heels", "suit", "formal"],
            "date": ["dress", "heels", "nice top", "romantic"],
        }
        
        target_styles = occasion_styles.get(occasion, [])
        
        if not target_styles:
            return 0.5
        
        # Check item tags and subcategories
        matches = 0
        for item in items:
            item_terms = item.tags + [item.subcategory or "", item.category]
            for term in item_terms:
                if term.lower() in target_styles:
                    matches += 1
                    break
        
        return min(1.0, matches / len(items)) if items else 0.0
    
    def _generate_outfit_tips(
        self,
        items: List[WardrobeItem],
        occasion: Optional[str]
    ) -> List[str]:
        """Generate styling tips for outfit."""
        tips = []
        
        # Color tips
        colors = set()
        for item in items:
            colors.update(item.colors)
        
        if len(colors) > 3:
            tips.append("Consider removing one piece to simplify the color palette")
        
        # Occasion tips
        if occasion == "work":
            tips.append("Add a blazer for a more professional look")
        elif occasion == "date":
            tips.append("Add a statement accessory for extra flair")
        
        return tips
    
    def _generate_outfit_name(self, items: List[WardrobeItem]) -> str:
        """Generate a name for the outfit."""
        if not items:
            return "Empty Outfit"
        
        top = next((i for i in items if i.category == "tops"), None)
        bottom = next((i for i in items if i.category in ("bottoms", "dresses")), None)
        
        if top and bottom:
            return f"{top.name} + {bottom.name}"
        
        return "Custom Outfit"
    
    # ==========================================
    # Embedding Generation
    # ==========================================
    
    async def _generate_embedding(self, image_bytes: bytes) -> List[float]:
        """Generate CLIP embedding for image."""
        try:
            from sentence_transformers import SentenceTransformer
            
            if self._embedding_model is None:
                self._embedding_model = SentenceTransformer('clip-ViT-B-32')
            
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            embedding = self._embedding_model.encode(image)
            
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return [0.0] * 512
    
    # ==========================================
    # Storage Operations
    # ==========================================
    
    async def _upload_image(
        self,
        user_id: str,
        item_id: str,
        image_bytes: bytes
    ) -> str:
        """Upload image to S3."""
        key = f"wardrobe/{user_id}/{item_id}.jpg"
        
        if not self.s3:
            # Fallback: store in Redis
            if self.redis:
                self.redis.setex(f"wardrobe:image:{key}", 86400 * 30, image_bytes)
            return key
        
        try:
            self.s3.put_object(
                Bucket=S3_BUCKET,
                Key=key,
                Body=image_bytes,
                ContentType="image/jpeg",
                ServerSideEncryption="AES256",
            )
            return key
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise
    
    async def get_image_url(self, item: WardrobeItem, expires_in: int = 3600) -> Optional[str]:
        """Get presigned URL for item image."""
        if not item.image_key:
            return None
        
        if not self.s3:
            return f"redis://{item.image_key}"
        
        try:
            return self.s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": S3_BUCKET, "Key": item.image_key},
                ExpiresIn=expires_in
            )
        except Exception as e:
            logger.error(f"Failed to generate URL: {e}")
            return None
    
    # ==========================================
    # Database Operations
    # ==========================================
    
    async def _save_item(self, item: WardrobeItem) -> None:
        """Save item to database."""
        try:
            embedding_str = None
            if item.embedding:
                embedding_str = "[" + ",".join(str(x) for x in item.embedding) + "]"
            
            sql = text("""
                INSERT INTO wardrobe_items (
                    id, user_id, name, category, subcategory,
                    colors, patterns, materials, brands, tags,
                    image_key, embedding, is_favorite, created_at
                ) VALUES (
                    :id, :user_id, :name, :category, :subcategory,
                    :colors, :patterns, :materials, :brands, :tags,
                    :image_key, :embedding::vector, :is_favorite, :created_at
                )
            """)
            
            self.db.execute(sql, {
                "id": item.id,
                "user_id": item.user_id,
                "name": item.name,
                "category": item.category,
                "subcategory": item.subcategory,
                "colors": item.colors,
                "patterns": item.patterns,
                "materials": item.materials,
                "brands": item.brands,
                "tags": item.tags,
                "image_key": item.image_key,
                "embedding": embedding_str,
                "is_favorite": item.is_favorite,
                "created_at": item.created_at,
            })
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to save item: {e}")
            self.db.rollback()
            raise
    
    def _row_to_item(self, row) -> WardrobeItem:
        """Convert database row to WardrobeItem."""
        import json
        
        return WardrobeItem(
            id=str(row.id),
            user_id=str(row.user_id),
            name=row.name,
            category=row.category,
            subcategory=row.subcategory,
            colors=row.colors if isinstance(row.colors, list) else json.loads(row.colors or "[]"),
            patterns=row.patterns if isinstance(row.patterns, list) else json.loads(row.patterns or "[]"),
            materials=row.materials if isinstance(row.materials, list) else json.loads(row.materials or "[]"),
            brands=row.brands if isinstance(row.brands, list) else json.loads(row.brands or "[]"),
            tags=row.tags if isinstance(row.tags, list) else json.loads(row.tags or "[]"),
            image_key=row.image_key,
            purchase_date=row.purchase_date,
            purchase_price=float(row.purchase_price) if row.purchase_price else None,
            times_worn=row.times_worn or 0,
            last_worn=row.last_worn,
            is_favorite=row.is_favorite or False,
            created_at=row.created_at,
        )
    
    async def _invalidate_cache(self, user_id: str) -> None:
        """Invalidate wardrobe cache for user."""
        if self.redis:
            try:
                self.redis.delete(f"wardrobe:items:{user_id}")
            except Exception:
                pass
    
    # ==========================================
    # Limits & Quotas
    # ==========================================
    
    async def get_item_count(self, user_id: str) -> int:
        """Get number of items in user's wardrobe."""
        try:
            sql = text("SELECT COUNT(*) FROM wardrobe_items WHERE user_id = :user_id")
            result = self.db.execute(sql, {"user_id": user_id})
            return result.scalar() or 0
        except Exception:
            return 0
    
    async def check_quota(self, user_id: str, tier: str = "free") -> tuple[bool, int]:
        """Check if user can add more items."""
        count = await self.get_item_count(user_id)
        
        limits = {
            "free": WARDROBE_MAX_ITEMS_FREE,
            "club": WARDROBE_MAX_ITEMS_CLUB,
            "icon": 1000,
        }
        
        limit = limits.get(tier, WARDROBE_MAX_ITEMS_FREE)
        
        if count >= limit:
            return False, limit - count
        
        return True, limit - count
