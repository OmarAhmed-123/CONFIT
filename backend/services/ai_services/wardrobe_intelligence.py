"""
CONFIT AI Services - Wardrobe Intelligence
==========================================
Intelligent wardrobe analysis and clothing detection.

Features:
- Clothing detection and segmentation
- Color extraction and analysis
- Style classification
- Wardrobe analytics
- Outfit suggestions from wardrobe
"""

import asyncio
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set
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

class ClothingCategory(Enum):
    """Clothing categories."""
    TOP = "top"
    BOTTOM = "bottom"
    DRESS = "dress"
    OUTERWEAR = "outerwear"
    FOOTWEAR = "footwear"
    ACCESSORY = "accessory"
    BAG = "bag"
    JEWELRY = "jewelry"
    HEADWEAR = "headwear"
    SCARF = "scarf"
    UNDERWEAR = "underwear"
    SLEEPWEAR = "sleepwear"
    SWIMWEAR = "swimwear"
    ATHLETIC = "athletic"
    OTHER = "other"


class ClothingSubcategory(Enum):
    """Clothing subcategories."""
    # Tops
    T_SHIRT = "t_shirt"
    SHIRT = "shirt"
    BLOUSE = "blouse"
    SWEATER = "sweater"
    HOODIE = "hoodie"
    TANK_TOP = "tank_top"
    POLO = "polo"
    CARDIGAN = "cardigan"
    
    # Bottoms
    JEANS = "jeans"
    PANTS = "pants"
    SHORTS = "shorts"
    SKIRT = "skirt"
    LEGGINGS = "leggings"
    TROUSERS = "trousers"
    
    # Dresses
    MAXI_DRESS = "maxi_dress"
    MIDI_DRESS = "midi_dress"
    MINI_DRESS = "mini_dress"
    WRAP_DRESS = "wrap_dress"
    
    # Outerwear
    JACKET = "jacket"
    COAT = "coat"
    BLAZER = "blazer"
    VEST = "vest"
    PARKA = "parka"
    
    # Footwear
    SNEAKERS = "sneakers"
    BOOTS = "boots"
    HEELS = "heels"
    FLATS = "flats"
    SANDALS = "sandals"
    LOAFERS = "loafers"


class ColorFamily(Enum):
    """Color families."""
    NEUTRAL = "neutral"
    WARM = "warm"
    COOL = "cool"
    EARTH = "earth"
    PASTEL = "pastel"
    BRIGHT = "bright"
    DARK = "dark"


class StyleCategory(Enum):
    """Style categories."""
    CASUAL = "casual"
    FORMAL = "formal"
    BUSINESS = "business"
    SPORTY = "sporty"
    BOHEMIAN = "bohemian"
    MINIMALIST = "minimalist"
    STREETWEAR = "streetwear"
    VINTAGE = "vintage"
    ROMANTIC = "romantic"
    EDGY = "edgy"
    PREPPY = "preppy"
    CLASSIC = "classic"


class Season(Enum):
    """Seasons."""
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"
    ALL_SEASON = "all_season"


@dataclass
class ColorInfo:
    """Detailed color information."""
    name: str
    hex_code: str
    rgb: Tuple[int, int, int]
    hsv: Tuple[float, float, float]
    family: ColorFamily
    percentage: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "hex": self.hex_code,
            "rgb": self.rgb,
            "family": self.family.value,
            "percentage": round(self.percentage, 2),
        }


@dataclass
class ClothingItem:
    """Detected clothing item."""
    item_id: str
    category: ClothingCategory
    subcategory: Optional[ClothingSubcategory] = None
    colors: List[ColorInfo] = field(default_factory=list)
    dominant_color: Optional[ColorInfo] = None
    secondary_colors: List[ColorInfo] = field(default_factory=list)
    pattern: str = "solid"
    style_tags: List[StyleCategory] = field(default_factory=list)
    seasons: List[Season] = field(default_factory=list)
    formality_score: float = 0.5
    comfort_score: float = 0.5
    trend_score: float = 0.5
    
    # Detection metadata
    confidence: float = 0.0
    bounding_box: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h
    segmentation_mask: Optional[np.ndarray] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "category": self.category.value,
            "subcategory": self.subcategory.value if self.subcategory else None,
            "colors": [c.to_dict() for c in self.colors],
            "dominant_color": self.dominant_color.to_dict() if self.dominant_color else None,
            "pattern": self.pattern,
            "style_tags": [s.value for s in self.style_tags],
            "seasons": [s.value for s in self.seasons],
            "formality_score": round(self.formality_score, 2),
            "comfort_score": round(self.comfort_score, 2),
            "confidence": round(self.confidence, 2),
        }


