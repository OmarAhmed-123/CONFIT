from typing import List, Optional
from fastapi import HTTPException
from services.brand_service import BrandService
from models.brand_models import BrandResponse, BrandMetrics, BrandCreate


class BrandController:
    def __init__(self, service: BrandService):
        self.service = service

    async def get_all_brands(self) -> List[BrandResponse]:
        return await self.service.get_all_brands()

    async def get_brand(self, brand_id: str) -> BrandResponse:
        brand = await self.service.get_brand(brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        return brand

    async def get_brand_metrics(self, brand_id: str) -> BrandMetrics:
        metrics = await self.service.get_brand_metrics(brand_id)
        if not metrics:
            raise HTTPException(status_code=404, detail="Metrics not found for this brand")
        return metrics

    async def create_brand(self, brand: BrandCreate) -> BrandResponse:
        return await self.service.create_brand(brand)

    async def get_analytics(self, brand_id: str) -> dict:
        return await self.service.get_analytics(brand_id)

    async def get_advice(self, brand_id: str) -> List[dict]:
        return await self.service.get_advice(brand_id)
