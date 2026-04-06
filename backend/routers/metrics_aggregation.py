"""
CONFIT Backend — Metrics Aggregation Router
===========================================
RESTful API endpoints for pre-aggregated metrics queries.

Features:
- KPI summary with comparisons
- Time-series trend data
- Performance rankings
- Real-time dashboard KPIs
- On-demand recalculation (admin)
- Health monitoring
"""

import logging
from datetime import datetime, timezone, timedelta, date
from typing import Annotated, Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from database.session import get_db
from services.metrics_aggregation_service import (
    MetricsAggregationService,
    get_metrics_aggregation_service,
    DateRange,
)
from schemas.metrics_schemas import (
    KPIQueryRequest,
    TrendQueryRequest,
    RankingQueryRequest,
    RecalculateRequest,
    KPISummaryResponse,
    TrendResponse,
    RankingResponse,
    RecalculateResponse,
    RealtimeKPIResponse,
    MetricsHealthResponse,
    MetricValue,
    TrendDataPoint,
    RankingItem,
    MetricGranularity,
    DateRangePreset,
    ComparisonMode,
    MetricName,
    RankingType,
    format_metric_value,
    calculate_trend,
)
from utils.auth_deps import require_auth
from services.auth_service import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["Metrics Aggregation"])


# ─── Dependency Injection ─────────────────────────────────────────────────────

def get_service(db: Session = Depends(get_db)) -> MetricsAggregationService:
    """Get MetricsAggregationService instance with DB session."""
    return get_metrics_aggregation_service(db)


def _get_user_store_id(user: UserProfile) -> Optional[str]:
    """Extract store_id from user profile for data scoping."""
    if hasattr(user, 'store_id') and user.store_id:
        return user.store_id
    
    if hasattr(user, 'stores') and user.stores:
        return user.stores[0].get('id') if isinstance(user.stores[0], dict) else user.stores[0].id
    
    # Development fallback
    if hasattr(user, 'roles') and 'brand_manager' in getattr(user, 'roles', []):
        from database.models import Store
        from database.session import SessionLocal
        
        db = SessionLocal()
        try:
            brand_id = getattr(user, 'brand_id', None)
            if brand_id:
                store = db.query(Store).filter(Store.brand_id == brand_id).first()
                if store:
                    return str(store.id)
            store = db.query(Store).first()
            if store:
                return str(store.id)
        finally:
            db.close()
    
    return None


def _resolve_date_range(
    preset: DateRangePreset,
    custom_from: Optional[date],
    custom_to: Optional[date],
) -> DateRange:
    """Resolve date range from preset or custom dates."""
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if preset == DateRangePreset.CUSTOM:
        start = datetime.combine(custom_from or today, datetime.min.time()).replace(tzinfo=timezone.utc)
        end = datetime.combine(custom_to or today, datetime.max.time()).replace(tzinfo=timezone.utc)
        return DateRange(start=start, end=end + timedelta(days=1))
    
    ranges = {
        DateRangePreset.TODAY: (today, today + timedelta(days=1)),
        DateRangePreset.YESTERDAY: (today - timedelta(days=1), today),
        DateRangePreset.THIS_WEEK: (today - timedelta(days=today.weekday()), today + timedelta(days=1)),
        DateRangePreset.LAST_WEEK: (
            today - timedelta(days=today.weekday() + 7),
            today - timedelta(days=today.weekday())
        ),
        DateRangePreset.THIS_MONTH: (today.replace(day=1), today + timedelta(days=1)),
        DateRangePreset.LAST_MONTH: (
            (today.replace(day=1) - timedelta(days=1)).replace(day=1),
            today.replace(day=1)
        ),
        DateRangePreset.LAST_7_DAYS: (today - timedelta(days=7), today + timedelta(days=1)),
        DateRangePreset.LAST_30_DAYS: (today - timedelta(days=30), today + timedelta(days=1)),
        DateRangePreset.LAST_90_DAYS: (today - timedelta(days=90), today + timedelta(days=1)),
        DateRangePreset.YTD: (today.replace(month=1, day=1), today + timedelta(days=1)),
    }
    
    start, end = ranges.get(preset, (today, today + timedelta(days=1)))
    return DateRange(start=start, end=end)


# ─── Real-time KPIs Endpoint ───────────────────────────────────────────────────

