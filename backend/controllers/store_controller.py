from typing import List, Optional
from fastapi import HTTPException
from services.store_service import StoreService
from models.store_models import StoreResponse, StoreCreate


class StoreController:
    def __init__(self, service: StoreService):
        self.service = service

    async def get_stores(self, brand_id: Optional[str] = None) -> List[StoreResponse]:
        return await self.service.get_stores(brand_id)

    async def create_store(self, store: StoreCreate) -> StoreResponse:
        return await self.service.create_store(store)
