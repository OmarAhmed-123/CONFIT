"""
CONFIT Backend - Product Application Service
=============================================
Product catalog management with search, filtering, and recommendations.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, validator
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities import Product, ProductVariant
from domain.base import Money, PaginatedResult, PaginationParams, ProductStatus
from infrastructure.elasticsearch import ElasticsearchService, get_elasticsearch_client
from infrastructure.redis_client import RedisCache, get_cache_client
from core.security.input_sanitization import (
    sanitize_string,
    sanitize_html,
    sanitize_url,
    sanitize_float,
    detect_sql_injection,
    detect_xss,
    SecurityValidationError,
)
from database.models import (
    Product as ProductModel,
    ProductVariant as ProductVariantModel,
    Brand as BrandModel,
)
from models.production_models import ProductCategory as ProductCategoryModel


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DTOs
# ─────────────────────────────────────────────────────────────────────────────

class ProductCreateDTO(BaseModel):
    """Product creation DTO."""
    name: str
    slug: str
    description: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    brand_id: Optional[str] = None
    category_id: Optional[UUID] = None
    subcategory_id: Optional[UUID] = None
    color: Optional[str] = None
    color_hex: Optional[str] = None
    material: Optional[str] = None
    pattern: Optional[str] = None
    style_tags: List[str] = []
    occasion_tags: List[str] = []
    season_tags: List[str] = []
    base_price: float
    sale_price: Optional[float] = None
    currency: str = "USD"
    cost_price: Optional[float] = None
    weight_kg: Optional[float] = None
    primary_image_url: Optional[str] = None
    images: List[str] = []
    attributes: Dict[str, Any] = {}
    
    @validator('name', 'slug', 'sku', 'barcode')
    def sanitize_basic_fields(cls, v):
        if v is None:
            return v
        v = sanitize_string(v, max_length=200)
        if detect_sql_injection(v) or detect_xss(v):
            raise ValueError("Invalid characters detected")
        return v
    
    @validator('description')
    def sanitize_description(cls, v):
        if v is None:
            return v
        # Allow limited HTML for product descriptions
        return sanitize_html(v, allowed_tags=['p', 'br', 'b', 'i', 'u', 'strong', 'em', 'ul', 'ol', 'li'])
    
    @validator('color', 'material', 'pattern')
    def sanitize_text_fields(cls, v):
        if v is None:
            return v
        return sanitize_string(v, max_length=100)
    
    @validator('color_hex')
    def validate_color_hex(cls, v):
        if v is None:
            return v
        v = sanitize_string(v, max_length=7)
        if not v.startswith('#') or len(v) != 7:
            raise ValueError("Invalid hex color format")
        return v
    
    @validator('style_tags', 'occasion_tags', 'season_tags', pre=True)
    def sanitize_tags(cls, v):
        if not v:
            return []
        return [sanitize_string(tag, max_length=50) for tag in v]
    
    @validator('base_price', 'sale_price', 'cost_price')
    def validate_prices(cls, v):
        if v is None:
            return v
        return sanitize_float(v, min_value=0, max_value=999999.99)
    
    @validator('primary_image_url', 'images', pre=True)
    def sanitize_urls(cls, v):
        if v is None or (isinstance(v, list) and not v):
            return v if isinstance(v, list) else None
        if isinstance(v, list):
            return [sanitize_url(url) for url in v]
        return sanitize_url(v)


class ProductUpdateDTO(BaseModel):
    """Product update DTO."""
    name: Optional[str] = None
    description: Optional[str] = None
    brand_id: Optional[str] = None
    category_id: Optional[UUID] = None
    color: Optional[str] = None
    material: Optional[str] = None
    style_tags: Optional[List[str]] = None
    occasion_tags: Optional[List[str]] = None
    season_tags: Optional[List[str]] = None
    base_price: Optional[float] = None
    sale_price: Optional[float] = None
    sale_starts_at: Optional[datetime] = None
    sale_ends_at: Optional[datetime] = None
    status: Optional[str] = None
    is_featured: Optional[bool] = None
    
    @validator('name')
    def sanitize_name(cls, v):
        if v is None:
            return v
        v = sanitize_string(v, max_length=200)
        if detect_sql_injection(v) or detect_xss(v):
            raise ValueError("Invalid characters detected")
        return v
    
    @validator('description')
    def sanitize_description(cls, v):
        if v is None:
            return v
        return sanitize_html(v, allowed_tags=['p', 'br', 'b', 'i', 'u', 'strong', 'em', 'ul', 'ol', 'li'])
    
    @validator('color', 'material')
    def sanitize_text_fields(cls, v):
        if v is None:
            return v
        return sanitize_string(v, max_length=100)
    
    @validator('style_tags', 'occasion_tags', 'season_tags', pre=True)
    def sanitize_tags(cls, v):
        if v is None:
            return v
        return [sanitize_string(tag, max_length=50) for tag in v]
    
    @validator('base_price', 'sale_price')
    def validate_prices(cls, v):
        if v is None:
            return v
        return sanitize_float(v, min_value=0, max_value=999999.99)
    
    @validator('status')
    def validate_status(cls, v):
        if v is None:
            return v
        allowed = ['draft', 'active', 'inactive', 'discontinued']
        v = sanitize_string(v, max_length=20).lower()
        if v not in allowed:
            raise ValueError(f"Invalid status. Allowed: {allowed}")
        return v


class ProductVariantDTO(BaseModel):
    """Product variant DTO."""
    id: str
    product_id: str
    sku: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    color_hex: Optional[str] = None
    price_adjustment: float = 0.0
    inventory_quantity: int = 0
    reserved_quantity: int = 0
    available_quantity: int = 0
    is_active: bool = True
    image_url: Optional[str] = None


class ProductDTO(BaseModel):
    """Product response DTO."""
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    sku: Optional[str] = None
    brand_id: Optional[str] = None
    brand_name: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    color: Optional[str] = None
    color_hex: Optional[str] = None
    material: Optional[str] = None
    pattern: Optional[str] = None
    style_tags: List[str] = []
    occasion_tags: List[str] = []
    season_tags: List[str] = []
    base_price: float
    sale_price: Optional[float] = None
    current_price: float
    currency: str = "USD"
    is_on_sale: bool = False
    status: str = "draft"
    is_featured: bool = False
    is_new_arrival: bool = False
    is_bestseller: bool = False
    is_in_stock: bool = False
    primary_image_url: Optional[str] = None
    images: List[str] = []
    rating_average: Optional[float] = None
    review_count: int = 0
    view_count: int = 0
    purchase_count: int = 0
    variants: List[ProductVariantDTO] = []
    created_at: datetime
    updated_at: datetime


class ProductFilterDTO(BaseModel):
    """Product filter DTO."""
    query: Optional[str] = None
    brand_id: Optional[str] = None
    category_id: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    style_tags: Optional[List[str]] = None
    occasion_tags: Optional[List[str]] = None
    season_tags: Optional[List[str]] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    is_featured: Optional[bool] = None
    is_new_arrival: Optional[bool] = None
    is_bestseller: Optional[bool] = None
    is_on_sale: Optional[bool] = None
    status: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: str = "desc"


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class ProductService:
    """Product catalog service."""
    
    CACHE_TTL = 300  # 5 minutes
    CACHE_PREFIX = "products"
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: Optional[RedisCache] = None
        self._search: Optional[ElasticsearchService] = None
    
    async def _get_cache(self) -> RedisCache:
        if self._cache is None:
            self._cache = RedisCache(await get_cache_client(), self.CACHE_PREFIX)
        return self._cache
    
    async def _get_search(self) -> ElasticsearchService:
        if self._search is None:
            self._search = ElasticsearchService(await get_elasticsearch_client())
        return self._search
    
    # ─────────────────────────────────────────────────────────────────────────
    # CRUD OPERATIONS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def create_product(
        self,
        dto: ProductCreateDTO,
        brand_manager_id: Optional[UUID] = None,
    ) -> Tuple[Optional[ProductDTO], Optional[str]]:
        """Create a new product."""
        # Check if slug exists
        existing = await self._get_by_slug(dto.slug)
        if existing:
            return None, "Product with this slug already exists"
        
        if dto.sku:
            existing_sku = await self._get_by_sku(dto.sku)
            if existing_sku:
                return None, "Product with this SKU already exists"
        
        # Create product model
        product = ProductModel(
            name=dto.name,
            slug=dto.slug,
            description=dto.description,
            sku=dto.sku,
            barcode=dto.barcode,
            brand_id=dto.brand_id,
            category_id=str(dto.category_id) if dto.category_id else None,
            subcategory_id=str(dto.subcategory_id) if dto.subcategory_id else None,
            color=dto.color,
            color_hex=dto.color_hex,
            material=dto.material,
            pattern=dto.pattern,
            style_tags=dto.style_tags,
            occasion_tags=dto.occasion_tags,
            season_tags=dto.season_tags,
            base_price=Decimal(str(dto.base_price)),
            sale_price=Decimal(str(dto.sale_price)) if dto.sale_price else None,
            currency=dto.currency,
            cost_price=Decimal(str(dto.cost_price)) if dto.cost_price else None,
            weight_kg=Decimal(str(dto.weight_kg)) if dto.weight_kg else None,
            primary_image_url=dto.primary_image_url,
            images=dto.images,
            attributes=dto.attributes,
            status=ProductStatus.DRAFT.value,
        )
        
        self.session.add(product)
        await self.session.flush()
        await self.session.refresh(product)
        
        # Index in Elasticsearch
        await self._index_product(product)
        
        logger.info(f"Product created: {product.id}")
        
        return self._to_dto(product), None
    
    async def update_product(
        self,
        product_id: UUID,
        dto: ProductUpdateDTO,
    ) -> Tuple[Optional[ProductDTO], Optional[str]]:
        """Update product."""
        product = await self._get_model_by_id(product_id)
        if not product:
            return None, "Product not found"
        
        # Update fields
        update_data = dto.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                if field in ['base_price', 'sale_price', 'cost_price']:
                    value = Decimal(str(value))
                setattr(product, field, value)
        
        product.updated_at = datetime.now(timezone.utc)
        
        await self.session.flush()
        await self.session.refresh(product)
        
        # Update Elasticsearch index
        await self._index_product(product)
        
        # Invalidate cache
        cache = await self._get_cache()
        await cache.delete(f"product:{product_id}")
        
        return self._to_dto(product), None
    
    async def delete_product(self, product_id: UUID) -> Tuple[bool, Optional[str]]:
        """Delete product (soft delete)."""
        product = await self._get_model_by_id(product_id)
        if not product:
            return False, "Product not found"
        
        product.deleted_at = datetime.now(timezone.utc)
        product.is_active = False
        product.status = ProductStatus.ARCHIVED.value
        
        await self.session.flush()
        
        # Remove from Elasticsearch
        search = await self._get_search()
        await search.delete_product(str(product_id))
        
        # Invalidate cache
        cache = await self._get_cache()
        await cache.delete(f"product:{product_id}")
        
        return True, None
    
    async def publish_product(self, product_id: UUID) -> Tuple[bool, Optional[str]]:
        """Publish product to make it active."""
        product = await self._get_model_by_id(product_id)
        if not product:
            return False, "Product not found"
        
        product.status = ProductStatus.ACTIVE.value
        product.published_at = datetime.now(timezone.utc)
        
        await self.session.flush()
        await self._index_product(product)
        
        return True, None
    
    # ─────────────────────────────────────────────────────────────────────────
    # VARIANTS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def add_variant(
        self,
        product_id: UUID,
        size: Optional[str] = None,
        color: Optional[str] = None,
        color_hex: Optional[str] = None,
        sku: Optional[str] = None,
        price_adjustment: float = 0.0,
        inventory_quantity: int = 0,
        image_url: Optional[str] = None,
    ) -> Tuple[Optional[ProductVariantDTO], Optional[str]]:
        """Add variant to product."""
        product = await self._get_model_by_id(product_id)
        if not product:
            return None, "Product not found"
        
        # Check for duplicate variant
        existing = await self._get_variant(product_id, size, color)
        if existing:
            return None, "Variant with this size/color already exists"
        
        variant = ProductVariantModel(
            product_id=str(product_id),
            size=size,
            color=color,
            color_hex=color_hex,
            sku=sku,
            price_adjustment=Decimal(str(price_adjustment)),
            inventory_quantity=inventory_quantity,
            image_url=image_url,
        )
        
        self.session.add(variant)
        await self.session.flush()
        await self.session.refresh(variant)
        
        return self._variant_to_dto(variant), None
    
    async def update_inventory(
        self,
        variant_id: UUID,
        quantity: int,
        operation: str = "set",  # set, add, subtract
    ) -> Tuple[bool, Optional[str]]:
        """Update variant inventory."""
        variant = await self._get_variant_model(variant_id)
        if not variant:
            return False, "Variant not found"
        
        if operation == "set":
            variant.inventory_quantity = quantity
        elif operation == "add":
            variant.inventory_quantity += quantity
        elif operation == "subtract":
            variant.inventory_quantity = max(0, variant.inventory_quantity - quantity)
        
        await self.session.flush()
        
        return True, None
    
    async def reserve_inventory(
        self,
        variant_id: UUID,
        quantity: int,
    ) -> Tuple[bool, Optional[str]]:
        """Reserve inventory for order."""
        variant = await self._get_variant_model(variant_id)
        if not variant:
            return False, "Variant not found"
        
        available = variant.inventory_quantity - variant.reserved_quantity
        if available < quantity:
            return False, f"Insufficient inventory. Available: {available}"
        
        variant.reserved_quantity += quantity
        await self.session.flush()
        
        return True, None
    
    async def release_inventory(
        self,
        variant_id: UUID,
        quantity: int,
    ) -> None:
        """Release reserved inventory."""
        variant = await self._get_variant_model(variant_id)
        if variant:
            variant.reserved_quantity = max(0, variant.reserved_quantity - quantity)
            await self.session.flush()
    
    async def fulfill_inventory(
        self,
        variant_id: UUID,
        quantity: int,
    ) -> Tuple[bool, Optional[str]]:
        """Fulfill reserved inventory (after payment)."""
        variant = await self._get_variant_model(variant_id)
        if not variant:
            return False, "Variant not found"
        
        if variant.reserved_quantity < quantity:
            return False, "Reserved quantity is less than fulfillment quantity"
        
        variant.reserved_quantity -= quantity
        variant.inventory_quantity -= quantity
        variant.sold_count += quantity
        
        await self.session.flush()
        
        return True, None
    
    # ─────────────────────────────────────────────────────────────────────────
    # SEARCH & FILTER
    # ─────────────────────────────────────────────────────────────────────────
    
    async def search_products(
        self,
        filters: ProductFilterDTO,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[ProductDTO]:
        """Search products with filters using Elasticsearch."""
        search = await self._get_search()
        
        result = await search.search_products(
            query=filters.query or "",
            filters=filters.dict(exclude_unset=True, exclude={'query', 'sort_by', 'sort_order'}),
            sort=[{filters.sort_by: {"order": filters.sort_order}}] if filters.sort_by else None,
            page=page,
            page_size=page_size,
        )
        
        hits = result.get("hits", {}).get("hits", [])
        total = result.get("hits", {}).get("total", {}).get("value", 0)
        
        products = [self._es_hit_to_dto(hit) for hit in hits]
        
        return PaginatedResult(
            items=products,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )
    
    async def get_featured_products(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult[ProductDTO]:
        """Get featured products."""
        cache = await self._get_cache()
        cache_key = f"featured:{page}:{page_size}"
        
        cached = await cache.get(cache_key)
        if cached:
            return PaginatedResult(**cached)
        
        query = (
            select(ProductModel)
            .options(selectinload(ProductModel.variants))
            .where(
                ProductModel.is_featured == True,
                ProductModel.status == ProductStatus.ACTIVE.value,
                ProductModel.is_active == True,
            )
            .order_by(ProductModel.created_at.desc())
        )
        
        total_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(total_query)
        total = total_result.scalar() or 0
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(query)
        products = result.scalars().all()
        
        paginated = PaginatedResult(
            items=[self._to_dto(p) for p in products],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )
        
        await cache.set(cache_key, paginated.dict(), ttl=self.CACHE_TTL)
        
        return paginated
    
    async def get_by_id(self, product_id: UUID) -> Optional[ProductDTO]:
        """Get product by ID."""
        cache = await self._get_cache()
        cache_key = f"product:{product_id}"
        
        cached = await cache.get(cache_key)
        if cached:
            return ProductDTO(**cached)
        
        product = await self._get_model_by_id(product_id)
        if not product:
            return None
        
        dto = self._to_dto(product)
        await cache.set(cache_key, dto.dict(), ttl=self.CACHE_TTL)
        
        return dto
    
    async def get_by_slug(self, slug: str) -> Optional[ProductDTO]:
        """Get product by slug."""
        product = await self._get_by_slug(slug)
        return self._to_dto(product) if product else None
    
    async def get_similar_products(
        self,
        product_id: UUID,
        size: int = 10,
    ) -> List[ProductDTO]:
        """Get similar products using Elasticsearch."""
        search = await self._get_search()
        
        result = await search.similar_products(str(product_id), size)
        hits = result.get("hits", {}).get("hits", [])
        
        return [self._es_hit_to_dto(hit) for hit in hits]
    
    async def record_view(self, product_id: UUID) -> None:
        """Record product view."""
        product = await self._get_model_by_id(product_id)
        if product:
            product.view_count += 1
            await self.session.flush()
    
    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE METHODS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _get_model_by_id(self, product_id: UUID) -> Optional[ProductModel]:
        """Get product model by ID."""
        query = (
            select(ProductModel)
            .options(selectinload(ProductModel.variants))
            .where(ProductModel.id == str(product_id))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_by_slug(self, slug: str) -> Optional[ProductModel]:
        """Get product by slug."""
        query = (
            select(ProductModel)
            .options(selectinload(ProductModel.variants))
            .where(ProductModel.slug == slug)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_by_sku(self, sku: str) -> Optional[ProductModel]:
        """Get product by SKU."""
        query = select(ProductModel).where(ProductModel.sku == sku)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_variant(
        self,
        product_id: UUID,
        size: Optional[str],
        color: Optional[str],
    ) -> Optional[ProductVariantModel]:
        """Get variant by product, size, and color."""
        conditions = [ProductVariantModel.product_id == str(product_id)]
        if size:
            conditions.append(ProductVariantModel.size == size)
        if color:
            conditions.append(ProductVariantModel.color == color)
        
        query = select(ProductVariantModel).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_variant_model(self, variant_id: UUID) -> Optional[ProductVariantModel]:
        """Get variant model by ID."""
        query = select(ProductVariantModel).where(ProductVariantModel.id == str(variant_id))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def _index_product(self, product: ProductModel) -> None:
        """Index product in Elasticsearch."""
        search = await self._get_search()
        
        is_on_sale = (
            product.sale_price is not None
            and product.sale_starts_at is not None
            and product.sale_ends_at is not None
            and product.sale_starts_at <= datetime.now(timezone.utc) <= product.sale_ends_at
        )
        
        current_price = float(product.sale_price) if is_on_sale else float(product.base_price)
        
        await search.index_product({
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "description": product.description,
            "brand_id": product.brand_id,
            "brand_name": None,  # TODO: Load brand name
            "category_id": product.category_id,
            "category_name": None,  # TODO: Load category name
            "color": product.color,
            "color_hex": product.color_hex,
            "material": product.material,
            "pattern": product.pattern,
            "style_tags": product.style_tags or [],
            "occasion_tags": product.occasion_tags or [],
            "season_tags": product.season_tags or [],
            "base_price": float(product.base_price),
            "sale_price": float(product.sale_price) if product.sale_price else None,
            "current_price": current_price,
            "currency": product.currency,
            "status": product.status,
            "is_featured": product.is_featured,
            "is_new_arrival": product.is_new_arrival,
            "is_bestseller": product.is_bestseller,
            "is_on_sale": is_on_sale,
            "rating_average": float(product.rating_average) if product.rating_average else None,
            "review_count": product.review_count,
            "view_count": product.view_count,
            "purchase_count": product.purchase_count,
            "primary_image_url": product.primary_image_url,
            "images": product.images or [],
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None,
            "published_at": product.published_at.isoformat() if product.published_at else None,
            "style_compatibility": product.style_compatibility,
            "attributes": product.attributes or {},
        })
    
    def _to_dto(self, model: ProductModel) -> ProductDTO:
        """Convert model to DTO."""
        is_on_sale = (
            model.sale_price is not None
            and model.sale_starts_at is not None
            and model.sale_ends_at is not None
            and model.sale_starts_at <= datetime.now(timezone.utc) <= model.sale_ends_at
        )
        
        current_price = float(model.sale_price) if is_on_sale else float(model.base_price)
        
        total_inventory = sum(v.inventory_quantity for v in model.variants) if model.variants else 0
        
        return ProductDTO(
            id=model.id,
            name=model.name,
            slug=model.slug,
            description=model.description,
            sku=model.sku,
            brand_id=model.brand_id,
            brand_name=None,  # TODO: Load
            category_id=model.category_id,
            category_name=None,  # TODO: Load
            color=model.color,
            color_hex=model.color_hex,
            material=model.material,
            pattern=model.pattern,
            style_tags=model.style_tags or [],
            occasion_tags=model.occasion_tags or [],
            season_tags=model.season_tags or [],
            base_price=float(model.base_price),
            sale_price=float(model.sale_price) if model.sale_price else None,
            current_price=current_price,
            currency=model.currency,
            is_on_sale=is_on_sale,
            status=model.status,
            is_featured=model.is_featured,
            is_new_arrival=model.is_new_arrival,
            is_bestseller=model.is_bestseller,
            is_in_stock=total_inventory > 0,
            primary_image_url=model.primary_image_url,
            images=model.images or [],
            rating_average=float(model.rating_average) if model.rating_average else None,
            review_count=model.review_count,
            view_count=model.view_count,
            purchase_count=model.purchase_count,
            variants=[self._variant_to_dto(v) for v in model.variants] if model.variants else [],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    def _variant_to_dto(self, model: ProductVariantModel) -> ProductVariantDTO:
        """Convert variant model to DTO."""
        return ProductVariantDTO(
            id=model.id,
            product_id=model.product_id,
            sku=model.sku,
            size=model.size,
            color=model.color,
            color_hex=model.color_hex,
            price_adjustment=float(model.price_adjustment),
            inventory_quantity=model.inventory_quantity,
            reserved_quantity=model.reserved_quantity,
            available_quantity=max(0, model.inventory_quantity - model.reserved_quantity),
            is_active=model.is_active,
            image_url=model.image_url,
        )
    
    def _es_hit_to_dto(self, hit: dict) -> ProductDTO:
        """Convert Elasticsearch hit to DTO."""
        source = hit.get("_source", {})
        return ProductDTO(
            id=source.get("id"),
            name=source.get("name", ""),
            slug=source.get("slug", ""),
            description=source.get("description"),
            brand_id=source.get("brand_id"),
            brand_name=source.get("brand_name"),
            category_id=source.get("category_id"),
            category_name=source.get("category_name"),
            color=source.get("color"),
            color_hex=source.get("color_hex"),
            material=source.get("material"),
            pattern=source.get("pattern"),
            style_tags=source.get("style_tags", []),
            occasion_tags=source.get("occasion_tags", []),
            season_tags=source.get("season_tags", []),
            base_price=source.get("base_price", 0),
            sale_price=source.get("sale_price"),
            current_price=source.get("current_price", 0),
            currency=source.get("currency", "USD"),
            is_on_sale=source.get("is_on_sale", False),
            status=source.get("status", "draft"),
            is_featured=source.get("is_featured", False),
            is_new_arrival=source.get("is_new_arrival", False),
            is_bestseller=source.get("is_bestseller", False),
            is_in_stock=True,  # TODO: Check inventory
            primary_image_url=source.get("primary_image_url"),
            images=source.get("images", []),
            rating_average=source.get("rating_average"),
            review_count=source.get("review_count", 0),
            view_count=source.get("view_count", 0),
            purchase_count=source.get("purchase_count", 0),
            variants=[],
            created_at=datetime.fromisoformat(source["created_at"]) if source.get("created_at") else None,
            updated_at=datetime.fromisoformat(source["updated_at"]) if source.get("updated_at") else None,
        )
