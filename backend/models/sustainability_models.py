"""
CONFIT Backend — Sustainability Models
======================================
Sustainability scoring and environmental impact tracking.
"""

import enum
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text,
    JSON, Numeric, Enum as SQLEnum, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from database.base import Base
from database.models import UUIDType

_DB_URL = os.getenv("DATABASE_URL", "sqlite:///./confit.db")
if not _DB_URL.startswith("postgresql"):
    JSONB = JSON  # type: ignore[assignment]


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class VersionMixin:
    version = Column(Integer, nullable=False, default=1)


# ═══════════════════════════════════════════════════════════════════
# ENUMERATED TYPES
# ═══════════════════════════════════════════════════════════════════

class EcoBadgeEnum(str, enum.Enum):
    """Environmental certification badges."""
    organic = "organic"
    recycled = "recycled"
    fair_trade = "fair_trade"
    carbon_neutral = "carbon_neutral"
    water_saved = "water_saved"
    sustainable_materials = "sustainable_materials"
    ethical_manufacturing = "ethical_manufacturing"
    low_impact_dye = "low_impact_dye"
    biodegradable = "biodegradable"
    upcycled = "upcycled"
    gots_certified = "gots_certified"
    bluesign = "bluesign"
    cradle_to_cradle = "cradle_to_cradle"


class SustainabilityTierEnum(str, enum.Enum):
    """Overall sustainability rating tiers."""
    excellent = "excellent"      # 90-100
    very_good = "very_good"      # 80-89
    good = "good"                # 70-79
    fair = "fair"                # 60-69
    moderate = "moderate"        # 50-59
    low = "low"                  # 40-49
    poor = "poor"                # 0-39


class MaterialTypeEnum(str, enum.Enum):
    """Material type categories for sustainability scoring."""
    organic_cotton = "organic_cotton"
    conventional_cotton = "conventional_cotton"
    recycled_polyester = "recycled_polyester"
    virgin_polyester = "virgin_polyester"
    wool = "wool"
    organic_wool = "organic_wool"
    silk = "silk"
    linen = "linen"
    hemp = "hemp"
    tencel_lyocell = "tencel_lyocell"
    modal = "modal"
    viscose = "viscose"
    nylon = "nylon"
    recycled_nylon = "recycled_nylon"
    leather = "leather"
    vegan_leather = "vegan_leather"
    recycled_leather = "recycled_leather"
    cashmere = "cashmere"
    organic_cashmere = "organic_cashmere"
    bamboo = "bamboo"
    organic_bamboo = "organic_bamboo"
    other = "other"


class ManufacturingRegionEnum(str, enum.Enum):
    """Manufacturing regions with sustainability considerations."""
    europe = "europe"
    north_america = "north_america"
    east_asia = "east_asia"
    southeast_asia = "southeast_asia"
    south_asia = "south_asia"
    south_america = "south_america"
    africa = "africa"
    middle_east = "middle_east"


# ═══════════════════════════════════════════════════════════════════
# BRAND SUSTAINABILITY PROFILE
# ═══════════════════════════════════════════════════════════════════

