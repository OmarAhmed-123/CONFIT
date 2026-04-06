"""
CONFIT Backend — SQLAlchemy ORM Models
=======================================
Persistent entities for users, brands, stores, products, orders,
wardrobe, outfits, and new features: digital twins, QR scans, gamification.

UUID columns use a helper (UUIDType) so the same model code works with
both SQLite (development) and PostgreSQL (production).
"""

import enum
import os
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    BigInteger,
    String,
    Text,
    JSON,
    Numeric,
    Enum as SQLEnum,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database.base import Base

# ── UUID column helper ────────────────────────────────────────────────────────
# Use PostgreSQL-native UUID in production; fall back to String(36) for SQLite.
_DB_URL = os.getenv("DATABASE_URL", "sqlite:///./confit.db")

if _DB_URL.startswith("postgresql"):
    try:
        from sqlalchemy.dialects.postgresql import UUID as _PGUUID
        UUIDType = _PGUUID(as_uuid=True)
    except ImportError:
        UUIDType = String(36)
else:
    UUIDType = String(36)


def _new_uuid() -> str:
    import uuid
    return str(uuid.uuid4())


# ── Enums ─────────────────────────────────────────────────────────────────────

class AppRole(str, enum.Enum):
    admin = "admin"
    brand_manager = "brand_manager"
    stylist = "stylist"
    user = "user"


class ActorType(str, enum.Enum):
    """Actor types for multi-actor notification system."""
    CUSTOMER = "CUSTOMER"
    STORE = "STORE"
    FACTORY = "FACTORY"
    DONOR = "DONOR"
    ADMIN = "ADMIN"


# ── User & Auth ───────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id             = Column(UUIDType, primary_key=True, default=_new_uuid)
    name           = Column(String(255), nullable=False)
    email          = Column(String(255), unique=True, nullable=False, index=True)
    password_hash  = Column(String(255), nullable=False)
    created_at     = Column(DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc))

    phone                = Column(String(64), nullable=True)
    address              = Column(JSON, nullable=True)
    avatar_url           = Column(String(1024), nullable=True)
    date_of_birth        = Column(DateTime(timezone=True), nullable=True)  # For birthday emails
    style_preference     = Column(String(255), nullable=True)
    body_profile         = Column(JSON, nullable=True)
    budget_range         = Column(JSON, nullable=True)
    preferred_brands     = Column(JSON, nullable=True)
    occasion_preferences = Column(JSON, nullable=True)
    marketing_consent    = Column(Boolean, nullable=True)
    data_sharing_consent = Column(Boolean, nullable=True)

    orders            = relationship("Order",           back_populates="user")
    wardrobe_items    = relationship("WardrobeItem",    back_populates="user")
    outfits           = relationship("Outfit",          back_populates="user")
    digital_twins     = relationship("DigitalTwin",     back_populates="user")
    qr_scans          = relationship("QrScanSession",   back_populates="user")
    quest_completions = relationship("QuestCompletion", back_populates="user")
    gamification      = relationship("UserGamification", back_populates="user",
                                     uselist=False)
    
    # Profile relationships (from profile_models.py)
    style_profile_rel           = relationship("UserStyleProfile",           back_populates="user", uselist=False)
    body_profile_rel            = relationship("UserBodyProfile",            back_populates="user", uselist=False)
    budget_profile_rel          = relationship("UserBudgetProfile",          back_populates="user", uselist=False)
    brand_affinities_rel        = relationship("UserBrandAffinity",          back_populates="user")
    contextual_preferences_rel  = relationship("UserContextualPreference",   back_populates="user", uselist=False)
    confidence_profile_rel      = relationship("UserConfidenceProfile",      back_populates="user", uselist=False)
    confidence_history_rel      = relationship("UserConfidenceHistory",      back_populates="user")
    behavior_signals_rel        = relationship("UserBehaviorSignal",         back_populates="user")
    style_evolution_rel         = relationship("UserStyleEvolution",         back_populates="user")
    consent_history_rel         = relationship("UserConsentHistory",         back_populates="user")
    profile_audit_log_rel       = relationship("UserProfileAuditLog",        back_populates="user")
    onboarding_session_rel      = relationship("UserOnboardingSession",      back_populates="user", uselist=False)
    data_export_requests_rel    = relationship("UserDataExportRequest",      back_populates="user")


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = {"extend_existing": True}

    id         = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id    = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    role       = Column(SQLEnum(AppRole), nullable=False, default=AppRole.user)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))


# ── Brand ─────────────────────────────────────────────────────────────────────

class Brand(Base):
    __tablename__ = "brands"
    __table_args__ = {"extend_existing": True}

    id          = Column(String(64), primary_key=True)
    name        = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    logo_url    = Column(String(1024), nullable=True)
    banner_url  = Column(String(1024), nullable=True)
    website     = Column(String(1024), nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False,
                         default=lambda: datetime.now(timezone.utc))
    updated_at  = Column(DateTime(timezone=True), nullable=False,
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    stores   = relationship("Store",   back_populates="brand")
    products = relationship("Product", back_populates="brand")


# ── Store ─────────────────────────────────────────────────────────────────────

class Store(Base):
    __tablename__ = "stores"
    __table_args__ = {"extend_existing": True}

    id          = Column(UUIDType, primary_key=True, default=_new_uuid)
    brand_id    = Column(String(64), ForeignKey("brands.id"), nullable=False, index=True)
    name        = Column(String(255), nullable=False)
    address     = Column(String(512), nullable=False)
    city        = Column(String(128), nullable=False)
    state       = Column(String(128), nullable=True)
    country     = Column(String(128), nullable=False)
    postal_code = Column(String(32), nullable=False)
    phone       = Column(String(64), nullable=True)
    email       = Column(String(255), nullable=True)
    location    = Column(JSON, nullable=True)   # {lat, lng}
    hours       = Column(JSON, nullable=True)   # {day: "9-17"}
    services    = Column(JSON, nullable=True)   # ["BOPIS", "Stylist"]

    brand    = relationship("Brand",   back_populates="stores")
    products = relationship("Product", back_populates="store")


# ── Order ─────────────────────────────────────────────────────────────────────

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = {"extend_existing": True}

    id                 = Column(String(64), primary_key=True)
    order_number       = Column(String(32), unique=True, nullable=False)
    user_id            = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    placed_at          = Column(DateTime(timezone=True), nullable=False,
                                default=lambda: datetime.now(timezone.utc))
    status             = Column(String(32), nullable=False, default="confirmed")
    shipping_address   = Column(JSON, nullable=False)
    payment_method     = Column(String(64), nullable=False, default="card")
    subtotal           = Column(Float, nullable=False)
    shipping           = Column(Float, nullable=False, default=0.0)
    tax                = Column(Float, nullable=False, default=0.0)
    total              = Column(Float, nullable=False)
    tracking_number    = Column(String(128), nullable=True)
    estimated_delivery = Column(String(64), nullable=True)
    # Checkout / payment confirmation flow (draft -> paid)
    delivery_method     = Column(String(32), nullable=True)  # "shipping" | "pickup"
    pickup_store_id     = Column(UUIDType, ForeignKey("stores.id"), nullable=True, index=True)
    pickup_time         = Column(String(64), nullable=True)  # ISO8601 string
    payment_status      = Column(String(32), nullable=False, default="pending")  # pending|success|failed

    user  = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order",
                         cascade="all, delete-orphan")


