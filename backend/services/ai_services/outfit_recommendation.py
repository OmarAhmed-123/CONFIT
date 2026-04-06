"""
CONFIT AI Services - Outfit Recommendation Engine
=================================================
Intelligent outfit recommendations using collaborative filtering
and style vector matching.

Features:
- Collaborative filtering (user-item interactions)
- Style vector computation
- Outfit compatibility scoring
- Personalized recommendations
- Trend-aware suggestions
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set
import json
from collections import defaultdict

import numpy as np
from scipy.spatial.distance import cosine
from scipy.stats import pearsonr

from .base import (
    AIServiceBase,
    InferenceResult,
    ModelConfig,
    DeviceType,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────────────────────

class RecommendationType(Enum):
    """Types of recommendations."""
    OUTFIT_COMPLETE = "outfit_complete"
    ITEM_PAIRING = "item_pairing"
    STYLE_SIMILAR = "style_similar"
    TRENDING = "trending"
    SEASONAL = "seasonal"
    OCCASION = "occasion"
    COMPLEMENTARY = "complementary"


class ItemType(Enum):
    """Types of fashion items."""
    TOP = "top"
    BOTTOM = "bottom"
    DRESS = "dress"
    OUTERWEAR = "outerwear"
    SHOES = "shoes"
    ACCESSORY = "accessory"
    BAG = "bag"
    JEWELRY = "jewelry"
    HEADWEAR = "headwear"
    SCARF = "scarf"


@dataclass
class StyleVector:
    """
    Multi-dimensional style representation.
    
    Dimensions:
    - Formality (0-1): casual to formal
    - Minimalism (0-1): ornate to minimalist
    - Boldness (0-1): subtle to bold
    - Classicism (0-1): trendy to classic
    - Comfort (0-1): uncomfortable to comfortable
    - Edge (0-1): safe to edgy
    - Femininity (0-1): masculine to feminine
    - Seasonality (4 dims): spring/summer/fall/winter weights
    """
    formality: float = 0.5
    minimalism: float = 0.5
    boldness: float = 0.5
    classicism: float = 0.5
    comfort: float = 0.5
    edge: float = 0.5
    femininity: float = 0.5
    seasonality: np.ndarray = field(default_factory=lambda: np.array([0.25, 0.25, 0.25, 0.25]))
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array for similarity computation."""
        return np.array([
            self.formality,
            self.minimalism,
            self.boldness,
            self.classicism,
            self.comfort,
            self.edge,
            self.femininity,
            *self.seasonality,
        ])
    
    @classmethod
    def from_array(cls, arr: np.ndarray) -> 'StyleVector':
        """Create from numpy array."""
        return cls(
            formality=arr[0],
            minimalism=arr[1],
            boldness=arr[2],
            classicism=arr[3],
            comfort=arr[4],
            edge=arr[5],
            femininity=arr[6],
            seasonality=arr[7:11],
        )
    
    def similarity(self, other: 'StyleVector') -> float:
        """Compute cosine similarity between style vectors."""
        v1 = self.to_array()
        v2 = other.to_array()
        return float(1 - cosine(v1, v2))


@dataclass
class FashionItem:
    """Fashion item representation."""
    id: str
    item_type: ItemType
    style_vector: StyleVector
    colors: List[str]
    patterns: List[str]
    brand: Optional[str] = None
    price: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    image_embedding: Optional[np.ndarray] = None
    popularity_score: float = 0.0
    trend_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "item_type": self.item_type.value,
            "colors": self.colors,
            "patterns": self.patterns,
            "brand": self.brand,
            "price": self.price,
            "tags": self.tags,
            "popularity_score": self.popularity_score,
            "trend_score": self.trend_score,
        }


@dataclass
class UserPreferences:
    """User style preferences and history."""
    user_id: str
    style_vector: Optional[StyleVector] = None
    liked_items: List[str] = field(default_factory=list)
    purchased_items: List[str] = field(default_factory=list)
    viewed_items: List[str] = field(default_factory=list)
    outfit_history: List[List[str]] = field(default_factory=list)
    brand_affinity: Dict[str, float] = field(default_factory=dict)
    color_affinity: Dict[str, float] = field(default_factory=dict)
    price_range: Tuple[float, float] = (0, 1000)
    interaction_count: int = 0


