"""
CONFIT — Notification Service (Pickup)
======================================

Responsibilities:
- listen to pickup event `order.pickup_selected`
- build secure notification payload (DB-backed store name)
- send real-time notification (WS preferred, SSE fallback)
- persist notification log
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from core.security.input_sanitization import sanitize_string
from database.models import Notification as NotificationModel, Store as StoreModel, User as UserModel, Order as OrderModel, OrderItem as OrderItemModel
from domain.events import EVENT_ORDER_PICKUP_SELECTED
from services.notificationService.realtime import realtime_hub
from services.analytics.event_logger import log_notification_sent, log_notification_delivered

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PickupSelectedData:
    order_id: str
    customer_user_id: str
    pickup_store_id: str
    pickup_time: str  # ISO8601 (validated upstream)
    receiver_id: str  # owner/manager user id (validated upstream)


class NotificationService:
    def __init__(self, db: Session):
        self._db = db

    @staticmethod
    def _idempotency_key(data: PickupSelectedData) -> str:
        raw = f"{EVENT_ORDER_PICKUP_SELECTED}:{data.order_id}:{data.receiver_id}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _build_message(self, customer_name: str, pickup_location_name: str, pickup_time: str, order_id: str) -> dict[str, Any]:
        # Localization-ready: keep template key + params.
        template_key = "pickup_scheduled"
        params = {
            "customer_name": customer_name,
            "pickup_location_name": pickup_location_name,
            "pickup_time": pickup_time,
            "order_id": order_id,
        }
        text = (
            f"Customer {params['customer_name']} will pick up order #{params['order_id']}\n"
            f"from {params['pickup_location_name']} at {params['pickup_time']}."
        )
        return {"key": template_key, "params": params, "text": text}

    def create_pickup_notification_row(
        self,
        *,
        data: PickupSelectedData,
        reject_if_exists: bool = True,
    ) -> tuple[Optional[NotificationModel], Optional[dict[str, Any]]]:
        """
        Build + validate the unified payload and create a Notification row in the current DB session.

        IMPORTANT:
        - This function does NOT commit.
        - Caller must commit the surrounding transaction before emitting websocket events.
        """
        # Fetch store name from DB only.
        store = self._db.query(StoreModel).filter(StoreModel.id == data.pickup_store_id).first()
        if not store:
            logger.warning("pickup_selected: store not found (%s)", data.pickup_store_id)
            return None, None

        order = self._db.query(OrderModel).filter(OrderModel.id == data.order_id).first()
        if not order:
            logger.warning("pickup_selected: order not found (%s)", data.order_id)
            return None, None

        shipping_name = ""
        try:
            if isinstance(order.shipping_address, dict):
                shipping_name = str(order.shipping_address.get("name") or "")
        except Exception:
            shipping_name = ""

        customer = self._db.query(UserModel).filter(UserModel.id == data.customer_user_id).first()
        customer_name_raw = shipping_name or (customer.name if customer and customer.name else "Customer")
        customer_name = sanitize_string(customer_name_raw, max_length=100)

        pickup_location_name = sanitize_string(store.name, max_length=255)
        pickup_time = sanitize_string(data.pickup_time, max_length=64)

        first_item = (
            self._db.query(OrderItemModel)
            .filter(OrderItemModel.order_id == data.order_id)
            .order_by(OrderItemModel.id.asc())
            .first()
        )
        product_name_raw = first_item.name if first_item and first_item.name else ""
        product_name = sanitize_string(product_name_raw, max_length=255)

        required = {
            "customer_name": customer_name,
            "product_name": product_name,
            "pickup_location_name": pickup_location_name,
            "pickup_time": pickup_time,
        }
        if any(not str(v).strip() for v in required.values()):
            logger.warning("pickup_selected: rejected empty notification fields=%s", required)
            return None, None

        msg = self._build_message(
            customer_name=customer_name,
            pickup_location_name=pickup_location_name,
            pickup_time=pickup_time,
            order_id=data.order_id,
        )

        idempotency_key = self._idempotency_key(data)
        if reject_if_exists:
            existing = (
                self._db.query(NotificationModel)
                .filter(NotificationModel.idempotency_key == idempotency_key)
                .first()
            )
            if existing:
                return None, None

        metadata = {
            "schema_version": 1,
            "event": EVENT_ORDER_PICKUP_SELECTED,
            "status": "scheduled_pickup",
            "order_id": data.order_id,
            "pickup_store_id": data.pickup_store_id,
            "pickup_location_name": pickup_location_name,
            "pickup_time": pickup_time,
            "customer_user_id": data.customer_user_id,
            "customer_name": customer_name,
            "product_name": product_name,
            "i18n": {"message": msg},
        }

        notif = NotificationModel(
            id=f"notif-{uuid.uuid4().hex[:12]}",
            receiver_id=data.receiver_id,
            order_id=data.order_id,
            store_id=data.pickup_store_id,
            message=msg["text"],
            metadata_json=metadata,
            read_status=False,
            created_at=datetime.now(timezone.utc),
            idempotency_key=idempotency_key,
            delivery_status="pending",
            delivery_attempts=0,
            last_emitted_at=None,
            ack_received_at=None,
        )
        self._db.add(notif)

        payload = {
            "notification_id": notif.id,
            "order_id": data.order_id,
            "customer_name": customer_name,
            "product_name": product_name,
            "pickup_location_name": pickup_location_name,
            "pickup_time": pickup_time,
            "status": "scheduled_pickup",
            "created_at": notif.created_at.isoformat(),
        }
        return notif, payload

    async def handle_pickup_selected(self, data: PickupSelectedData) -> None:
        """
        Full secure pipeline: DB lookup, persist (idempotent), then realtime deliver.
        """
        row, payload = self.create_pickup_notification_row(data=data, reject_if_exists=True)
        if row is None or payload is None:
            return

        # Commit the notification row, then emit.
        self._db.commit()
        self._db.refresh(row)
        payload["created_at"] = row.created_at.isoformat() if row.created_at else payload.get("created_at")

        await realtime_hub.publish_notification(
            receiver_id=data.receiver_id,
            store_id=data.pickup_store_id,
            notification_id=row.id,
            payload=payload,
        )
        
        # Log analytics events
        log_notification_sent(
            db=self._db,
            notification_id=row.id,
            recipient_id=data.receiver_id,
            recipient_type="owner",
            channel="in_app",
            payload={
                "order_id": data.order_id,
                "store_id": data.pickup_store_id,
                "notification_type": "pickup_scheduled",
            },
        )
        log_notification_delivered(
            db=self._db,
            notification_id=row.id,
            recipient_id=data.receiver_id,
            recipient_type="owner",
            channel="in_app",
        )
        
        logger.info("notification delivered receiver=%s notif=%s", data.receiver_id, row.id)

    # Domain handler registration lives in bootstrap.py (opens its own DB session per event).

