"""
Sales Analytics Materialized View Scheduler
==========================================
Periodically refreshes expensive sales analytics materialized views.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy import text

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False

_scheduler: Optional["BackgroundScheduler"] = None


def _is_enabled() -> bool:
    return os.getenv("SALES_MV_REFRESH_ENABLED", "true").strip().lower() in ("1", "true", "yes")


def _refresh_interval_minutes() -> int:
    raw = os.getenv("SALES_MV_REFRESH_INTERVAL_MINUTES", "5").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 5
    return max(1, min(5, value))


def _refresh_materialized_views() -> int:
    """
    Refreshes materialized views concurrently.
    Returns number of successfully refreshed views.
    """
    from database.session import SessionLocal

    views = [
        "mv_sales_daily_store_category",
        "mv_sales_monthly_store_segment",
        "mv_sales_monthly_store_segment_category",
    ]

    db = SessionLocal()
    refreshed = 0
    try:
        bind = db.get_bind()
        if bind is None or bind.dialect.name != "postgresql":
            return 0

        for view_name in views:
            try:
                db.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}"))
                db.commit()
                refreshed += 1
            except Exception as exc:
                db.rollback()
                logger.warning("Failed refreshing MV %s: %s", view_name, exc)
        if refreshed > 0:
            logger.info("Refreshed %s sales materialized views", refreshed)
        return refreshed
    finally:
        db.close()


def start_sales_mv_scheduler() -> Optional["BackgroundScheduler"]:
    global _scheduler
    if not HAS_APSCHEDULER:
        logger.warning("APScheduler not installed — sales MV scheduler disabled")
        return None
    if not _is_enabled():
        logger.info("Sales MV scheduler disabled by env")
        return None

    if _scheduler is None:
        _scheduler = BackgroundScheduler(daemon=True)
    if _scheduler.running:
        return _scheduler

    interval = _refresh_interval_minutes()
    _scheduler.add_job(
        id="refresh_sales_materialized_views",
        func=_refresh_materialized_views,
        trigger=IntervalTrigger(minutes=interval),
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Sales MV scheduler started (interval=%s minutes)", interval)
    return _scheduler


def stop_sales_mv_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Sales MV scheduler stopped")
