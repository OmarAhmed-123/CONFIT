-- ============================================================
-- CONFIT — Production-Grade PostgreSQL Schema
-- Created: 2026-03-06
-- Description: Complete normalized schema for global fashion commerce
-- Version: 1.0.0
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- For trigram similarity search
CREATE EXTENSION IF NOT EXISTS "postgis";      -- For geospatial queries

-- ═══════════════════════════════════════════════════════════════════
-- UTILITY FUNCTIONS
-- ═══════════════════════════════════════════════════════════════════

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Soft delete function
CREATE OR REPLACE FUNCTION soft_delete()
RETURNS TRIGGER AS $$
BEGIN
    NEW.deleted_at = NOW();
    NEW.is_active = FALSE;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Generate secure random token
CREATE OR REPLACE FUNCTION generate_secure_token(length INT DEFAULT 32)
RETURNS TEXT AS $$
BEGIN
    RETURN encode(gen_random_bytes(length), 'hex');
END;
$$ LANGUAGE plpgsql;

-- ═══════════════════════════════════════════════════════════════════
-- ENUMERATED TYPES
-- ═══════════════════════════════════════════════════════════════════

-- User roles
CREATE TYPE user_role_enum AS ENUM ('admin', 'brand_manager', 'stylist', 'user', 'moderator');

-- Order status
CREATE TYPE order_status_enum AS ENUM (
    'pending', 'confirmed', 'processing', 'shipped', 'delivered',
    'cancelled', 'refunded', 'returned', 'failed'
);

-- Payment status
CREATE TYPE payment_status_enum AS ENUM (
    'pending', 'processing', 'completed', 'failed', 'refunded', 'partially_refunded', 'disputed'
);

-- Payment method
CREATE TYPE payment_method_enum AS ENUM (
    'card', 'apple_pay', 'google_pay', 'paypal', 'bnpl_affirm', 'bnpl_klarna', 'bnpl_afterpay', 'store_credit'
);

-- BNPL status
CREATE TYPE bnpl_status_enum AS ENUM (
    'pending', 'approved', 'active', 'paid', 'defaulted', 'cancelled'
);

-- Product status
CREATE TYPE product_status_enum AS ENUM ('draft', 'active', 'out_of_stock', 'discontinued', 'archived');

-- Inventory status
CREATE TYPE inventory_status_enum AS ENUM ('in_stock', 'low_stock', 'out_of_stock', 'reserved', 'discontinued');

-- Try-on status
CREATE TYPE tryon_status_enum AS ENUM ('pending', 'processing', 'completed', 'failed', 'expired');

-- Visual search status
CREATE TYPE visual_search_status_enum AS ENUM ('pending', 'processing', 'completed', 'failed');

-- Recommendation type
CREATE TYPE recommendation_type_enum AS ENUM (
    'personalized', 'trending', 'similar', 'complementary', 'occasion', 'seasonal', 'price_drop'
);

-- Event type for tracking
CREATE TYPE event_type_enum AS ENUM (
    'view', 'click', 'add_to_cart', 'remove_from_cart', 'purchase', 'wishlist_add',
    'wishlist_remove', 'try_on', 'search', 'share', 'review', 'return', 'refund'
);

-- ═══════════════════════════════════════════════════════════════════
-- CORE USER MODULE
-- ═══════════════════════════════════════════════════════════════════

