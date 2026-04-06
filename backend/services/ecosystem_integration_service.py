"""
CONFIT Backend — Ecosystem Integration Service
==============================================
Central orchestration layer ensuring all feature groups work as ONE unified intelligent ecosystem.

This service:
- Coordinates cross-feature workflows
- Ensures signal consistency across groups
- Manages unified user journey
- Triggers cascading updates when user data changes
- Provides event-driven communication between services

GROUP Coverage:
- GROUP 1: User Identity & USP
- GROUP 2: Discovery & Styling Experience (Virtual Stylist, Outfit Builder)
- GROUP 3: Virtual Try-On
- GROUP 4: Virtual Wardrobe
- GROUP 5: Marketplace & Commerce
- GROUP 6: Budget Intelligence
- GROUP 7: Social & Community
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from collections import defaultdict
import asyncio

from fastapi import Depends
from sqlalchemy.orm import Session

from database.session import get_db

from services.identity_intelligence_service import IdentityIntelligenceService
from services.ai_brain_service import AIBrainService
from services.confidence_service import ConfidenceService
from services.behavior_signal_service import BehaviorSignalService

logger = logging.getLogger(__name__)


# ── Event Types for Cross-Feature Communication ────────────────────────

class EcosystemEvent(Enum):
    """Events that trigger cross-feature updates."""
    
    # Identity Events
    ONBOARDING_COMPLETED = "onboarding_completed"
    STYLE_PROFILE_UPDATED = "style_profile_updated"
    BODY_PROFILE_UPDATED = "body_profile_updated"
    BUDGET_PROFILE_UPDATED = "budget_profile_updated"
    
    # Styling Events (GROUP 2)
    STYLIST_CONVERSATION = "stylist_conversation"
    OUTFIT_CREATED = "outfit_created"
    OUTFIT_SAVED = "outfit_saved"
    OUTFIT_SHARED = "outfit_shared"
    OUTFIT_TRYON = "outfit_tryon"
    RECOMMENDATION_ACCEPTED = "recommendation_accepted"
    RECOMMENDATION_REJECTED = "recommendation_rejected"
    
    # Try-On Events (GROUP 3)
    TRYON_COMPLETED = "tryon_completed"
    TRYON_SHARED = "tryon_shared"
    DIGITAL_TWIN_UPDATED = "digital_twin_updated"
    
    # Wardrobe Events (GROUP 4)
    WARDROBE_ITEM_ADDED = "wardrobe_item_added"
    WARDROBE_ITEM_WORN = "wardrobe_item_worn"
    WARDROBE_ITEM_REMOVED = "wardrobe_item_removed"
    CAPSULE_DETECTED = "capsule_detected"
    
    # Commerce Events (GROUP 5)
    PRODUCT_VIEWED = "product_viewed"
    PRODUCT_WISHLISTED = "product_wishlisted"
    CART_UPDATED = "cart_updated"
    ORDER_PLACED = "order_placed"
    ORDER_DELIVERED = "order_delivered"
    RETURN_INITIATED = "return_initiated"
    
    # Budget Events (GROUP 6)
    BUDGET_LIMIT_REACHED = "budget_limit_reached"
    BNPL_APPLIED = "bnpl_applied"
    PRICE_ALERT_TRIGGERED = "price_alert_triggered"
    
    # Social Events (GROUP 7)
    POST_CREATED = "post_created"
    POST_VOTED = "post_voted"
    LOOKBOOK_CREATED = "lookbook_created"
    FOLLOW_ADDED = "follow_added"


# ── Event Handlers Registry ───────────────────────────────────────────

class EventHandlerRegistry:
    """
    Registry for event handlers across feature groups.
    Enables loose coupling between services.
    """
    
    def __init__(self):
        self._handlers: Dict[EcosystemEvent, List[Callable]] = defaultdict(list)
    
    def register(self, event: EcosystemEvent, handler: Callable) -> None:
        """Register a handler for an event type."""
        self._handlers[event].append(handler)
        logger.debug("Registered handler for %s: %s", event.value, handler.__name__)
    
    def get_handlers(self, event: EcosystemEvent) -> List[Callable]:
        """Get all handlers for an event type."""
        return self._handlers.get(event, [])
    
    def clear(self, event: EcosystemEvent = None) -> None:
        """Clear handlers for an event or all events."""
        if event:
            self._handlers[event] = []
        else:
            self._handlers.clear()


# Global registry instance
_event_registry = EventHandlerRegistry()


# ── Ecosystem Integration Service ─────────────────────────────────────

class EcosystemIntegrationService:
    """
    Central orchestration service for cross-feature integration.
    
    Responsibilities:
    1. Route events to appropriate handlers
    2. Ensure signal consistency across groups
    3. Trigger cascading updates
    4. Maintain user journey continuity
    5. Provide unified analytics hooks
    """
    
    def __init__(self, db: Session):
        self._db = db
        self._identity = IdentityIntelligenceService(db)
        self._ai_brain = AIBrainService(db)
        self._confidence = ConfidenceService(db)
        self._signals = BehaviorSignalService(db)
        
        # Register core handlers
        self._register_core_handlers()
    
    def _register_core_handlers(self) -> None:
        """Register handlers for core ecosystem events."""
        
        # Styling events → Update identity & confidence
        _event_registry.register(
            EcosystemEvent.STYLIST_CONVERSATION,
            self._handle_stylist_conversation
        )
        _event_registry.register(
            EcosystemEvent.OUTFIT_CREATED,
            self._handle_outfit_created
        )
        _event_registry.register(
            EcosystemEvent.RECOMMENDATION_ACCEPTED,
            self._handle_recommendation_accepted
        )
        _event_registry.register(
            EcosystemEvent.RECOMMENDATION_REJECTED,
            self._handle_recommendation_rejected
        )
        
        # Try-on events → Update style profile & confidence
        _event_registry.register(
            EcosystemEvent.TRYON_COMPLETED,
            self._handle_tryon_completed
        )
        
        # Commerce events → Update budget & preferences
        _event_registry.register(
            EcosystemEvent.ORDER_PLACED,
            self._handle_order_placed
        )
        
        # Wardrobe events → Update style evolution
        _event_registry.register(
            EcosystemEvent.WARDROBE_ITEM_WORN,
            self._handle_wardrobe_item_worn
        )
        _event_registry.register(
            EcosystemEvent.PRODUCT_VIEWED,
            self._handle_product_viewed
        )
        _event_registry.register(
            EcosystemEvent.PRODUCT_WISHLISTED,
            self._handle_product_wishlisted
        )
        _event_registry.register(
            EcosystemEvent.CART_UPDATED,
            self._handle_cart_updated
        )
    
    # ── Event Processing ───────────────────────────────────────────────
    
    async def emit_event(
        self,
        event: EcosystemEvent,
        user_id: str,
        data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Emit an ecosystem event and trigger all registered handlers.
        
        Returns aggregated results from all handlers.
        """
        handlers = _event_registry.get_handlers(event)
        results = {
            "event": event.value,
            "user_id": user_id,
            "handlers_triggered": 0,
            "updates": [],
        }
        
        if not handlers:
            logger.debug("No handlers registered for %s", event.value)
            return results
        
        for handler in handlers:
            try:
                result = await handler(user_id, data or {})
                if result:
                    results["handlers_triggered"] += 1
                    results["updates"].append(result)
            except Exception as e:
                logger.error(
                    "Handler %s failed for %s: %s",
                    handler.__name__, event.value, e
                )
        
        logger.info(
            "Event %s processed for %s: %d handlers triggered",
            event.value, user_id, results["handlers_triggered"]
        )
        
        return results
    
    # ── Core Event Handlers ────────────────────────────────────────────
    
    async def _handle_stylist_conversation(
        self,
        user_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle stylist conversation event.
        
        Updates:
        - Style preferences from conversation
        - Confidence engagement score
        - AI Brain signals
        """
        message = data.get("message", "")
        intent = data.get("intent", "")
        entities = data.get("entities", {})
        
        updates = {
            "type": "stylist_conversation",
            "style_updates": [],
            "confidence_delta": 0,
        }
        
        # Track interaction in AI Brain
        self._ai_brain.track_interaction(
            user_id=user_id,
            interaction_type="stylist_chat",
            entity_type="conversation",
            entity_id=data.get("conversation_id", "unknown"),
            context={
                "intent": intent,
                "entities": entities,
                "message_length": len(message),
            },
        )
        
        # Update style preferences if entities detected
        if entities.get("styles"):
            for style in entities["styles"]:
                updates["style_updates"].append(f"style_{style}")
        
        if entities.get("colors"):
            for color in entities["colors"]:
                updates["style_updates"].append(f"color_{color}")
        
        # Increment engagement confidence
        updates["confidence_delta"] = 0.5
        
        return updates
    
    async def _handle_outfit_created(
        self,
        user_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle outfit creation event.
        
        Updates:
        - Wardrobe compatibility score
        - Style alignment score
        - Budget tracking
        - AI Brain signals
        """
        outfit_id = data.get("outfit_id", "")
        items = data.get("items", [])
        occasion = data.get("occasion")
        total_price = data.get("total_price", 0)
        
        updates = {
            "type": "outfit_created",
            "outfit_id": outfit_id,
            "signals_tracked": [],
        }
        
        # Track outfit creation in AI Brain
        self._ai_brain.track_interaction(
            user_id=user_id,
            interaction_type="outfit_create",
            entity_type="outfit",
            entity_id=outfit_id,
            context={
                "item_count": len(items),
                "occasion": occasion,
                "total_price": total_price,
            },
        )
        updates["signals_tracked"].append("outfit_create")
        
        # Track occasion pattern
        if occasion:
            self._ai_brain.track_occasion_pattern(
                user_id=user_id,
                occasion=occasion,
                outfit_id=outfit_id,
            )
            updates["signals_tracked"].append("occasion_pattern")
        
        # Track budget behavior
        if total_price > 0:
            self._ai_brain.track_budget_behavior(
                user_id=user_id,
                action="outfit_create",
                amount=total_price,
            )
            updates["signals_tracked"].append("budget_behavior")
        
        # Update confidence scores
        self._confidence.recalculate(user_id, "outfit_created")
        updates["signals_tracked"].append("confidence_recalc")
        
        return updates
    
    async def _handle_recommendation_accepted(
        self,
        user_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle recommendation acceptance event.
        
        Updates:
        - Style alignment confidence
        - Preference reinforcement
        - AI Brain feedback loop
        """
        recommendation_id = data.get("recommendation_id", "")
        recommendation_type = data.get("type", "outfit")
        
        updates = {
            "type": "recommendation_accepted",
            "confidence_delta": 2.0,
        }
        
        # Track feedback in AI Brain
        self._ai_brain.track_outfit_feedback(
            user_id=user_id,
            outfit_id=recommendation_id,
            accepted=True,
            feedback_type="explicit",
        )

        # Also track unified recommendation acceptance signal for analytics/personalization.
        self._ai_brain.track_interaction(
            user_id=user_id,
            interaction_type="recommendation_accept",
            entity_type="recommendation",
            entity_id=recommendation_id,
            context={"recommendation_type": recommendation_type},
        )
        
        # Update style evolution
        self._ai_brain.update_style_evolution(
            user_id=user_id,
            event_type="recommendation_accept",
            previous_value={"id": recommendation_id},
            new_value={"accepted": True},
            trigger_source="user_action",
        )
        
        return updates

    async def _handle_recommendation_rejected(
        self,
        user_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle recommendation rejection event.
        
        We record both:
        - outfit_accepted/outfit_rejected signals (for preference drift logic)
        - recommendation_reject signals (for unified analytics/investor reporting)
        """
        recommendation_id = data.get("recommendation_id", "")
        recommendation_type = data.get("type", "outfit")

        updates = {
            "type": "recommendation_rejected",
            "confidence_delta": -2.0,
        }

        # Track feedback in AI Brain (keeps existing drift logic intact)
        self._ai_brain.track_outfit_feedback(
            user_id=user_id,
            outfit_id=recommendation_id,
            accepted=False,
            feedback_type="explicit",
        )

        # Track unified recommendation rejection signal
        self._ai_brain.track_interaction(
            user_id=user_id,
            interaction_type="recommendation_reject",
            entity_type="recommendation",
            entity_id=recommendation_id,
            context={"recommendation_type": recommendation_type},
        )

        # Update style evolution
        self._ai_brain.update_style_evolution(
            user_id=user_id,
            event_type="recommendation_reject",
            previous_value={"id": recommendation_id},
            new_value={"accepted": False},
            trigger_source="user_action",
        )

        return updates
    
    async def _handle_tryon_completed(
        self,
        user_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle virtual try-on completion event.
        
        Updates:
        - Fit confidence score
        - Brand affinity (if brand specified)
        - Size preference validation
        - AI Brain signals
        """
        product_id = data.get("product_id", "")
        brand = data.get("brand", "")
        category = data.get("category", "")
        fit_score = data.get("fit_score", 0)
        
        updates = {
            "type": "tryon_completed",
            "fit_confidence_delta": fit_score * 0.1,
        }
        
        # Track try-on in AI Brain
        self._ai_brain.track_interaction(
            user_id=user_id,
            interaction_type="tryon_complete",
            entity_type="product",
            entity_id=product_id,
            context={
                "brand": brand,
                "category": category,
                "fit_score": fit_score,
            },
        )
        
        # Track brand affinity
        if brand:
            self._ai_brain.track_brand_affinity(
                user_id=user_id,
                brand=brand,
                interaction_type="tryon_complete",
            )
        
        return updates

    async def _handle_product_viewed(
        self,
        user_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Track product discovery engagement for unified analytics."""
        product_id = data.get("product_id", "")
        if not product_id:
            return {"type": "product_viewed", "tracked": False}

        self._ai_brain.track_interaction(
            user_id=user_id,
            interaction_type="product_view",
            entity_type="product",
            entity_id=str(product_id),
            context={
                "category": data.get("category"),
                "brand": data.get("brand"),
                "price": data.get("price"),
                "source": data.get("source"),
            },
        )

        return {"type": "product_viewed", "tracked": True}

    async def _handle_product_wishlisted(
        self,
        user_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Track wishlist intent for unified analytics."""
        product_id = data.get("product_id", "")
        if not product_id:
            return {"type": "product_wishlisted", "tracked": False}

        self._ai_brain.track_interaction(
            user_id=user_id,
            interaction_type="wishlist_add",
            entity_type="product",
            entity_id=str(product_id),
            context={"source": data.get("source")},
        )

        return {"type": "product_wishlisted", "tracked": True}

    async def _handle_cart_updated(
        self,
        user_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Track cart add/remove signals for funnel analytics."""
        action = (data.get("action") or "").lower()
        if not action and isinstance(data.get("delta"), (int, float)):
            action = "add" if data["delta"] > 0 else "remove"

        if action not in {"add", "remove"}:
            return {"type": "cart_updated", "tracked": False}

        interaction_type = "cart_add" if action == "add" else "cart_remove"
        entity_id = str(data.get("product_id") or "cart")

        self._ai_brain.track_interaction(
            user_id=user_id,
            interaction_type=interaction_type,
            entity_type="cart_item",
            entity_id=entity_id,
            context={
                "source": data.get("source"),
                "delta": data.get("delta"),
                "cart_total": data.get("cart_total"),
            },
        )

        return {"type": "cart_updated", "tracked": True}
    
    async def _handle_order_placed(
        self,
        user_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle order placement event.
        
        Updates:
        - Budget tracking
        - Brand affinity reinforcement
        - Style profile evolution
        - Confidence scores
        """
        order_id = data.get("order_id", "")
        items = data.get("items", [])
        total = data.get("total", 0)
        
        updates = {
            "type": "order_placed",
            "budget_impact": total,
            "brands_purchased": [],
        }
        
        # Track purchase in AI Brain
        self._ai_brain.track_purchase_behavior(
            user_id=user_id,
            order_id=order_id,
            items=items,
            total=total,
            payment_method=data.get("payment_method", "unknown"),
        )
        
        # Track brand affinities
        brands = set(item.get("brand", "") for item in items if item.get("brand"))
        for brand in brands:
            self._ai_brain.track_brand_affinity(
                user_id=user_id,
                brand=brand,
                interaction_type="purchase",
            )
            updates["brands_purchased"].append(brand)
        
        # Update confidence
        self._confidence.recalculate(user_id, "purchase_made")
        
        return updates
    
    async def _handle_wardrobe_item_worn(
        self,
        user_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle wardrobe item worn event.
        
        Updates:
        - Wardrobe compatibility score
        - Item usage tracking
        - Style evolution
        """
        item_id = data.get("item_id", "")
        outfit_context = data.get("outfit_id")
        
        updates = {
            "type": "wardrobe_item_worn",
            "item_id": item_id,
        }
        
        # Track wear event
        self._ai_brain.track_interaction(
            user_id=user_id,
            interaction_type="item_worn",
            entity_type="wardrobe_item",
            entity_id=item_id,
            context={"outfit_id": outfit_context},
        )
        
        return updates
    
    # ── Cross-Feature Integration Methods ─────────────────────────────
    
    async def integrate_stylist_with_tryon(
        self,
        user_id: str,
        outfit_id: str,
        items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Integrate stylist recommendations with virtual try-on.
        
        Flow: Stylist → Outfit Builder → Try-On
        """
        # Get user's body context for try-on
        tryon_context = self._identity.get_tryon_context(user_id)
        
        # Determine which items can be tried on
        tryon_candidates = []
        for item in items:
            category = item.get("category", "").lower()
            if category in ["tops", "bottoms", "dresses", "outerwear"]:
                tryon_candidates.append({
                    "product_id": item.get("id"),
                    "category": category,
                    "brand": item.get("brand"),
                    "image_url": item.get("image"),
                })
        
        # Track integration event
        await self.emit_event(
            EcosystemEvent.OUTFIT_TRYON,
            user_id,
            {"outfit_id": outfit_id, "tryon_candidates": len(tryon_candidates)}
        )
        
        return {
            "tryon_available": len(tryon_candidates) > 0,
            "tryon_candidates": tryon_candidates,
            "body_context": tryon_context,
        }
    
    async def integrate_outfit_with_wardrobe(
        self,
        user_id: str,
        outfit_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Integrate outfit builder with virtual wardrobe.
        
        Checks wardrobe compatibility and suggests reusing owned items.
        """
        from database.models import WardrobeItem
        
        # Get user's wardrobe
        wardrobe = self._db.query(WardrobeItem).filter_by(
            owner_user_id=user_id
        ).all()
        
        wardrobe_by_category = defaultdict(list)
        for item in wardrobe:
            wardrobe_by_category[item.category].append({
                "id": item.id,
                "name": item.name,
                "brand": item.brand,
                "color": item.color,
                "image_url": item.image_url,
            })
        
        # Check for matching items
        integration_suggestions = []
        for outfit_item in outfit_items:
            category = outfit_item.get("category", "").lower()
            if category in wardrobe_by_category:
                # Find similar items in wardrobe
                for wardrobe_item in wardrobe_by_category[category]:
                    if self._items_similar(outfit_item, wardrobe_item):
                        integration_suggestions.append({
                            "outfit_item": outfit_item.get("name"),
                            "wardrobe_alternative": wardrobe_item,
                            "savings": outfit_item.get("price", 0),
                            "message": f"You already have {wardrobe_item['name']} in your wardrobe!",
                        })
        
        return {
            "wardrobe_items_available": len(wardrobe),
            "integration_suggestions": integration_suggestions,
            "potential_savings": sum(s["savings"] for s in integration_suggestions),
        }
    
    def _items_similar(self, item1: Dict, item2: Dict) -> bool:
        """Check if two items are similar enough to suggest substitution."""
        # Same category
        if item1.get("category", "").lower() != item2.get("category", "").lower():
            return False
        
        # Similar color
        color1 = item1.get("color", "").lower() if item1.get("color") else ""
        color2 = item2.get("color", "").lower() if item2.get("color") else ""
        
        # Allow neutral color substitutions
        neutrals = {"black", "white", "grey", "gray", "navy", "beige"}
        if color1 in neutrals and color2 in neutrals:
            return True
        
        # Exact color match
        if color1 and color2 and color1 == color2:
            return True
        
        return False
    
    async def integrate_stylist_with_commerce(
        self,
        user_id: str,
        recommendations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Integrate stylist recommendations with marketplace commerce.
        
        Adds purchase links, availability, and pricing.
        """
        # Get commerce context
        commerce_context = self._identity.get_commerce_context(user_id)
        budget_max = commerce_context.get("budget_context", {}).get("per_item_range", {}).get("max")
        
        enriched_recommendations = []
        for rec in recommendations:
            enriched = rec.copy()
            
            # Add commerce metadata
            enriched["commerce"] = {
                "available": True,  # Would check inventory
                "price": rec.get("price", 0),
                "within_budget": budget_max is None or rec.get("price", 0) <= budget_max,
                "purchase_url": f"/products/{rec.get('id', '')}",
            }
            
            # Add BNPL eligibility
            if rec.get("price", 0) >= 35:
                enriched["commerce"]["bnpl_eligible"] = True
                enriched["commerce"]["bnpl_options"] = [
                    {"provider": "affirm", "installments": 4, "per_payment": round(rec.get("price", 0) / 4, 2)},
                    {"provider": "klarna", "installments": 4, "per_payment": round(rec.get("price", 0) / 4, 2)},
                ]
            
            enriched_recommendations.append(enriched)
        
        return {
            "recommendations": enriched_recommendations,
            "budget_context": commerce_context.get("budget_context"),
            "total_within_budget": sum(1 for r in enriched_recommendations if r.get("commerce", {}).get("within_budget")),
        }
    
    async def integrate_outfit_with_social(
        self,
        user_id: str,
        outfit_id: str,
        outfit_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Integrate outfit builder with social features.
        
        Enables sharing to social feed.
        """
        return {
            "shareable": True,
            "share_options": [
                {
                    "type": "feed",
                    "label": "Share to CONFIT Feed",
                    "endpoint": "/api/social/posts",
                },
                {
                    "type": "lookbook",
                    "label": "Add to Lookbook",
                    "endpoint": "/api/social/lookbooks",
                },
                {
                    "type": "link",
                    "label": "Copy Share Link",
                    "link": f"/shared/outfit/{outfit_data.get('share_slug', outfit_id)}",
                },
            ],
            "outfit_preview": {
                "image": outfit_data.get("preview_image"),
                "title": outfit_data.get("title"),
                "style_score": outfit_data.get("style_score"),
            },
        }
    
    # ── Unified User Journey ───────────────────────────────────────────
    
    async def get_user_journey_state(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get current state of user's journey across all features.
        
        Provides unified view for progressive personalization.
        """
        # Get full identity
        identity = self._identity.get_full_identity(user_id)
        
        # Get confidence scores
        confidence = self._confidence.get_profile(user_id)
        
        # Get recent signals summary
        signals = self._signals.get_preference_summary(user_id)
        
        # Determine journey phase
        journey_phase = self._determine_journey_phase(identity, confidence, signals)
        
        return {
            "user_id": user_id,
            "journey_phase": journey_phase,
            "identity_completeness": identity.get("identity_completeness", 0),
            "confidence_level": float(confidence.overall_confidence) if confidence else 0,
            "signal_strength": signals.get("total_signals", 0),
            "recommended_next_actions": self._get_next_actions(journey_phase, identity),
            "feature_engagement": {
                "stylist": signals.get("feature_usage", {}).get("stylist", 0),
                "tryon": signals.get("feature_usage", {}).get("tryon", 0),
                "wardrobe": signals.get("feature_usage", {}).get("wardrobe", 0),
                "outfits": signals.get("feature_usage", {}).get("outfits", 0),
                "social": signals.get("feature_usage", {}).get("social", 0),
            },
        }
    
    def _determine_journey_phase(
        self,
        identity: Dict[str, Any],
        confidence: Any,
        signals: Dict[str, Any],
    ) -> str:
        """Determine user's journey phase for progressive personalization."""
        
        # New user
        if not identity.get("onboarding_status", {}).get("completed"):
            return "onboarding"
        
        # Exploring
        if signals.get("total_signals", 0) < 10:
            return "exploring"
        
        # Engaged
        if signals.get("total_signals", 0) < 50:
            return "engaged"
        
        # Proficient
        if float(confidence.overall_confidence or 0) < 70:
            return "proficient"
        
        # Expert
        return "expert"
    
    def _get_next_actions(
        self,
        phase: str,
        identity: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Get recommended next actions for user journey progression."""
        
        actions = {
            "onboarding": [
                {"action": "complete_style_quiz", "priority": 1, "feature": "identity"},
                {"action": "add_body_measurements", "priority": 2, "feature": "identity"},
                {"action": "set_budget_preferences", "priority": 3, "feature": "identity"},
            ],
            "exploring": [
                {"action": "try_virtual_stylist", "priority": 1, "feature": "stylist"},
                {"action": "build_first_outfit", "priority": 2, "feature": "outfits"},
                {"action": "add_wardrobe_items", "priority": 3, "feature": "wardrobe"},
            ],
            "engaged": [
                {"action": "try_virtual_tryon", "priority": 1, "feature": "tryon"},
                {"action": "create_lookbook", "priority": 2, "feature": "social"},
                {"action": "discover_new_brands", "priority": 3, "feature": "marketplace"},
            ],
            "proficient": [
                {"action": "optimize_wardrobe", "priority": 1, "feature": "wardrobe"},
                {"action": "share_style", "priority": 2, "feature": "social"},
                {"action": "set_style_goals", "priority": 3, "feature": "identity"},
            ],
            "expert": [
                {"action": "mentor_others", "priority": 1, "feature": "social"},
                {"action": "curate_lookbook", "priority": 2, "feature": "social"},
                {"action": "advanced_styling", "priority": 3, "feature": "stylist"},
            ],
        }
        
        return actions.get(phase, actions["exploring"])


def get_ecosystem_service(db: Session = Depends(get_db)) -> EcosystemIntegrationService:
    """Factory function for ecosystem integration service."""
    return EcosystemIntegrationService(db)
