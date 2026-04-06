"""
CONFIT Backend - Notification Analytics API Routes
===================================================
Admin dashboard endpoints for notification analytics and A/B testing.
Provides real-time querying, aggregation, and export capabilities.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_user, require_admin
from core.security.rbac import AuthContext, Role, Permission


router = APIRouter(prefix="/analytics/notifications", tags=["Notification Analytics"])


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class AnalyticsChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    TOAST = "toast"


class AnalyticsRecipientType(str, Enum):
    CUSTOMER = "customer"
    OWNER = "owner"


class NotificationEventType(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    CLICKED = "clicked"
    DISMISSED = "dismissed"


class ABTestStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ABTestVariable(str, Enum):
    TIMING = "timing"
    CONTENT = "content"
    CHANNEL = "channel"
    FREQUENCY = "frequency"


class ABTestSegment(str, Enum):
    ALL_CUSTOMERS = "all_customers"
    ALL_OWNERS = "all_owners"
    NEW_CUSTOMERS = "new_customers"
    REPEAT_CUSTOMERS = "repeat_customers"
    SPECIFIC_STORES = "specific_stores"


# ─────────────────────────────────────────────────────────────────────────────
# DTOs
# ─────────────────────────────────────────────────────────────────────────────

class NotificationEventDTO(BaseModel):
    id: str
    notification_id: str
    recipient_id: str
    recipient_type: AnalyticsRecipientType
    channel: AnalyticsChannel
    event_type: NotificationEventType
    event_timestamp: datetime
    payload: dict = Field(default_factory=dict)
    time_spent_ms: Optional[int] = None
    scroll_depth: Optional[float] = None
    action_taken: Optional[str] = None


class ChannelMetricsDTO(BaseModel):
    channel: AnalyticsChannel
    total_sent: int
    total_delivered: int
    total_read: int
    total_clicked: int
    total_dismissed: int
    delivery_rate: float
    open_rate: float
    click_rate: float
    avg_latency_ms: float
    avg_time_spent_ms: Optional[float] = None


class KPISummaryDTO(BaseModel):
    overall_delivery_rate: float
    avg_open_rate: float
    avg_click_rate: float
    most_used_channel: AnalyticsChannel
    most_used_channel_count: int
    top_conversion_channel: AnalyticsChannel
    top_conversion_rate: float
    delivery_rate_trend: float
    open_rate_trend: float
    total_events: int
    period_days: int


class HeatmapCellDTO(BaseModel):
    day: int
    hour: int
    open_rate: float
    click_rate: float
    event_count: int


class ConversionDataPointDTO(BaseModel):
    channel: AnalyticsChannel
    period_days: int
    conversion_rate: float
    notification_count: int
    conversion_count: int


class OwnerResponseTimeDTO(BaseModel):
    store_id: str
    store_name: str
    notification_count: int
    avg_response_time_min: float
    median_response_time_min: float


class CohortComparisonDTO(BaseModel):
    period: str
    notified_purchase_rate: float
    non_notified_purchase_rate: float
    lift_percentage: float


class DailyTrendDTO(BaseModel):
    date: str
    delivery_rate: float
    open_rate: float
    click_rate: float
    count: int


class ActivityFeedItemDTO(BaseModel):
    id: str
    notification_id: str
    notification_title: str
    recipient_id: str
    recipient_type: AnalyticsRecipientType
    channel: AnalyticsChannel
    event_type: NotificationEventType
    timestamp: datetime


class ABTestVariantDTO(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    sample_size: int
    metrics: dict


class ABTestDTO(BaseModel):
    id: str
    name: str
    hypothesis: str
    variable: ABTestVariable
    status: ABTestStatus
    segment: ABTestSegment
    traffic_percentage: int
    duration_days: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    variants: List[ABTestVariantDTO]
    is_significant: bool
    created_at: datetime
    updated_at: datetime


class CreateABTestRequest(BaseModel):
    name: str
    hypothesis: str
    variable: ABTestVariable
    segment: ABTestSegment
    traffic_percentage: int = Field(ge=1, le=100)
    duration_days: int = Field(ge=1, le=90)
    variants: List[dict]
    use_ml_predictions: bool = False
    ml_confidence_threshold: float = Field(default=0.3, ge=0.0, le=1.0)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def require_analytics_access(
    current_user: AuthContext = Depends(get_current_user),
) -> AuthContext:
    """Require admin or analytics role."""
    allowed_roles = {Role.ADMIN, Role.ANALYTICS, Role.STORE_OWNER, Role.FACTORY_OWNER}
    if not any(current_user.has_role(role) for role in allowed_roles):
        raise HTTPException(
            status_code=403,
            detail="Analytics access requires admin, analytics, or owner role"
        )
    return current_user


def get_period_dates(period_days: int) -> tuple[datetime, datetime]:
    """Get start and end dates for a period."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    return start_date, end_date


