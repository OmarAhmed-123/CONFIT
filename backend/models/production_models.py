"""
CONFIT Backend - Production model extensions.

This module intentionally defines only tables that are not present in
database.models to avoid SQLAlchemy metadata collisions during startup.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database.base import Base
from database.models import UUIDType, _new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class ProductCategory(Base):
    __tablename__ = "product_categories"
    __table_args__ = {"extend_existing": True}

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    parent_id = Column(
        UUIDType,
        ForeignKey("product_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    level = Column(Integer, nullable=False, default=0)
    path = Column(String(500), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    parent = relationship("ProductCategory", remote_side=[id], backref="children")


class BrandManager(Base):
    __tablename__ = "brand_managers"
    __table_args__ = (
        UniqueConstraint("brand_id", "user_id", name="uq_brand_user"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    brand_id = Column(
        String(64),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUIDType,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(30), nullable=False, default="manager")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    brand = relationship("Brand")
    user = relationship("User")


class BrandFollower(Base):
    __tablename__ = "brand_followers"
    __table_args__ = (
        UniqueConstraint("brand_id", "user_id", name="uq_brand_follower"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    brand_id = Column(
        String(64),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUIDType,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    brand = relationship("Brand")
    user = relationship("User")
