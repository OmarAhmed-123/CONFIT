-- CONFIT Sustainability Tables Migration
-- Creates tables for sustainability scoring and brand sustainability profiles

-- ═══════════════════════════════════════════════════════════════════
-- BRAND SUSTAINABILITY PROFILE
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS brand_sustainability (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id VARCHAR(36) NOT NULL UNIQUE,
    
    -- Overall Scores (0-100)
    overall_score FLOAT NOT NULL DEFAULT 0.0 CHECK (overall_score >= 0 AND overall_score <= 100),
    environmental_score FLOAT NOT NULL DEFAULT 0.0 CHECK (environmental_score >= 0 AND environmental_score <= 100),
    social_score FLOAT NOT NULL DEFAULT 0.0 CHECK (social_score >= 0 AND social_score <= 100),
    governance_score FLOAT NOT NULL DEFAULT 0.0 CHECK (governance_score >= 0 AND governance_score <= 100),
    
    -- Brand Practices
    sustainability_report_published BOOLEAN NOT NULL DEFAULT FALSE,
    carbon_offset_program BOOLEAN NOT NULL DEFAULT FALSE,
    water_reduction_program BOOLEAN NOT NULL DEFAULT FALSE,
    renewable_energy_usage FLOAT NOT NULL DEFAULT 0.0,
    living_wage_commitment BOOLEAN NOT NULL DEFAULT FALSE,
    supply_chain_transparency FLOAT NOT NULL DEFAULT 0.0 CHECK (supply_chain_transparency >= 0 AND supply_chain_transparency <= 100),
    
    -- Certifications
    certifications JSONB NOT NULL DEFAULT '[]'::jsonb,
    eco_badges JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Supply Chain
    factory_audit_score FLOAT CHECK (factory_audit_score >= 0 AND factory_audit_score <= 100),
    supplier_code_of_conduct BOOLEAN NOT NULL DEFAULT FALSE,
    traceability_score FLOAT NOT NULL DEFAULT 0.0 CHECK (traceability_score >= 0 AND traceability_score <= 100),
    
    -- Materials Policy
    sustainable_materials_percentage FLOAT NOT NULL DEFAULT 0.0,
    recycled_materials_percentage FLOAT NOT NULL DEFAULT 0.0,
    organic_materials_percentage FLOAT NOT NULL DEFAULT 0.0,
    materials_policy_url TEXT,
    
    -- Shipping & Packaging
    sustainable_packaging BOOLEAN NOT NULL DEFAULT FALSE,
    carbon_neutral_shipping BOOLEAN NOT NULL DEFAULT FALSE,
    packaging_recycled_content FLOAT NOT NULL DEFAULT 0.0,
    
    -- Third-party Ratings
    b_corp_certified BOOLEAN NOT NULL DEFAULT FALSE,
    b_corp_score FLOAT,
    fashion_transparency_index FLOAT CHECK (fashion_transparency_index >= 0 AND fashion_transparency_index <= 100),
    
    -- Metadata
    last_audit_date TIMESTAMP WITH TIME ZONE,
    next_audit_date TIMESTAMP WITH TIME ZONE,
    data_source VARCHAR(100),
    verification_status VARCHAR(50) NOT NULL DEFAULT 'unverified',
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    version INTEGER NOT NULL DEFAULT 1
);

-- Indexes for brand_sustainability
CREATE INDEX ix_brand_sustainability_brand_id ON brand_sustainability(brand_id);
CREATE INDEX ix_brand_sustainability_score ON brand_sustainability(overall_score);

-- ═══════════════════════════════════════════════════════════════════
-- PRODUCT SUSTAINABILITY SCORE
-- ═══════════════════════════════════════════════════════════════════

CREATE TYPE sustainability_tier AS ENUM (
    'excellent', 'very_good', 'good', 'fair', 'moderate', 'low', 'poor'
);

CREATE TYPE manufacturing_region AS ENUM (
    'europe', 'north_america', 'east_asia', 'southeast_asia', 
    'south_asia', 'south_america', 'africa', 'middle_east'
);

