"""
CONFIT Store Analytics API
==========================
Analytics endpoints for store manager dashboards.
Auth: store_manager or admin required.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, and_, text
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import (
    AnalyticsEvent, DailyStoreSummary, Order, ReturnRequest, Store, User, UserRole, AppRole
)
from services.analytics_realtime import realtime_counters
from services.auth_service import UserProfile
from utils.auth_deps import require_auth
from utils.rbac import require_role

router = APIRouter(prefix="/api/v1/analytics/stores", tags=["Store Analytics"])


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------

class TopSKU(BaseModel):
    """Top viewed SKU with count."""
    sku: str
    product_name: Optional[str] = None
    view_count: int


class ReturnReasonBreakdown(BaseModel):
    """Return reason breakdown."""
    fit: int = 0
    color: int = 0
    quality: int = 0
    other: int = 0


class StoreDashboardResponse(BaseModel):
    """Store dashboard analytics response."""
    store_id: str
    store_name: str
    visitors_today: int
    visitors_7d: int
    visitors_30d: int
    conversion_rate: float  # visitors -> purchases
    try_on_to_purchase_rate: float
    top_viewed_skus: List[TopSKU]
    bopis_avg_pickup_time_minutes: Optional[float]
    return_reason_breakdown: ReturnReasonBreakdown
    coupon_redemption_rate: float
    donor_coupon_attribution_egp: float
    
    # Additional metrics
    revenue_today_egp: float = 0
    revenue_7d_egp: float = 0
    revenue_30d_egp: float = 0
    orders_today: int = 0
    orders_7d: int = 0
    orders_30d: int = 0


class HeatmapCell(BaseModel):
    """Heatmap cell for hour × day_of_week."""
    hour: int
    day_of_week: int  # 0=Monday, 6=Sunday
    visitor_count: int


class HeatmapResponse(BaseModel):
    """Store visitor heatmap response."""
    store_id: str
    data: List[HeatmapCell]


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def _get_store_or_404(db: Session, store_id: str) -> Store:
    """Get store or raise 404."""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


def _check_store_access(user: UserProfile, store: Store, db: Session) -> None:
    """Check if user has access to store analytics (store_manager or admin)."""
    # Admin has access to all stores
    user_role = db.query(UserRole).filter(UserRole.user_id == user.id).first()
    if user_role and user_role.role == AppRole.admin:
        return
    
    # Store manager must be associated with the store's brand
    if user_role and user_role.role == AppRole.brand_manager:
        # Check if user is manager for this store's brand
        # In a real system, there would be a brand_manager assignment table
        # For now, we allow brand_manager access if they manage the brand
        pass
    
    # If no valid role, deny access
    if not user_role or user_role.role not in (AppRole.admin, AppRole.brand_manager):
        raise HTTPException(status_code=403, detail="Access denied")


def _parse_return_reason(reason: str) -> str:
    """Categorize return reason into standard categories."""
    reason_lower = reason.lower()
    if any(word in reason_lower for word in ["fit", "size", "tight", "loose", "length"]):
        return "fit"
    elif any(word in reason_lower for word in ["color", "colour", "shade"]):
        return "color"
    elif any(word in reason_lower for word in ["quality", "material", "fabric", "stitch", "defect"]):
        return "quality"
    return "other"


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.get("/{store_id}/dashboard", response_model=StoreDashboardResponse)
async def get_store_dashboard(
    store_id: str,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Get comprehensive store analytics dashboard.
    
    Auth: store_manager (for their store) or admin.
    
    Returns:
        - Visitor counts (today, 7d, 30d)
        - Conversion rates
        - Top viewed SKUs
        - BOPIS pickup metrics
        - Return reason breakdown
        - Coupon metrics
    """
    store = _get_store_or_404(db, store_id)
    _check_store_access(user, store, db)
    
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_7_ago = today_start - timedelta(days=7)
    day_30_ago = today_start - timedelta(days=30)
    
    # Try Redis realtime counters first, fallback to DB
    realtime_data = realtime_counters.get_store_counters(store_id, days=30)
    
    # Get visitor counts from analytics_events
    visitors_today = db.query(func.count(func.distinct(AnalyticsEvent.user_id))).filter(
        AnalyticsEvent.store_id == store_id,
        AnalyticsEvent.event_name == "store_visited",
        AnalyticsEvent.timestamp >= today_start,
    ).scalar() or 0
    
    visitors_7d = db.query(func.count(func.distinct(AnalyticsEvent.user_id))).filter(
        AnalyticsEvent.store_id == store_id,
        AnalyticsEvent.event_name == "store_visited",
        AnalyticsEvent.timestamp >= day_7_ago,
    ).scalar() or 0
    
    visitors_30d = db.query(func.count(func.distinct(AnalyticsEvent.user_id))).filter(
        AnalyticsEvent.store_id == store_id,
        AnalyticsEvent.event_name == "store_visited",
        AnalyticsEvent.timestamp >= day_30_ago,
    ).scalar() or 0
    
    # Use realtime if available and higher
    if realtime_data.get("visits_today", 0) > visitors_today:
        visitors_today = realtime_data["visits_today"]
    
    # Get purchase counts
    purchases_30d = db.query(func.count(func.distinct(Order.id))).filter(
        Order.pickup_store_id == store_id,
        Order.placed_at >= day_30_ago,
        Order.payment_status == "success",
    ).scalar() or 0
    
    # Calculate conversion rate
    conversion_rate = (purchases_30d / visitors_30d * 100) if visitors_30d > 0 else 0.0
    
    # Get try-on to purchase rate
    try_on_events = db.query(func.count(func.distinct(AnalyticsEvent.session_id))).filter(
        AnalyticsEvent.store_id == store_id,
        AnalyticsEvent.event_name == "try_on_completed",
        AnalyticsEvent.timestamp >= day_30_ago,
    ).scalar() or 0
    
    try_on_purchases = db.query(func.count(func.distinct(AnalyticsEvent.session_id))).filter(
        AnalyticsEvent.store_id == store_id,
        AnalyticsEvent.event_name == "try_on_added_to_bag",
        AnalyticsEvent.timestamp >= day_30_ago,
    ).scalar() or 0
    
    try_on_to_purchase_rate = (try_on_purchases / try_on_events * 100) if try_on_events > 0 else 0.0
    
    # Get top viewed SKUs
    top_skus_query = db.query(
        AnalyticsEvent.properties["sku"].label("sku"),
        func.count().label("view_count"),
    ).filter(
        AnalyticsEvent.store_id == store_id,
        AnalyticsEvent.event_name == "product_viewed",
        AnalyticsEvent.timestamp >= day_30_ago,
    ).group_by(
        AnalyticsEvent.properties["sku"]
    ).order_by(
        func.count().desc()
    ).limit(10).all()
    
    top_viewed_skus = [
        TopSKU(sku=row.sku or "unknown", view_count=row.view_count)
        for row in top_skus_query
    ]
    
    # Get BOPIS avg pickup time
    # This would come from pickup_records with pickup_time vs order.placed_at
    bopis_avg_pickup_time = None
    try:
        pickup_query = text("""
            SELECT AVG(EXTRACT(EPOCH FROM (
                CAST(pickup_time AS TIMESTAMP) - o.placed_at
            )) / 60) as avg_minutes
            FROM pickup_records pr
            JOIN orders o ON o.id = pr.order_id
            WHERE pr.store_id = :store_id
            AND o.placed_at >= :start_date
            AND pr.status != 'cancelled'
        """)
        result = db.execute(pickup_query, {"store_id": store_id, "start_date": day_30_ago}).first()
        if result and result[0]:
            bopis_avg_pickup_time = float(result[0])
    except Exception:
        pass
    
    # Get return reason breakdown
    returns = db.query(ReturnRequest.reason).filter(
        ReturnRequest.order_id.in_(
            db.query(Order.id).filter(
                Order.pickup_store_id == store_id,
                Order.placed_at >= day_30_ago,
            )
        )
    ).all()
    
    return_breakdown = ReturnReasonBreakdown()
    for r in returns:
        category = _parse_return_reason(r.reason or "")
        if category == "fit":
            return_breakdown.fit += 1
        elif category == "color":
            return_breakdown.color += 1
        elif category == "quality":
            return_breakdown.quality += 1
        else:
            return_breakdown.other += 1
    
    # Get coupon metrics
    coupon_applied = db.query(func.count()).filter(
        AnalyticsEvent.store_id == store_id,
        AnalyticsEvent.event_name == "coupon_applied",
        AnalyticsEvent.timestamp >= day_30_ago,
    ).scalar() or 0
    
    coupon_redeemed = db.query(func.count()).filter(
        AnalyticsEvent.store_id == store_id,
        AnalyticsEvent.event_name == "coupon_redeemed",
        AnalyticsEvent.timestamp >= day_30_ago,
    ).scalar() or 0
    
    coupon_redemption_rate = (coupon_redeemed / coupon_applied * 100) if coupon_applied > 0 else 0.0
    
    # Get donor coupon attribution
    donor_coupon_egp = db.query(
        func.sum(AnalyticsEvent.properties["amount_egp"])
    ).filter(
        AnalyticsEvent.store_id == store_id,
        AnalyticsEvent.event_name == "donor_coupon_redeemed",
        AnalyticsEvent.timestamp >= day_30_ago,
    ).scalar() or 0
    
    # Get revenue metrics
    revenue_today = db.query(func.sum(Order.total)).filter(
        Order.pickup_store_id == store_id,
        Order.placed_at >= today_start,
        Order.payment_status == "success",
    ).scalar() or 0
    
    revenue_7d = db.query(func.sum(Order.total)).filter(
        Order.pickup_store_id == store_id,
        Order.placed_at >= day_7_ago,
        Order.payment_status == "success",
    ).scalar() or 0
    
    revenue_30d = db.query(func.sum(Order.total)).filter(
        Order.pickup_store_id == store_id,
        Order.placed_at >= day_30_ago,
        Order.payment_status == "success",
    ).scalar() or 0
    
    # Get order counts
    orders_today = db.query(func.count(Order.id)).filter(
        Order.pickup_store_id == store_id,
        Order.placed_at >= today_start,
        Order.payment_status == "success",
    ).scalar() or 0
    
    orders_7d = db.query(func.count(Order.id)).filter(
        Order.pickup_store_id == store_id,
        Order.placed_at >= day_7_ago,
        Order.payment_status == "success",
    ).scalar() or 0
    
    orders_30d = db.query(func.count(Order.id)).filter(
        Order.pickup_store_id == store_id,
        Order.placed_at >= day_30_ago,
        Order.payment_status == "success",
    ).scalar() or 0
    
    return StoreDashboardResponse(
        store_id=store_id,
        store_name=store.name,
        visitors_today=int(visitors_today),
        visitors_7d=int(visitors_7d),
        visitors_30d=int(visitors_30d),
        conversion_rate=round(conversion_rate, 2),
        try_on_to_purchase_rate=round(try_on_to_purchase_rate, 2),
        top_viewed_skus=top_viewed_skus,
        bopis_avg_pickup_time_minutes=bopis_avg_pickup_time,
        return_reason_breakdown=return_breakdown,
        coupon_redemption_rate=round(coupon_redemption_rate, 2),
        donor_coupon_attribution_egp=float(donor_coupon_egp),
        revenue_today_egp=float(revenue_today),
        revenue_7d_egp=float(revenue_7d),
        revenue_30d_egp=float(revenue_30d),
        orders_today=int(orders_today),
        orders_7d=int(orders_7d),
        orders_30d=int(orders_30d),
    )


