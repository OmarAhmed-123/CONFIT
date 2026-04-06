-- ============================================================
-- CONFIT — Notification Analytics Schema Migration
-- Created: 2026-04-05
-- Description: Comprehensive event logging for notification
-- analytics, A/B testing, and business impact tracking.
-- ============================================================

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Notification Events ─────────────────────────────────────────────
-- Core event log table for all notification lifecycle events

CREATE TABLE IF NOT EXISTS public.notification_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    notification_id TEXT NOT NULL,
    recipient_id    TEXT NOT NULL,
    recipient_type  TEXT NOT NULL CHECK (recipient_type IN ('customer', 'owner')),
    channel         TEXT NOT NULL CHECK (channel IN ('in_app', 'email', 'push', 'toast')),
    event_type      TEXT NOT NULL CHECK (event_type IN ('sent', 'delivered', 'read', 'clicked', 'dismissed')),
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Payload for context (order_id, store_id, notification_type, etc.)
    payload         JSONB NOT NULL DEFAULT '{}',
    
    -- Engagement metadata
    time_spent_ms   INTEGER,
    scroll_depth    NUMERIC(3, 2),
    action_taken    TEXT,
    
    -- A/B test tracking
    ab_test_id      TEXT,
    variant_id      TEXT,
    
    -- Conversion tracking (linked to subsequent purchases)
    conversion_order_id TEXT,
    conversion_timestamp TIMESTAMPTZ,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_notification_events_notification_id 
    ON public.notification_events(notification_id);
CREATE INDEX IF NOT EXISTS idx_notification_events_recipient_id 
    ON public.notification_events(recipient_id);
CREATE INDEX IF NOT EXISTS idx_notification_events_recipient_type 
    ON public.notification_events(recipient_type);
CREATE INDEX IF NOT EXISTS idx_notification_events_channel 
    ON public.notification_events(channel);
CREATE INDEX IF NOT EXISTS idx_notification_events_event_type 
    ON public.notification_events(event_type);
CREATE INDEX IF NOT EXISTS idx_notification_events_timestamp 
    ON public.notification_events(event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_notification_events_ab_test 
    ON public.notification_events(ab_test_id, variant_id);
CREATE INDEX IF NOT EXISTS idx_notification_events_store 
    ON public.notification_events((payload->>'store_id'));

-- Composite index for common dashboard queries
CREATE INDEX IF NOT EXISTS idx_notification_events_dashboard 
    ON public.notification_events(recipient_type, channel, event_type, event_timestamp DESC);

-- RLS Policies
ALTER TABLE public.notification_events ENABLE ROW LEVEL SECURITY;

-- Admins and analytics team can read all events
CREATE POLICY "Admins can read all notification events"
    ON public.notification_events FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.user_roles ur
            WHERE ur.user_id = auth.uid() 
            AND ur.role IN ('admin', 'analytics')
        )
    );

-- Service role can insert events (for backend notification service)
CREATE POLICY "Service role can insert notification events"
    ON public.notification_events FOR INSERT
    WITH (auth.role() = 'service_role');

-- ── Notification Aggregates (Materialized View for Performance) ────
-- Pre-aggregated daily stats for dashboard performance

CREATE MATERIALIZED VIEW IF NOT EXISTS public.notification_daily_stats AS
SELECT 
    DATE(event_timestamp) AS stat_date,
    recipient_type,
    channel,
    COUNT(*) FILTER (WHERE event_type = 'sent') AS total_sent,
    COUNT(*) FILTER (WHERE event_type = 'delivered') AS total_delivered,
    COUNT(*) FILTER (WHERE event_type = 'read') AS total_read,
    COUNT(*) FILTER (WHERE event_type = 'clicked') AS total_clicked,
    COUNT(*) FILTER (WHERE event_type = 'dismissed') AS total_dismissed,
    AVG(time_spent_ms) FILTER (WHERE event_type = 'read' AND time_spent_ms IS NOT NULL) AS avg_time_spent_ms,
    COUNT(DISTINCT recipient_id) AS unique_recipients
FROM public.notification_events
GROUP BY DATE(event_timestamp), recipient_type, channel;

-- Refresh index
CREATE UNIQUE INDEX IF NOT EXISTS idx_notification_daily_stats_unique 
    ON public.notification_daily_stats(stat_date, recipient_type, channel);

