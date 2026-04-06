"""
CONFIT Backend — Sales Alert Database Models
=============================================
SQLAlchemy models for persisting sales alerts and preferences.
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
)
from sqlalchemy.orm import relationship

from database.base import Base
from database.models import UUIDType, _new_uuid


# ─── Enums ─────────────────────────────────────────────────────────────────────

class AlertType(str, enum.Enum):
    HIGH_VALUE_ORDER = "high_value_order"
    UNUSUAL_RETURNS = "unusual_returns"
    INVENTORY_DEPLETION = "inventory_depletion"
    CONVERSION_ANOMALY = "conversion_anomaly"
    CUSTOMER_SEGMENT_CHANGE = "customer_segment_change"


class AlertSeverity(str, enum.Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertStatus(str, enum.Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


# ─── Sales Alert Model ─────────────────────────────────────────────────────────

class SalesAlert(Base):
    """
    Persistent storage for sales alerts.
    Retained for 30 days for audit and history purposes.
    """
    __tablename__ = "sales_alerts"
    __table_args__ = (
        Index("ix_sales_alerts_store_id", "store_id"),
        Index("ix_sales_alerts_created_at", "created_at"),
        Index("ix_sales_alerts_type_severity", "type", "severity"),
        Index("ix_sales_alerts_store_status", "store_id", "status"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    
    # Alert classification
    type = Column(SQLEnum(AlertType), nullable=False)
    severity = Column(SQLEnum(AlertSeverity), nullable=False, default=AlertSeverity.WARNING)
    status = Column(SQLEnum(AlertStatus), nullable=False, default=AlertStatus.ACTIVE)
    
    # Content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    rich_preview = Column(String(500), nullable=True)
    
    # Payload (JSON data specific to alert type)
    data = Column(JSON, nullable=False, default=dict)
    
    # Actions (list of action objects with type, label, target_path)
    actions = Column(JSON, nullable=True, default=list)
    
    # Store reference
    store_id = Column(UUIDType, ForeignKey("stores.id"), nullable=False, index=True)
    store_name = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # State
    read = Column(Boolean, nullable=False, default=False)
    dismissed = Column(Boolean, nullable=False, default=False)
    
    # Deduplication metadata
    dedup_key = Column(String(255), nullable=True, index=True)
    first_triggered_at = Column(DateTime(timezone=True), nullable=True)
    trigger_count = Column(Integer, nullable=False, default=1)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    store = relationship("Store", backref="sales_alerts")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "type": self.type.value if self.type else None,
            "severity": self.severity.value if self.severity else None,
            "status": self.status.value if self.status else None,
            "title": self.title,
            "message": self.message,
            "rich_preview": self.rich_preview,
            "data": self.data or {},
            "actions": self.actions or [],
            "store_id": str(self.store_id),
            "store_name": self.store_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "read": self.read,
            "dismissed": self.dismissed,
            "dedup_key": self.dedup_key,
            "trigger_count": self.trigger_count,
        }


# ─── Alert Preferences Model ──────────────────────────────────────────────────

class SalesAlertPreferences(Base):
    """
    Store-specific alert preferences and thresholds.
    """
    __tablename__ = "sales_alert_preferences"
    __table_args__ = (
        Index("ix_alert_prefs_store_id", "store_id", unique=True),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    store_id = Column(UUIDType, ForeignKey("stores.id"), nullable=False, unique=True)
    
    # Threshold configuration (JSON)
    thresholds = Column(JSON, nullable=False, default=dict)
    # Default: {
    #   "high_value_aov_multiplier": 1.5,
    #   "inventory_threshold_units": 10,
    #   "inventory_threshold_percent": 20.0,
    #   "conversion_drop_threshold_percent": 15.0,
    #   "conversion_rise_threshold_percent": 20.0,
    #   "conversion_baseline_days": 7,
    #   "returns_spike_count": 5,
    #   "returns_spike_window_hours": 1,
    #   "returns_rate_increase_percent": 50.0,
    #   "vip_inactive_days": 30,
    #   "returning_to_inactive_days": 60,
    # }
    
    # Frequency configuration (JSON)
    frequency = Column(JSON, nullable=False, default=dict)
    # Default: {
    #   "mode": "throttled",
    #   "max_alerts_per_hour": 10,
    #   "batch_interval_minutes": 30,
    #   "dedup_window_minutes": 60,
    #   "critical_mode": "real_time",
    #   "warning_mode": "batched",
    #   "info_mode": "batched",
    # }
    
    # Per-type preferences (JSON)
    type_preferences = Column(JSON, nullable=False, default=dict)
    # Default: {
    #   "high_value_order": {"enabled": true, "frequency": "real_time", "channels": ["in_app", "push"]},
    #   "unusual_returns": {"enabled": true, "frequency": "batched_30m", "channels": ["in_app", "email"]},
    #   ...
    # }
    
    # Timestamps
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
    
    # Relationships
    store = relationship("Store", backref="alert_preferences")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "store_id": str(self.store_id),
            "thresholds": self.thresholds or {},
            "frequency": self.frequency or {},
            "type_preferences": self.type_preferences or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ─── Alert History Log ────────────────────────────────────────────────────────

class SalesAlertLog(Base):
    """
    Immutable log of alert events for audit trail.
    Retained for 30 days minimum.
    """
    __tablename__ = "sales_alert_logs"
    __table_args__ = (
        Index("ix_alert_logs_alert_id", "alert_id"),
        Index("ix_alert_logs_store_id", "store_id"),
        Index("ix_alert_logs_created_at", "created_at"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    alert_id = Column(UUIDType, ForeignKey("sales_alerts.id"), nullable=False)
    store_id = Column(UUIDType, ForeignKey("stores.id"), nullable=False)
    
    # Event details
    event_type = Column(String(50), nullable=False)  # created, read, acknowledged, resolved, dismissed
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    
    # Actor (user who performed the action)
    actor_id = Column(UUIDType, nullable=True)
    actor_type = Column(String(50), nullable=True)  # user, system, api
    
    # Timestamp
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    alert = relationship("SalesAlert", backref="logs")
    store = relationship("Store", backref="alert_logs")


# ─── Default Preferences Factory ──────────────────────────────────────────────

def get_default_thresholds() -> dict:
    """Get default threshold configuration."""
    return {
        "high_value_aov_multiplier": 1.5,
        "inventory_threshold_units": 10,
        "inventory_threshold_percent": 20.0,
        "conversion_drop_threshold_percent": 15.0,
        "conversion_rise_threshold_percent": 20.0,
        "conversion_baseline_days": 7,
        "returns_spike_count": 5,
        "returns_spike_window_hours": 1,
        "returns_rate_increase_percent": 50.0,
        "vip_inactive_days": 30,
        "returning_to_inactive_days": 60,
    }


def get_default_frequency() -> dict:
    """Get default frequency configuration."""
    return {
        "mode": "throttled",
        "max_alerts_per_hour": 10,
        "batch_interval_minutes": 30,
        "dedup_window_minutes": 60,
        "critical_mode": "real_time",
        "warning_mode": "batched",
        "info_mode": "batched",
    }


def get_default_type_preferences() -> dict:
    """Get default per-type preferences."""
    return {
        "high_value_order": {
            "enabled": True,
            "frequency": "real_time",
            "channels": ["in_app", "push"],
        },
        "unusual_returns": {
            "enabled": True,
            "frequency": "batched_30m",
            "channels": ["in_app", "email"],
        },
        "inventory_depletion": {
            "enabled": True,
            "frequency": "real_time",
            "channels": ["in_app", "email", "push"],
        },
        "conversion_anomaly": {
            "enabled": True,
            "frequency": "batched_30m",
            "channels": ["in_app"],
        },
        "customer_segment_change": {
            "enabled": True,
            "frequency": "batched_1h",
            "channels": ["in_app", "email"],
        },
    }
