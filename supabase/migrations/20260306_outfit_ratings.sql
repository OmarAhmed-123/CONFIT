-- Outfit Rating System Migration
-- Creates tables for outfit ratings, likes, popularity, saves, shares, and rate limiting

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Outfit Ratings ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS outfit_ratings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    outfit_id VARCHAR(64) NOT NULL REFERENCES outfits(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- One rating per user per outfit
    UNIQUE(outfit_id, user_id)
);

-- Indexes for outfit_ratings
CREATE INDEX idx_outfit_ratings_outfit_id ON outfit_ratings(outfit_id);
CREATE INDEX idx_outfit_ratings_user_id ON outfit_ratings(user_id);
CREATE INDEX idx_outfit_ratings_created_at ON outfit_ratings(created_at DESC);

-- ── Outfit Likes ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS outfit_likes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    outfit_id VARCHAR(64) NOT NULL REFERENCES outfits(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_like BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- One like/dislike per user per outfit
    UNIQUE(outfit_id, user_id)
);

-- Indexes for outfit_likes
CREATE INDEX idx_outfit_likes_outfit_id ON outfit_likes(outfit_id);
CREATE INDEX idx_outfit_likes_user_id ON outfit_likes(user_id);
CREATE INDEX idx_outfit_likes_is_like ON outfit_likes(is_like);

-- ── Outfit Popularity ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS outfit_popularity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    outfit_id VARCHAR(64) NOT NULL REFERENCES outfits(id) ON DELETE CASCADE UNIQUE,
    total_ratings INTEGER NOT NULL DEFAULT 0,
    rating_sum INTEGER NOT NULL DEFAULT 0,
    avg_rating FLOAT NOT NULL DEFAULT 0.0,
    like_count INTEGER NOT NULL DEFAULT 0,
    dislike_count INTEGER NOT NULL DEFAULT 0,
    save_count INTEGER NOT NULL DEFAULT 0,
    share_count INTEGER NOT NULL DEFAULT 0,
    view_count INTEGER NOT NULL DEFAULT 0,
    trending_score FLOAT NOT NULL DEFAULT 0.0,
    popularity_score FLOAT NOT NULL DEFAULT 0.0,
    style_relevance_score FLOAT NOT NULL DEFAULT 0.0,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for outfit_popularity
CREATE INDEX idx_outfit_popularity_outfit_id ON outfit_popularity(outfit_id);
CREATE INDEX idx_outfit_popularity_trending ON outfit_popularity(trending_score DESC);
CREATE INDEX idx_outfit_popularity_popularity ON outfit_popularity(popularity_score DESC);
CREATE INDEX idx_outfit_popularity_last_activity ON outfit_popularity(last_activity_at DESC);

