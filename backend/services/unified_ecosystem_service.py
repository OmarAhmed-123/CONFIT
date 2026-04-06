"""
CONFIT Backend — Unified Ecosystem Integration Service
========================================================
Orchestrates cross-group communication and ensures all features
work together as ONE unified intelligent ecosystem.

Core Principle: "Understand the user once, personalize forever."

This service provides:
- Cross-group event bus
- Unified signal aggregation
- Feedback learning loops
- Shared intelligence layer
- Identity evolution tracking
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Callable
from collections import defaultdict
from enum import Enum
import asyncio
import json

from fastapi import Depends
from sqlalchemy.orm import Session

from database.session import get_db
from sqlalchemy import and_, or_, func

from models.profile_models import (
    UserStyleProfile,
    UserBehaviorSignal,
    UserStyleEvolution,
)
from database.models import Order, OrderItem, Product, Outfit

logger = logging.getLogger(__name__)


# ── Cross-Group Event Types ─────────────────────────────────────────────

class EcosystemEvent(str, Enum):
    """Events that flow between feature groups."""
    
    # Group 1 → All: User Identity Events
    USER_ONBOARDING_COMPLETE = "user_onboarding_complete"
    USER_PREFERENCE_CHANGE = "user_preference_change"
    USER_CONFIDENCE_UPDATE = "user_confidence_update"
    USER_STYLE_EVOLUTION = "user_style_evolution"
    
    # Group 2 → All: Styling Events
    OUTFIT_CREATED = "outfit_created"
    OUTFIT_ACCEPTED = "outfit_accepted"
    OUTFIT_REJECTED = "outfit_rejected"
    STYLIST_RECOMMENDATION = "stylist_recommendation"
    STYLE_FEEDBACK = "style_feedback"
    
    # Group 3 → All: Try-On Events
    TRY_ON_COMPLETE = "try_on_complete"
    TRY_ON_SUCCESS = "try_on_success"
    TRY_ON_FAILURE = "try_on_failure"
    FIT_FEEDBACK = "fit_feedback"
    SIZE_PREDICTION = "size_prediction"
    
    # Group 5 → All: Commerce Events
    CART_ADD = "cart_add"
    CART_REMOVE = "cart_remove"
    CART_ABANDON = "cart_abandon"
    CHECKOUT_START = "checkout_start"
    PURCHASE_COMPLETE = "purchase_complete"
    RETURN_INITIATED = "return_initiated"
    RETURN_COMPLETE = "return_complete"
    
    # Cross-Group: Learning Events
    PREFERENCE_DRIFT = "preference_drift"
    BEHAVIOR_PATTERN = "behavior_pattern"
    RECOMMENDATION_FEEDBACK = "recommendation_feedback"


# ── Signal Aggregation Weights ─────────────────────────────────────────

SIGNAL_WEIGHTS = {
    # High-weight signals (strong preference indicators)
    "purchase": 1.0,
    "outfit_accept": 0.9,
    "try_on_success": 0.8,
    "wishlist_add": 0.7,
    "outfit_save": 0.6,
    
    # Medium-weight signals
    "cart_add": 0.5,
    "try_on_attempt": 0.4,
    "product_view": 0.3,
    "search_query": 0.2,
    
    # Negative signals
    "outfit_reject": -0.5,
    "return": -0.7,
    "cart_abandon": -0.3,
    "try_on_failure": -0.2,
}

SIGNAL_DECAY = {
    "purchase": None,  # Never decay
    "outfit_accept": 180,  # 6 months
    "try_on_success": 90,  # 3 months
    "cart_add": 30,  # 1 month
    "product_view": 7,  # 1 week
}


# ── Unified Ecosystem Service ──────────────────────────────────────────

class UnifiedEcosystemService:
    """
    Central orchestrator for cross-group communication.
    
    Responsibilities:
    1. Event Bus: Route events between feature groups
    2. Signal Aggregation: Combine signals from all sources
    3. Feedback Loops: Learn from user actions across groups
    4. Identity Evolution: Track how user preferences change
    5. Shared Intelligence: Provide unified user context to all groups
    """
    
    def __init__(self, db: Session):
        self._db = db
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._signal_buffer: List[Dict] = []
        
    # ── Event Bus ───────────────────────────────────────────────────────
    
    def subscribe(self, event_type: EcosystemEvent, handler: Callable) -> None:
        """Subscribe to ecosystem events."""
        self._event_handlers[event_type.value].append(handler)
        logger.debug(f"Subscribed handler to {event_type.value}")
    
    async def emit(self, event_type: EcosystemEvent, payload: Dict[str, Any]) -> None:
        """
        Emit an event to all subscribers.
        
        Events flow between groups:
        - Group 1 (Identity) → Groups 2,3,5: User context updates
        - Group 2 (Styling) → Groups 3,5: Outfit recommendations
        - Group 3 (Try-On) → Groups 2,5: Fit confidence, size predictions
        - Group 5 (Commerce) → Groups 1,2: Purchase patterns, returns
        """
        event_data = {
            "event_type": event_type.value,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Log event for audit trail
        logger.info(f"Ecosystem event: {event_type.value}", extra=event_data)
        
        # Notify all subscribers
        handlers = self._event_handlers.get(event_type.value, [])
        for handler in handlers:
            try:
                result = handler(event_data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Event handler failed for {event_type.value}: {e}")
        
        # Store event for analytics
        await self._store_event(event_data)
    
    async def _store_event(self, event_data: Dict) -> None:
        """Store event for analytics and replay."""
        # Buffer for batch insert
        self._signal_buffer.append(event_data)
        
        # Flush when buffer reaches threshold
        if len(self._signal_buffer) >= 100:
            await self._flush_events()
    
    async def _flush_events(self) -> None:
        """Flush buffered events to database."""
        if not self._signal_buffer:
            return
            
        try:
            # Batch insert would go here
            self._signal_buffer.clear()
        except Exception as e:
            logger.error(f"Failed to flush events: {e}")
    
    # ── Cross-Group Integration Methods ────────────────────────────────
    
    async def connect_tryon_to_checkout(
        self,
        user_id: str,
        garment_id: str,
        tryon_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Connect Group 3 (Try-On) to Group 5 (Checkout).
        
        Flow:
        1. Try-on provides fit confidence
        2. Fit confidence influences purchase confidence
        3. Size prediction pre-fills checkout
        4. Visual feedback loop for future predictions
        """
        fit_confidence = tryon_result.get("fitConfidence", 0.5)
        predicted_size = tryon_result.get("predictedSize", "M")
        quality_score = tryon_result.get("qualityScore", 0.5)
        
        # Emit try-on complete event
        await self.emit(EcosystemEvent.TRY_ON_COMPLETE, {
            "user_id": user_id,
            "garment_id": garment_id,
            "fit_confidence": fit_confidence,
            "predicted_size": predicted_size,
            "quality_score": quality_score,
        })
        
        # Calculate checkout readiness
        checkout_readiness = self._calculate_checkout_readiness(
            fit_confidence=fit_confidence,
            quality_score=quality_score,
        )
        
        return {
            "checkout_ready": checkout_readiness["ready"],
            "confidence_boost": checkout_readiness["confidence_boost"],
            "suggested_size": predicted_size,
            "fit_notes": tryon_result.get("fitIssues", []),
            "should_prefer_bnp": fit_confidence > 0.7,  # High fit = good BNPL candidate
        }
    
    def _calculate_checkout_readiness(
        self,
        fit_confidence: float,
        quality_score: float,
    ) -> Dict[str, Any]:
        """Calculate if user is ready to proceed to checkout."""
        combined_score = (fit_confidence * 0.7 + quality_score * 0.3)
        
        return {
            "ready": combined_score > 0.5,
            "confidence_boost": combined_score * 10,  # 0-10 point boost
            "readiness_level": "high" if combined_score > 0.8 else "medium" if combined_score > 0.5 else "low",
        }
    
    async def connect_styling_to_cart(
        self,
        user_id: str,
        outfit: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Connect Group 2 (Styling) to Group 5 (Cart).
        
        Flow:
        1. Outfit builder creates styled look
        2. User can add entire outfit to cart
        3. Cart optimization considers outfit context
        4. Purchase confidence includes style alignment
        """
        items = outfit.get("items", [])
        style_score = outfit.get("styleScore", 0)
        occasion = outfit.get("occasion", "casual")
        
        # Calculate bundle opportunity
        bundle_savings = self._calculate_bundle_savings(items)
        
        # Emit outfit created event
        await self.emit(EcosystemEvent.OUTFIT_CREATED, {
            "user_id": user_id,
            "outfit_id": outfit.get("id"),
            "item_count": len(items),
            "style_score": style_score,
            "occasion": occasion,
        })
        
        return {
            "can_add_to_cart": True,
            "items": items,
            "bundle_savings": bundle_savings,
            "style_alignment_score": style_score,
            "purchase_confidence_boost": style_score * 5,
            "occasion_match": occasion,
        }
    
    def _calculate_bundle_savings(self, items: List[Dict]) -> float:
        """Calculate potential bundle savings for outfit items."""
        if len(items) < 2:
            return 0
        
        total = sum(i.get("price", 0) for i in items)
        
        # Check for same-brand items
        brands = [i.get("brand") for i in items]
        same_brand_count = len([b for b in brands if brands.count(b) >= 2])
        
        if same_brand_count >= 2:
            return total * 0.10  # 10% bundle discount
        
        return 0
    
    async def connect_purchase_to_ai_brain(
        self,
        user_id: str,
        order: Dict[str, Any],
    ) -> None:
        """
        Connect Group 5 (Purchase) to AI Brain (Group 2).
        
        Flow:
        1. Purchase completed
        2. Update user style profile with purchase patterns
        3. Adjust future recommendations
        4. Track brand affinity evolution
        """
        items = order.get("items", [])
        total = order.get("total", 0)
        
        # Emit purchase complete event
        await self.emit(EcosystemEvent.PURCHASE_COMPLETE, {
            "user_id": user_id,
            "order_id": order.get("id"),
            "item_count": len(items),
            "total": total,
            "categories": list(set(i.get("category") for i in items)),
            "brands": list(set(i.get("brand") for i in items)),
        })
        
        # Update style profile
        await self._update_style_profile_from_purchase(user_id, items)
    
    async def _update_style_profile_from_purchase(
        self,
        user_id: str,
        items: List[Dict],
    ) -> None:
        """Update user style profile based on purchase."""
        try:
            profile = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
            if not profile:
                return
            
            # Track category purchases
            categories = [i.get("category") for i in items]
            for cat in categories:
                # Would update category affinity
                pass
            
            # Track brand purchases
            brands = [i.get("brand") for i in items]
            for brand in brands:
                # Would update brand affinity
                pass
            
            self._db.commit()
        except Exception as e:
            logger.error(f"Failed to update style profile: {e}")
    
    async def connect_return_to_learning(
        self,
        user_id: str,
        return_request: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Connect Group 5 (Returns) to AI Brain learning.
        
        Flow:
        1. Return initiated
        2. Learn from return reasons
        3. Adjust future recommendations
        4. Update size/fit predictions
        """
        reason = return_request.get("reason", "")
        items = return_request.get("items", [])
        
        # Emit return event
        await self.emit(EcosystemEvent.RETURN_INITIATED, {
            "user_id": user_id,
            "return_id": return_request.get("id"),
            "reason": reason,
            "item_categories": [i.get("category") for i in items],
        })
        
        # Determine learning impact
        learning_impact = self._analyze_return_impact(reason, items)
        
        return {
            "style_adjustments": learning_impact["style_adjustments"],
            "size_adjustments": learning_impact["size_adjustments"],
            "brand_adjustments": learning_impact["brand_adjustments"],
            "future_recommendations_impact": learning_impact["overall_impact"],
        }
    
    def _analyze_return_impact(
        self,
        reason: str,
        items: List[Dict],
    ) -> Dict[str, Any]:
        """Analyze how return should impact future recommendations."""
        impact = {
            "style_adjustments": [],
            "size_adjustments": [],
            "brand_adjustments": [],
            "overall_impact": 0.0,
        }
        
        # Size-related returns
        if "size" in reason.lower() or "fit" in reason.lower():
            impact["size_adjustments"] = ["review_size_predictions"]
            impact["overall_impact"] = 0.3
        
        # Style-related returns
        if "style" in reason.lower() or "not as expected" in reason.lower():
            impact["style_adjustments"] = ["reduce_similar_recommendations"]
            impact["overall_impact"] = 0.5
        
        # Quality-related returns
        if "quality" in reason.lower():
            impact["brand_adjustments"] = ["flag_brand_quality"]
            impact["overall_impact"] = 0.2
        
        return impact
    
    # ── Unified Intelligence Layer ─────────────────────────────────────
    
    async def get_unified_user_context(
        self,
        user_id: str,
        context_type: str = "full",
    ) -> Dict[str, Any]:
        """
        Get unified user context for any feature group.
        
        This is the single source of truth for user intelligence.
        All groups should call this instead of maintaining separate profiles.
        """
        # Aggregate from all sources
        style_profile = await self._get_style_profile(user_id)
        behavior_signals = await self._get_behavior_signals(user_id)
        purchase_history = await self._get_purchase_history(user_id)
        try_on_history = await self._get_try_on_history(user_id)
        confidence_profile = await self._get_confidence_profile(user_id)
        
        return {
            "user_id": user_id,
            "identity": {
                "style_archetype": style_profile.get("primary_archetype"),
                "style_dimensions": style_profile.get("style_dimensions", {}),
                "brand_affinities": style_profile.get("brand_affinities", []),
            },
            "behavior": {
                "top_categories": behavior_signals.get("top_categories", []),
                "price_sensitivity": behavior_signals.get("price_sensitivity", 0.5),
                "engagement_level": behavior_signals.get("engagement_level", "medium"),
            },
            "commerce": {
                "purchase_count": purchase_history.get("count", 0),
                "total_spent": purchase_history.get("total", 0),
                "return_rate": purchase_history.get("return_rate", 0),
                "avg_order_value": purchase_history.get("avg_order", 0),
            },
            "try_on": {
                "sessions_count": try_on_history.get("count", 0),
                "avg_fit_confidence": try_on_history.get("avg_fit_confidence", 0.5),
                "preferred_sizes": try_on_history.get("preferred_sizes", {}),
            },
            "confidence": {
                "overall": confidence_profile.get("overall", 50),
                "dimensions": confidence_profile.get("dimensions", {}),
                "growth_rate": confidence_profile.get("growth_rate", 0),
            },
            "context_timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    async def _get_style_profile(self, user_id: str) -> Dict:
        """Get user style profile."""
        profile = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        if profile:
            return {
                "primary_archetype": getattr(profile, "primary_archetype", None),
                "style_dimensions": getattr(profile, "style_dimensions", {}),
                "brand_affinities": [],  # Would query
            }
        return {}
    
    async def _get_behavior_signals(self, user_id: str) -> Dict:
        """Get aggregated behavior signals."""
        signals = self._db.query(UserBehaviorSignal).filter_by(user_id=user_id).all()
        
        if not signals:
            return {}
        
        # Aggregate signals
        categories = defaultdict(float)
        for signal in signals:
            entity_type = getattr(signal, "entity_type", None)
            if entity_type == "category":
                entity_id = getattr(signal, "entity_id", "")
                weight = getattr(signal, "weight", 0)
                categories[entity_id] += weight
        
        return {
            "top_categories": sorted(categories.keys(), key=lambda k: categories[k], reverse=True)[:5],
            "price_sensitivity": 0.5,  # Would calculate
            "engagement_level": "medium" if len(signals) > 10 else "low",
        }
    
    async def _get_purchase_history(self, user_id: str) -> Dict:
        """Get purchase history summary."""
        orders = self._db.query(Order).filter_by(user_id=user_id).all()
        
        if not orders:
            return {"count": 0, "total": 0, "return_rate": 0, "avg_order": 0}
        
        total = sum(float(o.total or 0) for o in orders)
        returns = sum(1 for o in orders if o.status == "returned")
        
        return {
            "count": len(orders),
            "total": total,
            "return_rate": returns / len(orders) if orders else 0,
            "avg_order": total / len(orders) if orders else 0,
        }
    
    async def _get_try_on_history(self, user_id: str) -> Dict:
        """Get try-on history summary."""
        # Would query try-on sessions
        return {
            "count": 0,
            "avg_fit_confidence": 0.5,
            "preferred_sizes": {},
        }
    
    async def _get_confidence_profile(self, user_id: str) -> Dict:
        """Get confidence profile."""
        # Would query confidence service
        return {
            "overall": 50,
            "dimensions": {},
            "growth_rate": 0,
        }
    
    # ── Identity Evolution Tracking ─────────────────────────────────────
    
    async def track_identity_evolution(
        self,
        user_id: str,
        event_type: str,
        previous_state: Dict,
        new_state: Dict,
        trigger: str = "explicit",
    ) -> None:
        """
        Track how user identity evolves over time.
        
        This enables:
        - "Your Style Journey" insights
        - Predictive trend recommendations
        - Churn prevention (detect style drift)
        - Brand partnership insights
        """
        evolution = UserStyleEvolution(
            user_id=user_id,
            event_type=event_type,
            previous_state=json.dumps(previous_state),
            new_state=json.dumps(new_state),
            trigger=trigger,
            created_at=datetime.now(timezone.utc),
        )
        
        self._db.add(evolution)
        self._db.commit()
        
        # Emit evolution event
        await self.emit(EcosystemEvent.USER_STYLE_EVOLUTION, {
            "user_id": user_id,
            "event_type": event_type,
            "trigger": trigger,
        })
    
    # ── Feedback Learning Loops ─────────────────────────────────────────
    
    async def process_feedback_loop(
        self,
        user_id: str,
        feedback_type: str,
        feedback_data: Dict,
    ) -> Dict[str, Any]:
        """
        Process feedback and update all relevant systems.
        
        Feedback flows:
        1. Outfit rejection → Update style predictions
        2. Return → Update size predictions, brand affinity
        3. Try-on failure → Update pose recommendations
        4. Cart abandon → Update urgency, pricing signals
        """
        # Determine which systems need updates
        updates_needed = self._determine_feedback_updates(feedback_type, feedback_data)
        
        # Apply updates
        results = {}
        for system, update in updates_needed.items():
            try:
                result = await self._apply_feedback_update(user_id, system, update)
                results[system] = result
            except Exception as e:
                logger.error(f"Failed to apply feedback to {system}: {e}")
                results[system] = {"error": str(e)}
        
        # Emit feedback event
        await self.emit(EcosystemEvent.RECOMMENDATION_FEEDBACK, {
            "user_id": user_id,
            "feedback_type": feedback_type,
            "updates_applied": list(updates_needed.keys()),
        })
        
        return {
            "feedback_processed": True,
            "systems_updated": results,
            "learning_impact": self._calculate_learning_impact(feedback_type),
        }
    
    def _determine_feedback_updates(
        self,
        feedback_type: str,
        feedback_data: Dict,
    ) -> Dict[str, Dict]:
        """Determine which systems need updates based on feedback."""
        updates = {}
        
        if feedback_type == "outfit_reject":
            updates["style_predictions"] = {
                "action": "reduce_similar",
                "data": feedback_data,
            }
            updates["recommendations"] = {
                "action": "adjust_ranking",
                "data": feedback_data,
            }
        
        elif feedback_type == "return":
            updates["size_predictions"] = {
                "action": "recalibrate",
                "data": feedback_data,
            }
            updates["brand_affinity"] = {
                "action": "reduce" if feedback_data.get("reason") != "quality" else "flag",
                "data": feedback_data,
            }
        
        elif feedback_type == "try_on_failure":
            updates["pose_recommendations"] = {
                "action": "improve_guidance",
                "data": feedback_data,
            }
        
        elif feedback_type == "cart_abandon":
            updates["urgency_signals"] = {
                "action": "increase",
                "data": feedback_data,
            }
            updates["pricing_sensitivity"] = {
                "action": "recalibrate",
                "data": feedback_data,
            }
        
        return updates
    
    async def _apply_feedback_update(
        self,
        user_id: str,
        system: str,
        update: Dict,
    ) -> Dict:
        """Apply feedback update to a specific system."""
        # Would implement actual updates
        return {"system": system, "action": update["action"], "status": "applied"}
    
    def _calculate_learning_impact(self, feedback_type: str) -> float:
        """Calculate how much this feedback should impact learning."""
        impacts = {
            "outfit_reject": 0.3,
            "return": 0.5,
            "try_on_failure": 0.2,
            "cart_abandon": 0.1,
            "purchase": 0.8,
            "outfit_accept": 0.6,
        }
        return impacts.get(feedback_type, 0.1)


def get_unified_ecosystem_service(db: Session = Depends(get_db)) -> UnifiedEcosystemService:
    return UnifiedEcosystemService(db)
