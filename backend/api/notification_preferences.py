"""
CONFIT Backend - Notification Preferences API
=============================================

REST API for managing user notification preferences.

Endpoints:
- GET /api/v1/notifications/preferences
- PATCH /api/v1/notifications/preferences
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from core.security.rbac import AuthContext
from database.models import NotificationPreferences, User
from schemas.notifications import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# -------------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------------

async def get_or_create_preferences(
    db: AsyncSession,
    user_id: str,
    recipient_type: str = "customer",
) -> NotificationPreferences:
    """Get existing preferences or create default for user."""
    result = await db.execute(
        select(NotificationPreferences).where(
            NotificationPreferences.recipient_id == user_id
        )
    )
    prefs = result.scalar_one_or_none()
    
    if not prefs:
        # Create default preferences
        # Detect language from user phone (Egypt = Arabic)
        user = await db.get(User, user_id)
        language = "en"
        if user and user.phone and user.phone.startswith("+20"):
            language = "ar"
        
        prefs = NotificationPreferences(
            recipient_id=user_id,
            recipient_type=recipient_type,
            push_enabled=True,
            email_enabled=True,
            sms_enabled=True,
            whatsapp_enabled=False,
            in_app_enabled=True,
            categories={
                "orders": True,
                "styling": True,
                "promotions": True,
                "donor_impact": True,
            },
            language=language,
            dnd_start=None,
            dnd_end=None,
        )
        db.add(prefs)
        await db.flush()
    
    return prefs


def validate_dnd_times(dnd_start: Optional[str], dnd_end: Optional[str]) -> None:
    """Validate DND time configuration."""
    if dnd_start and not dnd_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both dnd_start and dnd_end must be specified together",
        )
    if dnd_end and not dnd_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both dnd_start and dnd_end must be specified together",
        )


# -------------------------------------------------------------------------
# API ENDPOINTS
# -------------------------------------------------------------------------

@router.get(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    summary="Get notification preferences",
    description="Get the current user's notification preferences.",
)
async def get_preferences(
    current_user: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferences:
    """Get notification preferences for current user."""
    prefs = await get_or_create_preferences(db, current_user.user_id)
    await db.commit()
    return prefs


@router.patch(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    summary="Update notification preferences",
    description="Update notification preferences for current user.",
)
async def update_preferences(
    update_data: NotificationPreferencesUpdate,
    current_user: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferences:
    """Update notification preferences for current user."""
    prefs = await get_or_create_preferences(db, current_user.user_id)
    
    # Validate DND times
    dnd_start = update_data.dnd_start if update_data.dnd_start is not None else prefs.dnd_start
    dnd_end = update_data.dnd_end if update_data.dnd_end is not None else prefs.dnd_end
    validate_dnd_times(dnd_start, dnd_end)
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        if hasattr(prefs, field):
            setattr(prefs, field, value)
    
    # Increment version
    prefs.version = (prefs.version or 1) + 1
    prefs.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(prefs)
    
    logger.info(f"Updated notification preferences for user {current_user.user_id}")
    return prefs


@router.put(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    summary="Replace notification preferences",
    description="Replace all notification preferences for current user.",
)
async def replace_preferences(
    update_data: NotificationPreferencesUpdate,
    current_user: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferences:
    """Replace all notification preferences for current user."""
    prefs = await get_or_create_preferences(db, current_user.user_id)
    
    # Validate DND times
    validate_dnd_times(update_data.dnd_start, update_data.dnd_end)
    
    # Update all fields
    prefs.push_enabled = update_data.push_enabled if update_data.push_enabled is not None else True
    prefs.email_enabled = update_data.email_enabled if update_data.email_enabled is not None else True
    prefs.sms_enabled = update_data.sms_enabled if update_data.sms_enabled is not None else True
    prefs.whatsapp_enabled = update_data.whatsapp_enabled if update_data.whatsapp_enabled is not None else False
    prefs.in_app_enabled = update_data.in_app_enabled if update_data.in_app_enabled is not None else True
    
    if update_data.categories is not None:
        prefs.categories = update_data.categories
    
    if update_data.language is not None:
        prefs.language = update_data.language
    
    prefs.dnd_start = update_data.dnd_start
    prefs.dnd_end = update_data.dnd_end
    
    # Increment version
    prefs.version = (prefs.version or 1) + 1
    prefs.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(prefs)
    
    logger.info(f"Replaced notification preferences for user {current_user.user_id}")
    return prefs


# -------------------------------------------------------------------------
# CHANNEL TOGGLE ENDPOINTS
# -------------------------------------------------------------------------

@router.post(
    "/preferences/toggle/{channel}",
    response_model=NotificationPreferencesResponse,
    summary="Toggle notification channel",
    description="Enable or disable a specific notification channel.",
)
async def toggle_channel(
    channel: str,
    enabled: bool = True,
    current_user: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferences:
    """Toggle a specific notification channel on/off."""
    valid_channels = ["push", "email", "sms", "whatsapp", "in_app"]
    if channel not in valid_channels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel. Must be one of: {valid_channels}",
        )
    
    prefs = await get_or_create_preferences(db, current_user.user_id)
    
    field_name = f"{channel}_enabled"
    setattr(prefs, field_name, enabled)
    prefs.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(prefs)
    
    logger.info(f"Toggled {channel} to {enabled} for user {current_user.user_id}")
    return prefs


# -------------------------------------------------------------------------
# CATEGORY ENDPOINTS
# -------------------------------------------------------------------------

@router.post(
    "/preferences/category/{category}",
    response_model=NotificationPreferencesResponse,
    summary="Toggle notification category",
    description="Enable or disable a specific notification category.",
)
async def toggle_category(
    category: str,
    enabled: bool = True,
    current_user: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferences:
    """Toggle a specific notification category on/off."""
    valid_categories = ["orders", "styling", "promotions", "donor_impact"]
    if category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {valid_categories}",
        )
    
    prefs = await get_or_create_preferences(db, current_user.user_id)
    
    categories = prefs.categories or {}
    categories[category] = enabled
    prefs.categories = categories
    prefs.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(prefs)
    
    logger.info(f"Toggled category {category} to {enabled} for user {current_user.user_id}")
    return prefs


# -------------------------------------------------------------------------
# DND ENDPOINTS
# -------------------------------------------------------------------------

@router.post(
    "/preferences/dnd",
    response_model=NotificationPreferencesResponse,
    summary="Set DND hours",
    description="Set Do Not Disturb hours for the current user.",
)
async def set_dnd_hours(
    dnd_start: str = Field(..., pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$", description="DND start time (HH:MM)"),
    dnd_end: str = Field(..., pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$", description="DND end time (HH:MM)"),
    current_user: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferences:
    """Set DND hours for the current user."""
    prefs = await get_or_create_preferences(db, current_user.user_id)
    
    prefs.dnd_start = dnd_start
    prefs.dnd_end = dnd_end
    prefs.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(prefs)
    
    logger.info(f"Set DND hours {dnd_start}-{dnd_end} for user {current_user.user_id}")
    return prefs


@router.delete(
    "/preferences/dnd",
    response_model=NotificationPreferencesResponse,
    summary="Clear DND hours",
    description="Clear Do Not Disturb hours for the current user.",
)
async def clear_dnd_hours(
    current_user: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferences:
    """Clear DND hours for the current user."""
    prefs = await get_or_create_preferences(db, current_user.user_id)
    
    prefs.dnd_start = None
    prefs.dnd_end = None
    prefs.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(prefs)
    
    logger.info(f"Cleared DND hours for user {current_user.user_id}")
    return prefs


# -------------------------------------------------------------------------
# LANGUAGE ENDPOINTS
# -------------------------------------------------------------------------

@router.post(
    "/preferences/language/{language}",
    response_model=NotificationPreferencesResponse,
    summary="Set notification language",
    description="Set notification language for the current user (en or ar).",
)
async def set_language(
    language: str,
    current_user: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferences:
    """Set notification language for the current user."""
    if language not in ["en", "ar"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Language must be 'en' or 'ar'",
        )
    
    prefs = await get_or_create_preferences(db, current_user.user_id)
    
    prefs.language = language
    prefs.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(prefs)
    
    logger.info(f"Set language to {language} for user {current_user.user_id}")
    return prefs


# -------------------------------------------------------------------------
# EXPORTS
# -------------------------------------------------------------------------

__all__ = [
    "router",
    "get_or_create_preferences",
]
