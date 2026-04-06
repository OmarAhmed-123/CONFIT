"""
CONFIT Backend — MY CLOSET Virtual Wardrobe v1 Router
======================================================
POST /api/v1/closet/items              — Upload wardrobe item (photo)
GET  /api/v1/closet/items              — List wardrobe items
GET  /api/v1/closet/suggestions        — Outfit suggestions (closet + catalog)
POST /api/v1/closet/check-duplicate    — Duplicate purchase alert
DEL  /api/v1/closet/items/{id}         — Delete item
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from pydantic import BaseModel, Field

from database.session import get_db
from services.ai.wardrobe_service import WardrobeService
from services.ai.cost_tracker import get_cost_tracker
from utils.auth_deps import require_auth
from services.auth_service import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/closet", tags=["MY CLOSET — Virtual Wardrobe"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


# ── Schemas ──────────────────────────────────────────────────────────

class WardrobeItemResponse(BaseModel):
    id: str
    name: str
    category: str
    subcategory: Optional[str] = None
    colors: list[str] = []
    patterns: list[str] = []
    materials: list[str] = []
    brands: list[str] = []
    tags: list[str] = []
    image_url: Optional[str] = None
    purchase_price: Optional[float] = None
    times_worn: int = 0
    is_favorite: bool = False
    created_at: str = ""


class DuplicateCheckRequest(BaseModel):
    product_name: str = Field(..., min_length=1)
    category: Optional[str] = None
    color: Optional[str] = None
    product_sku: Optional[str] = None


class DuplicateAlertResponse(BaseModel):
    has_duplicate: bool
    similarity_score: float = 0.0
    existing_item: Optional[WardrobeItemResponse] = None
    message: str = ""


class OutfitSuggestionItem(BaseModel):
    item_id: str
    name: str
    category: str
    color: Optional[str] = None
    image_url: Optional[str] = None
    source: str = "closet"  # closet | catalog
    sku: Optional[str] = None


class OutfitSuggestionResponse(BaseModel):
    outfit_id: str
    name: str
    items: list[OutfitSuggestionItem]
    occasion: Optional[str] = None
    style_match_score: float = 0.0
    color_harmony_score: float = 0.0
    tips: list[str] = []


# ── Helpers ──────────────────────────────────────────────────────────

def _get_service(db=Depends(get_db)) -> WardrobeService:
    from core.redis_client import get_redis_client
    redis = get_redis_client()
    s3 = None
    try:
        from core.s3_client import get_s3_client
        s3 = get_s3_client()
    except Exception:
        pass
    service = WardrobeService(db, redis, s3)
    tracker = get_cost_tracker(db, redis)
    service.set_cost_tracker(tracker)
    return service


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/items", response_model=WardrobeItemResponse)
async def upload_closet_item(
    photo: UploadFile = File(..., description="Clothing item photo"),
    name: Optional[str] = Form(None),
    user: UserProfile = Depends(require_auth),
    service: WardrobeService = Depends(_get_service),
):
    """
    Upload a photo to add to your virtual closet.

    Flow:
    1. Upload to S3 (user private bucket, encrypted)
    2. Google Vision → auto-tag (category, color, pattern, style)
    3. Compute embedding for similarity
    4. Create WardrobeItem record
    """
    # Validate file
    if photo.content_type and photo.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Invalid file type: {photo.content_type}. Allowed: JPEG, PNG, WebP, GIF")

    contents = await photo.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Maximum: {MAX_FILE_SIZE // (1024*1024)} MB")
    if len(contents) < 100:
        raise HTTPException(400, "File appears to be empty or too small.")

    # Budget kill-switch
    if service._cost_tracker and service._cost_tracker.is_kill_switch_active():
        raise HTTPException(503, "AI services temporarily unavailable due to budget limits.")

    item_name = name or photo.filename or "New Item"

    item = await service.add_item(
        user_id=str(user.id),
        image_bytes=contents,
        name=item_name,
    )

    return WardrobeItemResponse(
        id=item.id,
        name=item.name,
        category=item.category,
        subcategory=item.subcategory,
        colors=item.colors,
        patterns=item.patterns,
        materials=item.materials,
        brands=item.brands,
        tags=item.tags,
        image_url=item.image_url,
        purchase_price=item.purchase_price,
        times_worn=item.times_worn,
        is_favorite=item.is_favorite,
        created_at=item.created_at.isoformat() if item.created_at else "",
    )


@router.get("/items", response_model=list[WardrobeItemResponse])
async def list_closet_items(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: UserProfile = Depends(require_auth),
    service: WardrobeService = Depends(_get_service),
):
    """List all items in the user's virtual closet."""
    items = service.list_items(str(user.id))

    result = []
    for item in items:
        if isinstance(item, dict):
            d = item
        else:
            d = {
                "id": getattr(item, "id", ""),
                "name": getattr(item, "name", ""),
                "category": getattr(item, "category", ""),
                "subcategory": getattr(item, "subcategory", None),
                "colors": getattr(item, "colors", []),
                "patterns": getattr(item, "patterns", []),
                "materials": getattr(item, "materials", []),
                "brands": getattr(item, "brands", []),
                "tags": getattr(item, "tags", []),
                "image_url": getattr(item, "image_url", None),
                "purchase_price": getattr(item, "purchase_price", None),
                "times_worn": getattr(item, "times_worn", 0),
                "is_favorite": getattr(item, "is_favorite", False),
                "created_at": getattr(item, "created_at", ""),
            }

        # Filter by category
        if category and d["category"] != category:
            continue
        # Filter by search
        if search and search.lower() not in d["name"].lower():
            continue

        created_str = d["created_at"]
        if hasattr(created_str, "isoformat"):
            created_str = created_str.isoformat()

        result.append(WardrobeItemResponse(
            id=str(d["id"]),
            name=d["name"],
            category=d["category"],
            subcategory=d.get("subcategory"),
            colors=d.get("colors", []),
            patterns=d.get("patterns", []),
            materials=d.get("materials", []),
            brands=d.get("brands", []),
            tags=d.get("tags", []),
            image_url=d.get("image_url"),
            purchase_price=d.get("purchase_price"),
            times_worn=d.get("times_worn", 0),
            is_favorite=d.get("is_favorite", False),
            created_at=str(created_str) if created_str else "",
        ))

    return result


