"""
CONFIT AI Services - Virtual Stylist
====================================
NLP-powered personal styling assistant.

Features:
- Natural language understanding
- Occasion detection from text
- Budget extraction
- Style preference analysis
- Outfit generation with constraints
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set
import json

import numpy as np

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

class OccasionType(Enum):
    """Types of fashion occasions."""
    CASUAL = "casual"
    WORK = "work"
    FORMAL = "formal"
    DATE = "date"
    PARTY = "party"
    WEDDING = "wedding"
    INTERVIEW = "interview"
    TRAVEL = "travel"
    WORKOUT = "workout"
    WEEKEND = "weekend"
    BUSINESS_CASUAL = "business_casual"
    COCKTAIL = "cocktail"
    BEACH = "beach"
    OUTDOOR = "outdoor"
    NIGHT_OUT = "night_out"
    BRUNCH = "brunch"
    GRADUATION = "graduation"
    HOLIDAY = "holiday"
    OTHER = "other"


class StylePreference(Enum):
    """Style preferences."""
    MINIMALIST = "minimalist"
    CLASSIC = "classic"
    BOHEMIAN = "bohemian"
    STREETWEAR = "streetwear"
    PREPPY = "preppy"
    EDGY = "edgy"
    ROMANTIC = "romantic"
    SPORTY = "sporty"
    VINTAGE = "vintage"
    LUXURY = "luxury"
    SUSTAINABLE = "sustainable"
    ANDROGYNOUS = "androgynous"


class Season(Enum):
    """Seasons for styling."""
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"
    ALL_SEASON = "all_season"


@dataclass
class StyleProfile:
    """User's style profile."""
    preferences: List[StylePreference] = field(default_factory=list)
    colors_liked: List[str] = field(default_factory=list)
    colors_disliked: List[str] = field(default_factory=list)
    fit_preferences: List[str] = field(default_factory=list)
    brands_liked: List[str] = field(default_factory=list)
    price_range: Tuple[float, float] = (0.0, 1000.0)
    sustainability_priority: float = 0.0
    comfort_priority: float = 0.5
    trendiness_priority: float = 0.5


@dataclass
class OccasionContext:
    """Detected occasion context from input."""
    occasion_type: OccasionType
    confidence: float
    formality_level: int  # 1-5 scale
    time_of_day: Optional[str] = None
    season: Optional[Season] = None
    weather: Optional[str] = None
    location: Optional[str] = None
    keywords: List[str] = field(default_factory=list)


@dataclass
class BudgetConstraints:
    """Extracted budget constraints."""
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    currency: str = "USD"
    per_item: bool = True
    total_outfit: bool = False
    flexibility: float = 0.2  # 20% flexibility by default


@dataclass
class StylistRequest:
    """Input request for virtual stylist."""
    text: str
    user_id: Optional[str] = None
    style_profile: Optional[StyleProfile] = None
    wardrobe_items: Optional[List[Dict[str, Any]]] = None
    constraints: Optional[Dict[str, Any]] = None


@dataclass
class OutfitSuggestion:
    """Generated outfit suggestion."""
    items: List[Dict[str, Any]]
    total_price: float
    style_match_score: float
    occasion_match_score: float
    budget_fit_score: float
    explanation: str
    alternatives: List[List[Dict[str, Any]]] = field(default_factory=list)
    styling_tips: List[str] = field(default_factory=list)


@dataclass
class StylistResult:
    """Complete stylist response."""
    occasion: OccasionContext
    budget: BudgetConstraints
    style_analysis: Dict[str, Any]
    outfit_suggestions: List[OutfitSuggestion]
    confidence: float
    reasoning: str


# ─────────────────────────────────────────────────────────────────────────────
# Virtual Stylist Service
# ─────────────────────────────────────────────────────────────────────────────

