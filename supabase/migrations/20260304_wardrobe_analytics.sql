-- ============================================================
-- CONFIT — Wardrobe Analytics Migration
-- Created: 2026-03-04
-- Description: GROUP 4 - Personal Wardrobe & Smart Reuse Analytics
-- ============================================================

-- Enable UUID extension (if not already)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ═══════════════════════════════════════════════════════════════════
-- Wardrobe Item Usage Tracking
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.wardrobe_item_usage (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    item_id                 VARCHAR(64) NOT NULL REFERENCES public.wardrobe_items(id) ON DELETE CASCADE,
    
    -- Wear tracking
    wear_count              INTEGER NOT NULL DEFAULT 0,
    last_worn_at            TIMESTAMPTZ,
    first_worn_at           TIMESTAMPTZ,
    
    -- Seasonal tracking
    seasons_worn            JSONB NOT NULL DEFAULT '[]'::jsonb,
    current_season_wears    INTEGER NOT NULL DEFAULT 0,
    
    -- Occasion tracking
    occasions_worn          JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Performance metrics
    cost_per_wear           NUMERIC(10, 2),
    wear_frequency_score    NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    
    analytics_updated_at    TIMESTAMPTZ,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, item_id)
);

CREATE INDEX IF NOT EXISTS idx_wardrobe_item_usage_user_id ON public.wardrobe_item_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_wardrobe_item_usage_item_id ON public.wardrobe_item_usage(item_id);
CREATE INDEX IF NOT EXISTS idx_wardrobe_item_usage_wear_count ON public.wardrobe_item_usage(wear_count DESC);

ALTER TABLE public.wardrobe_item_usage ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own wardrobe usage"
    ON public.wardrobe_item_usage FOR ALL
    USING (auth.uid() = user_id);

-- ═══════════════════════════════════════════════════════════════════
-- Outfit History
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.outfit_history (
    id                      VARCHAR(64) PRIMARY KEY,
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Outfit composition
    outfit_name             VARCHAR(200),
    item_ids                JSONB NOT NULL,
    item_details            JSONB,
    
    -- Occasion & context
    occasion                VARCHAR(50),
    weather                 VARCHAR(30),
    temperature_c           INTEGER,
    season                  VARCHAR(20),
    
    -- Wear tracking
    worn_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_favorite             BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Feedback
    user_rating             INTEGER CHECK (user_rating >= 1 AND user_rating <= 5),
    feedback_notes          TEXT,
    
    -- AI insights
    ai_generated            BOOLEAN NOT NULL DEFAULT FALSE,
    style_score             NUMERIC(5, 2),
    color_harmony_score     NUMERIC(5, 2),
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outfit_history_user_id ON public.outfit_history(user_id);
CREATE INDEX IF NOT EXISTS idx_outfit_history_worn_at ON public.outfit_history(worn_at DESC);
CREATE INDEX IF NOT EXISTS idx_outfit_history_occasion ON public.outfit_history(occasion);
CREATE INDEX IF NOT EXISTS idx_outfit_history_season ON public.outfit_history(season);

ALTER TABLE public.outfit_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own outfit history"
    ON public.outfit_history FOR ALL
    USING (auth.uid() = user_id);

-- ═══════════════════════════════════════════════════════════════════
-- Wardrobe Seasonal Rotation
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.wardrobe_seasonal_rotation (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    item_id                 VARCHAR(64) NOT NULL REFERENCES public.wardrobe_items(id) ON DELETE CASCADE,
    
    -- Season classification
    primary_season          VARCHAR(20) CHECK (primary_season IN ('spring', 'summer', 'fall', 'winter', 'all_season')),
    secondary_seasons       JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Rotation status
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    stored_at               TIMESTAMPTZ,
    reactivated_at          TIMESTAMPTZ,
    
    -- Weather preferences
    min_temp_c              INTEGER,
    max_temp_c              INTEGER,
    weather_conditions      JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, item_id)
);

CREATE INDEX IF NOT EXISTS idx_seasonal_rotation_user_id ON public.wardrobe_seasonal_rotation(user_id);
CREATE INDEX IF NOT EXISTS idx_seasonal_rotation_item_id ON public.wardrobe_seasonal_rotation(item_id);
CREATE INDEX IF NOT EXISTS idx_seasonal_rotation_season ON public.wardrobe_seasonal_rotation(primary_season);

ALTER TABLE public.wardrobe_seasonal_rotation ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own seasonal rotation"
    ON public.wardrobe_seasonal_rotation FOR ALL
    USING (auth.uid() = user_id);

