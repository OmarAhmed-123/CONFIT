"""
CONFIT Backend — Outfit Ratings Router
=====================================
API endpoints for outfit rating, like, save, share operations
and trending/popular outfit rankings.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.session import get_db
from services.outfit_rating_service import OutfitRatingService
from services.auth_service import UserProfile
from schemas.outfit_rating_schemas import (
    OutfitRatingCreate,
    OutfitRatingUpdate,
    OutfitRatingResponse,
    OutfitLikeCreate,
    OutfitLikeResponse,
    OutfitLikeToggleResponse,
    OutfitSaveCreate,
    OutfitSaveResponse,
    OutfitShareCreate,
    OutfitShareResponse,
    OutfitPopularityResponse,
    OutfitWithRatingsResponse,
    TrendingOutfitsResponse,
    OutfitRankingFilters,
    UserOutfitEngagementSummary,
)
from utils.auth_deps import require_auth, optional_auth

router = APIRouter(prefix="/api/outfit-ratings", tags=["Outfit Ratings"])


def get_rating_service(db: Session = Depends(get_db)) -> OutfitRatingService:
    return OutfitRatingService(db)


# ── Rating Endpoints ───────────────────────────────────────────────────────────

@router.post("/{outfit_id}/rate", response_model=OutfitRatingResponse)
async def rate_outfit(
    outfit_id: str,
    payload: OutfitRatingCreate,
    user: UserProfile = Depends(require_auth),
    service: OutfitRatingService = Depends(get_rating_service),
):
    """Rate an outfit (1-5 stars). Updates existing rating if present."""
    try:
        return service.rate_outfit(user.id, outfit_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{outfit_id}/rating", response_model=Optional[OutfitRatingResponse])
async def get_user_rating(
    outfit_id: str,
    user: UserProfile = Depends(require_auth),
    service: OutfitRatingService = Depends(get_rating_service),
):
    """Get the current user's rating for an outfit."""
    return service.get_user_rating(user.id, outfit_id)


@router.get("/{outfit_id}/ratings", response_model=List[OutfitRatingResponse])
async def get_outfit_ratings(
    outfit_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: UserProfile = Depends(require_auth),
    service: OutfitRatingService = Depends(get_rating_service),
):
    """Get all ratings for an outfit with pagination."""
    ratings, _ = service.get_outfit_ratings(outfit_id, page, page_size)
    return ratings


@router.delete("/{outfit_id}/rating")
async def delete_rating(
    outfit_id: str,
    user: UserProfile = Depends(require_auth),
    service: OutfitRatingService = Depends(get_rating_service),
):
    """Delete user's rating for an outfit."""
    if not service.delete_rating(user.id, outfit_id):
        raise HTTPException(status_code=404, detail="Rating not found")
    return {"success": True, "message": "Rating deleted"}


# ── Like Endpoints ────────────────────────────────────────────────────────────