# ─────────────────────────────────────────────────────────────────────────────
# KPI ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/kpis",
    response_model=KPISummaryDTO,
    summary="Get KPI summary for dashboard",
)
async def get_kpis(
    period: int = Query(30, ge=1, le=90, description="Period in days"),
    recipient_type: Optional[AnalyticsRecipientType] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """Get aggregated KPI summary for the executive summary section."""
    start_date, end_date = get_period_dates(period)
    prev_start = start_date - timedelta(days=period)
    
    # Current period metrics
    current_metrics_query = text("""
        SELECT 
            COUNT(*) FILTER (WHERE event_type = 'sent') AS total_sent,
            COUNT(*) FILTER (WHERE event_type = 'delivered') AS total_delivered,
            COUNT(*) FILTER (WHERE event_type = 'read') AS total_read,
            COUNT(*) FILTER (WHERE event_type = 'clicked') AS total_clicked
        FROM notification_events
        WHERE event_timestamp >= :start_date
          AND event_timestamp < :end_date
          AND (:recipient_type IS NULL OR recipient_type = :recipient_type)
    """)
    
    result = await db.execute(
        current_metrics_query,
        {"start_date": start_date, "end_date": end_date, "recipient_type": recipient_type.value if recipient_type else None}
    )
    current = result.fetchone()
    
    # Previous period metrics for trend
    prev_result = await db.execute(
        current_metrics_query,
        {"start_date": prev_start, "end_date": start_date, "recipient_type": recipient_type.value if recipient_type else None}
    )
    prev = prev_result.fetchone()
    
    # Channel breakdown
    channel_query = text("""
        SELECT 
            channel,
            COUNT(*) FILTER (WHERE event_type = 'sent') AS sent_count,
            COUNT(*) FILTER (WHERE event_type = 'delivered') AS delivered_count,
            COUNT(*) FILTER (WHERE event_type = 'read') AS read_count,
            COUNT(*) FILTER (WHERE event_type = 'clicked') AS clicked_count
        FROM notification_events
        WHERE event_timestamp >= :start_date
          AND event_timestamp < :end_date
          AND (:recipient_type IS NULL OR recipient_type = :recipient_type)
        GROUP BY channel
        ORDER BY sent_count DESC
    """)
    
    channel_result = await db.execute(
        channel_query,
        {"start_date": start_date, "end_date": end_date, "recipient_type": recipient_type.value if recipient_type else None}
    )
    channels = channel_result.fetchall()
    
    # Calculate metrics
    total_sent = current.total_sent or 0
    total_delivered = current.total_delivered or 0
    total_read = current.total_read or 0
    total_clicked = current.total_clicked or 0
    
    delivery_rate = total_delivered / total_sent if total_sent > 0 else 0
    open_rate = total_read / total_delivered if total_delivered > 0 else 0
    click_rate = total_clicked / total_read if total_read > 0 else 0
    
    # Previous period rates
    prev_sent = prev.total_sent or 0
    prev_delivered = prev.total_delivered or 0
    prev_read = prev.total_read or 0
    prev_delivery_rate = prev_delivered / prev_sent if prev_sent > 0 else 0
    prev_open_rate = prev_read / prev_delivered if prev_delivered > 0 else 0
    
    delivery_trend = delivery_rate - prev_delivery_rate
    open_trend = open_rate - prev_open_rate
    
    # Most used channel
    most_used = channels[0] if channels else None
    most_used_channel = most_used.channel if most_used else "in_app"
    most_used_count = most_used.sent_count if most_used else 0
    
    # Top conversion channel (simplified - use click rate as proxy)
    top_conversion = max(channels, key=lambda c: (c.clicked_count / c.read_count) if c.read_count > 0 else 0) if channels else None
    top_conversion_channel = top_conversion.channel if top_conversion else "in_app"
    top_conversion_rate = (top_conversion.clicked_count / top_conversion.read_count) if top_conversion and top_conversion.read_count > 0 else 0
    
    return KPISummaryDTO(
        overall_delivery_rate=round(delivery_rate, 4),
        avg_open_rate=round(open_rate, 4),
        avg_click_rate=round(click_rate, 4),
        most_used_channel=most_used_channel,
        most_used_channel_count=most_used_count,
        top_conversion_channel=top_conversion_channel,
        top_conversion_rate=round(top_conversion_rate, 4),
        delivery_rate_trend=round(delivery_trend, 4),
        open_rate_trend=round(open_trend, 4),
        total_events=total_sent,
        period_days=period,
    )


# ─────────────────────────────────────────────────────────────────────────────
# CHANNEL METRICS ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/channels",
    response_model=List[ChannelMetricsDTO],
    summary="Get metrics by channel",
)
async def get_channel_metrics(
    period: int = Query(30, ge=1, le=90),
    recipient_type: Optional[AnalyticsRecipientType] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """Get detailed metrics for each notification channel."""
    start_date, end_date = get_period_dates(period)
    
    query = text("""
        SELECT 
            channel,
            COUNT(*) FILTER (WHERE event_type = 'sent') AS total_sent,
            COUNT(*) FILTER (WHERE event_type = 'delivered') AS total_delivered,
            COUNT(*) FILTER (WHERE event_type = 'read') AS total_read,
            COUNT(*) FILTER (WHERE event_type = 'clicked') AS total_clicked,
            COUNT(*) FILTER (WHERE event_type = 'dismissed') AS total_dismissed,
            AVG(time_spent_ms) FILTER (WHERE time_spent_ms IS NOT NULL) AS avg_time_spent
        FROM notification_events
        WHERE event_timestamp >= :start_date
          AND event_timestamp < :end_date
          AND (:recipient_type IS NULL OR recipient_type = :recipient_type)
        GROUP BY channel
        ORDER BY total_sent DESC
    """)
    
    result = await db.execute(
        query,
        {"start_date": start_date, "end_date": end_date, "recipient_type": recipient_type.value if recipient_type else None}
    )
    rows = result.fetchall()
    
    metrics = []
    for row in rows:
        sent = row.total_sent or 0
        delivered = row.total_delivered or 0
        read = row.total_read or 0
        clicked = row.total_clicked or 0
        
        metrics.append(ChannelMetricsDTO(
            channel=row.channel,
            total_sent=sent,
            total_delivered=delivered,
            total_read=read,
            total_clicked=clicked,
            total_dismissed=row.total_dismissed or 0,
            delivery_rate=round(delivered / sent, 4) if sent > 0 else 0,
            open_rate=round(read / delivered, 4) if delivered > 0 else 0,
            click_rate=round(clicked / read, 4) if read > 0 else 0,
            avg_latency_ms=0,  # Would need sent/delivered timestamp join
            avg_time_spent_ms=round(row.avg_time_spent, 2) if row.avg_time_spent else None,
        ))
    
    return metrics


# ─────────────────────────────────────────────────────────────────────────────
# HEATMAP ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/heatmap",
    response_model=List[HeatmapCellDTO],
    summary="Get engagement heatmap data",
)
async def get_heatmap(
    period: int = Query(30, ge=1, le=90),
    recipient_type: Optional[AnalyticsRecipientType] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """Get day-of-week × hour-of-day engagement data."""
    start_date, end_date = get_period_dates(period)
    
    query = text("""
        SELECT 
            EXTRACT(DOW FROM event_timestamp)::INTEGER AS day,
            EXTRACT(HOUR FROM event_timestamp)::INTEGER AS hour,
            COUNT(*) FILTER (WHERE event_type = 'sent') AS event_count,
            COUNT(*) FILTER (WHERE event_type = 'read') AS read_count,
            COUNT(*) FILTER (WHERE event_type = 'clicked') AS click_count
        FROM notification_events
        WHERE event_timestamp >= :start_date
          AND event_timestamp < :end_date
          AND (:recipient_type IS NULL OR recipient_type = :recipient_type)
        GROUP BY day, hour
        ORDER BY day, hour
    """)
    
    result = await db.execute(
        query,
        {"start_date": start_date, "end_date": end_date, "recipient_type": recipient_type.value if recipient_type else None}
    )
    rows = result.fetchall()
    
    heatmap = []
    for row in rows:
        event_count = row.event_count or 0
        read_count = row.read_count or 0
        click_count = row.click_count or 0
        
        heatmap.append(HeatmapCellDTO(
            day=row.day,
            hour=row.hour,
            open_rate=round(read_count / event_count, 4) if event_count > 0 else 0,
            click_rate=round(click_count / event_count, 4) if event_count > 0 else 0,
            event_count=event_count,
        ))
    
    return heatmap


# ─────────────────────────────────────────────────────────────────────────────
# CONVERSION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/conversions",
    response_model=List[ConversionDataPointDTO],
    summary="Get conversion data by channel",
)
async def get_conversions(
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """Get conversion rates by channel for 7/14/30 day periods."""
    
    query = text("""
        SELECT 
            channel,
            days_to_conversion AS period_days,
            COUNT(DISTINCT notification_id) AS notification_count,
            COUNT(DISTINCT conversion_order_id) AS conversion_count
        FROM notification_conversions
        WHERE days_to_conversion IN (7, 14, 30)
        GROUP BY channel, days_to_conversion
        ORDER BY channel, days_to_conversion
    """)
    
    result = await db.execute(query)
    rows = result.fetchall()
    
    conversions = []
    for row in rows:
        notification_count = row.notification_count or 0
        conversion_count = row.conversion_count or 0
        
        conversions.append(ConversionDataPointDTO(
            channel=row.channel,
            period_days=row.period_days,
            conversion_rate=round(conversion_count / notification_count, 4) if notification_count > 0 else 0,
            notification_count=notification_count,
            conversion_count=conversion_count,
        ))
    
    return conversions


# ─────────────────────────────────────────────────────────────────────────────
# OWNER RESPONSE TIME ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/owner-response-times",
    response_model=List[OwnerResponseTimeDTO],
    summary="Get owner response times by store",
)
async def get_owner_response_times(
    period: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """Get average response times from notification to owner action."""
    start_date, end_date = get_period_dates(period)
    
    query = text("""
        SELECT 
            store_id,
            store_name,
            COUNT(*) AS notification_count,
            AVG(response_time_minutes) AS avg_response_time,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_time_minutes) AS median_response_time
        FROM owner_response_times
        WHERE notification_sent_at >= :start_date
          AND notification_sent_at < :end_date
          AND response_time_minutes IS NOT NULL
        GROUP BY store_id, store_name
        ORDER BY avg_response_time
    """)
    
    result = await db.execute(
        query,
        {"start_date": start_date, "end_date": end_date}
    )
    rows = result.fetchall()
    
    return [
        OwnerResponseTimeDTO(
            store_id=row.store_id,
            store_name=row.store_name,
            notification_count=row.notification_count,
            avg_response_time_min=round(row.avg_response_time, 2),
            median_response_time_min=round(row.median_response_time, 2),
        )
        for row in rows
    ]


# ─────────────────────────────────────────────────────────────────────────────
# DAILY TREND ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/daily-trend",
    response_model=List[DailyTrendDTO],
    summary="Get daily trend data",
)
async def get_daily_trend(
    period: int = Query(30, ge=1, le=90),
    recipient_type: Optional[AnalyticsRecipientType] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """Get daily metrics trend for the period."""
    start_date, end_date = get_period_dates(period)
    
    query = text("""
        SELECT 
            DATE(event_timestamp) AS date,
            COUNT(*) FILTER (WHERE event_type = 'sent') AS sent_count,
            COUNT(*) FILTER (WHERE event_type = 'delivered') AS delivered_count,
            COUNT(*) FILTER (WHERE event_type = 'read') AS read_count,
            COUNT(*) FILTER (WHERE event_type = 'clicked') AS clicked_count
        FROM notification_events
        WHERE event_timestamp >= :start_date
          AND event_timestamp < :end_date
          AND (:recipient_type IS NULL OR recipient_type = :recipient_type)
        GROUP BY DATE(event_timestamp)
        ORDER BY date
    """)
    
    result = await db.execute(
        query,
        {"start_date": start_date, "end_date": end_date, "recipient_type": recipient_type.value if recipient_type else None}
    )
    rows = result.fetchall()
    
    trends = []
    for row in rows:
        sent = row.sent_count or 0
        delivered = row.delivered_count or 0
        read = row.read_count or 0
        clicked = row.clicked_count or 0
        
        trends.append(DailyTrendDTO(
            date=row.date.isoformat(),
            delivery_rate=round(delivered / sent, 4) if sent > 0 else 0,
            open_rate=round(read / delivered, 4) if delivered > 0 else 0,
            click_rate=round(clicked / read, 4) if read > 0 else 0,
            count=sent,
        ))
    
    return trends


# ─────────────────────────────────────────────────────────────────────────────
# ACTIVITY FEED ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/activity",
    response_model=List[ActivityFeedItemDTO],
    summary="Get recent activity feed",
)
async def get_activity_feed(
    limit: int = Query(50, ge=1, le=200),
    channel: Optional[AnalyticsChannel] = Query(None),
    recipient_type: Optional[AnalyticsRecipientType] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """Get recent notification events for real-time activity feed."""
    
    query = text("""
        SELECT 
            id,
            notification_id,
            recipient_id,
            recipient_type,
            channel,
            event_type,
            event_timestamp,
            payload->>'notification_title' AS notification_title
        FROM notification_events
        WHERE (:channel IS NULL OR channel = :channel)
          AND (:recipient_type IS NULL OR recipient_type = :recipient_type)
        ORDER BY event_timestamp DESC
        LIMIT :limit
    """)
    
    result = await db.execute(
        query,
        {"limit": limit, "channel": channel.value if channel else None, "recipient_type": recipient_type.value if recipient_type else None}
    )
    rows = result.fetchall()
    
    return [
        ActivityFeedItemDTO(
            id=str(row.id),
            notification_id=row.notification_id,
            notification_title=row.notification_title or "Notification",
            recipient_id=row.recipient_id,
            recipient_type=row.recipient_type,
            channel=row.channel,
            event_type=row.event_type,
            timestamp=row.event_timestamp,
        )
        for row in rows
    ]


# ─────────────────────────────────────────────────────────────────────────────
# A/B TEST ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/ab-tests",
    response_model=List[ABTestDTO],
    summary="Get all A/B tests",
)
async def get_ab_tests(
    status: Optional[ABTestStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """Get all A/B tests with optional status filter."""
    
    query = text("""
        SELECT 
            t.id, t.name, t.hypothesis, t.variable, t.status, t.segment,
            t.traffic_percentage, t.duration_days, t.start_date, t.end_date,
            t.is_significant, t.created_at, t.updated_at,
            json_agg(
                json_build_object(
                    'id', v.id,
                    'name', v.name,
                    'description', v.description,
                    'sample_size', v.sample_size,
                    'metrics', json_build_object(
                        'delivery_rate', v.delivery_rate,
                        'open_rate', v.open_rate,
                        'click_rate', v.click_rate,
                        'conversion_rate', v.conversion_rate
                    )
                )
            ) AS variants
        FROM ab_tests t
        LEFT JOIN ab_test_variants v ON t.id = v.test_id
        WHERE (:status IS NULL OR t.status = :status)
        GROUP BY t.id
        ORDER BY t.created_at DESC
    """)
    
    result = await db.execute(
        query,
        {"status": status.value if status else None}
    )
    rows = result.fetchall()
    
    return [
        ABTestDTO(
            id=row.id,
            name=row.name,
            hypothesis=row.hypothesis,
            variable=row.variable,
            status=row.status,
            segment=row.segment,
            traffic_percentage=row.traffic_percentage,
            duration_days=row.duration_days,
            start_date=row.start_date,
            end_date=row.end_date,
            variants=row.variants or [],
            is_significant=row.is_significant,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.post(
    "/ab-tests",
    response_model=ABTestDTO,
    status_code=201,
    summary="Create new A/B test",
)
async def create_ab_test(
    request: CreateABTestRequest,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_admin),
):
    """Create a new A/B test configuration."""
    
    test_id = f"ab-{int(datetime.utcnow().timestamp() * 1000)}"
    now = datetime.utcnow()
    
    # Insert test
    test_query = text("""
        INSERT INTO ab_tests (
            id, name, hypothesis, variable, status, segment,
            traffic_percentage, duration_days, is_significant, created_at, updated_at
        ) VALUES (
            :id, :name, :hypothesis, :variable, 'draft', :segment,
            :traffic_percentage, :duration_days, false, :now, :now
        )
    """)
    
    await db.execute(
        test_query,
        {
            "id": test_id,
            "name": request.name,
            "hypothesis": request.hypothesis,
            "variable": request.variable.value,
            "segment": request.segment.value,
            "traffic_percentage": request.traffic_percentage,
            "duration_days": request.duration_days,
            "now": now,
        }
    )
    
    variants = list(request.variants)
    if request.use_ml_predictions:
        variants.append(
            {
                "name": "Use ML Predictions",
                "description": (
                    "Deliver notifications at per-recipient ML-predicted optimal times. "
                    f"Fallback to control timing below confidence {request.ml_confidence_threshold:.2f}."
                ),
                "use_ml_predictions": True,
                "confidence_threshold": request.ml_confidence_threshold,
            }
        )

    # Insert variants
    for i, variant in enumerate(variants):
        variant_id = f"{test_id}-var-{i}"
        variant_query = text("""
            INSERT INTO ab_test_variants (
                id, test_id, name, description, sample_size,
                delivery_rate, open_rate, click_rate, conversion_rate, created_at, updated_at
            ) VALUES (
                :id, :test_id, :name, :description, 0,
                0, 0, 0, 0, :now, :now
            )
        """)
        
        await db.execute(
            variant_query,
            {
                "id": variant_id,
                "test_id": test_id,
                "name": variant.get("name", f"Variant {i}"),
                "description": variant.get("description"),
                "now": now,
            }
        )
    
    await db.commit()
    
    return ABTestDTO(
        id=test_id,
        name=request.name,
        hypothesis=request.hypothesis,
        variable=request.variable,
        status=ABTestStatus.DRAFT,
        segment=request.segment,
        traffic_percentage=request.traffic_percentage,
        duration_days=request.duration_days,
        start_date=None,
        end_date=None,
        variants=[
            ABTestVariantDTO(
                id=f"{test_id}-var-{i}",
                name=v.get("name", f"Variant {i}"),
                description=v.get("description"),
                sample_size=0,
                metrics={"delivery_rate": 0, "open_rate": 0, "click_rate": 0, "conversion_rate": 0},
            )
            for i, v in enumerate(variants)
        ],
        is_significant=False,
        created_at=now,
        updated_at=now,
    )


@router.post(
    "/ab-tests/{test_id}/start",
    summary="Start an A/B test",
)
async def start_ab_test(
    test_id: str,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_admin),
):
    """Start a draft A/B test."""
    
    query = text("""
        UPDATE ab_tests
        SET status = 'running', start_date = :now, updated_at = :now
        WHERE id = :test_id AND status = 'draft'
    """)
    
    result = await db.execute(
        query,
        {"test_id": test_id, "now": datetime.utcnow()}
    )
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Test not found or not in draft status")
    
    await db.commit()
    return {"status": "running", "started_at": datetime.utcnow().isoformat()}


@router.post(
    "/ab-tests/{test_id}/pause",
    summary="Pause a running A/B test",
)
async def pause_ab_test(
    test_id: str,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_admin),
):
    """Pause a running A/B test."""
    
    query = text("""
        UPDATE ab_tests
        SET status = 'paused', updated_at = :now
        WHERE id = :test_id AND status = 'running'
    """)
    
    result = await db.execute(
        query,
        {"test_id": test_id, "now": datetime.utcnow()}
    )
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Test not found or not running")
    
    await db.commit()
    return {"status": "paused"}


@router.post(
    "/ab-tests/{test_id}/complete",
    summary="Complete an A/B test",
)
async def complete_ab_test(
    test_id: str,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_admin),
):
    """Complete a running or paused A/B test."""
    
    query = text("""
        UPDATE ab_tests
        SET status = 'completed', end_date = :now, updated_at = :now
        WHERE id = :test_id AND status IN ('running', 'paused')
    """)
    
    result = await db.execute(
        query,
        {"test_id": test_id, "now": datetime.utcnow()}
    )
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Test not found or already completed")
    
    await db.commit()
    return {"status": "completed", "completed_at": datetime.utcnow().isoformat()}


