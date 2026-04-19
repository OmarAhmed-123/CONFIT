from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class GeoLocation(BaseModel):
    lat: float
    lng: float

class StoreBase(BaseModel):
    name: str = Field(..., description="Store name")
    brand_id: str = Field(..., description="ID of the brand this store belongs to")
    address: str = Field(..., description="Full address")
    city: str
    state: Optional[str] = None
    country: str
    postal_code: str
    phone: Optional[str] = None
    email: Optional[str] = None
    location: Optional[GeoLocation] = None
    hours: Dict[str, str] = Field(default_factory=dict, description="Opening hours per day")
    services: List[str] = Field(default_factory=list, description="Services available (e.g. 'BOPIS', 'Stylist')")

class StoreCreate(StoreBase):
    pass

class StoreResponse(StoreBase):
    id: str
    distance_km: Optional[float] = None
    
    class Config:
        from_attributes = True

class InventoryCheck(BaseModel):
    product_id: str
    variant_id: Optional[str] = None
    quantity: int
