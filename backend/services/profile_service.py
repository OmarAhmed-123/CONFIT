"""
CONFIT Backend — Profile Service
================================
Service layer for user profile management.
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

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
    UserProfileAuditLog,
    UserOnboardingSession,
    StyleProfileCreate,
    StyleProfileResponse,
    StyleDimensions,
    BodyProfileCreate,
    BodyProfileResponse,
    BudgetProfileCreate,
    BudgetProfileResponse,
    BrandAffinityCreate,
    BrandAffinityResponse,
    ContextualPreferenceCreate,
    ContextualPreferenceResponse,
    ConfidenceProfileResponse,
    ConfidenceDimensions,
    BehaviorSignalCreate,
    OnboardingStatusResponse,
    ProfileCompletenessResponse,
    StyleArchetypeResult,
)

logger = logging.getLogger(__name__)


STYLE_ARCHETYPES = {
    "classic_chic": {"classic": 0.8, "minimalist": 0.6, "trendy": 0.3},
    "urban_edge": {"edgy": 0.8, "trendy": 0.7, "maximalist": 0.5},
    "bohemian_spirit": {"romantic": 0.7, "maximalist": 0.6, "trendy": 0.4},
    "modern_minimalist": {"minimalist": 0.9, "classic": 0.5, "edgy": 0.3},
    "romantic_feminine": {"romantic": 0.8, "feminine": 0.7, "classic": 0.4},
    "sport_luxe": {"edgy": 0.5, "minimalist": 0.5, "trendy": 0.6},
    "avant_garde": {"edgy": 0.9, "maximalist": 0.7, "trendy": 0.5},
    "preppy_polished": {"classic": 0.7, "minimalist": 0.4, "feminine": 0.4},
}

COMPLETENESS_WEIGHTS = {
    "style": {
        "primary_archetype": 15,
        "style_dimensions": 15,
        "preferred_colors": 5,
        "skin_undertone": 5,
    },
    "body": {
        "height_cm": 5,
        "body_shape": 5,
        "size_tops": 5,
        "size_bottoms": 5,
    },
    "budget": {
        "per_item_max": 10,
        "currency": 5,
    },
    "context": {
        "work_environment": 5,
        "climate_zone": 5,
        "activity_level": 5,
    },
    "brands": {
        "brand_affinities": 10,
    },
}


class ProfileService:
    """Service for managing user profiles."""
    
    def __init__(self, db: Session):
        self._db = db
    
    def _ensure_style_profile(self, user_id: str) -> UserStyleProfile:
        profile = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        if not profile:
            profile = UserStyleProfile(user_id=user_id)
            self._db.add(profile)
            self._db.commit()
            self._db.refresh(profile)
        return profile
    
    def _ensure_body_profile(self, user_id: str) -> UserBodyProfile:
        profile = self._db.query(UserBodyProfile).filter_by(user_id=user_id).first()
        if not profile:
            profile = UserBodyProfile(user_id=user_id)
            self._db.add(profile)
            self._db.commit()
            self._db.refresh(profile)
        return profile
    
    def _ensure_budget_profile(self, user_id: str) -> UserBudgetProfile:
        profile = self._db.query(UserBudgetProfile).filter_by(user_id=user_id).first()
        if not profile:
            profile = UserBudgetProfile(user_id=user_id)
            self._db.add(profile)
            self._db.commit()
            self._db.refresh(profile)
        return profile
    
    def _ensure_contextual_preference(self, user_id: str) -> UserContextualPreference:
        pref = self._db.query(UserContextualPreference).filter_by(user_id=user_id).first()
        if not pref:
            pref = UserContextualPreference(user_id=user_id)
            self._db.add(pref)
            self._db.commit()
            self._db.refresh(pref)
        return pref
    
    def _ensure_confidence_profile(self, user_id: str) -> UserConfidenceProfile:
        profile = self._db.query(UserConfidenceProfile).filter_by(user_id=user_id).first()
        if not profile:
            profile = UserConfidenceProfile(user_id=user_id)
            self._db.add(profile)
            self._db.commit()
            self._db.refresh(profile)
        return profile
    
    def _ensure_onboarding_session(self, user_id: str) -> UserOnboardingSession:
        session = self._db.query(UserOnboardingSession).filter_by(user_id=user_id).first()
        if not session:
            session = UserOnboardingSession(user_id=user_id)
            self._db.add(session)
            self._db.commit()
            self._db.refresh(session)
        return session
    
    def _log_audit(
        self,
        user_id: str,
        table_name: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        source: str,
        ip_address: str = None,
        user_agent: str = None,
    ) -> None:
        log = UserProfileAuditLog(
            user_id=user_id,
            table_name=table_name,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            change_source=source,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._db.add(log)
        self._db.commit()
    
    def _calculate_completeness(self, user_id: str) -> float:
        score = 0.0
        style = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        body = self._db.query(UserBodyProfile).filter_by(user_id=user_id).first()
        budget = self._db.query(UserBudgetProfile).filter_by(user_id=user_id).first()
        context = self._db.query(UserContextualPreference).filter_by(user_id=user_id).first()
        brands = self._db.query(UserBrandAffinity).filter_by(user_id=user_id).count()
        
        if style:
            if style.primary_archetype:
                score += COMPLETENESS_WEIGHTS["style"]["primary_archetype"]
            if style.style_classic is not None:
                score += COMPLETENESS_WEIGHTS["style"]["style_dimensions"]
            if style.preferred_colors:
                score += COMPLETENESS_WEIGHTS["style"]["preferred_colors"]
            if style.skin_undertone:
                score += COMPLETENESS_WEIGHTS["style"]["skin_undertone"]
        
        if body and body.profile_status != "not_set":
            if body.height_cm:
                score += COMPLETENESS_WEIGHTS["body"]["height_cm"]
            if body.body_shape:
                score += COMPLETENESS_WEIGHTS["body"]["body_shape"]
            if body.size_tops:
                score += COMPLETENESS_WEIGHTS["body"]["size_tops"]
            if body.size_bottoms:
                score += COMPLETENESS_WEIGHTS["body"]["size_bottoms"]
        
        if budget:
            if budget.per_item_max:
                score += COMPLETENESS_WEIGHTS["budget"]["per_item_max"]
            if budget.currency:
                score += COMPLETENESS_WEIGHTS["budget"]["currency"]
        
        if context:
            if context.work_environment:
                score += COMPLETENESS_WEIGHTS["context"]["work_environment"]
            if context.climate_zone:
                score += COMPLETENESS_WEIGHTS["context"]["climate_zone"]
            if context.activity_level:
                score += COMPLETENESS_WEIGHTS["context"]["activity_level"]
        
        if brands > 0:
            score += min(brands * 5, COMPLETENESS_WEIGHTS["brands"]["brand_affinities"])
        
        return min(score, 100.0)
    
    def get_style_profile(self, user_id: str) -> Optional[StyleProfileResponse]:
        profile = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        if not profile:
            return None
        
        return StyleProfileResponse(
            id=str(profile.id),
            user_id=str(profile.user_id),
            primary_archetype=profile.primary_archetype,
            secondary_archetypes=profile.secondary_archetypes or [],
            archetype_confidence=float(profile.archetype_confidence or 0),
            style_dimensions=StyleDimensions(
                classic=float(profile.style_classic or 0.5),
                trendy=float(profile.style_trendy or 0.5),
                minimalist=float(profile.style_minimalist or 0.5),
                maximalist=float(profile.style_maximalist or 0.5),
                feminine=float(profile.style_feminine or 0.5),
                masculine=float(profile.style_masculine or 0.5),
                edgy=float(profile.style_edgy or 0.5),
                romantic=float(profile.style_romantic or 0.5),
            ),
            skin_undertone=profile.skin_undertone,
            preferred_colors=profile.preferred_colors or [],
            avoided_colors=profile.avoided_colors or [],
            color_confidence=float(profile.color_confidence or 0),
            pattern_preferences=profile.pattern_preferences or {},
            fabric_preferences=profile.fabric_preferences or [],
            silhouette_preferences=profile.silhouette_preferences or {},
            fit_preference=profile.fit_preference or "regular",
            profile_completeness=float(profile.profile_completeness or 0),
            onboarding_completed=profile.onboarding_completed or False,
            onboarding_phase=profile.onboarding_phase or 0,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
    
    def update_style_profile(
        self,
        user_id: str,
        data: StyleProfileCreate,
        source: str = "explicit",
        ip_address: str = None,
        user_agent: str = None,
    ) -> StyleProfileResponse:
        profile = self._ensure_style_profile(user_id)
        
        updates = []
        
        if data.primary_archetype is not None:
            old = profile.primary_archetype
            profile.primary_archetype = data.primary_archetype
            updates.append(("primary_archetype", old, data.primary_archetype))
        
        if data.secondary_archetypes is not None:
            old = profile.secondary_archetypes
            profile.secondary_archetypes = data.secondary_archetypes
            updates.append(("secondary_archetypes", old, data.secondary_archetypes))
        
        if data.style_dimensions is not None:
            dims = data.style_dimensions
            old_dims = {
                "classic": float(profile.style_classic or 0.5),
                "trendy": float(profile.style_trendy or 0.5),
            }
            profile.style_classic = Decimal(str(dims.classic))
            profile.style_trendy = Decimal(str(dims.trendy))
            profile.style_minimalist = Decimal(str(dims.minimalist))
            profile.style_maximalist = Decimal(str(dims.maximalist))
            profile.style_feminine = Decimal(str(dims.feminine))
            profile.style_masculine = Decimal(str(dims.masculine))
            profile.style_edgy = Decimal(str(dims.edgy))
            profile.style_romantic = Decimal(str(dims.romantic))
            updates.append(("style_dimensions", old_dims, dims.model_dump()))
        
        if data.skin_undertone is not None:
            old = profile.skin_undertone
            profile.skin_undertone = data.skin_undertone
            updates.append(("skin_undertone", old, data.skin_undertone))
        
        if data.preferred_colors is not None:
            old = profile.preferred_colors
            profile.preferred_colors = data.preferred_colors
            updates.append(("preferred_colors", old, data.preferred_colors))
        
        if data.avoided_colors is not None:
            old = profile.avoided_colors
            profile.avoided_colors = data.avoided_colors
            updates.append(("avoided_colors", old, data.avoided_colors))
        
        if data.pattern_preferences is not None:
            old = profile.pattern_preferences
            profile.pattern_preferences = data.pattern_preferences
            updates.append(("pattern_preferences", old, data.pattern_preferences))
        
        if data.fabric_preferences is not None:
            old = profile.fabric_preferences
            profile.fabric_preferences = data.fabric_preferences
            updates.append(("fabric_preferences", old, data.fabric_preferences))
        
        if data.silhouette_preferences is not None:
            old = profile.silhouette_preferences
            profile.silhouette_preferences = data.silhouette_preferences
            updates.append(("silhouette_preferences", old, data.silhouette_preferences))
        
        if data.fit_preference is not None:
            old = profile.fit_preference
            profile.fit_preference = data.fit_preference
            updates.append(("fit_preference", old, data.fit_preference))
        
        profile.profile_completeness = Decimal(str(self._calculate_completeness(user_id)))
        
        self._db.commit()
        self._db.refresh(profile)
        
        for field_name, old_val, new_val in updates:
            self._log_audit(user_id, "user_style_profiles", field_name, old_val, new_val, source, ip_address, user_agent)
        
        return self.get_style_profile(user_id)
    
    def get_body_profile(self, user_id: str) -> Optional[BodyProfileResponse]:
        profile = self._db.query(UserBodyProfile).filter_by(user_id=user_id).first()
        if not profile:
            return None
        
        return BodyProfileResponse(
            id=str(profile.id),
            user_id=str(profile.user_id),
            profile_status=profile.profile_status or "not_set",
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
            chest_cm=profile.chest_cm,
            waist_cm=profile.waist_cm,
            hips_cm=profile.hips_cm,
            inseam_cm=profile.inseam_cm,
            body_shape=profile.body_shape,
            size_tops=profile.size_tops,
            size_bottoms=profile.size_bottoms,
            size_dresses=profile.size_dresses,
            size_shoes=profile.size_shoes,
            brand_size_overrides=profile.brand_size_overrides or {},
            fit_issues=profile.fit_issues or [],
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
    
    def update_body_profile(
        self,
        user_id: str,
        data: BodyProfileCreate,
        source: str = "explicit",
        ip_address: str = None,
        user_agent: str = None,
    ) -> BodyProfileResponse:
        profile = self._ensure_body_profile(user_id)
        
        fields = [
            "height_cm", "weight_kg", "chest_cm", "waist_cm", "hips_cm", "inseam_cm",
            "body_shape", "size_tops", "size_bottoms", "size_dresses", "size_shoes",
        ]
        
        for field in fields:
            value = getattr(data, field, None)
            if value is not None:
                old = getattr(profile, field)
                setattr(profile, field, value)
                self._log_audit(user_id, "user_body_profiles", field, old, value, source, ip_address, user_agent)
        
        if data.brand_size_overrides is not None:
            old = profile.brand_size_overrides
            profile.brand_size_overrides = data.brand_size_overrides
            self._log_audit(user_id, "user_body_profiles", "brand_size_overrides", old, data.brand_size_overrides, source, ip_address, user_agent)
        
        if data.fit_issues is not None:
            old = profile.fit_issues
            profile.fit_issues = data.fit_issues
            self._log_audit(user_id, "user_body_profiles", "fit_issues", old, data.fit_issues, source, ip_address, user_agent)
        
        has_data = any(getattr(profile, f) for f in fields if f not in ["body_shape"])
        profile.profile_status = "complete" if has_data else "partial"
        
        style_profile = self._ensure_style_profile(user_id)
        style_profile.profile_completeness = Decimal(str(self._calculate_completeness(user_id)))
        
        self._db.commit()
        self._db.refresh(profile)
        
        return self.get_body_profile(user_id)
    
    def get_budget_profile(self, user_id: str) -> Optional[BudgetProfileResponse]:
        profile = self._db.query(UserBudgetProfile).filter_by(user_id=user_id).first()
        if not profile:
            return None
        
        return BudgetProfileResponse(
            id=str(profile.id),
            user_id=str(profile.user_id),
            per_item_min=float(profile.per_item_min) if profile.per_item_min else None,
            per_item_max=float(profile.per_item_max) if profile.per_item_max else None,
            monthly_max=float(profile.monthly_max) if profile.monthly_max else None,
            currency=profile.currency or "USD",
            investment_willing=profile.investment_willing or False,
            price_sensitivity=float(profile.price_sensitivity or 0.5),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
    
    def update_budget_profile(
        self,
        user_id: str,
        data: BudgetProfileCreate,
        source: str = "explicit",
        ip_address: str = None,
        user_agent: str = None,
    ) -> BudgetProfileResponse:
        profile = self._ensure_budget_profile(user_id)
        
        if data.per_item_min is not None:
            old = profile.per_item_min
            profile.per_item_min = Decimal(str(data.per_item_min))
            self._log_audit(user_id, "user_budget_profiles", "per_item_min", float(old) if old else None, data.per_item_min, source, ip_address, user_agent)
        
        if data.per_item_max is not None:
            old = profile.per_item_max
            profile.per_item_max = Decimal(str(data.per_item_max))
            self._log_audit(user_id, "user_budget_profiles", "per_item_max", float(old) if old else None, data.per_item_max, source, ip_address, user_agent)
        
        if data.monthly_max is not None:
            old = profile.monthly_max
            profile.monthly_max = Decimal(str(data.monthly_max))
            self._log_audit(user_id, "user_budget_profiles", "monthly_max", float(old) if old else None, data.monthly_max, source, ip_address, user_agent)
        
        if data.currency is not None:
            old = profile.currency
            profile.currency = data.currency
            self._log_audit(user_id, "user_budget_profiles", "currency", old, data.currency, source, ip_address, user_agent)
        
        if data.investment_willing is not None:
            old = profile.investment_willing
            profile.investment_willing = data.investment_willing
            self._log_audit(user_id, "user_budget_profiles", "investment_willing", old, data.investment_willing, source, ip_address, user_agent)
        
        if data.price_sensitivity is not None:
            old = profile.price_sensitivity
            profile.price_sensitivity = Decimal(str(data.price_sensitivity))
            self._log_audit(user_id, "user_budget_profiles", "price_sensitivity", float(old) if old else None, data.price_sensitivity, source, ip_address, user_agent)
        
        style_profile = self._ensure_style_profile(user_id)
        style_profile.profile_completeness = Decimal(str(self._calculate_completeness(user_id)))
        
        self._db.commit()
        self._db.refresh(profile)
        
        return self.get_budget_profile(user_id)
    
    def get_brand_affinities(self, user_id: str) -> List[BrandAffinityResponse]:
        affinities = self._db.query(UserBrandAffinity).filter_by(user_id=user_id).all()
        return [
            BrandAffinityResponse(
                id=str(a.id),
                user_id=str(a.user_id),
                brand_id=a.brand_id,
                affinity_score=float(a.affinity_score or 0.5),
                affinity_source=a.affinity_source or "explicit",
                reason=a.reason,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in affinities
        ]
    
    def add_brand_affinity(
        self,
        user_id: str,
        data: BrandAffinityCreate,
        source: str = "explicit",
    ) -> BrandAffinityResponse:
        existing = self._db.query(UserBrandAffinity).filter_by(
            user_id=user_id, brand_id=data.brand_id
        ).first()
        
        if existing:
            existing.affinity_score = Decimal(str(data.affinity_score))
            existing.affinity_source = source
            if data.reason:
                existing.reason = data.reason
            self._db.commit()
            self._db.refresh(existing)
            affinity = existing
        else:
            affinity = UserBrandAffinity(
                user_id=user_id,
                brand_id=data.brand_id,
                affinity_score=Decimal(str(data.affinity_score)),
                affinity_source=source,
                reason=data.reason,
            )
            self._db.add(affinity)
            self._db.commit()
            self._db.refresh(affinity)
        
        self._log_audit(user_id, "user_brand_affinities", "brand_id", None, data.brand_id, source)
        
        style_profile = self._ensure_style_profile(user_id)
        style_profile.profile_completeness = Decimal(str(self._calculate_completeness(user_id)))
        self._db.commit()
        
        return BrandAffinityResponse(
            id=str(affinity.id),
            user_id=str(affinity.user_id),
            brand_id=affinity.brand_id,
            affinity_score=float(affinity.affinity_score or 0.5),
            affinity_source=affinity.affinity_source or "explicit",
            reason=affinity.reason,
            created_at=affinity.created_at,
            updated_at=affinity.updated_at,
        )
    
    def remove_brand_affinity(self, user_id: str, brand_id: str) -> bool:
        affinity = self._db.query(UserBrandAffinity).filter_by(
            user_id=user_id, brand_id=brand_id
        ).first()
        
        if not affinity:
            return False
        
        self._log_audit(user_id, "user_brand_affinities", "brand_id", brand_id, None, "explicit")
        
        self._db.delete(affinity)
        self._db.commit()
        
        style_profile = self._ensure_style_profile(user_id)
        style_profile.profile_completeness = Decimal(str(self._calculate_completeness(user_id)))
        self._db.commit()
        
        return True
    
    def get_contextual_preferences(self, user_id: str) -> Optional[ContextualPreferenceResponse]:
        pref = self._db.query(UserContextualPreference).filter_by(user_id=user_id).first()
        if not pref:
            return None
        
        return ContextualPreferenceResponse(
            id=str(pref.id),
            user_id=str(pref.user_id),
            occasion_weights=pref.occasion_weights or {},
            work_environment=pref.work_environment,
            climate_zone=pref.climate_zone,
            activity_level=pref.activity_level,
            has_children=pref.has_children,
            pet_friendly=pref.pet_friendly,
            weather_preferences=pref.weather_preferences or {},
            cultural_influences=pref.cultural_influences or [],
            modesty_preference=pref.modesty_preference,
            style_icons=pref.style_icons or [],
            social_influences=pref.social_influences or [],
            created_at=pref.created_at,
            updated_at=pref.updated_at,
        )
    
    def update_contextual_preferences(
        self,
        user_id: str,
        data: ContextualPreferenceCreate,
        source: str = "explicit",
        ip_address: str = None,
        user_agent: str = None,
    ) -> ContextualPreferenceResponse:
        pref = self._ensure_contextual_preference(user_id)
        
        simple_fields = [
            "work_environment", "climate_zone", "activity_level",
            "has_children", "pet_friendly", "modesty_preference",
        ]
        
        for field in simple_fields:
            value = getattr(data, field, None)
            if value is not None:
                old = getattr(pref, field)
                setattr(pref, field, value)
                self._log_audit(user_id, "user_contextual_preferences", field, old, value, source, ip_address, user_agent)
        
        json_fields = [
            "occasion_weights", "weather_preferences", "cultural_influences",
            "style_icons", "social_influences",
        ]
        
        for field in json_fields:
            value = getattr(data, field, None)
            if value is not None:
                old = getattr(pref, field)
                setattr(pref, field, value)
                self._log_audit(user_id, "user_contextual_preferences", field, old, value, source, ip_address, user_agent)
        
        style_profile = self._ensure_style_profile(user_id)
        style_profile.profile_completeness = Decimal(str(self._calculate_completeness(user_id)))
        
        self._db.commit()
        self._db.refresh(pref)
        
        return self.get_contextual_preferences(user_id)
    
    def get_completeness(self, user_id: str) -> ProfileCompletenessResponse:
        score = self._calculate_completeness(user_id)
        
        sections = {
            "style": 0.0,
            "body": 0.0,
            "budget": 0.0,
            "context": 0.0,
            "brands": 0.0,
        }
        
        style = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        body = self._db.query(UserBodyProfile).filter_by(user_id=user_id).first()
        budget = self._db.query(UserBudgetProfile).filter_by(user_id=user_id).first()
        context = self._db.query(UserContextualPreference).filter_by(user_id=user_id).first()
        brands = self._db.query(UserBrandAffinity).filter_by(user_id=user_id).count()
        
        if style:
            s = 0
            if style.primary_archetype:
                s += COMPLETENESS_WEIGHTS["style"]["primary_archetype"]
            if style.style_classic is not None:
                s += COMPLETENESS_WEIGHTS["style"]["style_dimensions"]
            if style.preferred_colors:
                s += COMPLETENESS_WEIGHTS["style"]["preferred_colors"]
            if style.skin_undertone:
                s += COMPLETENESS_WEIGHTS["style"]["skin_undertone"]
            sections["style"] = s
        
        if body and body.profile_status != "not_set":
            b = 0
            if body.height_cm:
                b += COMPLETENESS_WEIGHTS["body"]["height_cm"]
            if body.body_shape:
                b += COMPLETENESS_WEIGHTS["body"]["body_shape"]
            if body.size_tops:
                b += COMPLETENESS_WEIGHTS["body"]["size_tops"]
            if body.size_bottoms:
                b += COMPLETENESS_WEIGHTS["body"]["size_bottoms"]
            sections["body"] = b
        
        if budget:
            bu = 0
            if budget.per_item_max:
                bu += COMPLETENESS_WEIGHTS["budget"]["per_item_max"]
            if budget.currency:
                bu += COMPLETENESS_WEIGHTS["budget"]["currency"]
            sections["budget"] = bu
        
        if context:
            c = 0
            if context.work_environment:
                c += COMPLETENESS_WEIGHTS["context"]["work_environment"]
            if context.climate_zone:
                c += COMPLETENESS_WEIGHTS["context"]["climate_zone"]
            if context.activity_level:
                c += COMPLETENESS_WEIGHTS["context"]["activity_level"]
            sections["context"] = c
        
        sections["brands"] = min(brands * 5, COMPLETENESS_WEIGHTS["brands"]["brand_affinities"])
        
        missing = []
        suggestions = []
        
        if not style or not style.primary_archetype:
            missing.append("style.primary_archetype")
            suggestions.append("Complete the style quiz to discover your style archetype")
        
        if not body or body.profile_status == "not_set":
            missing.append("body.measurements")
            suggestions.append("Add your body measurements for better fit recommendations")
        
        if not budget or not budget.per_item_max:
            missing.append("budget.per_item_max")
            suggestions.append("Set your budget range for personalized price filtering")
        
        if not context or not context.work_environment:
            missing.append("context.work_environment")
            suggestions.append("Tell us about your work environment for occasion-based styling")
        
        if brands == 0:
            missing.append("brands.affinities")
            suggestions.append("Add your favorite brands for better recommendations")
        
        return ProfileCompletenessResponse(
            overall_score=score,
            sections=sections,
            missing_fields=missing,
            suggestions=suggestions,
        )
    
    def calculate_archetype(self, user_id: str) -> Optional[StyleArchetypeResult]:
        profile = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        if not profile:
            return None
        
        dims = {
            "classic": float(profile.style_classic or 0.5),
            "trendy": float(profile.style_trendy or 0.5),
            "minimalist": float(profile.style_minimalist or 0.5),
            "maximalist": float(profile.style_maximalist or 0.5),
            "feminine": float(profile.style_feminine or 0.5),
            "masculine": float(profile.style_masculine or 0.5),
            "edgy": float(profile.style_edgy or 0.5),
            "romantic": float(profile.style_romantic or 0.5),
        }
        
        best_match = None
        best_score = 0.0
        
        for archetype, weights in STYLE_ARCHETYPES.items():
            score = sum(dims.get(k, 0.5) * v for k, v in weights.items())
            if score > best_score:
                best_score = score
                best_match = archetype
        
        secondary = []
        for archetype, weights in STYLE_ARCHETYPES.items():
            if archetype == best_match:
                continue
            score = sum(dims.get(k, 0.5) * v for k, v in weights.items())
            if score > best_score * 0.8:
                secondary.append(archetype)
        
        confidence = min(best_score / 2.5, 1.0)
        
        old_archetype = profile.primary_archetype
        profile.primary_archetype = best_match
        profile.secondary_archetypes = secondary[:2]
        profile.archetype_confidence = Decimal(str(confidence))
        
        self._db.commit()
        
        if old_archetype != best_match:
            evolution = UserStyleEvolution(
                user_id=user_id,
                event_type="archetype_change",
                previous_value={"archetype": old_archetype},
                new_value={"archetype": best_match, "confidence": confidence},
                trigger_source="calculated",
            )
            self._db.add(evolution)
            self._db.commit()
        
        return StyleArchetypeResult(
            primary=best_match,
            secondary=secondary[:2],
            confidence=confidence,
            dimensions=StyleDimensions(**dims),
        )


def get_profile_service(db: Session = Depends(get_db)) -> ProfileService:
    """Factory function for ProfileService dependency injection."""
    return ProfileService(db)
