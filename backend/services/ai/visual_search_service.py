"""
CONFIT Backend - SNAP & STYLE Visual Search Service
====================================================
Enhanced visual search with Google Vision API and pgvector.

Features:
- Google Vision API for label detection
- CLIP embeddings via sentence-transformers
- pgvector for similarity search
- Rate limiting (30/day per user)
- Cost tracking
- Arabic/English support
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
GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY", "")
EMBEDDING_MODEL = os.getenv("VISUAL_SEARCH_MODEL", "sentence-transformers/clip-ViT-B-32")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "512"))
VISUAL_SEARCH_COST_USD = float(os.getenv("VISUAL_SEARCH_COST_USD", "0.001"))


@dataclass
class DetectedAttributes:
    """Attributes detected from an image."""
    category: str
    subcategory: Optional[str] = None
    colors: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    styles: List[str] = field(default_factory=list)
    materials: List[str] = field(default_factory=list)
    brands: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class VisualSearchResult:
    """A single search result."""
    product_id: str
    sku: str
    name: str
    brand: Optional[str] = None
    price: Optional[float] = None
    currency: str = "USD"
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    similarity_score: float = 0.0
    matched_attributes: List[str] = field(default_factory=list)


@dataclass
class VisualSearchResponse:
    """Response from visual search."""
    session_id: str
    query_attributes: Optional[DetectedAttributes] = None
    results: List[VisualSearchResult] = field(default_factory=list)
    total_results: int = 0
    processing_time_ms: float = 0.0
    cost_usd: float = 0.0


class VisualSearchService:
    """
    SNAP & STYLE Visual Search Service.
    
    Usage:
        service = VisualSearchService(db, redis)
        
        # Search by image
        response = await service.search_by_image(
            image_bytes=image_data,
            user_id="user-123",
            filters={"category": "tops", "max_price": 100}
        )
        
        # Search by text
        response = await service.search_by_text(
            query="red summer dress",
            user_id="user-123"
        )
    """
    
    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.redis = redis_client
        self._embedding_model = None
        self._cost_tracker = None
    
    def set_cost_tracker(self, cost_tracker):
        """Set the cost tracker for logging AI calls."""
        self._cost_tracker = cost_tracker
    
    # ==========================================
    # Main Search Methods
    # ==========================================
    
    async def search_by_image(
        self,
        image_bytes: bytes,
        user_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        min_similarity: float = 0.5,
    ) -> VisualSearchResponse:
        """
        Search for similar products by image.
        
        Args:
            image_bytes: Query image bytes
            user_id: User UUID for rate limiting
            filters: Optional filters (category, brand, price range)
            limit: Maximum results
            min_similarity: Minimum similarity threshold
            
        Returns:
            VisualSearchResponse with results
        """
        start_time = time.perf_counter()
        session_id = f"vissearch-{uuid.uuid4().hex[:12]}"
        
        try:
            # 1. Detect attributes using Google Vision API
            attributes = await self._detect_attributes_google_vision(image_bytes)
            
            # 2. Generate embedding
            embedding = await self._generate_embedding(image_bytes)
            
            # 3. Search pgvector
            results = await self._search_pgvector(
                embedding=embedding,
                filters=filters,
                limit=limit,
                min_similarity=min_similarity
            )
            
            # Calculate metrics
            processing_time = (time.perf_counter() - start_time) * 1000
            cost_usd = VISUAL_SEARCH_COST_USD
            
            # Track cost
            if self._cost_tracker and user_id:
                await self._cost_tracker.track(
                    service="visual_search",
                    model="clip-ViT-B-32",
                    user_id=user_id,
                    cost_usd=cost_usd,
                    latency_ms=processing_time,
                )
            
            return VisualSearchResponse(
                session_id=session_id,
                query_attributes=attributes,
                results=results,
                total_results=len(results),
                processing_time_ms=processing_time,
                cost_usd=cost_usd,
            )
            
        except Exception as e:
            logger.error(f"Visual search failed: {e}")
            return VisualSearchResponse(
                session_id=session_id,
                total_results=0,
            )
    
    async def search_by_text(
        self,
        query: str,
        user_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        min_similarity: float = 0.3,
    ) -> VisualSearchResponse:
        """
        Search for products by text query.
        
        Args:
            query: Text search query
            user_id: User UUID
            filters: Optional filters
            limit: Maximum results
            min_similarity: Minimum similarity threshold
            
        Returns:
            VisualSearchResponse with results
        """
        start_time = time.perf_counter()
        session_id = f"vissearch-{uuid.uuid4().hex[:12]}"
        
        try:
            # 1. Generate text embedding
            embedding = await self._generate_text_embedding(query)
            
            # 2. Parse query for attributes
            attributes = self._parse_query_attributes(query)
            
            # 3. Search pgvector
            results = await self._search_pgvector(
                embedding=embedding,
                filters=filters,
                limit=limit,
                min_similarity=min_similarity
            )
            
            processing_time = (time.perf_counter() - start_time) * 1000
            
            return VisualSearchResponse(
                session_id=session_id,
                query_attributes=attributes,
                results=results,
                total_results=len(results),
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            logger.error(f"Text search failed: {e}")
            return VisualSearchResponse(
                session_id=session_id,
                total_results=0,
            )
    
    # ==========================================
    # Google Vision API Integration
    # ==========================================
    
    async def _detect_attributes_google_vision(
        self,
        image_bytes: bytes
    ) -> DetectedAttributes:
        """
        Detect fashion attributes using Google Vision API.
        
        Uses label detection and web detection for comprehensive analysis.
        """
        if not GOOGLE_VISION_API_KEY:
            return await self._fallback_attribute_detection(image_bytes)
        
        try:
            import httpx
            
            # Encode image
            encoded_image = self._encode_image_base64(image_bytes)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Label detection
                label_response = await client.post(
                    f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_VISION_API_KEY}",
                    json={
                        "requests": [{
                            "image": {"content": encoded_image},
                            "features": [
                                {"type": "LABEL_DETECTION", "maxResults": 20},
                                {"type": "WEB_DETECTION", "maxResults": 10},
                                {"type": "IMAGE_PROPERTIES"},
                            ]
                        }]
                    }
                )
                
                if label_response.status_code != 200:
                    logger.warning(f"Google Vision API error: {label_response.text}")
                    return await self._fallback_attribute_detection(image_bytes)
                
                data = label_response.json()
                response = data.get("responses", [{}])[0]
                
                # Parse labels
                labels = []
                label_annotations = response.get("labelAnnotations", [])
                for label in label_annotations:
                    labels.append(label["description"])
                
                # Parse web detection for brands
                brands = []
                web_detection = response.get("webDetection", {})
                for entity in web_detection.get("webEntities", []):
                    if entity.get("description"):
                        # Check if it might be a brand
                        desc = entity["description"]
                        if entity.get("score", 0) > 0.5:
                            brands.append(desc)
                
                # Parse colors
                colors = []
                color_info = response.get("imagePropertiesAnnotation", {}).get("dominantColors", {})
                for color in color_info.get("colors", [])[:5]:
                    rgb = color.get("color", {})
                    color_name = self._rgb_to_color_name(
                        rgb.get("red", 0),
                        rgb.get("green", 0),
                        rgb.get("blue", 0)
                    )
                    if color_name not in colors:
                        colors.append(color_name)
                
                # Infer category from labels
                category, subcategory = self._infer_category_from_labels(labels)
                
                # Infer patterns
                patterns = self._infer_patterns_from_labels(labels)
                
                # Infer materials
                materials = self._infer_materials_from_labels(labels)
                
                return DetectedAttributes(
                    category=category,
                    subcategory=subcategory,
                    colors=colors,
                    patterns=patterns,
                    materials=materials,
                    labels=labels[:15],
                    brands=brands[:3],
                    confidence_scores={
                        "category": 0.8 if category != "unknown" else 0.3,
                    }
                )
                
        except Exception as e:
            logger.error(f"Google Vision API call failed: {e}")
            return await self._fallback_attribute_detection(image_bytes)
    
    def _encode_image_base64(self, image_bytes: bytes) -> str:
        """Encode image bytes to base64."""
        import base64
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def _rgb_to_color_name(self, r: int, g: int, b: int) -> str:
        """Convert RGB to color name."""
        # Color reference values
        color_refs = {
            "black": (0, 0, 0),
            "white": (255, 255, 255),
            "gray": (128, 128, 128),
            "red": (255, 0, 0),
            "blue": (0, 0, 255),
            "green": (0, 128, 0),
            "yellow": (255, 255, 0),
            "orange": (255, 165, 0),
            "purple": (128, 0, 128),
            "pink": (255, 192, 203),
            "brown": (139, 69, 19),
            "beige": (245, 245, 220),
            "navy": (0, 0, 128),
            "teal": (0, 128, 128),
            "maroon": (128, 0, 0),
            "coral": (255, 127, 80),
        }
        
        min_dist = float('inf')
        closest = "unknown"
        
        for name, (cr, cg, cb) in color_refs.items():
            dist = ((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                closest = name
        
        return closest
    
    def _infer_category_from_labels(self, labels: List[str]) -> Tuple[str, Optional[str]]:
        """Infer product category from labels."""
        labels_lower = [l.lower() for l in labels]
        
        # Category mapping
        category_keywords = {
            ("tops", "t-shirt"): ["t-shirt", "shirt", "blouse", "top", "tee"],
            ("tops", "sweater"): ["sweater", "pullover", "knitwear", "cardigan"],
            ("tops", "jacket"): ["jacket", "coat", "blazer", "outerwear"],
            ("bottoms", "pants"): ["pants", "trousers", "jeans", "denim"],
            ("bottoms", "shorts"): ["shorts", "bermuda"],
            ("bottoms", "skirt"): ["skirt", "mini skirt", "maxi skirt"],
            ("dresses", None): ["dress", "gown", "frock"],
            ("shoes", "sneakers"): ["sneakers", "trainers", "athletic shoe"],
            ("shoes", "heels"): ["heels", "pumps", "stiletto"],
            ("shoes", "boots"): ["boots", "ankle boots", "knee-high boots"],
            ("accessories", "bag"): ["bag", "handbag", "purse", "clutch"],
            ("accessories", "hat"): ["hat", "cap", "beanie"],
        }
        
        for (cat, subcat), keywords in category_keywords.items():
            for keyword in keywords:
                if any(keyword in label for label in labels_lower):
                    return cat, subcat
        
        return "unknown", None
    
    def _infer_patterns_from_labels(self, labels: List[str]) -> List[str]:
        """Infer patterns from labels."""
        patterns = []
        labels_lower = " ".join(labels).lower()
        
        pattern_keywords = {
            "striped": ["stripe", "striped"],
            "plaid": ["plaid", "checkered", "tartan"],
            "floral": ["floral", "flower"],
            "polka dot": ["polka dot", "dotted"],
            "solid": ["solid", "plain"],
            "geometric": ["geometric", "pattern"],
            "animal print": ["animal", "leopard", "zebra", "snake print"],
        }
        
        for pattern, keywords in pattern_keywords.items():
            if any(kw in labels_lower for kw in keywords):
                patterns.append(pattern)
        
        return patterns[:3]
    
    def _infer_materials_from_labels(self, labels: List[str]) -> List[str]:
        """Infer materials from labels."""
        materials = []
        labels_lower = " ".join(labels).lower()
        
        material_keywords = {
            "cotton": ["cotton"],
            "silk": ["silk"],
            "wool": ["wool", "knit"],
            "leather": ["leather"],
            "denim": ["denim", "jeans"],
            "polyester": ["polyester", "synthetic"],
            "linen": ["linen"],
            "velvet": ["velvet"],
        }
        
        for material, keywords in material_keywords.items():
            if any(kw in labels_lower for kw in keywords):
                materials.append(material)
        
        return materials[:3]
    
    async def _fallback_attribute_detection(
        self,
        image_bytes: bytes
    ) -> DetectedAttributes:
        """Fallback attribute detection using local processing."""
        try:
            import cv2
            
            # Decode image
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detect colors
            colors = self._detect_colors_opencv(image)
            
            # Detect pattern
            pattern = self._detect_pattern_opencv(image)
            
            # Estimate category from aspect ratio
            h, w = image.shape[:2]
            aspect = w / h
            
            if aspect < 0.6:
                category = "dresses"
            elif aspect > 1.2:
                category = "tops"
            else:
                category = "unknown"
            
            return DetectedAttributes(
                category=category,
                colors=colors,
                patterns=[pattern],
                confidence_scores={"category": 0.3}
            )
            
        except Exception as e:
            logger.error(f"Fallback detection failed: {e}")
            return DetectedAttributes(category="unknown")
    
    def _detect_colors_opencv(self, image: np.ndarray, n_colors: int = 3) -> List[str]:
        """Detect dominant colors using OpenCV."""
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
                color_name = self._rgb_to_color_name(
                    int(center[0]), int(center[1]), int(center[2])
                )
                colors.append(color_name)
            
            return colors
            
        except Exception:
            return ["unknown"]
    
    def _detect_pattern_opencv(self, image: np.ndarray) -> str:
        """Detect pattern type using OpenCV."""
        try:
            import cv2
            
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            if edge_density < 0.05:
                return "solid"
            elif edge_density < 0.1:
                return "textured"
            else:
                return "patterned"
                
        except Exception:
            return "solid"
    
    # ==========================================
    # Embedding Generation
    # ==========================================
    
    async def _generate_embedding(self, image_bytes: bytes) -> List[float]:
        """Generate CLIP embedding for image."""
        try:
            from sentence_transformers import SentenceTransformer
            
            # Lazy load model
            if self._embedding_model is None:
                self._embedding_model = SentenceTransformer('clip-ViT-B-32')
            
            # Load image
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            
            # Generate embedding
            embedding = self._embedding_model.encode(image)
            
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Return zero vector as fallback
            return [0.0] * EMBEDDING_DIMENSIONS
    
    async def _generate_text_embedding(self, text: str) -> List[float]:
        """Generate CLIP embedding for text."""
        try:
            from sentence_transformers import SentenceTransformer
            
            if self._embedding_model is None:
                self._embedding_model = SentenceTransformer('clip-ViT-B-32')
            
            embedding = self._embedding_model.encode(text)
            
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Text embedding generation failed: {e}")
            return [0.0] * EMBEDDING_DIMENSIONS
    
    def _parse_query_attributes(self, query: str) -> DetectedAttributes:
        """Parse text query for attributes."""
        query_lower = query.lower()
        
        # Extract colors
        colors = []
        color_keywords = [
            "black", "white", "red", "blue", "green", "yellow", "pink",
            "purple", "orange", "brown", "gray", "navy", "beige"
        ]
        for color in color_keywords:
            if color in query_lower:
                colors.append(color)
        
        # Extract category
        category, subcategory = self._infer_category_from_labels([query])
        
        return DetectedAttributes(
            category=category,
            subcategory=subcategory,
            colors=colors,
        )
    
    # ==========================================
    # pgvector Search
    # ==========================================
    
    async def _search_pgvector(
        self,
        embedding: List[float],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        min_similarity: float = 0.5
    ) -> List[VisualSearchResult]:
        """
        Search for similar products using pgvector.
        
        Uses cosine similarity via vector operator.
        """
        try:
            # Convert embedding to string for SQL
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            
            # Build filter clauses
            where_clauses = ["embedding IS NOT NULL"]
            params = {"embedding": embedding_str, "limit": limit}
            
            if filters:
                if filters.get("category"):
                    where_clauses.append("category = :category")
                    params["category"] = filters["category"]
                
                if filters.get("brand"):
                    where_clauses.append("brand_id = :brand")
                    params["brand"] = filters["brand"]
                
                if filters.get("min_price"):
                    where_clauses.append("price >= :min_price")
                    params["min_price"] = filters["min_price"]
                
                if filters.get("max_price"):
                    where_clauses.append("price <= :max_price")
                    params["max_price"] = filters["max_price"]
            
            where_clause = " AND ".join(where_clauses)
            
            # Execute search
            sql = text(f"""
                SELECT 
                    id, sku, name, brand_id, price, currency, 
                    image_url, url, category,
                    1 - (embedding <=> :embedding::vector) as similarity
                FROM products
                WHERE {where_clause}
                ORDER BY embedding <=> :embedding::vector
                LIMIT :limit
            """)
            
            result = self.db.execute(sql, params)
            rows = result.fetchall()
            
            # Build results
            results = []
            for row in rows:
                similarity = float(row.similarity) if row.similarity else 0
                
                if similarity < min_similarity:
                    continue
                
                results.append(VisualSearchResult(
                    product_id=str(row.id),
                    sku=row.sku or "",
                    name=row.name or "",
                    brand=row.brand_id,
                    price=float(row.price) if row.price else None,
                    currency=row.currency or "USD",
                    image_url=row.image_url,
                    product_url=row.url,
                    similarity_score=similarity,
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"pgvector search failed: {e}")
            return []
    
    # ==========================================
    # Product Embedding Management
    # ==========================================
    
    async def index_product(
        self,
        product_id: str,
        image_bytes: bytes
    ) -> bool:
        """
        Generate and store embedding for a product.
        
        Called when product is created or updated.
        """
        try:
            # Generate embedding
            embedding = await self._generate_embedding(image_bytes)
            
            # Store in database
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            
            sql = text("""
                UPDATE products 
                SET embedding = :embedding::vector
                WHERE id = :id
            """)
            
            self.db.execute(sql, {
                "id": product_id,
                "embedding": embedding_str
            })
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to index product: {e}")
            self.db.rollback()
            return False
    
    async def batch_index_products(
        self,
        products: List[Dict[str, Any]]
    ) -> int:
        """
        Batch index multiple products.
        
        Args:
            products: List of dicts with product_id and image_bytes
            
        Returns:
            Number of successfully indexed products
        """
        indexed = 0
        
        for product in products:
            success = await self.index_product(
                product["product_id"],
                product["image_bytes"]
            )
            if success:
                indexed += 1
        
        return indexed
    
    # ==========================================
    # Rate Limiting
    # ==========================================
    
    async def check_rate_limit(self, user_id: str) -> tuple[bool, int]:
        """
        Check if user is within rate limits.
        
        Limit: 30 searches per day per user.
        """
        if not self.redis:
            return True, 0
        
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"vissearch:ratelimit:{user_id}:{today}"
        
        try:
            current = self.redis.get(key)
            if current is None:
                self.redis.setex(key, 86400, 1)
                return True, 0
            
            count = int(current)
            if count >= 30:
                return False, 86400
            
            self.redis.incr(key)
            return True, 0
            
        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")
            return True, 0
