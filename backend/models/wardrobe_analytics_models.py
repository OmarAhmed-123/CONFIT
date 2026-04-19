"""
CONFIT Backend — Wardrobe Analytics Models
==========================================
GROUP 4: Personal Wardrobe & Smart Reuse
Analytics, tracking, and sustainability models.
"""

from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel, Field
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, JSON, Numeric, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from database.base import Base
from database.models import UUIDType, _new_uuid


# ═══════════════════════════════════════════════════════════════════
# SQLAlchemy ORM Models
# ═══════════════════════════════════════════════════════════════════

class WardrobeItemUsage(Base):
    """Track wear frequency and patterns for each wardrobe item."""
    __tablename__ = "wardrobe_item_usage"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    item_id = Column(String(64), ForeignKey("wardrobe_items.id"), nullable=False, index=True)
    
    # Wear tracking
    wear_count = Column(Integer, nullable=False, default=0)
    last_worn_at = Column(DateTime(timezone=True), nullable=True)
    first_worn_at = Column(DateTime(timezone=True), nullable=True)
    
    # Seasonal tracking
    seasons_worn = Column(JSON, default=list)  # ["spring", "summer", "fall", "winter"]
    current_season_wears = Column(Integer, default=0)
    
    # Occasion tracking
    occasions_worn = Column(JSON, default=dict)  # {"casual": 5, "work": 3, "date": 1}
    
    # Performance metrics
    cost_per_wear = Column(Numeric(10, 2), nullable=True)
    wear_frequency_score = Column(Numeric(5, 2), default=Decimal("0.0"))  # 0-100
    
    # Last calculated
    analytics_updated_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="wardrobe_usage")
    item = relationship("WardrobeItem", backref="usage_stats")
    
    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_user_item_usage"),
        Index("idx_usage_wear_count", "wear_count"),
    )


class OutfitHistory(Base):
    """Track outfit creation and wearing history."""
    __tablename__ = "outfit_history"
    
    id = Column(String(64), primary_key=True)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    # Outfit composition
    outfit_name = Column(String(200), nullable=True)
    item_ids = Column(JSON, nullable=False)  # ["item-1", "item-2", ...]
    item_details = Column(JSON, nullable=True)  # Full item snapshots
    
    # Occasion & context
    occasion = Column(String(50), nullable=True)
    weather = Column(String(30), nullable=True)  # "sunny", "rainy", "cold", etc.
    temperature_c = Column(Integer, nullable=True)
    season = Column(String(20), nullable=True)
    
    # Wear tracking
    worn_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    is_favorite = Column(Boolean, default=False)
    
    # Feedback
    user_rating = Column(Integer, nullable=True)  # 1-5 stars
    feedback_notes = Column(Text, nullable=True)
    
    # AI insights
    ai_generated = Column(Boolean, default=False)
    style_score = Column(Numeric(5, 2), nullable=True)
    color_harmony_score = Column(Numeric(5, 2), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="outfit_history")


class WardrobeSeasonalRotation(Base):
    """Track seasonal rotation and storage of items."""
    __tablename__ = "wardrobe_seasonal_rotation"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    item_id = Column(String(64), ForeignKey("wardrobe_items.id"), nullable=False, index=True)
    
    # Season classification
    primary_season = Column(String(20), nullable=True)  # "spring", "summer", "fall", "winter", "all_season"
    secondary_seasons = Column(JSON, default=list)
    
    # Rotation status
    is_active = Column(Boolean, default=True)  # Currently in active rotation
    stored_at = Column(DateTime(timezone=True), nullable=True)  # When moved to storage
    reactivated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Weather preferences
    min_temp_c = Column(Integer, nullable=True)
    max_temp_c = Column(Integer, nullable=True)
    weather_conditions = Column(JSON, default=list)  # ["sunny", "cloudy"]
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="seasonal_rotations")
    item = relationship("WardrobeItem", backref="seasonal_info")