# ─────────────────────────────────────────────────────────────────────────────
# EVENT LOGGING ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

class LogEventRequest(BaseModel):
    notification_id: str
    recipient_id: str
    recipient_type: AnalyticsRecipientType
    channel: AnalyticsChannel
    event_type: NotificationEventType
    payload: dict = Field(default_factory=dict)
    time_spent_ms: Optional[int] = None
    scroll_depth: Optional[float] = None
    action_taken: Optional[str] = None
    ab_test_id: Optional[str] = None
    variant_id: Optional[str] = None


@router.post(
    "/events",
    status_code=201,
    summary="Log notification event",
)
async def log_event(
    request: LogEventRequest,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(get_current_user),
):
    """Log a notification lifecycle event."""
    
    query = text("""
        INSERT INTO notification_events (
            notification_id, recipient_id, recipient_type, channel, event_type,
            event_timestamp, payload, time_spent_ms, scroll_depth, action_taken,
            ab_test_id, variant_id
        ) VALUES (
            :notification_id, :recipient_id, :recipient_type, :channel, :event_type,
            NOW(), :payload, :time_spent_ms, :scroll_depth, :action_taken,
            :ab_test_id, :variant_id
        )
    """)
    
    await db.execute(
        query,
        {
            "notification_id": request.notification_id,
            "recipient_id": request.recipient_id,
            "recipient_type": request.recipient_type.value,
            "channel": request.channel.value,
            "event_type": request.event_type.value,
            "payload": request.payload,
            "time_spent_ms": request.time_spent_ms,
            "scroll_depth": request.scroll_depth,
            "action_taken": request.action_taken,
            "ab_test_id": request.ab_test_id,
            "variant_id": request.variant_id,
        }
    )
    
    await db.commit()
    return {"status": "logged", "notification_id": request.notification_id}


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/export/csv",
    summary="Export analytics data as CSV",
)
async def export_csv(
    period: int = Query(30, ge=1, le=90),
    recipient_type: Optional[AnalyticsRecipientType] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """Export notification events as CSV."""
    import io
    import csv
    
    start_date, end_date = get_period_dates(period)
    
    query = text("""
        SELECT 
            id, notification_id, recipient_id, recipient_type, channel, event_type,
            event_timestamp, payload, time_spent_ms, scroll_depth, action_taken
        FROM notification_events
        WHERE event_timestamp >= :start_date
          AND event_timestamp < :end_date
          AND (:recipient_type IS NULL OR recipient_type = :recipient_type)
        ORDER BY event_timestamp DESC
        LIMIT 10000
    """)
    
    result = await db.execute(
        query,
        {"start_date": start_date, "end_date": end_date, "recipient_type": recipient_type.value if recipient_type else None}
    )
    rows = result.fetchall()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "id", "notification_id", "recipient_id", "recipient_type", "channel",
        "event_type", "event_timestamp", "time_spent_ms", "scroll_depth", "action_taken"
    ])
    
    # Data
    for row in rows:
        writer.writerow([
            str(row.id), row.notification_id, row.recipient_id, row.recipient_type,
            row.channel, row.event_type, row.event_timestamp.isoformat(),
            row.time_spent_ms, row.scroll_depth, row.action_taken
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=notification_analytics_{period}d.csv"
        }
    )
