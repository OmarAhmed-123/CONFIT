"""
CONFIT Backend - Alert Rules Configuration API
===============================================
CRUD endpoints for store-level alert configuration.
Supports real-time validation, presets, and intelligent defaults.
"""

from datetime import datetime, time
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body
from pydantic import BaseModel, Field, validator
from sqlalchemy import text, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_user, get_current_user_id
from core.security.rbac import AuthContext, Role


router = APIRouter(prefix="/api/alert-rules", tags=["Alert Rules Configuration"])


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class DeliveryMode(str, Enum):
    REAL_TIME = "real_time"
    HOURLY_DIGEST = "hourly_digest"
    DAILY_SUMMARY = "daily_summary"


class AlertFrequency(str, Enum):
    REAL_TIME = "real_time"
    BATCHED_15M = "batched_15m"
    BATCHED_30M = "batched_30m"
    BATCHED_1H = "batched_1h"
    DISABLED = "disabled"


class SensitivityPreset(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class InventoryVelocityPreset(str, Enum):
    FAST_MOVER = "fast_mover"
    BALANCED = "balanced"
    SLOW_MOVER = "slow_mover"


class AlertType(str, Enum):
    HIGH_VALUE_ORDER = "high_value_order"
    UNUSUAL_RETURNS = "unusual_returns"
    INVENTORY_DEPLETION = "inventory_depletion"
    CONVERSION_ANOMALY = "conversion_anomaly"
    CUSTOMER_SEGMENT = "customer_segment"


# ─────────────────────────────────────────────────────────────────────────────
# INDUSTRY BENCHMARKS (for validation warnings)
# ─────────────────────────────────────────────────────────────────────────────

LUXURY_RETAIL_BENCHMARKS = {
    "high_value_aov_multiplier": {"min": 1.3, "recommended": 1.5, "max": 2.5},
    "conversion_drop_threshold": {"min": 10, "recommended": 15, "max": 25},
    "conversion_rise_threshold": {"min": 15, "recommended": 20, "max": 35},
    "returns_spike_multiplier": {"min": 2.0, "recommended": 3.0, "max": 5.0},
    "inventory_threshold_units": {"min": 5, "recommended": 10, "max": 50},
    "vip_inactive_days": {"min": 21, "recommended": 30, "max": 60},
    "returning_inactive_days": {"min": 30, "recommended": 45, "max": 90},
}


# ─────────────────────────────────────────────────────────────────────────────
# DTOS
# ─────────────────────────────────────────────────────────────────────────────

class AlertTypeConfigDTO(BaseModel):
    """Configuration for a single alert type."""
    enabled: bool = True
    frequency: AlertFrequency = AlertFrequency.REAL_TIME
    channels: List[str] = Field(default_factory=lambda: ["in_app"])


class ThresholdConfigDTO(BaseModel):
    """Threshold configuration for all alert types."""
    # High-Value Orders
    high_value_aov_multiplier: Decimal = Field(default=Decimal("1.5"), ge=1.0, le=5.0)
    high_value_min_order_value: Optional[Decimal] = Field(default=None, ge=0)
    
    # Inventory
    inventory_threshold_units: int = Field(default=10, ge=1, le=500)
    inventory_threshold_percent: Decimal = Field(default=Decimal("20.0"), ge=1.0, le=100.0)
    inventory_velocity_preset: InventoryVelocityPreset = InventoryVelocityPreset.BALANCED
    
    # Conversion
    conversion_drop_threshold_percent: Decimal = Field(default=Decimal("15.0"), ge=5.0, le=50.0)
    conversion_rise_threshold_percent: Decimal = Field(default=Decimal("20.0"), ge=10.0, le=100.0)
    conversion_baseline_days: int = Field(default=7, ge=1, le=30)
    conversion_sensitivity_preset: SensitivityPreset = SensitivityPreset.MODERATE
    
    # Returns
    returns_spike_multiplier: Decimal = Field(default=Decimal("3.0"), ge=1.0, le=10.0)
    returns_spike_window_hours: int = Field(default=24, ge=1, le=168)
    returns_sensitivity_preset: SensitivityPreset = SensitivityPreset.MODERATE
    
    # Customer Segment
    vip_inactive_days: int = Field(default=30, ge=7, le=180)
    returning_inactive_days: int = Field(default=45, ge=14, le=365)
    customer_sensitivity_preset: SensitivityPreset = SensitivityPreset.MODERATE


class DoNotDisturbConfigDTO(BaseModel):
    """Do-not-disturb window configuration."""
    enabled: bool = False
    start_time: Optional[time] = Field(default=None, description="DND start time (e.g., 20:00)")
    end_time: Optional[time] = Field(default=None, description="DND end time (e.g., 08:00)")
    timezone: str = Field(default="UTC", max_length=50)
    allow_critical: bool = Field(default=True, description="Allow critical alerts during DND")


class FrequencyConfigDTO(BaseModel):
    """Global frequency and delivery configuration."""
    delivery_mode: DeliveryMode = DeliveryMode.REAL_TIME
    max_alerts_per_hour: int = Field(default=10, ge=1, le=100)
    max_alerts_per_day: int = Field(default=50, ge=1, le=500)
    dedup_window_minutes: int = Field(default=60, ge=15, le=480)
    critical_delivery_mode: AlertFrequency = AlertFrequency.REAL_TIME
    warning_delivery_mode: AlertFrequency = AlertFrequency.BATCHED_30M
    info_delivery_mode: AlertFrequency = AlertFrequency.BATCHED_1H


class AlertRulesConfigDTO(BaseModel):
    """Complete alert rules configuration for a store."""
    store_id: UUID
    
    # Alert type toggles
    high_value_order: AlertTypeConfigDTO = Field(default_factory=AlertTypeConfigDTO)
    unusual_returns: AlertTypeConfigDTO = Field(default_factory=lambda: AlertTypeConfigDTO(frequency=AlertFrequency.BATCHED_30M))
    inventory_depletion: AlertTypeConfigDTO = Field(default_factory=AlertTypeConfigDTO)
    conversion_anomaly: AlertTypeConfigDTO = Field(default_factory=lambda: AlertTypeConfigDTO(frequency=AlertFrequency.BATCHED_30M))
    customer_segment: AlertTypeConfigDTO = Field(default_factory=lambda: AlertTypeConfigDTO(frequency=AlertFrequency.BATCHED_1H))
    
    # Thresholds
    thresholds: ThresholdConfigDTO = Field(default_factory=ThresholdConfigDTO)
    
    # Frequency
    frequency: FrequencyConfigDTO = Field(default_factory=FrequencyConfigDTO)
    
    # DND
    do_not_disturb: DoNotDisturbConfigDTO = Field(default_factory=DoNotDisturbConfigDTO)
    
    # Metadata
    is_customized: bool = False
    version: int = 1


class AlertRulesUpdateDTO(BaseModel):
    """Update request for alert rules configuration."""
    # Alert type toggles (optional updates)
    high_value_order: Optional[AlertTypeConfigDTO] = None
    unusual_returns: Optional[AlertTypeConfigDTO] = None
    inventory_depletion: Optional[AlertTypeConfigDTO] = None
    conversion_anomaly: Optional[AlertTypeConfigDTO] = None
    customer_segment: Optional[AlertTypeConfigDTO] = None
    
    # Thresholds (optional updates)
    thresholds: Optional[ThresholdConfigDTO] = None
    
    # Frequency (optional updates)
    frequency: Optional[FrequencyConfigDTO] = None
    
    # DND (optional updates)
    do_not_disturb: Optional[DoNotDisturbConfigDTO] = None
    
    # Version for optimistic locking
    version: int = Field(..., description="Current version for optimistic locking")


class ValidationWarning(BaseModel):
    """A non-blocking validation warning."""
    field: str
    message: str
    current_value: Any
    benchmark_value: Any
    severity: str = "info"  # "info", "warning", "critical"


class AlertRulesResponse(BaseModel):
    """Response for alert rules operations."""
    success: bool = True
    data: Optional[AlertRulesConfigDTO] = None
    warnings: List[ValidationWarning] = Field(default_factory=list)
    error: Optional[str] = None


class PresetApplicationDTO(BaseModel):
    """Request to apply a preset to threshold configuration."""
    preset_type: str = Field(..., description="Type: 'conservative', 'moderate', 'aggressive'")
    target_fields: Optional[List[str]] = Field(default=None, description="Specific fields to update, or all if None")


class StoreMetricsDTO(BaseModel):
    """Store metrics for intelligent preset calculations."""
    avg_order_value: Optional[Decimal] = None
    median_order_value: Optional[Decimal] = None
    avg_conversion_rate: Optional[Decimal] = None
    avg_return_rate: Optional[Decimal] = None


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def validate_thresholds_against_benchmarks(
    thresholds: ThresholdConfigDTO,
    store_metrics: Optional[StoreMetricsDTO] = None
) -> List[ValidationWarning]:
    """Validate thresholds against industry benchmarks and return warnings."""
    warnings = []
    
    # High Value AOV Multiplier
    if thresholds.high_value_aov_multiplier < Decimal(str(LUXURY_RETAIL_BENCHMARKS["high_value_aov_multiplier"]["min"])):
        warnings.append(ValidationWarning(
            field="high_value_aov_multiplier",
            message=f"AOV multiplier {thresholds.high_value_aov_multiplier}x is very low. You may receive excessive alerts for normal orders.",
            current_value=float(thresholds.high_value_aov_multiplier),
            benchmark_value=LUXURY_RETAIL_BENCHMARKS["high_value_aov_multiplier"]["recommended"],
            severity="warning"
        ))
    elif thresholds.high_value_aov_multiplier > Decimal(str(LUXURY_RETAIL_BENCHMARKS["high_value_aov_multiplier"]["max"])):
        warnings.append(ValidationWarning(
            field="high_value_aov_multiplier",
            message=f"AOV multiplier {thresholds.high_value_aov_multiplier}x is unusually high. You may miss important high-value orders.",
            current_value=float(thresholds.high_value_aov_multiplier),
            benchmark_value=LUXURY_RETAIL_BENCHMARKS["high_value_aov_multiplier"]["recommended"],
            severity="warning"
        ))
    
    # Conversion Drop Threshold
    if thresholds.conversion_drop_threshold_percent > Decimal("20"):
        warnings.append(ValidationWarning(
            field="conversion_drop_threshold_percent",
            message=f"This conversion anomaly threshold (±{thresholds.conversion_drop_threshold_percent}%) is higher than typical luxury retail. You may miss important dips.",
            current_value=float(thresholds.conversion_drop_threshold_percent),
            benchmark_value=LUXURY_RETAIL_BENCHMARKS["conversion_drop_threshold"]["recommended"],
            severity="info"
        ))
    
    # Returns Spike Multiplier
    if thresholds.returns_spike_multiplier > Decimal("4.0"):
        warnings.append(ValidationWarning(
            field="returns_spike_multiplier",
            message=f"Returns spike threshold {thresholds.returns_spike_multiplier}x is high. Consider a lower threshold to catch return issues earlier.",
            current_value=float(thresholds.returns_spike_multiplier),
            benchmark_value=LUXURY_RETAIL_BENCHMARKS["returns_spike_multiplier"]["recommended"],
            severity="info"
        ))
    
    # VIP Inactive Days
    if thresholds.vip_inactive_days > 45:
        warnings.append(ValidationWarning(
            field="vip_inactive_days",
            message=f"VIP inactivity threshold of {thresholds.vip_inactive_days} days is generous. Consider shorter windows for luxury customer engagement.",
            current_value=thresholds.vip_inactive_days,
            benchmark_value=LUXURY_RETAIL_BENCHMARKS["vip_inactive_days"]["recommended"],
            severity="info"
        ))
    
    # Check against store metrics if available
    if store_metrics and store_metrics.median_order_value and thresholds.high_value_min_order_value:
        if thresholds.high_value_min_order_value < store_metrics.median_order_value:
            warnings.append(ValidationWarning(
                field="high_value_min_order_value",
                message=f"Minimum order value ${thresholds.high_value_min_order_value} is below your median order value ${store_metrics.median_order_value}. This may trigger alerts for typical orders.",
                current_value=float(thresholds.high_value_min_order_value),
                benchmark_value=float(store_metrics.median_order_value),
                severity="warning"
            ))
    
    return warnings


async def get_store_id_for_user(
    db: AsyncSession,
    user_id: UUID
) -> Optional[UUID]:
    """Get the store ID that a user has access to."""
    result = await db.execute(
        text("""
            SELECT s.id 
            FROM public.stores s
            JOIN public.brand_managers bm ON bm.brand_id = s.brand_id
            WHERE bm.user_id = :user_id AND bm.is_active = TRUE
            LIMIT 1
        """),
        {"user_id": str(user_id)}
    )
    row = result.fetchone()
    return UUID(row[0]) if row else None


async def get_store_metrics(db: AsyncSession, store_id: UUID) -> Optional[StoreMetricsDTO]:
    """Get cached store metrics for preset calculations."""
    result = await db.execute(
        text("""
            SELECT store_avg_order_value, store_median_order_value,
                   store_avg_conversion_rate, store_avg_return_rate
            FROM public.alert_rules
            WHERE store_id = :store_id
        """),
        {"store_id": str(store_id)}
    )
    row = result.fetchone()
    if row and row[0]:
        return StoreMetricsDTO(
            avg_order_value=row[0],
            median_order_value=row[1],
            avg_conversion_rate=row[2],
            avg_return_rate=row[3]
        )
    return None


def row_to_dto(row: Any) -> AlertRulesConfigDTO:
    """Convert a database row to AlertRulesConfigDTO."""
    return AlertRulesConfigDTO(
        store_id=UUID(row.store_id),
        high_value_order=AlertTypeConfigDTO(
            enabled=row.high_value_order_enabled,
            frequency=AlertFrequency(row.high_value_order_frequency),
            channels=list(row.high_value_order_channels) if row.high_value_order_channels else ["in_app"]
        ),
        unusual_returns=AlertTypeConfigDTO(
            enabled=row.unusual_returns_enabled,
            frequency=AlertFrequency(row.unusual_returns_frequency),
            channels=list(row.unusual_returns_channels) if row.unusual_returns_channels else ["in_app"]
        ),
        inventory_depletion=AlertTypeConfigDTO(
            enabled=row.inventory_depletion_enabled,
            frequency=AlertFrequency(row.inventory_depletion_frequency),
            channels=list(row.inventory_depletion_channels) if row.inventory_depletion_channels else ["in_app"]
        ),
        conversion_anomaly=AlertTypeConfigDTO(
            enabled=row.conversion_anomaly_enabled,
            frequency=AlertFrequency(row.conversion_anomaly_frequency),
            channels=list(row.conversion_anomaly_channels) if row.conversion_anomaly_channels else ["in_app"]
        ),
        customer_segment=AlertTypeConfigDTO(
            enabled=row.customer_segment_enabled,
            frequency=AlertFrequency(row.customer_segment_frequency),
            channels=list(row.customer_segment_channels) if row.customer_segment_channels else ["in_app"]
        ),
        thresholds=ThresholdConfigDTO(
            high_value_aov_multiplier=row.high_value_aov_multiplier or Decimal("1.5"),
            high_value_min_order_value=row.high_value_min_order_value,
            inventory_threshold_units=row.inventory_threshold_units or 10,
            inventory_threshold_percent=row.inventory_threshold_percent or Decimal("20.0"),
            inventory_velocity_preset=InventoryVelocityPreset(row.inventory_velocity_preset or "balanced"),
            conversion_drop_threshold_percent=row.conversion_drop_threshold_percent or Decimal("15.0"),
            conversion_rise_threshold_percent=row.conversion_rise_threshold_percent or Decimal("20.0"),
            conversion_baseline_days=row.conversion_baseline_days or 7,
            conversion_sensitivity_preset=SensitivityPreset(row.conversion_sensitivity_preset or "moderate"),
            returns_spike_multiplier=row.returns_spike_multiplier or Decimal("3.0"),
            returns_spike_window_hours=row.returns_spike_window_hours or 24,
            returns_sensitivity_preset=SensitivityPreset(row.returns_sensitivity_preset or "moderate"),
            vip_inactive_days=row.vip_inactive_days or 30,
            returning_inactive_days=row.returning_inactive_days or 45,
            customer_sensitivity_preset=SensitivityPreset(row.customer_sensitivity_preset or "moderate")
        ),
        frequency=FrequencyConfigDTO(
            delivery_mode=DeliveryMode(row.delivery_mode or "real_time"),
            max_alerts_per_hour=row.max_alerts_per_hour or 10,
            max_alerts_per_day=row.max_alerts_per_day or 50,
            dedup_window_minutes=row.dedup_window_minutes or 60,
            critical_delivery_mode=AlertFrequency(row.critical_delivery_mode or "real_time"),
            warning_delivery_mode=AlertFrequency(row.warning_delivery_mode or "batched"),
            info_delivery_mode=AlertFrequency(row.info_delivery_mode or "batched")
        ),
        do_not_disturb=DoNotDisturbConfigDTO(
            enabled=row.dnd_enabled or False,
            start_time=row.dnd_start_time,
            end_time=row.dnd_end_time,
            timezone=row.dnd_timezone or "UTC",
            allow_critical=row.dnd_allow_critical if row.dnd_allow_critical is not None else True
        ),
        is_customized=row.is_customized or False,
        version=row.version or 1
    )


# ─────────────────────────────────────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{store_id}", response_model=AlertRulesResponse)
async def get_alert_rules(
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user)
):
    """
    Get alert rules configuration for a store.
    Creates default configuration if none exists.
    """
    # Verify user has access to this store
    user_store_id = await get_store_id_for_user(db, UUID(current_user.user_id))
    if not user_store_id or user_store_id != store_id:
        raise HTTPException(status_code=403, detail="Access denied to this store")
    
    # Get or create configuration
    result = await db.execute(
        text("""
            SELECT * FROM public.alert_rules 
            WHERE store_id = :store_id AND deleted_at IS NULL
        """),
        {"store_id": str(store_id)}
    )
    row = result.fetchone()
    
    if not row:
        # Create default configuration
        await db.execute(
            text("""
                INSERT INTO public.alert_rules (store_id)
                VALUES (:store_id)
            """),
            {"store_id": str(store_id)}
        )
        await db.commit()
        
        # Fetch the newly created config
        result = await db.execute(
            text("""
                SELECT * FROM public.alert_rules 
                WHERE store_id = :store_id AND deleted_at IS NULL
            """),
            {"store_id": str(store_id)}
        )
        row = result.fetchone()
    
    config = row_to_dto(row)
    
    # Get store metrics and validate against benchmarks
    store_metrics = await get_store_metrics(db, store_id)
    warnings = validate_thresholds_against_benchmarks(config.thresholds, store_metrics)
    
    return AlertRulesResponse(
        success=True,
        data=config,
        warnings=warnings
    )


