"""
CONFIT Backend — AI Stylist Chat Models
========================================
Database models for chat sessions, messages, and recommendations.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import enum

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text,
    JSON, Numeric, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from database.base import Base


# UUID column helper
_DB_URL = os.getenv("DATABASE_URL", "sqlite:///./confit.db")
if not _DB_URL.startswith("postgresql"):
    # SQLite fallback: map PostgreSQL JSONB columns to generic JSON.
    JSONB = JSON  # type: ignore[assignment]

if _DB_URL.startswith("postgresql"):
    UUIDType = PG_UUID(as_uuid=True)
else:
    UUIDType = String(36)


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MessageRoleEnum(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class RecommendationTypeEnum(str, enum.Enum):
    outfit = "outfit"
    product = "product"
    wardrobe_item = "wardrobe_item"
    style_tip = "style_tip"
    color_advice = "color_advice"


class OccasionEnum(str, enum.Enum):
    wedding = "wedding"
    work = "work"
    casual = "casual"
    date = "date"
    party = "party"
    interview = "interview"
    travel = "travel"
    gym = "gym"
    beach = "beach"
    formal = "formal"
    brunch = "brunch"
    outdoor = "outdoor"


class BudgetLevelEnum(str, enum.Enum):
    budget = "budget"      # Under $100
    moderate = "moderate"  # $100-$300
    premium = "premium"    # $300-$500
    luxury = "luxury"      # $500+


# ═══════════════════════════════════════════════════════════════════
# CHAT SESSION MODEL
# ═══════════════════════════════════════════════════════════════════

class ChatSession(Base):
    """A conversation session between user and AI stylist."""
    __tablename__ = "chat_sessions"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Session metadata
    title = Column(String(255), nullable=True)
    context = Column(JSONB, nullable=False, default=dict)
    
    # Detected context from conversation
    detected_occasion = Column(SQLEnum(OccasionEnum), nullable=True)
    detected_budget = Column(SQLEnum(BudgetLevelEnum), nullable=True)
    detected_style_preference = Column(String(100), nullable=True)
    
    # Session state
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    message_count = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    last_message_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")
    recommendations = relationship("StylistRecommendation", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_chat_sessions_user_active", "user_id", "is_active"),
    )


# ═══════════════════════════════════════════════════════════════════
# CHAT MESSAGE MODEL
# ═══════════════════════════════════════════════════════════════════

class ChatMessage(Base):
    """Individual messages within a chat session."""
    __tablename__ = "chat_messages"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    session_id = Column(UUIDType, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Message content
    role = Column(SQLEnum(MessageRoleEnum), nullable=False, index=True)
    content = Column(Text, nullable=False)
    
    # Structured response data (for assistant messages)
    detected_intent = Column(String(100), nullable=True)
    detected_entities = Column(JSONB, nullable=False, default=dict)  # occasion, budget, colors, etc.
    
    # Response metadata
    tokens_used = Column(Integer, nullable=True)
    model_version = Column(String(50), nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Feedback
    user_feedback = Column(Integer, nullable=True)  # 1-5 rating
    feedback_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    recommendations = relationship("StylistRecommendation", back_populates="message", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
        CheckConstraint("user_feedback IS NULL OR (user_feedback >= 1 AND user_feedback <= 5)", name="chk_feedback_range"),
    )


# ═══════════════════════════════════════════════════════════════════
# STYLIST RECOMMENDATION MODEL
# ═══════════════════════════════════════════════════════════════════

class StylistRecommendation(Base):
    """Recommendations made by the AI stylist during chat."""
    __tablename__ = "stylist_recommendations"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    session_id = Column(UUIDType, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(UUIDType, ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Recommendation type
    recommendation_type = Column(SQLEnum(RecommendationTypeEnum), nullable=False, index=True)
    
    # Content
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Reference data
    product_id = Column(UUIDType, ForeignKey("products.id"), nullable=True)
    wardrobe_item_id = Column(String(64), ForeignKey("wardrobe_items.id"), nullable=True)
    outfit_id = Column(String(64), ForeignKey("outfits.id"), nullable=True)
    
    # For outfit recommendations (multiple items)
    item_ids = Column(JSONB, nullable=False, default=list)
    
    # Media
    image_url = Column(Text, nullable=True)
    
    # Scoring
    relevance_score = Column(Float, nullable=False, default=0.0)  # 0.0 - 1.0
    style_match_score = Column(Float, nullable=True)
    price_match_score = Column(Float, nullable=True)
    occasion_fit_score = Column(Float, nullable=True)
    
    # Pricing
    estimated_price = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default="USD")
    
    # User interaction
    was_clicked = Column(Boolean, nullable=False, default=False)
    was_added_to_cart = Column(Boolean, nullable=False, default=False)
    was_added_to_wishlist = Column(Boolean, nullable=False, default=False)
    was_dismissed = Column(Boolean, nullable=False, default=False)
    
    # Context
    context_data = Column(JSONB, nullable=False, default=dict)  # Occasion, budget context when recommended
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    interacted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    session = relationship("ChatSession", back_populates="recommendations")
    message = relationship("ChatMessage", back_populates="recommendations")
    
    __table_args__ = (
        Index("ix_stylist_recommendations_session_type", "session_id", "recommendation_type"),
        Index("ix_stylist_recommendations_scores", "relevance_score", "style_match_score"),
    )


# ═══════════════════════════════════════════════════════════════════
# FASHION KNOWLEDGE EMBEDDINGS (for vector search)
# ═══════════════════════════════════════════════════════════════════

class FashionKnowledgeEmbedding(Base):
    """Vector embeddings for fashion knowledge base (pgvector)."""
    __tablename__ = "fashion_knowledge_embeddings"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    
    # Content
    content_type = Column(String(50), nullable=False, index=True)  # style_tip, color_rule, outfit_template
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    
    # Metadata
    tags = Column(JSONB, nullable=False, default=list)
    categories = Column(JSONB, nullable=False, default=list)
    occasions = Column(JSONB, nullable=False, default=list)
    seasons = Column(JSONB, nullable=False, default=list)
    
    # Embedding vector (for pgvector - stored as JSON for SQLite compatibility)
    embedding = Column(JSONB, nullable=True)  # Will store vector as array
    embedding_model = Column(String(100), nullable=True)
    
    # Usage tracking
    usage_count = Column(Integer, nullable=False, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    
    __table_args__ = (
        Index("ix_fashion_embeddings_type", "content_type"),
    )
