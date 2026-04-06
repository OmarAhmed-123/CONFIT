"""
CONFIT Backend — Sales Analytics Database Models
=================================================
SQLAlchemy models for sales transactions and analytics caching.
Designed for partitioned PostgreSQL deployment with store-scoped isolation.
"""

import enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Numeric,
    Enum as SQLEnum,
    Index,
    UniqueConstraint,
    CheckConstraint,
    text,
    func,
    select,
)
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSTZRANGE
from database.base import Base, JSONType, SCHEMA  # Use JSONType for SQLite/PostgreSQL compatibility

from database.models import UUIDType, _new_uuid


# ═══════════════════════════════════════════════════════════════════
# ENUMERATED TYPES
# ═══════════════════════════════════════════════════════════════════

class SalesCategory(str, enum.Enum):
    """Product category enumeration for sales transactions."""
    CLOTHES = "Clothes"
    SHOES = "Shoes"
    ACCESSORIES = "Accessories"
    FULL_OUTFIT = "Full Outfit"


class CustomerSegment(str, enum.Enum):
    """Customer segment enumeration for analytics."""
    NEW_CUSTOMER = "New Customer"
    RETURNING = "Returning"
    VIP = "VIP"
    WHOLESALE = "Wholesale"


class ReturnStatus(str, enum.Enum):
    """Return status enumeration for transaction tracking."""
    COMPLETED = "Completed"
    RETURNED = "Returned"
    PENDING_RETURN = "Pending Return"


