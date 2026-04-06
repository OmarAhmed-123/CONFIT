"""
CONFIT Backend — Confidence Service
===================================
Multi-dimensional confidence scoring engine.
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Dict, List
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.session import get_db

from models.profile_models import (
    UserConfidenceProfile,
    UserConfidenceHistory,
    UserBehaviorSignal,
    UserStyleProfile,
    UserBodyProfile,
    UserBudgetProfile,
    UserBrandAffinity,
    UserContextualPreference,
    ConfidenceProfileResponse,
    ConfidenceDimensions,
)

logger = logging.getLogger(__name__)


CONFIDENCE_WEIGHTS = {
    "fit_confidence": 0.15,
    "style_alignment": 0.15,
    "budget_comfort": 0.10,
    "experimentation_level": 0.10,
    "wardrobe_compatibility": 0.15,
    "occasion_readiness": 0.10,
    "consistency_score": 0.15,
    "engagement_score": 0.10,
}

BADGE_THRESHOLDS = {
    "style_seeker": {"overall": 10},
    "style_explorer": {"overall": 25},
    "style_confident": {"overall": 50},
    "style_master": {"overall": 75},
    "fit_expert": {"fit_confidence": 70},
    "budget_pro": {"budget_comfort": 70},
    "wardrobe_wizard": {"wardrobe_compatibility": 70},
    "trendsetter": {"experimentation_level": 70},
    "consistent_queen": {"consistency_score": 80},
    "engaged_stylist": {"engagement_score": 70},
}


class ConfidenceService:
    """Service for calculating and managing user confidence scores."""
    
    def __init__(self, db: Session):
        self._db = db
    
    def _ensure_profile(self, user_id: str) -> UserConfidenceProfile:
        profile = self._db.query(UserConfidenceProfile).filter_by(user_id=user_id).first()
        if not profile:
            profile = UserConfidenceProfile(user_id=user_id)
            self._db.add(profile)
            self._db.commit()
            self._db.refresh(profile)
        return profile
    
    def _calculate_fit_confidence(self, user_id: str) -> float:
        body = self._db.query(UserBodyProfile).filter_by(user_id=user_id).first()
        if not body or body.profile_status == "not_set":
            return 0.0
        
        score = 0.0
        
        if body.height_cm:
            score += 15
        if body.weight_kg:
            score += 10
        if body.body_shape:
            score += 20
        if body.size_tops:
            score += 15
        if body.size_bottoms:
            score += 15
        if body.size_dresses:
            score += 10
        if body.size_shoes:
            score += 10
        if body.brand_size_overrides:
            score += 5
        
        return min(score, 100.0)
    
    def _calculate_style_alignment(self, user_id: str) -> float:
        style = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        if not style:
            return 0.0
        
        score = 0.0
        
        if style.primary_archetype:
            score += 30
            if style.archetype_confidence and float(style.archetype_confidence) > 0.7:
                score += 10
        
        if style.preferred_colors and len(style.preferred_colors) > 0:
            score += 15
        if style.skin_undertone:
            score += 10
        if style.pattern_preferences:
            score += 10
        if style.fabric_preferences and len(style.fabric_preferences) > 0:
            score += 10
        if style.silhouette_preferences:
            score += 10
        if style.fit_preference:
            score += 5
        
        return min(score, 100.0)
    
    def _calculate_budget_comfort(self, user_id: str) -> float:
        budget = self._db.query(UserBudgetProfile).filter_by(user_id=user_id).first()
        if not budget:
            return 0.0
        
        score = 0.0
        
        if budget.per_item_min is not None and budget.per_item_max is not None:
            score += 40
        elif budget.per_item_max is not None:
            score += 25
        
        if budget.monthly_max:
            score += 20
        if budget.currency:
            score += 10
        if budget.price_sensitivity:
            sensitivity = float(budget.price_sensitivity)
            if 0.3 <= sensitivity <= 0.7:
                score += 20
            else:
                score += 10
        
        return min(score, 100.0)
    
    def _calculate_experimentation_level(self, user_id: str) -> float:
        style = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        signals = self._db.query(UserBehaviorSignal).filter_by(user_id=user_id).all()
        
        score = 0.0
        
        if style:
            dims = [
                float(style.style_trendy or 0.5),
                float(style.style_edgy or 0.5),
                float(style.style_maximalist or 0.5),
            ]
            avg_dim = sum(dims) / len(dims)
            score += avg_dim * 40
        
        unique_categories = set()
        unique_brands = set()
        for s in signals:
            if s.signal_type in ["try_on", "outfit_create", "purchase"]:
                if s.entity_type == "category":
                    unique_categories.add(s.entity_id)
                elif s.entity_type == "brand":
                    unique_brands.add(s.entity_id)
        
        score += min(len(unique_categories) * 5, 30)
        score += min(len(unique_brands) * 3, 30)
        
        return min(score, 100.0)
    
    def _calculate_wardrobe_compatibility(self, user_id: str) -> float:
        signals = self._db.query(UserBehaviorSignal).filter_by(user_id=user_id).all()
        
        outfit_creates = [s for s in signals if s.signal_type == "outfit_create"]
        outfit_saves = [s for s in signals if s.signal_type == "outfit_save"]
        
        score = 0.0
        
        score += min(len(outfit_creates) * 10, 40)
        score += min(len(outfit_saves) * 15, 40)
        
        context = self._db.query(UserContextualPreference).filter_by(user_id=user_id).first()
        if context and context.occasion_weights:
            occasions = len(context.occasion_weights)
            score += min(occasions * 5, 20)
        
        return min(score, 100.0)
    
    def _calculate_occasion_readiness(self, user_id: str) -> float:
        context = self._db.query(UserContextualPreference).filter_by(user_id=user_id).first()
        if not context:
            return 0.0
        
        score = 0.0
        
        if context.work_environment:
            score += 20
        if context.activity_level:
            score += 15
        if context.occasion_weights:
            occasions = context.occasion_weights
            score += min(len(occasions) * 10, 40)
        
        if context.weather_preferences:
            score += 15
        if context.climate_zone:
            score += 10
        
        return min(score, 100.0)
    
    def _calculate_consistency_score(self, user_id: str) -> float:
        history = self._db.query(UserConfidenceHistory).filter_by(user_id=user_id).order_by(
            UserConfidenceHistory.created_at.desc()
        ).limit(10).all()
        
        if len(history) < 2:
            return 50.0
        
        scores = [float(h.overall_score) for h in history]
        
        if len(scores) < 2:
            return 50.0
        
        variance = sum((s - sum(scores) / len(scores)) ** 2 for s in scores) / len(scores)
        consistency = max(0, 100 - variance)
        
        return min(consistency, 100.0)
    
    def _calculate_engagement_score(self, user_id: str) -> float:
        signals = self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.user_id == user_id,
            UserBehaviorSignal.created_at >= datetime.now(timezone.utc) - timedelta(days=30)
        ).all()
        
        score = 0.0
        
        signal_weights = {
            "view": 1,
            "view_long": 2,
            "wishlist_add": 3,
            "try_on": 4,
            "try_on_save": 5,
            "outfit_create": 5,
            "outfit_save": 4,
            "purchase": 6,
            "share": 3,
            "feedback": 4,
        }
        
        weighted_sum = sum(signal_weights.get(s.signal_type, 1) for s in signals)
        score = min(weighted_sum, 100)
        
        return score
    
    def _determine_badges(self, profile: UserConfidenceProfile) -> List[str]:
        badges = []
        
        for badge_name, thresholds in BADGE_THRESHOLDS.items():
            for dimension, threshold in thresholds.items():
                if dimension == "overall":
                    if float(profile.overall_confidence or 0) >= threshold:
                        badges.append(badge_name)
                else:
                    dim_value = getattr(profile, dimension, None)
                    if dim_value and float(dim_value) >= threshold:
                        badges.append(badge_name)
        
        return list(set(badges))
    
    def recalculate(self, user_id: str, trigger_event: str = None) -> ConfidenceProfileResponse:
        profile = self._ensure_profile(user_id)
        
        old_overall = float(profile.overall_confidence or 0)
        old_dimensions = {
            "fit_confidence": float(profile.fit_confidence or 0),
            "style_alignment": float(profile.style_alignment or 0),
            "budget_comfort": float(profile.budget_comfort or 0),
            "experimentation_level": float(profile.experimentation_level or 0),
            "wardrobe_compatibility": float(profile.wardrobe_compatibility or 0),
            "occasion_readiness": float(profile.occasion_readiness or 0),
            "consistency_score": float(profile.consistency_score or 0),
            "engagement_score": float(profile.engagement_score or 0),
        }
        
        profile.fit_confidence = Decimal(str(self._calculate_fit_confidence(user_id)))
        profile.style_alignment = Decimal(str(self._calculate_style_alignment(user_id)))
        profile.budget_comfort = Decimal(str(self._calculate_budget_comfort(user_id)))
        profile.experimentation_level = Decimal(str(self._calculate_experimentation_level(user_id)))
        profile.wardrobe_compatibility = Decimal(str(self._calculate_wardrobe_compatibility(user_id)))
        profile.occasion_readiness = Decimal(str(self._calculate_occasion_readiness(user_id)))
        profile.consistency_score = Decimal(str(self._calculate_consistency_score(user_id)))
        profile.engagement_score = Decimal(str(self._calculate_engagement_score(user_id)))
        
        overall = (
            float(profile.fit_confidence) * CONFIDENCE_WEIGHTS["fit_confidence"] +
            float(profile.style_alignment) * CONFIDENCE_WEIGHTS["style_alignment"] +
            float(profile.budget_comfort) * CONFIDENCE_WEIGHTS["budget_comfort"] +
            float(profile.experimentation_level) * CONFIDENCE_WEIGHTS["experimentation_level"] +
            float(profile.wardrobe_compatibility) * CONFIDENCE_WEIGHTS["wardrobe_compatibility"] +
            float(profile.occasion_readiness) * CONFIDENCE_WEIGHTS["occasion_readiness"] +
            float(profile.consistency_score) * CONFIDENCE_WEIGHTS["consistency_score"] +
            float(profile.engagement_score) * CONFIDENCE_WEIGHTS["engagement_score"]
        )
        
        profile.overall_confidence = Decimal(str(min(overall, 100.0)))
        
        profile.earned_badges = self._determine_badges(profile)
        
        delta = float(profile.overall_confidence) - old_overall
        if abs(delta) > 0.5 or trigger_event:
            history = UserConfidenceHistory(
                user_id=user_id,
                overall_score=profile.overall_confidence,
                dimensions={
                    "fit_confidence": float(profile.fit_confidence),
                    "style_alignment": float(profile.style_alignment),
                    "budget_comfort": float(profile.budget_comfort),
                    "experimentation_level": float(profile.experimentation_level),
                    "wardrobe_compatibility": float(profile.wardrobe_compatibility),
                    "occasion_readiness": float(profile.occasion_readiness),
                    "consistency_score": float(profile.consistency_score),
                    "engagement_score": float(profile.engagement_score),
                },
                delta=Decimal(str(delta)),
                trigger_event=trigger_event,
            )
            self._db.add(history)
        
        self._db.commit()
        self._db.refresh(profile)
        
        return self.get_profile(user_id)
    
    def get_profile(self, user_id: str) -> ConfidenceProfileResponse:
        profile = self._ensure_profile(user_id)
        
        return ConfidenceProfileResponse(
            id=str(profile.id),
            user_id=str(profile.user_id),
            overall_confidence=float(profile.overall_confidence or 0),
            dimensions=ConfidenceDimensions(
                fit_confidence=float(profile.fit_confidence or 0),
                style_alignment=float(profile.style_alignment or 0),
                budget_comfort=float(profile.budget_comfort or 0),
                experimentation_level=float(profile.experimentation_level or 0),
                wardrobe_compatibility=float(profile.wardrobe_compatibility or 0),
                occasion_readiness=float(profile.occasion_readiness or 0),
                consistency_score=float(profile.consistency_score or 0),
                engagement_score=float(profile.engagement_score or 0),
            ),
            earned_badges=profile.earned_badges or [],
            growth_rate=float(profile.growth_rate or 0),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
    
    def get_history(self, user_id: str, limit: int = 30) -> List[dict]:
        history = self._db.query(UserConfidenceHistory).filter_by(user_id=user_id).order_by(
            UserConfidenceHistory.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": str(h.id),
                "overall_score": float(h.overall_score),
                "dimensions": h.dimensions,
                "delta": float(h.delta) if h.delta else None,
                "trigger_event": h.trigger_event,
                "created_at": h.created_at.isoformat(),
            }
            for h in history
        ]
    
    def update_growth_rate(self, user_id: str) -> float:
        profile = self._ensure_profile(user_id)
        
        history = self._db.query(UserConfidenceHistory).filter_by(user_id=user_id).order_by(
            UserConfidenceHistory.created_at.desc()
        ).limit(7).all()
        
        if len(history) < 2:
            profile.growth_rate = Decimal("0.0")
            self._db.commit()
            return 0.0
        
        deltas = [float(h.delta) for h in history if h.delta is not None]
        if not deltas:
            profile.growth_rate = Decimal("0.0")
            self._db.commit()
            return 0.0
        
        avg_growth = sum(deltas) / len(deltas)
        profile.growth_rate = Decimal(str(avg_growth))
        self._db.commit()
        
        return avg_growth


def get_confidence_service(db: Session = Depends(get_db)) -> ConfidenceService:
    """Factory function for ConfidenceService dependency injection."""
    return ConfidenceService(db)
