-- ============================================================
-- CONFIT — Supabase Initial Schema Migration
-- Created: 2026-02-24
-- Description: Digital Twin, Smart Mirror/QR, and Gamification
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── User Roles ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.user_roles (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role        TEXT NOT NULL DEFAULT 'user'
                    CHECK (role IN ('admin', 'brand_manager', 'stylist', 'user')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON public.user_roles(user_id);

-- RLS
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own role"
    ON public.user_roles FOR SELECT
    USING (auth.uid() = user_id);

-- ── Digital Twins ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.digital_twins (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    reference_images JSONB NOT NULL DEFAULT '[]',
    twin_image_url   TEXT,
    skin_undertone   TEXT CHECK (skin_undertone IN ('warm', 'cool', 'neutral')),
    environment      TEXT NOT NULL DEFAULT 'studio'
                         CHECK (environment IN ('beach', 'office', 'evening', 'street', 'studio')),
    status           TEXT NOT NULL DEFAULT 'pending'
                         CHECK (status IN ('pending', 'processing', 'complete', 'failed')),
    meta             JSONB NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_digital_twins_user_id ON public.digital_twins(user_id);

ALTER TABLE public.digital_twins ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own digital twins"
    ON public.digital_twins FOR ALL
    USING (auth.uid() = user_id);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_digital_twins_updated_at
    BEFORE UPDATE ON public.digital_twins
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ── QR Scan Sessions ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.qr_scan_sessions (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    product_sku  TEXT NOT NULL,
    store_id     UUID,                          -- nullable: may be scanned outside a known store
    product_data JSONB NOT NULL DEFAULT '{}',
    scanned_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_qr_scan_sessions_user_id   ON public.qr_scan_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_qr_scan_sessions_scanned_at ON public.qr_scan_sessions(scanned_at DESC);

ALTER TABLE public.qr_scan_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own qr scans"
    ON public.qr_scan_sessions FOR ALL
    USING (auth.uid() = user_id);

-- ── Quests ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.quests (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    type            TEXT NOT NULL DEFAULT 'daily'
                        CHECK (type IN ('daily', 'weekly', 'milestone')),
    reward_points   INT NOT NULL DEFAULT 100,
    reward_badge    TEXT,
    icon            TEXT NOT NULL DEFAULT '⭐',
    constraint_json JSONB NOT NULL DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed default quests
INSERT INTO public.quests (title, description, type, reward_points, reward_badge, icon, constraint_json)
VALUES
    ('First Look',        'Create your first outfit in the Outfit Builder.',             'milestone', 150, 'creator',       '✨', '{}'),
    ('Mindful Monday',    'Style a complete look using only items in your wardrobe.',    'weekly',    200, 'sustainista',   '♻️', '{"wardrobe_only": true}'),
    ('Budget Stylist',    'Build a full outfit under $100.',                             'daily',     100,  NULL,           '💸', '{"max_budget": 100}'),
    ('AI Explorer',       'Use the Virtual Try-On feature for the first time.',          'milestone', 250, 'early_adopter', '🤖', '{}'),
    ('Rainy Day Edit',    'Style a look for a rainy day under $150.',                   'daily',     120,  NULL,           '🌧️', '{"max_budget": 150, "occasion": "casual"}'),
    ('Digital Twin Debut','Generate your first Digital Twin.',                           'milestone', 300, 'trendsetter',   '🪞', '{}'),
    ('Store Scout',       'Scan a QR code in a physical store.',                        'milestone', 200, 'explorer',      '📱', '{}'),
    ('Style Streak',      'Log an outfit 7 days in a row.',                             'weekly',    500, 'streak_master', '🔥', '{"days": 7}')
ON CONFLICT DO NOTHING;

-- ── Quest Completions ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.quest_completions (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    quest_id      UUID NOT NULL REFERENCES public.quests(id) ON DELETE CASCADE,
    points_earned INT NOT NULL DEFAULT 0,
    completed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, quest_id)              -- one completion per quest per user
);

CREATE INDEX IF NOT EXISTS idx_quest_completions_user_id  ON public.quest_completions(user_id);
CREATE INDEX IF NOT EXISTS idx_quest_completions_quest_id ON public.quest_completions(quest_id);

ALTER TABLE public.quest_completions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own completions"
    ON public.quest_completions FOR ALL
    USING (auth.uid() = user_id);

-- ── User Gamification ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.user_gamification (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    total_points     INT NOT NULL DEFAULT 0,
    confidence_score NUMERIC(4, 1) NOT NULL DEFAULT 0.0,
    level            INT NOT NULL DEFAULT 1,
    badges           JSONB NOT NULL DEFAULT '[]',
    current_streak   INT NOT NULL DEFAULT 0,
    longest_streak   INT NOT NULL DEFAULT 0,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_gamification_user_id      ON public.user_gamification(user_id);
CREATE INDEX IF NOT EXISTS idx_user_gamification_total_points ON public.user_gamification(total_points DESC);

ALTER TABLE public.user_gamification ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own gamification"
    ON public.user_gamification FOR SELECT
    USING (auth.uid() = user_id);
CREATE POLICY "Users can update own gamification"
    ON public.user_gamification FOR UPDATE
    USING (auth.uid() = user_id);

CREATE TRIGGER trg_user_gamification_updated_at
    BEFORE UPDATE ON public.user_gamification
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
