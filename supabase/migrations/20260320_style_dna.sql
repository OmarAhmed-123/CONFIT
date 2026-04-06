-- ============================================================
-- CONFIT — Style DNA Feature
-- Created: 2026-03-20
-- Description: Unique style fingerprint system using pgvector
-- Version: 1.0.0
-- ============================================================

-- Enable pgvector extension for embedding-based similarity
CREATE EXTENSION IF NOT EXISTS "vector";

-- ═══════════════════════════════════════════════════════════════════
-- ENUMERATED TYPES
-- ═══════════════════════════════════════════════════════════════════

-- Style category enum
CREATE TYPE style_category_enum AS ENUM (
    'classic', 'trendy', 'minimalist', 'maximalist',
    'feminine', 'masculine', 'edgy', 'romantic',
    'bohemian', 'preppy', 'sporty', 'avant_garde',
    'streetwear', 'vintage', 'luxury', 'casual'
);

-- Budget level enum
CREATE TYPE budget_level_enum AS ENUM (
    'budget_conscious', 'moderate', 'premium', 'luxury', 'ultra_luxury'
);

-- Fit preference enum
CREATE TYPE fit_preference_enum AS ENUM (
    'tight', 'slim', 'regular', 'relaxed', 'oversized', 'loose'
);

-- Occasion type enum
CREATE TYPE occasion_type_enum AS ENUM (
    'everyday', 'work', 'formal', 'casual', 'date_night',
    'weekend', 'vacation', 'party', 'athletic', 'special_event'
);

-- Signal source enum
CREATE TYPE style_signal_source_enum AS ENUM (
    'wardrobe', 'liked_outfits', 'purchase_history', 'style_quiz',
    'browsing_behavior', 'explicit_preference', 'inferred'
);

-- ═══════════════════════════════════════════════════════════════════
-- STYLE DNA PROFILE TABLE
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE style_dna_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Primary style archetype
    primary_style style_category_enum,
    secondary_styles style_category_enum[] DEFAULT '{}',
    style_confidence DECIMAL(5,4) DEFAULT 0.0,
    
    -- Style vector (384 dimensions for sentence-transformers)
    style_vector VECTOR(384),
    
    -- Color preferences (normalized weights)
    color_preferences JSONB DEFAULT '{
        "primary": [],
        "secondary": [],
        "avoided": [],
        "undertone": null,
        "palette_type": null
    }'::jsonb,
    
    -- Fit preferences
    fit_preference fit_preference_enum DEFAULT 'regular',
    fit_preferences JSONB DEFAULT '{
        "tops": "regular",
        "bottoms": "regular",
        "dresses": "regular",
        "outerwear": "regular"
    }'::jsonb,
    
    -- Occasion preferences (weights 0-1)
    occasion_preferences JSONB DEFAULT '{
        "everyday": 0.5,
        "work": 0.5,
        "formal": 0.3,
        "casual": 0.7,
        "date_night": 0.4,
        "weekend": 0.6,
        "vacation": 0.5,
        "party": 0.4,
        "athletic": 0.3,
        "special_event": 0.2
    }'::jsonb,
    
    -- Brand affinity (top brands with scores)
    brand_affinity JSONB DEFAULT '[]'::jsonb,
    
    -- Budget profile
    budget_level budget_level_enum DEFAULT 'moderate',
    budget_range JSONB DEFAULT '{
        "per_item_min": null,
        "per_item_max": null,
        "monthly_max": null,
        "currency": "USD"
    }'::jsonb,
    
    -- Pattern preferences
    pattern_preferences JSONB DEFAULT '{
        "preferred": [],
        "avoided": [],
        "neutral": []
    }'::jsonb,
    
    -- Fabric preferences
    fabric_preferences JSONB DEFAULT '{
        "preferred": [],
        "avoided": [],
        "seasonal": {}
    }'::jsonb,
    
    -- Silhouette preferences
    silhouette_preferences JSONB DEFAULT '{
        "tops": [],
        "bottoms": [],
        "dresses": []
    }'::jsonb,
    
    -- Style signals summary
    signal_summary JSONB DEFAULT '{
        "wardrobe_items": 0,
        "liked_outfits": 0,
        "purchases": 0,
        "quiz_answers": 0,
        "browsing_events": 0,
        "last_analyzed": null
    }'::jsonb,
    
    -- Profile metadata
    profile_completeness DECIMAL(5,2) DEFAULT 0.0,
    profile_version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Encrypted sensitive data (for privacy)
    encrypted_preferences TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_user_style_dna UNIQUE (user_id)
);

