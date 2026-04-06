"""
CONFIT Backend — Influencer Marketplace Router
==============================================
API endpoints for influencer profiles, outfit collections, affiliate links, and commissions.
"""

import uuid
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from database.session import get_db
from database.models import (
    Influencer,
    InfluencerOutfit,
    AffiliateLink,
    CommissionRecord,
    InfluencerFollower,
    AffiliateClick,
    InfluencerOutfitLike,
    InfluencerOutfitSave,
    InfluencerRecommendation,
    Product,
    User,
)
from models.influencer_models import (
    InfluencerProfileCreate,
    InfluencerProfileUpdate,
    InfluencerProfileResponse,
    InfluencerListResponse,
    InfluencerStats,
    SocialLinks,
    InfluencerOutfitCreate,
    InfluencerOutfitUpdate,
    InfluencerOutfitResponse,
    InfluencerOutfitListResponse,
    OutfitItem,
    OutfitStats,
    AffiliateLinkCreate,
    AffiliateLinkUpdate,
    AffiliateLinkResponse,
    AffiliateLinkStats,
    CommissionRecordResponse,
    CommissionSummary,
    FollowRequest,
    FollowResponse,
    OutfitLikeRequest,
    OutfitSaveRequest,
    OutfitActionResponse,
    ProductRecommendationCreate,
    ProductRecommendationUpdate,
    ProductRecommendationResponse,
    InfluencerFeedResponse,
    FeaturedInfluencersResponse,
    DiscoverResponse,
    AffiliateClickRequest,
    AffiliateClickResponse,
)
from utils.auth_deps import require_auth, optional_auth
from services.auth_service import UserProfile

router = APIRouter(prefix="/api/influencers", tags=["influencer-marketplace"])


# ── Helper Functions ────────────────────────────────────────────────────────────

def _generate_tracking_code() -> str:
    """Generate a unique tracking code for affiliate links."""
    return secrets.token_urlsafe(8).upper()


def _generate_slug(product_id: str, influencer_id: str) -> str:
    """Generate a unique slug for affiliate links."""
    short_product = product_id[:8] if product_id else "prod"
    short_influencer = influencer_id[:8]
    random_suffix = secrets.token_hex(3)
    return f"{short_influencer}-{short_product}-{random_suffix}"


def _influencer_to_response(inf: Influencer, is_following: bool = None) -> InfluencerProfileResponse:
    """Convert Influencer ORM to response model."""
    social_links = inf.social_links or {}
    return InfluencerProfileResponse(
        id=str(inf.id),
        user_id=str(inf.user_id),
        display_name=inf.display_name,
        bio=inf.bio,
        avatar_url=inf.avatar_url,
        banner_url=inf.banner_url,
        website_url=inf.website_url,
        social_links=SocialLinks(**social_links),
        tier=inf.tier,
        status=inf.status,
        niches=inf.niches or [],
        style_tags=inf.style_tags or [],
        stats=InfluencerStats(
            followers_count=inf.followers_count,
            following_count=inf.following_count,
            total_outfits=inf.total_outfits,
            total_views=int(inf.total_views or 0),
            total_engagement=int(inf.total_engagement or 0),
            total_earnings=inf.total_earnings or Decimal("0.00"),
            pending_commissions=inf.pending_commissions or Decimal("0.00"),
            paid_commissions=inf.paid_commissions or Decimal("0.00"),
        ),
        is_verified=inf.is_verified,
        is_featured=inf.is_featured,
        created_at=inf.created_at,
        updated_at=inf.updated_at,
        is_following=is_following,
    )


def _outfit_to_response(outfit: InfluencerOutfit, is_liked: bool = False, is_saved: bool = False) -> InfluencerOutfitResponse:
    """Convert InfluencerOutfit ORM to response model."""
    items = [OutfitItem(**item) for item in (outfit.items or [])]
    return InfluencerOutfitResponse(
        id=str(outfit.id),
        influencer_id=str(outfit.influencer_id),
        title=outfit.title,
        description=outfit.description,
        image_url=outfit.image_url,
        thumbnail_url=outfit.thumbnail_url,
        items=items,
        occasion=outfit.occasion,
        season=outfit.season,
        style_tags=outfit.style_tags or [],
        budget_range=outfit.budget_range,
        commission_rate=outfit.commission_rate or Decimal("0.10"),
        stats=OutfitStats(
            view_count=int(outfit.view_count or 0),
            save_count=outfit.save_count,
            share_count=outfit.share_count,
            like_count=outfit.like_count,
            purchase_count=outfit.purchase_count,
            total_commission=outfit.total_commission or Decimal("0.00"),
        ),
        status=outfit.status,
        visibility=outfit.visibility,
        is_featured=outfit.is_featured,
        is_liked=is_liked,
        is_saved=is_saved,
        published_at=outfit.published_at,
        created_at=outfit.created_at,
        updated_at=outfit.updated_at,
    )