class WardrobeSustainabilityMetrics(Base):
    """Track sustainability and environmental impact."""
    __tablename__ = "wardrobe_sustainability_metrics"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Usage metrics
    total_items = Column(Integer, default=0)
    active_items = Column(Integer, default=0)  # Worn in last 90 days
    unused_items = Column(Integer, default=0)  # Not worn in 180+ days
    
    # Sustainability scores
    wardrobe_utilization_score = Column(Numeric(5, 2), default=Decimal("0.0"))  # 0-100
    sustainability_score = Column(Numeric(5, 2), default=Decimal("0.0"))  # 0-100
    
    # Environmental impact
    total_estimated_co2_kg = Column(Numeric(10, 2), default=Decimal("0.0"))  # CO2 saved via reuse
    total_water_saved_l = Column(Numeric(10, 2), default=Decimal("0.0"))  # Water saved via reuse
    
    # Shopping prevention
    purchases_prevented = Column(Integer, default=0)  # Items not bought due to wardrobe
    money_saved = Column(Numeric(12, 2), default=Decimal("0.0"))
    
    # Capsule wardrobe
    capsule_wardrobe_score = Column(Numeric(5, 2), default=Decimal("0.0"))  # 0-100
    capsule_items_identified = Column(Integer, default=0)
    
    # Declutter suggestions
    declutter_candidates = Column(Integer, default=0)
    declutter_value_estimate = Column(Numeric(12, 2), default=Decimal("0.0"))
    
    # Period tracking
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="sustainability_metrics")


class WardrobeColorDominance(Base):
    """Track color distribution and dominance in wardrobe."""
    __tablename__ = "wardrobe_color_dominance"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    # Color counts
    color_name = Column(String(50), nullable=False)
    item_count = Column(Integer, nullable=False, default=0)
    percentage = Column(Numeric(5, 2), default=Decimal("0.0"))
    
    # Color harmony
    harmony_group = Column(String(30), nullable=True)  # "neutral", "warm", "cool", "accent"
    complementary_colors = Column(JSON, default=list)
    
    # Style insights
    is_dominant = Column(Boolean, default=False)
    is_overrepresented = Column(Boolean, default=False)
    style_impact = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="color_dominance")
    
    __table_args__ = (
        UniqueConstraint("user_id", "color_name", name="uq_user_color"),
        Index("idx_color_dominance_pct", "percentage"),
    )


class WardrobeStyleDominance(Base):
    """Track style/category distribution in wardrobe."""
    __tablename__ = "wardrobe_style_dominance"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    # Category/style
    category = Column(String(50), nullable=False)
    item_count = Column(Integer, nullable=False, default=0)
    percentage = Column(Numeric(5, 2), default=Decimal("0.0"))
    
    # Style tags
    style_tags = Column(JSON, default=list)
    
    # Wear patterns
    avg_wear_count = Column(Numeric(8, 2), default=Decimal("0.0"))
    most_worn_item_id = Column(String(64), nullable=True)
    
    # Gaps and recommendations
    is_gap = Column(Boolean, default=False)  # Category gap identified
    gap_severity = Column(String(20), nullable=True)  # "critical", "moderate", "minor"
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="style_dominance")
    
    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_user_category"),
    )


class WardrobeConfidenceScore(Base):
    """Wardrobe-specific confidence scoring."""
    __tablename__ = "wardrobe_confidence_scores"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Overall wardrobe confidence
    overall_confidence = Column(Numeric(5, 2), default=Decimal("0.0"))  # 0-100
    
    # Dimension scores
    variety_score = Column(Numeric(5, 2), default=Decimal("0.0"))  # Category variety
    versatility_score = Column(Numeric(5, 2), default=Decimal("0.0"))  # Mix & match potential
    utilization_score = Column(Numeric(5, 2), default=Decimal("0.0"))  # Items being worn
    cohesion_score = Column(Numeric(5, 2), default=Decimal("0.0"))  # Color/style harmony
    seasonality_score = Column(Numeric(5, 2), default=Decimal("0.0"))  # Season coverage
    quality_score = Column(Numeric(5, 2), default=Decimal("0.0"))  # Investment pieces
    
    # Outfit creation readiness
    outfit_readiness = Column(Numeric(5, 2), default=Decimal("0.0"))
    occasion_coverage = Column(JSON, default=dict)  # {"work": 85, "casual": 90, "formal": 40}
    
    # Improvement suggestions
    top_improvements = Column(JSON, default=list)
    quick_wins = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="wardrobe_confidence")


