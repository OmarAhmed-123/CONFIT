-- ============================================================
-- CONFIT — AI Central Brain Integration Migration
-- Created: 2026-03-03
-- Description: Tables for AI brain signals, recommendations,
--              and style evolution tracking
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── AI Recommendation History ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_recommendation_history (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Recommendation details
    recommendation_type     VARCHAR(50) NOT NULL,
    entity_ids              JSONB NOT NULL DEFAULT '[]',
    scores                  JSONB NOT NULL DEFAULT '{}',
    explanation             TEXT,
    confidence              DECIMAL(5,2) NOT NULL DEFAULT 0.0,
    
    -- Context
    occasion                VARCHAR(50),
    budget                  DECIMAL(10,2),
    context_snapshot        JSONB DEFAULT '{}',
    
    -- Feedback
    user_feedback           VARCHAR(20),
    feedback_reason         TEXT,
    feedback_at             TIMESTAMPTZ,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_rec_history_user ON ai_recommendation_history(user_id, created_at DESC);
CREATE INDEX idx_ai_rec_history_type ON ai_recommendation_history(recommendation_type);
CREATE INDEX idx_ai_rec_history_feedback ON ai_recommendation_history(user_feedback);

ALTER TABLE ai_recommendation_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own recommendations" ON ai_recommendation_history FOR SELECT USING (auth.uid() = user_id);

-- ── Conversational Memory Store ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS stylist_conversation_memory (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Serialized conversation state
    turns                   JSONB NOT NULL DEFAULT '[]',
    context                 JSONB NOT NULL DEFAULT '{}',
    user_goals              JSONB NOT NULL DEFAULT '[]',
    last_recommendation_ids JSONB NOT NULL DEFAULT '[]',
    
    -- Metadata
    turn_count              INTEGER DEFAULT 0,
    last_intent             VARCHAR(50),
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conversation_memory_user ON stylist_conversation_memory(user_id);

ALTER TABLE stylist_conversation_memory ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own conversation" ON stylist_conversation_memory FOR ALL USING (auth.uid() = user_id);

CREATE TRIGGER trg_conversation_memory_updated_at
    BEFORE UPDATE ON stylist_conversation_memory
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── Outfit Interaction Events ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS outfit_interaction_events (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    outfit_id               VARCHAR(100) NOT NULL,
    
    -- Event details
    event_type              VARCHAR(50) NOT NULL,
    duration_seconds        INTEGER,
    
    -- Context
    source_page             VARCHAR(100),
    device_type             VARCHAR(20),
    referrer                VARCHAR(200),
    
    -- Items involved
    items_viewed            JSONB DEFAULT '[]',
    items_clicked           JSONB DEFAULT '[]',
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_outfit_interactions_user ON outfit_interaction_events(user_id, created_at DESC);
CREATE INDEX idx_outfit_interactions_outfit ON outfit_interaction_events(outfit_id);
CREATE INDEX idx_outfit_interactions_type ON outfit_interaction_events(event_type);

ALTER TABLE outfit_interaction_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users read own interactions" ON outfit_interaction_events FOR SELECT USING (auth.uid() = user_id);

-- ── Style Rule Violations Log ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS style_rule_violations (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    outfit_id               VARCHAR(100),
    
    -- Violation details
    rule_type               VARCHAR(50) NOT NULL,
    rule_name               VARCHAR(100) NOT NULL,
    severity                VARCHAR(20) NOT NULL DEFAULT 'warning',
    description             TEXT NOT NULL,
    
    -- Context
    affected_items          JSONB DEFAULT '[]',
    suggestion              TEXT,
    
    -- User response
    user_acknowledged       BOOLEAN DEFAULT FALSE,
    user_dismissed          BOOLEAN DEFAULT FALSE,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_style_violations_user ON style_rule_violations(user_id, created_at DESC);
CREATE INDEX idx_style_violations_rule ON style_rule_violations(rule_type, rule_name);

-- ── Trend Engagement Tracking ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS trend_engagement (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Trend details
    trend_type              VARCHAR(30) NOT NULL,
    trend_name              VARCHAR(100) NOT NULL,
    
    -- Engagement
    engagement_type         VARCHAR(30) NOT NULL,
    engagement_score        DECIMAL(5,2) DEFAULT 1.0,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trend_engagement_user ON trend_engagement(user_id, created_at DESC);
CREATE INDEX idx_trend_engagement_trend ON trend_engagement(trend_type, trend_name);

-- ── Weather-Based Recommendations Cache ────────────────────────────
CREATE TABLE IF NOT EXISTS weather_recommendation_cache (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Weather snapshot
    weather_condition       VARCHAR(50) NOT NULL,
    temperature_c           INTEGER,
    humidity                INTEGER,
    location                VARCHAR(100),
    
    -- Recommendations
    recommendations         JSONB NOT NULL DEFAULT '[]',
    
    -- Cache validity
    valid_until             TIMESTAMPTZ NOT NULL,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_weather_cache_user ON weather_recommendation_cache(user_id);
CREATE INDEX idx_weather_cache_valid ON weather_recommendation_cache(valid_until);

-- ── AI Brain Session Context ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS ai_brain_sessions (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_type            VARCHAR(50) NOT NULL,
    
    -- Session state
    style_vector_snapshot   JSONB NOT NULL DEFAULT '{}',
    context_snapshot        JSONB NOT NULL DEFAULT '{}',
    
    -- Metrics
    recommendations_shown   INTEGER DEFAULT 0,
    recommendations_accepted INTEGER DEFAULT 0,
    recommendations_rejected INTEGER DEFAULT 0,
    
    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at                TIMESTAMPTZ,
    duration_seconds        INTEGER
);

CREATE INDEX idx_ai_sessions_user ON ai_brain_sessions(user_id, started_at DESC);
CREATE INDEX idx_ai_sessions_type ON ai_brain_sessions(session_type);

-- ── Outfit Scoring History ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS outfit_scoring_history (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    outfit_id               VARCHAR(100) NOT NULL,
    user_id                 UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Multi-dimensional scores
    style_alignment         DECIMAL(5,2),
    color_harmony           DECIMAL(5,2),
    occasion_fit            DECIMAL(5,2),
    trend_alignment         DECIMAL(5,2),
    budget_fit              DECIMAL(5,2),
    wardrobe_compat         DECIMAL(5,2),
    overall_score           DECIMAL(5,2) NOT NULL,
    
    -- Context
    scoring_context         JSONB DEFAULT '{}',
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_outfit_scoring_outfit ON outfit_scoring_history(outfit_id, created_at DESC);
CREATE INDEX idx_outfit_scoring_score ON outfit_scoring_history(overall_score DESC);

-- ── Trigger for updating conversation turn count ────────────────────
CREATE OR REPLACE FUNCTION update_conversation_turn_count()
RETURNS TRIGGER AS $$
BEGIN
    NEW.turn_count = jsonb_array_length(NEW.turns);
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_conversation_turn_count
    BEFORE UPDATE ON stylist_conversation_memory
    FOR EACH ROW EXECUTE FUNCTION update_conversation_turn_count();
