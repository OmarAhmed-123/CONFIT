-- ============================================================
-- CONFIT — ML Notification Optimization Schema
-- Created: 2026-04-06
-- Description: Database schema for predictive notification optimization
-- including recipient personas, delivery predictions, and accuracy tracking.
-- ============================================================

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Recipient Personas ──────────────────────────────────────────────
-- Stores persona definitions created by clustering algorithm

CREATE TABLE IF NOT EXISTS public.ml_personas (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL,
    recipient_type  TEXT NOT NULL CHECK (recipient_type IN ('customer', 'owner')),
    
    -- Persona characteristics (aggregated from clustering)
    characteristics JSONB NOT NULL DEFAULT '{}',
    -- Example: {
    --   "peak_hours": [9, 10, 11],
    --   "peak_days": [1, 2, 3, 4, 5],  -- Monday=1, Sunday=7
    --   "avg_open_rate": 0.45,
    --   "avg_click_rate": 0.12,
    --   "avg_response_time_min": 15.5,
    --   "consistency_score": 0.78,
    --   "preferred_channel": "in_app",
    --   "engagement_pattern": "early_morning"
    -- }
    
    -- Size and metrics
    recipient_count INTEGER NOT NULL DEFAULT 0,
    avg_open_rate   NUMERIC(5, 4) DEFAULT 0,
    avg_click_rate  NUMERIC(5, 4) DEFAULT 0,
    avg_conversion_rate NUMERIC(5, 4) DEFAULT 0,
    avg_response_time_min NUMERIC(10, 2),
    
    -- Model metadata
    model_version   TEXT NOT NULL,
    cluster_id      INTEGER,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ml_personas_recipient_type 
    ON public.ml_personas(recipient_type);
CREATE INDEX IF NOT EXISTS idx_ml_personas_model_version 
    ON public.ml_personas(model_version);

-- ── Recipient Persona Assignments ───────────────────────────────────
-- Maps each recipient to their assigned persona

CREATE TABLE IF NOT EXISTS public.ml_recipient_personas (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_id    TEXT NOT NULL,
    recipient_type  TEXT NOT NULL CHECK (recipient_type IN ('customer', 'owner')),
    persona_id      TEXT NOT NULL REFERENCES public.ml_personas(id) ON DELETE CASCADE,
    
    -- Assignment confidence (from clustering)
    assignment_confidence NUMERIC(5, 4) NOT NULL DEFAULT 1.0,
    
    -- Feature snapshot at assignment time
    feature_snapshot JSONB NOT NULL DEFAULT '{}',
    
    -- Validity period
    assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until     TIMESTAMPTZ,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(recipient_id, recipient_type, assigned_at)
);

CREATE INDEX IF NOT EXISTS idx_ml_recipient_personas_recipient 
    ON public.ml_recipient_personas(recipient_id, recipient_type);
CREATE INDEX IF NOT EXISTS idx_ml_recipient_personas_persona 
    ON public.ml_recipient_personas(persona_id);
CREATE INDEX IF NOT EXISTS idx_ml_recipient_personas_valid 
    ON public.ml_recipient_personas(valid_until) WHERE valid_until IS NOT NULL;

-- ── Delivery Time Predictions ───────────────────────────────────────
-- Stores ML predictions for optimal notification delivery times

CREATE TABLE IF NOT EXISTS public.ml_delivery_predictions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_id    TEXT NOT NULL,
    recipient_type  TEXT NOT NULL CHECK (recipient_type IN ('customer', 'owner')),
    persona_id      TEXT REFERENCES public.ml_personas(id) ON DELETE SET NULL,
    
    -- Prediction output
    recommended_hour INTEGER NOT NULL CHECK (recommended_hour >= 0 AND recommended_hour < 24),
    recommended_hours JSONB DEFAULT '[]',  -- Top-3 ranked hours with scores
    -- Example: [{"hour": 9, "score": 0.92}, {"hour": 10, "score": 0.85}, {"hour": 18, "score": 0.72}]
    
    confidence_score NUMERIC(5, 4) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    
    -- Explainability
    explanation     JSONB NOT NULL DEFAULT '{}',
    -- Example: {
    --   "reason": "This persona shows 45% open rate at 9 AM vs 12% at 3 PM",
    --   "feature_importance": {"hour_9_open_rate": 0.35, "morning_engagement": 0.28},
    --   "historical_context": "Similar recipients had 3.2x conversion rate at 9 AM",
    --   "fallback_reason": null
    -- }
    
    -- Context for prediction
    notification_type TEXT,
    channel         TEXT CHECK (channel IN ('in_app', 'email', 'push', 'toast')),
    
    -- Model metadata
    model_version   TEXT NOT NULL,
    feature_values  JSONB DEFAULT '{}',  -- Input features used for prediction
    
    -- Prediction validity
    predicted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_for_hours INTEGER NOT NULL DEFAULT 24,
    expires_at      TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),
    
    -- Outcome tracking (filled after notification is sent)
    was_used        BOOLEAN DEFAULT FALSE,
    notification_id TEXT,
    actual_outcome  JSONB,
    -- Example: {"opened": true, "clicked": false, "response_time_min": 12.5, "converted": true}
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ml_delivery_predictions_recipient 
    ON public.ml_delivery_predictions(recipient_id, recipient_type);
