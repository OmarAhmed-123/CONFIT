"""
CONFIT Backend — Ecosystem event ingestion
==========================================
Lightweight endpoint used by frontend telemetry/event bus.
"""

from typing import Any

from fastapi import APIRouter, Body

router = APIRouter(prefix="/api/ecosystem", tags=["Ecosystem"])


@router.post("/events/emit")
async def emit_event(payload: dict[str, Any] = Body(default_factory=dict)):
    """
    Accept ecosystem events without failing local development flows.
    The payload is acknowledged but not persisted by this stub handler.
    """
    return {
        "success": True,
        "accepted": True,
        "type": payload.get("type"),
        "eventId": payload.get("eventId") or payload.get("id"),
    }

"""
CONFIT Backend — Ecosystem Integration Router
=============================================
API endpoints for cross-feature orchestration and unified user journey.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from services.ecosystem_integration_service import (
    EcosystemIntegrationService,
    EcosystemEvent,
    get_ecosystem_service,
)
from services.unified_signal_service import UnifiedSignalService, get_unified_signal_service
from utils.auth_deps import require_auth
from services.auth_service import UserProfile
from pydantic import BaseModel

router = APIRouter(prefix="/api/ecosystem", tags=["Ecosystem Integration"])


# ── Request Models ───────────────────────────────────────────────────

class EmitEventRequest(BaseModel):
    event: str
    data: Dict[str, Any] = {}


class RegisterSignalRequest(BaseModel):
    signal_type: str
    entity_type: str
    entity_id: str
    context: Optional[Dict[str, Any]] = None
    source_group: Optional[str] = None


class IntegrateOutfitRequest(BaseModel):
    outfit_id: str
    items: List[Dict[str, Any]]
    occasion: Optional[str] = None


class IntegrateTryonRequest(BaseModel):
    outfit_id: str
    items: List[Dict[str, Any]]


# ── Event Endpoints ──────────────────────────────────────────────────

@router.post("/events/emit")
async def emit_ecosystem_event(
    data: EmitEventRequest,
    user: UserProfile = Depends(require_auth),
    ecosystem: EcosystemIntegrationService = Depends(get_ecosystem_service),
):
    """Emit an ecosystem event to trigger cross-feature updates."""
    try:
        event = EcosystemEvent(data.event)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event type. Valid events: {[e.value for e in EcosystemEvent]}"
        )
    
    result = await ecosystem.emit_event(event, user.id, data.data)
    return result


@router.get("/events/list")
async def list_ecosystem_events():
    """List all available ecosystem event types."""
    return {
        "events": [
            {"value": e.value, "name": e.name}
            for e in EcosystemEvent
        ]
    }


# ── User Journey Endpoints ───────────────────────────────────────────

@router.get("/journey/state")
async def get_user_journey_state(
    user: UserProfile = Depends(require_auth),
    ecosystem: EcosystemIntegrationService = Depends(get_ecosystem_service),
):
    """Get current state of user's journey across all features."""
    return await ecosystem.get_user_journey_state(user.id)


@router.get("/journey/next-actions")
async def get_next_actions(
    user: UserProfile = Depends(require_auth),
    ecosystem: EcosystemIntegrationService = Depends(get_ecosystem_service),
):
    """Get recommended next actions for user journey progression."""
    state = await ecosystem.get_user_journey_state(user.id)
    return {
        "journey_phase": state["journey_phase"],
        "recommended_actions": state["recommended_next_actions"],
    }


# ── Cross-Feature Integration Endpoints ──────────────────────────────

@router.post("/integrate/stylist-tryon")
async def integrate_stylist_with_tryon(
    data: IntegrateTryonRequest,
    user: UserProfile = Depends(require_auth),
    ecosystem: EcosystemIntegrationService = Depends(get_ecosystem_service),
):
    """Integrate stylist recommendations with virtual try-on."""
    result = await ecosystem.integrate_stylist_with_tryon(
        user_id=user.id,
        outfit_id=data.outfit_id,
        items=data.items,
    )
    return result


@router.post("/integrate/outfit-wardrobe")
async def integrate_outfit_with_wardrobe(
    data: IntegrateOutfitRequest,
    user: UserProfile = Depends(require_auth),
    ecosystem: EcosystemIntegrationService = Depends(get_ecosystem_service),
):
    """Integrate outfit builder with virtual wardrobe."""
    result = await ecosystem.integrate_outfit_with_wardrobe(
        user_id=user.id,
        outfit_items=data.items,
    )
    return result


@router.post("/integrate/stylist-commerce")
async def integrate_stylist_with_commerce(
    data: IntegrateOutfitRequest,
    user: UserProfile = Depends(require_auth),
    ecosystem: EcosystemIntegrationService = Depends(get_ecosystem_service),
):
    """Integrate stylist recommendations with marketplace commerce."""
    result = await ecosystem.integrate_stylist_with_commerce(
        user_id=user.id,
        recommendations=data.items,
    )
    return result


