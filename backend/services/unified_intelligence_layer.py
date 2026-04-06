"""
CONFIT Backend — Unified Intelligence Layer
===========================================
Single source of truth for AI signals across ALL feature groups.

This layer ensures:
- No duplicated signals
- Consistent personalization across features
- Unified user context for all AI operations
- Cross-feature signal propagation

Signal Sources:
- GROUP 1: Identity signals (style, body, budget, brand affinities)
- GROUP 2: Styling signals (conversations, outfits, recommendations)
- GROUP 3: Try-on signals (fit, pose, visual realism, size prediction)
- GROUP 4: Wardrobe signals (items, usage, gaps, versatility)
- GROUP 5: Commerce signals (purchases, returns, cart, price sensitivity)
- GROUP 6: Budget signals (limits, BNPL, spending patterns)
- GROUP 7: Social signals (shares, votes, follows, challenges)
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal
from enum import Enum
from collections import defaultdict
import json

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from models.profile_models import (
    UserStyleProfile,
    UserBodyProfile,
    UserBudgetProfile,
    UserBrandAffinity,
    UserContextualPreference,
    UserConfidenceProfile,
    UserBehaviorSignal,
    UserStyleEvolution,
)

logger = logging.getLogger(__name__)


# ── Signal Categories ─────────────────────────────────────────────────

class SignalCategory(Enum):
    """Unified signal categories across all feature groups."""
    
    # Identity Signals (GROUP 1)
    STYLE_PREFERENCE = "style_preference"
    BODY_PROFILE = "body_profile"
    BUDGET_PREFERENCE = "budget_preference"
    BRAND_AFFINITY = "brand_affinity"
    OCCASION_PREFERENCE = "occasion_preference"
    
    # Styling Signals (GROUP 2)
    STYLIST_INTERACTION = "stylist_interaction"
    OUTFIT_CREATED = "outfit_created"
    RECOMMENDATION_FEEDBACK = "recommendation_feedback"
    STYLE_SCORE = "style_score"
    
    # Try-On Signals (GROUP 3)
    TRYON_COMPLETED = "tryon_completed"
    FIT_CONFIDENCE = "fit_confidence"
    POSE_QUALITY = "pose_quality"
    VISUAL_REALISM = "visual_realism"
    SIZE_PREDICTION = "size_prediction"
    GARMENT_DEFORMATION = "garment_deformation"
    
    # Wardrobe Signals (GROUP 4)
    WARDROBE_ITEM_ADDED = "wardrobe_item_added"
    WARDROBE_ITEM_WORN = "wardrobe_item_worn"
    WARDROBE_GAP = "wardrobe_gap"
    CAPSULE_CREATED = "capsule_created"
    COST_PER_WEAR = "cost_per_wear"
    
    # Commerce Signals (GROUP 5)
    PRODUCT_VIEWED = "product_viewed"
    PRODUCT_WISHLISTED = "product_wishlisted"
    CART_ABANDONED = "cart_abandoned"
    PURCHASE_MADE = "purchase_made"
    RETURN_INITIATED = "return_initiated"
    PRICE_SENSITIVITY = "price_sensitivity"
    
    # Budget Signals (GROUP 6)
    BUDGET_LIMIT_SET = "budget_limit_set"
    SPENDING_PATTERN = "spending_pattern"
    BNPL_USED = "bnpl_used"
    SAVINGS_GOAL = "savings_goal"
    
    # Social Signals (GROUP 7)
    POST_SHARED = "post_shared"
    POST_VOTED = "post_voted"
    FOLLOW_GAINED = "follow_gained"
    CHALLENGE_COMPLETED = "challenge_completed"


# ── Signal Weights for AI ─────────────────────────────────────────────

SIGNAL_WEIGHTS = {
    # High-weight signals (strong preference indicators)
    SignalCategory.PURCHASE_MADE: 1.0,
    SignalCategory.RETURN_INITIATED: -0.5,
    SignalCategory.RECOMMENDATION_FEEDBACK: 0.8,
    SignalCategory.TRYON_COMPLETED: 0.6,
    SignalCategory.FIT_CONFIDENCE: 0.5,
    SignalCategory.OUTFIT_CREATED: 0.5,
    SignalCategory.WARDROBE_ITEM_WORN: 0.4,
    
    # Medium-weight signals
    SignalCategory.PRODUCT_WISHLISTED: 0.3,
    SignalCategory.STYLIST_INTERACTION: 0.3,
    SignalCategory.POST_SHARED: 0.3,
    SignalCategory.POST_VOTED: 0.2,
    SignalCategory.PRODUCT_VIEWED: 0.1,
    
    # Context signals (lower weight, high volume)
    SignalCategory.STYLE_PREFERENCE: 0.7,
    SignalCategory.BRAND_AFFINITY: 0.6,
    SignalCategory.OCCASION_PREFERENCE: 0.5,
    SignalCategory.BUDGET_PREFERENCE: 0.4,
    
    # Decay rates (days)
    "decay_days": {
        SignalCategory.PRODUCT_VIEWED: 30,
        SignalCategory.PRODUCT_WISHLISTED: 90,
        SignalCategory.TRYON_COMPLETED: 60,
        SignalCategory.PURCHASE_MADE: None,  # Never decay
        SignalCategory.RETURN_INITIATED: None,
    }
}


# ── Unified User Context ─────────────────────────────────────────────

class UnifiedUserContext:
    """
    Complete user context for any AI operation.
    
    This is the single source of truth for personalization.
    All feature groups should use this context, not their own queries.
    """
    
    def __init__(self, user_id: str, db: Session):
        self.user_id = user_id
        self._db = db
        self._cache = {}
        self._loaded = False
    
    def load(self) -> "UnifiedUserContext":
        """Load all user context data."""
        if self._loaded:
            return self
        
        # Load all profile data
        self._cache["style_profile"] = self._db.query(UserStyleProfile).filter_by(
            user_id=self.user_id
        ).first()
        
        self._cache["body_profile"] = self._db.query(UserBodyProfile).filter_by(
            user_id=self.user_id
        ).first()
        
        self._cache["budget_profile"] = self._db.query(UserBudgetProfile).filter_by(
            user_id=self.user_id
        ).first()
        
        self._cache["contextual_prefs"] = self._db.query(UserContextualPreference).filter_by(
            user_id=self.user_id
        ).first()
        
        self._cache["confidence_profile"] = self._db.query(UserConfidenceProfile).filter_by(
            user_id=self.user_id
        ).first()
        
        self._cache["brand_affinities"] = self._db.query(UserBrandAffinity).filter_by(
            user_id=self.user_id
        ).all()
        
        # Load recent signals (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        self._cache["recent_signals"] = self._db.query(UserBehaviorSignal).filter(
            and_(
                UserBehaviorSignal.user_id == self.user_id,
                UserBehaviorSignal.created_at >= thirty_days_ago
            )
        ).order_by(UserBehaviorSignal.created_at.desc()).limit(100).all()
        
        # Load style evolution
        self._cache["style_evolution"] = self._db.query(UserStyleEvolution).filter_by(
            user_id=self.user_id
        ).order_by(UserStyleEvolution.created_at.desc()).limit(20).all()
        
        self._loaded = True
        return self
    
    # ── Style Context ───────────────────────────────────────────────
    
    @property
    def style_vector(self) -> Dict[str, float]:
        """Get normalized style vector (8 dimensions)."""
        profile = self._cache.get("style_profile")
        if not profile:
            return self._default_style_vector()
        
        return {
            "classic": float(profile.style_classic or 0.5),
            "trendy": float(profile.style_trendy or 0.5),
            "minimalist": float(profile.style_minimalist or 0.5),
            "maximalist": float(profile.style_maximalist or 0.5),
            "feminine": float(profile.style_feminine or 0.5),
            "masculine": float(profile.style_masculine or 0.5),
            "edgy": float(profile.style_edgy or 0.5),
            "romantic": float(profile.style_romantic or 0.5),
        }
    
    @property
    def archetype(self) -> Dict[str, Any]:
        """Get style archetype information."""
        profile = self._cache.get("style_profile")
        if not profile:
            return {"primary": None, "secondary": [], "confidence": 0.0}
        
        return {
            "primary": profile.primary_archetype,
            "secondary": profile.secondary_archetypes or [],
            "confidence": float(profile.archetype_confidence or 0),
        }
    
    @property
    def color_profile(self) -> Dict[str, Any]:
        """Get color preferences and undertone."""
        profile = self._cache.get("style_profile")
        if not profile:
            return {"preferred": [], "avoided": [], "undertone": None}
        
        return {
            "preferred": profile.preferred_colors or [],
            "avoided": profile.avoided_colors or [],
            "undertone": profile.skin_undertone,
            "confidence": float(profile.color_confidence or 0),
        }
    
    @property
    def pattern_preferences(self) -> Dict[str, float]:
        """Get pattern preferences."""
        profile = self._cache.get("style_profile")
        return profile.pattern_preferences if profile and profile.pattern_preferences else {}
    
    @property
    def fit_preference(self) -> str:
        """Get fit preference (tight, regular, relaxed, oversized)."""
        profile = self._cache.get("style_profile")
        return profile.fit_preference if profile else "regular"
    
    # ── Body Context ─────────────────────────────────────────────────
    
    @property
    def body_measurements(self) -> Dict[str, Optional[int]]:
        """Get body measurements in cm."""
        profile = self._cache.get("body_profile")
        if not profile or profile.profile_status == "not_set":
            return {}
        
        return {
            "height_cm": profile.height_cm,
            "weight_kg": profile.weight_kg,
            "chest_cm": profile.chest_cm,
            "waist_cm": profile.waist_cm,
            "hips_cm": profile.hips_cm,
            "inseam_cm": profile.inseam_cm,
        }
    
    @property
    def body_shape(self) -> Optional[str]:
        """Get body shape classification."""
        profile = self._cache.get("body_profile")
        return profile.body_shape if profile else None
    
    @property
    def size_profile(self) -> Dict[str, Any]:
        """Get size profile with brand overrides."""
        profile = self._cache.get("body_profile")
        if not profile:
            return {}
        
        return {
            "tops": profile.size_tops,
            "bottoms": profile.size_bottoms,
            "dresses": profile.size_dresses,
            "shoes": profile.size_shoes,
            "brand_overrides": profile.brand_size_overrides or {},
        }
    
    @property
    def fit_issues(self) -> List[str]:
        """Get known fit issues."""
        profile = self._cache.get("body_profile")
        return profile.fit_issues if profile and profile.fit_issues else []
    
    # ── Budget Context ──────────────────────────────────────────────
    
    @property
    def budget_limits(self) -> Dict[str, Any]:
        """Get budget limits and preferences."""
        profile = self._cache.get("budget_profile")
        if not profile:
            return {}
        
        return {
            "per_item_min": float(profile.per_item_min) if profile.per_item_min else None,
            "per_item_max": float(profile.per_item_max) if profile.per_item_max else None,
            "monthly_max": float(profile.monthly_max) if profile.monthly_max else None,
            "currency": profile.currency or "USD",
            "investment_willing": profile.investment_willing or False,
            "price_sensitivity": float(profile.price_sensitivity or 0.5),
        }
    
    # ── Brand Context ────────────────────────────────────────────────
    
    @property
    def brand_affinities(self) -> Dict[str, float]:
        """Get brand affinity scores."""
        affinities = self._cache.get("brand_affinities", [])
        return {
            a.brand_id: float(a.affinity_score or 0.5)
            for a in affinities
        }
    
    @property
    def preferred_brands(self) -> List[str]:
        """Get list of preferred brands (affinity > 0.6)."""
        return [
            brand for brand, score in self.brand_affinities.items()
            if score > 0.6
        ]
    
    @property
    def avoided_brands(self) -> List[str]:
        """Get list of avoided brands (affinity < 0.3)."""
        return [
            brand for brand, score in self.brand_affinities.items()
            if score < 0.3
        ]
    
    # ── Contextual Preferences ──────────────────────────────────────
    
    @property
    def occasion_weights(self) -> Dict[str, float]:
        """Get occasion preference weights."""
        prefs = self._cache.get("contextual_prefs")
        return prefs.occasion_weights if prefs and prefs.occasion_weights else {}
    
    @property
    def lifestyle_context(self) -> Dict[str, Any]:
        """Get lifestyle context."""
        prefs = self._cache.get("contextual_prefs")
        if not prefs:
            return {}
        
        return {
            "work_environment": prefs.work_environment,
            "climate_zone": prefs.climate_zone,
            "activity_level": prefs.activity_level,
            "has_children": prefs.has_children,
            "pet_friendly": prefs.pet_friendly,
        }
    
    @property
    def weather_preferences(self) -> Dict[str, Any]:
        """Get weather-based preferences."""
        prefs = self._cache.get("contextual_prefs")
        return prefs.weather_preferences if prefs and prefs.weather_preferences else {}
    
    # ── Confidence Context ──────────────────────────────────────────
    
    @property
    def confidence_scores(self) -> Dict[str, float]:
        """Get multi-dimensional confidence scores."""
        profile = self._cache.get("confidence_profile")
        if not profile:
            return self._default_confidence_scores()
        
        return {
            "overall": float(profile.overall_confidence or 0),
            "fit": float(profile.fit_confidence or 0),
            "style_alignment": float(profile.style_alignment or 0),
            "budget_comfort": float(profile.budget_comfort or 0),
            "experimentation": float(profile.experimentation_level or 0),
            "wardrobe_compatibility": float(profile.wardrobe_compatibility or 0),
            "occasion_readiness": float(profile.occasion_readiness or 0),
            "consistency": float(profile.consistency_score or 0),
            "engagement": float(profile.engagement_score or 0),
        }
    
    @property
    def earned_badges(self) -> List[str]:
        """Get earned confidence badges."""
        profile = self._cache.get("confidence_profile")
        return profile.earned_badges if profile and profile.earned_badges else []
    
    # ── Signal Aggregation ──────────────────────────────────────────
    
    @property
    def recent_signals(self) -> List[Dict[str, Any]]:
        """Get recent behavior signals."""
        signals = self._cache.get("recent_signals", [])
        return [
            {
                "type": s.signal_type,
                "entity_type": s.entity_type,
                "entity_id": s.entity_id,
                "weight": float(s.weight or 0),
                "context": s.context or {},
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in signals
        ]
    
    def aggregate_signals_by_category(self) -> Dict[str, float]:
        """Aggregate signals by category with decay."""
        signals = self._cache.get("recent_signals", [])
        aggregated = defaultdict(float)
        
        now = datetime.now(timezone.utc)
        
        for signal in signals:
            category = signal.signal_type
            weight = float(signal.weight or 0.1)
            
            # Apply time decay
            if signal.created_at:
                age_days = (now - signal.created_at).days
                decay_days = SIGNAL_WEIGHTS.get("decay_days", {}).get(category, 60)
                if decay_days:
                    decay_factor = max(0, 1 - (age_days / decay_days))
                    weight *= decay_factor
            
            aggregated[category] += weight
        
        return dict(aggregated)
    
    # ── Style Evolution ─────────────────────────────────────────────
    
    @property
    def style_evolution_events(self) -> List[Dict[str, Any]]:
        """Get style evolution events."""
        events = self._cache.get("style_evolution", [])
        return [
            {
                "event_type": e.event_type,
                "previous_value": e.previous_value,
                "new_value": e.new_value,
                "trigger_source": e.trigger_source,
                "confidence_delta": float(e.confidence_delta or 0),
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]
    
    # ── Composite Contexts ──────────────────────────────────────────
    
    def get_tryon_context(self) -> Dict[str, Any]:
        """Get context optimized for virtual try-on."""
        self.load()
        return {
            "user_id": self.user_id,
            "body": {
                "measurements": self.body_measurements,
                "shape": self.body_shape,
                "sizes": self.size_profile,
                "fit_issues": self.fit_issues,
            },
            "style": {
                "fit_preference": self.fit_preference,
                "colors": self.color_profile,
                "archetype": self.archetype,
            },
            "confidence": {
                "fit_confidence": self.confidence_scores.get("fit", 0),
                "style_alignment": self.confidence_scores.get("style_alignment", 0),
            },
            "signals": {
                "tryon_count": len([s for s in self.recent_signals if s["type"] == "try_on"]),
                "purchase_count": len([s for s in self.recent_signals if s["type"] == "purchase"]),
            },
        }
    
    def get_styling_context(self) -> Dict[str, Any]:
        """Get context optimized for AI styling."""
        self.load()
        return {
            "user_id": self.user_id,
            "style": {
                "vector": self.style_vector,
                "archetype": self.archetype,
                "colors": self.color_profile,
                "patterns": self.pattern_preferences,
            },
            "body": {
                "shape": self.body_shape,
                "sizes": self.size_profile,
            },
            "preferences": {
                "brands": {
                    "preferred": self.preferred_brands,
                    "avoided": self.avoided_brands,
                },
                "occasions": self.occasion_weights,
                "lifestyle": self.lifestyle_context,
            },
            "budget": self.budget_limits,
            "confidence": self.confidence_scores,
            "signal_aggregation": self.aggregate_signals_by_category(),
        }
    
    def get_commerce_context(self) -> Dict[str, Any]:
        """Get context optimized for commerce operations."""
        self.load()
        return {
            "user_id": self.user_id,
            "budget": self.budget_limits,
            "brands": {
                "affinities": self.brand_affinities,
                "preferred": self.preferred_brands,
                "avoided": self.avoided_brands,
            },
            "confidence": {
                "overall": self.confidence_scores.get("overall", 0),
                "budget_comfort": self.confidence_scores.get("budget_comfort", 0),
            },
            "signals": {
                "purchase_count": len([s for s in self.recent_signals if s["type"] == "purchase"]),
                "return_count": len([s for s in self.recent_signals if s["type"] == "return"]),
                "cart_abandon_count": len([s for s in self.recent_signals if s["type"] == "cart_abandon"]),
            },
        }
    
    def get_wardrobe_context(self) -> Dict[str, Any]:
        """Get context optimized for wardrobe operations."""
        self.load()
        return {
            "user_id": self.user_id,
            "style": {
                "archetype": self.archetype,
                "colors": self.color_profile,
                "patterns": self.pattern_preferences,
            },
            "lifestyle": self.lifestyle_context,
            "weather": self.weather_preferences,
            "confidence": {
                "wardrobe_compatibility": self.confidence_scores.get("wardrobe_compatibility", 0),
                "style_alignment": self.confidence_scores.get("style_alignment", 0),
            },
        }
    
    # ── Defaults ────────────────────────────────────────────────────
    
    def _default_style_vector(self) -> Dict[str, float]:
        return {
            "classic": 0.5, "trendy": 0.5, "minimalist": 0.5, "maximalist": 0.5,
            "feminine": 0.5, "masculine": 0.5, "edgy": 0.5, "romantic": 0.5,
        }
    
    def _default_confidence_scores(self) -> Dict[str, float]:
        return {
            "overall": 0, "fit": 0, "style_alignment": 0, "budget_comfort": 0,
            "experimentation": 0, "wardrobe_compatibility": 0, "occasion_readiness": 0,
            "consistency": 0, "engagement": 0,
        }
    
    # ── Serialization ───────────────────────────────────────────────
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize full context for caching or API response."""
        self.load()
        return {
            "user_id": self.user_id,
            "style": {
                "vector": self.style_vector,
                "archetype": self.archetype,
                "colors": self.color_profile,
                "patterns": self.pattern_preferences,
                "fit_preference": self.fit_preference,
            },
            "body": {
                "measurements": self.body_measurements,
                "shape": self.body_shape,
                "sizes": self.size_profile,
                "fit_issues": self.fit_issues,
            },
            "budget": self.budget_limits,
            "brands": {
                "affinities": self.brand_affinities,
                "preferred": self.preferred_brands,
                "avoided": self.avoided_brands,
            },
            "context": {
                "occasions": self.occasion_weights,
                "lifestyle": self.lifestyle_context,
                "weather": self.weather_preferences,
            },
            "confidence": self.confidence_scores,
            "badges": self.earned_badges,
            "signal_summary": self.aggregate_signals_by_category(),
            "evolution": self.style_evolution_events[:5],  # Last 5 events
        }


