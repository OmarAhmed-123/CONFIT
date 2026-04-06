"""
CONFIT Backend — Metrics API Schemas
====================================
Pydantic schemas for metrics aggregation API endpoints.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict

from schemas.base import BaseSchema


# ─── Enums ─────────────────────────────────────────────────────────────────────

class MetricGranularity(str, Enum):
    """Time granularity for metric queries."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class DateRangePreset(str, Enum):
    """Predefined date range options."""
    TODAY = "today"
    YESTERDAY = "yesterday"
    THIS_WEEK = "this_week"
    LAST_WEEK = "last_week"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    YTD = "ytd"
    CUSTOM = "custom"


class ComparisonMode(str, Enum):
    """Comparison modes for trend analysis."""
    NONE = "none"
    PREVIOUS_PERIOD = "previous_period"
    YOY = "yoy"  # Year over Year
    MOM = "mom"  # Month over Month
    WOW = "wow"  # Week over Week


class MetricName(str, Enum):
    """Available metric names for selective queries."""
    TOTAL_REVENUE = "totalRevenue"
    TRANSACTION_COUNT = "transactionCount"
    AVG_TRANSACTION_VALUE = "avgTransactionValue"
    TOTAL_PROFIT = "totalProfit"
    AVG_PROFIT_MARGIN = "avgProfitMargin"
    RETURN_RATE = "returnRate"
    RETURN_COUNT = "returnCount"
    UNIQUE_CUSTOMERS = "uniqueCustomers"
    NEW_CUSTOMERS = "newCustomers"
    UNITS_SOLD = "unitsSold"


class RankingType(str, Enum):
    """Types of performance rankings."""
    TOP_REVENUE = "top_revenue"
    TOP_VOLUME = "top_volume"
    BOTTOM_RETURNS = "bottom_returns"
    TOP_MARGIN = "top_margin"
    BOTTOM_MARGIN = "bottom_margin"


# ─── Request Schemas ───────────────────────────────────────────────────────────

class KPIQueryRequest(BaseModel):
    """Request for fetching KPI summary."""
    
    store_id: Optional[str] = Field(
        default=None,
        description="Store ID (from auth context if not provided)"
    )
    
    date_range_preset: DateRangePreset = Field(
        default=DateRangePreset.THIS_MONTH,
        description="Predefined date range or 'custom'"
    )
    
    custom_date_from: Optional[date] = Field(
        default=None,
        description="Start date for custom range"
    )
    
    custom_date_to: Optional[date] = Field(
        default=None,
        description="End date for custom range"
    )
    
    granularity: MetricGranularity = Field(
        default=MetricGranularity.DAILY,
        description="Time granularity for metrics"
    )
    
    metrics: Optional[List[MetricName]] = Field(
        default=None,
        description="Specific metrics to return (all if omitted)"
    )
    
    include_comparisons: bool = Field(
        default=True,
        description="Include previous period comparisons"
    )
    
    comparison_mode: ComparisonMode = Field(
        default=ComparisonMode.PREVIOUS_PERIOD,
        description="How to calculate comparison values"
    )
    
    include_breakdowns: bool = Field(
        default=True,
        description="Include category and segment breakdowns"
    )
    
    skip_cache: bool = Field(
        default=False,
        description="Skip cache and compute fresh metrics"
    )

    @field_validator('custom_date_to')
    @classmethod
    def validate_date_range(cls, v, info):
        if v and info.data.get('custom_date_from'):
            if v < info.data['custom_date_from']:
                raise ValueError('custom_date_to must be after custom_date_from')
        return v


class TrendQueryRequest(BaseModel):
    """Request for fetching metric time-series trends."""
    
    store_id: Optional[str] = Field(default=None)
    
    metric_name: MetricName = Field(
        description="Single metric to track over time"
    )
    
    date_range_preset: DateRangePreset = Field(
        default=DateRangePreset.LAST_30_DAYS
    )
    
    custom_date_from: Optional[date] = Field(default=None)
    custom_date_to: Optional[date] = Field(default=None)
    
    granularity: MetricGranularity = Field(
        default=MetricGranularity.DAILY,
        description="Data point granularity"
    )
    
    compare: ComparisonMode = Field(
        default=ComparisonMode.NONE,
        description="Include comparison series"
    )
    
    include_sparkline: bool = Field(
        default=False,
        description="Include pre-computed sparkline data"
    )


class RankingQueryRequest(BaseModel):
    """Request for fetching performance rankings."""
    
    store_id: Optional[str] = Field(default=None)
    
    ranking_type: RankingType = Field(
        default=RankingType.TOP_REVENUE,
        description="Type of ranking to return"
    )
    
    date_range_preset: DateRangePreset = Field(
        default=DateRangePreset.THIS_MONTH
    )
    
    custom_date_from: Optional[date] = Field(default=None)
    custom_date_to: Optional[date] = Field(default=None)
    
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of items to return"
    )
    
    drill_down: bool = Field(
        default=False,
        description="Include drill-down data (products within categories)"
    )
    
    category: Optional[str] = Field(
        default=None,
        description="Filter to specific category"
    )


class RecalculateRequest(BaseModel):
    """Request for on-demand metric recalculation (admin)."""
    
    store_id: str = Field(description="Store ID to recalculate")
    
    granularity: MetricGranularity = Field(
        description="Granularity level to recalculate"
    )
    
    date_from: date = Field(description="Start date")
    
    date_to: date = Field(description="End date")
    
    cascade: bool = Field(
        default=True,
        description="Also recalculate downstream rollups"
    )
    
    force: bool = Field(
        default=False,
        description="Force recalculation even if metrics are fresh"
    )


# ─── Response Schemas ──────────────────────────────────────────────────────────

