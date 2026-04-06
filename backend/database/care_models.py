"""
CONFIT Backend - CONFIT CARE Database Models
============================================
Enhanced models for the charitable giving feature including:
- CareSession: Beneficiary session management with device fingerprinting
- CareAnalytics: Campaign performance metrics
- CareAuditLog: Complete audit trail for compliance
- CareOrder: Orders placed through CARE vouchers
"""

import enum
import os
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

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
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from database.base import Base, JSONType  # Use JSONType for SQLite/PostgreSQL compatibility

# UUID column helper
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
    return str(uuid.uuid4())


def _new_secure_token() -> str:
    """Generate a cryptographically secure 32-character token."""
    import secrets
    import string
    chars = string.ascii_uppercase + string.digits
    # Remove ambiguous characters
    chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("L", "")
    return ''.join(secrets.choice(chars) for _ in range(32))


# =============================================================================
# Enums
# =============================================================================

class CareCampaignType(str, enum.Enum):
    """Types of care campaigns."""
    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"
    SEASONAL = "seasonal"
    CORPORATE = "corporate"
    EMERGENCY = "emergency"


class CareCampaignStatus(str, enum.Enum):
    """Care campaign status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class CareVoucherStatus(str, enum.Enum):
    """Care voucher status."""
    PENDING = "pending"  # Created but not yet sent
    SENT = "sent"  # Invitation sent to beneficiary
    ACCESSED = "accessed"  # Beneficiary has accessed
    ACTIVE = "active"  # Currently shopping
    COMPLETED = "completed"  # Used fully
    PARTIALLY_USED = "partially_used"  # Some balance remaining
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class CareSessionStatus(str, enum.Enum):
    """Care session status."""
    PENDING = "pending"
    OTP_SENT = "otp_sent"
    OTP_VERIFIED = "otp_verified"
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    LOCKED = "locked"  # Too many failed attempts


class CareOrderStatus(str, enum.Enum):
    """Care order status."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


# =============================================================================
# Care Campaign Model (Enhanced)
# =============================================================================

