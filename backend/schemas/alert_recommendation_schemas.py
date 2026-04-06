"""
CONFIT Backend — Alert Recommendation Schemas
=============================================
Pydantic schemas for the Predictive Alert Recommendations Engine.
Defines request/response models for recommendations, backtesting, and A/B testing.
"""

from datetime import datetime, date
from enum import Enum
from typing import List, Optional, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field, validator


# ─── Enums ─────────────────────────────────────────────────────────────────────

class RecommendationType(str, Enum):
    """Types of alert recommendations."""
    RETURN_SPIKE = "return_spike"
    HIGH_VALUE_AOV = "high_value_aov"
    CONVERSION_ANOMALY = "conversion_anomaly"
    INVENTORY_DEPLETION = "inventory_depletion"
    SEASONAL_ADJUSTMENT = "seasonal_adjustment"
    VIP_INACTIVITY = "vip_inactivity"


class RecommendationStatus(str, Enum):
    """Status of a recommendation."""
    PENDING = "pending"          # Generated but not shown
    SHOWN = "shown"              # Displayed to user
    ACCEPTED = "accepted"         # User accepted
    DISMISSED = "dismissed"       # User dismissed
    APPLIED = "applied"           # Applied to preferences
    EXPIRED = "expired"           # No longer relevant


class ConfidenceLevel(str, Enum):
    """Confidence level for recommendations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ABTestGroup(str, Enum):
    """A/B test group assignment."""
    CONTROL = "control"           # Recommendations shown but not auto-applied
    TREATMENT = "treatment"       # Recommendations auto-applied or one-click accept


class ImpactEstimate(str, Enum):
    """Estimated business impact."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BacktestEventType(str, Enum):
    """Types of events detected in backtesting."""
    TRUE_POSITIVE = "true_positive"     # Would have caught real anomaly
    FALSE_POSITIVE = "false_positive"   # Would have triggered unnecessarily
    TRUE_NEGATIVE = "true_negative"     # Correctly would not have triggered
    FALSE_NEGATIVE = "false_negative"   # Would have missed real anomaly


# ─── Backtesting Models ───────────────────────────────────────────────────────

class BacktestEvent(BaseModel):
    """A single event detected during backtesting."""
    event_type: BacktestEventType
    timestamp: datetime
    actual_value: float
    threshold_value: float
    deviation_percent: float
    would_have_alerted: bool
    was_actionable: Optional[bool] = None
    context: Optional[Dict[str, Any]] = None


class BacktestSummary(BaseModel):
    """Summary of backtesting results."""
    total_events: int
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float = Field(..., description="TP / (TP + FP)")
    recall: float = Field(..., description="TP / (TP + FN)")
    f1_score: float = Field(..., description="Harmonic mean of precision and recall")
    false_positive_rate: float = Field(..., description="FP / (FP + TN)")
    significant_moments_caught: int
    significant_moments_missed: int
    analysis_period_days: int
    data_points_analyzed: int


# ─── Recommendation Models ────────────────────────────────────────────────────

class ThresholdRecommendation(BaseModel):
    """A specific threshold recommendation."""
    parameter_name: str
    current_value: Any
    recommended_value: Any
    unit: str = ""  # e.g., "units", "%", "days", "$"
    percentile_used: Optional[int] = None  # e.g., 80, 85, 90


class RecommendationExplanation(BaseModel):
    """Explanation for why a recommendation was made."""
    summary: str
    data_points: Dict[str, Any]
    methodology: str
    historical_examples: List[Dict[str, Any]] = Field(default_factory=list)


class AlertRecommendation(BaseModel):
    """Complete recommendation object."""
    id: str
    store_id: str
    type: RecommendationType
    status: RecommendationStatus
    
    # Content
    title: str
    description: str
    
    # Threshold details
    thresholds: List[ThresholdRecommendation]
    
    # Confidence and impact
    confidence: ConfidenceLevel
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    impact_estimate: ImpactEstimate
    
    # Explanation
    explanation: RecommendationExplanation
    
    # Backtesting
    backtest_summary: BacktestSummary
    backtest_events: List[BacktestEvent] = Field(default_factory=list)
    
    # Metadata
    data_window_days: int = Field(default=60, ge=15, le=90)
    generated_at: datetime
    expires_at: Optional[datetime] = None
    
    # User interaction
    shown_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    user_feedback: Optional[str] = None
    
    # Ranking
    rank_score: float = Field(default=0.0, description="Score for ordering recommendations")
    
    class Config:
        use_enum_values = True


# ─── Pattern Analysis Models ──────────────────────────────────────────────────

class ReturnPatternAnalysis(BaseModel):
    """Analysis of return patterns."""
    baseline_weekly_returns: float
    return_volatility: float
    spike_threshold_80th: float
    spike_threshold_90th: float
    products_with_high_return_velocity: List[Dict[str, Any]]
    seasonal_return_patterns: Dict[str, float]  # month -> avg returns


class AOVPatternAnalysis(BaseModel):
    """Analysis of Average Order Value patterns."""
    baseline_aov: float
    aov_range_low: float
    aov_range_high: float
    outlier_threshold_85th: float
    outlier_threshold_90th: float
    high_value_order_frequency: float  # orders per month
    seasonal_aov_patterns: Dict[str, float]


class ConversionPatternAnalysis(BaseModel):
    """Analysis of conversion rate patterns."""
    baseline_conversion_rate: float
    rolling_7day_variance: float
    deviation_threshold_drop: float
    deviation_threshold_rise: float
    historical_anomalies: List[Dict[str, Any]]
    seasonal_conversion_patterns: Dict[str, float]


