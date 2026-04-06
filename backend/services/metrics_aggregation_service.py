"""
CONFIT Backend — Metrics Aggregation Service
============================================
Service for computing and managing pre-aggregated metrics.
Implements hybrid streaming + batch aggregation pipeline.
"""

import logging
import hashlib
import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from uuid import UUID
from enum import Enum
import asyncio
from dataclasses import dataclass, field

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, text, select, update
from sqlalchemy.dialects.postgresql import insert

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
from database.sales_analytics_models import (
    SalesTransaction,
    SalesCategory,
    CustomerSegment,
    ReturnStatus,
)
from database.models import Store

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

# Cache TTLs (seconds)
CACHE_TTL_REALTIME = 30
CACHE_TTL_HOURLY = 300  # 5 minutes
CACHE_TTL_DAILY = 3600  # 1 hour
CACHE_TTL_WEEKLY = 21600  # 6 hours
CACHE_TTL_MONTHLY = 21600  # 6 hours

# Debounce window for batching updates
DEBOUNCE_WINDOW_SECONDS = 30

# Staleness thresholds
STALE_THRESHOLD_HOURLY = timedelta(minutes=10)
STALE_THRESHOLD_DAILY = timedelta(hours=2)
STALE_THRESHOLD_WEEKLY = timedelta(hours=12)
STALE_THRESHOLD_MONTHLY = timedelta(hours=24)


# ═══════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════

@dataclass
class MetricDelta:
    """Delta values for incremental metric updates."""
    revenue: Decimal = Decimal("0.00")
    transactions: int = 0
    units: int = 0
    profit: Decimal = Decimal("0.00")
    returns: int = 0
    return_amount: Decimal = Decimal("0.00")
    new_customers: int = 0
    returning_customers: int = 0
    vip_customers: int = 0
    transaction_ids: List[str] = field(default_factory=list)


@dataclass
class DateRange:
    """Date range for metric queries."""
    start: datetime
    end: datetime
    
    def hash(self) -> str:
        """Generate hash for cache key."""
        data = f"{self.start.isoformat()}:{self.end.isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()[:12]


# ═══════════════════════════════════════════════════════════════════
# METRICS AGGREGATION SERVICE
# ═══════════════════════════════════════════════════════════════════

