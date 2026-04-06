"""
CONFIT Backend — Orders Router
================================
Endpoints for creating and retrieving orders.
"""

import logging
from typing import Annotated, Optional, Literal, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from sqlalchemy.orm import Session

from database.session import get_db
from services.order_service import OrderService
from utils.auth_deps import optional_auth, require_auth
from services.auth_service import AuthService, UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orders", tags=["Orders"])


def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    return OrderService(db)


def _get_user_id(user: UserProfile | None) -> str:
    """User ID for order ownership; guest orders use shared guest user."""
    return user.id if user else "user-guest"


# ── Request / Response Models ──────────────────────────────────────


def _coerce_item_str(v: object) -> str:
    """Normalize cart line strings; reject structured values that break Pydantic `str` parsing."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (dict, list)):
        return ""
    return str(v)


class OrderItemRequest(BaseModel):
    productId: Annotated[str, BeforeValidator(_coerce_item_str)]
    name: Annotated[str, BeforeValidator(_coerce_item_str)]
    brand: Annotated[str, BeforeValidator(_coerce_item_str)] = ""
    price: float = Field(ge=0)
    quantity: int = Field(ge=1, default=1)
    size: Annotated[str, BeforeValidator(_coerce_item_str)] = ""
    image: Annotated[str, BeforeValidator(_coerce_item_str)] = ""


class ShippingAddressRequest(BaseModel):
    name: str = Field(min_length=1)
    address: str = Field(min_length=1)
    city: str = Field(min_length=1)
    state: str = ""
    zip: str = ""
    country: str = "US"


class CreateOrderRequest(BaseModel):
    """Client may send extra fields (e.g. deliveryMethod); ignore unknown keys for 422 safety."""

    model_config = ConfigDict(extra="ignore")

    items: list[OrderItemRequest] = Field(min_length=1)
    shippingAddress: ShippingAddressRequest
    paymentMethod: str = "card"
    deliveryMethod: Optional[str] = None  # "shipping" | "pickup"
    pickupStoreId: Optional[str] = None
    pickupTime: Optional[str] = None  # ISO8601 string


class OrderStatusUpdateRequest(BaseModel):
    status: Literal[
        "confirmed",
        "processing",
        "shipped",
        "delivered",
        "cancelled",
        "returned",
    ]
    trackingNumber: Optional[str] = None
    estimatedDelivery: Optional[str] = None


class CreateReturnRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)
    items: Optional[list[dict]] = None


# ── Endpoints ──────────────────────────────────────────────────────


@router.post("")
async def create_order(
    request: CreateOrderRequest,
    user: UserProfile | None = Depends(optional_auth),
    order_service: OrderService = Depends(get_order_service),
    db: Session = Depends(get_db),
):
    """Create a new order from the checkout flow."""
    user_id = _get_user_id(user)

    items_data = [
        {
            "productId": item.productId,
            "name": item.name,
            "brand": item.brand,
            "price": item.price,
            "quantity": item.quantity,
            "image": item.image,
        }
        for item in request.items
    ]
    address_data = request.shippingAddress.model_dump()

    # Prepare pickup/shipping variables up-front (order_service needs them).
    delivery_method = (request.deliveryMethod or "").strip().lower()
    pickup_store_id = (request.pickupStoreId or "").strip() if delivery_method == "pickup" else None
    pickup_time = (request.pickupTime or "").strip() if delivery_method == "pickup" else None

    pm = (request.paymentMethod or "").strip().lower()
    # Card payments use Stripe Payment Element; stay pending until /api/payments/confirm.
    # BNPL stays "success at create" here until a live BNPL redirect is integrated.
    if pm == "card" and delivery_method in ("pickup", "shipping"):
        pay_status = "pending"
    else:
        pay_status = "success"

    order = order_service.create_order(
        user_id=user_id,
        items=items_data,
        shipping_address=address_data,
        payment_method=request.paymentMethod,
        delivery_method=delivery_method if delivery_method in ("shipping", "pickup") else None,
        pickup_store_id=pickup_store_id if delivery_method == "pickup" else None,
        pickup_time=pickup_time if delivery_method == "pickup" else None,
        payment_status=pay_status,
    )

    # Validate pickup fields, but do not create/emit notifications here.
    if delivery_method == "pickup":
        if not pickup_store_id or not pickup_time:
            raise HTTPException(status_code=400, detail="pickupStoreId and pickupTime are required for pickup orders")

        # Fetch store from DB only (never trust frontend store name).
        from database.models import Store as StoreModel
        store = db.query(StoreModel).filter(StoreModel.id == pickup_store_id).first()
        if not store:
            raise HTTPException(status_code=400, detail="Invalid pickup store")
    else:
        delivery_method = "shipping"

    # Emit sales notification (async, non-blocking)
    try:
        from services.notificationService.sales_notifications import SalesNotificationService, OrderPlacedData
        import asyncio

        notif_service = SalesNotificationService(db)
        order_data = OrderPlacedData(
            order_id=order["id"],
            customer_user_id=user_id,
            store_id=pickup_store_id if delivery_method == "pickup" else None,
            total=float(order.get("total", 0)),
            currency="USD",
            delivery_method=delivery_method,
        )
        # Run async notification in background
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(notif_service.handle_order_placed(order_data))
        else:
            asyncio.run(notif_service.handle_order_placed(order_data))
    except Exception as e:
        logger.warning("Failed to emit sales notification: %s", e)

    return {
        "success": True,
        "order": order,
        "message": f"Order {order['id']} placed successfully!",
    }


@router.get("")
async def list_orders(
    user: UserProfile | None = Depends(optional_auth),
    order_service: OrderService = Depends(get_order_service),
):
    """Get all orders for the authenticated user (or guest)."""
    user_id = _get_user_id(user)
    orders = order_service.get_orders(user_id)

    return {
        "success": True,
        "orders": orders,
        "total": len(orders),
    }


@router.get("/returns")
async def list_user_returns(
    user: UserProfile = Depends(require_auth),
    order_service: OrderService = Depends(get_order_service),
):
    """List all return requests created by the authenticated user."""
    records = order_service.list_returns(user.id)
    return {
        "success": True,
        "returns": records,
        "total": len(records),
    }


@router.get("/{order_id}")
async def get_order(
    order_id: str,
    user: UserProfile | None = Depends(optional_auth),
    order_service: OrderService = Depends(get_order_service),
):
    """Get a specific order by ID."""
    user_id = _get_user_id(user)
    order = order_service.get_order_by_id(user_id, order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "success": True,
        "order": order,
    }


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: str,
    payload: OrderStatusUpdateRequest,
    user: UserProfile = Depends(require_auth),
    order_service: OrderService = Depends(get_order_service),
):
    """
    Update order status and optional tracking information.

    Restricted to authenticated users to avoid exposing order data
    to unauthorised callers.
    """
    updated = order_service.update_status(
        user_id=user.id,
        order_id=order_id,
        status=payload.status,
        tracking_number=payload.trackingNumber,
        estimated_delivery=payload.estimatedDelivery,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "success": True,
        "order": updated,
    }


@router.post("/{order_id}/returns")
async def create_return_request(
    order_id: str,
    payload: CreateReturnRequest,
    user: UserProfile = Depends(require_auth),
    order_service: OrderService = Depends(get_order_service),
):
    """Create a return request for the specified order."""
    order = order_service.get_order_by_id(user.id, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    record = order_service.create_return(
        user_id=user.id,
        order_id=order_id,
        reason=payload.reason,
        items=payload.items,
    )

    order_service.update_status(user.id, order_id, status="returned")

    return {
        "success": True,
        "return": record,
    }


@router.get("/{order_id}/returns")
async def list_order_returns(
    order_id: str,
    user: UserProfile = Depends(require_auth),
    order_service: OrderService = Depends(get_order_service),
):
    """List all return requests associated with a single order."""
    records = order_service.list_returns_for_order(user.id, order_id)
    return {
        "success": True,
        "returns": records,
        "total": len(records),
    }


@router.get("/health", include_in_schema=False)
async def orders_health():
    """Health check for the orders service."""
    return {"status": "ok", "service": "orders"}
