"""
CONFIT Backend — Style DNA Models
=================================
Unique style fingerprint system using embeddings.
"""

from datetime import datetime, timezone
import os
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, JSON,
    Numeric, ForeignKey, Index, UniqueConstraint, ARRAY, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship

from database.base import Base
from database.models import UUIDType, _new_uuid

_DB_URL = os.getenv("DATABASE_URL", "sqlite:///./confit.db")
_IS_POSTGRES = _DB_URL.startswith("postgresql")
if not _DB_URL.startswith("postgresql"):
    JSONB = JSON  # type: ignore[assignment]


def enum_array_column(enum_cls):
    if _IS_POSTGRES:
        return ARRAY(SQLEnum(enum_cls))
    return JSON

try:
    from pgvector.sqlalchemy import Vector as PGVector
except Exception:
    PGVector = None


def vector_column(dimensions: int):
    """
    Use pgvector in PostgreSQL when available.
    Fallback to JSON for local/dev environments.
    """
    if PGVector is not None:
        return PGVector(dimensions)
    return JSON


# ── Enums ─────────────────────────────────────────────────────────────

class StyleCategory(str, Enum):
    CLASSIC = "classic"
    TRENDY = "trendy"
    MINIMALIST = "minimalist"
    MAXIMALIST = "maximalist"
    FEMININE = "feminine"
    MASCULINE = "masculine"
    EDGY = "edgy"
    ROMANTIC = "romantic"
    BOHEMIAN = "bohemian"
    PREPPY = "preppy"
    SPORTY = "sporty"
    AVANT_GARDE = "avant_garde"
    STREETWEAR = "streetwear"
    VINTAGE = "vintage"
    LUXURY = "luxury"
    CASUAL = "casual"


class BudgetLevel(str, Enum):
    BUDGET_CONSCIOUS = "budget_conscious"
    MODERATE = "moderate"
    PREMIUM = "premium"
    LUXURY = "luxury"
    ULTRA_LUXURY = "ultra_luxury"


class FitPreference(str, Enum):
    TIGHT = "tight"
    SLIM = "slim"
    REGULAR = "regular"
    RELAXED = "relaxed"
    OVERSIZED = "oversized"
    LOOSE = "loose"


class OccasionType(str, Enum):
    EVERYDAY = "everyday"
    WORK = "work"
    FORMAL = "formal"
    CASUAL = "casual"
    DATE_NIGHT = "date_night"
    WEEKEND = "weekend"
    VACATION = "vacation"
    PARTY = "party"
    ATHLETIC = "athletic"
    SPECIAL_EVENT = "special_event"


class StyleSignalSource(str, Enum):
    WARDROBE = "wardrobe"
    LIKED_OUTFITS = "liked_outfits"
    PURCHASE_HISTORY = "purchase_history"
    STYLE_QUIZ = "style_quiz"
    BROWSING_BEHAVIOR = "browsing_behavior"
    EXPLICIT_PREFERENCE = "explicit_preference"
    INFERRED = "inferred"


# ── SQLAlchemy ORM Models ─────────────────────────────────────────────