class VirtualStylistService(AIServiceBase):
    """
    NLP-powered virtual stylist service.
    
    Capabilities:
    - Parse natural language styling requests
    - Detect occasion from context
    - Extract budget constraints
    - Generate outfit recommendations
    
    Usage:
        stylist = VirtualStylistService()
        
        result = await stylist.infer(StylistRequest(
            text="I need an outfit for a wedding this weekend, budget around $300",
            user_id="user123",
        ))
    """
    
    # Occasion keywords mapping
    OCCASION_KEYWORDS = {
        OccasionType.CASUAL: [
            "casual", "everyday", "relaxed", "laid-back", "chill", "hanging out",
            "coffee", "errands", "shopping", "mall"
        ],
        OccasionType.WORK: [
            "work", "office", "meeting", "professional", "business", "corporate",
            "presentation", "conference", "job", "workplace"
        ],
        OccasionType.FORMAL: [
            "formal", "black tie", "gala", "charity", "awards", "ceremony",
            "formal event", "upscale", "elegant"
        ],
        OccasionType.DATE: [
            "date", "romantic", "first date", "dinner date", "anniversary",
            "valentine", "romantic dinner"
        ],
        OccasionType.PARTY: [
            "party", "club", "clubbing", "dance", "celebration", "birthday party",
            "house party", "celebration"
        ],
        OccasionType.WEDDING: [
            "wedding", "bride", "groom", "wedding guest", "rehearsal dinner",
            "wedding ceremony", "reception"
        ],
        OccasionType.INTERVIEW: [
            "interview", "job interview", "interviewing", "hiring", "recruiter"
        ],
        OccasionType.TRAVEL: [
            "travel", "vacation", "trip", "flight", "airport", "road trip",
            "traveling", "destination"
        ],
        OccasionType.WORKOUT: [
            "workout", "gym", "exercise", "yoga", "running", "hiking",
            "sports", "training", "fitness"
        ],
        OccasionType.WEEKEND: [
            "weekend", "saturday", "sunday", "brunch", "farmers market",
            "weekend getaway"
        ],
        OccasionType.BUSINESS_CASUAL: [
            "business casual", "smart casual", "casual friday", "team lunch",
            "networking event"
        ],
        OccasionType.COCKTAIL: [
            "cocktail", "cocktail party", "happy hour", "drinks", "bar",
            "lounge", "mixology"
        ],
        OccasionType.BEACH: [
            "beach", "pool", "swimming", "resort", "vacation beach", "seaside",
            "ocean", "surfing"
        ],
        OccasionType.OUTDOOR: [
            "outdoor", "picnic", "park", "camping", "festival", "outdoor concert",
            "nature", "hiking"
        ],
        OccasionType.NIGHT_OUT: [
            "night out", "evening", "dinner", "fine dining", "nightlife",
            "late night", "evening event"
        ],
        OccasionType.BRUNCH: [
            "brunch", "breakfast", "morning", "cafe", "brunch date"
        ],
        OccasionType.GRADUATION: [
            "graduation", "grad", "commencement", "graduation ceremony",
            "graduation party"
        ],
        OccasionType.HOLIDAY: [
            "holiday", "christmas", "thanksgiving", "easter", "new year",
            "halloween", "holiday party", "festive"
        ],
    }
    
    # Style keywords mapping
    STYLE_KEYWORDS = {
        StylePreference.MINIMALIST: [
            "minimalist", "simple", "clean", "basic", "minimal", "understated"
        ],
        StylePreference.CLASSIC: [
            "classic", "timeless", "elegant", "sophisticated", "traditional"
        ],
        StylePreference.BOHEMIAN: [
            "bohemian", "boho", "hippie", "free-spirited", "flowy", "boho-chic"
        ],
        StylePreference.STREETWEAR: [
            "streetwear", "urban", "street", "hypebeast", "sneaker", "cool"
        ],
        StylePreference.PREPPY: [
            "preppy", "polished", "ivy league", "country club", "nautical"
        ],
        StylePreference.EDGY: [
            "edgy", "bold", "avant-garde", "alternative", "punk", "rock"
        ],
        StylePreference.ROMANTIC: [
            "romantic", "feminine", "soft", "dreamy", "floral", "delicate"
        ],
        StylePreference.SPORTY: [
            "sporty", "athletic", "sport", "activewear", "athleisure"
        ],
        StylePreference.VINTAGE: [
            "vintage", "retro", "throwback", "antique", "old-school", "classic"
        ],
        StylePreference.LUXURY: [
            "luxury", "designer", "high-end", "premium", "expensive", "luxe"
        ],
        StylePreference.SUSTAINABLE: [
            "sustainable", "eco-friendly", "ethical", "organic", "conscious"
        ],
    }
    
    # Time of day keywords
    TIME_KEYWORDS = {
        "morning": ["morning", "breakfast", "early", "sunrise", "a.m."],
        "afternoon": ["afternoon", "lunch", "midday", "noon", "p.m."],
        "evening": ["evening", "dinner", "night", "late", "p.m."],
        "night": ["night", "midnight", "late night", "club", "party"],
    }
    
    # Weather keywords
    WEATHER_KEYWORDS = {
        "hot": ["hot", "warm", "summer", "sunny", "heat", "humid"],
        "cold": ["cold", "winter", "freezing", "snow", "frost"],
        "mild": ["mild", "pleasant", "comfortable", "spring", "fall"],
        "rainy": ["rain", "rainy", "wet", "storm", "drizzle"],
        "windy": ["windy", "breezy", "gust", "wind"],
    }
    
    def __init__(self, config: Optional[ModelConfig] = None):
        config = config or ModelConfig(
            name="virtual_stylist",
            device=DeviceType.CPU,
            batch_size=8,
        )
        super().__init__(config)
        self._nlp_pipeline = None
        self._embedding_model = None
    
    @property
    def model_name(self) -> str:
        return "virtual_stylist_v1"
    
    async def load_model(self) -> None:
        """Load NLP models for text understanding."""
        try:
            # Try to load transformer models
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
            
            logger.info(f"Loaded embedding model on {device}")
            
        except ImportError:
            logger.info("Transformers not available, using rule-based NLP")
            self._model = "rule_based"
    
    async def _infer(self, input_data: StylistRequest) -> StylistResult:
        """
        Process stylist request and generate recommendations.
        
        Args:
            input_data: StylistRequest with text and context
            
        Returns:
            StylistResult with occasion, budget, and suggestions
        """
        # Step 1: Detect occasion
        occasion = await self._detect_occasion(input_data.text)
        
        # Step 2: Extract budget
        budget = await self._extract_budget(input_data.text)
        
        # Step 3: Analyze style preferences
        style_analysis = await self._analyze_style(
            input_data.text,
            input_data.style_profile
        )
        
        # Step 4: Generate outfit suggestions
        suggestions = await self._generate_outfits(
            occasion=occasion,
            budget=budget,
            style_analysis=style_analysis,
            wardrobe=input_data.wardrobe_items,
            user_id=input_data.user_id,
        )
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(occasion, budget, style_analysis)
        
        # Generate reasoning explanation
        reasoning = self._generate_reasoning(occasion, budget, style_analysis)
        
        return StylistResult(
            occasion=occasion,
            budget=budget,
            style_analysis=style_analysis,
            outfit_suggestions=suggestions,
            confidence=confidence,
            reasoning=reasoning,
        )
    
    async def _detect_occasion(self, text: str) -> OccasionContext:
        """
        Detect occasion type from text input.
        
        Uses keyword matching and semantic similarity.
        """
        text_lower = text.lower()
        detected_keywords = []
        
        # Score each occasion type
        scores: Dict[OccasionType, float] = {}
        
        for occasion_type, keywords in self.OCCASION_KEYWORDS.items():
            score = 0.0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1.0
                    detected_keywords.append(keyword)
            
            # Normalize by number of keywords
            if score > 0:
                scores[occasion_type] = score / len(keywords)
        
        # Get best match
        if scores:
            best_occasion = max(scores, key=scores.get)
            confidence = scores[best_occasion]
        else:
            best_occasion = OccasionType.OTHER
            confidence = 0.3
        
        # Determine formality level (1-5)
        formality = self._infer_formality(best_occasion, text_lower)
        
        # Detect time of day
        time_of_day = self._detect_time_of_day(text_lower)
        
        # Detect weather context
        weather = self._detect_weather(text_lower)
        
        return OccasionContext(
            occasion_type=best_occasion,
            confidence=min(confidence * 2, 1.0),  # Scale up confidence
            formality_level=formality,
            time_of_day=time_of_day,
            weather=weather,
            keywords=detected_keywords,
        )
    
    def _infer_formality(self, occasion: OccasionType, text: str) -> int:
        """Infer formality level (1-5) from occasion and text."""
        # Base formality by occasion
        formality_map = {
            OccasionType.FORMAL: 5,
            OccasionType.WEDDING: 4,
            OccasionType.INTERVIEW: 4,
            OccasionType.COCKTAIL: 4,
            OccasionType.WORK: 3,
            OccasionType.BUSINESS_CASUAL: 3,
            OccasionType.DATE: 3,
            OccasionType.BRUNCH: 2,
            OccasionType.NIGHT_OUT: 3,
            OccasionType.PARTY: 2,
            OccasionType.WEEKEND: 1,
            OccasionType.CASUAL: 1,
            OccasionType.BEACH: 1,
            OccasionType.WORKOUT: 1,
            OccasionType.TRAVEL: 2,
            OccasionType.OUTDOOR: 1,
            OccasionType.GRADUATION: 4,
            OccasionType.HOLIDAY: 3,
            OccasionType.OTHER: 2,
        }
        
        base_formality = formality_map.get(occasion, 2)
        
        # Adjust based on text modifiers
        if "very formal" in text or "black tie" in text:
            base_formality = 5
        elif "semi-formal" in text:
            base_formality = min(base_formality + 1, 4)
        elif "casual" in text:
            base_formality = max(base_formality - 1, 1)
        
        return base_formality
    
    def _detect_time_of_day(self, text: str) -> Optional[str]:
        """Detect time of day from text."""
        for time_period, keywords in self.TIME_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return time_period
        return None
    
    def _detect_weather(self, text: str) -> Optional[str]:
        """Detect weather context from text."""
        for weather_type, keywords in self.WEATHER_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return weather_type
        return None
    
    async def _extract_budget(self, text: str) -> BudgetConstraints:
        """
        Extract budget constraints from text.
        
        Handles various formats:
        - "$300"
        - "around $200"
        - "under $100"
        - "$50-100"
        - "budget is 200 dollars"
        """
        text_lower = text.lower()
        
        # Currency detection
        currency = "USD"
        if "£" in text or "pound" in text_lower:
            currency = "GBP"
        elif "€" in text or "euro" in text_lower:
            currency = "EUR"
        
        # Pattern matching for budget
        patterns = [
            # Range: $50-100 or $50 to $100
            r'\$?(\d+(?:\.\d{2})?)\s*(?:-|to)\s*\$?(\d+(?:\.\d{2})?)',
            # Under/less than: under $100
            r'(?:under|less than|below|up to|max|maximum)\s*\$?(\d+(?:\.\d{2})?)',
            # Over/more than: over $50
            r'(?:over|more than|above|min|minimum|at least)\s*\$?(\d+(?:\.\d{2})?)',
            # Around/about: around $200
            r'(?:around|about|approximately|roughly|~)\s*\$?(\d+(?:\.\d{2})?)',
            # Simple: $300
            r'\$(\d+(?:\.\d{2})?)',
            # Text: 200 dollars
            r'(\d+(?:\.\d{2})?)\s*(?:dollars?|bucks?|usd)',
        ]
        
        min_budget = None
        max_budget = None
        
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                if isinstance(matches[0], tuple):
                    # Range pattern
                    min_budget = float(matches[0][0])
                    max_budget = float(matches[0][1])
                else:
                    value = float(matches[0])
                    
                    # Determine if min or max based on context
                    if any(word in text_lower for word in ["under", "less", "below", "max", "up to"]):
                        max_budget = value
                    elif any(word in text_lower for word in ["over", "more", "above", "min", "at least"]):
                        min_budget = value
                    elif any(word in text_lower for word in ["around", "about", "approximately", "roughly"]):
                        # Around X means X ± 20%
                        min_budget = value * 0.8
                        max_budget = value * 1.2
                    else:
                        # Default: treat as max budget
                        max_budget = value
                
                break
        
        # Check for per-item vs total
        per_item = any(phrase in text_lower for phrase in ["per item", "each", "per piece"])
        total_outfit = any(phrase in text_lower for phrase in ["total", "whole outfit", "entire look"])
        
        return BudgetConstraints(
            min_budget=min_budget,
            max_budget=max_budget,
            currency=currency,
            per_item=per_item or not total_outfit,
            total_outfit=total_outfit,
        )
    
    async def _analyze_style(
        self,
        text: str,
        profile: Optional[StyleProfile] = None
    ) -> Dict[str, Any]:
        """
        Analyze style preferences from text and profile.
        
        Returns detected style attributes and preferences.
        """
        text_lower = text.lower()
        
        # Detect style preferences from text
        detected_styles: List[StylePreference] = []
        style_scores: Dict[StylePreference, float] = {}
        
        for style_pref, keywords in self.STYLE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    detected_styles.append(style_pref)
                    style_scores[style_pref] = style_scores.get(style_pref, 0) + 1
                    break
        
        # Color detection
        color_keywords = [
            "black", "white", "red", "blue", "green", "yellow", "pink",
            "purple", "orange", "brown", "gray", "grey", "navy", "beige",
            "cream", "maroon", "teal", "coral", "gold", "silver"
        ]
        
        detected_colors = [
            color for color in color_keywords
            if color in text_lower
        ]
        
        # Fit preferences
        fit_keywords = {
            "slim": "slim_fit",
            "fitted": "fitted",
            "loose": "loose_fit",
            "oversized": "oversized",
            "regular": "regular_fit",
            "tight": "tight_fit",
            "relaxed": "relaxed_fit",
        }
        
        detected_fits = [
            fit_keywords[keyword]
            for keyword in fit_keywords
            if keyword in text_lower
        ]
        
        # Merge with user profile if available
        if profile:
            detected_styles.extend(profile.preferences)
            detected_colors.extend(profile.colors_liked)
            detected_fits.extend(profile.fit_preferences)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_styles = []
        for style in detected_styles:
            if style not in seen:
                seen.add(style)
                unique_styles.append(style)
        
        return {
            "styles": unique_styles,
            "style_scores": style_scores,
            "colors": list(set(detected_colors)),
            "fits": list(set(detected_fits)),
            "comfort_priority": profile.comfort_priority if profile else 0.5,
            "trendiness_priority": profile.trendiness_priority if profile else 0.5,
        }
    
    async def _generate_outfits(
        self,
        occasion: OccasionContext,
        budget: BudgetConstraints,
        style_analysis: Dict[str, Any],
        wardrobe: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
    ) -> List[OutfitSuggestion]:
        """
        Generate outfit suggestions based on constraints.
        
        This is a placeholder that would integrate with:
        - Product catalog
        - User wardrobe
        - Outfit recommendation engine
        """
        suggestions = []
        
        # Define outfit templates by occasion
        outfit_templates = self._get_outfit_templates(occasion, style_analysis)
        
        for template in outfit_templates[:3]:  # Top 3 suggestions
            items = template["items"]
            
            # Calculate total price (placeholder)
            total_price = sum(item.get("estimated_price", 50) for item in items)
            
            # Check budget fit
            budget_fit = self._calculate_budget_fit(total_price, budget)
            
            # Calculate scores
            style_match = self._calculate_style_match(items, style_analysis)
            occasion_match = occasion.confidence
            
            suggestion = OutfitSuggestion(
                items=items,
                total_price=total_price,
                style_match_score=style_match,
                occasion_match_score=occasion_match,
                budget_fit_score=budget_fit,
                explanation=template["explanation"],
                styling_tips=template.get("tips", []),
            )
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _get_outfit_templates(
        self,
        occasion: OccasionContext,
        style_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get outfit templates for occasion."""
        
        templates = {
            OccasionType.CASUAL: [
                {
                    "items": [
                        {"type": "t-shirt", "estimated_price": 30},
                        {"type": "jeans", "estimated_price": 60},
                        {"type": "sneakers", "estimated_price": 80},
                    ],
                    "explanation": "A relaxed casual look perfect for everyday activities.",
                    "tips": ["Roll up sleeves for a laid-back vibe", "Add a watch for subtle style"]
                },
            ],
            OccasionType.WORK: [
                {
                    "items": [
                        {"type": "blouse", "estimated_price": 60},
                        {"type": "dress_pants", "estimated_price": 70},
                        {"type": "loafers", "estimated_price": 90},
                    ],
                    "explanation": "Professional and polished for the office.",
                    "tips": ["Keep accessories minimal", "Choose neutral colors"]
                },
            ],
            OccasionType.WEDDING: [
                {
                    "items": [
                        {"type": "dress", "estimated_price": 150},
                        {"type": "heels", "estimated_price": 80},
                        {"type": "clutch", "estimated_price": 40},
                    ],
                    "explanation": "Elegant and wedding-appropriate attire.",
                    "tips": ["Avoid white unless you're the bride", "Consider the venue"]
                },
            ],
            OccasionType.DATE: [
                {
                    "items": [
                        {"type": "nice_top", "estimated_price": 50},
                        {"type": "dark_jeans", "estimated_price": 70},
                        {"type": "ankle_boots", "estimated_price": 90},
                    ],
                    "explanation": "Flattering and comfortable for a romantic evening.",
                    "tips": ["Add a subtle fragrance", "Choose one statement piece"]
                },
            ],
            OccasionType.INTERVIEW: [
                {
                    "items": [
                        {"type": "blazer", "estimated_price": 100},
                        {"type": "dress_shirt", "estimated_price": 50},
                        {"type": "dress_pants", "estimated_price": 70},
                        {"type": "oxford_shoes", "estimated_price": 90},
                    ],
                    "explanation": "Professional and confident interview attire.",
                    "tips": ["Stick to neutral colors", "Ensure clothes are well-pressed"]
                },
            ],
        }
        
        # Default template for other occasions
        default_template = {
            "items": [
                {"type": "versatile_top", "estimated_price": 45},
                {"type": "versatile_bottom", "estimated_price": 65},
                {"type": "versatile_shoes", "estimated_price": 75},
            ],
            "explanation": f"A versatile outfit suitable for {occasion.occasion_type.value}.",
            "tips": ["Dress it up or down with accessories"]
        }
        
        return templates.get(occasion.occasion_type, [default_template])
    
    def _calculate_budget_fit(
        self,
        price: float,
        budget: BudgetConstraints
    ) -> float:
        """Calculate how well price fits budget."""
        if budget.max_budget is None:
            return 1.0
        
        if price <= budget.max_budget:
            # Within budget - score based on how much room left
            room = (budget.max_budget - price) / budget.max_budget
            return 1.0 - (room * 0.3)  # Slight penalty for too much room
        else:
            # Over budget - score based on how much over
            over = (price - budget.max_budget) / budget.max_budget
            return max(0, 1.0 - over)
    
    def _calculate_style_match(
        self,
        items: List[Dict[str, Any]],
        style_analysis: Dict[str, Any]
    ) -> float:
        """Calculate style match score."""
        # Placeholder - would use style vectors in production
        return 0.85
    
    def _calculate_confidence(
        self,
        occasion: OccasionContext,
        budget: BudgetConstraints,
        style_analysis: Dict[str, Any]
    ) -> float:
        """Calculate overall confidence in recommendations."""
        scores = [
            occasion.confidence,
            0.8 if budget.max_budget else 0.5,
            min(1.0, len(style_analysis.get("styles", [])) * 0.3 + 0.5),
        ]
        return sum(scores) / len(scores)
    
    def _generate_reasoning(
        self,
        occasion: OccasionContext,
        budget: BudgetConstraints,
        style_analysis: Dict[str, Any]
    ) -> str:
        """Generate human-readable reasoning."""
        parts = []
        
        # Occasion reasoning
        parts.append(
            f"Detected occasion: {occasion.occasion_type.value.replace('_', ' ').title()} "
            f"(formality level: {occasion.formality_level}/5)"
        )
        
        # Budget reasoning
        if budget.max_budget:
            budget_str = f"Budget constraint: up to ${budget.max_budget:.0f}"
            if budget.min_budget:
                budget_str = f"Budget range: ${budget.min_budget:.0f} - ${budget.max_budget:.0f}"
            parts.append(budget_str)
        else:
            parts.append("No specific budget detected")
        
        # Style reasoning
        styles = style_analysis.get("styles", [])
        if styles:
            style_names = [s.value.replace('_', ' ').title() for s in styles[:3]]
            parts.append(f"Style preferences: {', '.join(style_names)}")
        
        return ". ".join(parts) + "."


# ─────────────────────────────────────────────────────────────────────────────
# Convenience Functions
# ─────────────────────────────────────────────────────────────────────────────

async def get_styling_advice(
    text: str,
    user_id: Optional[str] = None,
    style_profile: Optional[StyleProfile] = None,
) -> StylistResult:
    """
    Convenience function to get styling advice.
    
    Args:
        text: Natural language styling request
        user_id: Optional user ID for personalization
        style_profile: Optional user style profile
        
    Returns:
        StylistResult with recommendations
    """
    service = VirtualStylistService()
    request = StylistRequest(
        text=text,
        user_id=user_id,
        style_profile=style_profile,
    )
    result = await service.infer(request)
    return result.data
