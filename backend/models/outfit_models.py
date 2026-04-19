from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class OutfitItem(BaseModel):
    """Single line item within a saved outfit."""

    item_type: Literal["product", "wardrobe"] = Field(
        ...,
        description="Indicates whether this item is from the CONFIT marketplace or the user's wardrobe.",
    )
    reference_id: str = Field(
        ...,
        description="Product ID (for marketplace items) or wardrobe item ID.",
    )
    name: str = Field(..., min_length=1, max_length=200)
    brand: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = None
    color: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    currency: str = Field("USD", max_length=10)


class OutfitCreate(BaseModel):
    """Payload for creating a new outfit."""

    title: str = Field(..., min_length=1, max_length=200)
    items: List[OutfitItem] = Field(..., min_items=1)
    occasion: Optional[str] = Field(
        None,
        description="Optional occasion hint such as 'work', 'party', 'wedding'.",
    )
    notes: Optional[str] = Field(None, max_length=500)
    budget_limit: Optional[float] = Field(
        None,
        ge=0,
        description="Optional budget ceiling used in the client for validation.",
    )


class OutfitUpdate(BaseModel):
    """Partial update for an outfit."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    items: Optional[List[OutfitItem]] = None
    occasion: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)
    budget_limit: Optional[float] = Field(None, ge=0)


class OutfitResponse(BaseModel):
    """Representation of a saved outfit returned to the client."""

    id: str
    owner_user_id: str
    title: str
    items: List[OutfitItem]
    occasion: Optional[str] = None
    notes: Optional[str] = None
    budget_limit: Optional[float] = None
    total_price: Optional[float] = None
    currency: str = "USD"
    created_at: datetime
    updated_at: datetime
    share_slug: Optional[str] = Field(
        None,
        description="Optional generated slug that can be used to share the outfit publicly.",
    )

    class Config:
        from_attributes = True

