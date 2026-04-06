-- ============================================================
-- CONFIT — Preference Analytics & Recommendation System
-- Created: 2026-04-07
-- Description: Intelligent preference analytics, pattern detection,
--              engagement correlation, personalized recommendations,
--              and A/B testing framework for notification optimization
-- ============================================================

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ═══════════════════════════════════════════════════════════════════
-- PREFERENCE HISTORY TABLE
-- Tracks all preference configuration changes with full context
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.preference_history (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_id        TEXT NOT NULL,
    recipient_type      TEXT NOT NULL CHECK (recipient_type IN ('customer', 'owner')),
    
    -- What changed
    change_category     TEXT NOT NULL CHECK (change_category IN (
        'channel_toggle', 'frequency_adjustment', 'type_selection', 
        'batch_settings', 'global_toggle', 'full_config'
    )),
    field_path          TEXT NOT NULL,                    -- e.g., "channels.email.enabled"
    old_value           JSONB,
    new_value           JSONB,
    
    -- Full state snapshots for pattern analysis
    previous_state      JSONB NOT NULL,                   -- Complete preference state before change
    new_state           JSONB NOT NULL,                   -- Complete preference state after change
    
    -- Trigger context
    trigger_source      TEXT NOT NULL CHECK (trigger_source IN (
        'user_initiated', 'system_recommended', 'ab_test', 
        'onboarding_default', 'bulk_update', 'api_sync'
    )),
    recommendation_id   UUID,                             -- Link to recommendation if applicable
    ab_test_id          TEXT,                             -- Link to A/B test if applicable
    variant_id          TEXT,
    
    -- Device/session context
    device_id           TEXT,
    device_type         TEXT,
    session_id          TEXT,
    ip_address          INET,
    user_agent          TEXT,
    
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Retention
    retention_until     TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '3 years')
);

-- Indexes for pattern analysis queries
CREATE INDEX IF NOT EXISTS idx_preference_history_recipient 
    ON public.preference_history(recipient_id, recipient_type);
CREATE INDEX IF NOT EXISTS idx_preference_history_created 
    ON public.preference_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_preference_history_category 
    ON public.preference_history(change_category, recipient_type);
CREATE INDEX IF NOT EXISTS idx_preference_history_trigger 
    ON public.preference_history(trigger_source, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_preference_history_state 
    ON public.preference_history USING GIN (new_state);
CREATE INDEX IF NOT EXISTS idx_preference_history_retention 
    ON public.preference_history(retention_until);

-- ═══════════════════════════════════════════════════════════════════
-- ENGAGEMENT METRICS TABLE
-- Per-user engagement data by channel and frequency
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.engagement_metrics (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_id        TEXT NOT NULL,
    recipient_type      TEXT NOT NULL CHECK (recipient_type IN ('customer', 'owner')),
    
    -- Time period for metrics
    period_start        DATE NOT NULL,
    period_end          DATE NOT NULL,
    period_type         TEXT NOT NULL CHECK (period_type IN ('daily', 'weekly', 'monthly')),
    
    -- Channel-specific metrics
    -- Structure: { "in_app": { "sent": 10, "delivered": 9, "read": 7, "clicked": 3, "dismissed": 2 }, ... }
    channel_metrics     JSONB NOT NULL DEFAULT '{}',
    
    -- Aggregate metrics
    total_sent          INTEGER NOT NULL DEFAULT 0,
    total_delivered     INTEGER NOT NULL DEFAULT 0,
    total_read          INTEGER NOT NULL DEFAULT 0,
    total_clicked       INTEGER NOT NULL DEFAULT 0,
    total_dismissed     INTEGER NOT NULL DEFAULT 0,
    
    -- Calculated rates
    overall_open_rate   NUMERIC(5, 4) DEFAULT 0,          -- read / delivered
    overall_click_rate  NUMERIC(5, 4) DEFAULT 0,          -- clicked / read
    overall_ignore_rate NUMERIC(5, 4) DEFAULT 0,          -- dismissed / delivered
    
    -- Unsubscribe events
    unsubscribe_events  INTEGER NOT NULL DEFAULT 0,
    unsubscribe_channel TEXT,                             -- Which channel triggered unsubscribe
    
    -- Active preference snapshot at period start
    active_preferences  JSONB NOT NULL DEFAULT '{}',
    
    -- Engagement score (composite metric 0-100)
    engagement_score    NUMERIC(5, 2) DEFAULT 0,
    
    -- Timestamps
    calculated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(recipient_id, recipient_type, period_start, period_type)
);

-- Indexes for engagement analysis
CREATE INDEX IF NOT EXISTS idx_engagement_metrics_recipient 
    ON public.engagement_metrics(recipient_id, recipient_type);
CREATE INDEX IF NOT EXISTS idx_engagement_metrics_period 
    ON public.engagement_metrics(period_start DESC);
CREATE INDEX IF NOT EXISTS idx_engagement_metrics_type 
    ON public.engagement_metrics(recipient_type, period_type);
CREATE INDEX IF NOT EXISTS idx_engagement_metrics_score 
    ON public.engagement_metrics(engagement_score DESC);
CREATE INDEX IF NOT EXISTS idx_engagement_metrics_prefs 
    ON public.engagement_metrics USING GIN (active_preferences);
CREATE INDEX IF NOT EXISTS idx_engagement_metrics_unsub 
    ON public.engagement_metrics(unsubscribe_events) WHERE unsubscribe_events > 0;

-- ═══════════════════════════════════════════════════════════════════
-- USER COHORTS TABLE
-- Define cohorts based on shared preference patterns
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.user_cohorts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cohort_name         TEXT NOT NULL UNIQUE,
    cohort_slug         TEXT NOT NULL UNIQUE,              -- e.g., "weekly_digest_users"
    description         TEXT NOT NULL,
    
    -- Cohort definition (JSON query matching preference patterns)
    -- Example: { "email_frequency": "weekly_summary", "push_enabled": true }
    definition          JSONB NOT NULL,
    
    -- Cohort type
    cohort_type         TEXT NOT NULL CHECK (cohort_type IN (
        'frequency_pattern', 'channel_preference', 'notification_type',
        'engagement_level', 'behavioral', 'custom'
    )),
    recipient_type      TEXT CHECK (recipient_type IN ('customer', 'owner')),  -- NULL = both
    
    -- Statistics (updated periodically)
    member_count        INTEGER NOT NULL DEFAULT 0,
    avg_engagement_score NUMERIC(5, 2),
    avg_open_rate       NUMERIC(5, 4),
    avg_click_rate      NUMERIC(5, 4),
    avg_ignore_rate     NUMERIC(5, 4),
    
    -- Business outcomes (for owners)
    avg_response_time_hours NUMERIC(8, 2),
    avg_satisfaction_score  NUMERIC(3, 2),
    
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_computed_at    TIMESTAMPTZ
);

