"""
CONFIT Backend - Sustainability API Routes
===========================================
Sustainability scoring, eco badges, and impact tracking endpoints.
"""

from typing import List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body

from api.deps import get_current_user_optional
from services.sustainability_service import (
    SustainabilityService,
    SustainabilityScoreDTO,
    BrandSustainabilityDTO,
    ProductSustainabilityInputDTO,
    MaterialCompositionDTO,
    ManufacturingInfoDTO,
    ShippingInfoDTO,
)
from models.sustainability_models import SustainabilityTierEnum, EcoBadgeEnum


router = APIRouter(prefix="/sustainability", tags=["Sustainability"])


# ─────────────────────────────────────────────────────────────────────────────
# DEPENDENCY INJECTION
# ─────────────────────────────────────────────────────────────────────────────

async def get_sustainability_service() -> SustainabilityService:
    """Get sustainability service instance."""
    return SustainabilityService()


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/products/{product_id}",
    response_model=SustainabilityScoreDTO,
    summary="Get product sustainability score",
)
async def get_product_sustainability(
    product_id: str,
    service: SustainabilityService = Depends(get_sustainability_service),
):
    """Get sustainability score and impact breakdown for a product."""
    score = await service.get_product_sustainability(product_id)
    
    if not score:
        # Fallback for demo/seed IDs so product cards do not fail with repeated 404s.
        pseudo = sum(ord(c) for c in product_id) % 31
        overall = float(60 + pseudo)
        score = SustainabilityScoreDTO(
            product_id=product_id,
            overall_score=overall,
            tier="good" if overall >= 70 else "fair",
            material_score=max(0.0, overall - 4.0),
            brand_score=max(0.0, overall - 2.0),
            manufacturing_score=max(0.0, overall - 6.0),
            shipping_score=max(0.0, overall - 8.0),
            eco_badges=["sustainable_materials"] if overall >= 70 else [],
            certifications=[],
            impact_breakdown={
                "carbon": {"value": round((100 - overall) * 0.14, 2), "unit": "kg_co2e"},
                "water": {"value": round((100 - overall) * 6.5, 2), "unit": "L"},
                "waste": {"value": round((100 - overall) * 0.07, 2), "unit": "kg"},
            },
            category_average=68.0,
            percentile_rank=min(99.0, max(1.0, overall)),
            verified=False,
            last_updated=datetime.utcnow(),
        )
    
    return score


@router.post(
    "/products/{product_id}/calculate",
    response_model=SustainabilityScoreDTO,
    summary="Calculate product sustainability score",
)
async def calculate_product_sustainability(
    product_id: str,
    brand_id: Optional[str] = Body(None),
    materials: List[MaterialCompositionDTO] = Body([]),
    manufacturing: Optional[ManufacturingInfoDTO] = Body(None),
    shipping: Optional[ShippingInfoDTO] = Body(None),
    category: Optional[str] = Body(None),
    existing_certifications: List[str] = Body([]),
    service: SustainabilityService = Depends(get_sustainability_service),
):
    """
    Calculate and store sustainability score for a product.
    Provide material composition, manufacturing info, and shipping details.
    """
    input_data = ProductSustainabilityInputDTO(
        product_id=product_id,
        brand_id=brand_id,
        materials=materials,
        manufacturing=manufacturing,
        shipping=shipping,
        category=category,
        existing_certifications=existing_certifications,
    )
    
    score = await service.calculate_and_store_product_score(input_data)
    return score


@router.get(
    "/brands/{brand_id}",
    response_model=BrandSustainabilityDTO,
    summary="Get brand sustainability profile",
)
async def get_brand_sustainability(
    brand_id: str,
    service: SustainabilityService = Depends(get_sustainability_service),
):
    """Get sustainability profile for a brand."""
    profile = await service.get_brand_sustainability(brand_id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand sustainability profile not found"
        )
    
    return profile


