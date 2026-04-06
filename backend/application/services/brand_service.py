"""
CONFIT Backend - Brand Dashboard Service
========================================
Brand management, analytics, and inventory tracking.
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities import Brand
from domain.base import PaginatedResult, PaginationParams
from infrastructure.elasticsearch import ElasticsearchService, get_elasticsearch_client
from database.models import (
    Brand as BrandModel,
    Product as ProductModel,
    ProductVariant as ProductVariantModel,
    Order as OrderModel,
    OrderItem as OrderItemModel,
    Payment as PaymentModel,
)
from models.production_models import BrandFollower as BrandFollowerModel, BrandManager as BrandManagerModel


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DTOs
# ─────────────────────────────────────────────────────────────────────────────

class BrandCreateDTO(BaseModel):
    """Brand creation DTO."""
    name: str
    slug: str
    description: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    support_email: Optional[str] = None
    support_phone: Optional[str] = None
    industry: Optional[str] = None
    founded_year: Optional[int] = None
    headquarters_country: Optional[str] = None
    headquarters_city: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    social_links: Dict[str, str] = {}
    commission_rate: float = 0.10
    return_policy_days: int = 30


class BrandUpdateDTO(BaseModel):
    """Brand update DTO."""
    name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    support_email: Optional[str] = None
    support_phone: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None
    commission_rate: Optional[float] = None
    return_policy_days: Optional[int] = None


class BrandDTO(BaseModel):
    """Brand response DTO."""
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    industry: Optional[str] = None
    is_verified: bool = False
    is_featured: bool = False
    product_count: int = 0
    follower_count: int = 0
    rating_average: Optional[float] = None
    review_count: int = 0
    social_links: Dict[str, str] = {}
    created_at: datetime


class BrandAnalyticsDTO(BaseModel):
    """Brand analytics DTO."""
    brand_id: str
    period_start: datetime
    period_end: datetime
    
    # Sales metrics
    total_orders: int = 0
    total_revenue: float = 0.0
    total_products_sold: int = 0
    average_order_value: float = 0.0
    
    # Product metrics
    total_products: int = 0
    active_products: int = 0
    out_of_stock_products: int = 0
    low_stock_products: int = 0
    
    # Customer metrics
    unique_customers: int = 0
    repeat_customers: int = 0
    customer_retention_rate: float = 0.0
    
    # Engagement metrics
    total_views: int = 0
    total_wishlist_adds: int = 0
    conversion_rate: float = 0.0
    
    # Top products
    top_products: List[Dict[str, Any]] = []
    
    # Revenue by category
    revenue_by_category: Dict[str, float] = {}
    
    # Daily trend
    daily_revenue: List[Dict[str, Any]] = []


class InventoryStatusDTO(BaseModel):
    """Inventory status DTO."""
    product_id: str
    product_name: str
    sku: Optional[str] = None
    total_inventory: int = 0
    reserved_inventory: int = 0
    available_inventory: int = 0
    sold_count: int = 0
    status: str = "in_stock"
    last_restocked: Optional[datetime] = None
    variants: List[Dict[str, Any]] = []


class BrandDashboardDTO(BaseModel):
    """Brand dashboard summary."""
    brand: BrandDTO
    analytics: BrandAnalyticsDTO
    inventory_alerts: List[InventoryStatusDTO] = []
    recent_orders: List[Dict[str, Any]] = []
    pending_actions: List[str] = []


# ─────────────────────────────────────────────────────────────────────────────
# BRAND SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class BrandService:
    """Brand management and analytics service."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._search: Optional[ElasticsearchService] = None
    
    async def _get_search(self) -> ElasticsearchService:
        if self._search is None:
            self._search = ElasticsearchService(await get_elasticsearch_client())
        return self._search
    
    # ─────────────────────────────────────────────────────────────────────────
    # BRAND CRUD
    # ─────────────────────────────────────────────────────────────────────────
    
    async def create_brand(
        self,
        dto: BrandCreateDTO,
        owner_id: UUID,
    ) -> Tuple[Optional[BrandDTO], Optional[str]]:
        """Create a new brand."""
        # Check if slug exists
        existing = await self._get_by_slug(dto.slug)
        if existing:
            return None, "Brand with this slug already exists"
        
        brand = BrandModel(
            id=UUID().hex[:24],  # Generate unique string ID
            name=dto.name,
            slug=dto.slug,
            description=dto.description,
            website=dto.website,
            contact_email=dto.contact_email,
            support_email=dto.support_email,
            support_phone=dto.support_phone,
            industry=dto.industry,
            founded_year=dto.founded_year,
            headquarters_country=dto.headquarters_country,
            headquarters_city=dto.headquarters_city,
            logo_url=dto.logo_url,
            banner_url=dto.banner_url,
            social_links=dto.social_links,
            commission_rate=Decimal(str(dto.commission_rate)),
            return_policy_days=dto.return_policy_days,
        )
        
        self.session.add(brand)
        await self.session.flush()
        
        # Add owner as brand manager
        manager = BrandManagerModel(
            brand_id=brand.id,
            user_id=str(owner_id),
            role="owner",
        )
        self.session.add(manager)
        
        await self.session.flush()
        await self.session.refresh(brand)
        
        # Index in Elasticsearch
        await self._index_brand(brand)
        
        logger.info(f"Brand created: {brand.id}")
        
        return self._to_dto(brand), None
    
    async def update_brand(
        self,
        brand_id: str,
        dto: BrandUpdateDTO,
        user_id: UUID,
    ) -> Tuple[Optional[BrandDTO], Optional[str]]:
        """Update brand."""
        brand = await self._get_model(brand_id)
        if not brand:
            return None, "Brand not found"
        
        # Check permission
        if not await self._is_brand_manager(brand_id, user_id):
            return None, "Unauthorized"
        
        update_data = dto.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "commission_rate" and value is not None:
                value = Decimal(str(value))
            setattr(brand, field, value)
        
        brand.updated_at = datetime.now(timezone.utc)
        
        await self.session.flush()
        await self.session.refresh(brand)
        
        # Update Elasticsearch
        await self._index_brand(brand)
        
        return self._to_dto(brand), None
    
    async def get_brand(self, brand_id: str) -> Optional[BrandDTO]:
        """Get brand by ID."""
        brand = await self._get_model(brand_id)
        return self._to_dto(brand) if brand else None
    
    async def get_brand_by_slug(self, slug: str) -> Optional[BrandDTO]:
        """Get brand by slug."""
        brand = await self._get_by_slug(slug)
        return self._to_dto(brand) if brand else None
    
    async def search_brands(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Search brands."""
        search = await self._get_search()
        
        result = await search.search_brands(query, page, page_size)
        
        hits = result.get("hits", {}).get("hits", [])
        total = result.get("hits", {}).get("total", {}).get("value", 0)
        
        brands = []
        for hit in hits:
            source = hit.get("_source", {})
            brands.append(BrandDTO(
                id=source.get("id", ""),
                name=source.get("name", ""),
                slug=source.get("slug", ""),
                description=source.get("description"),
                logo_url=source.get("logo_url"),
                website=source.get("website"),
                industry=source.get("industry"),
                is_verified=source.get("is_verified", False),
                is_featured=source.get("is_featured", False),
                product_count=source.get("product_count", 0),
                follower_count=source.get("follower_count", 0),
                rating_average=source.get("rating_average"),
                review_count=source.get("review_count", 0),
                social_links=source.get("social_links", {}),
                created_at=datetime.fromisoformat(source["created_at"]) if source.get("created_at") else None,
            ))
        
        return {
            "items": brands,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    
    # ─────────────────────────────────────────────────────────────────────────
    # BRAND MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────
    
    async def add_brand_manager(
        self,
        brand_id: str,
        user_id: UUID,
        role: str = "manager",
        added_by: UUID = None,
    ) -> Tuple[bool, Optional[str]]:
        """Add manager to brand."""
        brand = await self._get_model(brand_id)
        if not brand:
            return False, "Brand not found"
        
        # Check if already manager
        query = select(BrandManagerModel).where(
            BrandManagerModel.brand_id == brand_id,
            BrandManagerModel.user_id == str(user_id),
        )
        result = await self.session.execute(query)
        if result.scalar_one_or_none():
            return False, "User is already a manager"
        
        manager = BrandManagerModel(
            brand_id=brand_id,
            user_id=str(user_id),
            role=role,
            added_by=str(added_by) if added_by else None,
        )
        
        self.session.add(manager)
        await self.session.flush()
        
        return True, None
    
    async def remove_brand_manager(
        self,
        brand_id: str,
        user_id: UUID,
    ) -> Tuple[bool, Optional[str]]:
        """Remove manager from brand."""
        query = select(BrandManagerModel).where(
            BrandManagerModel.brand_id == brand_id,
            BrandManagerModel.user_id == str(user_id),
        )
        result = await self.session.execute(query)
        manager = result.scalar_one_or_none()
        
        if not manager:
            return False, "Manager not found"
        
        if manager.role == "owner":
            return False, "Cannot remove owner"
        
        await self.session.delete(manager)
        await self.session.flush()
        
        return True, None
    
    async def follow_brand(
        self,
        brand_id: str,
        user_id: UUID,
    ) -> Tuple[bool, Optional[str]]:
        """Follow a brand."""
        brand = await self._get_model(brand_id)
        if not brand:
            return False, "Brand not found"
        
        # Check if already following
        query = select(BrandFollowerModel).where(
            BrandFollowerModel.brand_id == brand_id,
            BrandFollowerModel.user_id == str(user_id),
        )
        result = await self.session.execute(query)
        if result.scalar_one_or_none():
            return False, "Already following"
        
        follower = BrandFollowerModel(
            brand_id=brand_id,
            user_id=str(user_id),
        )
        
        self.session.add(follower)
        
        # Update follower count
        brand.follower_count += 1
        
        await self.session.flush()
        
        return True, None
    
    async def unfollow_brand(
        self,
        brand_id: str,
        user_id: UUID,
    ) -> Tuple[bool, Optional[str]]:
        """Unfollow a brand."""
        query = select(BrandFollowerModel).where(
            BrandFollowerModel.brand_id == brand_id,
            BrandFollowerModel.user_id == str(user_id),
        )
        result = await self.session.execute(query)
        follower = result.scalar_one_or_none()
        
        if not follower:
            return False, "Not following"
        
        await self.session.delete(follower)
        
        # Update follower count
        brand = await self._get_model(brand_id)
        if brand:
            brand.follower_count = max(0, brand.follower_count - 1)
        
        await self.session.flush()
        
        return True, None
    
    # ─────────────────────────────────────────────────────────────────────────
    # ANALYTICS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def get_brand_analytics(
        self,
        brand_id: str,
        period_days: int = 30,
    ) -> BrandAnalyticsDTO:
        """Get brand analytics for period."""
        brand = await self._get_model(brand_id)
        if not brand:
            return None
        
        period_end = datetime.now(timezone.utc)
        period_start = period_end - timedelta(days=period_days)
        
        # Get orders for brand in period
        orders_query = (
            select(OrderItemModel, OrderModel)
            .join(OrderModel, OrderModel.id == OrderItemModel.order_id)
            .join(ProductModel, ProductModel.id == OrderItemModel.product_id)
            .where(
                ProductModel.brand_id == brand_id,
                OrderModel.created_at >= period_start,
                OrderModel.created_at <= period_end,
                OrderModel.status.in_(["completed", "delivered", "shipped"]),
            )
        )
        
        orders_result = await self.session.execute(orders_query)
        order_items = orders_result.all()
        
        # Calculate metrics
        total_orders = len(set(item.order_id for item, _ in order_items))
        total_revenue = sum(float(item.total_price) for item, _ in order_items)
        total_products_sold = sum(item.quantity for item, _ in order_items)
        average_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Product metrics
        products_query = select(ProductModel).where(ProductModel.brand_id == brand_id)
        products_result = await self.session.execute(products_query)
        products = products_result.scalars().all()
        
        total_products = len(products)
        active_products = sum(1 for p in products if p.status == "active")
        out_of_stock = sum(1 for p in products if p.status == "out_of_stock")
        
        # Inventory alerts
        inventory_alerts = await self._get_inventory_alerts(brand_id)
        
        # Top products
        top_products = await self._get_top_products(brand_id, period_start, period_end)
        
        # Daily revenue
        daily_revenue = await self._get_daily_revenue(brand_id, period_start, period_end)
        
        return BrandAnalyticsDTO(
            brand_id=brand_id,
            period_start=period_start,
            period_end=period_end,
            total_orders=total_orders,
            total_revenue=total_revenue,
            total_products_sold=total_products_sold,
            average_order_value=average_order_value,
            total_products=total_products,
            active_products=active_products,
            out_of_stock_products=out_of_stock,
            low_stock_products=len(inventory_alerts),
            unique_customers=0,  # TODO: Calculate
            repeat_customers=0,
            customer_retention_rate=0.0,
            total_views=0,  # TODO: Track
            total_wishlist_adds=0,
            conversion_rate=0.0,
            top_products=top_products,
            revenue_by_category={},
            daily_revenue=daily_revenue,
        )
    
    async def get_brand_dashboard(
        self,
        brand_id: str,
        user_id: UUID,
    ) -> Optional[BrandDashboardDTO]:
        """Get brand dashboard summary."""
        brand = await self._get_model(brand_id)
        if not brand:
            return None
        
        if not await self._is_brand_manager(brand_id, user_id):
            return None
        
        analytics = await self.get_brand_analytics(brand_id)
        inventory_alerts = await self._get_inventory_alerts(brand_id)
        recent_orders = await self._get_recent_orders(brand_id, limit=10)
        
        # Generate pending actions
        pending_actions = []
        if inventory_alerts:
            pending_actions.append(f"{len(inventory_alerts)} products need restocking")
        if analytics.out_of_stock_products > 0:
            pending_actions.append(f"{analytics.out_of_stock_products} products are out of stock")
        
        return BrandDashboardDTO(
            brand=self._to_dto(brand),
            analytics=analytics,
            inventory_alerts=inventory_alerts[:5],
            recent_orders=recent_orders,
            pending_actions=pending_actions,
        )
    
    async def get_inventory_status(
        self,
        brand_id: str,
        user_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """Get inventory status for all brand products."""
        if not await self._is_brand_manager(brand_id, user_id):
            return {"items": [], "total": 0}
        
        query = (
            select(ProductModel)
            .options(selectinload(ProductModel.variants))
            .where(ProductModel.brand_id == brand_id)
        )
        
        result = await self.session.execute(query)
        products = result.scalars().all()
        
        items = []
        for product in products:
            total_inventory = sum(v.inventory_quantity for v in product.variants)
            reserved = sum(v.reserved_quantity for v in product.variants)
            available = total_inventory - reserved
            
            item_status = "in_stock"
            if available <= 0:
                item_status = "out_of_stock"
            elif available < 10:
                item_status = "low_stock"
            
            if status and item_status != status:
                continue
            
            items.append(InventoryStatusDTO(
                product_id=product.id,
                product_name=product.name,
                sku=product.sku,
                total_inventory=total_inventory,
                reserved_inventory=reserved,
                available_inventory=available,
                sold_count=sum(v.sold_count for v in product.variants),
                status=item_status,
                last_restocked=None,  # TODO: Track
                variants=[
                    {
                        "id": v.id,
                        "size": v.size,
                        "color": v.color,
                        "quantity": v.inventory_quantity,
                        "reserved": v.reserved_quantity,
                    }
                    for v in product.variants
                ],
            ))
        
        return {
            "items": items[(page - 1) * page_size:page * page_size],
            "total": len(items),
            "page": page,
            "page_size": page_size,
        }
    
    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE METHODS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _get_model(self, brand_id: str) -> Optional[BrandModel]:
        """Get brand model by ID."""
        query = select(BrandModel).where(BrandModel.id == brand_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_by_slug(self, slug: str) -> Optional[BrandModel]:
        """Get brand by slug."""
        query = select(BrandModel).where(BrandModel.slug == slug)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def _is_brand_manager(self, brand_id: str, user_id: UUID) -> bool:
        """Check if user is brand manager."""
        query = select(BrandManagerModel).where(
            BrandManagerModel.brand_id == brand_id,
            BrandManagerModel.user_id == str(user_id),
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def _get_inventory_alerts(self, brand_id: str) -> List[InventoryStatusDTO]:
        """Get products with low or out of stock inventory."""
        inventory = await self.get_inventory_status(brand_id, UUID(int=0))
        
        alerts = [
            item for item in inventory.get("items", [])
            if item.status in ["low_stock", "out_of_stock"]
        ]
        
        return alerts
    
    async def _get_top_products(
        self,
        brand_id: str,
        period_start: datetime,
        period_end: datetime,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top selling products."""
        query = (
            select(
                ProductModel.id,
                ProductModel.name,
                func.sum(OrderItemModel.quantity).label("sold"),
                func.sum(OrderItemModel.total_price).label("revenue"),
            )
            .join(OrderItemModel, OrderItemModel.product_id == ProductModel.id)
            .join(OrderModel, OrderModel.id == OrderItemModel.order_id)
            .where(
                ProductModel.brand_id == brand_id,
                OrderModel.created_at >= period_start,
                OrderModel.created_at <= period_end,
            )
            .group_by(ProductModel.id)
            .order_by(func.sum(OrderItemModel.quantity).desc())
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        
        return [
            {
                "product_id": row.id,
                "name": row.name,
                "sold": row.sold,
                "revenue": float(row.revenue),
            }
            for row in result
        ]
    
    async def _get_daily_revenue(
        self,
        brand_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> List[Dict[str, Any]]:
        """Get daily revenue breakdown."""
        # Simplified - in production use proper date truncation
        query = (
            select(
                func.date(OrderModel.created_at).label("date"),
                func.sum(OrderItemModel.total_price).label("revenue"),
            )
            .join(OrderItemModel, OrderItemModel.order_id == OrderModel.id)
            .join(ProductModel, ProductModel.id == OrderItemModel.product_id)
            .where(
                ProductModel.brand_id == brand_id,
                OrderModel.created_at >= period_start,
                OrderModel.created_at <= period_end,
            )
            .group_by(func.date(OrderModel.created_at))
            .order_by(func.date(OrderModel.created_at))
        )
        
        result = await self.session.execute(query)
        
        return [
            {
                "date": str(row.date),
                "revenue": float(row.revenue),
            }
            for row in result
        ]
    
    async def _get_recent_orders(
        self,
        brand_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get recent orders for brand."""
        query = (
            select(OrderModel)
            .join(OrderItemModel, OrderItemModel.order_id == OrderModel.id)
            .join(ProductModel, ProductModel.id == OrderItemModel.product_id)
            .where(ProductModel.brand_id == brand_id)
            .order_by(OrderModel.created_at.desc())
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        orders = result.scalars().all()
        
        return [
            {
                "order_id": order.id,
                "order_number": order.order_number,
                "status": order.status,
                "total": float(order.total),
                "created_at": order.created_at.isoformat(),
            }
            for order in orders
        ]
    
    async def _index_brand(self, brand: BrandModel) -> None:
        """Index brand in Elasticsearch."""
        search = await self._get_search()
        
        await search.index_brand({
            "id": brand.id,
            "name": brand.name,
            "slug": brand.slug,
            "description": brand.description,
            "industry": brand.industry,
            "is_verified": brand.is_verified,
            "is_featured": brand.is_featured,
            "product_count": brand.product_count,
            "follower_count": brand.follower_count,
            "rating_average": float(brand.rating_average) if brand.rating_average else None,
            "logo_url": brand.logo_url,
            "created_at": brand.created_at.isoformat() if brand.created_at else None,
        })
    
    def _to_dto(self, model: BrandModel) -> BrandDTO:
        """Convert model to DTO."""
        return BrandDTO(
            id=model.id,
            name=model.name,
            slug=model.slug,
            description=model.description,
            logo_url=model.logo_url,
            banner_url=model.banner_url,
            website=model.website,
            contact_email=model.contact_email,
            industry=model.industry,
            is_verified=model.is_verified,
            is_featured=model.is_featured,
            product_count=model.product_count,
            follower_count=model.follower_count,
            rating_average=float(model.rating_average) if model.rating_average else None,
            review_count=model.review_count,
            social_links=model.social_links or {},
            created_at=model.created_at,
        )
