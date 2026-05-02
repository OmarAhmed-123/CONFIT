"""
CONFIT Admin Platform Analytics API
====================================
Platform-wide analytics for admin dashboards.
Auth: admin only.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, and_, text, desc
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import (
    AnalyticsEvent, DailyStoreSummary, DailyBrandSummary, DailyUserSummary,
    Order, User, UserRole, AppRole, Notification, ReturnRequest
)
from models.profile_models import UserBehaviorSignal
from services.analytics_realtime import realtime_counters
from services.auth_service import UserProfile
from utils.auth_deps import require_auth
from utils.rbac import require_admin

router = APIRouter(prefix="/api/v1/analytics/admin", tags=["Admin Analytics"])


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------

class RetentionCohort(BaseModel):
    """Retention cohort data."""
    cohort_date: str
    users_count: int
    d1_retention: float
    d7_retention: float
    d30_retention: float


class CouponHealth(BaseModel):
    """Coupon ecosystem health."""
    active_coupons: int
    redeemed_coupons: int
    expired_coupons: int
    total_discount_egp: float


class AdminOverviewResponse(BaseModel):
    """Admin platform overview response."""
    # North Star metric
    confident_purchases_per_month: int
    
    # User metrics
    dau: int
    wau: int
    mau: int
    
    # Retention
    retention_cohorts: List[RetentionCohort]
    
    # Quality metrics
    fraud_flags_count: int
    nps_score: Optional[float]
    csat_score: Optional[float]
    
    # Coupon ecosystem
    coupon_ecosystem_health: CouponHealth
    
    # Additional metrics
    total_revenue_egp: float
    total_orders: int
    total_users: int
    active_stores: int
    active_brands: int


class PlatformMetricsResponse(BaseModel):
    """Platform metrics response."""
    period_start: str
    period_end: str
    total_events: int
    events_by_type: Dict[str, int]
    top_events: List[Dict[str, Any]]


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def _require_admin(user: UserProfile, db: Session) -> None:
    """Ensure user is admin."""
    user_role = db.query(UserRole).filter(UserRole.user_id == user.id).first()
    if not user_role or user_role.role != AppRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")


def _calculate_retention(db: Session, cohort_date: datetime, days: int) -> float:
    """Calculate retention for a cohort."""
    cohort_users = db.query(func.distinct(UserBehaviorSignal.user_id)).filter(
        UserBehaviorSignal.created_at >= cohort_date,
        UserBehaviorSignal.created_at < cohort_date + timedelta(days=1),
    ).subquery()
    
    if days == 1:
        target_date = cohort_date + timedelta(days=1)
    elif days == 7:
        target_date = cohort_date + timedelta(days=7)
    else:  # 30
        target_date = cohort_date + timedelta(days=30)
    
    retained = db.query(func.count()).filter(
        UserBehaviorSignal.user_id.in_(cohort_users),
        UserBehaviorSignal.created_at >= target_date,
        UserBehaviorSignal.created_at < target_date + timedelta(days=1),
    ).scalar() or 0
    
    cohort_size = db.query(func.count()).select_from(cohort_users).scalar() or 1
    
    return (retained / cohort_size * 100) if cohort_size > 0 else 0.0


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.get("/overview", response_model=AdminOverviewResponse)
async def get_admin_overview(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Get platform-wide analytics overview.
    
    Auth: admin only.
    
    Returns:
        - North Star: confident_purchases_per_month
        - DAU, WAU, MAU
        - Retention cohorts (D1, D7, D30)
        - Fraud flags
        - NPS, CSAT
        - Coupon ecosystem health
    """
    _require_admin(user, db)
    
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # North Star: confident purchases (orders not returned within 30 days)
    confident_purchases = db.query(func.count(Order.id)).filter(
        Order.payment_status == "success",
        Order.placed_at >= month_start,
        Order.placed_at < now - timedelta(days=30),  # At least 30 days old
        ~Order.id.in_(
            db.query(ReturnRequest.order_id).filter(
                ReturnRequest.requested_at >= month_start,
            )
        ),
    ).scalar() or 0
    
    # Get DAU from Redis or DB
    dau = realtime_counters.get_dau()
    if dau == 0:
        dau = db.query(func.count(func.distinct(UserBehaviorSignal.user_id))).filter(
            UserBehaviorSignal.created_at >= day_start,
        ).scalar() or 0
    
    # Get WAU
    wau = db.query(func.count(func.distinct(UserBehaviorSignal.user_id))).filter(
        UserBehaviorSignal.created_at >= week_ago,
    ).scalar() or 0
    
    # Get MAU
    mau = db.query(func.count(func.distinct(UserBehaviorSignal.user_id))).filter(
        UserBehaviorSignal.created_at >= month_ago,
    ).scalar() or 0
    
    # Calculate retention cohorts (last 4 weeks)
    retention_cohorts = []
    for i in range(4):
        cohort_date = (now - timedelta(weeks=i+1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        # Get cohort size
        cohort_size = db.query(
            func.count(func.distinct(UserBehaviorSignal.user_id))
        ).filter(
            UserBehaviorSignal.created_at >= cohort_date,
            UserBehaviorSignal.created_at < cohort_date + timedelta(days=1),
        ).scalar() or 0
        
        if cohort_size > 0:
            retention_cohorts.append(RetentionCohort(
                cohort_date=cohort_date.strftime("%Y-%m-%d"),
                users_count=cohort_size,
                d1_retention=round(_calculate_retention(db, cohort_date, 1), 2),
                d7_retention=round(_calculate_retention(db, cohort_date, 7), 2),
                d30_retention=round(_calculate_retention(db, cohort_date, 30), 2),
            ))
    
    # Get fraud flags (from analytics events)
    fraud_flags = db.query(func.count(AnalyticsEvent.id)).filter(
        AnalyticsEvent.event_name == "fraud_flagged",
        AnalyticsEvent.timestamp >= month_start,
    ).scalar() or 0
    
    # Get NPS and CSAT (from analytics events)
    nps_events = db.query(
        AnalyticsEvent.properties["score"].label("score"),
    ).filter(
        AnalyticsEvent.event_name == "nps_response",
        AnalyticsEvent.timestamp >= month_start,
    ).all()
    
    nps_score = None
    if nps_events:
        scores = [e.score for e in nps_events if e.score is not None]
        if scores:
            promoters = len([s for s in scores if s >= 9])
            detractors = len([s for s in scores if s <= 6])
            nps_score = ((promoters - detractors) / len(scores)) * 100
    
    csat_events = db.query(
        AnalyticsEvent.properties["score"].label("score"),
    ).filter(
        AnalyticsEvent.event_name == "csat_response",
        AnalyticsEvent.timestamp >= month_start,
    ).all()
    
    csat_score = None
    if csat_events:
        scores = [e.score for e in csat_events if e.score is not None]
        if scores:
            csat_score = sum(scores) / len(scores)
    
    # Get coupon ecosystem health
    coupon_applied = db.query(func.count(func.distinct(AnalyticsEvent.properties["coupon_code"]))).filter(
        AnalyticsEvent.event_name == "coupon_applied",
        AnalyticsEvent.timestamp >= month_start,
    ).scalar() or 0
    
    coupon_redeemed = db.query(func.count(func.distinct(AnalyticsEvent.properties["coupon_code"]))).filter(
        AnalyticsEvent.event_name == "coupon_redeemed",
        AnalyticsEvent.timestamp >= month_start,
    ).scalar() or 0
    
    coupon_expired = db.query(func.count(func.distinct(AnalyticsEvent.properties["coupon_code"]))).filter(
        AnalyticsEvent.event_name == "coupon_expired",
        AnalyticsEvent.timestamp >= month_start,
    ).scalar() or 0
    
    total_discount = db.query(
        func.sum(AnalyticsEvent.properties["discount_egp"])
    ).filter(
        AnalyticsEvent.event_name == "coupon_redeemed",
        AnalyticsEvent.timestamp >= month_start,
    ).scalar() or 0
    
    coupon_health = CouponHealth(
        active_coupons=int(coupon_applied - coupon_redeemed - coupon_expired),
        redeemed_coupons=int(coupon_redeemed),
        expired_coupons=int(coupon_expired),
        total_discount_egp=float(total_discount),
    )
    
    # Get additional metrics
    total_revenue = db.query(func.sum(Order.total)).filter(
        Order.payment_status == "success",
        Order.placed_at >= month_start,
    ).scalar() or 0
    
    total_orders = db.query(func.count(Order.id)).filter(
        Order.payment_status == "success",
        Order.placed_at >= month_start,
    ).scalar() or 0
    
    total_users = db.query(func.count(User.id)).scalar() or 0
    
    active_stores = db.query(func.count(func.distinct(AnalyticsEvent.store_id))).filter(
        AnalyticsEvent.store_id.isnot(None),
        AnalyticsEvent.timestamp >= month_ago,
    ).scalar() or 0
    
    active_brands = db.query(func.count(func.distinct(AnalyticsEvent.properties["brand_id"]))).filter(
        AnalyticsEvent.properties["brand_id"].isnot(None),
        AnalyticsEvent.timestamp >= month_ago,
    ).scalar() or 0
    
    return AdminOverviewResponse(
        confident_purchases_per_month=int(confident_purchases),
        dau=int(dau),
        wau=int(wau),
        mau=int(mau),
        retention_cohorts=retention_cohorts,
        fraud_flags_count=int(fraud_flags),
        nps_score=round(nps_score, 2) if nps_score else None,
        csat_score=round(csat_score, 2) if csat_score else None,
        coupon_ecosystem_health=coupon_health,
        total_revenue_egp=float(total_revenue),
        total_orders=int(total_orders),
        total_users=int(total_users),
        active_stores=int(active_stores),
        active_brands=int(active_brands),
    )


@router.get("/metrics")
async def get_platform_metrics(
    days: int = Query(7, ge=1, le=90),
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get platform-wide event metrics."""
    _require_admin(user, db)
    
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    # Get total events
    total_events = db.query(func.count(AnalyticsEvent.id)).filter(
        AnalyticsEvent.timestamp >= start_date,
    ).scalar() or 0
    
    # Get events by type
    events_by_type = dict(db.query(
        AnalyticsEvent.event_name,
        func.count(),
    ).filter(
        AnalyticsEvent.timestamp >= start_date,
    ).group_by(
        AnalyticsEvent.event_name,
    ).all())
    
    # Get top events
    top_events = [
        {"event_name": name, "count": count}
        for name, count in sorted(events_by_type.items(), key=lambda x: x[1], reverse=True)[:20]
    ]
    
    return PlatformMetricsResponse(
        period_start=start_date.isoformat(),
        period_end=now.isoformat(),
        total_events=int(total_events),
        events_by_type=events_by_type,
        top_events=top_events,
    )


@router.get("/revenue")
async def get_revenue_analytics(
    days: int = Query(30, ge=1, le=365),
    group_by: str = Query("day", pattern="^(day|week|month|store|brand)$"),
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get revenue analytics grouped by time period or entity."""
    _require_admin(user, db)
    
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    if group_by == "day":
        query = text("""
            SELECT
                DATE(placed_at) as period,
                COUNT(*) as orders,
                SUM(total) as revenue
            FROM orders
            WHERE payment_status = 'success'
            AND placed_at >= :start_date
            GROUP BY DATE(placed_at)
            ORDER BY period
        """)
    elif group_by == "week":
        query = text("""
            SELECT
                DATE_TRUNC('week', placed_at) as period,
                COUNT(*) as orders,
                SUM(total) as revenue
            FROM orders
            WHERE payment_status = 'success'
            AND placed_at >= :start_date
            GROUP BY DATE_TRUNC('week', placed_at)
            ORDER BY period
        """)
    elif group_by == "month":
        query = text("""
            SELECT
                DATE_TRUNC('month', placed_at) as period,
                COUNT(*) as orders,
                SUM(total) as revenue
            FROM orders
            WHERE payment_status = 'success'
            AND placed_at >= :start_date
            GROUP BY DATE_TRUNC('month', placed_at)
            ORDER BY period
        """)
    elif group_by == "store":
        query = text("""
            SELECT
                s.id as store_id,
                s.name as store_name,
                COUNT(o.id) as orders,
                SUM(o.total) as revenue
            FROM orders o
            JOIN stores s ON s.id = o.pickup_store_id
            WHERE o.payment_status = 'success'
            AND o.placed_at >= :start_date
            GROUP BY s.id, s.name
            ORDER BY revenue DESC
        """)
    else:  # brand
        query = text("""
            SELECT
                b.id as brand_id,
                b.name as brand_name,
                COUNT(DISTINCT o.id) as orders,
                SUM(o.total) as revenue
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN products p ON p.id = oi.product_id
            JOIN brands b ON b.id = p.brand_id
            WHERE o.payment_status = 'success'
            AND o.placed_at >= :start_date
            GROUP BY b.id, b.name
            ORDER BY revenue DESC
        """)
    
    results = db.execute(query, {"start_date": start_date}).all()
    
    return {
        "period_days": days,
        "group_by": group_by,
        "data": [
            {
                "period": str(row[0]) if group_by in ("day", "week", "month") else None,
                "store_id": str(row[0]) if group_by == "store" else None,
                "store_name": row[1] if group_by == "store" else None,
                "brand_id": str(row[0]) if group_by == "brand" else None,
                "brand_name": row[1] if group_by == "brand" else None,
                "orders": int(row[-2]),
                "revenue_egp": float(row[-1] or 0),
            }
            for row in results
        ],
    }


@router.get("/funnel")
async def get_conversion_funnel(
    days: int = Query(30, ge=1, le=90),
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get conversion funnel metrics."""
    _require_admin(user, db)
    
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    # Define funnel stages
    stages = [
        ("app_opened", "App Opened"),
        ("product_viewed", "Product Viewed"),
        ("try_on_started", "Try-On Started"),
        ("try_on_completed", "Try-On Completed"),
        ("checkout_started", "Checkout Started"),
        ("payment_succeeded", "Payment Succeeded"),
    ]
    
    funnel_data = []
    previous_count = None
    
    for event_name, stage_name in stages:
        count = db.query(func.count(func.distinct(AnalyticsEvent.user_id))).filter(
            AnalyticsEvent.event_name == event_name,
            AnalyticsEvent.timestamp >= start_date,
        ).scalar() or 0
        
        conversion_rate = None
        if previous_count is not None and previous_count > 0:
            conversion_rate = (count / previous_count) * 100
        
        funnel_data.append({
            "stage": stage_name,
            "event_name": event_name,
            "unique_users": int(count),
            "conversion_from_previous": round(conversion_rate, 2) if conversion_rate else None,
        })
        
        previous_count = count
    
    return {
        "period_days": days,
        "funnel": funnel_data,
    }


@router.get("/geographic")
async def get_geographic_distribution(
    days: int = Query(30, ge=1, le=90),
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get user and order distribution by geography."""
    _require_admin(user, db)
    
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    # Get user distribution by country
    user_by_country = dict(db.query(
        AnalyticsEvent.country,
        func.count(func.distinct(AnalyticsEvent.user_id)),
    ).filter(
        AnalyticsEvent.timestamp >= start_date,
        AnalyticsEvent.country.isnot(None),
    ).group_by(
        AnalyticsEvent.country,
    ).all())
    
    # Get order distribution by city (Egypt)
    order_by_city = dict(db.query(
        Order.shipping_address["city"].label("city"),
        func.count(Order.id),
    ).filter(
        Order.payment_status == "success",
        Order.placed_at >= start_date,
    ).group_by(
        Order.shipping_address["city"],
    ).all())
    
    return {
        "period_days": days,
        "users_by_country": user_by_country,
        "orders_by_city_egypt": order_by_city,
    }
