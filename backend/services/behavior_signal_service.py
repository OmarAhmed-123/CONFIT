"""
CONFIT Backend — Behavior Signal Service
========================================
Behavioral intelligence and signal collection.
"""

import logging
import json
import os
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
from collections import defaultdict
from pathlib import Path

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from database.session import get_db

from models.profile_models import (
    UserBehaviorSignal,
    UserStyleEvolution,
    BehaviorSignalCreate,
    BehaviorSignalResponse,
)

logger = logging.getLogger(__name__)


SIGNAL_CONFIG = {
    "view": {"weight": 0.1, "decay_days": 30},
    "view_long": {"weight": 0.3, "decay_days": 60},
    "wishlist_add": {"weight": 0.5, "decay_days": 90},
    "wishlist_remove": {"weight": -0.3, "decay_days": 90},
    "try_on": {"weight": 0.6, "decay_days": 60},
    "try_on_save": {"weight": 0.7, "decay_days": 90},
    "outfit_create": {"weight": 0.5, "decay_days": None},
    "outfit_save": {"weight": 0.6, "decay_days": None},
    "outfit_delete": {"weight": -0.2, "decay_days": None},
    "outfit_accepted": {"weight": 0.8, "decay_days": 60},
    "outfit_rejected": {"weight": -0.6, "decay_days": 60},
    "purchase": {"weight": 1.0, "decay_days": None},
    "return": {"weight": -0.5, "decay_days": None},
    "share": {"weight": 0.4, "decay_days": 60},
    "feedback_positive": {"weight": 0.5, "decay_days": None},
    "feedback_negative": {"weight": -0.4, "decay_days": None},
    "search": {"weight": 0.2, "decay_days": 7},
    "filter_apply": {"weight": 0.1, "decay_days": 14},
    "scroll_past": {"weight": 0.05, "decay_days": 7},
    "quick_view": {"weight": 0.15, "decay_days": 14},
}

_OVERRIDES_PATH = Path(__file__).resolve().parents[1] / "data" / "training" / "signal_config_overrides.json"
_OVERRIDES_TTL_SEC = max(int(os.getenv("SIGNAL_CONFIG_OVERRIDES_TTL_SEC", "30")), 5)
_overrides_cache: Dict[str, Any] = {}
_overrides_loaded_at: float = 0.0


def _load_signal_config_overrides() -> Dict[str, Any]:
    """
    Load runtime signal weight overrides (training output).

    Expected JSON shape:
      { "updated_at": "...", "signal_config": { "<signal_type>": { "weight": ..., "decay_days": ... }, ... } }
    """
    global _overrides_cache, _overrides_loaded_at
    now = time.time()
    if now - _overrides_loaded_at < _OVERRIDES_TTL_SEC:
        return _overrides_cache

    _overrides_loaded_at = now
    if not _OVERRIDES_PATH.exists():
        _overrides_cache = {}
        return _overrides_cache

    try:
        raw = _OVERRIDES_PATH.read_text(encoding="utf-8")
        payload = json.loads(raw)
        configs = payload.get("signal_config")
        _overrides_cache = configs if isinstance(configs, dict) else {}
    except Exception as exc:
        logger.debug("Failed loading signal overrides: %s", exc)
        _overrides_cache = {}

    return _overrides_cache


def _effective_signal_config(signal_type: str) -> Dict[str, Any]:
    base = SIGNAL_CONFIG.get(signal_type)
    if base is None:
        base = {"weight": 0.1, "decay_days": 30}

    overrides = _load_signal_config_overrides().get(signal_type)
    if not overrides:
        return base

    weight = overrides.get("weight", base.get("weight", 0.1))
    decay_days = overrides.get("decay_days", base.get("decay_days", 30))
    return {"weight": weight, "decay_days": decay_days}


