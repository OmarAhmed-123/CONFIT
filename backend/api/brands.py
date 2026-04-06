"""
CONFIT Backend - Brand API Routes
=================================
Brand management, analytics, and inventory.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import (
    get_brand_service, get_current_user, get_current_user_optional,
    require_brand_manager
)
from application.services.brand_service import (
    BrandService,
    BrandCreateDTO,
    BrandUpdateDTO,
    BrandDTO,
    BrandAnalyticsDTO,
    BrandDashboardDTO,
    InventoryStatusDTO,
)
from core.security.rbac import AuthContext, Role


router = APIRouter(prefix="/brands", tags=["Brands"])


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    summary="Search brands",
)
async def search_brands(
    query: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    brand_service: BrandService = Depends(get_brand_service),
):
    """Search brands."""
    return await brand_service.search_brands(
        query=query or "",
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{brand_id}",
    response_model=BrandDTO,
    summary="Get brand by ID",
)
async def get_brand(
    brand_id: str,
    brand_service: BrandService = Depends(get_brand_service),
):
    """Get brand details by ID."""
    brand = await brand_service.get_brand(brand_id)
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    return brand


@router.get(
    "/slug/{slug}",
    response_model=BrandDTO,
    summary="Get brand by slug",
)
async def get_brand_by_slug(
    slug: str,
    brand_service: BrandService = Depends(get_brand_service),
):
    """Get brand details by slug."""
    brand = await brand_service.get_brand_by_slug(slug)
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    return brand


@router.post(
    "/{brand_id}/follow",
    summary="Follow brand",
)
async def follow_brand(
    brand_id: str,
    brand_service: BrandService = Depends(get_brand_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Follow a brand."""
    from uuid import UUID
    success, error = await brand_service.follow_brand(
        brand_id=brand_id,
        user_id=UUID(current_user.user_id),
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Brand followed"}


@router.delete(
    "/{brand_id}/follow",
    summary="Unfollow brand",
)
async def unfollow_brand(
    brand_id: str,
    brand_service: BrandService = Depends(get_brand_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Unfollow a brand."""
    from uuid import UUID
    success, error = await brand_service.unfollow_brand(
        brand_id=brand_id,
        user_id=UUID(current_user.user_id),
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Brand unfollowed"}


# ─────────────────────────────────────────────────────────────────────────────
# BRAND CREATION & MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=BrandDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create brand",
)
async def create_brand(
    dto: BrandCreateDTO,
    brand_service: BrandService = Depends(get_brand_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Create a new brand."""
    from uuid import UUID
    brand, error = await brand_service.create_brand(
        dto=dto,
        owner_id=UUID(current_user.user_id),
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return brand


@router.patch(
    "/{brand_id}",
    response_model=BrandDTO,
    summary="Update brand",
)
async def update_brand(
    brand_id: str,
    dto: BrandUpdateDTO,
    brand_service: BrandService = Depends(get_brand_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Update brand details."""
    from uuid import UUID
    brand, error = await brand_service.update_brand(
        brand_id=brand_id,
        dto=dto,
        user_id=UUID(current_user.user_id),
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return brand


@router.post(
    "/{brand_id}/managers",
    summary="Add brand manager",
)
async def add_brand_manager(
    brand_id: str,
    user_id: str,
    role: str = "manager",
    brand_service: BrandService = Depends(get_brand_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Add manager to brand."""
    from uuid import UUID
    success, error = await brand_service.add_brand_manager(
        brand_id=brand_id,
        user_id=UUID(user_id),
        role=role,
        added_by=UUID(current_user.user_id),
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Manager added"}


@router.delete(
    "/{brand_id}/managers/{user_id}",
    summary="Remove brand manager",
)
async def remove_brand_manager(
    brand_id: str,
    user_id: str,
    brand_service: BrandService = Depends(get_brand_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Remove manager from brand."""
    from uuid import UUID
    success, error = await brand_service.remove_brand_manager(
        brand_id=brand_id,
        user_id=UUID(user_id),
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Manager removed"}


# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{brand_id}/analytics",
    response_model=BrandAnalyticsDTO,
    summary="Get brand analytics",
)
async def get_brand_analytics(
    brand_id: str,
    period_days: int = Query(30, ge=1, le=365),
    brand_service: BrandService = Depends(get_brand_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get brand analytics for period."""
    from uuid import UUID
    
    analytics = await brand_service.get_brand_analytics(
        brand_id=brand_id,
        period_days=period_days,
    )
    
    return analytics


@router.get(
    "/{brand_id}/dashboard",
    response_model=BrandDashboardDTO,
    summary="Get brand dashboard",
)
async def get_brand_dashboard(
    brand_id: str,
    brand_service: BrandService = Depends(get_brand_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get brand dashboard summary."""
    from uuid import UUID
    
    dashboard = await brand_service.get_brand_dashboard(
        brand_id=brand_id,
        user_id=UUID(current_user.user_id),
    )
    
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return dashboard


@router.get(
    "/{brand_id}/inventory",
    summary="Get inventory status",
)
async def get_inventory_status(
    brand_id: str,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    brand_service: BrandService = Depends(get_brand_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get inventory status for all brand products."""
    from uuid import UUID
    return await brand_service.get_inventory_status(
        brand_id=brand_id,
        user_id=UUID(current_user.user_id),
        status=status,
        page=page,
        page_size=page_size,
    )
