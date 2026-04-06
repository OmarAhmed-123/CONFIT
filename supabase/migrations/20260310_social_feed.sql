-- CONFIT Social Feed Migration
-- Creates tables for social feed functionality

-- ── Social Posts ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS social_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    outfit_id VARCHAR(64) REFERENCES outfits(id) ON DELETE SET NULL,
    caption TEXT,
    hashtags JSONB DEFAULT '[]'::jsonb,
    image_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    video_url VARCHAR(1024),
    post_type VARCHAR(32) NOT NULL DEFAULT 'outfit',
    visibility VARCHAR(32) NOT NULL DEFAULT 'public',
    location VARCHAR(255),
    tags JSONB DEFAULT '[]'::jsonb,
    is_featured BOOLEAN NOT NULL DEFAULT FALSE,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_social_posts_user_id ON social_posts(user_id);
CREATE INDEX idx_social_posts_outfit_id ON social_posts(outfit_id);
CREATE INDEX idx_social_posts_created_at ON social_posts(created_at DESC);
CREATE INDEX idx_social_posts_visibility ON social_posts(visibility);
CREATE INDEX idx_social_posts_hashtags ON social_posts USING GIN(hashtags);

-- ── Social Post Stats ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS social_post_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL UNIQUE REFERENCES social_posts(id) ON DELETE CASCADE,
    like_count INTEGER NOT NULL DEFAULT 0,
    comment_count INTEGER NOT NULL DEFAULT 0,
    share_count INTEGER NOT NULL DEFAULT 0,
    save_count INTEGER NOT NULL DEFAULT 0,
    view_count INTEGER NOT NULL DEFAULT 0,
    engagement_rate FLOAT NOT NULL DEFAULT 0.0,
    trending_score FLOAT NOT NULL DEFAULT 0.0,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_social_post_stats_post_id ON social_post_stats(post_id);
CREATE INDEX idx_social_post_stats_trending ON social_post_stats(trending_score DESC);
CREATE INDEX idx_social_post_stats_engagement ON social_post_stats(engagement_rate DESC);

-- ── Social Comments ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS social_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES social_posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES social_comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    mentions JSONB DEFAULT '[]'::jsonb,
    is_edited BOOLEAN NOT NULL DEFAULT FALSE,
    is_hidden BOOLEAN NOT NULL DEFAULT FALSE,
    like_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_social_comments_post_id ON social_comments(post_id);
CREATE INDEX idx_social_comments_user_id ON social_comments(user_id);
CREATE INDEX idx_social_comments_parent_id ON social_comments(parent_id);
CREATE INDEX idx_social_comments_created_at ON social_comments(created_at DESC);

-- ── Social Likes ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS social_likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_type VARCHAR(32) NOT NULL,
    entity_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, entity_type, entity_id)
);

CREATE INDEX idx_social_likes_user_id ON social_likes(user_id);
CREATE INDEX idx_social_likes_entity ON social_likes(entity_type, entity_id);

-- ── Social Follows ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS social_follows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    following_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(follower_id, following_id)
);

CREATE INDEX idx_social_follows_follower ON social_follows(follower_id);
CREATE INDEX idx_social_follows_following ON social_follows(following_id);
CREATE INDEX idx_social_follows_status ON social_follows(status);

-- ── Social Stories ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS social_stories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    outfit_id VARCHAR(64) REFERENCES outfits(id) ON DELETE SET NULL,
    media_url VARCHAR(1024) NOT NULL,
    media_type VARCHAR(32) NOT NULL DEFAULT 'image',
    caption VARCHAR(500),
    hashtags JSONB DEFAULT '[]'::jsonb,
    duration_secs INTEGER,
    view_count INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_social_stories_user_id ON social_stories(user_id);
CREATE INDEX idx_social_stories_expires ON social_stories(expires_at);
CREATE INDEX idx_social_stories_outfit_id ON social_stories(outfit_id);

-- ── Social Story Views ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS social_story_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES social_stories(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(story_id, user_id)
);

CREATE INDEX idx_social_story_views_story ON social_story_views(story_id);
CREATE INDEX idx_social_story_views_user ON social_story_views(user_id);

-- ── Social Reports ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS social_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_type VARCHAR(32) NOT NULL,
    entity_id UUID NOT NULL,
    reason VARCHAR(64) NOT NULL,
    description TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    action_taken VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_social_reports_reporter ON social_reports(reporter_id);
CREATE INDEX idx_social_reports_entity ON social_reports(entity_type, entity_id);
CREATE INDEX idx_social_reports_status ON social_reports(status);

-- ── Social Saves ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS social_saves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES social_posts(id) ON DELETE CASCADE,
    collection_name VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, post_id)
);

CREATE INDEX idx_social_saves_user ON social_saves(user_id);
CREATE INDEX idx_social_saves_post ON social_saves(post_id);
CREATE INDEX idx_social_saves_collection ON social_saves(collection_name);

-- ── Social Hashtags ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS social_hashtags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag VARCHAR(128) NOT NULL UNIQUE,
    post_count INTEGER NOT NULL DEFAULT 0,
    trending_score FLOAT NOT NULL DEFAULT 0.0,
    is_trending BOOLEAN NOT NULL DEFAULT FALSE,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_social_hashtags_tag ON social_hashtags(tag);
CREATE INDEX idx_social_hashtags_trending ON social_hashtags(is_trending, trending_score DESC);

-- ── Social Feed Cache ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS social_feed_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES social_posts(id) ON DELETE CASCADE,
    feed_type VARCHAR(32) NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    score FLOAT NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    
    UNIQUE(user_id, post_id, feed_type)
);