-- ── Outfit Saves ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS outfit_saves (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    outfit_id VARCHAR(64) NOT NULL REFERENCES outfits(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    collection_name VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- One save per user per outfit
    UNIQUE(outfit_id, user_id)
);

-- Indexes for outfit_saves
CREATE INDEX idx_outfit_saves_outfit_id ON outfit_saves(outfit_id);
CREATE INDEX idx_outfit_saves_user_id ON outfit_saves(user_id);
CREATE INDEX idx_outfit_saves_collection ON outfit_saves(collection_name);

-- ── Outfit Shares ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS outfit_shares (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    outfit_id VARCHAR(64) NOT NULL REFERENCES outfits(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for outfit_shares
CREATE INDEX idx_outfit_shares_outfit_id ON outfit_shares(outfit_id);
CREATE INDEX idx_outfit_shares_user_id ON outfit_shares(user_id);
CREATE INDEX idx_outfit_shares_platform ON outfit_shares(platform);

-- ── Outfit Rating Rate Limits ──────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS outfit_rating_rate_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action_type VARCHAR(32) NOT NULL CHECK (action_type IN ('rate', 'like', 'save', 'share')),
    action_count INTEGER NOT NULL DEFAULT 1,
    window_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- One rate limit record per user per action type per window
    UNIQUE(user_id, action_type)
);

-- Indexes for rate limits
CREATE INDEX idx_outfit_rate_limits_user_id ON outfit_rating_rate_limits(user_id);
CREATE INDEX idx_outfit_rate_limits_window ON outfit_rating_rate_limits(window_start);

-- ── Triggers ───────────────────────────────────────────────────────────────────

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_outfit_ratings_updated_at ON outfit_ratings;
CREATE TRIGGER update_outfit_ratings_updated_at
    BEFORE UPDATE ON outfit_ratings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_outfit_popularity_updated_at ON outfit_popularity;
CREATE TRIGGER update_outfit_popularity_updated_at
    BEFORE UPDATE ON outfit_popularity
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_outfit_rate_limits_updated_at ON outfit_rating_rate_limits;
CREATE TRIGGER update_outfit_rate_limits_updated_at
    BEFORE UPDATE ON outfit_rating_rate_limits
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ── Row Level Security ─────────────────────────────────────────────────────────

-- Enable RLS on all tables
ALTER TABLE outfit_ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE outfit_likes ENABLE ROW LEVEL SECURITY;
ALTER TABLE outfit_popularity ENABLE ROW LEVEL SECURITY;
ALTER TABLE outfit_saves ENABLE ROW LEVEL SECURITY;
ALTER TABLE outfit_shares ENABLE ROW LEVEL SECURITY;
ALTER TABLE outfit_rating_rate_limits ENABLE ROW LEVEL SECURITY;

-- RLS Policies for outfit_ratings
CREATE POLICY "Users can view all ratings" ON outfit_ratings
    FOR SELECT USING (TRUE);

CREATE POLICY "Users can insert their own ratings" ON outfit_ratings
    FOR INSERT WITH CHECK (auth.uid()::uuid = user_id);

CREATE POLICY "Users can update their own ratings" ON outfit_ratings
    FOR UPDATE USING (auth.uid()::uuid = user_id);

CREATE POLICY "Users can delete their own ratings" ON outfit_ratings
    FOR DELETE USING (auth.uid()::uuid = user_id);

-- RLS Policies for outfit_likes
CREATE POLICY "Users can view all likes" ON outfit_likes
    FOR SELECT USING (TRUE);

CREATE POLICY "Users can insert their own likes" ON outfit_likes
    FOR INSERT WITH CHECK (auth.uid()::uuid = user_id);

CREATE POLICY "Users can delete their own likes" ON outfit_likes
    FOR DELETE USING (auth.uid()::uuid = user_id);

-- RLS Policies for outfit_popularity
CREATE POLICY "Users can view all popularity" ON outfit_popularity
    FOR SELECT USING (TRUE);

-- RLS Policies for outfit_saves
CREATE POLICY "Users can view their own saves" ON outfit_saves
    FOR SELECT USING (auth.uid()::uuid = user_id);

CREATE POLICY "Users can insert their own saves" ON outfit_saves
    FOR INSERT WITH CHECK (auth.uid()::uuid = user_id);

CREATE POLICY "Users can delete their own saves" ON outfit_saves
    FOR DELETE USING (auth.uid()::uuid = user_id);

-- RLS Policies for outfit_shares
CREATE POLICY "Users can view their own shares" ON outfit_shares
    FOR SELECT USING (auth.uid()::uuid = user_id);

CREATE POLICY "Users can insert their own shares" ON outfit_shares
    FOR INSERT WITH CHECK (auth.uid()::uuid = user_id);

-- RLS Policies for outfit_rating_rate_limits
CREATE POLICY "Users can view their own rate limits" ON outfit_rating_rate_limits
    FOR SELECT USING (auth.uid()::uuid = user_id);

-- ── Comments ───────────────────────────────────────────────────────────────────

COMMENT ON TABLE outfit_ratings IS 'User ratings for outfits (1-5 stars)';
COMMENT ON TABLE outfit_likes IS 'User likes/dislikes for outfits';
COMMENT ON TABLE outfit_popularity IS 'Aggregated popularity metrics for outfits';
COMMENT ON TABLE outfit_saves IS 'Users saving outfits to their collection';
COMMENT ON TABLE outfit_shares IS 'Track outfit shares for analytics and popularity';
COMMENT ON TABLE outfit_rating_rate_limits IS 'Rate limiting for outfit ratings to prevent spam';
