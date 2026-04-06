"""
CONFIT AI Services - Visual Search
==================================
CLIP-based image similarity and visual search.

Features:
- CLIP image embeddings
- Text-to-image search
- Image-to-image search
- Multi-modal similarity
- Fashion-specific fine-tuning
"""

import asyncio
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import hashlib

import numpy as np
from PIL import Image

from .base import (
    AIServiceBase,
    InferenceResult,
    ModelConfig,
    DeviceType,
    gpu_context,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ImageEmbedding:
    """Image embedding with metadata."""
    vector: np.ndarray
    model_name: str
    image_hash: str
    dimensions: int
    normalized: bool = True
    
    def similarity(self, other: 'ImageEmbedding') -> float:
        """Compute cosine similarity with another embedding."""
        if self.normalized and other.normalized:
            return float(np.dot(self.vector, other.vector))
        return float(1 - np.dot(self.vector, other.vector) / (
            np.linalg.norm(self.vector) * np.linalg.norm(other.vector)
        ))


@dataclass
class TextEmbedding:
    """Text embedding with metadata."""
    vector: np.ndarray
    model_name: str
    text: str
    dimensions: int
    normalized: bool = True


@dataclass
class FashionAttributes:
    """Detected fashion attributes from image."""
    category: str
    subcategory: Optional[str] = None
    colors: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    styles: List[str] = field(default_factory=list)
    materials: List[str] = field(default_factory=list)
    brands: List[str] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class SearchResult:
    """Visual search result."""
    item_id: str
    similarity_score: float
    fashion_attributes: Optional[FashionAttributes] = None
    image_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualSearchRequest:
    """Request for visual search."""
    image_bytes: Optional[bytes] = None
    image_url: Optional[str] = None
    text_query: Optional[str] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: int = 20
    min_similarity: float = 0.5
    return_attributes: bool = True


@dataclass
class VisualSearchResult:
    """Result from visual search."""
    query_embedding: Optional[ImageEmbedding] = None
    text_embedding: Optional[TextEmbedding] = None
    results: List[SearchResult] = field(default_factory=list)
    detected_attributes: Optional[FashionAttributes] = None
    processing_time_ms: float = 0.0
    model_version: str = "clip-vit-base-patch32"


# ─────────────────────────────────────────────────────────────────────────────
# Visual Search AI Service
# ─────────────────────────────────────────────────────────────────────────────

class VisualSearchAIService(AIServiceBase):
    """
    CLIP-based visual search service.
    
    Capabilities:
    - Image embedding generation
    - Text-to-image search
    - Image-to-image search
    - Fashion attribute detection
    - Multi-modal similarity
    
    Usage:
        service = VisualSearchAIService()
        
        # Image search
        result = await service.infer(VisualSearchRequest(
            image_bytes=image_data,
            limit=10,
        ))
        
        # Text search
        result = await service.infer(VisualSearchRequest(
            text_query="red summer dress",
            limit=10,
        ))
    """
    
    # Fashion category labels for zero-shot classification
    FASHION_CATEGORIES = [
        "t-shirt", "blouse", "shirt", "sweater", "hoodie", "jacket", "coat",
        "jeans", "pants", "shorts", "skirt", "dress", "jumpsuit",
        "sneakers", "boots", "heels", "sandals", "loafers",
        "bag", "backpack", "purse", "clutch",
        "hat", "cap", "scarf", "belt", "watch", "jewelry",
        "sunglasses", "tie", "socks",
    ]
    
    # Style labels
    STYLE_LABELS = [
        "casual", "formal", "business casual", "streetwear",
        "bohemian", "minimalist", "vintage", "preppy",
        "sporty", "romantic", "edgy", "classic",
    ]
    
    # Color names for detection
    COLOR_NAMES = [
        "black", "white", "gray", "navy", "blue", "red", "pink",
        "green", "yellow", "orange", "purple", "brown", "beige",
        "cream", "gold", "silver", "coral", "teal", "maroon",
    ]
    
    # Pattern labels
    PATTERN_LABELS = [
        "solid", "striped", "plaid", "floral", "polka dot",
        "checkered", "geometric", "animal print", "abstract",
        "tie-dye", "embroidered", "textured",
    ]
    
    def __init__(self, config: Optional[ModelConfig] = None):
        config = config or ModelConfig(
            name="visual_search",
            device=DeviceType.CUDA,
            batch_size=32,
            precision="float16",
        )
        super().__init__(config)
        
        self._clip_model = None
        self._clip_processor = None
        self._device = None
        
        # Embedding cache
        self._embedding_cache: Dict[str, ImageEmbedding] = {}
        
        # Index for search (would use FAISS in production)
        self._index: Dict[str, np.ndarray] = {}
        self._item_metadata: Dict[str, Dict[str, Any]] = {}
    
    @property
    def model_name(self) -> str:
        return "clip_visual_search_v1"
    
    async def load_model(self) -> None:
        """Load CLIP model for visual search."""
        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor
            
            # Load CLIP model
            model_name = "openai/clip-vit-base-patch32"
            
            self._clip_processor = CLIPProcessor.from_pretrained(model_name)
            self._clip_model = CLIPModel.from_pretrained(model_name)
            
            # Set device
            self._device = self._get_device()
            if self._device != "cpu":
                self._clip_model = self._clip_model.to(self._device)
            
            # Set precision
            if self.config.precision == "float16" and self._device != "cpu":
                self._clip_model = self._clip_model.half()
            
            self._clip_model.eval()
            self._model = self._clip_model
            
            logger.info(f"Loaded CLIP model on {self._device}")
            
        except ImportError as e:
            logger.warning(f"CLIP dependencies not available: {e}")
            self._model = "fallback"
    
    async def _infer(self, input_data: VisualSearchRequest) -> VisualSearchResult:
        """
        Process visual search request.
        
        Args:
            input_data: VisualSearchRequest with image or text query
            
        Returns:
            VisualSearchResult with similar items
        """
        start_time = datetime.now(timezone.utc)
        
        query_embedding = None
        text_embedding = None
        detected_attributes = None
        
        # Step 1: Generate query embedding
        if input_data.image_bytes:
            query_embedding = await self._encode_image(input_data.image_bytes)
            
            if input_data.return_attributes:
                detected_attributes = await self._detect_attributes(
                    input_data.image_bytes
                )
        
        if input_data.text_query:
            text_embedding = await self._encode_text(input_data.text_query)
        
        # Step 2: Search for similar items
        results = await self._search_similar(
            query_embedding=query_embedding,
            text_embedding=text_embedding,
            filters=input_data.filters,
            limit=input_data.limit,
            min_similarity=input_data.min_similarity,
        )
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return VisualSearchResult(
            query_embedding=query_embedding,
            text_embedding=text_embedding,
            results=results,
            detected_attributes=detected_attributes,
            processing_time_ms=processing_time,
        )
    
    async def _encode_image(
        self,
        image_bytes: bytes
    ) -> ImageEmbedding:
        """
        Generate CLIP embedding for image.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            ImageEmbedding with normalized vector
        """
        # Compute hash for caching
        image_hash = hashlib.sha256(image_bytes).hexdigest()[:16]
        
        # Check cache
        if image_hash in self._embedding_cache:
            return self._embedding_cache[image_hash]
        
        if self._model == "fallback":
            return self._fallback_image_embedding(image_bytes, image_hash)
        
        try:
            import torch
            
            # Load image
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            
            # Preprocess
            inputs = self._clip_processor(images=image, return_tensors="pt")
            
            if self._device != "cpu":
                inputs = {k: v.to(self._device) for k, v in inputs.items()}
            
            # Get embedding
            with torch.no_grad():
                image_features = self._clip_model.get_image_features(**inputs)
            
            # Normalize
            embedding = image_features.cpu().numpy().flatten()
            embedding = embedding / np.linalg.norm(embedding)
            
            result = ImageEmbedding(
                vector=embedding,
                model_name="clip-vit-base-patch32",
                image_hash=image_hash,
                dimensions=len(embedding),
                normalized=True,
            )
            
            # Cache it
            self._embedding_cache[image_hash] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Image encoding error: {e}")
            return self._fallback_image_embedding(image_bytes, image_hash)
    
    def _fallback_image_embedding(
        self,
        image_bytes: bytes,
        image_hash: str
    ) -> ImageEmbedding:
        """Generate fallback embedding using image features."""
        try:
            import cv2
            
            # Load image
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Resize
            image = cv2.resize(image, (224, 224))
            
            # Color histogram
            hist = cv2.calcHist([image], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            hist = cv2.normalize(hist, None).flatten()
            
            # Texture features (LBP-like)
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # Gradient features
            gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            
            magnitude = np.sqrt(gx**2 + gy**2)
            grad_hist = np.histogram(magnitude.flatten(), bins=32, range=(0, 255))[0]
            grad_hist = grad_hist / (np.linalg.norm(grad_hist) + 1e-6)
            
            # Combine features
            embedding = np.concatenate([hist, grad_hist])
            embedding = embedding / (np.linalg.norm(embedding) + 1e-6)
            
            return ImageEmbedding(
                vector=embedding,
                model_name="fallback_histogram",
                image_hash=image_hash,
                dimensions=len(embedding),
                normalized=True,
            )
            
        except Exception as e:
            logger.error(f"Fallback embedding error: {e}")
            # Return random embedding as last resort
            return ImageEmbedding(
                vector=np.random.randn(512).astype(np.float32),
                model_name="random",
                image_hash=image_hash,
                dimensions=512,
                normalized=False,
            )
    
    async def _encode_text(
        self,
        text: str
    ) -> TextEmbedding:
        """
        Generate CLIP embedding for text.
        
        Args:
            text: Text query
            
        Returns:
            TextEmbedding with normalized vector
        """
        if self._model == "fallback":
            return self._fallback_text_embedding(text)
        
        try:
            import torch
            
            # Tokenize
            inputs = self._clip_processor(text=[text], return_tensors="pt", padding=True)
            
            if self._device != "cpu":
                inputs = {k: v.to(self._device) for k, v in inputs.items()}
            
            # Get embedding
            with torch.no_grad():
                text_features = self._clip_model.get_text_features(**inputs)
            
            # Normalize
            embedding = text_features.cpu().numpy().flatten()
            embedding = embedding / np.linalg.norm(embedding)
            
            return TextEmbedding(
                vector=embedding,
                model_name="clip-vit-base-patch32",
                text=text,
                dimensions=len(embedding),
                normalized=True,
            )
            
        except Exception as e:
            logger.error(f"Text encoding error: {e}")
            return self._fallback_text_embedding(text)
    
    def _fallback_text_embedding(
        self,
        text: str
    ) -> TextEmbedding:
        """Generate fallback text embedding using TF-IDF-like features."""
        # Simple bag-of-words embedding
        text_lower = text.lower()
        
        # Fashion keyword features
        features = np.zeros(256, dtype=np.float32)
        
        # Category features
        for i, category in enumerate(self.FASHION_CATEGORIES[:64]):
            if category in text_lower:
                features[i] = 1.0
        
        # Style features
        for i, style in enumerate(self.STYLE_LABELS[:32]):
            if style in text_lower:
                features[64 + i] = 1.0
        
        # Color features
        for i, color in enumerate(self.COLOR_NAMES[:32]):
            if color in text_lower:
                features[96 + i] = 1.0
        
        # Pattern features
        for i, pattern in enumerate(self.PATTERN_LABELS[:32]):
            if pattern in text_lower:
                features[128 + i] = 1.0
        
        # Normalize
        norm = np.linalg.norm(features)
        if norm > 0:
            features = features / norm
        
        return TextEmbedding(
            vector=features,
            model_name="fallback_bow",
            text=text,
            dimensions=len(features),
            normalized=True,
        )
    
    async def _detect_attributes(
        self,
        image_bytes: bytes
    ) -> FashionAttributes:
        """
        Detect fashion attributes from image using CLIP zero-shot.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            FashionAttributes with detected categories, colors, etc.
        """
        if self._model == "fallback":
            return self._fallback_attribute_detection(image_bytes)
        
        try:
            import torch
            
            # Load image
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            
            # Prepare inputs for zero-shot classification
            all_labels = (
                self.FASHION_CATEGORIES +
                self.STYLE_LABELS +
                self.COLOR_NAMES +
                self.PATTERN_LABELS
            )
            
            inputs = self._clip_processor(
                text=all_labels,
                images=image,
                return_tensors="pt",
                padding=True
            )
            
            if self._device != "cpu":
                inputs = {k: v.to(self._device) for k, v in inputs.items()}
            
            # Get similarities
            with torch.no_grad():
                outputs = self._clip_model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=-1).cpu().numpy().flatten()
            
            # Parse results
            n_categories = len(self.FASHION_CATEGORIES)
            n_styles = len(self.STYLE_LABELS)
            n_colors = len(self.COLOR_NAMES)
            n_patterns = len(self.PATTERN_LABELS)
            
            # Get top category
            category_probs = probs[:n_categories]
            top_cat_idx = np.argmax(category_probs)
            category = self.FASHION_CATEGORIES[top_cat_idx]
            category_confidence = float(category_probs[top_cat_idx])
            
            # Get top styles (threshold-based)
            style_probs = probs[n_categories:n_categories + n_styles]
            styles = [
                self.STYLE_LABELS[i]
                for i, p in enumerate(style_probs)
                if p > 0.15
            ]
            
            # Get top colors
            color_probs = probs[n_categories + n_styles:n_categories + n_styles + n_colors]
            colors = [
                self.COLOR_NAMES[i]
                for i, p in enumerate(color_probs)
                if p > 0.1
            ]
            
            # Get top patterns
            pattern_probs = probs[n_categories + n_styles + n_colors:]
            patterns = [
                self.PATTERN_LABELS[i]
                for i, p in enumerate(pattern_probs)
                if p > 0.15
            ]
            
            return FashionAttributes(
                category=category,
                colors=colors,
                patterns=patterns,
                styles=styles,
                confidence_scores={
                    "category": category_confidence,
                }
            )
            
        except Exception as e:
            logger.error(f"Attribute detection error: {e}")
            return self._fallback_attribute_detection(image_bytes)
    
    def _fallback_attribute_detection(
        self,
        image_bytes: bytes
    ) -> FashionAttributes:
        """Fallback attribute detection using image processing."""
        try:
            import cv2
            
            # Load image
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detect dominant colors
            colors = self._detect_colors(image)
            
            # Detect pattern using edge density
            pattern = self._detect_pattern(image)
            
            # Estimate category from aspect ratio
            h, w = image.shape[:2]
            aspect = w / h
            
            if aspect < 0.6:
                category = "dress" if aspect < 0.4 else "pants"
            elif aspect > 1.2:
                category = "t-shirt" if aspect > 1.5 else "shirt"
            else:
                category = "top"
            
            return FashionAttributes(
                category=category,
                colors=colors,
                patterns=[pattern],
                confidence_scores={"category": 0.5},
            )
            
        except Exception as e:
            logger.error(f"Fallback attribute detection error: {e}")
            return FashionAttributes(category="unknown")
    
    def _detect_colors(
        self,
        image: np.ndarray,
        n_colors: int = 3
    ) -> List[str]:
        """Detect dominant colors in image."""
        try:
            from sklearn.cluster import KMeans
            
            # Reshape and sample
            pixels = image.reshape(-1, 3)
            if len(pixels) > 5000:
                indices = np.random.choice(len(pixels), 5000, replace=False)
                pixels = pixels[indices]
            
            # Cluster
            kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=3)
            kmeans.fit(pixels)
            
            colors = kmeans.cluster_centers_.astype(int)
            
            # Map to color names
            color_names = []
            for color in colors:
                name = self._rgb_to_color_name(color)
                color_names.append(name)
            
            return color_names
            
        except ImportError:
            # Simple quantization fallback
            return ["unknown"]
    
    def _rgb_to_color_name(
        self,
        rgb: np.ndarray
    ) -> str:
        """Map RGB value to color name."""
        # Color name reference values
        color_refs = {
            "black": np.array([0, 0, 0]),
            "white": np.array([255, 255, 255]),
            "gray": np.array([128, 128, 128]),
            "red": np.array([255, 0, 0]),
            "blue": np.array([0, 0, 255]),
            "green": np.array([0, 128, 0]),
            "yellow": np.array([255, 255, 0]),
            "orange": np.array([255, 165, 0]),
            "purple": np.array([128, 0, 128]),
            "pink": np.array([255, 192, 203]),
            "brown": np.array([139, 69, 19]),
            "beige": np.array([245, 245, 220]),
            "navy": np.array([0, 0, 128]),
        }
        
        # Find closest color
        min_dist = float('inf')
        closest = "unknown"
        
        for name, ref in color_refs.items():
            dist = np.linalg.norm(rgb - ref)
            if dist < min_dist:
                min_dist = dist
                closest = name
        
        return closest
    
    def _detect_pattern(
        self,
        image: np.ndarray
    ) -> str:
        """Detect pattern type from image."""
        try:
            import cv2
            
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # Edge detection
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
    
    async def _search_similar(
        self,
        query_embedding: Optional[ImageEmbedding],
        text_embedding: Optional[TextEmbedding],
        filters: Dict[str, Any],
        limit: int,
        min_similarity: float
    ) -> List[SearchResult]:
        """
        Search for similar items in index.
        
        In production, would use FAISS or similar vector database.
        """
        results = []
        
        # Combine embeddings if both present
        if query_embedding and text_embedding:
            # Weighted combination (image weighted higher)
            query_vector = (
                query_embedding.vector * 0.6 +
                text_embedding.vector[:len(query_embedding.vector)] * 0.4
            )
            query_vector = query_vector / np.linalg.norm(query_vector)
        elif query_embedding:
            query_vector = query_embedding.vector
        elif text_embedding:
            query_vector = text_embedding.vector
        else:
            return results
        
        # Search in index
        similarities = []
        
        for item_id, item_vector in self._index.items():
            # Compute similarity
            if len(item_vector) == len(query_vector):
                sim = float(np.dot(query_vector, item_vector))
            else:
                # Handle dimension mismatch
                min_dim = min(len(item_vector), len(query_vector))
                sim = float(np.dot(query_vector[:min_dim], item_vector[:min_dim]))
            
            if sim >= min_similarity:
                # Apply filters
                if self._matches_filters(item_id, filters):
                    similarities.append((item_id, sim))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Build results
        for item_id, similarity in similarities[:limit]:
            metadata = self._item_metadata.get(item_id, {})
            
            result = SearchResult(
                item_id=item_id,
                similarity_score=similarity,
                image_url=metadata.get("image_url"),
                metadata=metadata,
            )
            
            results.append(result)
        
        return results
    
    def _matches_filters(
        self,
        item_id: str,
        filters: Dict[str, Any]
    ) -> bool:
        """Check if item matches filter criteria."""
        metadata = self._item_metadata.get(item_id, {})
        
        # Category filter
        if "category" in filters:
            if metadata.get("category") != filters["category"]:
                return False
        
        # Price range filter
        if "min_price" in filters or "max_price" in filters:
            price = metadata.get("price", 0)
            if "min_price" in filters and price < filters["min_price"]:
                return False
            if "max_price" in filters and price > filters["max_price"]:
                return False
        
        # Brand filter
        if "brands" in filters:
            if metadata.get("brand") not in filters["brands"]:
                return False
        
        # Color filter
        if "colors" in filters:
            item_colors = set(metadata.get("colors", []))
            filter_colors = set(filters["colors"])
            if not item_colors & filter_colors:
                return False
        
        return True
    
    # ==========================================
    # Index Management
    # ==========================================
    
    def add_item(
        self,
        item_id: str,
        embedding: np.ndarray,
        metadata: Dict[str, Any]
    ) -> None:
        """Add item to search index."""
        self._index[item_id] = embedding
        self._item_metadata[item_id] = metadata
    
    def add_items_batch(
        self,
        items: List[Tuple[str, np.ndarray, Dict[str, Any]]]
    ) -> None:
        """Add multiple items to index."""
        for item_id, embedding, metadata in items:
            self.add_item(item_id, embedding, metadata)
    
    def remove_item(self, item_id: str) -> None:
        """Remove item from index."""
        self._index.pop(item_id, None)
        self._item_metadata.pop(item_id, None)
    
    def clear_index(self) -> None:
        """Clear the entire index."""
        self._index.clear()
        self._item_metadata.clear()
    
    def get_index_size(self) -> int:
        """Get number of items in index."""
        return len(self._index)
    
    # ==========================================
    # Batch Processing
    # ==========================================
    
    async def encode_images_batch(
        self,
        images: List[bytes]
    ) -> List[ImageEmbedding]:
        """
        Encode multiple images in batch.
        
        More efficient than individual encoding.
        """
        if self._model == "fallback":
            return [
                self._fallback_image_embedding(img, hashlib.sha256(img).hexdigest()[:16])
                for img in images
            ]
        
        try:
            import torch
            
            # Load all images
            pil_images = [
                Image.open(io.BytesIO(img_bytes)).convert('RGB')
                for img_bytes in images
            ]
            
            # Batch preprocess
            inputs = self._clip_processor(images=pil_images, return_tensors="pt", padding=True)
            
            if self._device != "cpu":
                inputs = {k: v.to(self._device) for k, v in inputs.items()}
            
            # Get embeddings
            with torch.no_grad():
                features = self._clip_model.get_image_features(**inputs)
            
            # Normalize
            embeddings = features.cpu().numpy()
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / norms
            
            # Create result objects
            results = []
            for i, (img_bytes, embedding) in enumerate(zip(images, embeddings)):
                img_hash = hashlib.sha256(img_bytes).hexdigest()[:16]
                
                result = ImageEmbedding(
                    vector=embedding,
                    model_name="clip-vit-base-patch32",
                    image_hash=img_hash,
                    dimensions=len(embedding),
                    normalized=True,
                )
                results.append(result)
                
                # Cache
                self._embedding_cache[img_hash] = result
            
            return results
            
        except Exception as e:
            logger.error(f"Batch encoding error: {e}")
            return [
                self._fallback_image_embedding(img, hashlib.sha256(img).hexdigest()[:16])
                for img in images
            ]


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Functions
# ─────────────────────────────────────────────────────────────────────────────

async def search_by_image(
    image_bytes: bytes,
    limit: int = 10
) -> List[SearchResult]:
    """
    Convenience function for image-based search.
    
    Args:
        image_bytes: Query image bytes
        limit: Maximum results
        
    Returns:
        List of SearchResult objects
    """
    service = VisualSearchAIService()
    request = VisualSearchRequest(
        image_bytes=image_bytes,
        limit=limit,
    )
    result = await service.infer(request)
    return result.results


async def search_by_text(
    text_query: str,
    limit: int = 10
) -> List[SearchResult]:
    """
    Convenience function for text-based search.
    
    Args:
        text_query: Text search query
        limit: Maximum results
        
    Returns:
        List of SearchResult objects
    """
    service = VisualSearchAIService()
    request = VisualSearchRequest(
        text_query=text_query,
        limit=limit,
    )
    result = await service.infer(request)
    return result.results
