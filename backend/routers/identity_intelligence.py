"""
CONFIT Backend — Identity Intelligence Router
============================================
Unified identity endpoints for cross-feature access.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from services.identity_intelligence_service import IdentityIntelligenceService, get_identity_intelligence
from utils.auth_deps import require_auth
from services.auth_service import UserProfile

router = APIRouter(prefix="/api/identity", tags=["Identity Intelligence"])


@router.get("/full")
async def get_full_identity(
    user: UserProfile = Depends(require_auth),
    identity: IdentityIntelligenceService = Depends(get_identity_intelligence),
):
    """Retrieve complete user identity for cross-feature personalization."""
    return identity.get_full_identity(user.id)


@router.get("/styling-context")
async def get_styling_context(
    user: UserProfile = Depends(require_auth),
    identity: IdentityIntelligenceService = Depends(get_identity_intelligence),
):
    """Get identity context optimized for styling operations."""
    return identity.get_styling_context(user.id)


@router.get("/tryon-context")
async def get_tryon_context(
    user: UserProfile = Depends(require_auth),
    identity: IdentityIntelligenceService = Depends(get_identity_intelligence),
):
    """Get identity context optimized for virtual try-on."""
    return identity.get_tryon_context(user.id)


@router.get("/commerce-context")
async def get_commerce_context(
    user: UserProfile = Depends(require_auth),
    identity: IdentityIntelligenceService = Depends(get_identity_intelligence),
):
    """Get identity context optimized for commerce operations."""
    return identity.get_commerce_context(user.id)


@router.get("/wardrobe-context")
async def get_wardrobe_context(
    user: UserProfile = Depends(require_auth),
    identity: IdentityIntelligenceService = Depends(get_identity_intelligence),
):
    """Get identity context optimized for wardrobe operations."""
    return identity.get_wardrobe_context(user.id)


@router.get("/social-context")
async def get_social_context(
    user: UserProfile = Depends(require_auth),
    identity: IdentityIntelligenceService = Depends(get_identity_intelligence),
):
    """Get identity context optimized for social features."""
    return identity.get_social_context(user.id)


@router.post("/sync/wardrobe")
async def sync_wardrobe_to_identity(
    user: UserProfile = Depends(require_auth),
    identity: IdentityIntelligenceService = Depends(get_identity_intelligence),
):
    """Sync wardrobe data back to identity profile."""
    return identity.sync_wardrobe_to_identity(user.id)


@router.post("/sync/purchase")
async def sync_purchase_to_identity(
    order_data: Dict[str, Any],
    user: UserProfile = Depends(require_auth),
    identity: IdentityIntelligenceService = Depends(get_identity_intelligence),
):
    """Sync purchase data to identity profile."""
    return identity.sync_purchase_to_identity(user.id, order_data)


@router.get("/gaps")
async def get_identity_gaps(
    user: UserProfile = Depends(require_auth),
    identity: IdentityIntelligenceService = Depends(get_identity_intelligence),
):
    """Identify missing identity data affecting personalization."""
    return identity.get_identity_gaps(user.id)


@router.get("/health")
async def get_identity_health(
    user: UserProfile = Depends(require_auth),
    identity: IdentityIntelligenceService = Depends(get_identity_intelligence),
):
    """Calculate overall identity health for AI readiness."""
    return identity.get_identity_health_score(user.id)
