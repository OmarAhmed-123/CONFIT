-- ============================================================
-- CONFIT — Smart Closet Planner Migration
-- Created: 2026-03-25
-- Description: Weekly outfit planning with weather and calendar
-- ============================================================

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Closet Plans ────────────────────────────────────────────────────
-- Weekly outfit plans for users
CREATE TABLE IF NOT EXISTS public.closet_plans (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Plan period
    week_start_date DATE NOT NULL,
    week_end_date   DATE NOT NULL,
    
    -- Plan metadata
    plan_name       TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_template     BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Generation context
    generation_context JSONB NOT NULL DEFAULT '{}',
    -- Contains: weather_forecast, calendar_events, style_preferences_snapshot
    
    -- Statistics
    total_outfits   INTEGER NOT NULL DEFAULT 0,
    days_planned    INTEGER NOT NULL DEFAULT 0,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- One active plan per week per user
    UNIQUE (user_id, week_start_date)
);

CREATE INDEX IF NOT EXISTS idx_closet_plans_user_id ON public.closet_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_closet_plans_week_start ON public.closet_plans(week_start_date);
CREATE INDEX IF NOT EXISTS idx_closet_plans_active ON public.closet_plans(user_id, is_active) WHERE is_active = TRUE;

ALTER TABLE public.closet_plans ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own closet plans"
    ON public.closet_plans FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY "Users can read own closet plans"
    ON public.closet_plans FOR SELECT
    USING (auth.uid() = user_id);

