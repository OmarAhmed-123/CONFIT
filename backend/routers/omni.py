"""
CONFIT Backend — Omnichannel Router
=====================================
Smart Mirror / QR Scan and in-store navigation endpoints.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import QrScanSession
from utils.auth_deps import require_auth
from services.auth_service import UserProfile

router = APIRouter(prefix="/api/omni", tags=["omni"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class QrScanRequest(BaseModel):
    product_sku: str = Field(..., min_length=1, max_length=128)
    store_id: Optional[str] = None
    product_data: dict = {}


class QrScanResponse(BaseModel):
    id: str
    product_sku: str
    store_id: Optional[str] = None
    product_data: dict
    scanned_at: datetime

    model_config = {"from_attributes": True}


class StoreRouteResponse(BaseModel):
    store_id: str
    route: List[dict]   # [{product_id, aisle, shelf}]
    message: str = ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_uuid(value: str, field: str = "ID") -> str:
    """Validate a UUID string; raises 400 on invalid format."""
    try:
        uuid.UUID(value)
        return value
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field} format")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", tags=["omni"])
async def omni_root():
    """List available omni endpoints."""
    return {
        "endpoints": [
            "POST /api/omni/qr-scan",
            "GET  /api/omni/qr-scans",
            "GET  /api/omni/store-route",
        ]
    }


@router.post("/qr-scan", response_model=QrScanResponse)
async def qr_scan(
    payload: QrScanRequest,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Record a QR code scan from a smart mirror or omnichannel device."""
    store_id = None
    if payload.store_id:
        store_id = _validate_uuid(payload.store_id, "store ID")

    row = QrScanSession(
        user_id=str(user.id),
        product_sku=payload.product_sku,
        store_id=store_id,
        product_data=payload.product_data,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return QrScanResponse.model_validate(row)


@router.get("/qr-scans", response_model=List[QrScanResponse])
async def list_qr_scans(
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Get the authenticated user's QR scan history."""
    rows = (
        db.query(QrScanSession)
        .filter(QrScanSession.user_id == str(user.id))
        .order_by(QrScanSession.scanned_at.desc())
        .all()
    )
    return [QrScanResponse.model_validate(r) for r in rows]


@router.get("/store-route", response_model=StoreRouteResponse)
async def store_route(
    store_id: str,
    product_ids: str,
    user: UserProfile = Depends(require_auth),
):
    """
    Demo in-store navigation route.
    `product_ids` is a comma-separated list of product IDs.
    """
    import random

    _validate_uuid(store_id, "store ID")
    ids = [p.strip() for p in product_ids.split(",") if p.strip()]
    route: List[dict] = [
        {
            "product_id": pid,
            "aisle": random.randint(1, 20),
            "shelf": random.choice(["A", "B", "C", "D"]),
        }
        for pid in ids
    ]
    route.sort(key=lambda x: x["aisle"])
    return StoreRouteResponse(
        store_id=store_id,
        route=route,
        message="Demo route generated.",
    )
