"""
CONFIT Backend - Domain Entities
================================
Core domain entities for the CONFIT platform.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from .base import (
    AggregateRoot, DomainEvent, Email, Entity, Money, PhoneNumber, Address,
    UserRole, OrderStatus, PaymentStatus, PaymentMethod, ProductStatus,
    InventoryStatus, TryOnStatus, VisualSearchStatus, ShippingMethod
)


# ─────────────────────────────────────────────────────────────────────────────
# USER AGGREGATE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class UserCreatedEvent(DomainEvent):
    """Event fired when a new user is created."""
    aggregate_type: str = "User"


@dataclass
class UserLoggedInEvent(DomainEvent):
    """Event fired when a user logs in."""
    ip_address: str = ""
    user_agent: str = ""
    aggregate_type: str = "User"


@dataclass
class StyleProfileUpdatedEvent(DomainEvent):
    """Event fired when user style profile is updated."""
    aggregate_type: str = "User"


@dataclass
class User(AggregateRoot):
    """User aggregate root."""
    email: Email = None
    password_hash: str = ""
    name: str = ""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[PhoneNumber] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    
    # Location
    country_code: Optional[str] = None
    timezone: str = "UTC"
    language: str = "en"
    currency: str = "USD"
    
    # Status
    email_verified: bool = False
    phone_verified: bool = False
    is_verified: bool = False
    is_staff: bool = False
    is_active: bool = True
    
    # Settings
    settings: Dict[str, Any] = field(default_factory=dict)
    notification_preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    login_count: int = 0
    
    # Relationships (IDs only)
    roles: List["UserRoleAssignment"] = field(default_factory=list)
    addresses: List["UserAddress"] = field(default_factory=list)
    
    def __post_init__(self):
        if self.email and isinstance(self.email, str):
            self.email = Email(self.email)
    
    @classmethod
    def create(
        cls,
        email: str,
        password_hash: str,
        name: str,
        **kwargs
    ) -> "User":
        """Factory method to create a new user."""
        user = cls(
            email=Email(email),
            password_hash=password_hash,
            name=name,
            **kwargs
        )
        user.add_event(UserCreatedEvent(aggregate_id=user.id))
        return user
    
    def update_profile(
        self,
        name: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        bio: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> None:
        """Update user profile information."""
        if name is not None:
            self.name = name
        if first_name is not None:
            self.first_name = first_name
        if last_name is not None:
            self.last_name = last_name
        if bio is not None:
            self.bio = bio
        if avatar_url is not None:
            self.avatar_url = avatar_url
        self.touch()
    
    def record_login(self, ip_address: str, user_agent: str) -> None:
        """Record a successful login."""
        self.last_login_at = datetime.now(timezone.utc)
        self.last_login_ip = ip_address
        self.login_count += 1
        self.add_event(UserLoggedInEvent(
            aggregate_id=self.id,
            ip_address=ip_address,
            user_agent=user_agent
        ))
    
    def verify_email(self) -> None:
        """Mark email as verified."""
        self.email_verified = True
        self.is_verified = self.phone_verified or self.email_verified
        self.touch()
    
    def verify_phone(self) -> None:
        """Mark phone as verified."""
        self.phone_verified = True
        self.is_verified = self.email_verified or self.phone_verified
        self.touch()
    
    def deactivate(self) -> None:
        """Deactivate the user account."""
        self.is_active = False
        self.touch()
    
    def activate(self) -> None:
        """Activate the user account."""
        self.is_active = True
        self.touch()
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role."""
        return any(r.role == role for r in self.roles)
    
    def add_role(self, role: UserRole, granted_by: Optional[UUID] = None) -> None:
        """Add a role to the user."""
        if not self.has_role(role):
            self.roles.append(UserRoleAssignment(
                user_id=self.id,
                role=role,
                granted_by=granted_by
            ))
            self.touch()
    
    def remove_role(self, role: UserRole) -> None:
        """Remove a role from the user."""
        self.roles = [r for r in self.roles if r.role != role]
        self.touch()


