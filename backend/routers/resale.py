import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import ResaleListing, WardrobeItem as WardrobeItemModel
from models.resale_models import (
    ResaleListingResponse,
    ResaleListFromWardrobeRequest,
    ResalePurchaseResponse,
    EcoImpactResponse,
)
from utils.auth_deps import require_auth, optional_auth
from services.auth_service import UserProfile

router = APIRouter(prefix="/api/resale", tags=["resale"])


def _listing_to_response(row: ResaleListing, item: Optional[WardrobeItemModel]) -> ResaleListingResponse:
    return ResaleListingResponse(
        id=row.id,
        wardrobe_item_id=row.wardrobe_item_id,
        seller_user_id=row.seller_user_id,
        buyer_user_id=row.buyer_user_id,
        status=row.status,  # type: ignore
        price=row.price,
        currency=row.currency,
        created_at=row.created_at,
        sold_at=row.sold_at,
        item_name=getattr(item, "name", None),
        item_brand=getattr(item, "brand", None),
        item_category=getattr(item, "category", None),
        item_color=getattr(item, "color", None),
        item_image_url=getattr(item, "image_url", None),
    )


@router.post("/list-from-wardrobe/{wardrobe_item_id}", response_model=ResaleListingResponse)
async def list_from_wardrobe(
    wardrobe_item_id: str,
    payload: ResaleListFromWardrobeRequest,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    item = (
        db.query(WardrobeItemModel)
        .filter(WardrobeItemModel.id == wardrobe_item_id, WardrobeItemModel.owner_user_id == user.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")

    listing_id = f"listing-{uuid.uuid4().hex[:12]}"
    row = ResaleListing(
        id=listing_id,
        wardrobe_item_id=item.id,
        seller_user_id=user.id,
        buyer_user_id=None,
        status="active",
        price=payload.price,
        currency=payload.currency,
        created_at=datetime.utcnow(),
        sold_at=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _listing_to_response(row, item)


@router.get("/listings", response_model=List[ResaleListingResponse])
async def list_listings(
    db: Session = Depends(get_db),
    status: str = Query(default="active"),
    limit: int = Query(default=50, ge=1, le=200),
):
    q = db.query(ResaleListing)
    if status in {"draft", "active", "sold", "cancelled"}:
        q = q.filter(ResaleListing.status == status)
    rows = q.order_by(ResaleListing.created_at.desc()).limit(limit).all()

    out: List[ResaleListingResponse] = []
    for r in rows:
        item = db.query(WardrobeItemModel).filter(WardrobeItemModel.id == r.wardrobe_item_id).first()
        out.append(_listing_to_response(r, item))
    return out


@router.get("/my-listings", response_model=List[ResaleListingResponse])
async def my_listings(
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    rows = (
        db.query(ResaleListing)
        .filter(ResaleListing.seller_user_id == user.id)
        .order_by(ResaleListing.created_at.desc())
        .all()
    )
    out: List[ResaleListingResponse] = []
    for r in rows:
        item = db.query(WardrobeItemModel).filter(WardrobeItemModel.id == r.wardrobe_item_id).first()
        out.append(_listing_to_response(r, item))
    return out


@router.post("/listings/{listing_id}/purchase", response_model=ResalePurchaseResponse)
async def purchase_listing(
    listing_id: str,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """
    Purchase endpoint (stub).
    Phase 2: integrate Stripe Connect; Phase 3: escrow + shipping workflow.
    """
    row = db.query(ResaleListing).filter(ResaleListing.id == listing_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Listing not found")
    if row.status != "active":
        raise HTTPException(status_code=400, detail="Listing is not available")
    if row.seller_user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot purchase your own listing")

    row.status = "sold"
    row.buyer_user_id = user.id
    row.sold_at = datetime.utcnow()
    db.commit()
    return ResalePurchaseResponse(success=True, message="Purchase recorded (demo).")


@router.get("/eco-impact", response_model=EcoImpactResponse)
async def eco_impact(
    db: Session = Depends(get_db),
    user: Optional[UserProfile] = Depends(optional_auth),
    period: str = Query(default="weekly"),
):
    """
    Eco impact (demo): estimates savings from resale activity.
    """
    if not user:
        return EcoImpactResponse(period=period, co2_saved_kg=0.0, water_saved_l=0.0, message="Sign in to see your impact.")

    sold = db.query(ResaleListing).filter(ResaleListing.seller_user_id == user.id, ResaleListing.status == "sold").count()
    # Rough demo multipliers per resale
    co2 = round(sold * 6.5, 2)
    water = round(sold * 1800.0, 2)
    return EcoImpactResponse(period=period, co2_saved_kg=co2, water_saved_l=water, message="Estimated savings from your resale activity.")