CREATE INDEX IF NOT EXISTS idx_ml_delivery_predictions_persona 
    ON public.ml_delivery_predictions(persona_id);
CREATE INDEX IF NOT EXISTS idx_ml_delivery_predictions_expires 
    ON public.ml_delivery_predictions(expires_at) WHERE was_used = FALSE;
CREATE INDEX IF NOT EXISTS idx_ml_delivery_predictions_outcome 
    ON public.ml_delivery_predictions(was_used, actual_outcome IS NOT NULL);

-- ── Model Version History ───────────────────────────────────────────
-- Tracks model versions for reproducibility and rollback

CREATE TABLE IF NOT EXISTS public.ml_model_versions (
    id              TEXT PRIMARY KEY,
    model_type      TEXT NOT NULL CHECK (model_type IN ('persona_clustering', 'delivery_prediction')),
    description     TEXT NOT NULL,
    
    -- Training metadata
    training_data_start TIMESTAMPTZ NOT NULL,
    training_data_end   TIMESTAMPTZ NOT NULL,
    training_samples    INTEGER NOT NULL,
    validation_samples  INTEGER NOT NULL,
    
    -- Hyperparameters
    hyperparameters JSONB NOT NULL DEFAULT '{}',
    
    -- Performance metrics
    metrics         JSONB NOT NULL DEFAULT '{}',
    -- Example for clustering: {"silhouette_score": 0.65, "inertia": 1234.5, "n_clusters": 5}
    -- Example for prediction: {"mae": 1.2, "rmse": 1.8, "r2": 0.72, "accuracy_top1": 0.68}
    
    -- Feature importance
    feature_importance JSONB DEFAULT '{}',
    
    -- Status
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'deprecated', 'rollback')),
    deployed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deprecated_at   TIMESTAMPTZ,
    
    -- File paths
    model_path      TEXT,
    scaler_path     TEXT,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ml_model_versions_type 
    ON public.ml_model_versions(model_type, status);

-- ── Prediction Accuracy Tracking ─────────────────────────────────────
-- Tracks accuracy of predictions over time