class PickupRecord(Base):
    """
    Persisted pickup coordination record.
    Created only after payment confirmation.
    """
    __tablename__ = "pickup_records"
    __table_args__ = {"extend_existing": True}

    id            = Column(String(64), primary_key=True)  # pickup-<uuid>
    order_id      = Column(String(64), ForeignKey("orders.id"), nullable=False, unique=True, index=True)
    store_id      = Column(UUIDType, ForeignKey("stores.id"), nullable=False, index=True)
    pickup_time   = Column(String(64), nullable=False)  # ISO8601 string
    status        = Column(String(32), nullable=False, default="scheduled")  # scheduled|updated|cancelled
    created_at    = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = {"extend_existing": True}

    id         = Column(Integer, primary_key=True, autoincrement=True)
    order_id   = Column(String(64), ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(String(64), nullable=True)
    name       = Column(String(255), nullable=False)
    quantity   = Column(Integer, nullable=False, default=1)
    price      = Column(Float, nullable=False)
    image_url  = Column(String(1024), nullable=True)

    order = relationship("Order", back_populates="items")


class ReturnRequest(Base):
    __tablename__ = "return_requests"
    __table_args__ = {"extend_existing": True}

    id           = Column(String(64), primary_key=True)
    order_id     = Column(String(64), nullable=False, index=True)
    user_id      = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    reason       = Column(Text, nullable=False)
    items        = Column(JSON, nullable=True)
    status       = Column(String(32), nullable=False, default="requested")
    requested_at = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime(timezone=True), nullable=True)


# ── Notifications ─────────────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {"extend_existing": True}

    id = Column(String(64), primary_key=True)  # e.g. notif-<uuid>
    receiver_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    # Multi-actor support: actor_type and actor_id for generic reference
    actor_type = Column(SQLEnum(ActorType), nullable=False, default=ActorType.CUSTOMER)
    actor_id = Column(UUIDType, nullable=False, index=True)  # Generic reference to customer_id, store_id, brand_id, etc.
    
    order_id = Column(String(64), nullable=False, index=True)
    store_id = Column(UUIDType, ForeignKey("stores.id"), nullable=True, index=True)
    
    # Notification trigger and content
    trigger = Column(String(64), nullable=False, index=True)  # e.g., 'order_placed', 'payment_confirmed'
    message = Column(Text, nullable=False)
    
    # NOTE: "metadata" is reserved on SQLAlchemy declarative models.
    # Keep the DB column name as "metadata" to match API contract.
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    
    # Read status
    read_status = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Idempotency to prevent duplicated notifications per event.
    idempotency_key = Column(String(128), nullable=False, unique=True, index=True)

    # Delivery tracking (ACK + retry)
    status = Column(String(32), nullable=False, default="QUEUED", index=True)  # QUEUED, SENT, DELIVERED, READ, FAILED
    channel = Column(String(32), nullable=True, index=True)  # push, whatsapp, sms, email, in_app
    delivery_status = Column(String(32), nullable=False, default="pending")  # pending|delivered|failed
    delivery_attempts = Column(Integer, nullable=False, default=0)
    last_emitted_at = Column(DateTime(timezone=True), nullable=True)
    ack_received_at = Column(DateTime(timezone=True), nullable=True)
    
    # DND scheduling: when to send if queued during DND hours
    send_at = Column(DateTime(timezone=True), nullable=True)
    
    # Provider message IDs for webhook callbacks
    provider_message_id = Column(String(255), nullable=True, index=True)


class NotificationPreferences(Base):
    """Granular notification preferences per user with channel toggles, frequency settings, and batch options."""
    __tablename__ = "notification_preferences"
    __table_args__ = {"extend_existing": True}

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    recipient_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    recipient_type = Column(String(20), nullable=False)  # 'customer' | 'store_owner' | 'factory' | 'donor' | 'admin'

    # Channel preferences: {"push": true, "email": true, "sms": true, "whatsapp": true, "in_app": true}
    push_enabled = Column(Boolean, nullable=False, default=True)
    email_enabled = Column(Boolean, nullable=False, default=True)
    sms_enabled = Column(Boolean, nullable=False, default=True)
    whatsapp_enabled = Column(Boolean, nullable=False, default=False)
    in_app_enabled = Column(Boolean, nullable=False, default=True)

    # Category preferences: {"orders": true, "styling": true, "promotions": false, "donor_impact": true}
    categories = Column(JSON, nullable=False, default=lambda: {
        "orders": True,
        "styling": True,
        "promotions": True,
        "donor_impact": True,
    })

    # Language preference: "en" | "ar"
    language = Column(String(2), nullable=False, default="en")

    # DND (Do Not Disturb) hours
    dnd_start = Column(String(5), nullable=True)  # HH:MM format, e.g., "22:00"
    dnd_end = Column(String(5), nullable=True)  # HH:MM format, e.g., "08:00"

    # Legacy fields (kept for backward compatibility)
    channel_preferences = Column(JSON, nullable=False, default=dict)
    frequency_settings = Column(JSON, nullable=False, default=dict)
    notification_types = Column(JSON, nullable=False, default=list)
    batch_options = Column(JSON, nullable=False, default=dict)

    # Versioning & audit
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationship
    user = relationship("User", backref="notification_preferences")


class NotificationQueue(Base):
    """Queue for batch notification delivery (daily digest / weekly summary)."""
    __tablename__ = "notification_queue"
    __table_args__ = {"extend_existing": True}

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    recipient_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    recipient_type = Column(String(20), nullable=False)  # 'customer' | 'store_owner'

    # Batch type: 'daily_digest' | 'weekly_summary'
    batch_type = Column(String(20), nullable=False)

    # Queued notification payload
    notification_payload = Column(JSON, nullable=False)

    # Original notification metadata
    notification_type = Column(String(50), nullable=False)
    channel = Column(String(20), nullable=False)  # 'in_app' | 'email' | 'push'

    # Scheduling
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Status: 'pending' | 'processing' | 'sent' | 'failed'
    status = Column(String(20), nullable=False, default="pending")

    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationship
    user = relationship("User", backref="notification_queue")

# ── Wardrobe ──────────────────────────────────────────────────────────────────

class WardrobeItem(Base):
    __tablename__ = "wardrobe_items"
    __table_args__ = {"extend_existing": True}

    id                = Column(String(64), primary_key=True)
    owner_user_id     = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    name              = Column(String(200), nullable=False)
    brand             = Column(String(100), nullable=True)
    category          = Column(String(64), nullable=False)
    color             = Column(String(50), nullable=True)
    size              = Column(String(20), nullable=True)
    price             = Column(Float, nullable=True)
    currency          = Column(String(10), nullable=False, default="USD")
    image_url         = Column(String(1024), nullable=True)
    tags              = Column(JSON, nullable=True)
    notes             = Column(String(500), nullable=True)
    source_product_id = Column(String(64), nullable=True)
    created_at        = Column(DateTime(timezone=True), nullable=False,
                               default=lambda: datetime.now(timezone.utc))
    updated_at        = Column(DateTime(timezone=True), nullable=False,
                               default=lambda: datetime.now(timezone.utc),
                               onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="wardrobe_items")


# ── Outfit ────────────────────────────────────────────────────────────────────

class Outfit(Base):
    __tablename__ = "outfits"
    __table_args__ = {"extend_existing": True}

    id            = Column(String(64), primary_key=True)
    owner_user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    title         = Column(String(200), nullable=False)
    items         = Column(JSON, nullable=False)
    occasion      = Column(String(128), nullable=True)
    notes         = Column(String(500), nullable=True)
    budget_limit  = Column(Float, nullable=True)
    total_price   = Column(Float, nullable=True)
    currency      = Column(String(10), nullable=False, default="USD")
    share_slug    = Column(String(32), nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="outfits")


# ── Digital Twins ─────────────────────────────────────────────────────────────

class DigitalTwin(Base):
    __tablename__ = "digital_twins"
    __table_args__ = {"extend_existing": True}

    id               = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id          = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    reference_images = Column(JSON, nullable=False, default=list)
    twin_image_url   = Column(Text, nullable=True)
    skin_undertone   = Column(String(50), nullable=True)   # 'warm' | 'cool' | 'neutral'
    environment      = Column(String(50), nullable=False, default="studio")
    status           = Column(String(50), nullable=False, default="pending")
    meta             = Column(JSON, nullable=False, default=dict)
    created_at       = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc))
    updated_at       = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="digital_twins")


