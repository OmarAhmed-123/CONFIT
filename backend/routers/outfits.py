"""
CONFIT Backend — Outfit Builder Router
======================================
Endpoints for saving, updating, listing, and sharing outfits
that combine items across brands and from the user's wardrobe.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from controllers.outfit_controller import OutfitController
from models.outfit_models import OutfitCreate, OutfitUpdate, OutfitResponse
from services.auth_service import UserProfile
from services.outfit_service import OutfitService
from utils.auth_deps import require_auth

router = APIRouter(prefix="/api/outfits", tags=["Outfit Builder"])


def get_outfit_service(db: Session = Depends(get_db)) -> OutfitService:
    return OutfitService(db)


def get_outfit_controller(service: OutfitService = Depends(get_outfit_service)) -> OutfitController:
    return OutfitController(service)


@router.get("", response_model=List[OutfitResponse])
async def list_outfits(
    user: UserProfile = Depends(require_auth),
    controller: OutfitController = Depends(get_outfit_controller),
):
    """List all outfits saved by the authenticated user."""
    return await controller.list_outfits(user.id)


@router.post("", response_model=OutfitResponse)
async def create_outfit(
    payload: OutfitCreate,
    user: UserProfile = Depends(require_auth),
    controller: OutfitController = Depends(get_outfit_controller),
):
    """Create a new outfit for the authenticated user."""
    return await controller.create_outfit(user.id, payload)


@router.get("/{outfit_id}", response_model=OutfitResponse)
async def get_outfit(
    outfit_id: str,
    user: UserProfile = Depends(require_auth),
    controller: OutfitController = Depends(get_outfit_controller),
):
    """Get a single outfit by identifier."""
    return await controller.get_outfit(user.id, outfit_id)


@router.patch("/{outfit_id}", response_model=OutfitResponse)
async def update_outfit(
    outfit_id: str,
    payload: OutfitUpdate,
    user: UserProfile = Depends(require_auth),
    controller: OutfitController = Depends(get_outfit_controller),
):
    """Update a saved outfit."""
    return await controller.update_outfit(user.id, outfit_id, payload)


@router.delete("/{outfit_id}")
async def delete_outfit(
    outfit_id: str,
    user: UserProfile = Depends(require_auth),
    controller: OutfitController = Depends(get_outfit_controller),
):
    """Delete a saved outfit."""
    await controller.delete_outfit(user.id, outfit_id)
    return {"success": True, "message": "Outfit deleted"}


@router.get("/shared/{share_slug}", response_model=OutfitResponse)
async def get_shared_outfit(
    share_slug: str,
    controller: OutfitController = Depends(get_outfit_controller),
):
    """
    Public endpoint to retrieve an outfit by its share slug.
    Does not require authentication and does not reveal the owner.
    """
    return await controller.get_shared_outfit(share_slug)