-- Indexes
CREATE INDEX idx_style_dna_user ON style_dna_profiles(user_id);
CREATE INDEX idx_style_dna_primary_style ON style_dna_profiles(primary_style);
CREATE INDEX idx_style_dna_budget ON style_dna_profiles(budget_level);

-- Vector index for similarity search (using HNSW)
CREATE INDEX idx_style_dna_vector ON style_dna_profiles 
    USING hnsw (style_vector vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ═══════════════════════════════════════════════════════════════════
-- STYLE VECTORS TABLE (Historical vectors for evolution tracking)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE style_vectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Vector data
    vector VECTOR(384) NOT NULL,
    vector_type VARCHAR(50) NOT NULL DEFAULT 'full_profile',
    
    -- Source composition
    source_weights JSONB DEFAULT '{
        "wardrobe": 0.3,
        "liked_outfits": 0.25,
        "purchases": 0.2,
        "style_quiz": 0.15,
        "browsing": 0.1
    }'::jsonb,
    
    -- Confidence and quality metrics
    confidence_score DECIMAL(5,4) DEFAULT 0.0,
    data_quality_score DECIMAL(5,4) DEFAULT 0.0,
    
    -- Snapshot metadata
    snapshot_reason VARCHAR(50) DEFAULT 'periodic',
    is_baseline BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_style_vectors_user ON style_vectors(user_id);
CREATE INDEX idx_style_vectors_created ON style_vectors(created_at DESC);
CREATE INDEX idx_style_vectors_type ON style_vectors(vector_type);

-- ═══════════════════════════════════════════════════════════════════
-- STYLE PREFERENCES TABLE (Detailed preference signals)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE style_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Preference details
    preference_type VARCHAR(50) NOT NULL,
    preference_key VARCHAR(100) NOT NULL,
    preference_value JSONB NOT NULL,
    
    -- Signal strength
    weight DECIMAL(4,3) DEFAULT 0.5,
    confidence DECIMAL(4,3) DEFAULT 0.5,
    
    -- Source tracking
    source style_signal_source_enum NOT NULL,
    source_metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Decay for behavioral signals
    decay_rate DECIMAL(4,4) DEFAULT 0.0,
    effective_weight DECIMAL(4,3) DEFAULT 0.5,
    
    -- Validity
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_user_preference UNIQUE (user_id, preference_type, preference_key)
);

-- Indexes
CREATE INDEX idx_style_preferences_user ON style_preferences(user_id);
CREATE INDEX idx_style_preferences_type ON style_preferences(preference_type);
CREATE INDEX idx_style_preferences_source ON style_preferences(source);
CREATE INDEX idx_style_preferences_active ON style_preferences(is_active) WHERE is_active = TRUE;

-- ═══════════════════════════════════════════════════════════════════
-- STYLE SIGNALS TABLE (Raw behavioral signals for analysis)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE style_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Signal identification
    signal_type VARCHAR(50) NOT NULL,
    signal_category VARCHAR(50) NOT NULL,
    
    -- Entity reference
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    
    -- Signal data
    signal_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Weight and scoring
    base_weight DECIMAL(4,3) DEFAULT 0.5,
    computed_weight DECIMAL(4,3) DEFAULT 0.5,
    
    -- Context
    context JSONB DEFAULT '{}'::jsonb,
    session_id UUID,
    
    -- Processing status
    is_processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    
    -- Decay
    decay_factor DECIMAL(4,4) DEFAULT 1.0,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_style_signals_user ON style_signals(user_id);
CREATE INDEX idx_style_signals_type ON style_signals(signal_type);
CREATE INDEX idx_style_signals_entity ON style_signals(entity_type, entity_id);
CREATE INDEX idx_style_signals_processed ON style_signals(is_processed) WHERE is_processed = FALSE;
CREATE INDEX idx_style_signals_created ON style_signals(created_at DESC);

-- ═══════════════════════════════════════════════════════════════════
-- STYLE EVOLUTION HISTORY TABLE
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE style_evolution_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Change details
    change_type VARCHAR(50) NOT NULL,
    previous_value JSONB,
    new_value JSONB NOT NULL,
    
    -- Vector delta (for tracking style drift)
    vector_delta VECTOR(384),
    drift_magnitude DECIMAL(5,4),
    
    -- Trigger
    trigger_source VARCHAR(50) NOT NULL,
    trigger_event_id UUID,
    
    -- Impact metrics
    confidence_delta DECIMAL(5,4),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_style_evolution_user ON style_evolution_history(user_id);
