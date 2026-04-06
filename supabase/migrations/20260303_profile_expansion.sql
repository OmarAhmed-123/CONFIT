-- ============================================================
-- CONFIT — Group 1 Profile Expansion Migration
-- Created: 2026-03-03
-- Description: Multi-dimensional user identity system
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Style Profiles ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_style_profiles (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Archetype
    primary_archetype       VARCHAR(50),
    secondary_archetypes    JSONB DEFAULT '[]',
    archetype_confidence    DECIMAL(3,2) DEFAULT 0.0,
    
    -- Style Vector (8 dimensions, 0.0-1.0)
    style_classic           DECIMAL(3,2) DEFAULT 0.5,
    style_trendy            DECIMAL(3,2) DEFAULT 0.5,
    style_minimalist        DECIMAL(3,2) DEFAULT 0.5,
    style_maximalist        DECIMAL(3,2) DEFAULT 0.5,
    style_feminine          DECIMAL(3,2) DEFAULT 0.5,
    style_masculine         DECIMAL(3,2) DEFAULT 0.5,
    style_edgy              DECIMAL(3,2) DEFAULT 0.5,
    style_romantic          DECIMAL(3,2) DEFAULT 0.5,
    
    -- Color Affinity
    skin_undertone          VARCHAR(20),
    preferred_colors        JSONB DEFAULT '[]',
    avoided_colors          JSONB DEFAULT '[]',
    color_confidence        DECIMAL(3,2) DEFAULT 0.0,
    
    -- Pattern & Fabric
    pattern_preferences     JSONB DEFAULT '{}',
    fabric_preferences      JSONB DEFAULT '[]',
    
    -- Silhouette
    silhouette_preferences  JSONB DEFAULT '{}',
    fit_preference          VARCHAR(30) DEFAULT 'regular',
    
    -- Status
    profile_completeness    DECIMAL(5,2) DEFAULT 0.0,
    onboarding_completed    BOOLEAN DEFAULT FALSE,
    onboarding_phase        INTEGER DEFAULT 0,
    profile_version         INTEGER DEFAULT 1,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_style_profiles_user ON user_style_profiles(user_id);
CREATE INDEX idx_style_profiles_archetype ON user_style_profiles(primary_archetype);
CREATE INDEX idx_style_profiles_completeness ON user_style_profiles(profile_completeness);

ALTER TABLE user_style_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own style profile" ON user_style_profiles FOR ALL USING (auth.uid() = user_id);

-- ── Body Profiles ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_body_profiles (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    
    profile_status          VARCHAR(20) DEFAULT 'not_set',
    
    -- Measurements (cm)
    height_cm               INTEGER,
    weight_kg               INTEGER,
    chest_cm                INTEGER,
    waist_cm                INTEGER,
    hips_cm                 INTEGER,
    inseam_cm               INTEGER,
    
    -- Classification
    body_shape              VARCHAR(50),
    
    -- Sizes
    size_tops               VARCHAR(10),
    size_bottoms            VARCHAR(10),
    size_dresses            VARCHAR(10),
    size_shoes              VARCHAR(10),
    brand_size_overrides    JSONB DEFAULT '{}',
    
    -- Fit Issues
    fit_issues              JSONB DEFAULT '[]',
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_body_profiles_user ON user_body_profiles(user_id);

ALTER TABLE user_body_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own body profile" ON user_body_profiles FOR ALL USING (auth.uid() = user_id);

-- ── Budget Profiles ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_budget_profiles (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    
    per_item_min            DECIMAL(10,2),
    per_item_max            DECIMAL(10,2),
    monthly_max             DECIMAL(10,2),
    currency                VARCHAR(3) DEFAULT 'USD',
    investment_willing      BOOLEAN DEFAULT FALSE,
    price_sensitivity       DECIMAL(3,2) DEFAULT 0.5,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE user_budget_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own budget profile" ON user_budget_profiles FOR ALL USING (auth.uid() = user_id);

-- ── Brand Affinities ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_brand_affinities (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    brand_id                VARCHAR(64) NOT NULL,
    
    affinity_score          DECIMAL(3,2) DEFAULT 0.5,
    affinity_source         VARCHAR(30) DEFAULT 'explicit',
    reason                  TEXT,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, brand_id)
);

CREATE INDEX idx_brand_affinities_user ON user_brand_affinities(user_id);
CREATE INDEX idx_brand_affinities_brand ON user_brand_affinities(brand_id);

ALTER TABLE user_brand_affinities ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own brand affinities" ON user_brand_affinities FOR ALL USING (auth.uid() = user_id);

-- ── Contextual Preferences ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_contextual_preferences (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Occasion Weights
    occasion_weights        JSONB DEFAULT '{}',
    
    -- Lifestyle
    work_environment        VARCHAR(30),
    climate_zone            VARCHAR(30),
    activity_level          VARCHAR(20),
    has_children            BOOLEAN,
    pet_friendly            BOOLEAN,
    
    -- Weather Preferences
    weather_preferences     JSONB DEFAULT '{}',
    
    -- Cultural
    cultural_influences     JSONB DEFAULT '[]',
    modesty_preference      VARCHAR(20),
    
    -- Social
    style_icons             JSONB DEFAULT '[]',
    social_influences       JSONB DEFAULT '[]',
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE user_contextual_preferences ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own contextual preferences" ON user_contextual_preferences FOR ALL USING (auth.uid() = user_id);

-- ── Confidence Profiles ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_confidence_profiles (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    
    overall_confidence      DECIMAL(5,2) DEFAULT 0.0,
    
    -- Dimensions (0-100)
    fit_confidence          DECIMAL(5,2) DEFAULT 0.0,
    style_alignment         DECIMAL(5,2) DEFAULT 0.0,
    budget_comfort          DECIMAL(5,2) DEFAULT 0.0,
    experimentation_level   DECIMAL(5,2) DEFAULT 0.0,
    wardrobe_compatibility  DECIMAL(5,2) DEFAULT 0.0,
    occasion_readiness      DECIMAL(5,2) DEFAULT 0.0,
    consistency_score       DECIMAL(5,2) DEFAULT 0.0,
    engagement_score        DECIMAL(5,2) DEFAULT 0.0,
    
    -- Badges & Growth
    earned_badges           JSONB DEFAULT '[]',
    growth_rate             DECIMAL(5,4) DEFAULT 0.0,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_confidence_profiles_score ON user_confidence_profiles(overall_confidence DESC);

ALTER TABLE user_confidence_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own confidence profile" ON user_confidence_profiles FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "System updates confidence profile" ON user_confidence_profiles FOR UPDATE USING (auth.uid() = user_id);

-- ── Confidence History ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_confidence_history (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    overall_score           DECIMAL(5,2) NOT NULL,
    dimensions              JSONB NOT NULL,
    delta                   DECIMAL(5,2),
    trigger_event           VARCHAR(50),
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_confidence_history_user ON user_confidence_history(user_id, created_at DESC);

-- ── Behavior Signals ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_behavior_signals (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    signal_type             VARCHAR(30) NOT NULL,
    entity_type             VARCHAR(30) NOT NULL,
    entity_id               VARCHAR(100) NOT NULL,
    
    weight                  DECIMAL(4,3) NOT NULL,
    context                 JSONB DEFAULT '{}',
    duration_ms             INTEGER,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at              TIMESTAMPTZ
);

CREATE INDEX idx_behavior_signals_user ON user_behavior_signals(user_id, created_at DESC);
CREATE INDEX idx_behavior_signals_entity ON user_behavior_signals(entity_type, entity_id);
CREATE INDEX idx_behavior_signals_type ON user_behavior_signals(signal_type);
CREATE INDEX idx_behavior_signals_expires ON user_behavior_signals(expires_at) WHERE expires_at IS NOT NULL;

-- ── Style Evolution ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_style_evolution (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    event_type              VARCHAR(50) NOT NULL,
    previous_value          JSONB,
    new_value               JSONB NOT NULL,
    trigger_source          VARCHAR(30) NOT NULL,
    confidence_delta        DECIMAL(5,2),
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_style_evolution_user ON user_style_evolution(user_id, created_at DESC);

-- ── Consent History ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_consent_history (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    consent_type            VARCHAR(50) NOT NULL,
    granted                 BOOLEAN NOT NULL,
    consent_version         INTEGER NOT NULL DEFAULT 1,
    
    ip_address              INET,
    user_agent              TEXT,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_consent_history_user ON user_consent_history(user_id, created_at DESC);

-- ── Profile Audit Log ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_profile_audit_log (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    table_name              VARCHAR(50) NOT NULL,
    field_name              VARCHAR(100) NOT NULL,
    old_value               JSONB,
    new_value               JSONB NOT NULL,
    change_source           VARCHAR(30) NOT NULL,
    
    ip_address              INET,
    user_agent              TEXT,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_profile_audit_user ON user_profile_audit_log(user_id, created_at DESC);

-- ── Onboarding Sessions ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_onboarding_sessions (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    
    current_phase           INTEGER DEFAULT 1,
    phase_data              JSONB DEFAULT '{}',
    quiz_answers            JSONB DEFAULT '{}',
    skipped_phases          JSONB DEFAULT '[]',
    
    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    last_activity_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_onboarding_sessions_user ON user_onboarding_sessions(user_id);

ALTER TABLE user_onboarding_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own onboarding" ON user_onboarding_sessions FOR ALL USING (auth.uid() = user_id);

-- ── Data Export Requests ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_data_export_requests (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    status                  VARCHAR(20) DEFAULT 'pending',
    format                  VARCHAR(10) DEFAULT 'json',
    
    requested_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    expires_at              TIMESTAMPTZ,
    download_url            TEXT,
    
    error_message           TEXT
);

CREATE INDEX idx_data_export_requests_user ON user_data_export_requests(user_id);

-- ── Deletion Requests ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_deletion_requests (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    status                  VARCHAR(20) DEFAULT 'pending',
    reason                  TEXT,
    confirmation_code       VARCHAR(64),
    
    requested_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scheduled_for           TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '30 days'),
    executed_at             TIMESTAMPTZ
);

CREATE INDEX idx_deletion_requests_user ON user_deletion_requests(user_id);

-- ── Triggers ─────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_style_profiles_updated_at
    BEFORE UPDATE ON user_style_profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_body_profiles_updated_at
    BEFORE UPDATE ON user_body_profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_budget_profiles_updated_at
    BEFORE UPDATE ON user_budget_profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_brand_affinities_updated_at
    BEFORE UPDATE ON user_brand_affinities
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_contextual_preferences_updated_at
    BEFORE UPDATE ON user_contextual_preferences
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_confidence_profiles_updated_at
    BEFORE UPDATE ON user_confidence_profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── Seed Style Archetypes ───────────────────────────────────────────
INSERT INTO user_style_profiles (user_id, primary_archetype, archetype_confidence, profile_completeness)
SELECT id, NULL, 0.0, 0.0 FROM auth.users
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO user_body_profiles (user_id)
SELECT id FROM auth.users
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO user_budget_profiles (user_id)
SELECT id FROM auth.users
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO user_contextual_preferences (user_id)
SELECT id FROM auth.users
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO user_confidence_profiles (user_id)
SELECT id FROM auth.users
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO user_onboarding_sessions (user_id)
SELECT id FROM auth.users
ON CONFLICT (user_id) DO NOTHING;
