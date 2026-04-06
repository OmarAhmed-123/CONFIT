import random
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from controllers.store_controller import StoreController
from models.store_models import StoreResponse, StoreCreate, InventoryCheck
from services.auth_service import UserProfile
from services.store_service import StoreService
from utils.auth_deps import require_auth

router = APIRouter(prefix="/api/stores", tags=["stores"])


def get_store_service(db: Session = Depends(get_db)) -> StoreService:
    return StoreService(db)


def get_store_controller(service: StoreService = Depends(get_store_service)) -> StoreController:
    return StoreController(service)


@router.get("", response_model=List[StoreResponse])
async def get_stores(
    brand_id: Optional[str] = None,
    controller: StoreController = Depends(get_store_controller),
):
    """Get stores, optionally filtered by brand."""
    return await controller.get_stores(brand_id)


@router.post("", response_model=StoreResponse)
async def create_store(
    store: StoreCreate,
    user: UserProfile = Depends(require_auth),
    controller: StoreController = Depends(get_store_controller),
):
    """Register a new store location (authenticated)."""
    return await controller.create_store(store)


@router.post("/availability")
async def check_bopis_availability(
    request: InventoryCheck,
    store_service: StoreService = Depends(get_store_service),
):
    """
    Check BOPIS availability for a product at stores that offer it.
    Simulates inventory; replace with real stock when available.
    """
    results: List[dict] = []
    for store in store_service.get_stores_with_bopis():
        random.seed(f"{store.id}-{request.product_id}")
        available_qty = random.randint(0, max(request.quantity, 5))
        results.append({
            "storeId": store.id,
            "storeName": store.name,
            "available": available_qty >= request.quantity,
            "availableQuantity": available_qty,
        })
    return {
        "productId": request.product_id,
        "requestedQuantity": request.quantity,
        "stores": results,
    }
