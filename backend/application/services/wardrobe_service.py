"""
CONFIT Backend - Virtual Wardrobe Application Service
======================================================
User wardrobe management with auto-tagging and outfit suggestions.
"""

import os
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities import WardrobeItem, Outfit
from domain.base import Money
from infrastructure.elasticsearch import ElasticsearchService, get_elasticsearch_client
from database.models import WardrobeItem as WardrobeItemModel, Outfit as OutfitModel


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DTOs
# ─────────────────────────────────────────────────────────────────────────────

class WardrobeItemCreateDTO(BaseModel):
    """Wardrobe item creation DTO."""
    name: str
    product_id: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    color: Optional[str] = None
    color_hex: Optional[str] = None
    size: Optional[str] = None
    material: Optional[str] = None
    pattern: Optional[str] = None
    style_tags: List[str] = []
    occasion_tags: List[str] = []
    image_url: Optional[str] = None
    images: List[str] = []
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = None
    purchase_store: Optional[str] = None


class WardrobeItemUpdateDTO(BaseModel):
    """Wardrobe item update DTO."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    style_tags: Optional[List[str]] = None
    occasion_tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_favorite: Optional[bool] = None


class WardrobeItemDTO(BaseModel):
    """Wardrobe item response DTO."""
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    color: Optional[str] = None
    color_hex: Optional[str] = None
    size: Optional[str] = None
    material: Optional[str] = None
    pattern: Optional[str] = None
    style_tags: List[str] = []
    occasion_tags: List[str] = []
    image_url: Optional[str] = None
    images: List[str] = []
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = None
    purchase_store: Optional[str] = None
    wear_count: int = 0
    last_worn_at: Optional[datetime] = None
    is_active: bool = True
    is_favorite: bool = False
    auto_tags: List[str] = []
    auto_category: Optional[str] = None
    auto_color: Optional[str] = None
    auto_style: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OutfitCreateDTO(BaseModel):
    """Outfit creation DTO."""
    name: str
    description: Optional[str] = None
    item_ids: List[str] = []
    occasion: Optional[str] = None
    season: Optional[str] = None
    style_tags: List[str] = []
    image_url: Optional[str] = None
    is_public: bool = False


class OutfitDTO(BaseModel):
    """Outfit response DTO."""
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    items: List[WardrobeItemDTO] = []
    occasion: Optional[str] = None
    season: Optional[str] = None
    style_tags: List[str] = []
    image_url: Optional[str] = None
    estimated_value: Optional[float] = None
    is_public: bool = False
    is_favorite: bool = False
    view_count: int = 0
    like_count: int = 0
    created_at: datetime
    updated_at: datetime


class OutfitSuggestionDTO(BaseModel):
    """Outfit suggestion DTO."""
    items: List[WardrobeItemDTO]
    occasion: str
    style_score: float
    color_harmony_score: float
    overall_score: float
    reasoning: str


# ─────────────────────────────────────────────────────────────────────────────
# WARDROBE SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class WardrobeService:
    """Virtual wardrobe service with AI-powered features."""
    
    CATEGORIES = [
        "tops", "bottoms", "dresses", "outerwear", "footwear",
        "accessories", "bags", "jewelry", "activewear", "swimwear",
        "sleepwear", "underwear", "hats", "scarves", "belts"
    ]
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._search: Optional[ElasticsearchService] = None
    
    async def _get_search(self) -> ElasticsearchService:
        """Get Elasticsearch service."""
        if self._search is None:
            self._search = ElasticsearchService(await get_elasticsearch_client())
        return self._search
    
    # ─────────────────────────────────────────────────────────────────────────
    # WARDROBE ITEMS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def add_item(
        self,
        user_id: UUID,
        dto: WardrobeItemCreateDTO,
    ) -> Tuple[Optional[WardrobeItemDTO], Optional[str]]:
        """Add item to wardrobe."""
        item = WardrobeItemModel(
            user_id=str(user_id),
            product_id=dto.product_id,
            name=dto.name,
            description=dto.description,
            category=dto.category,
            brand=dto.brand,
            color=dto.color,
            color_hex=dto.color_hex,
            size=dto.size,
            material=dto.material,
            pattern=dto.pattern,
            style_tags=dto.style_tags,
            occasion_tags=dto.occasion_tags,
            image_url=dto.image_url,
            images=dto.images,
            purchase_date=dto.purchase_date,
            purchase_price=Decimal(str(dto.purchase_price)) if dto.purchase_price else None,
            purchase_store=dto.purchase_store,
        )
        
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        
        # Auto-tag if image provided
        if dto.image_url and not dto.style_tags:
            auto_tags = await self._auto_tag_item(dto.image_url)
            item.auto_tags = auto_tags["tags"]
            item.auto_category = auto_tags.get("category")
            item.auto_color = auto_tags.get("color")
            item.auto_style = auto_tags.get("style")
            await self.session.flush()
        
        # Index in Elasticsearch
        await self._index_wardrobe_item(item)
        
        logger.info(f"Wardrobe item added: {item.id}")
        
        return self._item_to_dto(item), None
    
    async def update_item(
        self,
        user_id: UUID,
        item_id: UUID,
        dto: WardrobeItemUpdateDTO,
    ) -> Tuple[Optional[WardrobeItemDTO], Optional[str]]:
        """Update wardrobe item."""
        item = await self._get_item_model(item_id)
        
        if not item:
            return None, "Item not found"
        
        if item.user_id != str(user_id):
            return None, "Unauthorized"
        
        update_data = dto.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)
        
        item.updated_at = datetime.now(timezone.utc)
        
        await self.session.flush()
        await self.session.refresh(item)
        
        # Update Elasticsearch index
        await self._index_wardrobe_item(item)
        
        return self._item_to_dto(item), None
    
    async def delete_item(
        self,
        user_id: UUID,
        item_id: UUID,
    ) -> Tuple[bool, Optional[str]]:
        """Delete wardrobe item."""
        item = await self._get_item_model(item_id)
        
        if not item:
            return False, "Item not found"
        
        if item.user_id != str(user_id):
            return False, "Unauthorized"
        
        # Remove from outfits
        from sqlalchemy import delete
        stmt = delete(OutfitItemModel).where(OutfitItemModel.item_id == str(item_id))
        await self.session.execute(stmt)
        
        await self.session.delete(item)
        await self.session.flush()
        
        return True, None
    
    async def get_item(
        self,
        user_id: UUID,
        item_id: UUID,
    ) -> Optional[WardrobeItemDTO]:
        """Get wardrobe item by ID."""
        item = await self._get_item_model(item_id)
        
        if not item or item.user_id != str(user_id):
            return None
        
        return self._item_to_dto(item)
    
    async def get_user_wardrobe(
        self,
        user_id: UUID,
        category: Optional[str] = None,
        is_favorite: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """Get user's wardrobe with filters."""
        query = (
            select(WardrobeItemModel)
            .where(
                WardrobeItemModel.user_id == str(user_id),
                WardrobeItemModel.is_active == True,
            )
        )
        
        if category:
            query = query.where(WardrobeItemModel.category == category)
        
        if is_favorite is not None:
            query = query.where(WardrobeItemModel.is_favorite == is_favorite)
        
        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Paginate
        query = query.order_by(WardrobeItemModel.is_favorite.desc(), WardrobeItemModel.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        # Get category breakdown
        category_query = (
            select(
                WardrobeItemModel.category,
                func.count(WardrobeItemModel.id).label("count")
            )
            .where(WardrobeItemModel.user_id == str(user_id))
            .group_by(WardrobeItemModel.category)
        )
        category_result = await self.session.execute(category_query)
        categories = {row.category: row.count for row in category_result}
        
        return {
            "items": [self._item_to_dto(i) for i in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "categories": categories,
        }
    
    async def record_wear(
        self,
        user_id: UUID,
        item_id: UUID,
    ) -> Tuple[bool, Optional[str]]:
        """Record that an item was worn."""
        item = await self._get_item_model(item_id)
        
        if not item:
            return False, "Item not found"
        
        if item.user_id != str(user_id):
            return False, "Unauthorized"
        
        item.wear_count += 1
        item.last_worn_at = datetime.now(timezone.utc)
        
        await self.session.flush()
        
        return True, None
    
    async def toggle_favorite(
        self,
        user_id: UUID,
        item_id: UUID,
    ) -> Tuple[bool, Optional[str]]:
        """Toggle favorite status."""
        item = await self._get_item_model(item_id)
        
        if not item:
            return False, "Item not found"
        
        if item.user_id != str(user_id):
            return False, "Unauthorized"
        
        item.is_favorite = not item.is_favorite
        await self.session.flush()
        
        return True, None
    
    # ─────────────────────────────────────────────────────────────────────────
    # OUTFITS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def create_outfit(
        self,
        user_id: UUID,
        dto: OutfitCreateDTO,
    ) -> Tuple[Optional[OutfitDTO], Optional[str]]:
        """Create outfit from wardrobe items."""
        # Validate items belong to user
        items = []
        estimated_value = Decimal("0")
        
        for item_id in dto.item_ids:
            item = await self._get_item_model(UUID(item_id))
            if not item or item.user_id != str(user_id):
                return None, f"Invalid item: {item_id}"
            items.append(item)
            if item.purchase_price:
                estimated_value += item.purchase_price
        
        outfit = OutfitModel(
            user_id=str(user_id),
            name=dto.name,
            description=dto.description,
            occasion=dto.occasion,
            season=dto.season,
            style_tags=dto.style_tags,
            image_url=dto.image_url,
            estimated_value=estimated_value,
            is_public=dto.is_public,
        )
        
        self.session.add(outfit)
        await self.session.flush()
        await self.session.refresh(outfit)
        
        # Add items to outfit
        for item in items:
            outfit_item = OutfitItemModel(
                outfit_id=outfit.id,
                item_id=item.id,
            )
            self.session.add(outfit_item)
        
        await self.session.flush()
        await self.session.refresh(outfit)
        
        logger.info(f"Outfit created: {outfit.id}")
        
        return await self._outfit_to_dto(outfit), None
    
    async def get_outfit(
        self,
        user_id: UUID,
        outfit_id: UUID,
    ) -> Optional[OutfitDTO]:
        """Get outfit by ID."""
        query = (
            select(OutfitModel)
            .options(selectinload(OutfitModel.items))
            .where(OutfitModel.id == str(outfit_id))
        )
        result = await self.session.execute(query)
        outfit = result.scalar_one_or_none()
        
        if not outfit:
            return None
        
        # Check access
        if outfit.user_id != str(user_id) and not outfit.is_public:
            return None
        
        return await self._outfit_to_dto(outfit)
    
    async def get_user_outfits(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Get user's outfits."""
        query = (
            select(OutfitModel)
            .options(selectinload(OutfitModel.items))
            .where(OutfitModel.user_id == str(user_id))
        )
        
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(OutfitModel.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.session.execute(query)
        outfits = result.scalars().all()
        
        return {
            "items": [await self._outfit_to_dto(o) for o in outfits],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    
    async def delete_outfit(
        self,
        user_id: UUID,
        outfit_id: UUID,
    ) -> Tuple[bool, Optional[str]]:
        """Delete outfit."""
        query = select(OutfitModel).where(OutfitModel.id == str(outfit_id))
        result = await self.session.execute(query)
        outfit = result.scalar_one_or_none()
        
        if not outfit:
            return False, "Outfit not found"
        
        if outfit.user_id != str(user_id):
            return False, "Unauthorized"
        
        await self.session.delete(outfit)
        await self.session.flush()
        
        return True, None
    
    # ─────────────────────────────────────────────────────────────────────────
    # OUTFIT SUGGESTIONS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def suggest_outfits(
        self,
        user_id: UUID,
        occasion: Optional[str] = None,
        season: Optional[str] = None,
        style_preference: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[OutfitSuggestionDTO]:
        """
        Generate outfit suggestions based on user's wardrobe.
        
        Uses AI to match items by style, color harmony, and occasion.
        """
        # Get user's wardrobe items
        query = (
            select(WardrobeItemModel)
            .where(
                WardrobeItemModel.user_id == str(user_id),
                WardrobeItemModel.is_active == True,
            )
        )
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        if len(items) < 3:
            return []
        
        suggestions = []
        
        # Generate outfit combinations
        # In production, use ML model for better recommendations
        combinations = self._generate_combinations(items, occasion, season, style_preference)
        
        for combo in combinations[:limit]:
            suggestion = OutfitSuggestionDTO(
                items=[self._item_to_dto(i) for i in combo["items"]],
                occasion=combo["occasion"],
                style_score=combo["style_score"],
                color_harmony_score=combo["color_harmony"],
                overall_score=combo["overall_score"],
                reasoning=combo["reasoning"],
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_combinations(
        self,
        items: List[WardrobeItemModel],
        occasion: Optional[str],
        season: Optional[str],
        style_preference: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """Generate outfit combinations from items."""
        combinations = []
        
        # Group items by category
        by_category = {}
        for item in items:
            cat = item.category or "other"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(item)
        
        # Generate basic combinations
        # Top + Bottom combination
        if "tops" in by_category and "bottoms" in by_category:
            for top in by_category["tops"][:5]:
                for bottom in by_category["bottoms"][:5]:
                    style_score = self._calculate_style_match(top, bottom, style_preference)
                    color_harmony = self._calculate_color_harmony(top, bottom)
                    
                    combinations.append({
                        "items": [top, bottom],
                        "occasion": occasion or "casual",
                        "style_score": style_score,
                        "color_harmony": color_harmony,
                        "overall_score": (style_score + color_harmony) / 2,
                        "reasoning": f"{top.name} pairs well with {bottom.name} for a {occasion or 'casual'} look",
                    })
        
        # Dress + Accessories combination
        if "dresses" in by_category:
            for dress in by_category["dresses"][:5]:
                accessories = by_category.get("accessories", [])[:2]
                style_score = 0.8
                color_harmony = 0.85
                
                combo_items = [dress] + accessories
                combinations.append({
                    "items": combo_items,
                    "occasion": occasion or "everyday",
                    "style_score": style_score,
                    "color_harmony": color_harmony,
                    "overall_score": (style_score + color_harmony) / 2,
                    "reasoning": f"{dress.name} creates a complete look",
                })
        
        # Sort by overall score
        combinations.sort(key=lambda x: x["overall_score"], reverse=True)
        
        return combinations
    
    def _calculate_style_match(
        self,
        item1: WardrobeItemModel,
        item2: WardrobeItemModel,
        style_preference: Optional[List[str]],
    ) -> float:
        """Calculate style compatibility between items."""
        tags1 = set(item1.style_tags or [])
        tags2 = set(item2.style_tags or [])
        
        if not tags1 or not tags2:
            return 0.5
        
        overlap = len(tags1 & tags2)
        total = len(tags1 | tags2)
        
        base_score = overlap / total if total > 0 else 0.5
        
        # Boost if matches user preference
        if style_preference:
            pref_match = len((tags1 | tags2) & set(style_preference))
            base_score += pref_match * 0.1
        
        return min(base_score, 1.0)
    
    def _calculate_color_harmony(
        self,
        item1: WardrobeItemModel,
        item2: WardrobeItemModel,
    ) -> float:
        """Calculate color harmony between items."""
        # Simple color matching (in production, use color theory)
        color1 = item1.color
        color2 = item2.color
        
        if not color1 or not color2:
            return 0.7
        
        # Neutral colors go with everything
        neutrals = {"black", "white", "gray", "navy", "beige", "brown"}
        
        if color1 in neutrals or color2 in neutrals:
            return 0.9
        
        if color1 == color2:
            return 0.95  # Monochromatic
        
        # Complementary colors (simplified)
        complementary = {
            "blue": "orange",
            "red": "green",
            "yellow": "purple",
        }
        
        if complementary.get(color1) == color2 or complementary.get(color2) == color1:
            return 0.85
        
        return 0.6  # Default harmony
    
    # ─────────────────────────────────────────────────────────────────────────
    # AUTO-TAGGING
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _auto_tag_item(self, image_url: str) -> Dict[str, Any]:
        """Auto-tag wardrobe item from image using AI."""
        # In production, integrate with:
        # - Google Vision API
        # - AWS Rekognition
        # - Custom ML models
        
        return {
            "tags": ["casual", "everyday", "versatile"],
            "category": "tops",
            "color": "blue",
            "style": "minimalist",
        }
    
    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE METHODS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _get_item_model(self, item_id: UUID) -> Optional[WardrobeItemModel]:
        """Get wardrobe item model."""
        query = select(WardrobeItemModel).where(WardrobeItemModel.id == str(item_id))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def _index_wardrobe_item(self, item: WardrobeItemModel) -> None:
        """Index wardrobe item in Elasticsearch."""
        search = await self._get_search()
        
        await search.index_wardrobe_item({
            "id": item.id,
            "user_id": item.user_id,
            "name": item.name,
            "category": item.category,
            "brand": item.brand,
            "color": item.color,
            "color_hex": item.color_hex,
            "style_tags": item.style_tags or [],
            "occasion_tags": item.occasion_tags or [],
            "image_url": item.image_url,
            "auto_tags": item.auto_tags or [],
            "is_active": item.is_active,
            "is_favorite": item.is_favorite,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })
    
    def _item_to_dto(self, model: WardrobeItemModel) -> WardrobeItemDTO:
        """Convert item model to DTO."""
        return WardrobeItemDTO(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            description=model.description,
            category=model.category,
            brand=model.brand,
            color=model.color,
            color_hex=model.color_hex,
            size=model.size,
            material=model.material,
            pattern=model.pattern,
            style_tags=model.style_tags or [],
            occasion_tags=model.occasion_tags or [],
            image_url=model.image_url,
            images=model.images or [],
            purchase_date=model.purchase_date,
            purchase_price=float(model.purchase_price) if model.purchase_price else None,
            purchase_store=model.purchase_store,
            wear_count=model.wear_count,
            last_worn_at=model.last_worn_at,
            is_active=model.is_active,
            is_favorite=model.is_favorite,
            auto_tags=model.auto_tags or [],
            auto_category=model.auto_category,
            auto_color=model.auto_color,
            auto_style=model.auto_style,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    async def _outfit_to_dto(self, model: OutfitModel) -> OutfitDTO:
        """Convert outfit model to DTO."""
        items = []
        
        # Load items
        if model.items:
            for outfit_item in model.items:
                item = await self._get_item_model(UUID(outfit_item.item_id))
                if item:
                    items.append(self._item_to_dto(item))
        
        return OutfitDTO(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            description=model.description,
            items=items,
            occasion=model.occasion,
            season=model.season,
            style_tags=model.style_tags or [],
            image_url=model.image_url,
            estimated_value=float(model.estimated_value) if model.estimated_value else None,
            is_public=model.is_public,
            is_favorite=model.is_favorite,
            view_count=model.view_count,
            like_count=model.like_count,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