class InventoryVelocityAnalysis(BaseModel):
    """Analysis of inventory depletion patterns."""
    category_velocities: Dict[str, float]  # category -> units/week
    fast_mover_threshold: float
    slow_mover_threshold: float
    recommended_stock_thresholds: Dict[str, int]  # category -> units


class SeasonalPatternAnalysis(BaseModel):
    """Analysis of seasonal patterns."""
    peak_seasons: List[str]
    peak_conversion_lift_percent: float
    peak_aov_lift_percent: float
    recommended_temporary_adjustments: Dict[str, Any]


class CustomerSegmentAnalysis(BaseModel):
    """Analysis of customer segment behavior."""
    vip_avg_purchase_cycle_days: float
    returning_avg_purchase_cycle_days: float
    recommended_vip_inactivity_days: int
    recommended_returning_inactivity_days: int
    at_risk_customers: List[Dict[str, Any]]


class StorePatternAnalysis(BaseModel):
    """Complete pattern analysis for a store."""
    store_id: str
    analysis_date: datetime
    data_window_days: int
    
    return_patterns: ReturnPatternAnalysis
    aov_patterns: AOVPatternAnalysis
    conversion_patterns: ConversionPatternAnalysis
    inventory_patterns: InventoryVelocityAnalysis
    seasonal_patterns: SeasonalPatternAnalysis
    customer_segment_patterns: CustomerSegmentAnalysis
    
    data_quality_score: float = Field(..., ge=0.0, le=1.0)
    has_sufficient_data: bool


# ─── A/B Testing Models ────────────────────────────────────────────────────────

class ABTestMetrics(BaseModel):
    """Metrics tracked for A/B testing."""
    # Engagement
    engagement_velocity_seconds: Optional[float] = None
    alert_actionability_rate: Optional[float] = None
    
    # Decision making
    decision_making_velocity_seconds: Optional[float] = None
    time_from_anomaly_to_response_seconds: Optional[float] = None
    
    # Configuration
    configuration_churn_count: int = 0
    manual_threshold_adjustments: int = 0
    
    # Adoption
    recommendations_accepted: int = 0
    recommendations_dismissed: int = 0
    recommendation_adoption_rate: Optional[float] = None
    
    # Revenue proxy
    revenue_correlation_score: Optional[float] = None


class ABTestExperiment(BaseModel):
    """A/B test experiment configuration."""
    id: str
    name: str
    description: str
    
    # Configuration
    control_group_size: int
    treatment_group_size: int
    start_date: date
    end_date: Optional[date] = None
    min_duration_days: int = 30
    
    # Status
    is_active: bool = True
    is_paused: bool = False
    
    # Metrics
    control_metrics: ABTestMetrics = Field(default_factory=ABTestMetrics)
    treatment_metrics: ABTestMetrics = Field(default_factory=ABTestMetrics)
    
    # Statistical significance
    significance_level: Optional[float] = None
    p_value: Optional[float] = None
    is_significant: bool = False
    
    created_at: datetime
    updated_at: datetime


class ABTestAssignment(BaseModel):
    """Store's assignment to an A/B test group."""
    id: str
    experiment_id: str
    store_id: str
    group: ABTestGroup
    assigned_at: datetime
    metrics: ABTestMetrics = Field(default_factory=ABTestMetrics)


class ABTestInteractionEvent(BaseModel):
    """Logged interaction event for A/B testing."""
    id: str
    experiment_id: str
    store_id: str
    group: ABTestGroup
    
    event_type: str  # recommendation_shown, recommendation_accepted, alert_received, etc.
    event_data: Dict[str, Any]
    
    timestamp: datetime
    session_id: Optional[str] = None


# ─── Request/Response Models ──────────────────────────────────────────────────

class GenerateRecommendationsRequest(BaseModel):
    """Request to generate recommendations for a store."""
    store_id: str
    data_window_days: int = Field(default=60, ge=15, le=90)
    force_refresh: bool = False


class GenerateRecommendationsResponse(BaseModel):
    """Response with generated recommendations."""
    store_id: str
    recommendations: List[AlertRecommendation]
    pattern_analysis: StorePatternAnalysis
    generated_at: datetime
    cache_hit: bool = False


class ApplyRecommendationRequest(BaseModel):
    """Request to apply a recommendation."""
    recommendation_id: str
    store_id: str
    custom_thresholds: Optional[Dict[str, Any]] = None  # User customizations


class ApplyRecommendationResponse(BaseModel):
    """Response after applying a recommendation."""
    success: bool
    recommendation_id: str
    applied_thresholds: Dict[str, Any]
    updated_preferences: Dict[str, Any]


class DismissRecommendationRequest(BaseModel):
    """Request to dismiss a recommendation."""
    recommendation_id: str
    store_id: str
    reason: Optional[str] = None


class RecommendationFeedbackRequest(BaseModel):
    """User feedback on a recommendation."""
    recommendation_id: str
    store_id: str
    rating: int = Field(..., ge=1, le=5)
    feedback_text: Optional[str] = None
    was_valuable: bool


class ABTestDashboardResponse(BaseModel):
    """Dashboard data for A/B test results."""
    experiments: List[ABTestExperiment]
    total_stores_in_tests: int
    aggregate_metrics: ABTestMetrics
    significance_results: List[Dict[str, Any]]


# ─── Pagination ───────────────────────────────────────────────────────────────

class RecommendationListRequest(BaseModel):
    """Request to list recommendations."""
    store_id: str
    status: Optional[List[RecommendationStatus]] = None
    types: Optional[List[RecommendationType]] = None
    min_confidence: Optional[ConfidenceLevel] = None
    include_dismissed: bool = False
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=50)


class RecommendationListResponse(BaseModel):
    """Paginated list of recommendations."""
    recommendations: List[AlertRecommendation]
    total_count: int
    page: int
    limit: int
    has_more: bool
