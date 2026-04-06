"""
CONFIT Backend — Visual Search Service
=====================================
Real visual search implementation using image embeddings.

Features:
- Image feature extraction
- Similarity search using embeddings
- Category detection
- Color extraction
- Style classification
"""

import io
import logging
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class ImageFeatures:
    """Extracted features from an image."""
    # Embedding vector (for similarity search)
    embedding: Optional[np.ndarray] = None
    
    # Detected attributes
    category: str = "unknown"
    category_confidence: float = 0.0
    
    # Color features
    dominant_colors: List[Tuple[int, int, int]] = field(default_factory=list)
    color_histogram: Optional[np.ndarray] = None
    
    # Style features
    style_tags: List[str] = field(default_factory=list)
    pattern: str = "solid"
    
    # Additional metadata
    aspect_ratio: float = 1.0
    brightness: float = 0.0
    contrast: float = 0.0


@dataclass
class SearchResult:
    """Result from visual search."""
    product_id: str
    similarity_score: float
    category_match: bool
    color_similarity: float
    style_match: bool
    
    # Debug info
    match_reasons: List[str] = field(default_factory=list)


class VisualSearchService:
    """
    Real visual search implementation.
    
    Uses image embeddings and feature extraction to find
    visually similar products.
    
    Usage:
        service = VisualSearchService()
        
        # Extract features from query image
        features = await service.extract_features(image_bytes)
        
        # Search for similar products
        results = await service.search_similar(features, limit=10)
    """
    
    def __init__(self, embedding_model: str = "clip"):
        """
        Initialize visual search service.
        
        Args:
            embedding_model: Model to use for embeddings (clip, vit, etc.)
        """
        self.embedding_model = embedding_model
        self._model = None
        self._preprocess = None
        
        # Category classification thresholds
        self.category_keywords = {
            'tops': ['shirt', 'blouse', 't-shirt', 'sweater', 'jacket', 'coat', 'hoodie'],
            'pants': ['pants', 'jeans', 'trousers', 'shorts', 'leggings'],
            'dresses': ['dress', 'gown', 'romper', 'jumpsuit'],
            'shoes': ['shoe', 'boot', 'sneaker', 'heel', 'sandal'],
            'bags': ['bag', 'purse', 'backpack', 'tote', 'clutch'],
            'accessories': ['hat', 'scarf', 'belt', 'watch', 'jewelry', 'sunglasses'],
        }
        
        # Style tags mapping
        self.style_patterns = {
            'casual': ['t-shirt', 'jeans', 'hoodie', 'sneaker'],
            'formal': ['blazer', 'dress', 'heel', 'oxford'],
            'sporty': ['athletic', 'sport', 'gym', 'running'],
            'bohemian': ['flowy', 'floral', 'embroidered', 'fringe'],
            'minimalist': ['simple', 'clean', 'monochrome', 'basic'],
        }
    
    # ==========================================
    # Feature Extraction
    # ==========================================
    
    async def extract_features(
        self,
        image_bytes: bytes,
        extract_embedding: bool = True
    ) -> ImageFeatures:
        """
        Extract comprehensive features from an image.
        
        Args:
            image_bytes: Raw image bytes
            extract_embedding: Whether to compute embedding vector
            
        Returns:
            ImageFeatures with all extracted attributes
        """
        # Load image
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        image_array = np.array(image)
        
        features = ImageFeatures()
        
        # Extract basic image properties
        features.aspect_ratio = image.width / max(image.height, 1)
        
        # Calculate brightness and contrast
        gray = np.array(image.convert('L'))
        features.brightness = float(np.mean(gray)) / 255.0
        features.contrast = float(np.std(gray)) / 255.0
        
        # Extract color features
        features.dominant_colors = self._extract_dominant_colors(image_array)
        features.color_histogram = self._compute_color_histogram(image_array)
        
        # Detect category
        category, confidence = await self._detect_category(image_array)
        features.category = category
        features.category_confidence = confidence
        
        # Detect pattern
        features.pattern = self._detect_pattern(image_array)
        
        # Generate style tags
        features.style_tags = self._infer_style_tags(
            features.category, features.pattern, features.dominant_colors
        )
        
        # Extract embedding if requested
        if extract_embedding:
            features.embedding = await self._compute_embedding(image_array)
        
        return features
    
    def _extract_dominant_colors(
        self,
        image: np.ndarray,
        n_colors: int = 5
    ) -> List[Tuple[int, int, int]]:
        """Extract dominant colors using k-means clustering."""
        try:
            from sklearn.cluster import KMeans
            
            # Reshape image to list of pixels
            pixels = image.reshape(-1, 3)
            
            # Sample for performance
            if len(pixels) > 10000:
                indices = np.random.choice(len(pixels), 10000, replace=False)
                pixels = pixels[indices]
            
            # Cluster colors
            kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=3)
            kmeans.fit(pixels)
            
            # Get dominant colors sorted by cluster size
            colors = kmeans.cluster_centers_.astype(int)
            counts = np.bincount(kmeans.labels_)
            
            sorted_indices = np.argsort(-counts)
            dominant = [tuple(colors[i]) for i in sorted_indices]
            
            return dominant
            
        except ImportError:
            # Fallback: simple color quantization
            return self._simple_color_extraction(image, n_colors)
    
    def _simple_color_extraction(
        self,
        image: np.ndarray,
        n_colors: int = 5
    ) -> List[Tuple[int, int, int]]:
        """Simple color extraction without sklearn."""
        # Quantize to 16 levels per channel
        quantized = (image // 16) * 16
        
        # Find unique colors and their counts
        pixels = quantized.reshape(-1, 3)
        
        # Count color frequencies
        color_counts = {}
        for pixel in pixels:
            color = tuple(pixel)
            color_counts[color] = color_counts.get(color, 0) + 1
        
        # Sort by frequency
        sorted_colors = sorted(color_counts.items(), key=lambda x: -x[1])
        
        return [color for color, _ in sorted_colors[:n_colors]]
    
    def _compute_color_histogram(
        self,
        image: np.ndarray,
        bins: int = 32
    ) -> np.ndarray:
        """Compute color histogram for color similarity matching."""
        import cv2
        
        # Convert to HSV for better color representation
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        
        # Compute histogram for H, S, V channels
        h_hist = cv2.calcHist([hsv], [0], None, [bins], [0, 180])
        s_hist = cv2.calcHist([hsv], [1], None, [bins], [0, 256])
        v_hist = cv2.calcHist([hsv], [2], None, [bins], [0, 256])
        
        # Normalize and concatenate
        h_hist = cv2.normalize(h_hist, None).flatten()
        s_hist = cv2.normalize(s_hist, None).flatten()
        v_hist = cv2.normalize(v_hist, None).flatten()
        
        return np.concatenate([h_hist, s_hist, v_hist])
    
    async def _detect_category(
        self,
        image: np.ndarray
    ) -> Tuple[str, float]:
        """
        Detect garment category from image.
        
        Uses shape analysis and aspect ratio heuristics.
        In production, would use trained classifier.
        """
        h, w = image.shape[:2]
        aspect = w / max(h, 1)
        
        # Shape-based heuristics
        if aspect < 0.6:
            # Tall and narrow - likely pants or dress
            return self._detect_tall_garment(image)
        elif aspect > 1.2:
            # Wide - likely top or shoes
            return self._detect_wide_garment(image)
        else:
            # Square-ish
            return self._detect_square_garment(image)
    
    def _detect_tall_garment(self, image: np.ndarray) -> Tuple[str, float]:
        """Detect tall garment category."""
        h, w = image.shape[:2]
        
        # Check for pants-like shape (two distinct leg regions)
        # Simple heuristic: check color distribution in lower half
        
        lower_half = image[h//2:, :, :]
        left_region = lower_half[:, :w//3]
        right_region = lower_half[:, 2*w//3:]
        
        left_mean = np.mean(left_region, axis=(0, 1))
        right_mean = np.mean(right_region, axis=(0, 1))
        
        # If sides are similar, likely pants
        color_diff = np.linalg.norm(left_mean - right_mean)
        
        if color_diff < 30:
            return ('pants', 0.7)
        else:
            return ('dresses', 0.6)
    
    def _detect_wide_garment(self, image: np.ndarray) -> Tuple[str, float]:
        """Detect wide garment category."""
        h, w = image.shape[:2]
        
        # Wide items are often tops or shoes
        # Check for shoulder-like shape (wider at top)
        
        top_third = image[:h//3, :, :]
        mid_third = image[h//3:2*h//3, :, :]
        
        # Count non-background pixels
        top_pixels = np.sum(np.std(top_third, axis=2) > 10)
        mid_pixels = np.sum(np.std(mid_third, axis=2) > 10)
        
        if top_pixels > mid_pixels * 1.2:
            return ('tops', 0.7)
        else:
            return ('shoes', 0.5)
    
    def _detect_square_garment(self, image: np.ndarray) -> Tuple[str, float]:
        """Detect square-ish garment category."""
        # Could be bags, accessories, or tops
        
        # Check for handle/strap features (bags)
        # Check for small size (accessories)
        
        h, w = image.shape[:2]
        area = h * w
        
        # Simple heuristic based on color complexity
        color_variance = np.var(image)
        
        if color_variance > 2000:
            return ('tops', 0.6)
        elif color_variance > 1000:
            return ('bags', 0.5)
        else:
            return ('accessories', 0.5)
    
    def _detect_pattern(self, image: np.ndarray) -> str:
        """Detect pattern type in garment."""
        import cv2
        
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Calculate texture using local binary patterns or gradient
        # Simplified: use edge density
        
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # High edge density = patterned
        if edge_density > 0.15:
            return 'patterned'
        elif edge_density > 0.08:
            return 'textured'
        else:
            return 'solid'
    
    def _infer_style_tags(
        self,
        category: str,
        pattern: str,
        colors: List[Tuple[int, int, int]]
    ) -> List[str]:
        """Infer style tags from visual features."""
        tags = []
        
        # Color-based style inference
        if colors:
            # Check for neutral colors
            first_color = colors[0]
            brightness = np.mean(first_color)
            
            if brightness > 200:
                tags.append('light')
            elif brightness < 50:
                tags.append('dark')
            
            # Check for vibrant colors
            saturation = max(first_color) - min(first_color)
            if saturation > 100:
                tags.append('colorful')
            elif saturation < 30:
                tags.append('neutral')
        
        # Pattern-based style
        if pattern == 'solid':
            tags.append('minimalist')
        elif pattern == 'patterned':
            tags.append('bold')
        
        return tags
    
    async def _compute_embedding(
        self,
        image: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        Compute image embedding using CLIP or similar.
        
        In production, uses actual CLIP model.
        Falls back to color histogram if model unavailable.
        """
        try:
            # Try to use CLIP
            import torch
            from transformers import CLIPProcessor, CLIPModel
            
            if self._model is None:
                self._model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
                self._processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            
            # Prepare image
            pil_image = Image.fromarray(image)
            inputs = self._processor(images=pil_image, return_tensors="pt")
            
            # Get image features
            with torch.no_grad():
                features = self._model.get_image_features(**inputs)
            
            # Normalize embedding
            embedding = features.numpy().flatten()
            embedding = embedding / np.linalg.norm(embedding)
            
            return embedding
            
        except ImportError:
            logger.debug("CLIP not available, using fallback embedding")
            return self._compute_fallback_embedding(image)
        except Exception as e:
            logger.warning(f"Embedding computation failed: {e}")
            return self._compute_fallback_embedding(image)
    
    def _compute_fallback_embedding(
        self,
        image: np.ndarray
    ) -> np.ndarray:
        """Compute fallback embedding using color and texture features."""
        import cv2
        
        # Resize for consistency
        resized = cv2.resize(image, (224, 224))
        
        # Color histogram (normalized)
        hist = self._compute_color_histogram(resized, bins=16)
        
        # Texture features (HOG-like)
        gray = cv2.cvtColor(resized, cv2.COLOR_RGB2GRAY)
        
        # Gradient features
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        
        # Compute gradient histogram
        magnitude = np.sqrt(gx**2 + gy**2)
        angle = np.arctan2(gy, gx)
        
        # Bin by angle
        hist_bins = 16
        grad_hist = np.zeros(hist_bins)
        for i in range(hist_bins):
            mask = (angle >= i * np.pi / hist_bins) & (angle < (i + 1) * np.pi / hist_bins)
            grad_hist[i] = np.sum(magnitude[mask])
        
        # Normalize
        grad_hist = grad_hist / (np.linalg.norm(grad_hist) + 1e-6)
        
        # Combine features
        embedding = np.concatenate([hist, grad_hist])
        
        # Normalize final embedding
        embedding = embedding / (np.linalg.norm(embedding) + 1e-6)
        
        return embedding
    
    # ==========================================
    # Similarity Search
    # ==========================================
    
    async def search_similar(
        self,
        query_features: ImageFeatures,
        product_features: List[Dict[str, Any]],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for similar products using extracted features.
        
        Args:
            query_features: Features from query image
            product_features: List of product feature dicts from database
            limit: Maximum results to return
            filters: Optional filters (category, price range, etc.)
            
        Returns:
            List of SearchResult objects
        """
        results = []
        
        for product in product_features:
            # Apply filters
            if filters:
                if not self._matches_filters(product, filters):
                    continue
            
            # Calculate similarity scores
            scores = self._calculate_similarity(query_features, product)
            
            result = SearchResult(
                product_id=product['id'],
                similarity_score=scores['overall'],
                category_match=scores['category_match'],
                color_similarity=scores['color_similarity'],
                style_match=scores['style_match'],
                match_reasons=scores['reasons'],
            )
            
            results.append(result)
        
        # Sort by similarity score
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return results[:limit]
    
    def _matches_filters(
        self,
        product: Dict[str, Any],
        filters: Dict[str, Any]
    ) -> bool:
        """Check if product matches filter criteria."""
        # Category filter
        if 'category' in filters:
            if product.get('category') != filters['category']:
                return False
        
        # Price range filter
        if 'min_price' in filters or 'max_price' in filters:
            price = product.get('price', 0)
            if 'min_price' in filters and price < filters['min_price']:
                return False
            if 'max_price' in filters and price > filters['max_price']:
                return False
        
        # Brand filter
        if 'brands' in filters:
            if product.get('brand') not in filters['brands']:
                return False
        
        return True
    
    def _calculate_similarity(
        self,
        query: ImageFeatures,
        product: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate similarity scores between query and product."""
        scores = {
            'overall': 0.0,
            'category_match': False,
            'color_similarity': 0.0,
            'style_match': False,
            'reasons': [],
        }
        
        # Category match
        product_category = product.get('category', 'unknown')
        scores['category_match'] = (query.category == product_category)
        if scores['category_match']:
            scores['reasons'].append(f"Category match: {query.category}")
        
        # Color similarity
        product_colors = product.get('colors', [])
        if product_colors and query.dominant_colors:
            scores['color_similarity'] = self._compute_color_similarity(
                query.dominant_colors,
                product_colors
            )
            if scores['color_similarity'] > 0.7:
                scores['reasons'].append("Similar colors")
        
        # Style match
        product_tags = product.get('style_tags', [])
        query_tags = set(query.style_tags)
        product_tags_set = set(product_tags)
        
        if query_tags and product_tags_set:
            overlap = query_tags & product_tags_set
            scores['style_match'] = len(overlap) > 0
            if scores['style_match']:
                scores['reasons'].append(f"Style match: {overlap}")
        
        # Embedding similarity (if available)
        embedding_score = 0.0
        if query.embedding is not None:
            product_embedding = product.get('embedding')
            if product_embedding is not None:
                embedding_score = float(np.dot(query.embedding, product_embedding))
                if embedding_score > 0.8:
                    scores['reasons'].append("Visually similar")
        
        # Calculate overall score
        weights = {
            'category': 0.25,
            'color': 0.20,
            'style': 0.15,
            'embedding': 0.40,
        }
        
        scores['overall'] = (
            (1.0 if scores['category_match'] else 0.3) * weights['category'] +
            scores['color_similarity'] * weights['color'] +
            (1.0 if scores['style_match'] else 0.5) * weights['style'] +
            embedding_score * weights['embedding']
        )
        
        return scores
    
    def _compute_color_similarity(
        self,
        colors1: List[Tuple[int, int, int]],
        colors2: List[Any]
    ) -> float:
        """Compute color similarity between two color sets."""
        if not colors1 or not colors2:
            return 0.0
        
        # Convert to numpy arrays
        c1 = np.array(colors1[:3])  # Top 3 colors
        
        # Handle different color formats
        if isinstance(colors2[0], dict):
            c2 = np.array([[c.get('r', 0), c.get('g', 0), c.get('b', 0)] for c in colors2[:3]])
        else:
            c2 = np.array(colors2[:3])
        
        # Calculate minimum distance between color sets
        distances = []
        for color1 in c1:
            min_dist = float('inf')
            for color2 in c2:
                dist = np.linalg.norm(color1 - color2)
                min_dist = min(min_dist, dist)
            distances.append(min_dist)
        
        # Convert to similarity (0-1)
        avg_distance = np.mean(distances)
        similarity = max(0, 1 - avg_distance / 255)
        
        return similarity


# ==========================================
# Convenience Functions
# ==========================================

async def analyze_image(image_bytes: bytes) -> ImageFeatures:
    """
    Convenience function to analyze an image.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        ImageFeatures with extracted attributes
    """
    service = VisualSearchService()
    return await service.extract_features(image_bytes)


async def find_similar_products(
    image_bytes: bytes,
    products: List[Dict[str, Any]],
    limit: int = 10
) -> List[SearchResult]:
    """
    Convenience function to find similar products.
    
    Args:
        image_bytes: Query image bytes
        products: List of product dicts with features
        limit: Maximum results
        
    Returns:
        List of SearchResult objects
    """
    service = VisualSearchService()
    features = await service.extract_features(image_bytes)
    return await service.search_similar(features, products, limit)
