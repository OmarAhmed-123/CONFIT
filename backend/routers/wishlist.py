"""
CONFIT Backend — Wishlist Router
==================================
Manage user wishlists backed by the database (WishlistItem model).
All endpoints require authentication.
"""

import uuid
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import WishlistItem
from utils.auth_deps import require_auth
from services.auth_service import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wishlist", tags=["Wishlist"])


class AddWishlistRequest(BaseModel):
    product_id: str
    name: str
    brand: str = ""
    price: float | None = None
    image_url: str | None = None


# ── Endpoints ──────────────────────────────────────────────────────


@router.get("")
async def get_wishlist(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Return all wishlist items for the authenticated user."""
    items: list[WishlistItem] = (
        db.query(WishlistItem)
        .filter(WishlistItem.user_id == user.id)
        .order_by(WishlistItem.created_at.desc())
        .all()
    )
    return [
        {
            "id": item.id,
            "product_id": item.product_id,
            "name": item.name,
            "brand": item.brand,
            "price": item.price,
            "image_url": item.image_url,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in items
    ]


@router.post("")
async def add_to_wishlist(
    payload: AddWishlistRequest,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Add a product to the user's wishlist. Idempotent — duplicate product IDs are ignored."""
    existing = (
        db.query(WishlistItem)
        .filter(
            WishlistItem.user_id == user.id,
            WishlistItem.product_id == payload.product_id,
        )
        .first()
    )
    if existing:
        return {"success": True, "message": "Already in wishlist", "id": existing.id}

    item = WishlistItem(
        id=str(uuid.uuid4()),
        user_id=user.id,
        product_id=payload.product_id,
        name=payload.name,
        brand=payload.brand or None,
        price=payload.price,
        image_url=payload.image_url,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    logger.info("Wishlist item added: user=%s product=%s", user.id, payload.product_id)
    return {"success": True, "message": "Added to wishlist", "id": item.id}


@router.delete("/{product_id}")
async def remove_from_wishlist(
    product_id: str,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Remove a product from the user's wishlist by product_id."""
    rows_deleted = (
        db.query(WishlistItem)
        .filter(
            WishlistItem.user_id == user.id,
            WishlistItem.product_id == product_id,
        )
        .delete(synchronize_session=False)
    )
    db.commit()

    if rows_deleted == 0:
        raise HTTPException(status_code=404, detail="Item not found in wishlist")

    return {"success": True, "message": "Removed from wishlist"}


@router.delete("/")
async def clear_wishlist(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Remove all items from the user's wishlist."""
    db.query(WishlistItem).filter(WishlistItem.user_id == user.id).delete(
        synchronize_session=False
    )
    db.commit()
    return {"success": True, "message": "Wishlist cleared"}
