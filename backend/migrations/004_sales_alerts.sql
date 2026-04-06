-- CONFIT — Sales Alert System Migration
-- ======================================
-- Creates tables for sales alerts, preferences, and audit logs.
-- Retained for 30 days for history and compliance.

-- Enable UUID extension if not already enabled (PostgreSQL)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Sales Alerts Table ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sales_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Classification
    type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'warning',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    
    -- Content
    title VARCHAR(255) NOT NULL,
    message TEXT,
    rich_preview VARCHAR(500),
    
    -- Payload
    data JSONB NOT NULL DEFAULT '{}',
    actions JSONB DEFAULT '[]',
    
    -- Store reference
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    store_name VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    
    -- State
    read BOOLEAN NOT NULL DEFAULT FALSE,
    dismissed BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Deduplication
    dedup_key VARCHAR(255),
    first_triggered_at TIMESTAMPTZ,
    trigger_count INTEGER NOT NULL DEFAULT 1,
    last_triggered_at TIMESTAMPTZ
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS ix_sales_alerts_store_id ON sales_alerts(store_id);
CREATE INDEX IF NOT EXISTS ix_sales_alerts_created_at ON sales_alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_sales_alerts_type_severity ON sales_alerts(type, severity);
CREATE INDEX IF NOT EXISTS ix_sales_alerts_store_status ON sales_alerts(store_id, status);
CREATE INDEX IF NOT EXISTS ix_sales_alerts_dedup_key ON sales_alerts(dedup_key);
CREATE INDEX IF NOT EXISTS ix_sales_alerts_read ON sales_alerts(read) WHERE read = FALSE;

-- ─── Sales Alert Preferences Table ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sales_alert_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL UNIQUE REFERENCES stores(id) ON DELETE CASCADE,
    
    -- Configuration (JSON)
    thresholds JSONB NOT NULL DEFAULT '{}',
    frequency JSONB NOT NULL DEFAULT '{}',
    type_preferences JSONB NOT NULL DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_alert_prefs_store_id ON sales_alert_preferences(store_id);

-- ─── Sales Alert Logs Table (Audit Trail) ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS sales_alert_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES sales_alerts(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    
    -- Event details
    event_type VARCHAR(50) NOT NULL,
    previous_state JSONB,
    new_state JSONB,
    
    -- Actor
    actor_id UUID,
    actor_type VARCHAR(50),
    
    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_alert_logs_alert_id ON sales_alert_logs(alert_id);
CREATE INDEX IF NOT EXISTS ix_alert_logs_store_id ON sales_alert_logs(store_id);
CREATE INDEX IF NOT EXISTS ix_alert_logs_created_at ON sales_alert_logs(created_at DESC);

-- ─── Insert Default Preferences for Existing Stores ───────────────────────────

INSERT INTO sales_alert_preferences (store_id, thresholds, frequency, type_preferences)
SELECT 
    s.id,
    '{
        "high_value_aov_multiplier": 1.5,
        "inventory_threshold_units": 10,
        "inventory_threshold_percent": 20.0,
        "conversion_drop_threshold_percent": 15.0,
        "conversion_rise_threshold_percent": 20.0,
        "conversion_baseline_days": 7,
        "returns_spike_count": 5,
        "returns_spike_window_hours": 1,
        "returns_rate_increase_percent": 50.0,
        "vip_inactive_days": 30,
        "returning_to_inactive_days": 60
    }'::jsonb,
    '{
        "mode": "throttled",
        "max_alerts_per_hour": 10,
        "batch_interval_minutes": 30,
        "dedup_window_minutes": 60,
        "critical_mode": "real_time",
        "warning_mode": "batched",
        "info_mode": "batched"
    }'::jsonb,
    '{
        "high_value_order": {"enabled": true, "frequency": "real_time", "channels": ["in_app", "push"]},
        "unusual_returns": {"enabled": true, "frequency": "batched_30m", "channels": ["in_app", "email"]},
        "inventory_depletion": {"enabled": true, "frequency": "real_time", "channels": ["in_app", "email", "push"]},
        "conversion_anomaly": {"enabled": true, "frequency": "batched_30m", "channels": ["in_app"]},
        "customer_segment_change": {"enabled": true, "frequency": "batched_1h", "channels": ["in_app", "email"]}
    }'::jsonb
FROM stores s
WHERE NOT EXISTS (
    SELECT 1 FROM sales_alert_preferences p WHERE p.store_id = s.id
);

-- ─── Retention Policy Function ────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION cleanup_old_sales_alerts()
RETURNS void AS $$
BEGIN
    -- Delete alerts older than 30 days (except unresolved critical)
    DELETE FROM sales_alerts
    WHERE created_at < NOW() - INTERVAL '30 days'
      AND (severity != 'critical' OR status IN ('resolved', 'dismissed'));
    
    -- Delete logs older than 30 days
    DELETE FROM sales_alert_logs
    WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- ─── Trigger for Auto-Cleanup ─────────────────────────────────────────────────

-- Optionally create a cron job or scheduled task to call cleanup_old_sales_alerts()
-- SELECT cleanup_old_sales_alerts();

-- ─── Update Timestamp Trigger ─────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_sales_alert_preferences_updated_at ON sales_alert_preferences;
CREATE TRIGGER update_sales_alert_preferences_updated_at
    BEFORE UPDATE ON sales_alert_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ─── Grant Permissions ────────────────────────────────────────────────────────

-- GRANT SELECT, INSERT, UPDATE, DELETE ON sales_alerts TO confit_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON sales_alert_preferences TO confit_app;
-- GRANT SELECT, INSERT, DELETE ON sales_alert_logs TO confit_app;
