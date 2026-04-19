"""
CONFIT Backend — Profile Models
===============================
Multi-dimensional user identity system for Group 1.
"""

from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, JSON, Numeric, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship

from database.base import Base
from database.models import UUIDType, _new_uuid


# ── SQLAlchemy ORM Models ─────────────────────────────────────────────

class UserStyleProfile(Base):
    __tablename__ = "user_style_profiles"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Archetype
    primary_archetype = Column(String(50), nullable=True)
    secondary_archetypes = Column(JSON, default=list)
    archetype_confidence = Column(Numeric(3, 2), default=Decimal("0.0"))
    
    # Style Vector (8 dimensions)
    style_classic = Column(Numeric(3, 2), default=Decimal("0.5"))
    style_trendy = Column(Numeric(3, 2), default=Decimal("0.5"))
    style_minimalist = Column(Numeric(3, 2), default=Decimal("0.5"))
    style_maximalist = Column(Numeric(3, 2), default=Decimal("0.5"))
    style_feminine = Column(Numeric(3, 2), default=Decimal("0.5"))
    style_masculine = Column(Numeric(3, 2), default=Decimal("0.5"))
    style_edgy = Column(Numeric(3, 2), default=Decimal("0.5"))
    style_romantic = Column(Numeric(3, 2), default=Decimal("0.5"))
    
    # Color Affinity
    skin_undertone = Column(String(20), nullable=True)
    preferred_colors = Column(JSON, default=list)
    avoided_colors = Column(JSON, default=list)
    color_confidence = Column(Numeric(3, 2), default=Decimal("0.0"))
    
    # Pattern & Fabric
    pattern_preferences = Column(JSON, default=dict)
    fabric_preferences = Column(JSON, default=list)
    
    # Silhouette
    silhouette_preferences = Column(JSON, default=dict)
    fit_preference = Column(String(30), default="regular")
    
    # Status
    profile_completeness = Column(Numeric(5, 2), default=Decimal("0.0"))
    onboarding_completed = Column(Boolean, default=False)
    onboarding_phase = Column(Integer, default=0)
    profile_version = Column(Integer, default=1)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="style_profile_rel")


class UserBodyProfile(Base):
    __tablename__ = "user_body_profiles"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    profile_status = Column(String(20), default="not_set")
    
    # Measurements (cm)
    height_cm = Column(Integer, nullable=True)
    weight_kg = Column(Integer, nullable=True)
    chest_cm = Column(Integer, nullable=True)
    waist_cm = Column(Integer, nullable=True)
    hips_cm = Column(Integer, nullable=True)
    inseam_cm = Column(Integer, nullable=True)
    
    # Classification
    body_shape = Column(String(50), nullable=True)
    
    # Sizes
    size_tops = Column(String(10), nullable=True)
    size_bottoms = Column(String(10), nullable=True)
    size_dresses = Column(String(10), nullable=True)
    size_shoes = Column(String(10), nullable=True)
    brand_size_overrides = Column(JSON, default=dict)
    
    # Fit Issues
    fit_issues = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="body_profile_rel")


class UserBudgetProfile(Base):
    __tablename__ = "user_budget_profiles"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    per_item_min = Column(Numeric(10, 2), nullable=True)
    per_item_max = Column(Numeric(10, 2), nullable=True)
    monthly_max = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default="USD")
    investment_willing = Column(Boolean, default=False)
    price_sensitivity = Column(Numeric(3, 2), default=Decimal("0.5"))
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="budget_profile_rel")


class UserBrandAffinity(Base):
    __tablename__ = "user_brand_affinities"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    brand_id = Column(String(64), nullable=False, index=True)
    
    affinity_score = Column(Numeric(3, 2), default=Decimal("0.5"))
    affinity_source = Column(String(30), default="explicit")
    reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="brand_affinities_rel")
    
    __table_args__ = (UniqueConstraint("user_id", "brand_id", name="uq_user_brand"),)


