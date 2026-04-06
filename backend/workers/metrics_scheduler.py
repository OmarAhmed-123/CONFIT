"""
CONFIT Backend — Metrics Aggregation Scheduler
=============================================
Scheduled tasks for batch metric computation and rollups.
Uses APScheduler for cron-like scheduling.
"""

import logging
from datetime import datetime, timezone, timedelta, date
from typing import Optional, List, Dict, Any
from uuid import UUID
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from database.session import SessionLocal
from database.metrics_aggregation_models import (
    HourlyMetric,
    DailyMetric,
    WeeklyMetric,
    MonthlyMetric,
    RealtimeKPICache,
    MetricComputationLog,
    MetricUpdateQueue,
    MetricGranularity,
    MetricStatus,
)
from database.sales_analytics_models import SalesTransaction
from database.models import Store
from services.metrics_aggregation_service import (
    MetricsAggregationService,
    get_metrics_aggregation_service,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# SCHEDULED TASKS
# ═══════════════════════════════════════════════════════════════════

def process_pending_metric_updates():
    """
    Process pending metric updates from the queue.
    
    Runs every 30 seconds to process debounced updates.
    """
    db = SessionLocal()
    try:
        service = get_metrics_aggregation_service(db)
        processed = service.process_pending_updates(batch_size=100)
        
        if processed > 0:
            logger.info(f"Processed {processed} pending metric updates")
        
        return processed
        
    except Exception as e:
        logger.error(f"Failed to process pending updates: {e}")
        return 0
    finally:
        db.close()


def compute_hourly_metrics():
    """
    Compute hourly metrics for all active stores.
    
    Runs 5 minutes after each hour to capture late-arriving transactions.
    Schedule: Every hour at minute 5
    """
    db = SessionLocal()
    try:
        service = get_metrics_aggregation_service(db)
        
        # Get the previous hour
        now = datetime.now(timezone.utc)
        previous_hour = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        
        # Get all active stores
        stores = db.query(Store).filter(Store.is_active == True).all()
        
        computed = 0
        errors = 0
        
        for store in stores:
            try:
                service._compute_hourly_metric(store.id, previous_hour)
                computed += 1
            except Exception as e:
                logger.error(f"Failed to compute hourly metric for store {store.id}: {e}")
                errors += 1
        
        logger.info(f"Hourly metrics computed: {computed} stores, {errors} errors")
        
        return {"computed": computed, "errors": errors}
        
    except Exception as e:
        logger.error(f"Hourly metrics job failed: {e}")
        return {"computed": 0, "errors": 1}
    finally:
        db.close()


def compute_daily_rollups():
    """
    Roll up hourly metrics to daily metrics.
    
    Runs at 00:05 UTC daily.
    """
    db = SessionLocal()
    try:
        service = get_metrics_aggregation_service(db)
        
        # Get yesterday's date
        now = datetime.now(timezone.utc)
        yesterday = (now - timedelta(days=1)).date()
        
        # Get all active stores
        stores = db.query(Store).filter(Store.is_active == True).all()
        
        computed = 0
        errors = 0
        
        for store in stores:
            try:
                service._compute_daily_metric(store.id, yesterday, from_hourly=True)
                computed += 1
            except Exception as e:
                logger.error(f"Failed to compute daily rollup for store {store.id}: {e}")
                errors += 1
        
        logger.info(f"Daily rollups computed: {computed} stores, {errors} errors")
        
        return {"computed": computed, "errors": errors}
        
    except Exception as e:
        logger.error(f"Daily rollup job failed: {e}")
        return {"computed": 0, "errors": 1}
    finally:
        db.close()


def compute_weekly_rollups():
    """
    Roll up daily metrics to weekly metrics.
    
    Runs on Monday at 00:10 UTC.
    """
    db = SessionLocal()
    try:
        service = get_metrics_aggregation_service(db)
        
        # Get previous week's ISO week
        now = datetime.now(timezone.utc)
        last_week = now - timedelta(weeks=1)
        iso_cal = last_week.isocalendar()
        year = iso_cal[0]
        week = iso_cal[1]
        
        # Get all active stores
        stores = db.query(Store).filter(Store.is_active == True).all()
        
        computed = 0
        errors = 0
        
        for store in stores:
            try:
                service._compute_weekly_metric(store.id, year, week)
                computed += 1
            except Exception as e:
                logger.error(f"Failed to compute weekly rollup for store {store.id}: {e}")
                errors += 1
        
        logger.info(f"Weekly rollups computed: {computed} stores, {errors} errors")
        
        return {"computed": computed, "errors": errors}
        
    except Exception as e:
        logger.error(f"Weekly rollup job failed: {e}")
        return {"computed": 0, "errors": 1}
    finally:
        db.close()


def compute_monthly_rollups():
    """
    Roll up daily metrics to monthly metrics.
    
    Runs on the 1st of each month at 00:15 UTC.
    """
    db = SessionLocal()
    try:
        service = get_metrics_aggregation_service(db)
        
        # Get previous month
        now = datetime.now(timezone.utc)
        first_of_this_month = now.replace(day=1)
        last_of_prev_month = first_of_this_month - timedelta(days=1)
        year = last_of_prev_month.year
        month = last_of_prev_month.month
        
        # Get all active stores
        stores = db.query(Store).filter(Store.is_active == True).all()
        
        computed = 0
        errors = 0
        
        for store in stores:
            try:
                service._compute_monthly_metric(store.id, year, month)
                computed += 1
            except Exception as e:
                logger.error(f"Failed to compute monthly rollup for store {store.id}: {e}")
                errors += 1
        
        logger.info(f"Monthly rollups computed: {computed} stores, {errors} errors")
        
        return {"computed": computed, "errors": errors}
        
    except Exception as e:
        logger.error(f"Monthly rollup job failed: {e}")
        return {"computed": 0, "errors": 1}
    finally:
        db.close()


def refresh_realtime_kpis():
    """
    Refresh real-time KPI caches for all active stores.
    
    Runs every 5 minutes to keep real-time cache fresh.
    """
    db = SessionLocal()
    try:
        service = get_metrics_aggregation_service(db)
        
        # Get all active stores
        stores = db.query(Store).filter(Store.is_active == True).all()
        
        refreshed = 0
        errors = 0
        
        for store in stores:
            try:
                service._compute_realtime_kpis(store.id)
                refreshed += 1
            except Exception as e:
                logger.error(f"Failed to refresh realtime KPIs for store {store.id}: {e}")
                errors += 1
        
        if refreshed > 0:
            logger.debug(f"Realtime KPIs refreshed: {refreshed} stores")
        
        return {"refreshed": refreshed, "errors": errors}
        
    except Exception as e:
        logger.error(f"Realtime KPI refresh job failed: {e}")
        return {"refreshed": 0, "errors": 1}
    finally:
        db.close()


def detect_stale_metrics():
    """
    Detect and alert on stale metrics.
    
    Runs every 15 minutes.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        
        # Check hourly metrics (should be updated within 10 minutes of hour end)
        stale_hourly = db.query(HourlyMetric).filter(
            and_(
                HourlyMetric.status == MetricStatus.FRESH,
                HourlyMetric.computed_at < now - timedelta(minutes=15),
                HourlyMetric.hour_key >= now - timedelta(hours=24),
            )
        ).count()
        
        # Check daily metrics (should be updated by 00:10 UTC)
        stale_daily = db.query(DailyMetric).filter(
            and_(
                DailyMetric.status == MetricStatus.FRESH,
                DailyMetric.computed_at < now.replace(hour=0, minute=10, second=0),
                DailyMetric.date_key >= (now - timedelta(days=7)).date(),
            )
        ).count() if now.hour >= 1 else 0
        
        # Mark as stale
        if stale_hourly > 0:
            db.query(HourlyMetric).filter(
                and_(
                    HourlyMetric.status == MetricStatus.FRESH,
                    HourlyMetric.computed_at < now - timedelta(minutes=15),
                    HourlyMetric.hour_key >= now - timedelta(hours=24),
                )
            ).update({"status": MetricStatus.STALE})
        
        if stale_daily > 0:
            db.query(DailyMetric).filter(
                and_(
                    DailyMetric.status == MetricStatus.FRESH,
                    DailyMetric.computed_at < now.replace(hour=0, minute=10, second=0),
                    DailyMetric.date_key >= (now - timedelta(days=7)).date(),
                )
            ).update({"status": MetricStatus.STALE})
        
        db.commit()
        
        if stale_hourly > 0 or stale_daily > 0:
            logger.warning(
                f"Stale metrics detected: {stale_hourly} hourly, {stale_daily} daily"
            )
        
        return {
            "stale_hourly": stale_hourly,
            "stale_daily": stale_daily,
        }
        
    except Exception as e:
        logger.error(f"Stale metrics detection failed: {e}")
        return {"stale_hourly": 0, "stale_daily": 0}
    finally:
        db.close()


def cleanup_old_metrics():
    """
    Clean up old metrics beyond retention period.
    
    Runs daily at 03:00 UTC.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        
        # Delete hourly metrics older than 7 days
        hourly_cutoff = now - timedelta(days=7)
        deleted_hourly = db.query(HourlyMetric).filter(
            HourlyMetric.hour_key < hourly_cutoff
        ).delete()
        
        # Delete daily metrics older than 2 years
        daily_cutoff = now - timedelta(days=730)
        deleted_daily = db.query(DailyMetric).filter(
            DailyMetric.date_key < daily_cutoff.date()
        ).delete()
        
        # Delete weekly metrics older than 3 years
        weekly_cutoff = now - timedelta(days=1095)
        deleted_weekly = db.query(WeeklyMetric).filter(
            WeeklyMetric.week_end_date < weekly_cutoff.date()
        ).delete()
        
        # Delete monthly metrics older than 5 years
        monthly_cutoff = now - timedelta(days=1825)
        deleted_monthly = db.query(MonthlyMetric).filter(
            MonthlyMetric.month_end_date < monthly_cutoff.date()
        ).delete()
        
        # Delete old computation logs (older than 30 days)
        log_cutoff = now - timedelta(days=30)
        deleted_logs = db.query(MetricComputationLog).filter(
            MetricComputationLog.computed_at < log_cutoff
        ).delete()
        
        # Delete processed queue items older than 7 days
        queue_cutoff = now - timedelta(days=7)
        deleted_queue = db.query(MetricUpdateQueue).filter(
            and_(
                MetricUpdateQueue.status.in_(["completed", "failed"]),
                MetricUpdateQueue.processed_at < queue_cutoff,
            )
        ).delete()
        
        db.commit()
        
        logger.info(
            f"Cleanup completed: {deleted_hourly} hourly, {deleted_daily} daily, "
            f"{deleted_weekly} weekly, {deleted_monthly} monthly, "
            f"{deleted_logs} logs, {deleted_queue} queue items"
        )
        
        return {
            "deleted_hourly": deleted_hourly,
            "deleted_daily": deleted_daily,
            "deleted_weekly": deleted_weekly,
            "deleted_monthly": deleted_monthly,
            "deleted_logs": deleted_logs,
            "deleted_queue": deleted_queue,
        }
        
    except Exception as e:
        logger.error(f"Metrics cleanup failed: {e}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


def verify_metric_consistency():
    """
    Verify that rolled-up metrics match raw calculations.
    
    Runs daily at 04:00 UTC for previous day's metrics.
    """
    db = SessionLocal()
    try:
        service = get_metrics_aggregation_service(db)
        
        # Get yesterday's date
        now = datetime.now(timezone.utc)
        yesterday = (now - timedelta(days=1)).date()
        
        # Get all active stores
        stores = db.query(Store).filter(Store.is_active == True).all()
        
        verified = 0
        discrepancies = 0
        
        for store in stores:
            try:
                # Get daily metric
                daily = db.query(DailyMetric).filter(
                    and_(
                        DailyMetric.store_id == store.id,
                        DailyMetric.date_key == yesterday,
                    )
                ).first()
                
                if not daily:
                    continue
                
                # Get hourly metrics for same day
                hourly = db.query(HourlyMetric).filter(
                    and_(
                        HourlyMetric.store_id == store.id,
                        HourlyMetric.date_key == yesterday,
                    )
                ).all()
                
                if not hourly:
                    continue
                
                # Compare revenue
                hourly_revenue = sum(float(h.total_revenue) for h in hourly)
                daily_revenue = float(daily.total_revenue)
                
                discrepancy = abs(hourly_revenue - daily_revenue)
                if discrepancy > 0.01:  # Allow for rounding
                    logger.warning(
                        f"Metric discrepancy for store {store.id} on {yesterday}: "
                        f"hourly={hourly_revenue}, daily={daily_revenue}, "
                        f"diff={discrepancy}"
                    )
                    discrepancies += 1
                    
                    # Trigger recalculation
                    service._compute_daily_metric(store.id, yesterday, from_hourly=False)
                else:
                    verified += 1
                    
            except Exception as e:
                logger.error(f"Consistency check failed for store {store.id}: {e}")
        
        logger.info(
            f"Consistency check completed: {verified} verified, {discrepancies} discrepancies"
        )
        
        return {"verified": verified, "discrepancies": discrepancies}
        
    except Exception as e:
        logger.error(f"Metric consistency verification failed: {e}")
        return {"verified": 0, "discrepancies": 0}
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════
# SCHEDULER SETUP
# ═══════════════════════════════════════════════════════════════════

def setup_metrics_scheduler(scheduler):
    """
    Set up scheduled tasks for metrics aggregation.
    
    Args:
        scheduler: APScheduler instance
    """
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    
    # Process pending updates every 30 seconds
    scheduler.add_job(
        process_pending_metric_updates,
        trigger=IntervalTrigger(seconds=30),
        id="process_pending_metrics",
        name="Process pending metric updates",
        replace_existing=True,
    )
    
    # Compute hourly metrics at minute 5 of each hour
    scheduler.add_job(
        compute_hourly_metrics,
        trigger=CronTrigger(minute=5),
        id="compute_hourly_metrics",
        name="Compute hourly metrics",
        replace_existing=True,
    )
    
    # Daily rollup at 00:05 UTC
    scheduler.add_job(
        compute_daily_rollups,
        trigger=CronTrigger(hour=0, minute=5),
        id="compute_daily_rollups",
        name="Compute daily rollups",
        replace_existing=True,
    )
    
    # Weekly rollup on Monday at 00:10 UTC
    scheduler.add_job(
        compute_weekly_rollups,
        trigger=CronTrigger(day_of_week="mon", hour=0, minute=10),
        id="compute_weekly_rollups",
        name="Compute weekly rollups",
        replace_existing=True,
    )
    
    # Monthly rollup on 1st at 00:15 UTC
    scheduler.add_job(
        compute_monthly_rollups,
        trigger=CronTrigger(day=1, hour=0, minute=15),
        id="compute_monthly_rollups",
        name="Compute monthly rollups",
        replace_existing=True,
    )
    
    # Refresh realtime KPIs every 5 minutes
    scheduler.add_job(
        refresh_realtime_kpis,
        trigger=IntervalTrigger(minutes=5),
        id="refresh_realtime_kpis",
        name="Refresh realtime KPIs",
        replace_existing=True,
    )
    
    # Detect stale metrics every 15 minutes
    scheduler.add_job(
        detect_stale_metrics,
        trigger=IntervalTrigger(minutes=15),
        id="detect_stale_metrics",
        name="Detect stale metrics",
        replace_existing=True,
    )
    
    # Cleanup old metrics daily at 03:00 UTC
    scheduler.add_job(
        cleanup_old_metrics,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_old_metrics",
        name="Cleanup old metrics",
        replace_existing=True,
    )
    
    # Verify consistency daily at 04:00 UTC
    scheduler.add_job(
        verify_metric_consistency,
        trigger=CronTrigger(hour=4, minute=0),
        id="verify_metric_consistency",
        name="Verify metric consistency",
        replace_existing=True,
    )
    
    logger.info("Metrics aggregation scheduler configured")


# ═══════════════════════════════════════════════════════════════════
# EVENT TRIGGERS (for streaming updates)
# ═══════════════════════════════════════════════════════════════════

def on_transaction_created(transaction: SalesTransaction):
    """
    Called when a new sales transaction is created.
    Triggers incremental metric updates.
    """
    db = SessionLocal()
    try:
        service = get_metrics_aggregation_service(db)
        service.update_metrics_for_transaction(transaction, event_type="sale_created")
        logger.debug(f"Metrics updated for new transaction {transaction.id}")
    except Exception as e:
        logger.error(f"Failed to update metrics for transaction {transaction.id}: {e}")
    finally:
        db.close()


def on_transaction_returned(transaction: SalesTransaction):
    """
    Called when a transaction return is processed.
    Triggers metric updates for return metrics.
    """
    db = SessionLocal()
    try:
        service = get_metrics_aggregation_service(db)
        service.update_metrics_for_transaction(transaction, event_type="return_processed")
        logger.debug(f"Metrics updated for returned transaction {transaction.id}")
    except Exception as e:
        logger.error(f"Failed to update metrics for return {transaction.id}: {e}")
    finally:
        db.close()


def on_transaction_modified(
    transaction: SalesTransaction, 
    old_values: Dict[str, Any]
):
    """
    Called when a transaction is modified.
    Triggers metric recalculation if relevant fields changed.
    """
    # Check if relevant fields changed
    relevant_fields = {'price', 'quantity', 'profit_margin', 'return_status', 'sale_date'}
    changed_fields = set(old_values.keys()) & relevant_fields
    
    if not changed_fields:
        return
    
    db = SessionLocal()
    try:
        service = get_metrics_aggregation_service(db)
        
        # If sale_date changed, need to update metrics for both old and new periods
        if 'sale_date' in changed_fields:
            old_date = old_values['sale_date']
            new_date = transaction.sale_date
            
            # Mark old period as stale
            service._mark_downstream_stale(transaction.store_id, old_date)
            
            # Mark new period as stale
            service._mark_downstream_stale(transaction.store_id, new_date)
        else:
            # Just mark current period as stale
            service._mark_downstream_stale(transaction.store_id, transaction.sale_date)
        
        # Update realtime KPIs
        service._update_realtime_kpis(transaction, "sale_modified")
        
        logger.debug(f"Metrics marked stale for modified transaction {transaction.id}")
        
    except Exception as e:
        logger.error(f"Failed to update metrics for modified transaction {transaction.id}: {e}")
    finally:
        db.close()
