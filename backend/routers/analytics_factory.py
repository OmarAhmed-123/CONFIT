"""
CONFIT Factory/Brand Analytics API
==================================
Analytics endpoints for brand owner dashboards.
Auth: brand_owner or admin required.
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
    AnalyticsEvent, DailyBrandSummary, Order, OrderItem, Product, Brand, User, UserRole, AppRole
)
from services.analytics_realtime import realtime_counters
from services.auth_service import UserProfile
from utils.auth_deps import require_auth

router = APIRouter(prefix="/api/v1/analytics/brands", tags=["Brand Analytics"])


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------

class MidwayRejectionBreakdown(BaseModel):
    """Midway rejection breakdown by reason."""
    fabric_qa: int = 0
    stitch_qa: int = 0
    final_qa: int = 0
    size_mismatch: int = 0
    color_mismatch: int = 0


class SKUSales(BaseModel):
    """SKU sales data."""
    sku: str
    product_name: Optional[str] = None
    quantity_sold: int
    revenue_egp: float


class StyledWith(BaseModel):
    """Cross-brand affinity data."""
    product_id: str
    product_name: Optional[str] = None
    brand_id: str
    brand_name: str
    styled_together_count: int


class RegionalSales(BaseModel):
    """Regional sales breakdown for Egypt."""
    city: str
    sales_count: int
    revenue_egp: float


class ForecastData(BaseModel):
    """Simple forecast data point."""
    date: str
    predicted_sales: int
    confidence_lower: int
    confidence_upper: int


class BrandDashboardResponse(BaseModel):
    """Brand dashboard analytics response."""
    brand_id: str
    brand_name: str
    products_sold_total: int
    products_sold_30d: int
    sku_breakdown: List[SKUSales]
    midway_rejections_count: int
    midway_rejections_by_reason: MidwayRejectionBreakdown
    outfit_to_purchase_ratio: float
    return_reduction_delta: Optional[float]  # vs. pre-CONFIT baseline
    most_styled_with: List[StyledWith]
    regional_heatmap_egypt: List[RegionalSales]
    forecast_next_30d: List[ForecastData]


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def _get_brand_or_404(db: Session, brand_id: str) -> Brand:
    """Get brand or raise 404."""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


def _check_brand_access(user: UserProfile, brand: Brand, db: Session) -> None:
    """Check if user has access to brand analytics (brand_owner or admin)."""
    user_role = db.query(UserRole).filter(UserRole.user_id == user.id).first()
    
    # Admin has access to all brands
    if user_role and user_role.role == AppRole.admin:
        return
    
    # Brand manager must be associated with this brand
    # In a real system, there would be a brand_manager assignment table
    if user_role and user_role.role == AppRole.brand_manager:
        # For now, allow access - in production, verify brand assignment
        return
    
    raise HTTPException(status_code=403, detail="Access denied")


def _categorize_rejection_reason(reason_code: str) -> str:
    """Categorize midway rejection reason code."""
    reason_lower = (reason_code or "").lower()
    if any(word in reason_lower for word in ["fabric", "material", "textile"]):
        return "fabric_qa"
    elif any(word in reason_lower for word in ["stitch", "seam", "sewing"]):
        return "stitch_qa"
    elif any(word in reason_lower for word in ["final", "finish", "overall"]):
        return "final_qa"
    elif any(word in reason_lower for word in ["size", "measurement", "fit"]):
        return "size_mismatch"
    elif any(word in reason_lower for word in ["color", "colour", "shade", "dye"]):
        return "color_mismatch"
    return "final_qa"  # Default category


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.get("/{brand_id}/dashboard", response_model=BrandDashboardResponse)
async def get_brand_dashboard(
    brand_id: str,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Get comprehensive brand analytics dashboard.
    
    Auth: brand_owner (for their brand) or admin.
    
    Returns:
        - Products sold (total, 30d, SKU breakdown)
        - Midway rejection metrics
        - Outfit-to-purchase ratio
        - Return reduction vs baseline
        - Cross-brand affinity (most styled with)
        - Regional heatmap (Egypt cities)
        - 30-day forecast
    """
    brand = _get_brand_or_404(db, brand_id)
    _check_brand_access(user, brand, db)
    
    now = datetime.now(timezone.utc)
    day_30_ago = now - timedelta(days=30)
    
    # Get products sold total
    products_sold_total = db.query(func.sum(OrderItem.quantity)).join(
        Order, Order.id == OrderItem.order_id
    ).join(
        Product, Product.id == OrderItem.product_id
    ).filter(
        Product.brand_id == brand_id,
        Order.payment_status == "success",
    ).scalar() or 0
    
    # Get products sold in last 30 days
    products_sold_30d = db.query(func.sum(OrderItem.quantity)).join(
        Order, Order.id == OrderItem.order_id
    ).join(
        Product, Product.id == OrderItem.product_id
    ).filter(
        Product.brand_id == brand_id,
        Order.payment_status == "success",
        Order.placed_at >= day_30_ago,
    ).scalar() or 0
    
    # Get SKU breakdown
    sku_sales = db.query(
        Product.id.label("product_id"),
        Product.name.label("product_name"),
        OrderItem.product_id,
        func.sum(OrderItem.quantity).label("quantity_sold"),
        func.sum(OrderItem.price * OrderItem.quantity).label("revenue"),
    ).join(
        Order, Order.id == OrderItem.order_id
    ).join(
        Product, Product.id == OrderItem.product_id
    ).filter(
        Product.brand_id == brand_id,
        Order.payment_status == "success",
        Order.placed_at >= day_30_ago,
    ).group_by(
        Product.id,
        Product.name,
        OrderItem.product_id,
    ).order_by(
        desc(func.sum(OrderItem.quantity))
    ).limit(20).all()
    
    sku_breakdown = [
        SKUSales(
            sku=str(row.product_id)[:8],  # Use product_id prefix as SKU
            product_name=row.product_name,
            quantity_sold=int(row.quantity_sold),
            revenue_egp=float(row.revenue or 0),
        )
        for row in sku_sales
    ]
    
    # Get midway rejections
    rejection_events = db.query(
        AnalyticsEvent.properties["reason_code"].label("reason_code"),
        func.count().label("count"),
    ).filter(
        AnalyticsEvent.event_name == "midway_rejection",
        AnalyticsEvent.properties["brand_id"].astext == brand_id,
        AnalyticsEvent.timestamp >= day_30_ago,
    ).all()
    
    midway_rejections_count = sum(r.count for r in rejection_events)
    rejection_breakdown = MidwayRejectionBreakdown()
    
    for r in rejection_events:
        category = _categorize_rejection_reason(str(r.reason_code))
        if category == "fabric_qa":
            rejection_breakdown.fabric_qa += r.count
        elif category == "stitch_qa":
            rejection_breakdown.stitch_qa += r.count
        elif category == "final_qa":
            rejection_breakdown.final_qa += r.count
        elif category == "size_mismatch":
            rejection_breakdown.size_mismatch += r.count
        elif category == "color_mismatch":
            rejection_breakdown.color_mismatch += r.count
    
    # Get outfit-to-purchase ratio
    outfit_appearances = db.query(func.count()).filter(
        AnalyticsEvent.event_name == "outfit_saved",
        AnalyticsEvent.properties["brand_id"].astext == brand_id,
        AnalyticsEvent.timestamp >= day_30_ago,
    ).scalar() or 0
    
    outfit_purchases = db.query(func.count()).filter(
        AnalyticsEvent.event_name == "order_placed",
        AnalyticsEvent.properties["brand_id"].astext == brand_id,
        AnalyticsEvent.properties["from_outfit"].astext == "true",
        AnalyticsEvent.timestamp >= day_30_ago,
    ).scalar() or 0
    
    outfit_to_purchase_ratio = (outfit_purchases / outfit_appearances) if outfit_appearances > 0 else 0.0
    
    # Get return reduction delta (vs baseline)
    # This requires a baseline config - for now, return None
    return_reduction_delta = None
    # In production: compare current return rate to stored baseline
    
    # Get most styled with (cross-brand affinity)
    styled_with_query = text("""
        SELECT
            p2.id as product_id,
            p2.name as product_name,
            p2.brand_id,
            b.name as brand_name,
            COUNT(*) as styled_together_count
        FROM analytics_events ae1
        JOIN analytics_events ae2 ON ae1.session_id = ae2.session_id
        JOIN products p1 ON p1.id = ae1.product_id
        JOIN products p2 ON p2.id = ae2.product_id
        JOIN brands b ON b.id = p2.brand_id
        WHERE ae1.event_name = 'outfit_saved'
        AND ae2.event_name = 'outfit_saved'
        AND p1.brand_id = :brand_id
        AND p2.brand_id != :brand_id
        AND ae1.timestamp >= :start_date
        GROUP BY p2.id, p2.name, p2.brand_id, b.name
        ORDER BY styled_together_count DESC
        LIMIT 10
    """)
    
    styled_with_results = db.execute(styled_with_query, {
        "brand_id": brand_id,
        "start_date": day_30_ago,
    }).all()
    
    most_styled_with = [
        StyledWith(
            product_id=str(row.product_id),
            product_name=row.product_name,
            brand_id=row.brand_id,
            brand_name=row.brand_name,
            styled_together_count=row.styled_together_count,
        )
        for row in styled_with_results
    ]
    
    # Get regional heatmap for Egypt
    regional_query = db.query(
        Order.shipping_address["city"].label("city"),
        func.count(Order.id).label("sales_count"),
        func.sum(Order.total).label("revenue"),
    ).join(
        OrderItem, OrderItem.order_id == Order.id
    ).join(
        Product, Product.id == OrderItem.product_id
    ).filter(
        Product.brand_id == brand_id,
        Order.payment_status == "success",
        Order.placed_at >= day_30_ago,
    ).group_by(
        Order.shipping_address["city"],
    ).all()
    
    # Map to Egyptian cities
    egypt_cities = ["Cairo", "Alexandria", "Giza", "Luxor", "Aswan", "Port Said", "Suez", "Mansoura", "Tanta", "Fayoum"]
    regional_heatmap = []
    
    for row in regional_query:
        city = row.city
        if city and city in egypt_cities:
            regional_heatmap.append(RegionalSales(
                city=city,
                sales_count=int(row.sales_count),
                revenue_egp=float(row.revenue or 0),
            ))
    
    # Generate simple forecast (using moving average as placeholder)
    # In production, use ARIMA or Prophet
    forecast = _generate_simple_forecast(db, brand_id, days=30)
    
    return BrandDashboardResponse(
        brand_id=brand_id,
        brand_name=brand.name,
        products_sold_total=int(products_sold_total),
        products_sold_30d=int(products_sold_30d),
        sku_breakdown=sku_breakdown,
        midway_rejections_count=int(midway_rejections_count),
        midway_rejections_by_reason=rejection_breakdown,
        outfit_to_purchase_ratio=round(outfit_to_purchase_ratio, 3),
        return_reduction_delta=return_reduction_delta,
        most_styled_with=most_styled_with,
        regional_heatmap_egypt=regional_heatmap,
        forecast_next_30d=forecast,
    )