@router.post("/integrate/outfit-social")
async def integrate_outfit_with_social(
    data: IntegrateOutfitRequest,
    user: UserProfile = Depends(require_auth),
    ecosystem: EcosystemIntegrationService = Depends(get_ecosystem_service),
):
    """Integrate outfit builder with social features."""
    result = await ecosystem.integrate_outfit_with_social(
        user_id=user.id,
        outfit_id=data.outfit_id,
        outfit_data={"items": data.items, "occasion": data.occasion, "share_slug": data.outfit_id},
    )
    return result


# ── Unified Signal Endpoints ─────────────────────────────────────────

@router.post("/signals/register")
async def register_unified_signal(
    data: RegisterSignalRequest,
    user: UserProfile = Depends(require_auth),
    signals: UnifiedSignalService = Depends(get_unified_signal_service),
):
    """Register a signal with uniqueness validation."""
    return signals.register_signal(
        user_id=user.id,
        signal_type=data.signal_type,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        context=data.context,
        source_group=data.source_group,
    )


@router.get("/signals/unified")
async def get_unified_signals(
    categories: str = None,
    days: int = 30,
    user: UserProfile = Depends(require_auth),
    signals: UnifiedSignalService = Depends(get_unified_signal_service),
):
    """Get unified signal aggregation across all feature groups."""
    category_list = categories.split(",") if categories else None
    return signals.get_unified_signals(
        user_id=user.id,
        categories=category_list,
        time_window_days=days,
    )


@router.get("/signals/categories")
async def get_signal_categories():
    """Get signal categories by feature group."""
    return {
        "categories": {
            name: {
                "group": info["group"],
                "signals": info["signals"],
                "weight": info["weight"],
            }
            for name, info in SIGNAL_CATEGORIES.items()
        }
    }


@router.post("/signals/resolve/{preference_type}")
async def resolve_preference_conflict(
    preference_type: str,
    user: UserProfile = Depends(require_auth),
    signals: UnifiedSignalService = Depends(get_unified_signal_service),
):
    """Resolve conflicting preference signals."""
    result = signals.resolve_preference_conflict(user.id, preference_type)
    return result


@router.get("/signals/evolution")
async def get_style_evolution(
    limit: int = 50,
    user: UserProfile = Depends(require_auth),
    signals: UnifiedSignalService = Depends(get_unified_signal_service),
):
    """Get style evolution history for a user."""
    return signals.get_style_evolution_history(user.id, limit)


# ── Cross-Group Status Endpoints ─────────────────────────────────────

@router.get("/status/groups")
async def get_feature_group_status(
    user: UserProfile = Depends(require_auth),
    ecosystem: EcosystemIntegrationService = Depends(get_ecosystem_service),
):
    """Get status of user's engagement across all feature groups."""
    state = await ecosystem.get_user_journey_state(user.id)
    
    return {
        "groups": {
            "GROUP_1_IDENTITY": {
                "name": "User Identity & USP",
                "engagement": "active" if state["identity_completeness"] > 50 else "pending",
                "completeness": state["identity_completeness"],
            },
            "GROUP_2_STYLING": {
                "name": "Discovery & Styling",
                "engagement": "active" if state["feature_engagement"]["stylist"] > 5 else "exploring",
                "usage": state["feature_engagement"]["stylist"],
            },
            "GROUP_3_TRYON": {
                "name": "Virtual Try-On",
                "engagement": "active" if state["feature_engagement"]["tryon"] > 3 else "pending",
                "usage": state["feature_engagement"]["tryon"],
            },
            "GROUP_4_WARDROBE": {
                "name": "Virtual Wardrobe",
                "engagement": "active" if state["feature_engagement"]["wardrobe"] > 10 else "exploring",
                "usage": state["feature_engagement"]["wardrobe"],
            },
            "GROUP_5_COMMERCE": {
                "name": "Marketplace & Commerce",
                "engagement": "active" if state["signal_strength_by_group"].get("GROUP_5", 0) > 5 else "pending",
            },
            "GROUP_6_BUDGET": {
                "name": "Budget Intelligence",
                "engagement": "active" if state["signal_strength_by_group"].get("GROUP_6", 0) > 3 else "pending",
            },
            "GROUP_7_SOCIAL": {
                "name": "Social & Community",
                "engagement": "active" if state["feature_engagement"]["social"] > 5 else "pending",
                "usage": state["feature_engagement"]["social"],
            },
        },
        "journey_phase": state["journey_phase"],
        "confidence_level": state["confidence_level"],
    }


@router.get("/health")
async def ecosystem_health():
    """Health check for ecosystem integration."""
    return {
        "status": "healthy",
        "services": {
            "ecosystem_integration": "operational",
            "unified_signals": "operational",
            "event_registry": "operational",
        },
        "version": "1.0.0",
    }


# Import for signal categories
from services.unified_signal_service import SIGNAL_CATEGORIES
