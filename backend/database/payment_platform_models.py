"""
Unified payment ledger + invoices (Stripe, Paymob, PayPal).
Used by FastAPI payment orchestrator; SQLite + PostgreSQL compatible.
"""

from __future__ import annotations

import enum
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from database.base import Base

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


class PaymentProvider(str, enum.Enum):
    stripe = "stripe"
    paymob = "paymob"
    paypal = "paypal"
    fawry = "fawry"
    valu = "valu"
    cash_on_delivery = "cash_on_delivery"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    succeeded = "succeeded"
    failed = "failed"
    canceled = "canceled"
    pending_cod = "pending_cod"  # Cash on Delivery - awaiting collection


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_payments_idempotency_key"),
        Index("ix_payments_order_id", "order_id"),
        Index("ix_payments_provider_external", "provider", "external_payment_id"),
        {"extend_existing": True},
    )

    id = Column(String(64), primary_key=True, default=lambda: f"pay_{uuid.uuid4().hex[:16]}")
    order_id = Column(String(64), ForeignKey("orders.id"), nullable=False)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=True)
    provider = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default=PaymentStatus.pending.value)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(8), nullable=False, default="egp")
    tax_amount_cents = Column(Integer, nullable=True)  # VAT amount in piastres
    external_payment_id = Column(String(255), nullable=True)
    idempotency_key = Column(String(128), nullable=True)
    client_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    order = relationship("Order", backref="platform_payments_rel")
    transactions = relationship("PaymentTransaction", back_populates="payment", cascade="all, delete-orphan")
    events = relationship("PaymentEvent", back_populates="payment", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="payment", cascade="all, delete-orphan")


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    __table_args__ = (Index("ix_payment_transactions_payment_id", "payment_id"), {"extend_existing": True})

    id = Column(String(64), primary_key=True, default=lambda: f"ptx_{uuid.uuid4().hex[:16]}")
    payment_id = Column(String(64), ForeignKey("payments.id"), nullable=False)
    kind = Column(String(64), nullable=False)
    amount_cents = Column(Integer, nullable=True)
    currency = Column(String(8), nullable=True)
    provider_reference = Column(String(255), nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    payment = relationship("Payment", back_populates="transactions")


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    __table_args__ = (
        UniqueConstraint("provider_event_fingerprint", name="uq_payment_events_fingerprint"),
        Index("ix_payment_events_payment_id", "payment_id"),
        {"extend_existing": True},
    )

    id = Column(String(64), primary_key=True, default=lambda: f"pve_{uuid.uuid4().hex[:16]}")
    payment_id = Column(String(64), ForeignKey("payments.id"), nullable=True)
    event_type = Column(String(128), nullable=False)
    provider_event_fingerprint = Column(String(512), nullable=False)
    payload = Column(JSON, nullable=True)
    processed_ok = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    payment = relationship("Payment", back_populates="events")


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("invoice_number", name="uq_invoices_number"),
        Index("ix_invoices_order_id", "order_id"),
        {"extend_existing": True},
    )

    id = Column(String(64), primary_key=True, default=lambda: f"inv_{uuid.uuid4().hex[:16]}")
    invoice_number = Column(String(64), nullable=False)
    order_id = Column(String(64), ForeignKey("orders.id"), nullable=False)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=True)
    payment_id = Column(String(64), ForeignKey("payments.id"), nullable=True)
    subtotal = Column(String(32), nullable=False)
    tax = Column(String(32), nullable=False)
    total = Column(String(32), nullable=False)
    currency = Column(String(8), nullable=False, default="USD")
    pdf_storage_path = Column(String(1024), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    order = relationship("Order", backref="invoices_rel")
    payment = relationship("Payment", back_populates="invoices")