class UserContextualPreference(Base):
    __tablename__ = "user_contextual_preferences"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Occasion Weights
    occasion_weights = Column(JSON, default=dict)
    
    # Lifestyle
    work_environment = Column(String(30), nullable=True)
    climate_zone = Column(String(30), nullable=True)
    activity_level = Column(String(20), nullable=True)
    has_children = Column(Boolean, nullable=True)
    pet_friendly = Column(Boolean, nullable=True)
    
    # Weather Preferences
    weather_preferences = Column(JSON, default=dict)
    
    # Cultural
    cultural_influences = Column(JSON, default=list)
    modesty_preference = Column(String(20), nullable=True)
    
    # Social
    style_icons = Column(JSON, default=list)
    social_influences = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="contextual_preferences_rel")


class UserConfidenceProfile(Base):
    __tablename__ = "user_confidence_profiles"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    overall_confidence = Column(Numeric(5, 2), default=Decimal("0.0"))
    
    # Dimensions (0-100)
    fit_confidence = Column(Numeric(5, 2), default=Decimal("0.0"))
    style_alignment = Column(Numeric(5, 2), default=Decimal("0.0"))
    budget_comfort = Column(Numeric(5, 2), default=Decimal("0.0"))
    experimentation_level = Column(Numeric(5, 2), default=Decimal("0.0"))
    wardrobe_compatibility = Column(Numeric(5, 2), default=Decimal("0.0"))
    occasion_readiness = Column(Numeric(5, 2), default=Decimal("0.0"))
    consistency_score = Column(Numeric(5, 2), default=Decimal("0.0"))
    engagement_score = Column(Numeric(5, 2), default=Decimal("0.0"))
    
    # Badges & Growth
    earned_badges = Column(JSON, default=list)
    growth_rate = Column(Numeric(5, 4), default=Decimal("0.0"))
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="confidence_profile_rel")


class UserConfidenceHistory(Base):
    __tablename__ = "user_confidence_history"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    overall_score = Column(Numeric(5, 2), nullable=False)
    dimensions = Column(JSON, nullable=False)
    delta = Column(Numeric(5, 2), nullable=True)
    trigger_event = Column(String(50), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="confidence_history_rel")


class UserBehaviorSignal(Base):
    __tablename__ = "user_behavior_signals"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    signal_type = Column(String(30), nullable=False, index=True)
    entity_type = Column(String(30), nullable=False)
    entity_id = Column(String(100), nullable=False, index=True)
    
    weight = Column(Numeric(4, 3), nullable=False)
    context = Column(JSON, default=dict)
    duration_ms = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="behavior_signals_rel")


class UserStyleEvolution(Base):
    __tablename__ = "user_style_evolution"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    event_type = Column(String(50), nullable=False)
    previous_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=False)
    trigger_source = Column(String(30), nullable=False)
    confidence_delta = Column(Numeric(5, 2), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="style_evolution_rel")


class UserConsentHistory(Base):
    __tablename__ = "user_consent_history"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    consent_type = Column(String(50), nullable=False)
    granted = Column(Boolean, nullable=False)
    consent_version = Column(Integer, nullable=False, default=1)
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="consent_history_rel")


class UserProfileAuditLog(Base):
    __tablename__ = "user_profile_audit_log"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    table_name = Column(String(50), nullable=False)
    field_name = Column(String(100), nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=False)
    change_source = Column(String(30), nullable=False)
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="profile_audit_log_rel")


class UserOnboardingSession(Base):
    __tablename__ = "user_onboarding_sessions"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    current_phase = Column(Integer, default=1)
    phase_data = Column(JSON, default=dict)
    quiz_answers = Column(JSON, default=dict)
    skipped_phases = Column(JSON, default=list)
    
    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="onboarding_session_rel")


class UserDataExportRequest(Base):
    __tablename__ = "user_data_export_requests"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    status = Column(String(20), default="pending")
    format = Column(String(10), default="json")
    
    requested_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    download_url = Column(Text, nullable=True)
    export_data = Column(JSON, nullable=True)
    
    error_message = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="data_export_requests_rel")