@dataclass
class WardrobeStats:
    """Wardrobe statistics."""
    total_items: int = 0
    by_category: Dict[str, int] = field(default_factory=dict)
    by_color_family: Dict[str, int] = field(default_factory=dict)
    by_style: Dict[str, int] = field(default_factory=dict)
    by_season: Dict[str, int] = field(default_factory=dict)
    
    # Style metrics
    formality_avg: float = 0.0
    comfort_avg: float = 0.0
    trend_avg: float = 0.5
    
    # Wardrobe health
    color_diversity: float = 0.0
    style_diversity: float = 0.0
    category_balance: float = 0.0
    
    # Gaps and recommendations
    missing_essentials: List[str] = field(default_factory=list)
    underutilized_items: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_items": self.total_items,
            "by_category": self.by_category,
            "by_color_family": self.by_color_family,
            "by_style": self.by_style,
            "by_season": self.by_season,
            "style_metrics": {
                "formality_avg": round(self.formality_avg, 2),
                "comfort_avg": round(self.comfort_avg, 2),
                "trend_avg": round(self.trend_avg, 2),
            },
            "diversity_scores": {
                "color": round(self.color_diversity, 2),
                "style": round(self.style_diversity, 2),
                "category": round(self.category_balance, 2),
            },
            "recommendations": {
                "missing_essentials": self.missing_essentials,
                "underutilized_items": self.underutilized_items,
            },
        }


@dataclass
class WardrobeAnalysisRequest:
    """Request for wardrobe analysis."""
    image_bytes: Optional[bytes] = None
    wardrobe_items: Optional[List[Dict[str, Any]]] = None
    user_id: Optional[str] = None
    detect_clothing: bool = True
    extract_colors: bool = True
    classify_style: bool = True
    generate_stats: bool = True
    detect_gaps: bool = True


@dataclass
class WardrobeAnalysisResult:
    """Result from wardrobe analysis."""
    detected_items: List[ClothingItem] = field(default_factory=list)
    wardrobe_stats: Optional[WardrobeStats] = None
    style_profile: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    model_version: str = "wardrobe_intelligence_v1"


# ─────────────────────────────────────────────────────────────────────────────
# Wardrobe Intelligence Service
# ─────────────────────────────────────────────────────────────────────────────

