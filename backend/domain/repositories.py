"""
CONFIT Backend - Repository Interfaces
======================================
Repository pattern interfaces for Clean Architecture.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from .base import Entity, PaginatedResult, PaginationParams, Specification
from .entities import (
    User, StyleProfile, BodyProfile, BudgetProfile, BrandAffinity,
    Product, ProductVariant, Order, OrderItem,
    WardrobeItem, Outfit, TryOnSession, VisualSearchSession, Brand
)


# ─────────────────────────────────────────────────────────────────────────────
# GENERIC REPOSITORY INTERFACE
# ─────────────────────────────────────────────────────────────────────────────

EntityT = TypeVar("EntityT", bound=Entity)


class IRepository(ABC, Generic[EntityT]):
    """Base repository interface."""
    
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[EntityT]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def get_all(
        self,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[EntityT]:
        """Get all entities with optional pagination."""
        pass
    
    @abstractmethod
    async def add(self, entity: EntityT) -> EntityT:
        """Add a new entity."""
        pass
    
    @abstractmethod
    async def update(self, entity: EntityT) -> EntityT:
        """Update an existing entity."""
        pass
    
    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete an entity by ID."""
        pass
    
    @abstractmethod
    async def exists(self, id: UUID) -> bool:
        """Check if entity exists."""
        pass
    
    @abstractmethod
    async def find(
        self,
        specification: Specification[EntityT],
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[EntityT]:
        """Find entities matching a specification."""
        pass
    
    @abstractmethod
    async def find_one(
        self,
        specification: Specification[EntityT]
    ) -> Optional[EntityT]:
        """Find a single entity matching a specification."""
        pass


# ─────────────────────────────────────────────────────────────────────────────
# USER REPOSITORY
# ─────────────────────────────────────────────────────────────────────────────

class IUserRepository(IRepository[User]):
    """User repository interface."""
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        pass
    
    @abstractmethod
    async def get_by_phone(self, phone: str) -> Optional[User]:
        """Get user by phone number."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[User]:
        """Search users by name or email."""
        pass
    
    @abstractmethod
    async def get_by_role(
        self,
        role: str,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[User]:
        """Get users by role."""
        pass
    
    @abstractmethod
    async def get_active_users(
        self,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[User]:
        """Get all active users."""
        pass
    
    @abstractmethod
    async def update_last_login(
        self,
        user_id: UUID,
        ip_address: str,
        user_agent: str
    ) -> None:
        """Update user's last login information."""
        pass
    
    @abstractmethod
    async def verify_email(self, user_id: UUID) -> None:
        """Mark user's email as verified."""
        pass
    
    @abstractmethod
    async def verify_phone(self, user_id: UUID) -> None:
        """Mark user's phone as verified."""
        pass


# ─────────────────────────────────────────────────────────────────────────────
# STYLE PROFILE REPOSITORY
# ─────────────────────────────────────────────────────────────────────────────

class IStyleProfileRepository(IRepository[StyleProfile]):
    """Style profile repository interface."""
    
    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> Optional[StyleProfile]:
        """Get style profile by user ID."""
        pass
    
    @abstractmethod
    async def get_by_archetype(
        self,
        archetype: str,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[StyleProfile]:
        """Get profiles by archetype."""
        pass


class IBodyProfileRepository(IRepository[BodyProfile]):
    """Body profile repository interface."""
    
    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> Optional[BodyProfile]:
        """Get body profile by user ID."""
        pass


class IBudgetProfileRepository(IRepository[BudgetProfile]):
    """Budget profile repository interface."""
    
    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> Optional[BudgetProfile]:
        """Get budget profile by user ID."""
        pass


class IBrandAffinityRepository(IRepository[BrandAffinity]):
    """Brand affinity repository interface."""
    
    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: UUID,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[BrandAffinity]:
        """Get brand affinities by user ID."""
        pass
    
    @abstractmethod
    async def get_by_user_and_brand(
        self,
        user_id: UUID,
        brand_id: str
    ) -> Optional[BrandAffinity]:
        """Get affinity for a specific user and brand."""
        pass


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT REPOSITORY
# ─────────────────────────────────────────────────────────────────────────────

class IProductRepository(IRepository[Product]):
    """Product repository interface."""
    
    @abstractmethod
    async def get_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU."""
        pass
    
    @abstractmethod
    async def get_by_slug(self, slug: str) -> Optional[Product]:
        """Get product by slug."""
        pass
    
    @abstractmethod
    async def get_by_brand(
        self,
        brand_id: str,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Product]:
        """Get products by brand."""
        pass
    
    @abstractmethod
    async def get_by_category(
        self,
        category_id: UUID,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Product]:
        """Get products by category."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Product]:
        """Search products with filters."""
        pass
    
    @abstractmethod
    async def get_featured(
        self,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Product]:
        """Get featured products."""
        pass
    
    @abstractmethod
    async def get_new_arrivals(
        self,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Product]:
        """Get new arrival products."""
        pass
    
    @abstractmethod
    async def get_bestsellers(
        self,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Product]:
        """Get bestseller products."""
        pass
    
    @abstractmethod
    async def get_on_sale(
        self,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Product]:
        """Get products on sale."""
        pass
    
    @abstractmethod
    async def get_by_style_tags(
        self,
        tags: List[str],
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Product]:
        """Get products by style tags."""
        pass
    
    @abstractmethod
    async def get_by_occasion_tags(
        self,
        tags: List[str],
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Product]:
        """Get products by occasion tags."""
        pass
    
    @abstractmethod
    async def update_inventory(
        self,
        product_id: UUID,
        variant_id: UUID,
        quantity: int
    ) -> bool:
        """Update product variant inventory."""
        pass
    
    @abstractmethod
    async def increment_view_count(self, product_id: UUID) -> None:
        """Increment product view count."""
        pass


class IProductVariantRepository(IRepository[ProductVariant]):
    """Product variant repository interface."""
    
    @abstractmethod
    async def get_by_product_id(
        self,
        product_id: UUID,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[ProductVariant]:
        """Get variants by product ID."""
        pass
    
    @abstractmethod
    async def get_by_sku(self, sku: str) -> Optional[ProductVariant]:
        """Get variant by SKU."""
        pass
    
    @abstractmethod
    async def get_available(
        self,
        product_id: UUID
    ) -> List[ProductVariant]:
        """Get available (in stock) variants for a product."""
        pass


# ─────────────────────────────────────────────────────────────────────────────
# ORDER REPOSITORY
# ─────────────────────────────────────────────────────────────────────────────

class IOrderRepository(IRepository[Order]):
    """Order repository interface."""
    
    @abstractmethod
    async def get_by_order_number(self, order_number: str) -> Optional[Order]:
        """Get order by order number."""
        pass
    
    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: UUID,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Order]:
        """Get orders by user ID."""
        pass
    
    @abstractmethod
    async def get_by_status(
        self,
        status: str,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Order]:
        """Get orders by status."""
        pass
    
    @abstractmethod
    async def get_by_date_range(
        self,
        start_date: Any,
        end_date: Any,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Order]:
        """Get orders within a date range."""
        pass
    
    @abstractmethod
    async def update_status(
        self,
        order_id: UUID,
        status: str,
        **kwargs
    ) -> bool:
        """Update order status."""
        pass


# ─────────────────────────────────────────────────────────────────────────────
# WARDROBE REPOSITORY
# ─────────────────────────────────────────────────────────────────────────────

class IWardrobeRepository(IRepository[WardrobeItem]):
    """Wardrobe item repository interface."""
    
    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: UUID,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[WardrobeItem]:
        """Get wardrobe items by user ID."""
        pass
    
    @abstractmethod
    async def get_by_category(
        self,
        user_id: UUID,
        category: str,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[WardrobeItem]:
        """Get wardrobe items by category."""
        pass
    
    @abstractmethod
    async def get_favorites(
        self,
        user_id: UUID,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[WardrobeItem]:
        """Get favorite wardrobe items."""
        pass
    
    @abstractmethod
    async def get_by_style_tags(
        self,
        user_id: UUID,
        tags: List[str],
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[WardrobeItem]:
        """Get wardrobe items by style tags."""
        pass
    
    @abstractmethod
    async def search(
        self,
        user_id: UUID,
        query: str,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[WardrobeItem]:
        """Search wardrobe items."""
        pass


class IOutfitRepository(IRepository[Outfit]):
    """Outfit repository interface."""
    
    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: UUID,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Outfit]:
        """Get outfits by user ID."""
        pass
    
    @abstractmethod
    async def get_public(
        self,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Outfit]:
        """Get public outfits."""
        pass
    
    @abstractmethod
    async def get_by_occasion(
        self,
        user_id: UUID,
        occasion: str,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Outfit]:
        """Get outfits by occasion."""
        pass


# ─────────────────────────────────────────────────────────────────────────────
# VIRTUAL TRY-ON REPOSITORY
# ─────────────────────────────────────────────────────────────────────────────

class ITryOnRepository(IRepository[TryOnSession]):
    """Try-on session repository interface."""
    
    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: UUID,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[TryOnSession]:
        """Get try-on sessions by user ID."""
        pass
    
    @abstractmethod
    async def get_pending(self) -> List[TryOnSession]:
        """Get all pending try-on sessions."""
        pass
    
    @abstractmethod
    async def get_by_status(
        self,
        status: str,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[TryOnSession]:
        """Get try-on sessions by status."""
        pass
    
    @abstractmethod
    async def update_status(
        self,
        session_id: UUID,
        status: str,
        result_url: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update try-on session status."""
        pass


# ─────────────────────────────────────────────────────────────────────────────
# VISUAL SEARCH REPOSITORY
# ─────────────────────────────────────────────────────────────────────────────

class IVisualSearchRepository(IRepository[VisualSearchSession]):
    """Visual search session repository interface."""
    
    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: UUID,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[VisualSearchSession]:
        """Get visual search sessions by user ID."""
        pass
    
    @abstractmethod
    async def get_pending(self) -> List[VisualSearchSession]:
        """Get all pending visual search sessions."""
        pass
    
    @abstractmethod
    async def update_status(
        self,
        session_id: UUID,
        status: str,
        results: Optional[List[Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update visual search session status."""
        pass


# ─────────────────────────────────────────────────────────────────────────────
# BRAND REPOSITORY
# ─────────────────────────────────────────────────────────────────────────────

class IBrandRepository(IRepository[Brand]):
    """Brand repository interface."""
    
    @abstractmethod
    async def get_by_slug(self, slug: str) -> Optional[Brand]:
        """Get brand by slug."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Brand]:
        """Search brands."""
        pass
    
    @abstractmethod
    async def get_featured(
        self,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Brand]:
        """Get featured brands."""
        pass
    
    @abstractmethod
    async def get_verified(
        self,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Brand]:
        """Get verified brands."""
        pass
    
    @abstractmethod
    async def get_by_industry(
        self,
        industry: str,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[Brand]:
        """Get brands by industry."""
        pass
    
    @abstractmethod
    async def increment_follower_count(self, brand_id: str) -> None:
        """Increment brand follower count."""
        pass
    
    @abstractmethod
    async def update_product_count(self, brand_id: str, count: int) -> None:
        """Update brand product count."""
        pass