-- Predefined cohorts
INSERT INTO public.user_cohorts (cohort_name, cohort_slug, description, definition, cohort_type, recipient_type) VALUES
    ('Weekly Digest Users', 'weekly_digest_users', 'Users who receive weekly email digests instead of real-time', 
     '{"email_frequency": "weekly_summary"}', 'frequency_pattern', 'customer'),
    ('Real-Time Everything', 'real_time_everything', 'Users with all channels set to real-time', 
     '{"in_app_frequency": "real_time", "email_frequency": "real_time", "push_frequency": "real_time"}', 'frequency_pattern', NULL),
    ('Email-Only Customers', 'email_only_customers', 'Customers who disabled push and in-app, rely on email only',
     '{"push_enabled": false, "in_app_enabled": false, "email_enabled": true}', 'channel_preference', 'customer'),
    ('Batch Processing Owners', 'batch_processing_owners', 'Store owners who batch customer inquiries',
     '{"batch_settings": {"enabled": true}}', 'behavioral', 'owner'),
    ('High Engagers', 'high_engagers', 'Users with engagement score > 70',
     '{"engagement_score_min": 70}', 'engagement_level', NULL),
    ('Fatigue Risk', 'fatigue_risk', 'Users with ignore rate > 50% or recent unsubscribe',
     '{"ignore_rate_min": 0.5}', 'behavioral', NULL)
ON CONFLICT (cohort_slug) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_user_cohorts_slug 
    ON public.user_cohorts(cohort_slug);
CREATE INDEX IF NOT EXISTS idx_user_cohorts_type 
    ON public.user_cohorts(cohort_type, recipient_type);
CREATE INDEX IF NOT EXISTS idx_user_cohorts_definition 
    ON public.user_cohorts USING GIN (definition);

-- ═══════════════════════════════════════════════════════════════════
-- USER COHORT MEMBERSHIP TABLE
-- Track which users belong to which cohorts
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.user_cohort_membership (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cohort_id           UUID NOT NULL REFERENCES public.user_cohorts(id) ON DELETE CASCADE,
    recipient_id        TEXT NOT NULL,
    recipient_type      TEXT NOT NULL CHECK (recipient_type IN ('customer', 'owner')),
    
    -- Membership details
    joined_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    exited_at           TIMESTAMPTZ,                       -- NULL if still member
    
    -- User's metrics while in cohort (for cohort-level stats)
    engagement_score    NUMERIC(5, 2),
    open_rate           NUMERIC(5, 4),
    click_rate          NUMERIC(5, 4),
    
    -- Business metrics (for owners)
    response_time_hours NUMERIC(8, 2),
    satisfaction_score  NUMERIC(3, 2),
    
    UNIQUE(cohort_id, recipient_id, recipient_type, joined_at)
);

CREATE INDEX IF NOT EXISTS idx_user_cohort_membership_cohort 
    ON public.user_cohort_membership(cohort_id);
CREATE INDEX IF NOT EXISTS idx_user_cohort_membership_recipient 
    ON public.user_cohort_membership(recipient_id, recipient_type);
CREATE INDEX IF NOT EXISTS idx_user_cohort_membership_active 
    ON public.user_cohort_membership(cohort_id, recipient_id) WHERE exited_at IS NULL;