class DigitalTwinProfile(Base):
    """Legacy digital-twin profile model (kept for backward-compat)."""
    __tablename__ = "digital_twin_profiles"
    __table_args__ = {"extend_existing": True}

    id            = Column(String(64), primary_key=True)
    owner_user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    status        = Column(String(32), nullable=False, default="pending")
    source_photos = Column(JSON, nullable=True)
    model_id      = Column(String(128), nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))


class DigitalTwinRender(Base):
    __tablename__ = "digital_twin_renders"
    __table_args__ = {"extend_existing": True}

    id                 = Column(String(64), primary_key=True)
    twin_id            = Column(String(64), ForeignKey("digital_twin_profiles.id"),
                                nullable=False, index=True)
    environment        = Column(String(128), nullable=True)
    garment_product_id = Column(String(64), nullable=True)
    image_url          = Column(String(1024), nullable=False)
    created_at         = Column(DateTime(timezone=True), nullable=False,
                                default=lambda: datetime.now(timezone.utc))


# ── QR Scan Sessions ──────────────────────────────────────────────────────────

class QrScanSession(Base):
    __tablename__ = "qr_scan_sessions"
    __table_args__ = {"extend_existing": True}

    id           = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id      = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    product_sku  = Column(String(128), nullable=False)
    store_id     = Column(UUIDType, nullable=True)   # nullable: outside known store
    product_data = Column(JSON, nullable=False, default=dict)
    scanned_at   = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="qr_scans")


# ── Gamification ──────────────────────────────────────────────────────────────

class Quest(Base):
    __tablename__ = "quests"
    __table_args__ = {"extend_existing": True}

    id              = Column(UUIDType, primary_key=True, default=_new_uuid)
    title           = Column(String(255), nullable=False)
    description     = Column(Text, nullable=False)
    type            = Column(String(50), nullable=False, default="daily")
    reward_points   = Column(Integer, nullable=False, default=100)
    reward_badge    = Column(String(100), nullable=True)
    icon            = Column(String(50), nullable=False, default="⭐")
    constraint_json = Column(JSON, nullable=False, default=dict)
    is_active       = Column(Boolean, nullable=False, default=True)
    expires_at      = Column(DateTime(timezone=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), nullable=False,
                             default=lambda: datetime.now(timezone.utc))


class QuestCompletion(Base):
    __tablename__ = "quest_completions"
    __table_args__ = {"extend_existing": True}

    id            = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id       = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    quest_id      = Column(UUIDType, ForeignKey("quests.id"), nullable=False)
    points_earned = Column(Integer, nullable=False, default=0)
    completed_at  = Column(DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="quest_completions")


class UserGamification(Base):
    __tablename__ = "user_gamification"
    __table_args__ = {"extend_existing": True}

    id               = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id          = Column(UUIDType, ForeignKey("users.id"), nullable=False, unique=True)
    total_points     = Column(Integer, nullable=False, default=0)
    confidence_score = Column(Numeric(4, 1), nullable=False, default=0.0)
    level            = Column(Integer, nullable=False, default=1)
    badges           = Column(JSON, nullable=False, default=list)
    current_streak   = Column(Integer, nullable=False, default=0)
    longest_streak   = Column(Integer, nullable=False, default=0)
    updated_at       = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))
    created_at       = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="gamification")


# ── Social Votes (SocialPost defined later in Social Feed section) ────────────

class SocialVote(Base):
    __tablename__ = "social_votes"
    __table_args__ = {"extend_existing": True}

    id            = Column(String(64), primary_key=True)
    # Use UUIDType for post_id to align with SocialPost.id (UUID) and avoid FK type mismatch
    post_id       = Column(UUIDType, ForeignKey("social_posts.id"),
                           nullable=False, index=True)
    voter_user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    value         = Column(String(8), nullable=False)   # "hot" / "cold"
    created_at    = Column(DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc))


# ── Resale ────────────────────────────────────────────────────────────────────

class ResaleListing(Base):
    __tablename__ = "resale_listings"
    __table_args__ = {"extend_existing": True}

    id               = Column(String(64), primary_key=True)
    wardrobe_item_id = Column(String(64), ForeignKey("wardrobe_items.id"),
                              nullable=False, index=True)
    seller_user_id   = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    buyer_user_id    = Column(UUIDType, ForeignKey("users.id"), nullable=True, index=True)
    status           = Column(String(32), nullable=False, default="active")
    price            = Column(Float, nullable=False)
    currency         = Column(String(10), nullable=False, default="USD")
    created_at       = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc))
    sold_at          = Column(DateTime(timezone=True), nullable=True)


# ── Eco Impact ────────────────────────────────────────────────────────────────

class EcoImpactSnapshot(Base):
    __tablename__ = "eco_impact_snapshots"
    __table_args__ = {"extend_existing": True}

    id           = Column(String(64), primary_key=True)
    user_id      = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    period       = Column(String(32), nullable=False)
    co2_saved_kg = Column(Float, nullable=False, default=0.0)
    water_saved_l = Column(Float, nullable=False, default=0.0)
    created_at   = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))


# ── Legacy Style Quests (kept for backward-compat, superseded by Quest) ───────

class StyleQuest(Base):
    __tablename__ = "style_quests"
    __table_args__ = {"extend_existing": True}

    id          = Column(String(64), primary_key=True)
    title       = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    conditions  = Column(JSON, nullable=True)
    starts_at   = Column(DateTime(timezone=True), nullable=False,
                         default=lambda: datetime.now(timezone.utc))
    ends_at     = Column(DateTime(timezone=True), nullable=True)


class QuestSubmission(Base):
    __tablename__ = "quest_submissions"
    __table_args__ = {"extend_existing": True}

    id         = Column(String(64), primary_key=True)
    quest_id   = Column(String(64), ForeignKey("style_quests.id"),
                        nullable=False, index=True)
    user_id    = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    outfit_id  = Column(String(64), nullable=True)
    image_url  = Column(String(1024), nullable=True)
    score      = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))


# ── Stylist Lookbook ──────────────────────────────────────────────────────────

class StylistLookbook(Base):
    __tablename__ = "stylist_lookbooks"
    __table_args__ = {"extend_existing": True}

    id               = Column(String(64), primary_key=True)
    stylist_user_id  = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    title            = Column(String(200), nullable=False)
    description      = Column(Text, nullable=True)
    items            = Column(JSON, nullable=False)
    commission_rate  = Column(Float, nullable=False, default=0.1)
    visibility       = Column(String(16), nullable=False, default="public")
    created_at       = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc))
    updated_at       = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))


# ── QR Mapping ────────────────────────────────────────────────────────────────

class QrMapping(Base):
    __tablename__ = "qr_mappings"
    __table_args__ = {"extend_existing": True}

    id         = Column(String(64), primary_key=True)
    store_id   = Column(UUIDType, ForeignKey("stores.id"), nullable=True, index=True)
    product_id = Column(String(64), nullable=False, index=True)
    qr_code    = Column(String(128), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))


# ── Wishlist ──────────────────────────────────────────────────────────────────

class WishlistItem(Base):
    """An item saved to a user's wishlist (product reference only)."""
    __tablename__ = "wishlist_items"
    __table_args__ = {"extend_existing": True}

    id         = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id    = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    product_id = Column(UUIDType, ForeignKey("products.id"), nullable=False)
    brand      = Column(String(255), nullable=True)
    price      = Column(Float, nullable=True)
    image_url  = Column(String(1024), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="wishlist_items")


# ── Products ──────────────────────────────────────────────────────────────────

class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"extend_existing": True}

    id                  = Column(UUIDType, primary_key=True, default=_new_uuid)
    name                = Column(String(255), nullable=False)
    description         = Column(Text, nullable=True)
    category            = Column(String(100), nullable=False)
    subcategory         = Column(String(100), nullable=True)
    color               = Column(String(50), nullable=True)
    size                = Column(String(20), nullable=True)
    price               = Column(Float, nullable=False)
    # brand_id is String(64) because Brand.id is a string slug (e.g. "brand-luxelayers")
    brand_id            = Column(String(64), ForeignKey("brands.id"), nullable=True)
    store_id            = Column(UUIDType, ForeignKey("stores.id"), nullable=True)
    image_url           = Column(String(1024), nullable=True)
    tags                = Column(JSON, nullable=True)
    style_compatibility = Column(Integer, nullable=True, default=85)
    is_active           = Column(Boolean, nullable=False, default=True)
    created_at          = Column(DateTime(timezone=True), nullable=False,
                                 default=lambda: datetime.now(timezone.utc))

    brand = relationship("Brand", back_populates="products")
    store = relationship("Store", back_populates="products")