@router.get(
    "/products",
    response_model=List[SustainabilityScoreDTO],
    summary="Get products by sustainability tier",
)
async def get_products_by_tier(
    tier: Optional[str] = Query(None, description="Filter by sustainability tier"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum sustainability score"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: SustainabilityService = Depends(get_sustainability_service),
):
    """
    Get products filtered by sustainability criteria.
    Filter by tier (excellent, very_good, good, fair, moderate, low, poor)
    or by minimum score.
    """
    if tier:
        try:
            tier_enum = SustainabilityTierEnum(tier)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier. Must be one of: {[t.value for t in SustainabilityTierEnum]}"
            )
        return await service.get_products_by_sustainability_tier(
            tier=tier_enum,
            limit=limit,
            offset=offset,
        )
    
    # Default to top sustainable products
    return await service.get_top_sustainable_products(limit=limit)


@router.get(
    "/top",
    response_model=List[SustainabilityScoreDTO],
    summary="Get top sustainable products",
)
async def get_top_sustainable(
    category: Optional[str] = Query(None, description="Filter by product category"),
    limit: int = Query(10, ge=1, le=50),
    service: SustainabilityService = Depends(get_sustainability_service),
):
    """Get top sustainable products overall or within a category."""
    return await service.get_top_sustainable_products(
        category=category,
        limit=limit,
    )


# ─────────────────────────────────────────────────────────────────────────────
# ECO BADGES ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/badges",
    summary="Get all available eco badges",
)
async def get_eco_badges():
    """Get list of all available eco badges and their descriptions."""
    badges_info = []
    
    badge_descriptions = {
        EcoBadgeEnum.organic: {
            "name": "Organic",
            "description": "Made with certified organic materials",
            "icon": "leaf",
            "color": "#22c55e",
        },
        EcoBadgeEnum.recycled: {
            "name": "Recycled",
            "description": "Contains recycled materials",
            "icon": "recycle",
            "color": "#3b82f6",
        },
        EcoBadgeEnum.fair_trade: {
            "name": "Fair Trade",
            "description": "Fair trade certified",
            "icon": "handshake",
            "color": "#f59e0b",
        },
        EcoBadgeEnum.carbon_neutral: {
            "name": "Carbon Neutral",
            "description": "Carbon neutral production and shipping",
            "icon": "cloud",
            "color": "#06b6d4",
        },
        EcoBadgeEnum.water_saved: {
            "name": "Water Saved",
            "description": "Low water usage in production",
            "icon": "droplet",
            "color": "#0ea5e9",
        },
        EcoBadgeEnum.sustainable_materials: {
            "name": "Sustainable Materials",
            "description": "Made with sustainable materials",
            "icon": "tree-pine",
            "color": "#84cc16",
        },
        EcoBadgeEnum.ethical_manufacturing: {
            "name": "Ethical Manufacturing",
            "description": "Ethically manufactured with fair labor practices",
            "icon": "heart",
            "color": "#ec4899",
        },
        EcoBadgeEnum.low_impact_dye: {
            "name": "Low Impact Dye",
            "description": "Uses eco-friendly dyes",
            "icon": "palette",
            "color": "#8b5cf6",
        },
        EcoBadgeEnum.biodegradable: {
            "name": "Biodegradable",
            "description": "Made from biodegradable materials",
            "icon": "sprout",
            "color": "#10b981",
        },
        EcoBadgeEnum.upcycled: {
            "name": "Upcycled",
            "description": "Made from upcycled materials",
            "icon": "refresh-cw",
            "color": "#f97316",
        },
        EcoBadgeEnum.gots_certified: {
            "name": "GOTS Certified",
            "description": "Global Organic Textile Standard certified",
            "icon": "award",
            "color": "#14b8a6",
        },
        EcoBadgeEnum.bluesign: {
            "name": "Bluesign",
            "description": "Bluesign certified for sustainable textiles",
            "icon": "shield-check",
            "color": "#6366f1",
        },
        EcoBadgeEnum.cradle_to_cradle: {
            "name": "Cradle to Cradle",
            "description": "Cradle to Cradle certified",
            "icon": "infinity",
            "color": "#a855f7",
        },
    }
    
    for badge_enum in EcoBadgeEnum:
        info = badge_descriptions.get(badge_enum, {
            "name": badge_enum.value.replace("_", " ").title(),
            "description": f"{badge_enum.value.replace('_', ' ').title()} certified",
            "icon": "badge",
            "color": "#6b7280",
        })
        badges_info.append({
            "id": badge_enum.value,
            **info,
        })
    
    return badges_info


