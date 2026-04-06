"""
CONFIT Backend — AI Central Brain Service
=========================================
Centralized personalization engine that aggregates signals,
generates recommendations, and coordinates all AI-powered features.

This is the core intelligence layer that:
- Receives signals from all user interactions
- Aggregates preferences and behavior patterns
- Generates personalized recommendations
- Provides adaptive styling logic
- Tracks accepted/rejected recommendations for learning
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from collections import defaultdict
import json

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from database.session import get_db

from models.profile_models import (
    UserStyleProfile,
    UserBodyProfile,
    UserBudgetProfile,
    UserBrandAffinity,
    UserContextualPreference,
    UserBehaviorSignal,
    UserStyleEvolution,
)
from services.behavior_signal_service import BehaviorSignalService
from services.confidence_service import ConfidenceService

logger = logging.getLogger(__name__)


# ── Fashion Rules Engine ─────────────────────────────────────────────

COLOR_HARMONY_RULES = {
    "complementary": {
        "pairs": [
            ("blue", "orange"), ("red", "green"), ("yellow", "purple"),
            ("teal", "coral"), ("pink", "olive")
        ],
        "description": "High contrast, bold and vibrant",
        "confidence_modifier": 0.9,
    },
    "analogous": {
        "pairs": [
            ("blue", "green"), ("red", "orange"), ("yellow", "orange"),
            ("purple", "blue"), ("green", "teal")
        ],
        "description": "Harmonious and cohesive",
        "confidence_modifier": 0.95,
    },
    "triadic": {
        "pairs": [
            ("red", "yellow", "blue"), ("orange", "green", "purple"),
            ("teal", "magenta", "yellow")
        ],
        "description": "Balanced with visual interest",
        "confidence_modifier": 0.85,
    },
    "monochromatic": {
        "pairs": [],  # Same color family, different shades
        "description": "Sophisticated and elegant",
        "confidence_modifier": 0.92,
    },
    "neutral_safe": {
        "pairs": [
            ("black", "white"), ("navy", "beige"), ("grey", "white"),
            ("camel", "black"), ("charcoal", "cream")
        ],
        "description": "Timeless and versatile",
        "confidence_modifier": 0.98,
    },
}

PATTERN_COMPATIBILITY = {
    "solid": ["solid", "striped", "floral", "plaid", "geometric", "animal"],
    "striped": ["solid", "floral", "geometric"],
    "floral": ["solid", "striped"],
    "plaid": ["solid"],
    "geometric": ["solid", "striped"],
    "animal": ["solid"],
}

SILHOUETTE_RULES = {
    "fitted_top": ["wide_leg_bottom", "straight_bottom", "fitted_bottom"],
    "oversized_top": ["fitted_bottom", "straight_bottom"],
    "crop_top": ["high_waist_bottom", "wide_leg_bottom"],
    "long_top": ["fitted_bottom", "straight_bottom"],
    "structured_jacket": ["fitted_bottom", "straight_bottom"],
    "flowy_top": ["fitted_bottom"],
}

OCCASION_DRESS_CODES = {
    "formal": {
        "required_categories": ["top", "bottom", "shoes"],
        "preferred_colors": ["black", "navy", "charcoal", "white", "burgundy"],
        "avoid_patterns": ["animal", "loud_geometric"],
        "style_keywords": ["elegant", "sophisticated", "tailored"],
        "min_price_tier": "mid",
    },
    "work": {
        "required_categories": ["top", "bottom", "shoes"],
        "preferred_colors": ["navy", "grey", "black", "white", "beige", "blue"],
        "avoid_patterns": ["animal"],
        "style_keywords": ["professional", "polished", "smart"],
        "min_price_tier": "budget",
    },
    "date": {
        "required_categories": ["top", "bottom", "shoes"],
        "preferred_colors": ["black", "navy", "burgundy", "emerald", "florals"],
        "avoid_patterns": [],
        "style_keywords": ["attractive", "confident", "romantic"],
        "min_price_tier": "budget",
    },
    "party": {
        "required_categories": ["top", "bottom", "shoes"],
        "preferred_colors": ["black", "metallic", "red", "white", "sequin"],
        "avoid_patterns": [],
        "style_keywords": ["trendy", "bold", "eye-catching"],
        "min_price_tier": "budget",
    },
    "casual": {
        "required_categories": ["top", "bottom", "shoes"],
        "preferred_colors": [],
        "avoid_patterns": [],
        "style_keywords": ["relaxed", "comfortable", "effortless"],
        "min_price_tier": "budget",
    },
    "active": {
        "required_categories": ["top", "bottom", "shoes"],
        "preferred_colors": ["black", "grey", "navy", "bright_accents"],
        "avoid_patterns": [],
        "style_keywords": ["athletic", "functional", "performance"],
        "min_price_tier": "budget",
    },
}

# Trend data (would be updated via external API in production)
CURRENT_TRENDS = {
    "colors": ["sage_green", "terracotta", "navy", "cream", "burgundy"],
    "patterns": ["subtle_plaid", "micro_floral", "solid_textured"],
    "silhouettes": ["oversized_blazer", "wide_leg_pants", "crop_jacket"],
    "items": ["chunky_loafers", "structured_bag", "gold_jewelry"],
    "avoid": ["skinny_jeans", "neon_colors", "excessive_distressing"],
}


class AIBrainService:
    """
    Central AI brain for personalization and recommendation generation.
    
    Coordinates:
    - Behavior signals → Preference learning
    - Style profiles → Personalized recommendations  
    - Outfit interactions → Feedback loops
    - Trends → Adaptive styling
    """
    
    def __init__(self, db: Session):
        self._db = db
        self._signal_service = BehaviorSignalService(db)
        self._confidence_service = ConfidenceService(db)
    
    # ── Signal Collection (INPUT) ─────────────────────────────────────
    
    def track_style_preference(
        self,
        user_id: str,
        preference_type: str,
        value: str,
        source: str = "explicit",
        confidence: float = 0.5,
    ) -> None:
        """Track explicit style preferences from user actions."""
        self._signal_service.track(
            user_id=user_id,
            signal_type="style_preference",
            entity_type=preference_type,
            entity_id=value,
            context={"source": source, "confidence": confidence},
        )
    
    def track_interaction(
        self,
        user_id: str,
        interaction_type: str,
        entity_type: str,
        entity_id: str,
        context: Dict[str, Any] = None,
        duration_ms: int = None,
    ) -> None:
        """Track user interactions for implicit preference learning."""
        self._signal_service.track(
            user_id=user_id,
            signal_type=interaction_type,
            entity_type=entity_type,
            entity_id=entity_id,
            context=context,
            duration_ms=duration_ms,
        )
    
    def track_outfit_feedback(
        self,
        user_id: str,
        outfit_id: str,
        accepted: bool,
        feedback_type: str = "explicit",
        reason: str = None,
        context: Dict[str, Any] = None,
    ) -> None:
        """Track outfit acceptance/rejection for learning."""
        signal_type = "outfit_accepted" if accepted else "outfit_rejected"
        ctx = context or {}
        if reason:
            ctx["reason"] = reason
        ctx["feedback_type"] = feedback_type
        
        self._signal_service.track(
            user_id=user_id,
            signal_type=signal_type,
            entity_type="outfit",
            entity_id=outfit_id,
            context=ctx,
        )
        
        # Trigger preference drift check
        self._check_preference_drift(user_id, outfit_id, accepted)
    
    def track_occasion_pattern(
        self,
        user_id: str,
        occasion: str,
        outfit_id: str,
        context: Dict[str, Any] = None,
    ) -> None:
        """Track occasion-based outfit patterns."""
        ctx = context or {}
        ctx["occasion"] = occasion
        
        self._signal_service.track(
            user_id=user_id,
            signal_type="occasion_outfit",
            entity_type="occasion",
            entity_id=occasion,
            context=ctx,
        )
    
    def track_budget_behavior(
        self,
        user_id: str,
        action: str,
        amount: float,
        context: Dict[str, Any] = None,
    ) -> None:
        """Track budget-related behaviors."""
        ctx = context or {}
        ctx["amount"] = amount
        ctx["action"] = action
        
        self._signal_service.track(
            user_id=user_id,
            signal_type="budget_behavior",
            entity_type="budget",
            entity_id=action,
            context=ctx,
        )
    
    # ── Commerce Signal Tracking (GROUP 5) ───────────────────────────────
    
    def track_purchase_behavior(
        self,
        user_id: str,
        order_id: str,
        items: List[Dict[str, Any]],
        total: float,
        payment_method: str,
        context: Dict[str, Any] = None,
    ) -> None:
        """Track purchase behavior for commerce intelligence."""
        ctx = context or {}
        ctx["total"] = total
        ctx["payment_method"] = payment_method
        ctx["item_count"] = len(items)
        ctx["categories"] = list(set(i.get("category", "") for i in items))
        ctx["brands"] = list(set(i.get("brand", "") for i in items))
        
        self._signal_service.track(
            user_id=user_id,
            signal_type="purchase",
            entity_type="order",
            entity_id=order_id,
            context=ctx,
            duration_ms=None,
        )
        
        # Track individual item purchases
        for item in items:
            self._signal_service.track(
                user_id=user_id,
                signal_type="purchase",
                entity_type="product",
                entity_id=item.get("productId", ""),
                context={
                    "price": item.get("price", 0),
                    "quantity": item.get("quantity", 1),
                    "category": item.get("category", ""),
                    "brand": item.get("brand", ""),
                },
            )
    
    def track_cart_abandonment(
        self,
        user_id: str,
        cart_value: float,
        item_count: int,
        abandonment_stage: str,
        context: Dict[str, Any] = None,
    ) -> None:
        """Track cart abandonment signals for rescue strategies."""
        ctx = context or {}
        ctx["cart_value"] = cart_value
        ctx["item_count"] = item_count
        ctx["abandonment_stage"] = abandonment_stage  # 'cart', 'shipping', 'payment', 'review'
        
        self._signal_service.track(
            user_id=user_id,
            signal_type="cart_abandon",
            entity_type="cart",
            entity_id="abandoned",
            context=ctx,
        )
    
    def track_price_sensitivity(
        self,
        user_id: str,
        action: str,
        price_point: float,
        context: Dict[str, Any] = None,
    ) -> None:
        """Track price sensitivity signals."""
        ctx = context or {}
        ctx["price_point"] = price_point
        ctx["action"] = action  # 'viewed', 'added_to_cart', 'purchased', 'removed', 'abandoned'
        
        self._signal_service.track(
            user_id=user_id,
            signal_type="price_interaction",
            entity_type="price",
            entity_id=str(price_point),
            context=ctx,
        )
    
    def track_brand_affinity(
        self,
        user_id: str,
        brand: str,
        interaction_type: str,
        context: Dict[str, Any] = None,
    ) -> None:
        """Track brand affinity signals."""
        ctx = context or {}
        ctx["interaction_type"] = interaction_type  # 'view', 'try_on', 'purchase', 'wishlist', 'share'
        
        self._signal_service.track(
            user_id=user_id,
            signal_type="brand_interaction",
            entity_type="brand",
            entity_id=brand,
            context=ctx,
        )
    
    def get_commerce_insights(self, user_id: str) -> Dict[str, Any]:
        """Get aggregated commerce insights for a user."""
        signals = self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.user_id == user_id,
            UserBehaviorSignal.signal_type.in_([
                "purchase", "cart_abandon", "price_interaction", "brand_interaction",
                "view", "wishlist_add", "try_on"
            ])
        ).all()
        
        # Aggregate purchase patterns
        purchase_count = sum(1 for s in signals if s.signal_type == "purchase")
        abandon_count = sum(1 for s in signals if s.signal_type == "cart_abandon")
        
        # Price sensitivity analysis
        price_points = []
        for s in signals:
            if s.context and "price" in s.context:
                price_points.append(s.context["price"])
            elif s.context and "price_point" in s.context:
                price_points.append(s.context["price_point"])
        
        avg_price = sum(price_points) / len(price_points) if price_points else 0
        
        # Brand affinities
        brand_counts = defaultdict(int)
        for s in signals:
            if s.entity_type == "brand":
                brand_counts[s.entity_id] += 1
            elif s.context and "brand" in s.context:
                brand_counts[s.context["brand"]] += 1
        
        top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Category preferences
        categories = defaultdict(int)
        for s in signals:
            if s.context and "category" in s.context:
                categories[s.context["category"]] += 1
        
        return {
            "purchase_count": purchase_count,
            "abandonment_count": abandon_count,
            "conversion_rate": purchase_count / (purchase_count + abandon_count) if (purchase_count + abandon_count) > 0 else 0,
            "avg_price_point": round(avg_price, 2),
            "top_brands": [{"brand": b, "count": c} for b, c in top_brands],
            "preferred_categories": dict(sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]),
            "price_sensitivity": self._calculate_price_sensitivity(signals),
        }
    
    def _calculate_price_sensitivity(self, signals: List) -> float:
        """Calculate price sensitivity score (0-1, higher = more sensitive)."""
        purchases = [s for s in signals if s.signal_type == "purchase"]
        abandons = [s for s in signals if s.signal_type == "cart_abandon"]
        
        if not purchases and not abandons:
            return 0.5  # Default middle sensitivity
        
        # Higher abandonment rate = higher price sensitivity
        total = len(purchases) + len(abandons)
        abandon_rate = len(abandons) / total if total > 0 else 0
        
        return min(1.0, abandon_rate * 1.5)  # Scale up slightly
    
    # ── Preference Aggregation ────────────────────────────────────────
    
    def get_user_style_vector(self, user_id: str) -> Dict[str, Any]:
        """
        Aggregate all signals into a unified style vector.
        Returns normalized preferences across all dimensions.
        """
        profile = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        signals = self._signal_service.get_preference_summary(user_id)
        
        # Base vector from explicit profile
        vector = {
            "archetype": profile.primary_archetype if profile else None,
            "archetype_confidence": float(profile.archetype_confidence) if profile and profile.archetype_confidence else 0.0,
            "dimensions": {
                "classic": float(profile.style_classic) if profile and profile.style_classic else 0.5,
                "trendy": float(profile.style_trendy) if profile and profile.style_trendy else 0.5,
                "minimalist": float(profile.style_minimalist) if profile and profile.style_minimalist else 0.5,
                "maximalist": float(profile.style_maximalist) if profile and profile.style_maximalist else 0.5,
                "feminine": float(profile.style_feminine) if profile and profile.style_feminine else 0.5,
                "masculine": float(profile.style_masculine) if profile and profile.style_masculine else 0.5,
                "edgy": float(profile.style_edgy) if profile and profile.style_edgy else 0.5,
                "romantic": float(profile.style_romantic) if profile and profile.style_romantic else 0.5,
            },
            "colors": {
                "preferred": signals.get("colors", {}),
                "avoided": list(profile.avoided_colors) if profile and profile.avoided_colors else [],
            },
            "brands": signals.get("brands", {}),
            "categories": signals.get("categories", {}),
            "price_behavior": signals.get("price_behavior", {}),
            "signal_strength": signals.get("total_signals", 0),
        }
        
        # Enhance with implicit signals
        if signals["total_signals"] > 10:
            vector["confidence_level"] = "high"
        elif signals["total_signals"] > 5:
            vector["confidence_level"] = "medium"
        else:
            vector["confidence_level"] = "low"
        
        return vector
    
    def get_wardrobe_context(self, user_id: str) -> Dict[str, Any]:
        """Get wardrobe-aware context for personalized styling."""
        signals = self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.user_id == user_id,
            UserBehaviorSignal.entity_type == "wardrobe_item",
        ).all()
        
        items_by_category = defaultdict(list)
        colors = []
        brands = []
        
        for s in signals:
            if s.context:
                cat = s.context.get("category")
                if cat:
                    items_by_category[cat].append(s.entity_id)
                if s.context.get("color"):
                    colors.append(s.context["color"])
                if s.context.get("brand"):
                    brands.append(s.context["brand"])
        
        return {
            "categories": dict(items_by_category),
            "available_colors": list(set(colors)),
            "available_brands": list(set(brands)),
            "total_items": len(signals),
        }
    
    def get_contextual_factors(self, user_id: str) -> Dict[str, Any]:
        """Get contextual factors like location, weather, lifestyle."""
        context = self._db.query(UserContextualPreference).filter_by(user_id=user_id).first()
        
        if not context:
            return {
                "climate_zone": None,
                "work_environment": None,
                "activity_level": None,
                "weather_preferences": {},
                "occasion_weights": {},
            }
        
        return {
            "climate_zone": context.climate_zone,
            "work_environment": context.work_environment,
            "activity_level": context.activity_level,
            "weather_preferences": context.weather_preferences or {},
            "occasion_weights": context.occasion_weights or {},
            "cultural_influences": context.cultural_influences or [],
            "modesty_preference": context.modesty_preference,
        }
    
    # ── Recommendation Generation (OUTPUT) ────────────────────────────
    
    def generate_outfit_recommendations(
        self,
        user_id: str,
        occasion: str = None,
        budget: float = None,
        item_constraints: Dict[str, str] = None,
        use_wardrobe: bool = True,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate personalized outfit recommendations.
        
        Args:
            user_id: User identifier
            occasion: Target occasion (formal, work, date, etc.)
            budget: Budget constraint
            item_constraints: Required items, e.g., {"top": "item_123"}
            use_wardrobe: Whether to include wardrobe items
            limit: Max recommendations to return
            
        Returns:
            List of outfit recommendations with scores and explanations
        """
        style_vector = self.get_user_style_vector(user_id)
        wardrobe_context = self.get_wardrobe_context(user_id) if use_wardrobe else {}
        contextual = self.get_contextual_factors(user_id)
        
        recommendations = []
        
        # Get dress code rules for occasion
        dress_code = OCCASION_DRESS_CODES.get(occasion, OCCASION_DRESS_CODES["casual"])
        
        # Generate base recommendations (would integrate with product catalog)
        for i in range(limit):
            outfit = {
                "id": f"rec_{user_id[:8]}_{i}",
                "items": [],  # Would be populated from catalog/wardrobe
                "scores": self._calculate_outfit_scores(
                    {}, style_vector, dress_code, contextual
                ),
                "explanation": "",
                "confidence": 0.0,
            }
            
            outfit["explanation"] = self._generate_explanation(outfit, style_vector, occasion)
            outfit["confidence"] = self._calculate_confidence(outfit, style_vector)
            
            recommendations.append(outfit)
        
        # Sort by confidence and return top results
        recommendations.sort(key=lambda x: x["confidence"], reverse=True)
        return recommendations[:limit]
    
    def _calculate_outfit_scores(
        self,
        outfit: Dict[str, Any],
        style_vector: Dict[str, Any],
        dress_code: Dict[str, Any],
        contextual: Dict[str, Any],
    ) -> Dict[str, float]:
        """Calculate multi-dimensional outfit scores."""
        scores = {
            "style_alignment": 0.0,
            "color_harmony": 0.0,
            "occasion_fit": 0.0,
            "trend_alignment": 0.0,
            "wardrobe_compatibility": 0.0,
            "budget_fit": 0.0,
        }
        
        # Style alignment (how well it matches user's style dimensions)
        # Would be calculated based on actual items
        
        # Color harmony (based on fashion rules)
        # Would check if colors follow harmony rules
        
        # Occasion fit (how well it matches dress code)
        # Would check against OCCASION_DRESS_CODES
        
        # Trend alignment
        # Would check against CURRENT_TRENDS
        
        return scores
    
    def _generate_explanation(
        self,
        outfit: Dict[str, Any],
        style_vector: Dict[str, Any],
        occasion: str,
    ) -> str:
        """Generate human-readable explanation for the recommendation."""
        explanations = []
        
        if style_vector.get("archetype"):
            explanations.append(
                f"This look aligns with your {style_vector['archetype']} style archetype."
            )
        
        if occasion:
            explanations.append(
                f"Perfect for a {occasion} occasion with appropriate formality."
            )
        
        # Would add more specific explanations based on items
        
        return " ".join(explanations) if explanations else "A personalized recommendation based on your style profile."
    
    def _calculate_confidence(
        self,
        outfit: Dict[str, Any],
        style_vector: Dict[str, Any],
    ) -> float:
        """Calculate overall confidence score for recommendation."""
        base_confidence = style_vector.get("signal_strength", 0) / 100
        profile_confidence = style_vector.get("archetype_confidence", 0)
        
        # Weighted average
        confidence = (base_confidence * 0.4) + (profile_confidence * 0.6)
        
        return min(confidence, 1.0)
    
    # ── Fashion Rule Engine ───────────────────────────────────────────
    
    def validate_color_combination(self, colors: List[str]) -> Dict[str, Any]:
        """Validate color combination against fashion rules."""
        if len(colors) < 2:
            return {"valid": True, "harmony": "monochromatic", "confidence": 1.0}
        
        # Check each harmony type
        for harmony_type, rules in COLOR_HARMONY_RULES.items():
            if harmony_type == "monochromatic":
                # Check if all colors are from same family
                pass
            else:
                for pair in rules["pairs"]:
                    if len(pair) == 2:
                        if pair[0] in colors and pair[1] in colors:
                            return {
                                "valid": True,
                                "harmony": harmony_type,
                                "description": rules["description"],
                                "confidence": rules["confidence_modifier"],
                            }
        
        # Default neutral check
        neutral_colors = ["black", "white", "grey", "navy", "beige", "cream", "charcoal"]
        neutral_count = sum(1 for c in colors if c in neutral_colors)
        
        if neutral_count >= len(colors) - 1:
            return {
                "valid": True,
                "harmony": "neutral_safe",
                "description": "Timeless neutral palette",
                "confidence": 0.95,
            }
        
        return {
            "valid": True,
            "harmony": "mixed",
            "description": "Eclectic combination",
            "confidence": 0.7,
        }
    
    def validate_pattern_combination(self, patterns: List[str]) -> Dict[str, Any]:
        """Validate pattern combination against fashion rules."""
        if len(patterns) < 2:
            return {"valid": True, "confidence": 1.0}
        
        # Check compatibility
        for i, pattern in enumerate(patterns):
            compatible = PATTERN_COMPATIBILITY.get(pattern, ["solid"])
            for other_pattern in patterns[i+1:]:
                if other_pattern not in compatible:
                    return {
                        "valid": False,
                        "reason": f"{pattern} and {other_pattern} may clash",
                        "confidence": 0.5,
                    }
        
        return {"valid": True, "confidence": 0.9}
    
    def validate_silhouette_balance(self, silhouettes: List[str]) -> Dict[str, Any]:
        """Validate silhouette balance for proportion."""
        if len(silhouettes) < 2:
            return {"valid": True, "confidence": 1.0}
        
        # Check top/bottom balance
        for i, silhouette in enumerate(silhouettes):
            compatible = SILHOUETTE_RULES.get(silhouette, [])
            for other in silhouettes[i+1:]:
                if other not in compatible:
                    return {
                        "valid": True,
                        "warning": f"Consider balancing {silhouette} with different proportions",
                        "confidence": 0.75,
                    }
        
        return {"valid": True, "confidence": 0.95}
    
    def check_occasion_appropriateness(
        self,
        outfit_data: Dict[str, Any],
        occasion: str,
    ) -> Dict[str, Any]:
        """Check if outfit meets occasion dress code requirements."""
        dress_code = OCCASION_DRESS_CODES.get(occasion)
        
        if not dress_code:
            return {"appropriate": True, "confidence": 1.0}
        
        issues = []
        score = 1.0
        
        # Check required categories
        # Check preferred colors
        # Check avoided patterns
        # Check style keywords
        
        return {
            "appropriate": len(issues) == 0,
            "issues": issues,
            "score": score,
            "dress_code": dress_code,
        }
    
    # ── Trend Adaptation ───────────────────────────────────────────────
    
    def get_trending_elements(self) -> Dict[str, Any]:
        """Get current trending elements for recommendations."""
        return CURRENT_TRENDS.copy()
    
    def adapt_to_trends(
        self,
        style_vector: Dict[str, Any],
        trend_sensitivity: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Adapt recommendations to current trends based on user's
        trend sensitivity (from experimentation_level).
        """
        trends = self.get_trending_elements()
        
        # Higher trend sensitivity = more trend influence
        adapted = {
            "trending_colors": trends["colors"] if trend_sensitivity > 0.3 else [],
            "trending_patterns": trends["patterns"] if trend_sensitivity > 0.4 else [],
            "trending_silhouettes": trends["silhouettes"] if trend_sensitivity > 0.5 else [],
            "avoid": trends["avoid"] if trend_sensitivity > 0.2 else [],
        }
        
        return adapted
    
    # ── Climate/Location Awareness ─────────────────────────────────────
    
    def get_weather_appropriate_items(
        self,
        user_id: str,
        weather_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Get weather-appropriate styling recommendations."""
        contextual = self.get_contextual_factors(user_id)
        climate_zone = contextual.get("climate_zone")
        weather_prefs = contextual.get("weather_preferences", {})
        
        # Would integrate with weather API
        recommendations = {
            "layering_suggested": False,
            "fabrics": [],
            "colors": [],
            "accessories": [],
        }
        
        # Temperature-based logic
        # Weather condition logic (rain, sun, etc.)
        
        return recommendations
    
    # ── Learning & Feedback Loop ───────────────────────────────────────
    
    def _check_preference_drift(
        self,
        user_id: str,
        outfit_id: str,
        accepted: bool,
    ) -> None:
        """Check if user preferences are drifting based on feedback patterns."""
        recent_feedback = self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.user_id == user_id,
            UserBehaviorSignal.signal_type.in_(["outfit_accepted", "outfit_rejected"]),
            UserBehaviorSignal.created_at >= datetime.now(timezone.utc) - timedelta(days=30)
        ).all()
        
        if len(recent_feedback) < 5:
            return
        
        accepted_count = sum(1 for s in recent_feedback if s.signal_type == "outfit_accepted")
        rejection_rate = 1 - (accepted_count / len(recent_feedback))
        
        # High rejection rate indicates preference drift
        if rejection_rate > 0.6:
            evolution = UserStyleEvolution(
                user_id=user_id,
                event_type="preference_drift_detected",
                previous_value={"rejection_rate": 0},
                new_value={"rejection_rate": rejection_rate},
                trigger_source="implicit",
                confidence_delta=Decimal("-0.1"),
            )
            self._db.add(evolution)
            self._db.commit()
            
            logger.info(f"Preference drift detected for user {user_id}: {rejection_rate:.2%} rejection rate")
    
    def update_style_evolution(
        self,
        user_id: str,
        event_type: str,
        previous_value: Any,
        new_value: Any,
        trigger_source: str = "implicit",
    ) -> None:
        """Record style evolution event for tracking user journey."""
        evolution = UserStyleEvolution(
            user_id=user_id,
            event_type=event_type,
            previous_value=previous_value,
            new_value=new_value,
            trigger_source=trigger_source,
        )
        self._db.add(evolution)
        self._db.commit()
    
    # ── Confidence Integration ─────────────────────────────────────────
    
    def recalculate_user_confidence(self, user_id: str, trigger_event: str = None) -> Dict[str, Any]:
        """Recalculate user's confidence scores after significant events."""
        return self._confidence_service.recalculate(user_id, trigger_event)
    
    def get_confidence_breakdown(self, user_id: str) -> Dict[str, Any]:
        """Get detailed breakdown of user's confidence dimensions."""
        profile = self._confidence_service.get_profile(user_id)
        return profile.model_dump()
    
    # ── Brand Intelligence Integration (GROUP 6) ───────────────────────────
    
    def track_brand_performance(
        self,
        brand_id: str,
        performance_type: str,
        metrics: Dict[str, Any],
        context: Dict[str, Any] = None,
    ) -> None:
        """Track brand performance signals for marketplace intelligence."""
        ctx = context or {}
        ctx["metrics"] = metrics
        
        self._signal_service.track(
            user_id="system",
            signal_type=f"brand_{performance_type}",
            entity_type="brand",
            entity_id=brand_id,
            context=ctx,
        )
    
    def track_item_performance(
        self,
        brand_id: str,
        product_id: str,
        performance_data: Dict[str, Any],
    ) -> None:
        """Track item-level performance for brand intelligence."""
        self._signal_service.track(
            user_id="system",
            signal_type="item_performance",
            entity_type="product",
            entity_id=product_id,
            context={
                "brand_id": brand_id,
                **performance_data,
            },
        )
    
    def track_styling_popularity(
        self,
        brand_id: str,
        product_id: str,
        outfit_appearances: int,
        stylist_picks: int,
        user_favorites: int,
    ) -> None:
        """Track how often brand items appear in styled outfits."""
        self._signal_service.track(
            user_id="system",
            signal_type="styling_popularity",
            entity_type="product",
            entity_id=product_id,
            context={
                "brand_id": brand_id,
                "outfit_appearances": outfit_appearances,
                "stylist_picks": stylist_picks,
                "user_favorites": user_favorites,
            },
        )
    
    def track_brand_return_data(
        self,
        brand_id: str,
        return_rate: float,
        return_reasons: Dict[str, int],
        affected_categories: List[str],
    ) -> None:
        """Track brand return data for quality intelligence."""
        self._signal_service.track(
            user_id="system",
            signal_type="brand_returns",
            entity_type="brand",
            entity_id=brand_id,
            context={
                "return_rate": return_rate,
                "return_reasons": return_reasons,
                "affected_categories": affected_categories,
            },
        )
    
    def track_engagement_analytics(
        self,
        brand_id: str,
        views: int,
        wishlist_adds: int,
        try_on_sessions: int,
        shares: int,
        conversion_rate: float,
    ) -> None:
        """Track brand engagement analytics."""
        self._signal_service.track(
            user_id="system",
            signal_type="brand_engagement",
            entity_type="brand",
            entity_id=brand_id,
            context={
                "views": views,
                "wishlist_adds": wishlist_adds,
                "try_on_sessions": try_on_sessions,
                "shares": shares,
                "conversion_rate": conversion_rate,
            },
        )
    
    def get_brand_insights(self, brand_id: str) -> Dict[str, Any]:
        """Get aggregated insights for a brand from AI Brain data."""
        # Aggregate brand signals
        signals = self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.entity_type == "brand",
            UserBehaviorSignal.entity_id == brand_id,
        ).all()
        
        # Also get product signals for this brand
        product_signals = self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.context.contains(f'"brand_id": "{brand_id}"'),
        ).all()
        
        all_signals = list(signals) + list(product_signals)
        
        # Aggregate insights
        total_views = sum(1 for s in all_signals if s.signal_type == "view")
        total_purchases = sum(1 for s in all_signals if s.signal_type == "purchase")
        total_tryons = sum(1 for s in all_signals if "try_on" in s.signal_type)
        
        # Calculate popularity score
        popularity_score = (total_views * 0.1 + total_purchases * 10 + total_tryons * 2)
        
        # Get user affinities for this brand
        affinities = self._db.query(UserBrandAffinity).filter_by(brand_name=brand_id).all()
        avg_affinity = sum(float(a.affinity_score) for a in affinities) / len(affinities) if affinities else 0
        
        return {
            "brand_id": brand_id,
            "popularity_score": round(popularity_score, 2),
            "total_views": total_views,
            "total_purchases": total_purchases,
            "total_tryons": total_tryons,
            "average_user_affinity": round(avg_affinity, 3),
            "signal_count": len(all_signals),
            "unique_users": len(set(s.user_id for s in all_signals if s.user_id != "system")),
        }
    
    def generate_ranking_adjustments(self, brand_id: str) -> Dict[str, float]:
        """
        Generate ranking adjustments for brand products.
        
        Based on:
        - User preference alignment
        - Trend alignment
        - Performance metrics
        - Quality scores
        """
        insights = self.get_brand_insights(brand_id)
        
        # Calculate adjustment factors
        popularity_factor = min(1.5, insights["popularity_score"] / 100)
        affinity_factor = insights["average_user_affinity"]
        
        # Generate product-level adjustments
        adjustments = {
            "visibility_boost": round((popularity_factor + affinity_factor) / 2, 3),
            "recommendation_weight": round(affinity_factor * 1.2, 3),
            "search_ranking_boost": round(popularity_factor * 0.8, 3),
        }
        
        return adjustments
    
    def generate_recommendation_boost(self, brand_id: str) -> Dict[str, Any]:
        """
        Generate recommendation boost configuration for brand.
        
        Determines how brand products should be boosted in:
        - Outfit recommendations
        - Similar item suggestions
        - Search results
        """
        insights = self.get_brand_insights(brand_id)
        adjustments = self.generate_ranking_adjustments(brand_id)
        
        # Determine boost level
        if insights["popularity_score"] > 100:
            boost_level = "high"
        elif insights["popularity_score"] > 50:
            boost_level = "medium"
        else:
            boost_level = "low"
        
        return {
            "brand_id": brand_id,
            "boost_level": boost_level,
            "boost_factors": adjustments,
            "target_contexts": [
                "outfit_recommendations",
                "similar_items",
                "search_results",
                "trending_section",
            ],
            "effective_until": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }
    
    def get_inventory_intelligence_request(self, brand_id: str) -> Dict[str, Any]:
        """
        Request inventory intelligence from brand service.
        
        Returns parameters for inventory analysis.
        """
        insights = self.get_brand_insights(brand_id)
        
        return {
            "brand_id": brand_id,
            "analysis_parameters": {
                "demand_forecast_weight": min(1.0, insights["popularity_score"] / 50),
                "seasonality_importance": 0.3,
                "trend_sensitivity": 0.2,
            },
            "priority_categories": self._identify_priority_categories(brand_id),
            "reorder_threshold_days": 14,
            "overstock_threshold_days": 90,
        }
    
    def _identify_priority_categories(self, brand_id: str) -> List[str]:
        """Identify high-priority categories for a brand."""
        # Would analyze product signals to identify top categories
        return ["tops", "dresses", "outerwear"]  # Placeholder