# ── Virtual Try-On Sessions ─────────────────────────────────────────────────────

class TryOnSession(Base):
    """Tracks virtual try-on sessions with quality metrics."""
    __tablename__ = "tryon_sessions"
    __table_args__ = {"extend_existing": True}

    id                = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id           = Column(UUIDType, ForeignKey("users.id"), nullable=True, index=True)
    
    # Input data references
    user_image_hash   = Column(String(64), nullable=False)  # SHA-256 hash for privacy
    garment_image_url = Column(String(1024), nullable=False)
    garment_name      = Column(String(255), nullable=False)
    garment_category  = Column(String(50), nullable=False, default="tops")
    
    # Processing options
    fit_type          = Column(String(20), nullable=False, default="regular")
    
    # Results
    result_image_url  = Column(String(1024), nullable=True)  # URL to stored result
    result_image_hash = Column(String(64), nullable=True)    # Hash of result image
    
    # Quality metrics
    quality_score     = Column(Float, nullable=False, default=0.0)
    realism_score     = Column(Float, nullable=True)
    edge_quality      = Column(Float, nullable=True)
    color_consistency = Column(Float, nullable=True)
    proportion_score  = Column(Float, nullable=True)
    artifact_score    = Column(Float, nullable=True)
    
    # Processing details
    pose_detected     = Column(Boolean, nullable=False, default=False)
    processing_mode   = Column(String(30), nullable=False, default="advanced")  # advanced, hf, local
    processing_time_ms = Column(Float, nullable=False, default=0.0)
    
    # Status and metadata
    status            = Column(String(20), nullable=False, default="completed")  # completed, failed
    error_message     = Column(Text, nullable=True)
    warnings          = Column(JSON, nullable=True, default=list)
    
    # Timestamps
    created_at        = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="tryon_sessions")


# ── Outfit Ratings & Engagement ────────────────────────────────────────────────

class OutfitRating(Base):
    """User ratings for outfits (1-5 stars)."""
    __tablename__ = "outfit_ratings"
    __table_args__ = {"extend_existing": True}

    id            = Column(UUIDType, primary_key=True, default=_new_uuid)
    outfit_id     = Column(String(64), ForeignKey("outfits.id"), nullable=False, index=True)
    user_id       = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    rating        = Column(Integer, nullable=False)  # 1-5 stars
    review        = Column(Text, nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="outfit_ratings")


class OutfitLike(Base):
    """User likes/dislikes for outfits."""
    __tablename__ = "outfit_likes"
    __table_args__ = {"extend_existing": True}

    id            = Column(UUIDType, primary_key=True, default=_new_uuid)
    outfit_id     = Column(String(64), ForeignKey("outfits.id"), nullable=False, index=True)
    user_id       = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    is_like       = Column(Boolean, nullable=False, default=True)  # True=like, False=dislike
    created_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="outfit_likes")


class OutfitPopularity(Base):
    """Aggregated popularity metrics for outfits (denormalized for performance)."""
    __tablename__ = "outfit_popularity"
    __table_args__ = {"extend_existing": True}

    id                  = Column(UUIDType, primary_key=True, default=_new_uuid)
    outfit_id           = Column(String(64), ForeignKey("outfits.id"), nullable=False, unique=True, index=True)
    total_ratings       = Column(Integer, nullable=False, default=0)
    rating_sum          = Column(Integer, nullable=False, default=0)
    avg_rating          = Column(Float, nullable=False, default=0.0)
    like_count          = Column(Integer, nullable=False, default=0)
    dislike_count       = Column(Integer, nullable=False, default=0)
    save_count          = Column(Integer, nullable=False, default=0)
    share_count         = Column(Integer, nullable=False, default=0)
    view_count          = Column(Integer, nullable=False, default=0)
    trending_score      = Column(Float, nullable=False, default=0.0)
    popularity_score    = Column(Float, nullable=False, default=0.0)
    style_relevance_score = Column(Float, nullable=False, default=0.0)
    last_activity_at    = Column(DateTime(timezone=True), nullable=False,
                                default=lambda: datetime.now(timezone.utc))
    created_at          = Column(DateTime(timezone=True), nullable=False,
                                default=lambda: datetime.now(timezone.utc))
    updated_at          = Column(DateTime(timezone=True), nullable=False,
                                default=lambda: datetime.now(timezone.utc),
                                onupdate=lambda: datetime.now(timezone.utc))


class OutfitSave(Base):
    """Users saving outfits to their collection."""
    __tablename__ = "outfit_saves"
    __table_args__ = {"extend_existing": True}

    id            = Column(UUIDType, primary_key=True, default=_new_uuid)
    outfit_id     = Column(String(64), ForeignKey("outfits.id"), nullable=False, index=True)
    user_id       = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    collection_name = Column(String(100), nullable=True)  # Optional collection grouping
    created_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="outfit_saves")


class OutfitShare(Base):
    """Track outfit shares for analytics and popularity."""
    __tablename__ = "outfit_shares"
    __table_args__ = {"extend_existing": True}

    id            = Column(UUIDType, primary_key=True, default=_new_uuid)
    outfit_id     = Column(String(64), ForeignKey("outfits.id"), nullable=False, index=True)
    user_id       = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    platform      = Column(String(50), nullable=True)  # e.g., 'instagram', 'twitter', 'copy_link'
    created_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="outfit_shares")


class OutfitRatingRateLimit(Base):
    """Rate limiting for outfit ratings to prevent spam."""
    __tablename__ = "outfit_rating_rate_limits"
    __table_args__ = {"extend_existing": True}

    id            = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id       = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    action_type   = Column(String(32), nullable=False)  # 'rate', 'like', 'save', 'share'
    action_count  = Column(Integer, nullable=False, default=1)
    window_start  = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))


# ── Social Feed ────────────────────────────────────────────────────────────────

class SocialPost(Base):
    """Social feed posts for outfit sharing."""
    __tablename__ = "social_posts"
    __table_args__ = {"extend_existing": True}

    id            = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id       = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    outfit_id     = Column(String(64), ForeignKey("outfits.id"), nullable=True, index=True)
    caption       = Column(Text, nullable=True)
    hashtags      = Column(JSON, nullable=True, default=list)
    image_urls    = Column(JSON, nullable=False, default=list)
    video_url     = Column(String(1024), nullable=True)
    post_type     = Column(String(32), nullable=False, default="outfit")  # outfit, lookbook, story
    visibility    = Column(String(32), nullable=False, default="public")  # public, followers, private
    location      = Column(String(255), nullable=True)
    tags          = Column(JSON, nullable=True, default=list)  # tagged users
    is_featured   = Column(Boolean, nullable=False, default=False)
    is_archived   = Column(Boolean, nullable=False, default=False)
    created_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="social_posts")


class SocialPostStats(Base):
    """Aggregated stats for social posts (denormalized for performance)."""
    __tablename__ = "social_post_stats"
    __table_args__ = {"extend_existing": True}

    id             = Column(UUIDType, primary_key=True, default=_new_uuid)
    post_id        = Column(UUIDType, ForeignKey("social_posts.id"), nullable=False, unique=True, index=True)
    like_count     = Column(Integer, nullable=False, default=0)
    comment_count  = Column(Integer, nullable=False, default=0)
    share_count    = Column(Integer, nullable=False, default=0)
    save_count     = Column(Integer, nullable=False, default=0)
    view_count     = Column(Integer, nullable=False, default=0)
    engagement_rate = Column(Float, nullable=False, default=0.0)
    trending_score = Column(Float, nullable=False, default=0.0)
    last_activity_at = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc))
    created_at     = Column(DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc))
    updated_at     = Column(DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))


