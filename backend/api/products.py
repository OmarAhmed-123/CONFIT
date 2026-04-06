"""
CONFIT Backend - Product API Routes
===================================
Product catalog, search, and inventory management.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import (
    get_product_service, get_current_user, get_current_user_optional,
    require_permission, require_brand_manager
)
from application.services.product_service import (
    ProductService,
    ProductCreateDTO,
    ProductUpdateDTO,
    ProductDTO,
    ProductFilterDTO,
    ProductVariantDTO,
)
from core.security.rbac import Permission, AuthContext


router = APIRouter(prefix="/products", tags=["Products"])


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    summary="Search products",
)
async def search_products(
    query: Optional[str] = Query(None),
    brand_id: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
    material: Optional[str] = Query(None),
    price_min: Optional[float] = Query(None),
    price_max: Optional[float] = Query(None),
    is_featured: Optional[bool] = Query(None),
    is_new_arrival: Optional[bool] = Query(None),
    is_bestseller: Optional[bool] = Query(None),
    is_on_sale: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    product_service: ProductService = Depends(get_product_service),
):
    """Search products with filters."""
    filters = ProductFilterDTO(
        query=query,
        brand_id=brand_id,
        category_id=category_id,
        color=color,
        material=material,
        price_min=price_min,
        price_max=price_max,
        is_featured=is_featured,
        is_new_arrival=is_new_arrival,
        is_bestseller=is_bestseller,
        is_on_sale=is_on_sale,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    
    return await product_service.search_products(filters, page, page_size)


@router.get(
    "/featured",
    summary="Get featured products",
)
async def get_featured_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    product_service: ProductService = Depends(get_product_service),
):
    """Get featured products."""
    return await product_service.get_featured_products(page, page_size)


@router.get(
    "/{product_id}",
    response_model=ProductDTO,
    summary="Get product by ID",
)
async def get_product(
    product_id: UUID,
    product_service: ProductService = Depends(get_product_service),
    current_user: Optional[AuthContext] = Depends(get_current_user_optional),
):
    """Get product details by ID."""
    product = await product_service.get_by_id(product_id)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Record view
    await product_service.record_view(product_id)
    
    return product


@router.get(
    "/slug/{slug}",
    response_model=ProductDTO,
    summary="Get product by slug",
)
async def get_product_by_slug(
    slug: str,
    product_service: ProductService = Depends(get_product_service),
):
    """Get product details by slug."""
    product = await product_service.get_by_slug(slug)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return product


@router.get(
    "/{product_id}/similar",
    response_model=List[ProductDTO],
    summary="Get similar products",
)
async def get_similar_products(
    product_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    product_service: ProductService = Depends(get_product_service),
):
    """Get similar products."""
    return await product_service.get_similar_products(product_id, limit)


# ─────────────────────────────────────────────────────────────────────────────
# VARIANTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{product_id}/variants",
    response_model=List[ProductVariantDTO],
    summary="Get product variants",
)
async def get_product_variants(
    product_id: UUID,
    product_service: ProductService = Depends(get_product_service),
):
    """Get all variants for a product."""
    product = await product_service.get_by_id(product_id)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return product.variants


# ─────────────────────────────────────────────────────────────────────────────
# BRAND MANAGER ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ProductDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create product",
    dependencies=[require_brand_manager()],
)
async def create_product(
    dto: ProductCreateDTO,
    product_service: ProductService = Depends(get_product_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Create a new product (brand managers only)."""
    product, error = await product_service.create_product(dto)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return product


@router.patch(
    "/{product_id}",
    response_model=ProductDTO,
    summary="Update product",
    dependencies=[require_permission(Permission.PRODUCT_WRITE)],
)
async def update_product(
    product_id: UUID,
    dto: ProductUpdateDTO,
    product_service: ProductService = Depends(get_product_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Update product details."""
    product, error = await product_service.update_product(product_id, dto)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return product


@router.delete(
    "/{product_id}",
    summary="Delete product",
    dependencies=[require_permission(Permission.PRODUCT_DELETE)],
)
async def delete_product(
    product_id: UUID,
    product_service: ProductService = Depends(get_product_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Delete product (soft delete)."""
    success, error = await product_service.delete_product(product_id)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Product deleted"}


@router.post(
    "/{product_id}/publish",
    summary="Publish product",
    dependencies=[require_permission(Permission.PRODUCT_WRITE)],
)
async def publish_product(
    product_id: UUID,
    product_service: ProductService = Depends(get_product_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Publish product to make it active."""
    success, error = await product_service.publish_product(product_id)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Product published"}


@router.post(
    "/{product_id}/variants",
    response_model=ProductVariantDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Add product variant",
    dependencies=[require_permission(Permission.PRODUCT_WRITE)],
)
async def add_variant(
    product_id: UUID,
    size: Optional[str] = None,
    color: Optional[str] = None,
    color_hex: Optional[str] = None,
    sku: Optional[str] = None,
    price_adjustment: float = 0.0,
    inventory_quantity: int = 0,
    image_url: Optional[str] = None,
    product_service: ProductService = Depends(get_product_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Add variant to product."""
    variant, error = await product_service.add_variant(
        product_id=product_id,
        size=size,
        color=color,
        color_hex=color_hex,
        sku=sku,
        price_adjustment=price_adjustment,
        inventory_quantity=inventory_quantity,
        image_url=image_url,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return variant


@router.patch(
    "/variants/{variant_id}/inventory",
    summary="Update inventory",
    dependencies=[require_permission(Permission.PRODUCT_MANAGE)],
)
async def update_inventory(
    variant_id: UUID,
    quantity: int,
    operation: str = "set",  # set, add, subtract
    product_service: ProductService = Depends(get_product_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Update variant inventory."""
    success, error = await product_service.update_inventory(
        variant_id, quantity, operation
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Inventory updated"}