# ── Unified Intelligence Service ───────────────────────────────────────

class UnifiedIntelligenceService:
    """
    Central service for all AI intelligence operations.
    
    Provides:
    - Unified context retrieval
    - Signal tracking with proper categorization
    - Cross-feature signal propagation
    - Confidence recalculation triggers
    """
    
    def __init__(self, db: Session):
        self._db = db
    
    def get_context(self, user_id: str) -> UnifiedUserContext:
        """Get unified user context."""
        return UnifiedUserContext(user_id, self._db).load()
    
    def track_signal(
        self,
        user_id: str,
        category: SignalCategory,
        entity_type: str,
        entity_id: str,
        context: Dict[str, Any] = None,
        weight_override: float = None,
    ) -> None:
        """Track a behavior signal with proper categorization."""
        weight = weight_override or SIGNAL_WEIGHTS.get(category, 0.1)
        
        # Calculate decay
        decay_days = SIGNAL_WEIGHTS.get("decay_days", {}).get(category)
        expires_at = None
        if decay_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=decay_days)
        
        signal = UserBehaviorSignal(
            user_id=user_id,
            signal_type=category.value,
            entity_type=entity_type,
            entity_id=entity_id,
            weight=Decimal(str(weight)),
            context=context or {},
            expires_at=expires_at,
        )
        
        self._db.add(signal)
        self._db.commit()
        
        logger.debug(
            "Tracked signal: user=%s, category=%s, entity=%s/%s, weight=%.2f",
            user_id, category.value, entity_type, entity_id, weight
        )
    
    def propagate_to_confidence(
        self,
        user_id: str,
        category: SignalCategory,
        impact: float,
    ) -> None:
        """Propagate signal impact to confidence scores."""
        from services.confidence_service import ConfidenceService
        
        confidence_service = ConfidenceService(self._db)
        
        # Map signal categories to confidence dimensions
        dimension_mapping = {
            SignalCategory.TRYON_COMPLETED: "fit_confidence",
            SignalCategory.FIT_CONFIDENCE: "fit_confidence",
            SignalCategory.OUTFIT_CREATED: "style_alignment",
            SignalCategory.RECOMMENDATION_FEEDBACK: "style_alignment",
            SignalCategory.PURCHASE_MADE: "budget_comfort",
            SignalCategory.BUDGET_LIMIT_SET: "budget_comfort",
            SignalCategory.WARDROBE_ITEM_WORN: "wardrobe_compatibility",
            SignalCategory.POST_SHARED: "engagement",
            SignalCategory.STYLIST_INTERACTION: "engagement",
        }
        
        dimension = dimension_mapping.get(category)
        if dimension:
            confidence_service.increment_dimension(user_id, dimension, impact)
        
        confidence_service.recalculate(user_id, trigger_event=category.value)
    
    def get_cross_feature_signals(
        self,
        user_id: str,
        features: List[str],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get signals filtered by feature groups."""
        feature_signal_types = {
            "identity": ["style_preference", "body_profile", "budget_preference", "brand_affinity"],
            "styling": ["stylist_interaction", "outfit_created", "recommendation_feedback", "style_score"],
            "tryon": ["tryon_completed", "fit_confidence", "pose_quality", "visual_realism", "size_prediction"],
            "wardrobe": ["wardrobe_item_added", "wardrobe_item_worn", "wardrobe_gap", "capsule_created"],
            "commerce": ["product_viewed", "product_wishlisted", "cart_abandoned", "purchase_made", "return_initiated"],
            "budget": ["budget_limit_set", "spending_pattern", "bnpl_used"],
            "social": ["post_shared", "post_voted", "follow_gained", "challenge_completed"],
        }
        
        result = {}
        for feature in features:
            signal_types = feature_signal_types.get(feature, [])
            signals = self._db.query(UserBehaviorSignal).filter(
                and_(
                    UserBehaviorSignal.user_id == user_id,
                    UserBehaviorSignal.signal_type.in_(signal_types)
                )
            ).order_by(UserBehaviorSignal.created_at.desc()).limit(50).all()
            
            result[feature] = [
                {
                    "type": s.signal_type,
                    "entity": f"{s.entity_type}/{s.entity_id}",
                    "weight": float(s.weight or 0),
                    "context": s.context,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in signals
            ]
        
        return result


def get_unified_intelligence(db: Session = Depends(get_db)) -> UnifiedIntelligenceService:
    """Factory function for unified intelligence service."""
    return UnifiedIntelligenceService(db)
