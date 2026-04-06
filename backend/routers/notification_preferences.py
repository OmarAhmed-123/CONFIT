"""
CONFIT Backend — Notification Preferences API
=============================================
CRUD endpoints for user notification preferences.
Supports both customer and store_owner recipient types.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_

from core.slowapi_limiter import limiter
from database.models import NotificationPreferences, NotificationQueue
from database.session import get_db
from utils.auth_deps import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notification-preferences", tags=["Notification Preferences"])


# ── Pydantic Schemas ─────────────────────────────────────────────────────────────

class ChannelPreferences(BaseModel):
    in_app: bool = True
    email: bool = True
    push: bool = True


class BatchOptions(BaseModel):
    enabled: bool = False


class NotificationPreferencesResponse(BaseModel):
    id: str
    recipient_id: str
    recipient_type: str
    channel_preferences: ChannelPreferences
    frequency_settings: dict
    notification_types: List[str]
    batch_options: BatchOptions
    version: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class NotificationPreferencesUpdate(BaseModel):
    channel_preferences: Optional[ChannelPreferences] = None
    frequency_settings: Optional[dict] = None
    notification_types: Optional[List[str]] = None
    batch_options: Optional[BatchOptions] = None


class NotificationPreferencesCreate(BaseModel):
    recipient_type: str = Field(..., pattern="^(customer|store_owner)$")
    channel_preferences: Optional[ChannelPreferences] = ChannelPreferences()
    frequency_settings: Optional[dict] = {}
    notification_types: Optional[List[str]] = []
    batch_options: Optional[BatchOptions] = BatchOptions()


# ── Default Preferences Factory ─────────────────────────────────────────────────

CUSTOMER_DEFAULT_TYPES = ["order_updates", "delivery_updates", "promotions", "style_recommendations", "restock_alerts"]
OWNER_DEFAULT_TYPES = ["new_orders", "status_updates", "customer_inquiries"]


def get_default_preferences(recipient_type: str) -> dict:
    """Generate default preferences for a recipient type."""
    types = CUSTOMER_DEFAULT_TYPES if recipient_type == "customer" else OWNER_DEFAULT_TYPES
    frequency_settings = {t: "real_time" for t in types}
    
    return {
        "channel_preferences": {"in_app": True, "email": True, "push": True},
        "frequency_settings": frequency_settings,
        "notification_types": types,
        "batch_options": {"enabled": False},
    }


# ── REST Endpoints ──────────────────────────────────────────────────────────────

@router.get("", response_model=NotificationPreferencesResponse)
@limiter.limit("30/minute")
async def get_preferences(
    request: Request,
    recipient_type: str = "customer",
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get notification preferences for the authenticated user."""
    if recipient_type not in ("customer", "store_owner"):
        raise HTTPException(status_code=400, detail="Invalid recipient_type")

    prefs = db.query(NotificationPreferences).filter(
        NotificationPreferences.recipient_id == user.id,
        NotificationPreferences.recipient_type == recipient_type,
    ).first()

    # Create default preferences if not exists
    if not prefs:
        defaults = get_default_preferences(recipient_type)
        prefs = NotificationPreferences(
            recipient_id=user.id,
            recipient_type=recipient_type,
            channel_preferences=defaults["channel_preferences"],
            frequency_settings=defaults["frequency_settings"],
            notification_types=defaults["notification_types"],
            batch_options=defaults["batch_options"],
        )
        db.add(prefs)
        db.commit()
        db.refresh(prefs)

    return NotificationPreferencesResponse(
        id=str(prefs.id),
        recipient_id=str(prefs.recipient_id),
        recipient_type=prefs.recipient_type,
        channel_preferences=ChannelPreferences(**prefs.channel_preferences),
        frequency_settings=prefs.frequency_settings,
        notification_types=prefs.notification_types,
        batch_options=BatchOptions(**prefs.batch_options),
        version=prefs.version,
        created_at=prefs.created_at.isoformat() if prefs.created_at else None,
        updated_at=prefs.updated_at.isoformat() if prefs.updated_at else None,
    )