# ── Influencer Profile Endpoints ────────────────────────────────────────────────

@router.post("/profile", response_model=InfluencerProfileResponse)
async def create_influencer_profile(
    payload: InfluencerProfileCreate,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Create an influencer profile for the authenticated user."""
    # Check if profile already exists
    existing = db.query(Influencer).filter(Influencer.user_id == user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Influencer profile already exists")

    influencer = Influencer(
        id=uuid.uuid4(),
        user_id=user.id,
        display_name=payload.display_name,
        bio=payload.bio,
        avatar_url=payload.avatar_url,
        banner_url=payload.banner_url,
        website_url=payload.website_url,
        social_links=payload.social_links.model_dump(),
        niches=payload.niches,
        style_tags=payload.style_tags,
        default_commission_rate=payload.default_commission_rate,
        status="pending",  # Requires approval
        tier="emerging",
    )
    db.add(influencer)
    db.commit()
    db.refresh(influencer)
    return _influencer_to_response(influencer)


@router.get("/profile", response_model=InfluencerProfileResponse)
async def get_my_influencer_profile(
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Get the authenticated user's influencer profile."""
    influencer = db.query(Influencer).filter(Influencer.user_id == user.id).first()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")
    return _influencer_to_response(influencer)


@router.patch("/profile", response_model=InfluencerProfileResponse)
async def update_influencer_profile(
    payload: InfluencerProfileUpdate,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Update the authenticated user's influencer profile."""
    influencer = db.query(Influencer).filter(Influencer.user_id == user.id).first()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "social_links" in update_data and update_data["social_links"]:
        influencer.social_links = update_data["social_links"].model_dump()
        del update_data["social_links"]

    for key, value in update_data.items():
        setattr(influencer, key, value)

    db.commit()
    db.refresh(influencer)
    return _influencer_to_response(influencer)


@router.get("/{influencer_id}", response_model=InfluencerProfileResponse)
async def get_influencer_profile(
    influencer_id: str,
    db: Session = Depends(get_db),
    user: Optional[UserProfile] = Depends(optional_auth),
):
    """Get a public influencer profile by ID."""
    influencer = db.query(Influencer).filter(Influencer.id == influencer_id).first()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer not found")

    if influencer.status != "approved" and (not user or str(influencer.user_id) != user.id):
        raise HTTPException(status_code=404, detail="Influencer not found")

    # Check if current user is following
    is_following = None
    if user:
        follow = db.query(InfluencerFollower).filter(
            InfluencerFollower.influencer_id == influencer.id,
            InfluencerFollower.follower_user_id == user.id,
        ).first()
        is_following = follow is not None

    return _influencer_to_response(influencer, is_following)


@router.get("", response_model=List[InfluencerListResponse])
async def list_influencers(
    tier: Optional[str] = Query(None),
    niche: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    featured: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List approved influencers with optional filters."""
    query = db.query(Influencer).filter(Influencer.status == "approved")

    if tier:
        query = query.filter(Influencer.tier == tier)
    if niche:
        query = query.filter(Influencer.niches.contains([niche]))
    if featured is not None:
        query = query.filter(Influencer.is_featured == featured)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Influencer.display_name.ilike(search_term),
                Influencer.bio.ilike(search_term),
            )
        )

    influencers = query.order_by(
        Influencer.is_featured.desc(),
        Influencer.followers_count.desc(),
    ).offset(offset).limit(limit).all()

    return [
        InfluencerListResponse(
            id=str(inf.id),
            display_name=inf.display_name,
            avatar_url=inf.avatar_url,
            tier=inf.tier,
            niches=inf.niches or [],
            followers_count=inf.followers_count,
            total_outfits=inf.total_outfits,
            is_verified=inf.is_verified,
            is_featured=inf.is_featured,
        )
        for inf in influencers
    ]


# ── Outfit Collection Endpoints ─────────────────────────────────────────────────

@router.post("/outfits", response_model=InfluencerOutfitResponse)
async def create_outfit(
    payload: InfluencerOutfitCreate,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Create a new outfit collection."""
    influencer = db.query(Influencer).filter(Influencer.user_id == user.id).first()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")

    outfit = InfluencerOutfit(
        id=uuid.uuid4(),
        influencer_id=influencer.id,
        title=payload.title,
        description=payload.description,
        image_url=payload.image_url,
        thumbnail_url=payload.thumbnail_url,
        items=[item.model_dump() for item in payload.items],
        occasion=payload.occasion,
        season=payload.season,
        style_tags=payload.style_tags,
        budget_range=payload.budget_range,
        commission_rate=payload.commission_rate,
        visibility=payload.visibility,
        status="draft",
    )
    db.add(outfit)
    db.commit()
    db.refresh(outfit)
    return _outfit_to_response(outfit)


@router.post("/outfits/{outfit_id}/publish", response_model=InfluencerOutfitResponse)
async def publish_outfit(
    outfit_id: str,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Publish a draft outfit."""
    influencer = db.query(Influencer).filter(Influencer.user_id == user.id).first()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")

    outfit = db.query(InfluencerOutfit).filter(
        InfluencerOutfit.id == outfit_id,
        InfluencerOutfit.influencer_id == influencer.id,
    ).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    if outfit.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft outfits can be published")

    outfit.status = "published"
    outfit.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(outfit)
    return _outfit_to_response(outfit)


@router.get("/outfits", response_model=List[InfluencerOutfitListResponse])
async def list_my_outfits(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """List the authenticated influencer's outfits."""
    influencer = db.query(Influencer).filter(Influencer.user_id == user.id).first()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")

    query = db.query(InfluencerOutfit).filter(InfluencerOutfit.influencer_id == influencer.id)
    if status:
        query = query.filter(InfluencerOutfit.status == status)

    outfits = query.order_by(InfluencerOutfit.created_at.desc()).offset(offset).limit(limit).all()

    return [
        InfluencerOutfitListResponse(
            id=str(o.id),
            influencer_id=str(o.influencer_id),
            influencer_name=influencer.display_name,
            influencer_avatar=influencer.avatar_url,
            title=o.title,
            thumbnail_url=o.thumbnail_url or o.image_url,
            occasion=o.occasion,
            style_tags=o.style_tags or [],
            like_count=o.like_count,
            save_count=o.save_count,
            is_featured=o.is_featured,
            published_at=o.published_at,
        )
        for o in outfits
    ]


@router.get("/outfits/{outfit_id}", response_model=InfluencerOutfitResponse)
async def get_outfit(
    outfit_id: str,
    db: Session = Depends(get_db),
    user: Optional[UserProfile] = Depends(optional_auth),
):
    """Get an outfit collection by ID."""
    outfit = db.query(InfluencerOutfit).filter(InfluencerOutfit.id == outfit_id).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    # Check visibility
    if outfit.visibility == "private":
        if not user:
            raise HTTPException(status_code=404, detail="Outfit not found")
        influencer = db.query(Influencer).filter(Influencer.id == outfit.influencer_id).first()
        if str(influencer.user_id) != user.id:
            raise HTTPException(status_code=404, detail="Outfit not found")

    # Increment view count
    outfit.view_count = (outfit.view_count or 0) + 1
    db.commit()

    # Check if liked/saved
    is_liked = False
    is_saved = False
    if user:
        like = db.query(InfluencerOutfitLike).filter(
            InfluencerOutfitLike.outfit_id == outfit.id,
            InfluencerOutfitLike.user_id == user.id,
        ).first()
        is_liked = like is not None

        save = db.query(InfluencerOutfitSave).filter(
            InfluencerOutfitSave.outfit_id == outfit.id,
            InfluencerOutfitSave.user_id == user.id,
        ).first()
        is_saved = save is not None

    return _outfit_to_response(outfit, is_liked, is_saved)


@router.patch("/outfits/{outfit_id}", response_model=InfluencerOutfitResponse)
async def update_outfit(
    outfit_id: str,
    payload: InfluencerOutfitUpdate,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Update an outfit collection."""
    influencer = db.query(Influencer).filter(Influencer.user_id == user.id).first()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")

    outfit = db.query(InfluencerOutfit).filter(
        InfluencerOutfit.id == outfit_id,
        InfluencerOutfit.influencer_id == influencer.id,
    ).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "items" in update_data and update_data["items"]:
        update_data["items"] = [item.model_dump() for item in update_data["items"]]

    for key, value in update_data.items():
        setattr(outfit, key, value)

    db.commit()
    db.refresh(outfit)
    return _outfit_to_response(outfit)


@router.delete("/outfits/{outfit_id}")
async def delete_outfit(
    outfit_id: str,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Delete an outfit collection."""
    influencer = db.query(Influencer).filter(Influencer.user_id == user.id).first()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")

    outfit = db.query(InfluencerOutfit).filter(
        InfluencerOutfit.id == outfit_id,
        InfluencerOutfit.influencer_id == influencer.id,
    ).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    db.delete(outfit)
    db.commit()
    return {"success": True, "message": "Outfit deleted"}


# ── Feed & Discovery ────────────────────────────────────────────────────────────

@router.get("/feed/outfits", response_model=InfluencerFeedResponse)
async def get_outfit_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    occasion: Optional[str] = Query(None),
    season: Optional[str] = Query(None),
    style: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: Optional[UserProfile] = Depends(optional_auth),
):
    """Get a paginated feed of published outfits."""
    query = db.query(InfluencerOutfit).join(Influencer).filter(
        InfluencerOutfit.status == "published",
        InfluencerOutfit.visibility == "public",
        Influencer.status == "approved",
    )

    if occasion:
        query = query.filter(InfluencerOutfit.occasion == occasion)
    if season:
        query = query.filter(InfluencerOutfit.season == season)
    if style:
        query = query.filter(InfluencerOutfit.style_tags.contains([style]))

    # Get total count
    total_count = query.count()

    # Get paginated results
    offset = (page - 1) * page_size
    outfits = query.order_by(
        InfluencerOutfit.is_featured.desc(),
        InfluencerOutfit.published_at.desc(),
    ).offset(offset).limit(page_size).all()

    # Check likes/saves for current user
    liked_ids = set()
    saved_ids = set()
    if user:
        outfit_ids = [o.id for o in outfits]
        likes = db.query(InfluencerOutfitLike).filter(
            InfluencerOutfitLike.user_id == user.id,
            InfluencerOutfitLike.outfit_id.in_(outfit_ids),
        ).all()
        liked_ids = {l.outfit_id for l in likes}

        saves = db.query(InfluencerOutfitSave).filter(
            InfluencerOutfitSave.user_id == user.id,
            InfluencerOutfitSave.outfit_id.in_(outfit_ids),
        ).all()
        saved_ids = {s.outfit_id for s in saves}

    outfit_list = [
        InfluencerOutfitListResponse(
            id=str(o.id),
            influencer_id=str(o.influencer_id),
            influencer_name=o.influencer.display_name if o.influencer else None,
            influencer_avatar=o.influencer.avatar_url if o.influencer else None,
            title=o.title,
            thumbnail_url=o.thumbnail_url or o.image_url,
            occasion=o.occasion,
            style_tags=o.style_tags or [],
            like_count=o.like_count,
            save_count=o.save_count,
            is_featured=o.is_featured,
            published_at=o.published_at,
        )
        for o in outfits
    ]

    return InfluencerFeedResponse(
        outfits=outfit_list,
        has_more=(offset + page_size) < total_count,
        total_count=total_count,
        page=page,
        page_size=page_size,
    )


@router.get("/discover", response_model=DiscoverResponse)
async def get_discover_page(
    db: Session = Depends(get_db),
):
    """Get discovery page with featured outfits and trending influencers."""
    # Featured outfits
    featured_outfits = db.query(InfluencerOutfit).join(Influencer).filter(
        InfluencerOutfit.status == "published",
        InfluencerOutfit.visibility == "public",
        InfluencerOutfit.is_featured == True,
        Influencer.status == "approved",
    ).order_by(InfluencerOutfit.published_at.desc()).limit(10).all()

    # Trending influencers
    trending_influencers = db.query(Influencer).filter(
        Influencer.status == "approved",
        Influencer.is_featured == True,
    ).order_by(Influencer.followers_count.desc()).limit(10).all()

    # Categories
    categories = [
        {"id": "streetwear", "name": "Streetwear", "icon": "🏙️"},
        {"id": "minimalist", "name": "Minimalist", "icon": "✨"},
        {"id": "sustainable", "name": "Sustainable", "icon": "🌿"},
        {"id": "luxury", "name": "Luxury", "icon": "💎"},
        {"id": "casual", "name": "Casual", "icon": "👕"},
        {"id": "formal", "name": "Formal", "icon": "👔"},
    ]

    return DiscoverResponse(
        featured_outfits=[
            InfluencerOutfitListResponse(
                id=str(o.id),
                influencer_id=str(o.influencer_id),
                influencer_name=o.influencer.display_name if o.influencer else None,
                influencer_avatar=o.influencer.avatar_url if o.influencer else None,
                title=o.title,
                thumbnail_url=o.thumbnail_url or o.image_url,
                occasion=o.occasion,
                style_tags=o.style_tags or [],
                like_count=o.like_count,
                save_count=o.save_count,
                is_featured=o.is_featured,
                published_at=o.published_at,
            )
            for o in featured_outfits
        ],
        trending_influencers=[
            InfluencerListResponse(
                id=str(inf.id),
                display_name=inf.display_name,
                avatar_url=inf.avatar_url,
                tier=inf.tier,
                niches=inf.niches or [],
                followers_count=inf.followers_count,
                total_outfits=inf.total_outfits,
                is_verified=inf.is_verified,
                is_featured=inf.is_featured,
            )
            for inf in trending_influencers
        ],
        categories=categories,
    )


@router.get("/featured", response_model=FeaturedInfluencersResponse)
async def get_featured_influencers(
    category: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get featured influencers, optionally filtered by category."""
    query = db.query(Influencer).filter(
        Influencer.status == "approved",
        Influencer.is_featured == True,
    )

    if category:
        query = query.filter(Influencer.niches.contains([category]))

    influencers = query.order_by(Influencer.followers_count.desc()).limit(limit).all()

    return FeaturedInfluencersResponse(
        influencers=[
            InfluencerListResponse(
                id=str(inf.id),
                display_name=inf.display_name,
                avatar_url=inf.avatar_url,
                tier=inf.tier,
                niches=inf.niches or [],
                followers_count=inf.followers_count,
                total_outfits=inf.total_outfits,
                is_verified=inf.is_verified,
                is_featured=inf.is_featured,
            )
            for inf in influencers
        ],
        category=category,
    )


# ── Follow Endpoints ────────────────────────────────────────────────────────────

@router.post("/follow", response_model=FollowResponse)
async def follow_influencer(
    payload: FollowRequest,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Follow an influencer."""
    influencer = db.query(Influencer).filter(Influencer.id == payload.influencer_id).first()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer not found")

    if str(influencer.user_id) == user.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    # Check if already following
    existing = db.query(InfluencerFollower).filter(
        InfluencerFollower.influencer_id == influencer.id,
        InfluencerFollower.follower_user_id == user.id,
    ).first()

    if existing:
        return FollowResponse(
            is_following=True,
            followers_count=influencer.followers_count,
            message="Already following",
        )

    follow = InfluencerFollower(
        id=uuid.uuid4(),
        influencer_id=influencer.id,
        follower_user_id=user.id,
    )
    db.add(follow)
    db.commit()

    return FollowResponse(
        is_following=True,
        followers_count=influencer.followers_count,
        message="Successfully followed",
    )


@router.delete("/follow/{influencer_id}", response_model=FollowResponse)
async def unfollow_influencer(
    influencer_id: str,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Unfollow an influencer."""
    follow = db.query(InfluencerFollower).filter(
        InfluencerFollower.influencer_id == influencer_id,
        InfluencerFollower.follower_user_id == user.id,
    ).first()

    if not follow:
        influencer = db.query(Influencer).filter(Influencer.id == influencer_id).first()
        return FollowResponse(
            is_following=False,
            followers_count=influencer.followers_count if influencer else 0,
            message="Not following",
        )

    influencer_id_uuid = follow.influencer_id
    db.delete(follow)
    db.commit()

    # Get updated count
    influencer = db.query(Influencer).filter(Influencer.id == influencer_id_uuid).first()

    return FollowResponse(
        is_following=False,
        followers_count=influencer.followers_count if influencer else 0,
        message="Successfully unfollowed",
    )


# ── Like & Save Endpoints ───────────────────────────────────────────────────────

@router.post("/outfits/{outfit_id}/like", response_model=OutfitActionResponse)
async def like_outfit(
    outfit_id: str,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Like or unlike an outfit (toggle)."""
    outfit = db.query(InfluencerOutfit).filter(InfluencerOutfit.id == outfit_id).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    existing = db.query(InfluencerOutfitLike).filter(
        InfluencerOutfitLike.outfit_id == outfit.id,
        InfluencerOutfitLike.user_id == user.id,
    ).first()

    if existing:
        # Unlike
        db.delete(existing)
        db.commit()
        db.refresh(outfit)
        return OutfitActionResponse(
            success=True,
            like_count=outfit.like_count,
            is_liked=False,
        )
    else:
        # Like
        like = InfluencerOutfitLike(
            id=uuid.uuid4(),
            outfit_id=outfit.id,
            user_id=user.id,
        )
        db.add(like)
        db.commit()
        db.refresh(outfit)
        return OutfitActionResponse(
            success=True,
            like_count=outfit.like_count,
            is_liked=True,
        )


@router.post("/outfits/{outfit_id}/save", response_model=OutfitActionResponse)
async def save_outfit(
    outfit_id: str,
    payload: OutfitSaveRequest = None,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Save or unsave an outfit (toggle)."""
    outfit = db.query(InfluencerOutfit).filter(InfluencerOutfit.id == outfit_id).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    existing = db.query(InfluencerOutfitSave).filter(
        InfluencerOutfitSave.outfit_id == outfit.id,
        InfluencerOutfitSave.user_id == user.id,
    ).first()

    collection_name = payload.collection_name if payload else "Saved"

    if existing:
        # Unsave
        db.delete(existing)
        db.commit()
        db.refresh(outfit)
        return OutfitActionResponse(
            success=True,
            save_count=outfit.save_count,
            is_saved=False,
        )
    else:
        # Save
        save = InfluencerOutfitSave(
            id=uuid.uuid4(),
            outfit_id=outfit.id,
            user_id=user.id,
            collection_name=collection_name,
        )
        db.add(save)
        db.commit()
        db.refresh(outfit)
        return OutfitActionResponse(
            success=True,
            save_count=outfit.save_count,
            is_saved=True,
        )


# ── Affiliate Link Endpoints ────────────────────────────────────────────────────

@router.post("/affiliate-links", response_model=AffiliateLinkResponse)
async def create_affiliate_link(
    payload: AffiliateLinkCreate,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Create an affiliate link for a product."""
    influencer = db.query(Influencer).filter(Influencer.user_id == user.id).first()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")

    tracking_code = _generate_tracking_code()
    slug = _generate_slug(str(payload.product_id) if payload.product_id else "url", str(influencer.id))

    link = AffiliateLink(
        id=uuid.uuid4(),
        influencer_id=influencer.id,
        product_id=payload.product_id,
        original_url=payload.original_url,
        slug=slug,
        tracking_code=tracking_code,
        commission_rate=payload.commission_rate,
        commission_override=payload.commission_override,
        attribution_window_days=payload.attribution_window_days,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    return AffiliateLinkResponse(
        id=str(link.id),
        influencer_id=str(link.influencer_id),
        product_id=str(link.product_id) if link.product_id else None,
        slug=link.slug,
        original_url=link.original_url,
        tracking_code=link.tracking_code,
        short_url=f"/go/{link.slug}",
        commission_rate=link.commission_rate,
        commission_override=link.commission_override,
        stats=AffiliateLinkStats(
            click_count=int(link.click_count or 0),
            unique_clicks=int(link.unique_clicks or 0),
            conversion_count=link.conversion_count,
            total_revenue=link.total_revenue or Decimal("0.00"),
            total_commission=link.total_commission or Decimal("0.00"),
            conversion_rate=0.0,
        ),
        attribution_window_days=link.attribution_window_days,
        is_active=link.is_active,
        expires_at=link.expires_at,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


@router.get("/affiliate-links", response_model=List[AffiliateLinkResponse])
async def list_affiliate_links(
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """List the authenticated influencer's affiliate links."""
    influencer = db.query(Influencer).filter(Influencer.user_id == user.id).first()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")

    query = db.query(AffiliateLink).filter(AffiliateLink.influencer_id == influencer.id)
    if is_active is not None:
        query = query.filter(AffiliateLink.is_active == is_active)

    links = query.order_by(AffiliateLink.created_at.desc()).offset(offset).limit(limit).all()

    return [
        AffiliateLinkResponse(
            id=str(link.id),
            influencer_id=str(link.influencer_id),
            product_id=str(link.product_id) if link.product_id else None,
            slug=link.slug,
            original_url=link.original_url,
            tracking_code=link.tracking_code,
            short_url=f"/go/{link.slug}",
            commission_rate=link.commission_rate,
            commission_override=link.commission_override,
            stats=AffiliateLinkStats(
                click_count=int(link.click_count or 0),
                unique_clicks=int(link.unique_clicks or 0),
                conversion_count=link.conversion_count,
                total_revenue=link.total_revenue or Decimal("0.00"),
                total_commission=link.total_commission or Decimal("0.00"),
                conversion_rate=0.0,
            ),
            attribution_window_days=link.attribution_window_days,
            is_active=link.is_active,
            expires_at=link.expires_at,
            created_at=link.created_at,
            updated_at=link.updated_at,
        )
        for link in links
    ]


@router.post("/track-click", response_model=AffiliateClickResponse)
async def track_affiliate_click(
    payload: AffiliateClickRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: Optional[UserProfile] = Depends(optional_auth),
):
    """Track an affiliate link click and redirect."""
    link = db.query(AffiliateLink).filter(
        AffiliateLink.tracking_code == payload.tracking_code,
        AffiliateLink.is_active == True,
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="Affiliate link not found")

    # Create click record
    click = AffiliateClick(
        id=uuid.uuid4(),
        affiliate_link_id=link.id,
        user_id=user.id if user else None,
        session_id=payload.session_id,
        referrer=payload.referrer,
    )
    db.add(click)

    # Update link stats
    link.click_count = (link.click_count or 0) + 1
    db.commit()

    return AffiliateClickResponse(
        success=True,
        redirect_url=link.original_url,
        click_id=str(click.id),
    )


# ── Commission Endpoints ────────────────────────────────────────────────────────

@router.get("/commissions", response_model=CommissionSummary)
async def get_commission_summary(
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Get commission earnings summary for the authenticated influencer."""
    influencer = db.query(Influencer).filter(Influencer.user_id == user.id).first()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")

    # Calculate totals
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    total_pending = db.query(func.sum(CommissionRecord.commission_amount)).filter(
        CommissionRecord.influencer_id == influencer.id,
        CommissionRecord.status == "pending",
    ).scalar() or Decimal("0.00")

    total_approved = db.query(func.sum(CommissionRecord.commission_amount)).filter(
        CommissionRecord.influencer_id == influencer.id,
        CommissionRecord.status == "approved",
    ).scalar() or Decimal("0.00")

    total_paid = db.query(func.sum(CommissionRecord.commission_amount)).filter(
        CommissionRecord.influencer_id == influencer.id,
        CommissionRecord.status == "paid",
    ).scalar() or Decimal("0.00")

    total_this_month = db.query(func.sum(CommissionRecord.commission_amount)).filter(
        CommissionRecord.influencer_id == influencer.id,
        CommissionRecord.created_at >= month_start,
    ).scalar() or Decimal("0.00")

    total_this_year = db.query(func.sum(CommissionRecord.commission_amount)).filter(
        CommissionRecord.influencer_id == influencer.id,
        CommissionRecord.created_at >= year_start,
    ).scalar() or Decimal("0.00")

    # Recent commissions
    recent = db.query(CommissionRecord).filter(
        CommissionRecord.influencer_id == influencer.id,
    ).order_by(CommissionRecord.created_at.desc()).limit(10).all()

    return CommissionSummary(
        total_pending=total_pending,
        total_approved=total_approved,
        total_paid=total_paid,
        total_this_month=total_this_month,
        total_this_year=total_this_year,
        recent_commissions=[
            CommissionRecordResponse(
                id=str(c.id),
                influencer_id=str(c.influencer_id),
                affiliate_link_id=str(c.affiliate_link_id) if c.affiliate_link_id else None,
                order_id=c.order_id,
                product_id=str(c.product_id) if c.product_id else None,
                product_name=c.product_name,
                product_price=c.product_price,
                quantity=c.quantity,
                commission_rate=c.commission_rate,
                commission_amount=c.commission_amount,
                attribution_type=c.attribution_type,
                status=c.status,
                approved_at=c.approved_at,
                paid_at=c.paid_at,
                created_at=c.created_at,
            )
            for c in recent
        ],
    )


# ── Product Recommendations ────────────────────────────────────────────────────

@router.post("/recommendations", response_model=ProductRecommendationResponse)
async def create_recommendation(
    payload: ProductRecommendationCreate,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Create a product recommendation."""
    influencer = db.query(Influencer).filter(Influencer.user_id == user.id).first()
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer profile not found")

    # Check if product exists
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check for existing recommendation
    existing = db.query(InfluencerRecommendation).filter(
        InfluencerRecommendation.influencer_id == influencer.id,
        InfluencerRecommendation.product_id == payload.product_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Product already recommended")

    recommendation = InfluencerRecommendation(
        id=uuid.uuid4(),
        influencer_id=influencer.id,
        product_id=payload.product_id,
        review_text=payload.review_text,
        rating=payload.rating,
        pros=payload.pros,
        cons=payload.cons,
        affiliate_link_id=payload.affiliate_link_id,
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)

    return ProductRecommendationResponse(
        id=str(recommendation.id),
        influencer_id=str(recommendation.influencer_id),
        influencer_name=influencer.display_name,
        influencer_avatar=influencer.avatar_url,
        product_id=str(recommendation.product_id),
        product_name=product.name,
        product_image_url=product.image_url,
        product_price=product.price,
        review_text=recommendation.review_text,
        rating=recommendation.rating,
        pros=recommendation.pros or [],
        cons=recommendation.cons or [],
        affiliate_link_id=str(recommendation.affiliate_link_id) if recommendation.affiliate_link_id else None,
        helpful_count=recommendation.helpful_count,
        view_count=int(recommendation.view_count or 0),
        is_featured=recommendation.is_featured,
        created_at=recommendation.created_at,
    )


@router.get("/{influencer_id}/recommendations", response_model=List[ProductRecommendationResponse])
async def get_influencer_recommendations(
    influencer_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get product recommendations by an influencer."""
    recommendations = db.query(InfluencerRecommendation).filter(
        InfluencerRecommendation.influencer_id == influencer_id,
        InfluencerRecommendation.status == "active",
    ).order_by(
        InfluencerRecommendation.is_featured.desc(),
        InfluencerRecommendation.created_at.desc(),
    ).limit(limit).all()

    result = []
    for rec in recommendations:
        product = rec.product
        influencer = rec.influencer
        result.append(ProductRecommendationResponse(
            id=str(rec.id),
            influencer_id=str(rec.influencer_id),
            influencer_name=influencer.display_name if influencer else None,
            influencer_avatar=influencer.avatar_url if influencer else None,
            product_id=str(rec.product_id),
            product_name=product.name if product else None,
            product_image_url=product.image_url if product else None,
            product_price=product.price if product else None,
            review_text=rec.review_text,
            rating=rec.rating,
            pros=rec.pros or [],
            cons=rec.cons or [],
            affiliate_link_id=str(rec.affiliate_link_id) if rec.affiliate_link_id else None,
            helpful_count=rec.helpful_count,
            view_count=int(rec.view_count or 0),
            is_featured=rec.is_featured,
            created_at=rec.created_at,
        ))

    return result


# ── Storefront Endpoint ────────────────────────────────────────────────────────

@router.get("/{influencer_id}/storefront")
async def get_influencer_storefront(
    influencer_id: str,
    db: Session = Depends(get_db),
    user: Optional[UserProfile] = Depends(optional_auth),
):
    """Get complete storefront data for an influencer."""
    influencer = db.query(Influencer).filter(Influencer.id == influencer_id).first()
    if not influencer or influencer.status != "approved":
        raise HTTPException(status_code=404, detail="Influencer not found")

    # Get featured outfits
    featured_outfits = db.query(InfluencerOutfit).filter(
        InfluencerOutfit.influencer_id == influencer.id,
        InfluencerOutfit.status == "published",
        InfluencerOutfit.visibility == "public",
    ).order_by(
        InfluencerOutfit.is_featured.desc(),
        InfluencerOutfit.published_at.desc(),
    ).limit(6).all()

    # Get all outfits count
    total_outfits = db.query(InfluencerOutfit).filter(
        InfluencerOutfit.influencer_id == influencer.id,
        InfluencerOutfit.status == "published",
        InfluencerOutfit.visibility == "public",
    ).count()

    # Get recommendations
    recommendations = db.query(InfluencerRecommendation).filter(
        InfluencerRecommendation.influencer_id == influencer.id,
        InfluencerRecommendation.status == "active",
    ).order_by(InfluencerRecommendation.is_featured.desc()).limit(12).all()

    # Check if following
    is_following = False
    if user:
        follow = db.query(InfluencerFollower).filter(
            InfluencerFollower.influencer_id == influencer.id,
            InfluencerFollower.follower_user_id == user.id,
        ).first()
        is_following = follow is not None

    return {
        "profile": _influencer_to_response(influencer, is_following),
        "featured_outfits": [
            InfluencerOutfitListResponse(
                id=str(o.id),
                influencer_id=str(o.influencer_id),
                influencer_name=influencer.display_name,
                influencer_avatar=influencer.avatar_url,
                title=o.title,
                thumbnail_url=o.thumbnail_url or o.image_url,
                occasion=o.occasion,
                style_tags=o.style_tags or [],
                like_count=o.like_count,
                save_count=o.save_count,
                is_featured=o.is_featured,
                published_at=o.published_at,
            )
            for o in featured_outfits
        ],
        "total_outfits": total_outfits,
        "recommendations": [
            ProductRecommendationResponse(
                id=str(r.id),
                influencer_id=str(r.influencer_id),
                influencer_name=influencer.display_name,
                influencer_avatar=influencer.avatar_url,
                product_id=str(r.product_id),
                product_name=r.product.name if r.product else None,
                product_image_url=r.product.image_url if r.product else None,
                product_price=r.product.price if r.product else None,
                review_text=r.review_text,
                rating=r.rating,
                pros=r.pros or [],
                cons=r.cons or [],
                affiliate_link_id=str(r.affiliate_link_id) if r.affiliate_link_id else None,
                helpful_count=r.helpful_count,
                view_count=int(r.view_count or 0),
                is_featured=r.is_featured,
                created_at=r.created_at,
            )
            for r in recommendations
        ],
    }
