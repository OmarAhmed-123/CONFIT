"""
CONFIT Backend — Outfit Rating Schemas
======================================
Pydantic models for outfit rating, like, save, and share operations.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ── Rating Schemas ─────────────────────────────────────────────────────────────

class OutfitRatingCreate(BaseModel):
    """Payload for rating an outfit (1-5 stars)."""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    review: Optional[str] = Field(None, max_length=1000, description="Optional review text")

    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v


class OutfitRatingUpdate(BaseModel):
    """Payload for updating an existing rating."""
    rating: Optional[int] = Field(None, ge=1, le=5)
    review: Optional[str] = Field(None, max_length=1000)


class OutfitRatingResponse(BaseModel):
    """Response model for an outfit rating."""
    id: str
    outfit_id: str
    user_id: str
    rating: int
    review: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Like Schemas ───────────────────────────────────────────────────────────────

class OutfitLikeCreate(BaseModel):
    """Payload for liking/disliking an outfit."""
    is_like: bool = Field(..., description="True for like, False for dislike")


class OutfitLikeResponse(BaseModel):
    """Response model for an outfit like."""
    id: str
    outfit_id: str
    user_id: str
    is_like: bool
    created_at: datetime

    class Config:
        from_attributes = True


class OutfitLikeToggleResponse(BaseModel):
    """Response for like toggle operation."""
    outfit_id: str
    is_liked: Optional[bool] = None
    is_disliked: Optional[bool] = None
    like_count: int
    dislike_count: int


# ── Save Schemas ───────────────────────────────────────────────────────────────

class OutfitSaveCreate(BaseModel):
    """Payload for saving an outfit to collection."""
    collection_name: Optional[str] = Field(None, max_length=100, description="Optional collection name")


class OutfitSaveResponse(BaseModel):
    """Response model for a saved outfit."""
    id: str
    outfit_id: str
    user_id: str
    collection_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Share Schemas ──────────────────────────────────────────────────────────────

class OutfitShareCreate(BaseModel):
    """Payload for tracking an outfit share."""
    platform: Optional[str] = Field(None, max_length=50, description="Platform shared to")


class OutfitShareResponse(BaseModel):
    """Response model for an outfit share."""
    id: str
    outfit_id: str
    user_id: str
    platform: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Popularity Schemas ──────────────────────────────────────────────────────────

class OutfitPopularityResponse(BaseModel):
    """Aggregated popularity metrics for an outfit."""
    outfit_id: str
    total_ratings: int = 0
    avg_rating: float = 0.0
    like_count: int = 0
    dislike_count: int = 0
    save_count: int = 0
    share_count: int = 0
    view_count: int = 0
    trending_score: float = 0.0
    popularity_score: float = 0.0
    style_relevance_score: float = 0.0
    last_activity_at: datetime

    class Config:
        from_attributes = True


# ── Outfit with Rating Info ────────────────────────────────────────────────────

class OutfitWithRatingsResponse(BaseModel):
    """Outfit response with rating and popularity data."""
    id: str
    owner_user_id: str
    title: str
    items: List[dict]
    occasion: Optional[str] = None
    notes: Optional[str] = None
    budget_limit: Optional[float] = None
    total_price: Optional[float] = None
    currency: str = "USD"
    created_at: datetime
    updated_at: datetime
    share_slug: Optional[str] = None
    # Rating data
    popularity: Optional[OutfitPopularityResponse] = None
    user_rating: Optional[int] = None
    user_liked: Optional[bool] = None
    user_saved: bool = False

    class Config:
        from_attributes = True


# ── Trending & Rankings ────────────────────────────────────────────────────────

class TrendingOutfitItem(BaseModel):
    """Single item in trending outfits list."""
    outfit_id: str
    title: str
    items: List[dict]
    total_price: Optional[float] = None
    currency: str = "USD"
    avg_rating: float = 0.0
    total_ratings: int = 0
    like_count: int = 0
    trending_score: float = 0.0
    popularity_score: float = 0.0
    rank: int


class TrendingOutfitsResponse(BaseModel):
    """Response for trending outfits endpoint."""
    outfits: List[TrendingOutfitItem]
    time_window: str = "7d"
    total_count: int
    page: int = 1
    page_size: int = 20


class OutfitRankingFilters(BaseModel):
    """Filters for outfit rankings."""
    time_window: Literal["24h", "7d", "30d", "all"] = Field("7d", description="Time window for trending calculation")
    category: Optional[str] = None
    occasion: Optional[str] = None
    min_rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    min_ratings_count: Optional[int] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


# ── User Engagement Summary ────────────────────────────────────────────────────

class UserOutfitEngagementSummary(BaseModel):
    """Summary of user's engagement with an outfit."""
    outfit_id: str
    has_rated: bool = False
    user_rating: Optional[int] = None
    has_liked: bool = False
    is_like: Optional[bool] = None
    has_saved: bool = False
    collection_name: Optional[str] = None
    has_shared: bool = False
