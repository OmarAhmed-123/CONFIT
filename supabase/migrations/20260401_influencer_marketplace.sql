-- ============================================================
-- CONFIT — Influencer Marketplace Schema Migration
-- Created: 2026-04-01
-- Description: Influencer profiles, affiliate tracking, commissions
-- ============================================================

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Influencer Profiles ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.influencers (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Profile Info
    display_name        TEXT NOT NULL,
    bio                 TEXT,
    avatar_url          TEXT,
    banner_url          TEXT,
    website_url         TEXT,
    social_links        JSONB NOT NULL DEFAULT '{}',  -- {instagram, tiktok, youtube, pinterest, twitter}
    
    -- Influencer Tier & Status
    tier                TEXT NOT NULL DEFAULT 'emerging'
                        CHECK (tier IN ('emerging', 'rising', 'established', 'top_creator')),
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'suspended', 'inactive')),
    
    -- Niche & Style
    niches              JSONB NOT NULL DEFAULT '[]',   -- ["streetwear", "minimalist", "sustainable"]
    style_tags          JSONB NOT NULL DEFAULT '[]',
    
    -- Stats (denormalized for performance)
    followers_count     INTEGER NOT NULL DEFAULT 0,
    following_count     INTEGER NOT NULL DEFAULT 0,
    total_outfits       INTEGER NOT NULL DEFAULT 0,
    total_views         BIGINT NOT NULL DEFAULT 0,
    total_engagement    BIGINT NOT NULL DEFAULT 0,
    
    -- Commission Settings
    default_commission_rate NUMERIC(4,3) NOT NULL DEFAULT 0.10,  -- 10% default
    total_earnings      NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    pending_commissions NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    paid_commissions    NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    
    -- Verification
    is_verified         BOOLEAN NOT NULL DEFAULT FALSE,
    verified_at         TIMESTAMPTZ,
    
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Featured & Promoted
    is_featured         BOOLEAN NOT NULL DEFAULT FALSE,
    featured_until      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_influencers_user_id ON public.influencers(user_id);
CREATE INDEX IF NOT EXISTS idx_influencers_tier ON public.influencers(tier);
CREATE INDEX IF NOT EXISTS idx_influencers_status ON public.influencers(status);
CREATE INDEX IF NOT EXISTS idx_influencers_featured ON public.influencers(is_featured) WHERE is_featured = TRUE;
CREATE INDEX IF NOT EXISTS idx_influencers_followers ON public.influencers(followers_count DESC);

-- RLS Policies
ALTER TABLE public.influencers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view approved influencers"
    ON public.influencers FOR SELECT
    USING (status = 'approved' OR auth.uid() = user_id);

CREATE POLICY "Influencers can update own profile"
    ON public.influencers FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own influencer profile"
    ON public.influencers FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- ── Influencer Outfit Collections ───────────────────────────────────
CREATE TABLE IF NOT EXISTS public.influencer_outfits (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    influencer_id       UUID NOT NULL REFERENCES public.influencers(id) ON DELETE CASCADE,
    
    -- Outfit Details
    title               TEXT NOT NULL,
    description         TEXT,
    image_url           TEXT NOT NULL,
    thumbnail_url       TEXT,
    
    -- Items in outfit (references to products with styling notes)
    items               JSONB NOT NULL DEFAULT '[]',  -- [{product_id, note, position, affiliate_link_id}]
    
    -- Styling Context
    occasion            TEXT,
    season              TEXT,
    style_tags          JSONB NOT NULL DEFAULT '[]',
    budget_range        JSONB,  -- {min, max, currency}
    
    -- Stats
    view_count          BIGINT NOT NULL DEFAULT 0,
    save_count          INTEGER NOT NULL DEFAULT 0,
    share_count         INTEGER NOT NULL DEFAULT 0,
    like_count          INTEGER NOT NULL DEFAULT 0,
    purchase_count      INTEGER NOT NULL DEFAULT 0,
    
    -- Commission
    commission_rate     NUMERIC(4,3) NOT NULL DEFAULT 0.10,
    total_commission    NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    
    -- Status
    status              TEXT NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'published', 'archived')),
    visibility          TEXT NOT NULL DEFAULT 'public'
                        CHECK (visibility IN ('public', 'followers', 'private')),
    
    -- Featured
    is_featured         BOOLEAN NOT NULL DEFAULT FALSE,
    featured_order      INTEGER,
    featured_until      TIMESTAMPTZ,
    
    -- Timestamps
    published_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_influencer_outfits_influencer_id ON public.influencer_outfits(influencer_id);