class IngestionStatus(str, enum.Enum):
    """Status enumeration for ingestion queue."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ═══════════════════════════════════════════════════════════════════
# SALES TRANSACTION MODEL
# ═══════════════════════════════════════════════════════════════════

class SalesTransaction(Base):
    """
    Sales transaction model for store analytics.
    
    Partitioned by store_id for data isolation and query performance.
    Uses UUID primary key for distributed systems compatibility.
    """
    __tablename__ = "sales_transactions"
    __table_args__ = (
        # Check constraints for data integrity
        CheckConstraint('price >= 0', name='ck_sales_price_positive'),
        CheckConstraint('quantity > 0', name='ck_sales_quantity_positive'),
        CheckConstraint('profit_margin >= 0 AND profit_margin <= 100', name='ck_sales_margin_range'),
        # Indexes are created via migration for partitioned tables
        {"extend_existing": True, **({"schema": "public"} if SCHEMA else {})},
    )

    # Primary Key (UUID for partitioning compatibility)
    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    
    # Store isolation (partition key)
    store_id = Column(UUIDType, ForeignKey("stores.id"), nullable=False, index=True)
    
    # Product information
    product_name = Column(String(255), nullable=False)
    category = Column(SQLEnum(SalesCategory, name="sales_category_enum"), nullable=False)
    product_type = Column(String(100), nullable=True)
    
    # Pricing (DECIMAL for financial precision)
    price = Column(Numeric(12, 2), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    # total_amount is a generated column in PostgreSQL
    
    # Customer information
    customer_name = Column(String(255), nullable=True)
    customer_segment = Column(
        SQLEnum(CustomerSegment, name="customer_segment_enum"),
        nullable=False,
        default=CustomerSegment.NEW_CUSTOMER
    )
    customer_id = Column(UUIDType, nullable=True)  # Optional FK to users
    
    # Transaction details
    sale_date = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    profit_margin = Column(Numeric(5, 2), nullable=True)
    return_status = Column(
        SQLEnum(ReturnStatus, name="return_status_enum"),
        nullable=False,
        default=ReturnStatus.COMPLETED
    )
    
    # Order reference (links to existing orders)
    order_id = Column(String(64), nullable=True)
    order_item_id = Column(Integer, nullable=True)
    
    # Additional metadata
    channel = Column(String(50), nullable=True, default="in_store")
    region = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSONType, nullable=False, default=dict)
    
    # Audit fields
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
    
    # Soft delete support
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Version for optimistic locking
    version = Column(Integer, nullable=False, default=1)
    
    # Relationships
    store = relationship("Store", backref="sales_transactions")
    
    @hybrid_property
    def total_amount(self) -> Decimal:
        """Calculate total amount (price * quantity)."""
        if self.price is not None and self.quantity is not None:
            return self.price * self.quantity
        return Decimal("0.00")
    
    @total_amount.expression
    def total_amount(cls):
        """SQL expression for total amount calculation."""
        return cls.price * cls.quantity
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "store_id": str(self.store_id),
            "product_name": self.product_name,
            "category": self.category.value if self.category else None,
            "product_type": self.product_type,
            "price": float(self.price) if self.price else None,
            "quantity": self.quantity,
            "total_amount": float(self.total_amount),
            "customer_name": self.customer_name,
            "customer_segment": self.customer_segment.value if self.customer_segment else None,
            "customer_id": str(self.customer_id) if self.customer_id else None,
            "sale_date": self.sale_date.isoformat() if self.sale_date else None,
            "profit_margin": float(self.profit_margin) if self.profit_margin else None,
            "return_status": self.return_status.value if self.return_status else None,
            "order_id": self.order_id,
            "channel": self.channel,
            "region": self.region,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<SalesTransaction(id={self.id}, store_id={self.store_id}, product='{self.product_name}', total={self.total_amount})>"


# ═══════════════════════════════════════════════════════════════════
# STORE ANALYTICS CACHE MODEL
# ═══════════════════════════════════════════════════════════════════

class StoreAnalyticsCache(Base):
    """
    Pre-computed analytics cache for dashboard widgets.
    Updated periodically and invalidated on new sales data.
    """
    __tablename__ = "store_analytics_cache"
    __table_args__ = (
        Index("ix_analytics_cache_store", "store_id", unique=True),
        Index("ix_analytics_cache_expires", "expires_at", postgresql_where=text("is_stale = FALSE")),
        {"extend_existing": True, **({"schema": "public"} if SCHEMA else {})},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    store_id = Column(UUIDType, ForeignKey("stores.id"), nullable=False, unique=True)
    
    # Period identifiers
    period_type = Column(String(20), nullable=False, default="current")
    
    # Revenue metrics
    total_revenue = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    revenue_change_pct = Column(Numeric(6, 2), nullable=True)
    avg_order_value = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    aov_change_pct = Column(Numeric(6, 2), nullable=True)
    
    # Transaction metrics
    total_transactions = Column(Integer, nullable=False, default=0)
    transactions_change_pct = Column(Numeric(6, 2), nullable=True)
    total_units_sold = Column(Integer, nullable=False, default=0)
    
    # Profit metrics
    total_profit = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    avg_profit_margin = Column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    profit_change_pct = Column(Numeric(6, 2), nullable=True)
    
    # Customer metrics
    unique_customers = Column(Integer, nullable=False, default=0)
    new_customers = Column(Integer, nullable=False, default=0)
    returning_customers = Column(Integer, nullable=False, default=0)
    vip_customers = Column(Integer, nullable=False, default=0)
    
    # Return metrics
    return_rate = Column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    returns_count = Column(Integer, nullable=False, default=0)
    returns_amount = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    
    # Breakdowns (JSONType for flexibility)
    category_breakdown = Column(JSONType, nullable=False, default=list)
    top_products = Column(JSONType, nullable=False, default=list)
    segment_breakdown = Column(JSONType, nullable=False, default=list)
    
    # Time period
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    
    # Cache metadata
    computed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    is_stale = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    store = relationship("Store", backref="analytics_cache")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "store_id": str(self.store_id),
            "period_type": self.period_type,
            "revenue": {
                "total": float(self.total_revenue),
                "change_pct": float(self.revenue_change_pct) if self.revenue_change_pct else None,
            },
            "transactions": {
                "total": self.total_transactions,
                "change_pct": float(self.transactions_change_pct) if self.transactions_change_pct else None,
                "units_sold": self.total_units_sold,
            },
            "avg_order_value": {
                "value": float(self.avg_order_value),
                "change_pct": float(self.aov_change_pct) if self.aov_change_pct else None,
            },
            "profit": {
                "total": float(self.total_profit),
                "avg_margin": float(self.avg_profit_margin),
                "change_pct": float(self.profit_change_pct) if self.profit_change_pct else None,
            },
            "customers": {
                "unique": self.unique_customers,
                "new": self.new_customers,
                "returning": self.returning_customers,
                "vip": self.vip_customers,
            },
            "returns": {
                "rate": float(self.return_rate),
                "count": self.returns_count,
                "amount": float(self.returns_amount),
            },
            "category_breakdown": self.category_breakdown,
            "segment_breakdown": self.segment_breakdown,
            "top_products": self.top_products,
            "period": {
                "start": self.period_start.isoformat() if self.period_start else None,
                "end": self.period_end.isoformat() if self.period_end else None,
            },
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
            "is_stale": self.is_stale,
        }


# ═══════════════════════════════════════════════════════════════════
# SALES INGESTION QUEUE MODEL
# ═══════════════════════════════════════════════════════════════════

class SalesIngestionQueue(Base):
    """
    Queue table for batch ingestion of sales data.
    Supports idempotency and retry logic.
    """
    __tablename__ = "sales_ingestion_queue"
    __table_args__ = (
        Index("ix_ingestion_status", "status", "created_at", postgresql_where=text("status IN ('pending', 'processing')")),
        Index("ix_ingestion_batch", "batch_id", "batch_sequence"),
        UniqueConstraint("idempotency_key", name="uq_ingestion_idempotency"),
        {"extend_existing": True, **({"schema": "public"} if SCHEMA else {})},
    )

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    store_id = Column(UUIDType, ForeignKey("stores.id"), nullable=False)
    
    # Batch identifier
    batch_id = Column(UUIDType, nullable=False, default=_new_uuid)
    batch_sequence = Column(Integer, nullable=False, default=1)
    
    # Raw payload
    payload = Column(JSONType, nullable=False)
    # payload_hash is generated in PostgreSQL
    
    # Processing status
    status = Column(
        SQLEnum(IngestionStatus, name="ingestion_status_enum"),
        nullable=False,
        default=IngestionStatus.PENDING
    )
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    last_error = Column(Text, nullable=True)
    
    # Processing metadata
    processed_at = Column(DateTime(timezone=True), nullable=True)
    processed_by = Column(String(100), nullable=True)
    rows_inserted = Column(Integer, nullable=True, default=0)
    
    # Deduplication
    idempotency_key = Column(String(128), nullable=True, unique=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    store = relationship("Store", backref="ingestion_queue")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "store_id": str(self.store_id),
            "batch_id": str(self.batch_id),
            "batch_sequence": self.batch_sequence,
            "status": self.status.value if self.status else None,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "last_error": self.last_error,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "rows_inserted": self.rows_inserted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ═══════════════════════════════════════════════════════════════════
# DATE RANGE PRESET HELPER
# ═══════════════════════════════════════════════════════════════════

class DateRangePreset(str, enum.Enum):
    """Date range presets for analytics queries."""
    TODAY = "TODAY"
    YESTERDAY = "YESTERDAY"
    THIS_WEEK = "THIS_WEEK"
    LAST_WEEK = "LAST_WEEK"
    THIS_MONTH = "THIS_MONTH"
    LAST_MONTH = "LAST_MONTH"
    LAST_7_DAYS = "LAST_7_DAYS"
    LAST_30_DAYS = "LAST_30_DAYS"
    LAST_90_DAYS = "LAST_90_DAYS"
    YTD = "YTD"


def get_date_range_from_preset(preset: DateRangePreset) -> tuple[datetime, datetime]:
    """
    Convert preset to (start_date, end_date) tuple.
    
    Returns dates in UTC timezone.
    """
    from datetime import timedelta
    from dateutil.relativedelta import relativedelta
    
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    ranges = {
        DateRangePreset.TODAY: (today, today + timedelta(days=1)),
        DateRangePreset.YESTERDAY: (today - timedelta(days=1), today),
        DateRangePreset.THIS_WEEK: (today - timedelta(days=today.weekday()), today + timedelta(days=1)),
        DateRangePreset.LAST_WEEK: (
            today - timedelta(days=today.weekday() + 7),
            today - timedelta(days=today.weekday())
        ),
        DateRangePreset.THIS_MONTH: (today.replace(day=1), today + timedelta(days=1)),
        DateRangePreset.LAST_MONTH: (
            (today.replace(day=1) - timedelta(days=1)).replace(day=1),
            today.replace(day=1)
        ),
        DateRangePreset.LAST_7_DAYS: (today - timedelta(days=7), today + timedelta(days=1)),
        DateRangePreset.LAST_30_DAYS: (today - timedelta(days=30), today + timedelta(days=1)),
        DateRangePreset.LAST_90_DAYS: (today - timedelta(days=90), today + timedelta(days=1)),
        DateRangePreset.YTD: (today.replace(month=1, day=1), today + timedelta(days=1)),
    }
    
    return ranges.get(preset, (today, today + timedelta(days=1)))