CREATE INDEX idx_style_evolution_type ON style_evolution_history(change_type);
CREATE INDEX idx_style_evolution_created ON style_evolution_history(created_at DESC);

-- ═══════════════════════════════════════════════════════════════════
-- STYLE CLUSTERS TABLE (User clustering for recommendations)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE style_clusters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Cluster identification
    cluster_name VARCHAR(100) NOT NULL,
    cluster_description TEXT,
    
    -- Centroid vector
    centroid_vector VECTOR(384) NOT NULL,
    
    -- Cluster metadata
    cluster_size INTEGER DEFAULT 0,
    dominant_styles style_category_enum[] DEFAULT '{}',
    dominant_colors JSONB DEFAULT '[]'::jsonb,
    avg_budget_level budget_level_enum,
    
    -- Quality metrics
    cohesion_score DECIMAL(5,4),
    silhouette_score DECIMAL(5,4),
    
    -- Version tracking
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_style_clusters_active ON style_clusters(is_active) WHERE is_active = TRUE;

-- ═══════════════════════════════════════════════════════════════════
-- USER CLUSTER ASSIGNMENTS TABLE
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE user_cluster_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cluster_id UUID NOT NULL REFERENCES style_clusters(id) ON DELETE CASCADE,
    
    -- Assignment details
    distance_to_centroid DECIMAL(5,4) NOT NULL,
    assignment_confidence DECIMAL(5,4) DEFAULT 0.0,
    
    -- Secondary clusters (for users with mixed styles)
    secondary_clusters JSONB DEFAULT '[]'::jsonb,
    
    -- Validity period
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    is_current BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_user_current_cluster UNIQUE (user_id) WHERE is_current = TRUE
);

-- Indexes
CREATE INDEX idx_user_cluster_user ON user_cluster_assignments(user_id);
CREATE INDEX idx_user_cluster_cluster ON user_cluster_assignments(cluster_id);
CREATE INDEX idx_user_cluster_current ON user_cluster_assignments(is_current) WHERE is_current = TRUE;

-- ═══════════════════════════════════════════════════════════════════
-- STYLE SIMILARITY CACHE TABLE
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE style_similarity_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id_1 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_id_2 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Similarity metrics
    cosine_similarity DECIMAL(5,4) NOT NULL,
    style_overlap_score DECIMAL(5,4),
    color_harmony_score DECIMAL(5,4),
    brand_affinity_score DECIMAL(5,4),
    
    -- Combined score
    overall_similarity DECIMAL(5,4) NOT NULL,
    
    -- Shared attributes
    shared_styles style_category_enum[] DEFAULT '{}',
    shared_brands JSONB DEFAULT '[]'::jsonb,
    shared_colors JSONB DEFAULT '[]'::jsonb,
    
    -- Cache metadata
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '24 hours',
    
    CONSTRAINT unique_user_pair UNIQUE (user_id_1, user_id_2),
    CONSTRAINT user_pair_order CHECK (user_id_1 < user_id_2)
);

-- Indexes
CREATE INDEX idx_style_similarity_users ON style_similarity_cache(user_id_1, user_id_2);
CREATE INDEX idx_style_similarity_score ON style_similarity_cache(overall_similarity DESC);
CREATE INDEX idx_style_similarity_expires ON style_similarity_cache(expires_at);

-- ═══════════════════════════════════════════════════════════════════
-- STYLE QUIZ RESPONSES TABLE
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE style_quiz_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Quiz identification
    quiz_type VARCHAR(50) NOT NULL DEFAULT 'initial',
    quiz_version INTEGER DEFAULT 1,
    
    -- Responses
    responses JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Computed results
    computed_styles JSONB DEFAULT '{}'::jsonb,
    computed_colors JSONB DEFAULT '{}'::jsonb,
    computed_fit JSONB DEFAULT '{}'::jsonb,
    
    -- Confidence
    response_confidence DECIMAL(5,4) DEFAULT 0.0,
    
    -- Metadata
    duration_seconds INTEGER,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_user_quiz_type UNIQUE (user_id, quiz_type)
);

-- Indexes
CREATE INDEX idx_style_quiz_user ON style_quiz_responses(user_id);
CREATE INDEX idx_style_quiz_type ON style_quiz_responses(quiz_type);