class CapsuleWardrobeDetection(Base):
    """Capsule wardrobe detection and tracking."""
    __tablename__ = "capsule_wardrobe_detections"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    # Capsule info
    capsule_name = Column(String(100), nullable=True)
    capsule_type = Column(String(30), nullable=False)  # "work", "casual", "travel", "seasonal"
    
    # Items
    item_ids = Column(JSON, nullable=False)
    item_count = Column(Integer, nullable=False)
    
    # Metrics
    cohesion_score = Column(Numeric(5, 2), default=Decimal("0.0"))
    versatility_score = Column(Numeric(5, 2), default=Decimal("0.0"))
    outfit_combinations = Column(Integer, default=0)  # Possible outfit combinations
    
    # Color palette
    dominant_colors = Column(JSON, default=list)
    color_harmony_type = Column(String(30), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_ai_suggested = Column(Boolean, default=False)
    user_approved = Column(Boolean, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="capsule_wardrobes")


class DeclutterSuggestion(Base):
    """Smart declutter suggestions based on usage patterns."""
    __tablename__ = "declutter_suggestions"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    item_id = Column(String(64), ForeignKey("wardrobe_items.id"), nullable=False, index=True)
    
    # Suggestion details
    suggestion_type = Column(String(30), nullable=False)  # "unused", "duplicate", "style_mismatch", "size_change"
    confidence = Column(Numeric(3, 2), default=Decimal("0.0"))
    
    # Reasoning
    reason = Column(Text, nullable=True)
    data_points = Column(JSON, default=dict)  # Supporting data
    
    # Value estimation
    estimated_resale_value = Column(Numeric(10, 2), nullable=True)
    donation_value = Column(Numeric(10, 2), nullable=True)
    
    # User actions
    status = Column(String(20), default="pending")  # "pending", "dismissed", "acted", "kept"
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
    acted_at = Column(DateTime(timezone=True), nullable=True)
    action_taken = Column(String(30), nullable=True)  # "resold", "donated", "recycled"
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="declutter_suggestions")
    item = relationship("WardrobeItem", backref="declutter_suggestion")


class PurchaseAvoidanceSignal(Base):
    """Track purchase prevention signals from wardrobe."""
    __tablename__ = "purchase_avoidance_signals"
    
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    # Signal details
    signal_type = Column(String(30), nullable=False)  # "duplicate_check", "outfit_suggestion", "item_found"
    
    # Product info (what was considered for purchase)
    product_name = Column(String(200), nullable=True)
    product_category = Column(String(50), nullable=True)
    product_color = Column(String(50), nullable=True)
    product_price = Column(Numeric(10, 2), nullable=True)
    
    # Matching wardrobe item
    matched_item_id = Column(String(64), nullable=True)
    match_similarity = Column(Numeric(3, 2), nullable=True)
    
    # Outcome
    purchase_avoided = Column(Boolean, default=True)
    user_feedback = Column(String(20), nullable=True)  # "helpful", "not_similar", "still_bought"
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="purchase_avoidance_signals")


# ═══════════════════════════════════════════════════════════════════
# Pydantic Schemas
# ═══════════════════════════════════════════════════════════════════

class WearLogEntry(BaseModel):
    """Schema for logging a wear event."""
    item_id: str
    worn_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    occasion: Optional[str] = None
    outfit_id: Optional[str] = None
    notes: Optional[str] = None


