"""CONFIT Backend — Wardrobe Schemas."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator

from schemas.base import BaseSchema


# ── Request Schemas ─────────────────────────────────────────────────────

class WardrobeItemCreate(BaseModel):
    """Schema for adding wardrobe item."""
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    image_url: Optional[str] = Field(None, max_length=1024)
    brand: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    tags: Optional[List[str]] = []
    notes: Optional[str] = None
    purchase_date: Optional[datetime] = None


class WardrobeItemUpdate(BaseModel):
    """Schema for updating wardrobe item."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    image_url: Optional[str] = Field(None, max_length=1024)
    brand: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class OutfitCreate(BaseModel):
    """Schema for creating an outfit."""
    name: Optional[str] = Field(None, max_length=255)
    occasion: Optional[str] = Field(None, max_length=100)
    item_ids: List[str] = Field(..., min_items=1)
    notes: Optional[str] = None


class WardrobeSearchQuery(BaseModel):
    """Schema for wardrobe search."""
    category: Optional[str] = None
    color: Optional[str] = None
    brand: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


# ── Response Schemas ─────────────────────────────────────────────────────

class WardrobeItemResponse(BaseSchema):
    """Schema for wardrobe item response."""
    id: str
    name: str
    category: str
    image_url: Optional[str]
    brand: Optional[str]
    color: Optional[str]
    size: Optional[str]
    price: Optional[float]
    tags: List[str] = []
    is_active: bool
    created_at: datetime


class WardrobeItemDetailResponse(WardrobeItemResponse):
    """Detailed wardrobe item with usage stats."""
    notes: Optional[str]
    purchase_date: Optional[datetime]
    wear_count: int = 0
    last_worn_at: Optional[datetime]
    days_since_worn: Optional[int]


class WardrobeListResponse(BaseModel):
    """Paginated wardrobe list response."""
    total: int
    items: List[WardrobeItemResponse]


class OutfitResponse(BaseSchema):
    """Schema for outfit response."""
    id: str
    name: Optional[str]
    occasion: Optional[str]
    items: List[WardrobeItemResponse]
    total_price: Optional[float]
    created_at: datetime


class WardrobeStatsResponse(BaseModel):
    """Schema for wardrobe statistics."""
    total_items: int
    total_value: float
    items_by_category: Dict[str, int]
    items_by_color: Dict[str, int]
    most_worn_items: List[WardrobeItemResponse]
    never_worn_items: int
    sustainability_score: Optional[float]


class WardrobeAnalyticsResponse(BaseModel):
    """Schema for wardrobe analytics."""
    stats: WardrobeStatsResponse
    color_distribution: Dict[str, int]
    category_distribution: Dict[str, int]
    brand_distribution: Dict[str, int]
    usage_patterns: Dict[str, Any]
