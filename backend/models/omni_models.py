from typing import Optional, List

from pydantic import BaseModel, Field


class QrScanRequest(BaseModel):
    qr_code: str = Field(..., min_length=1, max_length=128)


class QrScanResponse(BaseModel):
    success: bool
    product_id: Optional[str] = None
    store_id: Optional[str] = None
    message: str = ""


class StoreRouteResponse(BaseModel):
    store_id: str
    route: List[dict]  # [{product_id, aisle, shelf}]
    message: str = ""

