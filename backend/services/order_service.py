"""
CONFIT Backend — Order Service
=================================
Order and return management backed by the database.
Use via dependency injection with a DB session.
"""

import uuid
import logging
from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from database.models import Order as OrderModel, OrderItem as OrderItemModel, ReturnRequest as ReturnRequestModel

logger = logging.getLogger(__name__)


def _order_to_dict(order: OrderModel) -> dict:
    """Map Order ORM and its items to the existing API response shape."""
    items = [
        {
            "productId": i.product_id,
            "name": i.name,
            "quantity": i.quantity,
            "price": i.price,
            "image": i.image_url or "",
        }
        for i in order.items
    ]
    return {
        "id": order.id,
        "order_number": order.order_number,
        "user_email": None,  # kept for backward compatibility; client may use user_id
        "placed_at": order.placed_at.isoformat() if order.placed_at else None,
        "status": order.status,
        "items": items,
        "shipping_address": order.shipping_address,
        "payment_method": order.payment_method,
        "subtotal": order.subtotal,
        "shipping": order.shipping,
        "tax": order.tax,
        "total": order.total,
        "tracking_number": order.tracking_number,
        "estimated_delivery": order.estimated_delivery,
    }


class OrderService:
    """Manages orders and returns in the database, keyed by user_id."""

    def __init__(self, db: Session):
        self._db = db

    def create_order(
        self,
        user_id: str,
        items: list[dict],
        shipping_address: dict,
        payment_method: str = "card",
        delivery_method: Optional[str] = None,
        pickup_store_id: Optional[str] = None,
        pickup_time: Optional[str] = None,
        payment_status: str = "pending",
    ) -> dict:
        """Create a new order for the given user (or guest)."""
        order_id = f"ord-{uuid.uuid4().hex[:8]}"
        order_number = f"CONF-{uuid.uuid4().hex[:6].upper()}"

        subtotal = sum(
            max(float(item.get("price", 0)), 0.0) * max(int(item.get("quantity", 1)), 1)
            for item in items
        )
        if subtotal <= 0:
            raise ValueError("Order total must be greater than zero")
        shipping = 0.0 if subtotal >= 100 else 9.99
        tax = round(subtotal * 0.08, 2)
        total = round(subtotal + shipping + tax, 2)

        order = OrderModel(
            id=order_id,
            order_number=order_number,
            user_id=user_id,
            placed_at=datetime.now(timezone.utc),
            status="confirmed",
            shipping_address=shipping_address,
            payment_method=payment_method,
            delivery_method=delivery_method,
            pickup_store_id=pickup_store_id,
            pickup_time=pickup_time,
            payment_status=payment_status,
            subtotal=round(subtotal, 2),
            shipping=shipping,
            tax=tax,
            total=total,
        )
        self._db.add(order)

        for it in items:
            self._db.add(
                OrderItemModel(
                    order_id=order_id,
                    product_id=it.get("productId"),
                    name=it.get("name", ""),
                    quantity=it.get("quantity", 1),
                    price=float(it.get("price", 0)),
                    image_url=it.get("image"),
                )
            )

        self._db.commit()
        self._db.refresh(order)

        logger.info("Order %s created for user %s, total: $%s", order_id, user_id, total)
        return _order_to_dict(order)

    def get_orders(self, user_id: str) -> List[dict]:
        """Get all orders for a user (or guest)."""
        orders = (
            self._db.query(OrderModel)
            .filter(OrderModel.user_id == user_id)
            .order_by(OrderModel.placed_at.desc())
            .all()
        )
        return [_order_to_dict(o) for o in orders]

    def get_order_by_id(self, user_id: str, order_id: str) -> Optional[dict]:
        """Get a single order by ID, scoped to user."""
        order = (
            self._db.query(OrderModel)
            .filter(OrderModel.id == order_id, OrderModel.user_id == user_id)
            .first()
        )
        return _order_to_dict(order) if order else None

    def update_status(
        self,
        user_id: str,
        order_id: str,
        status: str,
        tracking_number: Optional[str] = None,
        estimated_delivery: Optional[str] = None,
    ) -> Optional[dict]:
        """Update order status and optional tracking."""
        order = (
            self._db.query(OrderModel)
            .filter(OrderModel.id == order_id, OrderModel.user_id == user_id)
            .first()
        )
        if not order:
            return None

        order.status = status
        if tracking_number is not None:
            order.tracking_number = tracking_number
        if estimated_delivery is not None:
            order.estimated_delivery = estimated_delivery

        self._db.commit()
        self._db.refresh(order)
        logger.info("Order %s status updated to %s for user %s", order_id, status, user_id)
        return _order_to_dict(order)

    def create_return(
        self,
        user_id: str,
        order_id: str,
        reason: str,
        items: Optional[list[dict]] = None,
    ) -> dict:
        """Create a return request for an order."""
        return_id = f"ret-{uuid.uuid4().hex[:8]}"
        row = ReturnRequestModel(
            id=return_id,
            order_id=order_id,
            user_id=user_id,
            reason=reason,
            items=items or [],
            status="requested",
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)

        record = {
            "id": return_id,
            "order_id": order_id,
            "user_email": None,
            "reason": reason,
            "items": row.items or [],
            "status": row.status,
            "requested_at": row.requested_at.isoformat() if row.requested_at else None,
            "processed_at": row.processed_at.isoformat() if row.processed_at else None,
        }
        logger.info("Return %s created for order %s (user %s)", return_id, order_id, user_id)
        return record

    def list_returns(self, user_id: str) -> List[dict]:
        """List all return requests for a user."""
        rows = (
            self._db.query(ReturnRequestModel)
            .filter(ReturnRequestModel.user_id == user_id)
            .order_by(ReturnRequestModel.requested_at.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "order_id": r.order_id,
                "user_email": None,
                "reason": r.reason,
                "items": r.items or [],
                "status": r.status,
                "requested_at": r.requested_at.isoformat() if r.requested_at else None,
                "processed_at": r.processed_at.isoformat() if r.processed_at else None,
            }
            for r in rows
        ]

    def list_returns_for_order(self, user_id: str, order_id: str) -> List[dict]:
        """List return requests for a specific order (must belong to user)."""
        order = (
            self._db.query(OrderModel)
            .filter(OrderModel.id == order_id, OrderModel.user_id == user_id)
            .first()
        )
        if not order:
            return []

        rows = (
            self._db.query(ReturnRequestModel)
            .filter(ReturnRequestModel.order_id == order_id, ReturnRequestModel.user_id == user_id)
            .order_by(ReturnRequestModel.requested_at.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "order_id": r.order_id,
                "reason": r.reason,
                "items": r.items or [],
                "status": r.status,
                "requested_at": r.requested_at.isoformat() if r.requested_at else None,
                "processed_at": r.processed_at.isoformat() if r.processed_at else None,
            }
            for r in rows
        ]
