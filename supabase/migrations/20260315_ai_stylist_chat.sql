-- ═══════════════════════════════════════════════════════════════════════════
-- CONFIT - AI Stylist Chat Tables
-- ═══════════════════════════════════════════════════════════════════════════
-- Creates tables for chat sessions, messages, recommendations, and knowledge embeddings

-- ── Enumerated Types ────────────────────────────────────────────────────────

CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system');
CREATE TYPE recommendation_type AS ENUM ('outfit', 'product', 'wardrobe_item', 'style_tip', 'color_advice');
CREATE TYPE occasion_type AS ENUM ('wedding', 'work', 'casual', 'date', 'party', 'interview', 'travel', 'gym', 'beach', 'formal', 'brunch', 'outdoor');
CREATE TYPE budget_level AS ENUM ('budget', 'moderate', 'premium', 'luxury');

-- ── Chat Sessions Table ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Session metadata
    title VARCHAR(255),
    context JSONB NOT NULL DEFAULT '{}',
    
    -- Detected context from conversation
    detected_occasion occasion_type,
    detected_budget budget_level,
    detected_style_preference VARCHAR(100),
    
    -- Session state
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    message_count INTEGER NOT NULL DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ
);

-- Indexes for chat_sessions
CREATE INDEX ix_chat_sessions_user ON chat_sessions(user_id);
CREATE INDEX ix_chat_sessions_active ON chat_sessions(is_active);
CREATE INDEX ix_chat_sessions_user_active ON chat_sessions(user_id, is_active);
CREATE INDEX ix_chat_sessions_created ON chat_sessions(created_at DESC);
CREATE INDEX ix_chat_sessions_last_message ON chat_sessions(last_message_at DESC);

-- ── Chat Messages Table ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    
    -- Message content
    role message_role NOT NULL,
    content TEXT NOT NULL,
    
    -- Structured response data (for assistant messages)
    detected_intent VARCHAR(100),
    detected_entities JSONB NOT NULL DEFAULT '{}',
    
    -- Response metadata
    tokens_used INTEGER,
    model_version VARCHAR(50),
    response_time_ms INTEGER,
    
    -- Feedback
    user_feedback INTEGER CHECK (user_feedback IS NULL OR (user_feedback >= 1 AND user_feedback <= 5)),
    feedback_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for chat_messages
CREATE INDEX ix_chat_messages_session ON chat_messages(session_id);
CREATE INDEX ix_chat_messages_session_created ON chat_messages(session_id, created_at);
CREATE INDEX ix_chat_messages_role ON chat_messages(role);

-- ── Stylist Recommendations Table ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS stylist_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    message_id UUID REFERENCES chat_messages(id) ON DELETE CASCADE,
    
    -- Recommendation type
    recommendation_type recommendation_type NOT NULL,
    
    -- Content
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Reference data
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    wardrobe_item_id VARCHAR(64) REFERENCES wardrobe_items(id) ON DELETE SET NULL,
    outfit_id VARCHAR(64) REFERENCES outfits(id) ON DELETE SET NULL,
    
    -- For outfit recommendations (multiple items)
    item_ids JSONB NOT NULL DEFAULT '[]',
    
    -- Media
    image_url TEXT,
    
    -- Scoring
    relevance_score FLOAT NOT NULL DEFAULT 0.0,
    style_match_score FLOAT,
    price_match_score FLOAT,
    occasion_fit_score FLOAT,
    
    -- Pricing
    estimated_price NUMERIC(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- User interaction
    was_clicked BOOLEAN NOT NULL DEFAULT FALSE,
    was_added_to_cart BOOLEAN NOT NULL DEFAULT FALSE,
    was_added_to_wishlist BOOLEAN NOT NULL DEFAULT FALSE,
    was_dismissed BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Context
    context_data JSONB NOT NULL DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    interacted_at TIMESTAMPTZ
);

-- Indexes for stylist_recommendations
CREATE INDEX ix_stylist_recommendations_session ON stylist_recommendations(session_id);
CREATE INDEX ix_stylist_recommendations_message ON stylist_recommendations(message_id);
CREATE INDEX ix_stylist_recommendations_type ON stylist_recommendations(recommendation_type);
CREATE INDEX ix_stylist_recommendations_session_type ON stylist_recommendations(session_id, recommendation_type);
CREATE INDEX ix_stylist_recommendations_scores ON stylist_recommendations(relevance_score, style_match_score);

-- ── Fashion Knowledge Embeddings Table ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS fashion_knowledge_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Content
    content_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    
    -- Metadata
    tags JSONB NOT NULL DEFAULT '[]',
    categories JSONB NOT NULL DEFAULT '[]',
    occasions JSONB NOT NULL DEFAULT '[]',
    seasons JSONB NOT NULL DEFAULT '[]',
    
    -- Embedding vector (using pgvector)
    embedding VECTOR(1536),
    embedding_model VARCHAR(100),
    
    -- Usage tracking
    usage_count INTEGER NOT NULL DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for fashion_knowledge_embeddings
CREATE INDEX ix_fashion_embeddings_type ON fashion_knowledge_embeddings(content_type);
CREATE INDEX ix_fashion_embeddings_tags ON fashion_knowledge_embeddings USING GIN(tags);

-- Vector similarity search index (if pgvector is available)
-- CREATE INDEX ix_fashion_embeddings_vector ON fashion_knowledge_embeddings USING ivfflat (embedding vector_cosine_ops);

-- ── Triggers ────────────────────────────────────────────────────────────────

-- Update timestamp trigger for chat_sessions
CREATE OR REPLACE FUNCTION update_chat_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER chat_sessions_updated_at
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_session_timestamp();

-- Update message count on new message
CREATE OR REPLACE FUNCTION update_chat_session_message_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE chat_sessions
    SET message_count = message_count + 1,
        last_message_at = NOW()
    WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER chat_messages_count
    AFTER INSERT ON chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_session_message_count();

-- ── Row Level Security ──────────────────────────────────────────────────────

ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE stylist_recommendations ENABLE ROW LEVEL SECURITY;

-- Users can only access their own chat sessions
CREATE POLICY chat_sessions_user_policy ON chat_sessions
    FOR ALL USING (user_id = auth.uid() OR user_id IS NULL);

-- Users can only access messages from their own sessions
CREATE POLICY chat_messages_user_policy ON chat_messages
    FOR ALL USING (
        session_id IN (SELECT id FROM chat_sessions WHERE user_id = auth.uid() OR user_id IS NULL)
    );

-- Users can only access recommendations from their own sessions
CREATE POLICY stylist_recommendations_user_policy ON stylist_recommendations
    FOR ALL USING (
        session_id IN (SELECT id FROM chat_sessions WHERE user_id = auth.uid() OR user_id IS NULL)
    );

-- ── Comments ─────────────────────────────────────────────────────────────────

COMMENT ON TABLE chat_sessions IS 'Conversation sessions between users and AI stylist';
COMMENT ON TABLE chat_messages IS 'Individual messages within chat sessions';
COMMENT ON TABLE stylist_recommendations IS 'Product/outfit recommendations made by the AI stylist';
COMMENT ON TABLE fashion_knowledge_embeddings IS 'Vector embeddings for fashion knowledge base';
