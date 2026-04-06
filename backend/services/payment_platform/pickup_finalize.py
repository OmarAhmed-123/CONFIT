"""
Finalize in-store pickup flow after unified (PayPal/Paymob) payment succeeds.

Stripe pickup still uses POST /api/payments/confirm; this module mirrors that pickup
branch so webhook/capture paths create PickupRecord + store notifications.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from database.session import SessionLocal
from database.models import (
    Order as OrderModel,
    PickupRecord as PickupRecordModel,
    Store as StoreModel,
    UserRole,
    AppRole,
)
from models.production_models import BrandManager as BrandManagerModel
from services.notificationService.service import NotificationService, PickupSelectedData

logger = logging.getLogger(__name__)


async def finalize_pickup_after_online_payment(order_id: str) -> None:
    """Idempotent: no-op if not pickup, not paid, or pickup row already exists."""
    db: Session = SessionLocal()
    created: list[tuple[str, str, str, dict[str, Any]]] = []
    try:
        order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
        if not order:
            logger.warning("pickup_finalize: order %s not found", order_id)
            return
        dm = (getattr(order, "delivery_method", None) or "").strip().lower()
        if dm != "pickup":
            return
        if getattr(order, "payment_status", None) != "success":
            return
        if not getattr(order, "pickup_store_id", None) or not getattr(order, "pickup_time", None):
            logger.warning("pickup_finalize: order %s missing pickup fields", order_id)
            return

        existing_pickup = (
            db.query(PickupRecordModel).filter(PickupRecordModel.order_id == order.id).first()
        )
        if existing_pickup:
            return

        with db.begin():
            order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
            if not order or getattr(order, "payment_status", None) != "success":
                return

            pickup_id = f"pickup-{uuid.uuid4().hex[:12]}"
            db.add(
                PickupRecordModel(
                    id=pickup_id,
                    order_id=order.id,
                    store_id=order.pickup_store_id,
                    pickup_time=order.pickup_time,
                    status="scheduled",
                )
            )

            store = db.query(StoreModel).filter(StoreModel.id == order.pickup_store_id).first()
            if not store:
                logger.error("pickup_finalize: invalid store %s for order %s", order.pickup_store_id, order_id)
                raise ValueError("invalid_pickup_store")

            managers = (
                db.query(BrandManagerModel)
                .filter(BrandManagerModel.brand_id == store.brand_id, BrandManagerModel.is_active == True)  # noqa: E712
                .all()
            )
            owners = [m for m in managers if (m.role or "").lower() == "owner"]
            target = owners or managers
            receiver_ids: list[str] = [str(m.user_id) for m in target]

            if not receiver_ids:
                receiver_ids = [
                    str(r.user_id)
                    for r in db.query(UserRole).filter(UserRole.role == AppRole.brand_manager).all()
                ]

            if not receiver_ids:
                logger.error("pickup_finalize: no brand managers for order %s", order_id)
                raise ValueError("no_brand_managers")

            service = NotificationService(db)
            for receiver_id in receiver_ids:
                data = PickupSelectedData(
                    order_id=str(order.id),
                    customer_user_id=str(order.user_id),
                    pickup_store_id=str(order.pickup_store_id),
                    pickup_time=str(order.pickup_time),
                    receiver_id=str(receiver_id),
                )
                row, payload = service.create_pickup_notification_row(data=data, reject_if_exists=True)
                if row is not None and payload is not None:
                    created.append((receiver_id, str(order.pickup_store_id), row.id, payload))

        from services.notificationService.realtime import realtime_hub

        for receiver_id, store_id, notif_id, payload in created:
            await realtime_hub.publish_notification(
                receiver_id=receiver_id,
                store_id=store_id,
                notification_id=notif_id,
                payload=payload,
            )
    except Exception:
        logger.exception("pickup_finalize failed for order %s", order_id)
    finally:
        db.close()
