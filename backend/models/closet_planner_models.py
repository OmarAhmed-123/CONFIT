"""
CONFIT Backend — Smart Closet Planner Models
============================================
Weekly outfit planning with weather and calendar integration.
"""

from datetime import date, datetime, time, timezone
import os
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, JSON,
    Numeric, ForeignKey, Index, UniqueConstraint, SmallInteger, Date, Time
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship

from database.base import Base
from database.models import UUIDType, _new_uuid

_DB_URL = os.getenv("DATABASE_URL", "sqlite:///./confit.db")
if not _DB_URL.startswith("postgresql"):
    JSONB = JSON  # type: ignore[assignment]


# ── Enums ─────────────────────────────────────────────────────────────

class OutfitStatus(str, Enum):
    PLANNED = "planned"
    WORN = "worn"
    SKIPPED = "skipped"
    MODIFIED = "modified"


class DeviationType(str, Enum):
    NONE = "none"
    MINOR = "minor"
    MAJOR = "major"
    COMPLETELY_DIFFERENT = "completely_different"


class CalendarProvider(str, Enum):
    GOOGLE = "google"
    APPLE = "apple"
    OUTLOOK = "outlook"
    MANUAL = "manual"


class TemperatureUnit(str, Enum):
    CELSIUS = "celsius"
    FAHRENHEIT = "fahrenheit"


class WeatherCondition(str, Enum):
    CLEAR = "clear"
    SUNNY = "sunny"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    LIGHT_RAIN = "light_rain"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    THUNDERSTORM = "thunderstorm"
    LIGHT_SNOW = "light_snow"
    SNOW = "snow"
    HEAVY_SNOW = "heavy_snow"
    FOG = "fog"
    WINDY = "windy"


class EventType(str, Enum):
    MEETING = "meeting"
    WORK = "work"
    PARTY = "party"
    DINNER = "dinner"
    DATE = "date"
    CASUAL = "casual"
    FORMAL = "formal"
    ATHLETIC = "athletic"
    TRAVEL = "travel"
    SPECIAL_EVENT = "special_event"
    OTHER = "other"


# ── SQLAlchemy ORM Models ─────────────────────────────────────────────

class ClosetPlan(Base):
    """Weekly outfit plan for a user."""
    __tablename__ = "closet_plans"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    # Plan period
    week_start_date = Column(Date, nullable=False)
    week_end_date = Column(Date, nullable=False)
    
    # Plan metadata
    plan_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_template = Column(Boolean, nullable=False, default=False)
    
    # Generation context
    generation_context = Column(JSONB, nullable=False, default=dict)
    
    # Statistics
    total_outfits = Column(Integer, nullable=False, default=0)
    days_planned = Column(Integer, nullable=False, default=0)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    daily_outfits = relationship("DailyOutfit", back_populates="plan", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint("user_id", "week_start_date", name="uq_user_week"),
    )


