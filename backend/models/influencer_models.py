"""
CONFIT Backend — Influencer Marketplace Models
=============================================
Pydantic schemas for influencer profiles, outfits, affiliate links, and commissions.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


# ── Type Aliases ────────────────────────────────────────────────────────────────

InfluencerTier = Literal["emerging", "rising", "established", "top_creator"]
InfluencerStatus = Literal["pending", "approved", "suspended", "inactive"]
OutfitStatus = Literal["draft", "published", "archived"]
Visibility = Literal["public", "followers", "private"]
CommissionStatus = Literal["pending", "approved", "paid", "cancelled", "refunded"]
AttributionType = Literal["first_click", "last_click", "linear", "custom"]


# ── Social Links ────────────────────────────────────────────────────────────────

class SocialLinks(BaseModel):
    """Social media links for an influencer."""
    instagram: Optional[str] = None
    tiktok: Optional[str] = None
    youtube: Optional[str] = None
    pinterest: Optional[str] = None
    twitter: Optional[str] = None
    facebook: Optional[str] = None
    website: Optional[str] = None


# ── Influencer Profile Models ──────────────────────────────────────────────────

class InfluencerProfileCreate(BaseModel):
    """Request to create an influencer profile."""
    display_name: str = Field(..., min_length=2, max_length=100)
    bio: Optional[str] = Field(None, max_length=1000)
    avatar_url: Optional[str] = None
    banner_url: Optional[str] = None
    website_url: Optional[str] = None
    social_links: SocialLinks = Field(default_factory=SocialLinks)
    niches: List[str] = Field(default_factory=list)
    style_tags: List[str] = Field(default_factory=list)
    default_commission_rate: Decimal = Field(default=Decimal("0.10"), ge=0, le=1)


class InfluencerProfileUpdate(BaseModel):
    """Request to update an influencer profile."""
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    bio: Optional[str] = Field(None, max_length=1000)
    avatar_url: Optional[str] = None
    banner_url: Optional[str] = None
    website_url: Optional[str] = None
    social_links: Optional[SocialLinks] = None
    niches: Optional[List[str]] = None
    style_tags: Optional[List[str]] = None
    default_commission_rate: Optional[Decimal] = Field(None, ge=0, le=1)


class InfluencerStats(BaseModel):
    """Influencer statistics."""
    followers_count: int = 0
    following_count: int = 0
    total_outfits: int = 0
    total_views: int = 0
    total_engagement: int = 0
    total_earnings: Decimal = Decimal("0.00")
    pending_commissions: Decimal = Decimal("0.00")
    paid_commissions: Decimal = Decimal("0.00")


class InfluencerProfileResponse(BaseModel):
    """Full influencer profile response."""
    id: str
    user_id: str
    display_name: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    banner_url: Optional[str] = None
    website_url: Optional[str] = None
    social_links: SocialLinks = Field(default_factory=SocialLinks)
    tier: InfluencerTier = "emerging"
    status: InfluencerStatus = "pending"
    niches: List[str] = []
    style_tags: List[str] = []
    stats: InfluencerStats
    is_verified: bool = False
    is_featured: bool = False
    created_at: datetime
    updated_at: datetime
    is_following: Optional[bool] = None

    class Config:
        from_attributes = True


class InfluencerListResponse(BaseModel):
    """Simplified influencer for list views."""
    id: str
    display_name: str
    avatar_url: Optional[str] = None
    tier: InfluencerTier
    niches: List[str] = []
    followers_count: int = 0
    total_outfits: int = 0
    is_verified: bool = False
    is_featured: bool = False

    class Config:
        from_attributes = True


# ── Outfit Collection Models ───────────────────────────────────────────────────

class OutfitItem(BaseModel):
    """An item within an outfit collection."""
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    product_image_url: Optional[str] = None
    product_price: Optional[Decimal] = None
    brand: Optional[str] = None
    note: Optional[str] = Field(None, max_length=200)
    position: Optional[int] = None
    affiliate_link_id: Optional[str] = None


class InfluencerOutfitCreate(BaseModel):
    """Request to create an outfit collection."""
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    image_url: str
    thumbnail_url: Optional[str] = None
    items: List[OutfitItem] = Field(default_factory=list)
    occasion: Optional[str] = None
    season: Optional[str] = None
    style_tags: List[str] = Field(default_factory=list)
    budget_range: Optional[Dict[str, Any]] = None
    commission_rate: Decimal = Field(default=Decimal("0.10"), ge=0, le=1)
    visibility: Visibility = "public"


class InfluencerOutfitUpdate(BaseModel):
    """Request to update an outfit collection."""
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    items: Optional[List[OutfitItem]] = None
    occasion: Optional[str] = None
    season: Optional[str] = None
    style_tags: Optional[List[str]] = None
    budget_range: Optional[Dict[str, Any]] = None
    commission_rate: Optional[Decimal] = Field(None, ge=0, le=1)
    visibility: Optional[Visibility] = None
    status: Optional[OutfitStatus] = None


class OutfitStats(BaseModel):
    """Outfit statistics."""
    view_count: int = 0
    save_count: int = 0
    share_count: int = 0
    like_count: int = 0
    purchase_count: int = 0
    total_commission: Decimal = Decimal("0.00")


class InfluencerOutfitResponse(BaseModel):
    """Full outfit collection response."""
    id: str
    influencer_id: str
    influencer: Optional[InfluencerListResponse] = None
    title: str
    description: Optional[str] = None
    image_url: str
    thumbnail_url: Optional[str] = None
    items: List[OutfitItem] = []
    occasion: Optional[str] = None
    season: Optional[str] = None
    style_tags: List[str] = []
    budget_range: Optional[Dict[str, Any]] = None
    commission_rate: Decimal = Decimal("0.10")
    stats: OutfitStats
    status: OutfitStatus = "draft"
    visibility: Visibility = "public"
    is_featured: bool = False
    is_liked: Optional[bool] = False
    is_saved: Optional[bool] = False
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InfluencerOutfitListResponse(BaseModel):
    """Simplified outfit for list views."""
    id: str
    influencer_id: str
    influencer_name: Optional[str] = None
    influencer_avatar: Optional[str] = None
    title: str
    thumbnail_url: Optional[str] = None
    occasion: Optional[str] = None
    style_tags: List[str] = []
    like_count: int = 0
    save_count: int = 0
    is_featured: bool = False
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Affiliate Link Models ──────────────────────────────────────────────────────

class AffiliateLinkCreate(BaseModel):
    """Request to create an affiliate link."""
    product_id: Optional[str] = None
    original_url: str
    commission_rate: Decimal = Field(default=Decimal("0.10"), ge=0, le=1)
    commission_override: bool = False
    attribution_window_days: int = Field(default=30, ge=1, le=90)


class AffiliateLinkUpdate(BaseModel):
    """Request to update an affiliate link."""
    commission_rate: Optional[Decimal] = Field(None, ge=0, le=1)
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class AffiliateLinkStats(BaseModel):
    """Affiliate link statistics."""
    click_count: int = 0
    unique_clicks: int = 0
    conversion_count: int = 0
    total_revenue: Decimal = Decimal("0.00")
    total_commission: Decimal = Decimal("0.00")
    conversion_rate: float = 0.0


class AffiliateLinkResponse(BaseModel):
    """Full affiliate link response."""
    id: str
    influencer_id: str
    product_id: Optional[str] = None
    slug: str
    original_url: str
    tracking_code: str
    short_url: Optional[str] = None
    commission_rate: Decimal
    commission_override: bool = False
    stats: AffiliateLinkStats
    attribution_window_days: int = 30
    is_active: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Commission Models ──────────────────────────────────────────────────────────

class CommissionRecordResponse(BaseModel):
    """Commission record response."""
    id: str
    influencer_id: str
    affiliate_link_id: Optional[str] = None
    order_id: Optional[str] = None
    product_id: Optional[str] = None
    product_name: str
    product_price: Decimal
    quantity: int = 1
    commission_rate: Decimal
    commission_amount: Decimal
    attribution_type: AttributionType = "last_click"
    status: CommissionStatus = "pending"
    approved_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CommissionSummary(BaseModel):
    """Commission earnings summary."""
    total_pending: Decimal = Decimal("0.00")
    total_approved: Decimal = Decimal("0.00")
    total_paid: Decimal = Decimal("0.00")
    total_this_month: Decimal = Decimal("0.00")
    total_this_year: Decimal = Decimal("0.00")
    recent_commissions: List[CommissionRecordResponse] = []


# ── Follow Models ───────────────────────────────────────────────────────────────

class FollowRequest(BaseModel):
    """Request to follow/unfollow an influencer."""
    influencer_id: str


class FollowResponse(BaseModel):
    """Response to follow action."""
    is_following: bool
    followers_count: int
    message: Optional[str] = None


# ── Like/Save Models ────────────────────────────────────────────────────────────

class OutfitLikeRequest(BaseModel):
    """Request to like/unlike an outfit."""
    outfit_id: str


class OutfitSaveRequest(BaseModel):
    """Request to save/unsave an outfit."""
    outfit_id: str
    collection_name: Optional[str] = Field(None, max_length=100)


class OutfitActionResponse(BaseModel):
    """Response to like/save action."""
    success: bool
    like_count: Optional[int] = None
    save_count: Optional[int] = None
    is_liked: Optional[bool] = None
    is_saved: Optional[bool] = None


# ── Product Recommendation Models ──────────────────────────────────────────────

class ProductRecommendationCreate(BaseModel):
    """Request to create a product recommendation."""
    product_id: str
    review_text: Optional[str] = Field(None, max_length=2000)
    rating: Optional[int] = Field(None, ge=1, le=5)
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    affiliate_link_id: Optional[str] = None


class ProductRecommendationUpdate(BaseModel):
    """Request to update a product recommendation."""
    review_text: Optional[str] = Field(None, max_length=2000)
    rating: Optional[int] = Field(None, ge=1, le=5)
    pros: Optional[List[str]] = None
    cons: Optional[List[str]] = None
    is_featured: Optional[bool] = None


class ProductRecommendationResponse(BaseModel):
    """Product recommendation response."""
    id: str
    influencer_id: str
    influencer_name: Optional[str] = None
    influencer_avatar: Optional[str] = None
    product_id: str
    product_name: Optional[str] = None
    product_image_url: Optional[str] = None
    product_price: Optional[Decimal] = None
    review_text: Optional[str] = None
    rating: Optional[int] = None
    pros: List[str] = []
    cons: List[str] = []
    affiliate_link_id: Optional[str] = None
    helpful_count: int = 0
    view_count: int = 0
    is_featured: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


# ── Feed & Discovery Models ────────────────────────────────────────────────────

class InfluencerFeedResponse(BaseModel):
    """Paginated feed of outfits."""
    outfits: List[InfluencerOutfitListResponse]
    has_more: bool
    total_count: Optional[int] = None
    page: int = 1
    page_size: int = 20


class FeaturedInfluencersResponse(BaseModel):
    """Featured influencers for homepage."""
    influencers: List[InfluencerListResponse]
    category: Optional[str] = None


class DiscoverResponse(BaseModel):
    """Discovery page response."""
    featured_outfits: List[InfluencerOutfitListResponse]
    trending_influencers: List[InfluencerListResponse]
    categories: List[Dict[str, Any]]


# ── Click Tracking ─────────────────────────────────────────────────────────────

class AffiliateClickRequest(BaseModel):
    """Request to track an affiliate click."""
    tracking_code: str
    session_id: Optional[str] = None
    referrer: Optional[str] = None


class AffiliateClickResponse(BaseModel):
    """Response after tracking a click."""
    success: bool
    redirect_url: str
    click_id: Optional[str] = None