class UserDeletionRequest(Base):
    __tablename__ = "user_deletion_requests"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    status = Column(String(20), default="pending")
    reason = Column(Text, nullable=True)
    confirmation_code = Column(String(64), nullable=True)
    
    requested_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", backref="deletion_requests")


# ── Pydantic Schemas ──────────────────────────────────────────────────

class StyleDimensions(BaseModel):
    classic: float = Field(0.5, ge=0.0, le=1.0)
    trendy: float = Field(0.5, ge=0.0, le=1.0)
    minimalist: float = Field(0.5, ge=0.0, le=1.0)
    maximalist: float = Field(0.5, ge=0.0, le=1.0)
    feminine: float = Field(0.5, ge=0.0, le=1.0)
    masculine: float = Field(0.5, ge=0.0, le=1.0)
    edgy: float = Field(0.5, ge=0.0, le=1.0)
    romantic: float = Field(0.5, ge=0.0, le=1.0)


class StyleProfileCreate(BaseModel):
    primary_archetype: Optional[str] = None
    secondary_archetypes: List[str] = Field(default_factory=list)
    style_dimensions: Optional[StyleDimensions] = None
    skin_undertone: Optional[str] = None
    preferred_colors: List[str] = Field(default_factory=list)
    avoided_colors: List[str] = Field(default_factory=list)
    pattern_preferences: dict = Field(default_factory=dict)
    fabric_preferences: List[str] = Field(default_factory=list)
    silhouette_preferences: dict = Field(default_factory=dict)
    fit_preference: str = "regular"


class StyleProfileResponse(BaseModel):
    id: str
    user_id: str
    primary_archetype: Optional[str]
    secondary_archetypes: List[str]
    archetype_confidence: float
    style_dimensions: StyleDimensions
    skin_undertone: Optional[str]
    preferred_colors: List[str]
    avoided_colors: List[str]
    color_confidence: float
    pattern_preferences: dict
    fabric_preferences: List[str]
    silhouette_preferences: dict
    fit_preference: str
    profile_completeness: float
    onboarding_completed: bool
    onboarding_phase: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class BodyProfileCreate(BaseModel):
    height_cm: Optional[int] = Field(None, ge=100, le=250)
    weight_kg: Optional[int] = Field(None, ge=30, le=300)
    chest_cm: Optional[int] = Field(None, ge=50, le=200)
    waist_cm: Optional[int] = Field(None, ge=40, le=200)
    hips_cm: Optional[int] = Field(None, ge=50, le=200)
    inseam_cm: Optional[int] = Field(None, ge=50, le=120)
    body_shape: Optional[str] = None
    size_tops: Optional[str] = None
    size_bottoms: Optional[str] = None
    size_dresses: Optional[str] = None
    size_shoes: Optional[str] = None
    brand_size_overrides: dict = Field(default_factory=dict)
    fit_issues: List[str] = Field(default_factory=list)


