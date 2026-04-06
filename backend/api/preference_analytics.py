"""
CONFIT Backend - Preference Analytics API Routes
=================================================
Dashboard endpoints for preference analytics, recommendations, and A/B testing.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_user, require_admin
from core.security.rbac import AuthContext, Role, Permission
from services.preference_analytics import (
    PreferenceAnalyticsService,
    RecipientType,
    RecommendationType,
    Recommendation,
    EngagementMetrics,
    PreferencePattern,
)
from services.preference_ab_testing import (
    PreferenceABTestingService,
    TestStatus,
    TestSegment,
    ABTestConfig,
    TestResult,
)


router = APIRouter(prefix="/analytics/preferences", tags=["Preference Analytics"])


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class RecommendationTypeEnum(str, Enum):
    FREQUENCY_OPTIMIZATION = "frequency_optimization"
    CHANNEL_OPTIMIZATION = "channel_optimization"
    FATIGUE_PREVENTION = "fatigue_prevention"
    ENGAGEMENT_IMPROVEMENT = "engagement_improvement"
    BATCH_VS_REALTIME = "batch_vs_realtime"
    TYPE_SELECTION = "type_selection"


class TestStatusEnum(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TestSegmentEnum(str, Enum):
    ALL_CUSTOMERS = "all_customers"
    ALL_OWNERS = "all_owners"
    COHORT = "cohort"
    CUSTOM = "custom"


# ─────────────────────────────────────────────────────────────────────────────
# DTOs
# ─────────────────────────────────────────────────────────────────────────────

class PreferenceDistributionDTO(BaseModel):
    snapshot_date: str
    recipient_type: str
    channel_distribution: Dict[str, Dict[str, int]]
    frequency_distribution: Dict[str, Dict[str, int]]
    type_distribution: Dict[str, Dict[str, int]]
    total_users: int


class EngagementHeatmapDTO(BaseModel):
    preference_key: str
    preference_value: str
    user_count: int
    avg_engagement_score: float
    avg_open_rate: float
    avg_click_rate: float
    avg_ignore_rate: float


class CohortPerformanceDTO(BaseModel):
    cohort_id: str
    cohort_name: str
    cohort_slug: str
    member_count: int
    avg_engagement_score: float
    avg_open_rate: float
    avg_click_rate: float
    avg_ignore_rate: float
    avg_response_time_hours: Optional[float] = None
    avg_satisfaction_score: Optional[float] = None


class RecommendationDTO(BaseModel):
    id: str
    recipient_id: str
    recipient_type: str
    recommendation_type: str
    title: str
    description: str
    suggested_changes: Dict[str, Any]
    expected_outcome: str
    expected_metrics: Dict[str, float]
    similar_users_count: int
    similar_users_improvement: float
    priority_score: float
    status: str
    created_at: datetime


class UserEngagementDTO(BaseModel):
    recipient_id: str
    recipient_type: str
    engagement_score: float
    open_rate: float
    click_rate: float
    ignore_rate: float
    unsubscribe_events: int
    channel_metrics: Dict[str, Dict[str, int]]
    active_preferences: Dict[str, Any]


class FatigueIndicatorDTO(BaseModel):
    recipient_id: str
    recipient_type: str
    ignore_rate: float
    unsubscribe_events: int
    fatigue_channel: Optional[str]
    recommendation: Optional[str]


class BusinessOutcomeDTO(BaseModel):
    owner_id: str
    store_id: str
    avg_response_time_hours: Optional[float]
    avg_satisfaction_score: Optional[float]
    orders_received: int
    orders_processed: int
    notification_action_rate: float
    batch_inquiries_pct: float
    active_preferences: Dict[str, Any]


class ABTestDTO(BaseModel):
    test_id: str
    test_name: str
    hypothesis: str
    recommendation_type: str
    segment_type: str
    status: str
    duration_days: int
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    control_sample_size: int
    treatment_sample_size: int
    is_significant: bool
    winner_group: Optional[str]
    should_rollout: bool


class ABTestResultDTO(BaseModel):
    test_id: str
    test_name: str
    status: str
    
    control_sample_size: int
    treatment_sample_size: int
    
    control_open_rate: float
    control_engagement_score: float
    treatment_open_rate: float
    treatment_engagement_score: float
    
    open_rate_p_value: Optional[float]
    engagement_p_value: Optional[float]
    
    winner_group: Optional[str]
    is_significant: bool
    should_rollout: bool
    rollout_recommendation: Optional[str]


class CreateABTestRequest(BaseModel):
    test_name: str = Field(..., min_length=3, max_length=100)
    hypothesis: str = Field(..., min_length=10, max_length=500)
    recommendation_type: RecommendationTypeEnum
    segment_type: TestSegmentEnum
    segment_definition: Dict[str, Any] = Field(default_factory=dict)
    duration_days: int = Field(14, ge=7, le=90)
    treatment_changes: Dict[str, Any] = Field(default_factory=dict)


class AcceptRecommendationRequest(BaseModel):
    recommendation_id: str


class RejectRecommendationRequest(BaseModel):
    recommendation_id: str
    reason: Optional[str] = None


class PreferenceDriftDTO(BaseModel):
    has_drift: bool
    total_changes: int
    changes_by_category: Dict[str, int]
    trends: Dict[str, str]
    recent_changes: List[Dict[str, Any]]


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def require_analytics_access(
    current_user: AuthContext = Depends(get_current_user),
) -> AuthContext:
    """Require admin, analytics, or owner role."""
    allowed_roles = {Role.ADMIN, Role.ANALYTICS, Role.STORE_OWNER, Role.FACTORY_OWNER}
    if not any(current_user.has_role(role) for role in allowed_roles):
        raise HTTPException(
            status_code=403,
            detail="Analytics access requires admin, analytics, or owner role"
        )
    return current_user


# ─────────────────────────────────────────────────────────────────────────────
# PREFERENCE DISTRIBUTION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/distribution",
    response_model=List[PreferenceDistributionDTO],
    summary="Get preference distribution across users",
)
async def get_preference_distribution(
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    recipient_type: Optional[str] = Query(None, pattern="^(customer|owner)$"),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """
    Get distribution of preference configurations across the user base.
    
    Shows how many users have each channel/frequency combination.
    """
    
    query = text("""
        SELECT 
            snapshot_date,
            recipient_type,
            channel_distribution,
            frequency_distribution,
            type_distribution,
            total_users
        FROM preference_distribution_daily
        WHERE snapshot_date >= :start_date
          AND (:recipient_type IS NULL OR recipient_type = :recipient_type)
        ORDER BY snapshot_date DESC
    """)
    
    result = await db.execute(query, {
        "start_date": datetime.utcnow().date() - timedelta(days=days),
        "recipient_type": recipient_type,
    })
    rows = result.fetchall()
    
    if not rows:
        # Generate distribution on-the-fly
        return await _generate_distribution_on_demand(db, recipient_type)
    
    return [
        PreferenceDistributionDTO(
            snapshot_date=str(row.snapshot_date),
            recipient_type=row.recipient_type,
            channel_distribution=row.channel_distribution or {},
            frequency_distribution=row.frequency_distribution or {},
            type_distribution=row.type_distribution or {},
            total_users=row.total_users or 0,
        )
        for row in rows
    ]


async def _generate_distribution_on_demand(
    db: AsyncSession,
    recipient_type: Optional[str],
) -> List[PreferenceDistributionDTO]:
    """Generate preference distribution on demand if pre-computed data not available."""
    
    query = text("""
        SELECT 
            recipient_type,
            COUNT(*) AS total_users,
            jsonb_object_agg('in_app_enabled', in_app_enabled_count) ||
            jsonb_object_agg('email_enabled', email_enabled_count) ||
            jsonb_object_agg('push_enabled', push_enabled_count) AS channel_distribution,
            jsonb_object_agg('email_real_time', email_real_time_count) ||
            jsonb_object_agg('email_daily', email_daily_count) ||
            jsonb_object_agg('email_weekly', email_weekly_count) AS frequency_distribution
        FROM (
            SELECT 
                recipient_type,
                COUNT(*) FILTER (WHERE in_app_enabled = true) AS in_app_enabled_count,
                COUNT(*) FILTER (WHERE email_enabled = true) AS email_enabled_count,
                COUNT(*) FILTER (WHERE push_enabled = true) AS push_enabled_count,
                COUNT(*) FILTER (WHERE email_frequency = 'real_time') AS email_real_time_count,
                COUNT(*) FILTER (WHERE email_frequency = 'daily_digest') AS email_daily_count,
                COUNT(*) FILTER (WHERE email_frequency = 'weekly_summary') AS email_weekly_count
            FROM notification_preferences
            WHERE (:recipient_type IS NULL OR recipient_type = :recipient_type)
            GROUP BY recipient_type
        ) subq
        GROUP BY recipient_type, in_app_enabled_count, email_enabled_count, 
                 push_enabled_count, email_real_time_count, email_daily_count, email_weekly_count
    """)
    
    result = await db.execute(query, {"recipient_type": recipient_type})
    rows = result.fetchall()
    
    return [
        PreferenceDistributionDTO(
            snapshot_date=str(datetime.utcnow().date()),
            recipient_type=row.recipient_type,
            channel_distribution=row.channel_distribution or {},
            frequency_distribution=row.frequency_distribution or {},
            type_distribution={},
            total_users=row.total_users or 0,
        )
        for row in rows
    ]


# ─────────────────────────────────────────────────────────────────────────────
# ENGAGEMENT HEATMAP ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/heatmap",
    response_model=List[EngagementHeatmapDTO],
    summary="Get engagement heatmap by preferences",
)
async def get_engagement_heatmap(
    recipient_type: Optional[str] = Query(None, pattern="^(customer|owner)$"),
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """
    Get engagement metrics correlated with preference configurations.
    
    Shows which preference combinations correlate with high/low engagement.
    """
    
    service = PreferenceAnalyticsService(db)
    
    # Get correlation data
    correlations = await service.correlate_preferences_with_engagement(
        RecipientType(recipient_type) if recipient_type else None
    )
    
    heatmap = []
    
    # Convert frequency correlations to heatmap format
    for freq, data in correlations.get("correlations", {}).get("by_frequency", {}).items():
        heatmap.append(EngagementHeatmapDTO(
            preference_key="email_frequency",
            preference_value=freq,
            user_count=data["user_count"],
            avg_engagement_score=data["avg_engagement"],
            avg_open_rate=data["avg_open_rate"],
            avg_click_rate=0,  # Would need additional calculation
            avg_ignore_rate=data["avg_ignore_rate"],
        ))
    
    # Convert channel correlations
    for combo, data in correlations.get("correlations", {}).get("by_channel_combo", {}).items():
        heatmap.append(EngagementHeatmapDTO(
            preference_key="channel_combo",
            preference_value=combo,
            user_count=data["user_count"],
            avg_engagement_score=data["avg_engagement"],
            avg_open_rate=0,
            avg_click_rate=0,
            avg_ignore_rate=0,
        ))
    
    return heatmap


# ─────────────────────────────────────────────────────────────────────────────
# COHORT PERFORMANCE ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/cohorts",
    response_model=List[CohortPerformanceDTO],
    summary="Get cohort performance metrics",
)
async def get_cohort_performance(
    cohort_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """
    Get performance metrics for each user cohort.
    
    Compare engagement and business outcomes across cohorts.
    """
    
    query = text("""
        SELECT 
            uc.id,
            uc.cohort_name,
            uc.cohort_slug,
            uc.cohort_type,
            uc.member_count,
            uc.avg_engagement_score,
            uc.avg_open_rate,
            uc.avg_click_rate,
            uc.avg_ignore_rate,
            uc.avg_response_time_hours,
            uc.avg_satisfaction_score
        FROM user_cohorts uc
        WHERE (:cohort_type IS NULL OR uc.cohort_type = :cohort_type)
        ORDER BY uc.member_count DESC
    """)
    
    result = await db.execute(query, {"cohort_type": cohort_type})
    rows = result.fetchall()
    
    return [
        CohortPerformanceDTO(
            cohort_id=str(row.id),
            cohort_name=row.cohort_name,
            cohort_slug=row.cohort_slug,
            member_count=row.member_count or 0,
            avg_engagement_score=row.avg_engagement_score or 0,
            avg_open_rate=row.avg_open_rate or 0,
            avg_click_rate=row.avg_click_rate or 0,
            avg_ignore_rate=row.avg_ignore_rate or 0,
            avg_response_time_hours=row.avg_response_time_hours,
            avg_satisfaction_score=row.avg_satisfaction_score,
        )
        for row in rows
    ]


@router.get(
    "/cohorts/{cohort_slug}/members",
    summary="Get cohort members (anonymized)",
)
async def get_cohort_members(
    cohort_slug: str,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_admin),
):
    """Get members of a specific cohort (admin only, for analysis)."""
    
    query = text("""
        SELECT 
            ucm.recipient_id,
            ucm.recipient_type,
            ucm.engagement_score,
            ucm.open_rate,
            ucm.click_rate,
            ucm.response_time_hours,
            ucm.satisfaction_score
        FROM user_cohort_membership ucm
        JOIN user_cohorts uc ON uc.id = ucm.cohort_id
        WHERE uc.cohort_slug = :cohort_slug
          AND ucm.exited_at IS NULL
        ORDER BY ucm.engagement_score DESC NULLS LAST
        LIMIT :limit
    """)
    
    result = await db.execute(query, {
        "cohort_slug": cohort_slug,
        "limit": limit,
    })
    rows = result.fetchall()
    
    # Anonymize recipient IDs for privacy
    return {
        "members": [
            {
                "recipient_id": f"user_{i}",  # Anonymized
                "recipient_type": row.recipient_type,
                "engagement_score": row.engagement_score,
                "open_rate": row.open_rate,
                "click_rate": row.click_rate,
            }
            for i, row in enumerate(rows, 1)
        ],
        "total": len(rows),
    }


# ─────────────────────────────────────────────────────────────────────────────
# FATIGUE INDICATORS ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/fatigue-indicators",
    response_model=List[FatigueIndicatorDTO],
    summary="Get users showing fatigue signals",
)
async def get_fatigue_indicators(
    min_ignore_rate: float = Query(0.5, ge=0, le=1),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """
    Get users showing notification fatigue signals.
    
    Identifies users with high ignore rates or recent unsubscribes.
    """
    
    query = text("""
        SELECT 
            em.recipient_id,
            em.recipient_type,
            em.overall_ignore_rate,
            em.unsubscribe_events,
            em.unsubscribe_channel,
            em.active_preferences
        FROM engagement_metrics em
        WHERE em.period_type = 'weekly'
          AND em.period_start >= :recent_date
          AND (em.overall_ignore_rate >= :min_ignore_rate OR em.unsubscribe_events > 0)
        ORDER BY em.overall_ignore_rate DESC, em.unsubscribe_events DESC
        LIMIT :limit
    """)
    
    result = await db.execute(query, {
        "recent_date": datetime.utcnow().date() - timedelta(days=14),
        "min_ignore_rate": min_ignore_rate,
        "limit": limit,
    })
    rows = result.fetchall()
    
    fatigue_list = []
    for row in rows:
        # Determine fatigue channel
        fatigue_channel = None
        prefs = row.active_preferences or {}
        channels = prefs.get("channels", {})
        
        for ch, settings in channels.items():
            if settings.get("enabled", True) and settings.get("frequency") == "real_time":
                fatigue_channel = ch
                break
        
        # Generate recommendation
        recommendation = None
        if fatigue_channel:
            recommendation = f"Consider switching {fatigue_channel} to daily digest"
        
        fatigue_list.append(FatigueIndicatorDTO(
            recipient_id=row.recipient_id,
            recipient_type=row.recipient_type,
            ignore_rate=row.overall_ignore_rate or 0,
            unsubscribe_events=row.unsubscribe_events or 0,
            fatigue_channel=fatigue_channel,
            recommendation=recommendation,
        ))
    
    return fatigue_list


# ─────────────────────────────────────────────────────────────────────────────
# RECOMMENDATION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/recommendations",
    response_model=List[RecommendationDTO],
    summary="Get pending recommendations for current user",
)
async def get_my_recommendations(
    force_refresh: bool = Query(False, description="Force regeneration of recommendations"),
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get personalized preference recommendations for the authenticated user."""
    
    service = PreferenceAnalyticsService(db)
    
    # Determine recipient type
    recipient_type = RecipientType.CUSTOMER
    if current_user.has_role(Role.STORE_OWNER) or current_user.has_role(Role.FACTORY_OWNER):
        recipient_type = RecipientType.OWNER
    
    recommendations = await service.generate_recommendations(
        current_user.user_id,
        recipient_type,
        force_refresh=force_refresh,
    )
    
    return [
        RecommendationDTO(
            id="",  # Would need to fetch from DB
            recipient_id=rec.recipient_id,
            recipient_type=rec.recipient_type.value,
            recommendation_type=rec.recommendation_type.value,
            title=rec.title,
            description=rec.description,
            suggested_changes=rec.suggested_changes,
            expected_outcome=rec.expected_outcome,
            expected_metrics=rec.expected_metrics,
            similar_users_count=rec.similar_users_count,
            similar_users_improvement=rec.similar_users_improvement,
            priority_score=rec.priority_score,
            status="pending",
            created_at=datetime.utcnow(),
        )
        for rec in recommendations
    ]


