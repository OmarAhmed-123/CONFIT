"""
CONFIT Backend — Identity Intelligence Service
=============================================
Unified identity layer connecting all feature groups.
Single source of truth for user intelligence across the platform.

Integrates:
- GROUP 1: User Identity & Profile
- GROUP 2: Virtual Try-On
- GROUP 3: AI Styling Engine
- GROUP 4: Virtual Wardrobe
- GROUP 5: Marketplace & Commerce
- GROUP 6: Budget Intelligence
- GROUP 7: Social & Community
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
    UserConfidenceProfile,
    UserConfidenceHistory,
    UserBehaviorSignal,
    UserStyleEvolution,
    UserOnboardingSession,
)
from services.profile_service import ProfileService
from services.confidence_service import ConfidenceService
from services.behavior_signal_service import BehaviorSignalService

logger = logging.getLogger(__name__)


class IdentityIntelligenceService:
    """
    Central identity intelligence hub.
    
    Provides unified access to user identity data for all feature groups.
    Ensures consistent personalization across the entire platform.
    """
    
    def __init__(self, db: Session):
        self._db = db
        self._profile_service = ProfileService(db)
        self._confidence_service = ConfidenceService(db)
        self._signal_service = BehaviorSignalService(db)
    
    # ── Unified Identity Retrieval ─────────────────────────────────────
    
    def get_full_identity(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieve complete user identity for cross-feature personalization.
        Single source of truth for all user data.
        """
        style = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        body = self._db.query(UserBodyProfile).filter_by(user_id=user_id).first()
        budget = self._db.query(UserBudgetProfile).filter_by(user_id=user_id).first()
        context = self._db.query(UserContextualPreference).filter_by(user_id=user_id).first()
        confidence = self._db.query(UserConfidenceProfile).filter_by(user_id=user_id).first()
        brands = self._db.query(UserBrandAffinity).filter_by(user_id=user_id).all()
        onboarding = self._db.query(UserOnboardingSession).filter_by(user_id=user_id).first()
        
        return {
            "user_id": user_id,
            "style_identity": self._serialize_style(style) if style else None,
            "body_identity": self._serialize_body(body) if body else None,
            "budget_identity": self._serialize_budget(budget) if budget else None,
            "context_identity": self._serialize_context(context) if context else None,
            "confidence_identity": self._serialize_confidence(confidence) if confidence else None,
            "brand_affinities": [self._serialize_brand(b) for b in brands],
            "onboarding_status": {
                "completed": onboarding.completed_at is not None if onboarding else False,
                "phase": onboarding.current_phase if onboarding else 0,
            } if onboarding else None,
            "identity_completeness": self._calculate_identity_completeness(
                style, body, budget, context, brands
            ),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    
    def get_styling_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get identity context optimized for styling operations.
        Used by: Virtual Stylist, Outfit Builder, AI Brain
        """
        style = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        body = self._db.query(UserBodyProfile).filter_by(user_id=user_id).first()
        context = self._db.query(UserContextualPreference).filter_by(user_id=user_id).first()
        brands = self._db.query(UserBrandAffinity).filter_by(user_id=user_id).all()
        
        return {
            "style_vector": {
                "archetype": style.primary_archetype if style else None,
                "dimensions": {
                    "classic": float(style.style_classic) if style and style.style_classic else 0.5,
                    "trendy": float(style.style_trendy) if style and style.style_trendy else 0.5,
                    "minimalist": float(style.style_minimalist) if style and style.style_minimalist else 0.5,
                    "maximalist": float(style.style_maximalist) if style and style.style_maximalist else 0.5,
                    "feminine": float(style.style_feminine) if style and style.style_feminine else 0.5,
                    "masculine": float(style.style_masculine) if style and style.style_masculine else 0.5,
                    "edgy": float(style.style_edgy) if style and style.style_edgy else 0.5,
                    "romantic": float(style.style_romantic) if style and style.style_romantic else 0.5,
                } if style else {},
                "colors": {
                    "preferred": style.preferred_colors or [],
                    "avoided": style.avoided_colors or [],
                    "undertone": style.skin_undertone,
                } if style else {},
                "patterns": style.pattern_preferences if style else {},
                "silhouettes": style.silhouette_preferences if style else {},
                "fit_preference": style.fit_preference if style else "regular",
            },
            "body_context": {
                "shape": body.body_shape if body else None,
                "sizes": {
                    "tops": body.size_tops if body else None,
                    "bottoms": body.size_bottoms if body else None,
                    "dresses": body.size_dresses if body else None,
                    "shoes": body.size_shoes if body else None,
                } if body else {},
                "fit_issues": body.fit_issues if body else [],
                "measurements_available": body.profile_status != "not_set" if body else False,
            },
            "occasion_context": context.occasion_weights if context else {},
            "lifestyle_context": {
                "work_environment": context.work_environment if context else None,
                "activity_level": context.activity_level if context else None,
                "climate_zone": context.climate_zone if context else None,
            } if context else {},
            "brand_preferences": {
                "top_brands": [b.brand_id for b in brands if float(b.affinity_score or 0.5) > 0.6],
                "avoided_brands": [b.brand_id for b in brands if float(b.affinity_score or 0.5) < 0.3],
            },
        }
    
    def get_tryon_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get identity context optimized for virtual try-on.
        Used by: Virtual Try-On, Digital Twin
        """
        body = self._db.query(UserBodyProfile).filter_by(user_id=user_id).first()
        style = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        
        return {
            "body_measurements": {
                "height_cm": body.height_cm if body else None,
                "weight_kg": body.weight_kg if body else None,
                "chest_cm": body.chest_cm if body else None,
                "waist_cm": body.waist_cm if body else None,
                "hips_cm": body.hips_cm if body else None,
                "inseam_cm": body.inseam_cm if body else None,
            } if body and body.profile_status != "not_set" else {},
            "size_recommendations": {
                "tops": body.size_tops if body else None,
                "bottoms": body.size_bottoms if body else None,
                "dresses": body.size_dresses if body else None,
                "shoes": body.size_shoes if body else None,
                "brand_overrides": body.brand_size_overrides if body else {},
            } if body else {},
            "fit_preferences": {
                "preference": style.fit_preference if style else "regular",
                "issues": body.fit_issues if body else [],
            },
            "skin_undertone": style.skin_undertone if style else None,
            "preferred_colors": style.preferred_colors if style else [],
        }
    
    def get_commerce_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get identity context optimized for commerce operations.
        Used by: Orders, Payments, BNPL, Cart Intelligence
        """
        budget = self._db.query(UserBudgetProfile).filter_by(user_id=user_id).first()
        brands = self._db.query(UserBrandAffinity).filter_by(user_id=user_id).all()
        confidence = self._db.query(UserConfidenceProfile).filter_by(user_id=user_id).first()
        
        signals = self._signal_service.get_preference_summary(user_id)
        
        return {
            "budget_context": {
                "per_item_range": {
                    "min": float(budget.per_item_min) if budget and budget.per_item_min else None,
                    "max": float(budget.per_item_max) if budget and budget.per_item_max else None,
                },
                "monthly_max": float(budget.monthly_max) if budget and budget.monthly_max else None,
                "currency": budget.currency if budget else "USD",
                "price_sensitivity": float(budget.price_sensitivity) if budget and budget.price_sensitivity else 0.5,
                "investment_willing": budget.investment_willing if budget else False,
            },
            "brand_affinities": {
                "preferred": [{"brand": b.brand_id, "score": float(b.affinity_score)} for b in brands if float(b.affinity_score or 0.5) > 0.6],
                "neutral": [{"brand": b.brand_id, "score": float(b.affinity_score)} for b in brands if 0.3 <= float(b.affinity_score or 0.5) <= 0.6],
                "avoided": [b.brand_id for b in brands if float(b.affinity_score or 0.5) < 0.3],
            },
            "confidence_metrics": {
                "overall": float(confidence.overall_confidence) if confidence else 0,
                "budget_comfort": float(confidence.budget_comfort) if confidence else 0,
                "engagement": float(confidence.engagement_score) if confidence else 0,
            },
            "behavioral_price_data": signals.get("price_behavior", {}),
        }
    
    def get_wardrobe_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get identity context optimized for wardrobe operations.
        Used by: Wardrobe Service, Wardrobe Analytics
        """
        style = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        context = self._db.query(UserContextualPreference).filter_by(user_id=user_id).first()
        confidence = self._db.query(UserConfidenceProfile).filter_by(user_id=user_id).first()
        
        return {
            "style_profile": {
                "archetype": style.primary_archetype if style else None,
                "colors": {
                    "preferred": style.preferred_colors if style else [],
                    "avoided": style.avoided_colors if style else [],
                },
                "patterns": style.pattern_preferences if style else {},
            },
            "lifestyle": {
                "work_environment": context.work_environment if context else None,
                "activity_level": context.activity_level if context else None,
                "has_children": context.has_children if context else None,
                "pet_friendly": context.pet_friendly if context else None,
            } if context else {},
            "climate": {
                "zone": context.climate_zone if context else None,
                "preferences": context.weather_preferences if context else {},
            } if context else {},
            "confidence": {
                "wardrobe_compatibility": float(confidence.wardrobe_compatibility) if confidence else 0,
                "style_alignment": float(confidence.style_alignment) if confidence else 0,
                "experimentation": float(confidence.experimentation_level) if confidence else 0,
            } if confidence else {},
        }
    
    def get_social_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get identity context optimized for social features.
        Used by: Social Router, Challenges, Community
        """
        style = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        context = self._db.query(UserContextualPreference).filter_by(user_id=user_id).first()
        confidence = self._db.query(UserConfidenceProfile).filter_by(user_id=user_id).first()
        
        return {
            "style_identity": {
                "archetype": style.primary_archetype if style else None,
                "secondary": style.secondary_archetypes if style else [],
            },
            "style_icons": context.style_icons if context else [],
            "cultural_influences": context.cultural_influences if context else [],
            "confidence_level": float(confidence.overall_confidence) if confidence else 0,
            "badges": confidence.earned_badges if confidence else [],
            "shareable_profile": {
                "archetype": style.primary_archetype if style else None,
                "confidence": float(confidence.overall_confidence) if confidence else 0,
                "top_colors": (style.preferred_colors or [])[:3] if style else [],
            },
        }
    
    # ── Cross-Feature Signal Propagation ─────────────────────────────────
    
    def propagate_style_change(
        self,
        user_id: str,
        change_type: str,
        old_value: Any,
        new_value: Any,
        source: str,
    ) -> Dict[str, Any]:
        """
        Propagate style changes to all dependent systems.
        Ensures consistency across Try-On, Styling, Wardrobe, etc.
        """
        evolution = UserStyleEvolution(
            user_id=user_id,
            event_type=change_type,
            previous_value=old_value,
            new_value=new_value,
            trigger_source=source,
        )
        self._db.add(evolution)
        self._db.commit()
        
        affected_systems = self._get_affected_systems(change_type)
        
        self._confidence_service.recalculate(user_id, trigger_event=f"style_{change_type}")
        
        return {
            "propagated": True,
            "affected_systems": affected_systems,
            "evolution_id": str(evolution.id),
        }
    
    def sync_wardrobe_to_identity(self, user_id: str) -> Dict[str, Any]:
        """
        Sync wardrobe data back to identity profile.
        Creates implicit preferences from wardrobe composition.
        """
        signals = self._signal_service.get_preference_summary(user_id)
        
        style = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        if not style:
            return {"synced": False, "reason": "no_style_profile"}
        
        updates = {}
        
        if signals.get("colors"):
            existing = set(style.preferred_colors or [])
            implicit = set(signals["colors"].keys())
            new_colors = list(existing | implicit)[:10]
            if new_colors != style.preferred_colors:
                updates["preferred_colors"] = new_colors
                style.preferred_colors = new_colors
        
        if signals.get("brands"):
            for brand, score in signals["brands"].items():
                existing = self._db.query(UserBrandAffinity).filter_by(
                    user_id=user_id, brand_id=brand
                ).first()
                
                if not existing:
                    affinity = UserBrandAffinity(
                        user_id=user_id,
                        brand_id=brand,
                        affinity_score=Decimal(str(min(score / 5, 1.0))),
                        affinity_source="implicit_wardrobe",
                    )
                    self._db.add(affinity)
        
        if updates:
            self._db.commit()
            self._confidence_service.recalculate(user_id, trigger_event="wardrobe_sync")
        
        return {
            "synced": True,
            "updates": updates,
            "implicit_brands_added": len(signals.get("brands", {})),
        }
    
    def sync_purchase_to_identity(
        self,
        user_id: str,
        order_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Sync purchase data to identity profile.
        Updates brand affinities, budget patterns, style preferences.
        """
        items = order_data.get("items", [])
        total = order_data.get("total", 0)
        
        for item in items:
            brand = item.get("brand")
            if brand:
                existing = self._db.query(UserBrandAffinity).filter_by(
                    user_id=user_id, brand_id=brand
                ).first()
                
                if existing:
                    current = float(existing.affinity_score or 0.5)
                    new_score = min(current + 0.1, 1.0)
                    existing.affinity_score = Decimal(str(new_score))
                else:
                    affinity = UserBrandAffinity(
                        user_id=user_id,
                        brand_id=brand,
                        affinity_score=Decimal("0.7"),
                        affinity_source="implicit_purchase",
                    )
                    self._db.add(affinity)
            
            category = item.get("category")
            color = item.get("color")
            if category and color:
                self._signal_service.track(
                    user_id=user_id,
                    signal_type="purchase",
                    entity_type="product",
                    entity_id=item.get("productId", ""),
                    context={
                        "category": category,
                        "color": color,
                        "price": item.get("price", 0),
                        "brand": brand,
                    },
                )
        
        budget = self._db.query(UserBudgetProfile).filter_by(user_id=user_id).first()
        if budget:
            current_avg = float(budget.per_item_max or 0)
            item_avg = total / len(items) if items else 0
            if item_avg > current_avg * 1.2:
                budget.price_sensitivity = Decimal(str(max(0, float(budget.price_sensitivity or 0.5) - 0.1)))
        
        self._db.commit()
        self._confidence_service.recalculate(user_id, trigger_event="purchase")
        
        return {
            "synced": True,
            "brands_updated": len([i for i in items if i.get("brand")]),
            "signals_tracked": len(items),
        }
    
    # ── Identity Completeness & Quality ─────────────────────────────────
    
    def get_identity_gaps(self, user_id: str) -> Dict[str, Any]:
        """
        Identify missing identity data that affects personalization quality.
        Returns prioritized recommendations for profile completion.
        """
        completeness = self._profile_service.get_completeness(user_id)
        
        gaps = {
            "critical": [],
            "important": [],
            "optional": [],
        }
        
        for field in completeness.missing_fields:
            if field.startswith("style."):
                gaps["critical"].append({
                    "field": field,
                    "impact": "Reduces styling accuracy by 15-25%",
                    "action": "Complete style quiz",
                })
            elif field.startswith("body."):
                gaps["important"].append({
                    "field": field,
                    "impact": "Affects fit recommendations and try-on accuracy",
                    "action": "Add body measurements",
                })
            elif field.startswith("budget."):
                gaps["important"].append({
                    "field": field,
                    "impact": "Price filtering less accurate",
                    "action": "Set budget preferences",
                })
            elif field.startswith("context."):
                gaps["optional"].append({
                    "field": field,
                    "impact": "Occasion-based styling less personalized",
                    "action": "Complete lifestyle profile",
                })
            elif field.startswith("brands."):
                gaps["optional"].append({
                    "field": field,
                    "impact": "Brand recommendations less relevant",
                    "action": "Add favorite brands",
                })
        
        return {
            "overall_score": completeness.overall_score,
            "gaps": gaps,
            "suggestions": completeness.suggestions,
        }
    
    def get_identity_health_score(self, user_id: str) -> Dict[str, Any]:
        """
        Calculate overall identity health for AI readiness.
        Determines if user has enough data for quality personalization.
        """
        style = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        signals = self._db.query(UserBehaviorSignal).filter_by(user_id=user_id).count()
        confidence = self._db.query(UserConfidenceProfile).filter_by(user_id=user_id).first()
        
        scores = {
            "profile_richness": 0.0,
            "behavioral_depth": 0.0,
            "confidence_level": 0.0,
            "freshness": 0.0,
        }
        
        if style:
            richness = 0
            if style.primary_archetype:
                richness += 25
            if style.preferred_colors and len(style.preferred_colors) > 0:
                richness += 15
            if style.skin_undertone:
                richness += 10
            if style.pattern_preferences:
                richness += 10
            if style.silhouette_preferences:
                richness += 10
            scores["profile_richness"] = min(richness, 100)
        
        signal_score = min(signals * 2, 100)
        scores["behavioral_depth"] = signal_score
        
        if confidence:
            scores["confidence_level"] = float(confidence.overall_confidence or 0)
        
        if style and style.updated_at:
            days_since = (datetime.now(timezone.utc) - style.updated_at).days
            freshness = max(0, 100 - (days_since * 2))
            scores["freshness"] = freshness
        
        overall = sum(scores.values()) / len(scores)
        
        ai_ready = overall >= 50 and scores["profile_richness"] >= 30
        
        return {
            "overall_health": overall,
            "dimensions": scores,
            "ai_ready": ai_ready,
            "recommendations": self._get_health_recommendations(scores),
        }
    
    # ── Private Helpers ─────────────────────────────────────────────────
    
    def _serialize_style(self, profile: UserStyleProfile) -> Dict[str, Any]:
        return {
            "archetype": profile.primary_archetype,
            "archetype_confidence": float(profile.archetype_confidence or 0),
            "dimensions": {
                "classic": float(profile.style_classic or 0.5),
                "trendy": float(profile.style_trendy or 0.5),
                "minimalist": float(profile.style_minimalist or 0.5),
                "maximalist": float(profile.style_maximalist or 0.5),
                "feminine": float(profile.style_feminine or 0.5),
                "masculine": float(profile.style_masculine or 0.5),
                "edgy": float(profile.style_edgy or 0.5),
                "romantic": float(profile.style_romantic or 0.5),
            },
            "colors": {
                "preferred": profile.preferred_colors or [],
                "avoided": profile.avoided_colors or [],
                "undertone": profile.skin_undertone,
            },
            "completeness": float(profile.profile_completeness or 0),
        }
    
    def _serialize_body(self, profile: UserBodyProfile) -> Dict[str, Any]:
        return {
            "status": profile.profile_status,
            "shape": profile.body_shape,
            "sizes": {
                "tops": profile.size_tops,
                "bottoms": profile.size_bottoms,
                "dresses": profile.size_dresses,
                "shoes": profile.size_shoes,
            },
            "has_measurements": profile.profile_status != "not_set",
        }
    
    def _serialize_budget(self, profile: UserBudgetProfile) -> Dict[str, Any]:
        return {
            "per_item_max": float(profile.per_item_max) if profile.per_item_max else None,
            "monthly_max": float(profile.monthly_max) if profile.monthly_max else None,
            "currency": profile.currency,
            "price_sensitivity": float(profile.price_sensitivity or 0.5),
        }
    
    def _serialize_context(self, pref: UserContextualPreference) -> Dict[str, Any]:
        return {
            "work_environment": pref.work_environment,
            "climate_zone": pref.climate_zone,
            "activity_level": pref.activity_level,
            "occasion_weights": pref.occasion_weights or {},
        }
    
    def _serialize_confidence(self, profile: UserConfidenceProfile) -> Dict[str, Any]:
        return {
            "overall": float(profile.overall_confidence or 0),
            "dimensions": {
                "fit": float(profile.fit_confidence or 0),
                "style": float(profile.style_alignment or 0),
                "budget": float(profile.budget_comfort or 0),
                "experimentation": float(profile.experimentation_level or 0),
                "wardrobe": float(profile.wardrobe_compatibility or 0),
                "occasion": float(profile.occasion_readiness or 0),
                "consistency": float(profile.consistency_score or 0),
                "engagement": float(profile.engagement_score or 0),
            },
            "badges": profile.earned_badges or [],
        }
    
    def _serialize_brand(self, affinity: UserBrandAffinity) -> Dict[str, Any]:
        return {
            "brand_id": affinity.brand_id,
            "score": float(affinity.affinity_score or 0.5),
            "source": affinity.affinity_source,
        }
    
    def _calculate_identity_completeness(
        self,
        style, body, budget, context, brands
    ) -> float:
        score = 0.0
        
        if style and style.primary_archetype:
            score += 20
        if style and style.preferred_colors:
            score += 10
        if body and body.profile_status != "not_set":
            score += 15
        if budget and budget.per_item_max:
            score += 15
        if context and context.work_environment:
            score += 10
        if context and context.climate_zone:
            score += 10
        if len(brands) > 0:
            score += min(len(brands) * 5, 20)
        
        return min(score, 100.0)
    
    def _get_affected_systems(self, change_type: str) -> List[str]:
        mapping = {
            "archetype_change": ["stylist", "outfit_builder", "recommendations", "wardrobe"],
            "color_preference": ["stylist", "try_on", "outfit_builder", "wardrobe"],
            "body_update": ["try_on", "fit_prediction", "size_recommendation"],
            "budget_update": ["commerce", "bnpl", "recommendations", "cart"],
            "brand_affinity": ["marketplace", "recommendations", "stylist"],
            "occasion_preference": ["stylist", "outfit_builder", "calendar"],
        }
        return mapping.get(change_type, ["all"])
    
    def _get_health_recommendations(self, scores: Dict[str, float]) -> List[str]:
        recs = []
        
        if scores["profile_richness"] < 30:
            recs.append("Complete your style profile for better recommendations")
        if scores["behavioral_depth"] < 20:
            recs.append("Interact with more items to improve personalization")
        if scores["confidence_level"] < 30:
            recs.append("Build your confidence by completing outfit challenges")
        if scores["freshness"] < 50:
            recs.append("Update your preferences to keep recommendations current")
        
        return recs


def get_identity_intelligence(db: Session = Depends(get_db)) -> IdentityIntelligenceService:
    return IdentityIntelligenceService(db)