@router.put("/{store_id}", response_model=AlertRulesResponse)
async def update_alert_rules(
    store_id: UUID,
    update_data: AlertRulesUpdateDTO,
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user)
):
    """
    Update alert rules configuration for a store.
    Uses optimistic locking via version field.
    """
    # Verify user has access to this store
    user_store_id = await get_store_id_for_user(db, UUID(current_user.user_id))
    if not user_store_id or user_store_id != store_id:
        raise HTTPException(status_code=403, detail="Access denied to this store")
    
    # Get current configuration
    result = await db.execute(
        text("""
            SELECT * FROM public.alert_rules 
            WHERE store_id = :store_id AND deleted_at IS NULL
        """),
        {"store_id": str(store_id)}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Alert configuration not found")
    
    # Check version for optimistic locking
    if row.version != update_data.version:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Configuration has been modified by another session",
                "current_version": row.version,
                "your_version": update_data.version
            }
        )
    
    # Build update query dynamically
    update_fields = []
    params = {"store_id": str(store_id), "new_version": update_data.version + 1}
    
    # Alert type toggles
    if update_data.high_value_order:
        update_fields.extend([
            "high_value_order_enabled = :hvo_enabled",
            "high_value_order_frequency = :hvo_frequency",
            "high_value_order_channels = :hvo_channels"
        ])
        params["hvo_enabled"] = update_data.high_value_order.enabled
        params["hvo_frequency"] = update_data.high_value_order.frequency.value
        params["hvo_channels"] = update_data.high_value_order.channels
    
    if update_data.unusual_returns:
        update_fields.extend([
            "unusual_returns_enabled = :ur_enabled",
            "unusual_returns_frequency = :ur_frequency",
            "unusual_returns_channels = :ur_channels"
        ])
        params["ur_enabled"] = update_data.unusual_returns.enabled
        params["ur_frequency"] = update_data.unusual_returns.frequency.value
        params["ur_channels"] = update_data.unusual_returns.channels
    
    if update_data.inventory_depletion:
        update_fields.extend([
            "inventory_depletion_enabled = :id_enabled",
            "inventory_depletion_frequency = :id_frequency",
            "inventory_depletion_channels = :id_channels"
        ])
        params["id_enabled"] = update_data.inventory_depletion.enabled
        params["id_frequency"] = update_data.inventory_depletion.frequency.value
        params["id_channels"] = update_data.inventory_depletion.channels
    
    if update_data.conversion_anomaly:
        update_fields.extend([
            "conversion_anomaly_enabled = :ca_enabled",
            "conversion_anomaly_frequency = :ca_frequency",
            "conversion_anomaly_channels = :ca_channels"
        ])
        params["ca_enabled"] = update_data.conversion_anomaly.enabled
        params["ca_frequency"] = update_data.conversion_anomaly.frequency.value
        params["ca_channels"] = update_data.conversion_anomaly.channels
    
    if update_data.customer_segment:
        update_fields.extend([
            "customer_segment_enabled = :cs_enabled",
            "customer_segment_frequency = :cs_frequency",
            "customer_segment_channels = :cs_channels"
        ])
        params["cs_enabled"] = update_data.customer_segment.enabled
        params["cs_frequency"] = update_data.customer_segment.frequency.value
        params["cs_channels"] = update_data.customer_segment.channels
    
    # Thresholds
    if update_data.thresholds:
        threshold_fields = [
            ("high_value_aov_multiplier", "hvaovm"),
            ("high_value_min_order_value", "hvmov"),
            ("inventory_threshold_units", "itu"),
            ("inventory_threshold_percent", "itp"),
            ("inventory_velocity_preset", "ivp"),
            ("conversion_drop_threshold_percent", "cdtp"),
            ("conversion_rise_threshold_percent", "crtp"),
            ("conversion_baseline_days", "cbd"),
            ("conversion_sensitivity_preset", "csp"),
            ("returns_spike_multiplier", "rsm"),
            ("returns_spike_window_hours", "rswh"),
            ("returns_sensitivity_preset", "rsp"),
            ("vip_inactive_days", "vid"),
            ("returning_inactive_days", "rid"),
            ("customer_sensitivity_preset", "csep"),
        ]
        for field, param in threshold_fields:
            value = getattr(update_data.thresholds, field, None)
            if value is not None:
                update_fields.append(f"{field} = :{param}")
                params[param] = value.value if isinstance(value, Enum) else value
    
    # Frequency
    if update_data.frequency:
        freq_fields = [
            ("delivery_mode", "dm"),
            ("max_alerts_per_hour", "maph"),
            ("max_alerts_per_day", "mapd"),
            ("dedup_window_minutes", "dwm"),
            ("critical_delivery_mode", "cdm"),
            ("warning_delivery_mode", "wdm"),
            ("info_delivery_mode", "idm"),
        ]
        for field, param in freq_fields:
            value = getattr(update_data.frequency, field, None)
            if value is not None:
                update_fields.append(f"{field} = :{param}")
                params[param] = value.value if isinstance(value, Enum) else value
    
    # DND
    if update_data.do_not_disturb:
        dnd_fields = [
            ("dnd_enabled", "dnde"),
            ("dnd_start_time", "dndst"),
            ("dnd_end_time", "dndet"),
            ("dnd_timezone", "dndtz"),
            ("dnd_allow_critical", "dndac"),
        ]
        for field, param in dnd_fields:
            value = getattr(update_data.do_not_disturb, field, None)
            if value is not None:
                update_fields.append(f"{field} = :{param}")
                params[param] = value
    
    # Always update version and mark as customized
    update_fields.append("version = :new_version")
    update_fields.append("is_customized = TRUE")
    update_fields.append("last_modified_by = :user_id")
    params["user_id"] = current_user.user_id
    
    if not update_fields:
        return AlertRulesResponse(
            success=True,
            data=row_to_dto(row),
            warnings=[]
        )
    
    # Execute update
    query = f"""
        UPDATE public.alert_rules 
        SET {', '.join(update_fields)}
        WHERE store_id = :store_id AND deleted_at IS NULL AND version = :version
        RETURNING *
    """
    params["version"] = update_data.version
    
    result = await db.execute(text(query), params)
    updated_row = result.fetchone()
    
    if not updated_row:
        raise HTTPException(
            status_code=409,
            detail="Configuration was modified by another session. Please refresh and try again."
        )
    
    await db.commit()
    
    # Validate and return
    config = row_to_dto(updated_row)
    store_metrics = await get_store_metrics(db, store_id)
    warnings = validate_thresholds_against_benchmarks(config.thresholds, store_metrics)
    
    # Log the change to history
    await db.execute(
        text("""
            INSERT INTO public.alert_rules_history 
            (alert_rules_id, config_snapshot, changed_by, previous_version)
            SELECT id, :config_snapshot::jsonb, :user_id, :prev_version
            FROM public.alert_rules WHERE store_id = :store_id
        """),
        {
            "store_id": str(store_id),
            "config_snapshot": config.json(),
            "user_id": current_user.user_id,
            "prev_version": update_data.version
        }
    )
    await db.commit()
    
    return AlertRulesResponse(
        success=True,
        data=config,
        warnings=warnings
    )