class DailyOutfit(Base):
    """Individual day outfit assignment within a plan."""
    __tablename__ = "daily_outfits"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    plan_id = Column(UUIDType, ForeignKey("closet_plans.id"), nullable=False, index=True)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    # Day information
    plan_date = Column(Date, nullable=False)
    day_of_week = Column(SmallInteger, nullable=False)  # 0-6
    
    # Outfit details
    # Use String(64) to align with Outfit.id and existing migrations
    outfit_id = Column(String(64), ForeignKey("outfits.id"), nullable=True)
    outfit_data = Column(JSONB, nullable=False, default=dict)
    
    # Weather context
    weather_data = Column(JSONB, nullable=True, default=dict)
    
    # Calendar context
    calendar_events = Column(JSONB, nullable=True, default=list)
    
    # Occasion
    primary_occasion = Column(String(100), nullable=True)
    occasion_confidence = Column(Numeric(3, 2), default=Decimal("0.0"))
    
    # Alternatives
    alternative_outfits = Column(JSONB, nullable=True, default=list)
    
    # Status
    status = Column(String(32), nullable=False, default=OutfitStatus.PLANNED.value)
    worn_at = Column(DateTime(timezone=True), nullable=True)
    
    # User feedback
    user_rating = Column(SmallInteger, nullable=True)
    user_notes = Column(Text, nullable=True)
    
    # Style matching scores
    style_match_score = Column(Numeric(3, 2), nullable=True)
    weather_match_score = Column(Numeric(3, 2), nullable=True)
    occasion_match_score = Column(Numeric(3, 2), nullable=True)
    overall_score = Column(Numeric(3, 2), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    plan = relationship("ClosetPlan", back_populates="daily_outfits")
    
    __table_args__ = (
        UniqueConstraint("plan_id", "plan_date", name="uq_plan_date"),
    )


class OutfitHistory(Base):
    """History of what was actually worn vs planned."""
    __tablename__ = "closet_outfit_history"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    # Reference
    daily_outfit_id = Column(UUIDType, ForeignKey("daily_outfits.id"), nullable=True)
    plan_id = Column(UUIDType, ForeignKey("closet_plans.id"), nullable=True)
    
    # What was worn
    worn_date = Column(Date, nullable=False, index=True)
    planned_outfit = Column(JSONB, nullable=True)
    actual_outfit = Column(JSONB, nullable=True)
    
    # Deviation tracking
    deviation_type = Column(String(32), nullable=True)
    deviation_reason = Column(Text, nullable=True)
    
    # Context
    weather_actual = Column(JSONB, nullable=True)
    events_actual = Column(JSONB, nullable=True, default=list)
    
    # Feedback
    satisfaction_score = Column(SmallInteger, nullable=True)
    would_wear_again = Column(Boolean, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class WeatherCache(Base):
    """Cached weather forecasts to reduce API calls."""
    __tablename__ = "weather_cache"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    location_key = Column(String(255), nullable=False, index=True)
    forecast_date = Column(Date, nullable=False, index=True)
    
    # Weather data
    weather_data = Column(JSONB, nullable=False)
    
    # Metadata
    source = Column(String(50), nullable=False, default="openweathermap")
    fetched_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    __table_args__ = (
        UniqueConstraint("location_key", "forecast_date", name="uq_location_date"),
    )


class CalendarEventsCache(Base):
    """Cached calendar events from external providers."""
    __tablename__ = "calendar_events_cache"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    # Event details
    external_id = Column(String(255), nullable=False)
    provider = Column(String(32), nullable=False)
    
    # Event data
    event_title = Column(String(500), nullable=False)
    event_date = Column(Date, nullable=False, index=True)
    event_time = Column(Time, nullable=True)
    event_end_time = Column(Time, nullable=True)
    location = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    
    # Planning context
    dress_code = Column(String(100), nullable=True)
    event_type = Column(String(50), nullable=True)
    importance = Column(SmallInteger, nullable=True, default=5)
    
    # Metadata
    raw_event_data = Column(JSONB, nullable=True)
    synced_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        UniqueConstraint("user_id", "external_id", "event_date", name="uq_user_event"),
    )


class PlannerPreferences(Base):
    """User preferences for outfit planning behavior."""
    __tablename__ = "planner_preferences"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Planning behavior
    planning_day = Column(SmallInteger, nullable=True, default=0)  # 0 = Sunday
    planning_time = Column(Time, nullable=True, default=time(20, 0))
    auto_generate = Column(Boolean, nullable=True, default=True)
    
    # Weather preferences
    location = Column(JSONB, nullable=True, default=dict)
    temperature_unit = Column(String(20), nullable=True, default="celsius")
    weather_sensitivity = Column(JSONB, nullable=True, default=dict)
    
    # Calendar integration
    calendar_providers = Column(JSONB, nullable=True, default=list)
    default_event_occasion_map = Column(JSONB, nullable=True, default=dict)
    
    # Style preferences for planning
    prefer_favorite_items = Column(Boolean, nullable=True, default=True)
    avoid_recently_worn = Column(Boolean, nullable=True, default=True)
    recently_worn_days = Column(SmallInteger, nullable=True, default=7)
    max_item_frequency = Column(SmallInteger, nullable=True, default=2)
    
    # Occasion priorities
    occasion_priorities = Column(JSONB, nullable=True, default=dict)
    
    # Notifications
    notify_new_plan = Column(Boolean, nullable=True, default=True)
    notify_daily = Column(Boolean, nullable=True, default=True)
    notify_daily_time = Column(Time, nullable=True, default=time(7, 0))
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


# ── Pydantic DTOs ─────────────────────────────────────────────────────

class OutfitItemDTO(BaseModel):
    """Single item within an outfit."""
    id: str
    name: str
    category: str
    color: Optional[str] = None
    image_url: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[float] = None


class WeatherDataDTO(BaseModel):
    """Weather data for a day."""
    temp_high: float
    temp_low: float
    condition: str
    precipitation: float = 0.0
    humidity: float = 0.0
    wind_speed: float = 0.0
    uv_index: Optional[float] = None
    feels_like: Optional[float] = None
    icon: Optional[str] = None


class CalendarEventDTO(BaseModel):
    """Calendar event for planning context."""
    id: str
    title: str
    time: Optional[str] = None
    end_time: Optional[str] = None
    type: Optional[str] = None
    location: Optional[str] = None
    dress_code: Optional[str] = None
    importance: int = 5


class AlternativeOutfitDTO(BaseModel):
    """Alternative outfit suggestion."""
    outfit_data: Dict[str, Any]
    reason: Optional[str] = None
    score: Optional[float] = None


class DailyOutfitDTO(BaseModel):
    """Daily outfit assignment."""
    id: str
    plan_id: str
    plan_date: date
    day_of_week: int
    day_name: str
    
    outfit: Dict[str, Any]
    items: List[OutfitItemDTO] = []
    
    weather: Optional[WeatherDataDTO] = None
    events: List[CalendarEventDTO] = []
    
    primary_occasion: Optional[str] = None
    occasion_confidence: float = 0.0
    
    alternatives: List[AlternativeOutfitDTO] = []
    
    status: str = OutfitStatus.PLANNED.value
    worn_at: Optional[datetime] = None
    
    user_rating: Optional[int] = None
    user_notes: Optional[str] = None
    
    style_match_score: Optional[float] = None
    weather_match_score: Optional[float] = None
    occasion_match_score: Optional[float] = None
    overall_score: Optional[float] = None
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ClosetPlanDTO(BaseModel):
    """Weekly closet plan."""
    id: str
    user_id: str
    week_start_date: date
    week_end_date: date
    plan_name: Optional[str] = None
    is_active: bool = True
    is_template: bool = False
    
    generation_context: Dict[str, Any] = {}
    
    total_outfits: int = 0
    days_planned: int = 0
    
    daily_outfits: List[DailyOutfitDTO] = []
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ClosetPlanCreateDTO(BaseModel):
    """Request to create a new closet plan."""
    week_start_date: Optional[date] = None  # Defaults to next week
    plan_name: Optional[str] = None
    force_regenerate: bool = False


class DailyOutfitUpdateDTO(BaseModel):
    """Request to update a daily outfit."""
    outfit_data: Optional[Dict[str, Any]] = None
    status: Optional[OutfitStatus] = None
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    user_notes: Optional[str] = None
    primary_occasion: Optional[str] = None


class OutfitSwapDTO(BaseModel):
    """Request to swap outfit between days."""
    source_date: date
    target_date: date


class PlannerPreferencesDTO(BaseModel):
    """Planner preferences."""
    planning_day: int = 0
    planning_time: str = "20:00"
    auto_generate: bool = True
    
    location: Dict[str, Any] = {}
    temperature_unit: str = "celsius"
    weather_sensitivity: Dict[str, Any] = {}
    
    calendar_providers: List[str] = []
    
    prefer_favorite_items: bool = True
    avoid_recently_worn: bool = True
    recently_worn_days: int = 7
    max_item_frequency: int = 2
    
    occasion_priorities: Dict[str, int] = {}
    
    notify_new_plan: bool = True
    notify_daily: bool = True
    notify_daily_time: str = "07:00"
    
    model_config = {"from_attributes": True}


class PlannerPreferencesUpdateDTO(BaseModel):
    """Request to update planner preferences."""
    planning_day: Optional[int] = None
    planning_time: Optional[str] = None
    auto_generate: Optional[bool] = None
    
    location: Optional[Dict[str, Any]] = None
    temperature_unit: Optional[str] = None
    weather_sensitivity: Optional[Dict[str, Any]] = None
    
    calendar_providers: Optional[List[str]] = None
    
    prefer_favorite_items: Optional[bool] = None
    avoid_recently_worn: Optional[bool] = None
    recently_worn_days: Optional[int] = None
    max_item_frequency: Optional[int] = None
    
    occasion_priorities: Optional[Dict[str, int]] = None
    
    notify_new_plan: Optional[bool] = None
    notify_daily: Optional[bool] = None
    notify_daily_time: Optional[str] = None


class OutfitSuggestionRequestDTO(BaseModel):
    """Request for outfit suggestions for a specific day."""
    date: date
    occasion: Optional[str] = None
    weather_override: Optional[WeatherDataDTO] = None
    events_override: List[CalendarEventDTO] = []
    excluded_item_ids: List[str] = []
    preferred_item_ids: List[str] = []


class OutfitSuggestionDTO(BaseModel):
    """Generated outfit suggestion."""
    outfit_data: Dict[str, Any]
    items: List[OutfitItemDTO]
    occasion: str
    confidence: float
    style_match_score: float
    weather_match_score: float
    occasion_match_score: float
    overall_score: float
    reasoning: Optional[str] = None


class WeeklyPlanSummaryDTO(BaseModel):
    """Summary of a weekly plan."""
    plan_id: str
    week_start: date
    week_end: date
    total_days: int
    days_planned: int
    days_worn: int
    days_skipped: int
    average_rating: Optional[float] = None
    top_occasions: List[Dict[str, Any]] = []
    weather_summary: Dict[str, Any] = {}
    style_diversity_score: float = 0.0


class OutfitHistoryDTO(BaseModel):
    """Outfit history entry."""
    id: str
    user_id: str
    worn_date: date
    planned_outfit: Optional[Dict[str, Any]] = None
    actual_outfit: Optional[Dict[str, Any]] = None
    deviation_type: Optional[str] = None
    deviation_reason: Optional[str] = None
    satisfaction_score: Optional[int] = None
    would_wear_again: Optional[bool] = None
    notes: Optional[str] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class CalendarSyncRequestDTO(BaseModel):
    """Request to sync calendar events."""
    provider: CalendarProvider
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    force_refresh: bool = False


class WeatherForecastDTO(BaseModel):
    """Weather forecast for planning."""
    location: str
    forecasts: List[Dict[str, Any]]  # List of daily forecasts
    fetched_at: datetime
    source: str