-- ═══════════════════════════════════════════════════════════════════
-- BUSINESS OUTCOMES TABLE (Store Owners Only)
-- Track business metrics linked to active preference configuration
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.business_outcomes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id            TEXT NOT NULL,
    store_id            TEXT NOT NULL,
    
    -- Time period
    period_start        DATE NOT NULL,
    period_end          DATE NOT NULL,
    period_type         TEXT NOT NULL CHECK (period_type IN ('daily', 'weekly', 'monthly')),
    
    -- Response time metrics
    avg_order_response_time_hours NUMERIC(8, 2),
    median_order_response_time_hours NUMERIC(8, 2),
    response_time_sla_met_pct NUMERIC(5, 2),              -- % of orders responded within SLA
    
    -- Customer satisfaction
    avg_satisfaction_score NUMERIC(3, 2),                 -- 1-5 scale
    satisfaction_responses INTEGER DEFAULT 0,
    
    -- Order processing efficiency
    orders_received     INTEGER NOT NULL DEFAULT 0,
    orders_processed    INTEGER NOT NULL DEFAULT 0,
    orders_cancelled    INTEGER NOT NULL DEFAULT 0,
    processing_rate     NUMERIC(5, 2),                    -- processed / received
    
    -- Notification action rates
    notification_action_rate NUMERIC(5, 4),               -- How often they act on notifications
    
    -- Active preferences during this period
    active_preferences  JSONB NOT NULL DEFAULT '{}',
    
    -- Batch vs real-time comparison
    batch_inquiries_pct NUMERIC(5, 2),                    -- % of inquiries received in batch
    
    -- Timestamps
    calculated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(owner_id, store_id, period_start, period_type)
);

CREATE INDEX IF NOT EXISTS idx_business_outcomes_owner 
    ON public.business_outcomes(owner_id);
CREATE INDEX IF NOT EXISTS idx_business_outcomes_store 
    ON public.business_outcomes(store_id);
CREATE INDEX IF NOT EXISTS idx_business_outcomes_period 
    ON public.business_outcomes(period_start DESC);
CREATE INDEX IF NOT EXISTS idx_business_outcomes_prefs 
    ON public.business_outcomes USING GIN (active_preferences);
CREATE INDEX IF NOT EXISTS idx_business_outcomes_satisfaction 
    ON public.business_outcomes(avg_satisfaction_score DESC) WHERE avg_satisfaction_score IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════════
-- RECOMMENDATIONS TABLE
-- Store generated recommendations with full context
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.preference_recommendations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_id        TEXT NOT NULL,
    recipient_type      TEXT NOT NULL CHECK (recipient_type IN ('customer', 'owner')),
    
    -- Recommendation details
    recommendation_type TEXT NOT NULL CHECK (recommendation_type IN (
        'frequency_optimization', 'channel_optimization', 
        'fatigue_prevention', 'engagement_improvement',
        'batch_vs_realtime', 'type_selection'
    )),
    
    -- The recommendation
    title               TEXT NOT NULL,                    -- Short headline
    description         TEXT NOT NULL,                    -- Full explanation
    suggested_changes   JSONB NOT NULL,                   -- Specific preference changes
    
    -- Expected outcomes
    expected_outcome    TEXT NOT NULL,                    -- Human-readable expected benefit
    expected_metrics    JSONB NOT NULL DEFAULT '{}',      -- Predicted metric improvements
    
    -- Personalization context
    cohort_basis        TEXT,                             -- Which cohort pattern triggered this
    user_metrics_snapshot JSONB NOT NULL DEFAULT '{}',   -- User's current metrics
    similar_users_count INTEGER DEFAULT 0,                -- How many similar users
    similar_users_improvement NUMERIC(5, 2),              -- % improvement seen in similar users
    
    -- Priority and relevance
    priority_score      NUMERIC(5, 2) DEFAULT 50,        -- 0-100, higher = more relevant
    relevance_reason    TEXT,                             -- Why this is relevant to this user
    
    -- Status
    status              TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'shown', 'accepted', 'rejected', 'expired', 'applied'
    )),
    
    -- A/B test assignment
    ab_test_id          TEXT,
    test_group          TEXT CHECK (test_group IN ('control', 'treatment')),
    
    -- Tracking
    shown_at            TIMESTAMPTZ,
    responded_at        TIMESTAMPTZ,
    applied_at          TIMESTAMPTZ,
    
    -- Outcome tracking (filled after acceptance)
    actual_outcome      JSONB,                            -- Real metrics after change
    outcome_measured_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at          TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '30 days'),
    
    -- One active recommendation per type per user
    UNIQUE(recipient_id, recipient_type, recommendation_type, created_at)
);

CREATE INDEX IF NOT EXISTS idx_preference_recommendations_recipient 
    ON public.preference_recommendations(recipient_id, recipient_type);
