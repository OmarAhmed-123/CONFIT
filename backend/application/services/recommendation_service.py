"""
CONFIT Backend - Recommendation Engine Service
==============================================
AI-powered product recommendations based on user style, behavior, and preferences.
"""

import os
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities import StyleProfile, BrandAffinity
from domain.base import PaginatedResult
from infrastructure.elasticsearch import ElasticsearchService, get_elasticsearch_client
from infrastructure.redis_client import RedisCache, get_cache_client
from database.models import (
    User as UserModel,
    Product as ProductModel,
    Order as OrderModel,
    OrderItem as OrderItemModel,
    WardrobeItem as WardrobeItemModel,
)


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DTOs
# ─────────────────────────────────────────────────────────────────────────────

class RecommendationDTO(BaseModel):
    """Product recommendation DTO."""
    product_id: str
    name: str
    slug: str
    brand_name: Optional[str] = None
    category_name: Optional[str] = None
    image_url: Optional[str] = None
    price: float
    currency: str = "USD"
    score: float
    reasons: List[str] = []
    match_factors: Dict[str, float] = {}


class PersonalizedRecommendationsDTO(BaseModel):
    """Personalized recommendations response."""
    for_you: List[RecommendationDTO] = []
    because_you_liked: List[RecommendationDTO] = []
    trending: List[RecommendationDTO] = []
    new_arrivals: List[RecommendationDTO] = []
    complete_the_look: List[RecommendationDTO] = []
    style_matches: List[RecommendationDTO] = []


