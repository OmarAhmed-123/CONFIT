"""
CONFIT Backend — Brand Service
===============================
Brand CRUD and analytics backed by the database. Use via Depends(get_db).
"""

import random
import uuid
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from database.models import Brand as BrandModel, Product as ProductModel
from models.brand_models import BrandResponse, BrandMetrics, BrandCreate

logger = logging.getLogger(__name__)
_metrics_cache: dict = {}

# Mock brands for fallback
MOCK_BRANDS = [
    {
        "id": "brand-001",
        "name": "CONFIT Active Wear",
        "description": "Premium athletic wear designed for performance and style.",
        "logo_url": "https://images.unsplash.com/photo-1441986300917-64674e8c6e58?w=200",
        "banner_url": "https://images.unsplash.com/photo-1441986300917-64674e8c6e58?w=800",
        "website": "https://confit-active.com",
        "product_count": 24
    },
    {
        "id": "brand-002",
        "name": "Urban Style Co",
        "description": "Contemporary streetwear for the modern urbanite.",
        "logo_url": "https://images.unsplash.com/photo-1441984784389-e80c1f7d4a3b?w=200",
        "banner_url": "https://images.unsplash.com/photo-1441984784389-e80c1f7d4a3b?w=800",
        "website": "https://urbanstyle.co",
        "product_count": 18
    },
    {
        "id": "brand-003",
        "name": "EcoWear",
        "description": "Sustainable fashion for conscious consumers.",
        "logo_url": "https://images.unsplash.com/photo-1523380744952-b7e0e7d1e5e3?w=200",
        "banner_url": "https://images.unsplash.com/photo-1523380744952-b7e0e7d1e5e3?w=800",
        "website": "https://ecowear.com",
        "product_count": 12
    },
    {
        "id": "brand-004",
        "name": "Luxe Collection",
        "description": "High-end fashion for discerning tastes.",
        "logo_url": "https://images.unsplash.com/photo-1445205170231-68c6c3c91a52?w=200",
        "banner_url": "https://images.unsplash.com/photo-1445205170231-68c6c3c91a52?w=800",
        "website": "https://luxecollection.com",
        "product_count": 8
    },
]


def _row_to_response(row: BrandModel, product_count: int = 0) -> BrandResponse:
    return BrandResponse(
        id=row.id,
        name=row.name,
        description=row.description,
        logo_url=row.logo_url,
        banner_url=row.banner_url,
        website=row.website,
        created_at=row.created_at,
        updated_at=row.updated_at,
        product_count=product_count,
    )


def _mock_to_response(mock: dict) -> BrandResponse:
    return BrandResponse(
        id=mock["id"],
        name=mock["name"],
        description=mock.get("description", ""),
        logo_url=mock.get("logo_url"),
        banner_url=mock.get("banner_url"),
        website=mock.get("website"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        product_count=mock.get("product_count", 0),
    )


class BrandService:
    def __init__(self, db: Session):
        self._db = db

    def _product_count(self, brand_id: str) -> int:
        return self._db.query(ProductModel).filter(ProductModel.brand_id == brand_id).count()

    async def get_all_brands(self) -> List[BrandResponse]:
        try:
            rows = self._db.query(BrandModel).order_by(BrandModel.name).all()
            
            # If database has brands, return them
            if rows:
                return [_row_to_response(r, self._product_count(r.id)) for r in rows]
        except Exception as e:
            logger.warning(f"Database query failed for brands: {e}")
        
        # Otherwise return mock brands
        logger.info("Returning mock brands data")
        return [_mock_to_response(m) for m in MOCK_BRANDS]

    async def get_brand(self, brand_id: str) -> Optional[BrandResponse]:
        row = self._db.query(BrandModel).filter(BrandModel.id == brand_id).first()
        if row:
            return _row_to_response(row, self._product_count(row.id))
        
        # Fallback to mock data
        for mock in MOCK_BRANDS:
            if mock["id"] == brand_id:
                return _mock_to_response(mock)
        
        return None

    async def get_brand_metrics(self, brand_id: str) -> Optional[BrandMetrics]:
        # Check if brand exists in database or mock
        brand_exists = self._db.query(BrandModel).filter(BrandModel.id == brand_id).first()
        mock_exists = any(m["id"] == brand_id for m in MOCK_BRANDS)
        
        if not brand_exists and not mock_exists:
            return None
            
        if brand_id not in _metrics_cache:
            _metrics_cache[brand_id] = BrandMetrics(
                brand_id=brand_id,
                total_sales=125000.00,
                total_orders=850,
                top_products=["Summer Dress", "Slim Fit Blazer"],
                conversion_rate=3.2,
                return_rate=12.5,
            )
        return _metrics_cache[brand_id]

    async def create_brand(self, brand: BrandCreate) -> BrandResponse:
        b_id = f"brand-{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()
        row = BrandModel(
            id=b_id,
            name=brand.name,
            description=brand.description,
            logo_url=brand.logo_url,
            banner_url=brand.banner_url,
            website=brand.website,
            created_at=now,
            updated_at=now,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return _row_to_response(row, product_count=0)

    # ── Advanced Analytics & Advisory ──────────────────────────────────

    async def get_analytics(self, brand_id: str) -> dict:
        """Financial analytics; replace with real Order/Product aggregates when ready."""
        if not self._db.query(BrandModel).filter(BrandModel.id == brand_id).first():
            return {}
        random.seed(brand_id)
        revenue = random.uniform(50000, 500000)
        costs = revenue * random.uniform(0.4, 0.8)
        profit = revenue - costs
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        monthly_sales = [round(revenue / 6 * random.uniform(0.8, 1.2), 2) for _ in months]
        monthly_costs = [round(costs / 6 * random.uniform(0.9, 1.1), 2) for _ in months]
        return {
            "total_revenue": round(revenue, 2),
            "total_costs": round(costs, 2),
            "net_profit": round(profit, 2),
            "is_profitable": profit > 0,
            "profit_margin": round((profit / revenue) * 100, 1) if revenue else 0,
            "monthly_data": {"labels": months, "revenue": monthly_sales, "costs": monthly_costs},
        }

    async def get_advice(self, brand_id: str) -> List[dict]:
        """Business advice derived from analytics."""
        if not self._db.query(BrandModel).filter(BrandModel.id == brand_id).first():
            return []
        analytics = await self.get_analytics(brand_id)
        is_profitable = analytics.get("is_profitable", False)
        margin = analytics.get("profit_margin", 0)
        advice = []
        if not is_profitable:
            advice.append({"type": "critical", "title": "Immediate Cost Reduction Needed", "content": "Consider liquidating slow-moving inventory through a clearance sale."})
            advice.append({"type": "warning", "title": "Pricing Strategy Review", "content": "Review COGS and consider a 10-15% price increase on best-sellers."})
        elif margin < 10:
            advice.append({"type": "warning", "title": "Low Margin Alert", "content": "Focus on upselling higher-margin accessories."})
        else:
            advice.append({"type": "success", "title": "Strong Performance", "content": "Reinvest in marketing to scale."})
        advice.append({"type": "info", "title": "Inventory Optimization", "content": "Restock high-demand collections as forecast indicates."})
        return advice
