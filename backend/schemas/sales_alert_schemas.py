"""
CONFIT Backend — Sales Alert Schemas
====================================
Pydantic schemas for sales alert API requests and responses.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ─── Enums ─────────────────────────────────────────────────────────────────────

class AlertType(str, Enum):
    HIGH_VALUE_ORDER = "high_value_order"
    UNUSUAL_RETURNS = "unusual_returns"
    INVENTORY_DEPLETION = "inventory_depletion"
    CONVERSION_ANOMALY = "conversion_anomaly"
    CUSTOMER_SEGMENT_CHANGE = "customer_segment_change"


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


# ─── Alert Response Schemas ────────────────────────────────────────────────────

class AlertAction(BaseModel):
    type: str
    label: str
    primary: Optional[bool] = None
    target_path: Optional[str] = None
    target_params: Optional[Dict[str, str]] = None


class SalesAlertResponse(BaseModel):
    id: str
    type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    title: str
    message: Optional[str] = None
    rich_preview: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    actions: List[AlertAction] = Field(default_factory=list)
    store_id: str
    store_name: Optional[str] = None
    created_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    read: bool = False
    dismissed: bool = False
    dedup_key: Optional[str] = None
    trigger_count: int = 1

    class Config:
        from_attributes = True


class PaginationMeta(BaseModel):
    total_rows: int
    current_page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class SalesAlertListResponse(BaseModel):
    success: bool = True
    data: List[SalesAlertResponse]
    pagination: PaginationMeta
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    sort_applied: Dict[str, str] = Field(default_factory=dict)
    cached: bool = False


# ─── Preferences Schemas ───────────────────────────────────────────────────────

class ThresholdConfig(BaseModel):
    high_value_aov_multiplier: float = 1.5
    inventory_threshold_units: int = 10
    inventory_threshold_percent: float = 20.0
    conversion_drop_threshold_percent: float = 15.0
    conversion_rise_threshold_percent: float = 20.0
    conversion_baseline_days: int = 7
    returns_spike_count: int = 5
    returns_spike_window_hours: int = 1
    returns_rate_increase_percent: float = 50.0
    vip_inactive_days: int = 30
    returning_to_inactive_days: int = 60


class FrequencyConfig(BaseModel):
    mode: str = "throttled"
    max_alerts_per_hour: int = 10
    batch_interval_minutes: int = 30
    dedup_window_minutes: int = 60
    critical_mode: str = "real_time"
    warning_mode: str = "batched"
    info_mode: str = "batched"


class TypePreference(BaseModel):
    enabled: bool = True
    frequency: str = "real_time"
    channels: List[str] = Field(default_factory=lambda: ["in_app"])


class SalesAlertPreferencesResponse(BaseModel):
    id: str
    store_id: str
    thresholds: Dict[str, Any] = Field(default_factory=dict)
    frequency: Dict[str, Any] = Field(default_factory=dict)
    type_preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class SalesAlertPreferencesUpdate(BaseModel):
    thresholds: Optional[Dict[str, Any]] = None
    frequency: Optional[Dict[str, Any]] = None
    type_preferences: Optional[Dict[str, Any]] = None


# ─── Filter & Sort Schemas ─────────────────────────────────────────────────────

class SalesAlertFilterRequest(BaseModel):
    types: Optional[List[AlertType]] = None
    severities: Optional[List[AlertSeverity]] = None
    statuses: Optional[List[AlertStatus]] = None
    read: Optional[bool] = None
    search: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class SalesAlertSortRequest(BaseModel):
    sort_by: str = "created_at"
    sort_order: str = "desc"


class PaginationRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=25, ge=1, le=100)


# ─── Summary Schemas ───────────────────────────────────────────────────────────

class SalesAlertSummaryResponse(BaseModel):
    period_days: int
    total_alerts: int
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_severity: Dict[str, int] = Field(default_factory=dict)
    by_status: Dict[str, int] = Field(default_factory=dict)
    read_rate: float = 0.0


class UnreadCountResponse(BaseModel):
    total: int
    critical: int
    warning: int
    info: int