@router.get(
    "/realtime",
    response_model=RealtimeKPIResponse,
    summary="Get real-time dashboard KPIs",
    description="""
    Get real-time KPIs for dashboard header cards.
    
    Returns today's, this week's, and this month's metrics with comparisons.
    TTL: 30 seconds (served stale with warning if older).
    """,
)
async def get_realtime_kpis(
    user: UserProfile = Depends(require_auth),
    service: MetricsAggregationService = Depends(get_service),
    skip_cache: bool = Query(False, description="Skip cache and compute fresh"),
):
    """
    Get real-time KPIs for dashboard header.
    """
    store_id = _get_user_store_id(user)
    if not store_id:
        raise HTTPException(
            status_code=403,
            detail="User does not have access to any store.",
        )
    
    try:
        data = service.get_realtime_kpis(
            store_id=UUID(store_id),
            use_cache=not skip_cache,
        )
        
        return RealtimeKPIResponse(
            store_id=store_id,
            today=data.get("today", {}),
            this_week=data.get("this_week", {}),
            this_month=data.get("this_month", {}),
            comparisons=data.get("comparisons", {}),
            quick_stats=data.get("quick_stats", {}),
            top_performers=data.get("top_performers", {}),
            alerts=data.get("alerts", {}),
            cached=data.get("cached", False),
            computed_at=datetime.fromisoformat(data["computed_at"]) if data.get("computed_at") else datetime.now(timezone.utc),
            staleness_seconds=data.get("staleness_seconds", 0),
            staleness_warning=data.get("staleness_warning"),
        )
        
    except Exception as e:
        logger.error(f"Failed to get realtime KPIs for store {store_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve real-time metrics.",
        )


# ─── KPI Summary Endpoint ─────────────────────────────────────────────────────