-- ═══════════════════════════════════════════════════════════════════
-- Wardrobe Sustainability Metrics
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.wardrobe_sustainability_metrics (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Usage metrics
    total_items             INTEGER NOT NULL DEFAULT 0,
    active_items            INTEGER NOT NULL DEFAULT 0,
    unused_items            INTEGER NOT NULL DEFAULT 0,
    
    -- Sustainability scores
    wardrobe_utilization_score  NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    sustainability_score        NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    
    -- Environmental impact
    total_estimated_co2_kg      NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    total_water_saved_l         NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    
    -- Shopping prevention
    purchases_prevented     INTEGER NOT NULL DEFAULT 0,
    money_saved             NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    
    -- Capsule wardrobe
    capsule_wardrobe_score      NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    capsule_items_identified    INTEGER NOT NULL DEFAULT 0,
    
    -- Declutter suggestions
    declutter_candidates        INTEGER NOT NULL DEFAULT 0,
    declutter_value_estimate    NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    
    -- Period tracking
    period_start            TIMESTAMPTZ,
    period_end              TIMESTAMPTZ,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sustainability_user_id ON public.wardrobe_sustainability_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_sustainability_score ON public.wardrobe_sustainability_metrics(sustainability_score DESC);

ALTER TABLE public.wardrobe_sustainability_metrics ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own sustainability metrics"
    ON public.wardrobe_sustainability_metrics FOR SELECT
    USING (auth.uid() = user_id);
CREATE POLICY "Users can update own sustainability metrics"
    ON public.wardrobe_sustainability_metrics FOR UPDATE
    USING (auth.uid() = user_id);

-- ═══════════════════════════════════════════════════════════════════
-- Wardrobe Color Dominance
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.wardrobe_color_dominance (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Color counts
    color_name              VARCHAR(50) NOT NULL,
    item_count              INTEGER NOT NULL DEFAULT 0,
    percentage              NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    
    -- Color harmony
    harmony_group           VARCHAR(30) CHECK (harmony_group IN ('neutral', 'warm', 'cool', 'accent')),
    complementary_colors    JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Style insights
    is_dominant             BOOLEAN NOT NULL DEFAULT FALSE,
    is_overrepresented      BOOLEAN NOT NULL DEFAULT FALSE,
    style_impact            TEXT,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, color_name)
);

CREATE INDEX IF NOT EXISTS idx_color_dominance_user_id ON public.wardrobe_color_dominance(user_id);
CREATE INDEX IF NOT EXISTS idx_color_dominance_pct ON public.wardrobe_color_dominance(percentage DESC);

ALTER TABLE public.wardrobe_color_dominance ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own color dominance"
    ON public.wardrobe_color_dominance FOR SELECT
    USING (auth.uid() = user_id);

-- ═══════════════════════════════════════════════════════════════════
-- Wardrobe Style Dominance
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.wardrobe_style_dominance (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Category/style
    category                VARCHAR(50) NOT NULL,
    item_count              INTEGER NOT NULL DEFAULT 0,
    percentage              NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    
    -- Style tags
    style_tags              JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Wear patterns
    avg_wear_count          NUMERIC(8, 2) NOT NULL DEFAULT 0.0,
    most_worn_item_id       VARCHAR(64),
    
    -- Gaps and recommendations
    is_gap                  BOOLEAN NOT NULL DEFAULT FALSE,
    gap_severity            VARCHAR(20) CHECK (gap_severity IN ('critical', 'moderate', 'minor')),
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, category)
);

CREATE INDEX IF NOT EXISTS idx_style_dominance_user_id ON public.wardrobe_style_dominance(user_id);

ALTER TABLE public.wardrobe_style_dominance ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own style dominance"
    ON public.wardrobe_style_dominance FOR SELECT
    USING (auth.uid() = user_id);