CREATE INDEX IF NOT EXISTS idx_influencer_outfits_status ON public.influencer_outfits(status);
CREATE INDEX IF NOT EXISTS idx_influencer_outfits_featured ON public.influencer_outfits(is_featured) WHERE is_featured = TRUE;
CREATE INDEX IF NOT EXISTS idx_influencer_outfits_published ON public.influencer_outfits(published_at DESC);

-- RLS
ALTER TABLE public.influencer_outfits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view published public outfits"
    ON public.influencer_outfits FOR SELECT
    USING (
        (status = 'published' AND visibility = 'public')
        OR (status = 'published' AND visibility = 'followers' AND EXISTS (
            SELECT 1 FROM public.influencer_followers f 
            WHERE f.influencer_id = influencer_outfits.influencer_id 
            AND f.follower_user_id = auth.uid()
        ))
        OR EXISTS (
            SELECT 1 FROM public.influencers i 
            WHERE i.id = influencer_outfits.influencer_id AND i.user_id = auth.uid()
        )
    );

CREATE POLICY "Influencers can manage own outfits"
    ON public.influencer_outfits FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.influencers i 
        WHERE i.id = influencer_outfits.influencer_id AND i.user_id = auth.uid()
    ));

-- ── Affiliate Links ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.affiliate_links (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    influencer_id       UUID NOT NULL REFERENCES public.influencers(id) ON DELETE CASCADE,
    product_id          UUID REFERENCES public.products(id) ON DELETE SET NULL,
    
    -- Link Details
    slug                TEXT NOT NULL UNIQUE,  -- Short URL slug
    original_url        TEXT NOT NULL,         -- Original product URL
    tracking_code       TEXT NOT NULL UNIQUE,  -- Unique tracking code
    
    -- Commission
    commission_rate     NUMERIC(4,3) NOT NULL DEFAULT 0.10,
    commission_override BOOLEAN NOT NULL DEFAULT FALSE,  -- If true, overrides product default
    
    -- Stats
    click_count         BIGINT NOT NULL DEFAULT 0,
    unique_clicks       BIGINT NOT NULL DEFAULT 0,
    conversion_count    INTEGER NOT NULL DEFAULT 0,
    total_revenue       NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    total_commission    NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    
    -- Attribution Window
    attribution_window_days INTEGER NOT NULL DEFAULT 30,
    
    -- Status
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at          TIMESTAMPTZ,
    
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_affiliate_links_influencer_id ON public.affiliate_links(influencer_id);
CREATE INDEX IF NOT EXISTS idx_affiliate_links_product_id ON public.affiliate_links(product_id);
CREATE INDEX IF NOT EXISTS idx_affiliate_links_slug ON public.affiliate_links(slug);
CREATE INDEX IF NOT EXISTS idx_affiliate_links_tracking_code ON public.affiliate_links(tracking_code);
CREATE INDEX IF NOT EXISTS idx_affiliate_links_active ON public.affiliate_links(is_active) WHERE is_active = TRUE;

-- RLS
ALTER TABLE public.affiliate_links ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Influencers can view own affiliate links"
    ON public.affiliate_links FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.influencers i 
        WHERE i.id = affiliate_links.influencer_id AND i.user_id = auth.uid()
    ));

CREATE POLICY "Influencers can create own affiliate links"
    ON public.affiliate_links FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.influencers i 
        WHERE i.id = affiliate_links.influencer_id AND i.user_id = auth.uid()
    ));

