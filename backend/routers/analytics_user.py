"""
CONFIT Customer Personal Analytics API
======================================
Personal analytics endpoints for customer dashboards.
Auth: authenticated user (own data only).
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, and_, text
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import (
    AnalyticsEvent, DailyUserSummary, Order, Outfit, WardrobeItem, Store, User
)
from services.analytics_realtime import realtime_counters
from services.auth_service import UserProfile
from utils.auth_deps import require_auth

router = APIRouter(prefix="/api/v1/analytics/me", tags=["Personal Analytics"])


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------

class VisitedStore(BaseModel):
    """A visited store with location pin."""
    store_id: str
    store_name: str
    address: str
    city: str
    location: Optional[Dict[str, float]] = None  # {lat, lng}
    visit_count: int
    last_visited: str


class WardrobeItemStats(BaseModel):
    """Wardrobe item statistics."""
    total_items: int
    times_worn_total: int
    avg_times_worn_per_item: float


class UserSummaryResponse(BaseModel):
    """User personal analytics summary."""
    user_id: str
    outfits_saved: int
    outfits_saved_30d: int
    try_on_sessions_30d: int
    money_saved_via_coupons_egp: float
    reuse_score: float  # times worn per wardrobe item average
    visited_stores: List[VisitedStore]
    total_orders: int
    total_spent_egp: float
    member_since: str


class ActivityTimeline(BaseModel):
    """Activity timeline entry."""
    date: str
    event_type: str
    event_name: str
    details: Dict[str, Any]


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.get("/summary", response_model=UserSummaryResponse)
async def get_user_summary(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Get personal analytics summary for the authenticated user.
    
    Returns:
        - Outfits saved (total, 30d)
        - Try-on sessions (30d)
        - Money saved via coupons
        - Reuse score (sustainability metric)
        - Visited stores with map pins
    """
    now = datetime.now(timezone.utc)
    day_30_ago = now - timedelta(days=30)
    
    # Get outfits saved
    outfits_saved_total = db.query(func.count(Outfit.id)).filter(
        Outfit.owner_user_id == user.id,
    ).scalar() or 0
    
    outfits_saved_30d = db.query(func.count(AnalyticsEvent.id)).filter(
        AnalyticsEvent.user_id == user.id,
        AnalyticsEvent.event_name == "outfit_saved",
        AnalyticsEvent.timestamp >= day_30_ago,
    ).scalar() or 0
    
    # Get try-on sessions
    try_on_sessions_30d = db.query(func.count(func.distinct(AnalyticsEvent.session_id))).filter(
        AnalyticsEvent.user_id == user.id,
        AnalyticsEvent.event_name.in_(["try_on_started", "try_on_completed"]),
        AnalyticsEvent.timestamp >= day_30_ago,
    ).scalar() or 0
    
    # Get money saved via coupons
    coupon_savings = db.query(
        func.sum(AnalyticsEvent.properties["discount_egp"])
    ).filter(
        AnalyticsEvent.user_id == user.id,
        AnalyticsEvent.event_name == "coupon_applied",
        AnalyticsEvent.timestamp >= day_30_ago,
    ).scalar() or 0
    
    # Calculate reuse score (times worn per wardrobe item)
    wardrobe_items = db.query(func.count(WardrobeItem.id)).filter(
        WardrobeItem.owner_user_id == user.id,
    ).scalar() or 0
    
    # Get times worn from analytics events
    times_worn = db.query(func.count(AnalyticsEvent.id)).filter(
        AnalyticsEvent.user_id == user.id,
        AnalyticsEvent.event_name == "wardrobe_item_worn",
    ).scalar() or 0
    
    reuse_score = (times_worn / wardrobe_items) if wardrobe_items > 0 else 0.0
    
    # Get visited stores
    store_visits = db.query(
        AnalyticsEvent.store_id,
        func.count().label("visit_count"),
        func.max(AnalyticsEvent.timestamp).label("last_visited"),
    ).filter(
        AnalyticsEvent.user_id == user.id,
        AnalyticsEvent.event_name == "store_visited",
        AnalyticsEvent.timestamp >= day_30_ago,
        AnalyticsEvent.store_id.isnot(None),
    ).group_by(
        AnalyticsEvent.store_id,
    ).all()
    
    visited_stores = []
    for visit in store_visits:
        store = db.query(Store).filter(Store.id == visit.store_id).first()
        if store:
            visited_stores.append(VisitedStore(
                store_id=str(store.id),
                store_name=store.name,
                address=store.address,
                city=store.city,
                location=store.location,
                visit_count=visit.visit_count,
                last_visited=visit.last_visited.isoformat(),
            ))
    
    # Get order stats
    total_orders = db.query(func.count(Order.id)).filter(
        Order.user_id == user.id,
        Order.payment_status == "success",
    ).scalar() or 0
    
    total_spent = db.query(func.sum(Order.total)).filter(
        Order.user_id == user.id,
        Order.payment_status == "success",
    ).scalar() or 0
    
    # Get member since
    user_record = db.query(User).filter(User.id == user.id).first()
    member_since = user_record.created_at.isoformat() if user_record else now.isoformat()
    
    return UserSummaryResponse(
        user_id=user.id,
        outfits_saved=int(outfits_saved_total),
        outfits_saved_30d=int(outfits_saved_30d),
        try_on_sessions_30d=int(try_on_sessions_30d),
        money_saved_via_coupons_egp=float(coupon_savings),
        reuse_score=round(reuse_score, 2),
        visited_stores=visited_stores,
        total_orders=int(total_orders),
        total_spent_egp=float(total_spent),
        member_since=member_since,
    )


