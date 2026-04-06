"""
CONFIT Backend - Domain Base Classes
=====================================
Clean Architecture Domain Layer - Entity base classes and interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from uuid import UUID, uuid4


# ─────────────────────────────────────────────────────────────────────────────
# VALUE OBJECTS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ValueObject(ABC):
    """Base class for value objects - immutable and compared by value."""
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__
    
    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))


@dataclass(frozen=True)
class Money(ValueObject):
    """Money value object with currency."""
    amount: Decimal
    currency: str = "USD"
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
        if len(self.currency) != 3:
            raise ValueError("Currency must be a 3-letter ISO code")
    
    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot add money with different currencies")
        return Money(self.amount + other.amount, self.currency)
    
    def subtract(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot subtract money with different currencies")
        return Money(self.amount - other.amount, self.currency)
    
    def multiply(self, factor: Union[int, float, Decimal]) -> "Money":
        return Money(self.amount * Decimal(str(factor)), self.currency)


@dataclass(frozen=True)
class Email(ValueObject):
    """Email value object with validation."""
    address: str
    
    def __post_init__(self):
        if not self._is_valid_email(self.address):
            raise ValueError(f"Invalid email address: {self.address}")
    
    @staticmethod
    def _is_valid_email(email: str) -> bool:
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))


@dataclass(frozen=True)
class PhoneNumber(ValueObject):
    """Phone number value object."""
    number: str
    country_code: str = "+1"
    
    @property
    def full_number(self) -> str:
        return f"{self.country_code}{self.number}"


@dataclass(frozen=True)
class Address(ValueObject):
    """Address value object."""
    line1: str
    city: str
    postal_code: str
    country_code: str
    line2: Optional[str] = None
    state_province: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "line1": self.line1,
            "line2": self.line2,
            "city": self.city,
            "state_province": self.state_province,
            "postal_code": self.postal_code,
            "country_code": self.country_code,
        }


# ─────────────────────────────────────────────────────────────────────────────
# ENTITIES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Entity(ABC):
    """Base class for entities - identified by ID, mutable."""
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def touch(self) -> None:
        """Update the updated_at timestamp and increment version."""
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1


@dataclass
class AggregateRoot(Entity):
    """Base class for aggregate roots - entities that control other entities."""
    _events: List[Any] = field(default_factory=list, repr=False)
    
    def add_event(self, event: Any) -> None:
        """Add a domain event to be dispatched."""
        self._events.append(event)
    
    def clear_events(self) -> List[Any]:
        """Clear and return all domain events."""
        events = self._events.copy()
        self._events.clear()
        return events
    
    @property
    def events(self) -> List[Any]:
        """Get all pending domain events."""
        return self._events.copy()


# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN EVENTS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DomainEvent(ABC):
    """Base class for domain events."""
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    aggregate_id: UUID = field(default=None)
    aggregate_type: str = field(default="")


# ─────────────────────────────────────────────────────────────────────────────
# ENUMERATIONS
# ─────────────────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    """User roles for authorization."""
    ADMIN = "admin"
    BRAND_MANAGER = "brand_manager"
    STYLIST = "stylist"
    USER = "user"
    MODERATOR = "moderator"


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    RETURNED = "returned"
    FAILED = "failed"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    DISPUTED = "disputed"


class PaymentMethod(str, Enum):
    """Payment method enumeration."""
    CARD = "card"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    PAYPAL = "paypal"
    BNPL_AFFIRM = "bnpl_affirm"
    BNPL_KLARNA = "bnpl_klarna"
    BNPL_AFTERPAY = "bnpl_afterpay"
    STORE_CREDIT = "store_credit"


class ProductStatus(str, Enum):
    """Product status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"
    ARCHIVED = "archived"


class InventoryStatus(str, Enum):
    """Inventory status enumeration."""
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    RESERVED = "reserved"
    DISCONTINUED = "discontinued"


class TryOnStatus(str, Enum):
    """Virtual try-on status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class VisualSearchStatus(str, Enum):
    """Visual search status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ShippingMethod(str, Enum):
    """Shipping method enumeration."""
    STANDARD = "standard"
    EXPRESS = "express"
    OVERNIGHT = "overnight"
    SAME_DAY = "same_day"
    BOPIS = "bopis"  # Buy Online, Pickup In Store


# ─────────────────────────────────────────────────────────────────────────────
# GENERIC TYPES
# ─────────────────────────────────────────────────────────────────────────────

T = TypeVar("T")
EntityT = TypeVar("EntityT", bound=Entity)


# ─────────────────────────────────────────────────────────────────────────────
# PAGINATION
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PaginationParams:
    """Pagination parameters for queries."""
    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = None
    sort_order: str = "desc"
    
    def __post_init__(self):
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.page_size < 1 or self.page_size > 100:
            raise ValueError("Page size must be between 1 and 100")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size


@dataclass
class PaginatedResult(Generic[T]):
    """Paginated result container."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages
    
    @property
    def has_previous(self) -> bool:
        return self.page > 1


# ─────────────────────────────────────────────────────────────────────────────
# SPECIFICATIONS (Query Objects)
# ─────────────────────────────────────────────────────────────────────────────

class Specification(ABC, Generic[T]):
    """Specification pattern for complex queries."""
    
    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if the candidate satisfies this specification."""
        pass
    
    def and_(self, other: "Specification[T]") -> "AndSpecification[T]":
        return AndSpecification(self, other)
    
    def or_(self, other: "Specification[T]") -> "OrSpecification[T]":
        return OrSpecification(self, other)
    
    def not_(self) -> "NotSpecification[T]":
        return NotSpecification(self)


class AndSpecification(Specification[T]):
    """AND combination of specifications."""
    
    def __init__(self, left: Specification[T], right: Specification[T]):
        self.left = left
        self.right = right
    
    def is_satisfied_by(self, candidate: T) -> bool:
        return self.left.is_satisfied_by(candidate) and self.right.is_satisfied_by(candidate)


class OrSpecification(Specification[T]):
    """OR combination of specifications."""
    
    def __init__(self, left: Specification[T], right: Specification[T]):
        self.left = left
        self.right = right
    
    def is_satisfied_by(self, candidate: T) -> bool:
        return self.left.is_satisfied_by(candidate) or self.right.is_satisfied_by(candidate)


class NotSpecification(Specification[T]):
    """NOT specification."""
    
    def __init__(self, spec: Specification[T]):
        self.spec = spec
    
    def is_satisfied_by(self, candidate: T) -> bool:
        return not self.spec.is_satisfied_by(candidate)