@dataclass
class OutfitRecommendation:
    """Single outfit recommendation."""
    items: List[FashionItem]
    compatibility_score: float
    style_match_score: float
    personalization_score: float
    trend_score: float
    total_price: Optional[float] = None
    explanation: str = ""
    alternative_items: Dict[str, List[FashionItem]] = field(default_factory=dict)


@dataclass
class RecommendationRequest:
    """Request for outfit recommendations."""
    user_id: Optional[str] = None
    user_preferences: Optional[UserPreferences] = None
    seed_items: Optional[List[str]] = None
    occasion: Optional[str] = None
    budget: Optional[Tuple[float, float]] = None
    item_types: Optional[List[ItemType]] = None
    exclude_items: Optional[Set[str]] = None
    limit: int = 5
    recommendation_type: RecommendationType = RecommendationType.OUTFIT_COMPLETE


@dataclass
class RecommendationResult:
    """Result from recommendation engine."""
    recommendations: List[OutfitRecommendation]
    user_style_vector: Optional[StyleVector] = None
    processing_time_ms: float = 0.0
    model_version: str = "1.0.0"


# ─────────────────────────────────────────────────────────────────────────────
# Outfit Recommendation Engine
# ─────────────────────────────────────────────────────────────────────────────

class OutfitRecommendationEngine(AIServiceBase):
    """
    Intelligent outfit recommendation engine.
    
    Combines:
    - Collaborative filtering for user preferences
    - Style vector matching for compatibility
    - Trend analysis for current fashion
    - Rule-based outfit composition
    
    Usage:
        engine = OutfitRecommendationEngine()
        
        result = await engine.infer(RecommendationRequest(
            user_id="user123",
            seed_items=["item_001"],
            occasion="work",
            limit=5,
        ))
    """
    
    # Item type compatibility rules
    OUTFIT_STRUCTURES = {
        "casual": [
            [ItemType.TOP, ItemType.BOTTOM, ItemType.SHOES],
            [ItemType.TOP, ItemType.BOTTOM, ItemType.SHOES, ItemType.ACCESSORY],
            [ItemType.DRESS, ItemType.SHOES],
        ],
        "work": [
            [ItemType.TOP, ItemType.BOTTOM, ItemType.SHOES, ItemType.ACCESSORY],
            [ItemType.DRESS, ItemType.SHOES, ItemType.ACCESSORY],
            [ItemType.TOP, ItemType.BOTTOM, ItemType.OUTERWEAR, ItemType.SHOES],
        ],
        "formal": [
            [ItemType.DRESS, ItemType.SHOES, ItemType.JEWELRY, ItemType.BAG],
            [ItemType.TOP, ItemType.BOTTOM, ItemType.SHOES, ItemType.JEWELRY],
        ],
        "default": [
            [ItemType.TOP, ItemType.BOTTOM, ItemType.SHOES],
            [ItemType.DRESS, ItemType.SHOES],
        ],
    }
    
    # Color harmony rules
    COLOR_HARMONY = {
        "complementary": 0.8,  # Opposite colors
        "analogous": 0.9,  # Adjacent colors
        "monochromatic": 0.85,  # Same hue, different shades
        "triadic": 0.7,  # Three evenly spaced colors
        "neutral": 0.95,  # Neutral colors (black, white, gray, beige)
    }
    
    # Style compatibility matrix
    STYLE_COMPATIBILITY = {
        ("minimalist", "minimalist"): 1.0,
        ("minimalist", "classic"): 0.9,
        ("minimalist", "bohemian"): 0.4,
        ("classic", "classic"): 1.0,
        ("classic", "preppy"): 0.85,
        ("classic", "edgy"): 0.5,
        ("streetwear", "streetwear"): 1.0,
        ("streetwear", "sporty"): 0.8,
        ("streetwear", "classic"): 0.3,
        ("bohemian", "bohemian"): 1.0,
        ("bohemian", "romantic"): 0.85,
        ("bohemian", "minimalist"): 0.4,
    }
    
    def __init__(self, config: Optional[ModelConfig] = None):
        config = config or ModelConfig(
            name="outfit_recommendation",
            device=DeviceType.CPU,
            batch_size=16,
        )
        super().__init__(config)
        
        # User-item interaction matrix (for collaborative filtering)
        self._interaction_matrix: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Item cache
        self._item_cache: Dict[str, FashionItem] = {}
        
        # User preference cache
        self._user_cache: Dict[str, UserPreferences] = {}
        
        # Embedding model for style vectors
        self._embedding_model = None
    
    @property
    def model_name(self) -> str:
        return "outfit_recommendation_v1"
    
    async def load_model(self) -> None:
        """Load models for recommendations."""
        try:
            import torch
            from transformers import AutoTokenizer, AutoModel
            
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
            
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._embedding_model = AutoModel.from_pretrained(model_name)
            
            device = self._get_device()
            if device != "cpu":
                self._embedding_model = self._embedding_model.to(device)
            
            self._embedding_model.eval()
            self._model = self._embedding_model
            
            logger.info(f"Loaded recommendation model on {device}")
            
        except ImportError:
            logger.info("Transformers not available, using rule-based recommendations")
            self._model = "rule_based"
    
    async def _infer(self, input_data: RecommendationRequest) -> RecommendationResult:
        """
        Generate outfit recommendations.
        
        Args:
            input_data: RecommendationRequest with user context
            
        Returns:
            RecommendationResult with outfit suggestions
        """
        start_time = datetime.now(timezone.utc)
        
        # Step 1: Get or compute user style vector
        user_style = await self._get_user_style(input_data)
        
        # Step 2: Get candidate items
        candidates = await self._get_candidate_items(input_data, user_style)
        
        # Step 3: Generate outfit combinations
        outfits = await self._generate_outfits(
            candidates=candidates,
            user_style=user_style,
            request=input_data,
        )
        
        # Step 4: Score and rank outfits
        scored_outfits = await self._score_outfits(
            outfits=outfits,
            user_style=user_style,
            user_preferences=input_data.user_preferences,
            request=input_data,
        )
        
        # Step 5: Generate explanations
        recommendations = await self._generate_explanations(scored_outfits[:input_data.limit])
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        return RecommendationResult(
            recommendations=recommendations,
            user_style_vector=user_style,
            processing_time_ms=processing_time,
        )
    
    async def _get_user_style(
        self,
        request: RecommendationRequest
    ) -> StyleVector:
        """
        Compute user style vector from preferences and history.
        
        Uses collaborative filtering to infer style from interactions.
        """
        # If user preferences provided, use them
        if request.user_preferences and request.user_preferences.style_vector:
            return request.user_preferences.style_vector
        
        # If user_id provided, look up cached preferences
        if request.user_id and request.user_id in self._user_cache:
            user_pref = self._user_cache[request.user_id]
            if user_pref.style_vector:
                return user_pref.style_vector
        
        # Compute from interaction history
        if request.user_preferences:
            return self._compute_style_from_history(request.user_preferences)
        
        # Default style vector
        return StyleVector()
    
    def _compute_style_from_history(
        self,
        preferences: UserPreferences
    ) -> StyleVector:
        """
        Compute style vector from user interaction history.
        
        Analyzes liked/purchased items to infer style preferences.
        """
        # Get style vectors of liked items
        liked_vectors = []
        
        for item_id in preferences.liked_items + preferences.purchased_items:
            if item_id in self._item_cache:
                liked_vectors.append(self._item_cache[item_id].style_vector.to_array())
        
        if not liked_vectors:
            return StyleVector()
        
        # Average the style vectors
        avg_vector = np.mean(liked_vectors, axis=0)
        
        # Apply brand affinity adjustments
        for brand, affinity in preferences.brand_affinity.items():
            # Would adjust based on brand style profiles
            pass
        
        return StyleVector.from_array(avg_vector)
    
    async def _get_candidate_items(
        self,
        request: RecommendationRequest,
        user_style: StyleVector
    ) -> Dict[ItemType, List[FashionItem]]:
        """
        Get candidate items for outfit generation.
        
        Filters by:
        - Item type requirements
        - Budget constraints
        - Excluded items
        - Style compatibility
        """
        candidates: Dict[ItemType, List[FashionItem]] = defaultdict(list)
        
        # Get items from cache or would query database
        for item_id, item in self._item_cache.items():
            # Apply filters
            if request.exclude_items and item_id in request.exclude_items:
                continue
            
            if request.budget and item.price:
                if not (request.budget[0] <= item.price <= request.budget[1]):
                    continue
            
            if request.item_types and item.item_type not in request.item_types:
                continue
            
            # Compute style compatibility
            style_sim = user_style.similarity(item.style_vector)
            
            candidates[item.item_type].append((item, style_sim))
        
        # Sort by style similarity and take top candidates
        result: Dict[ItemType, List[FashionItem]] = {}
        for item_type, items_with_scores in candidates.items():
            sorted_items = sorted(items_with_scores, key=lambda x: x[1], reverse=True)
            result[item_type] = [item for item, _ in sorted_items[:50]]
        
        # If no items in cache, generate sample items
        if not result:
            result = self._generate_sample_items()
        
        return result
    
    def _generate_sample_items(self) -> Dict[ItemType, List[FashionItem]]:
        """Generate sample items for demonstration."""
        sample_items = {
            ItemType.TOP: [
                FashionItem(
                    id="top_001",
                    item_type=ItemType.TOP,
                    style_vector=StyleVector(formality=0.3, minimalism=0.7),
                    colors=["white"],
                    patterns=["solid"],
                    brand="Sample Brand",
                    price=45.0,
                ),
                FashionItem(
                    id="top_002",
                    item_type=ItemType.TOP,
                    style_vector=StyleVector(formality=0.7, minimalism=0.5),
                    colors=["navy"],
                    patterns=["solid"],
                    brand="Sample Brand",
                    price=65.0,
                ),
            ],
            ItemType.BOTTOM: [
                FashionItem(
                    id="bottom_001",
                    item_type=ItemType.BOTTOM,
                    style_vector=StyleVector(formality=0.2, minimalism=0.6),
                    colors=["blue"],
                    patterns=["solid"],
                    brand="Sample Brand",
                    price=75.0,
                ),
                FashionItem(
                    id="bottom_002",
                    item_type=ItemType.BOTTOM,
                    style_vector=StyleVector(formality=0.6, minimalism=0.8),
                    colors=["black"],
                    patterns=["solid"],
                    brand="Sample Brand",
                    price=90.0,
                ),
            ],
            ItemType.SHOES: [
                FashionItem(
                    id="shoes_001",
                    item_type=ItemType.SHOES,
                    style_vector=StyleVector(formality=0.2, comfort=0.8),
                    colors=["white"],
                    patterns=["solid"],
                    brand="Sample Brand",
                    price=85.0,
                ),
                FashionItem(
                    id="shoes_002",
                    item_type=ItemType.SHOES,
                    style_vector=StyleVector(formality=0.7, comfort=0.5),
                    colors=["black"],
                    patterns=["solid"],
                    brand="Sample Brand",
                    price=120.0,
                ),
            ],
            ItemType.DRESS: [
                FashionItem(
                    id="dress_001",
                    item_type=ItemType.DRESS,
                    style_vector=StyleVector(formality=0.5, femininity=0.8),
                    colors=["black"],
                    patterns=["solid"],
                    brand="Sample Brand",
                    price=150.0,
                ),
            ],
        }
        return sample_items
    
    async def _generate_outfits(
        self,
        candidates: Dict[ItemType, List[FashionItem]],
        user_style: StyleVector,
        request: RecommendationRequest
    ) -> List[List[FashionItem]]:
        """
        Generate outfit combinations from candidates.
        
        Uses outfit structure rules to create valid combinations.
        """
        outfits = []
        
        # Determine outfit structure based on occasion
        structure_key = "default"
        if request.occasion:
            if request.occasion in ["work", "interview", "meeting"]:
                structure_key = "work"
            elif request.occasion in ["formal", "wedding", "gala"]:
                structure_key = "formal"
            elif request.occasion in ["casual", "weekend", "brunch"]:
                structure_key = "casual"
        
        structures = self.OUTFIT_STRUCTURES.get(structure_key, self.OUTFIT_STRUCTURES["default"])
        
        # Generate outfits for each structure
        for structure in structures:
            outfit_combinations = self._combine_items(candidates, structure, user_style)
            # Limit number of outfits per structure to avoid combinatorial explosion
            outfits.extend(outfit_combinations[:10])
        
        return outfits
    
    def _combine_items(
        self,
        candidates: Dict[ItemType, List[FashionItem]],
        structure: List[ItemType],
        user_style: StyleVector,
        current_outfit: Optional[List[FashionItem]] = None,
        depth: int = 0
    ) -> List[List[FashionItem]]:
        """
        Recursively combine items following outfit structure.
        
        Uses backtracking to generate valid combinations.
        """
        if current_outfit is None:
            current_outfit = []
        
        if depth >= len(structure):
            return [current_outfit.copy()]
        
        item_type = structure[depth]
        items = candidates.get(item_type, [])
        
        if not items:
            return []
        
        outfits = []
        
        for item in items[:10]:  # Limit branching factor
            # Check compatibility with current outfit
            if current_outfit and not self._check_compatibility(item, current_outfit):
                continue
            
            current_outfit.append(item)
            sub_outfits = self._combine_items(
                candidates, structure, user_style, current_outfit, depth + 1
            )
            outfits.extend(sub_outfits)
            current_outfit.pop()
        
        return outfits
    
    def _check_compatibility(
        self,
        new_item: FashionItem,
        current_outfit: List[FashionItem]
    ) -> bool:
        """
        Check if new item is compatible with current outfit.
        
        Checks:
        - Color harmony
        - Style consistency
        - Formality level
        """
        if not current_outfit:
            return True
        
        # Check color harmony
        for existing_item in current_outfit:
            color_score = self._compute_color_harmony(new_item, existing_item)
            if color_score < 0.5:
                return False
        
        # Check style consistency
        style_scores = [
            new_item.style_vector.similarity(item.style_vector)
            for item in current_outfit
        ]
        if style_scores and min(style_scores) < 0.3:
            return False
        
        return True
    
    def _compute_color_harmony(
        self,
        item1: FashionItem,
        item2: FashionItem
    ) -> float:
        """
        Compute color harmony score between two items.
        
        Uses color theory rules.
        """
        # Neutral colors always work
        neutrals = {"black", "white", "gray", "grey", "beige", "navy", "brown"}
        
        colors1 = set(c.lower() for c in item1.colors)
        colors2 = set(c.lower() for c in item2.colors)
        
        # If both are neutral, high compatibility
        if colors1 & neutrals and colors2 & neutrals:
            return self.COLOR_HARMONY["neutral"]
        
        # If one is neutral, good compatibility
        if colors1 & neutrals or colors2 & neutrals:
            return 0.85
        
        # Same color family (monochromatic)
        if colors1 & colors2:
            return self.COLOR_HARMONY["monochromatic"]
        
        # Default: moderate compatibility
        return 0.65
    
    async def _score_outfits(
        self,
        outfits: List[List[FashionItem]],
        user_style: StyleVector,
        user_preferences: Optional[UserPreferences],
        request: RecommendationRequest
    ) -> List[Tuple[List[FashionItem], Dict[str, float]]]:
        """
        Score outfits on multiple dimensions.
        
        Scores:
        - Compatibility: How well items work together
        - Style match: How well it matches user style
        - Personalization: Based on user history
        - Trend: Current fashion trends
        """
        scored_outfits = []
        
        for outfit in outfits:
            scores = {}
            
            # Compatibility score
            scores["compatibility"] = self._compute_outfit_compatibility(outfit)
            
            # Style match score
            scores["style_match"] = self._compute_style_match(outfit, user_style)
            
            # Personalization score
            scores["personalization"] = self._compute_personalization(
                outfit, user_preferences
            )
            
            # Trend score
            scores["trend"] = self._compute_trend_score(outfit)
            
            # Overall score (weighted combination)
            scores["overall"] = (
                scores["compatibility"] * 0.3 +
                scores["style_match"] * 0.3 +
                scores["personalization"] * 0.25 +
                scores["trend"] * 0.15
            )
            
            scored_outfits.append((outfit, scores))
        
        # Sort by overall score
        scored_outfits.sort(key=lambda x: x[1]["overall"], reverse=True)
        
        return scored_outfits
    
    def _compute_outfit_compatibility(
        self,
        outfit: List[FashionItem]
    ) -> float:
        """Compute how well items in outfit work together."""
        if len(outfit) < 2:
            return 1.0
        
        scores = []
        for i, item1 in enumerate(outfit):
            for item2 in outfit[i + 1:]:
                # Color harmony
                color_score = self._compute_color_harmony(item1, item2)
                
                # Style similarity
                style_score = item1.style_vector.similarity(item2.style_vector)
                
                # Combined score
                combined = color_score * 0.4 + style_score * 0.6
                scores.append(combined)
        
        return np.mean(scores) if scores else 1.0
    
    def _compute_style_match(
        self,
        outfit: List[FashionItem],
        user_style: StyleVector
    ) -> float:
        """Compute how well outfit matches user style."""
        if not outfit:
            return 0.0
        
        # Compute average outfit style vector
        outfit_vectors = [item.style_vector.to_array() for item in outfit]
        avg_outfit_vector = np.mean(outfit_vectors, axis=0)
        outfit_style = StyleVector.from_array(avg_outfit_vector)
        
        return user_style.similarity(outfit_style)
    
    def _compute_personalization(
        self,
        outfit: List[FashionItem],
        preferences: Optional[UserPreferences]
    ) -> float:
        """Compute personalization score based on user history."""
        if not preferences:
            return 0.5
        
        score = 0.0
        weights_sum = 0.0
        
        for item in outfit:
            # Check if user has interacted with similar items
            if item.id in preferences.liked_items:
                score += 1.0
                weights_sum += 1.0
            elif item.id in preferences.purchased_items:
                score += 0.9
                weights_sum += 1.0
            elif item.id in preferences.viewed_items:
                score += 0.6
                weights_sum += 1.0
            
            # Brand affinity
            if item.brand and item.brand in preferences.brand_affinity:
                score += preferences.brand_affinity[item.brand]
                weights_sum += 1.0
            
            # Color affinity
            for color in item.colors:
                if color.lower() in preferences.color_affinity:
                    score += preferences.color_affinity[color.lower()]
                    weights_sum += 0.5
        
        return score / weights_sum if weights_sum > 0 else 0.5
    
    def _compute_trend_score(
        self,
        outfit: List[FashionItem]
    ) -> float:
        """Compute trend score based on current fashion trends."""
        if not outfit:
            return 0.5
        
        trend_scores = [item.trend_score for item in outfit]
        return np.mean(trend_scores) if trend_scores else 0.5
    
    async def _generate_explanations(
        self,
        scored_outfits: List[Tuple[List[FashionItem], Dict[str, float]]]
    ) -> List[OutfitRecommendation]:
        """Generate explanations for recommendations."""
        recommendations = []
        
        for outfit, scores in scored_outfits:
            # Compute total price
            total_price = sum(
                item.price for item in outfit if item.price is not None
            )
            
            # Generate explanation
            explanation = self._create_explanation(outfit, scores)
            
            # Find alternative items for each position
            alternatives = self._find_alternatives(outfit)
            
            recommendation = OutfitRecommendation(
                items=outfit,
                compatibility_score=scores["compatibility"],
                style_match_score=scores["style_match"],
                personalization_score=scores["personalization"],
                trend_score=scores["trend"],
                total_price=total_price if total_price > 0 else None,
                explanation=explanation,
                alternative_items=alternatives,
            )
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def _create_explanation(
        self,
        outfit: List[FashionItem],
        scores: Dict[str, float]
    ) -> str:
        """Create human-readable explanation."""
        parts = []
        
        # Overall assessment
        if scores["overall"] > 0.8:
            parts.append("Excellent match for your style")
        elif scores["overall"] > 0.6:
            parts.append("Good match for your style")
        else:
            parts.append("A unique style combination")
        
        # Style elements
        if scores["compatibility"] > 0.8:
            parts.append("the colors and styles work beautifully together")
        
        if scores["trend"] > 0.7:
            parts.append("features trending pieces")
        
        # Item highlights
        if outfit:
            key_item = max(outfit, key=lambda x: x.trend_score)
            if key_item.trend_score > 0.6:
                parts.append(f"the {key_item.item_type.value} is particularly stylish")
        
        return "This outfit " + ", and ".join(parts) + "."
    
    def _find_alternatives(
        self,
        outfit: List[FashionItem]
    ) -> Dict[str, List[FashionItem]]:
        """Find alternative items for each position in outfit."""
        alternatives = {}
        
        for item in outfit:
            # Would find similar items from catalog
            alternatives[item.id] = []
        
        return alternatives
    
    # ==========================================
    # Collaborative Filtering
    # ==========================================
    
    def update_interactions(
        self,
        user_id: str,
        item_id: str,
        interaction_type: str = "view",
        weight: float = 1.0
    ) -> None:
        """
        Update user-item interaction matrix.
        
        Interaction types:
        - view: weight = 1.0
        - like: weight = 2.0
        - purchase: weight = 3.0
        """
        type_weights = {
            "view": 1.0,
            "like": 2.0,
            "purchase": 3.0,
            "save": 1.5,
        }
        
        weight = type_weights.get(interaction_type, weight)
        self._interaction_matrix[user_id][item_id] = weight
    
    def get_similar_users(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Find similar users using collaborative filtering.
        
        Uses Pearson correlation on interaction vectors.
        """
        if user_id not in self._interaction_matrix:
            return []
        
        user_vector = self._interaction_matrix[user_id]
        similarities = []
        
        for other_id, other_vector in self._interaction_matrix.items():
            if other_id == user_id:
                continue
            
            # Find common items
            common_items = set(user_vector.keys()) & set(other_vector.keys())
            
            if len(common_items) < 2:
                continue
            
            # Compute correlation
            user_scores = [user_vector[item] for item in common_items]
            other_scores = [other_vector[item] for item in common_items]
            
            correlation, _ = pearsonr(user_scores, other_scores)
            
            if not np.isnan(correlation):
                similarities.append((other_id, correlation))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:limit]
    
    def get_collaborative_recommendations(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Get item recommendations from collaborative filtering.
        
        Uses user-based collaborative filtering.
        """
        similar_users = self.get_similar_users(user_id)
        
        if not similar_users:
            return []
        
        user_items = set(self._interaction_matrix[user_id].keys())
        recommendations = defaultdict(float)
        
        for similar_user, similarity in similar_users:
            for item_id, weight in self._interaction_matrix[similar_user].items():
                if item_id not in user_items:
                    recommendations[item_id] += similarity * weight
        
        # Sort by score
        sorted_recs = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_recs[:limit]


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Functions
# ─────────────────────────────────────────────────────────────────────────────

async def get_outfit_recommendations(
    user_id: str,
    occasion: Optional[str] = None,
    budget: Optional[Tuple[float, float]] = None,
    limit: int = 5
) -> List[OutfitRecommendation]:
    """
    Convenience function to get outfit recommendations.
    
    Args:
        user_id: User ID for personalization
        occasion: Optional occasion type
        budget: Optional budget range (min, max)
        limit: Number of recommendations
        
    Returns:
        List of OutfitRecommendation objects
    """
    engine = OutfitRecommendationEngine()
    request = RecommendationRequest(
        user_id=user_id,
        occasion=occasion,
        budget=budget,
        limit=limit,
    )
    result = await engine.infer(request)
    return result.recommendations