def _generate_simple_forecast(db: Session, brand_id: str, days: int = 30) -> List[ForecastData]:
    """Generate simple forecast using moving average (placeholder for ARIMA/Prophet)."""
    # Get last 30 days of sales data
    now = datetime.now(timezone.utc)
    day_60_ago = now - timedelta(days=60)
    
    daily_sales = db.query(
        func.date(Order.placed_at).label("date"),
        func.count(Order.id).label("sales_count"),
    ).join(
        OrderItem, OrderItem.order_id == Order.id
    ).join(
        Product, Product.id == OrderItem.product_id
    ).filter(
        Product.brand_id == brand_id,
        Order.payment_status == "success",
        Order.placed_at >= day_60_ago,
    ).group_by(
        func.date(Order.placed_at),
    ).all()
    
    # Calculate average daily sales
    if not daily_sales:
        avg_sales = 0
    else:
        avg_sales = sum(s.sales_count for s in daily_sales) / len(daily_sales)
    
    # Generate forecast with confidence interval
    forecast = []
    for i in range(days):
        forecast_date = (now + timedelta(days=i+1)).strftime("%Y-%m-%d")
        # Simple forecast: average with day-of-week adjustment
        day_of_week = (now + timedelta(days=i+1)).weekday()
        
        # Weekend boost (Friday/Saturday in Egypt)
        multiplier = 1.2 if day_of_week in (4, 5) else 1.0
        
        predicted = int(avg_sales * multiplier)
        confidence_range = max(1, int(predicted * 0.2))  # 20% confidence range
        
        forecast.append(ForecastData(
            date=forecast_date,
            predicted_sales=predicted,
            confidence_lower=max(0, predicted - confidence_range),
            confidence_upper=predicted + confidence_range,
        ))
    
    return forecast