CREATE POLICY "Influencers can update own affiliate links"
    ON public.affiliate_links FOR UPDATE
    USING (EXISTS (
        SELECT 1 FROM public.influencers i 
        WHERE i.id = affiliate_links.influencer_id AND i.user_id = auth.uid()
    ));

-- ── Commission Records ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.commission_records (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    influencer_id       UUID NOT NULL REFERENCES public.influencers(id) ON DELETE CASCADE,
    affiliate_link_id   UUID REFERENCES public.affiliate_links(id) ON DELETE SET NULL,
    order_id            TEXT,  -- Reference to order
    
    -- Commission Details
    product_id          UUID,
    product_name        TEXT NOT NULL,
    product_price       NUMERIC(12,2) NOT NULL,
    quantity            INTEGER NOT NULL DEFAULT 1,
    commission_rate     NUMERIC(4,3) NOT NULL,
    commission_amount   NUMERIC(12,2) NOT NULL,
    
    -- Attribution
    click_id            UUID,  -- Reference to click that led to purchase
    first_touch_at      TIMESTAMPTZ,
    last_touch_at       TIMESTAMPTZ,
    attribution_type    TEXT NOT NULL DEFAULT 'last_click'
                        CHECK (attribution_type IN ('first_click', 'last_click', 'linear', 'custom')),
    
    -- Status
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'paid', 'cancelled', 'refunded')),
    approved_at         TIMESTAMPTZ,
    paid_at             TIMESTAMPTZ,
    
    -- Payout Reference
    payout_id           UUID,
    
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_commission_records_influencer_id ON public.commission_records(influencer_id);
CREATE INDEX IF NOT EXISTS idx_commission_records_affiliate_link_id ON public.commission_records(affiliate_link_id);
CREATE INDEX IF NOT EXISTS idx_commission_records_status ON public.commission_records(status);
CREATE INDEX IF NOT EXISTS idx_commission_records_created_at ON public.commission_records(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_commission_records_payout_id ON public.commission_records(payout_id);

-- RLS
ALTER TABLE public.commission_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Influencers can view own commissions"
    ON public.commission_records FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.influencers i 
        WHERE i.id = commission_records.influencer_id AND i.user_id = auth.uid()
    ));

-- ── Influencer Followers ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.influencer_followers (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    influencer_id       UUID NOT NULL REFERENCES public.influencers(id) ON DELETE CASCADE,
    follower_user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Notification Preferences
    notify_new_outfits  BOOLEAN NOT NULL DEFAULT TRUE,
    notify_recommendations BOOLEAN NOT NULL DEFAULT TRUE,
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE (influencer_id, follower_user_id)
);

CREATE INDEX IF NOT EXISTS idx_influencer_followers_influencer_id ON public.influencer_followers(influencer_id);
CREATE INDEX IF NOT EXISTS idx_influencer_followers_follower_user_id ON public.influencer_followers(follower_user_id);

-- RLS
ALTER TABLE public.influencer_followers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view followers of public influencers"
    ON public.influencer_followers FOR SELECT
    USING (
        EXISTS (SELECT 1 FROM public.influencers WHERE id = influencer_followers.influencer_id AND status = 'approved')
        OR follower_user_id = auth.uid()
    );

CREATE POLICY "Users can follow influencers"
    ON public.influencer_followers FOR INSERT
    WITH CHECK (auth.uid() = follower_user_id);

CREATE POLICY "Users can unfollow"
    ON public.influencer_followers FOR DELETE
    USING (auth.uid() = follower_user_id);