class StyleDNAProfile(Base):
    """Main style DNA profile for each user."""
    __tablename__ = "style_dna_profiles"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Primary style archetype
    primary_style = Column(SQLEnum(StyleCategory), nullable=True)
    secondary_styles = Column(enum_array_column(StyleCategory), default=[])
    style_confidence = Column(Numeric(5, 4), default=Decimal("0.0"))
    
    # Style vector (384 dimensions for sentence-transformers)
    style_vector = Column(vector_column(384), nullable=True)
    
    # Color preferences
    color_preferences = Column(JSONB, default=lambda: {
        "primary": [], "secondary": [], "avoided": [],
        "undertone": None, "palette_type": None
    })
    
    # Fit preferences
    fit_preference = Column(SQLEnum(FitPreference), default=FitPreference.REGULAR)
    fit_preferences = Column(JSONB, default=lambda: {
        "tops": "regular", "bottoms": "regular",
        "dresses": "regular", "outerwear": "regular"
    })
    
    # Occasion preferences
    occasion_preferences = Column(JSONB, default=lambda: {
        "everyday": 0.5, "work": 0.5, "formal": 0.3, "casual": 0.7,
        "date_night": 0.4, "weekend": 0.6, "vacation": 0.5,
        "party": 0.4, "athletic": 0.3, "special_event": 0.2
    })
    
    # Brand affinity
    brand_affinity = Column(JSONB, default=[])
    
    # Budget profile
    budget_level = Column(SQLEnum(BudgetLevel), default=BudgetLevel.MODERATE)
    budget_range = Column(JSONB, default=lambda: {
        "per_item_min": None, "per_item_max": None,
        "monthly_max": None, "currency": "USD"
    })
    
    # Pattern preferences
    pattern_preferences = Column(JSONB, default=lambda: {
        "preferred": [], "avoided": [], "neutral": []
    })
    
    # Fabric preferences
    fabric_preferences = Column(JSONB, default=lambda: {
        "preferred": [], "avoided": [], "seasonal": {}
    })
    
    # Silhouette preferences
    silhouette_preferences = Column(JSONB, default=lambda: {
        "tops": [], "bottoms": [], "dresses": []
    })
    
    # Signal summary
    signal_summary = Column(JSONB, default=lambda: {
        "wardrobe_items": 0, "liked_outfits": 0, "purchases": 0,
        "quiz_answers": 0, "browsing_events": 0, "last_analyzed": None
    })
    
    # Profile metadata
    profile_completeness = Column(Numeric(5, 2), default=Decimal("0.0"))
    profile_version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    
    # Encrypted sensitive data
    encrypted_preferences = Column(Text, nullable=True)

    # Interpretable identity vector (never expose raw style_vector / embeddings to clients)
    identity_dna = Column(
        JSONB,
        nullable=True,
        default=lambda: {
            "elegance_score": 0.5,
            "minimalism_score": 0.5,
            "boldness_score": 0.5,
            "color_affinity": {"warm": 0.33, "cool": 0.33, "neutral": 0.34},
            "fit_preference": "regular",
            "budget_behavior": {"research_weight": 0.5, "splurge_tendency": 0.5},
            "seasonal_patterns": {"spring": 0.25, "summer": 0.25, "fall": 0.25, "winter": 0.25},
        },
    )
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="style_dna")


class InteractionLog(Base):
    """Implicit and explicit behavioral signals (encrypted payload optional)."""
    __tablename__ = "interaction_logs"

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)

    event_type = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(64), nullable=True)
    entity_id = Column(String(128), nullable=True, index=True)

    metrics = Column(JSONB, nullable=False, default=dict)
    payload_encrypted = Column(Text, nullable=True)

    interest_delta = Column(Numeric(5, 4), default=Decimal("0"))
    session_id = Column(String(64), nullable=True, index=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", backref="fashion_interaction_logs")

    __table_args__ = (
        Index("ix_interaction_logs_user_created", "user_id", "created_at"),
    )


class RecommendationScore(Base):
    """Cached ranking scores for products/outfits (fast path under 500ms)."""
    __tablename__ = "recommendation_scores"

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)

    entity_type = Column(String(32), nullable=False, index=True)
    entity_id = Column(String(128), nullable=False, index=True)

    score = Column(Numeric(5, 4), nullable=False)
    score_breakdown = Column(JSONB, nullable=False, default=dict)

    computed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="recommendation_scores_list")

    __table_args__ = (
        UniqueConstraint("user_id", "entity_type", "entity_id", name="uq_reco_score_entity"),
        Index("ix_reco_scores_user_score", "user_id", "score"),
    )


class StyleVector(Base):
    """Historical style vectors for evolution tracking."""
    __tablename__ = "style_vectors"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    vector = Column(vector_column(384), nullable=False)
    vector_type = Column(String(50), nullable=False, default="full_profile")
    
    source_weights = Column(JSONB, default=lambda: {
        "wardrobe": 0.3, "liked_outfits": 0.25, "purchases": 0.2,
        "style_quiz": 0.15, "browsing": 0.1
    })
    
    confidence_score = Column(Numeric(5, 4), default=Decimal("0.0"))
    data_quality_score = Column(Numeric(5, 4), default=Decimal("0.0"))
    
    snapshot_reason = Column(String(50), default="periodic")
    is_baseline = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="style_vectors_history")