class MetricsAggregationService:
    """
    Service for computing and managing pre-aggregated metrics.
    
    Implements:
    - Streaming updates for real-time KPIs
    - Incremental updates for hourly metrics
    - Batch rollups for daily/weekly/monthly metrics
    - Fallback computation from raw transactions
    """
    
    def __init__(self, db: Session):
        self._db = db
        self._pending_updates: Dict[str, MetricDelta] = {}
    
    # ─── Real-time KPI Methods ───────────────────────────────────────
    
    def get_realtime_kpis(
        self, 
        store_id: UUID,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Get real-time KPIs for dashboard header.
        
        Returns today's, this week's, this month's metrics.
        TTL: 30 seconds
        """
        cache = self._db.scalar(
            select(RealtimeKPICache).where(
                RealtimeKPICache.store_id == store_id
            )
        )
        
        if cache:
            staleness = (datetime.now(timezone.utc) - cache.computed_at).total_seconds()
            
            # If cache is fresh enough, return it
            if use_cache and staleness < CACHE_TTL_REALTIME:
                result = cache.to_dict()
                result["cached"] = True
                return result
            
            # If stale but within acceptable range, serve with warning
            if use_cache and staleness < 300:  # 5 minutes max staleness
                result = cache.to_dict()
                result["cached"] = True
                result["staleness_warning"] = {
                    "is_stale": True,
                    "age_seconds": staleness,
                }
                return result
        
        # Compute fresh KPIs
        return self._compute_realtime_kpis(store_id)
    
    def _compute_realtime_kpis(self, store_id: UUID) -> Dict[str, Any]:
        """Compute real-time KPIs from raw transactions."""
        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Single query for all metrics
        query = select(
            # Today
            func.count().filter(SalesTransaction.sale_date >= today).label("today_transactions"),
            func.sum(SalesTransaction.price * SalesTransaction.quantity).filter(
                SalesTransaction.sale_date >= today
            ).label("today_revenue"),
            func.sum(SalesTransaction.quantity).filter(
                SalesTransaction.sale_date >= today
            ).label("today_units"),
            func.count().filter(
                SalesTransaction.sale_date >= today,
                SalesTransaction.customer_segment == CustomerSegment.NEW_CUSTOMER
            ).label("today_new_customers"),
            
            # This week
            func.count().filter(SalesTransaction.sale_date >= week_start).label("week_transactions"),
            func.sum(SalesTransaction.price * SalesTransaction.quantity).filter(
                SalesTransaction.sale_date >= week_start
            ).label("week_revenue"),
            
            # This month
            func.count().filter(SalesTransaction.sale_date >= month_start).label("month_transactions"),
            func.sum(SalesTransaction.price * SalesTransaction.quantity).filter(
                SalesTransaction.sale_date >= month_start
            ).label("month_revenue"),
            
            # 30-day stats
            func.avg(SalesTransaction.profit_margin).filter(
                SalesTransaction.sale_date >= today - timedelta(days=30)
            ).label("avg_margin_30d"),
            
            # Return rate (30 days)
            func.count().filter(
                SalesTransaction.sale_date >= today - timedelta(days=30),
                SalesTransaction.return_status == ReturnStatus.RETURNED
            ).label("returns_30d"),
            func.count().filter(
                SalesTransaction.sale_date >= today - timedelta(days=30)
            ).label("total_30d"),
            
        ).where(
            and_(
                SalesTransaction.store_id == store_id,
                SalesTransaction.deleted_at.is_(None),
                SalesTransaction.is_active == True,
            )
        )
        
        result = self._db.execute(query).first()
        
        total_30d = result.total_30d or 1
        return_rate_30d = (result.returns_30d or 0) / total_30d * 100 if total_30d > 0 else 0
        
        # Get comparison values
        yesterday = today - timedelta(days=1)
        last_week_start = week_start - timedelta(weeks=1)
        last_month_start = month_start.replace(day=1) - timedelta(days=1)
        last_month_start = last_month_start.replace(day=1)
        
        comparisons = self._get_comparison_values(
            store_id, yesterday, last_week_start, last_month_start
        )
        
        # Update or create cache
        cache = self._db.scalar(
            select(RealtimeKPICache).where(RealtimeKPICache.store_id == store_id)
        )
        
        if cache:
            cache.today_revenue = result.today_revenue or Decimal("0.00")
            cache.today_transactions = result.today_transactions or 0
            cache.today_units_sold = result.today_units or 0
            cache.today_new_customers = result.today_new_customers or 0
            cache.week_revenue = result.week_revenue or Decimal("0.00")
            cache.week_transactions = result.week_transactions or 0
            cache.month_revenue = result.month_revenue or Decimal("0.00")
            cache.month_transactions = result.month_transactions or 0
            cache.avg_margin_30d = result.avg_margin_30d
            cache.return_rate_30d = Decimal(str(round(return_rate_30d, 2)))
            cache.yesterday_revenue = comparisons.get("yesterday")
            cache.last_week_revenue = comparisons.get("last_week")
            cache.last_month_revenue = comparisons.get("last_month")
            cache.computed_at = now
            cache.version += 1
        else:
            cache = RealtimeKPICache(
                store_id=store_id,
                today_revenue=result.today_revenue or Decimal("0.00"),
                today_transactions=result.today_transactions or 0,
                today_units_sold=result.today_units or 0,
                today_new_customers=result.today_new_customers or 0,
                week_revenue=result.week_revenue or Decimal("0.00"),
                week_transactions=result.week_transactions or 0,
                month_revenue=result.month_revenue or Decimal("0.00"),
                month_transactions=result.month_transactions or 0,
                avg_margin_30d=result.avg_margin_30d,
                return_rate_30d=Decimal(str(round(return_rate_30d, 2))),
                yesterday_revenue=comparisons.get("yesterday"),
                last_week_revenue=comparisons.get("last_week"),
                last_month_revenue=comparisons.get("last_month"),
                computed_at=now,
            )
            self._db.add(cache)
        
        self._db.commit()
        
        result_dict = cache.to_dict()
        result_dict["cached"] = False
        return result_dict
    
    def _get_comparison_values(
        self,
        store_id: UUID,
        yesterday: date,
        last_week_start: date,
        last_month_start: date,
    ) -> Dict[str, Decimal]:
        """Get comparison revenue values."""
        query = select(
            func.sum(SalesTransaction.price * SalesTransaction.quantity).filter(
                func.date(SalesTransaction.sale_date) == yesterday
            ).label("yesterday"),
            func.sum(SalesTransaction.price * SalesTransaction.quantity).filter(
                SalesTransaction.sale_date >= last_week_start,
                SalesTransaction.sale_date < last_week_start + timedelta(weeks=1)
            ).label("last_week"),
            func.sum(SalesTransaction.price * SalesTransaction.quantity).filter(
                SalesTransaction.sale_date >= last_month_start,
                SalesTransaction.sale_date < last_month_start + timedelta(days=32)
            ).filter(
                func.date_trunc('month', SalesTransaction.sale_date) == last_month_start.replace(day=1)
            ).label("last_month"),
        ).where(
            and_(
                SalesTransaction.store_id == store_id,
                SalesTransaction.deleted_at.is_(None),
                SalesTransaction.is_active == True,
            )
        )
        
        result = self._db.execute(query).first()
        
        return {
            "yesterday": result.yesterday,
            "last_week": result.last_week,
            "last_month": result.last_month,
        }
    
    # ─── Hourly Metrics Methods ──────────────────────────────────────
    
    def get_hourly_metrics(
        self,
        store_id: UUID,
        date_range: DateRange,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get hourly metrics for a date range.
        
        Returns pre-computed hourly metrics with staleness checks.
        """
        # Query hourly metrics
        metrics = self._db.scalars(
            select(HourlyMetric).where(
                and_(
                    HourlyMetric.store_id == store_id,
                    HourlyMetric.hour_key >= date_range.start,
                    HourlyMetric.hour_key < date_range.end,
                )
            ).order_by(HourlyMetric.hour_key)
        ).all()
        
        # Check for stale or missing metrics
        now = datetime.now(timezone.utc)
        needs_recalc = []
        
        for metric in metrics:
            staleness = now - metric.computed_at
            if metric.status == MetricStatus.STALE or staleness > STALE_THRESHOLD_HOURLY:
                needs_recalc.append(metric.hour_key)
        
        # Recalculate stale metrics
        if needs_recalc and not use_cache:
            for hour_key in needs_recalc:
                self._compute_hourly_metric(store_id, hour_key)
            
            # Re-fetch
            metrics = self._db.scalars(
                select(HourlyMetric).where(
                    and_(
                        HourlyMetric.store_id == store_id,
                        HourlyMetric.hour_key >= date_range.start,
                        HourlyMetric.hour_key < date_range.end,
                    )
                ).order_by(HourlyMetric.hour_key)
            ).all()
        
        return [m.to_dict() for m in metrics]
    
    def _compute_hourly_metric(
        self,
        store_id: UUID,
        hour_key: datetime,
    ) -> HourlyMetric:
        """
        Compute hourly metric from raw transactions.
        
        Creates or updates the hourly metric row.
        """
        start_time = datetime.now(timezone.utc)
        
        hour_start = hour_key.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)
        
        # Aggregate transactions for this hour
        query = select(
            func.count().label("transaction_count"),
            func.sum(SalesTransaction.price * SalesTransaction.quantity).label("total_revenue"),
            func.sum(SalesTransaction.quantity).label("units_sold"),
            func.sum(SalesTransaction.price * SalesTransaction.quantity * SalesTransaction.profit_margin / 100).label("total_profit"),
            func.avg(SalesTransaction.profit_margin).label("avg_profit_margin"),
            
            # Customer counts
            func.count(func.distinct(SalesTransaction.customer_id)).label("unique_customers"),
            func.count().filter(
                SalesTransaction.customer_segment == CustomerSegment.NEW_CUSTOMER
            ).label("new_customers"),
            func.count().filter(
                SalesTransaction.customer_segment == CustomerSegment.RETURNING
            ).label("returning_customers"),
            func.count().filter(
                SalesTransaction.customer_segment == CustomerSegment.VIP
            ).label("vip_customers"),
            
            # Returns
            func.count().filter(
                SalesTransaction.return_status == ReturnStatus.RETURNED
            ).label("return_count"),
            func.sum(SalesTransaction.price * SalesTransaction.quantity).filter(
                SalesTransaction.return_status == ReturnStatus.RETURNED
            ).label("return_amount"),
            
        ).where(
            and_(
                SalesTransaction.store_id == store_id,
                SalesTransaction.sale_date >= hour_start,
                SalesTransaction.sale_date < hour_end,
                SalesTransaction.deleted_at.is_(None),
                SalesTransaction.is_active == True,
            )
        )
        
        result = self._db.execute(query).first()
        
        # Category breakdown
        category_breakdown = self._compute_category_breakdown(store_id, hour_start, hour_end)
        segment_breakdown = self._compute_segment_breakdown(store_id, hour_start, hour_end)
        top_products = self._compute_top_products(store_id, hour_start, hour_end, limit=5)
        
        transaction_count = result.transaction_count or 0
        total_revenue = result.total_revenue or Decimal("0.00")
        return_count = result.return_count or 0
        return_rate = Decimal(str(round(return_count / transaction_count * 100, 2))) if transaction_count > 0 else Decimal("0.00")
        
        # Compute average transaction value
        atv = total_revenue / transaction_count if transaction_count > 0 else Decimal("0.00")
        
        computation_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        # Upsert hourly metric
        existing = self._db.scalar(
            select(HourlyMetric).where(
                and_(
                    HourlyMetric.store_id == store_id,
                    HourlyMetric.hour_key == hour_start,
                )
            )
        )
        
        if existing:
            existing.total_revenue = total_revenue
            existing.transaction_count = transaction_count
            existing.units_sold = result.units_sold or 0
            existing.total_profit = result.total_profit or Decimal("0.00")
            existing.avg_profit_margin = result.avg_profit_margin or Decimal("0.00")
            existing.avg_transaction_value = atv
            existing.return_count = return_count
            existing.return_amount = result.return_amount or Decimal("0.00")
            existing.return_rate = return_rate
            existing.unique_customers = result.unique_customers or 0
            existing.new_customers = result.new_customers or 0
            existing.returning_customers = result.returning_customers or 0
            existing.vip_customers = result.vip_customers or 0
            existing.category_breakdown = category_breakdown
            existing.segment_breakdown = segment_breakdown
            existing.top_products = top_products
            existing.status = MetricStatus.FRESH
            existing.computed_at = datetime.now(timezone.utc)
            existing.computation_time_ms = computation_time
            existing.rows_processed = transaction_count
            
            metric = existing
        else:
            metric = HourlyMetric(
                store_id=store_id,
                hour_key=hour_start,
                date_key=hour_start.date(),
                hour_of_day=hour_start.hour,
                day_of_week=hour_start.weekday(),
                total_revenue=total_revenue,
                transaction_count=transaction_count,
                units_sold=result.units_sold or 0,
                total_profit=result.total_profit or Decimal("0.00"),
                avg_profit_margin=result.avg_profit_margin or Decimal("0.00"),
                avg_transaction_value=atv,
                return_count=return_count,
                return_amount=result.return_amount or Decimal("0.00"),
                return_rate=return_rate,
                unique_customers=result.unique_customers or 0,
                new_customers=result.new_customers or 0,
                returning_customers=result.returning_customers or 0,
                vip_customers=result.vip_customers or 0,
                category_breakdown=category_breakdown,
                segment_breakdown=segment_breakdown,
                top_products=top_products,
                status=MetricStatus.FRESH,
                computation_time_ms=computation_time,
                rows_processed=transaction_count,
            )
            self._db.add(metric)
        
        self._db.commit()
        
        # Log computation
        self._log_computation(
            store_id=store_id,
            granularity=MetricGranularity.HOURLY,
            period_start=hour_start,
            period_end=hour_end,
            computation_type="full_recalc",
            status="success",
            rows_processed=transaction_count,
            computation_time_ms=computation_time,
        )
        
        return metric
    
    # ─── Daily Metrics Methods ──────────────────────────────────────
    
    def get_daily_metrics(
        self,
        store_id: UUID,
        date_range: DateRange,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get daily metrics for a date range."""
        metrics = self._db.scalars(
            select(DailyMetric).where(
                and_(
                    DailyMetric.store_id == store_id,
                    DailyMetric.date_key >= date_range.start.date(),
                    DailyMetric.date_key <= date_range.end.date(),
                )
            ).order_by(DailyMetric.date_key)
        ).all()
        
        now = datetime.now(timezone.utc)
        needs_recalc = []
        
        for metric in metrics:
            staleness = now - metric.computed_at
            if metric.status == MetricStatus.STALE or staleness > STALE_THRESHOLD_DAILY:
                needs_recalc.append(metric.date_key)
        
        if needs_recalc and not use_cache:
            for date_key in needs_recalc:
                self._compute_daily_metric(store_id, date_key)
            
            metrics = self._db.scalars(
                select(DailyMetric).where(
                    and_(
                        DailyMetric.store_id == store_id,
                        DailyMetric.date_key >= date_range.start.date(),
                        DailyMetric.date_key <= date_range.end.date(),
                    )
                ).order_by(DailyMetric.date_key)
            ).all()
        
        return [m.to_dict() for m in metrics]
    
    def _compute_daily_metric(
        self,
        store_id: UUID,
        date_key: date,
        from_hourly: bool = True,
    ) -> DailyMetric:
        """
        Compute daily metric.
        
        If from_hourly=True, rolls up from hourly metrics.
        Otherwise, computes from raw transactions.
        """
        start_time = datetime.now(timezone.utc)
        
        day_start = datetime.combine(date_key, datetime.min.time()).replace(tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        
        if from_hourly:
            # Rollup from hourly metrics
            hourly_metrics = self._db.scalars(
                select(HourlyMetric).where(
                    and_(
                        HourlyMetric.store_id == store_id,
                        HourlyMetric.date_key == date_key,
                    )
                )
            ).all()
            
            if hourly_metrics:
                # Aggregate from hourly
                total_revenue = sum(h.total_revenue for h in hourly_metrics)
                transaction_count = sum(h.transaction_count for h in hourly_metrics)
                units_sold = sum(h.units_sold for h in hourly_metrics)
                total_profit = sum(h.total_profit for h in hourly_metrics)
                
                # Weighted average profit margin
                if transaction_count > 0:
                    avg_profit_margin = sum(
                        h.avg_profit_margin * h.transaction_count 
                        for h in hourly_metrics
                    ) / transaction_count
                else:
                    avg_profit_margin = Decimal("0.00")
                
                return_count = sum(h.return_count for h in hourly_metrics)
                return_amount = sum(h.return_amount for h in hourly_metrics)
                unique_customers = max(h.unique_customers for h in hourly_metrics) if hourly_metrics else 0
                new_customers = sum(h.new_customers for h in hourly_metrics)
                returning_customers = sum(h.returning_customers for h in hourly_metrics)
                vip_customers = sum(h.vip_customers for h in hourly_metrics)
                
                # Merge breakdowns
                category_breakdown = self._merge_category_breakdowns(
                    [h.category_breakdown for h in hourly_metrics]
                )
                segment_breakdown = self._merge_segment_breakdowns(
                    [h.segment_breakdown for h in hourly_metrics]
                )
                top_products = self._merge_top_products(
                    [h.top_products for h in hourly_metrics]
                )
                
                rows_processed = len(hourly_metrics)
                computation_type = "rollup"
            else:
                # Fall back to raw computation
                return self._compute_daily_metric(store_id, date_key, from_hourly=False)
        else:
            # Compute from raw transactions
            query = select(
                func.count().label("transaction_count"),
                func.sum(SalesTransaction.price * SalesTransaction.quantity).label("total_revenue"),
                func.sum(SalesTransaction.quantity).label("units_sold"),
                func.sum(SalesTransaction.price * SalesTransaction.quantity * SalesTransaction.profit_margin / 100).label("total_profit"),
                func.avg(SalesTransaction.profit_margin).label("avg_profit_margin"),
                func.count(func.distinct(SalesTransaction.customer_id)).label("unique_customers"),
                func.count().filter(
                    SalesTransaction.customer_segment == CustomerSegment.NEW_CUSTOMER
                ).label("new_customers"),
                func.count().filter(
                    SalesTransaction.customer_segment == CustomerSegment.RETURNING
                ).label("returning_customers"),
                func.count().filter(
                    SalesTransaction.customer_segment == CustomerSegment.VIP
                ).label("vip_customers"),
                func.count().filter(
                    SalesTransaction.return_status == ReturnStatus.RETURNED
                ).label("return_count"),
                func.sum(SalesTransaction.price * SalesTransaction.quantity).filter(
                    SalesTransaction.return_status == ReturnStatus.RETURNED
                ).label("return_amount"),
            ).where(
                and_(
                    SalesTransaction.store_id == store_id,
                    SalesTransaction.sale_date >= day_start,
                    SalesTransaction.sale_date < day_end,
                    SalesTransaction.deleted_at.is_(None),
                    SalesTransaction.is_active == True,
                )
            )
            
            result = self._db.execute(query).first()
            
            transaction_count = result.transaction_count or 0
            total_revenue = result.total_revenue or Decimal("0.00")
            units_sold = result.units_sold or 0
            total_profit = result.total_profit or Decimal("0.00")
            avg_profit_margin = result.avg_profit_margin or Decimal("0.00")
            return_count = result.return_count or 0
            return_amount = result.return_amount or Decimal("0.00")
            unique_customers = result.unique_customers or 0
            new_customers = result.new_customers or 0
            returning_customers = result.returning_customers or 0
            vip_customers = result.vip_customers or 0
            
            category_breakdown = self._compute_category_breakdown(store_id, day_start, day_end)
            segment_breakdown = self._compute_segment_breakdown(store_id, day_start, day_end)
            top_products = self._compute_top_products(store_id, day_start, day_end, limit=10)
            
            rows_processed = transaction_count
            computation_type = "full_recalc"
        
        return_rate = Decimal(str(round(return_count / transaction_count * 100, 2))) if transaction_count > 0 else Decimal("0.00")
        atv = total_revenue / transaction_count if transaction_count > 0 else Decimal("0.00")
        
        computation_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        # Get comparison values
        previous_day_revenue = self._get_period_revenue(store_id, date_key - timedelta(days=1))
        previous_week_revenue = self._get_period_revenue(store_id, date_key - timedelta(weeks=1))
        previous_month_revenue = self._get_period_revenue(store_id, date_key - timedelta(days=30))
        
        # Upsert daily metric
        existing = self._db.scalar(
            select(DailyMetric).where(
                and_(
                    DailyMetric.store_id == store_id,
                    DailyMetric.date_key == date_key,
                )
            )
        )
        
        if existing:
            existing.total_revenue = total_revenue
            existing.transaction_count = transaction_count
            existing.units_sold = units_sold
            existing.total_profit = total_profit
            existing.avg_profit_margin = avg_profit_margin
            existing.avg_transaction_value = atv
            existing.return_count = return_count
            existing.return_amount = return_amount
            existing.return_rate = return_rate
            existing.unique_customers = unique_customers
            existing.new_customers = new_customers
            existing.returning_customers = returning_customers
            existing.vip_customers = vip_customers
            existing.category_breakdown = category_breakdown
            existing.segment_breakdown = segment_breakdown
            existing.top_products = top_products
            existing.previous_day_revenue = previous_day_revenue
            existing.previous_week_revenue = previous_week_revenue
            existing.previous_month_revenue = previous_month_revenue
            existing.status = MetricStatus.FRESH
            existing.computed_at = datetime.now(timezone.utc)
            existing.computation_time_ms = computation_time
            existing.rows_processed = rows_processed
            
            metric = existing
        else:
            metric = DailyMetric(
                store_id=store_id,
                date_key=date_key,
                year_key=date_key.year,
                month_key=date_key.month,
                week_key=date_key.isocalendar()[1],
                day_of_week=date_key.weekday(),
                day_of_month=date_key.day,
                is_weekend=date_key.weekday() >= 5,
                total_revenue=total_revenue,
                transaction_count=transaction_count,
                units_sold=units_sold,
                total_profit=total_profit,
                avg_profit_margin=avg_profit_margin,
                avg_transaction_value=atv,
                return_count=return_count,
                return_amount=return_amount,
                return_rate=return_rate,
                unique_customers=unique_customers,
                new_customers=new_customers,
                returning_customers=returning_customers,
                vip_customers=vip_customers,
                category_breakdown=category_breakdown,
                segment_breakdown=segment_breakdown,
                top_products=top_products,
                previous_day_revenue=previous_day_revenue,
                previous_week_revenue=previous_week_revenue,
                previous_month_revenue=previous_month_revenue,
                status=MetricStatus.FRESH,
                computation_time_ms=computation_time,
                rows_processed=rows_processed,
            )
            self._db.add(metric)
        
        self._db.commit()
        
        # Log computation
        self._log_computation(
            store_id=store_id,
            granularity=MetricGranularity.DAILY,
            period_start=day_start,
            period_end=day_end,
            computation_type=computation_type,
            status="success",
            rows_processed=rows_processed,
            computation_time_ms=computation_time,
        )
        
        return metric
    
    # ─── Weekly Metrics Methods ─────────────────────────────────────
    
    def get_weekly_metrics(
        self,
        store_id: UUID,
        year: int,
        week: int,
    ) -> Optional[Dict[str, Any]]:
        """Get weekly metric for a specific ISO week."""
        metric = self._db.scalar(
            select(WeeklyMetric).where(
                and_(
                    WeeklyMetric.store_id == store_id,
                    WeeklyMetric.year_key == year,
                    WeeklyMetric.week_key == week,
                )
            )
        )
        
        if not metric or metric.status == MetricStatus.STALE:
            metric = self._compute_weekly_metric(store_id, year, week)
        
        return metric.to_dict() if metric else None
    
    def _compute_weekly_metric(
        self,
        store_id: UUID,
        year: int,
        week: int,
    ) -> WeeklyMetric:
        """Compute weekly metric by rolling up daily metrics."""
        start_time = datetime.now(timezone.utc)
        
        # Calculate week boundaries
        from datetime import datetime
        week_start = datetime.strptime(f"{year}-W{week:02d}-1", "%Y-W%W-%w").date()
        week_end = week_start + timedelta(days=6)
        
        # Rollup from daily metrics
        daily_metrics = self._db.scalars(
            select(DailyMetric).where(
                and_(
                    DailyMetric.store_id == store_id,
                    DailyMetric.date_key >= week_start,
                    DailyMetric.date_key <= week_end,
                )
            )
        ).all()
        
        if not daily_metrics:
            # No data for this week
            return None
        
        # Aggregate
        total_revenue = sum(d.total_revenue for d in daily_metrics)
        transaction_count = sum(d.transaction_count for d in daily_metrics)
        units_sold = sum(d.units_sold for d in daily_metrics)
        total_profit = sum(d.total_profit for d in daily_metrics)
        
        # Weighted average
        if transaction_count > 0:
            avg_profit_margin = sum(
                d.avg_profit_margin * d.transaction_count 
                for d in daily_metrics
            ) / transaction_count
        else:
            avg_profit_margin = Decimal("0.00")
        
        return_count = sum(d.return_count for d in daily_metrics)
        return_amount = sum(d.return_amount for d in daily_metrics)
        unique_customers = max(d.unique_customers for d in daily_metrics) if daily_metrics else 0
        new_customers = sum(d.new_customers for d in daily_metrics)
        
        return_rate = Decimal(str(round(return_count / transaction_count * 100, 2))) if transaction_count > 0 else Decimal("0.00")
        atv = total_revenue / transaction_count if transaction_count > 0 else Decimal("0.00")
        
        # Merge breakdowns
        category_breakdown = self._merge_category_breakdowns(
            [d.category_breakdown for d in daily_metrics]
        )
        top_products = self._merge_top_products(
            [d.top_products for d in daily_metrics]
        )
        
        computation_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        # Get comparison values
        prev_week = week - 1 if week > 1 else 52
        prev_year = year if week > 1 else year - 1
        previous_week_revenue = self._get_week_revenue(store_id, prev_year, prev_week)
        previous_year_week_revenue = self._get_week_revenue(store_id, year - 1, week)
        
        # Upsert
        existing = self._db.scalar(
            select(WeeklyMetric).where(
                and_(
                    WeeklyMetric.store_id == store_id,
                    WeeklyMetric.year_key == year,
                    WeeklyMetric.week_key == week,
                )
            )
        )
        
        if existing:
            existing.total_revenue = total_revenue
            existing.transaction_count = transaction_count
            existing.units_sold = units_sold
            existing.total_profit = total_profit
            existing.avg_profit_margin = avg_profit_margin
            existing.avg_transaction_value = atv
            existing.return_count = return_count
            existing.return_amount = return_amount
            existing.return_rate = return_rate
            existing.unique_customers = unique_customers
            existing.new_customers = new_customers
            existing.category_breakdown = category_breakdown
            existing.top_products = top_products
            existing.previous_week_revenue = previous_week_revenue
            existing.previous_year_week_revenue = previous_year_week_revenue
            existing.status = MetricStatus.FRESH
            existing.computed_at = datetime.now(timezone.utc)
            existing.computation_time_ms = computation_time
            
            metric = existing
        else:
            metric = WeeklyMetric(
                store_id=store_id,
                year_key=year,
                week_key=week,
                week_start_date=week_start,
                week_end_date=week_end,
                total_revenue=total_revenue,
                transaction_count=transaction_count,
                units_sold=units_sold,
                total_profit=total_profit,
                avg_profit_margin=avg_profit_margin,
                avg_transaction_value=atv,
                return_count=return_count,
                return_amount=return_amount,
                return_rate=return_rate,
                unique_customers=unique_customers,
                new_customers=new_customers,
                category_breakdown=category_breakdown,
                top_products=top_products,
                previous_week_revenue=previous_week_revenue,
                previous_year_week_revenue=previous_year_week_revenue,
                status=MetricStatus.FRESH,
                computation_time_ms=computation_time,
            )
            self._db.add(metric)
        
        self._db.commit()
        
        return metric
    
    # ─── Monthly Metrics Methods ────────────────────────────────────
    
    def get_monthly_metrics(
        self,
        store_id: UUID,
        year: int,
        month: int,
    ) -> Optional[Dict[str, Any]]:
        """Get monthly metric for a specific month."""
        metric = self._db.scalar(
            select(MonthlyMetric).where(
                and_(
                    MonthlyMetric.store_id == store_id,
                    MonthlyMetric.year_key == year,
                    MonthlyMetric.month_key == month,
                )
            )
        )
        
        if not metric or metric.status == MetricStatus.STALE:
            metric = self._compute_monthly_metric(store_id, year, month)
        
        return metric.to_dict() if metric else None
    
    def _compute_monthly_metric(
        self,
        store_id: UUID,
        year: int,
        month: int,
    ) -> MonthlyMetric:
        """Compute monthly metric by rolling up daily metrics."""
        start_time = datetime.now(timezone.utc)
        
        # Calculate month boundaries
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
        
        days_in_month = (month_end - month_start).days + 1
        
        # Rollup from daily metrics
        daily_metrics = self._db.scalars(
            select(DailyMetric).where(
                and_(
                    DailyMetric.store_id == store_id,
                    DailyMetric.year_key == year,
                    DailyMetric.month_key == month,
                )
            )
        ).all()
        
        if not daily_metrics:
            return None
        
        # Aggregate
        total_revenue = sum(d.total_revenue for d in daily_metrics)
        transaction_count = sum(d.transaction_count for d in daily_metrics)
        units_sold = sum(d.units_sold for d in daily_metrics)
        total_profit = sum(d.total_profit for d in daily_metrics)
        
        if transaction_count > 0:
            avg_profit_margin = sum(
                d.avg_profit_margin * d.transaction_count 
                for d in daily_metrics
            ) / transaction_count
        else:
            avg_profit_margin = Decimal("0.00")
        
        return_count = sum(d.return_count for d in daily_metrics)
        return_amount = sum(d.return_amount for d in daily_metrics)
        unique_customers = max(d.unique_customers for d in daily_metrics) if daily_metrics else 0
        new_customers = sum(d.new_customers for d in daily_metrics)
        
        return_rate = Decimal(str(round(return_count / transaction_count * 100, 2))) if transaction_count > 0 else Decimal("0.00")
        atv = total_revenue / transaction_count if transaction_count > 0 else Decimal("0.00")
        
        # YTD
        ytd_metrics = self._db.scalars(
            select(DailyMetric).where(
                and_(
                    DailyMetric.store_id == store_id,
                    DailyMetric.year_key == year,
                    DailyMetric.month_key <= month,
                )
            )
        ).all()
        ytd_revenue = sum(d.total_revenue for d in ytd_metrics)
        ytd_transactions = sum(d.transaction_count for d in ytd_metrics)
        
        # Merge breakdowns
        category_breakdown = self._merge_category_breakdowns(
            [d.category_breakdown for d in daily_metrics]
        )
        segment_breakdown = self._merge_segment_breakdowns(
            [d.segment_breakdown for d in daily_metrics]
        )
        top_products = self._merge_top_products(
            [d.top_products for d in daily_metrics]
        )
        
        computation_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        # Comparison values
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        previous_month_revenue = self._get_month_revenue(store_id, prev_year, prev_month)
        previous_year_month_revenue = self._get_month_revenue(store_id, year - 1, month)
        
        # Upsert
        existing = self._db.scalar(
            select(MonthlyMetric).where(
                and_(
                    MonthlyMetric.store_id == store_id,
                    MonthlyMetric.year_key == year,
                    MonthlyMetric.month_key == month,
                )
            )
        )
        
        if existing:
            existing.total_revenue = total_revenue
            existing.transaction_count = transaction_count
            existing.units_sold = units_sold
            existing.total_profit = total_profit
            existing.avg_profit_margin = avg_profit_margin
            existing.avg_transaction_value = atv
            existing.return_count = return_count
            existing.return_amount = return_amount
            existing.return_rate = return_rate
            existing.unique_customers = unique_customers
            existing.new_customers = new_customers
            existing.category_breakdown = category_breakdown
            existing.segment_breakdown = segment_breakdown
            existing.top_products = top_products
            existing.ytd_revenue = ytd_revenue
            existing.ytd_transactions = ytd_transactions
            existing.previous_month_revenue = previous_month_revenue
            existing.previous_year_month_revenue = previous_year_month_revenue
            existing.status = MetricStatus.FRESH
            existing.computed_at = datetime.now(timezone.utc)
            existing.computation_time_ms = computation_time
            
            metric = existing
        else:
            metric = MonthlyMetric(
                store_id=store_id,
                year_key=year,
                month_key=month,
                month_start_date=month_start,
                month_end_date=month_end,
                days_in_month=days_in_month,
                total_revenue=total_revenue,
                transaction_count=transaction_count,
                units_sold=units_sold,
                total_profit=total_profit,
                avg_profit_margin=avg_profit_margin,
                avg_transaction_value=atv,
                return_count=return_count,
                return_amount=return_amount,
                return_rate=return_rate,
                unique_customers=unique_customers,
                new_customers=new_customers,
                category_breakdown=category_breakdown,
                segment_breakdown=segment_breakdown,
                top_products=top_products,
                ytd_revenue=ytd_revenue,
                ytd_transactions=ytd_transactions,
                previous_month_revenue=previous_month_revenue,
                previous_year_month_revenue=previous_year_month_revenue,
                status=MetricStatus.FRESH,
                computation_time_ms=computation_time,
            )
            self._db.add(metric)
        
        self._db.commit()
        
        return metric
    
    # ─── Incremental Update Methods ─────────────────────────────────
    
    def update_metrics_for_transaction(
        self,
        transaction: SalesTransaction,
        event_type: str = "sale_created",
    ) -> None:
        """
        Update metrics incrementally when a transaction is created/modified.
        
        This is the streaming update path.
        """
        store_id = transaction.store_id
        sale_date = transaction.sale_date
        
        # 1. Update real-time KPIs
        self._update_realtime_kpis(transaction, event_type)
        
        # 2. Queue hourly metric update (debounced)
        hour_key = sale_date.replace(minute=0, second=0, microsecond=0)
        self._queue_hourly_update(store_id, hour_key, transaction, event_type)
        
        # 3. Mark downstream metrics as stale
        self._mark_downstream_stale(store_id, sale_date)
    
    def _update_realtime_kpis(
        self,
        transaction: SalesTransaction,
        event_type: str,
    ) -> None:
        """Update real-time KPI cache."""
        cache = self._db.scalar(
            select(RealtimeKPICache).where(
                RealtimeKPICache.store_id == transaction.store_id
            )
        )
        
        if not cache:
            # Create cache entry
            self._compute_realtime_kpis(transaction.store_id)
            return
        
        # Apply delta
        delta_revenue = transaction.price * transaction.quantity
        
        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        transaction_date = transaction.sale_date
        
        if transaction_date >= today:
            # Today's transaction
            if event_type == "sale_created":
                cache.today_revenue += delta_revenue
                cache.today_transactions += 1
                cache.today_units_sold += transaction.quantity
                if transaction.customer_segment == CustomerSegment.NEW_CUSTOMER:
                    cache.today_new_customers += 1
            elif event_type == "return_processed":
                cache.today_revenue -= delta_revenue
                cache.today_transactions -= 1
        
        if transaction_date >= week_start:
            if event_type == "sale_created":
                cache.week_revenue += delta_revenue
                cache.week_transactions += 1
            elif event_type == "return_processed":
                cache.week_revenue -= delta_revenue
        
        if transaction_date >= month_start:
            if event_type == "sale_created":
                cache.month_revenue += delta_revenue
                cache.month_transactions += 1
            elif event_type == "return_processed":
                cache.month_revenue -= delta_revenue
        
        cache.computed_at = now
        cache.last_transaction_at = transaction_date
        cache.version += 1
        
        self._db.commit()
    
    def _queue_hourly_update(
        self,
        store_id: UUID,
        hour_key: datetime,
        transaction: SalesTransaction,
        event_type: str,
    ) -> None:
        """Queue an hourly metric update (debounced)."""
        delta_revenue = transaction.price * transaction.quantity
        delta_profit = delta_revenue * (transaction.profit_margin / 100) if transaction.profit_margin else Decimal("0.00")
        
        # Check for existing pending update
        existing = self._db.scalar(
            select(MetricUpdateQueue).where(
                and_(
                    MetricUpdateQueue.store_id == store_id,
                    MetricUpdateQueue.granularity == MetricGranularity.HOURLY,
                    MetricUpdateQueue.hour_key == hour_key,
                    MetricUpdateQueue.status == "pending",
                )
            )
        )
        
        if existing:
            # Append to existing
            if event_type == "sale_created":
                existing.delta_revenue += delta_revenue
                existing.delta_transactions += 1
                existing.delta_units += transaction.quantity
                existing.delta_profit += delta_profit
            elif event_type == "return_processed":
                existing.delta_returns += 1
                existing.delta_return_amount += delta_revenue
            
            existing.transaction_ids = existing.transaction_ids + [str(transaction.id)]
            existing.scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=DEBOUNCE_WINDOW_SECONDS)
        else:
            # Create new
            queue_item = MetricUpdateQueue(
                store_id=store_id,
                granularity=MetricGranularity.HOURLY,
                hour_key=hour_key,
                delta_revenue=delta_revenue if event_type == "sale_created" else Decimal("0.00"),
                delta_transactions=1 if event_type == "sale_created" else 0,
                delta_units=transaction.quantity if event_type == "sale_created" else 0,
                delta_returns=1 if event_type == "return_processed" else 0,
                delta_return_amount=delta_revenue if event_type == "return_processed" else Decimal("0.00"),
                transaction_ids=[str(transaction.id)],
                scheduled_at=datetime.now(timezone.utc) + timedelta(seconds=DEBOUNCE_WINDOW_SECONDS),
            )
            self._db.add(queue_item)
        
        self._db.commit()
    
    def process_pending_updates(self, batch_size: int = 100) -> int:
        """
        Process pending metric updates.
        
        Called by scheduler after debounce window.
        """
        now = datetime.now(timezone.utc)
        
        pending = self._db.scalars(
            select(MetricUpdateQueue).where(
                and_(
                    MetricUpdateQueue.status == "pending",
                    MetricUpdateQueue.scheduled_at <= now,
                )
            ).limit(batch_size)
        ).all()
        
        processed = 0
        
        for item in pending:
            try:
                item.status = "processing"
                self._db.commit()
                
                # Apply incremental update to hourly metric
                self._apply_hourly_delta(item)
                
                item.status = "completed"
                item.processed_at = now
                processed += 1
                
            except Exception as e:
                logger.error(f"Failed to process metric update {item.id}: {e}")
                item.status = "failed"
                item.attempts += 1
            
            self._db.commit()
        
        return processed
    
    def _apply_hourly_delta(self, queue_item: MetricUpdateQueue) -> None:
        """Apply delta to hourly metric."""
        metric = self._db.scalar(
            select(HourlyMetric).where(
                and_(
                    HourlyMetric.store_id == queue_item.store_id,
                    HourlyMetric.hour_key == queue_item.hour_key,
                )
            )
        )
        
        if not metric:
            # Create new metric
            self._compute_hourly_metric(queue_item.store_id, queue_item.hour_key)
            return
        
        # Apply delta
        metric.total_revenue += queue_item.delta_revenue
        metric.transaction_count += queue_item.delta_transactions
        metric.units_sold += queue_item.delta_units
        metric.total_profit += queue_item.delta_profit
        metric.return_count += queue_item.delta_returns
        metric.return_amount += queue_item.delta_return_amount
        
        # Recalculate derived metrics
        if metric.transaction_count > 0:
            metric.avg_transaction_value = metric.total_revenue / metric.transaction_count
            metric.return_rate = Decimal(str(round(
                metric.return_count / metric.transaction_count * 100, 2
            )))
        
        metric.computed_at = datetime.now(timezone.utc)
        metric.status = MetricStatus.FRESH
        
        self._db.commit()
    
    def _mark_downstream_stale(
        self,
        store_id: UUID,
        sale_date: datetime,
    ) -> None:
        """Mark downstream metrics as stale."""
        date_key = sale_date.date()
        
        # Mark daily metric as stale
        self._db.execute(
            update(DailyMetric)
            .where(
                and_(
                    DailyMetric.store_id == store_id,
                    DailyMetric.date_key == date_key,
                )
            )
            .values(status=MetricStatus.STALE)
        )
        
        # Mark weekly metric as stale
        iso_cal = date_key.isocalendar()
        self._db.execute(
            update(WeeklyMetric)
            .where(
                and_(
                    WeeklyMetric.store_id == store_id,
                    WeeklyMetric.year_key == iso_cal[0],
                    WeeklyMetric.week_key == iso_cal[1],
                )
            )
            .values(status=MetricStatus.STALE)
        )
        
        # Mark monthly metric as stale
        self._db.execute(
            update(MonthlyMetric)
            .where(
                and_(
                    MonthlyMetric.store_id == store_id,
                    MonthlyMetric.year_key == date_key.year,
                    MonthlyMetric.month_key == date_key.month,
                )
            )
            .values(status=MetricStatus.STALE)
        )
        
        self._db.commit()
    
    # ─── Helper Methods ─────────────────────────────────────────────
    
    def _compute_category_breakdown(
        self,
        store_id: UUID,
        start: datetime,
        end: datetime,
    ) -> List[Dict[str, Any]]:
        """Compute breakdown by category."""
        query = select(
            SalesTransaction.category,
            func.count().label("transactions"),
            func.sum(SalesTransaction.quantity).label("units"),
            func.sum(SalesTransaction.price * SalesTransaction.quantity).label("revenue"),
        ).where(
            and_(
                SalesTransaction.store_id == store_id,
                SalesTransaction.sale_date >= start,
                SalesTransaction.sale_date < end,
                SalesTransaction.deleted_at.is_(None),
                SalesTransaction.is_active == True,
            )
        ).group_by(SalesTransaction.category)
        
        results = self._db.execute(query).all()
        
        return [
            {
                "category": row.category.value if row.category else None,
                "transactions": row.transactions or 0,
                "units": row.units or 0,
                "revenue": float(row.revenue or 0),
            }
            for row in results
        ]
    
    def _compute_segment_breakdown(
        self,
        store_id: UUID,
        start: datetime,
        end: datetime,
    ) -> List[Dict[str, Any]]:
        """Compute breakdown by customer segment."""
        query = select(
            SalesTransaction.customer_segment,
            func.count().label("transactions"),
            func.sum(SalesTransaction.price * SalesTransaction.quantity).label("revenue"),
        ).where(
            and_(
                SalesTransaction.store_id == store_id,
                SalesTransaction.sale_date >= start,
                SalesTransaction.sale_date < end,
                SalesTransaction.deleted_at.is_(None),
                SalesTransaction.is_active == True,
            )
        ).group_by(SalesTransaction.customer_segment)
        
        results = self._db.execute(query).all()
        
        return [
            {
                "segment": row.customer_segment.value if row.customer_segment else None,
                "transactions": row.transactions or 0,
                "revenue": float(row.revenue or 0),
            }
            for row in results
        ]
    
    def _compute_top_products(
        self,
        store_id: UUID,
        start: datetime,
        end: datetime,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Compute top products by revenue."""
        query = select(
            SalesTransaction.product_name,
            SalesTransaction.category,
            func.count().label("transactions"),
            func.sum(SalesTransaction.quantity).label("units"),
            func.sum(SalesTransaction.price * SalesTransaction.quantity).label("revenue"),
        ).where(
            and_(
                SalesTransaction.store_id == store_id,
                SalesTransaction.sale_date >= start,
                SalesTransaction.sale_date < end,
                SalesTransaction.deleted_at.is_(None),
                SalesTransaction.is_active == True,
            )
        ).group_by(
            SalesTransaction.product_name,
            SalesTransaction.category,
        ).order_by(desc(text("revenue"))).limit(limit)
        
        results = self._db.execute(query).all()
        
        return [
            {
                "product_name": row.product_name,
                "category": row.category.value if row.category else None,
                "transactions": row.transactions or 0,
                "units": row.units or 0,
                "revenue": float(row.revenue or 0),
            }
            for row in results
        ]
    
    def _merge_category_breakdowns(
        self,
        breakdowns: List[List[Dict]],
    ) -> List[Dict[str, Any]]:
        """Merge multiple category breakdowns."""
        merged = {}
        
        for breakdown in breakdowns:
            for item in breakdown:
                cat = item.get("category")
                if cat not in merged:
                    merged[cat] = {
                        "category": cat,
                        "transactions": 0,
                        "units": 0,
                        "revenue": 0,
                    }
                merged[cat]["transactions"] += item.get("transactions", 0)
                merged[cat]["units"] += item.get("units", 0)
                merged[cat]["revenue"] += item.get("revenue", 0)
        
        return sorted(merged.values(), key=lambda x: x["revenue"], reverse=True)
    
    def _merge_segment_breakdowns(
        self,
        breakdowns: List[List[Dict]],
    ) -> List[Dict[str, Any]]:
        """Merge multiple segment breakdowns."""
        merged = {}
        
        for breakdown in breakdowns:
            for item in breakdown:
                seg = item.get("segment")
                if seg not in merged:
                    merged[seg] = {
                        "segment": seg,
                        "transactions": 0,
                        "revenue": 0,
                    }
                merged[seg]["transactions"] += item.get("transactions", 0)
                merged[seg]["revenue"] += item.get("revenue", 0)
        
        return sorted(merged.values(), key=lambda x: x["revenue"], reverse=True)
    
    def _merge_top_products(
        self,
        product_lists: List[List[Dict]],
    ) -> List[Dict[str, Any]]:
        """Merge multiple top product lists."""
        merged = {}
        
        for products in product_lists:
            for item in products:
                name = item.get("product_name")
                if name not in merged:
                    merged[name] = {
                        "product_name": name,
                        "category": item.get("category"),
                        "transactions": 0,
                        "units": 0,
                        "revenue": 0,
                    }
                merged[name]["transactions"] += item.get("transactions", 0)
                merged[name]["units"] += item.get("units", 0)
                merged[name]["revenue"] += item.get("revenue", 0)
        
        return sorted(merged.values(), key=lambda x: x["revenue"], reverse=True)[:10]
    
    def _get_period_revenue(
        self,
        store_id: UUID,
        date_key: date,
    ) -> Optional[Decimal]:
        """Get revenue for a specific date."""
        metric = self._db.scalar(
            select(DailyMetric).where(
                and_(
                    DailyMetric.store_id == store_id,
                    DailyMetric.date_key == date_key,
                )
            )
        )
        return metric.total_revenue if metric else None
    
    def _get_week_revenue(
        self,
        store_id: UUID,
        year: int,
        week: int,
    ) -> Optional[Decimal]:
        """Get revenue for a specific week."""
        metric = self._db.scalar(
            select(WeeklyMetric).where(
                and_(
                    WeeklyMetric.store_id == store_id,
                    WeeklyMetric.year_key == year,
                    WeeklyMetric.week_key == week,
                )
            )
        )
        return metric.total_revenue if metric else None
    
    def _get_month_revenue(
        self,
        store_id: UUID,
        year: int,
        month: int,
    ) -> Optional[Decimal]:
        """Get revenue for a specific month."""
        metric = self._db.scalar(
            select(MonthlyMetric).where(
                and_(
                    MonthlyMetric.store_id == store_id,
                    MonthlyMetric.year_key == year,
                    MonthlyMetric.month_key == month,
                )
            )
        )
        return metric.total_revenue if metric else None
    
    def _log_computation(
        self,
        store_id: UUID,
        granularity: MetricGranularity,
        period_start: datetime,
        period_end: datetime,
        computation_type: str,
        status: str,
        rows_processed: int,
        computation_time_ms: int,
        error_message: str = None,
    ) -> None:
        """Log metric computation for monitoring."""
        log = MetricComputationLog(
            store_id=store_id,
            granularity=granularity,
            period_start=period_start,
            period_end=period_end,
            computation_type=computation_type,
            status=status,
            rows_processed=rows_processed,
            computation_time_ms=computation_time_ms,
            error_message=error_message,
        )
        self._db.add(log)
        self._db.commit()


# ═══════════════════════════════════════════════════════════════════
# SERVICE FACTORY
# ═══════════════════════════════════════════════════════════════════

def get_metrics_aggregation_service(db: Session) -> MetricsAggregationService:
    """Factory function for dependency injection."""
    return MetricsAggregationService(db)