class SocialComment(Base):
    """Comments on social posts."""
    __tablename__ = "social_comments"
    __table_args__ = {"extend_existing": True}

    id            = Column(UUIDType, primary_key=True, default=_new_uuid)
    post_id       = Column(UUIDType, ForeignKey("social_posts.id"), nullable=False, index=True)
    user_id       = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    parent_id     = Column(UUIDType, ForeignKey("social_comments.id"), nullable=True, index=True)
    content       = Column(Text, nullable=False)
    mentions      = Column(JSON, nullable=True, default=list)
    is_edited     = Column(Boolean, nullable=False, default=False)
    is_hidden     = Column(Boolean, nullable=False, default=False)
    like_count    = Column(Integer, nullable=False, default=0)
    created_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="social_comments")
    replies = relationship("SocialComment", backref="parent", remote_side=[id])


class SocialLike(Base):
    """Likes on social posts and comments."""
    __tablename__ = "social_likes"
    __table_args__ = {"extend_existing": True}

    id            = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id       = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    entity_type   = Column(String(32), nullable=False)  # 'post', 'comment'
    entity_id     = Column(UUIDType, nullable=False, index=True)
    created_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="social_likes")


class SocialFollow(Base):
    """User follow relationships."""
    __tablename__ = "social_follows"
    __table_args__ = {"extend_existing": True}

    id            = Column(UUIDType, primary_key=True, default=_new_uuid)
    follower_id   = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    following_id  = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    status        = Column(String(32), nullable=False, default="active")  # active, pending, blocked
    created_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))

    follower = relationship("User", foreign_keys=[follower_id], backref="following")
    following = relationship("User", foreign_keys=[following_id], backref="followers")


class SocialStory(Base):
    """Story-style outfit highlights (ephemeral content)."""
    __tablename__ = "social_stories"
    __table_args__ = {"extend_existing": True}

    id            = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id       = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    outfit_id     = Column(String(64), ForeignKey("outfits.id"), nullable=True, index=True)
    media_url     = Column(String(1024), nullable=False)
    media_type    = Column(String(32), nullable=False, default="image")  # image, video
    caption       = Column(String(500), nullable=True)
    hashtags      = Column(JSON, nullable=True, default=list)
    duration_secs = Column(Integer, nullable=True)  # for video stories
    view_count    = Column(Integer, nullable=False, default=0)
    expires_at    = Column(DateTime(timezone=True), nullable=False)
    created_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="social_stories")


class SocialStoryView(Base):
    """Track who viewed stories."""
    __tablename__ = "social_story_views"
    __table_args__ = {"extend_existing": True}

    id            = Column(UUIDType, primary_key=True, default=_new_uuid)
    story_id      = Column(UUIDType, ForeignKey("social_stories.id"), nullable=False, index=True)
    user_id       = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    created_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="story_views")


class SocialReport(Base):
    """Content moderation reports."""
    __tablename__ = "social_reports"
    __table_args__ = {"extend_existing": True}

    id            = Column(UUIDType, primary_key=True, default=_new_uuid)
    reporter_id   = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    entity_type   = Column(String(32), nullable=False)  # 'post', 'comment', 'user', 'story'
    entity_id     = Column(UUIDType, nullable=False, index=True)
    reason        = Column(String(64), nullable=False)  # spam, harassment, inappropriate, etc.
    description   = Column(Text, nullable=True)
    status        = Column(String(32), nullable=False, default="pending")  # pending, reviewed, resolved, dismissed
    reviewed_by   = Column(UUIDType, ForeignKey("users.id"), nullable=True)
    reviewed_at   = Column(DateTime(timezone=True), nullable=True)
    action_taken  = Column(String(255), nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))

    reporter = relationship("User", foreign_keys=[reporter_id], backref="reports_made")
    reviewer = relationship("User", foreign_keys=[reviewed_by], backref="reports_reviewed")


class SocialSave(Base):
    """Users saving posts to their collection."""
    __tablename__ = "social_saves"
    __table_args__ = {"extend_existing": True}

    id              = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id         = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    post_id         = Column(UUIDType, ForeignKey("social_posts.id"), nullable=False, index=True)
    collection_name = Column(String(100), nullable=True)
    created_at      = Column(DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="saved_posts")


class SocialHashtag(Base):
    """Trending hashtags tracking."""
    __tablename__ = "social_hashtags"
    __table_args__ = {"extend_existing": True}

    id              = Column(UUIDType, primary_key=True, default=_new_uuid)
    tag             = Column(String(128), nullable=False, unique=True, index=True)
    post_count      = Column(Integer, nullable=False, default=0)
    trending_score  = Column(Float, nullable=False, default=0.0)
    is_trending     = Column(Boolean, nullable=False, default=False)
    last_used_at    = Column(DateTime(timezone=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc))
    updated_at      = Column(DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))


class SocialFeedCache(Base):
    """Cached personalized feed entries for performance."""
    __tablename__ = "social_feed_cache"
    __table_args__ = {"extend_existing": True}

    id            = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id       = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    post_id       = Column(UUIDType, ForeignKey("social_posts.id"), nullable=False, index=True)
    feed_type     = Column(String(32), nullable=False)  # 'home', 'discover', 'following'
    position      = Column(Integer, nullable=False, default=0)
    score         = Column(Float, nullable=False, default=0.0)
    created_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))
    expires_at    = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", backref="feed_cache")


class SpamDetectionLog(Base):
    """Log for spam detection and prevention."""
    __tablename__ = "spam_detection_logs"
    __table_args__ = {"extend_existing": True}

    id            = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id       = Column(UUIDType, ForeignKey("users.id"), nullable=True, index=True)
    action_type   = Column(String(64), nullable=False)
    content_hash  = Column(String(128), nullable=True, index=True)
    is_spam       = Column(Boolean, nullable=False, default=False)
    confidence    = Column(Float, nullable=False, default=0.0)
    detection_method = Column(String(64), nullable=True)
    extra_data    = Column(JSON, nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))


# ── Influencer Marketplace ─────────────────────────────────────────────────────

class Influencer(Base):
    """Influencer profile with stats and commission settings."""
    __tablename__ = "influencers"
    __table_args__ = {"extend_existing": True}

    id                      = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id                 = Column(UUIDType, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    display_name            = Column(String(100), nullable=False)
    bio                     = Column(Text, nullable=True)
    avatar_url              = Column(String(1024), nullable=True)
    banner_url              = Column(String(1024), nullable=True)
    website_url             = Column(String(1024), nullable=True)
    social_links            = Column(JSON, nullable=False, default=dict)
    tier                    = Column(String(32), nullable=False, default="emerging")
    status                  = Column(String(32), nullable=False, default="pending")
    niches                  = Column(JSON, nullable=False, default=list)
    style_tags              = Column(JSON, nullable=False, default=list)
    followers_count         = Column(Integer, nullable=False, default=0)
    following_count         = Column(Integer, nullable=False, default=0)
    total_outfits           = Column(Integer, nullable=False, default=0)
    total_views             = Column(BigInteger, nullable=False, default=0)
    total_engagement        = Column(BigInteger, nullable=False, default=0)
    default_commission_rate = Column(Numeric(4, 3), nullable=False, default=Decimal("0.100"))
    total_earnings          = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    pending_commissions     = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    paid_commissions        = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    is_verified             = Column(Boolean, nullable=False, default=False)
    verified_at             = Column(DateTime(timezone=True), nullable=True)
    is_featured             = Column(Boolean, nullable=False, default=False)
    featured_until          = Column(DateTime(timezone=True), nullable=True)
    created_at              = Column(DateTime(timezone=True), nullable=False,
                                    default=lambda: datetime.now(timezone.utc))
    updated_at              = Column(DateTime(timezone=True), nullable=False,
                                    default=lambda: datetime.now(timezone.utc),
                                    onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="influencer_profile")


class InfluencerOutfit(Base):
    """Outfit collections created by influencers."""
    __tablename__ = "influencer_outfits"
    __table_args__ = {"extend_existing": True}

    id                = Column(UUIDType, primary_key=True, default=_new_uuid)
    influencer_id     = Column(UUIDType, ForeignKey("influencers.id"), nullable=False, index=True)
    title             = Column(String(200), nullable=False)
    description       = Column(Text, nullable=True)
    image_url         = Column(String(1024), nullable=False)
    thumbnail_url     = Column(String(1024), nullable=True)
    items             = Column(JSON, nullable=False, default=list)
    occasion          = Column(String(128), nullable=True)
    season            = Column(String(64), nullable=True)
    style_tags        = Column(JSON, nullable=False, default=list)
    budget_range      = Column(JSON, nullable=True)
    view_count        = Column(BigInteger, nullable=False, default=0)
    save_count        = Column(Integer, nullable=False, default=0)
    share_count       = Column(Integer, nullable=False, default=0)
    like_count        = Column(Integer, nullable=False, default=0)
    purchase_count    = Column(Integer, nullable=False, default=0)
    commission_rate   = Column(Numeric(4, 3), nullable=False, default=Decimal("0.100"))
    total_commission  = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    status            = Column(String(32), nullable=False, default="draft")
    visibility        = Column(String(32), nullable=False, default="public")
    is_featured       = Column(Boolean, nullable=False, default=False)
    featured_order    = Column(Integer, nullable=True)
    featured_until    = Column(DateTime(timezone=True), nullable=True)
    published_at      = Column(DateTime(timezone=True), nullable=True)
    created_at        = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc))
    updated_at        = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))

    influencer = relationship("Influencer", backref="outfits")