class MetricValue(BaseModel):
    """Single metric value with metadata."""
    
    name: str
    value: float
    unit: str = "currency"  # currency, count, percentage
    formatted: Optional[str] = None
    
    # Comparison
    previous_value: Optional[float] = None
    change_absolute: Optional[float] = None
    change_percentage: Optional[float] = None
    trend: Optional[str] = None  # "up", "down", "stable"
    
    # Metadata
    computed_at: datetime
    is_stale: bool = False
    data_source: str = "cache"  # cache, computed, fallback


class KPISummaryResponse(BaseSchema):
    """Response for KPI summary query."""
    
    store_id: str
    date_range: Dict[str, Any]
    granularity: str
    
    # Core KPIs
    metrics: List[MetricValue]
    
    # Breakdowns
    category_breakdown: Optional[List[Dict[str, Any]]] = None
    segment_breakdown: Optional[List[Dict[str, Any]]] = None
    top_products: Optional[List[Dict[str, Any]]] = None
    
    # Metadata
    cached: bool = False
    computed_at: datetime
    computation_time_ms: Optional[int] = None
    staleness_warning: Optional[Dict[str, Any]] = None


class TrendDataPoint(BaseModel):
    """Single data point in a trend series."""
    
    timestamp: datetime
    value: float
    formatted_value: Optional[str] = None
    
    # Comparison data
    comparison_value: Optional[float] = None
    comparison_timestamp: Optional[datetime] = None


class TrendResponse(BaseSchema):
    """Response for metric trend query."""
    
    store_id: str
    metric_name: str
    granularity: str
    date_range: Dict[str, Any]
    
    # Trend data
    data: List[TrendDataPoint]
    
    # Summary stats
    total: float
    average: float
    min: float
    max: float
    
    # Comparison series
    comparison: Optional[Dict[str, Any]] = None
    
    # Sparkline (pre-computed for quick display)
    sparkline: Optional[str] = None  # Base64 encoded or SVG
    
    # Metadata
    cached: bool = False
    computed_at: datetime


class RankingItem(BaseModel):
    """Single item in a ranking."""
    
    rank: int
    name: str
    category: Optional[str] = None
    value: float
    formatted_value: str
    change_from_last: Optional[float] = None
    
    # Drill-down data
    drill_down_data: Optional[List[Dict[str, Any]]] = None


class RankingResponse(BaseSchema):
    """Response for ranking query."""
    
    store_id: str
    ranking_type: str
    date_range: Dict[str, Any]
    
    rankings: List[RankingItem]
    
    # Metadata
    cached: bool = False
    computed_at: datetime


class RecalculateResponse(BaseSchema):
    """Response for recalculation request."""
    
    success: bool
    store_id: str
    granularity: str
    date_range: Dict[str, Any]
    
    # Results
    metrics_computed: int
    computation_time_ms: int
    
    # Cascade results
    cascade_results: Optional[List[Dict[str, Any]]] = None
    
    # Errors
    errors: Optional[List[str]] = None


# ─── Health & Monitoring Schemas ───────────────────────────────────────────────

class ComponentHealth(BaseModel):
    """Health status of a component."""
    
    status: str  # healthy, degraded, unhealthy
    message: Optional[str] = None
    last_check: datetime
    details: Optional[Dict[str, Any]] = None


class MetricsHealthResponse(BaseSchema):
    """Response for metrics service health check."""
    
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    
    components: Dict[str, ComponentHealth]
    
    # Aggregate metrics
    metrics: Dict[str, Any]
    
    # Stale metrics alert
    stale_metrics: Optional[List[Dict[str, Any]]] = None


class StaleMetricAlert(BaseModel):
    """Alert for a stale metric."""
    
    store_id: str
    granularity: str
    period: str
    staleness_seconds: float
    computed_at: datetime


class ComputationLogEntry(BaseSchema):
    """Entry from computation log."""
    
    id: str
    store_id: Optional[str]
    granularity: str
    period_start: datetime
    period_end: datetime
    computation_type: str
    status: str
    rows_processed: int
    computation_time_ms: int
    error_message: Optional[str]
    computed_at: datetime


# ─── Real-time KPI Schemas ────────────────────────────────────────────────────

class RealtimeKPIResponse(BaseSchema):
    """Response for real-time KPI query."""
    
    store_id: str
    
    # Today's metrics
    today: Dict[str, Any]
    
    # This week
    this_week: Dict[str, Any]
    
    # This month
    this_month: Dict[str, Any]
    
    # Comparisons
    comparisons: Dict[str, Any]
    
    # Quick stats
    quick_stats: Dict[str, Any]
    
    # Top performers
    top_performers: Dict[str, Any]
    
    # Alerts
    alerts: Dict[str, Any]
    
    # Metadata
    cached: bool = False
    computed_at: datetime
    staleness_seconds: float = 0
    staleness_warning: Optional[Dict[str, Any]] = None


# ─── Helper Functions ──────────────────────────────────────────────────────────

def format_metric_value(value: float, unit: str, currency: str = "EGP") -> str:
    """Format a metric value for display."""
    if unit == "currency":
        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M {currency}"
        elif value >= 1_000:
            return f"{value / 1_000:.1f}K {currency}"
        return f"{value:.2f} {currency}"
    elif unit == "percentage":
        return f"{value:.1f}%"
    elif unit == "count":
        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        elif value >= 1_000:
            return f"{value / 1_000:.1f}K"
        return str(int(value))
    return str(value)


def calculate_trend(change_pct: Optional[float]) -> str:
    """Determine trend direction from percentage change."""
    if change_pct is None:
        return "stable"
    if change_pct > 2:
        return "up"
    elif change_pct < -2:
        return "down"
    return "stable"