@router.get("/activity")
async def get_user_activity(
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get user activity timeline."""
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    events = db.query(
        AnalyticsEvent.event_name,
        AnalyticsEvent.timestamp,
        AnalyticsEvent.properties,
        AnalyticsEvent.store_id,
        AnalyticsEvent.product_id,
    ).filter(
        AnalyticsEvent.user_id == user.id,
        AnalyticsEvent.timestamp >= start_date,
    ).order_by(
        AnalyticsEvent.timestamp.desc(),
    ).limit(limit).all()
    
    return {
        "user_id": user.id,
        "period_days": days,
        "activities": [
            {
                "date": event.timestamp.isoformat(),
                "event_type": event.event_name,
                "event_name": event.event_name.replace("_", " ").title(),
                "details": {
                    "store_id": str(event.store_id) if event.store_id else None,
                    "product_id": str(event.product_id) if event.product_id else None,
                    **(event.properties or {}),
                },
            }
            for event in events
        ],
    }


@router.get("/wardrobe-stats")
async def get_wardrobe_stats(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get wardrobe statistics for sustainability metrics."""
    # Get wardrobe items
    items = db.query(WardrobeItem).filter(
        WardrobeItem.owner_user_id == user.id,
    ).all()
    
    total_items = len(items)
    
    # Get category breakdown
    categories = {}
    for item in items:
        cat = item.category or "other"
        categories[cat] = categories.get(cat, 0) + 1
    
    # Get brand breakdown
    brands = {}
    for item in items:
        brand = item.brand or "unknown"
        brands[brand] = brands.get(brand, 0) + 1
    
    # Calculate reuse score
    times_worn = db.query(func.count(AnalyticsEvent.id)).filter(
        AnalyticsEvent.user_id == user.id,
        AnalyticsEvent.event_name == "wardrobe_item_worn",
    ).scalar() or 0
    
    reuse_score = (times_worn / total_items) if total_items > 0 else 0.0
    
    # Get sustainability impact (estimated)
    # Each re-wear saves ~2.5kg CO2 vs buying new
    co2_saved_kg = times_worn * 2.5
    
    return {
        "user_id": user.id,
        "total_items": total_items,
        "times_worn_total": int(times_worn),
        "reuse_score": round(reuse_score, 2),
        "sustainability_impact": {
            "co2_saved_kg": co2_saved_kg,
            "water_saved_liters": times_worn * 2700,  # ~2700L per garment
        },
        "category_breakdown": categories,
        "brand_breakdown": brands,
    }


@router.get("/try-on-history")
async def get_try_on_history(
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get try-on session history."""
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    sessions = db.query(
        AnalyticsEvent.session_id,
        AnalyticsEvent.product_id,
        AnalyticsEvent.timestamp,
        AnalyticsEvent.properties,
    ).filter(
        AnalyticsEvent.user_id == user.id,
        AnalyticsEvent.event_name == "try_on_completed",
        AnalyticsEvent.timestamp >= start_date,
    ).order_by(
        AnalyticsEvent.timestamp.desc(),
    ).limit(limit).all()
    
    return {
        "user_id": user.id,
        "period_days": days,
        "total_sessions": len(sessions),
        "sessions": [
            {
                "session_id": session.session_id,
                "product_id": str(session.product_id) if session.product_id else None,
                "timestamp": session.timestamp.isoformat(),
                "quality_score": session.properties.get("quality_score") if session.properties else None,
                "added_to_bag": session.properties.get("added_to_bag", False) if session.properties else False,
            }
            for session in sessions
        ],
    }


@router.get("/coupon-history")
async def get_coupon_history(
    days: int = Query(90, ge=1, le=365),
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get coupon usage history and savings."""
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    coupons_applied = db.query(AnalyticsEvent).filter(
        AnalyticsEvent.user_id == user.id,
        AnalyticsEvent.event_name == "coupon_applied",
        AnalyticsEvent.timestamp >= start_date,
    ).all()
    
    total_savings = sum(
        (e.properties or {}).get("discount_egp", 0)
        for e in coupons_applied
    )
    
    donor_coupons = [
        e for e in coupons_applied
        if (e.properties or {}).get("donor_id")
    ]
    
    return {
        "user_id": user.id,
        "period_days": days,
        "total_coupons_used": len(coupons_applied),
        "total_savings_egp": float(total_savings),
        "donor_coupons_redeemed": len(donor_coupons),
        "donor_savings_egp": float(sum(
            (e.properties or {}).get("discount_egp", 0)
            for e in donor_coupons
        )),
        "coupons": [
            {
                "coupon_code": (e.properties or {}).get("coupon_code"),
                "discount_egp": (e.properties or {}).get("discount_egp", 0),
                "order_id": (e.properties or {}).get("order_id"),
                "timestamp": e.timestamp.isoformat(),
                "donor_id": (e.properties or {}).get("donor_id"),
            }
            for e in coupons_applied
        ],
    }