CREATE INDEX idx_social_feed_cache_user ON social_feed_cache(user_id, feed_type);
CREATE INDEX idx_social_feed_cache_expires ON social_feed_cache(expires_at);

-- ── Spam Detection Logs ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS spam_detection_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action_type VARCHAR(64) NOT NULL,
    content_hash VARCHAR(128),
    is_spam BOOLEAN NOT NULL DEFAULT FALSE,
    confidence FLOAT NOT NULL DEFAULT 0.0,
    detection_method VARCHAR(64),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_spam_logs_user ON spam_detection_logs(user_id);
CREATE INDEX idx_spam_logs_hash ON spam_detection_logs(content_hash);
CREATE INDEX idx_spam_logs_created ON spam_detection_logs(created_at);

-- ── Functions & Triggers ──────────────────────────────────────────────────────

-- Function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_social_posts_updated_at
    BEFORE UPDATE ON social_posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_social_post_stats_updated_at
    BEFORE UPDATE ON social_post_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_social_comments_updated_at
    BEFORE UPDATE ON social_comments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_social_hashtags_updated_at
    BEFORE UPDATE ON social_hashtags
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Function to create post stats on new post
CREATE OR REPLACE FUNCTION create_post_stats()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO social_post_stats (post_id) VALUES (NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER create_social_post_stats
    AFTER INSERT ON social_posts
    FOR EACH ROW EXECUTE FUNCTION create_post_stats();

-- Function to update trending score
CREATE OR REPLACE FUNCTION update_trending_score()
RETURNS TRIGGER AS $$
DECLARE
    age_hours FLOAT;
    time_decay FLOAT;
BEGIN
    -- Calculate age in hours
    age_hours := EXTRACT(EPOCH FROM (NOW() - NEW.last_activity_at)) / 3600;
    
    -- Time decay (half-life of 24 hours)
    time_decay := EXP(-0.693 * age_hours / 24);
    
    -- Calculate trending score
    NEW.trending_score := (
        NEW.like_count * 1.0 +
        NEW.comment_count * 2.0 +
        NEW.share_count * 3.0 +
        NEW.save_count * 2.5
    ) * time_decay;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_social_post_stats_trending
    BEFORE UPDATE ON social_post_stats
    FOR EACH ROW EXECUTE FUNCTION update_trending_score();

-- ── RLS Policies ──────────────────────────────────────────────────────────────

-- Enable RLS
ALTER TABLE social_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_likes ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_follows ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_stories ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_story_views ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_saves ENABLE ROW LEVEL SECURITY;

-- Public posts are visible to everyone
CREATE POLICY "Public posts are viewable by everyone"
    ON social_posts FOR SELECT
    USING (visibility = 'public' AND is_archived = FALSE);

-- Users can view their own posts
CREATE POLICY "Users can view own posts"
    ON social_posts FOR SELECT
    USING (user_id = auth.uid());

-- Followers can view followers-only posts
CREATE POLICY "Followers can view followers posts"
    ON social_posts FOR SELECT
    USING (
        visibility = 'followers' AND
        EXISTS (
            SELECT 1 FROM social_follows
            WHERE follower_id = auth.uid()
            AND following_id = social_posts.user_id
            AND status = 'active'
        )
    );

-- Users can insert own posts
CREATE POLICY "Users can create own posts"
    ON social_posts FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- Users can update own posts
CREATE POLICY "Users can update own posts"
    ON social_posts FOR UPDATE
    USING (user_id = auth.uid());

-- Users can delete own posts
CREATE POLICY "Users can delete own posts"
    ON social_posts FOR DELETE
    USING (user_id = auth.uid());

-- Comments policies
CREATE POLICY "Comments are viewable by everyone"
    ON social_comments FOR SELECT
    USING (is_hidden = FALSE);

CREATE POLICY "Users can create comments"
    ON social_comments FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own comments"
    ON social_comments FOR UPDATE
    USING (user_id = auth.uid());

CREATE POLICY "Users can delete own comments"
    ON social_comments FOR DELETE
    USING (user_id = auth.uid());

-- Likes policies
CREATE POLICY "Likes are viewable by everyone"
    ON social_likes FOR SELECT
    USING (TRUE);

CREATE POLICY "Users can create own likes"
    ON social_likes FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete own likes"
    ON social_likes FOR DELETE
    USING (user_id = auth.uid());

-- Follows policies
CREATE POLICY "Follows are viewable by everyone"
    ON social_follows FOR SELECT
    USING (TRUE);

CREATE POLICY "Users can create follows"
    ON social_follows FOR INSERT
    WITH CHECK (follower_id = auth.uid());

CREATE POLICY "Users can delete own follows"
    ON social_follows FOR DELETE
    USING (follower_id = auth.uid());

-- Stories policies
CREATE POLICY "Stories are viewable by followers"
    ON social_stories FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM social_follows
            WHERE follower_id = auth.uid()
            AND following_id = social_stories.user_id
            AND status = 'active'
        )
        OR user_id = auth.uid()
    );

CREATE POLICY "Users can create own stories"
    ON social_stories FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete own stories"
    ON social_stories FOR DELETE
    USING (user_id = auth.uid());

-- Saves policies
CREATE POLICY "Users can view own saves"
    ON social_saves FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can create saves"
    ON social_saves FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete own saves"
    ON social_saves FOR DELETE
    USING (user_id = auth.uid());

-- Reports policies
CREATE POLICY "Users can create reports"
    ON social_reports FOR INSERT
    WITH CHECK (reporter_id = auth.uid());

CREATE POLICY "Users can view own reports"
    ON social_reports FOR SELECT
    USING (reporter_id = auth.uid());