class BehaviorSignalService:
    """Service for collecting and aggregating user behavior signals."""
    
    def __init__(self, db: Session):
        self._db = db
    
    def track(
        self,
        user_id: str,
        signal_type: str,
        entity_type: str,
        entity_id: str,
        context: Dict[str, Any] = None,
        duration_ms: int = None,
    ) -> Optional[BehaviorSignalResponse]:
        # Production safety: unknown signals should not be dropped.
        # Overrides come from the training pipeline output.
        config = _effective_signal_config(signal_type)
        
        weight = config["weight"]
        decay_days = config["decay_days"]
        
        expires_at = None
        if decay_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=decay_days)
        
        signal = UserBehaviorSignal(
            user_id=user_id,
            signal_type=signal_type,
            entity_type=entity_type,
            entity_id=entity_id,
            weight=Decimal(str(abs(weight))),
            context=context or {},
            duration_ms=duration_ms,
            expires_at=expires_at,
        )
        
        self._db.add(signal)
        self._db.commit()
        self._db.refresh(signal)
        
        if weight >= 0.5:
            self._check_preference_drift(user_id, entity_type, entity_id, weight)
        
        return BehaviorSignalResponse(
            id=str(signal.id),
            user_id=str(signal.user_id),
            signal_type=signal.signal_type,
            entity_type=signal.entity_type,
            entity_id=signal.entity_id,
            weight=float(signal.weight),
            context=signal.context or {},
            duration_ms=signal.duration_ms,
            created_at=signal.created_at,
            expires_at=signal.expires_at,
        )
    
    def track_batch(
        self,
        user_id: str,
        signals: List[BehaviorSignalCreate],
    ) -> List[BehaviorSignalResponse]:
        results = []
        for s in signals:
            result = self.track(
                user_id=user_id,
                signal_type=s.signal_type,
                entity_type=s.entity_type,
                entity_id=s.entity_id,
                context=s.context,
                duration_ms=s.duration_ms,
            )
            if result:
                results.append(result)
        return results
    
    def get_user_signals(
        self,
        user_id: str,
        signal_types: List[str] = None,
        entity_type: str = None,
        limit: int = 100,
    ) -> List[BehaviorSignalResponse]:
        query = self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.user_id == user_id,
            or_(
                UserBehaviorSignal.expires_at == None,
                UserBehaviorSignal.expires_at > datetime.now(timezone.utc)
            )
        )
        
        if signal_types:
            query = query.filter(UserBehaviorSignal.signal_type.in_(signal_types))
        if entity_type:
            query = query.filter(UserBehaviorSignal.entity_type == entity_type)
        
        signals = query.order_by(UserBehaviorSignal.created_at.desc()).limit(limit).all()
        
        return [
            BehaviorSignalResponse(
                id=str(s.id),
                user_id=str(s.user_id),
                signal_type=s.signal_type,
                entity_type=s.entity_type,
                entity_id=s.entity_id,
                weight=float(s.weight),
                context=s.context or {},
                duration_ms=s.duration_ms,
                created_at=s.created_at,
                expires_at=s.expires_at,
            )
            for s in signals
        ]
    
    def aggregate_by_entity(
        self,
        user_id: str,
        entity_type: str,
    ) -> Dict[str, float]:
        signals = self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.user_id == user_id,
            UserBehaviorSignal.entity_type == entity_type,
            or_(
                UserBehaviorSignal.expires_at == None,
                UserBehaviorSignal.expires_at > datetime.now(timezone.utc)
            )
        ).all()
        
        aggregated = defaultdict(float)
        
        for s in signals:
            weight = float(s.weight)
            if (
                s.signal_type.startswith("feedback_")
                or s.signal_type in ["return", "wishlist_remove", "outfit_rejected"]
            ):
                weight = -weight
            aggregated[s.entity_id] += weight
        
        return dict(sorted(aggregated.items(), key=lambda x: x[1], reverse=True))
    
    def get_preference_summary(self, user_id: str) -> Dict[str, Any]:
        signals = self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.user_id == user_id,
            or_(
                UserBehaviorSignal.expires_at == None,
                UserBehaviorSignal.expires_at > datetime.now(timezone.utc)
            )
        ).all()

        # Bridge explicit outfit feedback into brand/category/color preferences.
        outfit_map: Dict[str, Any] = {}
        outfit_feedback_ids = {
            str(s.entity_id)
            for s in signals
            if s.entity_type == "outfit"
            and s.signal_type in ["outfit_accepted", "outfit_rejected"]
        }
        if outfit_feedback_ids:
            from database.models import Outfit as OutfitModel

            rows = self._db.query(OutfitModel).filter(
                OutfitModel.id.in_(list(outfit_feedback_ids))
            ).all()
            outfit_map = {str(r.id): r for r in rows}
        
        brands = defaultdict(float)
        categories = defaultdict(float)
        styles = defaultdict(float)
        colors = defaultdict(float)
        price_range = {"min": None, "max": None, "avg": []}
        
        for s in signals:
            weight = float(s.weight)
            if s.signal_type in ["return", "feedback_negative", "wishlist_remove", "outfit_rejected"]:
                weight = -weight

            # Convert explicit outfit feedback into inferred preferences.
            if (
                s.entity_type == "outfit"
                and s.signal_type in ["outfit_accepted", "outfit_rejected"]
            ):
                outfit_row = outfit_map.get(str(s.entity_id))
                if outfit_row and outfit_row.items:
                    for item in (outfit_row.items or []):
                        if not isinstance(item, dict):
                            continue
                        brand = item.get("brand")
                        category = item.get("category")
                        color = item.get("color")
                        if brand:
                            brands[str(brand)] += weight
                        if category:
                            categories[str(category)] += weight
                        if color:
                            colors[str(color)] += weight
                        item_price = item.get("price")
                        if item_price is not None:
                            try:
                                price_range["avg"].append(float(item_price))
                            except Exception:
                                pass
                continue
            
            if s.entity_type == "brand":
                brands[s.entity_id] += weight
            elif s.entity_type == "category":
                categories[s.entity_id] += weight
            elif s.entity_type == "style":
                styles[s.entity_id] += weight
            elif s.entity_type == "color":
                colors[s.entity_id] += weight
            elif s.entity_type == "product":
                if s.context and "price" in s.context:
                    price = s.context["price"]
                    price_range["avg"].append(price)
        
        if price_range["avg"]:
            price_range["min"] = min(price_range["avg"])
            price_range["max"] = max(price_range["avg"])
            price_range["avg"] = sum(price_range["avg"]) / len(price_range["avg"])
        else:
            price_range["avg"] = None
        
        return {
            "brands": dict(sorted(brands.items(), key=lambda x: x[1], reverse=True)[:10]),
            "categories": dict(sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]),
            "styles": dict(sorted(styles.items(), key=lambda x: x[1], reverse=True)[:10]),
            "colors": dict(sorted(colors.items(), key=lambda x: x[1], reverse=True)[:10]),
            "price_behavior": price_range,
            "total_signals": len(signals),
        }
    
    def _check_preference_drift(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        weight: float,
    ) -> None:
        recent_signals = self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.user_id == user_id,
            UserBehaviorSignal.entity_type == entity_type,
            UserBehaviorSignal.created_at >= datetime.now(timezone.utc) - timedelta(days=30)
        ).count()
        
        if recent_signals > 10:
            evolution = UserStyleEvolution(
                user_id=user_id,
                event_type="preference_drift",
                previous_value={},
                new_value={
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "signal_count": recent_signals,
                },
                trigger_source="implicit",
                confidence_delta=Decimal(str(weight * 5)),
            )
            self._db.add(evolution)
            self._db.commit()
    
    def decay_expired_signals(self, batch_size: int = 1000) -> int:
        expired = self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.expires_at != None,
            UserBehaviorSignal.expires_at <= datetime.now(timezone.utc)
        ).limit(batch_size).all()
        
        count = len(expired)
        for s in expired:
            self._db.delete(s)
        
        if count > 0:
            self._db.commit()
        
        return count
    
    def clear_user_signals(self, user_id: str) -> int:
        count = self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.user_id == user_id
        ).delete()
        self._db.commit()
        return count
    
    def get_signal_counts_by_type(self, user_id: str) -> Dict[str, int]:
        result = self._db.query(
            UserBehaviorSignal.signal_type,
            func.count(UserBehaviorSignal.id)
        ).filter(
            UserBehaviorSignal.user_id == user_id
        ).group_by(UserBehaviorSignal.signal_type).all()
        
        return {r[0]: r[1] for r in result}


def get_behavior_signal_service(db: Session = Depends(get_db)) -> BehaviorSignalService:
    return BehaviorSignalService(db)
