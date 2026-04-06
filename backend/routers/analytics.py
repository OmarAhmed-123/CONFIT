"""
CONFIT Backend — Analytics & Insights Router
============================================
Read-only analytics endpoints aggregating data from the in-memory
catalog and order system to support brand dashboards and internal
reporting.
"""

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func

from controllers.product_controller import ProductController
from routers.orders import get_order_service
from services.auth_service import UserProfile
from utils.auth_deps import require_auth
from database.session import get_db
from sqlalchemy.orm import Session
from models.profile_models import UserBehaviorSignal

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

_product_controller = ProductController()


@router.get("/overview")
async def analytics_overview(user: UserProfile = Depends(require_auth)):
    """
    High-level analytics summarising product performance and return behaviour.

    This endpoint is restricted to authenticated users and is intended to
    back-brand dashboards and internal tools rather than public UI.
    """
    order_service = get_order_service()

    # Aggregate orders and returns
    # In a production system this would be scoped per brand or tenant;
    # here we aggregate across all users for a global view.
    all_orders: List[Dict] = []
    all_returns: List[Dict] = []
    orders_map = getattr(order_service, "_orders", {}) or {}
    returns_map = getattr(order_service, "_returns", {}) or {}
    for orders in orders_map.values():
        all_orders.extend(orders or [])
    for returns in returns_map.values():
        all_returns.extend(returns or [])

    total_orders = len(all_orders)
    total_returns = len(all_returns)
    return_rate = (total_returns / total_orders) * 100 if total_orders else 0.0

    # Build product-level statistics from order line items
    product_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    color_counts: Counter[str] = Counter()

    for order in all_orders:
        for item in order.get("items", []):
            product_id = item.get("productId")
            if not product_id:
                continue
            product_counts[product_id] += item.get("quantity", 1)

    # Enrich with catalog data for categories and colors
    for product_id, count in product_counts.items():
        product = await _product_controller.get_product_by_id(product_id)
        if not product:
            continue
        category = product.get("category")
        if category:
            category_counts[category] += count
        for color in product.get("colors", []):
            color_counts[color] += count

    most_styled_items: List[Dict] = []
    for product_id, count in product_counts.most_common(5):
        product = await _product_controller.get_product_by_id(product_id)
        if not product:
            continue
        most_styled_items.append(
            {
                "productId": product_id,
                "name": product.get("name"),
                "brand": product.get("brand"),
                "category": product.get("category"),
                "orders": count,
            }
        )

    # Simple outfit-to-purchase ratio approximation:
    # Treat each order as originating from at least one styled outfit.
    outfit_to_purchase_ratio = 1.0

    heatmap = {
        "byCategory": [{"category": c, "count": n} for c, n in category_counts.most_common()],
        "byColor": [{"color": c, "count": n} for c, n in color_counts.most_common()],
    }

    return {
        "orders": {
            "total": total_orders,
            "returns": total_returns,
            "returnRate": round(return_rate, 2),
        },
        "mostStyledItems": most_styled_items,
        "outfitToPurchaseRatio": outfit_to_purchase_ratio,
        "userPreferenceHeatmap": heatmap,
    }