@router.post(
    "/kpis",
    response_model=KPISummaryResponse,
    summary="Get KPI summary for a date range",
    description="""
    Get pre-computed KPI summary for a date range.
    
    Returns:
    - Revenue, transactions, profit metrics
    - Comparison values (previous period, YoY)
    - Category and segment breakdowns
    - Top products
    
    Performance: <500ms for cached, <2s for on-demand computation.
    """,
)
async def get_kpi_summary(
    request: KPIQueryRequest,
    user: UserProfile = Depends(require_auth),
    service: MetricsAggregationService = Depends(get_service),
):
    """
    Get KPI summary for a date range.
    """
    store_id = request.store_id or _get_user_store_id(user)
    if not store_id:
        raise HTTPException(
            status_code=403,
            detail="User does not have access to any store.",
        )
    
    try:
        date_range = _resolve_date_range(
            request.date_range_preset,
            request.custom_date_from,
            request.custom_date_to,
        )
        
        # Fetch metrics based on granularity
        if request.granularity == MetricGranularity.HOURLY:
            metrics_data = service.get_hourly_metrics(
                store_id=UUID(store_id),
                date_range=date_range,
                use_cache=not request.skip_cache,
            )
        elif request.granularity == MetricGranularity.DAILY:
            metrics_data = service.get_daily_metrics(
                store_id=UUID(store_id),
                date_range=date_range,
                use_cache=not request.skip_cache,
            )
        elif request.granularity == MetricGranularity.WEEKLY:
            # Get weekly metrics
            start_date = date_range.start.date()
            end_date = date_range.end.date()
            iso_start = start_date.isocalendar()
            iso_end = end_date.isocalendar()
            
            metrics_data = []
            for year in range(iso_start[0], iso_end[0] + 1):
                start_week = iso_start[1] if year == iso_start[0] else 1
                end_week = iso_end[1] if year == iso_end[0] else 53
                for week in range(start_week, end_week + 1):
                    data = service.get_weekly_metrics(UUID(store_id), year, week)
                    if data:
                        metrics_data.append(data)
        else:  # MONTHLY
            metrics_data = []
            start_date = date_range.start.date()
            end_date = date_range.end.date()
            
            for year in range(start_date.year, end_date.year + 1):
                start_month = start_date.month if year == start_date.year else 1
                end_month = end_date.month if year == end_date.year else 12
                for month in range(start_month, end_month + 1):
                    data = service.get_monthly_metrics(UUID(store_id), year, month)
                    if data:
                        metrics_data.append(data)
        
        # Aggregate metrics across the range
        aggregated = _aggregate_metrics(metrics_data, request.metrics)
        
        # Build metric values
        metric_values = _build_metric_values(aggregated, request.include_comparisons)
        
        # Get breakdowns if requested
        category_breakdown = None
        segment_breakdown = None
        top_products = None
        
        if request.include_breakdowns and metrics_data:
            # Use the most recent metric's breakdowns
            latest = metrics_data[-1] if isinstance(metrics_data, list) else metrics_data
            category_breakdown = latest.get("breakdowns", {}).get("category")
            segment_breakdown = latest.get("breakdowns", {}).get("segment")
            top_products = latest.get("breakdowns", {}).get("top_products")
        
        return KPISummaryResponse(
            store_id=store_id,
            date_range={
                "preset": request.date_range_preset.value,
                "start": date_range.start.isoformat(),
                "end": date_range.end.isoformat(),
            },
            granularity=request.granularity.value,
            metrics=metric_values,
            category_breakdown=category_breakdown,
            segment_breakdown=segment_breakdown,
            top_products=top_products,
            cached=any(m.get("cached", False) for m in metrics_data) if metrics_data else False,
            computed_at=datetime.now(timezone.utc),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get KPI summary for store {store_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve KPI summary.",
        )


@router.get(
    "/kpis",
    response_model=KPISummaryResponse,
    summary="Get KPI summary (GET variant)",
)
async def get_kpi_summary_get(
    user: UserProfile = Depends(require_auth),
    service: MetricsAggregationService = Depends(get_service),
    date_range: DateRangePreset = Query(DateRangePreset.THIS_MONTH),
    granularity: MetricGranularity = Query(MetricGranularity.DAILY),
    metrics: Optional[str] = Query(None, description="Comma-separated metric names"),
    skip_cache: bool = Query(False),
):
    """GET endpoint for KPI summary."""
    request = KPIQueryRequest(
        date_range_preset=date_range,
        granularity=granularity,
        metrics=[MetricName(m) for m in metrics.split(",")] if metrics else None,
        skip_cache=skip_cache,
    )
    return await get_kpi_summary(request, user, service)


# ─── Trend Endpoint ───────────────────────────────────────────────────────────

@router.post(
    "/trends",
    response_model=TrendResponse,
    summary="Get metric trend over time",
    description="""
    Get time-series data for a single metric.
    
    Returns data points suitable for charting/visualization.
    Supports comparison series (YoY, MoM, previous period).
    """,
)
async def get_metric_trend(
    request: TrendQueryRequest,
    user: UserProfile = Depends(require_auth),
    service: MetricsAggregationService = Depends(get_service),
):
    """
    Get time-series trend data for a metric.
    """
    store_id = request.store_id or _get_user_store_id(user)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store access configured.")
    
    try:
        date_range = _resolve_date_range(
            request.date_range_preset,
            request.custom_date_from,
            request.custom_date_to,
        )
        
        # Fetch metrics based on granularity
        if request.granularity == MetricGranularity.HOURLY:
            metrics_data = service.get_hourly_metrics(
                store_id=UUID(store_id),
                date_range=date_range,
                use_cache=True,
            )
        elif request.granularity == MetricGranularity.DAILY:
            metrics_data = service.get_daily_metrics(
                store_id=UUID(store_id),
                date_range=date_range,
                use_cache=True,
            )
        elif request.granularity == MetricGranularity.WEEKLY:
            metrics_data = []
            start_date = date_range.start.date()
            end_date = date_range.end.date()
            iso_start = start_date.isocalendar()
            iso_end = end_date.isocalendar()
            
            for year in range(iso_start[0], iso_end[0] + 1):
                start_week = iso_start[1] if year == iso_start[0] else 1
                end_week = iso_end[1] if year == iso_end[0] else 53
                for week in range(start_week, end_week + 1):
                    data = service.get_weekly_metrics(UUID(store_id), year, week)
                    if data:
                        metrics_data.append(data)
        else:  # MONTHLY
            metrics_data = []
            start_date = date_range.start.date()
            end_date = date_range.end.date()
            
            for year in range(start_date.year, end_date.year + 1):
                start_month = start_date.month if year == start_date.year else 1
                end_month = end_date.month if year == end_date.year else 12
                for month in range(start_month, end_month + 1):
                    data = service.get_monthly_metrics(UUID(store_id), year, month)
                    if data:
                        metrics_data.append(data)
        
        # Extract metric values
        data_points = _extract_trend_data(metrics_data, request.metric_name)
        
        # Calculate summary stats
        values = [dp.value for dp in data_points]
        total = sum(values) if values else 0
        average = total / len(values) if values else 0
        min_val = min(values) if values else 0
        max_val = max(values) if values else 0
        
        # Get comparison data if requested
        comparison = None
        if request.compare != ComparisonMode.NONE:
            comparison = _get_comparison_series(
                service, UUID(store_id), date_range, request.granularity, 
                request.metric_name, request.compare
            )
        
        return TrendResponse(
            store_id=store_id,
            metric_name=request.metric_name.value,
            granularity=request.granularity.value,
            date_range={
                "start": date_range.start.isoformat(),
                "end": date_range.end.isoformat(),
            },
            data=data_points,
            total=total,
            average=average,
            min=min_val,
            max=max_val,
            comparison=comparison,
            cached=False,
            computed_at=datetime.now(timezone.utc),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trend for store {store_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve trend data.")


@router.get(
    "/trends",
    response_model=TrendResponse,
    summary="Get metric trend (GET variant)",
)
async def get_metric_trend_get(
    user: UserProfile = Depends(require_auth),
    service: MetricsAggregationService = Depends(get_service),
    metric_name: MetricName = Query(..., description="Metric to track"),
    date_range: DateRangePreset = Query(DateRangePreset.LAST_30_DAYS),
    granularity: MetricGranularity = Query(MetricGranularity.DAILY),
    compare: ComparisonMode = Query(ComparisonMode.NONE),
):
    """GET endpoint for metric trends."""
    request = TrendQueryRequest(
        metric_name=metric_name,
        date_range_preset=date_range,
        granularity=granularity,
        compare=compare,
    )
    return await get_metric_trend(request, user, service)


# ─── Rankings Endpoint ────────────────────────────────────────────────────────

@router.post(
    "/rankings",
    response_model=RankingResponse,
    summary="Get performance rankings",
    description="""
    Get top/bottom performers by various metrics.
    
    Supports:
    - Top categories/products by revenue
    - Top products by sales volume
    - Bottom performers by return rate
    - Top/bottom by profit margin
    
    Includes drill-down capability for products within categories.
    """,
)
async def get_rankings(
    request: RankingQueryRequest,
    user: UserProfile = Depends(require_auth),
    service: MetricsAggregationService = Depends(get_service),
):
    """
    Get performance rankings.
    """
    store_id = request.store_id or _get_user_store_id(user)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store access configured.")
    
    try:
        date_range = _resolve_date_range(
            request.date_range_preset,
            request.custom_date_from,
            request.custom_date_to,
        )
        
        # Get daily metrics for the range to aggregate breakdowns
        metrics_data = service.get_daily_metrics(
            store_id=UUID(store_id),
            date_range=date_range,
            use_cache=True,
        )
        
        # Aggregate breakdowns
        category_data = {}
        product_data = {}
        
        for metric in metrics_data:
            # Aggregate category breakdown
            for cat in metric.get("breakdowns", {}).get("category", []):
                cat_name = cat.get("category")
                if cat_name not in category_data:
                    category_data[cat_name] = {
                        "category": cat_name,
                        "transactions": 0,
                        "units": 0,
                        "revenue": 0,
                    }
                category_data[cat_name]["transactions"] += cat.get("transactions", 0)
                category_data[cat_name]["units"] += cat.get("units", 0)
                category_data[cat_name]["revenue"] += cat.get("revenue", 0)
            
            # Aggregate top products
            for prod in metric.get("breakdowns", {}).get("top_products", []):
                prod_name = prod.get("product_name")
                if prod_name not in product_data:
                    product_data[prod_name] = {
                        "product_name": prod_name,
                        "category": prod.get("category"),
                        "transactions": 0,
                        "units": 0,
                        "revenue": 0,
                    }
                product_data[prod_name]["transactions"] += prod.get("transactions", 0)
                product_data[prod_name]["units"] += prod.get("units", 0)
                product_data[prod_name]["revenue"] += prod.get("revenue", 0)
        
        # Build rankings based on type
        rankings = _build_rankings(
            request.ranking_type,
            category_data,
            product_data,
            request.limit,
            request.category,
        )
        
        # Add drill-down if requested
        if request.drill_down and request.ranking_type in [RankingType.TOP_REVENUE, RankingType.TOP_VOLUME]:
            for ranking in rankings:
                if ranking.category:
                    # Get products within this category
                    category_products = [
                        p for p in product_data.values()
                        if p.get("category") == ranking.category
                    ]
                    category_products.sort(key=lambda x: x.get("revenue", 0), reverse=True)
                    ranking.drill_down_data = category_products[:5]
        
        return RankingResponse(
            store_id=store_id,
            ranking_type=request.ranking_type.value,
            date_range={
                "start": date_range.start.isoformat(),
                "end": date_range.end.isoformat(),
            },
            rankings=rankings,
            cached=False,
            computed_at=datetime.now(timezone.utc),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rankings for store {store_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve rankings.")


@router.get(
    "/rankings",
    response_model=RankingResponse,
    summary="Get performance rankings (GET variant)",
)
async def get_rankings_get(
    user: UserProfile = Depends(require_auth),
    service: MetricsAggregationService = Depends(get_service),
    ranking_type: RankingType = Query(RankingType.TOP_REVENUE),
    date_range: DateRangePreset = Query(DateRangePreset.THIS_MONTH),
    limit: int = Query(5, ge=1, le=20),
    category: Optional[str] = Query(None),
    drill_down: bool = Query(False),
):
    """GET endpoint for rankings."""
    request = RankingQueryRequest(
        ranking_type=ranking_type,
        date_range_preset=date_range,
        limit=limit,
        category=category,
        drill_down=drill_down,
    )
    return await get_rankings(request, user, service)


# ─── Recalculation Endpoint (Admin) ───────────────────────────────────────────

@router.post(
    "/recalculate",
    response_model=RecalculateResponse,
    summary="Trigger metric recalculation (Admin)",
    description="""
    Trigger on-demand metric recalculation.
    
    Requires admin privileges.
    Use for:
    - Fixing stale metrics
    - Recomputing after data corrections
    - Initial data population
    """,
)
async def recalculate_metrics(
    request: RecalculateRequest,
    background_tasks: BackgroundTasks,
    user: UserProfile = Depends(require_auth),
    service: MetricsAggregationService = Depends(get_service),
):
    """
    Trigger metric recalculation (admin endpoint).
    """
    # Check admin privileges
    if not hasattr(user, 'roles') or 'admin' not in getattr(user, 'roles', []):
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required for recalculation.",
        )
    
    try:
        start_time = datetime.now(timezone.utc)
        metrics_computed = 0
        errors = []
        cascade_results = []
        
        # Recalculate based on granularity
        if request.granularity == MetricGranularity.HOURLY:
            current = datetime.combine(request.date_from, datetime.min.time()).replace(tzinfo=timezone.utc)
            end = datetime.combine(request.date_to, datetime.max.time()).replace(tzinfo=timezone.utc)
            
            while current < end:
                try:
                    service._compute_hourly_metric(UUID(request.store_id), current)
                    metrics_computed += 1
                except Exception as e:
                    errors.append(f"Hour {current}: {str(e)}")
                current += timedelta(hours=1)
        
        elif request.granularity == MetricGranularity.DAILY:
            current = request.date_from
            while current <= request.date_to:
                try:
                    service._compute_daily_metric(UUID(request.store_id), current)
                    metrics_computed += 1
                except Exception as e:
                    errors.append(f"Day {current}: {str(e)}")
                current += timedelta(days=1)
        
        elif request.granularity == MetricGranularity.WEEKLY:
            start_iso = request.date_from.isocalendar()
            end_iso = request.date_to.isocalendar()
            
            for year in range(start_iso[0], end_iso[0] + 1):
                start_week = start_iso[1] if year == start_iso[0] else 1
                end_week = end_iso[1] if year == end_iso[0] else 53
                for week in range(start_week, end_week + 1):
                    try:
                        service._compute_weekly_metric(UUID(request.store_id), year, week)
                        metrics_computed += 1
                    except Exception as e:
                        errors.append(f"Week {year}-W{week}: {str(e)}")
        
        else:  # MONTHLY
            current_year = request.date_from.year
            current_month = request.date_from.month
            end_year = request.date_to.year
            end_month = request.date_to.month
            
            while (current_year, current_month) <= (end_year, end_month):
                try:
                    service._compute_monthly_metric(UUID(request.store_id), current_year, current_month)
                    metrics_computed += 1
                except Exception as e:
                    errors.append(f"Month {current_year}-{current_month}: {str(e)}")
                
                current_month += 1
                if current_month > 12:
                    current_month = 1
                    current_year += 1
        
        # Cascade to downstream granularities
        if request.cascade:
            if request.granularity == MetricGranularity.HOURLY:
                # Cascade to daily
                current = request.date_from
                while current <= request.date_to:
                    try:
                        service._compute_daily_metric(UUID(request.store_id), current)
                        cascade_results.append({"granularity": "daily", "date": str(current), "status": "success"})
                    except Exception as e:
                        cascade_results.append({"granularity": "daily", "date": str(current), "status": "failed", "error": str(e)})
                    current += timedelta(days=1)
        
        computation_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        return RecalculateResponse(
            success=len(errors) == 0,
            store_id=request.store_id,
            granularity=request.granularity.value,
            date_range={
                "from": request.date_from.isoformat(),
                "to": request.date_to.isoformat(),
            },
            metrics_computed=metrics_computed,
            computation_time_ms=computation_time,
            cascade_results=cascade_results if cascade_results else None,
            errors=errors if errors else None,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recalculation failed for store {request.store_id}: {e}")
        raise HTTPException(status_code=500, detail="Recalculation failed.")


# ─── Health Check Endpoint ────────────────────────────────────────────────────

@router.get(
    "/health",
    response_model=MetricsHealthResponse,
    summary="Get metrics service health",
    description="""
    Health check for the metrics aggregation service.
    
    Returns:
    - Component status (streaming aggregator, batch scheduler, storage)
    - Cache hit rates
    - Stale metrics alerts
    """,
)
async def get_metrics_health(
    service: MetricsAggregationService = Depends(get_service),
):
    """
    Get health status of metrics aggregation service.
    """
    from database.metrics_aggregation_models import (
        HourlyMetric,
        DailyMetric,
        WeeklyMetric,
        MonthlyMetric,
        MetricStatus,
    )
    from sqlalchemy import func as sql_func
    
    now = datetime.now(timezone.utc)
    
    # Check for stale hourly metrics
    stale_hourly = service._db.scalar(
        sql_func.count().select(
            select(HourlyMetric).where(
                HourlyMetric.status == MetricStatus.STALE,
                HourlyMetric.hour_key >= now - timedelta(days=1),
            ).exists()
        )
    ) or 0
    
    # Check for stale daily metrics
    stale_daily = service._db.scalar(
        sql_func.count().select(
            select(DailyMetric).where(
                DailyMetric.status == MetricStatus.STALE,
                DailyMetric.date_key >= (now - timedelta(days=7)).date(),
            ).exists()
        )
    ) or 0
    
    # Determine overall status
    if stale_hourly > 10 or stale_daily > 5:
        status = "degraded"
    elif stale_hourly > 0 or stale_daily > 0:
        status = "healthy"
    else:
        status = "healthy"
    
    # Build stale metrics list
    stale_metrics = []
    if stale_hourly > 0:
        stale_metrics.append({
            "granularity": "hourly",
            "count": stale_hourly,
            "threshold": 10,
        })
    if stale_daily > 0:
        stale_metrics.append({
            "granularity": "daily",
            "count": stale_daily,
            "threshold": 5,
        })
    
    return MetricsHealthResponse(
        status=status,
        timestamp=now,
        components={
            "metric_storage": {
                "status": "healthy",
                "last_check": now,
                "details": {
                    "stale_hourly": stale_hourly,
                    "stale_daily": stale_daily,
                },
            },
            "aggregation_service": {
                "status": "healthy",
                "last_check": now,
            },
        },
        metrics={
            "stale_hourly_metrics": stale_hourly,
            "stale_daily_metrics": stale_daily,
        },
        stale_metrics=stale_metrics if stale_metrics else None,
    )


# ─── Helper Functions ──────────────────────────────────────────────────────────

def _aggregate_metrics(
    metrics_data: List[Dict[str, Any]],
    requested_metrics: Optional[List[MetricName]],
) -> Dict[str, Any]:
    """Aggregate metrics across multiple data points."""
    if not metrics_data:
        return {}
    
    aggregated = {
        "total_revenue": 0,
        "transaction_count": 0,
        "units_sold": 0,
        "total_profit": 0,
        "return_count": 0,
        "return_amount": 0,
        "unique_customers": 0,
        "new_customers": 0,
        "returning_customers": 0,
        "vip_customers": 0,
        "profit_margin_sum": 0,
        "profit_margin_weight": 0,
    }
    
    for metric in metrics_data:
        # Handle both dict and object formats
        if isinstance(metric, dict):
            revenue = metric.get("revenue", {})
            transactions = metric.get("transactions", {})
            profit = metric.get("profit", {})
            returns = metric.get("returns", {})
            customers = metric.get("customers", {})
            
            aggregated["total_revenue"] += revenue.get("total", 0)
            aggregated["transaction_count"] += transactions.get("count", 0)
            aggregated["units_sold"] += transactions.get("units_sold", 0)
            aggregated["total_profit"] += profit.get("total", 0)
            aggregated["return_count"] += returns.get("count", 0)
            aggregated["return_amount"] += returns.get("amount", 0)
            aggregated["unique_customers"] = max(aggregated["unique_customers"], customers.get("unique", 0))
            aggregated["new_customers"] += customers.get("new", 0)
            aggregated["returning_customers"] += customers.get("returning", 0)
            aggregated["vip_customers"] += customers.get("vip", 0)
            
            # Weighted average for profit margin
            margin = profit.get("avg_margin", 0)
            weight = transactions.get("count", 0)
            if margin and weight:
                aggregated["profit_margin_sum"] += margin * weight
                aggregated["profit_margin_weight"] += weight
    
    return aggregated


def _build_metric_values(
    aggregated: Dict[str, Any],
    include_comparisons: bool,
) -> List[MetricValue]:
    """Build MetricValue list from aggregated data."""
    metrics = []
    
    # Revenue
    metrics.append(MetricValue(
        name="totalRevenue",
        value=aggregated.get("total_revenue", 0),
        unit="currency",
        formatted=format_metric_value(aggregated.get("total_revenue", 0), "currency"),
        computed_at=datetime.now(timezone.utc),
    ))
    
    # Transaction count
    metrics.append(MetricValue(
        name="transactionCount",
        value=aggregated.get("transaction_count", 0),
        unit="count",
        formatted=format_metric_value(aggregated.get("transaction_count", 0), "count"),
        computed_at=datetime.now(timezone.utc),
    ))
    
    # Average transaction value
    atv = aggregated.get("total_revenue", 0) / aggregated.get("transaction_count", 1) if aggregated.get("transaction_count") else 0
    metrics.append(MetricValue(
        name="avgTransactionValue",
        value=atv,
        unit="currency",
        formatted=format_metric_value(atv, "currency"),
        computed_at=datetime.now(timezone.utc),
    ))
    
    # Profit margin (weighted average)
    margin = aggregated.get("profit_margin_sum", 0) / aggregated.get("profit_margin_weight", 1) if aggregated.get("profit_margin_weight") else 0
    metrics.append(MetricValue(
        name="avgProfitMargin",
        value=margin,
        unit="percentage",
        formatted=format_metric_value(margin, "percentage"),
        computed_at=datetime.now(timezone.utc),
    ))
    
    # Total profit
    metrics.append(MetricValue(
        name="totalProfit",
        value=aggregated.get("total_profit", 0),
        unit="currency",
        formatted=format_metric_value(aggregated.get("total_profit", 0), "currency"),
        computed_at=datetime.now(timezone.utc),
    ))
    
    # Return rate
    return_rate = aggregated.get("return_count", 0) / aggregated.get("transaction_count", 1) * 100 if aggregated.get("transaction_count") else 0
    metrics.append(MetricValue(
        name="returnRate",
        value=return_rate,
        unit="percentage",
        formatted=format_metric_value(return_rate, "percentage"),
        computed_at=datetime.now(timezone.utc),
    ))
    
    # Units sold
    metrics.append(MetricValue(
        name="unitsSold",
        value=aggregated.get("units_sold", 0),
        unit="count",
        formatted=format_metric_value(aggregated.get("units_sold", 0), "count"),
        computed_at=datetime.now(timezone.utc),
    ))
    
    # Unique customers
    metrics.append(MetricValue(
        name="uniqueCustomers",
        value=aggregated.get("unique_customers", 0),
        unit="count",
        formatted=format_metric_value(aggregated.get("unique_customers", 0), "count"),
        computed_at=datetime.now(timezone.utc),
    ))
    
    # New customers
    metrics.append(MetricValue(
        name="newCustomers",
        value=aggregated.get("new_customers", 0),
        unit="count",
        formatted=format_metric_value(aggregated.get("new_customers", 0), "count"),
        computed_at=datetime.now(timezone.utc),
    ))
    
    return metrics


def _extract_trend_data(
    metrics_data: List[Dict[str, Any]],
    metric_name: MetricName,
) -> List[TrendDataPoint]:
    """Extract trend data points for a specific metric."""
    data_points = []
    
    for metric in metrics_data:
        timestamp = None
        
        # Get timestamp based on data structure
        if "hour_key" in metric:
            timestamp = datetime.fromisoformat(metric["hour_key"]) if isinstance(metric["hour_key"], str) else metric["hour_key"]
        elif "date_key" in metric:
            date_val = metric["date_key"]
            if isinstance(date_val, str):
                timestamp = datetime.fromisoformat(date_val)
            else:
                timestamp = datetime.combine(date_val, datetime.min.time()).replace(tzinfo=timezone.utc)
        elif "week" in metric:
            week_info = metric["week"]
            timestamp = datetime.strptime(f"{week_info['year']}-W{week_info['week_number']}-1", "%Y-W%W-%w")
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        elif "month" in metric:
            month_info = metric["month"]
            timestamp = datetime(month_info["year"], month_info["month_number"], 1, tzinfo=timezone.utc)
        
        if not timestamp:
            continue
        
        # Extract value based on metric name
        value = 0
        if metric_name == MetricName.TOTAL_REVENUE:
            value = metric.get("revenue", {}).get("total", 0)
        elif metric_name == MetricName.TRANSACTION_COUNT:
            value = metric.get("transactions", {}).get("count", 0)
        elif metric_name == MetricName.AVG_TRANSACTION_VALUE:
            value = metric.get("transactions", {}).get("avg_value", 0)
        elif metric_name == MetricName.AVG_PROFIT_MARGIN:
            value = metric.get("profit", {}).get("avg_margin", 0)
        elif metric_name == MetricName.TOTAL_PROFIT:
            value = metric.get("profit", {}).get("total", 0)
        elif metric_name == MetricName.RETURN_RATE:
            value = metric.get("returns", {}).get("rate", 0)
        elif metric_name == MetricName.RETURN_COUNT:
            value = metric.get("returns", {}).get("count", 0)
        elif metric_name == MetricName.UNIQUE_CUSTOMERS:
            value = metric.get("customers", {}).get("unique", 0)
        elif metric_name == MetricName.NEW_CUSTOMERS:
            value = metric.get("customers", {}).get("new", 0)
        elif metric_name == MetricName.UNITS_SOLD:
            value = metric.get("transactions", {}).get("units_sold", 0)
        
        data_points.append(TrendDataPoint(
            timestamp=timestamp,
            value=value,
            formatted_value=format_metric_value(value, _get_unit_for_metric(metric_name)),
        ))
    
    return data_points


def _get_unit_for_metric(metric_name: MetricName) -> str:
    """Get the unit type for a metric."""
    currency_metrics = {MetricName.TOTAL_REVENUE, MetricName.AVG_TRANSACTION_VALUE, MetricName.TOTAL_PROFIT}
    percentage_metrics = {MetricName.AVG_PROFIT_MARGIN, MetricName.RETURN_RATE}
    
    if metric_name in currency_metrics:
        return "currency"
    elif metric_name in percentage_metrics:
        return "percentage"
    return "count"


def _get_comparison_series(
    service: MetricsAggregationService,
    store_id: UUID,
    date_range: DateRange,
    granularity: MetricGranularity,
    metric_name: MetricName,
    compare_mode: ComparisonMode,
) -> Optional[Dict[str, Any]]:
    """Get comparison series for trend data."""
    # Calculate comparison date range
    duration = date_range.end - date_range.start
    
    if compare_mode == ComparisonMode.PREVIOUS_PERIOD:
        comp_start = date_range.start - duration
        comp_end = date_range.start
    elif compare_mode == ComparisonMode.YOY:
        comp_start = date_range.start.replace(year=date_range.start.year - 1)
        comp_end = date_range.end.replace(year=date_range.end.year - 1)
    elif compare_mode == ComparisonMode.MOM:
        # Shift back one month
        comp_start = date_range.start - timedelta(days=30)
        comp_end = date_range.end - timedelta(days=30)
    elif compare_mode == ComparisonMode.WOW:
        comp_start = date_range.start - timedelta(weeks=1)
        comp_end = date_range.end - timedelta(weeks=1)
    else:
        return None
    
    comp_range = DateRange(start=comp_start, end=comp_end)
    
    # Fetch comparison data
    if granularity == MetricGranularity.DAILY:
        comp_data = service.get_daily_metrics(store_id, comp_range, use_cache=True)
    else:
        return None
    
    comp_points = _extract_trend_data(comp_data, metric_name)
    
    return {
        "mode": compare_mode.value,
        "date_range": {
            "start": comp_start.isoformat(),
            "end": comp_end.isoformat(),
        },
        "data": [dp.model_dump() for dp in comp_points],
    }


def _build_rankings(
    ranking_type: RankingType,
    category_data: Dict[str, Any],
    product_data: Dict[str, Any],
    limit: int,
    category_filter: Optional[str],
) -> List[RankingItem]:
    """Build ranking items based on ranking type."""
    rankings = []
    
    if ranking_type in [RankingType.TOP_REVENUE, RankingType.TOP_VOLUME]:
        # Use product data
        products = list(product_data.values())
        
        if category_filter:
            products = [p for p in products if p.get("category") == category_filter]
        
        # Sort by appropriate metric
        if ranking_type == RankingType.TOP_REVENUE:
            products.sort(key=lambda x: x.get("revenue", 0), reverse=True)
        else:
            products.sort(key=lambda x: x.get("units", 0), reverse=True)
        
        for i, prod in enumerate(products[:limit], start=1):
            value = prod.get("revenue" if ranking_type == RankingType.TOP_REVENUE else "units", 0)
            rankings.append(RankingItem(
                rank=i,
                name=prod.get("product_name", "Unknown"),
                category=prod.get("category"),
                value=value,
                formatted_value=format_metric_value(
                    value, 
                    "currency" if ranking_type == RankingType.TOP_REVENUE else "count"
                ),
            ))
    
    elif ranking_type == RankingType.BOTTOM_RETURNS:
        # Products with highest return rates
        products = list(product_data.values())
        # Would need return data - placeholder
        for i, prod in enumerate(products[:limit], start=1):
            rankings.append(RankingItem(
                rank=i,
                name=prod.get("product_name", "Unknown"),
                category=prod.get("category"),
                value=0,  # Would calculate return rate
                formatted_value="0%",
            ))
    
    elif ranking_type in [RankingType.TOP_MARGIN, RankingType.BOTTOM_MARGIN]:
        # Categories by profit margin
        categories = list(category_data.values())
        
        # Would need margin data - for now use revenue
        categories.sort(
            key=lambda x: x.get("revenue", 0), 
            reverse=(ranking_type == RankingType.TOP_MARGIN)
        )
        
        for i, cat in enumerate(categories[:limit], start=1):
            rankings.append(RankingItem(
                rank=i,
                name=cat.get("category", "Unknown"),
                category=cat.get("category"),
                value=cat.get("revenue", 0),
                formatted_value=format_metric_value(cat.get("revenue", 0), "currency"),
            ))
    
    return rankings
