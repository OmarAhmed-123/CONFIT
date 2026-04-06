"""
Notification service bootstrap.

Registers domain event handlers on the in-process event bus.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from database.session import SessionLocal
from domain.events import DomainEvent, event_bus, EVENT_ORDER_PICKUP_SELECTED
from services.notificationService.service import NotificationService, PickupSelectedData

logger = logging.getLogger(__name__)


def register_notification_handlers() -> None:
    """
    Register handlers exactly once at process startup.
    """

    def _handler(evt: DomainEvent) -> None:
        if evt.name != EVENT_ORDER_PICKUP_SELECTED:
            return

        payload = dict(evt.payload or {})
        data = PickupSelectedData(
            order_id=str(payload.get("order_id", "")),
            customer_user_id=str(payload.get("customer_user_id", "")),
            pickup_store_id=str(payload.get("pickup_store_id", "")),
            pickup_time=str(payload.get("pickup_time", "")),
            receiver_id=str(payload.get("receiver_id", "")),
        )

        def _run() -> Any:
            db = SessionLocal()
            try:
                service = NotificationService(db)
                return service.handle_pickup_selected(data)
            finally:
                db.close()

        try:
            loop = asyncio.get_event_loop()
            loop.create_task(_run())
        except Exception:
            logger.exception("Failed scheduling notification handler task")

    event_bus.subscribe(EVENT_ORDER_PICKUP_SELECTED, _handler)