class OutfitHistoryCreate(BaseModel):
    """Schema for creating an outfit history entry."""
    outfit_name: Optional[str] = None
    item_ids: List[str]
    occasion: Optional[str] = None
    weather: Optional[str] = None
    temperature_c: Optional[int] = None
    season: Optional[str] = None
    is_favorite: bool = False
    ai_generated: bool = False


class OutfitHistoryResponse(BaseModel):
    """Schema for outfit history response."""
    id: str
    user_id: str
    outfit_name: Optional[str]
    item_ids: List[str]
    item_details: Optional[dict]
    occasion: Optional[str]
    weather: Optional[str]
    season: Optional[str]
    worn_at: datetime
    is_favorite: bool
    user_rating: Optional[int]
    style_score: Optional[float]
    created_at: datetime
    
    model_config = {"from_attributes": True}


class WardrobeAnalyticsResponse(BaseModel):
    """Comprehensive wardrobe analytics response."""
    total_items: int
    active_items: int
    unused_items: int
    
    # Usage metrics
    avg_wears_per_item: float
    most_worn_item: Optional[dict]
    least_worn_items: List[dict]
    
    # Seasonal
    seasonal_coverage: dict
    items_by_season: dict
    
    # Color analysis
    color_distribution: List[dict]
    dominant_colors: List[str]
    color_harmony_score: float
    
    # Style analysis
    category_distribution: List[dict]
    style_gaps: List[dict]
    
    # Sustainability
    sustainability_score: float
    wardrobe_utilization: float
    co2_saved_kg: float
    money_saved: float
    
    # Confidence
    wardrobe_confidence: float
    outfit_readiness: float
    
    model_config = {"from_attributes": True}


class SustainabilityInsightsResponse(BaseModel):
    """Sustainability insights response."""
    sustainability_score: float
    wardrobe_utilization_score: float
    
    # Environmental impact
    total_co2_saved_kg: float
    total_water_saved_l: float
    purchases_prevented: int
    money_saved: float
    
    # Breakdown
    item_breakdown: List[dict]
    monthly_trend: List[dict]
    
    # Recommendations
    sustainability_tips: List[str]
    eco_friendly_suggestions: List[str]
    
    model_config = {"from_attributes": True}


class CapsuleWardrobeResponse(BaseModel):
    """Capsule wardrobe detection response."""
    id: str
    capsule_name: Optional[str]
    capsule_type: str
    item_ids: List[str]
    item_count: int
    cohesion_score: float
    versatility_score: float
    outfit_combinations: int
    dominant_colors: List[str]
    color_harmony_type: Optional[str]
    is_ai_suggested: bool
    
    model_config = {"from_attributes": True}


class DeclutterSuggestionResponse(BaseModel):
    """Declutter suggestion response."""
    id: str
    item_id: str
    item_name: str
    item_image: Optional[str]
    suggestion_type: str
    confidence: float
    reason: str
    estimated_resale_value: Optional[float]
    days_since_last_wear: Optional[int]
    wear_count: int
    
    model_config = {"from_attributes": True}


class WardrobeConfidenceResponse(BaseModel):
    """Wardrobe confidence score response."""
    overall_confidence: float
    variety_score: float
    versatility_score: float
    utilization_score: float
    cohesion_score: float
    seasonality_score: float
    quality_score: float
    outfit_readiness: float
    occasion_coverage: dict
    top_improvements: List[str]
    quick_wins: List[str]
    
    model_config = {"from_attributes": True}


class PurchaseAvoidanceResponse(BaseModel):
    """Purchase avoidance signal response."""
    avoided: bool
    matched_item_id: Optional[str]
    matched_item_name: Optional[str]
    matched_item_image: Optional[str]
    similarity: float
    money_saved: Optional[float]
    suggestion: str


class SeasonalRotationResponse(BaseModel):
    """Seasonal rotation status response."""
    current_season: str
    active_items: int
    stored_items: int
    items_to_activate: List[dict]
    items_to_store: List[dict]
    weather_recommendations: dict
