"""
CONFIT Backend — Production SQLAlchemy Models (Unique Models Only)
==================================================================
This file contains ONLY models NOT defined in database/models.py.
Canonical models are in database/models.py.

Unique tables in this file:
- brand_managers, brand_followers
- product_categories, product_variants, product_tags
- inventory_items, inventory_movements
- wardrobe_collections, wardrobe_collection_items
- outfit_history
- payment_methods, payments, payment_events
- bnpl_applications, bnpl_payment_schedule
- tryon_sessions, tryon_results
- visual_search_sessions, visual_search_results
- user_events, brand_analytics, product_analytics
- recommendation_history
- audit_log, entity_versions
"""

import os
import uuid
import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text,
    JSON, Numeric, Enum as SQLEnum, UniqueConstraint, CheckConstraint,
    Index, event, func, select
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, INET, ARRAY
from sqlalchemy.orm import relationship, backref, column_property
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property

from database.base import Base

# ── UUID column helper ────────────────────────────────────────────────────────
_DB_URL = os.getenv("DATABASE_URL", "sqlite:///./confit.db")

if _DB_URL.startswith("postgresql"):
    UUIDType = PG_UUID(as_uuid=True)
else:
    UUIDType = String(36)


def generate_uuid() -> str:
    return str(uuid.uuid4())


def generate_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════
# ENUMERATED TYPES
# ═══════════════════════════════════════════════════════════════════

class UserRoleEnum(str, enum.Enum):
    admin = "admin"
    brand_manager = "brand_manager"
    stylist = "stylist"
    user = "user"
    moderator = "moderator"