-- ── Affiliate Click Tracking ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.affiliate_clicks (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    affiliate_link_id   UUID NOT NULL REFERENCES public.affiliate_links(id) ON DELETE CASCADE,
    user_id             UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    
    -- Click Details
    session_id          TEXT,
    ip_hash             TEXT,  -- Hashed IP for privacy
    user_agent          TEXT,
    referrer            TEXT,
    device_type         TEXT,
    country             TEXT,
    
    -- Conversion Tracking
    converted           BOOLEAN NOT NULL DEFAULT FALSE,
    converted_at        TIMESTAMPTZ,
    order_id            TEXT,
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_affiliate_clicks_affiliate_link_id ON public.affiliate_clicks(affiliate_link_id);
CREATE INDEX IF NOT EXISTS idx_affiliate_clicks_user_id ON public.affiliate_clicks(user_id);
CREATE INDEX IF NOT EXISTS idx_affiliate_clicks_session_id ON public.affiliate_clicks(session_id);
CREATE INDEX IF NOT EXISTS idx_affiliate_clicks_created_at ON public.affiliate_clicks(created_at DESC);

-- RLS
ALTER TABLE public.affiliate_clicks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Influencers can view clicks on own links"
    ON public.affiliate_clicks FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.affiliate_links al
        JOIN public.influencers i ON i.id = al.influencer_id
        WHERE al.id = affiliate_clicks.affiliate_link_id AND i.user_id = auth.uid()
    ));