@router.get("/suggestions", response_model=list[OutfitSuggestionResponse])
async def get_closet_suggestions(
    occasion: Optional[str] = Query(None),
    user: UserProfile = Depends(require_auth),
    service: WardrobeService = Depends(_get_service),
):
    """
    Get outfit suggestions that mix closet + catalog items.
    """
    outfits = await service.suggest_outfits(
        user_id=str(user.id),
        occasion=occasion,
    )

    suggestions = []
    for outfit in outfits:
        items = []
        for i in outfit.items if hasattr(outfit, "items") else outfit.get("items", []):
            if isinstance(i, dict):
                items.append(OutfitSuggestionItem(
                    item_id=str(i.get("id", "")),
                    name=i.get("name", ""),
                    category=i.get("category", ""),
                    color=i.get("color"),
                    image_url=i.get("image_url"),
                    source=i.get("source", "closet"),
                    sku=i.get("sku"),
                ))
            else:
                items.append(OutfitSuggestionItem(
                    item_id=str(getattr(i, "id", "")),
                    name=getattr(i, "name", ""),
                    category=getattr(i, "category", ""),
                    color=getattr(i, "color", None),
                    image_url=getattr(i, "image_url", None),
                    source=getattr(i, "source", "closet"),
                    sku=getattr(i, "sku", None),
                ))

        suggestions.append(OutfitSuggestionResponse(
            outfit_id=outfit.outfit_id if hasattr(outfit, "outfit_id") else outfit.get("outfit_id", ""),
            name=outfit.name if hasattr(outfit, "name") else outfit.get("name", ""),
            items=items,
            occasion=outfit.occasion if hasattr(outfit, "occasion") else outfit.get("occasion"),
            style_match_score=outfit.style_match_score if hasattr(outfit, "style_match_score") else outfit.get("style_match_score", 0),
            color_harmony_score=outfit.color_harmony_score if hasattr(outfit, "color_harmony_score") else outfit.get("color_harmony_score", 0),
            tips=outfit.tips if hasattr(outfit, "tips") else outfit.get("tips", []),
        ))

    return suggestions


@router.post("/check-duplicate", response_model=DuplicateAlertResponse)
async def check_duplicate_purchase(
    payload: DuplicateCheckRequest,
    user: UserProfile = Depends(require_auth),
    service: WardrobeService = Depends(_get_service),
):
    """
    Before checkout, check if similar item exists in closet.
    Returns warning like: "You already own a similar Ivory Linen Blazer."
    """
    alerts = await service.check_duplicates(
        user_id=str(user.id),
        item_data={
            "name": payload.product_name,
            "category": payload.category,
            "color": payload.color,
            "sku": payload.product_sku,
        },
    )

    if not alerts:
        return DuplicateAlertResponse(has_duplicate=False, message="No similar items found in your closet.")

    alert = alerts[0]
    existing = alert.existing_item if hasattr(alert, "existing_item") else alert.get("existing_item")

    existing_resp = None
    if existing:
        if isinstance(existing, dict):
            d = existing
        else:
            d = {
                "id": str(getattr(existing, "id", "")),
                "name": getattr(existing, "name", ""),
                "category": getattr(existing, "category", ""),
                "subcategory": getattr(existing, "subcategory", None),
                "colors": getattr(existing, "colors", []),
                "patterns": getattr(existing, "patterns", []),
                "materials": getattr(existing, "materials", []),
                "brands": getattr(existing, "brands", []),
                "tags": getattr(existing, "tags", []),
                "image_url": getattr(existing, "image_url", None),
                "purchase_price": getattr(existing, "purchase_price", None),
                "times_worn": getattr(existing, "times_worn", 0),
                "is_favorite": getattr(existing, "is_favorite", False),
                "created_at": "",
            }
        existing_resp = WardrobeItemResponse(
            id=d.get("id", ""),
            name=d.get("name", ""),
            category=d.get("category", ""),
            subcategory=d.get("subcategory"),
            colors=d.get("colors", []),
            patterns=d.get("patterns", []),
            materials=d.get("materials", []),
            brands=d.get("brands", []),
            tags=d.get("tags", []),
            image_url=d.get("image_url"),
            purchase_price=d.get("purchase_price"),
            times_worn=d.get("times_worn", 0),
            is_favorite=d.get("is_favorite", False),
        )

    sim = alert.similarity_score if hasattr(alert, "similarity_score") else alert.get("similarity_score", 0)
    msg = alert.message if hasattr(alert, "message") else alert.get("message", "")

    return DuplicateAlertResponse(
        has_duplicate=True,
        similarity_score=sim,
        existing_item=existing_resp,
        message=msg,
    )


@router.delete("/items/{item_id}")
async def delete_closet_item(
    item_id: str,
    user: UserProfile = Depends(require_auth),
    service: WardrobeService = Depends(_get_service),
):
    """Delete a wardrobe item."""
    success = service.delete_item(str(user.id), item_id)
    if not success:
        raise HTTPException(404, "Wardrobe item not found")
    return {"success": True, "message": "Item removed from closet"}