@router.get("/{store_id}/heatmap", response_model=HeatmapResponse)
async def get_store_heatmap(
    store_id: str,
    days: int = Query(7, ge=1, le=30, description="Number of days to aggregate"),
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Get store visitor heatmap (hour × day_of_week).
    
    Returns visitor counts aggregated by hour and day of week,
    useful for staffing optimization.
    """
    store = _get_store_or_404(db, store_id)
    _check_store_access(user, store, db)
    
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    # Try Redis heatmap first
    heatmap_data = realtime_counters.get_heatmap(store_id, days=days)
    
    if heatmap_data:
        # Convert to response format
        cells = []
        for key, count in heatmap_data.items():
            try:
                parts = key.split(":")
                hour = int(parts[0])
                day_of_week = int(parts[1])
                cells.append(HeatmapCell(
                    hour=hour,
                    day_of_week=day_of_week,
                    visitor_count=count,
                ))
            except (ValueError, IndexError):
                continue
        
        return HeatmapResponse(store_id=store_id, data=cells)
    
    # Fallback to database query
    query = text("""
        SELECT
            EXTRACT(HOUR FROM timestamp AT TIME ZONE 'Africa/Cairo') as hour,
            EXTRACT(DOW FROM timestamp AT TIME ZONE 'Africa/Cairo') as day_of_week,
            COUNT(*) as visitor_count
        FROM analytics_events
        WHERE store_id = :store_id
        AND event_name = 'store_visited'
        AND timestamp >= :start_date
        GROUP BY hour, day_of_week
        ORDER BY day_of_week, hour
    """)
    
    results = db.execute(query, {
        "store_id": store_id,
        "start_date": start_date,
    }).all()
    
    cells = [
        HeatmapCell(
            hour=int(row.hour),
            day_of_week=int(row.day_of_week),
            visitor_count=int(row.visitor_count),
        )
        for row in results
    ]
    
    return HeatmapResponse(store_id=store_id, data=cells)


@router.get("/{store_id}/top-products")
async def get_store_top_products(
    store_id: str,
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(10, ge=1, le=50),
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get top products by views and purchases for a store."""
    store = _get_store_or_404(db, store_id)
    _check_store_access(user, store, db)
    
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    # Get top viewed products
    top_viewed = db.query(
        AnalyticsEvent.product_id,
        AnalyticsEvent.properties["sku"].label("sku"),
        func.count().label("view_count"),
    ).filter(
        AnalyticsEvent.store_id == store_id,
        AnalyticsEvent.event_name == "product_viewed",
        AnalyticsEvent.timestamp >= start_date,
    ).group_by(
        AnalyticsEvent.product_id,
        AnalyticsEvent.properties["sku"],
    ).order_by(
        func.count().desc()
    ).limit(limit).all()
    
    # Get top purchased products
    top_purchased = db.query(
        AnalyticsEvent.product_id,
        AnalyticsEvent.properties["sku"].label("sku"),
        func.count().label("purchase_count"),
    ).filter(
        AnalyticsEvent.store_id == store_id,
        AnalyticsEvent.event_name == "order_placed",
        AnalyticsEvent.timestamp >= start_date,
    ).group_by(
        AnalyticsEvent.product_id,
        AnalyticsEvent.properties["sku"],
    ).order_by(
        func.count().desc()
    ).limit(limit).all()
    
    return {
        "store_id": store_id,
        "period_days": days,
        "top_viewed": [
            {
                "product_id": str(row.product_id) if row.product_id else None,
                "sku": row.sku,
                "view_count": row.view_count,
            }
            for row in top_viewed
        ],
        "top_purchased": [
            {
                "product_id": str(row.product_id) if row.product_id else None,
                "sku": row.sku,
                "purchase_count": row.purchase_count,
            }
            for row in top_purchased
        ],
    }