def get_ai_brain_service(db: Session = Depends(get_db)) -> AIBrainService:
    return AIBrainService(db)


# ── Outfit Rating Integration ──────────────────────────────────────────────────

def track_outfit_rating_signal(
    service: AIBrainService,
    user_id: str,
    outfit_id: str,
    rating: int,
    previous_rating: Optional[int] = None,
) -> None:
    """
    Track outfit rating as a preference signal.
    
    Ratings provide explicit preference signals that can be used to:
    - Understand style preferences
    - Identify preferred brands, categories, colors
    - Adjust recommendation confidence
    """
    context = {
        "rating": rating,
        "previous_rating": previous_rating,
        "rating_delta": rating - previous_rating if previous_rating else 0,
    }
    
    signal_type = "outfit_rated"
    service._signal_service.track(
        user_id=user_id,
        signal_type=signal_type,
        entity_type="outfit",
        entity_id=outfit_id,
        context=context,
    )


def track_outfit_like_signal(
    service: AIBrainService,
    user_id: str,
    outfit_id: str,
    is_like: bool,
) -> None:
    """
    Track outfit like/dislike as a preference signal.
    
    Likes provide implicit preference signals for:
    - Style affinity
    - Trend alignment
    - Brand/category preferences
    """
    signal_type = "outfit_liked" if is_like else "outfit_disliked"
    service._signal_service.track(
        user_id=user_id,
        signal_type=signal_type,
        entity_type="outfit",
        entity_id=outfit_id,
        context={"is_like": is_like},
    )


