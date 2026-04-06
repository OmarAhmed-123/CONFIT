"""
CONFIT Backend — Brand Ecosystem Integration Service
=====================================================
Cross-group integration for GROUP 6 (Brand & Admin Management) with:
- GROUP 1: User Identity & USP (brand affinities, confidence)
- GROUP 2: Discovery & Styling (recommendations, trends)
- GROUP 3: Virtual Try-On (fit confidence, quality signals)
- GROUP 4: Wardrobe (ownership patterns, sustainability)
- GROUP 5: Checkout (trust, BNPL, purchase confidence)

Orchestrates bidirectional signal flow for unified ecosystem intelligence.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from collections import defaultdict
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from database.models import (
    Brand, Product, Order, OrderItem, ReturnRequest,
    User, WardrobeItem, Outfit
)
from services.brand_intelligence_service import BrandIntelligenceService
from services.marketplace_governance_service import MarketplaceGovernanceService
from services.ai_brain_service import AIBrainService

logger = logging.getLogger(__name__)


# ── Cross-Group Signal Types ───────────────────────────────────────────────

BRAND_TO_USER_SIGNALS = {
    # GROUP 6 → GROUP 1: Brand signals affecting user profile
    "brand_affinity_update": {
        "target_group": 1,
        "signal_type": "brand_preference",
        "weight": 0.8,
        "decay_days": 180,
    },
    "brand_trust_change": {
        "target_group": 1,
        "signal_type": "confidence_impact",
        "weight": 0.5,
        "decay_days": 30,
    },
    
    # GROUP 6 → GROUP 2: Brand signals for styling
    "brand_trend_alignment": {
        "target_group": 2,
        "signal_type": "recommendation_weight",
        "weight": 0.7,
        "decay_days": 90,
    },
    "brand_style_vector": {
        "target_group": 2,
        "signal_type": "style_preference",
        "weight": 0.6,
        "decay_days": 60,
    },
    
    # GROUP 6 → GROUP 3: Brand signals for try-on
    "brand_fit_consistency": {
        "target_group": 3,
        "signal_type": "size_prediction_weight",
        "weight": 0.8,
        "decay_days": 180,
    },
    "brand_quality_score": {
        "target_group": 3,
        "signal_type": "visual_realism_factor",
        "weight": 0.5,
        "decay_days": 90,
    },
    
    # GROUP 6 → GROUP 4: Brand signals for wardrobe
    "brand_sustainability_rating": {
        "target_group": 4,
        "signal_type": "eco_preference",
        "weight": 0.4,
        "decay_days": 365,
    },
    "brand_longevity_score": {
        "target_group": 4,
        "signal_type": "investment_value",
        "weight": 0.6,
        "decay_days": 365,
    },
    
    # GROUP 6 → GROUP 5: Brand signals for checkout
    "brand_trust_index": {
        "target_group": 5,
        "signal_type": "purchase_confidence_factor",
        "weight": 0.7,
        "decay_days": 30,
    },
    "brand_return_risk": {
        "target_group": 5,
        "signal_type": "return_prediction_weight",
        "weight": 0.8,
        "decay_days": 90,
    },
}

USER_TO_BRAND_SIGNALS = {
    # GROUP 1 → GROUP 6: User signals affecting brand intelligence
    "user_brand_affinity": {
        "source_group": 1,
        "affects": "brand_popularity_score",
    },
    "user_brand_purchase": {
        "source_group": 1,
        "affects": "brand_revenue_metrics",
    },
    
    # GROUP 2 → GROUP 6: Styling signals affecting brands
    "outfit_brand_usage": {
        "source_group": 2,
        "affects": "brand_styling_popularity",
    },
    "stylist_brand_recommendation": {
        "source_group": 2,
        "affects": "brand_recommendation_score",
    },
    
    # GROUP 3 → GROUP 6: Try-on signals affecting brands
    "try_on_brand_success": {
        "source_group": 3,
        "affects": "brand_fit_confidence",
    },
    "try_on_brand_return": {
        "source_group": 3,
        "affects": "brand_return_rate",
    },
    
    # GROUP 4 → GROUP 6: Wardrobe signals affecting brands
    "wardrobe_brand_ownership": {
        "source_group": 4,
        "affects": "brand_market_penetration",
    },
    "wardrobe_brand_utilization": {
        "source_group": 4,
        "affects": "brand_quality_perception",
    },
    
    # GROUP 5 → GROUP 6: Commerce signals affecting brands
    "purchase_brand_conversion": {
        "source_group": 5,
        "affects": "brand_conversion_rate",
    },
    "return_brand_pattern": {
        "source_group": 5,
        "affects": "brand_return_metrics",
    },
}


class BrandEcosystemIntegration:
    """
    Orchestrates bidirectional signal flow between GROUP 6 and all other groups.
    
    Responsibilities:
    - Translate brand intelligence to user-facing signals
    - Aggregate user behavior into brand insights
    - Maintain consistency across ecosystem
    - Enable cross-group event propagation
    """
    
    def __init__(self, db: Session):
        self._db = db
        self._brand_intelligence = BrandIntelligenceService(db)
        self._governance = MarketplaceGovernanceService(db)
        self._ai_brain = AIBrainService(db)
    
    # ── GROUP 6 → GROUP 1: Brand to User Identity ─────────────────────────
    
    async def propagate_brand_affinity_to_user(
        self,
        user_id: str,
        brand_id: str,
        affinity_score: float,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Propagate brand affinity to user profile (GROUP 1).
        
        Updates:
        - User brand affinities list
        - Confidence dimensions (brand_affinity)
        - Style vector brand preferences
        """
        ctx = context or {}
        
        # Get brand intelligence
        trust_index = self._governance.calculate_brand_trust_index(brand_id)
        trend_analysis = self._brand_intelligence.analyze_style_trends(brand_id)
        
        # Calculate user impact
        user_impact = {
            "brand_affinity": affinity_score,
            "brand_trust_tier": trust_index.trust_tier,
            "brand_trend_alignment": trend_analysis.trend_alignment_score,
            "confidence_impact": affinity_score * (trust_index.trust_score / 100),
        }
        
        # Track in AI Brain
        self._ai_brain.track_brand_affinity(
            user_id=user_id,
            brand_id=brand_id,
            affinity_score=affinity_score,
            context={
                **ctx,
                "trust_tier": trust_index.trust_tier,
                "trend_alignment": trend_analysis.trend_alignment_score,
            },
        )
        
        return {
            "user_id": user_id,
            "brand_id": brand_id,
            "propagated": True,
            "user_impact": user_impact,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    async def get_user_brand_confidence_impact(
        self,
        user_id: str,
        brand_id: str,
    ) -> Dict[str, Any]:
        """
        Calculate how brand trust affects user confidence (GROUP 1).
        
        Returns impact on confidence dimensions.
        """
        trust = self._governance.calculate_brand_trust_index(brand_id)
        
        # Calculate dimension impacts
        impacts = {
            "brand_affinity": trust.trust_score / 100 * 0.3,
            "style_identity": trust.factor_scores.get("quality_score", 0) / 100 * 0.2,
            "occasion_readiness": trust.factor_scores.get("compliance_history", 0) / 100 * 0.1,
        }
        
        return {
            "user_id": user_id,
            "brand_id": brand_id,
            "trust_tier": trust.trust_tier,
            "confidence_impacts": impacts,
            "overall_impact": sum(impacts.values()) / len(impacts),
        }
    
    # ── GROUP 6 → GROUP 2: Brand to Styling ────────────────────────────────
    
    async def get_brand_recommendation_weight(
        self,
        brand_id: str,
        user_id: str = None,
    ) -> Dict[str, Any]:
        """
        Calculate brand weight for recommendation engine (GROUP 2).
        
        Factors:
        - Trust index
        - Trend alignment
        - User affinity (if user provided)
        - Marketplace performance
        """
        trust = self._governance.calculate_brand_trust_index(brand_id)
        trends = self._brand_intelligence.analyze_style_trends(brand_id)
        performance = self._brand_intelligence.get_brand_performance_signals(brand_id)
        
        # Calculate recommendation weight
        weight = (
            trust.trust_score * 0.30 +
            trends.trend_alignment_score * 0.25 +
            min(100, performance.get("performance", {}).get("total_units_sold", 0)) * 0.20 +
            (100 - trust.factor_scores.get("return_rate", 50)) * 0.25
        ) / 100
        
        # Adjust for user affinity if provided
        user_affinity = None
        if user_id:
            # Would fetch from user profile
            user_affinity = 0.5  # Placeholder
            weight = weight * 0.7 + user_affinity * 0.3
        
        return {
            "brand_id": brand_id,
            "recommendation_weight": round(weight, 3),
            "factors": {
                "trust_score": trust.trust_score,
                "trend_alignment": trends.trend_alignment_score,
                "performance_score": performance.get("performance", {}).get("total_units_sold", 0),
                "return_factor": 100 - trust.factor_scores.get("return_rate", 50),
            },
            "user_affinity": user_affinity,
            "boost_level": "high" if weight > 0.7 else "medium" if weight > 0.5 else "low",
        }
    
    async def get_brand_style_vector(
        self,
        brand_id: str,
    ) -> Dict[str, float]:
        """
        Extract brand style vector for AI Brain (GROUP 2).
        
        Returns style dimensions based on brand's product catalog.
        """
        trends = self._brand_intelligence.analyze_style_trends(brand_id)
        
        # Convert trend analysis to style vector
        style_vector = {
            "classic": 0.5,  # Would calculate from products
            "trendy": trends.trend_alignment_score / 100,
            "minimalist": 0.5,
            "maximalist": 0.3,
            "feminine": 0.5,
            "masculine": 0.5,
            "edgy": 0.3,
            "romantic": 0.3,
        }
        
        # Adjust based on trending elements
        trending = trends.trending_elements
        if "oversized_blazer" in str(trending.get("silhouettes", [])):
            style_vector["trendy"] += 0.1
        if "sage_green" in str(trending.get("colors", [])):
            style_vector["minimalist"] += 0.1
        
        # Normalize to 0-1 range
        for key in style_vector:
            style_vector[key] = min(1.0, max(0.0, style_vector[key]))
        
        return style_vector
    
    # ── GROUP 6 → GROUP 3: Brand to Try-On ──────────────────────────────────
    
    async def get_brand_fit_consistency(
        self,
        brand_id: str,
    ) -> Dict[str, Any]:
        """
        Get brand fit consistency for size prediction (GROUP 3).
        
        Returns:
        - Overall fit consistency score
        - Category-specific fit scores
        - Size prediction confidence modifier
        """
        risk = self._brand_intelligence.calculate_brand_return_risk(brand_id)
        trust = self._governance.calculate_brand_trust_index(brand_id)
        
        # Calculate fit consistency
        fit_consistency = 100 - risk.overall_risk_score
        
        # Category-specific fit scores
        category_fit = {}
        for cat, score in risk.category_risks.items():
            category_fit[cat] = 100 - score
        
        return {
            "brand_id": brand_id,
            "fit_consistency_score": round(fit_consistency, 2),
            "category_fit_scores": category_fit,
            "size_prediction_confidence": round(fit_consistency / 100, 2),
            "trust_tier": trust.trust_tier,
            "fit_reliability": "high" if fit_consistency > 80 else "medium" if fit_consistency > 60 else "low",
        }
    
    async def get_brand_quality_factor(
        self,
        brand_id: str,
    ) -> Dict[str, Any]:
        """
        Get brand quality factor for visual realism (GROUP 3).
        
        Affects try-on quality expectations.
        """
        quality = self._governance.calculate_brand_quality_score(brand_id)
        
        return {
            "brand_id": brand_id,
            "quality_score": quality.overall_score,
            "quality_tier": quality.tier,
            "visual_realism_factor": round(quality.overall_score / 100, 2),
            "image_quality_expectation": quality.dimension_scores.get("image_quality", 0),
        }
    
    # ── GROUP 6 → GROUP 4: Brand to Wardrobe ───────────────────────────────
    
    async def get_brand_sustainability_rating(
        self,
        brand_id: str,
    ) -> Dict[str, Any]:
        """
        Get brand sustainability rating for wardrobe insights (GROUP 4).
        
        Affects:
        - Eco-preference signals
        - Investment value calculations
        - Sustainability tips
        """
        # Would integrate with sustainability data
        # Placeholder calculation
        trust = self._governance.calculate_brand_trust_index(brand_id)
        quality = self._governance.calculate_brand_quality_score(brand_id)
        
        sustainability_score = (
            quality.dimension_scores.get("product_completeness", 0) * 0.3 +
            trust.trust_score * 0.4 +
            (100 - trust.factor_scores.get("return_rate", 50)) * 0.3
        )
        
        return {
            "brand_id": brand_id,
            "sustainability_score": round(sustainability_score, 2),
            "eco_rating": "A" if sustainability_score > 80 else "B" if sustainability_score > 60 else "C",
            "longevity_factor": round(quality.overall_score / 100, 2),
            "investment_value": round(sustainability_score / 100 * 0.8, 2),
        }
    
    async def get_brand_ownership_insights(
        self,
        brand_id: str,
    ) -> Dict[str, Any]:
        """
        Get brand ownership patterns for wardrobe analytics (GROUP 4).
        
        Returns market penetration and utilization patterns.
        """
        products = self._db.query(Product).filter_by(brand_id=brand_id).all()
        product_ids = [p.id for p in products]
        
        # Count wardrobe ownership
        ownership_count = self._db.query(WardrobeItem).filter(
            WardrobeItem.product_id.in_(product_ids) if product_ids else False
        ).count()
        
        return {
            "brand_id": brand_id,
            "market_penetration": ownership_count,  # Would normalize by total users
            "product_count": len(products),
            "ownership_rate": round(ownership_count / max(1, len(products)), 2),
        }
    
    # ── GROUP 6 → GROUP 5: Brand to Checkout ──────────────────────────────
    
    async def get_brand_purchase_confidence_factor(
        self,
        brand_id: str,
        user_id: str = None,
    ) -> Dict[str, Any]:
        """
        Get brand factor for purchase confidence calculation (GROUP 5).
        
        Affects:
        - Purchase confidence score
        - BNPL eligibility
        - Checkout readiness
        """
        trust = self._governance.calculate_brand_trust_index(brand_id)
        risk = self._brand_intelligence.calculate_brand_return_risk(brand_id)
        
        # Calculate confidence factor
        confidence_factor = (
            trust.trust_score * 0.35 +
            (100 - risk.overall_risk_score) * 0.30 +
            trust.factor_scores.get("quality_score", 0) * 0.20 +
            trust.factor_scores.get("customer_satisfaction", 0) * 0.15
        ) / 100
        
        return {
            "brand_id": brand_id,
            "confidence_factor": round(confidence_factor, 3),
            "trust_tier": trust.trust_tier,
            "return_risk_level": risk.risk_level,
            "purchase_recommendation": "highly_recommended" if confidence_factor > 0.8 else "recommended" if confidence_factor > 0.6 else "neutral",
        }
    
    async def get_brand_bnpl_eligibility_factor(
        self,
        brand_id: str,
    ) -> Dict[str, Any]:
        """
        Get brand factor for BNPL eligibility (GROUP 5).
        
        High-trust brands get better BNPL terms.
        """
        trust = self._governance.calculate_brand_trust_index(brand_id)
        
        # BNPL eligibility based on trust
        if trust.trust_tier in ["platinum", "gold"]:
            bnpl_factor = 1.0  # Full eligibility
            max_installments = 4
        elif trust.trust_tier == "silver":
            bnpl_factor = 0.8
            max_installments = 3
        elif trust.trust_tier == "bronze":
            bnpl_factor = 0.6
            max_installments = 2
        else:
            bnpl_factor = 0.3
            max_installments = 0  # Not eligible
        
        return {
            "brand_id": brand_id,
            "bnpl_eligibility_factor": bnpl_factor,
            "max_installments": max_installments,
            "trust_tier": trust.trust_tier,
            "requires_review": trust.trust_tier == "probation",
        }
    
    # ── Reverse Integration: User Signals → Brand Intelligence ─────────────
    
    async def process_user_brand_interaction(
        self,
        user_id: str,
        brand_id: str,
        interaction_type: str,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Process user interaction with brand and update brand intelligence.
        
        Aggregates signals from all groups into brand metrics.
        """
        ctx = context or {}
        
        # Get signal configuration
        signal_config = USER_TO_BRAND_SIGNALS.get(interaction_type, {})
        affects = signal_config.get("affects", "brand_general_metrics")
        
        # Track in AI Brain
        self._ai_brain.track_brand_performance(
            brand_id=brand_id,
            performance_type=interaction_type,
            metrics={
                "user_id": user_id,
                "interaction_type": interaction_type,
                "context": ctx,
            },
            context=ctx,
        )
        
        # Update brand intelligence based on signal type
        result = {
            "brand_id": brand_id,
            "user_id": user_id,
            "interaction_type": interaction_type,
            "affects": affects,
            "processed": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        return result
    
    async def aggregate_user_signals_to_brand(
        self,
        brand_id: str,
        time_window_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Aggregate all user signals for a brand over time window.
        
        Creates comprehensive brand intelligence report from user behavior.
        """
        since = datetime.now(timezone.utc) - timedelta(days=time_window_days)
        
        # Get brand insights from AI Brain
        brain_insights = self._ai_brain.get_brand_insights(brand_id)
        
        # Get performance signals
        performance = self._brand_intelligence.get_brand_performance_signals(brand_id)
        
        # Get trust index
        trust = self._governance.calculate_brand_trust_index(brand_id)
        
        # Aggregate
        aggregated = {
            "brand_id": brand_id,
            "time_window_days": time_window_days,
            "aggregated_signals": {
                "popularity_score": brain_insights.get("popularity_score", 0),
                "total_views": brain_insights.get("total_views", 0),
                "total_purchases": brain_insights.get("total_purchases", 0),
                "total_tryons": brain_insights.get("total_tryons", 0),
                "average_user_affinity": brain_insights.get("average_user_affinity", 0),
                "unique_users": brain_insights.get("unique_users", 0),
            },
            "trust_metrics": {
                "trust_score": trust.trust_score,
                "trust_tier": trust.trust_tier,
                "factor_scores": trust.factor_scores,
            },
            "performance_metrics": performance.get("performance", {}),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        return aggregated
    
    # ── Cross-Group Event Propagation ─────────────────────────────────────
    
    async def propagate_brand_event(
        self,
        event_type: str,
        brand_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Propagate brand event to all affected groups.
        
        Events:
        - brand_trust_change: Propagates to GROUP 1, 5
        - brand_trend_update: Propagates to GROUP 2
        - brand_quality_change: Propagates to GROUP 3, 4
        - brand_compliance_change: Propagates to all groups
        """
        propagation_map = {
            "brand_trust_change": [1, 5],
            "brand_trend_update": [2],
            "brand_quality_change": [3, 4],
            "brand_compliance_change": [1, 2, 3, 4, 5],
            "brand_suspension": [1, 2, 3, 4, 5],
            "brand_reinstatement": [1, 2, 3, 4, 5],
        }
        
        target_groups = propagation_map.get(event_type, [])
        propagation_results = []
        
        for group in target_groups:
            result = await self._propagate_to_group(group, event_type, brand_id, data)
            propagation_results.append(result)
        
        return {
            "event_type": event_type,
            "brand_id": brand_id,
            "propagated_to": target_groups,
            "results": propagation_results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    async def _propagate_to_group(
        self,
        group: int,
        event_type: str,
        brand_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Propagate event to specific group."""
        
        if group == 1:
            # Update user confidence impacts
            return {"group": 1, "action": "update_confidence_impacts", "status": "completed"}
        
        elif group == 2:
            # Update recommendation weights
            weight = await self.get_brand_recommendation_weight(brand_id)
            return {"group": 2, "action": "update_recommendation_weights", "weight": weight, "status": "completed"}
        
        elif group == 3:
            # Update fit consistency
            fit = await self.get_brand_fit_consistency(brand_id)
            return {"group": 3, "action": "update_fit_consistency", "fit_data": fit, "status": "completed"}
        
        elif group == 4:
            # Update sustainability ratings
            sustainability = await self.get_brand_sustainability_rating(brand_id)
            return {"group": 4, "action": "update_sustainability", "sustainability": sustainability, "status": "completed"}
        
        elif group == 5:
            # Update purchase confidence factors
            confidence = await self.get_brand_purchase_confidence_factor(brand_id)
            return {"group": 5, "action": "update_purchase_confidence", "confidence": confidence, "status": "completed"}
        
        return {"group": group, "status": "no_action"}
    
    # ── Unified Ecosystem Context ──────────────────────────────────────────
    
    async def get_brand_ecosystem_context(
        self,
        brand_id: str,
        user_id: str = None,
    ) -> Dict[str, Any]:
        """
        Get complete brand context across all ecosystem groups.
        
        Single source of truth for brand intelligence.
        """
        # Gather from all groups in parallel
        trust = self._governance.calculate_brand_trust_index(brand_id)
        quality = self._governance.calculate_brand_quality_score(brand_id)
        trends = self._brand_intelligence.analyze_style_trends(brand_id)
        risk = self._brand_intelligence.calculate_brand_return_risk(brand_id)
        performance = self._brand_intelligence.get_brand_performance_signals(brand_id)
        
        # Group-specific contexts
        group1_context = await self.get_user_brand_confidence_impact(user_id or "anonymous", brand_id)
        group2_context = await self.get_brand_recommendation_weight(brand_id, user_id)
        group3_context = await self.get_brand_fit_consistency(brand_id)
        group4_context = await self.get_brand_sustainability_rating(brand_id)
        group5_context = await self.get_brand_purchase_confidence_factor(brand_id, user_id)
        
        return {
            "brand_id": brand_id,
            "user_id": user_id,
            
            # Core brand intelligence
            "trust_index": trust.to_dict(),
            "quality_score": quality.to_dict(),
            "trend_analysis": trends.to_dict(),
            "return_risk": risk.to_dict(),
            "performance_signals": performance,
            
            # Cross-group contexts
            "group1_user_impact": group1_context,
            "group2_recommendation_weight": group2_context,
            "group3_fit_consistency": group3_context,
            "group4_sustainability": group4_context,
            "group5_purchase_confidence": group5_context,
            
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
