"""
CONFIT Backend — Metrics Aggregation Database Models
====================================================
SQLAlchemy models for pre-computed metrics storage.
Designed for time-series queries with store-scoped isolation.
"""

import enum
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Numeric,
    Enum as SQLEnum,
    Index,
    UniqueConstraint,
    CheckConstraint,
    text,
    func,
    select,
    Date,
    SmallInteger,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from database.base import Base, JSONType, SCHEMA  # Use JSONType for SQLite/PostgreSQL compatibility
from database.models import UUIDType, _new_uuid


# ═══════════════════════════════════════════════════════════════════
# ENUMERATED TYPES
# ═══════════════════════════════════════════════════════════════════

class MetricGranularity(str, enum.Enum):
    """Time granularity for aggregated metrics."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class MetricStatus(str, enum.Enum):
    """Status of metric computation."""
    FRESH = "fresh"
    STALE = "stale"
    COMPUTING = "computing"
    FAILED = "failed"


class ComparisonMode(str, enum.Enum):
    """Comparison modes for trend analysis."""
    NONE = "none"
    PREVIOUS_PERIOD = "previous_period"
    YOY = "yoy"  # Year over Year
    MOM = "mom"  # Month over Month
    WOW = "wow"  # Week over Week


# ═══════════════════════════════════════════════════════════════════
# BASE METRIC MODEL (Abstract)
# ═══════════════════════════════════════════════════════════════════

class BaseMetricModel:
    """
    Shared columns for all metric tables.
    Provides common fields for time-series metric storage.
    """
    
    # Primary Key
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    
    # Store isolation (required for all queries)
    store_id = Column(
        UUIDType, 
        ForeignKey("stores.id"), 
        nullable=False,
        index=True
    )
    
    # ─── Revenue Metrics ─────────────────────────────────────────────
    total_revenue = Column(
        Numeric(14, 2), 
        nullable=False, 
        default=Decimal("0.00")
    )
    revenue_delta = Column(
        Numeric(14, 2),
        nullable=True,
        comment="Change from previous period"
    )
    revenue_change_pct = Column(
        Numeric(6, 2),
        nullable=True,
        comment="Percentage change from previous period"
    )
    
    # ─── Transaction Metrics ────────────────────────────────────────
    transaction_count = Column(Integer, nullable=False, default=0)
    transaction_count_delta = Column(Integer, nullable=True)
    transaction_count_change_pct = Column(Numeric(6, 2), nullable=True)
    
    units_sold = Column(Integer, nullable=False, default=0)
    units_sold_delta = Column(Integer, nullable=True)
    
    avg_transaction_value = Column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    atv_delta = Column(Numeric(10, 2), nullable=True)
    atv_change_pct = Column(Numeric(6, 2), nullable=True)
    
    # ─── Profitability Metrics ───────────────────────────────────────
    total_profit = Column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    total_profit_delta = Column(Numeric(14, 2), nullable=True)
    
    avg_profit_margin = Column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    avg_profit_margin_delta = Column(Numeric(5, 2), nullable=True)
    profit_margin_change_pct = Column(Numeric(6, 2), nullable=True)
    
    # ─── Return Metrics ──────────────────────────────────────────────
    return_count = Column(Integer, nullable=False, default=0)
    return_count_delta = Column(Integer, nullable=True)
    
    return_amount = Column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00")
    )
    return_amount_delta = Column(Numeric(12, 2), nullable=True)
    
    return_rate = Column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Percentage of transactions returned"
    )
    return_rate_delta = Column(Numeric(5, 2), nullable=True)
    
    # ─── Customer Metrics ────────────────────────────────────────────
    unique_customers = Column(Integer, nullable=False, default=0)
    unique_customers_delta = Column(Integer, nullable=True)
    
    new_customers = Column(Integer, nullable=False, default=0)
    new_customers_delta = Column(Integer, nullable=True)
    
    returning_customers = Column(Integer, nullable=False, default=0)
    returning_customers_delta = Column(Integer, nullable=True)
    
    vip_customers = Column(Integer, nullable=False, default=0)
    vip_customers_delta = Column(Integer, nullable=True)
    
    # ─── Breakdown Data (JSONB) ─────────────────────────────────────
    category_breakdown = Column(
        JSONB,
        nullable=False,
        default=list,
        comment="Revenue/transactions by category"
    )
    segment_breakdown = Column(
        JSONB,
        nullable=False,
        default=list,
        comment="Revenue/transactions by customer segment"
    )
    top_products = Column(
        JSONB,
        nullable=False,
        default=list,
        comment="Top products by revenue"
    )
    bottom_products = Column(
        JSONB,
        nullable=False,
        default=list,
        comment="Bottom products by return rate"
    )
    
    # ─── Metadata ───────────────────────────────────────────────────
    status = Column(
        SQLEnum(MetricStatus, name="metric_status_enum"),
        nullable=False,
        default=MetricStatus.FRESH
    )
    
    computed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    computation_time_ms = Column(
        Integer,
        nullable=True,
        comment="Time taken to compute this metric"
    )
    
    rows_processed = Column(
        Integer,
        nullable=True,
        comment="Number of transaction rows processed"
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


# ═══════════════════════════════════════════════════════════════════
# HOURLY METRICS MODEL
# ═══════════════════════════════════════════════════════════════════

class HourlyMetric(Base, BaseMetricModel):
    """
    Pre-computed metrics at hourly granularity.
    
    Used for:
    - Real-time dashboard updates
    - Intraday trend analysis
    - Daily rollup source
    
    Retention: 7 days (high-frequency data)
    """
    __tablename__ = "hourly_metrics"
    __table_args__ = (
        # Unique constraint: one row per store per hour
        UniqueConstraint("store_id", "hour_key", name="uq_hourly_metric_store_hour"),
        
        # Indexes for common query patterns
        Index(
            "ix_hourly_metrics_store_date",
            "store_id",
            "hour_key",
            postgresql_using="btree"
        ),
        Index(
            "ix_hourly_metrics_stale",
            "store_id",
            "status",
            "computed_at",
            postgresql_where=text("status = 'stale'")
        ),
        Index(
            "ix_hourly_metrics_recent",
            "store_id",
            "hour_key",
            postgresql_where=text("hour_key >= CURRENT_DATE - INTERVAL '7 days'")
        ),
        
        {"extend_existing": True, **({"schema": "public"} if SCHEMA else {})},
    )
    
    # Time dimension (hour granularity)
    hour_key = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Start of the hour (e.g., 2026-04-05 14:00:00)"
    )
    
    date_key = Column(
        Date,
        nullable=False,
        comment="Date for daily rollup queries"
    )
    
    hour_of_day = Column(
        SmallInteger,
        nullable=False,
        comment="Hour 0-23 for hourly pattern analysis"
    )
    
    day_of_week = Column(
        SmallInteger,
        nullable=False,
        comment="Day 0-6 (Monday=0) for weekly patterns"
    )
    
    # Relationships
    store = relationship("Store", backref="hourly_metrics")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "store_id": str(self.store_id),
            "hour_key": self.hour_key.isoformat() if self.hour_key else None,
            "date_key": self.date_key.isoformat() if self.date_key else None,
            "hour_of_day": self.hour_of_day,
            "day_of_week": self.day_of_week,
            "granularity": "hourly",
            "revenue": {
                "total": float(self.total_revenue),
                "delta": float(self.revenue_delta) if self.revenue_delta else None,
                "change_pct": float(self.revenue_change_pct) if self.revenue_change_pct else None,
            },
            "transactions": {
                "count": self.transaction_count,
                "delta": self.transaction_count_delta,
                "change_pct": float(self.transaction_count_change_pct) if self.transaction_count_change_pct else None,
                "units_sold": self.units_sold,
                "avg_value": float(self.avg_transaction_value),
            },
            "profit": {
                "total": float(self.total_profit),
                "avg_margin": float(self.avg_profit_margin),
                "margin_change_pct": float(self.profit_margin_change_pct) if self.profit_margin_change_pct else None,
            },
            "returns": {
                "count": self.return_count,
                "amount": float(self.return_amount),
                "rate": float(self.return_rate),
            },
            "customers": {
                "unique": self.unique_customers,
                "new": self.new_customers,
                "returning": self.returning_customers,
                "vip": self.vip_customers,
            },
            "breakdowns": {
                "category": self.category_breakdown,
                "segment": self.segment_breakdown,
                "top_products": self.top_products,
            },
            "metadata": {
                "status": self.status.value if self.status else None,
                "computed_at": self.computed_at.isoformat() if self.computed_at else None,
                "computation_time_ms": self.computation_time_ms,
                "rows_processed": self.rows_processed,
            },
        }


# ═══════════════════════════════════════════════════════════════════
# DAILY METRICS MODEL
# ═══════════════════════════════════════════════════════════════════

class DailyMetric(Base, BaseMetricModel):
    """
    Pre-computed metrics at daily granularity.
    
    Used for:
    - Daily dashboard cards
    - Week-to-date comparisons
    - Weekly/Monthly rollup source
    
    Retention: 2 years
    """
    __tablename__ = "daily_metrics"
    __table_args__ = (
        UniqueConstraint("store_id", "date_key", name="uq_daily_metric_store_date"),
        
        Index(
            "ix_daily_metrics_store_date",
            "store_id",
            "date_key",
            postgresql_using="btree"
        ),
        Index(
            "ix_daily_metrics_month",
            "store_id",
            "year_key",
            "month_key",
        ),
        Index(
            "ix_daily_metrics_stale",
            "store_id",
            "status",
            "computed_at",
            postgresql_where=text("status = 'stale'")
        ),
        
        {"extend_existing": True, **({"schema": "public"} if SCHEMA else {})},
    )
    
    # Time dimension (day granularity)
    date_key = Column(Date, nullable=False)
    
    # Pre-computed date parts for efficient filtering
    year_key = Column(SmallInteger, nullable=False)
    month_key = Column(SmallInteger, nullable=False)  # 1-12
    week_key = Column(SmallInteger, nullable=True)    # ISO week number
    day_of_week = Column(SmallInteger, nullable=False)  # 0-6 (Monday=0)
    day_of_month = Column(SmallInteger, nullable=False)  # 1-31
    
    is_weekend = Column(Boolean, nullable=False, default=False)
    is_holiday = Column(Boolean, nullable=False, default=False)
    
    # Comparison values (pre-computed for performance)
    previous_day_revenue = Column(Numeric(14, 2), nullable=True)
    previous_week_revenue = Column(Numeric(14, 2), nullable=True)  # Same day last week
    previous_month_revenue = Column(Numeric(14, 2), nullable=True)  # Same day last month
    
    # Relationships
    store = relationship("Store", backref="daily_metrics")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "store_id": str(self.store_id),
            "date_key": self.date_key.isoformat() if self.date_key else None,
            "granularity": "daily",
            "date_parts": {
                "year": self.year_key,
                "month": self.month_key,
                "week": self.week_key,
                "day_of_week": self.day_of_week,
                "day_of_month": self.day_of_month,
                "is_weekend": self.is_weekend,
                "is_holiday": self.is_holiday,
            },
            "revenue": {
                "total": float(self.total_revenue),
                "delta": float(self.revenue_delta) if self.revenue_delta else None,
                "change_pct": float(self.revenue_change_pct) if self.revenue_change_pct else None,
                "comparisons": {
                    "previous_day": float(self.previous_day_revenue) if self.previous_day_revenue else None,
                    "previous_week": float(self.previous_week_revenue) if self.previous_week_revenue else None,
                    "previous_month": float(self.previous_month_revenue) if self.previous_month_revenue else None,
                },
            },
            "transactions": {
                "count": self.transaction_count,
                "units_sold": self.units_sold,
                "avg_value": float(self.avg_transaction_value),
            },
            "profit": {
                "total": float(self.total_profit),
                "avg_margin": float(self.avg_profit_margin),
            },
            "returns": {
                "count": self.return_count,
                "rate": float(self.return_rate),
            },
            "customers": {
                "unique": self.unique_customers,
                "new": self.new_customers,
            },
            "breakdowns": {
                "category": self.category_breakdown,
                "segment": self.segment_breakdown,
                "top_products": self.top_products,
            },
            "metadata": {
                "status": self.status.value if self.status else None,
                "computed_at": self.computed_at.isoformat() if self.computed_at else None,
            },
        }


# ═══════════════════════════════════════════════════════════════════
# WEEKLY METRICS MODEL
# ═══════════════════════════════════════════════════════════════════

class WeeklyMetric(Base, BaseMetricModel):
    """
    Pre-computed metrics at weekly granularity (ISO week).
    
    Used for:
    - Week-over-week trend analysis
    - Monthly rollup source
    - Executive summary reports
    
    Retention: 3 years
    """
    __tablename__ = "weekly_metrics"
    __table_args__ = (
        UniqueConstraint("store_id", "year_key", "week_key", name="uq_weekly_metric_store_week"),
        
        Index(
            "ix_weekly_metrics_store_week",
            "store_id",
            "year_key",
            "week_key",
        ),
        Index(
            "ix_weekly_metrics_year",
            "store_id",
            "year_key",
        ),
        
        {"extend_existing": True, **({"schema": "public"} if SCHEMA else {})},
    )
    
    # Time dimension (ISO week)
    year_key = Column(SmallInteger, nullable=False)  # ISO year
    week_key = Column(SmallInteger, nullable=False)  # ISO week 1-53
    
    week_start_date = Column(Date, nullable=False)  # Monday of the week
    week_end_date = Column(Date, nullable=False)    # Sunday of the week
    
    # Comparison values
    previous_week_revenue = Column(Numeric(14, 2), nullable=True)
    previous_year_week_revenue = Column(Numeric(14, 2), nullable=True)  # YoY
    
    # Store relationship
    store = relationship("Store", backref="weekly_metrics")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "store_id": str(self.store_id),
            "granularity": "weekly",
            "week": {
                "year": self.year_key,
                "week_number": self.week_key,
                "start_date": self.week_start_date.isoformat() if self.week_start_date else None,
                "end_date": self.week_end_date.isoformat() if self.week_end_date else None,
            },
            "revenue": {
                "total": float(self.total_revenue),
                "change_pct": float(self.revenue_change_pct) if self.revenue_change_pct else None,
                "comparisons": {
                    "previous_week": float(self.previous_week_revenue) if self.previous_week_revenue else None,
                    "yoy": float(self.previous_year_week_revenue) if self.previous_year_week_revenue else None,
                },
            },
            "transactions": {
                "count": self.transaction_count,
                "units_sold": self.units_sold,
                "avg_value": float(self.avg_transaction_value),
            },
            "profit": {
                "total": float(self.total_profit),
                "avg_margin": float(self.avg_profit_margin),
            },
            "returns": {
                "count": self.return_count,
                "rate": float(self.return_rate),
            },
            "breakdowns": {
                "category": self.category_breakdown,
                "top_products": self.top_products,
            },
            "metadata": {
                "status": self.status.value if self.status else None,
                "computed_at": self.computed_at.isoformat() if self.computed_at else None,
            },
        }


# ═══════════════════════════════════════════════════════════════════
# MONTHLY METRICS MODEL
# ═══════════════════════════════════════════════════════════════════

class MonthlyMetric(Base, BaseMetricModel):
    """
    Pre-computed metrics at monthly granularity.
    
    Used for:
    - Month-over-month trend analysis
    - Year-over-year comparisons
    - Executive dashboards
    - Annual reports
    
    Retention: 5 years
    """
    __tablename__ = "monthly_metrics"
    __table_args__ = (
        UniqueConstraint("store_id", "year_key", "month_key", name="uq_monthly_metric_store_month"),
        
        Index(
            "ix_monthly_metrics_store_month",
            "store_id",
            "year_key",
            "month_key",
        ),
        Index(
            "ix_monthly_metrics_year",
            "store_id",
            "year_key",
        ),
        
        {"extend_existing": True, **({"schema": "public"} if SCHEMA else {})},
    )
    
    # Time dimension (month)
    year_key = Column(SmallInteger, nullable=False)
    month_key = Column(SmallInteger, nullable=False)  # 1-12
    
    month_start_date = Column(Date, nullable=False)
    month_end_date = Column(Date, nullable=False)
    days_in_month = Column(SmallInteger, nullable=False)
    
    # Comparison values
    previous_month_revenue = Column(Numeric(14, 2), nullable=True)
    previous_year_month_revenue = Column(Numeric(14, 2), nullable=True)  # YoY
    
    # YTD accumulator
    ytd_revenue = Column(Numeric(14, 2), nullable=True)
    ytd_transactions = Column(Integer, nullable=True)
    
    # Store relationship
    store = relationship("Store", backref="monthly_metrics")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "store_id": str(self.store_id),
            "granularity": "monthly",
            "month": {
                "year": self.year_key,
                "month_number": self.month_key,
                "start_date": self.month_start_date.isoformat() if self.month_start_date else None,
                "end_date": self.month_end_date.isoformat() if self.month_end_date else None,
                "days": self.days_in_month,
            },
            "revenue": {
                "total": float(self.total_revenue),
                "change_pct": float(self.revenue_change_pct) if self.revenue_change_pct else None,
                "comparisons": {
                    "previous_month": float(self.previous_month_revenue) if self.previous_month_revenue else None,
                    "yoy": float(self.previous_year_month_revenue) if self.previous_year_month_revenue else None,
                },
                "ytd": float(self.ytd_revenue) if self.ytd_revenue else None,
            },
            "transactions": {
                "count": self.transaction_count,
                "units_sold": self.units_sold,
                "avg_value": float(self.avg_transaction_value),
                "ytd": self.ytd_transactions,
            },
            "profit": {
                "total": float(self.total_profit),
                "avg_margin": float(self.avg_profit_margin),
            },
            "returns": {
                "count": self.return_count,
                "rate": float(self.return_rate),
            },
            "breakdowns": {
                "category": self.category_breakdown,
                "segment": self.segment_breakdown,
                "top_products": self.top_products,
            },
            "metadata": {
                "status": self.status.value if self.status else None,
                "computed_at": self.computed_at.isoformat() if self.computed_at else None,
            },
        }


# ═══════════════════════════════════════════════════════════════════
# REAL-TIME KPI CACHE MODEL
# ═══════════════════════════════════════════════════════════════════

class RealtimeKPICache(Base):
    """
    Ultra-fast cache for real-time dashboard KPIs.
    
    Updated via streaming on every transaction.
    Single row per store.
    
    TTL: 30 seconds (served stale with warning if older)
    """
    __tablename__ = "realtime_kpi_cache"
    __table_args__ = (
        UniqueConstraint("store_id", name="uq_realtime_kpi_store"),
        
        {"extend_existing": True, **({"schema": "public"} if SCHEMA else {})},
    )
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    store_id = Column(UUIDType, ForeignKey("stores.id"), nullable=False, unique=True)
    
    # Today's metrics (updated in real-time)
    today_revenue = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    today_transactions = Column(Integer, nullable=False, default=0)
    today_units_sold = Column(Integer, nullable=False, default=0)
    today_new_customers = Column(Integer, nullable=False, default=0)
    
    # This week metrics
    week_revenue = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    week_transactions = Column(Integer, nullable=False, default=0)
    
    # This month metrics
    month_revenue = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    month_transactions = Column(Integer, nullable=False, default=0)
    
    # Comparison values (updated hourly)
    yesterday_revenue = Column(Numeric(14, 2), nullable=True)
    last_week_revenue = Column(Numeric(14, 2), nullable=True)
    last_month_revenue = Column(Numeric(14, 2), nullable=True)
    
    # Quick stats
    avg_margin_30d = Column(Numeric(5, 2), nullable=True)
    return_rate_30d = Column(Numeric(5, 2), nullable=True)
    
    # Top performers (updated hourly)
    top_category_today = Column(String(50), nullable=True)
    top_product_today = Column(String(255), nullable=True)
    
    # Alerts
    low_stock_alerts = Column(Integer, nullable=False, default=0)
    high_return_alerts = Column(Integer, nullable=False, default=0)
    
    # Metadata
    computed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    last_transaction_at = Column(DateTime(timezone=True), nullable=True)
    
    # Version for optimistic locking
    version = Column(Integer, nullable=False, default=1)
    
    # Store relationship
    store = relationship("Store", backref="realtime_kpi_cache")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "store_id": str(self.store_id),
            "today": {
                "revenue": float(self.today_revenue),
                "transactions": self.today_transactions,
                "units_sold": self.today_units_sold,
                "new_customers": self.today_new_customers,
            },
            "this_week": {
                "revenue": float(self.week_revenue),
                "transactions": self.week_transactions,
            },
            "this_month": {
                "revenue": float(self.month_revenue),
                "transactions": self.month_transactions,
            },
            "comparisons": {
                "vs_yesterday": self._calc_change(self.today_revenue, self.yesterday_revenue),
                "vs_last_week": self._calc_change(self.week_revenue, self.last_week_revenue),
                "vs_last_month": self._calc_change(self.month_revenue, self.last_month_revenue),
            },
            "quick_stats": {
                "avg_margin_30d": float(self.avg_margin_30d) if self.avg_margin_30d else None,
                "return_rate_30d": float(self.return_rate_30d) if self.return_rate_30d else None,
            },
            "top_performers": {
                "category": self.top_category_today,
                "product": self.top_product_today,
            },
            "alerts": {
                "low_stock": self.low_stock_alerts,
                "high_returns": self.high_return_alerts,
            },
            "metadata": {
                "computed_at": self.computed_at.isoformat() if self.computed_at else None,
                "last_transaction_at": self.last_transaction_at.isoformat() if self.last_transaction_at else None,
                "staleness_seconds": self._get_staleness(),
            },
        }
    
    def _calc_change(self, current, previous) -> Optional[Dict]:
        """Calculate percentage change."""
        if current is None or previous is None or previous == 0:
            return None
        change = float(current - previous)
        pct = (change / float(previous)) * 100
        return {
            "absolute": change,
            "percentage": round(pct, 2),
        }
    
    def _get_staleness(self) -> float:
        """Get staleness in seconds."""
        if not self.computed_at:
            return 0
        return (datetime.now(timezone.utc) - self.computed_at).total_seconds()


# ═══════════════════════════════════════════════════════════════════
# METRIC COMPUTATION LOG MODEL
# ═══════════════════════════════════════════════════════════════════

class MetricComputationLog(Base):
    """
    Log of metric computation runs for monitoring and debugging.
    """
    __tablename__ = "metric_computation_logs"
    __table_args__ = (
        Index("ix_computation_logs_store_time", "store_id", "computed_at"),
        Index("ix_computation_logs_granularity", "granularity", "computed_at"),
        {"extend_existing": True, **({"schema": "public"} if SCHEMA else {})},
    )
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    store_id = Column(UUIDType, ForeignKey("stores.id"), nullable=True)  # Null for system-wide
    
    granularity = Column(
        SQLEnum(MetricGranularity, name="metric_granularity_enum"),
        nullable=False
    )
    
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Computation details
    computation_type = Column(
        String(20),
        nullable=False,
        comment="full_recalc, incremental, rollup"
    )
    
    status = Column(
        String(20),
        nullable=False,
        comment="success, failed, partial"
    )
    
    rows_processed = Column(Integer, nullable=False, default=0)
    rows_inserted = Column(Integer, nullable=False, default=0)
    rows_updated = Column(Integer, nullable=False, default=0)
    
    computation_time_ms = Column(Integer, nullable=False)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_stack = Column(Text, nullable=True)
    
    # Metadata
    computed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    computed_by = Column(String(100), nullable=True)  # Worker ID or scheduler
    
    # Relationships
    store = relationship("Store", backref="computation_logs")
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "store_id": str(self.store_id) if self.store_id else None,
            "granularity": self.granularity.value,
            "period": {
                "start": self.period_start.isoformat() if self.period_start else None,
                "end": self.period_end.isoformat() if self.period_end else None,
            },
            "computation_type": self.computation_type,
            "status": self.status,
            "metrics": {
                "rows_processed": self.rows_processed,
                "rows_inserted": self.rows_inserted,
                "rows_updated": self.rows_updated,
                "time_ms": self.computation_time_ms,
            },
            "error": {
                "message": self.error_message,
            } if self.error_message else None,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
        }


# ═══════════════════════════════════════════════════════════════════
# METRIC UPDATE QUEUE MODEL
# ═══════════════════════════════════════════════════════════════════

class MetricUpdateQueue(Base):
    """
    Queue for pending metric updates (debouncing rapid transactions).
    
    Groups transactions by store/hour for batch processing.
    """
    __tablename__ = "metric_update_queue"
    __table_args__ = (
        Index("ix_metric_queue_pending", "status", "scheduled_at"),
        Index("ix_metric_queue_store_hour", "store_id", "hour_key"),
        {"extend_existing": True, **({"schema": "public"} if SCHEMA else {})},
    )
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    store_id = Column(UUIDType, ForeignKey("stores.id"), nullable=False)
    
    # Target metric
    granularity = Column(
        SQLEnum(MetricGranularity, name="metric_granularity_enum"),
        nullable=False
    )
    hour_key = Column(DateTime(timezone=True), nullable=True)  # For hourly
    date_key = Column(Date, nullable=True)  # For daily/weekly/monthly
    
    # Delta values to apply
    delta_revenue = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    delta_transactions = Column(Integer, nullable=False, default=0)
    delta_units = Column(Integer, nullable=False, default=0)
    delta_returns = Column(Integer, nullable=False, default=0)
    delta_return_amount = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    
    # Transaction references
    transaction_ids = Column(JSONType, nullable=False, default=list)
    
    # Status
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        comment="pending, processing, completed, failed"
    )
    
    scheduled_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    store = relationship("Store", backref="metric_update_queue")
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "store_id": str(self.store_id),
            "granularity": self.granularity.value,
            "target": {
                "hour_key": self.hour_key.isoformat() if self.hour_key else None,
                "date_key": self.date_key.isoformat() if self.date_key else None,
            },
            "deltas": {
                "revenue": float(self.delta_revenue),
                "transactions": self.delta_transactions,
                "units": self.delta_units,
                "returns": self.delta_returns,
            },
            "status": self.status,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
        }