@router.get(
    "/recommendations/stats",
    summary="Get recommendation acceptance statistics",
)
async def get_recommendation_stats(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """Get statistics on recommendation acceptance rates and outcomes."""
    
    query = text("""
        SELECT 
            recommendation_type,
            COUNT(*) FILTER (WHERE status = 'pending') AS pending_count,
            COUNT(*) FILTER (WHERE status = 'accepted') AS accepted_count,
            COUNT(*) FILTER (WHERE status = 'rejected') AS rejected_count,
            AVG(similar_users_improvement) FILTER (WHERE status = 'accepted') AS avg_improvement_accepted,
            COUNT(*) FILTER (WHERE status = 'applied') AS applied_count
        FROM preference_recommendations
        WHERE created_at >= :start_date
        GROUP BY recommendation_type
    """)
    
    result = await db.execute(query, {
        "start_date": datetime.utcnow() - timedelta(days=days),
    })
    rows = result.fetchall()
    
    stats = []
    for row in rows:
        total = (row.pending_count or 0) + (row.accepted_count or 0) + (row.rejected_count or 0)
        acceptance_rate = (row.accepted_count or 0) / total if total > 0 else 0
        
        stats.append({
            "recommendation_type": row.recommendation_type,
            "pending_count": row.pending_count or 0,
            "accepted_count": row.accepted_count or 0,
            "rejected_count": row.rejected_count or 0,
            "applied_count": row.applied_count or 0,
            "acceptance_rate": round(acceptance_rate, 4),
            "avg_improvement_accepted": row.avg_improvement_accepted,
        })
    
    return {
        "period_days": days,
        "by_type": stats,
        "total_recommendations": sum(s.get("pending_count", 0) + s.get("accepted_count", 0) + s.get("rejected_count", 0) for s in stats),
    }


@router.post(
    "/recommendations/accept",
    summary="Accept a recommendation",
)
async def accept_recommendation(
    request: AcceptRecommendationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user),
):
    """Accept and apply a preference recommendation."""
    
    service = PreferenceAnalyticsService(db)
    
    result = await service.accept_recommendation(
        request.recommendation_id,
        current_user.user_id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to accept recommendation"))
    
    return result


@router.post(
    "/recommendations/reject",
    summary="Reject a recommendation",
)
async def reject_recommendation(
    request: RejectRecommendationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user),
):
    """Reject a preference recommendation."""
    
    service = PreferenceAnalyticsService(db)
    
    result = await service.reject_recommendation(
        request.recommendation_id,
        current_user.user_id,
        request.reason,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to reject recommendation"))
    
    return result


# ─────────────────────────────────────────────────────────────────────────────
# USER ENGAGEMENT ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/engagement/me",
    response_model=UserEngagementDTO,
    summary="Get current user's engagement metrics",
)
async def get_my_engagement(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get engagement metrics for the authenticated user."""
    
    service = PreferenceAnalyticsService(db)
    
    # Determine recipient type
    recipient_type = RecipientType.CUSTOMER
    if current_user.has_role(Role.STORE_OWNER) or current_user.has_role(Role.FACTORY_OWNER):
        recipient_type = RecipientType.OWNER
    
    metrics = await service.calculate_engagement_metrics(
        current_user.user_id,
        recipient_type,
        datetime.utcnow() - timedelta(days=days),
        datetime.utcnow(),
    )
    
    # Get current preferences
    prefs = await service._get_current_preferences(current_user.user_id, recipient_type)
    
    return UserEngagementDTO(
        recipient_id=current_user.user_id,
        recipient_type=recipient_type.value,
        engagement_score=metrics.engagement_score,
        open_rate=metrics.open_rate,
        click_rate=metrics.click_rate,
        ignore_rate=metrics.ignore_rate,
        unsubscribe_events=metrics.unsubscribe_events,
        channel_metrics=metrics.channel_metrics,
        active_preferences=prefs.to_json(),
    )


@router.get(
    "/engagement/compare",
    summary="Compare user engagement to cohort peers",
)
async def compare_to_peers(
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user),
):
    """Compare current user's engagement to their cohort peers."""
    
    # Determine recipient type
    recipient_type = RecipientType.CUSTOMER
    if current_user.has_role(Role.STORE_OWNER) or current_user.has_role(Role.FACTORY_OWNER):
        recipient_type = RecipientType.OWNER
    
    service = PreferenceAnalyticsService(db)
    
    # Get user's cohorts
    query = text("""
        SELECT uc.cohort_slug, uc.cohort_name, uc.avg_engagement_score, uc.avg_open_rate
        FROM user_cohort_membership ucm
        JOIN user_cohorts uc ON uc.id = ucm.cohort_id
        WHERE ucm.recipient_id = :recipient_id
          AND ucm.recipient_type = :recipient_type
          AND ucm.exited_at IS NULL
    """)
    
    result = await db.execute(query, {
        "recipient_id": current_user.user_id,
        "recipient_type": recipient_type.value,
    })
    cohorts = result.fetchall()
    
    # Get user's metrics
    metrics = await service.calculate_engagement_metrics(
        current_user.user_id,
        recipient_type,
        datetime.utcnow() - timedelta(days=30),
        datetime.utcnow(),
    )
    
    comparisons = []
    for cohort in cohorts:
        cohort_avg = cohort.avg_engagement_score or 50
        diff = metrics.engagement_score - cohort_avg
        percentile = min(max(50 + diff, 0), 100)
        
        comparisons.append({
            "cohort_name": cohort.cohort_name,
            "your_score": round(metrics.engagement_score, 2),
            "cohort_avg": round(cohort_avg, 2),
            "percentile": round(percentile, 1),
            "comparison": "above" if diff > 0 else "below" if diff < 0 else "at",
        })
    
    return {
        "your_engagement_score": round(metrics.engagement_score, 2),
        "comparisons": comparisons,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PREFERENCE DRIFT ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/drift/me",
    response_model=PreferenceDriftDTO,
    summary="Get preference drift for current user",
)
async def get_my_preference_drift(
    days: int = Query(90, ge=30, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user),
):
    """Analyze how the user's preferences have evolved over time."""
    
    service = PreferenceAnalyticsService(db)
    
    # Determine recipient type
    recipient_type = RecipientType.CUSTOMER
    if current_user.has_role(Role.STORE_OWNER) or current_user.has_role(Role.FACTORY_OWNER):
        recipient_type = RecipientType.OWNER
    
    drift = await service.detect_preference_drift(
        current_user.user_id,
        recipient_type,
        days,
    )
    
    return PreferenceDriftDTO(
        has_drift=drift.get("has_drift", False),
        total_changes=drift.get("total_changes", 0),
        changes_by_category=drift.get("changes_by_category", {}),
        trends=drift.get("trends", {}),
        recent_changes=drift.get("recent_changes", []),
    )


# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS OUTCOMES ENDPOINTS (OWNERS)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/business-outcomes/me",
    response_model=BusinessOutcomeDTO,
    summary="Get business outcomes for store owner",
)
async def get_my_business_outcomes(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get business outcome metrics for the authenticated store owner."""
    
    if not (current_user.has_role(Role.STORE_OWNER) or current_user.has_role(Role.FACTORY_OWNER)):
        raise HTTPException(status_code=403, detail="This endpoint is for store/factory owners only")
    
    service = PreferenceAnalyticsService(db)
    
    # Get store ID from user's profile
    store_query = text("""
        SELECT store_id FROM store_owners WHERE user_id = :user_id LIMIT 1
    """)
    store_result = await db.execute(store_query, {"user_id": current_user.user_id})
    store_row = store_result.fetchone()
    
    store_id = store_row.store_id if store_row else "default"
    
    outcome = await service.get_business_outcomes_for_owner(
        current_user.user_id,
        store_id,
        days,
    )
    
    if not outcome:
        return BusinessOutcomeDTO(
            owner_id=current_user.user_id,
            store_id=store_id,
            avg_response_time_hours=None,
            avg_satisfaction_score=None,
            orders_received=0,
            orders_processed=0,
            notification_action_rate=0,
            batch_inquiries_pct=0,
            active_preferences={},
        )
    
    prefs = await service._get_current_preferences(
        current_user.user_id, RecipientType.OWNER
    )
    
    return BusinessOutcomeDTO(
        owner_id=outcome.owner_id,
        store_id=outcome.store_id,
        avg_response_time_hours=outcome.avg_response_time_hours,
        avg_satisfaction_score=outcome.avg_satisfaction_score,
        orders_received=outcome.orders_received,
        orders_processed=outcome.orders_processed,
        notification_action_rate=outcome.notification_action_rate,
        batch_inquiries_pct=outcome.batch_inquiries_pct,
        active_preferences=prefs.to_json(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# A/B TEST ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/ab-tests",
    response_model=List[ABTestDTO],
    summary="Get all A/B tests",
)
async def list_ab_tests(
    status: Optional[TestStatusEnum] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """List all A/B tests with optional status filter."""
    
    service = PreferenceABTestingService(db)
    
    tests = await service.list_tests(
        TestStatus(status) if status else None,
        limit,
    )
    
    return [
        ABTestDTO(
            test_id=test.test_id,
            test_name=test.test_name,
            hypothesis="",  # Would need to fetch
            recommendation_type="engagement_improvement",
            segment_type="all_customers",
            status=test.status.value,
            duration_days=14,
            start_date=None,
            end_date=None,
            control_sample_size=test.control_sample_size,
            treatment_sample_size=test.treatment_sample_size,
            is_significant=test.is_significant,
            winner_group=test.winner_group.value if test.winner_group else None,
            should_rollout=test.should_rollout,
        )
        for test in tests
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
    """Create a new A/B test for preference recommendations."""
    
    service = PreferenceABTestingService(db)
    
    config = ABTestConfig(
        test_id="",  # Generated by service
        test_name=request.test_name,
        hypothesis=request.hypothesis,
        recommendation_type=request.recommendation_type.value,
        segment_type=TestSegment(request.segment_type.value),
        segment_definition=request.segment_definition,
        duration_days=request.duration_days,
        treatment_changes=request.treatment_changes,
    )
    
    test_id = await service.create_test(config)
    
    return ABTestDTO(
        test_id=test_id,
        test_name=request.test_name,
        hypothesis=request.hypothesis,
        recommendation_type=request.recommendation_type.value,
        segment_type=request.segment_type.value,
        status="draft",
        duration_days=request.duration_days,
        control_sample_size=0,
        treatment_sample_size=0,
        is_significant=False,
        winner_group=None,
        should_rollout=False,
    )


@router.post(
    "/ab-tests/{test_id}/start",
    summary="Start an A/B test",
)
async def start_ab_test(
    test_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_admin),
):
    """Start a draft A/B test."""
    
    service = PreferenceABTestingService(db)
    
    result = await service.start_test(test_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


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
    
    service = PreferenceABTestingService(db)
    
    result = await service.pause_test(test_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post(
    "/ab-tests/{test_id}/complete",
    response_model=ABTestResultDTO,
    summary="Complete an A/B test and calculate results",
)
async def complete_ab_test(
    test_id: str,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_admin),
):
    """Complete a test and calculate final results with statistical analysis."""
    
    service = PreferenceABTestingService(db)
    
    result = await service.complete_test(test_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    test_result = await service.get_test_results(test_id)
    
    if not test_result:
        raise HTTPException(status_code=404, detail="Test results not found")
    
    return ABTestResultDTO(
        test_id=test_result.test_id,
        test_name=test_result.test_name,
        status=test_result.status.value,
        control_sample_size=test_result.control_sample_size,
        treatment_sample_size=test_result.treatment_sample_size,
        control_open_rate=test_result.control_open_rate,
        control_engagement_score=test_result.control_engagement_score,
        treatment_open_rate=test_result.treatment_open_rate,
        treatment_engagement_score=test_result.treatment_engagement_score,
        open_rate_p_value=test_result.open_rate_p_value,
        engagement_p_value=test_result.engagement_p_value,
        winner_group=test_result.winner_group.value if test_result.winner_group else None,
        is_significant=test_result.is_significant,
        should_rollout=test_result.should_rollout,
        rollout_recommendation=test_result.rollout_recommendation,
    )


@router.get(
    "/ab-tests/{test_id}/results",
    response_model=ABTestResultDTO,
    summary="Get A/B test results",
)
async def get_ab_test_results(
    test_id: str,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """Get results for a specific A/B test."""
    
    service = PreferenceABTestingService(db)
    
    test_result = await service.get_test_results(test_id)
    
    if not test_result:
        raise HTTPException(status_code=404, detail="Test not found")
    
    return ABTestResultDTO(
        test_id=test_result.test_id,
        test_name=test_result.test_name,
        status=test_result.status.value,
        control_sample_size=test_result.control_sample_size,
        treatment_sample_size=test_result.treatment_sample_size,
        control_open_rate=test_result.control_open_rate,
        control_engagement_score=test_result.control_engagement_score,
        treatment_open_rate=test_result.treatment_open_rate,
        treatment_engagement_score=test_result.treatment_engagement_score,
        open_rate_p_value=test_result.open_rate_p_value,
        engagement_p_value=test_result.engagement_p_value,
        winner_group=test_result.winner_group.value if test_result.winner_group else None,
        is_significant=test_result.is_significant,
        should_rollout=test_result.should_rollout,
        rollout_recommendation=test_result.rollout_recommendation,
    )


@router.get(
    "/ab-tests/{test_id}/interim",
    summary="Get interim results for running test",
)
async def get_interim_results(
    test_id: str,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """Get interim results for a running A/B test (for monitoring only)."""
    
    service = PreferenceABTestingService(db)
    
    result = await service.get_interim_results(test_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.post(
    "/ab-tests/{test_id}/rollout",
    summary="Roll out winning preference to all users",
)
async def rollout_test_results(
    test_id: str,
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_admin),
):
    """Roll out the winning preference configuration to all eligible users."""
    
    service = PreferenceABTestingService(db)
    
    result = await service.rollout_winning_preference(test_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


# ─────────────────────────────────────────────────────────────────────────────
# PATTERN DISCOVERY ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/patterns",
    summary="Get discovered preference patterns",
)
async def get_preference_patterns(
    min_prevalence: float = Query(5.0, ge=1, le=50),
    recipient_type: Optional[str] = Query(None, pattern="^(customer|owner)$"),
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_analytics_access),
):
    """Get discovered preference patterns with engagement correlations."""
    
    service = PreferenceAnalyticsService(db)
    
    patterns = await service.analyze_preference_patterns(
        RecipientType(recipient_type) if recipient_type else None,
        min_prevalence,
    )
    
    return {
        "patterns": [
            {
                "pattern_name": p.pattern_name,
                "pattern_type": p.pattern_type,
                "prevalence_pct": round(p.prevalence_pct, 2),
                "avg_engagement_score": round(p.avg_engagement_score, 2),
                "engagement_correlation": round(p.engagement_correlation, 4),
                "is_recommendation_candidate": p.is_recommendation_candidate,
            }
            for p in patterns
        ],
        "total_patterns": len(patterns),
    }


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN ANALYTICS SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    summary="Get admin analytics summary",
)
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db),
    _: AuthContext = Depends(require_admin),
):
    """Get comprehensive analytics summary for admin dashboard."""
    
    # Get total users with preferences
    total_query = text("""
        SELECT 
            recipient_type,
            COUNT(DISTINCT recipient_id) AS total_users
        FROM notification_preferences
        GROUP BY recipient_type
    """)
    total_result = await db.execute(total_query)
    total_rows = total_result.fetchall()
    
    # Get average engagement
    engagement_query = text("""
        SELECT 
            recipient_type,
            AVG(engagement_score) AS avg_engagement,
            AVG(overall_open_rate) AS avg_open_rate,
            AVG(overall_click_rate) AS avg_click_rate
        FROM engagement_metrics
        WHERE period_type = 'weekly'
          AND period_start >= :recent_date
        GROUP BY recipient_type
    """)
    engagement_result = await db.execute(
        engagement_query,
        {"recent_date": datetime.utcnow().date() - timedelta(days=14)},
    )
    engagement_rows = engagement_result.fetchall()
    
    # Get recommendation stats
    rec_query = text("""
        SELECT 
            COUNT(*) FILTER (WHERE status = 'pending') AS pending,
            COUNT(*) FILTER (WHERE status = 'accepted') AS accepted,
            COUNT(*) FILTER (WHERE status = 'rejected') AS rejected
        FROM preference_recommendations
        WHERE created_at >= :recent_date
    """)
    rec_result = await db.execute(
        rec_query,
        {"recent_date": datetime.utcnow() - timedelta(days=30)},
    )
    rec_row = rec_result.fetchone()
    
    # Get active tests
    test_query = text("""
        SELECT COUNT(*) AS active_tests
        FROM preference_ab_test_results
        WHERE status = 'running'
    """)
    test_result = await db.execute(test_query)
    test_row = test_result.fetchone()
    
    # Get fatigue users
    fatigue_query = text("""
        SELECT COUNT(DISTINCT recipient_id) AS fatigue_users
        FROM engagement_metrics
        WHERE period_type = 'weekly'
          AND period_start >= :recent_date
          AND overall_ignore_rate > 0.5
    """)
    fatigue_result = await db.execute(
        fatigue_query,
        {"recent_date": datetime.utcnow().date() - timedelta(days=14)},
    )
    fatigue_row = fatigue_result.fetchone()
    
    return {
        "users": {
            row.recipient_type: row.total_users
            for row in total_rows
        },
        "engagement": {
            row.recipient_type: {
                "avg_engagement_score": round(row.avg_engagement or 0, 2),
                "avg_open_rate": round(row.avg_open_rate or 0, 4),
                "avg_click_rate": round(row.avg_click_rate or 0, 4),
            }
            for row in engagement_rows
        },
        "recommendations": {
            "pending": rec_row.pending or 0,
            "accepted": rec_row.accepted or 0,
            "rejected": rec_row.rejected or 0,
            "acceptance_rate": round(
                (rec_row.accepted or 0) / max((rec_row.accepted or 0) + (rec_row.rejected or 0), 1), 4
            ),
        },
        "ab_tests": {
            "active": test_row.active_tests or 0,
        },
        "fatigue": {
            "users_at_risk": fatigue_row.fatigue_users or 0,
        },
        "generated_at": datetime.utcnow().isoformat(),
    }