class BodyProfileResponse(BaseModel):
    id: str
    user_id: str
    profile_status: str
    height_cm: Optional[int]
    weight_kg: Optional[int]
    chest_cm: Optional[int]
    waist_cm: Optional[int]
    hips_cm: Optional[int]
    inseam_cm: Optional[int]
    body_shape: Optional[str]
    size_tops: Optional[str]
    size_bottoms: Optional[str]
    size_dresses: Optional[str]
    size_shoes: Optional[str]
    brand_size_overrides: dict
    fit_issues: List[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class BudgetProfileCreate(BaseModel):
    per_item_min: Optional[float] = Field(None, ge=0)
    per_item_max: Optional[float] = Field(None, ge=0)
    monthly_max: Optional[float] = Field(None, ge=0)
    currency: str = "USD"
    investment_willing: bool = False
    price_sensitivity: float = Field(0.5, ge=0.0, le=1.0)


class BudgetProfileResponse(BaseModel):
    id: str
    user_id: str
    per_item_min: Optional[float]
    per_item_max: Optional[float]
    monthly_max: Optional[float]
    currency: str
    investment_willing: bool
    price_sensitivity: float
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class BrandAffinityCreate(BaseModel):
    brand_id: str
    affinity_score: float = Field(0.5, ge=0.0, le=1.0)
    reason: Optional[str] = None


class BrandAffinityResponse(BaseModel):
    id: str
    user_id: str
    brand_id: str
    affinity_score: float
    affinity_source: str
    reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ContextualPreferenceCreate(BaseModel):
    occasion_weights: dict = Field(default_factory=dict)
    work_environment: Optional[str] = None
    climate_zone: Optional[str] = None
    activity_level: Optional[str] = None
    has_children: Optional[bool] = None
    pet_friendly: Optional[bool] = None
    weather_preferences: dict = Field(default_factory=dict)
    cultural_influences: List[str] = Field(default_factory=list)
    modesty_preference: Optional[str] = None
    style_icons: List[str] = Field(default_factory=list)
    social_influences: List[str] = Field(default_factory=list)


class ContextualPreferenceResponse(BaseModel):
    id: str
    user_id: str
    occasion_weights: dict
    work_environment: Optional[str]
    climate_zone: Optional[str]
    activity_level: Optional[str]
    has_children: Optional[bool]
    pet_friendly: Optional[bool]
    weather_preferences: dict
    cultural_influences: List[str]
    modesty_preference: Optional[str]
    style_icons: List[str]
    social_influences: List[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ConfidenceDimensions(BaseModel):
    fit_confidence: float = 0.0
    style_alignment: float = 0.0
    budget_comfort: float = 0.0
    experimentation_level: float = 0.0
    wardrobe_compatibility: float = 0.0
    occasion_readiness: float = 0.0
    consistency_score: float = 0.0
    engagement_score: float = 0.0


class ConfidenceProfileResponse(BaseModel):
    id: str
    user_id: str
    overall_confidence: float
    dimensions: ConfidenceDimensions
    earned_badges: List[str]
    growth_rate: float
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class BehaviorSignalCreate(BaseModel):
    signal_type: str
    entity_type: str
    entity_id: str
    context: dict = Field(default_factory=dict)
    duration_ms: Optional[int] = None


class BehaviorSignalResponse(BaseModel):
    id: str
    user_id: str
    signal_type: str
    entity_type: str
    entity_id: str
    weight: float
    context: dict
    duration_ms: Optional[int]
    created_at: datetime
    expires_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


class ConsentUpdate(BaseModel):
    consent_type: str
    granted: bool


class ConsentHistoryResponse(BaseModel):
    id: str
    user_id: str
    consent_type: str
    granted: bool
    consent_version: int
    created_at: datetime
    
    model_config = {"from_attributes": True}


class OnboardingPhaseData(BaseModel):
    phase: int = Field(..., ge=1, le=5)
    data: dict = Field(default_factory=dict)


class StyleQuizAnswer(BaseModel):
    question_id: str
    selected_options: List[str] = Field(default_factory=list)
    image_selections: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None


class StyleQuizSubmission(BaseModel):
    answers: List[StyleQuizAnswer]
    skipped: bool = False


class OnboardingStatusResponse(BaseModel):
    user_id: str
    current_phase: int
    total_phases: int
    completed: bool
    skipped_phases: List[int]
    started_at: datetime
    completed_at: Optional[datetime]
    profile_completeness: float


class DataExportRequest(BaseModel):
    format: str = "json"


class DataExportResponse(BaseModel):
    id: str
    user_id: str
    status: str
    format: str
    requested_at: datetime
    completed_at: Optional[datetime]
    download_url: Optional[str]
    expires_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


class DeletionRequest(BaseModel):
    reason: Optional[str] = None


class DeletionConfirm(BaseModel):
    confirmation_code: str


class ProfileCompletenessResponse(BaseModel):
    overall_score: float
    sections: dict
    missing_fields: List[str]
    suggestions: List[str]


class StyleArchetypeResult(BaseModel):
    primary: str
    secondary: List[str]
    confidence: float
    dimensions: StyleDimensions