-- Users table (extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS public.users (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Identity
    email                   VARCHAR(255) NOT NULL UNIQUE,
    email_verified          BOOLEAN NOT NULL DEFAULT FALSE,
    phone                   VARCHAR(32),
    phone_verified          BOOLEAN NOT NULL DEFAULT FALSE,
    password_hash           VARCHAR(255) NOT NULL,
    
    -- Profile
    name                    VARCHAR(255) NOT NULL,
    first_name              VARCHAR(100),
    last_name               VARCHAR(100),
    display_name            VARCHAR(100),
    avatar_url              TEXT,
    bio                     TEXT,
    date_of_birth           DATE,
    gender                  VARCHAR(20),
    
    -- Location
    country_code            CHAR(2),
    timezone                VARCHAR(50) DEFAULT 'UTC',
    language                VARCHAR(10) DEFAULT 'en',
    currency                VARCHAR(3) DEFAULT 'USD',
    
    -- Status
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified             BOOLEAN NOT NULL DEFAULT FALSE,
    is_staff                BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at              TIMESTAMPTZ,
    
    -- Settings
    settings                JSONB NOT NULL DEFAULT '{}',
    notification_preferences JSONB NOT NULL DEFAULT '{}',
    
    -- Metadata
    last_login_at           TIMESTAMPTZ,
    last_login_ip           INET,
    login_count             INTEGER NOT NULL DEFAULT 0,
    
    -- Versioning & Audit
    version                 INTEGER NOT NULL DEFAULT 1,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- User indexes
CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_users_phone ON public.users(phone) WHERE phone IS NOT NULL;
CREATE INDEX idx_users_country ON public.users(country_code);
CREATE INDEX idx_users_active ON public.users(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_users_deleted ON public.users(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX idx_users_created ON public.users(created_at DESC);

-- User roles (many-to-many)
CREATE TABLE IF NOT EXISTS public.user_roles (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    role                    user_role_enum NOT NULL DEFAULT 'user',
    granted_by              UUID REFERENCES public.users(id),
    granted_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at              TIMESTAMPTZ,
    
    UNIQUE(user_id, role)
);

CREATE INDEX idx_user_roles_user ON public.user_roles(user_id);
CREATE INDEX idx_user_roles_role ON public.user_roles(role);

-- User sessions (for JWT refresh tokens)
CREATE TABLE IF NOT EXISTS public.user_sessions (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Session data
    refresh_token_hash      VARCHAR(64) NOT NULL,
    device_type             VARCHAR(20),
    device_name             VARCHAR(100),
    os                      VARCHAR(50),
    browser                 VARCHAR(50),
    ip_address              INET,
    user_agent              TEXT,
    location_country        CHAR(2),
    location_city           VARCHAR(100),
    
    -- Status
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    last_activity_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at              TIMESTAMPTZ NOT NULL,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_session_not_expired CHECK (expires_at > created_at)
);

CREATE INDEX idx_sessions_user ON public.user_sessions(user_id);
CREATE INDEX idx_sessions_token ON public.user_sessions(refresh_token_hash);
CREATE INDEX idx_sessions_active ON public.user_sessions(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_sessions_expires ON public.user_sessions(expires_at);

-- User addresses
CREATE TABLE IF NOT EXISTS public.user_addresses (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Address details
    label                   VARCHAR(50),  -- 'home', 'work', 'other'
    recipient_name          VARCHAR(255) NOT NULL,
    phone                   VARCHAR(32),
    
    -- Location
    address_line1           VARCHAR(255) NOT NULL,
    address_line2           VARCHAR(255),
    city                    VARCHAR(100) NOT NULL,
    state_province          VARCHAR(100),
    postal_code             VARCHAR(20) NOT NULL,
    country_code            CHAR(2) NOT NULL,
    
    -- Coordinates
    location                GEOGRAPHY(POINT, 4326),
    
    -- Status
    is_default_shipping     BOOLEAN NOT NULL DEFAULT FALSE,
    is_default_billing      BOOLEAN NOT NULL DEFAULT FALSE,
    is_verified             BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Audit
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_addresses_user ON public.user_addresses(user_id);
CREATE INDEX idx_addresses_location ON public.user_addresses USING GIST(location);

-- ═══════════════════════════════════════════════════════════════════
-- USER STYLE PROFILES MODULE
-- ═══════════════════════════════════════════════════════════════════

-- Style profiles (main)
CREATE TABLE IF NOT EXISTS public.user_style_profiles (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Archetype
    primary_archetype       VARCHAR(50),
    secondary_archetypes    JSONB NOT NULL DEFAULT '[]',
    archetype_confidence    NUMERIC(3,2) DEFAULT 0.0,
    
    -- Style Vector (8 dimensions: 0.0-1.0)
    style_classic           NUMERIC(3,2) DEFAULT 0.5,
    style_trendy            NUMERIC(3,2) DEFAULT 0.5,
    style_minimalist        NUMERIC(3,2) DEFAULT 0.5,
    style_maximalist        NUMERIC(3,2) DEFAULT 0.5,
    style_feminine          NUMERIC(3,2) DEFAULT 0.5,
    style_masculine         NUMERIC(3,2) DEFAULT 0.5,
    style_edgy              NUMERIC(3,2) DEFAULT 0.5,
    style_romantic          NUMERIC(3,2) DEFAULT 0.5,
    
    -- Color preferences
    skin_undertone          VARCHAR(20) CHECK (skin_undertone IN ('warm', 'cool', 'neutral')),
    preferred_colors        JSONB NOT NULL DEFAULT '[]',
    avoided_colors          JSONB NOT NULL DEFAULT '[]',
    color_confidence        NUMERIC(3,2) DEFAULT 0.0,
    
    -- Pattern & Fabric
    pattern_preferences     JSONB NOT NULL DEFAULT '{}',
    fabric_preferences      JSONB NOT NULL DEFAULT '[]',
    
    -- Silhouette
    silhouette_preferences  JSONB NOT NULL DEFAULT '{}',
    fit_preference          VARCHAR(30) DEFAULT 'regular',
    
    -- Status
    profile_completeness    NUMERIC(5,2) DEFAULT 0.0,
    onboarding_completed    BOOLEAN NOT NULL DEFAULT FALSE,
    onboarding_phase        INTEGER DEFAULT 0,
    
    -- Versioning
    version                 INTEGER NOT NULL DEFAULT 1,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_style_profiles_user ON public.user_style_profiles(user_id);
CREATE INDEX idx_style_profiles_archetype ON public.user_style_profiles(primary_archetype);

-- Body profiles
CREATE TABLE IF NOT EXISTS public.user_body_profiles (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
    
    profile_status          VARCHAR(20) DEFAULT 'not_set',
    
    -- Measurements (cm)
    height_cm               INTEGER CHECK (height_cm BETWEEN 100 AND 250),
    weight_kg               INTEGER CHECK (weight_kg BETWEEN 30 AND 300),
    chest_cm                INTEGER CHECK (chest_cm BETWEEN 50 AND 200),
    waist_cm                INTEGER CHECK (waist_cm BETWEEN 40 AND 200),
    hips_cm                 INTEGER CHECK (hips_cm BETWEEN 50 AND 200),
    inseam_cm               INTEGER CHECK (inseam_cm BETWEEN 50 AND 120),
    shoulder_width_cm       INTEGER CHECK (shoulder_width_cm BETWEEN 30 AND 70),
    arm_length_cm           INTEGER CHECK (arm_length_cm BETWEEN 40 AND 90),
    
    -- Classification
    body_shape              VARCHAR(50),
    
    -- Sizes
    size_tops               VARCHAR(10),
    size_bottoms            VARCHAR(10),
    size_dresses            VARCHAR(10),
    size_shoes              VARCHAR(10),
    brand_size_overrides    JSONB NOT NULL DEFAULT '{}',
    
    -- Fit issues
    fit_issues              JSONB NOT NULL DEFAULT '[]',
    
    -- Versioning
    version                 INTEGER NOT NULL DEFAULT 1,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_body_profiles_user ON public.user_body_profiles(user_id);

-- Budget profiles
CREATE TABLE IF NOT EXISTS public.user_budget_profiles (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
    
    per_item_min            NUMERIC(10,2),
    per_item_max            NUMERIC(10,2),
    monthly_max             NUMERIC(10,2),
    currency                VARCHAR(3) DEFAULT 'USD',
    investment_willing      BOOLEAN NOT NULL DEFAULT FALSE,
    price_sensitivity       NUMERIC(3,2) DEFAULT 0.5,
    
    version                 INTEGER NOT NULL DEFAULT 1,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_budget_profiles_user ON public.user_budget_profiles(user_id);

-- Brand affinities (many-to-many)
CREATE TABLE IF NOT EXISTS public.user_brand_affinities (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    brand_id                VARCHAR(64) NOT NULL,  -- Reference to brands table
    
    affinity_score          NUMERIC(3,2) DEFAULT 0.5,
    affinity_source         VARCHAR(30) DEFAULT 'explicit',  -- 'explicit', 'implicit', 'inferred'
    reason                  TEXT,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, brand_id)
);

CREATE INDEX idx_brand_affinities_user ON public.user_brand_affinities(user_id);
CREATE INDEX idx_brand_affinities_brand ON public.user_brand_affinities(brand_id);

-- Contextual preferences
CREATE TABLE IF NOT EXISTS public.user_contextual_preferences (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Occasion weights
    occasion_weights        JSONB NOT NULL DEFAULT '{}',
    
    -- Lifestyle
    work_environment        VARCHAR(30),
    climate_zone            VARCHAR(30),
    activity_level          VARCHAR(20),
    has_children            BOOLEAN,
    pet_friendly            BOOLEAN,
    
    -- Weather preferences
    weather_preferences     JSONB NOT NULL DEFAULT '{}',
    
    -- Cultural
    cultural_influences     JSONB NOT NULL DEFAULT '[]',
    modesty_preference      VARCHAR(20),
    
    -- Social
    style_icons             JSONB NOT NULL DEFAULT '[]',
    social_influences       JSONB NOT NULL DEFAULT '[]',
    
    version                 INTEGER NOT NULL DEFAULT 1,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_contextual_prefs_user ON public.user_contextual_preferences(user_id);

-- ═══════════════════════════════════════════════════════════════════
-- BRAND MODULE
-- ═══════════════════════════════════════════════════════════════════

-- Brands
CREATE TABLE IF NOT EXISTS public.brands (
    id                      VARCHAR(64) PRIMARY KEY,  -- Slug-based ID
    name                    VARCHAR(255) NOT NULL,
    slug                    VARCHAR(255) NOT NULL UNIQUE,
    description             TEXT,
    
    -- Branding
    logo_url                TEXT,
    banner_url              TEXT,
    icon_url                TEXT,
    
    -- Contact
    website                 VARCHAR(512),
    contact_email           VARCHAR(255),
    support_email           VARCHAR(255),
    support_phone           VARCHAR(32),
    
    -- Social
    social_links            JSONB NOT NULL DEFAULT '{}',
    
    -- Business
    industry                VARCHAR(50),
    founded_year            INTEGER,
    headquarters_country    CHAR(2),
    headquarters_city       VARCHAR(100),
    
    -- Status
    is_verified             BOOLEAN NOT NULL DEFAULT FALSE,
    is_featured             BOOLEAN NOT NULL DEFAULT FALSE,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Statistics (denormalized for performance)
    product_count           INTEGER NOT NULL DEFAULT 0,
    follower_count          INTEGER NOT NULL DEFAULT 0,
    rating_average          NUMERIC(3,2),
    review_count            INTEGER NOT NULL DEFAULT 0,
    
    -- Settings
    commission_rate         NUMERIC(4,3) DEFAULT 0.100,
    return_policy_days      INTEGER DEFAULT 30,
    
    -- Metadata
    metadata                JSONB NOT NULL DEFAULT '{}',
    
    -- Soft delete
    deleted_at              TIMESTAMPTZ,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_brands_slug ON public.brands(slug);
CREATE INDEX idx_brands_name ON public.brands USING gin(name gin_trgm_ops);
CREATE INDEX idx_brands_active ON public.brands(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_brands_featured ON public.brands(is_featured) WHERE is_featured = TRUE;
CREATE INDEX idx_brands_industry ON public.brands(industry);

-- Brand managers (many-to-many)
CREATE TABLE IF NOT EXISTS public.brand_managers (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id                VARCHAR(64) NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
    user_id                 UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    role                    VARCHAR(30) NOT NULL DEFAULT 'manager',  -- 'owner', 'admin', 'manager', 'viewer'
    permissions             JSONB NOT NULL DEFAULT '[]',
    
    invited_by              UUID REFERENCES public.users(id),
    invited_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_at             TIMESTAMPTZ,
    
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    
    UNIQUE(brand_id, user_id)
);

CREATE INDEX idx_brand_managers_brand ON public.brand_managers(brand_id);
CREATE INDEX idx_brand_managers_user ON public.brand_managers(user_id);

-- Brand followers
CREATE TABLE IF NOT EXISTS public.brand_followers (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id                VARCHAR(64) NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
    user_id                 UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    notification_enabled    BOOLEAN NOT NULL DEFAULT TRUE,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(brand_id, user_id)
);

CREATE INDEX idx_brand_followers_brand ON public.brand_followers(brand_id);
CREATE INDEX idx_brand_followers_user ON public.brand_followers(user_id);

-- ═══════════════════════════════════════════════════════════════════
-- PRODUCT MODULE
-- ═══════════════════════════════════════════════════════════════════

-- Product categories (hierarchical)
CREATE TABLE IF NOT EXISTS public.product_categories (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_id               UUID REFERENCES public.product_categories(id) ON DELETE SET NULL,
    
    name                    VARCHAR(100) NOT NULL,
    slug                    VARCHAR(100) NOT NULL UNIQUE,
    description             TEXT,
    
    -- Display
    icon                    VARCHAR(50),
    image_url               TEXT,
    
    -- Hierarchy
    level                   INTEGER NOT NULL DEFAULT 0,
    path                    VARCHAR(500),  -- Materialized path: /parent/child/grandchild
    
    -- Status
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    is_featured             BOOLEAN NOT NULL DEFAULT FALSE,
    display_order           INTEGER NOT NULL DEFAULT 0,
    
    -- SEO
    meta_title              VARCHAR(255),
    meta_description        TEXT,
    
    -- Statistics
    product_count           INTEGER NOT NULL DEFAULT 0,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_categories_parent ON public.product_categories(parent_id);
CREATE INDEX idx_categories_slug ON public.product_categories(slug);
CREATE INDEX idx_categories_path ON public.product_categories(path);
CREATE INDEX idx_categories_level ON public.product_categories(level);

-- Products
CREATE TABLE IF NOT EXISTS public.products (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Identification
    sku                     VARCHAR(100) UNIQUE,
    barcode                 VARCHAR(50),
    
    -- Core info
    name                    VARCHAR(255) NOT NULL,
    slug                    VARCHAR(255) NOT NULL,
    description             TEXT,
    
    -- Classification
    brand_id                VARCHAR(64) REFERENCES public.brands(id) ON DELETE SET NULL,
    category_id             UUID REFERENCES public.product_categories(id) ON DELETE SET NULL,
    subcategory_id          UUID REFERENCES public.product_categories(id) ON DELETE SET NULL,
    
    -- Attributes
    color                   VARCHAR(50),
    color_hex               CHAR(7),
    material                VARCHAR(100),
    pattern                 VARCHAR(50),
    style_tags              JSONB NOT NULL DEFAULT '[]',
    occasion_tags           JSONB NOT NULL DEFAULT '[]',
    season_tags             JSONB NOT NULL DEFAULT '[]',
    
    -- Pricing
    base_price              NUMERIC(10,2) NOT NULL,
    sale_price              NUMERIC(10,2),
    currency                VARCHAR(3) NOT NULL DEFAULT 'USD',
    cost_price              NUMERIC(10,2),  -- For margin calculation
    
    -- Status
    status                  product_status_enum NOT NULL DEFAULT 'draft',
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    is_featured             BOOLEAN NOT NULL DEFAULT FALSE,
    is_new_arrival          BOOLEAN NOT NULL DEFAULT FALSE,
    is_bestseller           BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Dates
    published_at            TIMESTAMPTZ,
    sale_starts_at          TIMESTAMPTZ,
    sale_ends_at            TIMESTAMPTZ,
    
    -- Statistics (denormalized)
    view_count              INTEGER NOT NULL DEFAULT 0,
    purchase_count          INTEGER NOT NULL DEFAULT 0,
    wishlist_count          INTEGER NOT NULL DEFAULT 0,
    rating_average          NUMERIC(3,2),
    review_count            INTEGER NOT NULL DEFAULT 0,
    return_rate             NUMERIC(5,2),
    
    -- SEO
    meta_title              VARCHAR(255),
    meta_description        TEXT,
    meta_keywords           JSONB NOT NULL DEFAULT '[]',
    
    -- Media
    primary_image_url       TEXT,
    images                  JSONB NOT NULL DEFAULT '[]',
    videos                  JSONB NOT NULL DEFAULT '[]',
    
    -- Dimensions (for shipping)
    weight_kg               NUMERIC(6,3),
    length_cm               NUMERIC(6,2),
    width_cm                NUMERIC(6,2),
    height_cm               NUMERIC(6,2),
    
    -- AI compatibility scores
    style_compatibility     INTEGER DEFAULT 85,
    color_compatibility     INTEGER,
    
    -- Versioning
    version                 INTEGER NOT NULL DEFAULT 1,
    
    -- Soft delete
    deleted_at              TIMESTAMPTZ,
    
    -- Metadata
    attributes              JSONB NOT NULL DEFAULT '{}',
    metadata                JSONB NOT NULL DEFAULT '{}',
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_price_positive CHECK (base_price >= 0),
    CONSTRAINT chk_sale_price CHECK (sale_price IS NULL OR sale_price <= base_price)
);

-- Product indexes
CREATE INDEX idx_products_brand ON public.products(brand_id);
CREATE INDEX idx_products_category ON public.products(category_id);
CREATE INDEX idx_products_sku ON public.products(sku);
CREATE INDEX idx_products_slug ON public.products(slug);
CREATE INDEX idx_products_name ON public.products USING gin(name gin_trgm_ops);
CREATE INDEX idx_products_status ON public.products(status);
CREATE INDEX idx_products_active ON public.products(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_products_price ON public.products(base_price);
CREATE INDEX idx_products_created ON public.products(created_at DESC);
CREATE INDEX idx_products_featured ON public.products(is_featured) WHERE is_featured = TRUE;
CREATE INDEX idx_products_style_tags ON public.products USING gin(style_tags);
CREATE INDEX idx_products_occasion_tags ON public.products USING gin(occasion_tags);

-- Product variants (size, color combinations)
CREATE TABLE IF NOT EXISTS public.product_variants (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id              UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    
    -- Identification
    sku                     VARCHAR(100) UNIQUE,
    barcode                 VARCHAR(50),
    
    -- Variant attributes
    size                    VARCHAR(20),
    color                   VARCHAR(50),
    color_hex               CHAR(7),
    
    -- Pricing override
    price_adjustment        NUMERIC(10,2) DEFAULT 0,
    
    -- Status
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Statistics
    inventory_quantity      INTEGER NOT NULL DEFAULT 0,
    reserved_quantity       INTEGER NOT NULL DEFAULT 0,
    sold_count              INTEGER NOT NULL DEFAULT 0,
    
    -- Images (variant-specific)
    image_url               TEXT,
    
    -- Weight override
    weight_kg               NUMERIC(6,3),
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(product_id, size, color)
);

CREATE INDEX idx_variants_product ON public.product_variants(product_id);
CREATE INDEX idx_variants_sku ON public.product_variants(sku);
CREATE INDEX idx_variants_size ON public.product_variants(size);
CREATE INDEX idx_variants_color ON public.product_variants(color);

-- Product tags (many-to-many)
CREATE TABLE IF NOT EXISTS public.product_tags (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                    VARCHAR(50) NOT NULL UNIQUE,
    slug                    VARCHAR(50) NOT NULL UNIQUE,
    description             TEXT,
    
    usage_count             INTEGER NOT NULL DEFAULT 0,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_product_tags_name ON public.product_tags USING gin(name gin_trgm_ops);

CREATE TABLE IF NOT EXISTS public.product_tag_associations (
    product_id              UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    tag_id                  UUID NOT NULL REFERENCES public.product_tags(id) ON DELETE CASCADE,
    
    PRIMARY KEY (product_id, tag_id)
);

-- ═══════════════════════════════════════════════════════════════════
-- INVENTORY MODULE
-- ═══════════════════════════════════════════════════════════════════

-- Store locations
CREATE TABLE IF NOT EXISTS public.stores (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id                VARCHAR(64) REFERENCES public.brands(id) ON DELETE CASCADE,
    
    -- Identification
    code                    VARCHAR(20) UNIQUE,
    name                    VARCHAR(255) NOT NULL,
    
    -- Location
    address_line1           VARCHAR(255) NOT NULL,
    address_line2           VARCHAR(255),
    city                    VARCHAR(100) NOT NULL,
    state_province          VARCHAR(100),
    postal_code             VARCHAR(20) NOT NULL,
    country_code            CHAR(2) NOT NULL,
    
    -- Coordinates
    location                GEOGRAPHY(POINT, 4326),
    
    -- Contact
    phone                   VARCHAR(32),
    email                   VARCHAR(255),
    
    -- Operating hours
    hours                   JSONB NOT NULL DEFAULT '{}',
    timezone                VARCHAR(50) DEFAULT 'UTC',
    
    -- Services
    services                JSONB NOT NULL DEFAULT '[]',  -- ['BOPIS', 'stylist', 'alterations']
    
    -- Status
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    is_flagship             BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Capacity
    max_capacity            INTEGER,
    
    -- Statistics
    inventory_count         INTEGER NOT NULL DEFAULT 0,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_stores_brand ON public.stores(brand_id);
CREATE INDEX idx_stores_location ON public.stores USING GIST(location);
CREATE INDEX idx_stores_city ON public.stores(city);
CREATE INDEX idx_stores_country ON public.stores(country_code);
CREATE INDEX idx_stores_active ON public.stores(is_active) WHERE is_active = TRUE;

-- Inventory items
CREATE TABLE IF NOT EXISTS public.inventory_items (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    variant_id              UUID NOT NULL REFERENCES public.product_variants(id) ON DELETE CASCADE,
    store_id                UUID REFERENCES public.stores(id) ON DELETE CASCADE,  -- NULL = warehouse
    
    -- Stock
    quantity                INTEGER NOT NULL DEFAULT 0,
    reserved_quantity       INTEGER NOT NULL DEFAULT 0,
    available_quantity      INTEGER GENERATED ALWAYS AS (quantity - reserved_quantity) STORED,
    
    -- Status
    status                  inventory_status_enum NOT NULL DEFAULT 'in_stock',
    low_stock_threshold     INTEGER DEFAULT 5,
    
    -- Location in store
    aisle                   VARCHAR(20),
    shelf                   VARCHAR(20),
    
    -- Cost tracking
    unit_cost               NUMERIC(10,2),
    
    -- Dates
    last_restocked_at       TIMESTAMPTZ,
    last_sold_at            TIMESTAMPTZ,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_quantity_non_negative CHECK (quantity >= 0),
    CONSTRAINT chk_reserved_non_negative CHECK (reserved_quantity >= 0),
    UNIQUE(variant_id, store_id)
);

CREATE INDEX idx_inventory_variant ON public.inventory_items(variant_id);
CREATE INDEX idx_inventory_store ON public.inventory_items(store_id);
CREATE INDEX idx_inventory_status ON public.inventory_items(status);
CREATE INDEX idx_inventory_low_stock ON public.inventory_items(status) WHERE status = 'low_stock';

-- Inventory movements (audit trail)
CREATE TABLE IF NOT EXISTS public.inventory_movements (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    inventory_id            UUID NOT NULL REFERENCES public.inventory_items(id) ON DELETE CASCADE,
    
    -- Movement details
    movement_type           VARCHAR(20) NOT NULL,  -- 'restock', 'sale', 'return', 'transfer', 'adjustment', 'reservation'
    quantity_change         INTEGER NOT NULL,
    quantity_before         INTEGER NOT NULL,
    quantity_after          INTEGER NOT NULL,
    
    -- Reference
    reference_type          VARCHAR(30),  -- 'order', 'return', 'purchase_order'
    reference_id            VARCHAR(64),
    
    -- Cost
    unit_cost               NUMERIC(10,2),
    total_value             NUMERIC(12,2),
    
    -- Notes
    reason                  TEXT,
    notes                   TEXT,
    
    -- Actor
    performed_by            UUID REFERENCES public.users(id),
    performed_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Transfer details
    from_store_id           UUID REFERENCES public.stores(id),
    to_store_id             UUID REFERENCES public.stores(id)
);

CREATE INDEX idx_inventory_movements_inventory ON public.inventory_movements(inventory_id);
CREATE INDEX idx_inventory_movements_type ON public.inventory_movements(movement_type);
CREATE INDEX idx_inventory_movements_date ON public.inventory_movements(performed_at DESC);
CREATE INDEX idx_inventory_movements_reference ON public.inventory_movements(reference_type, reference_id);

-- ═══════════════════════════════════════════════════════════════════
-- WARDROBE MODULE
-- ═══════════════════════════════════════════════════════════════════

-- Wardrobe items
CREATE TABLE IF NOT EXISTS public.wardrobe_items (
    id                      VARCHAR(64) PRIMARY KEY,
    user_id                 UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Item info
    name                    VARCHAR(200) NOT NULL,
    description             TEXT,
    
    -- Source
    source_type             VARCHAR(20) NOT NULL DEFAULT 'manual',  -- 'manual', 'purchase', 'import'
    source_product_id       UUID REFERENCES public.products(id),
    source_order_id         VARCHAR(64),
    
    -- Attributes
    brand                   VARCHAR(100),
    category                VARCHAR(64) NOT NULL,
    subcategory             VARCHAR(64),
    color                   VARCHAR(50),
    color_hex               CHAR(7),
    size                    VARCHAR(20),
    material                VARCHAR(100),
    pattern                 VARCHAR(50),
    
    -- Pricing
    purchase_price          NUMERIC(10,2),
    currency                VARCHAR(3) DEFAULT 'USD',
    purchase_date           DATE,
    purchase_store          VARCHAR(255),
    
    -- Media
    image_url               TEXT,
    images                  JSONB NOT NULL DEFAULT '[]',
    
    -- Tags & Organization
    tags                    JSONB NOT NULL DEFAULT '[]',
    notes                   TEXT,
    
    -- Wear tracking
    wear_count              INTEGER NOT NULL DEFAULT 0,
    last_worn_at            TIMESTAMPTZ,
    
    -- Status
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    is_favorite             BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Seasonal
    seasons                 JSONB NOT NULL DEFAULT '[]',
    
    -- Soft delete
    deleted_at              TIMESTAMPTZ,
    
    -- Versioning
    version                 INTEGER NOT NULL DEFAULT 1,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wardrobe_items_user ON public.wardrobe_items(user_id);
CREATE INDEX idx_wardrobe_items_category ON public.wardrobe_items(category);
CREATE INDEX idx_wardrobe_items_brand ON public.wardrobe_items(brand);
CREATE INDEX idx_wardrobe_items_color ON public.wardrobe_items(color);
CREATE INDEX idx_wardrobe_items_active ON public.wardrobe_items(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_wardrobe_items_tags ON public.wardrobe_items USING gin(tags);

-- Wardrobe collections (user-created groupings)
CREATE TABLE IF NOT EXISTS public.wardrobe_collections (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    name                    VARCHAR(100) NOT NULL,
    description             TEXT,
    cover_image_url         TEXT,
    
    is_public               BOOLEAN NOT NULL DEFAULT FALSE,
    is_featured             BOOLEAN NOT NULL DEFAULT FALSE,
    
    item_count              INTEGER NOT NULL DEFAULT 0,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wardrobe_collections_user ON public.wardrobe_collections(user_id);

CREATE TABLE IF NOT EXISTS public.wardrobe_collection_items (
    collection_id           UUID NOT NULL REFERENCES public.wardrobe_collections(id) ON DELETE CASCADE,
    item_id                 VARCHAR(64) NOT NULL REFERENCES public.wardrobe_items(id) ON DELETE CASCADE,
    
    added_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    display_order           INTEGER NOT NULL DEFAULT 0,
    
    PRIMARY KEY (collection_id, item_id)
);

-- ═══════════════════════════════════════════════════════════════════
-- OUTFITS MODULE
-- ═══════════════════════════════════════════════════════════════════

-- Outfits
CREATE TABLE IF NOT EXISTS public.outfits (
    id                      VARCHAR(64) PRIMARY KEY,
    user_id                 UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Info
    title                   VARCHAR(200) NOT NULL,
    description             TEXT,
    
    -- Composition
    item_ids                JSONB NOT NULL DEFAULT '[]',
    item_details            JSONB,  -- Snapshot of items at creation
    
    -- Context
    occasion                VARCHAR(50),
    season                  VARCHAR(20),
    weather                 VARCHAR(30),
    temperature_range       VARCHAR(20),  -- 'cold', 'mild', 'warm', 'hot'
    
    -- Budget
    total_price             NUMERIC(10,2),
    currency                VARCHAR(3) DEFAULT 'USD',
    budget_limit            NUMERIC(10,2),
    
    -- AI scores
    style_score             NUMERIC(5,2),
    color_harmony_score     NUMERIC(5,2),
    occasion_fit_score      NUMERIC(5,2),
    trend_alignment_score   NUMERIC(5,2),
    
    -- Status
    is_public               BOOLEAN NOT NULL DEFAULT FALSE,
    is_featured             BOOLEAN NOT NULL DEFAULT FALSE,
    is_ai_generated         BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Sharing
    share_slug              VARCHAR(32) UNIQUE,
    share_expires_at        TIMESTAMPTZ,
    
    -- Statistics
    view_count              INTEGER NOT NULL DEFAULT 0,
    like_count              INTEGER NOT NULL DEFAULT 0,
    save_count              INTEGER NOT NULL DEFAULT 0,
    
    -- Media
    preview_image_url       TEXT,
    
    -- Soft delete
    deleted_at              TIMESTAMPTZ,
    
    -- Versioning
    version                 INTEGER NOT NULL DEFAULT 1,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_outfits_user ON public.outfits(user_id);
CREATE INDEX idx_outfits_occasion ON public.outfits(occasion);
CREATE INDEX idx_outfits_season ON public.outfits(season);
CREATE INDEX idx_outfits_public ON public.outfits(is_public) WHERE is_public = TRUE;
CREATE INDEX idx_outfits_share_slug ON public.outfits(share_slug);
CREATE INDEX idx_outfits_created ON public.outfits(created_at DESC);

-- Outfit history (worn outfits)
CREATE TABLE IF NOT EXISTS public.outfit_history (
    id                      VARCHAR(64) PRIMARY KEY,
    user_id                 UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    outfit_id               VARCHAR(64) REFERENCES public.outfits(id) ON DELETE SET NULL,
    
    -- Snapshot
    outfit_name             VARCHAR(200),
    item_ids                JSONB NOT NULL,
    item_details            JSONB,
    
    -- Context
    occasion                VARCHAR(50),
    weather                 VARCHAR(30),
    temperature_c           INTEGER,
    season                  VARCHAR(20),
    
    -- Wear info
    worn_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_favorite             BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Feedback
    user_rating             INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    feedback_notes          TEXT,
    
    -- AI insights
    ai_generated            BOOLEAN NOT NULL DEFAULT FALSE,
    style_score             NUMERIC(5,2),
    color_harmony_score     NUMERIC(5,2),
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_outfit_history_user ON public.outfit_history(user_id);
CREATE INDEX idx_outfit_history_worn_at ON public.outfit_history(worn_at DESC);
CREATE INDEX idx_outfit_history_occasion ON public.outfit_history(occasion);

-- ═══════════════════════════════════════════════════════════════════
-- ORDERS MODULE
-- ═══════════════════════════════════════════════════════════════════

-- Orders
CREATE TABLE IF NOT EXISTS public.orders (
    id                      VARCHAR(64) PRIMARY KEY,
    order_number            VARCHAR(32) NOT NULL UNIQUE,
    
    -- Customer
    user_id                 UUID REFERENCES public.users(id) ON DELETE SET NULL,
    guest_email             VARCHAR(255),
    guest_phone             VARCHAR(32),
    
    -- Status
    status                  order_status_enum NOT NULL DEFAULT 'pending',
    status_history          JSONB NOT NULL DEFAULT '[]',
    
    -- Addresses (snapshots)
    shipping_address        JSONB NOT NULL,
    billing_address         JSONB NOT NULL,
    
    -- Fulfillment
    fulfillment_type        VARCHAR(20) NOT NULL DEFAULT 'shipping',  -- 'shipping', 'bopis', 'digital'
    store_id                UUID REFERENCES public.stores(id),  -- For BOPIS
    
    -- Pricing
    subtotal                NUMERIC(12,2) NOT NULL,
    discount_amount         NUMERIC(10,2) NOT NULL DEFAULT 0,
    shipping_amount         NUMERIC(10,2) NOT NULL DEFAULT 0,
    tax_amount              NUMERIC(10,2) NOT NULL DEFAULT 0,
    total                   NUMERIC(12,2) NOT NULL,
    currency                VARCHAR(3) NOT NULL DEFAULT 'USD',
    
    -- Discounts
    coupon_code             VARCHAR(50),
    coupon_discount         NUMERIC(10,2),
    
    -- Tracking
    tracking_number         VARCHAR(128),
    tracking_url            TEXT,
    carrier                 VARCHAR(50),
    estimated_delivery      DATE,
    actual_delivery         TIMESTAMPTZ,
    
    -- Notes
    customer_notes          TEXT,
    internal_notes          TEXT,
    
    -- Dates
    placed_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmed_at            TIMESTAMPTZ,
    shipped_at              TIMESTAMPTZ,
    delivered_at            TIMESTAMPTZ,
    cancelled_at            TIMESTAMPTZ,
    
    -- Versioning
    version                 INTEGER NOT NULL DEFAULT 1,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_order_total_positive CHECK (total >= 0)
);

-- Order indexes
CREATE INDEX idx_orders_user ON public.orders(user_id);
CREATE INDEX idx_orders_number ON public.orders(order_number);
CREATE INDEX idx_orders_status ON public.orders(status);
CREATE INDEX idx_orders_placed_at ON public.orders(placed_at DESC);
CREATE INDEX idx_orders_guest_email ON public.orders(guest_email);

-- Order items
CREATE TABLE IF NOT EXISTS public.order_items (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id                VARCHAR(64) NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
    
    -- Product snapshot
    product_id              UUID REFERENCES public.products(id),
    variant_id              UUID REFERENCES public.product_variants(id),
    product_name            VARCHAR(255) NOT NULL,
    product_sku             VARCHAR(100),
    variant_info            JSONB,  -- Size, color, etc.
    
    -- Pricing
    unit_price              NUMERIC(10,2) NOT NULL,
    quantity                INTEGER NOT NULL,
    discount_amount         NUMERIC(10,2) NOT NULL DEFAULT 0,
    tax_amount              NUMERIC(10,2) NOT NULL DEFAULT 0,
    total                   NUMERIC(12,2) NOT NULL,
    
    -- Media
    image_url               TEXT,
    
    -- Fulfillment
    fulfillment_status      VARCHAR(20) NOT NULL DEFAULT 'pending',
    tracking_number         VARCHAR(128),
    
    -- Return info
    returnable              BOOLEAN NOT NULL DEFAULT TRUE,
    return_deadline         DATE,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_quantity_positive CHECK (quantity > 0)
);

CREATE INDEX idx_order_items_order ON public.order_items(order_id);
CREATE INDEX idx_order_items_product ON public.order_items(product_id);
CREATE INDEX idx_order_items_variant ON public.order_items(variant_id);

-- Returns
CREATE TABLE IF NOT EXISTS public.return_requests (
    id                      VARCHAR(64) PRIMARY KEY,
    order_id                VARCHAR(64) NOT NULL REFERENCES public.orders(id),
    user_id                 UUID NOT NULL REFERENCES public.users(id),
    
    -- Details
    reason                  VARCHAR(50) NOT NULL,  -- 'defective', 'wrong_size', 'not_as_described', 'changed_mind'
    description             TEXT,
    
    -- Items
    items                   JSONB NOT NULL,  -- [{item_id, quantity, reason}]
    
    -- Status
    status                  VARCHAR(20) NOT NULL DEFAULT 'requested',  -- 'requested', 'approved', 'processing', 'completed', 'rejected'
    
    -- Refund
    refund_amount           NUMERIC(10,2),
    refund_method           VARCHAR(20),  -- 'original', 'store_credit'
    
    -- Shipping
    return_shipping_label   TEXT,
    tracking_number         VARCHAR(128),
    
    -- Dates
    requested_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at             TIMESTAMPTZ,
    received_at             TIMESTAMPTZ,
    processed_at            TIMESTAMPTZ,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_returns_order ON public.return_requests(order_id);
CREATE INDEX idx_returns_user ON public.return_requests(user_id);
CREATE INDEX idx_returns_status ON public.return_requests(status);

-- ═══════════════════════════════════════════════════════════════════
-- PAYMENTS MODULE (PCI-DSS Compliant)
-- ═══════════════════════════════════════════════════════════════════

-- Payment methods (stored tokens only, no raw card data)
CREATE TABLE IF NOT EXISTS public.payment_methods (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Type
    type                    payment_method_enum NOT NULL,
    
    -- Tokenized data (from payment processor)
    provider                VARCHAR(20) NOT NULL,  -- 'stripe', 'paypal', 'apple_pay', etc.
    provider_token          VARCHAR(255) NOT NULL,  -- Token from provider
    provider_customer_id    VARCHAR(255),  -- Customer ID at provider
    
    -- Display info (safe to store)
    last_four               CHAR(4),
    card_brand              VARCHAR(20),  -- 'visa', 'mastercard', 'amex'
    expiry_month            INTEGER,
    expiry_year             INTEGER,
    cardholder_name         VARCHAR(255),
    
    -- For digital wallets
    wallet_type             VARCHAR(20),  -- 'apple_pay', 'google_pay'
    
    -- Status
    is_default              BOOLEAN NOT NULL DEFAULT FALSE,
    is_verified             BOOLEAN NOT NULL DEFAULT FALSE,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Billing address
    billing_address_id      UUID REFERENCES public.user_addresses(id),
    
    -- Fingerprint (for fraud detection)
    fingerprint             VARCHAR(64),
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payment_methods_user ON public.payment_methods(user_id);
CREATE INDEX idx_payment_methods_provider ON public.payment_methods(provider, provider_token);
CREATE INDEX idx_payment_methods_active ON public.payment_methods(is_active) WHERE is_active = TRUE;

-- Payments
CREATE TABLE IF NOT EXISTS public.payments (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id                VARCHAR(64) NOT NULL REFERENCES public.orders(id),
    user_id                 UUID REFERENCES public.users(id),
    
    -- Amount
    amount                  NUMERIC(12,2) NOT NULL,
    currency                VARCHAR(3) NOT NULL DEFAULT 'USD',
    
    -- Method
    payment_method_id       UUID REFERENCES public.payment_methods(id),
    payment_method_type     payment_method_enum NOT NULL,
    
    -- Provider details
    provider                VARCHAR(20) NOT NULL,
    provider_payment_id     VARCHAR(255),  -- External payment ID
    provider_customer_id    VARCHAR(255),
    
    -- Status
    status                  payment_status_enum NOT NULL DEFAULT 'pending',
    
    -- Fraud detection
    fraud_score             NUMERIC(5,2),
    fraud_check_result      VARCHAR(20),  -- 'pass', 'review', 'block'
    risk_level              VARCHAR(20),  -- 'low', 'medium', 'high'
    
    -- 3D Secure
    three_d_secure_required BOOLEAN NOT NULL DEFAULT FALSE,
    three_d_secure_version   VARCHAR(10),
    
    -- Refunds
    refund_amount           NUMERIC(12,2) DEFAULT 0,
    
    -- Metadata
    description             TEXT,
    metadata                JSONB NOT NULL DEFAULT '{}',
    
    -- Dates
    attempted_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    failed_at               TIMESTAMPTZ,
    refunded_at             TIMESTAMPTZ,
    
    -- IP and device info (for fraud detection)
    ip_address              INET,
    user_agent              TEXT,
    device_fingerprint      VARCHAR(64),
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payments_order ON public.payments(order_id);
CREATE INDEX idx_payments_user ON public.payments(user_id);
CREATE INDEX idx_payments_status ON public.payments(status);
CREATE INDEX idx_payments_provider ON public.payments(provider, provider_payment_id);
CREATE INDEX idx_payments_date ON public.payments(created_at DESC);

-- Payment events (audit trail)
CREATE TABLE IF NOT EXISTS public.payment_events (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_id              UUID NOT NULL REFERENCES public.payments(id) ON DELETE CASCADE,
    
    event_type              VARCHAR(50) NOT NULL,  -- 'created', 'authorized', 'captured', 'refunded', 'failed'
    old_status              payment_status_enum,
    new_status              payment_status_enum NOT NULL,
    
    -- Provider data
    provider_event_id       VARCHAR(255),
    provider_event_data     JSONB,
    
    -- Details
    amount                  NUMERIC(12,2),
    description             TEXT,
    error_code              VARCHAR(50),
    error_message           TEXT,
    
    -- Actor
    triggered_by            VARCHAR(20),  -- 'user', 'system', 'admin', 'provider'
    actor_id                UUID,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payment_events_payment ON public.payment_events(payment_id);
CREATE INDEX idx_payment_events_type ON public.payment_events(event_type);
CREATE INDEX idx_payment_events_date ON public.payment_events(created_at DESC);

-- ═══════════════════════════════════════════════════════════════════
-- BNPL (Buy Now Pay Later) MODULE
-- ═══════════════════════════════════════════════════════════════════

-- BNPL applications
CREATE TABLE IF NOT EXISTS public.bnpl_applications (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES public.users(id),
    order_id                VARCHAR(64) NOT NULL REFERENCES public.orders(id),
    
    -- Provider
    provider                VARCHAR(20) NOT NULL,  -- 'affirm', 'klarna', 'afterpay'
    
    -- Amount
    principal_amount        NUMERIC(12,2) NOT NULL,
    interest_amount         NUMERIC(10,2) NOT NULL DEFAULT 0,
    total_amount            NUMERIC(12,2) NOT NULL,
    currency                VARCHAR(3) NOT NULL DEFAULT 'USD',
    
    -- Terms
    term_months             INTEGER NOT NULL,
    monthly_payment         NUMERIC(10,2) NOT NULL,
    apr                     NUMERIC(5,2),
    
    -- Status
    status                  bnpl_status_enum NOT NULL DEFAULT 'pending',
    
    -- Provider data
    provider_application_id VARCHAR(255),
    provider_decision       VARCHAR(20),
    provider_data           JSONB,
    
    -- Credit check
    credit_check_consent    BOOLEAN NOT NULL DEFAULT FALSE,
    soft_credit_pull        BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Dates
    applied_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at             TIMESTAMPTZ,
    activated_at            TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_bnpl_applications_user ON public.bnpl_applications(user_id);
CREATE INDEX idx_bnpl_applications_order ON public.bnpl_applications(order_id);
CREATE INDEX idx_bnpl_applications_status ON public.bnpl_applications(status);

-- BNPL payment schedule
CREATE TABLE IF NOT EXISTS public.bnpl_payment_schedule (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id          UUID NOT NULL REFERENCES public.bnpl_applications(id) ON DELETE CASCADE,
    
    -- Installment
    installment_number      INTEGER NOT NULL,
    total_installments      INTEGER NOT NULL,
    
    -- Amount
    amount_due              NUMERIC(10,2) NOT NULL,
    amount_paid             NUMERIC(10,2) NOT NULL DEFAULT 0,
    currency                VARCHAR(3) NOT NULL DEFAULT 'USD',
    
    -- Dates
    due_date                DATE NOT NULL,
    paid_at                 TIMESTAMPTZ,
    
    -- Status
    status                  VARCHAR(20) NOT NULL DEFAULT 'scheduled',  -- 'scheduled', 'paid', 'late', 'defaulted'
    
    -- Provider
    provider_payment_id     VARCHAR(255),
    
    -- Late fees
    late_fee                NUMERIC(10,2) DEFAULT 0,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(application_id, installment_number)
);

CREATE INDEX idx_bnpl_schedule_application ON public.bnpl_payment_schedule(application_id);
CREATE INDEX idx_bnpl_schedule_due ON public.bnpl_payment_schedule(due_date);

-- ═══════════════════════════════════════════════════════════════════
-- TRY-ON ASSETS MODULE
-- ═══════════════════════════════════════════════════════════════════

-- Digital twins
CREATE TABLE IF NOT EXISTS public.digital_twins (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Reference images
    reference_images        JSONB NOT NULL DEFAULT '[]',
    twin_image_url          TEXT,
    
    -- Body model
    body_model_url          TEXT,
    body_model_id           VARCHAR(128),
    
    -- Attributes
    skin_undertone          VARCHAR(20) CHECK (skin_undertone IN ('warm', 'cool', 'neutral')),
    environment             VARCHAR(50) DEFAULT 'studio',
    
    -- Status
    status                  tryon_status_enum NOT NULL DEFAULT 'pending',
    error_message           TEXT,
    
    -- Quality metrics
    quality_score           NUMERIC(5,2),
    realism_score           NUMERIC(5,2),
    
    -- Meta
    meta                    JSONB NOT NULL DEFAULT '{}',
    
    -- Versioning
    version                 INTEGER NOT NULL DEFAULT 1,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_digital_twins_user ON public.digital_twins(user_id);
CREATE INDEX idx_digital_twins_status ON public.digital_twins(status);

-- Try-on sessions
CREATE TABLE IF NOT EXISTS public.tryon_sessions (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID REFERENCES public.users(id) ON DELETE SET NULL,
    twin_id                 UUID REFERENCES public.digital_twins(id),
    
    -- Input
    user_image_hash         VARCHAR(64) NOT NULL,  -- SHA-256 for privacy
    garment_image_url       TEXT NOT NULL,
    garment_product_id      UUID REFERENCES public.products(id),
    garment_name            VARCHAR(255) NOT NULL,
    garment_category        VARCHAR(50) NOT NULL DEFAULT 'tops',
    
    -- Options
    fit_type                VARCHAR(20) NOT NULL DEFAULT 'regular',
    environment             VARCHAR(50) DEFAULT 'studio',
    
    -- Output
    result_image_url        TEXT,
    result_image_hash       VARCHAR(64),
    
    -- Quality metrics
    quality_score           NUMERIC(5,2) NOT NULL DEFAULT 0.0,
    realism_score           NUMERIC(5,2),
    edge_quality            NUMERIC(5,2),
    color_consistency       NUMERIC(5,2),
    proportion_score        NUMERIC(5,2),
    artifact_score          NUMERIC(5,2),
    
    -- Processing
    pose_detected           BOOLEAN NOT NULL DEFAULT FALSE,
    processing_mode         VARCHAR(30) NOT NULL DEFAULT 'advanced',
    processing_time_ms      INTEGER NOT NULL DEFAULT 0,
    
    -- Status
    status                  tryon_status_enum NOT NULL DEFAULT 'pending',
    error_message           TEXT,
    warnings                JSONB NOT NULL DEFAULT '[]',
    
    -- Expiration
    expires_at              TIMESTAMPTZ,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tryon_sessions_user ON public.tryon_sessions(user_id);
CREATE INDEX idx_tryon_sessions_product ON public.tryon_sessions(garment_product_id);
CREATE INDEX idx_tryon_sessions_status ON public.tryon_sessions(status);
CREATE INDEX idx_tryon_sessions_created ON public.tryon_sessions(created_at DESC);

-- Try-on results (persisted)
CREATE TABLE IF NOT EXISTS public.tryon_results (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id              UUID NOT NULL REFERENCES public.tryon_sessions(id) ON DELETE CASCADE,
    user_id                 UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Result
    result_image_url        TEXT NOT NULL,
    thumbnail_url           TEXT,
    
    -- Product
    product_id              UUID REFERENCES public.products(id),
    
    -- Engagement
    view_count              INTEGER NOT NULL DEFAULT 0,
    share_count             INTEGER NOT NULL DEFAULT 0,
    purchase_count          INTEGER NOT NULL DEFAULT 0,
    
    -- Status
    is_saved                BOOLEAN NOT NULL DEFAULT FALSE,
    is_public               BOOLEAN NOT NULL DEFAULT FALSE,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at              TIMESTAMPTZ
);

CREATE INDEX idx_tryon_results_user ON public.tryon_results(user_id);
CREATE INDEX idx_tryon_results_session ON public.tryon_results(session_id);

-- ═══════════════════════════════════════════════════════════════════
-- VISUAL SEARCH MODULE
-- ═══════════════════════════════════════════════════════════════════

-- Visual search sessions
CREATE TABLE IF NOT EXISTS public.visual_search_sessions (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID REFERENCES public.users(id) ON DELETE SET NULL,
    
    -- Input
    input_image_url         TEXT NOT NULL,
    input_image_hash        VARCHAR(64),
    
    -- Processing
    feature_vector          VECTOR(512),  -- Embedding vector (requires pgvector)
    detected_categories     JSONB NOT NULL DEFAULT '[]',
    detected_colors         JSONB NOT NULL DEFAULT '[]',
    detected_patterns       JSONB NOT NULL DEFAULT '[]',
    detected_styles         JSONB NOT NULL DEFAULT '[]',
    
    -- Status
    status                  visual_search_status_enum NOT NULL DEFAULT 'pending',
    error_message           TEXT,
    
    -- Processing metrics
    processing_time_ms      INTEGER NOT NULL DEFAULT 0,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_visual_search_user ON public.visual_search_sessions(user_id);
CREATE INDEX idx_visual_search_status ON public.visual_search_sessions(status);
CREATE INDEX idx_visual_search_created ON public.visual_search_sessions(created_at DESC);

-- Visual search results
CREATE TABLE IF NOT EXISTS public.visual_search_results (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id              UUID NOT NULL REFERENCES public.visual_search_sessions(id) ON DELETE CASCADE,
    
    -- Result
    product_id              UUID NOT NULL REFERENCES public.products(id),
    
    -- Matching
    similarity_score        NUMERIC(5,4) NOT NULL,
    match_type              VARCHAR(30) NOT NULL,  -- 'exact', 'similar', 'complementary'
    matched_attributes      JSONB NOT NULL DEFAULT '[]',
    
    -- Ranking
    rank_position           INTEGER NOT NULL,
    
    -- Engagement
    clicked                 BOOLEAN NOT NULL DEFAULT FALSE,
    clicked_at              TIMESTAMPTZ,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_visual_search_results_session ON public.visual_search_results(session_id);
CREATE INDEX idx_visual_search_results_product ON public.visual_search_results(product_id);
CREATE INDEX idx_visual_search_results_similarity ON public.visual_search_results(similarity_score DESC);

-- ═══════════════════════════════════════════════════════════════════
-- ANALYTICS MODULE
-- ═══════════════════════════════════════════════════════════════════

-- User events (partitioned)
CREATE TABLE IF NOT EXISTS public.user_events (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID REFERENCES public.users(id) ON DELETE SET NULL,
    session_id              UUID,
    
    -- Event
    event_type              event_type_enum NOT NULL,
    event_name              VARCHAR(100),
    
    -- Context
    entity_type             VARCHAR(30),  -- 'product', 'outfit', 'brand', 'order'
    entity_id               VARCHAR(100),
    
    -- Data
    event_data              JSONB NOT NULL DEFAULT '{}',
    
    -- Device/Session
    device_type             VARCHAR(20),
    platform                VARCHAR(20),
    app_version             VARCHAR(20),
    
    -- Location
    ip_address              INET,
    country_code            CHAR(2),
    city                    VARCHAR(100),
    
    -- Referrer
    referrer                TEXT,
    utm_source              VARCHAR(100),
    utm_medium              VARCHAR(100),
    utm_campaign            VARCHAR(100),
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Create monthly partitions for user_events
CREATE TABLE public.user_events_2026_03 PARTITION OF public.user_events
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE public.user_events_2026_04 PARTITION OF public.user_events
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE public.user_events_2026_05 PARTITION OF public.user_events
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE public.user_events_default PARTITION OF public.user_events DEFAULT;

-- Event indexes
CREATE INDEX idx_user_events_type ON public.user_events(event_type);
CREATE INDEX idx_user_events_user ON public.user_events(user_id);
CREATE INDEX idx_user_events_entity ON public.user_events(entity_type, entity_id);
CREATE INDEX idx_user_events_created ON public.user_events(created_at DESC);

-- Brand analytics (aggregated)
CREATE TABLE IF NOT EXISTS public.brand_analytics (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id                VARCHAR(64) NOT NULL REFERENCES public.brands(id) ON DELETE CASCADE,
    
    -- Period
    period_type             VARCHAR(10) NOT NULL,  -- 'daily', 'weekly', 'monthly'
    period_start            DATE NOT NULL,
    period_end              DATE NOT NULL,
    
    -- Metrics
    view_count              INTEGER NOT NULL DEFAULT 0,
    unique_visitors         INTEGER NOT NULL DEFAULT 0,
    add_to_cart_count       INTEGER NOT NULL DEFAULT 0,
    purchase_count          INTEGER NOT NULL DEFAULT 0,
    purchase_revenue        NUMERIC(14,2) NOT NULL DEFAULT 0,
    
    -- Engagement
    follower_gain           INTEGER NOT NULL DEFAULT 0,
    follower_loss           INTEGER NOT NULL DEFAULT 0,
    
    -- Conversion
    conversion_rate         NUMERIC(5,2),
    avg_order_value         NUMERIC(10,2),
    
    -- Products
    top_products            JSONB NOT NULL DEFAULT '[]',
    top_categories          JSONB NOT NULL DEFAULT '[]',
    
    -- Demographics
    top_countries           JSONB NOT NULL DEFAULT '[]',
    top_age_groups          JSONB NOT NULL DEFAULT '[]',
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(brand_id, period_type, period_start)
);

CREATE INDEX idx_brand_analytics_brand ON public.brand_analytics(brand_id);
CREATE INDEX idx_brand_analytics_period ON public.brand_analytics(period_type, period_start);

-- Product analytics (aggregated)
CREATE TABLE IF NOT EXISTS public.product_analytics (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id              UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    
    -- Period
    period_type             VARCHAR(10) NOT NULL,
    period_start            DATE NOT NULL,
    period_end              DATE NOT NULL,
    
    -- Metrics
    view_count              INTEGER NOT NULL DEFAULT 0,
    unique_viewers          INTEGER NOT NULL DEFAULT 0,
    add_to_cart_count       INTEGER NOT NULL DEFAULT 0,
    wishlist_add_count      INTEGER NOT NULL DEFAULT 0,
    purchase_count          INTEGER NOT NULL DEFAULT 0,
    purchase_revenue        NUMERIC(14,2) NOT NULL DEFAULT 0,
    
    -- Engagement
    try_on_count            INTEGER NOT NULL DEFAULT 0,
    share_count             INTEGER NOT NULL DEFAULT 0,
    
    -- Conversion
    conversion_rate         NUMERIC(5,2),
    return_rate             NUMERIC(5,2),
    
    -- Search
    search_impressions      INTEGER NOT NULL DEFAULT 0,
    search_clicks           INTEGER NOT NULL DEFAULT 0,
    search_ctr              NUMERIC(5,2),
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(product_id, period_type, period_start)
);

CREATE INDEX idx_product_analytics_product ON public.product_analytics(product_id);
CREATE INDEX idx_product_analytics_period ON public.product_analytics(period_type, period_start);

-- ═══════════════════════════════════════════════════════════════════
-- RECOMMENDATIONS MODULE
-- ═══════════════════════════════════════════════════════════════════

-- Recommendation history
CREATE TABLE IF NOT EXISTS public.recommendation_history (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    
    -- Recommendation
    recommendation_type     recommendation_type_enum NOT NULL,
    entity_type             VARCHAR(30) NOT NULL,  -- 'product', 'outfit', 'brand'
    entity_ids              JSONB NOT NULL DEFAULT '[]',
    
    -- Scores
    scores                  JSONB NOT NULL DEFAULT '{}',
    confidence              NUMERIC(5,2) NOT NULL DEFAULT 0.0,
    
    -- Context
    context_snapshot        JSONB NOT NULL DEFAULT '{}',
    occasion                VARCHAR(50),
    budget                  NUMERIC(10,2),
    
    -- Explanation
    explanation             TEXT,
    
    -- Feedback
    user_feedback           VARCHAR(20),  -- 'liked', 'disliked', 'purchased', 'dismissed'
    feedback_reason         TEXT,
    feedback_at             TIMESTAMPTZ,
    
    -- Session
    session_id              UUID,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_recommendation_history_user ON public.recommendation_history(user_id, created_at DESC);
CREATE INDEX idx_recommendation_history_type ON public.recommendation_history(recommendation_type);
CREATE INDEX idx_recommendation_history_feedback ON public.recommendation_history(user_feedback);

-- Recommendation embeddings (for ML)
CREATE TABLE IF NOT EXISTS public.product_embeddings (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id              UUID NOT NULL UNIQUE REFERENCES public.products(id) ON DELETE CASCADE,
    
    -- Embeddings
    visual_embedding        VECTOR(512),
    style_embedding         VECTOR(128),
    text_embedding          VECTOR(768),
    
    -- Metadata
    model_version           VARCHAR(50),
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_product_embeddings_product ON public.product_embeddings(product_id);
-- Vector similarity index (requires pgvector)
-- CREATE INDEX idx_product_embeddings_visual ON public.product_embeddings USING ivfflat (visual_embedding vector_cosine_ops);

-- ═══════════════════════════════════════════════════════════════════
-- AUDIT & VERSIONING MODULE
-- ═══════════════════════════════════════════════════════════════════

-- Audit log (partitioned)
CREATE TABLE IF NOT EXISTS public.audit_log (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Actor
    actor_type              VARCHAR(20) NOT NULL,  -- 'user', 'system', 'admin', 'api'
    actor_id                VARCHAR(100),
    
    -- Action
    action                  VARCHAR(50) NOT NULL,
    
    -- Target
    table_name              VARCHAR(50) NOT NULL,
    record_id               VARCHAR(100) NOT NULL,
    
    -- Changes
    old_values              JSONB,
    new_values              JSONB,
    changed_fields          JSONB NOT NULL DEFAULT '[]',
    
    -- Context
    ip_address              INET,
    user_agent              TEXT,
    request_id              UUID,
    
    -- Metadata
    metadata                JSONB NOT NULL DEFAULT '{}',
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Create monthly partitions for audit_log
CREATE TABLE public.audit_log_2026_03 PARTITION OF public.audit_log
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE public.audit_log_2026_04 PARTITION OF public.audit_log
    FOR VALUES FROM ('2026-04-01') TO ('2025-05-01');
CREATE TABLE public.audit_log_default PARTITION OF public.audit_log DEFAULT;

-- Audit indexes
CREATE INDEX idx_audit_log_actor ON public.audit_log(actor_type, actor_id);
CREATE INDEX idx_audit_log_table ON public.audit_log(table_name, record_id);
CREATE INDEX idx_audit_log_action ON public.audit_log(action);
CREATE INDEX idx_audit_log_created ON public.audit_log(created_at DESC);

-- Entity versions (for versioning/undo)
CREATE TABLE IF NOT EXISTS public.entity_versions (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Entity
    entity_type             VARCHAR(50) NOT NULL,
    entity_id               VARCHAR(100) NOT NULL,
    version                 INTEGER NOT NULL,
    
    -- Snapshot
    snapshot                JSONB NOT NULL,
    
    -- Actor
    created_by              UUID REFERENCES public.users(id),
    
    -- Change info
    change_reason           TEXT,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(entity_type, entity_id, version)
);

CREATE INDEX idx_entity_versions_entity ON public.entity_versions(entity_type, entity_id);
CREATE INDEX idx_entity_versions_version ON public.entity_versions(entity_type, entity_id, version DESC);

-- ═══════════════════════════════════════════════════════════════════
-- TRIGGERS
-- ═══════════════════════════════════════════════════════════════════

-- Users trigger
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- User addresses trigger
CREATE TRIGGER trg_user_addresses_updated_at
    BEFORE UPDATE ON public.user_addresses
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Style profiles trigger
CREATE TRIGGER trg_style_profiles_updated_at
    BEFORE UPDATE ON public.user_style_profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Body profiles trigger
CREATE TRIGGER trg_body_profiles_updated_at
    BEFORE UPDATE ON public.user_body_profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Brands trigger
CREATE TRIGGER trg_brands_updated_at
    BEFORE UPDATE ON public.brands
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Products trigger
CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON public.products
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Product variants trigger
CREATE TRIGGER trg_product_variants_updated_at
    BEFORE UPDATE ON public.product_variants
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Stores trigger
CREATE TRIGGER trg_stores_updated_at
    BEFORE UPDATE ON public.stores
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Inventory trigger
CREATE TRIGGER trg_inventory_updated_at
    BEFORE UPDATE ON public.inventory_items
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Wardrobe items trigger
CREATE TRIGGER trg_wardrobe_items_updated_at
    BEFORE UPDATE ON public.wardrobe_items
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Outfits trigger
CREATE TRIGGER trg_outfits_updated_at
    BEFORE UPDATE ON public.outfits
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Orders trigger
CREATE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON public.orders
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Payments trigger
CREATE TRIGGER trg_payments_updated_at
    BEFORE UPDATE ON public.payments
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Digital twins trigger
CREATE TRIGGER trg_digital_twins_updated_at
    BEFORE UPDATE ON public.digital_twins
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ═══════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY (RLS)
-- ═══════════════════════════════════════════════════════════════════

-- Enable RLS on all user-owned tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_addresses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_style_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_body_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_budget_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_brand_affinities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_contextual_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wardrobe_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wardrobe_collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outfits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outfit_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.digital_twins ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tryon_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tryon_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.visual_search_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payment_methods ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.return_requests ENABLE ROW LEVEL SECURITY;

-- User policies
CREATE POLICY "Users can read own data" ON public.users FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own data" ON public.users FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can manage own sessions" ON public.user_sessions FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own addresses" ON public.user_addresses FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own style profile" ON public.user_style_profiles FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own body profile" ON public.user_body_profiles FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own budget profile" ON public.user_budget_profiles FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own brand affinities" ON public.user_brand_affinities FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own contextual prefs" ON public.user_contextual_preferences FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own wardrobe" ON public.wardrobe_items FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own collections" ON public.wardrobe_collections FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own outfits" ON public.outfits FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own outfit history" ON public.outfit_history FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own digital twins" ON public.digital_twins FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own tryon sessions" ON public.tryon_sessions FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own tryon results" ON public.tryon_results FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own visual search" ON public.visual_search_sessions FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own payment methods" ON public.payment_methods FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can read own orders" ON public.orders FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create orders" ON public.orders FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can manage own returns" ON public.return_requests FOR ALL USING (auth.uid() = user_id);

-- Public read policies
CREATE POLICY "Anyone can read active brands" ON public.brands FOR SELECT USING (is_active = TRUE);
CREATE POLICY "Anyone can read active products" ON public.products FOR SELECT USING (is_active = TRUE);
CREATE POLICY "Anyone can read active stores" ON public.stores FOR SELECT USING (is_active = TRUE);
CREATE POLICY "Anyone can read categories" ON public.product_categories FOR SELECT USING (is_active = TRUE);
CREATE POLICY "Anyone can read public outfits" ON public.outfits FOR SELECT USING (is_public = TRUE);

-- ═══════════════════════════════════════════════════════════════════
-- VIEWS FOR COMMON QUERIES
-- ═══════════════════════════════════════════════════════════════════

-- Active products with inventory
CREATE OR REPLACE VIEW public.active_products_with_inventory AS
SELECT 
    p.*,
    COALESCE(SUM(iv.quantity - iv.reserved_quantity), 0) AS total_available,
    COALESCE(MIN(iv.quantity - iv.reserved_quantity), 0) AS min_available
FROM public.products p
LEFT JOIN public.product_variants pv ON p.id = pv.product_id
LEFT JOIN public.inventory_items iv ON pv.id = iv.variant_id
WHERE p.is_active = TRUE AND p.deleted_at IS NULL
GROUP BY p.id;

-- User order summary
CREATE OR REPLACE VIEW public.user_order_summary AS
SELECT 
    u.id AS user_id,
    COUNT(o.id) AS total_orders,
    SUM(CASE WHEN o.status = 'completed' THEN 1 ELSE 0 END) AS completed_orders,
    SUM(o.total) AS total_spent,
    AVG(o.total) AS avg_order_value,
    MAX(o.placed_at) AS last_order_at
FROM public.users u
LEFT JOIN public.orders o ON u.id = o.user_id
GROUP BY u.id;

-- Product performance
CREATE OR REPLACE VIEW public.product_performance AS
SELECT 
    p.id,
    p.name,
    p.brand_id,
    p.category_id,
    p.base_price,
    p.sale_price,
    p.view_count,
    p.purchase_count,
    p.wishlist_count,
    p.rating_average,
    p.review_count,
    CASE 
        WHEN p.view_count > 0 THEN ROUND((p.purchase_count::NUMERIC / p.view_count) * 100, 2)
        ELSE 0 
    END AS conversion_rate,
    COALESCE(SUM(iv.quantity - iv.reserved_quantity), 0) AS available_inventory
FROM public.products p
LEFT JOIN public.product_variants pv ON p.id = pv.product_id
LEFT JOIN public.inventory_items iv ON pv.id = iv.variant_id
WHERE p.is_active = TRUE AND p.deleted_at IS NULL
GROUP BY p.id;

-- ═══════════════════════════════════════════════════════════════════
-- FUNCTIONS FOR BUSINESS LOGIC
-- ═══════════════════════════════════════════════════════════════════

-- Update inventory on order
CREATE OR REPLACE FUNCTION update_inventory_on_order()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Reserve inventory for new order items
        UPDATE public.inventory_items iv
        SET reserved_quantity = reserved_quantity + NEW.quantity
        FROM public.product_variants pv
        WHERE pv.id = NEW.variant_id 
          AND iv.variant_id = pv.id
          AND iv.store_id IS NULL;  -- Warehouse inventory
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        -- Release reserved inventory
        UPDATE public.inventory_items iv
        SET reserved_quantity = GREATEST(0, reserved_quantity - OLD.quantity)
        FROM public.product_variants pv
        WHERE pv.id = OLD.variant_id 
          AND iv.variant_id = pv.id
          AND iv.store_id IS NULL;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create audit entry on change
CREATE OR REPLACE FUNCTION create_audit_entry()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.audit_log (
        actor_type, actor_id, action, table_name, record_id,
        old_values, new_values, changed_fields
    ) VALUES (
        'system', NULL, TG_OP, TG_TABLE_NAME, 
        COALESCE(NEW.id::TEXT, OLD.id::TEXT),
        CASE WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD) 
             WHEN TG_OP = 'UPDATE' THEN to_jsonb(OLD) END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) END,
        CASE WHEN TG_OP = 'UPDATE' THEN 
            (SELECT jsonb_agg(key) FROM jsonb_each(to_jsonb(NEW)) WHERE key NOT IN ('updated_at', 'version') AND to_jsonb(OLD)->key IS DISTINCT FROM value)
        END
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Increment version on update
CREATE OR REPLACE FUNCTION increment_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ═══════════════════════════════════════════════════════════════════
-- COMMENTS FOR DOCUMENTATION
-- ═══════════════════════════════════════════════════════════════════

COMMENT ON TABLE public.users IS 'Core user accounts with profile data and settings';
COMMENT ON TABLE public.user_style_profiles IS 'Multi-dimensional style preferences and archetype classification';
COMMENT ON TABLE public.user_body_profiles IS 'Body measurements and size preferences for fit recommendations';
COMMENT ON TABLE public.brands IS 'Brand entities with business information and statistics';
COMMENT ON TABLE public.products IS 'Product catalog with attributes, pricing, and performance metrics';
COMMENT ON TABLE public.inventory_items IS 'Real-time inventory tracking with location and reservation support';
COMMENT ON TABLE public.orders IS 'Order management with status tracking and fulfillment details';
COMMENT ON TABLE public.payments IS 'Payment transactions with PCI-DSS compliant tokenization';
COMMENT ON TABLE public.bnpl_applications IS 'Buy Now Pay Later financing applications and terms';
COMMENT ON TABLE public.digital_twins IS 'AI-generated body models for virtual try-on';
COMMENT ON TABLE public.tryon_sessions IS 'Virtual try-on processing sessions with quality metrics';
COMMENT ON TABLE public.visual_search_sessions IS 'Image-based product search with feature extraction';
COMMENT ON TABLE public.user_events IS 'User behavior analytics (partitioned by month)';
COMMENT ON TABLE public.audit_log IS 'System-wide audit trail (partitioned by month)';
COMMENT ON TABLE public.recommendation_history IS 'AI recommendation tracking with feedback loop';

-- ============================================================
-- END OF SCHEMA
-- ============================================================
