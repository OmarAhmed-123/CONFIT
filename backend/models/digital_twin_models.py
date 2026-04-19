from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class DigitalTwinCreateRequest(BaseModel):
    """Request to start a digital twin training session."""

    photo_urls: List[HttpUrl] = Field(
        ...,
        min_items=3,
        max_items=5,
        description="URLs of 3–5 source photos for the digital twin.",
    )


class DigitalTwinProfileResponse(BaseModel):
    """Minimal representation of a trained (or pending) twin."""

    id: UUID
    reference_images: List[HttpUrl] = []
    twin_image_url: Optional[str] = None
    skin_undertone: Optional[str] = None
    environment: str = "studio"
    status: str
    meta: dict = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DigitalTwinRenderRequest(BaseModel):
    """Request to generate a new render for an existing twin."""

    environment: str = Field(
        "studio",
        description="Scene prompt such as 'beach', 'office', 'evening', 'street'.",
        max_length=50,
    )
    garment_product_id: Optional[str] = Field(
        None,
        description="Optional CONFIT product id to emphasize in the render.",
    )


class DigitalTwinRenderResponse(BaseModel):
    """Response for a single render."""

    id: str
    twin_id: str
    environment: Optional[str]
    garment_product_id: Optional[str]
    image_url: HttpUrl
    created_at: datetime