@router.post("/{store_id}/reset", response_model=AlertRulesResponse)
async def reset_to_defaults(
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user)
):
    """Reset alert rules to recommended defaults."""
    # Verify user has access to this store
    user_store_id = await get_store_id_for_user(db, UUID(current_user.user_id))
    if not user_store_id or user_store_id != store_id:
        raise HTTPException(status_code=403, detail="Access denied to this store")
    
    # Reset to defaults
    result = await db.execute(
        text("""
            UPDATE public.alert_rules 
            SET 
                high_value_order_enabled = TRUE,
                high_value_order_frequency = 'real_time',
                high_value_order_channels = ARRAY['in_app', 'push'],
                unusual_returns_enabled = TRUE,
                unusual_returns_frequency = 'batched_30m',
                unusual_returns_channels = ARRAY['in_app', 'email'],
                inventory_depletion_enabled = TRUE,
                inventory_depletion_frequency = 'real_time',
                inventory_depletion_channels = ARRAY['in_app', 'email', 'push'],
                conversion_anomaly_enabled = TRUE,
                conversion_anomaly_frequency = 'batched_30m',
                conversion_anomaly_channels = ARRAY['in_app'],
                customer_segment_enabled = TRUE,
                customer_segment_frequency = 'batched_1h',
                customer_segment_channels = ARRAY['in_app', 'email'],
                high_value_aov_multiplier = 1.5,
                high_value_min_order_value = NULL,
                inventory_threshold_units = 10,
                inventory_threshold_percent = 20.0,
                inventory_velocity_preset = 'balanced',
                conversion_drop_threshold_percent = 15.0,
                conversion_rise_threshold_percent = 20.0,
                conversion_baseline_days = 7,
                conversion_sensitivity_preset = 'moderate',
                returns_spike_multiplier = 3.0,
                returns_spike_window_hours = 24,
                returns_sensitivity_preset = 'moderate',
                vip_inactive_days = 30,
                returning_inactive_days = 45,
                customer_sensitivity_preset = 'moderate',
                delivery_mode = 'real_time',
                max_alerts_per_hour = 10,
                max_alerts_per_day = 50,
                dedup_window_minutes = 60,
                critical_delivery_mode = 'real_time',
                warning_delivery_mode = 'batched',
                info_delivery_mode = 'batched',
                dnd_enabled = FALSE,
                dnd_start_time = NULL,
                dnd_end_time = NULL,
                dnd_timezone = 'UTC',
                dnd_allow_critical = TRUE,
                is_customized = FALSE,
                version = version + 1,
                last_modified_by = :user_id
            WHERE store_id = :store_id AND deleted_at IS NULL
            RETURNING *
        """),
        {"store_id": str(store_id), "user_id": current_user.user_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Alert configuration not found")
    
    await db.commit()
    
    return AlertRulesResponse(
        success=True,
        data=row_to_dto(row),
        warnings=[]
    )


@router.post("/{store_id}/apply-preset", response_model=AlertRulesResponse)
async def apply_sensitivity_preset(
    store_id: UUID,
    preset_data: PresetApplicationDTO,
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user)
):
    """
    Apply a sensitivity preset to threshold configuration.
    Presets: 'conservative', 'moderate', 'aggressive'
    """
    # Verify user has access to this store
    user_store_id = await get_store_id_for_user(db, UUID(current_user.user_id))
    if not user_store_id or user_store_id != store_id:
        raise HTTPException(status_code=403, detail="Access denied to this store")
    
    # Define presets
    presets = {
        "conservative": {
            "conversion_drop_threshold_percent": 20.0,
            "conversion_rise_threshold_percent": 30.0,
            "conversion_sensitivity_preset": "conservative",
            "returns_spike_multiplier": 2.0,
            "returns_sensitivity_preset": "conservative",
            "vip_inactive_days": 60,
            "returning_inactive_days": 90,
            "customer_sensitivity_preset": "conservative",
            "inventory_threshold_units": 15,
        },
        "moderate": {
            "conversion_drop_threshold_percent": 15.0,
            "conversion_rise_threshold_percent": 20.0,
            "conversion_sensitivity_preset": "moderate",
            "returns_spike_multiplier": 3.0,
            "returns_sensitivity_preset": "moderate",
            "vip_inactive_days": 30,
            "returning_inactive_days": 45,
            "customer_sensitivity_preset": "moderate",
            "inventory_threshold_units": 10,
        },
        "aggressive": {
            "conversion_drop_threshold_percent": 10.0,
            "conversion_rise_threshold_percent": 15.0,
            "conversion_sensitivity_preset": "aggressive",
            "returns_spike_multiplier": 5.0,
            "returns_sensitivity_preset": "aggressive",
            "vip_inactive_days": 21,
            "returning_inactive_days": 30,
            "customer_sensitivity_preset": "aggressive",
            "inventory_threshold_units": 5,
        }
    }
    
    if preset_data.preset_type not in presets:
        raise HTTPException(status_code=400, detail=f"Invalid preset type. Use: {list(presets.keys())}")
    
    preset_values = presets[preset_data.preset_type]
    
    # Filter to target fields if specified
    if preset_data.target_fields:
        preset_values = {k: v for k, v in preset_values.items() if k in preset_data.target_fields}
    
    # Build update
    set_clauses = [f"{k} = :{k}" for k in preset_values.keys()]
    set_clauses.extend(["version = version + 1", "is_customized = TRUE", "last_modified_by = :user_id"])
    
    params = {**preset_values, "store_id": str(store_id), "user_id": current_user.user_id}
    
    query = f"""
        UPDATE public.alert_rules 
        SET {', '.join(set_clauses)}
        WHERE store_id = :store_id AND deleted_at IS NULL
        RETURNING *
    """
    
    result = await db.execute(text(query), params)
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Alert configuration not found")
    
    await db.commit()
    
    config = row_to_dto(row)
    store_metrics = await get_store_metrics(db, store_id)
    warnings = validate_thresholds_against_benchmarks(config.thresholds, store_metrics)
    
    return AlertRulesResponse(
        success=True,
        data=config,
        warnings=warnings
    )


@router.get("/{store_id}/presets", response_model=Dict[str, Any])
async def get_available_presets(
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user)
):
    """Get available threshold presets with calculated values based on store metrics."""
    # Verify user has access
    user_store_id = await get_store_id_for_user(db, UUID(current_user.user_id))
    if not user_store_id or user_store_id != store_id:
        raise HTTPException(status_code=403, detail="Access denied to this store")
    
    store_metrics = await get_store_metrics(db, store_id)
    aov = store_metrics.avg_order_value or Decimal("150")
    
    return {
        "conservative": {
            "label": "Conservative",
            "description": "Fewer alerts, higher thresholds. Best for stable operations.",
            "values": {
                "high_value_aov_multiplier": 2.0,
                "high_value_preset_value": f"${(aov * Decimal('2.0')):.0f}",
                "conversion_drop_threshold_percent": 20.0,
                "returns_spike_multiplier": 2.0,
                "vip_inactive_days": 60,
                "returning_inactive_days": 90,
            }
        },
        "moderate": {
            "label": "Moderate (Recommended)",
            "description": "Balanced alert frequency. Industry standard for luxury retail.",
            "values": {
                "high_value_aov_multiplier": 1.5,
                "high_value_preset_value": f"${(aov * Decimal('1.5')):.0f}",
                "conversion_drop_threshold_percent": 15.0,
                "returns_spike_multiplier": 3.0,
                "vip_inactive_days": 30,
                "returning_inactive_days": 45,
            }
        },
        "aggressive": {
            "label": "Aggressive",
            "description": "More alerts, lower thresholds. Best for proactive monitoring.",
            "values": {
                "high_value_aov_multiplier": 1.3,
                "high_value_preset_value": f"${(aov * Decimal('1.3')):.0f}",
                "conversion_drop_threshold_percent": 10.0,
                "returns_spike_multiplier": 5.0,
                "vip_inactive_days": 21,
                "returning_inactive_days": 30,
            }
        }
    }


@router.get("/{store_id}/history", response_model=List[Dict[str, Any]])
async def get_configuration_history(
    store_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user)
):
    """Get configuration change history for audit purposes."""
    # Verify user has access
    user_store_id = await get_store_id_for_user(db, UUID(current_user.user_id))
    if not user_store_id or user_store_id != store_id:
        raise HTTPException(status_code=403, detail="Access denied to this store")
    
    result = await db.execute(
        text("""
            SELECT h.id, h.config_snapshot, h.change_description, 
                   h.changed_by, h.changed_at, h.previous_version
            FROM public.alert_rules_history h
            JOIN public.alert_rules ar ON ar.id = h.alert_rules_id
            WHERE ar.store_id = :store_id
            ORDER BY h.changed_at DESC
            LIMIT :limit
        """),
        {"store_id": str(store_id), "limit": limit}
    )
    
    return [
        {
            "id": str(row.id),
            "config_snapshot": row.config_snapshot,
            "change_description": row.change_description,
            "changed_by": str(row.changed_by) if row.changed_by else None,
            "changed_at": row.changed_at.isoformat(),
            "previous_version": row.previous_version
        }
        for row in result.fetchall()
    ]