class AffiliateLink(Base):
    """Trackable affiliate links for products."""
    __tablename__ = "affiliate_links"
    __table_args__ = {"extend_existing": True}

    id                      = Column(UUIDType, primary_key=True, default=_new_uuid)
    influencer_id           = Column(UUIDType, ForeignKey("influencers.id"), nullable=False, index=True)
    product_id              = Column(UUIDType, ForeignKey("products.id"), nullable=True)
    slug                    = Column(String(128), nullable=False, unique=True, index=True)
    original_url            = Column(String(2048), nullable=False)
    tracking_code           = Column(String(64), nullable=False, unique=True, index=True)
    commission_rate         = Column(Numeric(4, 3), nullable=False, default=Decimal("0.100"))
    commission_override     = Column(Boolean, nullable=False, default=False)
    click_count             = Column(BigInteger, nullable=False, default=0)
    unique_clicks           = Column(BigInteger, nullable=False, default=0)
    conversion_count        = Column(Integer, nullable=False, default=0)
    total_revenue           = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    total_commission        = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    attribution_window_days = Column(Integer, nullable=False, default=30)
    is_active               = Column(Boolean, nullable=False, default=True)
    expires_at              = Column(DateTime(timezone=True), nullable=True)
    created_at              = Column(DateTime(timezone=True), nullable=False,
                                    default=lambda: datetime.now(timezone.utc))
    updated_at              = Column(DateTime(timezone=True), nullable=False,
                                    default=lambda: datetime.now(timezone.utc),
                                    onupdate=lambda: datetime.now(timezone.utc))

    influencer = relationship("Influencer", backref="affiliate_links")
    product = relationship("Product", backref="affiliate_links")


class CommissionRecord(Base):
    """Commission earnings from affiliate sales."""
    __tablename__ = "commission_records"
    __table_args__ = {"extend_existing": True}

    id                = Column(UUIDType, primary_key=True, default=_new_uuid)
    influencer_id     = Column(UUIDType, ForeignKey("influencers.id"), nullable=False, index=True)
    affiliate_link_id = Column(UUIDType, ForeignKey("affiliate_links.id"), nullable=True)
    order_id          = Column(String(64), nullable=True)
    product_id        = Column(UUIDType, nullable=True)
    product_name      = Column(String(255), nullable=False)
    product_price     = Column(Numeric(12, 2), nullable=False)
    quantity          = Column(Integer, nullable=False, default=1)
    commission_rate   = Column(Numeric(4, 3), nullable=False)
    commission_amount = Column(Numeric(12, 2), nullable=False)
    click_id          = Column(UUIDType, nullable=True)
    first_touch_at    = Column(DateTime(timezone=True), nullable=True)
    last_touch_at     = Column(DateTime(timezone=True), nullable=True)
    attribution_type  = Column(String(32), nullable=False, default="last_click")
    status            = Column(String(32), nullable=False, default="pending")
    approved_at       = Column(DateTime(timezone=True), nullable=True)
    paid_at           = Column(DateTime(timezone=True), nullable=True)
    payout_id         = Column(UUIDType, nullable=True)
    created_at        = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc))
    updated_at        = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))

    influencer = relationship("Influencer", backref="commissions")
    affiliate_link = relationship("AffiliateLink", backref="commissions")


class InfluencerFollower(Base):
    """User follows for influencers."""
    __tablename__ = "influencer_followers"
    __table_args__ = (
        UniqueConstraint('influencer_id', 'follower_user_id', name='uq_influencer_follower'),
        {"extend_existing": True},
    )

    id                   = Column(UUIDType, primary_key=True, default=_new_uuid)
    influencer_id        = Column(UUIDType, ForeignKey("influencers.id"), nullable=False, index=True)
    follower_user_id     = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    notify_new_outfits   = Column(Boolean, nullable=False, default=True)
    notify_recommendations = Column(Boolean, nullable=False, default=True)
    created_at           = Column(DateTime(timezone=True), nullable=False,
                                  default=lambda: datetime.now(timezone.utc))

    influencer = relationship("Influencer", backref="followers_rel")
    follower = relationship("User", backref="following_influencers")


class AffiliateClick(Base):
    """Click tracking for affiliate attribution."""
    __tablename__ = "affiliate_clicks"
    __table_args__ = {"extend_existing": True}

    id                = Column(UUIDType, primary_key=True, default=_new_uuid)
    affiliate_link_id = Column(UUIDType, ForeignKey("affiliate_links.id"), nullable=False, index=True)
    user_id           = Column(UUIDType, ForeignKey("users.id"), nullable=True)
    session_id        = Column(String(128), nullable=True, index=True)
    ip_hash           = Column(String(64), nullable=True)
    user_agent        = Column(String(512), nullable=True)
    referrer          = Column(String(1024), nullable=True)
    device_type       = Column(String(32), nullable=True)
    country           = Column(String(64), nullable=True)
    converted         = Column(Boolean, nullable=False, default=False)
    converted_at      = Column(DateTime(timezone=True), nullable=True)
    order_id          = Column(String(64), nullable=True)
    created_at        = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc))

    affiliate_link = relationship("AffiliateLink", backref="clicks")
    user = relationship("User", backref="affiliate_clicks")


class InfluencerOutfitLike(Base):
    """User likes for influencer outfits."""
    __tablename__ = "influencer_outfit_likes"
    __table_args__ = (
        UniqueConstraint('outfit_id', 'user_id', name='uq_outfit_like'),
        {"extend_existing": True},
    )

    id          = Column(UUIDType, primary_key=True, default=_new_uuid)
    outfit_id   = Column(UUIDType, ForeignKey("influencer_outfits.id"), nullable=False, index=True)
    user_id     = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    created_at  = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    outfit = relationship("InfluencerOutfit", backref="likes_rel")
    user = relationship("User", backref="liked_influencer_outfits")


class InfluencerOutfitSave(Base):
    """User saves for influencer outfits."""
    __tablename__ = "influencer_outfit_saves"
    __table_args__ = (
        UniqueConstraint('outfit_id', 'user_id', name='uq_outfit_save'),
        {"extend_existing": True},
    )

    id              = Column(UUIDType, primary_key=True, default=_new_uuid)
    outfit_id       = Column(UUIDType, ForeignKey("influencer_outfits.id"), nullable=False, index=True)
    user_id         = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    collection_name = Column(String(100), nullable=True, default="Saved")
    created_at      = Column(DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc))

    outfit = relationship("InfluencerOutfit", backref="saves_rel")
    user = relationship("User", backref="saved_influencer_outfits")


