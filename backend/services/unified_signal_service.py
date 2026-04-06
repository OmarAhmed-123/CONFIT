"""
CONFIT Backend — Unified Signal Synchronization Service
=======================================================
Ensures all feature groups contribute to and consume from a single
source of truth for user intelligence signals.

This service:
- Prevents signal duplication across groups
- Maintains signal consistency
- Provides unified signal aggregation
- Enables cross-feature signal sharing
- Implements signal versioning and conflict resolution
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict
from decimal import Decimal
import json

from fastapi import Depends
from sqlalchemy.orm import Session

from database.session import get_db
from sqlalchemy import and_, or_, func

from models.profile_models import UserBehaviorSignal, UserStyleEvolution
from services.behavior_signal_service import BehaviorSignalService

logger = logging.getLogger(__name__)


# ── Signal Categories by Feature Group ────────────────────────────────

SIGNAL_CATEGORIES = {
    "identity": {
        "group": "GROUP_1",
        "signals": [
            "profile_update", "style_quiz_complete", "body_measurement",
            "budget_set", "preference_change", "onboarding_step",
        ],
        "weight": 1.0,
    },
    "styling": {
        "group": "GROUP_2",
        "signals": [
            "stylist_chat", "outfit_create", "outfit_save", "outfit_share",
            "recommendation_accept", "recommendation_reject", "style_score",
        ],
        "weight": 0.9,
    },
    "tryon": {
        "group": "GROUP_3",
        "signals": [
            "tryon_start", "tryon_complete", "tryon_share", "fit_feedback",
            "size_preference", "digital_twin_update",
        ],
        "weight": 0.85,
    },
    "wardrobe": {
        "group": "GROUP_4",
        "signals": [
            "wardrobe_add", "wardrobe_remove", "item_worn", "outfit_logged",
            "capsule_detected", "declutter_suggestion",
        ],
        "weight": 0.8,
    },
    "commerce": {
        "group": "GROUP_5",
        "signals": [
            "product_view", "wishlist_add", "cart_add", "cart_remove",
            "purchase", "return", "review_submit",
        ],
        "weight": 0.95,
    },
    "budget": {
        "group": "GROUP_6",
        "signals": [
            "budget_alert", "bnpl_apply", "price_sensitivity", "savings_goal",
            "spending_pattern",
        ],
        "weight": 0.75,
    },
    "social": {
        "group": "GROUP_7",
        "signals": [
            "post_create", "post_vote", "lookbook_create", "follow_add",
            "style_inspiration", "community_engagement",
        ],
        "weight": 0.7,
    },
}


# ── Signal Conflict Resolution Rules ─────────────────────────────────

CONFLICT_RESOLUTION = {
    "style_preference": {
        "strategy": "most_recent",
        "sources": ["stylist_chat", "style_quiz_complete", "outfit_create"],
    },
    "color_preference": {
        "strategy": "frequency_weighted",
        "sources": ["stylist_chat", "wardrobe_add", "purchase", "tryon_complete"],
    },
    "brand_affinity": {
        "strategy": "cumulative",
        "sources": ["purchase", "wishlist_add", "tryon_complete", "product_view"],
    },
    "budget_behavior": {
        "strategy": "rolling_average",
        "sources": ["purchase", "cart_add", "price_sensitivity", "savings_goal"],
    },
    "size_preference": {
        "strategy": "most_recent_verified",
        "sources": ["tryon_complete", "purchase", "body_measurement"],
    },
}


class UnifiedSignalService:
    """
    Unified signal synchronization and aggregation service.
    
    Provides:
    - Single source of truth for user signals
    - Cross-feature signal sharing
    - Conflict resolution
    - Signal versioning
    - Unified aggregation for AI Brain
    """
    
    def __init__(self, db: Session):
        self._db = db
        self._signal_service = BehaviorSignalService(db)
        self._signal_cache: Dict[str, Dict[str, Any]] = {}
    
    # ── Signal Registration ───────────────────────────────────────────
    
    def register_signal(
        self,
        user_id: str,
        signal_type: str,
        entity_type: str,
        entity_id: str,
        context: Dict[str, Any] = None,
        source_group: str = None,
        duration_ms: int = None,
        validate_uniqueness: bool = True,
    ) -> Dict[str, Any]:
        """
        Register a signal with uniqueness validation.
        
        Prevents duplicate signals from different feature groups
        representing the same user action.
        """
        # Check for duplicates
        if validate_uniqueness:
            existing = self._check_duplicate_signal(
                user_id, signal_type, entity_type, entity_id
            )
            if existing:
                logger.debug(
                    "Duplicate signal detected: %s/%s for %s, updating instead",
                    signal_type, entity_id, user_id
                )
                return self._update_existing_signal(existing, context)
        
        # Register new signal
        signal = self._signal_service.track(
            user_id=user_id,
            signal_type=signal_type,
            entity_type=entity_type,
            entity_id=entity_id,
            context=context,
            duration_ms=duration_ms,
        )
        
        # Add source group metadata
        if source_group and signal:
            signal_context = signal.context or {}
            signal_context["_source_group"] = source_group
            signal.context = signal_context
            self._db.commit()
        
        # Invalidate cache
        self._invalidate_cache(user_id)
        
        return signal.model_dump() if signal else {}
    
    def _check_duplicate_signal(
        self,
        user_id: str,
        signal_type: str,
        entity_type: str,
        entity_id: str,
        time_window_minutes: int = 5,
    ) -> Optional[UserBehaviorSignal]:
        """Check for recent duplicate signal."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
        
        return self._db.query(UserBehaviorSignal).filter(
            and_(
                UserBehaviorSignal.user_id == user_id,
                UserBehaviorSignal.signal_type == signal_type,
                UserBehaviorSignal.entity_type == entity_type,
                UserBehaviorSignal.entity_id == entity_id,
                UserBehaviorSignal.created_at >= cutoff,
            )
        ).first()
    
    def _update_existing_signal(
        self,
        signal: UserBehaviorSignal,
        new_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Update existing signal with new context."""
        if new_context:
            existing_context = signal.context or {}
            existing_context.update(new_context)
            existing_context["_duplicate_detected"] = True
            existing_context["_duplicate_count"] = existing_context.get("_duplicate_count", 0) + 1
            signal.context = existing_context
            self._db.commit()
        
        return signal.model_dump() if hasattr(signal, 'model_dump') else {}
    
    # ── Unified Aggregation ───────────────────────────────────────────
    
    def get_unified_signals(
        self,
        user_id: str,
        categories: List[str] = None,
        time_window_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get unified signal aggregation across all feature groups.
        
        Returns signals organized by category with cross-group insights.
        """
        cache_key = f"{user_id}:{':'.join(categories or ['all'])}:{time_window_days}"
        
        if cache_key in self._signal_cache:
            return self._signal_cache[cache_key]
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=time_window_days)
        
        # Query all signals
        query = self._db.query(UserBehaviorSignal).filter(
            and_(
                UserBehaviorSignal.user_id == user_id,
                UserBehaviorSignal.created_at >= cutoff,
            )
        )
        
        signals = query.all()
        
        # Organize by category
        categorized = defaultdict(list)
        for signal in signals:
            category = self._get_signal_category(signal.signal_type)
            if categories is None or category in categories:
                categorized[category].append(signal)
        
        # Build unified view
        unified = {
            "user_id": user_id,
            "time_window_days": time_window_days,
            "total_signals": len(signals),
            "categories": {},
            "cross_group_insights": self._generate_cross_group_insights(signals),
            "signal_strength_by_group": {},
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        
        for category, category_signals in categorized.items():
            category_info = SIGNAL_CATEGORIES.get(category, {})
            
            unified["categories"][category] = {
                "count": len(category_signals),
                "weight": category_info.get("weight", 1.0),
                "group": category_info.get("group", "UNKNOWN"),
                "recent": [
                    {
                        "type": s.signal_type,
                        "entity_type": s.entity_type,
                        "created_at": s.created_at.isoformat(),
                    }
                    for s in sorted(category_signals, key=lambda x: x.created_at, reverse=True)[:5]
                ],
            }
            
            # Calculate signal strength per group
            group = category_info.get("group", "UNKNOWN")
            if group not in unified["signal_strength_by_group"]:
                unified["signal_strength_by_group"][group] = 0
            unified["signal_strength_by_group"][group] += len(category_signals) * category_info.get("weight", 1.0)
        
        # Cache result
        self._signal_cache[cache_key] = unified
        
        return unified
    
    def _get_signal_category(self, signal_type: str) -> str:
        """Determine category for a signal type."""
        for category, info in SIGNAL_CATEGORIES.items():
            if signal_type in info.get("signals", []):
                return category
        return "other"
    
    def _generate_cross_group_insights(
        self,
        signals: List[UserBehaviorSignal],
    ) -> List[Dict[str, Any]]:
        """Generate insights from cross-group signal patterns."""
        insights = []
        
        # Group signals by type
        signals_by_type = defaultdict(list)
        for s in signals:
            signals_by_type[s.signal_type].append(s)
        
        # Stylist → Purchase correlation
        stylist_chats = len(signals_by_type.get("stylist_chat", []))
        purchases = len(signals_by_type.get("purchase", []))
        
        if stylist_chats > 3 and purchases > 0:
            conversion_rate = purchases / stylist_chats
            insights.append({
                "type": "stylist_purchase_correlation",
                "message": f"Stylist conversations lead to {conversion_rate:.0%} purchase rate",
                "data": {"chats": stylist_chats, "purchases": purchases},
            })
        
        # Try-on → Wishlist correlation
        tryons = len(signals_by_type.get("tryon_complete", []))
        wishlist_adds = len(signals_by_type.get("wishlist_add", []))
        
        if tryons > 0 and wishlist_adds > 0:
            insights.append({
                "type": "tryon_engagement",
                "message": f"Virtual try-on drives engagement: {tryons} sessions, {wishlist_adds} wishlist adds",
                "data": {"tryons": tryons, "wishlist_adds": wishlist_adds},
            })
        
        # Wardrobe → Outfit correlation
        wardrobe_adds = len(signals_by_type.get("wardrobe_add", []))
        outfit_creates = len(signals_by_type.get("outfit_create", []))
        
        if wardrobe_adds > 5 and outfit_creates > 0:
            insights.append({
                "type": "wardrobe_utilization",
                "message": f"Wardrobe items fuel outfit creation: {wardrobe_adds} items, {outfit_creates} outfits",
                "data": {"wardrobe_items": wardrobe_adds, "outfits": outfit_creates},
            })
        
        return insights
    
    # ── Conflict Resolution ───────────────────────────────────────────
    
    def resolve_preference_conflict(
        self,
        user_id: str,
        preference_type: str,
    ) -> Dict[str, Any]:
        """
        Resolve conflicting preference signals using defined strategies.
        """
        resolution_config = CONFLICT_RESOLUTION.get(preference_type)
        
        if not resolution_config:
            return {"resolved": False, "reason": "unknown_preference_type"}
        
        strategy = resolution_config["strategy"]
        sources = resolution_config["sources"]
        
        # Get relevant signals
        signals = self._db.query(UserBehaviorSignal).filter(
            and_(
                UserBehaviorSignal.user_id == user_id,
                UserBehaviorSignal.signal_type.in_(sources),
            )
        ).order_by(UserBehaviorSignal.created_at.desc()).all()
        
        if not signals:
            return {"resolved": False, "reason": "no_signals"}
        
        # Apply resolution strategy
        if strategy == "most_recent":
            return self._resolve_most_recent(signals, preference_type)
        elif strategy == "frequency_weighted":
            return self._resolve_frequency_weighted(signals, preference_type)
        elif strategy == "cumulative":
            return self._resolve_cumulative(signals, preference_type)
        elif strategy == "rolling_average":
            return self._resolve_rolling_average(signals, preference_type)
        elif strategy == "most_recent_verified":
            return self._resolve_most_recent_verified(signals, preference_type)
        
        return {"resolved": False, "reason": "unknown_strategy"}
    
    def _resolve_most_recent(
        self,
        signals: List[UserBehaviorSignal],
        preference_type: str,
    ) -> Dict[str, Any]:
        """Most recent signal wins."""
        most_recent = signals[0]
        
        return {
            "resolved": True,
            "strategy": "most_recent",
            "preference_type": preference_type,
            "value": most_recent.context,
            "source": most_recent.signal_type,
            "resolved_at": most_recent.created_at.isoformat(),
        }
    
    def _resolve_frequency_weighted(
        self,
        signals: List[UserBehaviorSignal],
        preference_type: str,
    ) -> Dict[str, Any]:
        """Weight by frequency of occurrence."""
        value_counts = defaultdict(int)
        
        for signal in signals:
            if signal.context:
                key = json.dumps(signal.context, sort_keys=True)
                value_counts[key] += 1
        
        if not value_counts:
            return {"resolved": False, "reason": "no_context_data"}
        
        most_frequent = max(value_counts.items(), key=lambda x: x[1])
        
        return {
            "resolved": True,
            "strategy": "frequency_weighted",
            "preference_type": preference_type,
            "value": json.loads(most_frequent[0]),
            "frequency": most_frequent[1],
            "total_signals": len(signals),
        }
    
    def _resolve_cumulative(
        self,
        signals: List[UserBehaviorSignal],
        preference_type: str,
    ) -> Dict[str, Any]:
        """Accumulate all values with decay."""
        accumulated = defaultdict(float)
        now = datetime.now(timezone.utc)
        
        for signal in signals:
            # Apply time decay
            age_days = (now - signal.created_at).total_seconds() / 86400
            decay = max(0.1, 1.0 - (age_days / 365))  # Decay over a year
            
            if signal.context:
                for key, value in signal.context.items():
                    if isinstance(value, (int, float)):
                        accumulated[key] += value * decay
        
        return {
            "resolved": True,
            "strategy": "cumulative",
            "preference_type": preference_type,
            "value": dict(accumulated),
            "signal_count": len(signals),
        }
    
    def _resolve_rolling_average(
        self,
        signals: List[UserBehaviorSignal],
        preference_type: str,
    ) -> Dict[str, Any]:
        """Calculate rolling average over time window."""
        # Get last 30 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent_signals = [s for s in signals if s.created_at >= cutoff]
        
        if not recent_signals:
            return {"resolved": False, "reason": "no_recent_signals"}
        
        # Calculate averages
        averages = defaultdict(list)
        for signal in recent_signals:
            if signal.context:
                for key, value in signal.context.items():
                    if isinstance(value, (int, float)):
                        averages[key].append(value)
        
        result = {k: sum(v) / len(v) for k, v in averages.items() if v}
        
        return {
            "resolved": True,
            "strategy": "rolling_average",
            "preference_type": preference_type,
            "value": result,
            "window_days": 30,
            "signal_count": len(recent_signals),
        }
    
    def _resolve_most_recent_verified(
        self,
        signals: List[UserBehaviorSignal],
        preference_type: str,
    ) -> Dict[str, Any]:
        """Most recent verified signal wins."""
        for signal in signals:
            if signal.context and signal.context.get("verified", False):
                return {
                    "resolved": True,
                    "strategy": "most_recent_verified",
                    "preference_type": preference_type,
                    "value": signal.context,
                    "source": signal.signal_type,
                    "verified": True,
                }
        
        # Fall back to most recent
        return self._resolve_most_recent(signals, preference_type)
    
    # ── Signal Versioning ─────────────────────────────────────────────
    
    def record_style_evolution(
        self,
        user_id: str,
        event_type: str,
        previous_value: Any,
        new_value: Any,
        trigger_source: str = "implicit",
        trigger_group: str = None,
    ) -> Dict[str, Any]:
        """
        Record style evolution event for versioning and tracking.
        """
        evolution = UserStyleEvolution(
            user_id=user_id,
            event_type=event_type,
            previous_value=previous_value,
            new_value=new_value,
            trigger_source=trigger_source,
        )
        
        self._db.add(evolution)
        self._db.commit()
        
        logger.info(
            "Style evolution recorded for %s: %s (source: %s, group: %s)",
            user_id, event_type, trigger_source, trigger_group
        )
        
        return {
            "recorded": True,
            "event_type": event_type,
            "evolution_id": evolution.id,
        }
    
    def get_style_evolution_history(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get style evolution history for a user."""
        history = self._db.query(UserStyleEvolution).filter(
            UserStyleEvolution.user_id == user_id
        ).order_by(UserStyleEvolution.created_at.desc()).limit(limit).all()
        
        return [
            {
                "id": h.id,
                "event_type": h.event_type,
                "previous_value": h.previous_value,
                "new_value": h.new_value,
                "trigger_source": h.trigger_source,
                "confidence_delta": float(h.confidence_delta) if h.confidence_delta else None,
                "created_at": h.created_at.isoformat(),
            }
            for h in history
        ]
    
    # ── Cache Management ──────────────────────────────────────────────
    
    def _invalidate_cache(self, user_id: str) -> None:
        """Invalidate cache for a user."""
        keys_to_remove = [k for k in self._signal_cache if k.startswith(user_id)]
        for key in keys_to_remove:
            del self._signal_cache[key]
    
    def clear_cache(self) -> None:
        """Clear entire signal cache."""
        self._signal_cache.clear()


def get_unified_signal_service(db: Session = Depends(get_db)) -> UnifiedSignalService:
    """Factory function for unified signal service."""
    return UnifiedSignalService(db)