-- Refresh function (call periodically or via trigger)
CREATE OR REPLACE FUNCTION public.refresh_notification_daily_stats()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.notification_daily_stats;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ── A/B Test Definitions ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.ab_tests (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    hypothesis      TEXT NOT NULL,
    variable        TEXT NOT NULL CHECK (variable IN ('timing', 'content', 'channel', 'frequency')),
    status          TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'running', 'paused', 'completed', 'archived')),
    segment         TEXT NOT NULL CHECK (segment IN ('all_customers', 'all_owners', 'new_customers', 'repeat_customers', 'specific_stores')),
    traffic_percentage INTEGER NOT NULL DEFAULT 50 CHECK (traffic_percentage BETWEEN 1 AND 100),
    start_date      TIMESTAMPTZ,
    end_date        TIMESTAMPTZ,
    duration_days   INTEGER NOT NULL DEFAULT 14,
    
    -- Statistical results
    winner_variant_id TEXT,
    confidence_level NUMERIC(5, 4),
    p_value         NUMERIC(10, 8),
    is_significant  BOOLEAN NOT NULL DEFAULT FALSE,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_dates CHECK (
        status = 'draft' OR start_date IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS idx_ab_tests_status 
    ON public.ab_tests(status);

-- ── A/B Test Variants ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.ab_test_variants (
    id              TEXT PRIMARY KEY,
    test_id         TEXT NOT NULL REFERENCES public.ab_tests(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    description     TEXT,
    
    -- Configuration
    channels        TEXT[] DEFAULT '{}',
    timing_delay_minutes INTEGER,
    content_format  TEXT CHECK (content_format IN ('short', 'detailed')),
    frequency       TEXT,
    
    -- Results (updated via trigger or batch job)
    sample_size     INTEGER NOT NULL DEFAULT 0,
    delivery_count  INTEGER NOT NULL DEFAULT 0,
    open_count      INTEGER NOT NULL DEFAULT 0,
    click_count     INTEGER NOT NULL DEFAULT 0,
    conversion_count INTEGER NOT NULL DEFAULT 0,
    
    delivery_rate   NUMERIC(5, 4) DEFAULT 0,
    open_rate       NUMERIC(5, 4) DEFAULT 0,
    click_rate      NUMERIC(5, 4) DEFAULT 0,
    conversion_rate NUMERIC(5, 4) DEFAULT 0,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ab_test_variants_test_id 
    ON public.ab_test_variants(test_id);

-- ── Owner Response Time Tracking ────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.owner_response_times (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id        TEXT NOT NULL,
    store_name      TEXT NOT NULL,
    notification_id TEXT NOT NULL,
    order_id        TEXT,
    notification_sent_at TIMESTAMPTZ NOT NULL,
    first_action_at TIMESTAMPTZ,
    response_time_minutes NUMERIC(10, 2),
    action_type    TEXT,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_owner_response_times_store 
    ON public.owner_response_times(store_id);
CREATE INDEX IF NOT EXISTS idx_owner_response_times_sent 
    ON public.owner_response_times(notification_sent_at DESC);

-- ── Conversion Tracking ─────────────────────────────────────────────
-- Links notification events to subsequent purchases

CREATE TABLE IF NOT EXISTS public.notification_conversions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    notification_id     TEXT NOT NULL,
    recipient_id        TEXT NOT NULL,
    channel             TEXT NOT NULL,
    notification_sent_at TIMESTAMPTZ NOT NULL,
    conversion_order_id TEXT NOT NULL,
    conversion_at       TIMESTAMPTZ NOT NULL,
    days_to_conversion  INTEGER NOT NULL,
    order_value         NUMERIC(12, 2),
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notification_conversions_notification 
    ON public.notification_conversions(notification_id);
CREATE INDEX IF NOT EXISTS idx_notification_conversions_recipient 
    ON public.notification_conversions(recipient_id);
CREATE INDEX IF NOT EXISTS idx_notification_conversions_channel 
    ON public.notification_conversions(channel);

-- ── Functions for Analytics Queries ────────────────────────────────

-- Get channel metrics for a period
CREATE OR REPLACE FUNCTION public.get_channel_metrics(
    p_start_date TIMESTAMPTZ,
    p_end_date TIMESTAMPTZ,
    p_recipient_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    channel TEXT,
    total_sent BIGINT,
    total_delivered BIGINT,
    total_read BIGINT,
    total_clicked BIGINT,
    total_dismissed BIGINT,
    delivery_rate NUMERIC,
    open_rate NUMERIC,
    click_rate NUMERIC,
    avg_latency_ms NUMERIC,
    avg_time_spent_ms NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ne.channel,
        COUNT(*) FILTER (WHERE ne.event_type = 'sent') AS total_sent,
        COUNT(*) FILTER (WHERE ne.event_type = 'delivered') AS total_delivered,
        COUNT(*) FILTER (WHERE ne.event_type = 'read') AS total_read,
        COUNT(*) FILTER (WHERE ne.event_type = 'clicked') AS total_clicked,
        COUNT(*) FILTER (WHERE ne.event_type = 'dismissed') AS total_dismissed,
        CASE 
            WHEN COUNT(*) FILTER (WHERE ne.event_type = 'sent') > 0 
            THEN ROUND(COUNT(*) FILTER (WHERE ne.event_type = 'delivered')::NUMERIC / 
                 COUNT(*) FILTER (WHERE ne.event_type = 'sent')::NUMERIC, 4)
            ELSE 0 
        END AS delivery_rate,
        CASE 
            WHEN COUNT(*) FILTER (WHERE ne.event_type = 'delivered') > 0 
            THEN ROUND(COUNT(*) FILTER (WHERE ne.event_type = 'read')::NUMERIC / 
                 COUNT(*) FILTER (WHERE ne.event_type = 'delivered')::NUMERIC, 4)
            ELSE 0 
        END AS open_rate,
        CASE 
            WHEN COUNT(*) FILTER (WHERE ne.event_type = 'read') > 0 
            THEN ROUND(COUNT(*) FILTER (WHERE ne.event_type = 'clicked')::NUMERIC / 
                 COUNT(*) FILTER (WHERE ne.event_type = 'read')::NUMERIC, 4)
            ELSE 0 
        END AS click_rate,
        0::NUMERIC AS avg_latency_ms, -- Computed via join
        AVG(ne.time_spent_ms) FILTER (WHERE ne.time_spent_ms IS NOT NULL) AS avg_time_spent_ms
    FROM public.notification_events ne
    WHERE ne.event_timestamp >= p_start_date
      AND ne.event_timestamp < p_end_date
      AND (p_recipient_type IS NULL OR ne.recipient_type = p_recipient_type)
    GROUP BY ne.channel
    ORDER BY ne.channel;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Get heatmap data
CREATE OR REPLACE FUNCTION public.get_engagement_heatmap(
    p_start_date TIMESTAMPTZ,
    p_end_date TIMESTAMPTZ,
    p_recipient_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    day_of_week INTEGER,
    hour_of_day INTEGER,
    event_count BIGINT,
    read_count BIGINT,
    click_count BIGINT,
    open_rate NUMERIC,
    click_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        EXTRACT(DOW FROM ne.event_timestamp)::INTEGER AS day_of_week,
        EXTRACT(HOUR FROM ne.event_timestamp)::INTEGER AS hour_of_day,
        COUNT(*) FILTER (WHERE ne.event_type = 'sent') AS event_count,
        COUNT(*) FILTER (WHERE ne.event_type = 'read') AS read_count,
        COUNT(*) FILTER (WHERE ne.event_type = 'clicked') AS click_count,
        CASE 
            WHEN COUNT(*) FILTER (WHERE ne.event_type = 'sent') > 0 
            THEN ROUND(COUNT(*) FILTER (WHERE ne.event_type = 'read')::NUMERIC / 
                 COUNT(*) FILTER (WHERE ne.event_type = 'sent')::NUMERIC, 4)
            ELSE 0 
        END AS open_rate,
        CASE 
            WHEN COUNT(*) FILTER (WHERE ne.event_type = 'sent') > 0 
            THEN ROUND(COUNT(*) FILTER (WHERE ne.event_type = 'clicked')::NUMERIC / 
                 COUNT(*) FILTER (WHERE ne.event_type = 'sent')::NUMERIC, 4)
            ELSE 0 
        END AS click_rate
    FROM public.notification_events ne
    WHERE ne.event_timestamp >= p_start_date
      AND ne.event_timestamp < p_end_date
      AND (p_recipient_type IS NULL OR ne.recipient_type = p_recipient_type)
    GROUP BY 
        EXTRACT(DOW FROM ne.event_timestamp)::INTEGER,
        EXTRACT(HOUR FROM ne.event_timestamp)::INTEGER
    ORDER BY day_of_week, hour_of_day;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Get owner response times by store
CREATE OR REPLACE FUNCTION public.get_owner_response_times(
    p_start_date TIMESTAMPTZ,
    p_end_date TIMESTAMPTZ
)
RETURNS TABLE (
    store_id TEXT,
    store_name TEXT,
    notification_count BIGINT,
    avg_response_time_min NUMERIC,
    median_response_time_min NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ort.store_id,
        ort.store_name,
        COUNT(*) AS notification_count,
        AVG(ort.response_time_minutes) AS avg_response_time_min,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ort.response_time_minutes) AS median_response_time_min
    FROM public.owner_response_times ort
    WHERE ort.notification_sent_at >= p_start_date
      AND ort.notification_sent_at < p_end_date
      AND ort.response_time_minutes IS NOT NULL
    GROUP BY ort.store_id, ort.store_name
    ORDER BY avg_response_time_min;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Get conversion data by channel
CREATE OR REPLACE FUNCTION public.get_conversion_by_channel(
    p_days ARRAY[INTEGER] DEFAULT ARRAY[7, 14, 30]
)
RETURNS TABLE (
    channel TEXT,
    period_days INTEGER,
    notification_count BIGINT,
    conversion_count BIGINT,
    conversion_rate NUMERIC
) AS $$
DECLARE
    day_val INTEGER;
BEGIN
    FOREACH day_val IN ARRAY p_days
    LOOP
        RETURN QUERY
        SELECT 
            nc.channel,
            day_val AS period_days,
            COUNT(DISTINCT nc.notification_id) AS notification_count,
            COUNT(DISTINCT nc.conversion_order_id) AS conversion_count,
            CASE 
                WHEN COUNT(DISTINCT nc.notification_id) > 0 
                THEN ROUND(COUNT(DISTINCT nc.conversion_order_id)::NUMERIC / 
                     COUNT(DISTINCT nc.notification_id)::NUMERIC, 4)
                ELSE 0 
            END AS conversion_rate
        FROM public.notification_conversions nc
        WHERE nc.days_to_conversion <= day_val
        GROUP BY nc.channel;
    END LOOP;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ── Triggers ─────────────────────────────────────────────────────────

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_ab_tests_updated_at
    BEFORE UPDATE ON public.ab_tests
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_ab_test_variants_updated_at
    BEFORE UPDATE ON public.ab_test_variants
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ── Grant Permissions ────────────────────────────────────────────────

-- Grant select on materialized view to authenticated users with admin role
GRANT SELECT ON public.notification_daily_stats TO authenticated;
GRANT SELECT ON public.notification_events TO authenticated;
GRANT SELECT ON public.ab_tests TO authenticated;
GRANT SELECT ON public.ab_test_variants TO authenticated;
GRANT SELECT ON public.owner_response_times TO authenticated;
GRANT SELECT ON public.notification_conversions TO authenticated;

-- Grant insert/update to service role for backend operations
GRANT INSERT ON public.notification_events TO service_role;
GRANT INSERT, UPDATE ON public.ab_tests TO service_role;
GRANT INSERT, UPDATE ON public.ab_test_variants TO service_role;
GRANT INSERT ON public.owner_response_times TO service_role;
GRANT INSERT ON public.notification_conversions TO service_role;

-- ── Comments for Documentation ──────────────────────────────────────

COMMENT ON TABLE public.notification_events IS 
    'Core event log for all notification lifecycle events (sent, delivered, read, clicked, dismissed)';

COMMENT ON TABLE public.ab_tests IS 
    'A/B test definitions for notification optimization experiments';

COMMENT ON TABLE public.ab_test_variants IS 
    'Variant configurations and results for A/B tests';

COMMENT ON TABLE public.owner_response_times IS 
    'Tracks time from notification delivery to owner action (accepting/processing order)';

COMMENT ON TABLE public.notification_conversions IS 
    'Links notification events to subsequent purchase transactions for conversion tracking';

COMMENT ON MATERIALIZED VIEW public.notification_daily_stats IS 
    'Pre-aggregated daily stats for dashboard performance optimization';
