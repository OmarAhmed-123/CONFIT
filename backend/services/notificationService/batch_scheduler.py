"""
CONFIT Backend — Batch Notification Scheduler
=============================================
APScheduler-based scheduler for processing batch notifications.
Runs periodically to process due daily digests and weekly summaries.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import APScheduler
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    logger.warning("APScheduler not installed — batch notification scheduler disabled")

_scheduler: Optional['BackgroundScheduler'] = None


def get_scheduler() -> Optional['BackgroundScheduler']:
    """Get or create the background scheduler instance."""
    global _scheduler
    
    if not HAS_APSCHEDULER:
        return None
    
    if _scheduler is None:
        _scheduler = BackgroundScheduler(daemon=True)
    
    return _scheduler


def start_batch_scheduler() -> Optional['BackgroundScheduler']:
    """
    Start the batch notification scheduler.
    Schedules jobs to process due batch notifications.
    
    Jobs:
    - Process due batches every 5 minutes
    - Cleanup old processed items daily at 3 AM UTC
    """
    scheduler = get_scheduler()
    if scheduler is None:
        logger.warning("Batch scheduler not started — APScheduler not available")
        return None

    if scheduler.running:
        logger.info("Batch scheduler already running")
        return scheduler

    # Job: Process due batch notifications every 5 minutes
    scheduler.add_job(
        id='batch_process_due',
        func=process_due_batches_job,
        trigger=IntervalTrigger(minutes=5),
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )

    # Job: Cleanup old processed items daily at 3 AM UTC
    scheduler.add_job(
        id='batch_cleanup_old',
        func=cleanup_old_items_job,
        trigger=CronTrigger(hour=3, minute=0, timezone='UTC'),
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Batch notification scheduler started (process every 5min, cleanup daily at 3AM UTC)")
    
    return scheduler


def stop_batch_scheduler() -> None:
    """Stop the batch notification scheduler."""
    global _scheduler
    
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Batch notification scheduler stopped")


def process_due_batches_job() -> int:
    """
    Job function to process all due batch notifications.
    Called by the scheduler every 5 minutes.
    """
    from database.session import SessionLocal
    from services.notificationService.batch_queue import BatchQueueService
    
    try:
        db = SessionLocal()
        try:
            count = BatchQueueService.process_due_batches(db)
            if count > 0:
                logger.info("Processed %d batch notification groups", count)
            return count
        finally:
            db.close()
    except Exception as e:
        logger.error("Failed to process due batches: %s", e)
        return 0


def cleanup_old_items_job() -> int:
    """
    Job function to cleanup old processed queue items.
    Called by the scheduler daily at 3 AM UTC.
    """
    from database.session import SessionLocal
    from services.notificationService.batch_queue import BatchQueueService
    
    try:
        db = SessionLocal()
        try:
            count = BatchQueueService.cleanup_old_processed_items(db, days=30)
            return count
        finally:
            db.close()
    except Exception as e:
        logger.error("Failed to cleanup old batch items: %s", e)
        return 0


def is_scheduler_running() -> bool:
    """Check if the batch scheduler is running."""
    global _scheduler
    return _scheduler is not None and _scheduler.running


# ── Manual trigger functions (for testing/admin) ─────────────────────────────

def trigger_process_batches() -> int:
    """Manually trigger batch processing (for testing or admin)."""
    return process_due_batches_job()


def trigger_cleanup() -> int:
    """Manually trigger cleanup (for testing or admin)."""
    return cleanup_old_items_job()