class InfluencerRecommendation(Base):
    """Product recommendations by influencers."""
    __tablename__ = "influencer_recommendations"
    __table_args__ = (
        UniqueConstraint('influencer_id', 'product_id', name='uq_influencer_product_rec'),
        {"extend_existing": True},
    )

    id                = Column(UUIDType, primary_key=True, default=_new_uuid)
    influencer_id     = Column(UUIDType, ForeignKey("influencers.id"), nullable=False, index=True)
    product_id        = Column(UUIDType, ForeignKey("products.id"), nullable=False, index=True)
    review_text       = Column(Text, nullable=True)
    rating            = Column(Integer, nullable=True)
    pros              = Column(JSON, nullable=True, default=list)
    cons              = Column(JSON, nullable=True, default=list)
    affiliate_link_id = Column(UUIDType, ForeignKey("affiliate_links.id"), nullable=True)
    helpful_count     = Column(Integer, nullable=False, default=0)
    view_count        = Column(BigInteger, nullable=False, default=0)
    is_featured       = Column(Boolean, nullable=False, default=False)
    status            = Column(String(32), nullable=False, default="active")
    created_at        = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc))
    updated_at        = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))

    influencer = relationship("Influencer", backref="recommendations")
    product = relationship("Product", backref="influencer_recommendations")
    affiliate_link = relationship("AffiliateLink", backref="recommendations")


# ── Sales Analytics ─────────────────────────────────────────────────────────────

class SaleCategory(str, enum.Enum):
    """Product category enum for sales analytics."""
    CLOTHES = "Clothes"
    SHOES = "Shoes"
    ACCESSORIES = "Accessories"
    FULL_OUTFIT = "Full Outfit"


class CustomerSegment(str, enum.Enum):
    """Customer segment enum for sales analytics."""
    NEW_CUSTOMER = "New Customer"
    RETURNING = "Returning"
    VIP = "VIP"
    WHOLESALE = "Wholesale"


class ReturnStatus(str, enum.Enum):
    """Return status enum for sales analytics."""
    COMPLETED = "Completed"
    RETURNED = "Returned"
    PENDING_RETURN = "Pending Return"


class SalesRecord(Base):
    """
    Sales analytics record for store owner dashboard.
    Tracks individual sale transactions with full metadata for filtering and analytics.
    """
    __tablename__ = "sales_records"
    __table_args__ = (
        Index('ix_sales_records_store_date', 'store_id', 'sale_date'),
        Index('ix_sales_records_store_category', 'store_id', 'category'),
        Index('ix_sales_records_store_price', 'store_id', 'price'),
        Index('ix_sales_records_store_margin', 'store_id', 'profit_margin'),
        {"extend_existing": True},
    )

    id               = Column(UUIDType, primary_key=True, default=_new_uuid)
    store_id         = Column(UUIDType, ForeignKey("stores.id"), nullable=False, index=True)
    order_id         = Column(String(64), ForeignKey("orders.id"), nullable=True, index=True)
    order_item_id    = Column(Integer, ForeignKey("order_items.id"), nullable=True)
    
    # Product information
    product_id       = Column(UUIDType, ForeignKey("products.id"), nullable=True, index=True)
    product_name     = Column(String(255), nullable=False)
    sku              = Column(String(128), nullable=True, index=True)
    thumbnail_url    = Column(String(1024), nullable=True)
    category         = Column(SQLEnum(SaleCategory), nullable=False, index=True)
    product_type     = Column(String(100), nullable=True, index=True)
    
    # Sale details
    price            = Column(Numeric(12, 2), nullable=False)
    quantity         = Column(Integer, nullable=False, default=1)
    currency         = Column(String(10), nullable=False, default="EGP")
    
    # Customer information
    customer_id      = Column(UUIDType, ForeignKey("users.id"), nullable=True, index=True)
    customer_name    = Column(String(255), nullable=False)
    customer_email   = Column(String(255), nullable=True)
    customer_phone   = Column(String(64), nullable=True)
    customer_segment = Column(SQLEnum(CustomerSegment), nullable=False, default=CustomerSegment.NEW_CUSTOMER)
    
    # Analytics fields
    sale_date        = Column(DateTime(timezone=True), nullable=False, index=True)
    profit_margin    = Column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))  # 0-100 percentage
    return_status    = Column(SQLEnum(ReturnStatus), nullable=False, default=ReturnStatus.COMPLETED)
    
    # Brand and store info (denormalized for query performance)
    brand_id         = Column(String(64), ForeignKey("brands.id"), nullable=True, index=True)
    brand_name       = Column(String(255), nullable=True)
    store_name       = Column(String(255), nullable=True)
    store_address    = Column(String(512), nullable=True)
    
    # Payment info
    payment_method   = Column(String(64), nullable=True)
    delivery_method  = Column(String(32), nullable=True)  # 'shipping' | 'pickup'
    
    # Timestamps
    created_at       = Column(DateTime(timezone=True), nullable=False,
                             default=lambda: datetime.now(timezone.utc))
    updated_at       = Column(DateTime(timezone=True), nullable=False,
                             default=lambda: datetime.now(timezone.utc),
                             onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    store     = relationship("Store", backref="sales_records")
    order     = relationship("Order", backref="sales_records")
    product   = relationship("Product", backref="sales_records")
    customer  = relationship("User", backref="sales_records")
    brand     = relationship("Brand", backref="sales_records")


# ── CONFIT CARE Donation System ─────────────────────────────────────────────────

class CampaignStatus(str, enum.Enum):
    """Donation campaign status."""
    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"
    cancelled = "cancelled"


class VoucherStatus(str, enum.Enum):
    """Care voucher status."""
    active = "active"
    used = "used"
    expired = "expired"
    cancelled = "cancelled"


class DonationCampaign(Base):
    """
    A donation campaign created by a donor.
    Donors can set up campaigns to help specific beneficiaries shop for clothing.
    """
    __tablename__ = "donation_campaigns"
    __table_args__ = {"extend_existing": True}

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    donor_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)

    # Campaign details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Financial targets
    target_amount = Column(Numeric(12, 2), nullable=False)
    current_amount = Column(Numeric(12, 2), nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="USD")

    # Status
    status = Column(SQLEnum(CampaignStatus), nullable=False, default=CampaignStatus.draft)

    # Dates
    start_date = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    end_date = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    donor = relationship("User", backref="donation_campaigns")
    beneficiaries = relationship("CampaignBeneficiary", back_populates="campaign",
                                 cascade="all, delete-orphan")
    vouchers = relationship("CareVoucher", back_populates="campaign",
                            cascade="all, delete-orphan")


class CampaignBeneficiary(Base):
    """
    A beneficiary of a donation campaign.
    Can shop using vouchers from the campaign.
    """
    __tablename__ = "campaign_beneficiaries"
    __table_args__ = {"extend_existing": True}

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    campaign_id = Column(UUIDType, ForeignKey("donation_campaigns.id"),
                         nullable=False, index=True)

    # Beneficiary details
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(32), nullable=True)

    # Budget control
    budget_cap = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    total_spent = Column(Numeric(12, 2), nullable=False, default=0)

    # Restrictions (e.g., ["clothing", "essentials"])
    restrictions = Column(JSON, nullable=True, default=list)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    campaign = relationship("DonationCampaign", back_populates="beneficiaries")
    vouchers = relationship("CareVoucher", back_populates="beneficiary")