class BrandSustainability(Base, TimestampMixin, VersionMixin):
    """
    Brand-level sustainability profile and certifications.
    Tracks overall brand environmental and ethical practices.
    """
    __tablename__ = "brand_sustainability"
    
    # Identity
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    brand_id = Column(String(36), nullable=False, unique=True, index=True)
    
    # Overall Scores (0-100)
    overall_score = Column(Float, nullable=False, default=0.0)
    environmental_score = Column(Float, nullable=False, default=0.0)
    social_score = Column(Float, nullable=False, default=0.0)
    governance_score = Column(Float, nullable=False, default=0.0)
    
    # Brand Practices
    sustainability_report_published = Column(Boolean, nullable=False, default=False)
    carbon_offset_program = Column(Boolean, nullable=False, default=False)
    water_reduction_program = Column(Boolean, nullable=False, default=False)
    renewable_energy_usage = Column(Float, nullable=False, default=0.0)  # Percentage
    living_wage_commitment = Column(Boolean, nullable=False, default=False)
    supply_chain_transparency = Column(Float, nullable=False, default=0.0)  # 0-100 score
    
    # Certifications
    certifications = Column(JSONB, nullable=False, default=list)  # List of certification objects
    eco_badges = Column(JSONB, nullable=False, default=list)  # List of EcoBadgeEnum values
    
    # Supply Chain
    factory_audit_score = Column(Float, nullable=True)  # 0-100
    supplier_code_of_conduct = Column(Boolean, nullable=False, default=False)
    traceability_score = Column(Float, nullable=False, default=0.0)  # 0-100
    
    # Materials Policy
    sustainable_materials_percentage = Column(Float, nullable=False, default=0.0)
    recycled_materials_percentage = Column(Float, nullable=False, default=0.0)
    organic_materials_percentage = Column(Float, nullable=False, default=0.0)
    materials_policy_url = Column(Text, nullable=True)
    
    # Shipping & Packaging
    sustainable_packaging = Column(Boolean, nullable=False, default=False)
    carbon_neutral_shipping = Column(Boolean, nullable=False, default=False)
    packaging_recycled_content = Column(Float, nullable=False, default=0.0)  # Percentage
    
    # Third-party Ratings
    b_corp_certified = Column(Boolean, nullable=False, default=False)
    b_corp_score = Column(Float, nullable=True)
    fashion_transparency_index = Column(Float, nullable=True)  # 0-100
    
    # Metadata
    last_audit_date = Column(DateTime(timezone=True), nullable=True)
    next_audit_date = Column(DateTime(timezone=True), nullable=True)
    data_source = Column(String(100), nullable=True)  # Where data was sourced from
    verification_status = Column(String(50), nullable=False, default="unverified")
    notes = Column(Text, nullable=True)
    
    __table_args__ = (
        CheckConstraint('overall_score >= 0 AND overall_score <= 100', name='chk_overall_score'),
        CheckConstraint('environmental_score >= 0 AND environmental_score <= 100', name='chk_env_score'),
        CheckConstraint('social_score >= 0 AND social_score <= 100', name='chk_social_score'),
        CheckConstraint('governance_score >= 0 AND governance_score <= 100', name='chk_gov_score'),
        Index('ix_brand_sustainability_score', 'overall_score'),
    )


# ═══════════════════════════════════════════════════════════════════
# PRODUCT SUSTAINABILITY SCORE
# ═══════════════════════════════════════════════════════════════════

