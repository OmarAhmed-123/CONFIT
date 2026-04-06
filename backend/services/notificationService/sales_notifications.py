"""
CONFIT — Sales Notification Service
===================================

Responsibilities:
- Emit real-time notifications to store/factory owners when orders are placed
- Emit confirmation notifications to customers when orders are placed/success
- Support both WebSocket delivery and persistent notification records
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
from database.models import (
    Notification as NotificationModel,
    Order as OrderModel,
    OrderItem as OrderItemModel,
    Store as StoreModel,
    User as UserModel,
    Brand as BrandModel,
    BrandManager as BrandManagerModel,
)
from domain.events import EVENT_ORDER_PLACED, EVENT_PAYMENT_SUCCESS
from services.notificationService.realtime import realtime_hub

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrderPlacedData:
    order_id: str
    customer_user_id: str
    store_id: Optional[str]  # For pickup orders
    total: float
    currency: str
    delivery_method: str  # pickup | shipping


@dataclass(frozen=True)
class PaymentSuccessData:
    order_id: str
    customer_user_id: str
    payment_id: str
    provider: str
    amount: float
    currency: str


class SalesNotificationService:
    def __init__(self, db: Session):
        self._db = db

    @staticmethod
    def _idempotency_key(event_type: str, order_id: str, receiver_id: str) -> str:
        raw = f"{event_type}:{order_id}:{receiver_id}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _build_owner_sale_message(
        self,
        customer_name: str,
        order_number: str,
        total: float,
        currency: str,
        delivery_method: str,
        product_names: list[str],
    ) -> dict[str, Any]:
        template_key = "new_sale"
        params = {
            "customer_name": customer_name,
            "order_number": order_number,
            "total": total,
            "currency": currency,
            "delivery_method": delivery_method,
            "product_names": product_names[:3],  # First 3 products
        }
        delivery_label = "pickup" if delivery_method == "pickup" else "shipping"
        text = (
            f"New order #{order_number} from {customer_name} "
            f"(${total:.2f} {currency}) - {delivery_label}"
        )
        return {"key": template_key, "params": params, "text": text}

    def _build_customer_order_message(
        self,
        order_number: str,
        total: float,
        currency: str,
        delivery_method: str,
        status: str,
    ) -> dict[str, Any]:
        template_key = "order_confirmation" if status == "placed" else "payment_confirmed"
        params = {
            "order_number": order_number,
            "total": total,
            "currency": currency,
            "delivery_method": delivery_method,
            "status": status,
        }
        if status == "placed":
            text = f"Your order #{order_number} has been placed! Total: ${total:.2f} {currency}"
        else:
            text = f"Payment confirmed for order #{order_number}. We're preparing your items!"
        return {"key": template_key, "params": params, "text": text}

    def create_owner_sale_notification(
        self,
        *,
        data: OrderPlacedData,
        reject_if_exists: bool = True,
    ) -> tuple[Optional[NotificationModel], Optional[dict[str, Any]]]:
        """
        Create notification for store/factory owner about new sale.
        """
        order = self._db.query(OrderModel).filter(OrderModel.id == data.order_id).first()
        if not order:
            logger.warning("order_placed: order not found (%s)", data.order_id)
            return None, None

        # Get customer info
        customer = self._db.query(UserModel).filter(UserModel.id == data.customer_user_id).first()
        customer_name = customer.name if customer and customer.name else "Customer"

        # Get product names
        items = (
            self._db.query(OrderItemModel)
            .filter(OrderItemModel.order_id == data.order_id)
            .limit(5)
            .all()
        )
        product_names = [item.name for item in items if item.name]

        # Determine owner receivers
        receiver_ids: list[str] = []
        store_id_for_notif = data.store_id

        if data.store_id:
            store = self._db.query(StoreModel).filter(StoreModel.id == data.store_id).first()
            if store:
                managers = (
                    self._db.query(BrandManagerModel)
                    .filter(
                        BrandManagerModel.brand_id == store.brand_id,
                        BrandManagerModel.is_active == True,  # noqa: E712
                    )
                    .all()
                )
                owners = [m for m in managers if (m.role or "").lower() == "owner"]
                target = owners or managers
                receiver_ids = [str(m.user_id) for m in target]
        else:
            # For shipping orders, notify brand managers of products in the order
            brand_ids = set()
            for item in items:
                if item.product_id:
                    # Get product's brand through product relationship
                    from database.models import Product as ProductModel
                    product = self._db.query(ProductModel).filter(ProductModel.id == item.product_id).first()
                    if product and product.brand_id:
                        brand_ids.add(product.brand_id)

            for brand_id in brand_ids:
                managers = (
                    self._db.query(BrandManagerModel)
                    .filter(
                        BrandManagerModel.brand_id == brand_id,
                        BrandManagerModel.is_active == True,  # noqa: E712
                    )
                    .all()
                )
                owners = [m for m in managers if (m.role or "").lower() == "owner"]
                for m in (owners or managers):
                    receiver_ids.append(str(m.user_id))

        if not receiver_ids:
            logger.info("order_placed: no owner receivers for order %s", data.order_id)
            return None, None

        # Create notification for first owner (primary)
        receiver_id = receiver_ids[0]
        idempotency_key = self._idempotency_key(EVENT_ORDER_PLACED, data.order_id, receiver_id)

        if reject_if_exists:
            existing = (
                self._db.query(NotificationModel)
                .filter(NotificationModel.idempotency_key == idempotency_key)
                .first()
            )
            if existing:
                return None, None

        msg = self._build_owner_sale_message(
            customer_name=customer_name,
            order_number=str(order.order_number or data.order_id[:8]),
            total=data.total,
            currency=data.currency,
            delivery_method=data.delivery_method,
            product_names=product_names,
        )

        metadata = {
            "schema_version": 2,
            "event": EVENT_ORDER_PLACED,
            "status": "new_order",
            "order_id": data.order_id,
            "order_number": str(order.order_number or ""),
            "customer_user_id": data.customer_user_id,
            "customer_name": customer_name,
            "total": data.total,
            "currency": data.currency,
            "delivery_method": data.delivery_method,
            "store_id": store_id_for_notif,
            "product_names": product_names,
            "i18n": {"message": msg},
        }

        notif = NotificationModel(
            id=f"notif-{uuid.uuid4().hex[:12]}",
            receiver_id=receiver_id,
            order_id=data.order_id,
            store_id=store_id_for_notif,
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
            "order_number": str(order.order_number or ""),
            "customer_name": customer_name,
            "total": data.total,
            "currency": data.currency,
            "delivery_method": data.delivery_method,
            "status": "new_order",
            "created_at": notif.created_at.isoformat(),
        }
        return notif, payload

    def create_customer_order_notification(
        self,
        *,
        data: OrderPlacedData,
        status: str = "placed",
        reject_if_exists: bool = True,
    ) -> tuple[Optional[NotificationModel], Optional[dict[str, Any]]]:
        """
        Create notification for customer about their order.
        """
        order = self._db.query(OrderModel).filter(OrderModel.id == data.order_id).first()
        if not order:
            return None, None

        idempotency_key = self._idempotency_key(
            f"customer_{status}", data.order_id, data.customer_user_id
        )

        if reject_if_exists:
            existing = (
                self._db.query(NotificationModel)
                .filter(NotificationModel.idempotency_key == idempotency_key)
                .first()
            )
            if existing:
                return None, None

        msg = self._build_customer_order_message(
            order_number=str(order.order_number or data.order_id[:8]),
            total=data.total,
            currency=data.currency,
            delivery_method=data.delivery_method,
            status=status,
        )

        event_type = EVENT_ORDER_PLACED if status == "placed" else EVENT_PAYMENT_SUCCESS

        metadata = {
            "schema_version": 2,
            "event": event_type,
            "status": status,
            "order_id": data.order_id,
            "order_number": str(order.order_number or ""),
            "total": data.total,
            "currency": data.currency,
            "delivery_method": data.delivery_method,
            "i18n": {"message": msg},
        }

        notif = NotificationModel(
            id=f"notif-{uuid.uuid4().hex[:12]}",
            receiver_id=data.customer_user_id,
            order_id=data.order_id,
            store_id=data.store_id,
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
            "order_number": str(order.order_number or ""),
            "total": data.total,
            "currency": data.currency,
            "status": status,
            "created_at": notif.created_at.isoformat(),
        }
        return notif, payload

    async def handle_order_placed(self, data: OrderPlacedData) -> None:
        """
        Full pipeline: create owner + customer notifications, commit, then deliver.
        """
        # Owner notification
        owner_notif, owner_payload = self.create_owner_sale_notification(
            data=data, reject_if_exists=True
        )

        # Customer notification
        customer_notif, customer_payload = self.create_customer_order_notification(
            data=data, status="placed", reject_if_exists=True
        )

        if not owner_notif and not customer_notif:
            return

        self._db.commit()

        # Deliver owner notification via WebSocket
        if owner_notif and owner_payload:
            self._db.refresh(owner_notif)
            owner_payload["created_at"] = (
                owner_notif.created_at.isoformat() if owner_notif.created_at else owner_payload.get("created_at")
            )
            await realtime_hub.publish_notification(
                receiver_id=owner_notif.receiver_id,
                store_id=data.store_id or "",
                notification_id=owner_notif.id,
                payload=owner_payload,
            )
            logger.info(
                "owner sale notification delivered receiver=%s order=%s",
                owner_notif.receiver_id,
                data.order_id,
            )

        # Deliver customer notification via WebSocket
        if customer_notif and customer_payload:
            self._db.refresh(customer_notif)
            customer_payload["created_at"] = (
                customer_notif.created_at.isoformat()
                if customer_notif.created_at
                else customer_payload.get("created_at")
            )
            await realtime_hub.publish_notification(
                receiver_id=data.customer_user_id,
                store_id=data.store_id or "",
                notification_id=customer_notif.id,
                payload=customer_payload,
            )
            logger.info(
                "customer order notification delivered user=%s order=%s",
                data.customer_user_id,
                data.order_id,
            )

    async def handle_payment_success(self, data: PaymentSuccessData) -> None:
        """
        Notify customer that payment succeeded.
        """
        order = self._db.query(OrderModel).filter(OrderModel.id == data.order_id).first()
        if not order:
            return

        order_data = OrderPlacedData(
            order_id=data.order_id,
            customer_user_id=data.customer_user_id,
            store_id=getattr(order, "pickup_store_id", None),
            total=data.amount,
            currency=data.currency,
            delivery_method=getattr(order, "delivery_method", "shipping"),
        )

        customer_notif, customer_payload = self.create_customer_order_notification(
            data=order_data, status="paid", reject_if_exists=True
        )

        if not customer_notif:
            return

        self._db.commit()
        self._db.refresh(customer_notif)

        customer_payload["created_at"] = (
            customer_notif.created_at.isoformat()
            if customer_notif.created_at
            else customer_payload.get("created_at")
        )

        await realtime_hub.publish_notification(
            receiver_id=data.customer_user_id,
            store_id=order_data.store_id or "",
            notification_id=customer_notif.id,
            payload=customer_payload,
        )
        logger.info(
            "payment success notification delivered user=%s order=%s",
            data.customer_user_id,
            data.order_id,
        )