CREATE TABLE IF NOT EXISTS sustainability_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id VARCHAR(36) NOT NULL UNIQUE,
    brand_id VARCHAR(36),
    
    -- Overall Score
    overall_score FLOAT NOT NULL DEFAULT 0.0 CHECK (overall_score >= 0 AND overall_score <= 100),
    tier sustainability_tier NOT NULL DEFAULT 'moderate',
    
    -- Component Scores (0-100 each)
    material_score FLOAT NOT NULL DEFAULT 0.0 CHECK (material_score >= 0 AND material_score <= 100),
    brand_score FLOAT NOT NULL DEFAULT 0.0 CHECK (brand_score >= 0 AND brand_score <= 100),
    manufacturing_score FLOAT NOT NULL DEFAULT 0.0 CHECK (manufacturing_score >= 0 AND manufacturing_score <= 100),
    shipping_score FLOAT NOT NULL DEFAULT 0.0 CHECK (shipping_score >= 0 AND shipping_score <= 100),
    
    -- Score Weights
    material_weight FLOAT NOT NULL DEFAULT 0.35,
    brand_weight FLOAT NOT NULL DEFAULT 0.25,
    manufacturing_weight FLOAT NOT NULL DEFAULT 0.25,
    shipping_weight FLOAT NOT NULL DEFAULT 0.15,
    
    -- Material Impact Details
    materials JSONB NOT NULL DEFAULT '[]'::jsonb,
    primary_material VARCHAR(100),
    material_composition JSONB NOT NULL DEFAULT '{}'::jsonb,
    recycled_content_percentage FLOAT NOT NULL DEFAULT 0.0,
    organic_content_percentage FLOAT NOT NULL DEFAULT 0.0,
    
    -- Manufacturing Impact
    manufacturing_region manufacturing_region,
    manufacturing_country VARCHAR(100),
    factory_certified BOOLEAN NOT NULL DEFAULT FALSE,
    factory_certifications JSONB NOT NULL DEFAULT '[]'::jsonb,
    energy_efficiency_score FLOAT CHECK (energy_efficiency_score >= 0 AND energy_efficiency_score <= 100),
    water_usage_score FLOAT CHECK (water_usage_score >= 0 AND water_usage_score <= 100),
    chemical_management_score FLOAT CHECK (chemical_management_score >= 0 AND chemical_management_score <= 100),
    
    -- Shipping Impact
    shipping_origin VARCHAR(100),
    estimated_shipping_distance_km FLOAT,
    shipping_method VARCHAR(50),
    carbon_footprint_kg FLOAT,
    packaging_sustainability_score FLOAT CHECK (packaging_sustainability_score >= 0 AND packaging_sustainability_score <= 100),
    
    -- Eco Badges
    eco_badges JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Impact Breakdown
    impact_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Comparison Context
    category_average_score FLOAT,
    percentile_rank FLOAT,
    
    -- Certification & Verification
    certifications JSONB NOT NULL DEFAULT '[]'::jsonb,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    verified_at TIMESTAMP WITH TIME ZONE,
    verified_by VARCHAR(36),
    
    -- Data Sources
    data_sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_calculated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    calculation_version VARCHAR(20) NOT NULL DEFAULT '1.0',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    version INTEGER NOT NULL DEFAULT 1
);

-- Indexes for sustainability_scores
CREATE INDEX ix_sustainability_product_id ON sustainability_scores(product_id);
CREATE INDEX ix_sustainability_brand_id ON sustainability_scores(brand_id);
CREATE INDEX ix_sustainability_product_score ON sustainability_scores(overall_score);
CREATE INDEX ix_sustainability_tier ON sustainability_scores(tier);

-- ═══════════════════════════════════════════════════════════════════
-- MATERIAL SUSTAINABILITY REFERENCE
-- ═══════════════════════════════════════════════════════════════════

CREATE TYPE material_type AS ENUM (
    'organic_cotton', 'conventional_cotton', 'recycled_polyester', 'virgin_polyester',
    'wool', 'organic_wool', 'silk', 'linen', 'hemp', 'tencel_lyocell', 'modal',
    'viscose', 'nylon', 'recycled_nylon', 'leather', 'vegan_leather', 'recycled_leather',
    'cashmere', 'organic_cashmere', 'bamboo', 'organic_bamboo', 'other'
);

