from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class WardrobeItemBase(BaseModel):
    """Core attributes for a wardrobe item stored in the Virtual Wardrobe."""

    name: str = Field(..., min_length=1, max_length=200)
    brand: Optional[str] = Field(None, max_length=100)
    category: str = Field(..., description="High-level category such as tops, bottoms, dresses, shoes")
    color: Optional[str] = Field(None, max_length=50)
    size: Optional[str] = Field(None, max_length=20)
    price: Optional[float] = Field(None, ge=0)
    currency: str = Field("USD", max_length=10)
    image_url: Optional[HttpUrl] = None
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Free-form notes about fit, occasions, or styling tips.",
    )
    source_product_id: Optional[str] = Field(
        None,
        description="Optional reference to a CONFIT marketplace product.",
    )


class WardrobeItemCreate(WardrobeItemBase):
    """Payload for creating a new wardrobe item."""

    pass


class WardrobeItemUpdate(BaseModel):
    """Partial update for a wardrobe item."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    brand: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    image_url: Optional[HttpUrl] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = Field(None, max_length=500)
    source_product_id: Optional[str] = None


class WardrobeItemResponse(WardrobeItemBase):
    """Representation of a wardrobe item returned to the client."""

    id: str
    owner_user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DuplicateCheckRequest(BaseModel):
    """Request body for duplicate wardrobe detection."""

    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None


class WardrobeOutfitItem(BaseModel):
    """Single item within an auto-generated outfit suggestion."""

    id: str
    name: str
    category: str
    color: Optional[str] = None
    image_url: Optional[HttpUrl] = None


class WardrobeOutfitSuggestion(BaseModel):
    """Represents one complete outfit suggestion generated from the wardrobe."""

    id: str
    title: str
    items: List[WardrobeOutfitItem]
    estimated_total_value: Optional[float] = None
    occasion_hint: Optional[str] = None