@dataclass
class UserRoleAssignment(Entity):
    """User role assignment entity."""
    user_id: UUID = None
    role: UserRole = UserRole.USER
    granted_by: Optional[UUID] = None
    granted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """Check if the role assignment has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


@dataclass
class UserAddress(Entity):
    """User address entity."""
    user_id: UUID = None
    label: Optional[str] = None
    recipient_name: str = ""
    phone: Optional[str] = None
    address: Address = None
    is_default_shipping: bool = False
    is_default_billing: bool = False
    is_verified: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# STYLE PROFILE ENTITIES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StyleProfile(Entity):
    """User style profile entity."""
    user_id: UUID = None
    
    # Archetype
    primary_archetype: Optional[str] = None
    secondary_archetypes: List[str] = field(default_factory=list)
    archetype_confidence: Decimal = Decimal("0.0")
    
    # Style Vector (8 dimensions)
    style_classic: Decimal = Decimal("0.5")
    style_trendy: Decimal = Decimal("0.5")
    style_minimalist: Decimal = Decimal("0.5")
    style_maximalist: Decimal = Decimal("0.5")
    style_feminine: Decimal = Decimal("0.5")
    style_masculine: Decimal = Decimal("0.5")
    style_edgy: Decimal = Decimal("0.5")
    style_romantic: Decimal = Decimal("0.5")
    
    # Color preferences
    skin_undertone: Optional[str] = None
    preferred_colors: List[str] = field(default_factory=list)
    avoided_colors: List[str] = field(default_factory=list)
    color_confidence: Decimal = Decimal("0.0")
    
    # Pattern & Fabric
    pattern_preferences: Dict[str, Any] = field(default_factory=dict)
    fabric_preferences: List[str] = field(default_factory=list)
    
    # Silhouette
    silhouette_preferences: Dict[str, Any] = field(default_factory=dict)
    fit_preference: str = "regular"
    
    # Status
    profile_completeness: Decimal = Decimal("0.0")
    onboarding_completed: bool = False
    onboarding_phase: int = 0
    
    def calculate_completeness(self) -> Decimal:
        """Calculate profile completeness percentage."""
        score = Decimal("0.0")
        
        if self.primary_archetype:
            score += Decimal("20.0")
        if self.preferred_colors:
            score += Decimal("15.0")
        if self.skin_undertone:
            score += Decimal("10.0")
        if self.pattern_preferences:
            score += Decimal("10.0")
        if self.fabric_preferences:
            score += Decimal("10.0")
        if self.silhouette_preferences:
            score += Decimal("15.0")
        if self.fit_preference != "regular":
            score += Decimal("10.0")
        if self.onboarding_completed:
            score += Decimal("10.0")
        
        self.profile_completeness = score
        return score


@dataclass
class BodyProfile(Entity):
    """User body measurements and size preferences."""
    user_id: UUID = None
    profile_status: str = "not_set"
    
    # Measurements (cm)
    height_cm: Optional[int] = None
    weight_kg: Optional[int] = None
    chest_cm: Optional[int] = None
    waist_cm: Optional[int] = None
    hips_cm: Optional[int] = None
    inseam_cm: Optional[int] = None
    shoulder_width_cm: Optional[int] = None
    arm_length_cm: Optional[int] = None
    
    # Classification
    body_shape: Optional[str] = None
    
    # Sizes
    size_tops: Optional[str] = None
    size_bottoms: Optional[str] = None
    size_dresses: Optional[str] = None
    size_shoes: Optional[str] = None
    brand_size_overrides: Dict[str, str] = field(default_factory=dict)
    
    # Fit issues
    fit_issues: List[str] = field(default_factory=list)


@dataclass
class BudgetProfile(Entity):
    """User budget preferences."""
    user_id: UUID = None
    per_item_min: Optional[Money] = None
    per_item_max: Optional[Money] = None
    monthly_max: Optional[Money] = None
    investment_willing: bool = False
    price_sensitivity: Decimal = Decimal("0.5")


@dataclass
class BrandAffinity(Entity):
    """User brand affinity."""
    user_id: UUID = None
    brand_id: str = ""
    affinity_score: Decimal = Decimal("0.5")
    affinity_source: str = "explicit"
    reason: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT AGGREGATE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ProductCreatedEvent(DomainEvent):
    """Event fired when a product is created."""
    aggregate_type: str = "Product"


@dataclass
class ProductUpdatedEvent(DomainEvent):
    """Event fired when a product is updated."""
    aggregate_type: str = "Product"


@dataclass
class Product(AggregateRoot):
    """Product aggregate root."""
    sku: Optional[str] = None
    barcode: Optional[str] = None
    name: str = ""
    slug: str = ""
    description: Optional[str] = None
    
    # Classification
    brand_id: Optional[str] = None
    category_id: Optional[UUID] = None
    subcategory_id: Optional[UUID] = None
    
    # Attributes
    color: Optional[str] = None
    color_hex: Optional[str] = None
    material: Optional[str] = None
    pattern: Optional[str] = None
    style_tags: List[str] = field(default_factory=list)
    occasion_tags: List[str] = field(default_factory=list)
    season_tags: List[str] = field(default_factory=list)
    
    # Pricing
    base_price: Money = None
    sale_price: Optional[Money] = None
    cost_price: Optional[Money] = None
    sale_starts_at: Optional[datetime] = None
    sale_ends_at: Optional[datetime] = None
    
    # Status
    status: ProductStatus = ProductStatus.DRAFT
    is_featured: bool = False
    is_new_arrival: bool = False
    is_bestseller: bool = False
    published_at: Optional[datetime] = None
    
    # Statistics
    view_count: int = 0
    purchase_count: int = 0
    wishlist_count: int = 0
    rating_average: Optional[Decimal] = None
    review_count: int = 0
    
    # Media
    primary_image_url: Optional[str] = None
    images: List[str] = field(default_factory=list)
    videos: List[str] = field(default_factory=list)
    
    # Dimensions
    weight_kg: Optional[Decimal] = None
    length_cm: Optional[Decimal] = None
    width_cm: Optional[Decimal] = None
    height_cm: Optional[Decimal] = None
    
    # AI compatibility
    style_compatibility: int = 85
    color_compatibility: Optional[int] = None
    
    # Metadata
    attributes: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Relationships
    variants: List["ProductVariant"] = field(default_factory=list)
    
    def __post_init__(self):
        if self.base_price and isinstance(self.base_price, (int, float)):
            self.base_price = Money(Decimal(str(self.base_price)), "USD")
    
    @classmethod
    def create(
        cls,
        name: str,
        slug: str,
        base_price: Decimal,
        currency: str = "USD",
        **kwargs
    ) -> "Product":
        """Factory method to create a new product."""
        product = cls(
            name=name,
            slug=slug,
            base_price=Money(base_price, currency),
            **kwargs
        )
        product.add_event(ProductCreatedEvent(aggregate_id=product.id))
        return product
    
    @property
    def current_price(self) -> Money:
        """Get the current price (sale price if active, otherwise base price)."""
        if self.sale_price and self.sale_starts_at and self.sale_ends_at:
            now = datetime.now(timezone.utc)
            if self.sale_starts_at <= now <= self.sale_ends_at:
                return self.sale_price
        return self.base_price
    
    def is_on_sale(self) -> bool:
        """Check if product is currently on sale."""
        if not self.sale_price or not self.sale_starts_at or not self.sale_ends_at:
            return False
        now = datetime.now(timezone.utc)
        return self.sale_starts_at <= now <= self.sale_ends_at
    
    def publish(self) -> None:
        """Publish the product."""
        self.status = ProductStatus.ACTIVE
        self.published_at = datetime.now(timezone.utc)
        self.touch()
    
    def unpublish(self) -> None:
        """Unpublish the product."""
        self.status = ProductStatus.DRAFT
        self.touch()
    
    def record_view(self) -> None:
        """Record a product view."""
        self.view_count += 1
    
    def record_purchase(self, quantity: int = 1) -> None:
        """Record a product purchase."""
        self.purchase_count += quantity
    
    def add_variant(self, variant: "ProductVariant") -> None:
        """Add a variant to the product."""
        self.variants.append(variant)
        self.touch()
    
    def get_variant(self, size: Optional[str], color: Optional[str]) -> Optional["ProductVariant"]:
        """Get a specific variant by size and color."""
        for variant in self.variants:
            if variant.size == size and variant.color == color:
                return variant
        return None
    
    def total_inventory(self) -> int:
        """Get total inventory across all variants."""
        return sum(v.inventory_quantity for v in self.variants)
    
    def is_in_stock(self) -> bool:
        """Check if product is in stock."""
        return self.total_inventory() > 0


@dataclass
class ProductVariant(Entity):
    """Product variant entity."""
    product_id: UUID = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    
    # Variant attributes
    size: Optional[str] = None
    color: Optional[str] = None
    color_hex: Optional[str] = None
    
    # Pricing override
    price_adjustment: Money = None
    
    # Status
    is_active: bool = True
    
    # Inventory
    inventory_quantity: int = 0
    reserved_quantity: int = 0
    sold_count: int = 0
    
    # Media
    image_url: Optional[str] = None
    
    # Weight override
    weight_kg: Optional[Decimal] = None
    
    @property
    def available_quantity(self) -> int:
        """Get available inventory (total minus reserved)."""
        return max(0, self.inventory_quantity - self.reserved_quantity)
    
    def is_in_stock(self) -> bool:
        """Check if variant is in stock."""
        return self.available_quantity > 0
    
    def reserve(self, quantity: int) -> bool:
        """Reserve inventory for an order."""
        if self.available_quantity < quantity:
            return False
        self.reserved_quantity += quantity
        return True
    
    def release_reservation(self, quantity: int) -> None:
        """Release reserved inventory."""
        self.reserved_quantity = max(0, self.reserved_quantity - quantity)
    
    def fulfill(self, quantity: int) -> bool:
        """Fulfill reserved inventory."""
        if self.reserved_quantity < quantity:
            return False
        self.reserved_quantity -= quantity
        self.inventory_quantity -= quantity
        self.sold_count += quantity
        return True


# ─────────────────────────────────────────────────────────────────────────────
# ORDER AGGREGATE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class OrderCreatedEvent(DomainEvent):
    """Event fired when an order is created."""
    aggregate_type: str = "Order"


@dataclass
class OrderPaidEvent(DomainEvent):
    """Event fired when an order is paid."""
    aggregate_type: str = "Order"
    payment_id: Optional[UUID] = None


@dataclass
class OrderShippedEvent(DomainEvent):
    """Event fired when an order is shipped."""
    aggregate_type: str = "Order"
    tracking_number: str = ""


@dataclass
class OrderDeliveredEvent(DomainEvent):
    """Event fired when an order is delivered."""
    aggregate_type: str = "Order"


@dataclass
class OrderItem(Entity):
    """Order line item entity."""
    order_id: UUID = None
    product_id: UUID = None
    variant_id: UUID = None
    product_name: str = ""
    variant_name: str = ""
    quantity: int = 1
    unit_price: Money = None
    total_price: Money = None
    discount_amount: Money = None
    tax_amount: Money = None
    image_url: Optional[str] = None
    
    def __post_init__(self):
        if self.unit_price and not self.total_price:
            self.total_price = self.unit_price.multiply(self.quantity)


@dataclass
class Order(AggregateRoot):
    """Order aggregate root."""
    user_id: UUID = None
    order_number: str = ""
    
    # Status
    status: OrderStatus = OrderStatus.PENDING
    
    # Items
    items: List[OrderItem] = field(default_factory=list)
    
    # Pricing
    subtotal: Money = None
    discount_amount: Money = None
    tax_amount: Money = None
    shipping_amount: Money = None
    total: Money = None
    currency: str = "USD"
    
    # Addresses
    shipping_address: Address = None
    billing_address: Address = None
    
    # Shipping
    shipping_method: ShippingMethod = ShippingMethod.STANDARD
    tracking_number: Optional[str] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    # Payment
    payment_status: PaymentStatus = PaymentStatus.PENDING
    payment_method: Optional[PaymentMethod] = None
    payment_id: Optional[UUID] = None
    paid_at: Optional[datetime] = None
    
    # Metadata
    notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.subtotal:
            self.subtotal = Money(Decimal("0"), self.currency)
        if not self.discount_amount:
            self.discount_amount = Money(Decimal("0"), self.currency)
        if not self.tax_amount:
            self.tax_amount = Money(Decimal("0"), self.currency)
        if not self.shipping_amount:
            self.shipping_amount = Money(Decimal("0"), self.currency)
        if not self.total:
            self.total = Money(Decimal("0"), self.currency)
    
    @classmethod
    def create(
        cls,
        user_id: UUID,
        items: List[OrderItem],
        shipping_address: Address,
        billing_address: Address,
        shipping_method: ShippingMethod,
        **kwargs
    ) -> "Order":
        """Factory method to create a new order."""
        order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"
        order = cls(
            user_id=user_id,
            order_number=order_number,
            items=items,
            shipping_address=shipping_address,
            billing_address=billing_address,
            shipping_method=shipping_method,
            **kwargs
        )
        order._calculate_totals()
        order.add_event(OrderCreatedEvent(aggregate_id=order.id))
        return order
    
    def _calculate_totals(self) -> None:
        """Calculate order totals."""
        subtotal = Decimal("0")
        for item in self.items:
            if item.total_price:
                subtotal += item.total_price.amount
        
        self.subtotal = Money(subtotal, self.currency)
        
        total = subtotal
        if self.discount_amount:
            total -= self.discount_amount.amount
        if self.tax_amount:
            total += self.tax_amount.amount
        if self.shipping_amount:
            total += self.shipping_amount.amount
        
        self.total = Money(total, self.currency)
    
    def add_item(self, item: OrderItem) -> None:
        """Add an item to the order."""
        self.items.append(item)
        self._calculate_totals()
        self.touch()
    
    def remove_item(self, item_id: UUID) -> None:
        """Remove an item from the order."""
        self.items = [i for i in self.items if i.id != item_id]
        self._calculate_totals()
        self.touch()
    
    def confirm(self) -> None:
        """Confirm the order."""
        if self.status != OrderStatus.PENDING:
            raise ValueError(f"Cannot confirm order in {self.status} status")
        self.status = OrderStatus.CONFIRMED
        self.touch()
    
    def mark_paid(self, payment_id: UUID, payment_method: PaymentMethod) -> None:
        """Mark the order as paid."""
        self.payment_status = PaymentStatus.COMPLETED
        self.payment_method = payment_method
        self.payment_id = payment_id
        self.paid_at = datetime.now(timezone.utc)
        self.status = OrderStatus.PROCESSING
        self.add_event(OrderPaidEvent(aggregate_id=self.id, payment_id=payment_id))
        self.touch()
    
    def ship(self, tracking_number: str) -> None:
        """Mark the order as shipped."""
        if self.status != OrderStatus.PROCESSING:
            raise ValueError(f"Cannot ship order in {self.status} status")
        self.status = OrderStatus.SHIPPED
        self.tracking_number = tracking_number
        self.shipped_at = datetime.now(timezone.utc)
        self.add_event(OrderShippedEvent(
            aggregate_id=self.id,
            tracking_number=tracking_number
        ))
        self.touch()
    
    def deliver(self) -> None:
        """Mark the order as delivered."""
        if self.status != OrderStatus.SHIPPED:
            raise ValueError(f"Cannot deliver order in {self.status} status")
        self.status = OrderStatus.DELIVERED
        self.delivered_at = datetime.now(timezone.utc)
        self.add_event(OrderDeliveredEvent(aggregate_id=self.id))
        self.touch()
    
    def cancel(self, reason: Optional[str] = None) -> None:
        """Cancel the order."""
        if self.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
            raise ValueError(f"Cannot cancel order in {self.status} status")
        self.status = OrderStatus.CANCELLED
        if reason:
            self.notes = reason
        self.touch()
    
    def can_cancel(self) -> bool:
        """Check if the order can be cancelled."""
        return self.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED]


# ─────────────────────────────────────────────────────────────────────────────
# WARDROBE AGGREGATE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class WardrobeItem(Entity):
    """Wardrobe item entity."""
    user_id: UUID = None
    product_id: Optional[UUID] = None
    
    # Item info
    name: str = ""
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    
    # Attributes
    color: Optional[str] = None
    color_hex: Optional[str] = None
    size: Optional[str] = None
    material: Optional[str] = None
    pattern: Optional[str] = None
    style_tags: List[str] = field(default_factory=list)
    occasion_tags: List[str] = field(default_factory=list)
    
    # Media
    image_url: Optional[str] = None
    images: List[str] = field(default_factory=list)
    
    # Purchase info
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[Money] = None
    purchase_store: Optional[str] = None
    
    # Usage
    wear_count: int = 0
    last_worn_at: Optional[datetime] = None
    
    # Status
    is_active: bool = True
    is_favorite: bool = False
    
    # Auto-tagging
    auto_tags: List[str] = field(default_factory=list)
    auto_category: Optional[str] = None
    auto_color: Optional[str] = None
    auto_style: Optional[str] = None


@dataclass
class Outfit(Entity):
    """Outfit entity - collection of wardrobe items."""
    user_id: UUID = None
    name: str = ""
    description: Optional[str] = None
    
    # Items
    item_ids: List[UUID] = field(default_factory=list)
    
    # Occasion
    occasion: Optional[str] = None
    season: Optional[str] = None
    
    # Style
    style_tags: List[str] = field(default_factory=list)
    
    # Media
    image_url: Optional[str] = None
    
    # Pricing
    estimated_value: Optional[Money] = None
    
    # Status
    is_public: bool = False
    is_favorite: bool = False
    view_count: int = 0
    like_count: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# VIRTUAL TRY-ON AGGREGATE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TryOnSession(Entity):
    """Virtual try-on session entity."""
    user_id: UUID = None
    product_id: Optional[UUID] = None
    variant_id: Optional[UUID] = None
    
    # Input
    user_image_url: str = ""
    garment_image_url: str = ""
    
    # Output
    result_image_url: Optional[str] = None
    quality_score: Optional[Decimal] = None
    
    # Status
    status: TryOnStatus = TryOnStatus.PENDING
    error_message: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    
    # Metadata
    model_used: Optional[str] = None
    processing_time_ms: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# VISUAL SEARCH AGGREGATE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class VisualSearchResult(Entity):
    """Visual search result entity."""
    search_id: UUID = None
    product_id: UUID = None
    similarity_score: Decimal = Decimal("0.0")
    match_attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualSearchSession(Entity):
    """Visual search session entity."""
    user_id: Optional[UUID] = None
    
    # Input
    image_url: str = ""
    
    # Detected attributes
    detected_category: Optional[str] = None
    detected_color: Optional[str] = None
    detected_style: Optional[str] = None
    detected_pattern: Optional[str] = None
    detected_attributes: Dict[str, Any] = field(default_factory=dict)
    
    # Results
    results: List[VisualSearchResult] = field(default_factory=list)
    
    # Status
    status: VisualSearchStatus = VisualSearchStatus.PENDING
    error_message: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None


# ─────────────────────────────────────────────────────────────────────────────
# BRAND AGGREGATE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Brand(Entity):
    """Brand entity."""
    id: str = ""  # String ID for brands
    name: str = ""
    slug: str = ""
    description: Optional[str] = None
    
    # Branding
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    icon_url: Optional[str] = None
    
    # Contact
    website: Optional[str] = None
    contact_email: Optional[str] = None
    support_email: Optional[str] = None
    support_phone: Optional[str] = None
    
    # Social
    social_links: Dict[str, str] = field(default_factory=dict)
    
    # Business
    industry: Optional[str] = None
    founded_year: Optional[int] = None
    headquarters_country: Optional[str] = None
    headquarters_city: Optional[str] = None
    
    # Status
    is_verified: bool = False
    is_featured: bool = False
    is_active: bool = True
    
    # Statistics
    product_count: int = 0
    follower_count: int = 0
    rating_average: Optional[Decimal] = None
    review_count: int = 0
    
    # Settings
    commission_rate: Decimal = Decimal("0.100")
    return_policy_days: int = 30
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
