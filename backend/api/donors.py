"""
CONFIT Backend - Donor Impact Wall API (Phase 4)
================================================
Public API endpoints for donor impact wall and coupons.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from api.deps import get_db, get_current_user_optional, get_current_user_id
from database.donation_models import Donor, Coupon, DonorTier, CouponType, CouponVisibility
from services.donor_service import DonorService, get_donor_service
from services.coupon_service import CouponService, get_coupon_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/donors", tags=["donors"])


# ========================================
# RESPONSE MODELS
# ========================================

class PublicDonorResponse(BaseModel):
    """Public donor info (no user_id exposed)."""
    id: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    tier: str
    total_donated_egp: float
    people_helped: int
    is_verified: bool
    
    class Config:
        from_attributes = True


class ImpactStatsResponse(BaseModel):
    """Global donation statistics."""
    total_donors: int
    total_donated_egp: float
    total_people_helped: int
    total_coupons_created: int
    total_coupons_redeemed: int
    tier_distribution: dict


class PublicCouponResponse(BaseModel):
    """Public coupon info for display."""
    id: str
    code: str
    type: str
    value: int
    min_cart_egp: Optional[float] = None
    max_discount_egp: Optional[float] = None
    donor_name: Optional[str] = None
    donor_message: Optional[str] = None
    valid_until: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CouponValidateRequest(BaseModel):
    """Coupon validation request."""
    code: str
    cart_total_egp: float = Field(..., ge=0)


class CouponValidateResponse(BaseModel):
    """Coupon validation response."""
    is_valid: bool
    discount_egp: float = 0
    error_reason: Optional[str] = None
    coupon_type: Optional[str] = None


class CouponRedeemRequest(BaseModel):
    """Coupon redemption request."""
    code: str
    order_id: str
    cart_total_egp: float = Field(..., gt=0)


class CouponRedeemResponse(BaseModel):
    """Coupon redemption response."""
    success: bool
    discount_applied_egp: float
    redemption_id: str


# ========================================
# IMPACT WALL ENDPOINTS
# ========================================

@router.get("/impact-wall", response_model=List[PublicDonorResponse])
async def get_impact_wall(
    tier: Optional[str] = Query(None, description="Filter by tier"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get public donor impact wall.
    
    Returns donors who are not anonymous, sorted by total donated.
    Never exposes donor.user_id.
    """
    query = select(Donor).where(Donor.is_anonymous == False)
    
    if tier:
        try:
            tier_enum = DonorTier(tier.lower())
            query = query.where(Donor.tier == tier_enum)
        except ValueError:
            pass
    
    query = query.order_by(Donor.total_donated_piastres.desc())
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    donors = result.scalars().all()
    
    return [
        PublicDonorResponse(
            id=d.id,
            display_name=d.display_name,
            avatar_url=d.avatar_url,
            bio=d.bio,
            tier=d.tier.value,
            total_donated_egp=d.total_donated_piastres / 100,
            people_helped=d.people_helped,
            is_verified=d.is_verified,
        )
        for d in donors
    ]


@router.get("/stats", response_model=ImpactStatsResponse)
async def get_impact_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get global donation statistics."""
    # Total donors
    total_donors_result = await db.execute(
        select(func.count()).select_from(Donor)
    )
    total_donors = total_donors_result.scalar() or 0
    
    # Total donated
    total_donated_result = await db.execute(
        select(func.sum(Donor.total_donated_piastres))
    )
    total_donated_piastres = total_donated_result.scalar() or 0
    
    # People helped
    people_helped_result = await db.execute(
        select(func.sum(Donor.people_helped))
    )
    people_helped = people_helped_result.scalar() or 0
    
    # Coupons created
    coupons_created_result = await db.execute(
        select(func.count()).select_from(Coupon)
    )
    coupons_created = coupons_created_result.scalar() or 0
    
    # Tier distribution
    tier_dist = {}
    for tier in DonorTier:
        count_result = await db.execute(
            select(func.count()).select_from(Donor).where(Donor.tier == tier)
        )
        tier_dist[tier.value] = count_result.scalar() or 0
    
    return ImpactStatsResponse(
        total_donors=total_donors,
        total_donated_egp=total_donated_piastres / 100,
        total_people_helped=people_helped,
        total_coupons_created=coupons_created,
        total_coupons_redeemed=0,
        tier_distribution=tier_dist,
    )


# ========================================
# COUPON ENDPOINTS
# ========================================

@router.get("/coupons", response_model=List[PublicCouponResponse])
async def list_visible_coupons(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    """List coupons visible to current user."""
    user_id = current_user.user_id if current_user else None
    user_category = None
    
    coupon_service = CouponService(db)
    coupons = await coupon_service.list_visible_coupons(
        user_id=user_id or "anonymous",
        user_category=user_category,
        limit=limit,
    )
    
    return [
        PublicCouponResponse(
            id=c.id,
            code=c.code,
            type=c.type.value,
            value=c.value,
            min_cart_egp=c.min_cart_piastres / 100 if c.min_cart_piastres else None,
            max_discount_egp=c.max_discount_piastres / 100 if c.max_discount_piastres else None,
            donor_name=c.donor.display_name if c.donor and not c.donor.is_anonymous else None,
            donor_message=c.donor_message,
            valid_until=c.valid_until,
        )
        for c in coupons
    ]


@router.post("/coupons/validate", response_model=CouponValidateResponse)
async def validate_coupon(
    request: CouponValidateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    """Validate a coupon code."""
    user_id = current_user.user_id if current_user else "anonymous"
    cart_piastres = int(request.cart_total_egp * 100)
    
    coupon_service = CouponService(db)
    validation = await coupon_service.validate_coupon(
        code=request.code,
        user_id=user_id,
        cart_total_piastres=cart_piastres,
    )
    
    return CouponValidateResponse(
        is_valid=validation.is_valid,
        discount_egp=validation.discount_amount_piastres / 100,
        error_reason=validation.error_reason,
        coupon_type=validation.coupon.type.value if validation.coupon else None,
    )


@router.post("/coupons/redeem", response_model=CouponRedeemResponse)
async def redeem_coupon(
    request: CouponRedeemRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Redeem a coupon (requires authentication)."""
    cart_piastres = int(request.cart_total_egp * 100)
    
    coupon_service = CouponService(db)
    
    try:
        redemption = await coupon_service.redeem_coupon(
            code=request.code,
            user_id=str(user_id),
            order_id=request.order_id,
            cart_total_piastres=cart_piastres,
        )
        
        return CouponRedeemResponse(
            success=True,
            discount_applied_egp=redemption.discount_applied_piastres / 100,
            redemption_id=redemption.id,
        )
    except Exception as e:
        logger.warning("Coupon redemption failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
