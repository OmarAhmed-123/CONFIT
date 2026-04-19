from datetime import datetime
from typing import Optional, Literal, List

from pydantic import BaseModel, Field, HttpUrl


ListingStatus = Literal["draft", "active", "sold", "cancelled"]


class ResaleListingResponse(BaseModel):
    id: str
    wardrobe_item_id: str
    seller_user_id: str
    buyer_user_id: Optional[str] = None
    status: ListingStatus
    price: float
    currency: str
    created_at: datetime
    sold_at: Optional[datetime] = None

    # Enriched fields for UI
    item_name: Optional[str] = None
    item_brand: Optional[str] = None
    item_category: Optional[str] = None
    item_color: Optional[str] = None
    item_image_url: Optional[str] = None

    class Config:
        from_attributes = True


class ResaleListFromWardrobeRequest(BaseModel):
    price: float = Field(..., ge=0)
    currency: str = Field("USD", max_length=10)


class ResalePurchaseResponse(BaseModel):
    success: bool
    message: str


class EcoImpactResponse(BaseModel):
    period: str
    co2_saved_kg: float
    water_saved_l: float
    message: str = ""