class StylePreference(Base):
    """Detailed preference signals."""
    __tablename__ = "style_preferences"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    preference_type = Column(String(50), nullable=False)
    preference_key = Column(String(100), nullable=False)
    preference_value = Column(JSONB, nullable=False)
    
    weight = Column(Numeric(4, 3), default=Decimal("0.5"))
    confidence = Column(Numeric(4, 3), default=Decimal("0.5"))
    
    source = Column(SQLEnum(StyleSignalSource), nullable=False)
    source_metadata = Column(JSONB, default={})
    
    decay_rate = Column(Numeric(4, 4), default=Decimal("0.0"))
    effective_weight = Column(Numeric(4, 3), default=Decimal("0.5"))
    
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="style_preferences_list")
    
    __table_args__ = (
        UniqueConstraint("user_id", "preference_type", "preference_key", name="uq_user_preference"),
    )


class StyleSignal(Base):
    """Raw behavioral signals for analysis."""
    __tablename__ = "style_signals"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    signal_type = Column(String(50), nullable=False, index=True)
    signal_category = Column(String(50), nullable=False)
    
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(100), nullable=True, index=True)
    
    signal_data = Column(JSONB, nullable=False, default={})
    
    base_weight = Column(Numeric(4, 3), default=Decimal("0.5"))
    computed_weight = Column(Numeric(4, 3), default=Decimal("0.5"))
    
    context = Column(JSONB, default={})
    session_id = Column(UUIDType, nullable=True)
    
    is_processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    decay_factor = Column(Numeric(4, 4), default=Decimal("1.0"))
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", backref="style_signals_list")


class StyleEvolutionHistory(Base):
    """Style evolution tracking."""
    __tablename__ = "style_evolution_history"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    change_type = Column(String(50), nullable=False)
    previous_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=False)
    
    vector_delta = Column(vector_column(384), nullable=True)
    drift_magnitude = Column(Numeric(5, 4), nullable=True)
    
    trigger_source = Column(String(50), nullable=False)
    trigger_event_id = Column(UUIDType, nullable=True)
    
    confidence_delta = Column(Numeric(5, 4), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="style_evolution")


class StyleCluster(Base):
    """User clustering for recommendations."""
    __tablename__ = "style_clusters"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    
    cluster_name = Column(String(100), nullable=False)
    cluster_description = Column(Text, nullable=True)
    
    centroid_vector = Column(vector_column(384), nullable=False)
    
    cluster_size = Column(Integer, default=0)
    dominant_styles = Column(enum_array_column(StyleCategory), default=[])
    dominant_colors = Column(JSONB, default=[])
    avg_budget_level = Column(SQLEnum(BudgetLevel), nullable=True)
    
    cohesion_score = Column(Numeric(5, 4), nullable=True)
    silhouette_score = Column(Numeric(5, 4), nullable=True)
    
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class UserClusterAssignment(Base):
    """User-to-cluster assignments."""
    __tablename__ = "user_cluster_assignments"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    cluster_id = Column(UUIDType, ForeignKey("style_clusters.id"), nullable=False)
    
    distance_to_centroid = Column(Numeric(5, 4), nullable=False)
    assignment_confidence = Column(Numeric(5, 4), default=Decimal("0.0"))
    
    secondary_clusters = Column(JSONB, default=[])
    
    valid_from = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    valid_until = Column(DateTime(timezone=True), nullable=True)
    is_current = Column(Boolean, default=True, index=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="cluster_assignments")
    cluster = relationship("StyleCluster", backref="user_assignments")