CREATE INDEX IF NOT EXISTS idx_preference_recommendations_status 
    ON public.preference_recommendations(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_preference_recommendations_type 
    ON public.preference_recommendations(recommendation_type, recipient_type);
CREATE INDEX IF NOT EXISTS idx_preference_recommendations_priority 
    ON public.preference_recommendations(priority_score DESC) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_preference_recommendations_ab_test 
    ON public.preference_recommendations(ab_test_id, test_group);
CREATE INDEX IF NOT EXISTS idx_preference_recommendations_expires 
    ON public.preference_recommendations(expires_at) WHERE status IN ('pending', 'shown');

-- ═══════════════════════════════════════════════════════════════════
-- A/B TEST RESULTS TABLE
-- Store A/B test outcomes with statistical analysis
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.preference_ab_test_results (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id             TEXT NOT NULL,
    
    -- Test configuration
    test_name           TEXT NOT NULL,
    hypothesis          TEXT NOT NULL,
    recommendation_type TEXT NOT NULL,
    
    -- Segment
    segment_type        TEXT NOT NULL CHECK (segment_type IN ('all_customers', 'all_owners', 'cohort', 'custom')),
    segment_definition  JSONB,
    
    -- Timing
    start_date          TIMESTAMPTZ NOT NULL,
    end_date            TIMESTAMPTZ,
    duration_days       INTEGER NOT NULL DEFAULT 14,
    
    -- Sample sizes
    control_sample_size INTEGER NOT NULL DEFAULT 0,
    treatment_sample_size INTEGER NOT NULL DEFAULT 0,
    
    -- Control group metrics
    control_open_rate       NUMERIC(5, 4),
    control_click_rate      NUMERIC(5, 4),
    control_engagement_score NUMERIC(5, 2),
    control_unsubscribe_rate NUMERIC(5, 4),
    control_response_time_hours NUMERIC(8, 2),           -- For owners
    control_satisfaction    NUMERIC(3, 2),               -- For owners
    
    -- Treatment group metrics
    treatment_open_rate     NUMERIC(5, 4),
    treatment_click_rate    NUMERIC(5, 4),
    treatment_engagement_score NUMERIC(5, 2),
    treatment_unsubscribe_rate NUMERIC(5, 4),
    treatment_response_time_hours NUMERIC(8, 2),         -- For owners
    treatment_satisfaction  NUMERIC(3, 2),               -- For owners
    
    -- Statistical results
    -- Per metric p-values and effect sizes
    open_rate_p_value       NUMERIC(10, 8),
    open_rate_effect_size   NUMERIC(5, 4),               -- Cohen's d
    click_rate_p_value      NUMERIC(10, 8),
    click_rate_effect_size  NUMERIC(5, 4),
    engagement_p_value      NUMERIC(10, 8),
    engagement_effect_size  NUMERIC(5, 4),
    unsubscribe_p_value     NUMERIC(10, 8),
    unsubscribe_effect_size NUMERIC(5, 4),
    
    -- Overall conclusion
    winner_group            TEXT CHECK (winner_group IN ('control', 'treatment', 'inconclusive')),
    confidence_level        NUMERIC(5, 4),               -- e.g., 0.95 for 95%
    is_significant          BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Recommendation
    should_rollout          BOOLEAN NOT NULL DEFAULT FALSE,
    rollout_recommendation  TEXT,
    
    -- Timestamps
    computed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(test_id)
);

CREATE INDEX IF NOT EXISTS idx_preference_ab_test_results_test 
    ON public.preference_ab_test_results(test_id);
CREATE INDEX IF NOT EXISTS idx_preference_ab_test_results_significant 
    ON public.preference_ab_test_results(is_significant, winner_group);
CREATE INDEX IF NOT EXISTS idx_preference_ab_test_results_rollout 
    ON public.preference_ab_test_results(should_rollout) WHERE should_rollout = TRUE;

-- ═══════════════════════════════════════════════════════════════════
-- PREFERENCE PATTERNS TABLE
-- Discovered patterns from preference analysis
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.preference_patterns (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pattern_name        TEXT NOT NULL,
    pattern_type        TEXT NOT NULL CHECK (pattern_type IN (
        'common_config', 'sequence', 'correlation', 'drift', 'anomaly'
    )),
    recipient_type      TEXT CHECK (recipient_type IN ('customer', 'owner')),
    
    -- Pattern definition
    pattern_definition  JSONB NOT NULL,                  -- The actual pattern
    prevalence_pct      NUMERIC(5, 2),                    -- % of users with this pattern
    
    -- Correlation with engagement
    avg_engagement_score NUMERIC(5, 2),
    engagement_correlation NUMERIC(5, 4),                 -- Correlation coefficient
    
    -- Business impact (for owners)
    avg_response_time_hours NUMERIC(8, 2),
    avg_satisfaction    NUMERIC(3, 2),
    
    -- Recommendation potential
    is_recommendation_candidate BOOLEAN NOT NULL DEFAULT FALSE,
    recommendation_template TEXT,
    
    -- Timestamps
    discovered_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_verified_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(pattern_name, recipient_type)
);

CREATE INDEX IF NOT EXISTS idx_preference_patterns_type 
    ON public.preference_patterns(pattern_type, recipient_type);
CREATE INDEX IF NOT EXISTS idx_preference_patterns_prevalence 
    ON public.preference_patterns(prevalence_pct DESC);
CREATE INDEX IF NOT EXISTS idx_preference_patterns_recommendation 
    ON public.preference_patterns(is_recommendation_candidate) WHERE is_recommendation_candidate = TRUE;

-- ═══════════════════════════════════════════════════════════════════
-- ANALYTICS AGGREGATION TABLES
-- Pre-computed aggregations for dashboard performance
-- ═══════════════════════════════════════════════════════════════════

-- Preference distribution snapshot
CREATE TABLE IF NOT EXISTS public.preference_distribution_daily (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    snapshot_date       DATE NOT NULL,
    recipient_type      TEXT NOT NULL CHECK (recipient_type IN ('customer', 'owner')),
    
    -- Channel distribution
    -- { "in_app": { "enabled": 850, "disabled": 150 }, ... }
    channel_distribution JSONB NOT NULL DEFAULT '{}',
    
    -- Frequency distribution
    -- { "email": { "real_time": 600, "daily_digest": 250, "weekly_summary": 100, "disabled": 50 }, ... }
    frequency_distribution JSONB NOT NULL DEFAULT '{}',
    
    -- Notification type distribution
    -- { "order_updates": { "enabled": 950, "disabled": 50 }, ... }
    type_distribution   JSONB NOT NULL DEFAULT '{}',
    
    -- Batch settings distribution (owners)
    batch_distribution  JSONB NOT NULL DEFAULT '{}',
    
    -- Total users
    total_users         INTEGER NOT NULL DEFAULT 0,
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(snapshot_date, recipient_type)
);

CREATE INDEX IF NOT EXISTS idx_preference_distribution_daily_date 
    ON public.preference_distribution_daily(snapshot_date DESC);

-- Cohort performance snapshot
CREATE TABLE IF NOT EXISTS public.cohort_performance_weekly (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cohort_id           UUID NOT NULL REFERENCES public.user_cohorts(id) ON DELETE CASCADE,
    week_start          DATE NOT NULL,
    week_end            DATE NOT NULL,
    
    -- Member stats
    member_count        INTEGER NOT NULL DEFAULT 0,
    new_members         INTEGER NOT NULL DEFAULT 0,
    exited_members      INTEGER NOT NULL DEFAULT 0,
    
    -- Engagement metrics
    avg_engagement_score NUMERIC(5, 2),
    avg_open_rate       NUMERIC(5, 4),
    avg_click_rate      NUMERIC(5, 4),
    avg_ignore_rate     NUMERIC(5, 4),
    unsubscribe_count   INTEGER DEFAULT 0,
    
    -- Business metrics (owners)
    avg_response_time_hours NUMERIC(8, 2),
    avg_satisfaction    NUMERIC(3, 2),
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(cohort_id, week_start)
);

CREATE INDEX IF NOT EXISTS idx_cohort_performance_weekly_cohort 
    ON public.cohort_performance_weekly(cohort_id, week_start DESC);

-- ═══════════════════════════════════════════════════════════════════
-- FUNCTIONS
-- ═══════════════════════════════════════════════════════════════════

-- Calculate engagement score from metrics
CREATE OR REPLACE FUNCTION public.calculate_engagement_score(
    p_open_rate NUMERIC,
    p_click_rate NUMERIC,
    p_ignore_rate NUMERIC,
    p_unsubscribe_events INTEGER DEFAULT 0
) RETURNS NUMERIC AS $$
DECLARE
    score NUMERIC;
BEGIN
    -- Weighted engagement score (0-100)
    -- Open rate: 40% weight
    -- Click rate: 30% weight  
    -- Low ignore rate: 20% weight (inverted)
    -- No unsubscribes: 10% weight
    
    score := (
        COALESCE(p_open_rate, 0) * 40 +
        COALESCE(p_click_rate, 0) * 30 +
        (1 - COALESCE(p_ignore_rate, 0)) * 20 +
        CASE WHEN COALESCE(p_unsubscribe_events, 0) = 0 THEN 10 ELSE 0 END
    );
    
    RETURN LEAST(GREATEST(score, 0), 100);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Check if user matches cohort definition
CREATE OR REPLACE FUNCTION public.matches_cohort_definition(
    p_preferences JSONB,
    p_definition JSONB
) RETURNS BOOLEAN AS $$
DECLARE
    key TEXT;
    def_value JSONB;
    pref_value JSONB;
BEGIN
    -- Check each key in definition against preferences
    FOR key, def_value IN SELECT * FROM jsonb_each(p_definition)
    LOOP
        -- Handle special keys
        IF key LIKE '%_min' OR key LIKE '%_max' THEN
            -- These are comparison keys, not direct matches
            -- Skip for now (handled separately)
            CONTINUE;
        END IF;
        
        -- Get corresponding preference value
        pref_value := p_preferences->key;
        
        -- If definition value is an object, do deep comparison
        IF jsonb_typeof(def_value) = 'object' THEN
            IF pref_value IS NULL OR NOT pref_value @> def_value THEN
                RETURN FALSE;
            END IF;
        ELSE
            -- Direct value comparison
            IF pref_value IS NULL OR pref_value != def_value THEN
                RETURN FALSE;
            END IF;
        END IF;
    END LOOP;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Get user's cohort memberships
CREATE OR REPLACE FUNCTION public.get_user_cohorts(
    p_recipient_id TEXT,
    p_recipient_type TEXT
) RETURNS TABLE (
    cohort_id UUID,
    cohort_name TEXT,
    cohort_slug TEXT,
    joined_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        uc.id,
        uc.cohort_name,
        uc.cohort_slug,
        ucm.joined_at
    FROM public.user_cohorts uc
    JOIN public.user_cohort_membership ucm ON ucm.cohort_id = uc.id
    WHERE ucm.recipient_id = p_recipient_id
      AND ucm.recipient_type = p_recipient_type
      AND ucm.exited_at IS NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Get similar users based on preferences
CREATE OR REPLACE FUNCTION public.get_similar_users(
    p_recipient_id TEXT,
    p_recipient_type TEXT,
    p_limit INTEGER DEFAULT 100
) RETURNS TABLE (
    recipient_id TEXT,
    similarity_score NUMERIC
) AS $$
DECLARE
    target_prefs JSONB;
BEGIN
    -- Get target user's preferences
    SELECT new_state INTO target_prefs
    FROM public.preference_history
    WHERE recipient_id = p_recipient_id
      AND recipient_type = p_recipient_type
    ORDER BY created_at DESC
    LIMIT 1;
    
    IF target_prefs IS NULL THEN
        RETURN;
    END IF;
    
    -- Find users with similar preferences
    -- This is a simplified version; production would use more sophisticated similarity
    RETURN QUERY
    SELECT 
        ph.recipient_id,
        0.8::NUMERIC AS similarity_score  -- Placeholder; real impl would calculate
    FROM public.preference_history ph
    WHERE ph.recipient_type = p_recipient_type
      AND ph.recipient_id != p_recipient_id
      AND ph.new_state @> target_prefs  -- Contains target prefs
    GROUP BY ph.recipient_id
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Get preference recommendations for a user
CREATE OR REPLACE FUNCTION public.get_pending_recommendations(
    p_recipient_id TEXT,
    p_recipient_type TEXT
) RETURNS TABLE (
    id UUID,
    recommendation_type TEXT,
    title TEXT,
    description TEXT,
    suggested_changes JSONB,
    expected_outcome TEXT,
    priority_score NUMERIC,
    similar_users_improvement NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pr.id,
        pr.recommendation_type,
        pr.title,
        pr.description,
        pr.suggested_changes,
        pr.expected_outcome,
        pr.priority_score,
        pr.similar_users_improvement
    FROM public.preference_recommendations pr
    WHERE pr.recipient_id = p_recipient_id
      AND pr.recipient_type = p_recipient_type
      AND pr.status = 'pending'
      AND pr.expires_at > NOW()
    ORDER BY pr.priority_score DESC;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Get engagement heatmap data
CREATE OR REPLACE FUNCTION public.get_preference_engagement_heatmap(
    p_recipient_type TEXT DEFAULT NULL,
    p_days INTEGER DEFAULT 30
) RETURNS TABLE (
    preference_key TEXT,
    preference_value TEXT,
    user_count BIGINT,
    avg_engagement_score NUMERIC,
    avg_open_rate NUMERIC,
    avg_click_rate NUMERIC,
    avg_ignore_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        -- Extract preference keys and values from active_preferences
        em.active_preferences->>'email_frequency' AS preference_key,
        em.active_preferences->>'email_frequency' AS preference_value,
        COUNT(*) AS user_count,
        AVG(em.engagement_score) AS avg_engagement_score,
        AVG(em.overall_open_rate) AS avg_open_rate,
        AVG(em.overall_click_rate) AS avg_click_rate,
        AVG(em.overall_ignore_rate) AS avg_ignore_rate
    FROM public.engagement_metrics em
    WHERE em.period_type = 'weekly'
      AND em.period_start >= (CURRENT_DATE - p_days)
      AND (p_recipient_type IS NULL OR em.recipient_type = p_recipient_type)
    GROUP BY 
        em.active_preferences->>'email_frequency'
    ORDER BY avg_engagement_score DESC;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Statistical significance test (two-proportion z-test)
CREATE OR REPLACE FUNCTION public.calculate_z_test_p_value(
    p_control_successes INTEGER,
    p_control_total INTEGER,
    p_treatment_successes INTEGER,
    p_treatment_total INTEGER
) RETURNS NUMERIC AS $$
DECLARE
    p1 NUMERIC;
    p2 NUMERIC;
    p_pooled NUMERIC;
    se NUMERIC;
    z_score NUMERIC;
    p_value NUMERIC;
BEGIN
    -- Handle edge cases
    IF p_control_total = 0 OR p_treatment_total = 0 THEN
        RETURN NULL;
    END IF;
    
    p1 := p_control_successes::NUMERIC / p_control_total;
    p2 := p_treatment_successes::NUMERIC / p_treatment_total;
    p_pooled := (p_control_successes + p_treatment_successes)::NUMERIC / 
                (p_control_total + p_treatment_total);
    
    -- Standard error
    se := SQRT(p_pooled * (1 - p_pooled) * (1.0/p_control_total + 1.0/p_treatment_total));
    
    -- Handle zero standard error
    IF se = 0 THEN
        RETURN NULL;
    END IF;
    
    -- Z-score
    z_score := (p2 - p1) / se;
    
    -- Two-tailed p-value approximation using error function
    p_value := 2 * (1 - public.normal_cdf(ABS(z_score)));
    
    RETURN p_value;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Helper: Standard normal CDF approximation
CREATE OR REPLACE FUNCTION public.normal_cdf(p_x NUMERIC)
RETURNS NUMERIC AS $$
DECLARE
    a1 NUMERIC := 0.254829592;
    a2 NUMERIC := -0.284496736;
    a3 NUMERIC := 1.421413741;
    a4 NUMERIC := -1.453152027;
    a5 NUMERIC := 1.061405429;
    p NUMERIC := 0.3275911;
    sign NUMERIC;
    x NUMERIC;
    t NUMERIC;
    y NUMERIC;
BEGIN
    sign := CASE WHEN p_x < 0 THEN -1 ELSE 1 END;
    x := ABS(p_x) / SQRT(2);
    t := 1.0 / (1.0 + p * x);
    y := 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * EXP(-x * x);
    
    RETURN 0.5 * (1.0 + sign * y);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Calculate Cohen's d effect size
CREATE OR REPLACE FUNCTION public.calculate_cohens_d(
    p_control_mean NUMERIC,
    p_control_std NUMERIC,
    p_treatment_mean NUMERIC,
    p_treatment_std NUMERIC,
    p_control_n INTEGER,
    p_treatment_n INTEGER
) RETURNS NUMERIC AS $$
DECLARE
    pooled_std NUMERIC;
    d NUMERIC;
BEGIN
    -- Pooled standard deviation
    pooled_std := SQRT(
        ((p_control_n - 1) * POWER(p_control_std, 2) + 
         (p_treatment_n - 1) * POWER(p_treatment_std, 2)) /
        (p_control_n + p_treatment_n - 2)
    );
    
    IF pooled_std = 0 THEN
        RETURN NULL;
    END IF;
    
    -- Cohen's d
    d := (p_treatment_mean - p_control_mean) / pooled_std;
    
    RETURN d;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ═══════════════════════════════════════════════════════════════════
-- TRIGGERS
-- ═══════════════════════════════════════════════════════════════════

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_user_cohorts_updated_at
    BEFORE UPDATE ON public.user_cohorts
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Log preference changes to history
CREATE OR REPLACE FUNCTION public.log_preference_change()
RETURNS TRIGGER AS $$
DECLARE
    change_cat TEXT;
    field_pat TEXT;
BEGIN
    -- Determine change category
    IF NEW.global_enabled != OLD.global_enabled THEN
        change_cat := 'global_toggle';
        field_pat := 'global_enabled';
    ELSIF NEW.in_app_enabled != OLD.in_app_enabled OR 
          NEW.email_enabled != OLD.email_enabled OR
          NEW.push_enabled != OLD.push_enabled OR
          NEW.toast_enabled != OLD.toast_enabled THEN
        change_cat := 'channel_toggle';
        field_pat := 'channels';
    ELSIF NEW.in_app_frequency != OLD.in_app_frequency OR
          NEW.email_frequency != OLD.email_frequency OR
          NEW.push_frequency != OLD.push_frequency OR
          NEW.toast_frequency != OLD.toast_frequency THEN
        change_cat := 'frequency_adjustment';
        field_pat := 'frequency';
    ELSIF NEW.notification_types != OLD.notification_types THEN
        change_cat := 'type_selection';
        field_pat := 'notification_types';
    ELSIF NEW.batch_settings != OLD.batch_settings THEN
        change_cat := 'batch_settings';
        field_pat := 'batch_settings';
    ELSE
        change_cat := 'full_config';
        field_pat := 'multiple';
    END IF;
    
    -- Insert history record
    INSERT INTO public.preference_history (
        recipient_id,
        recipient_type,
        change_category,
        field_path,
        old_value,
        new_value,
        previous_state,
        new_state,
        trigger_source,
        device_id,
        device_type
    ) VALUES (
        NEW.recipient_id,
        NEW.recipient_type,
        change_cat,
        field_pat,
        to_jsonb(OLD) - 'id' - 'created_at' - 'updated_at' - 'sync_version' - 'checksum' - 'vector_clock',
        to_jsonb(NEW) - 'id' - 'created_at' - 'updated_at' - 'sync_version' - 'checksum' - 'vector_clock',
        jsonb_build_object(
            'global_enabled', OLD.global_enabled,
            'channels', jsonb_build_object(
                'in_app', jsonb_build_object('enabled', OLD.in_app_enabled, 'frequency', OLD.in_app_frequency),
                'email', jsonb_build_object('enabled', OLD.email_enabled, 'frequency', OLD.email_frequency),
                'push', jsonb_build_object('enabled', OLD.push_enabled, 'frequency', OLD.push_frequency),
                'toast', jsonb_build_object('enabled', OLD.toast_enabled, 'frequency', OLD.toast_frequency)
            ),
            'notification_types', OLD.notification_types,
            'batch_settings', OLD.batch_settings
        ),
        jsonb_build_object(
            'global_enabled', NEW.global_enabled,
            'channels', jsonb_build_object(
                'in_app', jsonb_build_object('enabled', NEW.in_app_enabled, 'frequency', NEW.in_app_frequency),
                'email', jsonb_build_object('enabled', NEW.email_enabled, 'frequency', NEW.email_frequency),
                'push', jsonb_build_object('enabled', NEW.push_enabled, 'frequency', NEW.push_frequency),
                'toast', jsonb_build_object('enabled', NEW.toast_enabled, 'frequency', NEW.toast_frequency)
            ),
            'notification_types', NEW.notification_types,
            'batch_settings', NEW.batch_settings
        ),
        'user_initiated',
        NEW.last_modified_by,
        NULL
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach trigger to notification_preferences
DROP TRIGGER IF EXISTS trg_log_preference_change ON public.notification_preferences;
CREATE TRIGGER trg_log_preference_change
    AFTER UPDATE ON public.notification_preferences
    FOR EACH ROW EXECUTE FUNCTION public.log_preference_change();

-- ═══════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE public.preference_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.engagement_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_cohorts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_cohort_membership ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.business_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.preference_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.preference_ab_test_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.preference_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.preference_distribution_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cohort_performance_weekly ENABLE ROW LEVEL SECURITY;

-- Users can read own data
CREATE POLICY "Users can read own preference history"
    ON public.preference_history FOR SELECT
    USING (
        recipient_id = auth.uid()::text
        OR EXISTS (
            SELECT 1 FROM public.user_roles ur
            WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'analytics')
        )
    );

CREATE POLICY "Users can read own engagement metrics"
    ON public.engagement_metrics FOR SELECT
    USING (
        recipient_id = auth.uid()::text
        OR EXISTS (
            SELECT 1 FROM public.user_roles ur
            WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'analytics')
        )
    );

CREATE POLICY "Users can read own recommendations"
    ON public.preference_recommendations FOR SELECT
    USING (recipient_id = auth.uid()::text);

CREATE POLICY "Users can update own recommendations"
    ON public.preference_recommendations FOR UPDATE
    USING (recipient_id = auth.uid()::text);

-- Admins can read all analytics data
CREATE POLICY "Admins can read all cohort data"
    ON public.user_cohorts FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.user_roles ur
            WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'analytics')
        )
    );

