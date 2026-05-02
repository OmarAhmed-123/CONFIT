from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.models import AppRole, UserRole
from database.session import get_db
from controllers.brand_controller import BrandController
from models.brand_models import BrandResponse, BrandMetrics, BrandCreate
from services.auth_service import UserProfile
from services.brand_service import BrandService
from utils.auth_deps import require_auth

router = APIRouter(prefix="/api/brands", tags=["brands"])


def get_brand_service(db: Session = Depends(get_db)) -> BrandService:
    return BrandService(db)


def get_brand_controller(service: BrandService = Depends(get_brand_service)) -> BrandController:
    return BrandController(service)


def require_brand_staff(user: UserProfile = Depends(require_auth), db: Session = Depends(get_db)) -> UserProfile:
    roles = {row.role for row in db.query(UserRole).filter(UserRole.user_id == user.id).all()}
    if AppRole.admin in roles or AppRole.brand_manager in roles:
        return user
    raise HTTPException(status_code=403, detail="Brand staff access required")


@router.get("", response_model=List[BrandResponse])
async def get_all_brands(controller: BrandController = Depends(get_brand_controller)):
    """Get all registered brands."""
    return await controller.get_all_brands()


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(brand_id: str, controller: BrandController = Depends(get_brand_controller)):
    """Get specific brand details."""
    return await controller.get_brand(brand_id)


@router.get("/{brand_id}/metrics", response_model=BrandMetrics)
async def get_brand_metrics(
    brand_id: str,
    user: UserProfile = Depends(require_brand_staff),
    controller: BrandController = Depends(get_brand_controller),
):
    """Get restricted metrics for a brand (authenticated)."""
    return await controller.get_brand_metrics(brand_id)


@router.post("", response_model=BrandResponse)
async def create_brand(
    brand: BrandCreate,
    user: UserProfile = Depends(require_brand_staff),
    controller: BrandController = Depends(get_brand_controller),
):
    """Register a new brand (authenticated)."""
    return await controller.create_brand(brand)


@router.get("/{brand_id}/analytics")
async def get_brand_analytics(
    brand_id: str,
    user: UserProfile = Depends(require_brand_staff),
    controller: BrandController = Depends(get_brand_controller),
):
    """Get financial analytics for a brand (authenticated)."""
    return await controller.get_analytics(brand_id)


@router.get("/{brand_id}/advice")
async def get_brand_advice(
    brand_id: str,
    user: UserProfile = Depends(require_brand_staff),
    controller: BrandController = Depends(get_brand_controller),
):
    """Get AI-powered business advice for a brand (authenticated)."""
    return await controller.get_advice(brand_id)