CREATE TABLE IF NOT EXISTS public.ml_prediction_accuracy (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prediction_id   UUID REFERENCES public.ml_delivery_predictions(id) ON DELETE CASCADE,
    
    -- Accuracy metrics
    was_opened      BOOLEAN,
    was_clicked     BOOLEAN,
    was_converted   BOOLEAN,
    response_time_min NUMERIC(10, 2),
    
    -- Comparison with baseline
    baseline_hour   INTEGER,  -- What hour would have been used without ML
    baseline_outcome JSONB,  -- Outcome if sent at baseline hour
    
    -- Lift calculation
    open_rate_lift  NUMERIC(6, 4),  -- (actual - baseline) / baseline
    click_rate_lift NUMERIC(6, 4),
    conversion_lift NUMERIC(6, 4),
    response_time_improvement NUMERIC(10, 2),  -- baseline - actual (negative = faster)
    
    -- Attribution
    notification_id TEXT NOT NULL,
    sent_at         TIMESTAMPTZ NOT NULL,
    opened_at       TIMESTAMPTZ,
    clicked_at      TIMESTAMPTZ,
    converted_at    TIMESTAMPTZ,
    
    -- Persona and model context
    persona_id      TEXT,
    model_version   TEXT NOT NULL,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ml_prediction_accuracy_prediction 
    ON public.ml_prediction_accuracy(prediction_id);
CREATE INDEX IF NOT EXISTS idx_ml_prediction_accuracy_sent_at 
    ON public.ml_prediction_accuracy(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_ml_prediction_accuracy_persona 
    ON public.ml_prediction_accuracy(persona_id);
CREATE INDEX IF NOT EXISTS idx_ml_prediction_accuracy_model 
    ON public.ml_prediction_accuracy(model_version);

-- ── Daily Accuracy Summary ───────────────────────────────────────────
-- Pre-aggregated accuracy metrics for dashboard

CREATE TABLE IF NOT EXISTS public.ml_daily_accuracy_summary (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    summary_date    DATE NOT NULL,
    persona_id      TEXT REFERENCES public.ml_personas(id) ON DELETE CASCADE,
    recipient_type  TEXT NOT NULL CHECK (recipient_type IN ('customer', 'owner')),
    model_version   TEXT NOT NULL,
    
    -- Prediction counts
    total_predictions INTEGER NOT NULL DEFAULT 0,
    ml_timed_sent     INTEGER NOT NULL DEFAULT 0,  -- Sent at ML-predicted time
    baseline_timed_sent INTEGER NOT NULL DEFAULT 0,  -- Sent at default time
    
    -- ML outcomes
    ml_open_rate      NUMERIC(5, 4) DEFAULT 0,
    ml_click_rate     NUMERIC(5, 4) DEFAULT 0,
    ml_conversion_rate NUMERIC(5, 4) DEFAULT 0,
    ml_avg_response_time NUMERIC(10, 2),
    
    -- Baseline outcomes
    baseline_open_rate NUMERIC(5, 4) DEFAULT 0,
    baseline_click_rate NUMERIC(5, 4) DEFAULT 0,
    baseline_conversion_rate NUMERIC(5, 4) DEFAULT 0,
    baseline_avg_response_time NUMERIC(10, 2),
    
    -- Lift metrics
    open_rate_lift    NUMERIC(6, 4) DEFAULT 0,
    click_rate_lift   NUMERIC(6, 4) DEFAULT 0,
    conversion_lift   NUMERIC(6, 4) DEFAULT 0,
    response_time_improvement NUMERIC(10, 2) DEFAULT 0,
    
    -- Statistical significance
    open_rate_p_value NUMERIC(10, 8),
    click_rate_p_value NUMERIC(10, 8),
    conversion_p_value NUMERIC(10, 8),
    is_significant    BOOLEAN DEFAULT FALSE,
    
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(summary_date, persona_id, model_version)
);

CREATE INDEX IF NOT EXISTS idx_ml_daily_accuracy_summary_date 
    ON public.ml_daily_accuracy_summary(summary_date DESC);
CREATE INDEX IF NOT EXISTS idx_ml_daily_accuracy_summary_persona 
    ON public.ml_daily_accuracy_summary(persona_id);

-- ── Model Drift Detection ────────────────────────────────────────────
-- Tracks model performance degradation

CREATE TABLE IF NOT EXISTS public.ml_model_drift (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_version   TEXT NOT NULL REFERENCES public.ml_model_versions(id) ON DELETE CASCADE,
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Drift type
    drift_type      TEXT NOT NULL CHECK (drift_type IN ('performance', 'data', 'concept')),
    severity        TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    
    -- Metrics
    baseline_metric NUMERIC(10, 6) NOT NULL,
    current_metric  NUMERIC(10, 6) NOT NULL,
    drift_percentage NUMERIC(6, 2) NOT NULL,
    
    -- Affected segments
    affected_personas TEXT[] DEFAULT '{}',
    affected_recipient_types TEXT[] DEFAULT '{}',
    
    -- Details
    details         JSONB DEFAULT '{}',
    
    -- Resolution
    status          TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'acknowledged', 'resolved', 'ignored')),
    resolved_at     TIMESTAMPTZ,
    resolution_notes TEXT,
    retraining_triggered BOOLEAN DEFAULT FALSE,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ml_model_drift_model 
    ON public.ml_model_drift(model_version);
CREATE INDEX IF NOT EXISTS idx_ml_model_drift_status 
    ON public.ml_model_drift(status, detected_at DESC);

-- ── Recipient Engagement Features ────────────────────────────────────
-- Cached feature vectors for each recipient (updated periodically)

CREATE TABLE IF NOT EXISTS public.ml_recipient_features (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_id    TEXT NOT NULL,
    recipient_type  TEXT NOT NULL CHECK (recipient_type IN ('customer', 'owner')),
    
    -- Hourly engagement profile (24 values)
    hourly_open_rates JSONB NOT NULL DEFAULT '[]',  -- [0.12, 0.08, ..., 0.45]
    hourly_click_rates JSONB NOT NULL DEFAULT '[]',
    hourly_event_counts JSONB NOT NULL DEFAULT '[]',
    
    -- Daily engagement profile (7 values, Mon=0, Sun=6)
    daily_open_rates JSONB NOT NULL DEFAULT '[]',
    daily_click_rates JSONB NOT NULL DEFAULT '[]',
    daily_event_counts JSONB NOT NULL DEFAULT '[]',
    
    -- Aggregate metrics
    total_notifications_sent INTEGER DEFAULT 0,
    total_notifications_opened INTEGER DEFAULT 0,
    total_notifications_clicked INTEGER DEFAULT 0,
    overall_open_rate NUMERIC(5, 4) DEFAULT 0,
    overall_click_rate NUMERIC(5, 4) DEFAULT 0,
    
    -- Behavioral signals
    consistency_score NUMERIC(5, 4),  -- Variability in engagement patterns
    recency_weighted_engagement NUMERIC(5, 4),  -- Recent engagement weighted higher
    preferred_channel TEXT,
    peak_hour INTEGER,
    peak_day INTEGER,
    
    -- Time series features (trailing windows)
    engagement_trend_30d NUMERIC(6, 4),  -- Slope of engagement over 30 days
    engagement_trend_60d NUMERIC(6, 4),
    engagement_trend_90d NUMERIC(6, 4),
    
    -- Owner-specific features
    avg_response_time_min NUMERIC(10, 2),
    median_response_time_min NUMERIC(10, 2),
    response_consistency NUMERIC(5, 4),
    
    -- Customer-specific features
    conversion_rate_7d NUMERIC(5, 4),
    conversion_rate_14d NUMERIC(5, 4),
    conversion_rate_30d NUMERIC(5, 4),
    repeat_purchase_rate NUMERIC(5, 4),
    
    -- Metadata
    account_tenure_days INTEGER,
    last_notification_at TIMESTAMPTZ,
    last_engagement_at TIMESTAMPTZ,
    
    -- Feature computation metadata
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data_window_start TIMESTAMPTZ NOT NULL,
    data_window_end   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(recipient_id, recipient_type, computed_at)
);

CREATE INDEX IF NOT EXISTS idx_ml_recipient_features_recipient 
    ON public.ml_recipient_features(recipient_id, recipient_type);
CREATE INDEX IF NOT EXISTS idx_ml_recipient_features_computed 
    ON public.ml_recipient_features(computed_at DESC);

-- ── Functions ────────────────────────────────────────────────────────

-- Get active prediction for a recipient
CREATE OR REPLACE FUNCTION public.get_active_prediction(
    p_recipient_id TEXT,
    p_recipient_type TEXT,
    p_notification_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    prediction_id UUID,
    recommended_hour INTEGER,
    recommended_hours JSONB,
    confidence_score NUMERIC,
    explanation JSONB,
    persona_id TEXT,
    persona_name TEXT,
    model_version TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dp.id,
        dp.recommended_hour,
        dp.recommended_hours,
        dp.confidence_score,
        dp.explanation,
        dp.persona_id,
        p.name,
        dp.model_version
    FROM public.ml_delivery_predictions dp
    LEFT JOIN public.ml_personas p ON dp.persona_id = p.id
    WHERE dp.recipient_id = p_recipient_id
      AND dp.recipient_type = p_recipient_type
      AND dp.was_used = FALSE
      AND dp.expires_at > NOW()
      AND (p_notification_type IS NULL OR dp.notification_type = p_notification_type OR dp.notification_type IS NULL)
    ORDER BY dp.predicted_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Get recipient features for ML inference
CREATE OR REPLACE FUNCTION public.get_recipient_features_for_ml(
    p_recipient_id TEXT,
    p_recipient_type TEXT
)
RETURNS TABLE (
    hourly_open_rates JSONB,
    hourly_click_rates JSONB,
    daily_open_rates JSONB,
    daily_click_rates JSONB,
    overall_open_rate NUMERIC,
    overall_click_rate NUMERIC,
    consistency_score NUMERIC,
    peak_hour INTEGER,
    peak_day INTEGER,
    preferred_channel TEXT,
    avg_response_time_min NUMERIC,
    conversion_rate_30d NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rf.hourly_open_rates,
        rf.hourly_click_rates,
        rf.daily_open_rates,
        rf.daily_click_rates,
        rf.overall_open_rate,
        rf.overall_click_rate,
        rf.consistency_score,
        rf.peak_hour,
        rf.peak_day,
        rf.preferred_channel,
        rf.avg_response_time_min,
        rf.conversion_rate_30d
    FROM public.ml_recipient_features rf
    WHERE rf.recipient_id = p_recipient_id
      AND rf.recipient_type = p_recipient_type
    ORDER BY rf.computed_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Calculate accuracy metrics for a time period
CREATE OR REPLACE FUNCTION public.calculate_accuracy_metrics(
    p_start_date TIMESTAMPTZ,
    p_end_date TIMESTAMPTZ,
    p_persona_id TEXT DEFAULT NULL
)
RETURNS TABLE (
    persona_id TEXT,
    persona_name TEXT,
    recipient_type TEXT,
    total_predictions BIGINT,
    ml_open_rate NUMERIC,
    baseline_open_rate NUMERIC,
    open_rate_lift NUMERIC,
    ml_click_rate NUMERIC,
    baseline_click_rate NUMERIC,
    click_rate_lift NUMERIC,
    ml_conversion_rate NUMERIC,
    baseline_conversion_rate NUMERIC,
    conversion_lift NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pa.persona_id,
        p.name,
        p.recipient_type,
        COUNT(*) AS total_predictions,
        AVG(CASE WHEN pa.was_opened THEN 1.0 ELSE 0.0 END) AS ml_open_rate,
        AVG(CASE WHEN pa.baseline_outcome->>'opened' = 'true' THEN 1.0 ELSE 0.0 END) AS baseline_open_rate,
        AVG(CASE WHEN pa.was_opened THEN 1.0 ELSE 0.0 END) - 
        AVG(CASE WHEN pa.baseline_outcome->>'opened' = 'true' THEN 1.0 ELSE 0.0 END) AS open_rate_lift,
        AVG(CASE WHEN pa.was_clicked THEN 1.0 ELSE 0.0 END) AS ml_click_rate,
        AVG(CASE WHEN pa.baseline_outcome->>'clicked' = 'true' THEN 1.0 ELSE 0.0 END) AS baseline_click_rate,
        AVG(CASE WHEN pa.was_clicked THEN 1.0 ELSE 0.0 END) - 
        AVG(CASE WHEN pa.baseline_outcome->>'clicked' = 'true' THEN 1.0 ELSE 0.0 END) AS click_rate_lift,
        AVG(CASE WHEN pa.was_converted THEN 1.0 ELSE 0.0 END) AS ml_conversion_rate,
        AVG(CASE WHEN pa.baseline_outcome->>'converted' = 'true' THEN 1.0 ELSE 0.0 END) AS baseline_conversion_rate,
        AVG(CASE WHEN pa.was_converted THEN 1.0 ELSE 0.0 END) - 
        AVG(CASE WHEN pa.baseline_outcome->>'converted' = 'true' THEN 1.0 ELSE 0.0 END) AS conversion_lift
    FROM public.ml_prediction_accuracy pa
    LEFT JOIN public.ml_personas p ON pa.persona_id = p.id
    WHERE pa.sent_at >= p_start_date
      AND pa.sent_at < p_end_date
      AND (p_persona_id IS NULL OR pa.persona_id = p_persona_id)
    GROUP BY pa.persona_id, p.name, p.recipient_type
    ORDER BY total_predictions DESC;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ── Triggers ───────────────────────────────────────────────────────────

CREATE TRIGGER trg_ml_personas_updated_at
    BEFORE UPDATE ON public.ml_personas
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_ml_recipient_personas_updated_at
    BEFORE UPDATE ON public.ml_recipient_personas
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_ml_model_versions_updated_at
    BEFORE UPDATE ON public.ml_model_versions
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_ml_daily_accuracy_summary_updated_at
    BEFORE UPDATE ON public.ml_daily_accuracy_summary
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_ml_recipient_features_updated_at
    BEFORE UPDATE ON public.ml_recipient_features
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ── Grants ─────────────────────────────────────────────────────────────

GRANT SELECT ON public.ml_personas TO authenticated;
GRANT SELECT ON public.ml_recipient_personas TO authenticated;
GRANT SELECT ON public.ml_delivery_predictions TO authenticated;
GRANT SELECT ON public.ml_model_versions TO authenticated;
GRANT SELECT ON public.ml_prediction_accuracy TO authenticated;
GRANT SELECT ON public.ml_daily_accuracy_summary TO authenticated;
GRANT SELECT ON public.ml_model_drift TO authenticated;
GRANT SELECT ON public.ml_recipient_features TO authenticated;

GRANT INSERT, UPDATE ON public.ml_personas TO service_role;
GRANT INSERT, UPDATE ON public.ml_recipient_personas TO service_role;
GRANT INSERT, UPDATE ON public.ml_delivery_predictions TO service_role;
GRANT INSERT, UPDATE ON public.ml_model_versions TO service_role;
GRANT INSERT, UPDATE ON public.ml_prediction_accuracy TO service_role;
GRANT INSERT, UPDATE ON public.ml_daily_accuracy_summary TO service_role;
GRANT INSERT, UPDATE ON public.ml_model_drift TO service_role;
GRANT INSERT, UPDATE ON public.ml_recipient_features TO service_role;

-- ── Comments ───────────────────────────────────────────────────────────

COMMENT ON TABLE public.ml_personas IS 
    'Persona definitions created by ML clustering algorithm for recipient segmentation';

COMMENT ON TABLE public.ml_recipient_personas IS 
    'Maps recipients to their assigned persona with confidence scores';

COMMENT ON TABLE public.ml_delivery_predictions IS 
    'ML predictions for optimal notification delivery times with explainability';

COMMENT ON TABLE public.ml_model_versions IS 
    'Model version history for reproducibility and rollback capability';

COMMENT ON TABLE public.ml_prediction_accuracy IS 
    'Tracks accuracy of predictions by comparing outcomes with baseline';

COMMENT ON TABLE public.ml_daily_accuracy_summary IS 
    'Pre-aggregated daily accuracy metrics for dashboard performance';

COMMENT ON TABLE public.ml_model_drift IS 
    'Tracks model performance degradation and drift detection alerts';

COMMENT ON TABLE public.ml_recipient_features IS 
    'Cached feature vectors for each recipient used for ML inference';
