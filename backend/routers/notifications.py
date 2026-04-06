"""
CONFIT Backend — Notifications (Owner)
======================================
Real-time owner notifications for pickup scheduling.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.orm import Session

from core.slowapi_limiter import limiter
from database.models import Notification as NotificationModel, UserRole, AppRole, Store as StoreModel
from database.session import get_db
from services.auth_service import AuthService
from utils.auth_deps import require_auth, get_auth_service
from services.notificationService.realtime import realtime_hub
from models.production_models import BrandManager as BrandManagerModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


def _require_owner(user_id: str, db: Session) -> None:
    role_row = db.query(UserRole).filter(UserRole.user_id == user_id).first()
    if not role_row or role_row.role not in (AppRole.brand_manager, AppRole.admin):
        raise HTTPException(status_code=403, detail="Owner access required")


@router.get("")
@limiter.limit("30/minute")
async def list_notifications(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None, description="ISO datetime cursor (created_at < cursor)"),
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    _require_owner(user.id, db)

    q = db.query(NotificationModel).filter(NotificationModel.receiver_id == user.id)
    if cursor:
        try:
            dt = datetime.fromisoformat(cursor)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor")
        q = q.filter(NotificationModel.created_at < dt)

    rows = q.order_by(NotificationModel.created_at.desc()).limit(limit).all()
    items = [
        {
            "id": r.id,
            "receiver_id": str(r.receiver_id),
            "order_id": r.order_id,
            "message": r.message,
            "metadata": r.metadata_json or {},
            "read_status": bool(r.read_status),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    next_cursor = items[-1]["created_at"] if items else None
    return {"items": items, "next_cursor": next_cursor}


@router.post("/{notification_id}/read")
@limiter.limit("60/minute")
async def mark_read(
    request: Request,
    notification_id: str,
    user=Depends(require_auth),
    db: Session = Depends(get_db),
):
    _require_owner(user.id, db)
    row = (
        db.query(NotificationModel)
        .filter(NotificationModel.id == notification_id, NotificationModel.receiver_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    row.read_status = True
    db.commit()
    return {"success": True}


@router.websocket("/ws")
async def notifications_ws(
    websocket: WebSocket,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    WebSocket authentication via JWT:
    - Prefer query param `?token=...`
    - Also supports `Authorization: Bearer ...` header
    """
    # Extract token
    if not token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()

    if not token:
        await websocket.close(code=4401)
        return

    profile = auth_service.get_user_by_token(token)
    if not profile:
        await websocket.close(code=4401)
        return

    try:
        _require_owner(profile.id, db)
    except HTTPException:
        await websocket.close(code=4403)
        return

    await websocket.accept()
    await realtime_hub.attach_ws(profile.id, websocket)
    logger.info("notifications ws connected receiver=%s", profile.id)

    try:
        # Client protocol loop:
        # - subscribe: {type:'subscribe', store_ids:[...]}
        # - ack: {type:'notification.ack', notification_id:'...'}
        while True:
            raw = await websocket.receive_text()
            if raw.strip().lower() == "ping":
                await websocket.send_text("pong")
                continue

            try:
                msg = json.loads(raw)
            except Exception:
                continue

            if not isinstance(msg, dict):
                continue

            if msg.get("type") == "subscribe":
                store_ids = msg.get("store_ids")
                if not isinstance(store_ids, list):
                    continue

                is_admin = (
                    db.query(UserRole)
                    .filter(UserRole.user_id == profile.id, UserRole.role == AppRole.admin)
                    .first()
                    is not None
                )

                authorized: list[str] = []
                for store_id in store_ids:
                    if not isinstance(store_id, str) or not store_id:
                        continue
                    store = db.query(StoreModel).filter(StoreModel.id == store_id).first()
                    if not store:
                        continue
                    if is_admin:
                        authorized.append(store_id)
                        continue
                    bm = (
                        db.query(BrandManagerModel)
                        .filter(BrandManagerModel.brand_id == store.brand_id, BrandManagerModel.user_id == profile.id)
                        .filter(BrandManagerModel.is_active == True)  # noqa: E712
                        .first()
                    )
                    if bm is not None:
                        authorized.append(store_id)

                await realtime_hub.set_store_subscriptions(profile.id, authorized)

            elif msg.get("type") == "notification.ack":
                notification_id = msg.get("notification_id")
                if isinstance(notification_id, str) and notification_id:
                    await realtime_hub.mark_ack(receiver_id=profile.id, notification_id=notification_id)
    except WebSocketDisconnect:
        pass
    finally:
        await realtime_hub.detach_ws(profile.id, websocket)
        logger.info("notifications ws disconnected receiver=%s", profile.id)


@router.get("/stream")
@limiter.limit("15/minute")
async def notifications_sse(
    request: Request,
    token: str = Query(..., description="JWT access token"),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    # WS-only architecture; SSE endpoint intentionally disabled.
    raise HTTPException(status_code=410, detail="SSE disabled. Use WebSocket /api/notifications/ws.")