-- ── Outfit Likes ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.influencer_outfit_likes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    outfit_id           UUID NOT NULL REFERENCES public.influencer_outfits(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE (outfit_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_influencer_outfit_likes_outfit_id ON public.influencer_outfit_likes(outfit_id);
CREATE INDEX IF NOT EXISTS idx_influencer_outfit_likes_user_id ON public.influencer_outfit_likes(user_id);

-- RLS
ALTER TABLE public.influencer_outfit_likes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view likes"
    ON public.influencer_outfit_likes FOR SELECT
    USING (TRUE);

CREATE POLICY "Users can like outfits"
    ON public.influencer_outfit_likes FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can unlike"
    ON public.influencer_outfit_likes FOR DELETE
    USING (auth.uid() = user_id);

-- ── Outfit Saves ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.influencer_outfit_saves (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    outfit_id           UUID NOT NULL REFERENCES public.influencer_outfits(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    collection_name     TEXT DEFAULT 'Saved',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE (outfit_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_influencer_outfit_saves_outfit_id ON public.influencer_outfit_saves(outfit_id);
CREATE INDEX IF NOT EXISTS idx_influencer_outfit_saves_user_id ON public.influencer_outfit_saves(user_id);

-- RLS
ALTER TABLE public.influencer_outfit_saves ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own saves"
    ON public.influencer_outfit_saves FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can save outfits"
    ON public.influencer_outfit_saves FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can unsave"
    ON public.influencer_outfit_saves FOR DELETE
    USING (auth.uid() = user_id);

-- ── Product Recommendations ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.influencer_recommendations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    influencer_id       UUID NOT NULL REFERENCES public.influencers(id) ON DELETE CASCADE,
    product_id          UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    
    -- Recommendation Details
    review_text         TEXT,
    rating              INTEGER CHECK (rating >= 1 AND rating <= 5),
    pros                JSONB DEFAULT '[]',
    cons                JSONB DEFAULT '[]',
    
    -- Affiliate Link (optional)
    affiliate_link_id   UUID REFERENCES public.affiliate_links(id) ON DELETE SET NULL,
    
    -- Stats
    helpful_count       INTEGER NOT NULL DEFAULT 0,
    view_count          BIGINT NOT NULL DEFAULT 0,
    
    -- Status
    is_featured         BOOLEAN NOT NULL DEFAULT FALSE,
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'archived')),
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE (influencer_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_influencer_recommendations_influencer_id ON public.influencer_recommendations(influencer_id);
CREATE INDEX IF NOT EXISTS idx_influencer_recommendations_product_id ON public.influencer_recommendations(product_id);
CREATE INDEX IF NOT EXISTS idx_influencer_recommendations_featured ON public.influencer_recommendations(is_featured) WHERE is_featured = TRUE;

-- RLS
ALTER TABLE public.influencer_recommendations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view active recommendations"
    ON public.influencer_recommendations FOR SELECT
    USING (status = 'active');

CREATE POLICY "Influencers can manage own recommendations"
    ON public.influencer_recommendations FOR ALL
    USING (EXISTS (
        SELECT 1 FROM public.influencers i 
        WHERE i.id = influencer_recommendations.influencer_id AND i.user_id = auth.uid()
    ));

-- ── Triggers for updated_at ──────────────────────────────────────────
CREATE TRIGGER trg_influencers_updated_at
    BEFORE UPDATE ON public.influencers
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_influencer_outfits_updated_at
    BEFORE UPDATE ON public.influencer_outfits
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_affiliate_links_updated_at
    BEFORE UPDATE ON public.affiliate_links
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_commission_records_updated_at
    BEFORE UPDATE ON public.commission_records
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_influencer_recommendations_updated_at
    BEFORE UPDATE ON public.influencer_recommendations
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ── Functions for Stats Updates ──────────────────────────────────────

-- Update influencer stats when outfit is created/deleted
CREATE OR REPLACE FUNCTION update_influencer_outfit_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE public.influencers 
        SET total_outfits = total_outfits + 1,
            updated_at = NOW()
        WHERE id = NEW.influencer_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE public.influencers 
        SET total_outfits = GREATEST(total_outfits - 1, 0),
            updated_at = NOW()
        WHERE id = OLD.influencer_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_influencer_outfits_stats
    AFTER INSERT OR DELETE ON public.influencer_outfits
    FOR EACH ROW EXECUTE FUNCTION update_influencer_outfit_stats();

-- Update follower counts
CREATE OR REPLACE FUNCTION update_influencer_follower_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE public.influencers 
        SET followers_count = followers_count + 1,
            updated_at = NOW()
        WHERE id = NEW.influencer_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE public.influencers 
        SET followers_count = GREATEST(followers_count - 1, 0),
            updated_at = NOW()
        WHERE id = OLD.influencer_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_influencer_followers_stats
    AFTER INSERT OR DELETE ON public.influencer_followers
    FOR EACH ROW EXECUTE FUNCTION update_influencer_follower_stats();

-- Update outfit like counts
CREATE OR REPLACE FUNCTION update_outfit_like_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE public.influencer_outfits 
        SET like_count = like_count + 1,
            updated_at = NOW()
        WHERE id = NEW.outfit_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE public.influencer_outfits 
        SET like_count = GREATEST(like_count - 1, 0),
            updated_at = NOW()
        WHERE id = OLD.outfit_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_influencer_outfit_likes_stats
    AFTER INSERT OR DELETE ON public.influencer_outfit_likes
    FOR EACH ROW EXECUTE FUNCTION update_outfit_like_stats();

-- Update outfit save counts
CREATE OR REPLACE FUNCTION update_outfit_save_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE public.influencer_outfits 
        SET save_count = save_count + 1,
            updated_at = NOW()
        WHERE id = NEW.outfit_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE public.influencer_outfits 
        SET save_count = GREATEST(save_count - 1, 0),
            updated_at = NOW()
        WHERE id = OLD.outfit_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_influencer_outfit_saves_stats
    AFTER INSERT OR DELETE ON public.influencer_outfit_saves
    FOR EACH ROW EXECUTE FUNCTION update_outfit_save_stats();

-- ── Seed Sample Influencer Tiers ─────────────────────────────────────
-- These are just reference data, actual influencers will be created via API

COMMENT ON TABLE public.influencers IS 'Influencer profiles with stats and commission settings';
COMMENT ON TABLE public.influencer_outfits IS 'Outfit collections created by influencers';
COMMENT ON TABLE public.affiliate_links IS 'Trackable affiliate links for products';
COMMENT ON TABLE public.commission_records IS 'Commission earnings from affiliate sales';
COMMENT ON TABLE public.influencer_followers IS 'User follows for influencers';
COMMENT ON TABLE public.affiliate_clicks IS 'Click tracking for affiliate attribution';
COMMENT ON TABLE public.influencer_recommendations IS 'Product recommendations by influencers';