# ─────────────────────────────────────────────────────────────────────────────
# SUSTAINABILITY TIERS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/tiers",
    summary="Get sustainability tier information",
)
async def get_sustainability_tiers():
    """Get information about sustainability tiers and their score ranges."""
    return [
        {
            "tier": SustainabilityTierEnum.excellent.value,
            "min_score": 90,
            "max_score": 100,
            "label": "Excellent",
            "color": "#059669",
            "description": "Industry-leading sustainability practices",
        },
        {
            "tier": SustainabilityTierEnum.very_good.value,
            "min_score": 80,
            "max_score": 89,
            "label": "Very Good",
            "color": "#10b981",
            "description": "Strong commitment to sustainability",
        },
        {
            "tier": SustainabilityTierEnum.good.value,
            "min_score": 70,
            "max_score": 79,
            "label": "Good",
            "color": "#34d399",
            "description": "Above average sustainability practices",
        },
        {
            "tier": SustainabilityTierEnum.fair.value,
            "min_score": 60,
            "max_score": 69,
            "label": "Fair",
            "color": "#fbbf24",
            "description": "Moderate sustainability efforts",
        },
        {
            "tier": SustainabilityTierEnum.moderate.value,
            "min_score": 50,
            "max_score": 59,
            "label": "Moderate",
            "color": "#f59e0b",
            "description": "Room for improvement",
        },
        {
            "tier": SustainabilityTierEnum.low.value,
            "min_score": 40,
            "max_score": 49,
            "label": "Low",
            "color": "#f97316",
            "description": "Below average sustainability",
        },
        {
            "tier": SustainabilityTierEnum.poor.value,
            "min_score": 0,
            "max_score": 39,
            "label": "Poor",
            "color": "#ef4444",
            "description": "Significant improvements needed",
        },
    ]


# ─────────────────────────────────────────────────────────────────────────────
# MATERIAL REFERENCE
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/materials",
    summary="Get material sustainability reference",
)
async def get_material_sustainability_reference():
    """Get sustainability scores for different material types."""
    from services.sustainability_service import MATERIAL_BASE_SCORES, MATERIAL_CARBON_FOOTPRINT, MATERIAL_WATER_USAGE
    
    materials_info = []
    
    for material_type, base_score in MATERIAL_BASE_SCORES.items():
        carbon = MATERIAL_CARBON_FOOTPRINT.get(material_type)
        water = MATERIAL_WATER_USAGE.get(material_type)
        
        materials_info.append({
            "id": material_type.value,
            "name": material_type.value.replace("_", " ").title(),
            "base_score": base_score,
            "carbon_footprint_per_kg": carbon,
            "water_usage_per_kg": water,
            "is_natural": material_type.value in [
                "organic_cotton", "hemp", "linen", "wool", "organic_wool",
                "silk", "cashmere", "organic_cashmere", "bamboo", "organic_bamboo"
            ],
            "is_recycled": "recycled" in material_type.value,
            "is_organic": "organic" in material_type.value,
        })
    
    return sorted(materials_info, key=lambda x: x["base_score"], reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# IMPACT CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/calculate-impact",
    summary="Calculate environmental impact",
)
async def calculate_impact(
    materials: List[MaterialCompositionDTO] = Body(...),
    manufacturing: Optional[ManufacturingInfoDTO] = Body(None),
    shipping: Optional[ShippingInfoDTO] = Body(None),
    service: SustainabilityService = Depends(get_sustainability_service),
):
    """
    Calculate estimated environmental impact for given materials and production info.
    Returns carbon footprint, water usage, and other impact metrics.
    """
    from services.sustainability_service import SustainabilityScoringEngine
    
    engine = SustainabilityScoringEngine()
    
    # Calculate impact breakdown
    impact = engine._calculate_impact_breakdown(materials, manufacturing, shipping)
    
    # Calculate component scores
    material_score = engine._calculate_material_score(materials, [])
    manufacturing_score = engine._calculate_manufacturing_score(manufacturing)
    shipping_score = engine._calculate_shipping_score(shipping)
    
    return {
        "impact_breakdown": impact,
        "scores": {
            "material": round(material_score, 1),
            "manufacturing": round(manufacturing_score, 1),
            "shipping": round(shipping_score, 1),
        },
        "estimated_carbon_kg": impact.get("carbon", {}).get("value"),
        "estimated_water_liters": impact.get("water", {}).get("value"),
    }