def track_outfit_save_signal(
    service: AIBrainService,
    user_id: str,
    outfit_id: str,
    collection_name: Optional[str] = None,
) -> None:
    """
    Track outfit save as a strong preference signal.
    
    Saves indicate high intent and can be used for:
    - Purchase prediction
    - Style preference learning
    - Collection-based recommendations
    """
    context = {"collection_name": collection_name}
    service._signal_service.track(
        user_id=user_id,
        signal_type="outfit_saved",
        entity_type="outfit",
        entity_id=outfit_id,
        context=context,
    )


def get_rating_enhanced_recommendations(
    service: AIBrainService,
    user_id: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Get outfit recommendations enhanced by rating data.
    
    Combines:
    - User's style vector
    - Rating history patterns
    - Trending/popular outfits
    - Similar user preferences
    """
    from database.models import OutfitPopularity, OutfitRating, OutfitLike
    
    # Get user's style vector
    style_vector = service.get_user_style_vector(user_id)
    
    # Get user's rating patterns
    ratings = service._db.query(OutfitRating).filter(
        OutfitRating.user_id == user_id
    ).order_by(OutfitRating.created_at.desc()).limit(50).all()
    
    # Calculate average rating given by user
    avg_user_rating = sum(r.rating for r in ratings) / len(ratings) if ratings else 3.0
    
    # Get user's liked outfits
    likes = service._db.query(OutfitLike).filter(
        OutfitLike.user_id == user_id,
        OutfitLike.is_like == True
    ).limit(50).all()
    
    liked_outfit_ids = [l.outfit_id for l in likes]
    
    # Get trending outfits with high scores
    trending = service._db.query(OutfitPopularity).order_by(
        OutfitPopularity.trending_score.desc()
    ).limit(limit * 2).all()
    
    # Filter out already rated/liked outfits
    rated_outfit_ids = [r.outfit_id for r in ratings]
    recommendations = []
    
    for pop in trending:
        if pop.outfit_id in rated_outfit_ids or pop.outfit_id in liked_outfit_ids:
            continue
        
        # Calculate recommendation score
        rec_score = (
            pop.trending_score * 0.3 +
            pop.popularity_score * 0.3 +
            pop.avg_rating * 10 * 0.2 +
            pop.style_relevance_score * 0.2
        )
        
        # Boost if matches user's style confidence
        if style_vector.get("confidence_level") == "high":
            rec_score *= 1.1
        
        recommendations.append({
            "outfit_id": pop.outfit_id,
            "recommendation_score": round(rec_score, 2),
            "avg_rating": pop.avg_rating,
            "trending_score": pop.trending_score,
            "popularity_score": pop.popularity_score,
            "like_count": pop.like_count,
            "save_count": pop.save_count,
        })
        
        if len(recommendations) >= limit:
            break
    
    return recommendations


def get_rating_based_style_insights(
    service: AIBrainService,
    user_id: str,
) -> Dict[str, Any]:
    """
    Derive style insights from user's rating patterns.
    
    Analyzes:
    - Rating distribution
    - Preferred outfit characteristics
    - Style evolution over time
    """
    from database.models import OutfitRating, Outfit, OutfitLike
    from collections import Counter
    
    # Get all user ratings with outfit details
    ratings = service._db.query(OutfitRating, Outfit).join(
        Outfit, OutfitRating.outfit_id == Outfit.id
    ).filter(OutfitRating.user_id == user_id).all()
    
    if not ratings:
        return {
            "total_ratings": 0,
            "insights": [],
            "preferences": {},
        }
    
    # Analyze rating distribution
    rating_dist = Counter(r.rating for r, _ in ratings)
    avg_rating = sum(r.rating for r, _ in ratings) / len(ratings)
    
    # Analyze highly rated outfits (4-5 stars)
    high_rated = [(r, o) for r, o in ratings if r.rating >= 4]
    
    # Extract preferences from highly rated outfits
    preferred_occasions = Counter()
    preferred_categories = Counter()
    preferred_colors = Counter()
    
    for _, outfit in high_rated:
        if outfit.occasion:
            preferred_occasions[outfit.occasion] += 1
        for item in outfit.items:
            if item.get("category"):
                preferred_categories[item["category"]] += 1
            if item.get("color"):
                preferred_colors[item["color"]] += 1
    
    # Get likes for additional insight
    likes_count = service._db.query(OutfitLike).filter(
        OutfitLike.user_id == user_id,
        OutfitLike.is_like == True
    ).count()
    
    dislikes_count = service._db.query(OutfitLike).filter(
        OutfitLike.user_id == user_id,
        OutfitLike.is_like == False
    ).count()
    
    return {
        "total_ratings": len(ratings),
        "average_rating_given": round(avg_rating, 2),
        "rating_distribution": dict(rating_dist),
        "likes_count": likes_count,
        "dislikes_count": dislikes_count,
        "preferences": {
            "top_occasions": preferred_occasions.most_common(5),
            "top_categories": preferred_categories.most_common(5),
            "top_colors": preferred_colors.most_common(5),
        },
        "insights": _generate_rating_insights(avg_rating, rating_dist, likes_count, dislikes_count),
    }


def _generate_rating_insights(
    avg_rating: float,
    rating_dist: Dict[int, int],
    likes: int,
    dislikes: int,
) -> List[str]:
    """Generate human-readable insights from rating patterns."""
    insights = []
    
    # Rating behavior insights
    if avg_rating >= 4.0:
        insights.append("You tend to be generous with ratings, focusing on the positive aspects.")
    elif avg_rating <= 2.5:
        insights.append("You have discerning taste and high standards for outfits.")
    else:
        insights.append("You provide balanced ratings, giving fair assessments.")
    
    # Engagement insights
    total_engagement = sum(rating_dist.values()) + likes + dislikes
    if total_engagement > 50:
        insights.append("You're highly engaged with the community, actively rating and reviewing outfits.")
    elif total_engagement > 20:
        insights.append("You regularly engage with outfits, helping improve recommendations.")
    
    # Like/dislike ratio
    if likes + dislikes > 0:
        like_ratio = likes / (likes + dislikes)
        if like_ratio > 0.8:
            insights.append("You're very positive, liking most outfits you see!")
        elif like_ratio < 0.5:
            insights.append("You're selective, only liking outfits that truly resonate with you.")
    
    return insights