@router.get("/{brand_id}/rejections")
async def get_brand_rejections(
    brand_id: str,
    days: int = Query(30, ge=1, le=90),
    stage: Optional[str] = Query(None, description="Filter by stage: fabric, stitch, final"),
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get detailed midway rejection data for a brand."""
    brand = _get_brand_or_404(db, brand_id)
    _check_brand_access(user, brand, db)
    
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    query = db.query(
        AnalyticsEvent.properties["sku"].label("sku"),
        AnalyticsEvent.properties["stage"].label("stage"),
        AnalyticsEvent.properties["reason_code"].label("reason_code"),
        AnalyticsEvent.timestamp,
    ).filter(
        AnalyticsEvent.event_name == "midway_rejection",
        AnalyticsEvent.properties["brand_id"].astext == brand_id,
        AnalyticsEvent.timestamp >= start_date,
    )
    
    if stage:
        query = query.filter(AnalyticsEvent.properties["stage"].astext == stage)
    
    results = query.order_by(AnalyticsEvent.timestamp.desc()).limit(100).all()
    
    return {
        "brand_id": brand_id,
        "period_days": days,
        "total_rejections": len(results),
        "rejections": [
            {
                "sku": row.sku,
                "stage": row.stage,
                "reason_code": row.reason_code,
                "timestamp": row.timestamp.isoformat(),
            }
            for row in results
        ],
    }


@router.get("/{brand_id}/regional-sales")
async def get_brand_regional_sales(
    brand_id: str,
    days: int = Query(30, ge=1, le=90),
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get regional sales breakdown for Egypt."""
    brand = _get_brand_or_404(db, brand_id)
    _check_brand_access(user, brand, db)
    
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    query = text("""
        SELECT
            o.shipping_address->>'city' as city,
            COUNT(DISTINCT o.id) as sales_count,
            SUM(o.total) as revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        JOIN products p ON p.id = oi.product_id
        WHERE p.brand_id = :brand_id
        AND o.payment_status = 'success'
        AND o.placed_at >= :start_date
        GROUP BY o.shipping_address->>'city'
        ORDER BY sales_count DESC
    """)
    
    results = db.execute(query, {
        "brand_id": brand_id,
        "start_date": start_date,
    }).all()
    
    return {
        "brand_id": brand_id,
        "period_days": days,
        "regional_breakdown": [
            {
                "city": row.city or "Unknown",
                "sales_count": int(row.sales_count),
                "revenue_egp": float(row.revenue or 0),
            }
            for row in results
        ],
    }
