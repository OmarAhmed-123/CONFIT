"""CONFIT Backend — Wardrobe Repository."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from repositories.base import BaseRepository
from database.models import WardrobeItem, WardrobeItemUsage, Outfit


class WardrobeRepository(BaseRepository[WardrobeItem]):
    """Repository for WardrobeItem entity operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, WardrobeItem)
    
    def get_by_user(
        self,
        user_id: str,
        category: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WardrobeItem]:
        """Get wardrobe items by user with optional category filter."""
        query = self._db.query(WardrobeItem).filter(
            WardrobeItem.owner_user_id == user_id,
        )
        
        if category:
            query = query.filter(WardrobeItem.category == category)
        
        return query.offset(offset).limit(limit).all()
    
    def get_with_usage(self, item_id: str) -> Optional[WardrobeItem]:
        """Get wardrobe item with usage data."""
        return self._db.query(WardrobeItem).options(
            joinedload(WardrobeItem.usage),
        ).filter(WardrobeItem.id == item_id).first()
    
    def get_by_category(self, user_id: str, category: str) -> List[WardrobeItem]:
        """Get items by category for a user."""
        return self._db.query(WardrobeItem).filter(
            WardrobeItem.owner_user_id == user_id,
            WardrobeItem.category == category,
        ).all()
    
    def get_recently_worn(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 20,
    ) -> List[WardrobeItem]:
        """Get recently worn items."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        return self._db.query(WardrobeItem).join(
            WardrobeItemUsage,
            isouter=True,
        ).filter(
            WardrobeItem.owner_user_id == user_id,
            WardrobeItemUsage.last_worn_at >= cutoff,
        ).order_by(
            WardrobeItemUsage.last_worn_at.desc(),
        ).limit(limit).all()
    
    def get_never_worn(self, user_id: str) -> List[WardrobeItem]:
        """Get items that have never been worn."""
        return self._db.query(WardrobeItem).outerjoin(
            WardrobeItemUsage,
        ).filter(
            WardrobeItem.owner_user_id == user_id,
            or_(
                WardrobeItemUsage.id == None,
                WardrobeItemUsage.wear_count == 0,
            ),
        ).all()
    
    def get_by_color(self, user_id: str, color: str) -> List[WardrobeItem]:
        """Get items by color."""
        return self._db.query(WardrobeItem).filter(
            WardrobeItem.owner_user_id == user_id,
            WardrobeItem.color.ilike(f"%{color}%"),
        ).all()
    
    def get_by_brand(self, user_id: str, brand: str) -> List[WardrobeItem]:
        """Get items by brand."""
        return self._db.query(WardrobeItem).filter(
            WardrobeItem.owner_user_id == user_id,
            WardrobeItem.brand.ilike(f"%{brand}%"),
        ).all()
    
    def count_by_category(self, user_id: str) -> Dict[str, int]:
        """Count items per category for user."""
        results = self._db.query(
            WardrobeItem.category,
            func.count(WardrobeItem.id),
        ).filter(
            WardrobeItem.owner_user_id == user_id,
        ).group_by(WardrobeItem.category).all()
        
        return {cat: count for cat, count in results if cat}
    
    def get_total_value(self, user_id: str) -> float:
        """Get total wardrobe value."""
        result = self._db.query(
            func.sum(WardrobeItem.price),
        ).filter(
            WardrobeItem.owner_user_id == user_id,
            WardrobeItem.price != None,
        ).scalar()
        
        return float(result or 0)
    
    def record_wear(self, item_id: str) -> Optional[WardrobeItemUsage]:
        """Record a wear event for an item."""
        usage = self._db.query(WardrobeItemUsage).filter(
            WardrobeItemUsage.item_id == item_id,
        ).first()
        
        if usage:
            usage.wear_count += 1
            usage.last_worn_at = datetime.now(timezone.utc)
        else:
            usage = WardrobeItemUsage(
                item_id=item_id,
                wear_count=1,
                last_worn_at=datetime.now(timezone.utc),
            )
            self._db.add(usage)
        
        self._db.commit()
        self._db.refresh(usage)
        return usage
    
    def get_outfits_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Outfit]:
        """Get outfits for user."""
        return self._db.query(Outfit).filter(
            Outfit.user_id == user_id,
        ).order_by(Outfit.created_at.desc()).offset(offset).limit(limit).all()
    
    def create_outfit(
        self,
        user_id: str,
        item_ids: List[str],
        name: str = None,
        occasion: str = None,
    ) -> Outfit:
        """Create a new outfit from wardrobe items."""
        items = self._db.query(WardrobeItem).filter(
            WardrobeItem.id.in_(item_ids),
        ).all()
        
        outfit = Outfit(
            user_id=user_id,
            name=name,
            occasion=occasion,
            items=items,
        )
        self._db.add(outfit)
        self._db.commit()
        self._db.refresh(outfit)
        return outfit
