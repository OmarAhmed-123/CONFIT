"""
CONFIT Analytics Celery Tasks
=============================
Background tasks for analytics event processing and aggregation.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from celery import shared_task
from pydantic import BaseModel
from sqlalchemy import text, func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Event Persistence Task
# -----------------------------------------------------------------------------

@shared_task(
    name="workers.analytics_tasks.persist_event",
    queue="analytics",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def persist_event(
    self,
    event_name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    store_id: Optional[str] = None,
    product_id: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None,
    device: Optional[str] = None,
    country: Optional[str] = None,
) -> bool:
    """
    Persist an analytics event to the database.
    
    This task is called by AnalyticsService.track() for async non-blocking writes.
    """
    from database.session import SessionLocal
    
    properties = properties or {}
    
    try:
        db = SessionLocal()
        try:
            # Parse timestamp
            event_timestamp = datetime.fromisoformat(timestamp) if timestamp else datetime.now(timezone.utc)
            
            query = text("""
                INSERT INTO analytics_events (
                    id, event_name, user_id, session_id, store_id, product_id,
                    properties, timestamp, device, country
                ) VALUES (
                    :id, :event_name, :user_id, :session_id, :store_id, :product_id,
                    :properties, :timestamp, :device, :country
                )
            """)
            
            import uuid
            db.execute(query, {
                "id": str(uuid.uuid4()),
                "event_name": event_name,
                "user_id": user_id,
                "session_id": session_id,
                "store_id": store_id,
                "product_id": product_id,
                "properties": properties,
                "timestamp": event_timestamp,
                "device": device,
                "country": country,
            })
            db.commit()
            return True
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to persist analytics event: {e}")
        raise self.retry(exc=e)


# -----------------------------------------------------------------------------
# Mixpanel Forwarding Task
# -----------------------------------------------------------------------------

@shared_task(
    name="workers.analytics_tasks.send_to_mixpanel",
    queue="analytics",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def send_to_mixpanel(
    self,
    token: str,
    event_name: str,
    distinct_id: str,
    properties: Dict[str, Any],
    timestamp: Optional[str] = None,
) -> bool:
    """
    Send event to Mixpanel for external analytics.
    
    PII is minimized - user_id is hashed, no email/phone sent.
    """
    try:
        import requests
        
        event_timestamp = datetime.fromisoformat(timestamp) if timestamp else datetime.now(timezone.utc)
        
        payload = {
            "token": token,
            "event": event_name,
            "properties": {
                "distinct_id": distinct_id,
                "time": int(event_timestamp.timestamp()),
                **properties,
            },
        }
        
        response = requests.post(
            "https://api.mixpanel.com/track",
            json=[payload],
            timeout=10,
        )
        
        if response.status_code != 200:
            logger.warning(f"Mixpanel returned {response.status_code}: {response.text}")
        
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to send to Mixpanel: {e}")
        raise self.retry(exc=e)


# -----------------------------------------------------------------------------
# Nightly Aggregation Tasks
# -----------------------------------------------------------------------------

@shared_task(
    name="workers.analytics_tasks.aggregate_daily_summaries",
    queue="analytics",
    bind=True,
)
def aggregate_daily_summaries(self, target_date: Optional[str] = None) -> Dict[str, int]:
    """
    Aggregate raw analytics events into daily summary tables.
    
    This task runs nightly at 2am Cairo time.
    
    Args:
        target_date: ISO date string (YYYY-MM-DD), defaults to yesterday
        
    Returns:
        Dict with counts of aggregated records
    """
    from database.session import SessionLocal
    
    # Calculate target date (yesterday by default)
    if target_date:
        date = datetime.strptime(target_date, "%Y-%m-%d").date()
    else:
        # Use Cairo timezone for date calculation
        cairo_tz = timezone(timedelta(hours=2))  # Africa/Cairo is UTC+2
        now_cairo = datetime.now(cairo_tz)
        date = (now_cairo - timedelta(days=1)).date()
    
    logger.info(f"Starting daily aggregation for {date}")
    
    results = {
        "store_summaries": 0,
        "brand_summaries": 0,
        "user_summaries": 0,
    }
    
    try:
        db = SessionLocal()
        try:
            # Aggregate store summaries
            results["store_summaries"] = _aggregate_store_summaries(db, date)
            
            # Aggregate brand summaries
            results["brand_summaries"] = _aggregate_brand_summaries(db, date)
            
            # Aggregate user summaries
            results["user_summaries"] = _aggregate_user_summaries(db, date)
            
            db.commit()
            logger.info(f"Completed daily aggregation for {date}: {results}")
            return results
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed daily aggregation for {date}: {e}")
        raise


def _aggregate_store_summaries(db: Session, date) -> int:
    """Aggregate store-level metrics for a given date."""
    start_ts = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_ts = start_ts + timedelta(days=1)
    
    # Get stores with activity
    stores_query = text("""
        SELECT DISTINCT store_id
        FROM analytics_events
        WHERE store_id IS NOT NULL
        AND timestamp >= :start_ts
        AND timestamp < :end_ts
    """)
    
    stores = db.execute(stores_query, {"start_ts": start_ts, "end_ts": end_ts}).all()
    count = 0
    
    for (store_id,) in stores:
        # Calculate metrics
        visitors = db.execute(text("""
            SELECT COUNT(DISTINCT user_id) as visitors
            FROM analytics_events
            WHERE store_id = :store_id
            AND event_name = 'store_visited'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"store_id": store_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        purchases = db.execute(text("""
            SELECT COUNT(DISTINCT properties->>'order_id') as purchases
            FROM analytics_events
            WHERE store_id = :store_id
            AND event_name = 'order_placed'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"store_id": store_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        try_on = db.execute(text("""
            SELECT COUNT(DISTINCT session_id) as try_on
            FROM analytics_events
            WHERE store_id = :store_id
            AND event_name = 'try_on_completed'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"store_id": store_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        try_on_to_purchase = db.execute(text("""
            SELECT COUNT(DISTINCT session_id) as converted
            FROM analytics_events
            WHERE store_id = :store_id
            AND event_name = 'try_on_added_to_bag'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"store_id": store_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        # Get revenue from orders
        revenue = db.execute(text("""
            SELECT COALESCE(SUM(total), 0) as revenue
            FROM orders
            WHERE pickup_store_id = :store_id
            AND payment_status = 'success'
            AND placed_at >= :start_ts
            AND placed_at < :end_ts
        """), {"store_id": store_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        # Get returns
        returns = db.execute(text("""
            SELECT COUNT(*) as returns
            FROM return_requests rr
            JOIN orders o ON o.id = rr.order_id
            WHERE o.pickup_store_id = :store_id
            AND rr.requested_at >= :start_ts
            AND rr.requested_at < :end_ts
        """), {"store_id": store_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        # Get coupon metrics
        coupon_redemptions = db.execute(text("""
            SELECT COUNT(*) as redemptions
            FROM analytics_events
            WHERE store_id = :store_id
            AND event_name = 'coupon_redeemed'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"store_id": store_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        donor_coupon_egp = db.execute(text("""
            SELECT COALESCE(SUM((properties->>'amount_egp')::numeric), 0) as donor_total
            FROM analytics_events
            WHERE store_id = :store_id
            AND event_name = 'donor_coupon_redeemed'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"store_id": store_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        # Get top SKUs
        top_skus = db.execute(text("""
            SELECT properties->>'sku' as sku, COUNT(*) as views
            FROM analytics_events
            WHERE store_id = :store_id
            AND event_name = 'product_viewed'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
            GROUP BY properties->>'sku'
            ORDER BY views DESC
            LIMIT 10
        """), {"store_id": store_id, "start_ts": start_ts, "end_ts": end_ts}).all()
        
        top_skus_list = [{"sku": row[0], "views": row[1]} for row in top_skus if row[0]]
        
        # Insert or update summary
        import uuid
        db.execute(text("""
            INSERT INTO daily_store_summary (
                id, store_id, summary_date, visitors_count, purchases_count,
                try_on_count, try_on_to_purchase, revenue_egp, returns_count,
                coupon_redemptions, donor_coupon_egp, top_skus
            ) VALUES (
                :id, :store_id, :summary_date, :visitors, :purchases,
                :try_on, :try_on_to_purchase, :revenue, :returns,
                :coupon_redemptions, :donor_coupon_egp, :top_skus
            )
            ON CONFLICT (store_id, summary_date) DO UPDATE SET
                visitors_count = EXCLUDED.visitors_count,
                purchases_count = EXCLUDED.purchases_count,
                try_on_count = EXCLUDED.try_on_count,
                try_on_to_purchase = EXCLUDED.try_on_to_purchase,
                revenue_egp = EXCLUDED.revenue_egp,
                returns_count = EXCLUDED.returns_count,
                coupon_redemptions = EXCLUDED.coupon_redemptions,
                donor_coupon_egp = EXCLUDED.donor_coupon_egp,
                top_skus = EXCLUDED.top_skus
        """), {
            "id": str(uuid.uuid4()),
            "store_id": store_id,
            "summary_date": start_ts,
            "visitors": int(visitors),
            "purchases": int(purchases),
            "try_on": int(try_on),
            "try_on_to_purchase": int(try_on_to_purchase),
            "revenue": float(revenue),
            "returns": int(returns),
            "coupon_redemptions": int(coupon_redemptions),
            "donor_coupon_egp": float(donor_coupon_egp),
            "top_skus": top_skus_list,
        })
        
        count += 1
    
    return count


def _aggregate_brand_summaries(db: Session, date) -> int:
    """Aggregate brand-level metrics for a given date."""
    start_ts = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_ts = start_ts + timedelta(days=1)
    
    # Get brands with activity
    brands_query = text("""
        SELECT DISTINCT properties->>'brand_id' as brand_id
        FROM analytics_events
        WHERE properties->>'brand_id' IS NOT NULL
        AND timestamp >= :start_ts
        AND timestamp < :end_ts
    """)
    
    brands = db.execute(brands_query, {"start_ts": start_ts, "end_ts": end_ts}).all()
    count = 0
    
    for (brand_id,) in brands:
        if not brand_id:
            continue
        
        # Calculate metrics
        products_sold = db.execute(text("""
            SELECT COUNT(*) as sold
            FROM analytics_events
            WHERE properties->>'brand_id' = :brand_id
            AND event_name = 'order_placed'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"brand_id": brand_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        revenue = db.execute(text("""
            SELECT COALESCE(SUM((properties->>'total_egp')::numeric), 0) as revenue
            FROM analytics_events
            WHERE properties->>'brand_id' = :brand_id
            AND event_name = 'order_placed'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"brand_id": brand_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        midway_rejections = db.execute(text("""
            SELECT COUNT(*) as rejections
            FROM analytics_events
            WHERE properties->>'brand_id' = :brand_id
            AND event_name = 'midway_rejection'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"brand_id": brand_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        outfit_appearances = db.execute(text("""
            SELECT COUNT(*) as appearances
            FROM analytics_events
            WHERE properties->>'brand_id' = :brand_id
            AND event_name = 'outfit_saved'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"brand_id": brand_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        outfit_purchases = db.execute(text("""
            SELECT COUNT(*) as purchases
            FROM analytics_events
            WHERE properties->>'brand_id' = :brand_id
            AND event_name = 'order_placed'
            AND properties->>'from_outfit' = 'true'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"brand_id": brand_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        returns = db.execute(text("""
            SELECT COUNT(*) as returns
            FROM analytics_events
            WHERE properties->>'brand_id' = :brand_id
            AND event_name = 'order_returned'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"brand_id": brand_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        # Insert or update summary
        import uuid
        db.execute(text("""
            INSERT INTO daily_brand_summary (
                id, brand_id, summary_date, products_sold, revenue_egp,
                midway_rejections, outfit_appearances, outfit_purchases, returns_count
            ) VALUES (
                :id, :brand_id, :summary_date, :products_sold, :revenue,
                :midway_rejections, :outfit_appearances, :outfit_purchases, :returns
            )
            ON CONFLICT (brand_id, summary_date) DO UPDATE SET
                products_sold = EXCLUDED.products_sold,
                revenue_egp = EXCLUDED.revenue_egp,
                midway_rejections = EXCLUDED.midway_rejections,
                outfit_appearances = EXCLUDED.outfit_appearances,
                outfit_purchases = EXCLUDED.outfit_purchases,
                returns_count = EXCLUDED.returns_count
        """), {
            "id": str(uuid.uuid4()),
            "brand_id": brand_id,
            "summary_date": start_ts,
            "products_sold": int(products_sold),
            "revenue": float(revenue),
            "midway_rejections": int(midway_rejections),
            "outfit_appearances": int(outfit_appearances),
            "outfit_purchases": int(outfit_purchases),
            "returns": int(returns),
        })
        
        count += 1
    
    return count


def _aggregate_user_summaries(db: Session, date) -> int:
    """Aggregate user-level metrics for a given date."""
    start_ts = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_ts = start_ts + timedelta(days=1)
    
    # Get users with activity
    users_query = text("""
        SELECT DISTINCT user_id
        FROM analytics_events
        WHERE user_id IS NOT NULL
        AND timestamp >= :start_ts
        AND timestamp < :end_ts
    """)
    
    users = db.execute(users_query, {"start_ts": start_ts, "end_ts": end_ts}).all()
    count = 0
    
    for (user_id,) in users:
        # Calculate metrics
        outfits_saved = db.execute(text("""
            SELECT COUNT(*) as saved
            FROM analytics_events
            WHERE user_id = :user_id
            AND event_name = 'outfit_saved'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"user_id": user_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        try_on_sessions = db.execute(text("""
            SELECT COUNT(DISTINCT session_id) as sessions
            FROM analytics_events
            WHERE user_id = :user_id
            AND event_name = 'try_on_completed'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"user_id": user_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        coupons_used = db.execute(text("""
            SELECT COUNT(*) as used
            FROM analytics_events
            WHERE user_id = :user_id
            AND event_name = 'coupon_redeemed'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"user_id": user_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        coupon_savings = db.execute(text("""
            SELECT COALESCE(SUM((properties->>'discount_egp')::numeric), 0) as savings
            FROM analytics_events
            WHERE user_id = :user_id
            AND event_name = 'coupon_applied'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"user_id": user_id, "start_ts": start_ts, "end_ts": end_ts}).scalar() or 0
        
        stores_visited = db.execute(text("""
            SELECT DISTINCT store_id
            FROM analytics_events
            WHERE user_id = :user_id
            AND event_name = 'store_visited'
            AND timestamp >= :start_ts
            AND timestamp < :end_ts
        """), {"user_id": user_id, "start_ts": start_ts, "end_ts": end_ts}).all()
        
        stores_list = [str(row[0]) for row in stores_visited if row[0]]
        
        # Insert or update summary
        import uuid
        db.execute(text("""
            INSERT INTO daily_user_summary (
                id, user_id, summary_date, outfits_saved, try_on_sessions,
                coupons_used, coupon_savings_egp, stores_visited
            ) VALUES (
                :id, :user_id, :summary_date, :outfits_saved, :try_on_sessions,
                :coupons_used, :coupon_savings, :stores_visited
            )
            ON CONFLICT (user_id, summary_date) DO UPDATE SET
                outfits_saved = EXCLUDED.outfits_saved,
                try_on_sessions = EXCLUDED.try_on_sessions,
                coupons_used = EXCLUDED.coupons_used,
                coupon_savings_egp = EXCLUDED.coupon_savings_egp,
                stores_visited = EXCLUDED.stores_visited
        """), {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "summary_date": start_ts,
            "outfits_saved": int(outfits_saved),
            "try_on_sessions": int(try_on_sessions),
            "coupons_used": int(coupons_used),
            "coupon_savings": float(coupon_savings),
            "stores_visited": stores_list,
        })
        
        count += 1
    
    return count


@shared_task(
    name="workers.analytics_tasks.archive_old_events",
    queue="analytics",
)
def archive_old_events(days: int = 180) -> Dict[str, int]:
    """
    Archive analytics events older than specified days to cold storage.
    
    In production, this would export to S3/GCS and delete from Postgres.
    For now, it just logs the count.
    
    Args:
        days: Archive events older than this many days (default 180)
        
    Returns:
        Dict with archived event count
    """
    from database.session import SessionLocal
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    try:
        db = SessionLocal()
        try:
            # Count events to archive
            count = db.execute(text("""
                SELECT COUNT(*) FROM analytics_events
                WHERE timestamp < :cutoff
            """), {"cutoff": cutoff_date}).scalar() or 0
            
            logger.info(f"Would archive {count} events older than {cutoff_date}")
            
            # In production:
            # 1. Export to S3 as Parquet/CSV
            # 2. Delete from Postgres
            # 3. Update archive manifest
            
            return {"archived_count": count}
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to archive old events: {e}")
        return {"archived_count": 0, "error": str(e)}


# -----------------------------------------------------------------------------
# Scheduled Task Registration
# -----------------------------------------------------------------------------

def register_scheduled_tasks():
    """
    Register scheduled tasks with Celery beat.
    
    Call this from celery_app.py to set up the nightly aggregation.
    """
    from workers.celery_app import celery_app
    from celery.schedules import crontab
    
    # Schedule nightly aggregation at 2am Cairo time (UTC+2)
    # 2am Cairo = 0:00 UTC (standard time) or 23:00 UTC previous day (daylight saving)
    # Using 0:00 UTC as a reasonable approximation
    celery_app.conf.beat_schedule["analytics-daily-aggregation"] = {
        "task": "workers.analytics_tasks.aggregate_daily_summaries",
        "schedule": crontab(hour=0, minute=0),  # Midnight UTC = ~2am Cairo
        "args": (),
    }
    
    # Weekly archive task (Sundays at 3am UTC)
    celery_app.conf.beat_schedule["analytics-weekly-archive"] = {
        "task": "workers.analytics_tasks.archive_old_events",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),
        "args": (180,),
    }
