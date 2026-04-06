"""
CONFIT Backend — Style DNA Integration
======================================
Integration layer connecting Style DNA with recommendations, virtual stylist, and product ranking.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.style_dna_service import StyleDNAService
from models.style_dna_models import (
    StyleDNAProfile,
    StyleCategory,
    BudgetLevel,
    FitPreference,
)
from models.database import Product, Brand

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# STYLE DNA RECOMMENDATION ENHANCER
# ─────────────────────────────────────────────────────────────────────────────

class StyleDNARecommendationEnhancer:
    """
    Enhances product recommendations using Style DNA data.
    Integrates with the existing RecommendationEngine.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.style_dna_service = StyleDNAService(session)
    
    async def get_style_match_score(
        self,
        user_id: UUID,
        product_id: UUID,
    ) -> Dict[str, float]:
        """
        Calculate style match score between user's Style DNA and a product.
        
        Returns:
            Dict with overall_score and individual factor scores
        """
        profile = await self.style_dna_service._get_profile(user_id)
        
        if not profile or not profile.style_vector:
            return {"overall_score": 0.5, "reason": "no_profile"}
        
        # Get product details
        product = await self.session.get(Product, str(product_id))
        
        if not product:
            return {"overall_score": 0.0, "reason": "product_not_found"}
        
        scores = {}
        
        # 1. Style category match (30%)
        style_match = await self._calculate_style_match(profile, product)
        scores["style_match"] = style_match
        
        # 2. Color preference match (25%)
        color_match = await self._calculate_color_match(profile, product)
        scores["color_match"] = color_match
        
        # 3. Brand affinity match (20%)
        brand_match = await self._calculate_brand_match(profile, product)
        scores["brand_match"] = brand_match
        
        # 4. Budget fit (15%)
        budget_match = self._calculate_budget_match(profile, product)
        scores["budget_match"] = budget_match
        
        # 5. Occasion relevance (10%)
        occasion_match = self._calculate_occasion_match(profile, product)
        scores["occasion_match"] = occasion_match
        
        # Calculate weighted overall score
        overall = (
            style_match * 0.30 +
            color_match * 0.25 +
            brand_match * 0.20 +
            budget_match * 0.15 +
            occasion_match * 0.10
        )
        
        scores["overall_score"] = overall
        scores["confidence"] = float(profile.style_confidence)
        
        return scores
    
    async def _calculate_style_match(
        self,
        profile: StyleDNAProfile,
        product: Product,
    ) -> float:
        """Calculate style category match."""
        if not profile.primary_style:
            return 0.5
        
        # Get product style tags
        product_styles = []
        if product.tags:
            product_styles = [
                tag.get("value", "").lower()
                for tag in product.tags
                if tag.get("type") == "style"
            ]
        
        if not product_styles:
            return 0.5  # Neutral if no style tags
        
        # Check primary style match
        primary_style = profile.primary_style.value if isinstance(profile.primary_style, StyleCategory) else str(profile.primary_style)
        
        if primary_style.lower() in product_styles:
            return 1.0
        
        # Check secondary styles
        secondary_styles = [
            s.value if isinstance(s, StyleCategory) else str(s)
            for s in (profile.secondary_styles or [])
        ]
        
        for secondary in secondary_styles:
            if secondary.lower() in product_styles:
                return 0.8
        
        return 0.3  # Style mismatch
    
    async def _calculate_color_match(
        self,
        profile: StyleDNAProfile,
        product: Product,
    ) -> float:
        """Calculate color preference match."""
        if not product.color:
            return 0.5
        
        color_prefs = profile.color_preferences or {}
        primary_colors = [c.lower() for c in color_prefs.get("primary", [])]
        secondary_colors = [c.lower() for c in color_prefs.get("secondary", [])]
        avoided_colors = [c.lower() for c in color_prefs.get("avoided", [])]
        
        product_color = product.color.lower()
        
        # Check if color is avoided
        if product_color in avoided_colors:
            return 0.0
        
        # Check primary color match
        if product_color in primary_colors:
            return 1.0
        
        # Check secondary color match
        if product_color in secondary_colors:
            return 0.7
        
        # Neutral color handling
        neutral_colors = {"black", "white", "gray", "navy", "beige", "brown"}
        if product_color in neutral_colors:
            return 0.8  # Neutrals are generally good
        
        return 0.5  # Unknown color
    
    async def _calculate_brand_match(
        self,
        profile: StyleDNAProfile,
        product: Product,
    ) -> float:
        """Calculate brand affinity match."""
        if not product.brand_id:
            return 0.5
        
        brand_affinities = profile.brand_affinity or []
        
        for brand in brand_affinities:
            if brand.get("brand_id") == str(product.brand_id):
                return brand.get("affinity_score", 0.5)
        
        return 0.5  # Unknown brand
    
    def _calculate_budget_match(
        self,
        profile: StyleDNAProfile,
        product: Product,
    ) -> float:
        """Calculate budget fit score."""
        if not product.current_price:
            return 0.5
        
        price = float(product.current_price)
        budget_range = profile.budget_range or {}
        
        # Check if within explicit budget range
        min_price = budget_range.get("per_item_min")
        max_price = budget_range.get("per_item_max")
        
        if max_price and price > max_price:
            return 0.2  # Over budget
        
        if min_price and price < min_price:
            return 0.6  # Under minimum (might be low quality)
        
        # Budget level based scoring
        budget_level = profile.budget_level or BudgetLevel.MODERATE
        budget_ranges = {
            BudgetLevel.BUDGET_CONSCIOUS: (0, 50, 1.0, 0.5, 0.2),
            BudgetLevel.MODERATE: (50, 150, 1.0, 0.8, 0.4),
            BudgetLevel.PREMIUM: (150, 500, 1.0, 0.9, 0.6),
            BudgetLevel.LUXURY: (500, 1500, 1.0, 0.95, 0.7),
            BudgetLevel.ULTRA_LUXURY: (1500, float('inf'), 1.0, 1.0, 0.8),
        }
        
        if budget_level in budget_ranges:
            low, high, in_range, above, below = budget_ranges[budget_level]
            if low <= price <= high:
                return in_range
            elif price > high:
                return above
            else:
                return below
        
        return 0.5
    
    def _calculate_occasion_match(
        self,
        profile: StyleDNAProfile,
        product: Product,
    ) -> float:
        """Calculate occasion relevance score."""
        occasion_prefs = profile.occasion_preferences or {}
        
        # Get product occasion tags
        product_occasions = []
        if product.tags:
            product_occasions = [
                tag.get("value", "").lower()
                for tag in product.tags
                if tag.get("type") == "occasion"
            ]
        
        if not product_occasions:
            return 0.5
        
        # Calculate weighted match
        total_weight = 0.0
        matched_weight = 0.0
        
        for occasion, weight in occasion_prefs.items():
            total_weight += weight
            if occasion.lower() in product_occasions:
                matched_weight += weight
        
        if total_weight == 0:
            return 0.5
        
        return matched_weight / total_weight
    
    async def enhance_recommendations(
        self,
        user_id: UUID,
        products: List[Dict[str, Any]],
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Enhance a list of product recommendations with Style DNA scoring.
        
        Args:
            user_id: User ID
            products: List of product dictionaries
            max_results: Maximum results to return
        
        Returns:
            Enhanced and ranked product list
        """
        if not products:
            return []
        
        profile = await self.style_dna_service._get_profile(user_id)
        
        if not profile or not profile.style_vector:
            return products[:max_results]
        
        enhanced = []
        
        for product in products:
            product_id = product.get("id") or product.get("product_id")
            if not product_id:
                continue
            
            scores = await self.get_style_match_score(user_id, UUID(product_id))
            
            enhanced_product = {
                **product,
                "style_dna_score": scores.get("overall_score", 0.5),
                "style_match_factors": scores,
            }
            
            # Generate match reasons
            reasons = self._generate_match_reasons(scores, profile)
            enhanced_product["style_match_reasons"] = reasons
            
            enhanced.append(enhanced_product)
        
        # Sort by combined score (original + Style DNA)
        enhanced.sort(
            key=lambda x: (
                x.get("score", 0.5) * 0.4 + x.get("style_dna_score", 0.5) * 0.6
            ),
            reverse=True
        )
        
        return enhanced[:max_results]
    
    def _generate_match_reasons(
        self,
        scores: Dict[str, float],
        profile: StyleDNAProfile,
    ) -> List[str]:
        """Generate human-readable match reasons."""
        reasons = []
        
        if scores.get("style_match", 0) >= 0.8:
            reasons.append(f"Matches your {profile.primary_style.value.replace('_', ' ')} style")
        
        if scores.get("color_match", 0) >= 0.8:
            colors = profile.color_preferences.get("primary", [])
            if colors:
                reasons.append(f"Available in your favorite color ({colors[0]})")
        
        if scores.get("brand_match", 0) >= 0.7:
            reasons.append("From a brand you love")
        
        if scores.get("budget_match", 0) >= 0.9:
            reasons.append("Within your budget range")
        
        if scores.get("occasion_match", 0) >= 0.7:
            reasons.append("Perfect for your favorite occasions")
        
        return reasons


# ─────────────────────────────────────────────────────────────────────────────
# VIRTUAL STYLIST INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

class VirtualStylistStyleDNAIntegration:
    """
    Integrates Style DNA with Virtual Stylist for personalized outfit suggestions.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.style_dna_service = StyleDNAService(session)
    
    async def get_style_context(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get style context for Virtual Stylist prompts.
        
        Returns user's style preferences formatted for AI styling suggestions.
        """
        profile = await self.style_dna_service._get_profile(user_id)
        
        if not profile:
            return self._get_default_context()
        
        context = {
            "primary_style": profile.primary_style.value if profile.primary_style else None,
            "secondary_styles": [
                s.value if isinstance(s, StyleCategory) else str(s)
                for s in (profile.secondary_styles or [])
            ],
            "color_preferences": profile.color_preferences or {},
            "fit_preference": profile.fit_preference.value if profile.fit_preference else "regular",
            "occasion_preferences": profile.occasion_preferences or {},
            "budget_level": profile.budget_level.value if profile.budget_level else "moderate",
            "style_confidence": float(profile.style_confidence),
            "brand_affinities": profile.brand_affinity or [],
            "pattern_preferences": profile.pattern_preferences or {},
            "fabric_preferences": profile.fabric_preferences or {},
        }
        
        # Add style guidance
        context["style_guidance"] = self._generate_style_guidance(profile)
        
        return context
    
    def _get_default_context(self) -> Dict[str, Any]:
        """Get default context for users without Style DNA profile."""
        return {
            "primary_style": "casual",
            "secondary_styles": [],
            "color_preferences": {"primary": [], "secondary": [], "avoided": []},
            "fit_preference": "regular",
            "occasion_preferences": {"everyday": 0.7, "casual": 0.8},
            "budget_level": "moderate",
            "style_confidence": 0.0,
            "brand_affinities": [],
            "style_guidance": "Focus on versatile, everyday pieces that can be mixed and matched.",
        }
    
    def _generate_style_guidance(self, profile: StyleDNAProfile) -> str:
        """Generate style guidance text for AI prompts."""
        guidance_parts = []
        
        if profile.primary_style:
            style_name = profile.primary_style.value.replace('_', ' ')
            guidance_parts.append(f"User's primary style is {style_name}")
        
        if profile.color_preferences:
            colors = profile.color_preferences.get("primary", [])
            if colors:
                guidance_parts.append(f"Favorite colors: {', '.join(colors[:3])}")
            
            undertone = profile.color_preferences.get("undertone")
            if undertone:
                guidance_parts.append(f"Skin undertone: {undertone}")
        
        if profile.fit_preference:
            guidance_parts.append(f"Preferred fit: {profile.fit_preference.value}")
        
        if profile.budget_level:
            guidance_parts.append(f"Budget level: {profile.budget_level.value.replace('_', ' ')}")
        
        if profile.brand_affinity:
            top_brands = sorted(
                profile.brand_affinity,
                key=lambda x: x.get("affinity_score", 0),
                reverse=True
            )[:3]
            if top_brands:
                brand_names = [b.get("brand_id") for b in top_brands]
                guidance_parts.append(f"Preferred brands: {', '.join(brand_names)}")
        
        return ". ".join(guidance_parts) + "."
    
    async def get_outfit_suggestions(
        self,
        user_id: UUID,
        occasion: Optional[str] = None,
        weather: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get outfit suggestions based on Style DNA.
        
        Returns structured outfit recommendations.
        """
        context = await self.get_style_context(user_id)
        
        suggestions = {
            "style_context": context,
            "occasion": occasion,
            "weather": weather,
            "recommendations": [],
            "styling_tips": [],
        }
        
        # Generate styling tips based on style profile
        suggestions["styling_tips"] = self._generate_styling_tips(context, occasion)
        
        return suggestions
    
    def _generate_styling_tips(
        self,
        context: Dict[str, Any],
        occasion: Optional[str],
    ) -> List[str]:
        """Generate personalized styling tips."""
        tips = []
        
        primary_style = context.get("primary_style", "casual")
        
        # Style-specific tips
        style_tips = {
            "minimalist": [
                "Stick to a neutral color palette",
                "Focus on clean lines and simple silhouettes",
                "Invest in quality basics",
            ],
            "bohemian": [
                "Layer different textures and patterns",
                "Mix vintage and modern pieces",
                "Add accessories for personality",
            ],
            "classic": [
                "Invest in timeless pieces that won't go out of style",
                "Focus on quality over quantity",
                "Stick to traditional color combinations",
            ],
            "streetwear": [
                "Mix high and low fashion pieces",
                "Focus on comfortable, relaxed fits",
                "Add statement sneakers or accessories",
            ],
            "edgy": [
                "Incorporate leather and metal accents",
                "Mix textures like leather and denim",
                "Don't be afraid of bold colors or prints",
            ],
        }
        
        tips.extend(style_tips.get(primary_style, [
            "Wear what makes you feel confident",
            "Build outfits around your favorite pieces",
        ]))
        
        # Occasion-specific tips
        if occasion:
            occasion_tips = {
                "work": "Choose professional pieces that reflect your personal style",
                "date_night": "Add a statement piece that shows personality",
                "weekend": "Focus on comfort while maintaining style",
                "formal": "Elevate your look with refined accessories",
            }
            if occasion in occasion_tips:
                tips.append(occasion_tips[occasion])
        
        return tips


# ─────────────────────────────────────────────────────────────────────────────
# HOME FEED INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

class HomeFeedStyleDNAIntegration:
    """
    Integrates Style DNA with Home feed personalization.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.style_dna_service = StyleDNAService(session)
        self.recommendation_enhancer = StyleDNARecommendationEnhancer(session)
    
    async def personalize_feed(
        self,
        user_id: UUID,
        feed_items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Personalize home feed based on Style DNA.
        
        Args:
            user_id: User ID
            feed_items: List of feed items (products, articles, etc.)
        
        Returns:
            Personalized and ranked feed items
        """
        profile = await self.style_dna_service._get_profile(user_id)
        
        if not profile or not profile.style_vector:
            return feed_items  # Return unmodified if no profile
        
        personalized = []
        
        for item in feed_items:
            item_type = item.get("type", "product")
            
            if item_type == "product":
                # Enhance product items with Style DNA scoring
                product_id = item.get("id") or item.get("product_id")
                if product_id:
                    scores = await self.recommendation_enhancer.get_style_match_score(
                        user_id, UUID(product_id)
                    )
                    item["style_dna_score"] = scores.get("overall_score", 0.5)
                    item["personalization_reason"] = self._get_personalization_reason(scores)
            
            personalized.append(item)
        
        # Sort by Style DNA score (products) or keep original order (other content)
        products = [i for i in personalized if i.get("type") == "product"]
        other = [i for i in personalized if i.get("type") != "product"]
        
        products.sort(key=lambda x: x.get("style_dna_score", 0.5), reverse=True)
        
        # Interleave products with other content
        result = []
        product_idx = 0
        other_idx = 0
        
        while product_idx < len(products) or other_idx < len(other):
            # Add 2 products for every 1 other item
            if product_idx < len(products):
                result.append(products[product_idx])
                product_idx += 1
            
            if product_idx < len(products):
                result.append(products[product_idx])
                product_idx += 1
            
            if other_idx < len(other):
                result.append(other[other_idx])
                other_idx += 1
        
        return result
    
    def _get_personalization_reason(self, scores: Dict[str, float]) -> str:
        """Get personalization reason for UI display."""
        if scores.get("style_match", 0) >= 0.8:
            return "Matches your style"
        elif scores.get("color_match", 0) >= 0.8:
            return "In your favorite colors"
        elif scores.get("brand_match", 0) >= 0.7:
            return "From brands you love"
        elif scores.get("budget_match", 0) >= 0.9:
            return "Within your budget"
        else:
            return "Recommended for you"


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT RANKING INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

class ProductRankingStyleDNAIntegration:
    """
    Integrates Style DNA with product ranking for search and category pages.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.style_dna_service = StyleDNAService(session)
    
    async def rank_products(
        self,
        user_id: UUID,
        products: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rank products based on Style DNA and context.
        
        Args:
            user_id: User ID
            products: List of products to rank
            context: Additional context (category, search query, etc.)
        
        Returns:
            Ranked products list
        """
        profile = await self.style_dna_service._get_profile(user_id)
        
        if not profile or not profile.style_vector:
            return products  # Return unmodified if no profile
        
        # Calculate Style DNA score for each product
        scored_products = []
        
        for product in products:
            score = await self._calculate_product_score(profile, product, context)
            product["style_dna_rank_score"] = score
            scored_products.append(product)
        
        # Sort by score (descending)
        scored_products.sort(
            key=lambda x: x.get("style_dna_rank_score", 0),
            reverse=True
        )
        
        return scored_products
    
    async def _calculate_product_score(
        self,
        profile: StyleDNAProfile,
        product: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> float:
        """Calculate Style DNA score for a product."""
        scores = []
        
        # Style match (30%)
        style_score = self._score_style_match(profile, product)
        scores.append(("style", style_score, 0.30))
        
        # Color match (25%)
        color_score = self._score_color_match(profile, product)
        scores.append(("color", color_score, 0.25))
        
        # Brand match (20%)
        brand_score = self._score_brand_match(profile, product)
        scores.append(("brand", brand_score, 0.20))
        
        # Price fit (15%)
        price_score = self._score_price_fit(profile, product)
        scores.append(("price", price_score, 0.15))
        
        # Context relevance (10%)
        context_score = self._score_context_relevance(profile, product, context)
        scores.append(("context", context_score, 0.10))
        
        # Calculate weighted sum
        total_score = sum(score * weight for _, score, weight in scores)
        
        return total_score
    
    def _score_style_match(self, profile: StyleDNAProfile, product: Dict[str, Any]) -> float:
        """Score style match."""
        product_styles = product.get("style_tags", [])
        if not product_styles:
            return 0.5
        
        primary = profile.primary_style.value if profile.primary_style else None
        if primary and primary.lower() in [s.lower() for s in product_styles]:
            return 1.0
        
        secondary = [s.value if hasattr(s, 'value') else str(s) for s in (profile.secondary_styles or [])]
        for s in secondary:
            if s.lower() in [p.lower() for p in product_styles]:
                return 0.8
        
        return 0.3
    
    def _score_color_match(self, profile: StyleDNAProfile, product: Dict[str, Any]) -> float:
        """Score color match."""
        product_color = product.get("color", "").lower()
        if not product_color:
            return 0.5
        
        colors = profile.color_preferences or {}
        primary = [c.lower() for c in colors.get("primary", [])]
        avoided = [c.lower() for c in colors.get("avoided", [])]
        
        if product_color in avoided:
            return 0.0
        if product_color in primary:
            return 1.0
        
        return 0.5
    
    def _score_brand_match(self, profile: StyleDNAProfile, product: Dict[str, Any]) -> float:
        """Score brand match."""
        product_brand = str(product.get("brand_id", ""))
        if not product_brand:
            return 0.5
        
        for brand in (profile.brand_affinity or []):
            if str(brand.get("brand_id")) == product_brand:
                return brand.get("affinity_score", 0.5)
        
        return 0.5
    
    def _score_price_fit(self, profile: StyleDNAProfile, product: Dict[str, Any]) -> float:
        """Score price fit."""
        price = float(product.get("current_price", 0) or product.get("price", 0))
        if not price:
            return 0.5
        
        budget_range = profile.budget_range or {}
        max_price = budget_range.get("per_item_max")
        
        if max_price and price > max_price:
            return 0.3
        if max_price and price <= max_price:
            return 1.0
        
        return 0.5
    
    def _score_context_relevance(
        self,
        profile: StyleDNAProfile,
        product: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> float:
        """Score context relevance."""
        if not context:
            return 0.5
        
        # Check occasion context
        occasion = context.get("occasion")
        if occasion:
            occasion_prefs = profile.occasion_preferences or {}
            if occasion.lower() in occasion_prefs:
                return occasion_prefs[occasion.lower()]
        
        return 0.5


# ─────────────────────────────────────────────────────────────────────────────
# FACTORY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_recommendation_enhancer(session: AsyncSession) -> StyleDNARecommendationEnhancer:
    """Get recommendation enhancer instance."""
    return StyleDNARecommendationEnhancer(session)


def get_virtual_stylist_integration(session: AsyncSession) -> VirtualStylistStyleDNAIntegration:
    """Get Virtual Stylist integration instance."""
    return VirtualStylistStyleDNAIntegration(session)


def get_home_feed_integration(session: AsyncSession) -> HomeFeedStyleDNAIntegration:
    """Get Home Feed integration instance."""
    return HomeFeedStyleDNAIntegration(session)


def get_product_ranking_integration(session: AsyncSession) -> ProductRankingStyleDNAIntegration:
    """Get Product Ranking integration instance."""
    return ProductRankingStyleDNAIntegration(session)
