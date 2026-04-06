"""
WebSocket-only realtime delivery for owner notifications.

Protocol (client <-> server):
1. Client connects with JWT (validated in `routers/notifications.py`).
2. Client subscribes to its store dashboard(s):
   { "type": "subscribe", "store_ids": [ "<uuid>", ... ] }
3. Server emits per notification row:
   { "type": "notification.created", "data": { ...unifiedPayload... } }
4. Client ACKs:
   { "type": "notification.ack", "notification_id": "<notif-row-id>" }

Reliability:
- If no ACK is received within 5s, the server retries emission up to 3 times.
- Delivery state is persisted on `database.models.Notification`:
  `delivery_status`, `delivery_attempts`, `last_emitted_at`, `ack_received_at`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket
from sqlalchemy.orm import Session

from database.models import Notification as NotificationModel
from database.session import SessionLocal

logger = logging.getLogger(__name__)


class OwnerRealtimeHub:
    def __init__(self) -> None:
        # One active websocket per receiver (owner user).
        self._ws_by_receiver: Dict[str, WebSocket] = {}
        # Store ids the receiver is interested in.
        self._subs_by_receiver: Dict[str, Set[str]] = {}

        # ACK coordination (keyed by notification row id).
        self._ack_events: Dict[str, asyncio.Event] = {}
        self._retry_tasks: Dict[str, asyncio.Task[None]] = {}

        self._lock = asyncio.Lock()

    async def attach_ws(self, receiver_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            old = self._ws_by_receiver.get(receiver_id)
            self._ws_by_receiver[receiver_id] = websocket
        if old and old is not websocket:
            try:
                await old.close(code=4000)
            except Exception:
                pass

    async def detach_ws(self, receiver_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            if self._ws_by_receiver.get(receiver_id) is websocket:
                self._ws_by_receiver.pop(receiver_id, None)
            # Keep subscriptions; used after reconnect.

    async def set_store_subscriptions(self, receiver_id: str, store_ids: list[str]) -> None:
        async with self._lock:
            self._subs_by_receiver[receiver_id] = set(store_ids)

    async def _get_ws(self, receiver_id: str) -> Optional[WebSocket]:
        async with self._lock:
            return self._ws_by_receiver.get(receiver_id)

    async def _is_subscribed(self, receiver_id: str, store_id: str) -> bool:
        async with self._lock:
            return store_id in self._subs_by_receiver.get(receiver_id, set())

    async def _send_if_possible(self, *, receiver_id: str, store_id: str, payload: dict[str, Any]) -> bool:
        ws = await self._get_ws(receiver_id)
        if ws is None:
            return False
        if not await self._is_subscribed(receiver_id, store_id):
            return False

        try:
            await ws.send_json({"type": "notification.created", "data": payload})
            return True
        except Exception:
            logger.info("WS send failed receiver=%s store=%s notif_payload=%s", receiver_id, store_id, payload.get("notification_id"))
            return False

    async def publish_notification(
        self,
        *,
        receiver_id: str,
        store_id: str,
        notification_id: str,
        payload: dict[str, Any],
        max_attempts: int = 3,
        ack_timeout_s: float = 5.0,
    ) -> None:
        """
        Start delivery + retry for an already persisted notification row.
        """
        async with self._lock:
            if notification_id not in self._ack_events:
                self._ack_events[notification_id] = asyncio.Event()

            if notification_id not in self._retry_tasks:
                self._retry_tasks[notification_id] = asyncio.create_task(
                    self._retry_loop(
                        receiver_id=receiver_id,
                        store_id=store_id,
                        notification_id=notification_id,
                        payload=payload,
                        max_attempts=max_attempts,
                        ack_timeout_s=ack_timeout_s,
                    )
                )

    async def _retry_loop(
        self,
        *,
        receiver_id: str,
        store_id: str,
        notification_id: str,
        payload: dict[str, Any],
        max_attempts: int,
        ack_timeout_s: float,
    ) -> None:
        db: Session = SessionLocal()
        try:
            for attempt in range(1, max_attempts + 1):
                # Exit fast if already ACKed.
                async with self._lock:
                    ev = self._ack_events.get(notification_id)
                    if ev is not None and ev.is_set():
                        return

                now = datetime.now(timezone.utc)
                notif = (
                    db.query(NotificationModel)
                    .filter(NotificationModel.id == notification_id, NotificationModel.receiver_id == receiver_id)
                    .first()
                )
                if notif is None:
                    return
                if notif.delivery_status == "delivered":
                    return

                notif.delivery_status = "pending"
                notif.delivery_attempts = attempt
                notif.last_emitted_at = now
                db.commit()

                sent = await self._send_if_possible(receiver_id=receiver_id, store_id=store_id, payload=payload)
                if sent:
                    # Only wait when we actually sent.
                    try:
                        async with self._lock:
                            ev = self._ack_events.get(notification_id)
                        if ev is None:
                            continue
                        await asyncio.wait_for(ev.wait(), timeout=ack_timeout_s)
                        return
                    except asyncio.TimeoutError:
                        pass

                await asyncio.sleep(ack_timeout_s)

            # Max attempts reached; mark failed if not delivered.
            notif = (
                db.query(NotificationModel)
                .filter(NotificationModel.id == notification_id, NotificationModel.receiver_id == receiver_id)
                .first()
            )
            if notif is not None and notif.delivery_status != "delivered":
                notif.delivery_status = "failed"
                db.commit()
        finally:
            async with self._lock:
                self._retry_tasks.pop(notification_id, None)

    async def mark_ack(self, *, receiver_id: str, notification_id: str) -> None:
        """
        Called by websocket ACK handler.
        """
        async with self._lock:
            ev = self._ack_events.get(notification_id)
            if ev is not None:
                ev.set()

        db: Session = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            notif = (
                db.query(NotificationModel)
                .filter(NotificationModel.id == notification_id, NotificationModel.receiver_id == receiver_id)
                .first()
            )
            if notif is None:
                return
            notif.delivery_status = "delivered"
            notif.ack_received_at = now
            db.commit()
        finally:
            db.close()


realtime_hub = OwnerRealtimeHub()

