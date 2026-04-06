"""
CONFIT Backend — Sustainability Scoring Engine Service
=======================================================
Comprehensive sustainability scoring for products and brands.
Considers materials, manufacturing, brand practices, and shipping emissions.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from models.sustainability_models import (
    SustainabilityScore,
    BrandSustainability,
    MaterialSustainabilityReference,
    SustainabilityAuditLog,
    EcoBadgeEnum,
    SustainabilityTierEnum,
    MaterialTypeEnum,
    ManufacturingRegionEnum,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# DTOs / Schemas
# ═══════════════════════════════════════════════════════════════════

class MaterialCompositionDTO(BaseModel):
    """Material composition entry for scoring."""
    material_type: str
    percentage: float = Field(..., ge=0, le=100)
    certified_organic: bool = False
    certified_recycled: bool = False
    source_country: Optional[str] = None


class ManufacturingInfoDTO(BaseModel):
    """Manufacturing information for scoring."""
    region: Optional[str] = None
    country: Optional[str] = None
    factory_certified: bool = False
    factory_certifications: List[str] = []
    energy_source: Optional[str] = None  # 'renewable', 'mixed', 'conventional'
    water_treatment: bool = False
    chemical_management_system: bool = False


class ShippingInfoDTO(BaseModel):
    """Shipping information for emissions calculation."""
    origin_country: Optional[str] = None
    origin_city: Optional[str] = None
    shipping_method: Optional[str] = None  # 'air', 'sea', 'ground', 'express'
    packaging_type: Optional[str] = None  # 'recycled', 'biodegradable', 'standard', 'plastic'
    packaging_recycled_content: float = 0.0


class ProductSustainabilityInputDTO(BaseModel):
    """Input data for calculating product sustainability score."""
    product_id: str
    brand_id: Optional[str] = None
    materials: List[MaterialCompositionDTO] = []
    manufacturing: Optional[ManufacturingInfoDTO] = None
    shipping: Optional[ShippingInfoDTO] = None
    category: Optional[str] = None
    existing_certifications: List[str] = []


class ImpactBreakdownDTO(BaseModel):
    """Impact breakdown for a specific category."""
    value: float
    unit: str
    rating: str  # 'excellent', 'good', 'moderate', 'poor', 'very_poor'
    description: Optional[str] = None


class SustainabilityScoreDTO(BaseModel):
    """Complete sustainability score response."""
    product_id: str
    overall_score: float
    tier: str
    
    # Component scores
    material_score: float
    brand_score: float
    manufacturing_score: float
    shipping_score: float
    
    # Badges and certifications
    eco_badges: List[str]
    certifications: List[str]
    
    # Impact breakdown
    impact_breakdown: Dict[str, Any]
    
    # Context
    category_average: Optional[float] = None
    percentile_rank: Optional[float] = None
    
    # Metadata
    verified: bool
    last_updated: datetime


class BrandSustainabilityDTO(BaseModel):
    """Brand sustainability profile response."""
    brand_id: str
    overall_score: float
    environmental_score: float
    social_score: float
    governance_score: float
    
    certifications: List[str]
    eco_badges: List[str]
    
    sustainable_materials_pct: float
    recycled_materials_pct: float
    renewable_energy_usage: float
    
    carbon_offset_program: bool
    living_wage_commitment: bool
    supply_chain_transparency: float
    
    verification_status: str


# ═══════════════════════════════════════════════════════════════════
# MATERIAL SCORE REFERENCE DATA
# ═══════════════════════════════════════════════════════════════════

# Baseline sustainability scores for materials (0-100)
MATERIAL_BASE_SCORES = {
    # High sustainability (80-100)
    MaterialTypeEnum.organic_cotton: 85,
    MaterialTypeEnum.hemp: 90,
    MaterialTypeEnum.tencel_lyocell: 88,
    MaterialTypeEnum.organic_wool: 82,
    MaterialTypeEnum.organic_cashmere: 80,
    MaterialTypeEnum.recycled_polyester: 78,
    MaterialTypeEnum.recycled_nylon: 77,
    MaterialTypeEnum.recycled_leather: 72,
    MaterialTypeEnum.organic_bamboo: 83,
    
    # Good sustainability (60-79)
    MaterialTypeEnum.linen: 75,
    MaterialTypeEnum.modal: 68,
    MaterialTypeEnum.vegan_leather: 65,
    MaterialTypeEnum.bamboo: 62,
    
    # Moderate sustainability (40-59)
    MaterialTypeEnum.wool: 55,
    MaterialTypeEnum.silk: 52,
    MaterialTypeEnum.cashmere: 48,
    MaterialTypeEnum.conventional_cotton: 45,
    
    # Low sustainability (20-39)
    MaterialTypeEnum.viscose: 38,
    MaterialTypeEnum.virgin_polyester: 28,
    MaterialTypeEnum.nylon: 25,
    MaterialTypeEnum.leather: 22,
    
    # Default
    MaterialTypeEnum.other: 40,
}

# Carbon footprint per kg of material (kg CO2)
MATERIAL_CARBON_FOOTPRINT = {
    MaterialTypeEnum.organic_cotton: 2.5,
    MaterialTypeEnum.conventional_cotton: 5.5,
    MaterialTypeEnum.hemp: 1.5,
    MaterialTypeEnum.linen: 3.0,
    MaterialTypeEnum.tencel_lyocell: 2.0,
    MaterialTypeEnum.modal: 4.0,
    MaterialTypeEnum.viscose: 6.0,
    MaterialTypeEnum.virgin_polyester: 14.2,
    MaterialTypeEnum.recycled_polyester: 5.5,
    MaterialTypeEnum.nylon: 18.0,
    MaterialTypeEnum.recycled_nylon: 7.0,
    MaterialTypeEnum.wool: 25.0,
    MaterialTypeEnum.organic_wool: 15.0,
    MaterialTypeEnum.silk: 35.0,
    MaterialTypeEnum.leather: 65.0,
    MaterialTypeEnum.recycled_leather: 25.0,
    MaterialTypeEnum.vegan_leather: 15.0,
    MaterialTypeEnum.cashmere: 80.0,
    MaterialTypeEnum.organic_cashmere: 50.0,
    MaterialTypeEnum.bamboo: 4.0,
    MaterialTypeEnum.organic_bamboo: 2.5,
    MaterialTypeEnum.other: 10.0,
}

# Water usage per kg of material (Liters)
MATERIAL_WATER_USAGE = {
    MaterialTypeEnum.organic_cotton: 2500,
    MaterialTypeEnum.conventional_cotton: 10000,
    MaterialTypeEnum.hemp: 500,
    MaterialTypeEnum.linen: 800,
    MaterialTypeEnum.tencel_lyocell: 600,
    MaterialTypeEnum.modal: 1500,
    MaterialTypeEnum.viscose: 3000,
    MaterialTypeEnum.virgin_polyester: 200,
    MaterialTypeEnum.recycled_polyester: 100,
    MaterialTypeEnum.nylon: 250,
    MaterialTypeEnum.recycled_nylon: 120,
    MaterialTypeEnum.wool: 150000,  # Includes sheep rearing
    MaterialTypeEnum.organic_wool: 120000,
    MaterialTypeEnum.silk: 50000,
    MaterialTypeEnum.leather: 17000,  # Tanning process
    MaterialTypeEnum.recycled_leather: 5000,
    MaterialTypeEnum.vegan_leather: 3000,
    MaterialTypeEnum.cashmere: 200000,
    MaterialTypeEnum.organic_cashmere: 180000,
    MaterialTypeEnum.bamboo: 2500,
    MaterialTypeEnum.organic_bamboo: 1500,
    MaterialTypeEnum.other: 5000,
}

# Manufacturing region sustainability modifiers
REGION_MODIFIERS = {
    ManufacturingRegionEnum.europe: 1.15,  # Higher standards
    ManufacturingRegionEnum.north_america: 1.10,
    ManufacturingRegionEnum.south_america: 0.95,
    ManufacturingRegionEnum.east_asia: 0.85,
    ManufacturingRegionEnum.southeast_asia: 0.80,
    ManufacturingRegionEnum.south_asia: 0.75,
    ManufacturingRegionEnum.africa: 0.85,
    ManufacturingRegionEnum.middle_east: 0.80,
}

# Shipping emissions per km per kg (kg CO2)
SHIPPING_EMISSIONS = {
    "air": 0.00112,
    "express": 0.00112,  # Same as air
    "sea": 0.00004,
    "ground": 0.00021,
    "rail": 0.00004,
}


# ═══════════════════════════════════════════════════════════════════
# SUSTAINABILITY SCORING ENGINE
# ═══════════════════════════════════════════════════════════════════

class SustainabilityScoringEngine:
    """
    Core sustainability scoring engine.
    Calculates comprehensive sustainability scores for products.
    """
    
    # Default weights for score components
    DEFAULT_WEIGHTS = {
        "material": 0.35,
        "brand": 0.25,
        "manufacturing": 0.25,
        "shipping": 0.15,
    }
    
    def __init__(self, db_session=None):
        self.db = db_session
        self._brand_cache: Dict[str, BrandSustainability] = {}
    
    async def calculate_product_score(
        self,
        product_id: str,
        brand_id: Optional[str] = None,
        materials: List[MaterialCompositionDTO] = None,
        manufacturing: Optional[ManufacturingInfoDTO] = None,
        shipping: Optional[ShippingInfoDTO] = None,
        category: Optional[str] = None,
        existing_certifications: List[str] = None,
        weights: Dict[str, float] = None,
    ) -> Tuple[SustainabilityScoreDTO, List[EcoBadgeEnum]]:
        """
        Calculate comprehensive sustainability score for a product.
        
        Returns tuple of (score_dto, earned_badges)
        """
        materials = materials or []
        existing_certifications = existing_certifications or []
        weights = weights or self.DEFAULT_WEIGHTS
        
        # Calculate component scores
        material_score = self._calculate_material_score(materials, existing_certifications)
        brand_score = await self._calculate_brand_score(brand_id)
        manufacturing_score = self._calculate_manufacturing_score(manufacturing)
        shipping_score = self._calculate_shipping_score(shipping)
        
        # Calculate weighted overall score
        overall_score = (
            material_score * weights.get("material", 0.35) +
            brand_score * weights.get("brand", 0.25) +
            manufacturing_score * weights.get("manufacturing", 0.25) +
            shipping_score * weights.get("shipping", 0.15)
        )
        
        # Determine tier
        tier = self._determine_tier(overall_score)
        
        # Calculate impact breakdown
        impact_breakdown = self._calculate_impact_breakdown(
            materials, manufacturing, shipping
        )
        
        # Determine earned eco badges
        eco_badges = self._determine_eco_badges(
            material_score, brand_score, manufacturing_score,
            shipping_score, materials, existing_certifications
        )
        
        # Build response DTO
        score_dto = SustainabilityScoreDTO(
            product_id=product_id,
            overall_score=round(overall_score, 1),
            tier=tier.value,
            material_score=round(material_score, 1),
            brand_score=round(brand_score, 1),
            manufacturing_score=round(manufacturing_score, 1),
            shipping_score=round(shipping_score, 1),
            eco_badges=[badge.value for badge in eco_badges],
            certifications=existing_certifications,
            impact_breakdown=impact_breakdown,
            category_average=None,  # Would be calculated from category data
            percentile_rank=None,
            verified=False,
            last_updated=datetime.now(timezone.utc),
        )
        
        return score_dto, eco_badges
    
    def _calculate_material_score(
        self,
        materials: List[MaterialCompositionDTO],
        certifications: List[str],
    ) -> float:
        """Calculate material sustainability score."""
        if not materials:
            return 40.0  # Default moderate score if no data
        
        total_score = 0.0
        total_percentage = 0.0
        
        for material in materials:
            # Get base score for material type
            material_type = self._parse_material_type(material.material_type)
            base_score = MATERIAL_BASE_SCORES.get(material_type, 40.0)
            
            # Apply modifiers
            modifier = 1.0
            
            # Organic certification bonus
            if material.certified_organic:
                modifier += 0.15
            
            # Recycled content bonus
            if material.certified_recycled:
                modifier += 0.12
            
            # GOTS certification bonus
            if "gots" in [c.lower() for c in certifications]:
                modifier += 0.10
            
            # Calculate weighted score
            weighted_score = base_score * modifier * (material.percentage / 100)
            total_score += weighted_score
            total_percentage += material.percentage
        
        # Normalize if percentages don't sum to 100
        if total_percentage > 0:
            total_score = total_score * (100 / total_percentage)
        
        return min(100.0, max(0.0, total_score))
    
    def _parse_material_type(self, material_str: str) -> MaterialTypeEnum:
        """Parse material string to enum."""
        material_lower = material_str.lower().replace(" ", "_").replace("-", "_")
        
        # Direct match
        for mat_type in MaterialTypeEnum:
            if mat_type.value == material_lower:
                return mat_type
        
        # Fuzzy matching
        if "organic" in material_lower and "cotton" in material_lower:
            return MaterialTypeEnum.organic_cotton
        if "recycled" in material_lower and "polyester" in material_lower:
            return MaterialTypeEnum.recycled_polyester
        if "recycled" in material_lower and "nylon" in material_lower:
            return MaterialTypeEnum.recycled_nylon
        if "recycled" in material_lower and "leather" in material_lower:
            return MaterialTypeEnum.recycled_leather
        if "tencel" in material_lower or "lyocell" in material_lower:
            return MaterialTypeEnum.tencel_lyocell
        if "organic" in material_lower and "wool" in material_lower:
            return MaterialTypeEnum.organic_wool
        if "organic" in material_lower and "bamboo" in material_lower:
            return MaterialTypeEnum.organic_bamboo
        if "organic" in material_lower and "cashmere" in material_lower:
            return MaterialTypeEnum.organic_cashmere
        if "cotton" in material_lower:
            return MaterialTypeEnum.conventional_cotton
        if "polyester" in material_lower:
            return MaterialTypeEnum.virgin_polyester
        if "nylon" in material_lower:
            return MaterialTypeEnum.nylon
        if "leather" in material_lower and "vegan" in material_lower:
            return MaterialTypeEnum.vegan_leather
        if "leather" in material_lower:
            return MaterialTypeEnum.leather
        if "wool" in material_lower:
            return MaterialTypeEnum.wool
        if "silk" in material_lower:
            return MaterialTypeEnum.silk
        if "linen" in material_lower:
            return MaterialTypeEnum.linen
        if "hemp" in material_lower:
            return MaterialTypeEnum.hemp
        if "modal" in material_lower:
            return MaterialTypeEnum.modal
        if "viscose" in material_lower or "rayon" in material_lower:
            return MaterialTypeEnum.viscose
        if "cashmere" in material_lower:
            return MaterialTypeEnum.cashmere
        if "bamboo" in material_lower:
            return MaterialTypeEnum.bamboo
        
        return MaterialTypeEnum.other
    
    async def _calculate_brand_score(self, brand_id: Optional[str]) -> float:
        """Calculate brand sustainability score."""
        if not brand_id:
            return 50.0  # Default moderate score if no brand
        
        # Check cache
        if brand_id in self._brand_cache:
            brand = self._brand_cache[brand_id]
            return brand.overall_score if brand else 50.0
        
        # Look up brand sustainability profile
        brand_profile = None
        if self.db:
            try:
                brand_profile = await self.db.get(BrandSustainability, brand_id)
                self._brand_cache[brand_id] = brand_profile
            except Exception as e:
                logger.warning(f"Could not fetch brand sustainability for {brand_id}: {e}")
        
        if brand_profile:
            return brand_profile.overall_score
        
        # Estimate based on brand name heuristics
        return self._estimate_brand_score(brand_id)
    
    def _estimate_brand_score(self, brand_id: str) -> float:
        """Estimate brand sustainability score from brand ID/name."""
        brand_lower = brand_id.lower()
        
        # Known sustainable brands
        sustainable_brands = [
            "patagonia", "reformation", "everlane", "stella-mccartney",
            "eileen-fisher", "veja", "allbirds", "outerknown", "pact",
            "tentree", "ecothread"
        ]
        
        # Fast fashion brands (lower scores)
        fast_fashion_brands = [
            "zara", "h&m", "boohoo", "asos", "topshop", "urban-outfitters"
        ]
        
        # Luxury brands (moderate scores)
        luxury_brands = [
            "gucci", "prada", "versace", "louis-vuitton", "chanel",
            "hermes", "dior", "balenciaga"
        ]
        
        if any(sb in brand_lower for sb in sustainable_brands):
            return 80.0
        if any(ff in brand_lower for ff in fast_fashion_brands):
            return 35.0
        if any(lb in brand_lower for lb in luxury_brands):
            return 55.0
        
        return 50.0  # Default moderate score
    
    def _calculate_manufacturing_score(
        self,
        manufacturing: Optional[ManufacturingInfoDTO],
    ) -> float:
        """Calculate manufacturing sustainability score."""
        if not manufacturing:
            return 50.0  # Default moderate score
        
        base_score = 50.0
        
        # Region modifier
        if manufacturing.region:
            region_enum = self._parse_region(manufacturing.region)
            region_modifier = REGION_MODIFIERS.get(region_enum, 1.0)
            base_score *= region_modifier
        
        # Factory certification bonus
        if manufacturing.factory_certified:
            base_score += 15.0
            
            # Additional bonus for specific certifications
            cert_bonuses = {
                "bluesign": 8.0,
                "gots": 10.0,
                "fair_trade": 7.0,
                "b_corp": 5.0,
                "sa8000": 6.0,
                "iso14001": 5.0,
                "leed": 4.0,
            }
            
            for cert in manufacturing.factory_certifications:
                cert_lower = cert.lower().replace(" ", "_").replace("-", "_")
                for cert_name, bonus in cert_bonuses.items():
                    if cert_name in cert_lower:
                        base_score += bonus
        
        # Energy source bonus
        if manufacturing.energy_source:
            if manufacturing.energy_source.lower() == "renewable":
                base_score += 12.0
            elif manufacturing.energy_source.lower() == "mixed":
                base_score += 5.0
        
        # Water treatment bonus
        if manufacturing.water_treatment:
            base_score += 5.0
        
        # Chemical management bonus
        if manufacturing.chemical_management_system:
            base_score += 5.0
        
        return min(100.0, max(0.0, base_score))
    
    def _parse_region(self, region_str: str) -> ManufacturingRegionEnum:
        """Parse region string to enum."""
        region_lower = region_str.lower().replace(" ", "_").replace("-", "_")
        
        region_mapping = {
            "europe": ManufacturingRegionEnum.europe,
            "eu": ManufacturingRegionEnum.europe,
            "north_america": ManufacturingRegionEnum.north_america,
            "usa": ManufacturingRegionEnum.north_america,
            "canada": ManufacturingRegionEnum.north_america,
            "usa/canada": ManufacturingRegionEnum.north_america,
            "east_asia": ManufacturingRegionEnum.east_asia,
            "china": ManufacturingRegionEnum.east_asia,
            "japan": ManufacturingRegionEnum.east_asia,
            "korea": ManufacturingRegionEnum.east_asia,
            "southeast_asia": ManufacturingRegionEnum.southeast_asia,
            "vietnam": ManufacturingRegionEnum.southeast_asia,
            "thailand": ManufacturingRegionEnum.southeast_asia,
            "indonesia": ManufacturingRegionEnum.southeast_asia,
            "south_asia": ManufacturingRegionEnum.south_asia,
            "india": ManufacturingRegionEnum.south_asia,
            "bangladesh": ManufacturingRegionEnum.south_asia,
            "pakistan": ManufacturingRegionEnum.south_asia,
            "south_america": ManufacturingRegionEnum.south_america,
            "brazil": ManufacturingRegionEnum.south_america,
            "africa": ManufacturingRegionEnum.africa,
            "middle_east": ManufacturingRegionEnum.middle_east,
            "turkey": ManufacturingRegionEnum.middle_east,
        }
        
        return region_mapping.get(region_lower, ManufacturingRegionEnum.east_asia)
    
    def _calculate_shipping_score(
        self,
        shipping: Optional[ShippingInfoDTO],
    ) -> float:
        """Calculate shipping sustainability score."""
        if not shipping:
            return 50.0  # Default moderate score
        
        base_score = 50.0
        
        # Shipping method impact
        method_scores = {
            "sea": 75.0,
            "rail": 75.0,
            "ground": 60.0,
            "air": 30.0,
            "express": 25.0,  # Express is usually air
        }
        
        if shipping.shipping_method:
            method_lower = shipping.shipping_method.lower()
            base_score = method_scores.get(method_lower, 50.0)
        
        # Packaging sustainability bonus
        packaging_bonuses = {
            "biodegradable": 15.0,
            "recycled": 12.0,
            "standard": 0.0,
            "plastic": -10.0,
        }
        
        if shipping.packaging_type:
            pkg_lower = shipping.packaging_type.lower()
            base_score += packaging_bonuses.get(pkg_lower, 0.0)
        
        # Recycled content bonus
        if shipping.packaging_recycled_content > 0:
            base_score += min(10.0, shipping.packaging_recycled_content / 10)
        
        return min(100.0, max(0.0, base_score))
    
    def _determine_tier(self, score: float) -> SustainabilityTierEnum:
        """Determine sustainability tier from score."""
        if score >= 90:
            return SustainabilityTierEnum.excellent
        elif score >= 80:
            return SustainabilityTierEnum.very_good
        elif score >= 70:
            return SustainabilityTierEnum.good
        elif score >= 60:
            return SustainabilityTierEnum.fair
        elif score >= 50:
            return SustainabilityTierEnum.moderate
        elif score >= 40:
            return SustainabilityTierEnum.low
        else:
            return SustainabilityTierEnum.poor
    
    def _calculate_impact_breakdown(
        self,
        materials: List[MaterialCompositionDTO],
        manufacturing: Optional[ManufacturingInfoDTO],
        shipping: Optional[ShippingInfoDTO],
    ) -> Dict[str, Any]:
        """Calculate detailed impact breakdown for display."""
        breakdown = {}
        
        # Carbon impact
        carbon_kg = self._estimate_carbon_footprint(materials, shipping)
        carbon_rating = self._rate_carbon(carbon_kg)
        breakdown["carbon"] = {
            "value": round(carbon_kg, 1),
            "unit": "kg CO2",
            "rating": carbon_rating,
            "description": f"Estimated {carbon_kg:.1f} kg CO2 emissions",
        }
        
        # Water impact
        water_l = self._estimate_water_usage(materials)
        water_rating = self._rate_water(water_l)
        breakdown["water"] = {
            "value": int(water_l),
            "unit": "L",
            "rating": water_rating,
            "description": f"Estimated {int(water_l)} liters water usage",
        }
        
        # Chemical impact
        chemical_rating = self._rate_chemicals(manufacturing)
        breakdown["chemicals"] = {
            "value": chemical_rating,
            "rating": chemical_rating,
            "description": f"Chemical usage: {chemical_rating}",
        }
        
        # Waste impact
        waste_rating = self._estimate_waste_rating(manufacturing, shipping)
        breakdown["waste"] = {
            "value": waste_rating,
            "rating": waste_rating,
            "description": f"Waste generation: {waste_rating}",
        }
        
        return breakdown
    
    def _estimate_carbon_footprint(
        self,
        materials: List[MaterialCompositionDTO],
        shipping: Optional[ShippingInfoDTO],
    ) -> float:
        """Estimate total carbon footprint in kg CO2."""
        total_carbon = 0.0
        
        # Material carbon (assuming ~0.5kg average garment weight)
        garment_weight_kg = 0.5
        
        for material in materials:
            material_type = self._parse_material_type(material.material_type)
            carbon_per_kg = MATERIAL_CARBON_FOOTPRINT.get(material_type, 10.0)
            material_weight = garment_weight_kg * (material.percentage / 100)
            total_carbon += carbon_per_kg * material_weight
        
        # Shipping carbon (estimate distance)
        if shipping and shipping.shipping_method:
            distance_km = 8000  # Default long-haul distance
            emissions_factor = SHIPPING_EMISSIONS.get(
                shipping.shipping_method.lower(), 0.00021
            )
            total_carbon += distance_km * emissions_factor * garment_weight_kg
        
        return total_carbon
    
    def _estimate_water_usage(self, materials: List[MaterialCompositionDTO]) -> float:
        """Estimate total water usage in liters."""
        total_water = 0.0
        garment_weight_kg = 0.5
        
        for material in materials:
            material_type = self._parse_material_type(material.material_type)
            water_per_kg = MATERIAL_WATER_USAGE.get(material_type, 5000)
            material_weight = garment_weight_kg * (material.percentage / 100)
            total_water += water_per_kg * material_weight
        
        return total_water
    
    def _rate_carbon(self, carbon_kg: float) -> str:
        """Rate carbon footprint."""
        if carbon_kg < 5:
            return "excellent"
        elif carbon_kg < 10:
            return "good"
        elif carbon_kg < 20:
            return "moderate"
        elif carbon_kg < 40:
            return "poor"
        else:
            return "very_poor"
    
    def _rate_water(self, water_l: float) -> str:
        """Rate water usage."""
        if water_l < 1000:
            return "excellent"
        elif water_l < 2500:
            return "good"
        elif water_l < 5000:
            return "moderate"
        elif water_l < 10000:
            return "poor"
        else:
            return "very_poor"
    
    def _rate_chemicals(self, manufacturing: Optional[ManufacturingInfoDTO]) -> str:
        """Rate chemical usage."""
        if not manufacturing:
            return "moderate"
        
        if manufacturing.chemical_management_system:
            return "good"
        
        if manufacturing.factory_certified:
            return "good"
        
        return "moderate"
    
    def _estimate_waste_rating(
        self,
        manufacturing: Optional[ManufacturingInfoDTO],
        shipping: Optional[ShippingInfoDTO],
    ) -> str:
        """Estimate waste generation rating."""
        base_rating = "moderate"
        
        if manufacturing and manufacturing.factory_certified:
            base_rating = "good"
        
        if shipping:
            if shipping.packaging_type in ["biodegradable", "recycled"]:
                base_rating = "good"
            elif shipping.packaging_type == "plastic":
                base_rating = "poor"
        
        return base_rating
    
    def _determine_eco_badges(
        self,
        material_score: float,
        brand_score: float,
        manufacturing_score: float,
        shipping_score: float,
        materials: List[MaterialCompositionDTO],
        certifications: List[str],
    ) -> List[EcoBadgeEnum]:
        """Determine earned eco badges based on scores and certifications."""
        badges = []
        cert_lower = [c.lower() for c in certifications]
        
        # Organic badge
        if any(m.certified_organic for m in materials) or "organic" in cert_lower:
            badges.append(EcoBadgeEnum.organic)
        
        # Recycled badge
        if any(m.certified_recycled for m in materials) or "recycled" in cert_lower:
            badges.append(EcoBadgeEnum.recycled)
        
        # Fair trade badge
        if "fair_trade" in cert_lower:
            badges.append(EcoBadgeEnum.fair_trade)
        
        # Carbon neutral badge
        if brand_score >= 75 and shipping_score >= 70:
            badges.append(EcoBadgeEnum.carbon_neutral)
        
        # Water saved badge
        if material_score >= 75:
            badges.append(EcoBadgeEnum.water_saved)
        
        # Sustainable materials badge
        if material_score >= 70:
            badges.append(EcoBadgeEnum.sustainable_materials)
        
        # Ethical manufacturing badge
        if manufacturing_score >= 70:
            badges.append(EcoBadgeEnum.ethical_manufacturing)
        
        # Low impact dye badge
        if "bluesign" in cert_lower or "oeko_tex" in cert_lower:
            badges.append(EcoBadgeEnum.low_impact_dye)
        
        # Biodegradable badge
        natural_materials = [
            MaterialTypeEnum.organic_cotton,
            MaterialTypeEnum.hemp,
            MaterialTypeEnum.linen,
            MaterialTypeEnum.wool,
            MaterialTypeEnum.organic_wool,
            MaterialTypeEnum.silk,
            MaterialTypeEnum.cashmere,
            MaterialTypeEnum.organic_cashmere,
        ]
        if materials:
            primary_material = self._parse_material_type(materials[0].material_type)
            if primary_material in natural_materials and materials[0].percentage >= 70:
                badges.append(EcoBadgeEnum.biodegradable)
        
        # GOTS certified badge
        if "gots" in cert_lower:
            badges.append(EcoBadgeEnum.gots_certified)
        
        # Bluesign badge
        if "bluesign" in cert_lower:
            badges.append(EcoBadgeEnum.bluesign)
        
        # Cradle to cradle badge
        if "cradle_to_cradle" in cert_lower:
            badges.append(EcoBadgeEnum.cradle_to_cradle)
        
        # Upcycled badge
        if "upcycled" in cert_lower:
            badges.append(EcoBadgeEnum.upcycled)
        
        return list(set(badges))  # Remove duplicates


# ═══════════════════════════════════════════════════════════════════
# SUSTAINABILITY SERVICE
# ═══════════════════════════════════════════════════════════════════

class SustainabilityService:
    """
    Main service for sustainability operations.
    Wraps the scoring engine with database operations.
    """
    
    def __init__(self, db_session=None):
        self.db = db_session
        self.engine = SustainabilityScoringEngine(db_session)
    
    async def get_product_sustainability(
        self,
        product_id: str,
    ) -> Optional[SustainabilityScoreDTO]:
        """Get sustainability score for a product."""
        # Try database first
        if self.db:
            score = await self.db.get(SustainabilityScore, product_id)
            if score:
                return SustainabilityScoreDTO(
                    product_id=score.product_id,
                    overall_score=score.overall_score,
                    tier=score.tier.value,
                    material_score=score.material_score,
                    brand_score=score.brand_score,
                    manufacturing_score=score.manufacturing_score,
                    shipping_score=score.shipping_score,
                    eco_badges=[b.get("badge", b) if isinstance(b, dict) else b for b in score.eco_badges],
                    certifications=[c.get("name", c) if isinstance(c, dict) else c for c in score.certifications],
                    impact_breakdown=score.impact_breakdown,
                    category_average=score.category_average_score,
                    percentile_rank=score.percentile_rank,
                    verified=score.verified,
                    last_updated=score.last_calculated_at,
                )
        
        # Calculate on-the-fly if not in database
        # This would require product data - for now return None
        return None
    
    async def calculate_and_store_product_score(
        self,
        input_data: ProductSustainabilityInputDTO,
    ) -> SustainabilityScoreDTO:
        """Calculate and store sustainability score for a product."""
        score_dto, badges = await self.engine.calculate_product_score(
            product_id=input_data.product_id,
            brand_id=input_data.brand_id,
            materials=input_data.materials,
            manufacturing=input_data.manufacturing,
            shipping=input_data.shipping,
            category=input_data.category,
            existing_certifications=input_data.existing_certifications,
        )
        
        # Store in database if available
        if self.db:
            score_record = SustainabilityScore(
                product_id=input_data.product_id,
                brand_id=input_data.brand_id,
                overall_score=score_dto.overall_score,
                tier=SustainabilityTierEnum(score_dto.tier),
                material_score=score_dto.material_score,
                brand_score=score_dto.brand_score,
                manufacturing_score=score_dto.manufacturing_score,
                shipping_score=score_dto.shipping_score,
                eco_badges=[{"badge": b} for b in score_dto.eco_badges],
                certifications=[{"name": c} for c in score_dto.certifications],
                impact_breakdown=score_dto.impact_breakdown,
                last_calculated_at=datetime.now(timezone.utc),
            )
            
            self.db.add(score_record)
            await self.db.commit()
        
        return score_dto
    
    async def get_brand_sustainability(
        self,
        brand_id: str,
    ) -> Optional[BrandSustainabilityDTO]:
        """Get sustainability profile for a brand."""
        if not self.db:
            return None
        
        brand = await self.db.get(BrandSustainability, brand_id)
        if not brand:
            return None
        
        return BrandSustainabilityDTO(
            brand_id=brand.brand_id,
            overall_score=brand.overall_score,
            environmental_score=brand.environmental_score,
            social_score=brand.social_score,
            governance_score=brand.governance_score,
            certifications=[c.get("name", c) if isinstance(c, dict) else c for c in brand.certifications],
            eco_badges=[b.get("badge", b) if isinstance(b, dict) else b for b in brand.eco_badges],
            sustainable_materials_pct=brand.sustainable_materials_percentage,
            recycled_materials_pct=brand.recycled_materials_percentage,
            renewable_energy_usage=brand.renewable_energy_usage,
            carbon_offset_program=brand.carbon_offset_program,
            living_wage_commitment=brand.living_wage_commitment,
            supply_chain_transparency=brand.supply_chain_transparency,
            verification_status=brand.verification_status,
        )
    
    async def get_products_by_sustainability_tier(
        self,
        tier: SustainabilityTierEnum,
        limit: int = 20,
        offset: int = 0,
    ) -> List[SustainabilityScoreDTO]:
        """Get products filtered by sustainability tier."""
        if not self.db:
            return []
        
        from sqlalchemy import select
        
        query = (
            select(SustainabilityScore)
            .where(SustainabilityScore.tier == tier)
            .order_by(SustainabilityScore.overall_score.desc())
            .limit(limit)
            .offset(offset)
        )
        
        result = await self.db.execute(query)
        scores = result.scalars().all()
        
        return [
            SustainabilityScoreDTO(
                product_id=s.product_id,
                overall_score=s.overall_score,
                tier=s.tier.value,
                material_score=s.material_score,
                brand_score=s.brand_score,
                manufacturing_score=s.manufacturing_score,
                shipping_score=s.shipping_score,
                eco_badges=[b.get("badge", b) if isinstance(b, dict) else b for b in s.eco_badges],
                certifications=[c.get("name", c) if isinstance(c, dict) else c for c in s.certifications],
                impact_breakdown=s.impact_breakdown,
                category_average=s.category_average_score,
                percentile_rank=s.percentile_rank,
                verified=s.verified,
                last_updated=s.last_calculated_at,
            )
            for s in scores
        ]
    
    async def get_top_sustainable_products(
        self,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[SustainabilityScoreDTO]:
        """Get top sustainable products, optionally filtered by category."""
        if not self.db:
            return []
        
        from sqlalchemy import select
        
        query = (
            select(SustainabilityScore)
            .order_by(SustainabilityScore.overall_score.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        scores = result.scalars().all()
        
        return [
            SustainabilityScoreDTO(
                product_id=s.product_id,
                overall_score=s.overall_score,
                tier=s.tier.value,
                material_score=s.material_score,
                brand_score=s.brand_score,
                manufacturing_score=s.manufacturing_score,
                shipping_score=s.shipping_score,
                eco_badges=[b.get("badge", b) if isinstance(b, dict) else b for b in s.eco_badges],
                certifications=[c.get("name", c) if isinstance(c, dict) else c for c in s.certifications],
                impact_breakdown=s.impact_breakdown,
                category_average=s.category_average_score,
                percentile_rank=s.percentile_rank,
                verified=s.verified,
                last_updated=s.last_calculated_at,
            )
            for s in scores
        ]