class CareCampaign(Base):
    """
    Enhanced donation campaign model.
    Supports individual, organization, and seasonal giving campaigns.
    """
    __tablename__ = "care_campaigns"
    __table_args__ = (
        Index('ix_care_campaigns_donor_status', 'donor_id', 'status'),
        Index('ix_care_campaigns_dates', 'start_date', 'end_date'),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    donor_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    # Campaign details
    campaign_name = Column(String(255), nullable=False)
    campaign_type = Column(SQLEnum(CareCampaignType), nullable=False, default=CareCampaignType.INDIVIDUAL)
    description = Column(Text, nullable=True)
    
    # Financial configuration
    budget_per_person = Column(Numeric(12, 2), nullable=False)
    total_beneficiaries = Column(Integer, nullable=False, default=0)
    total_budget_allocated = Column(Numeric(12, 2), nullable=False, default=0)
    total_budget_used = Column(Numeric(12, 2), nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="EGP")
    
    # Restrictions and preferences
    allowed_categories = Column(JSON, nullable=True, default=list)  # Product categories allowed
    excluded_brands = Column(JSON, nullable=True, default=list)
    occasion_filter = Column(String(100), nullable=True)  # e.g., "work", "casual"
    
    # Status
    status = Column(SQLEnum(CareCampaignStatus), nullable=False, default=CareCampaignStatus.DRAFT)
    
    # Dates
    start_date = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    end_date = Column(DateTime(timezone=True), nullable=True)
    voucher_expiry_days = Column(Integer, nullable=False, default=30)
    
    # Messaging
    invitation_message = Column(Text, nullable=True)  # Custom message for beneficiaries
    confirmation_message = Column(Text, nullable=True)  # Message after order completion
    
    # Metadata
    metadata_json = Column("metadata", JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    donor = relationship("User", backref="care_campaigns")
    beneficiaries = relationship("CareBeneficiary", back_populates="campaign", cascade="all, delete-orphan")
    vouchers = relationship("CareVoucher", back_populates="campaign", cascade="all, delete-orphan")
    analytics = relationship("CareAnalytics", back_populates="campaign", uselist=False)
    audit_logs = relationship("CareAuditLog", back_populates="campaign")


# =============================================================================
# Care Beneficiary Model
# =============================================================================

class CareBeneficiary(Base):
    """
    Beneficiary of a care campaign.
    Can shop using vouchers from the campaign.
    """
    __tablename__ = "care_beneficiaries"
    __table_args__ = (
        Index('ix_care_beneficiaries_campaign_phone', 'campaign_id', 'phone'),
        Index('ix_care_beneficiaries_campaign_email', 'campaign_id', 'email'),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    campaign_id = Column(UUIDType, ForeignKey("care_campaigns.id"), nullable=False, index=True)
    
    # Beneficiary details
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(32), nullable=True)
    
    # Preferences
    age_group = Column(String(20), nullable=True)  # "18-25", "26-35", etc.
    size_preference = Column(String(20), nullable=True)
    style_preference = Column(JSON, nullable=True, default=list)
    occasion_needs = Column(JSON, nullable=True, default=list)  # ["work", "casual"]
    
    # Budget tracking
    budget_allocated = Column(Numeric(12, 2), nullable=False)
    budget_used = Column(Numeric(12, 2), nullable=False, default=0)
    budget_remaining = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="EGP")
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    invitation_sent_at = Column(DateTime(timezone=True), nullable=True)
    first_access_at = Column(DateTime(timezone=True), nullable=True)
    last_access_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    campaign = relationship("CareCampaign", back_populates="beneficiaries")
    voucher = relationship("CareVoucher", back_populates="beneficiary", uselist=False, cascade="all, delete-orphan")
    orders = relationship("CareOrder", back_populates="beneficiary")


# =============================================================================
# Care Voucher Model (Enhanced)
# =============================================================================

class CareVoucher(Base):
    """
    Enhanced voucher model for beneficiary shopping.
    Includes secure token generation and comprehensive tracking.
    """
    __tablename__ = "care_vouchers"
    __table_args__ = (
        Index('ix_care_vouchers_token', 'voucher_token', unique=True),
        Index('ix_care_vouchers_campaign_status', 'campaign_id', 'status'),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    campaign_id = Column(UUIDType, ForeignKey("care_campaigns.id"), nullable=False, index=True)
    beneficiary_id = Column(UUIDType, ForeignKey("care_beneficiaries.id"), nullable=True, index=True)
    
    # Secure voucher token (32-character cryptographically secure)
    voucher_token = Column(String(32), nullable=False, unique=True, index=True, default=_new_secure_token)
    
    # Budget
    budget_allocated = Column(Numeric(12, 2), nullable=False)
    budget_used = Column(Numeric(12, 2), nullable=False, default=0)
    budget_remaining = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="EGP")
    
    # Status
    status = Column(SQLEnum(CareVoucherStatus), nullable=False, default=CareVoucherStatus.PENDING)
    
    # Dates
    issued_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)  # When invitation was sent
    accessed_at = Column(DateTime(timezone=True), nullable=True)  # First access
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    campaign = relationship("CareCampaign", back_populates="vouchers")
    beneficiary = relationship("CareBeneficiary", back_populates="voucher")
    sessions = relationship("CareSession", back_populates="voucher", cascade="all, delete-orphan")
    transactions = relationship("CareVoucherTransaction", back_populates="voucher")
    orders = relationship("CareOrder", back_populates="voucher")


# =============================================================================
# Care Session Model (Security & Device Fingerprinting)
# =============================================================================