@router.post("/{outfit_id}/like", response_model=OutfitLikeToggleResponse)
async def toggle_like(
    outfit_id: str,
    payload: OutfitLikeCreate,
    user: UserProfile = Depends(require_auth),
    service: OutfitRatingService = Depends(get_rating_service),
):
    """Toggle like/dislike for an outfit. Removes existing if same action."""
    try:
        return service.toggle_like(user.id, outfit_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{outfit_id}/like", response_model=Optional[OutfitLikeResponse])
async def get_user_like(
    outfit_id: str,
    user: UserProfile = Depends(require_auth),
    service: OutfitRatingService = Depends(get_rating_service),
):
    """Get the current user's like status for an outfit."""
    return service.get_user_like(user.id, outfit_id)


# ── Save Endpoints ────────────────────────────────────────────────────────────

@router.post("/{outfit_id}/save", response_model=OutfitSaveResponse)
async def save_outfit(
    outfit_id: str,
    payload: OutfitSaveCreate,
    user: UserProfile = Depends(require_auth),
    service: OutfitRatingService = Depends(get_rating_service),
):
    """Save an outfit to user's collection."""
    try:
        return service.save_outfit(user.id, outfit_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{outfit_id}/save")
async def unsave_outfit(
    outfit_id: str,
    user: UserProfile = Depends(require_auth),
    service: OutfitRatingService = Depends(get_rating_service),
):
    """Remove an outfit from user's saved collection."""
    if not service.unsave_outfit(user.id, outfit_id):
        raise HTTPException(status_code=404, detail="Saved outfit not found")
    return {"success": True, "message": "Outfit unsaved"}


@router.get("/saved", response_model=List[OutfitSaveResponse])
async def get_saved_outfits(
    collection_name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: UserProfile = Depends(require_auth),
    service: OutfitRatingService = Depends(get_rating_service),
):
    """Get user's saved outfits with optional collection filter."""
    saves, _ = service.get_user_saved_outfits(user.id, collection_name, page, page_size)
    return saves


# ── Share Endpoints ───────────────────────────────────────────────────────────

@router.post("/{outfit_id}/share", response_model=OutfitShareResponse)
async def record_share(
    outfit_id: str,
    payload: OutfitShareCreate,
    user: UserProfile = Depends(require_auth),
    service: OutfitRatingService = Depends(get_rating_service),
):
    """Record an outfit share event."""
    try:
        return service.record_share(user.id, outfit_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── View Tracking ─────────────────────────────────────────────────────────────

@router.post("/{outfit_id}/view")
async def record_view(
    outfit_id: str,
    service: OutfitRatingService = Depends(get_rating_service),
):
    """Record a view for an outfit (for popularity calculations)."""
    service.record_view(outfit_id)
    return {"success": True}


# ── Popularity & Rankings ─────────────────────────────────────────────────────

@router.get("/{outfit_id}/popularity", response_model=OutfitPopularityResponse)
async def get_outfit_popularity(
    outfit_id: str,
    service: OutfitRatingService = Depends(get_rating_service),
):
    """Get popularity metrics for a specific outfit."""
    return service.get_outfit_popularity(outfit_id)


@router.get("/{outfit_id}/engagement", response_model=UserOutfitEngagementSummary)
async def get_user_engagement(
    outfit_id: str,
    user: UserProfile = Depends(require_auth),
    service: OutfitRatingService = Depends(get_rating_service),
):
    """Get summary of user's engagement with an outfit."""
    return service.get_user_engagement_summary(user.id, outfit_id)


@router.get("/{outfit_id}/details", response_model=OutfitWithRatingsResponse)
async def get_outfit_with_ratings(
    outfit_id: str,
    user: UserProfile = Depends(require_auth),
    service: OutfitRatingService = Depends(get_rating_service),
):
    """Get outfit details with rating info for a user."""
    result = service.get_outfit_with_ratings(user.id, outfit_id)
    if not result:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return result


# ── Trending & Popular ────────────────────────────────────────────────────────

@router.get("/trending", response_model=TrendingOutfitsResponse)
async def get_trending_outfits(
    time_window: str = Query("7d", pattern="^(24h|7d|30d|all)$"),
    min_rating: Optional[float] = Query(None, ge=1.0, le=5.0),
    min_ratings_count: Optional[int] = Query(None, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: OutfitRatingService = Depends(get_rating_service),
):
    """Get trending outfits based on ranking algorithms."""
    filters = OutfitRankingFilters(
        time_window=time_window,
        min_rating=min_rating,
        min_ratings_count=min_ratings_count,
        page=page,
        page_size=page_size,
    )
    return service.get_trending_outfits(filters)


@router.get("/popular", response_model=TrendingOutfitsResponse)
async def get_popular_outfits(
    time_window: str = Query("all", pattern="^(24h|7d|30d|all)$"),
    min_rating: Optional[float] = Query(None, ge=1.0, le=5.0),
    min_ratings_count: Optional[int] = Query(None, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: OutfitRatingService = Depends(get_rating_service),
):
    """Get popular outfits based on overall popularity score."""
    filters = OutfitRankingFilters(
        time_window=time_window,
        min_rating=min_rating,
        min_ratings_count=min_ratings_count,
        page=page,
        page_size=page_size,
    )
    return service.get_popular_outfits(filters)