@router.put("", response_model=NotificationPreferencesResponse)
@limiter.limit("30/minute")
async def update_preferences(
    request: Request,
    data: NotificationPreferencesUpdate,
    recipient_type: str = "customer",
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update notification preferences for the authenticated user."""
    if recipient_type not in ("customer", "store_owner"):
        raise HTTPException(status_code=400, detail="Invalid recipient_type")

    prefs = db.query(NotificationPreferences).filter(
        NotificationPreferences.recipient_id == user.id,
        NotificationPreferences.recipient_type == recipient_type,
    ).first()

    # Create if not exists
    if not prefs:
        defaults = get_default_preferences(recipient_type)
        prefs = NotificationPreferences(
            recipient_id=user.id,
            recipient_type=recipient_type,
            channel_preferences=defaults["channel_preferences"],
            frequency_settings=defaults["frequency_settings"],
            notification_types=defaults["notification_types"],
            batch_options=defaults["batch_options"],
        )
        db.add(prefs)

    # Apply updates
    if data.channel_preferences is not None:
        prefs.channel_preferences = data.channel_preferences.model_dump()
    if data.frequency_settings is not None:
        prefs.frequency_settings = data.frequency_settings
    if data.notification_types is not None:
        prefs.notification_types = data.notification_types
    if data.batch_options is not None:
        prefs.batch_options = data.batch_options.model_dump()

    prefs.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(prefs)

    logger.info("Updated notification preferences for user %s (type=%s)", user.id, recipient_type)

    return NotificationPreferencesResponse(
        id=str(prefs.id),
        recipient_id=str(prefs.recipient_id),
        recipient_type=prefs.recipient_type,
        channel_preferences=ChannelPreferences(**prefs.channel_preferences),
        frequency_settings=prefs.frequency_settings,
        notification_types=prefs.notification_types,
        batch_options=BatchOptions(**prefs.batch_options),
        version=prefs.version,
        created_at=prefs.created_at.isoformat() if prefs.created_at else None,
        updated_at=prefs.updated_at.isoformat() if prefs.updated_at else None,
    )


@router.post("/reset", response_model=NotificationPreferencesResponse)
@limiter.limit("10/minute")
async def reset_preferences(
    request: Request,
    recipient_type: str = "customer",
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Reset notification preferences to defaults."""
    if recipient_type not in ("customer", "store_owner"):
        raise HTTPException(status_code=400, detail="Invalid recipient_type")

    prefs = db.query(NotificationPreferences).filter(
        NotificationPreferences.recipient_id == user.id,
        NotificationPreferences.recipient_type == recipient_type,
    ).first()

    defaults = get_default_preferences(recipient_type)

    if not prefs:
        prefs = NotificationPreferences(
            recipient_id=user.id,
            recipient_type=recipient_type,
            channel_preferences=defaults["channel_preferences"],
            frequency_settings=defaults["frequency_settings"],
            notification_types=defaults["notification_types"],
            batch_options=defaults["batch_options"],
        )
        db.add(prefs)
    else:
        prefs.channel_preferences = defaults["channel_preferences"]
        prefs.frequency_settings = defaults["frequency_settings"]
        prefs.notification_types = defaults["notification_types"]
        prefs.batch_options = defaults["batch_options"]
        prefs.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(prefs)

    logger.info("Reset notification preferences for user %s (type=%s)", user.id, recipient_type)

    return NotificationPreferencesResponse(
        id=str(prefs.id),
        recipient_id=str(prefs.recipient_id),
        recipient_type=prefs.recipient_type,
        channel_preferences=ChannelPreferences(**prefs.channel_preferences),
        frequency_settings=prefs.frequency_settings,
        notification_types=prefs.notification_types,
        batch_options=BatchOptions(**prefs.batch_options),
        version=prefs.version,
        created_at=prefs.created_at.isoformat() if prefs.created_at else None,
        updated_at=prefs.updated_at.isoformat() if prefs.updated_at else None,
    )


# ── Batch Queue Endpoints (Internal) ────────────────────────────────────────────

@router.get("/queue", response_model=List[dict])
@limiter.limit("60/minute")
async def get_pending_queue(
    request: Request,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get pending batch notifications for the authenticated user."""
    items = db.query(NotificationQueue).filter(
        NotificationQueue.recipient_id == user.id,
        NotificationQueue.status == "pending",
    ).order_by(NotificationQueue.scheduled_for.asc()).all()

    return [
        {
            "id": str(item.id),
            "batch_type": item.batch_type,
            "notification_type": item.notification_type,
            "channel": item.channel,
            "scheduled_for": item.scheduled_for.isoformat() if item.scheduled_for else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in items
    ]


@router.delete("/queue/{queue_id}")
@limiter.limit("60/minute")
async def delete_queue_item(
    request: Request,
    queue_id: str,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete a specific queued notification."""
    item = db.query(NotificationQueue).filter(
        NotificationQueue.id == queue_id,
        NotificationQueue.recipient_id == user.id,
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    db.delete(item)
    db.commit()
    return {"success": True}


# ── Internal: Check Preferences for Dispatch ────────────────────────────────────

def check_dispatch_preferences(
    db: Session,
    recipient_id: str,
    recipient_type: str,
    notification_type: str,
    channel: str,
) -> dict:
    """
    Check if a notification should be dispatched based on user preferences.
    Returns: {"should_dispatch": bool, "frequency": str}
    """
    prefs = db.query(NotificationPreferences).filter(
        NotificationPreferences.recipient_id == recipient_id,
        NotificationPreferences.recipient_type == recipient_type,
    ).first()

    # No preferences = use defaults (all enabled, real-time)
    if not prefs:
        return {"should_dispatch": True, "frequency": "real_time"}

    # Check channel enabled
    channel_prefs = prefs.channel_preferences or {}
    if not channel_prefs.get(channel, True):
        return {"should_dispatch": False, "frequency": "disabled"}

    # Map notification types to preference categories
    category_map = {
        # Customer mappings
        "order_confirmed": "order_updates",
        "order_placed": "order_updates",
        "order_shipped": "delivery_updates",
        "order_delivered": "delivery_updates",
        "order_cancelled": "order_updates",
        "payment_success": "order_updates",
        "promotion": "promotions",
        "price_drop": "promotions",
        "styling_suggestion": "style_recommendations",
        "back_in_stock": "restock_alerts",
        "wishlist_available": "restock_alerts",
        "delivery_tracking": "delivery_updates",
        # Owner mappings
        "new_order": "new_orders",
        "status_update": "status_updates",
        "customer_inquiry": "customer_inquiries",
    }

    category = category_map.get(notification_type, notification_type)

    # Check type enabled
    enabled_types = prefs.notification_types or []
    if category not in enabled_types:
        return {"should_dispatch": False, "frequency": "disabled"}

    # Check frequency
    freq_settings = prefs.frequency_settings or {}
    frequency = freq_settings.get(category, "real_time")

    if frequency == "disabled":
        return {"should_dispatch": False, "frequency": "disabled"}

    return {"should_dispatch": True, "frequency": frequency}