CREATE TABLE IF NOT EXISTS material_sustainability_reference (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_type material_type NOT NULL UNIQUE,
    material_name VARCHAR(100) NOT NULL,
    
    -- Base sustainability score (0-100)
    base_score FLOAT NOT NULL CHECK (base_score >= 0 AND base_score <= 100),
    
    -- Environmental impact factors
    carbon_footprint_per_kg FLOAT,
    water_usage_per_kg FLOAT,
    biodegradability_score FLOAT CHECK (biodegradability_score >= 0 AND biodegradability_score <= 100),
    recyclability_score FLOAT CHECK (recyclability_score >= 0 AND recyclability_score <= 100),
    
    -- Chemical impact
    chemical_usage_score FLOAT CHECK (chemical_usage_score >= 0 AND chemical_usage_score <= 100),
    dye_impact_score FLOAT CHECK (dye_impact_score >= 0 AND dye_impact_score <= 100),
    
    -- Source and processing
    is_natural BOOLEAN NOT NULL DEFAULT FALSE,
    is_renewable BOOLEAN NOT NULL DEFAULT FALSE,
    is_biodegradable BOOLEAN NOT NULL DEFAULT FALSE,
    is_recyclable BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Description and alternatives
    description TEXT,
    sustainable_alternatives JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════════
-- SUSTAINABILITY AUDIT LOG
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sustainability_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Target
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(36) NOT NULL,
    
    -- Change Details
    action VARCHAR(50) NOT NULL,
    previous_score FLOAT,
    new_score FLOAT,
    score_delta FLOAT,
    
    -- Context
    reason TEXT,
    data_source VARCHAR(100),
    calculation_details JSONB,
    
    -- Actor
    performed_by VARCHAR(36),
    performed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Index for audit log
CREATE INDEX ix_sustainability_audit_entity ON sustainability_audit_log(entity_type, entity_id);

-- ═══════════════════════════════════════════════════════════════════
-- SEED MATERIAL REFERENCE DATA
-- ═══════════════════════════════════════════════════════════════════

INSERT INTO material_sustainability_reference (material_type, material_name, base_score, carbon_footprint_per_kg, water_usage_per_kg, is_natural, is_renewable, is_biodegradable, is_recyclable) VALUES
    -- High sustainability
    ('organic_cotton', 'Organic Cotton', 85, 2.5, 2500, TRUE, TRUE, TRUE, TRUE),
    ('hemp', 'Hemp', 90, 1.5, 500, TRUE, TRUE, TRUE, TRUE),
    ('tencel_lyocell', 'Tencel/Lyocell', 88, 2.0, 600, TRUE, TRUE, TRUE, TRUE),
    ('organic_wool', 'Organic Wool', 82, 15.0, 120000, TRUE, TRUE, TRUE, FALSE),
    ('organic_cashmere', 'Organic Cashmere', 80, 50.0, 180000, TRUE, TRUE, TRUE, FALSE),
    ('recycled_polyester', 'Recycled Polyester', 78, 5.5, 100, FALSE, FALSE, FALSE, TRUE),
    ('recycled_nylon', 'Recycled Nylon', 77, 7.0, 120, FALSE, FALSE, FALSE, TRUE),
    ('recycled_leather', 'Recycled Leather', 72, 25.0, 5000, FALSE, FALSE, FALSE, TRUE),
    ('organic_bamboo', 'Organic Bamboo', 83, 2.5, 1500, TRUE, TRUE, TRUE, TRUE),
    
    -- Good sustainability
    ('linen', 'Linen', 75, 3.0, 800, TRUE, TRUE, TRUE, TRUE),
    ('modal', 'Modal', 68, 4.0, 1500, TRUE, TRUE, TRUE, TRUE),
    ('vegan_leather', 'Vegan Leather', 65, 15.0, 3000, FALSE, FALSE, FALSE, TRUE),
    ('bamboo', 'Bamboo', 62, 4.0, 2500, TRUE, TRUE, TRUE, TRUE),
    
    -- Moderate sustainability
    ('wool', 'Wool', 55, 25.0, 150000, TRUE, TRUE, TRUE, FALSE),
    ('silk', 'Silk', 52, 35.0, 50000, TRUE, TRUE, TRUE, FALSE),
    ('cashmere', 'Cashmere', 48, 80.0, 200000, TRUE, TRUE, TRUE, FALSE),
    ('conventional_cotton', 'Conventional Cotton', 45, 5.5, 10000, TRUE, TRUE, TRUE, TRUE),
    
    -- Low sustainability
    ('viscose', 'Viscose', 38, 6.0, 3000, TRUE, FALSE, FALSE, FALSE),
    ('virgin_polyester', 'Virgin Polyester', 28, 14.2, 200, FALSE, FALSE, FALSE, TRUE),
    ('nylon', 'Nylon', 25, 18.0, 250, FALSE, FALSE, FALSE, TRUE),
    ('leather', 'Leather', 22, 65.0, 17000, TRUE, FALSE, TRUE, FALSE),
    
    -- Default
    ('other', 'Other Materials', 40, 10.0, 5000, FALSE, FALSE, FALSE, FALSE)
ON CONFLICT (material_type) DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════
-- TRIGGER FOR UPDATED_AT
-- ═══════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_brand_sustainability_updated_at
    BEFORE UPDATE ON brand_sustainability
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sustainability_scores_updated_at
    BEFORE UPDATE ON sustainability_scores
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_material_reference_updated_at
    BEFORE UPDATE ON material_sustainability_reference
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