@router.get("/metrics")
async def analytics_metrics(
    range: Literal["7d", "30d", "90d"] = Query("30d"),
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Real-time engagement + conversion metrics from `user_behavior_signals`.
    - DAU/MAU computed from distinct users active in the window.
    - Retention (D7): overlap between users active in days [-14,-7) and [-7,0).
    - Conversion: purchases per try-on (fallback to purchases per stylist chat).
    """
    days = 7 if range == "7d" else 30 if range == "30d" else 90
    now = datetime.now(timezone.utc)

    cutoff_d7 = now - timedelta(days=7)
    cutoff_d14 = now - timedelta(days=14)
    cutoff_window = now - timedelta(days=days)

    dau_1d = (
        db.query(func.count(func.distinct(UserBehaviorSignal.user_id)))
        .filter(UserBehaviorSignal.user_id != "system")
        .filter(UserBehaviorSignal.created_at >= now - timedelta(days=1))
        .scalar()
        or 0
    )

    mau = (
        db.query(func.count(func.distinct(UserBehaviorSignal.user_id)))
        .filter(UserBehaviorSignal.user_id != "system")
        .filter(UserBehaviorSignal.created_at >= cutoff_window)
        .scalar()
        or 0
    )

    # D7 retention
    active_prev = (
        db.query(func.count(func.distinct(UserBehaviorSignal.user_id)))
        .filter(UserBehaviorSignal.user_id != "system")
        .filter(UserBehaviorSignal.created_at >= cutoff_d14)
        .filter(UserBehaviorSignal.created_at < cutoff_d7)
        .scalar()
        or 0
    )

    if active_prev > 0:
        prev_sub = (
            db.query(func.distinct(UserBehaviorSignal.user_id))
            .filter(UserBehaviorSignal.user_id != "system")
            .filter(UserBehaviorSignal.created_at >= cutoff_d14)
            .filter(UserBehaviorSignal.created_at < cutoff_d7)
            .subquery()
        )
        retained = (
            db.query(func.count(func.distinct(UserBehaviorSignal.user_id)))
            .filter(UserBehaviorSignal.user_id != "system")
            .filter(UserBehaviorSignal.created_at >= cutoff_d7)
            .filter(UserBehaviorSignal.user_id.in_(prev_sub))
            .scalar()
            or 0
        )
        retention_d7 = retained / active_prev
    else:
        retention_d7 = 0.0

    # Conversion signals
    purchase_types = ["purchase"]
    tryon_types = ["try_on", "tryon_complete", "try_on_save"]
    stylist_types = ["stylist_chat"]

    # Use distinct users to produce a true conversion *rate* (0..1).
    purchase_count = (
        db.query(func.count(func.distinct(UserBehaviorSignal.user_id)))
        .filter(UserBehaviorSignal.user_id != "system")
        .filter(UserBehaviorSignal.signal_type.in_(purchase_types))
        .filter(UserBehaviorSignal.created_at >= cutoff_window)
        .scalar()
        or 0
    )

    tryon_count = (
        db.query(func.count(func.distinct(UserBehaviorSignal.user_id)))
        .filter(UserBehaviorSignal.user_id != "system")
        .filter(UserBehaviorSignal.signal_type.in_(tryon_types))
        .filter(UserBehaviorSignal.created_at >= cutoff_window)
        .scalar()
        or 0
    )

    stylist_count = (
        db.query(func.count(func.distinct(UserBehaviorSignal.user_id)))
        .filter(UserBehaviorSignal.user_id != "system")
        .filter(UserBehaviorSignal.signal_type.in_(stylist_types))
        .filter(UserBehaviorSignal.created_at >= cutoff_window)
        .scalar()
        or 0
    )

    denom = tryon_count if tryon_count > 0 else max(stylist_count, 1)
    conversion_rate = purchase_count / denom if denom > 0 else 0.0

    # Outfit interaction volume
    outfit_signal_types = [
        "outfit_create",
        "outfit_save",
        "outfit_delete",
        "outfit_accepted",
        "outfit_rejected",
        "outfit_shared",
        "outfit_share",
        "share",
    ]
    outfit_interactions = (
        db.query(func.count())
        .filter(UserBehaviorSignal.user_id != "system")
        .filter(UserBehaviorSignal.signal_type.in_(outfit_signal_types))
        .filter(UserBehaviorSignal.created_at >= cutoff_window)
        .scalar()
        or 0
    )

    ai_usage = (
        db.query(func.count())
        .filter(UserBehaviorSignal.user_id != "system")
        .filter(UserBehaviorSignal.signal_type.in_(stylist_types))
        .filter(UserBehaviorSignal.created_at >= cutoff_window)
        .scalar()
        or 0
    )

    # 14-day DAU series for charts
    series_days = 14
    series_start = now - timedelta(days=series_days - 1)
    dau_rows = (
        db.query(
            func.date(UserBehaviorSignal.created_at).label("day"),
            func.count(func.distinct(UserBehaviorSignal.user_id)).label("dau"),
        )
        .filter(UserBehaviorSignal.user_id != "system")
        .filter(UserBehaviorSignal.created_at >= series_start)
        .group_by(func.date(UserBehaviorSignal.created_at))
        .order_by(func.date(UserBehaviorSignal.created_at))
        .all()
    )
    dau_series = [{"date": r.day, "dau": int(r.dau)} for r in dau_rows]

    return {
        "range": range,
        "overview": {
            "dau_1d": int(dau_1d),
            "active_users": int(mau),
            "retention_d7": retention_d7,
            "conversion_rate": float(conversion_rate),
            "outfit_interactions": int(outfit_interactions),
            "ai_usage": int(ai_usage),
        },
        "dau_series": dau_series,
        "window_days": days,
        "purchase_count": int(purchase_count),
        "tryon_count": int(tryon_count),
        "stylist_chat_count": int(stylist_count),
    }