class CareSession(Base):
    """
    Beneficiary session with security features.
    Includes device fingerprinting, OTP verification, and session management.
    """
    __tablename__ = "care_sessions"
    __table_args__ = (
        Index('ix_care_sessions_token', 'session_token', unique=True),
        Index('ix_care_sessions_voucher_status', 'voucher_id', 'status'),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    voucher_id = Column(UUIDType, ForeignKey("care_vouchers.id"), nullable=False, index=True)
    
    # Session token
    session_token = Column(String(64), nullable=False, unique=True, index=True)
    
    # Device fingerprinting (for security)
    device_fingerprint = Column(String(255), nullable=True)  # Hash of IP + User-Agent + other identifiers
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(512), nullable=True)
    device_type = Column(String(32), nullable=True)  # mobile, tablet, desktop
    browser = Column(String(64), nullable=True)
    os = Column(String(64), nullable=True)
    
    # OTP verification
    otp_code = Column(String(6), nullable=True)  # Hashed OTP code
    otp_secret = Column(String(32), nullable=True)  # Secret for OTP generation
    otp_sent_at = Column(DateTime(timezone=True), nullable=True)
    otp_attempts = Column(Integer, nullable=False, default=0)
    otp_verified = Column(Boolean, nullable=False, default=False)
    otp_verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Session management
    status = Column(SQLEnum(CareSessionStatus), nullable=False, default=CareSessionStatus.PENDING)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Shopping context (persisted during session)
    cart_data = Column(JSON, nullable=True, default=dict)
    current_filters = Column(JSON, nullable=True, default=dict)
    viewed_products = Column(JSON, nullable=True, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    voucher = relationship("CareVoucher", back_populates="sessions")
    audit_logs = relationship("CareAuditLog", back_populates="session")


# =============================================================================
# Care Voucher Transaction Model
# =============================================================================

class CareVoucherTransaction(Base):
    """
    Transaction log for voucher usage.
    Tracks all balance changes with full audit trail.
    """
    __tablename__ = "care_voucher_transactions"
    __table_args__ = (
        Index('ix_care_voucher_transactions_voucher_created', 'voucher_id', 'created_at'),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    voucher_id = Column(UUIDType, ForeignKey("care_vouchers.id"), nullable=False, index=True)
    
    # Transaction details
    transaction_type = Column(String(32), nullable=False)  # allocation, redemption, refund, adjustment, expiry
    amount = Column(Numeric(12, 2), nullable=False)
    balance_before = Column(Numeric(12, 2), nullable=False)
    balance_after = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="EGP")
    
    # Reference
    order_id = Column(UUIDType, ForeignKey("care_orders.id"), nullable=True)
    reference = Column(String(64), nullable=True)  # External reference
    
    # Metadata
    description = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True, default=dict)
    
    # Actor (who initiated the transaction)
    actor_type = Column(String(32), nullable=True)  # system, donor, beneficiary, admin
    actor_id = Column(UUIDType, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    voucher = relationship("CareVoucher", back_populates="transactions")


# =============================================================================
# Care Order Model
# =============================================================================

class CareOrder(Base):
    """
    Order placed through a care voucher.
    Links to regular order system with additional CARE-specific data.
    """
    __tablename__ = "care_orders"
    __table_args__ = (
        Index('ix_care_orders_voucher_status', 'voucher_id', 'status'),
        Index('ix_care_orders_beneficiary', 'beneficiary_id'),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    voucher_id = Column(UUIDType, ForeignKey("care_vouchers.id"), nullable=False, index=True)
    beneficiary_id = Column(UUIDType, ForeignKey("care_beneficiaries.id"), nullable=False, index=True)
    order_id = Column(String(64), ForeignKey("orders.id"), nullable=False, unique=True)
    
    # Financial details
    subtotal = Column(Numeric(12, 2), nullable=False)
    shipping_cost = Column(Numeric(12, 2), nullable=False, default=0)
    total_amount = Column(Numeric(12, 2), nullable=False)
    amount_from_voucher = Column(Numeric(12, 2), nullable=False)  # How much was paid from voucher
    currency = Column(String(10), nullable=False, default="EGP")
    
    # Status
    status = Column(SQLEnum(CareOrderStatus), nullable=False, default=CareOrderStatus.PENDING)
    
    # Delivery details (hidden prices for beneficiary)
    delivery_method = Column(String(32), nullable=True)  # shipping, pickup
    shipping_address = Column(JSON, nullable=True)
    pickup_store_id = Column(UUIDType, nullable=True)
    
    # Items summary (for quick reference)
    items_count = Column(Integer, nullable=False, default=0)
    items_summary = Column(JSON, nullable=True, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    voucher = relationship("CareVoucher", back_populates="orders")
    beneficiary = relationship("CareBeneficiary", back_populates="orders")
    transaction = relationship("CareVoucherTransaction", backref="care_order", uselist=False)


# =============================================================================
# Care Analytics Model
# =============================================================================

class CareAnalytics(Base):
    """
    Aggregated analytics for a care campaign.
    Updated in real-time as beneficiaries shop.
    """
    __tablename__ = "care_analytics"
    __table_args__ = (
        Index('ix_care_analytics_campaign', 'campaign_id', unique=True),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    campaign_id = Column(UUIDType, ForeignKey("care_campaigns.id"), nullable=False, unique=True, index=True)
    
    # Voucher metrics
    total_vouchers_created = Column(Integer, nullable=False, default=0)
    vouchers_sent = Column(Integer, nullable=False, default=0)
    vouchers_accessed = Column(Integer, nullable=False, default=0)
    vouchers_completed = Column(Integer, nullable=False, default=0)
    vouchers_expired = Column(Integer, nullable=False, default=0)
    
    # Financial metrics
    total_budget_allocated = Column(Numeric(12, 2), nullable=False, default=0)
    total_budget_used = Column(Numeric(12, 2), nullable=False, default=0)
    average_order_value = Column(Numeric(12, 2), nullable=True)
    average_spend_per_beneficiary = Column(Numeric(12, 2), nullable=True)
    
    # Product metrics
    total_products_purchased = Column(Integer, nullable=False, default=0)
    most_purchased_categories = Column(JSON, nullable=True, default=list)
    most_purchased_brands = Column(JSON, nullable=True, default=list)
    category_distribution = Column(JSON, nullable=True, default=dict)
    
    # Engagement metrics
    engagement_rate = Column(Numeric(5, 2), nullable=False, default=0)  # % of beneficiaries who accessed
    completion_rate = Column(Numeric(5, 2), nullable=False, default=0)  # % who completed shopping
    average_session_duration_minutes = Column(Numeric(8, 2), nullable=True)
    total_sessions = Column(Integer, nullable=False, default=0)
    
    # Time metrics
    average_time_to_first_access_hours = Column(Numeric(8, 2), nullable=True)
    average_time_to_completion_hours = Column(Numeric(8, 2), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    campaign = relationship("CareCampaign", back_populates="analytics")


# =============================================================================
# Care Audit Log Model
# =============================================================================

class CareAuditLog(Base):
    """
    Comprehensive audit log for all CARE-related actions.
    Essential for compliance, transparency, and donor reporting.
    """
    __tablename__ = "care_audit_log"
    __table_args__ = (
        Index('ix_care_audit_log_campaign_timestamp', 'campaign_id', 'timestamp'),
        Index('ix_care_audit_log_voucher', 'voucher_id'),
        Index('ix_care_audit_log_actor', 'actor_id'),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    
    # References
    campaign_id = Column(UUIDType, ForeignKey("care_campaigns.id"), nullable=True, index=True)
    voucher_id = Column(UUIDType, ForeignKey("care_vouchers.id"), nullable=True, index=True)
    session_id = Column(UUIDType, ForeignKey("care_sessions.id"), nullable=True, index=True)
    beneficiary_id = Column(UUIDType, ForeignKey("care_beneficiaries.id"), nullable=True)
    order_id = Column(UUIDType, nullable=True)
    
    # Action details
    action = Column(String(100), nullable=False)  # e.g., "voucher_created", "otp_sent", "order_placed"
    action_category = Column(String(32), nullable=False)  # campaign, voucher, session, order, payment
    description = Column(Text, nullable=True)
    
    # Actor information
    actor_type = Column(String(32), nullable=False)  # donor, beneficiary, system, admin
    actor_id = Column(UUIDType, nullable=True, index=True)
    actor_ip = Column(String(45), nullable=True)
    actor_user_agent = Column(String(512), nullable=True)
    
    # State change
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    
    # Additional details
    details = Column(JSONType, nullable=True, default=dict)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationships
    campaign = relationship("CareCampaign", back_populates="audit_logs")
    session = relationship("CareSession", back_populates="audit_logs")


# =============================================================================
# Helper Functions
# =============================================================================

def generate_device_fingerprint(ip_address: str, user_agent: str, additional_data: Dict[str, Any] = None) -> str:
    """
    Generate a device fingerprint for security purposes.
    Combines IP, user agent, and additional data into a hash.
    """
    fingerprint_data = f"{ip_address}|{user_agent}"
    if additional_data:
        fingerprint_data += f"|{str(additional_data)}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:64]


def generate_otp_secret() -> str:
    """Generate a secure OTP secret."""
    import secrets
    return secrets.token_hex(16)


def hash_otp(otp_code: str, secret: str) -> str:
    """Hash an OTP code with the secret for storage."""
    return hashlib.sha256(f"{otp_code}{secret}".encode()).hexdigest()


def generate_session_token() -> str:
    """Generate a secure session token."""
    import secrets
    return secrets.token_urlsafe(48)


def calculate_voucher_expiry(campaign: CareCampaign) -> datetime:
    """Calculate voucher expiry date based on campaign settings."""
    return datetime.now(timezone.utc) + timedelta(days=campaign.voucher_expiry_days)


# =============================================================================
# Audit Action Constants
# =============================================================================

class AuditAction:
    """Constants for audit log actions."""
    # Campaign actions
    CAMPAIGN_CREATED = "campaign_created"
    CAMPAIGN_UPDATED = "campaign_updated"
    CAMPAIGN_ACTIVATED = "campaign_activated"
    CAMPAIGN_PAUSED = "campaign_paused"
    CAMPAIGN_COMPLETED = "campaign_completed"
    CAMPAIGN_CANCELLED = "campaign_cancelled"
    
    # Beneficiary actions
    BENEFICIARY_ADDED = "beneficiary_added"
    BENEFICIARY_REMOVED = "beneficiary_removed"
    BENEFICIARY_UPDATED = "beneficiary_updated"
    
    # Voucher actions
    VOUCHER_CREATED = "voucher_created"
    VOUCHER_SENT = "voucher_sent"
    VOUCHER_ACCESSED = "voucher_accessed"
    VOUCHER_EXPIRED = "voucher_expired"
    VOUCHER_CANCELLED = "voucher_cancelled"
    
    # Session actions
    SESSION_CREATED = "session_created"
    OTP_SENT = "otp_sent"
    OTP_VERIFIED = "otp_verified"
    OTP_FAILED = "otp_failed"
    SESSION_EXPIRED = "session_expired"
    SESSION_LOCKED = "session_locked"
    
    # Order actions
    ORDER_STARTED = "order_started"
    ORDER_PLACED = "order_placed"
    ORDER_CONFIRMED = "order_confirmed"
    ORDER_SHIPPED = "order_shipped"
    ORDER_DELIVERED = "order_delivered"
    ORDER_CANCELLED = "order_cancelled"
    
    # Payment actions
    BUDGET_ALLOCATED = "budget_allocated"
    BUDGET_USED = "budget_used"
    BUDGET_REFUNDED = "budget_refunded"