CREATE POLICY "Admins can read all cohort membership"
    ON public.user_cohort_membership FOR SELECT
    USING (
        recipient_id = auth.uid()::text
        OR EXISTS (
            SELECT 1 FROM public.user_roles ur
            WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'analytics')
        )
    );

CREATE POLICY "Owners can read own business outcomes"
    ON public.business_outcomes FOR SELECT
    USING (
        owner_id = auth.uid()::text
        OR EXISTS (
            SELECT 1 FROM public.user_roles ur
            WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'analytics')
        )
    );

-- Admins can read A/B test results
CREATE POLICY "Admins can read A/B test results"
    ON public.preference_ab_test_results FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.user_roles ur
            WHERE ur.user_id = auth.uid() AND ur.role IN ('admin', 'analytics')
        )
    );

-- Service role can manage all tables
CREATE POLICY "Service role can manage preference history"
    ON public.preference_history FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage engagement metrics"
    ON public.engagement_metrics FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage cohorts"
    ON public.user_cohorts FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage cohort membership"
    ON public.user_cohort_membership FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage business outcomes"
    ON public.business_outcomes FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage recommendations"
    ON public.preference_recommendations FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage A/B test results"
    ON public.preference_ab_test_results FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage patterns"
    ON public.preference_patterns FOR ALL
    USING (auth.role() = 'service_role');

