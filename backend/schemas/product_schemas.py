"""CONFIT Backend — Product Schemas."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator

from schemas.base import BaseSchema


# ── Request Schemas ─────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    """Schema for creating a product."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    price: Decimal = Field(..., ge=0)
    brand_id: Optional[str] = None
    store_id: Optional[str] = None
    image_url: Optional[str] = Field(None, max_length=1024)
    images: Optional[List[str]] = []
    tags: Optional[List[str]] = []
    color: Optional[str] = None
    size: Optional[str] = None
    style_compatibility: Optional[int] = Field(None, ge=0, le=100)


class ProductUpdate(BaseModel):
    """Schema for updating a product."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[Decimal] = Field(None, ge=0)
    image_url: Optional[str] = Field(None, max_length=1024)
    images: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    color: Optional[str] = None
    size: Optional[str] = None
    is_active: Optional[bool] = None
    style_compatibility: Optional[int] = Field(None, ge=0, le=100)


class ProductSearchQuery(BaseModel):
    """Schema for product search query."""
    query: Optional[str] = None
    category: Optional[str] = None
    min_price: Optional[Decimal] = Field(None, ge=0)
    max_price: Optional[Decimal] = Field(None, ge=0)
    brand_id: Optional[str] = None
    tags: Optional[List[str]] = None
    gender: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


# ── Response Schemas ─────────────────────────────────────────────────────

class ProductResponse(BaseSchema):
    """Schema for product response."""
    id: str
    name: str
    description: Optional[str]
    category: str
    price: float
    brand_id: Optional[str]
    store_id: Optional[str]
    image_url: Optional[str]
    images: List[str] = []
    tags: List[str] = []
    color: Optional[str]
    size: Optional[str]
    is_active: bool
    style_compatibility: int = 85
    created_at: datetime


class ProductDetailResponse(ProductResponse):
    """Detailed product response with brand info."""
    brand_name: Optional[str] = None
    store_name: Optional[str] = None
    description: Optional[str]


class ProductListResponse(BaseModel):
    """Paginated product list response."""
    total: int
    products: List[ProductResponse]


class ProductFeaturedQuery(BaseModel):
    """Schema for featured products query."""
    limit: int = Field(default=12, ge=1, le=50)
    gender: Optional[str] = None
    category: Optional[str] = None