class SustainabilityScore(Base, TimestampMixin, VersionMixin):
    """
    Product-level sustainability scoring.
    Aggregates material, manufacturing, brand, and shipping impact.
    """
    __tablename__ = "sustainability_scores"
    
    # Identity
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    product_id = Column(String(36), nullable=False, unique=True, index=True)
    brand_id = Column(String(36), nullable=True, index=True)
    
    # Overall Score
    overall_score = Column(Float, nullable=False, default=0.0)  # 0-100
    tier = Column(SQLEnum(SustainabilityTierEnum), nullable=False, default=SustainabilityTierEnum.moderate)
    
    # Component Scores (0-100 each)
    material_score = Column(Float, nullable=False, default=0.0)
    brand_score = Column(Float, nullable=False, default=0.0)
    manufacturing_score = Column(Float, nullable=False, default=0.0)
    shipping_score = Column(Float, nullable=False, default=0.0)
    
    # Score Weights (configurable, sum to 1.0)
    material_weight = Column(Float, nullable=False, default=0.35)
    brand_weight = Column(Float, nullable=False, default=0.25)
    manufacturing_weight = Column(Float, nullable=False, default=0.25)
    shipping_weight = Column(Float, nullable=False, default=0.15)
    
    # Material Impact Details
    materials = Column(JSONB, nullable=False, default=list)  # List of material breakdowns
    primary_material = Column(String(100), nullable=True)
    material_composition = Column(JSONB, nullable=False, default=dict)  # {material: percentage}
    recycled_content_percentage = Column(Float, nullable=False, default=0.0)
    organic_content_percentage = Column(Float, nullable=False, default=0.0)
    
    # Manufacturing Impact
    manufacturing_region = Column(SQLEnum(ManufacturingRegionEnum), nullable=True)
    manufacturing_country = Column(String(100), nullable=True)
    factory_certified = Column(Boolean, nullable=False, default=False)
    factory_certifications = Column(JSONB, nullable=False, default=list)
    energy_efficiency_score = Column(Float, nullable=True)  # 0-100
    water_usage_score = Column(Float, nullable=True)  # 0-100 (higher = less water used)
    chemical_management_score = Column(Float, nullable=True)  # 0-100
    
    # Shipping Impact
    shipping_origin = Column(String(100), nullable=True)
    estimated_shipping_distance_km = Column(Float, nullable=True)
    shipping_method = Column(String(50), nullable=True)
    carbon_footprint_kg = Column(Float, nullable=True)  # Estimated CO2 in kg
    packaging_sustainability_score = Column(Float, nullable=True)  # 0-100
    
    # Eco Badges (computed based on criteria)
    eco_badges = Column(JSONB, nullable=False, default=list)  # List of earned badges
    
    # Impact Breakdown (for display)
    impact_breakdown = Column(JSONB, nullable=False, default=dict)
    # Structure: {
    #   "carbon": {"value": 5.2, "unit": "kg", "rating": "low"},
    #   "water": {"value": 1200, "unit": "L", "rating": "moderate"},
    #   "chemicals": {"value": "low", "rating": "good"},
    #   "waste": {"value": "minimal", "rating": "good"}
    # }
    
    # Comparison Context
    category_average_score = Column(Float, nullable=True)  # Average for this product category
    percentile_rank = Column(Float, nullable=True)  # Percentile within category
    
    # Certification & Verification
    certifications = Column(JSONB, nullable=False, default=list)
    verified = Column(Boolean, nullable=False, default=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(String(36), nullable=True)
    
    # Data Sources
    data_sources = Column(JSONB, nullable=False, default=list)  # Where data was obtained
    last_calculated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    calculation_version = Column(String(20), nullable=False, default="1.0")
    
    __table_args__ = (
        CheckConstraint('overall_score >= 0 AND overall_score <= 100', name='chk_product_overall'),
        CheckConstraint('material_score >= 0 AND material_score <= 100', name='chk_material_score'),
        CheckConstraint('brand_score >= 0 AND brand_score <= 100', name='chk_brand_score'),
        CheckConstraint('manufacturing_score >= 0 AND manufacturing_score <= 100', name='chk_mfg_score'),
        CheckConstraint('shipping_score >= 0 AND shipping_score <= 100', name='chk_ship_score'),
        Index('ix_sustainability_product_score', 'overall_score'),
        Index('ix_sustainability_tier', 'tier'),
    )


# ═══════════════════════════════════════════════════════════════════
# MATERIAL SUSTAINABILITY REFERENCE
# ═══════════════════════════════════════════════════════════════════

class MaterialSustainabilityReference(Base, TimestampMixin):
    """
    Reference table for material sustainability scores.
    Used as baseline for calculating product material scores.
    """
    __tablename__ = "material_sustainability_reference"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    material_type = Column(SQLEnum(MaterialTypeEnum), nullable=False, unique=True)
    material_name = Column(String(100), nullable=False)
    
    # Base sustainability score (0-100)
    base_score = Column(Float, nullable=False)
    
    # Environmental impact factors
    carbon_footprint_per_kg = Column(Float, nullable=True)  # kg CO2 per kg material
    water_usage_per_kg = Column(Float, nullable=True)  # Liters per kg
    biodegradability_score = Column(Float, nullable=True)  # 0-100
    recyclability_score = Column(Float, nullable=True)  # 0-100
    
    # Chemical impact
    chemical_usage_score = Column(Float, nullable=True)  # 0-100 (higher = less chemicals)
    dye_impact_score = Column(Float, nullable=True)  # 0-100
    
    # Source and processing
    is_natural = Column(Boolean, nullable=False, default=False)
    is_renewable = Column(Boolean, nullable=False, default=False)
    is_biodegradable = Column(Boolean, nullable=False, default=False)
    is_recyclable = Column(Boolean, nullable=False, default=False)
    
    # Description and alternatives
    description = Column(Text, nullable=True)
    sustainable_alternatives = Column(JSONB, nullable=False, default=list)
    
    __table_args__ = (
        CheckConstraint('base_score >= 0 AND base_score <= 100', name='chk_material_base_score'),
    )


# ═══════════════════════════════════════════════════════════════════
# SUSTAINABILITY AUDIT LOG
# ═══════════════════════════════════════════════════════════════════

class SustainabilityAuditLog(Base, TimestampMixin):
    """
    Audit trail for sustainability score changes and updates.
    """
    __tablename__ = "sustainability_audit_log"
    
    id = Column(UUIDType, primary_key=True, default=generate_uuid)
    
    # Target
    entity_type = Column(String(50), nullable=False)  # 'product' or 'brand'
    entity_id = Column(String(36), nullable=False, index=True)
    
    # Change Details
    action = Column(String(50), nullable=False)  # 'create', 'update', 'verify', 'recalculate'
    previous_score = Column(Float, nullable=True)
    new_score = Column(Float, nullable=True)
    score_delta = Column(Float, nullable=True)
    
    # Context
    reason = Column(Text, nullable=True)
    data_source = Column(String(100), nullable=True)
    calculation_details = Column(JSONB, nullable=True)
    
    # Actor
    performed_by = Column(String(36), nullable=True)  # User ID or 'system'
    performed_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    
    __table_args__ = (
        Index('ix_sustainability_audit_entity', 'entity_type', 'entity_id'),
    )
