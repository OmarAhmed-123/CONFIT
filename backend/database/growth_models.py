"""
CONFIT — Autonomous Growth Engine persistence
======================================
Tables: user_graph_edges, referrals, engagement_scores, growth_events
(social_posts lives in database.models)
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)

from database.base import Base
from database.models import UUIDType, _new_uuid


class UserGraphEdge(Base):
    """
    Dynamic fashion graph: user → styles | creators | brands | outfits
    """

    __tablename__ = "user_graph_edges"
    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", name="uq_user_graph_edge"),
        Index("ix_graph_user_target", "user_id", "target_type"),
        Index("ix_graph_user_weight", "user_id", "weight"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    target_type = Column(String(32), nullable=False)  # style, creator, brand, outfit
    target_id = Column(String(128), nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    interaction_count = Column(Integer, nullable=False, default=1)
    last_interaction_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    meta = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Referral(Base):
    """Referral tracking: share links, rewards, attribution."""

    __tablename__ = "referrals"
    __table_args__ = (
        Index("ix_referrals_code", "referral_code"),
        Index("ix_referrals_referee", "referee_user_id"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    referrer_user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    referral_code = Column(String(64), nullable=False, unique=True, index=True)
    outfit_id = Column(String(64), ForeignKey("outfits.id"), nullable=True, index=True)
    post_id = Column(UUIDType, ForeignKey("social_posts.id"), nullable=True, index=True)
    referee_user_id = Column(UUIDType, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="pending")  # pending, completed, rewarded
    reward_credits = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)


class EngagementScore(Base):
    """Per-user engagement & conversion predictions (updated incrementally)."""

    __tablename__ = "engagement_scores"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_engagement_scores_user"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    purchase_likelihood = Column(Float, nullable=False, default=0.5)
    churn_risk = Column(Float, nullable=False, default=0.2)
    share_probability = Column(Float, nullable=False, default=0.3)
    engagement_index = Column(Float, nullable=False, default=0.5)
    style_vector_hint = Column(JSON, nullable=True)
    model_version = Column(String(32), nullable=False, default="heuristic-v1")
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class GrowthEvent(Base):
    """Audit + automation loop: shares, notifications, anomalies, self-optimization."""

    __tablename__ = "growth_events"
    __table_args__ = (
        Index("ix_growth_events_user_type", "user_id", "event_type"),
        Index("ix_growth_events_created", "created_at"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    payload = Column(JSON, nullable=True)
    severity = Column(String(16), nullable=False, default="info")  # info, warn, block
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class GrowthShareRateLimit(Base):
    """Per-user share rate limiting (anti-spam)."""

    __tablename__ = "growth_share_rate_limits"
    __table_args__ = (
        UniqueConstraint("user_id", "window_start", name="uq_growth_share_window"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    share_count = Column(Integer, nullable=False, default=0)
    window_start = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