-- ═══════════════════════════════════════════════════════════════════
-- GRANTS
-- ═══════════════════════════════════════════════════════════════════

GRANT SELECT ON public.preference_history TO authenticated;
GRANT SELECT ON public.engagement_metrics TO authenticated;
GRANT SELECT ON public.user_cohorts TO authenticated;
GRANT SELECT ON public.user_cohort_membership TO authenticated;
GRANT SELECT ON public.business_outcomes TO authenticated;
GRANT SELECT, UPDATE ON public.preference_recommendations TO authenticated;
GRANT SELECT ON public.preference_ab_test_results TO authenticated;
GRANT SELECT ON public.preference_patterns TO authenticated;
GRANT SELECT ON public.preference_distribution_daily TO authenticated;
GRANT SELECT ON public.cohort_performance_weekly TO authenticated;

GRANT ALL ON public.preference_history TO service_role;
GRANT ALL ON public.engagement_metrics TO service_role;
GRANT ALL ON public.user_cohorts TO service_role;
GRANT ALL ON public.user_cohort_membership TO service_role;
GRANT ALL ON public.business_outcomes TO service_role;
GRANT ALL ON public.preference_recommendations TO service_role;
GRANT ALL ON public.preference_ab_test_results TO service_role;
GRANT ALL ON public.preference_patterns TO service_role;
GRANT ALL ON public.preference_distribution_daily TO service_role;
GRANT ALL ON public.cohort_performance_weekly TO service_role;

