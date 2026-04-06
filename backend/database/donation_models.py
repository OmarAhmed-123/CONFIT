"""
CONFIT Backend - Donation System Database Models
=================================================
Production-grade schema for donations, donor credits, and redemptions.
Supports secure coupon generation, balance tracking, and expiration logic.
"""

import enum
import os
import uuid
from datetime import datetime, timezone, timedelta
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
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from database.base import Base

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


class DonationStatus(str, enum.Enum):
    """Donation payment status."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class DonorCreditStatus(str, enum.Enum):
    """Donor credit status."""
    ACTIVE = "active"
    DEPLETED = "depleted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Donation(Base):
    """
    Donation record with payment tracking.
    
    Tracks user donations and payment verification.
    Each donation generates a corresponding donor credit.
    """
    __tablename__ = "donations"
    __table_args__ = (
        Index("ix_donations_user_id", "user_id"),
        Index("ix_donations_status", "status"),
        Index("ix_donations_created_at", "created_at"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    
    # Donation amount
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    
    # Payment tracking
    payment_method = Column(String(32), nullable=False, default="card")
    payment_provider = Column(String(32), nullable=True)  # stripe, paymob, paypal
    transaction_id = Column(String(128), nullable=True, unique=True)
    payment_intent_id = Column(String(128), nullable=True)
    payment_metadata = Column(JSON, nullable=True)
    
    # Status
    status = Column(
        SQLEnum(DonationStatus),
        nullable=False,
        default=DonationStatus.PENDING
    )
    
    # Fraud prevention
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    risk_score = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    donor_credit = relationship(
        "DonorCredit",
        back_populates="donation",
        uselist=False,
        cascade="all, delete-orphan"
    )

    @hybrid_property
    def is_completed(self) -> bool:
        return self.status == DonationStatus.COMPLETED


class DonorCredit(Base):
    """
    Donor credit/wallet balance.
    
    Generated automatically after successful donation.
    Tracks remaining balance and expiration.
    """
    __tablename__ = "donor_credits"
    __table_args__ = (
        Index("ix_donor_credits_user_id", "user_id"),
        Index("ix_donor_credits_status", "status"),
        Index("ix_donor_credits_expires_at", "expires_at"),
        CheckConstraint("remaining_credit >= 0", name="ck_remaining_credit_non_negative"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    donation_id = Column(UUIDType, ForeignKey("donations.id"), nullable=False, unique=True)
    
    # Credit amounts
    total_credit = Column(Numeric(12, 2), nullable=False)
    remaining_credit = Column(Numeric(12, 2), nullable=False)
    
    # Coupon code (unique, secure)
    coupon_code = Column(String(24), nullable=False, unique=True)
    coupon_hash = Column(String(64), nullable=True)  # For additional security
    
    # Status and expiration
    status = Column(
        SQLEnum(DonorCreditStatus),
        nullable=False,
        default=DonorCreditStatus.ACTIVE
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    notes = Column(Text, nullable=True)
    credit_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    donation = relationship("Donation", back_populates="donor_credit")
    redemptions = relationship(
        "DonorRedemption",
        back_populates="credit",
        cascade="all, delete-orphan"
    )

    @hybrid_property
    def is_active(self) -> bool:
        if self.status != DonorCreditStatus.ACTIVE:
            return False
        if self.remaining_credit <= 0:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    @hybrid_property
    def used_credit(self) -> Decimal:
        return self.total_credit - self.remaining_credit


class DonorRedemption(Base):
    """
    Redemption record for donor credits.
    
    Tracks each purchase where donor credit was used.
    Supports partial redemptions and balance tracking.
    """
    __tablename__ = "donor_redemptions"
    __table_args__ = (
        Index("ix_donor_redemptions_credit_id", "credit_id"),
        Index("ix_donor_redemptions_order_id", "order_id"),
        Index("ix_donor_redemptions_user_id", "user_id"),
        Index("ix_donor_redemptions_created_at", "created_at"),
        CheckConstraint("amount_used > 0", name="ck_amount_used_positive"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    credit_id = Column(UUIDType, ForeignKey("donor_credits.id"), nullable=False)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    order_id = Column(String(64), ForeignKey("orders.id"), nullable=True)
    
    # Redemption details
    amount_used = Column(Numeric(12, 2), nullable=False)
    balance_before = Column(Numeric(12, 2), nullable=False)
    balance_after = Column(Numeric(12, 2), nullable=False)
    
    # Product details (for tracking)
    product_id = Column(String(64), nullable=True)
    product_name = Column(String(255), nullable=True)
    
    # Metadata
    redemption_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    credit = relationship("DonorCredit", back_populates="redemptions")


class DonationConfig(Base):
    """
    Configuration for donation system.
    
    Stores min/max amounts, expiration settings, etc.
    """
    __tablename__ = "donation_config"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Amount limits
    min_donation_amount = Column(Numeric(12, 2), nullable=False, default=1.00)
    max_donation_amount = Column(Numeric(12, 2), nullable=False, default=10000.00)
    
    # Preset amounts (JSON array)
    preset_amounts = Column(JSON, nullable=False, default=lambda: [10, 25, 50, 100])
    
    # Credit expiration (days from creation, null = no expiration)
    default_expiry_days = Column(Integer, nullable=True, default=365)
    
    # Feature flags
    enable_custom_amounts = Column(Boolean, nullable=False, default=True)
    enable_recurring = Column(Boolean, nullable=False, default=False)
    
    # Messaging
    hero_title = Column(String(255), nullable=True)
    hero_subtitle = Column(Text, nullable=True)
    benefits_text = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    updated_by = Column(UUIDType, nullable=True)


# # -------------------------------------------------------------------------
# DONOR TIER SYSTEM (CONFIT Spec)
# # -------------------------------------------------------------------------

class DonorTier(str, enum.Enum):
    """Donor tier levels based on total donated amount (EGP)."""
    SUPPORTER = "supporter"      # 500+ EGP
    STYLIST = "stylist"          # 2,500+ EGP
    PATRON = "patron"            # 10,000+ EGP
    ICON = "icon"                # 50,000+ EGP


class CouponType(str, enum.Enum):
    """Coupon discount types."""
    PERCENTAGE = "percentage"    # Percentage discount
    FIXED = "fixed"              # Fixed amount discount
    FREE_SHIPPING = "free_shipping"  # Free shipping


class CouponVisibility(str, enum.Enum):
    """Coupon visibility rules."""
    PUBLIC = "public"            # Visible to all eligible users
    CATEGORY = "category"        # Visible to specific user categories
    HIDDEN = "hidden"            # Only via direct code entry


class Donor(Base):
    """
    Donor profile with tier tracking and public display info.
    
    Links user to donation activity with optional anonymity.
    """
    __tablename__ = "donors"
    __table_args__ = (
        Index("ix_donors_user_id", "user_id", unique=True),
        Index("ix_donors_tier", "tier"),
        Index("ix_donors_is_anonymous", "is_anonymous"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Public display info (shown on Impact Wall if not anonymous)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(String(1024), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Tier tracking
    tier = Column(
        SQLEnum(DonorTier),
        nullable=False,
        default=DonorTier.SUPPORTER
    )
    total_donated_piastres = Column(BigInteger, nullable=False, default=0)  # In piastres (1 EGP = 100 piastres)
    people_helped = Column(Integer, nullable=False, default=0)
    
    # Privacy settings
    is_anonymous = Column(Boolean, nullable=False, default=False)
    is_verified = Column(Boolean, nullable=False, default=False)
    is_tax_deductible_eligible = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    coupons = relationship("Coupon", back_populates="donor", cascade="all, delete-orphan")
    donations = relationship("DonationRecord", back_populates="donor", cascade="all, delete-orphan")


class DonationRecord(Base):
    """
    Donation record with payment tracking (CONFIT spec version).
    
    Stores donation details with amount in piastres for precision.
    """
    __tablename__ = "donation_records"
    __table_args__ = (
        Index("ix_donation_records_donor_id", "donor_id"),
        Index("ix_donation_records_payment_id", "payment_id"),
        Index("ix_donation_records_created_at", "created_at"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    donor_id = Column(UUIDType, ForeignKey("donors.id"), nullable=False)
    payment_id = Column(String(64), ForeignKey("payments.id"), nullable=True)
    
    # Amount in piastres (integer for precision, 1 EGP = 100 piastres)
    amount_piastres = Column(BigInteger, nullable=False)
    currency = Column(String(3), nullable=False, default="EGP")
    
    # Optional message from donor
    message = Column(Text, nullable=True)
    
    # Tax receipt
    tax_receipt_url = Column(String(1024), nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    donor = relationship("Donor", back_populates="donations")


class Coupon(Base):
    """
    Discount coupon generated from donations.
    
    Supports various discount types with visibility rules and usage limits.
    """
    __tablename__ = "coupons"
    __table_args__ = (
        Index("ix_coupons_code", "code", unique=True),
        Index("ix_coupons_donor_id", "donor_id"),
        Index("ix_coupons_visibility", "visibility"),
        Index("ix_coupons_valid_from", "valid_from"),
        Index("ix_coupons_is_active", "is_active"),
        CheckConstraint("value > 0", name="ck_coupon_value_positive"),
        CheckConstraint("code ~ '^[A-Z0-9]{4,20}$'", name="ck_coupon_code_format"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    code = Column(String(20), nullable=False, unique=True)
    donor_id = Column(UUIDType, ForeignKey("donors.id"), nullable=False)
    
    # Discount configuration
    type = Column(SQLEnum(CouponType), nullable=False)
    value = Column(Integer, nullable=False)  # Percentage (1-100) or piastres for fixed
    min_cart_piastres = Column(BigInteger, nullable=True)  # Minimum cart total in piastres
    max_discount_piastres = Column(BigInteger, nullable=True)  # Maximum discount cap
    
    # Visibility rules
    visibility = Column(SQLEnum(CouponVisibility), nullable=False, default=CouponVisibility.PUBLIC)
    eligible_categories = Column(JSON, nullable=True)  # List of user categories: ["STUDENT", "FIRST_TIME"]
    visible_on = Column(DateTime(timezone=True), nullable=True)  # When to show publicly
    
    # Usage limits
    usage_limit = Column(Integer, nullable=True)  # Total uses allowed (null = unlimited)
    per_user_limit = Column(Integer, nullable=False, default=1)  # Uses per user
    used_count = Column(Integer, nullable=False, default=0)
    
    # Validity period
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Donor personalization
    donor_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    donor = relationship("Donor", back_populates="coupons")
    redemptions = relationship("CouponRedemption", back_populates="coupon", cascade="all, delete-orphan")


class CouponRedemption(Base):
    """
    Record of coupon redemption.
    
    Tracks each use of a coupon with discount applied.
    """
    __tablename__ = "coupon_redemptions"
    __table_args__ = (
        Index("ix_coupon_redemptions_coupon_id", "coupon_id"),
        Index("ix_coupon_redemptions_user_id", "user_id"),
        Index("ix_coupon_redemptions_order_id", "order_id"),
        Index("ix_coupon_redemptions_created_at", "created_at"),
        {"extend_existing": True},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    coupon_id = Column(UUIDType, ForeignKey("coupons.id"), nullable=False)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False)
    order_id = Column(String(64), ForeignKey("orders.id"), nullable=True)
    
    # Discount applied in piastres
    discount_applied_piastres = Column(BigInteger, nullable=False)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    coupon = relationship("Coupon", back_populates="redemptions")