class StyleAnalysisDTO(BaseModel):
    """User style analysis."""
    primary_archetype: Optional[str] = None
    secondary_archetypes: List[str] = []
    style_vector: Dict[str, float] = {}
    color_preferences: Dict[str, Any] = {}
    pattern_preferences: List[str] = []
    fit_preference: str = "regular"
    confidence_score: float = 0.0
    recommendations_count: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# RECOMMENDATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class RecommendationEngine:
    """AI-powered recommendation engine."""
    
    CACHE_TTL = 3600  # 1 hour
    CACHE_PREFIX = "recommendations"
    
    # Style dimensions for matching
    STYLE_DIMENSIONS = [
        "classic", "trendy", "minimalist", "maximalist",
        "feminine", "masculine", "edgy", "romantic"
    ]
    
    # Color harmony rules
    COLOR_HARMONY = {
        "complementary": 0.9,
        "analogous": 0.85,
        "triadic": 0.8,
        "monochromatic": 0.95,
        "neutral": 0.9,
    }
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: Optional[RedisCache] = None
        self._search: Optional[ElasticsearchService] = None
    
    async def _get_cache(self) -> RedisCache:
        if self._cache is None:
            self._cache = RedisCache(await get_cache_client(), self.CACHE_PREFIX)
        return self._cache
    
    async def _get_search(self) -> ElasticsearchService:
        if self._search is None:
            self._search = ElasticsearchService(await get_elasticsearch_client())
        return self._search
    
    # ─────────────────────────────────────────────────────────────────────────
    # MAIN RECOMMENDATION METHODS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def get_personalized_recommendations(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> PersonalizedRecommendationsDTO:
        """
        Get personalized recommendations for user.
        
        Combines multiple recommendation strategies:
        - Collaborative filtering (users like you)
        - Content-based (style match)
        - Behavioral (purchase/view history)
        - Trending/popular items
        """
        cache = await self._get_cache()
        cache_key = f"personalized:{user_id}:{limit}"
        
        cached = await cache.get(cache_key)
        if cached:
            return PersonalizedRecommendationsDTO(**cached)
        
        # Get user profile data
        style_profile = await self._get_style_profile(user_id)
        brand_affinities = await self._get_brand_affinities(user_id)
        purchase_history = await self._get_purchase_history(user_id)
        wardrobe_items = await self._get_wardrobe_items(user_id)
        
        # Generate recommendations from different strategies
        for_you = await self._get_for_you_recommendations(
            user_id, style_profile, brand_affinities, purchase_history, limit
        )
        
        because_you_liked = await self._get_similar_to_purchases(
            purchase_history, limit
        )
        
        trending = await self._get_trending_products(limit)
        
        new_arrivals = await self._get_new_arrivals(limit)
        
        complete_the_look = await self._get_complete_the_look(
            wardrobe_items, style_profile, limit
        )
        
        style_matches = await self._get_style_matches(
            style_profile, limit
        )
        
        result = PersonalizedRecommendationsDTO(
            for_you=for_you,
            because_you_liked=because_you_liked,
            trending=trending,
            new_arrivals=new_arrivals,
            complete_the_look=complete_the_look,
            style_matches=style_matches,
        )
        
        await cache.set(cache_key, result.dict(), ttl=self.CACHE_TTL)
        
        return result
    
    async def get_similar_products(
        self,
        product_id: UUID,
        limit: int = 10,
    ) -> List[RecommendationDTO]:
        """Get similar products based on attributes."""
        search = await self._get_search()
        
        result = await search.similar_products(str(product_id), limit)
        hits = result.get("hits", {}).get("hits", [])
        
        recommendations = []
        for hit in hits:
            source = hit.get("_source", {})
            score = hit.get("_score", 0) / 10  # Normalize score
            
            recommendations.append(RecommendationDTO(
                product_id=source.get("id", ""),
                name=source.get("name", ""),
                slug=source.get("slug", ""),
                brand_name=source.get("brand_name"),
                category_name=source.get("category_name"),
                image_url=source.get("primary_image_url"),
                price=source.get("current_price", 0),
                currency=source.get("currency", "USD"),
                score=min(score, 1.0),
                reasons=["Similar style and attributes"],
                match_factors={"similarity": score},
            ))
        
        return recommendations
    
    async def get_style_based_recommendations(
        self,
        user_id: UUID,
        occasion: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 20,
    ) -> List[RecommendationDTO]:
        """Get recommendations based on user's style profile."""
        style_profile = await self._get_style_profile(user_id)
        
        if not style_profile:
            return await self._get_trending_products(limit)
        
        # Build search query based on style profile
        search = await self._get_search()
        
        filters = {
            "status": "active",
        }
        
        # Add style tags
        if style_profile.primary_archetype:
            filters["style_tags"] = [style_profile.primary_archetype]
        
        # Add color preferences
        if style_profile.preferred_colors:
            filters["color"] = style_profile.preferred_colors[0]
        
        # Add occasion filter
        if occasion:
            filters["occasion_tags"] = [occasion]
        
        # Add season filter
        if season:
            filters["season_tags"] = [season]
        
        result = await search.search_products(
            query="",
            filters=filters,
            page=1,
            page_size=limit,
        )
        
        hits = result.get("hits", {}).get("hits", [])
        
        recommendations = []
        for hit in hits:
            source = hit.get("_source", {})
            
            # Calculate style match score
            match_score = self._calculate_style_match_score(style_profile, source)
            
            recommendations.append(RecommendationDTO(
                product_id=source.get("id", ""),
                name=source.get("name", ""),
                slug=source.get("slug", ""),
                brand_name=source.get("brand_name"),
                category_name=source.get("category_name"),
                image_url=source.get("primary_image_url"),
                price=source.get("current_price", 0),
                currency=source.get("currency", "USD"),
                score=match_score,
                reasons=[f"Matches your {style_profile.primary_archetype} style"],
                match_factors={"style_match": match_score},
            ))
        
        # Sort by score
        recommendations.sort(key=lambda x: x.score, reverse=True)
        
        return recommendations
    
    async def get_complete_outfit_recommendations(
        self,
        product_id: UUID,
        user_id: UUID,
        limit: int = 5,
    ) -> List[RecommendationDTO]:
        """Get items that complete an outfit with the given product."""
        # Get the base product
        product = await self._get_product(product_id)
        if not product:
            return []
        
        # Get user's style profile
        style_profile = await self._get_style_profile(user_id)
        
        # Determine what category to recommend
        complementary_categories = self._get_complementary_categories(product.category)
        
        search = await self._get_search()
        
        filters = {
            "status": "active",
            "category_id": complementary_categories[0] if complementary_categories else None,
        }
        
        # Match style if available
        if style_profile and style_profile.primary_archetype:
            filters["style_tags"] = [style_profile.primary_archetype]
        
        result = await search.search_products(
            query="",
            filters=filters,
            page=1,
            page_size=limit,
        )
        
        hits = result.get("hits", {}).get("hits", [])
        
        recommendations = []
        for hit in hits:
            source = hit.get("_source", {})
            
            # Calculate color harmony with base product
            color_harmony = self._calculate_color_harmony(
                product.color, source.get("color")
            )
            
            recommendations.append(RecommendationDTO(
                product_id=source.get("id", ""),
                name=source.get("name", ""),
                slug=source.get("slug", ""),
                brand_name=source.get("brand_name"),
                category_name=source.get("category_name"),
                image_url=source.get("primary_image_url"),
                price=source.get("current_price", 0),
                currency=source.get("currency", "USD"),
                score=color_harmony,
                reasons=["Completes your outfit", "Color matches well"],
                match_factors={"color_harmony": color_harmony},
            ))
        
        return recommendations
    
    # ─────────────────────────────────────────────────────────────────────────
    # RECOMMENDATION STRATEGIES
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _get_for_you_recommendations(
        self,
        user_id: UUID,
        style_profile: Optional[StyleProfileModel],
        brand_affinities: List[BrandAffinityModel],
        purchase_history: List[Dict],
        limit: int,
    ) -> List[RecommendationDTO]:
        """Get personalized 'For You' recommendations."""
        search = await self._get_search()
        
        # Build weighted query
        filters = {"status": "active"}
        
        # Add style preferences
        if style_profile:
            if style_profile.primary_archetype:
                filters["style_tags"] = [style_profile.primary_archetype]
            if style_profile.preferred_colors:
                filters["color"] = style_profile.preferred_colors[:3]
        
        # Add brand preferences
        if brand_affinities:
            high_affinity_brands = [
                b.brand_id for b in brand_affinities
                if float(b.affinity_score) >= 0.7
            ]
            if high_affinity_brands:
                filters["brand_id"] = high_affinity_brands[:3]
        
        result = await search.search_products(
            query="",
            filters=filters,
            page=1,
            page_size=limit,
        )
        
        hits = result.get("hits", {}).get("hits", [])
        
        recommendations = []
        for hit in hits:
            source = hit.get("_source", {})
            
            # Calculate personalized score
            score = self._calculate_personalized_score(
                source, style_profile, brand_affinities, purchase_history
            )
            
            reasons = self._generate_recommendation_reasons(
                source, style_profile, brand_affinities
            )
            
            recommendations.append(RecommendationDTO(
                product_id=source.get("id", ""),
                name=source.get("name", ""),
                slug=source.get("slug", ""),
                brand_name=source.get("brand_name"),
                category_name=source.get("category_name"),
                image_url=source.get("primary_image_url"),
                price=source.get("current_price", 0),
                currency=source.get("currency", "USD"),
                score=score,
                reasons=reasons,
                match_factors={},
            ))
        
        recommendations.sort(key=lambda x: x.score, reverse=True)
        
        return recommendations
    
    async def _get_similar_to_purchases(
        self,
        purchase_history: List[Dict],
        limit: int,
    ) -> List[RecommendationDTO]:
        """Get products similar to previous purchases."""
        if not purchase_history:
            return []
        
        # Get last 5 purchased products
        recent_purchases = purchase_history[:5]
        
        search = await self._get_search()
        
        all_recommendations = []
        
        for purchase in recent_purchases:
            product_id = purchase.get("product_id")
            if product_id:
                similar = await self.get_similar_products(UUID(product_id), limit // 2)
                for rec in similar:
                    rec.reasons = [f"Similar to {purchase.get('product_name', 'your purchase')}"]
                all_recommendations.extend(similar)
        
        # Deduplicate and sort
        seen = set()
        unique = []
        for rec in all_recommendations:
            if rec.product_id not in seen:
                seen.add(rec.product_id)
                unique.append(rec)
        
        return unique[:limit]
    
    async def _get_trending_products(self, limit: int) -> List[RecommendationDTO]:
        """Get trending/popular products."""
        query = (
            select(ProductModel)
            .where(
                ProductModel.status == "active",
                ProductModel.is_active == True,
            )
            .order_by(
                ProductModel.purchase_count.desc(),
                ProductModel.view_count.desc(),
            )
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        products = result.scalars().all()
        
        recommendations = []
        for product in products:
            recommendations.append(RecommendationDTO(
                product_id=product.id,
                name=product.name,
                slug=product.slug,
                brand_name=None,  # Would load brand
                category_name=None,
                image_url=product.primary_image_url,
                price=float(product.base_price),
                currency=product.currency,
                score=0.85,
                reasons=["Trending now", f"{product.purchase_count} people bought this"],
                match_factors={"popularity": float(product.purchase_count) / 1000},
            ))
        
        return recommendations
    
    async def _get_new_arrivals(self, limit: int) -> List[RecommendationDTO]:
        """Get new arrival products."""
        query = (
            select(ProductModel)
            .where(
                ProductModel.status == "active",
                ProductModel.is_new_arrival == True,
                ProductModel.is_active == True,
            )
            .order_by(ProductModel.created_at.desc())
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        products = result.scalars().all()
        
        recommendations = []
        for product in products:
            recommendations.append(RecommendationDTO(
                product_id=product.id,
                name=product.name,
                slug=product.slug,
                brand_name=None,
                category_name=None,
                image_url=product.primary_image_url,
                price=float(product.base_price),
                currency=product.currency,
                score=0.80,
                reasons=["New arrival", "Just added to our collection"],
                match_factors={},
            ))
        
        return recommendations
    
    async def _get_complete_the_look(
        self,
        wardrobe_items: List[Dict],
        style_profile: Optional[StyleProfileModel],
        limit: int,
    ) -> List[RecommendationDTO]:
        """Get items to complete outfits from wardrobe."""
        if not wardrobe_items:
            return []
        
        # Get categories user has
        user_categories = set(i.get("category") for i in wardrobe_items if i.get("category"))
        
        # Find missing essential categories
        essential_categories = {"tops", "bottoms", "footwear", "outerwear"}
        missing = essential_categories - user_categories
        
        if not missing:
            return []
        
        search = await self._get_search()
        
        filters = {
            "status": "active",
        }
        
        # Recommend from missing categories
        missing_category = list(missing)[0]
        
        result = await search.search_products(
            query="",
            filters=filters,
            page=1,
            page_size=limit,
        )
        
        hits = result.get("hits", {}).get("hits", [])
        
        recommendations = []
        for hit in hits:
            source = hit.get("_source", {})
            
            if source.get("category_name") not in missing:
                continue
            
            recommendations.append(RecommendationDTO(
                product_id=source.get("id", ""),
                name=source.get("name", ""),
                slug=source.get("slug", ""),
                brand_name=source.get("brand_name"),
                category_name=source.get("category_name"),
                image_url=source.get("primary_image_url"),
                price=source.get("current_price", 0),
                currency=source.get("currency", "USD"),
                score=0.85,
                reasons=["Complete your wardrobe", f"You're missing {missing_category}"],
                match_factors={},
            ))
        
        return recommendations[:limit]
    
    async def _get_style_matches(
        self,
        style_profile: Optional[StyleProfileModel],
        limit: int,
    ) -> List[RecommendationDTO]:
        """Get products that match user's style profile."""
        if not style_profile or not style_profile.primary_archetype:
            return []
        
        search = await self._get_search()
        
        result = await search.search_products(
            query="",
            filters={
                "status": "active",
                "style_tags": [style_profile.primary_archetype],
            },
            page=1,
            page_size=limit,
        )
        
        hits = result.get("hits", {}).get("hits", [])
        
        recommendations = []
        for hit in hits:
            source = hit.get("_source", {})
            
            recommendations.append(RecommendationDTO(
                product_id=source.get("id", ""),
                name=source.get("name", ""),
                slug=source.get("slug", ""),
                brand_name=source.get("brand_name"),
                category_name=source.get("category_name"),
                image_url=source.get("primary_image_url"),
                price=source.get("current_price", 0),
                currency=source.get("currency", "USD"),
                score=0.90,
                reasons=[f"Perfect for your {style_profile.primary_archetype} style"],
                match_factors={"style_match": 0.9},
            ))
        
        return recommendations
    
    # ─────────────────────────────────────────────────────────────────────────
    # SCORING METHODS
    # ─────────────────────────────────────────────────────────────────────────
    
    def _calculate_personalized_score(
        self,
        product: Dict[str, Any],
        style_profile: Optional[StyleProfileModel],
        brand_affinities: List[BrandAffinityModel],
        purchase_history: List[Dict],
    ) -> float:
        """Calculate personalized recommendation score."""
        score = 0.5  # Base score
        
        # Style match
        if style_profile and style_profile.primary_archetype:
            product_styles = set(product.get("style_tags", []))
            if style_profile.primary_archetype in product_styles:
                score += 0.2
        
        # Brand affinity
        if brand_affinities:
            for affinity in brand_affinities:
                if affinity.brand_id == product.get("brand_id"):
                    score += float(affinity.affinity_score) * 0.2
                    break
        
        # Color preference
        if style_profile and style_profile.preferred_colors:
            if product.get("color") in style_profile.preferred_colors:
                score += 0.1
        
        # Price range fit
        # TODO: Check against budget profile
        
        return min(score, 1.0)
    
    def _calculate_style_match_score(
        self,
        style_profile: StyleProfileModel,
        product: Dict[str, Any],
    ) -> float:
        """Calculate style match score."""
        if not style_profile:
            return 0.5
        
        score = 0.0
        
        # Archetype match
        if style_profile.primary_archetype:
            product_styles = product.get("style_tags", [])
            if style_profile.primary_archetype in product_styles:
                score += 0.4
        
        # Color preference
        if style_profile.preferred_colors:
            if product.get("color") in style_profile.preferred_colors:
                score += 0.2
        
        # Style vector match (if available)
        # TODO: Implement vector similarity
        
        return min(score + 0.4, 1.0)  # Add base score
    
    def _calculate_color_harmony(
        self,
        color1: Optional[str],
        color2: Optional[str],
    ) -> float:
        """Calculate color harmony score."""
        if not color1 or not color2:
            return 0.7
        
        if color1 == color2:
            return self.COLOR_HARMONY["monochromatic"]
        
        neutrals = {"black", "white", "gray", "navy", "beige", "brown", "cream"}
        
        if color1 in neutrals or color2 in neutrals:
            return self.COLOR_HARMONY["neutral"]
        
        # Simplified complementary check
        complementary_pairs = [
            {"blue", "orange"},
            {"red", "green"},
            {"yellow", "purple"},
        ]
        
        for pair in complementary_pairs:
            if color1 in pair and color2 in pair:
                return self.COLOR_HARMONY["complementary"]
        
        return 0.7  # Default harmony
    
    def _generate_recommendation_reasons(
        self,
        product: Dict[str, Any],
        style_profile: Optional[StyleProfileModel],
        brand_affinities: List[BrandAffinityModel],
    ) -> List[str]:
        """Generate human-readable recommendation reasons."""
        reasons = []
        
        if style_profile and style_profile.primary_archetype:
            if style_profile.primary_archetype in product.get("style_tags", []):
                reasons.append(f"Matches your {style_profile.primary_archetype} style")
        
        if brand_affinities:
            for affinity in brand_affinities:
                if affinity.brand_id == product.get("brand_id"):
                    reasons.append("From a brand you love")
                    break
        
        if style_profile and style_profile.preferred_colors:
            if product.get("color") in style_profile.preferred_colors:
                reasons.append(f"In your preferred {product.get('color')} color")
        
        if product.get("is_bestseller"):
            reasons.append("Popular choice")
        
        if product.get("is_new_arrival"):
            reasons.append("New arrival")
        
        if not reasons:
            reasons.append("Recommended for you")
        
        return reasons[:3]  # Limit to 3 reasons
    
    def _get_complementary_categories(self, category: Optional[str]) -> List[str]:
        """Get complementary categories for an outfit."""
        complementary_map = {
            "tops": ["bottoms", "footwear", "accessories"],
            "bottoms": ["tops", "footwear", "accessories"],
            "dresses": ["footwear", "accessories", "outerwear"],
            "outerwear": ["tops", "bottoms", "footwear"],
            "footwear": ["tops", "bottoms", "accessories"],
            "accessories": ["tops", "bottoms", "dresses"],
        }
        
        return complementary_map.get(category, ["tops", "bottoms"])
    
    # ─────────────────────────────────────────────────────────────────────────
    # DATA LOADING
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _get_style_profile(self, user_id: UUID) -> Optional[StyleProfileModel]:
        """Get user's style profile."""
        query = select(StyleProfileModel).where(StyleProfileModel.user_id == str(user_id))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_brand_affinities(self, user_id: UUID) -> List[BrandAffinityModel]:
        """Get user's brand affinities."""
        query = (
            select(BrandAffinityModel)
            .where(BrandAffinityModel.user_id == str(user_id))
            .order_by(BrandAffinityModel.affinity_score.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def _get_purchase_history(self, user_id: UUID) -> List[Dict]:
        """Get user's purchase history."""
        query = (
            select(OrderItemModel, ProductModel)
            .join(ProductModel, ProductModel.id == OrderItemModel.product_id)
            .join(OrderModel, OrderModel.id == OrderItemModel.order_id)
            .where(
                OrderModel.user_id == str(user_id),
                OrderModel.status.in_(["completed", "delivered"]),
            )
            .order_by(OrderModel.created_at.desc())
            .limit(20)
        )
        
        result = await self.session.execute(query)
        
        history = []
        for item, product in result:
            history.append({
                "product_id": product.id,
                "product_name": product.name,
                "category": product.category_id,
                "brand_id": product.brand_id,
            })
        
        return history
    
    async def _get_wardrobe_items(self, user_id: UUID) -> List[Dict]:
        """Get user's wardrobe items."""
        query = (
            select(WardrobeItemModel)
            .where(
                WardrobeItemModel.user_id == str(user_id),
                WardrobeItemModel.is_active == True,
            )
        )
        
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        return [
            {
                "id": item.id,
                "category": item.category,
                "color": item.color,
                "style_tags": item.style_tags,
            }
            for item in items
        ]
    
    async def _get_product(self, product_id: UUID) -> Optional[ProductModel]:
        """Get product by ID."""
        query = select(ProductModel).where(ProductModel.id == str(product_id))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