class CareVoucher(Base):
    """
    A voucher that can be used by beneficiaries to shop.
    Vouchers have a code that can be applied at checkout.
    """
    __tablename__ = "care_vouchers"
    __table_args__ = {"extend_existing": True}

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    code = Column(String(32), nullable=False, unique=True, index=True)

    # Campaign and beneficiary
    campaign_id = Column(UUIDType, ForeignKey("donation_campaigns.id"),
                         nullable=False, index=True)
    beneficiary_id = Column(UUIDType, ForeignKey("campaign_beneficiaries.id"),
                            nullable=True, index=True)

    # Value
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    balance = Column(Numeric(12, 2), nullable=False)

    # Status
    status = Column(SQLEnum(VoucherStatus), nullable=False, default=VoucherStatus.active)

    # Dates
    expires_at = Column(DateTime(timezone=True), nullable=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    campaign = relationship("DonationCampaign", back_populates="vouchers")
    beneficiary = relationship("CampaignBeneficiary", back_populates="vouchers")
    transactions = relationship("VoucherTransaction", back_populates="voucher",
                                cascade="all, delete-orphan")


class VoucherTransaction(Base):
    """
    Transaction log for voucher usage.
    Tracks redemptions, refunds, and balance changes.
    """
    __tablename__ = "voucher_transactions"
    __table_args__ = {"extend_existing": True}

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    voucher_id = Column(UUIDType, ForeignKey("care_vouchers.id"),
                        nullable=False, index=True)

    # Transaction details
    transaction_type = Column(String(32), nullable=False)  # redemption, refund, adjustment
    amount = Column(Numeric(12, 2), nullable=False)
    balance_before = Column(Numeric(12, 2), nullable=False)
    balance_after = Column(Numeric(12, 2), nullable=False)

    # Reference
    order_id = Column(String(64), nullable=True, index=True)

    # Metadata
    metadata_json = Column("metadata", JSON, nullable=True, default=dict)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    # Relationships
    voucher = relationship("CareVoucher", back_populates="transactions")


class DonationTransaction(Base):
    """
    Log of all donations to campaigns.
    Tracks when donors add funds to their campaigns.
    """
    __tablename__ = "donation_transactions"
    __table_args__ = {"extend_existing": True}

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    campaign_id = Column(UUIDType, ForeignKey("donation_campaigns.id"),
                         nullable=False, index=True)
    donor_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)

    # Transaction details
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")

    # Payment reference
    payment_method = Column(String(32), nullable=True)
    payment_reference = Column(String(128), nullable=True)

    # Status
    status = Column(String(32), nullable=False, default="completed")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    # Relationships
    campaign = relationship("DonationCampaign", backref="donation_transactions")
    donor = relationship("User", backref="donation_transactions")


# -- Analytics Events (High-volume event tracking) ----------------------------

class AnalyticsEvent(Base):
    """
    High-volume analytics events for dashboards and reporting.
    Supports 10k+ events/min at scale with proper indexing.
    """
    __tablename__ = "analytics_events"
    __table_args__ = (
        Index('ix_analytics_events_user_timestamp', 'user_id', 'timestamp'),
        Index('ix_analytics_events_event_timestamp', 'event_name', 'timestamp'),
        Index('ix_analytics_events_store_timestamp', 'store_id', 'timestamp'),
        {"extend_existing": True},
    )

    id           = Column(UUIDType, primary_key=True, default=_new_uuid)
    event_name   = Column(String(128), nullable=False, index=True)
    user_id      = Column(UUIDType, ForeignKey("users.id"), nullable=True, index=True)
    session_id   = Column(String(128), nullable=True, index=True)
    store_id     = Column(UUIDType, ForeignKey("stores.id"), nullable=True, index=True)
    product_id   = Column(UUIDType, ForeignKey("products.id"), nullable=True)
    properties   = Column(JSON, nullable=False, default=dict)
    timestamp    = Column(DateTime(timezone=True), nullable=False,
                         default=lambda: datetime.now(timezone.utc), index=True)
    device       = Column(String(64), nullable=True)  # ios, android, web
    country      = Column(String(64), nullable=True)  # EG, SA, etc.

    # Relationships
    user    = relationship("User", backref="analytics_events")
    store   = relationship("Store", backref="analytics_events")
    product = relationship("Product", backref="analytics_events")


# -- Daily Analytics Summary Tables (for aggregation) -------------------------

class DailyStoreSummary(Base):
    """Aggregated daily analytics per store for dashboard performance."""
    __tablename__ = "daily_store_summary"
    __table_args__ = (
        Index('ix_daily_store_summary_store_date', 'store_id', 'summary_date', unique=True),
        {"extend_existing": True},
    )

    id                    = Column(UUIDType, primary_key=True, default=_new_uuid)
    store_id              = Column(UUIDType, ForeignKey("stores.id"), nullable=False, index=True)
    summary_date          = Column(DateTime(timezone=True), nullable=False)
    visitors_count        = Column(Integer, nullable=False, default=0)
    purchases_count       = Column(Integer, nullable=False, default=0)
    try_on_count          = Column(Integer, nullable=False, default=0)
    try_on_to_purchase    = Column(Integer, nullable=False, default=0)
    revenue_egp           = Column(Numeric(12, 2), nullable=False, default=0)
    returns_count         = Column(Integer, nullable=False, default=0)
    coupon_redemptions    = Column(Integer, nullable=False, default=0)
    donor_coupon_egp      = Column(Numeric(12, 2), nullable=False, default=0)
    bopis_pickups         = Column(Integer, nullable=False, default=0)
    avg_pickup_time_mins  = Column(Integer, nullable=True)
    return_reasons        = Column(JSON, nullable=False, default=dict)
    top_skus              = Column(JSON, nullable=False, default=list)
    created_at            = Column(DateTime(timezone=True), nullable=False,
                                  default=lambda: datetime.now(timezone.utc))

    store = relationship("Store", backref="daily_summaries")


class DailyBrandSummary(Base):
    """Aggregated daily analytics per brand for dashboard performance."""
    __tablename__ = "daily_brand_summary"
    __table_args__ = (
        Index('ix_daily_brand_summary_brand_date', 'brand_id', 'summary_date', unique=True),
        {"extend_existing": True},
    )

    id                     = Column(UUIDType, primary_key=True, default=_new_uuid)
    brand_id               = Column(String(64), ForeignKey("brands.id"), nullable=False, index=True)
    summary_date           = Column(DateTime(timezone=True), nullable=False)
    products_sold          = Column(Integer, nullable=False, default=0)
    revenue_egp            = Column(Numeric(12, 2), nullable=False, default=0)
    midway_rejections      = Column(Integer, nullable=False, default=0)
    rejection_reasons      = Column(JSON, nullable=False, default=dict)
    outfit_appearances     = Column(Integer, nullable=False, default=0)
    outfit_purchases       = Column(Integer, nullable=False, default=0)
    returns_count          = Column(Integer, nullable=False, default=0)
    regional_sales         = Column(JSON, nullable=False, default=dict)  # {city: count}
    sku_breakdown          = Column(JSON, nullable=False, default=list)
    created_at             = Column(DateTime(timezone=True), nullable=False,
                                   default=lambda: datetime.now(timezone.utc))

    brand = relationship("Brand", backref="daily_summaries")


class DailyUserSummary(Base):
    """Aggregated daily analytics per user for personal insights."""
    __tablename__ = "daily_user_summary"
    __table_args__ = (
        Index('ix_daily_user_summary_user_date', 'user_id', 'summary_date', unique=True),
        {"extend_existing": True},
    )

    id                  = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id             = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    summary_date        = Column(DateTime(timezone=True), nullable=False)
    outfits_saved       = Column(Integer, nullable=False, default=0)
    try_on_sessions     = Column(Integer, nullable=False, default=0)
    coupons_used        = Column(Integer, nullable=False, default=0)
    coupon_savings_egp  = Column(Numeric(12, 2), nullable=False, default=0)
    stores_visited      = Column(JSON, nullable=False, default=list)
    created_at          = Column(DateTime(timezone=True), nullable=False,
                                default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="daily_summaries")


# Payment ledger + invoices (Stripe / Paymob / PayPal) -- register models with same Base metadata
from database.payment_platform_models import Payment, PaymentTransaction, PaymentEvent, Invoice  # noqa: E402,F401
