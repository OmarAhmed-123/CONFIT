"""
CONFIT Backend — Customer Notifications
=======================================
Real-time notifications for customers (order updates, promotions, etc.)
"""

import json
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.slowapi_limiter import limiter
from database.models import Notification as NotificationModel
from database.session import get_db
from services.auth_service import AuthService
from utils.auth_deps import require_auth, get_auth_service
from services.notificationService.realtime import realtime_hub

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["Customer Notifications"])


# ── Response Models ──────────────────────────────────────

class CustomerNotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    message: str
    read_status: bool
    created_at: Optional[str]
    metadata: Optional[dict] = None


class NotificationListResponse(BaseModel):
    items: List[CustomerNotificationResponse]
    next_cursor: Optional[str] = None


# ── REST Endpoints ────────────────────────────────────────

@router.get("/customer", response_model=NotificationListResponse)
@limiter.limit("30/minute")
async def list_customer_notifications(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None, description="ISO datetime cursor (created_at < cursor)"),
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """List notifications for the authenticated customer."""
    q = db.query(NotificationModel).filter(NotificationModel.receiver_id == user.id)
    
    if cursor:
        try:
            dt = datetime.fromisoformat(cursor)
            q = q.filter(NotificationModel.created_at < dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor")

    rows = q.order_by(NotificationModel.created_at.desc()).limit(limit).all()
    
    items = [
        CustomerNotificationResponse(
            id=r.id,
            type=r.metadata_json.get("type", "promotion") if r.metadata_json else "promotion",
            title=r.metadata_json.get("title", "Notification") if r.metadata_json else "Notification",
            message=r.message or "",
            read_status=bool(r.read_status),
            created_at=r.created_at.isoformat() if r.created_at else None,
            metadata=r.metadata_json,
        )
        for r in rows
    ]
    
    next_cursor = items[-1].created_at if items else None
    return NotificationListResponse(items=items, next_cursor=next_cursor)


@router.post("/read-all")
@limiter.limit("30/minute")
async def mark_all_read(
    request: Request,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read for the authenticated user."""
    db.query(NotificationModel).filter(
        NotificationModel.receiver_id == user.id,
        NotificationModel.read_status == False,
    ).update({"read_status": True})
    db.commit()
    return {"success": True}


@router.delete("/{notification_id}")
@limiter.limit("60/minute")
async def delete_notification(
    request: Request,
    notification_id: str,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete a specific notification."""
    row = (
        db.query(NotificationModel)
        .filter(
            NotificationModel.id == notification_id,
            NotificationModel.receiver_id == user.id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(row)
    db.commit()
    return {"success": True}


# ── WebSocket Endpoint ─────────────────────────────────────

@router.websocket("/customer/ws")
async def customer_notifications_ws(
    websocket: WebSocket,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    WebSocket for real-time customer notifications.
    Authentication via JWT token query param.
    """
    # Authenticate
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    user = auth_service.get_user_by_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = str(user.id)
    
    try:
        await websocket.accept()
        logger.info("Customer notifications WebSocket connected: user=%s", user_id)

        # Register with realtime hub
        await realtime_hub.register_client(user_id, websocket)

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "notification.ack":
                    # Mark notification as delivered
                    notification_id = msg.get("notification_id")
                    if notification_id:
                        row = (
                            db.query(NotificationModel)
                            .filter(NotificationModel.id == notification_id)
                            .first()
                        )
                        if row:
                            row.delivery_status = "delivered"
                            row.ack_received_at = datetime.utcnow()
                            db.commit()

            except json.JSONDecodeError:
                logger.warning("Invalid JSON from client: %s", data[:100])

    except WebSocketDisconnect:
        logger.info("Customer notifications WebSocket disconnected: user=%s", user_id)
    except Exception as e:
        logger.error("WebSocket error for user %s: %s", user_id, e)
    finally:
        await realtime_hub.unregister_client(user_id)
