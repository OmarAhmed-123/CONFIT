"""
CONFIT Backend - Notification Read Receipts API
================================================

API endpoints for marking notifications as read.

Endpoints:
- POST /api/v1/notifications/{id}/read
- POST /api/v1/notifications/read-all
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from core.security.rbac import AuthContext
from database.models import ActorType, Notification
from schemas.notifications import (
    MarkAllReadRequest,
    MarkReadRequest,
    MarkReadResponse,
    TriggerEnum,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# -------------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------------

async def get_notification_by_id(
    db: AsyncSession,
    notification_id: str,
    user_id: str,
) -> Optional[Notification]:
    """Get notification by ID, ensuring it belongs to the user."""
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.receiver_id == user_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def mark_notification_read(
    db: AsyncSession,
    notification: Notification,
) -> Notification:
    """Mark a notification as read."""
    notification.read_status = True
    notification.read_at = datetime.now(timezone.utc)
    notification.status = "READ"
    
    await db.commit()
    await db.refresh(notification)
    
    return notification


# -------------------------------------------------------------------------
# API ENDPOINTS
# -------------------------------------------------------------------------

@router.post(
    "/{notification_id}/read",
    response_model=MarkReadResponse,
    summary="Mark notification as read",
    description="Mark a single notification as read.",
)
async def mark_as_read(
    notification_id: str,
    current_user: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarkReadResponse:
    """Mark a single notification as read."""
    notification = await get_notification_by_id(db, notification_id, current_user.user_id)
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification not found: {notification_id}",
        )
    
    if notification.read_status:
        # Already read, return current state
        return MarkReadResponse(
            success=True,
            updated_count=0,
            updated_at=notification.read_at or datetime.now(timezone.utc),
        )
    
    notification = await mark_notification_read(db, notification)
    
    logger.info(f"Marked notification {notification_id} as read for user {current_user.user_id}")
    
    return MarkReadResponse(
        success=True,
        updated_count=1,
        updated_at=notification.read_at,
    )


@router.post(
    "/read-all",
    response_model=MarkReadResponse,
    summary="Mark all notifications as read",
    description="Mark all unread notifications as read for the current user.",
)
async def mark_all_as_read(
    request: MarkAllReadRequest = None,
    current_user: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarkReadResponse:
    """Mark all unread notifications as read."""
    # Build query
    conditions = [
        Notification.receiver_id == current_user.user_id,
        Notification.read_status == False,
    ]
    
    # Filter by actor type if provided
    if request and request.actor_type:
        conditions.append(Notification.actor_type == request.actor_type)
    
    # Filter by trigger if provided
    if request and request.trigger:
        conditions.append(Notification.trigger == request.trigger.value)
    
    # Get count of unread notifications
    count_result = await db.execute(
        select(Notification).where(and_(*conditions))
    )
    unread_notifications = count_result.scalars().all()
    updated_count = len(unread_notifications)
    
    if updated_count == 0:
        return MarkReadResponse(
            success=True,
            updated_count=0,
            updated_at=datetime.now(timezone.utc),
        )
    
    # Update all unread notifications
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Notification)
        .where(and_(*conditions))
        .values(
            read_status=True,
            read_at=now,
            status="READ",
        )
    )
    
    await db.commit()
    
    logger.info(
        f"Marked {updated_count} notifications as read for user {current_user.user_id}"
    )
    
    return MarkReadResponse(
        success=True,
        updated_count=updated_count,
        updated_at=now,
    )


@router.post(
    "/batch-read",
    response_model=MarkReadResponse,
    summary="Mark multiple notifications as read",
    description="Mark multiple specific notifications as read.",
)
async def mark_batch_as_read(
    notification_ids: List[str],
    current_user: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarkReadResponse:
    """Mark multiple specific notifications as read."""
    if not notification_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No notification IDs provided",
        )
    
    if len(notification_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 notification IDs per request",
        )
    
    # Update notifications
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(Notification)
        .where(
            and_(
                Notification.id.in_(notification_ids),
                Notification.receiver_id == current_user.user_id,
                Notification.read_status == False,
            )
        )
        .values(
            read_status=True,
            read_at=now,
            status="READ",
        )
        .returning(Notification.id)
    )
    
    updated_ids = [row[0] for row in result.fetchall()]
    updated_count = len(updated_ids)
    
    await db.commit()
    
    logger.info(
        f"Marked {updated_count} notifications as read for user {current_user.user_id}"
    )
    
    return MarkReadResponse(
        success=True,
        updated_count=updated_count,
        updated_at=now,
    )


# -------------------------------------------------------------------------
# UNREAD COUNT
# -------------------------------------------------------------------------

@router.get(
    "/unread-count",
    summary="Get unread notification count",
    description="Get the count of unread notifications for the current user.",
)
async def get_unread_count(
    actor_type: Optional[ActorType] = Query(None, description="Filter by actor type"),
    trigger: Optional[str] = Query(None, description="Filter by trigger"),
    current_user: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get unread notification count."""
    # Build query
    conditions = [
        Notification.receiver_id == current_user.user_id,
        Notification.read_status == False,
    ]
    
    if actor_type:
        conditions.append(Notification.actor_type == actor_type)
    
    if trigger:
        conditions.append(Notification.trigger == trigger)
    
    # Count unread
    result = await db.execute(
        select(Notification).where(and_(*conditions))
    )
    notifications = result.scalars().all()
    count = len(notifications)
    
    return {
        "unread_count": count,
        "actor_type": actor_type.value if actor_type else None,
        "trigger": trigger,
    }


# -------------------------------------------------------------------------
# EXPORTS
# -------------------------------------------------------------------------

__all__ = [
    "router",
    "mark_as_read",
    "mark_all_as_read",
    "mark_batch_as_read",
    "get_unread_count",
]