class StyleSimilarityCache(Base):
    """Cached style similarity between users."""
    __tablename__ = "style_similarity_cache"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id_1 = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    user_id_2 = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    cosine_similarity = Column(Numeric(5, 4), nullable=False)
    style_overlap_score = Column(Numeric(5, 4), nullable=True)
    color_harmony_score = Column(Numeric(5, 4), nullable=True)
    brand_affinity_score = Column(Numeric(5, 4), nullable=True)
    
    overall_similarity = Column(Numeric(5, 4), nullable=False, index=True)
    
    shared_styles = Column(enum_array_column(StyleCategory), default=[])
    shared_brands = Column(JSONB, default=[])
    shared_colors = Column(JSONB, default=[])
    
    computed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    __table_args__ = (
        UniqueConstraint("user_id_1", "user_id_2", name="uq_user_pair"),
    )


class StyleQuizResponse(Base):
    """Style quiz responses."""
    __tablename__ = "style_quiz_responses"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    quiz_type = Column(String(50), nullable=False, default="initial")
    quiz_version = Column(Integer, default=1)
    
    responses = Column(JSONB, nullable=False, default=[])
    
    computed_styles = Column(JSONB, default={})
    computed_colors = Column(JSONB, default={})
    computed_fit = Column(JSONB, default={})
    
    response_confidence = Column(Numeric(5, 4), default=Decimal("0.0"))
    
    duration_seconds = Column(Integer, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="quiz_responses")
    
    __table_args__ = (
        UniqueConstraint("user_id", "quiz_type", name="uq_user_quiz_type"),
    )


# ── Pydantic DTOs ─────────────────────────────────────────────────────

class ColorPreferencesDTO(BaseModel):
    primary: List[str] = []
    secondary: List[str] = []
    avoided: List[str] = []
    undertone: Optional[str] = None
    palette_type: Optional[str] = None


class FitPreferencesDTO(BaseModel):
    tops: str = "regular"
    bottoms: str = "regular"
    dresses: str = "regular"
    outerwear: str = "regular"


class OccasionPreferencesDTO(BaseModel):
    everyday: float = 0.5
    work: float = 0.5
    formal: float = 0.3
    casual: float = 0.7
    date_night: float = 0.4
    weekend: float = 0.6
    vacation: float = 0.5
    party: float = 0.4
    athletic: float = 0.3
    special_event: float = 0.2


class BrandAffinityDTO(BaseModel):
    brand_id: str
    brand_name: Optional[str] = None
    affinity_score: float = Field(ge=0.0, le=1.0)
    category: Optional[str] = None


class BudgetRangeDTO(BaseModel):
    per_item_min: Optional[float] = None
    per_item_max: Optional[float] = None
    monthly_max: Optional[float] = None
    currency: str = "USD"


class PatternPreferencesDTO(BaseModel):
    preferred: List[str] = []
    avoided: List[str] = []
    neutral: List[str] = []


class FabricPreferencesDTO(BaseModel):
    preferred: List[str] = []
    avoided: List[str] = []
    seasonal: Dict[str, List[str]] = {}


class SilhouettePreferencesDTO(BaseModel):
    tops: List[str] = []
    bottoms: List[str] = []
    dresses: List[str] = []


class SignalSummaryDTO(BaseModel):
    wardrobe_items: int = 0
    liked_outfits: int = 0
    purchases: int = 0
    quiz_answers: int = 0
    browsing_events: int = 0
    last_analyzed: Optional[datetime] = None


class StyleDNACreateDTO(BaseModel):
    """DTO for creating/updating style DNA profile."""
    primary_style: Optional[StyleCategory] = None
    secondary_styles: List[StyleCategory] = []
    color_preferences: Optional[ColorPreferencesDTO] = None
    fit_preference: FitPreference = FitPreference.REGULAR
    fit_preferences: Optional[FitPreferencesDTO] = None
    occasion_preferences: Optional[OccasionPreferencesDTO] = None
    brand_affinity: List[BrandAffinityDTO] = []
    budget_level: BudgetLevel = BudgetLevel.MODERATE
    budget_range: Optional[BudgetRangeDTO] = None
    pattern_preferences: Optional[PatternPreferencesDTO] = None
    fabric_preferences: Optional[FabricPreferencesDTO] = None
    silhouette_preferences: Optional[SilhouettePreferencesDTO] = None


