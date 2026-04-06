"""
CONFIT Backend — Wardrobe Router
==================================
Endpoints for wardrobe management and image auto-tagging.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from services.wardrobe_service import WardrobeService
from models.wardrobe_models import (
    WardrobeItemCreate,
    WardrobeItemUpdate,
    WardrobeItemResponse,
    DuplicateCheckRequest,
    WardrobeOutfitSuggestion,
    WardrobeOutfitItem,
)
from utils.auth_deps import require_auth
from services.auth_service import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wardrobe", tags=["Wardrobe"])


def get_wardrobe_service(db: Session = Depends(get_db)) -> WardrobeService:
    return WardrobeService(db)


# Maximum upload size: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed image MIME types
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


# ── Endpoints ──────────────────────────────────────────────────────

@router.post("/auto-tag")
async def auto_tag_item(
    file: UploadFile = File(...),
    service: WardrobeService = Depends(get_wardrobe_service),
):
    """
    Upload a clothing image and get automatic category, color, and tag detection.
    
    Accepts JPEG, PNG, WebP, or GIF images up to 10 MB.
    Returns detected category, color, and suggested tags.
    """
    # Validate file type
    if file.content_type and file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: JPEG, PNG, WebP, GIF",
        )

    # Read file contents
    contents = await file.read()

    # Validate file size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)} MB",
        )

    if len(contents) < 100:
        raise HTTPException(
            status_code=400,
            detail="File appears to be empty or too small",
        )

    try:
        result = await service.auto_tag(
            image_bytes=contents,
            filename=file.filename,
        )

        return {
            "success": True,
            "category": result["category"],
            "color": result["color"],
            "tags": result["tags"],
            "message": f"Detected: {result['color']} {result['category']}",
        }

    except Exception as e:
        logger.error(f"Auto-tagging failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze image. Please try again.",
        )


@router.get("/items", response_model=List[WardrobeItemResponse])
async def list_wardrobe_items(
    user: UserProfile = Depends(require_auth),
    service: WardrobeService = Depends(get_wardrobe_service),
):
    """
    List all wardrobe items for the authenticated user.
    """
    raw_items = service.list_items(user.id)
    return [
        WardrobeItemResponse(
            **item,
        )
        for item in raw_items
    ]


@router.post("/items", response_model=WardrobeItemResponse)
async def add_wardrobe_item(
    payload: WardrobeItemCreate,
    user: UserProfile = Depends(require_auth),
    service: WardrobeService = Depends(get_wardrobe_service),
):
    """
    Add a new item to the authenticated user's Virtual Wardrobe.
    """
    item = service.add_item(user.id, payload.model_dump())
    return WardrobeItemResponse(**item)


@router.patch("/items/{item_id}", response_model=WardrobeItemResponse)
async def update_wardrobe_item(
    item_id: str,
    payload: WardrobeItemUpdate,
    user: UserProfile = Depends(require_auth),
    service: WardrobeService = Depends(get_wardrobe_service),
):
    """
    Update a wardrobe item belonging to the authenticated user.
    """
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = service.update_item(user.id, item_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")
    return WardrobeItemResponse(**updated)


@router.delete("/items/{item_id}")
async def delete_wardrobe_item(
    item_id: str,
    user: UserProfile = Depends(require_auth),
    service: WardrobeService = Depends(get_wardrobe_service),
):
    """
    Delete a wardrobe item from the authenticated user's Virtual Wardrobe.
    """
    success = service.delete_item(user.id, item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Wardrobe item not found")
    return {"success": True, "message": "Wardrobe item deleted"}


@router.post("/items/check-duplicate")
async def check_duplicate_item(
    payload: DuplicateCheckRequest,
    user: UserProfile = Depends(require_auth),
    service: WardrobeService = Depends(get_wardrobe_service),
):
    """
    Check if a similar item already exists in the user's wardrobe.
    Used to prevent accidental duplicate purchases.
    """
    matches = service.find_duplicates(user.id, payload.model_dump())
    return {
        "hasDuplicates": bool(matches),
        "matches": matches,
    }


@router.get("/outfits/suggestions", response_model=List[WardrobeOutfitSuggestion])
async def suggest_outfits_from_wardrobe(
    user: UserProfile = Depends(require_auth),
    service: WardrobeService = Depends(get_wardrobe_service),
):
    """
    Generate simple outfit suggestions using the user's Virtual Wardrobe.
    """
    outfits = service.suggest_outfits(user.id)

    suggestions: List[WardrobeOutfitSuggestion] = []
    for outfit in outfits:
        items = [
            WardrobeOutfitItem(
                id=i.get("id", ""),
                name=i.get("name", ""),
                category=i.get("category", ""),
                color=i.get("color"),
                image_url=i.get("image_url"),
            )
            for i in outfit.get("items", [])
        ]
        suggestions.append(
            WardrobeOutfitSuggestion(
                id=outfit.get("id", ""),
                title=outfit.get("title", "Outfit"),
                items=items,
                estimated_total_value=outfit.get("estimated_total_value"),
                occasion_hint=outfit.get("occasion_hint"),
            )
        )

    return suggestions


@router.get("/health")
async def wardrobe_health():
    """Health check for the wardrobe service."""
    return {"status": "ok", "service": "wardrobe"}
