"""CONFIT Backend — Order Schemas."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator

from schemas.base import BaseSchema


# ── Request Schemas ─────────────────────────────────────────────────────

class OrderItemCreate(BaseModel):
    """Schema for order item."""
    product_id: str
    quantity: int = Field(..., ge=1, le=100)
    price: Decimal = Field(..., ge=0)


class OrderCreate(BaseModel):
    """Schema for creating an order."""
    items: List[OrderItemCreate] = Field(..., min_items=1)
    shipping_address: Dict[str, Any]
    billing_address: Optional[Dict[str, Any]] = None
    payment_method: str
    promo_code: Optional[str] = None
    notes: Optional[str] = None
    
    @validator("items")
    def validate_items(cls, v):
        if not v:
            raise ValueError("Order must have at least one item")
        return v


class OrderUpdate(BaseModel):
    """Schema for updating an order."""
    status: Optional[str] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None


class ReturnRequestCreate(BaseModel):
    """Schema for creating a return request."""
    order_id: str
    items: List[Dict[str, Any]] = Field(..., min_items=1)
    reason: str = Field(..., min_length=1, max_length=1000)
    notes: Optional[str] = None


# ── Response Schemas ─────────────────────────────────────────────────────

class OrderItemResponse(BaseSchema):
    """Schema for order item response."""
    id: str
    product_id: str
    product_name: Optional[str] = None
    quantity: int
    price: float


class OrderResponse(BaseSchema):
    """Schema for order response."""
    id: str
    user_id: str
    status: str
    total: float
    subtotal: float
    tax: float
    shipping: float
    discount: float
    currency: str = "USD"
    items: List[OrderItemResponse] = []
    shipping_address: Optional[Dict[str, Any]]
    tracking_number: Optional[str]
    placed_at: datetime
    updated_at: Optional[datetime]


class OrderDetailResponse(OrderResponse):
    """Detailed order response."""
    billing_address: Optional[Dict[str, Any]]
    payment_method: Optional[str]
    promo_code: Optional[str]
    notes: Optional[str]


class OrderListResponse(BaseModel):
    """Paginated order list response."""
    total: int
    orders: List[OrderResponse]


class ReturnRequestResponse(BaseSchema):
    """Schema for return request response."""
    id: str
    order_id: str
    items: List[Dict[str, Any]]
    reason: str
    status: str
    requested_at: datetime
    processed_at: Optional[datetime]