-- ── Daily Outfits ────────────────────────────────────────────────────
-- Individual day outfit assignments
CREATE TABLE IF NOT EXISTS public.daily_outfits (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_id         UUID NOT NULL REFERENCES public.closet_plans(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Day information
    plan_date      DATE NOT NULL,
    day_of_week    SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    
    -- Outfit details
    outfit_id      UUID REFERENCES public.outfits(id) ON DELETE SET NULL,
    outfit_data    JSONB NOT NULL DEFAULT '{}',
    -- Contains: items (array with id, name, category, color, image_url), title, occasion
    
    -- Weather context
    weather_data   JSONB DEFAULT '{}',
    -- Contains: temp_high, temp_low, condition, precipitation, humidity, wind
    
    -- Calendar context
    calendar_events JSONB DEFAULT '[]',
    -- Array of events: [{id, title, time, type, location, dress_code}]
    
    -- Occasion
    primary_occasion TEXT,
    occasion_confidence NUMERIC(3,2) DEFAULT 0.0,
    
    -- Alternatives
    alternative_outfits JSONB DEFAULT '[]',
    -- Array of alternative outfit suggestions
    
    -- Status
    status         TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'worn', 'skipped', 'modified')),
    worn_at        TIMESTAMPTZ,
    
    -- User feedback
    user_rating    SMALLINT CHECK (user_rating BETWEEN 1 AND 5),
    user_notes     TEXT,
    
    -- Style matching
    style_match_score NUMERIC(3,2),
    weather_match_score NUMERIC(3,2),
    occasion_match_score NUMERIC(3,2),
    overall_score NUMERIC(3,2),
    
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE (plan_id, plan_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_outfits_plan_id ON public.daily_outfits(plan_id);
CREATE INDEX IF NOT EXISTS idx_daily_outfits_user_id ON public.daily_outfits(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_outfits_date ON public.daily_outfits(plan_date);
CREATE INDEX IF NOT EXISTS idx_daily_outfits_status ON public.daily_outfits(status);

ALTER TABLE public.daily_outfits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own daily outfits"
    ON public.daily_outfits FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY "Users can read own daily outfits"
    ON public.daily_outfits FOR SELECT
    USING (auth.uid() = user_id);

-- ── Outfit History ────────────────────────────────────────────────────
-- Track what was actually worn vs planned
CREATE TABLE IF NOT EXISTS public.outfit_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Reference
    daily_outfit_id UUID REFERENCES public.daily_outfits(id) ON DELETE SET NULL,
    plan_id         UUID REFERENCES public.closet_plans(id) ON DELETE SET NULL,
    
    -- What was worn
    worn_date       DATE NOT NULL,
    planned_outfit  JSONB,
    actual_outfit   JSONB,
    
    -- Deviation tracking
    deviation_type TEXT CHECK (deviation_type IN ('none', 'minor', 'major', 'completely_different')),
    deviation_reason TEXT,
    
    -- Context
    weather_actual JSONB,
    events_actual JSONB DEFAULT '[]',
    
    -- Feedback
    satisfaction_score SMALLINT CHECK (satisfaction_score BETWEEN 1 AND 5),
    would_wear_again BOOLEAN,
    notes TEXT,
    
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outfit_history_user_id ON public.outfit_history(user_id);
CREATE INDEX IF NOT EXISTS idx_outfit_history_date ON public.outfit_history(worn_date);
CREATE INDEX IF NOT EXISTS idx_outfit_history_daily ON public.outfit_history(daily_outfit_id);

ALTER TABLE public.outfit_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own outfit history"
    ON public.outfit_history FOR ALL
    USING (auth.uid() = user_id);

-- ── Weather Cache ────────────────────────────────────────────────────
-- Cache weather data to reduce API calls
CREATE TABLE IF NOT EXISTS public.weather_cache (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location_key    TEXT NOT NULL,  -- city or coordinates
    forecast_date   DATE NOT NULL,
    
    -- Weather data
    weather_data    JSONB NOT NULL,
    -- Contains: temp_high, temp_low, condition, precipitation, humidity, wind, uv_index, feels_like
    
    -- Metadata
    source          TEXT NOT NULL DEFAULT 'openweathermap',
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,
    
    UNIQUE (location_key, forecast_date)
);

CREATE INDEX IF NOT EXISTS idx_weather_cache_location ON public.weather_cache(location_key);
CREATE INDEX IF NOT EXISTS idx_weather_cache_date ON public.weather_cache(forecast_date);
CREATE INDEX IF NOT EXISTS idx_weather_cache_expires ON public.weather_cache(expires_at);

-- ── Calendar Events Cache ─────────────────────────────────────────────
-- Cache calendar events for planning
CREATE TABLE IF NOT EXISTS public.calendar_events_cache (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Event details
    external_id     TEXT NOT NULL,  -- ID from calendar provider
    provider        TEXT NOT NULL CHECK (provider IN ('google', 'apple', 'outlook', 'manual')),
    
    -- Event data
    event_title     TEXT NOT NULL,
    event_date      DATE NOT NULL,
    event_time      TIME,
    event_end_time  TIME,
    location        TEXT,
    description     TEXT,
    
    -- Planning context
    dress_code      TEXT,
    event_type      TEXT,  -- meeting, party, casual, formal, etc.
    importance      SMALLINT DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
    
    -- Metadata
    raw_event_data  JSONB,
    synced_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE (user_id, external_id, event_date)
);

CREATE INDEX IF NOT EXISTS idx_calendar_events_user ON public.calendar_events_cache(user_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_date ON public.calendar_events_cache(event_date);
CREATE INDEX IF NOT EXISTS idx_calendar_events_provider ON public.calendar_events_cache(provider);

ALTER TABLE public.calendar_events_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own calendar events"
    ON public.calendar_events_cache FOR ALL
    USING (auth.uid() = user_id);

-- ── Planner Preferences ───────────────────────────────────────────────
-- User preferences for outfit planning
CREATE TABLE IF NOT EXISTS public.planner_preferences (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Planning behavior
    planning_day    SMALLINT DEFAULT 0 CHECK (planning_day BETWEEN 0 AND 6),  -- 0 = Sunday
    planning_time   TIME DEFAULT '20:00:00',
    auto_generate    BOOLEAN DEFAULT TRUE,
    
    -- Weather preferences
    location         JSONB DEFAULT '{}',  -- {city, country, lat, lng}
    temperature_unit TEXT DEFAULT 'celsius' CHECK (temperature_unit IN ('celsius', 'fahrenheit')),
    weather_sensitivity JSONB DEFAULT '{}',  -- adjustments for weather conditions
    
    -- Calendar integration
    calendar_providers JSONB DEFAULT '[]',  -- enabled providers
    default_event_occasion_map JSONB DEFAULT '{}',  -- event type -> occasion mapping
    
    -- Style preferences for planning
    prefer_favorite_items BOOLEAN DEFAULT TRUE,
    avoid_recently_worn   BOOLEAN DEFAULT TRUE,
    recently_worn_days    SMALLINT DEFAULT 7,
    max_item_frequency    SMALLINT DEFAULT 2,  -- max times per week
    
    -- Occasion priorities
    occasion_priorities JSONB DEFAULT '{}',
    
    -- Notifications
    notify_new_plan    BOOLEAN DEFAULT TRUE,
    notify_daily       BOOLEAN DEFAULT TRUE,
    notify_daily_time  TIME DEFAULT '07:00:00',
    
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.planner_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own planner preferences"
    ON public.planner_preferences FOR ALL
    USING (auth.uid() = user_id);

-- ── Auto-update triggers ───────────────────────────────────────────────
CREATE TRIGGER trg_closet_plans_updated_at
    BEFORE UPDATE ON public.closet_plans
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_daily_outfits_updated_at
    BEFORE UPDATE ON public.daily_outfits
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_planner_preferences_updated_at
    BEFORE UPDATE ON public.planner_preferences
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ── Helper Functions ───────────────────────────────────────────────────

-- Get or create planner preferences
CREATE OR REPLACE FUNCTION public.get_or_create_planner_preferences(p_user_id UUID)
RETURNS UUID AS $$
DECLARE
    v_pref_id UUID;
BEGIN
    SELECT id INTO v_pref_id FROM public.planner_preferences WHERE user_id = p_user_id;
    
    IF v_pref_id IS NULL THEN
        INSERT INTO public.planner_preferences (user_id)
        VALUES (p_user_id)
        RETURNING id INTO v_pref_id;
    END IF;
    
    RETURN v_pref_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get current week's plan
CREATE OR REPLACE FUNCTION public.get_current_week_plan(p_user_id UUID)
RETURNS TABLE (
    plan_id UUID,
    week_start DATE,
    week_end DATE,
    daily_outfits JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cp.id,
        cp.week_start_date,
        cp.week_end_date,
        jsonb_agg(
            jsonb_build_object(
                'date', do2.plan_date,
                'day_of_week', do2.day_of_week,
                'outfit', do2.outfit_data,
                'weather', do2.weather_data,
                'events', do2.calendar_events,
                'status', do2.status,
                'alternatives', do2.alternative_outfits
            )
            ORDER BY do2.plan_date
        ) as daily_outfits
    FROM public.closet_plans cp
    LEFT JOIN public.daily_outfits do2 ON cp.id = do2.plan_id
    WHERE cp.user_id = p_user_id
      AND cp.week_start_date <= CURRENT_DATE
      AND cp.week_end_date >= CURRENT_DATE
      AND cp.is_active = TRUE
    GROUP BY cp.id, cp.week_start_date, cp.week_end_date;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ── Seed default planner preferences ───────────────────────────────────
-- No seeding needed, created on demand

-- ── Comments ───────────────────────────────────────────────────────────
COMMENT ON TABLE public.closet_plans IS 'Weekly outfit plans generated by the Smart Closet Planner';
COMMENT ON TABLE public.daily_outfits IS 'Individual day outfit assignments within a weekly plan';
COMMENT ON TABLE public.outfit_history IS 'History of what was actually worn vs planned';
COMMENT ON TABLE public.weather_cache IS 'Cached weather forecasts to reduce API calls';
COMMENT ON TABLE public.calendar_events_cache IS 'Cached calendar events from external providers';
COMMENT ON TABLE public.planner_preferences IS 'User preferences for outfit planning behavior';