-- ═══════════════════════════════════════════════════════════════════
-- HELPER FUNCTIONS
-- ═══════════════════════════════════════════════════════════════════

-- Calculate cosine similarity between two style vectors
CREATE OR REPLACE FUNCTION style_cosine_similarity(v1 VECTOR, v2 VECTOR)
RETURNS DECIMAL AS $$
BEGIN
    RETURN 1 - (v1 <=> v2);
END;
$$ LANGUAGE SQL IMMUTABLE;

-- Find similar users by style vector
CREATE OR REPLACE FUNCTION find_similar_users_by_style(
    target_user_id UUID,
    limit_count INTEGER DEFAULT 10,
    min_similarity DECIMAL DEFAULT 0.7
)
RETURNS TABLE (
    user_id UUID,
    similarity DECIMAL,
    shared_styles style_category_enum[],
    shared_brands JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sdp.user_id,
        style_cosine_similarity(
            (SELECT style_vector FROM style_dna_profiles WHERE user_id = target_user_id),
            sdp.style_vector
        )::DECIMAL AS similarity,
        sdp.secondary_styles AS shared_styles,
        sdp.brand_affinity AS shared_brands
    FROM style_dna_profiles sdp
    WHERE sdp.user_id != target_user_id
      AND sdp.style_vector IS NOT NULL
      AND style_cosine_similarity(
          (SELECT style_vector FROM style_dna_profiles WHERE user_id = target_user_id),
          sdp.style_vector
      ) >= min_similarity
    ORDER BY similarity DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql STABLE;

-- Update style vector and track evolution
CREATE OR REPLACE FUNCTION update_style_vector(
    p_user_id UUID,
    p_new_vector VECTOR,
    p_reason VARCHAR DEFAULT 'periodic'
)
RETURNS VOID AS $$
DECLARE
    v_old_vector VECTOR;
    v_drift DECIMAL;
BEGIN
    -- Get old vector
    SELECT style_vector INTO v_old_vector
    FROM style_dna_profiles
    WHERE user_id = p_user_id;
    
    -- Calculate drift if old vector exists
    IF v_old_vector IS NOT NULL THEN
        v_drift := 1 - style_cosine_similarity(v_old_vector, p_new_vector);
        
        -- Record evolution
        INSERT INTO style_evolution_history (
            user_id, change_type, previous_value, new_value,
            vector_delta, drift_magnitude, trigger_source
        ) VALUES (
            p_user_id,
            'vector_update',
            jsonb_build_object('vector_type', 'previous'),
            jsonb_build_object('vector_type', 'current'),
            p_new_vector - v_old_vector,
            v_drift,
            p_reason
        );
    END IF;
    
    -- Update profile
    UPDATE style_dna_profiles
    SET style_vector = p_new_vector,
        updated_at = NOW(),
        profile_version = profile_version + 1
    WHERE user_id = p_user_id;
    
    -- Store historical vector
    INSERT INTO style_vectors (user_id, vector, snapshot_reason)
    VALUES (p_user_id, p_new_vector, p_reason);
END;
$$ LANGUAGE plpgsql;

-- Calculate profile completeness
CREATE OR REPLACE FUNCTION calculate_style_completeness(p_user_id UUID)
RETURNS DECIMAL AS $$
DECLARE
    v_score DECIMAL := 0.0;
    v_profile RECORD;
BEGIN
    SELECT * INTO v_profile FROM style_dna_profiles WHERE user_id = p_user_id;
    
    IF NOT FOUND THEN
        RETURN 0.0;
    END IF;
    
    -- Primary style (20%)
    IF v_profile.primary_style IS NOT NULL THEN
        v_score := v_score + 0.20;
    END IF;
    
    -- Style vector (20%)
    IF v_profile.style_vector IS NOT NULL THEN
        v_score := v_score + 0.20;
    END IF;
    
    -- Color preferences (15%)
    IF jsonb_array_length(v_profile.color_preferences->'primary') > 0 THEN
        v_score := v_score + 0.15;
    END IF;
    
    -- Brand affinity (15%)
    IF jsonb_array_length(v_profile.brand_affinity) > 0 THEN
        v_score := v_score + 0.15;
    END IF;
    
    -- Occasion preferences (10%)
    IF v_profile.occasion_preferences IS NOT NULL THEN
        v_score := v_score + 0.10;
    END IF;
    
    -- Budget level (10%)
    IF v_profile.budget_level IS NOT NULL THEN
        v_score := v_score + 0.10;
    END IF;
    
    -- Fit preference (5%)
    IF v_profile.fit_preference IS NOT NULL THEN
        v_score := v_score + 0.05;
    END IF;
    
    -- Pattern preferences (5%)
    IF jsonb_array_length(v_profile.pattern_preferences->'preferred') > 0 THEN
        v_score := v_score + 0.05;
    END IF;
    
    RETURN v_score * 100;
END;
$$ LANGUAGE plpgsql STABLE;

-- ═══════════════════════════════════════════════════════════════════
-- TRIGGERS
-- ═══════════════════════════════════════════════════════════════════

-- Auto-update updated_at
CREATE TRIGGER style_dna_profiles_updated_at
    BEFORE UPDATE ON style_dna_profiles
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER style_preferences_updated_at
    BEFORE UPDATE ON style_preferences
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- ═══════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE style_dna_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE style_vectors ENABLE ROW LEVEL SECURITY;
ALTER TABLE style_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE style_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE style_evolution_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE style_quiz_responses ENABLE ROW LEVEL SECURITY;

-- Users can only access their own style data
CREATE POLICY "Users can view own style DNA"
    ON style_dna_profiles FOR SELECT
    USING (auth.uid()::UUID = user_id);

CREATE POLICY "Users can update own style DNA"
    ON style_dna_profiles FOR UPDATE
    USING (auth.uid()::UUID = user_id);

CREATE POLICY "Users can insert own style DNA"
    ON style_dna_profiles FOR INSERT
    WITH CHECK (auth.uid()::UUID = user_id);

CREATE POLICY "Users can view own style vectors"
    ON style_vectors FOR SELECT
    USING (auth.uid()::UUID = user_id);

CREATE POLICY "Users can view own preferences"
    ON style_preferences FOR SELECT
    USING (auth.uid()::UUID = user_id);

CREATE POLICY "Users can manage own preferences"
    ON style_preferences FOR ALL
    USING (auth.uid()::UUID = user_id);

CREATE POLICY "Users can view own signals"
    ON style_signals FOR SELECT
    USING (auth.uid()::UUID = user_id);

CREATE POLICY "Users can insert own signals"
    ON style_signals FOR INSERT
    WITH CHECK (auth.uid()::UUID = user_id);

CREATE POLICY "Users can view own evolution"
    ON style_evolution_history FOR SELECT
    USING (auth.uid()::UUID = user_id);

CREATE POLICY "Users can view own quiz responses"
    ON style_quiz_responses FOR SELECT
    USING (auth.uid()::UUID = user_id);

CREATE POLICY "Users can insert own quiz responses"
    ON style_quiz_responses FOR INSERT
    WITH CHECK (auth.uid()::UUID = user_id);

-- ═══════════════════════════════════════════════════════════════════
-- INITIAL DATA
-- ═══════════════════════════════════════════════════════════════════

-- Insert default style clusters (will be updated by clustering algorithm)
INSERT INTO style_clusters (cluster_name, cluster_description, centroid_vector, dominant_styles) VALUES
    ('Minimalist Modern', 'Clean lines, neutral colors, timeless pieces', 
     array_fill(0.0::float, ARRAY[384])::VECTOR(384), 
     ARRAY['minimalist', 'classic']::style_category_enum[]),
    ('Bohemian Spirit', 'Free-flowing, eclectic, artistic expression',
     array_fill(0.0::float, ARRAY[384])::VECTOR(384),
     ARRAY['bohemian', 'vintage']::style_category_enum[]),
    ('Urban Edge', 'Streetwear, contemporary, bold statements',
     array_fill(0.0::float, ARRAY[384])::VECTOR(384),
     ARRAY['streetwear', 'edgy']::style_category_enum[]),
    ('Classic Elegance', 'Timeless sophistication, refined taste',
     array_fill(0.0::float, ARRAY[384])::VECTOR(384),
     ARRAY['classic', 'luxury']::style_category_enum[]),
    ('Casual Comfort', 'Relaxed, practical, everyday wear',
     array_fill(0.0::float, ARRAY[384])::VECTOR(384),
     ARRAY['casual', 'sporty']::style_category_enum[]);

-- ═══════════════════════════════════════════════════════════════════
-- GRANTS
-- ═══════════════════════════════════════════════════════════════════

GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
