from typing import List, Optional, Dict
from services.product_service import ProductService

class ProductController:
    def __init__(self):
        self.service = ProductService()

    async def get_all_products(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        brand_id: Optional[str] = None,
        gender: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        in_stock_only: bool = False,
    ) -> List[Dict]:
        return self.service.get_all(
            query=query,
            category=category,
            brand=brand,
            brand_id=brand_id,
            gender=gender,
            price_min=price_min,
            price_max=price_max,
            in_stock_only=in_stock_only
        )

    async def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        return self.service.get_by_id(product_id)

    async def get_featured_products(self, limit: int = 8, gender: Optional[str] = None) -> List[Dict]:
        return self.service.get_featured(limit, gender)

    async def get_trending_products(self, limit: int = 6, gender: Optional[str] = None) -> List[Dict]:
        return self.service.get_trending(limit, gender)

    async def create_product(self, product_data: Dict) -> Dict:
        return self.service.create(product_data)

    async def update_product(self, product_id: str, updates: Dict) -> Optional[Dict]:
        return self.service.update(product_id, updates)

    async def delete_product(self, product_id: str) -> bool:
        return self.service.delete(product_id)