class WardrobeIntelligenceService(AIServiceBase):
    """
    Intelligent wardrobe analysis service.
    
    Capabilities:
    - Clothing detection from images
    - Color extraction and classification
    - Style classification
    - Wardrobe statistics
    - Gap analysis and recommendations
    
    Usage:
        service = WardrobeIntelligenceService()
        
        # Analyze single image
        result = await service.infer(WardrobeAnalysisRequest(
            image_bytes=image_data,
            detect_clothing=True,
            extract_colors=True,
        ))
        
        # Analyze full wardrobe
        result = await service.infer(WardrobeAnalysisRequest(
            wardrobe_items=items_list,
            generate_stats=True,
            detect_gaps=True,
        ))
    """
    
    # Color name mappings
    COLOR_NAMES = {
        # Neutrals
        (0, 0, 0): "black",
        (255, 255, 255): "white",
        (128, 128, 128): "gray",
        (192, 192, 192): "silver",
        (245, 245, 220): "beige",
        (139, 90, 43): "brown",
        (0, 0, 128): "navy",
        
        # Warm colors
        (255, 0, 0): "red",
        (255, 165, 0): "orange",
        (255, 255, 0): "yellow",
        (255, 192, 203): "pink",
        (255, 0, 255): "magenta",
        (139, 69, 19): "rust",
        
        # Cool colors
        (0, 0, 255): "blue",
        (0, 128, 0): "green",
        (0, 255, 255): "cyan",
        (128, 0, 128): "purple",
        (0, 128, 128): "teal",
        
        # Earth tones
        (85, 107, 47): "olive",
        (210, 180, 140): "tan",
        (188, 143, 143): "rose",
        (244, 164, 96): "sand",
    }
    
    # Essential wardrobe items
    ESSENTIAL_ITEMS = {
        "tops": ["white_shirt", "black_top", "neutral_tee"],
        "bottoms": ["dark_jeans", "neutral_trousers"],
        "outerwear": ["blazer", "casual_jacket"],
        "footwear": ["neutral_sneakers", "dress_shoes"],
        "accessories": ["belt", "watch"],
    }
    
    # Category detection keywords
    CATEGORY_KEYWORDS = {
        ClothingCategory.TOP: ["shirt", "blouse", "top", "sweater", "hoodie", "t-shirt", "tank"],
        ClothingCategory.BOTTOM: ["pants", "jeans", "shorts", "skirt", "trousers", "leggings"],
        ClothingCategory.DRESS: ["dress", "gown", "jumpsuit", "romper"],
        ClothingCategory.OUTERWEAR: ["jacket", "coat", "blazer", "vest", "parka"],
        ClothingCategory.FOOTWEAR: ["shoes", "boots", "sneakers", "heels", "sandals"],
        ClothingCategory.ACCESSORY: ["belt", "watch", "scarf", "hat", "bag"],
    }
    
    def __init__(self, config: Optional[ModelConfig] = None):
        config = config or ModelConfig(
            name="wardrobe_intelligence",
            device=DeviceType.CUDA,
            batch_size=16,
        )
        super().__init__(config)
        
        self._detection_model = None
        self._segmentation_model = None
        self._classification_model = None
        self._device = None
    
    @property
    def model_name(self) -> str:
        return "wardrobe_intelligence_v1"
    
    async def load_model(self) -> None:
        """Load models for wardrobe analysis."""
        try:
            import torch
            from transformers import AutoImageProcessor, AutoModelForImageClassification
            
            # Load classification model
            model_name = "microsoft/resnet-50"
            
            self._processor = AutoImageProcessor.from_pretrained(model_name)
            self._classification_model = AutoModelForImageClassification.from_pretrained(model_name)
            
            # Set device
            self._device = self._get_device()
            if self._device != "cpu":
                self._classification_model = self._classification_model.to(self._device)
            
            self._classification_model.eval()
            self._model = self._classification_model
            
            logger.info(f"Loaded wardrobe intelligence model on {self._device}")
            
        except ImportError:
            logger.info("Transformers not available, using rule-based detection")
            self._model = "rule_based"
    
    async def _infer(self, input_data: WardrobeAnalysisRequest) -> WardrobeAnalysisResult:
        """
        Analyze wardrobe or clothing image.
        
        Args:
            input_data: WardrobeAnalysisRequest
            
        Returns:
            WardrobeAnalysisResult with detected items and stats
        """
        start_time = datetime.now(timezone.utc)
        
        detected_items = []
        wardrobe_stats = None
        style_profile = {}
        recommendations = []
        
        # Step 1: Detect clothing from image
        if input_data.image_bytes and input_data.detect_clothing:
            detected_items = await self._detect_clothing(input_data.image_bytes)
        
        # Step 2: Analyze existing wardrobe items
        if input_data.wardrobe_items:
            for item_data in input_data.wardrobe_items:
                item = await self._analyze_wardrobe_item(item_data)
                detected_items.append(item)
        
        # Step 3: Generate wardrobe statistics
        if input_data.generate_stats and detected_items:
            wardrobe_stats = self._compute_wardrobe_stats(detected_items)
        
        # Step 4: Build style profile
        if detected_items:
            style_profile = self._build_style_profile(detected_items)
        
        # Step 5: Detect gaps and generate recommendations
        if input_data.detect_gaps and wardrobe_stats:
            recommendations = self._generate_recommendations(
                detected_items, wardrobe_stats
            )
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return WardrobeAnalysisResult(
            detected_items=detected_items,
            wardrobe_stats=wardrobe_stats,
            style_profile=style_profile,
            recommendations=recommendations,
            processing_time_ms=processing_time,
        )
    
    async def _detect_clothing(
        self,
        image_bytes: bytes
    ) -> List[ClothingItem]:
        """
        Detect clothing items from image.
        
        Uses object detection and segmentation.
        """
        items = []
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            image_array = np.array(image)
            
            if self._model == "rule_based":
                # Rule-based detection
                item = await self._rule_based_detection(image_array)
                items.append(item)
            else:
                # ML-based detection
                items = await self._ml_based_detection(image_array, image_bytes)
            
        except Exception as e:
            logger.error(f"Clothing detection error: {e}")
        
        return items
    
    async def _rule_based_detection(
        self,
        image: np.ndarray
    ) -> ClothingItem:
        """Rule-based clothing detection using image analysis."""
        h, w = image.shape[:2]
        aspect = w / max(h, 1)
        
        # Detect category from aspect ratio
        if aspect < 0.5:
            category = ClothingCategory.DRESS
        elif aspect < 0.7:
            category = ClothingCategory.BOTTOM
        elif aspect > 1.3:
            category = ClothingCategory.FOOTWEAR
        else:
            category = ClothingCategory.TOP
        
        # Extract colors
        colors = await self._extract_colors(image)
        
        # Detect pattern
        pattern = self._detect_pattern(image)
        
        # Infer style
        style_tags = self._infer_style(category, colors, pattern)
        
        # Infer seasons
        seasons = self._infer_seasons(colors, category)
        
        return ClothingItem(
            item_id=hashlib.md5(image.tobytes()).hexdigest()[:12],
            category=category,
            colors=colors,
            dominant_color=colors[0] if colors else None,
            secondary_colors=colors[1:4] if len(colors) > 1 else [],
            pattern=pattern,
            style_tags=style_tags,
            seasons=seasons,
            confidence=0.6,
        )
    
    async def _ml_based_detection(
        self,
        image: np.ndarray,
        image_bytes: bytes
    ) -> List[ClothingItem]:
        """ML-based clothing detection."""
        items = []
        
        try:
            import torch
            from PIL import Image
            
            # Convert to PIL
            pil_image = Image.fromarray(image)
            
            # Preprocess
            inputs = self._processor(images=pil_image, return_tensors="pt")
            
            if self._device != "cpu":
                inputs = {k: v.to(self._device) for k, v in inputs.items()}
            
            # Classify
            with torch.no_grad():
                outputs = self._classification_model(**inputs)
                logits = outputs.logits
                probs = torch.nn.functional.softmax(logits, dim=-1)
            
            # Get top predictions
            top_probs, top_indices = torch.topk(probs, 5)
            
            # Map to clothing categories
            # Note: ResNet labels need to be mapped to clothing categories
            predicted_category = self._map_to_clothing_category(top_indices[0][0].item())
            confidence = float(top_probs[0][0])
            
            # Extract colors
            colors = await self._extract_colors(image)
            
            # Detect pattern
            pattern = self._detect_pattern(image)
            
            item = ClothingItem(
                item_id=hashlib.md5(image_bytes).hexdigest()[:12],
                category=predicted_category,
                colors=colors,
                dominant_color=colors[0] if colors else None,
                pattern=pattern,
                confidence=confidence,
            )
            
            items.append(item)
            
        except Exception as e:
            logger.error(f"ML detection error: {e}")
            # Fallback to rule-based
            item = await self._rule_based_detection(image)
            items.append(item)
        
        return items
    
    def _map_to_clothing_category(
        self,
        class_index: int
    ) -> ClothingCategory:
        """Map classification index to clothing category."""
        # Simplified mapping - would use proper label mapping in production
        category_ranges = {
            (0, 200): ClothingCategory.TOP,
            (200, 400): ClothingCategory.BOTTOM,
            (400, 500): ClothingCategory.DRESS,
            (500, 700): ClothingCategory.OUTERWEAR,
            (700, 900): ClothingCategory.ACCESSORY,
        }
        
        for (start, end), category in category_ranges.items():
            if start <= class_index < end:
                return category
        
        return ClothingCategory.OTHER
    
    async def _extract_colors(
        self,
        image: np.ndarray,
        n_colors: int = 5
    ) -> List[ColorInfo]:
        """
        Extract dominant colors from image.
        
        Uses k-means clustering for color extraction.
        """
        colors = []
        
        try:
            from sklearn.cluster import KMeans
            
            # Reshape image
            pixels = image.reshape(-1, 3)
            
            # Sample for performance
            if len(pixels) > 10000:
                indices = np.random.choice(len(pixels), 10000, replace=False)
                pixels = pixels[indices]
            
            # Remove near-white and near-black background
            brightness = np.mean(pixels, axis=1)
            mask = (brightness > 20) & (brightness < 240)
            pixels = pixels[mask]
            
            if len(pixels) < 100:
                pixels = image.reshape(-1, 3)
            
            # Cluster colors
            kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=3)
            kmeans.fit(pixels)
            
            # Get cluster centers and sizes
            centers = kmeans.cluster_centers_.astype(int)
            labels = kmeans.labels_
            counts = np.bincount(labels)
            
            # Sort by frequency
            sorted_indices = np.argsort(-counts)
            
            total_pixels = len(pixels)
            
            for idx in sorted_indices:
                rgb = tuple(centers[idx])
                percentage = counts[idx] / total_pixels * 100
                
                color_info = self._create_color_info(rgb, percentage)
                colors.append(color_info)
            
        except ImportError:
            # Fallback: simple color extraction
            colors = self._simple_color_extraction(image)
        
        return colors
    
    def _create_color_info(
        self,
        rgb: Tuple[int, int, int],
        percentage: float
    ) -> ColorInfo:
        """Create ColorInfo from RGB values."""
        # Convert to HSV
        import colorsys
        r, g, b = [x / 255.0 for x in rgb]
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        hsv = (h * 360, s * 100, v * 100)
        
        # Get color name
        name = self._get_color_name(rgb)
        
        # Get hex code
        hex_code = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        
        # Determine color family
        family = self._get_color_family(hsv)
        
        return ColorInfo(
            name=name,
            hex_code=hex_code,
            rgb=rgb,
            hsv=hsv,
            family=family,
            percentage=percentage,
        )
    
    def _get_color_name(
        self,
        rgb: Tuple[int, int, int]
    ) -> str:
        """Get color name from RGB values."""
        # Find closest named color
        min_dist = float('inf')
        closest_name = "unknown"
        
        for ref_rgb, name in self.COLOR_NAMES.items():
            dist = sum((a - b) ** 2 for a, b in zip(rgb, ref_rgb))
            if dist < min_dist:
                min_dist = dist
                closest_name = name
        
        return closest_name
    
    def _get_color_family(
        self,
        hsv: Tuple[float, float, float]
    ) -> ColorFamily:
        """Determine color family from HSV values."""
        h, s, v = hsv
        
        # Low saturation = neutral
        if s < 15:
            return ColorFamily.NEUTRAL
        
        # Low value = dark
        if v < 25:
            return ColorFamily.DARK
        
        # Pastel = low saturation, high value
        if s < 50 and v > 75:
            return ColorFamily.PASTEL
        
        # Bright = high saturation, high value
        if s > 70 and v > 60:
            return ColorFamily.BRIGHT
        
        # Determine warm/cool by hue
        if h < 60 or h > 300:  # Red to yellow, or magenta
            return ColorFamily.WARM
        elif 60 <= h <= 150:  # Yellow to green
            return ColorFamily.EARTH
        else:  # Green to blue to purple
            return ColorFamily.COOL
    
    def _simple_color_extraction(
        self,
        image: np.ndarray,
        n_colors: int = 5
    ) -> List[ColorInfo]:
        """Simple color extraction without sklearn."""
        # Quantize image
        quantized = (image // 32) * 32
        
        # Count colors
        pixels = quantized.reshape(-1, 3)
        color_counts = {}
        
        for pixel in pixels:
            color = tuple(pixel)
            color_counts[color] = color_counts.get(color, 0) + 1
        
        # Sort by frequency
        sorted_colors = sorted(color_counts.items(), key=lambda x: -x[1])
        
        total_pixels = len(pixels)
        colors = []
        
        for rgb, count in sorted_colors[:n_colors]:
            percentage = count / total_pixels * 100
            color_info = self._create_color_info(rgb, percentage)
            colors.append(color_info)
        
        return colors
    
    def _detect_pattern(
        self,
        image: np.ndarray
    ) -> str:
        """Detect pattern type in clothing."""
        try:
            import cv2
            
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # Edge detection
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            # Texture analysis using local binary patterns
            if edge_density < 0.03:
                return "solid"
            elif edge_density < 0.08:
                return "textured"
            elif edge_density < 0.15:
                return "patterned"
            else:
                # Check for specific patterns
                return self._classify_pattern_type(edges, gray)
                
        except Exception:
            return "solid"
    
    def _classify_pattern_type(
        self,
        edges: np.ndarray,
        gray: np.ndarray
    ) -> str:
        """Classify specific pattern type."""
        # Check for stripes (horizontal or vertical lines)
        h_lines = np.sum(edges, axis=0)
        v_lines = np.sum(edges, axis=1)
        
        h_variance = np.var(h_lines)
        v_variance = np.var(v_lines)
        
        if h_variance > 2 * v_variance or v_variance > 2 * h_variance:
            return "striped"
        
        # Check for plaid (grid pattern)
        if h_variance > 100 and v_variance > 100:
            return "plaid"
        
        return "patterned"
    
    def _infer_style(
        self,
        category: ClothingCategory,
        colors: List[ColorInfo],
        pattern: str
    ) -> List[StyleCategory]:
        """Infer style tags from visual features."""
        styles = []
        
        # Color-based inference
        if colors:
            dominant = colors[0]
            
            if dominant.family == ColorFamily.NEUTRAL:
                styles.append(StyleCategory.MINIMALIST)
            elif dominant.family == ColorFamily.PASTEL:
                styles.append(StyleCategory.ROMANTIC)
            elif dominant.family == ColorFamily.BRIGHT:
                styles.append(StyleCategory.STREETWEAR)
        
        # Pattern-based inference
        if pattern == "solid":
            if StyleCategory.MINIMALIST not in styles:
                styles.append(StyleCategory.MINIMALIST)
        elif pattern in ["striped", "plaid"]:
            styles.append(StyleCategory.CLASSIC)
        elif pattern == "patterned":
            styles.append(StyleCategory.BOHEMIAN)
        
        # Category-based inference
        if category == ClothingCategory.DRESS:
            styles.append(StyleCategory.FORMAL)
        elif category == ClothingCategory.OUTERWEAR:
            styles.append(StyleCategory.CLASSIC)
        
        return list(set(styles))[:3]  # Limit to 3 styles
    
    def _infer_seasons(
        self,
        colors: List[ColorInfo],
        category: ClothingCategory
    ) -> List[Season]:
        """Infer appropriate seasons for item."""
        seasons = []
        
        if colors:
            dominant = colors[0]
            h, s, v = dominant.hsv
            
            # Bright, light colors = summer
            if v > 70 and s > 50:
                seasons.append(Season.SUMMER)
            
            # Warm earth tones = fall
            if 30 <= h <= 60 or dominant.family == ColorFamily.EARTH:
                seasons.append(Season.FALL)
            
            # Dark, muted = winter
            if v < 40 or dominant.family == ColorFamily.DARK:
                seasons.append(Season.WINTER)
            
            # Pastels and brights = spring
            if dominant.family == ColorFamily.PASTEL or (v > 60 and s > 40):
                seasons.append(Season.SPRING)
        
        # Category-based
        if category == ClothingCategory.OUTERWEAR:
            if Season.WINTER not in seasons:
                seasons.append(Season.WINTER)
            if Season.FALL not in seasons:
                seasons.append(Season.FALL)
        
        return seasons if seasons else [Season.ALL_SEASON]
    
    async def _analyze_wardrobe_item(
        self,
        item_data: Dict[str, Any]
    ) -> ClothingItem:
        """Analyze a wardrobe item from stored data."""
        # Extract from stored metadata
        category_str = item_data.get("category", "other")
        category = ClothingCategory(category_str) if category_str in [c.value for c in ClothingCategory] else ClothingCategory.OTHER
        
        # Build color info
        colors = []
        for color_data in item_data.get("colors", []):
            if isinstance(color_data, dict):
                color_info = ColorInfo(
                    name=color_data.get("name", "unknown"),
                    hex_code=color_data.get("hex", "#000000"),
                    rgb=tuple(color_data.get("rgb", [0, 0, 0])),
                    hsv=(0, 0, 0),
                    family=ColorFamily.NEUTRAL,
                    percentage=color_data.get("percentage", 0),
                )
                colors.append(color_info)
        
        # Build style tags
        style_tags = []
        for style_str in item_data.get("style_tags", []):
            try:
                style_tags.append(StyleCategory(style_str))
            except ValueError:
                pass
        
        return ClothingItem(
            item_id=item_data.get("id", "unknown"),
            category=category,
            colors=colors,
            dominant_color=colors[0] if colors else None,
            pattern=item_data.get("pattern", "solid"),
            style_tags=style_tags,
            confidence=1.0,  # Stored data is assumed accurate
        )
    
    def _compute_wardrobe_stats(
        self,
        items: List[ClothingItem]
    ) -> WardrobeStats:
        """Compute comprehensive wardrobe statistics."""
        stats = WardrobeStats(total_items=len(items))
        
        # Count by category
        for item in items:
            cat = item.category.value
            stats.by_category[cat] = stats.by_category.get(cat, 0) + 1
            
            # Count by color family
            if item.dominant_color:
                family = item.dominant_color.family.value
                stats.by_color_family[family] = stats.by_color_family.get(family, 0) + 1
            
            # Count by style
            for style in item.style_tags:
                stats.by_style[style.value] = stats.by_style.get(style.value, 0) + 1
            
            # Count by season
            for season in item.seasons:
                stats.by_season[season.value] = stats.by_season.get(season.value, 0) + 1
            
            # Accumulate scores
            stats.formality_avg += item.formality_score
            stats.comfort_avg += item.comfort_score
            stats.trend_avg += item.trend_score
        
        # Average scores
        n = len(items)
        if n > 0:
            stats.formality_avg /= n
            stats.comfort_avg /= n
            stats.trend_avg /= n
        
        # Compute diversity scores
        stats.color_diversity = self._compute_diversity(stats.by_color_family)
        stats.style_diversity = self._compute_diversity(stats.by_style)
        stats.category_balance = self._compute_balance(stats.by_category)
        
        # Detect missing essentials
        stats.missing_essentials = self._detect_missing_essentials(items)
        
        return stats
    
    def _compute_diversity(
        self,
        distribution: Dict[str, int]
    ) -> float:
        """Compute diversity score using entropy."""
        if not distribution:
            return 0.0
        
        total = sum(distribution.values())
        if total == 0:
            return 0.0
        
        probs = [v / total for v in distribution.values()]
        
        # Shannon entropy normalized
        import math
        entropy = -sum(p * math.log(p + 1e-10) for p in probs if p > 0)
        max_entropy = math.log(len(distribution))
        
        return entropy / max_entropy if max_entropy > 0 else 0.0
    
    def _compute_balance(
        self,
        distribution: Dict[str, int]
    ) -> float:
        """Compute category balance score."""
        if not distribution:
            return 0.0
        
        # Ideal distribution
        categories = list(ClothingCategory)
        ideal_per_category = sum(distribution.values()) / len(categories)
        
        if ideal_per_category == 0:
            return 0.0
        
        # Compute deviation from ideal
        deviations = []
        for cat in categories:
            actual = distribution.get(cat.value, 0)
            deviation = abs(actual - ideal_per_category) / ideal_per_category
            deviations.append(deviation)
        
        # Balance is inverse of average deviation
        avg_deviation = sum(deviations) / len(deviations)
        return max(0, 1 - avg_deviation)
    
    def _detect_missing_essentials(
        self,
        items: List[ClothingItem]
    ) -> List[str]:
        """Detect missing essential wardrobe items."""
        missing = []
        
        # Build inventory
        inventory = {
            "tops": [],
            "bottoms": [],
            "outerwear": [],
            "footwear": [],
            "accessories": [],
        }
        
        for item in items:
            if item.category == ClothingCategory.TOP:
                inventory["tops"].append(item)
            elif item.category == ClothingCategory.BOTTOM:
                inventory["bottoms"].append(item)
            elif item.category == ClothingCategory.OUTERWEAR:
                inventory["outerwear"].append(item)
            elif item.category == ClothingCategory.FOOTWEAR:
                inventory["footwear"].append(item)
            elif item.category == ClothingCategory.ACCESSORY:
                inventory["accessories"].append(item)
        
        # Check for essentials
        for category, essentials in self.ESSENTIAL_ITEMS.items():
            if not inventory.get(category):
                missing.extend(essentials)
            elif len(inventory[category]) < 2:
                missing.append(f"More {category}")
        
        return missing[:5]  # Limit recommendations
    
    def _build_style_profile(
        self,
        items: List[ClothingItem]
    ) -> Dict[str, Any]:
        """Build user style profile from wardrobe."""
        profile = {
            "dominant_styles": [],
            "color_preferences": [],
            "formality_range": (1.0, 0.0),
            "preferred_patterns": {},
            "seasonal_distribution": {},
        }
        
        # Aggregate style tags
        style_counts = {}
        for item in items:
            for style in item.style_tags:
                style_counts[style.value] = style_counts.get(style.value, 0) + 1
        
        # Sort styles
        sorted_styles = sorted(style_counts.items(), key=lambda x: -x[1])
        profile["dominant_styles"] = [s[0] for s in sorted_styles[:3]]
        
        # Aggregate colors
        color_counts = {}
        for item in items:
            if item.dominant_color:
                name = item.dominant_color.name
                color_counts[name] = color_counts.get(name, 0) + 1
        
        sorted_colors = sorted(color_counts.items(), key=lambda x: -x[1])
        profile["color_preferences"] = [c[0] for c in sorted_colors[:5]]
        
        # Formality range
        formalities = [item.formality_score for item in items]
        if formalities:
            profile["formality_range"] = (min(formalities), max(formalities))
        
        return profile
    
    def _generate_recommendations(
        self,
        items: List[ClothingItem],
        stats: WardrobeStats
    ) -> List[str]:
        """Generate wardrobe improvement recommendations."""
        recommendations = []
        
        # Missing essentials
        if stats.missing_essentials:
            recommendations.append(
                f"Consider adding: {', '.join(stats.missing_essentials[:3])}"
            )
        
        # Color diversity
        if stats.color_diversity < 0.5:
            recommendations.append(
                "Your wardrobe could benefit from more color variety"
            )
        
        # Category balance
        if stats.category_balance < 0.5:
            dominant = max(stats.by_category.items(), key=lambda x: x[1])
            recommendations.append(
                f"You have many {dominant[0]}s. Consider diversifying"
            )
        
        # Seasonal gaps
        if len(stats.by_season) < 3:
            recommendations.append(
                "Add items for missing seasons in your wardrobe"
            )
        
        return recommendations


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Functions
# ─────────────────────────────────────────────────────────────────────────────

async def analyze_clothing_image(
    image_bytes: bytes
) -> List[ClothingItem]:
    """
    Convenience function to analyze clothing image.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        List of detected ClothingItem objects
    """
    service = WardrobeIntelligenceService()
    request = WardrobeAnalysisRequest(
        image_bytes=image_bytes,
        detect_clothing=True,
        extract_colors=True,
        classify_style=True,
    )
    result = await service.infer(request)
    return result.detected_items


async def get_wardrobe_stats(
    wardrobe_items: List[Dict[str, Any]]
) -> WardrobeStats:
    """
    Convenience function to get wardrobe statistics.
    
    Args:
        wardrobe_items: List of wardrobe item dictionaries
        
    Returns:
        WardrobeStats with analytics
    """
    service = WardrobeIntelligenceService()
    request = WardrobeAnalysisRequest(
        wardrobe_items=wardrobe_items,
        generate_stats=True,
        detect_gaps=True,
    )
    result = await service.infer(request)
    return result.wardrobe_stats