class StyleDNAResponseDTO(BaseModel):
    """DTO for style DNA profile response."""
    id: str
    user_id: str
    primary_style: Optional[StyleCategory]
    secondary_styles: List[StyleCategory]
    style_confidence: float
    
    color_preferences: ColorPreferencesDTO
    fit_preference: FitPreference
    fit_preferences: FitPreferencesDTO
    occasion_preferences: OccasionPreferencesDTO
    brand_affinity: List[BrandAffinityDTO]
    
    budget_level: BudgetLevel
    budget_range: BudgetRangeDTO
    
    pattern_preferences: PatternPreferencesDTO
    fabric_preferences: FabricPreferencesDTO
    silhouette_preferences: SilhouettePreferencesDTO
    
    signal_summary: SignalSummaryDTO
    profile_completeness: float
    profile_version: int
    
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class StyleVectorDTO(BaseModel):
    """DTO for style vector."""
    id: str
    user_id: str
    vector_type: str
    confidence_score: float
    data_quality_score: float
    snapshot_reason: str
    created_at: datetime
    
    model_config = {"from_attributes": True}


class StyleEvolutionDTO(BaseModel):
    """DTO for style evolution event."""
    id: str
    user_id: str
    change_type: str
    previous_value: Optional[Dict[str, Any]]
    new_value: Dict[str, Any]
    drift_magnitude: Optional[float]
    trigger_source: str
    created_at: datetime
    
    model_config = {"from_attributes": True}


class StyleSimilarityDTO(BaseModel):
    """DTO for style similarity result."""
    user_id: str
    similarity: float
    shared_styles: List[StyleCategory]
    shared_brands: List[str]
    shared_colors: List[str]


class StyleClusterDTO(BaseModel):
    """DTO for style cluster."""
    id: str
    cluster_name: str
    cluster_description: Optional[str]
    dominant_styles: List[StyleCategory]
    dominant_colors: List[str]
    cluster_size: int
    
    model_config = {"from_attributes": True}


class UserClusterAssignmentDTO(BaseModel):
    """DTO for user cluster assignment."""
    cluster: StyleClusterDTO
    distance_to_centroid: float
    assignment_confidence: float
    secondary_clusters: List[Dict[str, Any]]


class StyleAnalysisResultDTO(BaseModel):
    """Complete style analysis result."""
    profile: StyleDNAResponseDTO
    cluster_assignment: Optional[UserClusterAssignmentDTO]
    similar_users: List[StyleSimilarityDTO]
    style_evolution: List[StyleEvolutionDTO]
    recommendations: Dict[str, Any]


class StyleQuizAnswerDTO(BaseModel):
    """Single quiz answer."""
    question_id: str
    selected_options: List[str] = []
    image_selections: List[str] = []
    confidence: Optional[float] = None


class StyleQuizSubmissionDTO(BaseModel):
    """Quiz submission DTO."""
    quiz_type: str = "initial"
    answers: List[StyleQuizAnswerDTO]
    duration_seconds: Optional[int] = None


class StyleQuizResultDTO(BaseModel):
    """Quiz result DTO."""
    computed_styles: Dict[str, float]
    computed_colors: Dict[str, Any]
    computed_fit: Dict[str, str]
    confidence: float
    profile_updated: bool


class StyleSignalCreateDTO(BaseModel):
    """DTO for creating a style signal."""
    signal_type: str
    signal_category: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    signal_data: Dict[str, Any] = {}
    base_weight: float = 0.5
    context: Dict[str, Any] = {}
    session_id: Optional[str] = None


class StyleDNADashboardDTO(BaseModel):
    """Complete dashboard data for Style DNA."""
    profile: StyleDNAResponseDTO
    style_map: Dict[str, Any]
    color_wheel: Dict[str, Any]
    brand_universe: List[Dict[str, Any]]
    evolution_timeline: List[StyleEvolutionDTO]
    style_insights: List[Dict[str, Any]]
    completeness_breakdown: Dict[str, float]
    recommendations: Dict[str, Any]