class OrderStatusEnum(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"
    refunded = "refunded"
    returned = "returned"
    failed = "failed"


class PaymentStatusEnum(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"
    partially_refunded = "partially_refunded"
    disputed = "disputed"


class PaymentMethodEnum(str, enum.Enum):
    card = "card"
    apple_pay = "apple_pay"
    google_pay = "google_pay"
    paypal = "paypal"
    bnpl_affirm = "bnpl_affirm"
    bnpl_klarna = "bnpl_klarna"
    bnpl_afterpay = "bnpl_afterpay"
    store_credit = "store_credit"


class BNPLStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    active = "active"
    paid = "paid"
    defaulted = "defaulted"
    cancelled = "cancelled"


class ProductStatusEnum(str, enum.Enum):
    draft = "draft"
    active = "active"
    out_of_stock = "out_of_stock"
    discontinued = "discontinued"
    archived = "archived"


class InventoryStatusEnum(str, enum.Enum):
    in_stock = "in_stock"
    low_stock = "low_stock"
    out_of_stock = "out_of_stock"
    reserved = "reserved"
    discontinued = "discontinued"


class TryOnStatusEnum(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    expired = "expired"


class VisualSearchStatusEnum(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class RecommendationTypeEnum(str, enum.Enum):
    personalized = "personalized"
    trending = "trending"
    similar = "similar"
    complementary = "complementary"
    occasion = "occasion"
    seasonal = "seasonal"
    price_drop = "price_drop"


class EventTypeEnum(str, enum.Enum):
    view = "view"
    click = "click"
    add_to_cart = "add_to_cart"
    remove_from_cart = "remove_from_cart"
    purchase = "purchase"
    wishlist_add = "wishlist_add"
    wishlist_remove = "wishlist_remove"
    try_on = "try_on"
    search = "search"
    share = "share"
    review = "review"
    returned = "return"
    refund = "refund"


# ═══════════════════════════════════════════════════════════════════
# BASE MIXINS
# ═══════════════════════════════════════════════════════════════════

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    @hybrid_property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class VersionMixin:
    """Mixin for versioning support."""
    
    version = Column(Integer, nullable=False, default=1)


# ═══════════════════════════════════════════════════════════════════
# BRAND MODULE (Unique models only - Brand is in database/models.py)
# ═══════════════════════════════════════════════════════════════════

class BrandManager(Base, TimestampMixin):
    """Brand manager assignments."""
    __tablename__ = "brand_managers"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    brand_id = Column(String(64), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    role = Column(String(30), nullable=False, default="manager")
    permissions = Column(JSONB, nullable=False, default=list)
    
    invited_by = Column(UUIDType, ForeignKey("users.id"), nullable=True)
    invited_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    
    is_active = Column(Boolean, nullable=False, default=True)
    
    brand = relationship("Brand", back_populates="managers")
    user = relationship("User", foreign_keys=[user_id])
    inviter = relationship("User", foreign_keys=[invited_by])
    
    __table_args__ = (
        UniqueConstraint("brand_id", "user_id", name="uq_brand_user"),
    )


class BrandFollower(Base, TimestampMixin):
    """Brand followers."""
    __tablename__ = "brand_followers"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    brand_id = Column(String(64), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    notification_enabled = Column(Boolean, nullable=False, default=True)
    
    brand = relationship("Brand", back_populates="followers")
    user = relationship("User")
    
    __table_args__ = (
        UniqueConstraint("brand_id", "user_id", name="uq_brand_follower"),
    )


# ═══════════════════════════════════════════════════════════════════
# PRODUCT MODULE (Unique models only - Product is in database/models.py)
# ═══════════════════════════════════════════════════════════════════

class ProductCategory(Base, TimestampMixin):
    """Product categories (hierarchical)."""
    __tablename__ = "product_categories"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    parent_id = Column(UUIDType, ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    
    # Display
    icon = Column(String(50), nullable=True)
    image_url = Column(Text, nullable=True)
    
    # Hierarchy
    level = Column(Integer, nullable=False, default=0)
    path = Column(String(500), nullable=True, index=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    is_featured = Column(Boolean, nullable=False, default=False)
    display_order = Column(Integer, nullable=False, default=0)
    
    # SEO
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)
    
    # Statistics
    product_count = Column(Integer, nullable=False, default=0)
    
    # Relationships
    parent = relationship("ProductCategory", remote_side=[id], backref="children")
    products = relationship("Product", back_populates="category")


class ProductVariant(Base, TimestampMixin):
    """Product variants (size, color combinations)."""
    __tablename__ = "product_variants"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    product_id = Column(UUIDType, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Variant attributes
    sku = Column(String(100), nullable=False, unique=True, index=True)
    barcode = Column(String(50), nullable=True)
    
    # Options
    size = Column(String(20), nullable=True, index=True)
    color = Column(String(50), nullable=True, index=True)
    color_hex = Column(String(7), nullable=True)
    
    # Pricing
    price_adjustment = Column(Numeric(10, 2), nullable=False, default=Decimal("0.0"))
    cost_price = Column(Numeric(10, 2), nullable=True)
    
    # Inventory
    inventory_quantity = Column(Integer, nullable=False, default=0)
    inventory_status = Column(SQLEnum(InventoryStatusEnum), nullable=False, default=InventoryStatusEnum.in_stock)
    low_stock_threshold = Column(Integer, nullable=False, default=5)
    
    # Media
    image_url = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    product = relationship("Product", back_populates="variants")


class ProductTag(Base, TimestampMixin):
    """Product tags."""
    __tablename__ = "product_tags"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    name = Column(String(50), nullable=False, unique=True, index=True)
    slug = Column(String(50), nullable=False, unique=True, index=True)
    
    usage_count = Column(Integer, nullable=False, default=0)


# ═══════════════════════════════════════════════════════════════════
# INVENTORY MODULE (Store is in database/models.py)
# ═══════════════════════════════════════════════════════════════════

class InventoryItem(Base, TimestampMixin):
    """Inventory tracking with location and reservation support."""
    __tablename__ = "inventory_items"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    variant_id = Column(UUIDType, ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False, index=True)
    store_id = Column(UUIDType, ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Quantities
    quantity = Column(Integer, nullable=False, default=0)
    reserved_quantity = Column(Integer, nullable=False, default=0)
    available_quantity = Column(Integer, nullable=False, default=0)
    
    # Location
    location_code = Column(String(50), nullable=True)
    
    # Status
    status = Column(SQLEnum(InventoryStatusEnum), nullable=False, default=InventoryStatusEnum.in_stock)
    
    # Reorder
    reorder_point = Column(Integer, nullable=False, default=10)
    reorder_quantity = Column(Integer, nullable=False, default=50)
    
    # Cost
    unit_cost = Column(Numeric(10, 2), nullable=True)


class InventoryMovement(Base, TimestampMixin):
    """Inventory movement audit trail."""
    __tablename__ = "inventory_movements"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    inventory_id = Column(UUIDType, ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Movement
    movement_type = Column(String(20), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    previous_quantity = Column(Integer, nullable=False)
    new_quantity = Column(Integer, nullable=False)
    
    # Reference
    reference_type = Column(String(30), nullable=True)
    reference_id = Column(String(64), nullable=True)
    
    # Context
    reason = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Actor
    performed_by = Column(UUIDType, ForeignKey("users.id"), nullable=True)


# ═══════════════════════════════════════════════════════════════════
# WARDROBE MODULE (WardrobeItem is in database/models.py)
# ═══════════════════════════════════════════════════════════════════

class WardrobeCollection(Base, TimestampMixin):
    """User-created wardrobe groupings."""
    __tablename__ = "wardrobe_collections"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    cover_image_url = Column(Text, nullable=True)
    
    is_public = Column(Boolean, nullable=False, default=False)
    is_featured = Column(Boolean, nullable=False, default=False)
    
    item_count = Column(Integer, nullable=False, default=0)
    
    items = relationship("WardrobeItem", secondary="wardrobe_collection_items", back_populates="collections")


class WardrobeCollectionItem(Base):
    """Association table for wardrobe collections and items."""
    __tablename__ = "wardrobe_collection_items"
    
    collection_id = Column(UUIDType, ForeignKey("wardrobe_collections.id", ondelete="CASCADE"), primary_key=True)
    item_id = Column(String(64), ForeignKey("wardrobe_items.id", ondelete="CASCADE"), primary_key=True)
    
    added_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    display_order = Column(Integer, nullable=False, default=0)


# ═══════════════════════════════════════════════════════════════════
# OUTFITS MODULE (Outfit is in database/models.py)
# ═══════════════════════════════════════════════════════════════════

class OutfitHistory(Base, TimestampMixin):
    """Worn outfit history."""
    __tablename__ = "outfit_history"
    
    id = Column(String(64), primary_key=True)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    outfit_id = Column(String(64), ForeignKey("outfits.id", ondelete="SET NULL"), nullable=True)
    
    # Snapshot
    outfit_name = Column(String(200), nullable=True)
    item_ids = Column(JSONB, nullable=False)
    item_details = Column(JSONB, nullable=True)
    
    # Context
    occasion = Column(String(50), nullable=True, index=True)
    weather = Column(String(30), nullable=True)
    temperature_c = Column(Integer, nullable=True)
    season = Column(String(20), nullable=True)
    
    # Wear info
    worn_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    is_favorite = Column(Boolean, nullable=False, default=False)
    
    # Feedback
    user_rating = Column(Integer, nullable=True)
    feedback_notes = Column(Text, nullable=True)
    
    # AI insights
    ai_generated = Column(Boolean, nullable=False, default=False)
    style_score = Column(Numeric(5, 2), nullable=True)
    color_harmony_score = Column(Numeric(5, 2), nullable=True)
    
    user = relationship("User")


# ═══════════════════════════════════════════════════════════════════
# PAYMENTS MODULE (Order, OrderItem, ReturnRequest in database/models.py)
# ═══════════════════════════════════════════════════════════════════

class PaymentMethod(Base, TimestampMixin):
    """Stored payment method tokens (PCI-DSS compliant)."""
    __tablename__ = "payment_methods"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Type
    type = Column(SQLEnum(PaymentMethodEnum), nullable=False)
    
    # Tokenized data
    provider = Column(String(20), nullable=False)
    provider_token = Column(String(255), nullable=False)
    provider_customer_id = Column(String(255), nullable=True)
    
    # Display info (safe to store)
    last_four = Column(String(4), nullable=True)
    card_brand = Column(String(20), nullable=True)
    expiry_month = Column(Integer, nullable=True)
    expiry_year = Column(Integer, nullable=True)
    
    # Billing address
    billing_address = Column(JSONB, nullable=True)
    
    # Status
    is_default = Column(Boolean, nullable=False, default=False)
    is_verified = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    
    user = relationship("User", back_populates="payment_methods")


class Payment(Base, TimestampMixin):
    """Payment transactions."""
    __tablename__ = "payments"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    order_id = Column(String(64), ForeignKey("orders.id"), nullable=False, index=True)
    
    # Amount
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    
    # Method
    method = Column(SQLEnum(PaymentMethodEnum), nullable=False)
    payment_method_id = Column(UUIDType, ForeignKey("payment_methods.id"), nullable=True)
    
    # Provider
    provider = Column(String(20), nullable=False)
    provider_transaction_id = Column(String(255), nullable=True, index=True)
    provider_customer_id = Column(String(255), nullable=True)
    
    # Status
    status = Column(SQLEnum(PaymentStatusEnum), nullable=False, default=PaymentStatusEnum.pending, index=True)
    
    # 3D Secure
    three_d_secure_required = Column(Boolean, nullable=False, default=False)
    three_d_secure_version = Column(String(10), nullable=True)
    
    # Refunds
    refund_amount = Column(Numeric(12, 2), default=Decimal("0.0"))
    
    # Metadata
    description = Column(Text, nullable=True)
    extra_metadata = Column(JSONB, nullable=False, default=dict)
    
    # Dates
    attempted_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    refunded_at = Column(DateTime(timezone=True), nullable=True)
    
    # IP and device info
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Risk
    risk_score = Column(Numeric(3, 2), nullable=True)
    risk_flags = Column(JSONB, nullable=False, default=list)
    
    # Error
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    
    order = relationship("Order", back_populates="payments")
    payment_method = relationship("PaymentMethod")


class PaymentEvent(Base, TimestampMixin):
    """Payment event audit trail."""
    __tablename__ = "payment_events"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    payment_id = Column(UUIDType, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Event
    event_type = Column(String(30), nullable=False, index=True)
    old_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=False)
    
    # Provider data
    provider_event_id = Column(String(255), nullable=True)
    provider_data = Column(JSONB, nullable=True)
    
    # Context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    payment = relationship("Payment", back_populates="events")


# ═══════════════════════════════════════════════════════════════════
# BNPL MODULE
# ═══════════════════════════════════════════════════════════════════

class BNPLApplication(Base, TimestampMixin):
    """Buy Now Pay Later financing applications."""
    __tablename__ = "bnpl_applications"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    order_id = Column(String(64), ForeignKey("orders.id"), nullable=False, index=True)
    
    # Provider
    provider = Column(String(20), nullable=False)
    provider_application_id = Column(String(255), nullable=True, index=True)
    
    # Amount
    principal_amount = Column(Numeric(12, 2), nullable=False)
    interest_rate = Column(Numeric(5, 4), nullable=True)
    total_repayable = Column(Numeric(12, 2), nullable=True)
    
    # Terms
    term_months = Column(Integer, nullable=False)
    installment_count = Column(Integer, nullable=False)
    
    # Status
    status = Column(SQLEnum(BNPLStatusEnum), nullable=False, default=BNPLStatusEnum.pending, index=True)
    
    # Dates
    applied_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User")
    order = relationship("Order")


class BNPLPaymentSchedule(Base, TimestampMixin):
    """BNPL payment installment schedule."""
    __tablename__ = "bnpl_payment_schedule"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    application_id = Column(UUIDType, ForeignKey("bnpl_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Installment
    installment_number = Column(Integer, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    
    # Due
    due_date = Column(DateTime, nullable=False, index=True)
    
    # Payment
    paid_at = Column(DateTime(timezone=True), nullable=True)
    payment_method_id = Column(UUIDType, ForeignKey("payment_methods.id"), nullable=True)
    payment_id = Column(UUIDType, ForeignKey("payments.id"), nullable=True)
    
    # Status
    status = Column(String(20), nullable=False, default="pending", index=True)
    
    # Late
    is_late = Column(Boolean, nullable=False, default=False)
    late_fee = Column(Numeric(10, 2), nullable=True)
    
    application = relationship("BNPLApplication")


# ═══════════════════════════════════════════════════════════════════
# TRY-ON MODULE (DigitalTwin is in database/models.py)
# ═══════════════════════════════════════════════════════════════════

class TryOnSession(Base, TimestampMixin):
    """Virtual try-on processing sessions."""
    __tablename__ = "tryon_sessions"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    twin_id = Column(UUIDType, ForeignKey("digital_twins.id"), nullable=True)
    
    # Input
    user_image_hash = Column(String(64), nullable=False)
    garment_image_url = Column(Text, nullable=False)
    garment_product_id = Column(UUIDType, ForeignKey("products.id"), nullable=True)
    garment_name = Column(String(255), nullable=False)
    garment_category = Column(String(50), nullable=False, default="tops")
    
    # Options
    fit_type = Column(String(20), nullable=False, default="regular")
    environment = Column(String(50), default="studio")
    
    # Output
    result_image_url = Column(Text, nullable=True)
    result_image_hash = Column(String(64), nullable=True)
    
    # Quality metrics
    quality_score = Column(Numeric(5, 2), nullable=False, default=Decimal("0.0"))
    realism_score = Column(Numeric(5, 2), nullable=True)
    edge_quality = Column(Numeric(5, 2), nullable=True)
    color_consistency = Column(Numeric(5, 2), nullable=True)
    proportion_score = Column(Numeric(5, 2), nullable=True)
    artifact_score = Column(Numeric(5, 2), nullable=True)
    
    # Processing
    pose_detected = Column(Boolean, nullable=False, default=False)
    processing_mode = Column(String(30), nullable=False, default="advanced")
    processing_time_ms = Column(Integer, nullable=False, default=0)
    
    # Status
    status = Column(SQLEnum(TryOnStatusEnum), nullable=False, default=TryOnStatusEnum.pending, index=True)
    error_message = Column(Text, nullable=True)
    warnings = Column(JSONB, nullable=False, default=list)
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="tryon_sessions")
    results = relationship("TryOnResult", back_populates="session", cascade="all, delete-orphan")


class TryOnResult(Base, TimestampMixin):
    """Persisted try-on results."""
    __tablename__ = "tryon_results"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    session_id = Column(UUIDType, ForeignKey("tryon_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Result
    result_image_url = Column(Text, nullable=False)
    thumbnail_url = Column(Text, nullable=True)
    
    # Product
    product_id = Column(UUIDType, ForeignKey("products.id"), nullable=True)
    
    # Engagement
    view_count = Column(Integer, nullable=False, default=0)
    share_count = Column(Integer, nullable=False, default=0)
    purchase_count = Column(Integer, nullable=False, default=0)
    
    # Status
    is_saved = Column(Boolean, nullable=False, default=False)
    is_public = Column(Boolean, nullable=False, default=False)
    
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    session = relationship("TryOnSession", back_populates="results")


# ═══════════════════════════════════════════════════════════════════
# VISUAL SEARCH MODULE
# ═══════════════════════════════════════════════════════════════════

class VisualSearchSession(Base, TimestampMixin):
    """Image-based product search sessions."""
    __tablename__ = "visual_search_sessions"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Input
    input_image_url = Column(Text, nullable=False)
    input_image_hash = Column(String(64), nullable=True)
    
    # Processing
    detected_categories = Column(JSONB, nullable=False, default=list)
    detected_colors = Column(JSONB, nullable=False, default=list)
    detected_patterns = Column(JSONB, nullable=False, default=list)
    detected_styles = Column(JSONB, nullable=False, default=list)
    
    # Status
    status = Column(SQLEnum(VisualSearchStatusEnum), nullable=False, default=VisualSearchStatusEnum.pending, index=True)
    error_message = Column(Text, nullable=True)
    
    # Processing metrics
    processing_time_ms = Column(Integer, nullable=False, default=0)
    
    results = relationship("VisualSearchResult", back_populates="session", cascade="all, delete-orphan")


class VisualSearchResult(Base, TimestampMixin):
    """Visual search result matches."""
    __tablename__ = "visual_search_results"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    session_id = Column(UUIDType, ForeignKey("visual_search_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Result
    product_id = Column(UUIDType, ForeignKey("products.id"), nullable=False, index=True)
    
    # Matching
    similarity_score = Column(Numeric(5, 4), nullable=False, index=True)
    match_type = Column(String(30), nullable=False)
    matched_attributes = Column(JSONB, nullable=False, default=list)
    
    # Ranking
    rank_position = Column(Integer, nullable=False)
    
    # Engagement
    clicked = Column(Boolean, nullable=False, default=False)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    
    session = relationship("VisualSearchSession", back_populates="results")


# ═══════════════════════════════════════════════════════════════════
# ANALYTICS MODULE
# ═══════════════════════════════════════════════════════════════════

class UserEvent(Base, TimestampMixin):
    """User behavior analytics (partitioned)."""
    __tablename__ = "user_events"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id = Column(UUIDType, nullable=True)
    
    # Event
    event_type = Column(SQLEnum(EventTypeEnum), nullable=False, index=True)
    event_name = Column(String(100), nullable=True)
    
    # Context
    entity_type = Column(String(30), nullable=True)
    entity_id = Column(String(100), nullable=True, index=True)
    
    # Data
    event_data = Column(JSONB, nullable=False, default=dict)
    
    # Device/Session
    device_type = Column(String(20), nullable=True)
    platform = Column(String(20), nullable=True)
    app_version = Column(String(20), nullable=True)
    
    # Location
    ip_address = Column(String(45), nullable=True)
    country_code = Column(String(2), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Referrer
    referrer = Column(Text, nullable=True)
    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)


class BrandAnalytics(Base, TimestampMixin):
    """Aggregated brand analytics."""
    __tablename__ = "brand_analytics"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    brand_id = Column(String(64), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Period
    period_type = Column(String(10), nullable=False)
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)
    
    # Metrics
    view_count = Column(Integer, nullable=False, default=0)
    unique_visitors = Column(Integer, nullable=False, default=0)
    add_to_cart_count = Column(Integer, nullable=False, default=0)
    purchase_count = Column(Integer, nullable=False, default=0)
    purchase_revenue = Column(Numeric(14, 2), nullable=False, default=Decimal("0.0"))
    
    # Engagement
    follower_gain = Column(Integer, nullable=False, default=0)
    follower_loss = Column(Integer, nullable=False, default=0)
    
    # Conversion
    conversion_rate = Column(Numeric(5, 2), nullable=True)
    avg_order_value = Column(Numeric(10, 2), nullable=True)
    
    # Products
    top_products = Column(JSONB, nullable=False, default=list)
    top_categories = Column(JSONB, nullable=False, default=list)
    
    # Demographics
    top_countries = Column(JSONB, nullable=False, default=list)
    top_age_groups = Column(JSONB, nullable=False, default=list)
    
    __table_args__ = (
        UniqueConstraint("brand_id", "period_type", "period_start", name="uq_brand_analytics_period"),
    )


class ProductAnalytics(Base, TimestampMixin):
    """Aggregated product analytics."""
    __tablename__ = "product_analytics"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    product_id = Column(UUIDType, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Period
    period_type = Column(String(10), nullable=False)
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)
    
    # Metrics
    view_count = Column(Integer, nullable=False, default=0)
    unique_viewers = Column(Integer, nullable=False, default=0)
    add_to_cart_count = Column(Integer, nullable=False, default=0)
    wishlist_add_count = Column(Integer, nullable=False, default=0)
    purchase_count = Column(Integer, nullable=False, default=0)
    purchase_revenue = Column(Numeric(14, 2), nullable=False, default=Decimal("0.0"))
    
    # Engagement
    try_on_count = Column(Integer, nullable=False, default=0)
    share_count = Column(Integer, nullable=False, default=0)
    
    # Conversion
    conversion_rate = Column(Numeric(5, 2), nullable=True)
    return_rate = Column(Numeric(5, 2), nullable=True)
    
    # Search
    search_impressions = Column(Integer, nullable=False, default=0)
    search_clicks = Column(Integer, nullable=False, default=0)
    search_ctr = Column(Numeric(5, 2), nullable=True)
    
    __table_args__ = (
        UniqueConstraint("product_id", "period_type", "period_start", name="uq_product_analytics_period"),
    )


# ═══════════════════════════════════════════════════════════════════
# RECOMMENDATIONS MODULE
# ═══════════════════════════════════════════════════════════════════

class RecommendationHistory(Base, TimestampMixin):
    """AI recommendation tracking with feedback loop."""
    __tablename__ = "recommendation_history"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Recommendation
    recommendation_type = Column(SQLEnum(RecommendationTypeEnum), nullable=False, index=True)
    entity_type = Column(String(30), nullable=False)
    entity_ids = Column(JSONB, nullable=False, default=list)
    
    # Scores
    scores = Column(JSONB, nullable=False, default=dict)
    confidence = Column(Numeric(5, 2), nullable=False, default=Decimal("0.0"))
    
    # Context
    context_snapshot = Column(JSONB, nullable=False, default=dict)
    occasion = Column(String(50), nullable=True)
    budget = Column(Numeric(10, 2), nullable=True)
    
    # Explanation
    explanation = Column(Text, nullable=True)
    
    # Feedback
    user_feedback = Column(String(20), nullable=True, index=True)
    feedback_reason = Column(Text, nullable=True)
    feedback_at = Column(DateTime(timezone=True), nullable=True)
    
    # Session
    session_id = Column(UUIDType, nullable=True)


# ═══════════════════════════════════════════════════════════════════
# AUDIT & VERSIONING MODULE
# ═══════════════════════════════════════════════════════════════════

class AuditLog(Base, TimestampMixin):
    """System-wide audit trail (partitioned)."""
    __tablename__ = "audit_log"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    
    # Actor
    actor_type = Column(String(20), nullable=False, index=True)
    actor_id = Column(String(100), nullable=True, index=True)
    
    # Action
    action = Column(String(50), nullable=False, index=True)
    
    # Target
    table_name = Column(String(50), nullable=False, index=True)
    record_id = Column(String(100), nullable=False, index=True)
    
    # Changes
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    changed_fields = Column(JSONB, nullable=False, default=list)
    
    # Context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_id = Column(UUIDType, nullable=True)
    
    # Metadata
    extra_metadata = Column(JSONB, nullable=False, default=dict)


class EntityVersion(Base, TimestampMixin):
    """Entity version snapshots for undo/versioning."""
    __tablename__ = "entity_versions"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    
    # Entity
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(100), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    
    # Snapshot
    snapshot = Column(JSONB, nullable=False)
    
    # Actor
    created_by = Column(UUIDType, ForeignKey("users.id"), nullable=True)
    
    # Change info
    change_reason = Column(Text, nullable=True)
    
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "version", name="uq_entity_version"),
    )


# ═══════════════════════════════════════════════════════════════════
# MODEL REGISTRY
# ═══════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "UserRoleEnum", "OrderStatusEnum", "PaymentStatusEnum", "PaymentMethodEnum",
    "BNPLStatusEnum", "ProductStatusEnum", "InventoryStatusEnum", "TryOnStatusEnum",
    "VisualSearchStatusEnum", "RecommendationTypeEnum", "EventTypeEnum",
    
    # Brand Module (unique)
    "BrandManager", "BrandFollower",
    
    # Product Module (unique)
    "ProductCategory", "ProductVariant", "ProductTag",
    
    # Inventory Module
    "InventoryItem", "InventoryMovement",
    
    # Wardrobe Module (unique)
    "WardrobeCollection", "WardrobeCollectionItem",
    
    # Outfits Module (unique)
    "OutfitHistory",
    
    # Payments Module
    "PaymentMethod", "Payment", "PaymentEvent",
    
    # BNPL Module
    "BNPLApplication", "BNPLPaymentSchedule",
    
    # Try-On Module (unique)
    "TryOnSession", "TryOnResult",
    
    # Visual Search Module
    "VisualSearchSession", "VisualSearchResult",
    
    # Analytics Module
    "UserEvent", "BrandAnalytics", "ProductAnalytics",
    
    # Recommendations Module
    "RecommendationHistory",
    
    # Audit Module
    "AuditLog", "EntityVersion",
    
    # Utilities
    "generate_uuid", "generate_id", "utcnow",
]