-- Grant execute on functions
GRANT EXECUTE ON FUNCTION public.calculate_engagement_score TO service_role;
GRANT EXECUTE ON FUNCTION public.matches_cohort_definition TO service_role;
GRANT EXECUTE ON FUNCTION public.get_user_cohorts TO service_role;
GRANT EXECUTE ON FUNCTION public.get_similar_users TO service_role;
GRANT EXECUTE ON FUNCTION public.get_pending_recommendations TO service_role;
GRANT EXECUTE ON FUNCTION public.get_preference_engagement_heatmap TO service_role;
GRANT EXECUTE ON FUNCTION public.calculate_z_test_p_value TO service_role;
GRANT EXECUTE ON FUNCTION public.normal_cdf TO service_role;
GRANT EXECUTE ON FUNCTION public.calculate_cohens_d TO service_role;

-- ═══════════════════════════════════════════════════════════════════
-- COMMENTS
-- ═══════════════════════════════════════════════════════════════════

COMMENT ON TABLE public.preference_history IS 
    'Complete history of all preference configuration changes with context for pattern analysis';

COMMENT ON TABLE public.engagement_metrics IS 
    'Per-user engagement metrics by channel and frequency, linked to active preferences';

COMMENT ON TABLE public.user_cohorts IS 
    'User cohorts defined by shared preference patterns for comparative analysis';

COMMENT ON TABLE public.user_cohort_membership IS 
    'Tracks which users belong to which cohorts over time';

COMMENT ON TABLE public.business_outcomes IS 
    'Store owner business metrics (response time, satisfaction) linked to their preference configuration';

COMMENT ON TABLE public.preference_recommendations IS 
    'Personalized preference recommendations with expected outcomes and acceptance tracking';

COMMENT ON TABLE public.preference_ab_test_results IS 
    'A/B test outcomes with statistical significance analysis for recommendation validation';

COMMENT ON TABLE public.preference_patterns IS 
    'Discovered preference patterns from analysis with correlation to engagement';

COMMENT ON TABLE public.preference_distribution_daily IS 
    'Daily snapshots of preference distribution across user base for trend analysis';

COMMENT ON TABLE public.cohort_performance_weekly IS 
    'Weekly performance metrics per cohort for dashboard visualization';
