"""
CONFIT Backend - Wardrobe API Routes
====================================
User wardrobe management and outfit suggestions.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import get_wardrobe_service, get_current_user
from application.services.wardrobe_service import (
    WardrobeService,
    WardrobeItemCreateDTO,
    WardrobeItemUpdateDTO,
    WardrobeItemDTO,
    OutfitCreateDTO,
    OutfitDTO,
    OutfitSuggestionDTO,
)
from core.security.rbac import AuthContext


router = APIRouter(prefix="/wardrobe", tags=["Wardrobe"])


# ─────────────────────────────────────────────────────────────────────────────
# WARDROBE ITEMS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    summary="Get user's wardrobe",
)
async def get_wardrobe(
    category: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    wardrobe_service: WardrobeService = Depends(get_wardrobe_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get user's wardrobe with optional filters."""
    from uuid import UUID
    return await wardrobe_service.get_user_wardrobe(
        user_id=UUID(current_user.user_id),
        category=category,
        is_favorite=is_favorite,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=WardrobeItemDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Add item to wardrobe",
)
async def add_wardrobe_item(
    dto: WardrobeItemCreateDTO,
    wardrobe_service: WardrobeService = Depends(get_wardrobe_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Add item to wardrobe."""
    from uuid import UUID
    item, error = await wardrobe_service.add_item(
        user_id=UUID(current_user.user_id),
        dto=dto,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return item


@router.get(
    "/{item_id}",
    response_model=WardrobeItemDTO,
    summary="Get wardrobe item",
)
async def get_wardrobe_item(
    item_id: str,
    wardrobe_service: WardrobeService = Depends(get_wardrobe_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get wardrobe item by ID."""
    from uuid import UUID
    item = await wardrobe_service.get_item(
        user_id=UUID(current_user.user_id),
        item_id=UUID(item_id),
    )
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return item


@router.patch(
    "/{item_id}",
    response_model=WardrobeItemDTO,
    summary="Update wardrobe item",
)
async def update_wardrobe_item(
    item_id: str,
    dto: WardrobeItemUpdateDTO,
    wardrobe_service: WardrobeService = Depends(get_wardrobe_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Update wardrobe item."""
    from uuid import UUID
    item, error = await wardrobe_service.update_item(
        user_id=UUID(current_user.user_id),
        item_id=UUID(item_id),
        dto=dto,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return item


@router.delete(
    "/{item_id}",
    summary="Delete wardrobe item",
)
async def delete_wardrobe_item(
    item_id: str,
    wardrobe_service: WardrobeService = Depends(get_wardrobe_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Delete item from wardrobe."""
    from uuid import UUID
    success, error = await wardrobe_service.delete_item(
        user_id=UUID(current_user.user_id),
        item_id=UUID(item_id),
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Item deleted"}


@router.post(
    "/{item_id}/wear",
    summary="Record item worn",
)
async def record_item_worn(
    item_id: str,
    wardrobe_service: WardrobeService = Depends(get_wardrobe_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Record that an item was worn."""
    from uuid import UUID
    success, error = await wardrobe_service.record_wear(
        user_id=UUID(current_user.user_id),
        item_id=UUID(item_id),
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Wear recorded"}


@router.post(
    "/{item_id}/favorite",
    summary="Toggle favorite",
)
async def toggle_favorite(
    item_id: str,
    wardrobe_service: WardrobeService = Depends(get_wardrobe_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Toggle favorite status of item."""
    from uuid import UUID
    success, error = await wardrobe_service.toggle_favorite(
        user_id=UUID(current_user.user_id),
        item_id=UUID(item_id),
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Favorite toggled"}


# ─────────────────────────────────────────────────────────────────────────────
# OUTFITS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/outfits",
    summary="Get user's outfits",
)
async def get_outfits(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    wardrobe_service: WardrobeService = Depends(get_wardrobe_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get user's saved outfits."""
    from uuid import UUID
    return await wardrobe_service.get_user_outfits(
        user_id=UUID(current_user.user_id),
        page=page,
        page_size=page_size,
    )


@router.post(
    "/outfits",
    response_model=OutfitDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create outfit",
)
async def create_outfit(
    dto: OutfitCreateDTO,
    wardrobe_service: WardrobeService = Depends(get_wardrobe_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Create outfit from wardrobe items."""
    from uuid import UUID
    outfit, error = await wardrobe_service.create_outfit(
        user_id=UUID(current_user.user_id),
        dto=dto,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return outfit


@router.get(
    "/outfits/{outfit_id}",
    response_model=OutfitDTO,
    summary="Get outfit",
)
async def get_outfit(
    outfit_id: str,
    wardrobe_service: WardrobeService = Depends(get_wardrobe_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get outfit by ID."""
    from uuid import UUID
    outfit = await wardrobe_service.get_outfit(
        user_id=UUID(current_user.user_id),
        outfit_id=UUID(outfit_id),
    )
    
    if not outfit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outfit not found"
        )
    
    return outfit


@router.delete(
    "/outfits/{outfit_id}",
    summary="Delete outfit",
)
async def delete_outfit(
    outfit_id: str,
    wardrobe_service: WardrobeService = Depends(get_wardrobe_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Delete outfit."""
    from uuid import UUID
    success, error = await wardrobe_service.delete_outfit(
        user_id=UUID(current_user.user_id),
        outfit_id=UUID(outfit_id),
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Outfit deleted"}


# ─────────────────────────────────────────────────────────────────────────────
# OUTFIT SUGGESTIONS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/suggestions",
    response_model=List[OutfitSuggestionDTO],
    summary="Get outfit suggestions",
)
async def get_outfit_suggestions(
    occasion: Optional[str] = None,
    season: Optional[str] = None,
    limit: int = Query(5, ge=1, le=20),
    wardrobe_service: WardrobeService = Depends(get_wardrobe_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get AI-powered outfit suggestions."""
    from uuid import UUID
    return await wardrobe_service.suggest_outfits(
        user_id=UUID(current_user.user_id),
        occasion=occasion,
        season=season,
        limit=limit,
    )