-- ═══════════════════════════════════════════════════════════════════
-- Wardrobe Confidence Scores
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.wardrobe_confidence_scores (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Overall wardrobe confidence
    overall_confidence      NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    
    -- Dimension scores (0-100)
    variety_score           NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    versatility_score       NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    utilization_score       NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    cohesion_score          NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    seasonality_score       NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    quality_score           NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    
    -- Outfit creation readiness
    outfit_readiness        NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    occasion_coverage       JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Improvement suggestions
    top_improvements        JSONB NOT NULL DEFAULT '[]'::jsonb,
    quick_wins              JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wardrobe_confidence_user_id ON public.wardrobe_confidence_scores(user_id);

ALTER TABLE public.wardrobe_confidence_scores ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own wardrobe confidence"
    ON public.wardrobe_confidence_scores FOR SELECT
    USING (auth.uid() = user_id);

-- ═══════════════════════════════════════════════════════════════════
-- Capsule Wardrobe Detection
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.capsule_wardrobe_detections (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Capsule info
    capsule_name            VARCHAR(100),
    capsule_type            VARCHAR(30) NOT NULL CHECK (capsule_type IN ('work', 'casual', 'travel', 'seasonal', 'custom')),
    
    -- Items
    item_ids                JSONB NOT NULL,
    item_count              INTEGER NOT NULL,
    
    -- Metrics
    cohesion_score          NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    versatility_score       NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    outfit_combinations     INTEGER NOT NULL DEFAULT 0,
    
    -- Color palette
    dominant_colors         JSONB NOT NULL DEFAULT '[]'::jsonb,
    color_harmony_type      VARCHAR(30),
    
    -- Status
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    is_ai_suggested         BOOLEAN NOT NULL DEFAULT FALSE,
    user_approved           BOOLEAN,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_capsule_wardrobe_user_id ON public.capsule_wardrobe_detections(user_id);
CREATE INDEX IF NOT EXISTS idx_capsule_wardrobe_type ON public.capsule_wardrobe_detections(capsule_type);

ALTER TABLE public.capsule_wardrobe_detections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own capsule wardrobes"
    ON public.capsule_wardrobe_detections FOR ALL
    USING (auth.uid() = user_id);

-- ═══════════════════════════════════════════════════════════════════
-- Declutter Suggestions
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.declutter_suggestions (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    item_id                 VARCHAR(64) NOT NULL REFERENCES public.wardrobe_items(id) ON DELETE CASCADE,
    
    -- Suggestion details
    suggestion_type         VARCHAR(30) NOT NULL CHECK (suggestion_type IN ('unused', 'duplicate', 'style_mismatch', 'size_change', 'low_usage')),
    confidence              NUMERIC(3, 2) NOT NULL DEFAULT 0.0,
    
    -- Reasoning
    reason                  TEXT,
    data_points             JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Value estimation
    estimated_resale_value  NUMERIC(10, 2),
    donation_value          NUMERIC(10, 2),
    
    -- User actions
    status                  VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'dismissed', 'acted', 'kept')),
    dismissed_at            TIMESTAMPTZ,
    acted_at                TIMESTAMPTZ,
    action_taken            VARCHAR(30) CHECK (action_taken IN ('resold', 'donated', 'recycled', 'gifted')),
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_declutter_user_id ON public.declutter_suggestions(user_id);
CREATE INDEX IF NOT EXISTS idx_declutter_item_id ON public.declutter_suggestions(item_id);
CREATE INDEX IF NOT EXISTS idx_declutter_status ON public.declutter_suggestions(status);

ALTER TABLE public.declutter_suggestions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own declutter suggestions"
    ON public.declutter_suggestions FOR ALL
    USING (auth.uid() = user_id);

-- ═══════════════════════════════════════════════════════════════════
-- Purchase Avoidance Signals
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.purchase_avoidance_signals (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Signal details
    signal_type             VARCHAR(30) NOT NULL CHECK (signal_type IN ('duplicate_check', 'outfit_suggestion', 'item_found')),
    
    -- Product info (what was considered for purchase)
    product_name            VARCHAR(200),
    product_category        VARCHAR(50),
    product_color           VARCHAR(50),
    product_price           NUMERIC(10, 2),
    
    -- Matching wardrobe item
    matched_item_id         VARCHAR(64),
    match_similarity        NUMERIC(3, 2),
    
    -- Outcome
    purchase_avoided        BOOLEAN NOT NULL DEFAULT TRUE,
    user_feedback           VARCHAR(20) CHECK (user_feedback IN ('helpful', 'not_similar', 'still_bought')),
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_purchase_avoidance_user_id ON public.purchase_avoidance_signals(user_id);
CREATE INDEX IF NOT EXISTS idx_purchase_avoidance_created_at ON public.purchase_avoidance_signals(created_at DESC);

ALTER TABLE public.purchase_avoidance_signals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own purchase avoidance signals"
    ON public.purchase_avoidance_signals FOR SELECT
    USING (auth.uid() = user_id);

-- ═══════════════════════════════════════════════════════════════════
-- Auto-update triggers
-- ═══════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_wardrobe_item_usage_updated_at
    BEFORE UPDATE ON public.wardrobe_item_usage
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_seasonal_rotation_updated_at
    BEFORE UPDATE ON public.wardrobe_seasonal_rotation
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_sustainability_metrics_updated_at
    BEFORE UPDATE ON public.wardrobe_sustainability_metrics
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_color_dominance_updated_at
    BEFORE UPDATE ON public.wardrobe_color_dominance
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_style_dominance_updated_at
    BEFORE UPDATE ON public.wardrobe_style_dominance
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_wardrobe_confidence_updated_at
    BEFORE UPDATE ON public.wardrobe_confidence_scores
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_capsule_wardrobe_updated_at
    BEFORE UPDATE ON public.capsule_wardrobe_detections
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_declutter_suggestions_updated_at
    BEFORE UPDATE ON public.declutter_suggestions
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
