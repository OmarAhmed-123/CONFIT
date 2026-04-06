"""CONFIT Backend — Product Repository."""

from typing import Optional, List, Dict, Any
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from repositories.base import BaseRepository
from database.models import Product, Brand, Store


class ProductRepository(BaseRepository[Product]):
    """Repository for Product entity operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, Product)
    
    def get_with_brand(self, product_id: str) -> Optional[Product]:
        """Get product with brand relationship loaded."""
        return self._db.query(Product).options(
            joinedload(Product.brand),
        ).filter(Product.id == product_id).first()
    
    def get_featured(
        self,
        limit: int = 12,
        gender: str = None,
        category: str = None,
    ) -> List[Product]:
        """Get featured products."""
        query = self._db.query(Product).filter(Product.is_active == True)
        
        if gender and gender in ['men', 'women']:
            query = query.filter(Product.tags.contains([gender]))
        
        if category:
            query = query.filter(Product.category == category)
        
        return query.order_by(
            Product.style_compatibility.desc()
        ).limit(limit).all()
    
    def search(
        self,
        query: str,
        category: str = None,
        min_price: Decimal = None,
        max_price: Decimal = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Product]:
        """Search products with filters."""
        q = self._db.query(Product).filter(Product.is_active == True)
        
        if query:
            q = q.filter(Product.name.ilike(f"%{query}%"))
        
        if category:
            q = q.filter(Product.category == category)
        
        if min_price is not None:
            q = q.filter(Product.price >= min_price)
        
        if max_price is not None:
            q = q.filter(Product.price <= max_price)
        
        return q.offset(offset).limit(limit).all()
    
    def get_by_brand(self, brand_id: str, limit: int = 50) -> List[Product]:
        """Get products by brand."""
        return self._db.query(Product).filter(
            Product.brand_id == brand_id,
            Product.is_active == True,
        ).limit(limit).all()
    
    def get_by_store(self, store_id: str, limit: int = 50) -> List[Product]:
        """Get products by store."""
        return self._db.query(Product).filter(
            Product.store_id == store_id,
            Product.is_active == True,
        ).limit(limit).all()
    
    def get_by_category(
        self,
        category: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Product]:
        """Get products by category."""
        return self._db.query(Product).filter(
            Product.category == category,
            Product.is_active == True,
        ).offset(offset).limit(limit).all()
    
    def get_by_price_range(
        self,
        min_price: Decimal,
        max_price: Decimal,
        limit: int = 50,
    ) -> List[Product]:
        """Get products within price range."""
        return self._db.query(Product).filter(
            Product.is_active == True,
            Product.price >= min_price,
            Product.price <= max_price,
        ).order_by(Product.price).limit(limit).all()
    
    def get_by_tags(self, tags: List[str], limit: int = 50) -> List[Product]:
        """Get products containing any of the specified tags."""
        return self._db.query(Product).filter(
            Product.is_active == True,
            or_(*[Product.tags.contains([tag]) for tag in tags]),
        ).limit(limit).all()
    
    def count_by_category(self) -> Dict[str, int]:
        """Count products per category."""
        from sqlalchemy import func
        
        results = self._db.query(
            Product.category,
            func.count(Product.id),
        ).filter(
            Product.is_active == True,
        ).group_by(Product.category).all()
        
        return {cat: count for cat, count in results}
    
    def update_stock(self, product_id: str, in_stock: bool) -> Optional[Product]:
        """Update product stock status."""
        return self.update(product_id, {"is_active": in_stock})
