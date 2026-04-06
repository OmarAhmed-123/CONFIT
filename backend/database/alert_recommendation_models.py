"""
CONFIT Backend — Alert Recommendation Database Models
=====================================================
SQLAlchemy models for persisting recommendations, backtesting results, and A/B testing.
"""

import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Enum as SQLEnum,
    Index,
    UniqueConstraint,
    Date,
)
from sqlalchemy.orm import relationship

from database.base import Base
from database.models import UUIDType, _new_uuid


# ─── Enums ─────────────────────────────────────────────────────────────────────

class RecommendationType(str, enum.Enum):
    RETURN_SPIKE = "return_spike"
    HIGH_VALUE_AOV = "high_value_aov"
    CONVERSION_ANOMALY = "conversion_anomaly"
    INVENTORY_DEPLETION = "inventory_depletion"
    SEASONAL_ADJUSTMENT = "seasonal_adjustment"
    VIP_INACTIVITY = "vip_inactivity"


class RecommendationStatus(str, enum.Enum):
    PENDING = "pending"
    SHOWN = "shown"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    APPLIED = "applied"
    EXPIRED = "expired"


class ConfidenceLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ImpactEstimate(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ABTestGroup(str, enum.Enum):
    CONTROL = "control"
    TREATMENT = "treatment"


# ─── Alert Recommendation Model ──────────────────────────────────────────────

class AlertRecommendation(Base):
    """
    Persistent storage for alert recommendations.
    Stores personalized threshold recommendations for each store.
    """
    __tablename__ = "alert_recommendations"
    __table_args__ = (
        Index("ix_recommendations_store_id", "store_id"),
        Index("ix_recommendations_store_status", "store_id", "status"),
        Index("ix_recommendations_type", "type"),
        Index("ix_recommendations_generated_at", "generated_at"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    store_id = Column(UUIDType, ForeignKey("stores.id"), nullable=False, index=True)
    
    # Classification
    type = Column(SQLEnum(RecommendationType), nullable=False)
    status = Column(SQLEnum(RecommendationStatus), nullable=False, default=RecommendationStatus.PENDING)
    
    # Content
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Threshold recommendations (JSON array of threshold objects)
    thresholds = Column(JSON, nullable=False, default=list)
    # Format: [{"parameter_name": "returns_spike_count", "current_value": 5, "recommended_value": 20, "unit": "returns", "percentile_used": 80}]
    
    # Confidence and impact
    confidence = Column(SQLEnum(ConfidenceLevel), nullable=False, default=ConfidenceLevel.MEDIUM)
    confidence_score = Column(Float, nullable=False, default=0.5)  # 0.0 - 1.0
    impact_estimate = Column(SQLEnum(ImpactEstimate), nullable=False, default=ImpactEstimate.MEDIUM)
    
    # Explanation (JSON)
    explanation = Column(JSON, nullable=False, default=dict)
    # Format: {"summary": "...", "data_points": {...}, "methodology": "...", "historical_examples": [...]}
    
    # Backtesting results (JSON)
    backtest_summary = Column(JSON, nullable=True)
    # Format: {"total_events": 100, "true_positives": 15, "false_positives": 3, "precision": 0.83, ...}
    
    backtest_events = Column(JSON, nullable=True, default=list)
    # Format: [{"event_type": "true_positive", "timestamp": "...", "actual_value": 25, ...}]
    
    # Metadata
    data_window_days = Column(Integer, nullable=False, default=60)
    generated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # User interaction timestamps
    shown_at = Column(DateTime(timezone=True), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    
    # User feedback
    user_feedback = Column(Text, nullable=True)
    user_rating = Column(Integer, nullable=True)  # 1-5 stars
    was_valuable = Column(Boolean, nullable=True)
    
    # Ranking score for ordering
    rank_score = Column(Float, nullable=False, default=0.0)
    
    # Relationships
    store = relationship("Store", backref="alert_recommendations")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "store_id": str(self.store_id),
            "type": self.type.value if self.type else None,
            "status": self.status.value if self.status else None,
            "title": self.title,
            "description": self.description,
            "thresholds": self.thresholds or [],
            "confidence": self.confidence.value if self.confidence else None,
            "confidence_score": self.confidence_score,
            "impact_estimate": self.impact_estimate.value if self.impact_estimate else None,
            "explanation": self.explanation or {},
            "backtest_summary": self.backtest_summary,
            "backtest_events": self.backtest_events or [],
            "data_window_days": self.data_window_days,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "shown_at": self.shown_at.isoformat() if self.shown_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "dismissed_at": self.dismissed_at.isoformat() if self.dismissed_at else None,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "user_feedback": self.user_feedback,
            "user_rating": self.user_rating,
            "was_valuable": self.was_valuable,
            "rank_score": self.rank_score,
        }


# ─── Store Pattern Analysis Model ─────────────────────────────────────────────

class StorePatternAnalysis(Base):
    """
    Cached pattern analysis for a store.
    Recomputed nightly or on-demand.
    """
    __tablename__ = "store_pattern_analyses"
    __table_args__ = (
        Index("ix_pattern_analyses_store_id", "store_id", unique=True),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    store_id = Column(UUIDType, ForeignKey("stores.id"), nullable=False, unique=True)
    
    # Analysis results (JSON)
    return_patterns = Column(JSON, nullable=True)
    aov_patterns = Column(JSON, nullable=True)
    conversion_patterns = Column(JSON, nullable=True)
    inventory_patterns = Column(JSON, nullable=True)
    seasonal_patterns = Column(JSON, nullable=True)
    customer_segment_patterns = Column(JSON, nullable=True)
    
    # Metadata
    analysis_date = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    data_window_days = Column(Integer, nullable=False, default=60)
    data_quality_score = Column(Float, nullable=False, default=0.0)  # 0.0 - 1.0
    has_sufficient_data = Column(Boolean, nullable=False, default=False)
    
    # Cache invalidation
    last_transaction_at = Column(DateTime(timezone=True), nullable=True)
    invalidation_hash = Column(String(64), nullable=True)  # Hash of data to detect changes
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    store = relationship("Store", backref="pattern_analysis")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "store_id": str(self.store_id),
            "return_patterns": self.return_patterns,
            "aov_patterns": self.aov_patterns,
            "conversion_patterns": self.conversion_patterns,
            "inventory_patterns": self.inventory_patterns,
            "seasonal_patterns": self.seasonal_patterns,
            "customer_segment_patterns": self.customer_segment_patterns,
            "analysis_date": self.analysis_date.isoformat() if self.analysis_date else None,
            "data_window_days": self.data_window_days,
            "data_quality_score": self.data_quality_score,
            "has_sufficient_data": self.has_sufficient_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ─── A/B Test Experiment Model ────────────────────────────────────────────────

class ABTestExperiment(Base):
    """
    A/B test experiment configuration.
    """
    __tablename__ = "ab_test_experiments"
    __table_args__ = (
        Index("ix_experiments_is_active", "is_active"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Configuration
    control_group_size = Column(Integer, nullable=False, default=0)
    treatment_group_size = Column(Integer, nullable=False, default=0)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    min_duration_days = Column(Integer, nullable=False, default=30)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    is_paused = Column(Boolean, nullable=False, default=False)
    
    # Aggregated metrics (JSON)
    control_metrics = Column(JSON, nullable=False, default=dict)
    treatment_metrics = Column(JSON, nullable=False, default=dict)
    
    # Statistical significance
    significance_level = Column(Float, nullable=True)
    p_value = Column(Float, nullable=True)
    is_significant = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    assignments = relationship("ABTestAssignment", back_populates="experiment")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "control_group_size": self.control_group_size,
            "treatment_group_size": self.treatment_group_size,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "min_duration_days": self.min_duration_days,
            "is_active": self.is_active,
            "is_paused": self.is_paused,
            "control_metrics": self.control_metrics or {},
            "treatment_metrics": self.treatment_metrics or {},
            "significance_level": self.significance_level,
            "p_value": self.p_value,
            "is_significant": self.is_significant,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ─── A/B Test Assignment Model ─────────────────────────────────────────────────

class ABTestAssignment(Base):
    """
    Store's assignment to an A/B test group.
    """
    __tablename__ = "ab_test_assignments"
    __table_args__ = (
        Index("ix_assignments_experiment_store", "experiment_id", "store_id", unique=True),
        Index("ix_assignments_store_id", "store_id"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    experiment_id = Column(UUIDType, ForeignKey("ab_test_experiments.id"), nullable=False)
    store_id = Column(UUIDType, ForeignKey("stores.id"), nullable=False)
    group = Column(SQLEnum(ABTestGroup), nullable=False)
    
    assigned_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Metrics for this store (JSON)
    metrics = Column(JSON, nullable=False, default=dict)
    
    # Relationships
    experiment = relationship("ABTestExperiment", back_populates="assignments")
    store = relationship("Store", backref="ab_test_assignments")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "experiment_id": str(self.experiment_id),
            "store_id": str(self.store_id),
            "group": self.group.value if self.group else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "metrics": self.metrics or {},
        }


# ─── A/B Test Interaction Event Model ─────────────────────────────────────────

class ABTestInteractionEvent(Base):
    """
    Logged interaction event for A/B testing analysis.
    Immutable log for audit and analysis.
    """
    __tablename__ = "ab_test_interaction_events"
    __table_args__ = (
        Index("ix_interaction_events_experiment", "experiment_id"),
        Index("ix_interaction_events_store", "store_id"),
        Index("ix_interaction_events_timestamp", "timestamp"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    experiment_id = Column(UUIDType, ForeignKey("ab_test_experiments.id"), nullable=False)
    store_id = Column(UUIDType, ForeignKey("stores.id"), nullable=False)
    group = Column(SQLEnum(ABTestGroup), nullable=False)
    
    # Event details
    event_type = Column(String(100), nullable=False)  # recommendation_shown, recommendation_accepted, etc.
    event_data = Column(JSON, nullable=False, default=dict)
    
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    session_id = Column(String(64), nullable=True)
    
    # Relationships
    experiment = relationship("ABTestExperiment", backref="interaction_events")
    store = relationship("Store", backref="interaction_events")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "experiment_id": str(self.experiment_id),
            "store_id": str(self.store_id),
            "group": self.group.value if self.group else None,
            "event_type": self.event_type,
            "event_data": self.event_data or {},
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "session_id": self.session_id,
        }


# ─── Recommendation Interaction Log ───────────────────────────────────────────

class RecommendationInteractionLog(Base):
    """
    Immutable log of all recommendation interactions.
    Used for analytics and A/B testing.
    """
    __tablename__ = "recommendation_interaction_logs"
    __table_args__ = (
        Index("ix_rec_interaction_recommendation", "recommendation_id"),
        Index("ix_rec_interaction_store", "store_id"),
        Index("ix_rec_interaction_timestamp", "timestamp"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    recommendation_id = Column(UUIDType, ForeignKey("alert_recommendations.id"), nullable=False)
    store_id = Column(UUIDType, ForeignKey("stores.id"), nullable=False)
    
    # Interaction details
    interaction_type = Column(String(50), nullable=False)  # shown, accepted, dismissed, customized, applied
    interaction_data = Column(JSON, nullable=True)
    
    # Timing
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    time_to_action_seconds = Column(Integer, nullable=True)  # Time from shown to action
    
    # Session context
    session_id = Column(String(64), nullable=True)
    ab_test_group = Column(SQLEnum(ABTestGroup), nullable=True)
    
    # Relationships
    recommendation = relationship("AlertRecommendation", backref="interaction_logs")
    store = relationship("Store", backref="recommendation_interaction_logs")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "recommendation_id": str(self.recommendation_id),
            "store_id": str(self.store_id),
            "interaction_type": self.interaction_type,
            "interaction_data": self.interaction_data,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "time_to_action_seconds": self.time_to_action_seconds,
            "session_id": self.session_id,
            "ab_test_group": self.ab_test_group.value if self.ab_test_group else None,
        }
