-- ============================================================
-- CONFIT — Alert Rules Configuration Schema
-- Created: 2026-04-11
-- Description: Production-grade alert rules configuration for store owners
-- Version: 1.0.0
-- ============================================================

-- ═══════════════════════════════════════════════════════════════════
-- ALERT RULES CONFIGURATION TABLE
-- ═══════════════════════════════════════════════════════════════════

-- Main configuration table for store-level alert rules
CREATE TABLE IF NOT EXISTS public.alert_rules (
    -- Primary Key
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Store reference (one config per store)
    store_id                UUID NOT NULL UNIQUE,
    
    -- ═══════════════════════════════════════════════════════════════
    -- ALERT TYPE TOGGLES
    -- ═══════════════════════════════════════════════════════════════
    
    -- High-Value Orders
    high_value_order_enabled            BOOLEAN NOT NULL DEFAULT TRUE,
    high_value_order_frequency          VARCHAR(20) NOT NULL DEFAULT 'real_time',
    high_value_order_channels           TEXT[] NOT NULL DEFAULT ARRAY['in_app', 'push'],
    
    -- Unusual Return Patterns
    unusual_returns_enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    unusual_returns_frequency           VARCHAR(20) NOT NULL DEFAULT 'batched_30m',
    unusual_returns_channels            TEXT[] NOT NULL DEFAULT ARRAY['in_app', 'email'],
    
    -- Inventory Depletion
    inventory_depletion_enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    inventory_depletion_frequency       VARCHAR(20) NOT NULL DEFAULT 'real_time',
    inventory_depletion_channels        TEXT[] NOT NULL DEFAULT ARRAY['in_app', 'email', 'push'],
    
    -- Conversion Rate Anomalies
    conversion_anomaly_enabled          BOOLEAN NOT NULL DEFAULT TRUE,
    conversion_anomaly_frequency        VARCHAR(20) NOT NULL DEFAULT 'batched_30m',
    conversion_anomaly_channels         TEXT[] NOT NULL DEFAULT ARRAY['in_app'],
    
    -- Customer Segment Changes
    customer_segment_enabled            BOOLEAN NOT NULL DEFAULT TRUE,
    customer_segment_frequency          VARCHAR(20) NOT NULL DEFAULT 'batched_1h',
    customer_segment_channels           TEXT[] NOT NULL DEFAULT ARRAY['in_app', 'email'],
    
    -- ═══════════════════════════════════════════════════════════════
    -- THRESHOLD CONFIGURATION
    -- ═══════════════════════════════════════════════════════════════
    
    -- High-Value Order Thresholds
    high_value_aov_multiplier          NUMERIC(4, 2) NOT NULL DEFAULT 1.5 CHECK (high_value_aov_multiplier >= 1.0),
    high_value_min_order_value         NUMERIC(12, 2) DEFAULT NULL, -- Optional absolute minimum
    
    -- Inventory Depletion Thresholds
    inventory_threshold_units           INTEGER NOT NULL DEFAULT 10 CHECK (inventory_threshold_units > 0),
    inventory_threshold_percent         NUMERIC(5, 2) NOT NULL DEFAULT 20.0 CHECK (inventory_threshold_percent > 0 AND inventory_threshold_percent <= 100),
    inventory_velocity_preset           VARCHAR(20) NOT NULL DEFAULT 'balanced', -- 'fast_mover', 'balanced', 'slow_mover'
    
    -- Conversion Anomaly Thresholds
    conversion_drop_threshold_percent   NUMERIC(5, 2) NOT NULL DEFAULT 15.0 CHECK (conversion_drop_threshold_percent > 0),
    conversion_rise_threshold_percent   NUMERIC(5, 2) NOT NULL DEFAULT 20.0 CHECK (conversion_rise_threshold_percent > 0),
    conversion_baseline_days            INTEGER NOT NULL DEFAULT 7 CHECK (conversion_baseline_days >= 1),
    conversion_sensitivity_preset       VARCHAR(20) NOT NULL DEFAULT 'moderate', -- 'conservative', 'moderate', 'aggressive'
    
    -- Returns Pattern Thresholds
    returns_spike_multiplier            NUMERIC(4, 2) NOT NULL DEFAULT 3.0 CHECK (returns_spike_multiplier >= 1.0),
    returns_spike_window_hours          INTEGER NOT NULL DEFAULT 24 CHECK (returns_spike_window_hours >= 1),
    returns_sensitivity_preset          VARCHAR(20) NOT NULL DEFAULT 'moderate', -- 'conservative', 'moderate', 'aggressive'
    
    -- Customer Segment Thresholds
    vip_inactive_days                   INTEGER NOT NULL DEFAULT 30 CHECK (vip_inactive_days >= 7),
    returning_inactive_days             INTEGER NOT NULL DEFAULT 45 CHECK (returning_inactive_days >= 14),
    customer_sensitivity_preset         VARCHAR(20) NOT NULL DEFAULT 'moderate', -- 'conservative', 'moderate', 'aggressive'
    
    -- ═══════════════════════════════════════════════════════════════
    -- NOTIFICATION FREQUENCY & DELIVERY
    -- ═══════════════════════════════════════════════════════════════
    
    -- Global delivery mode
    delivery_mode                       VARCHAR(20) NOT NULL DEFAULT 'real_time', -- 'real_time', 'hourly_digest', 'daily_summary'
    
    -- Throttling
    max_alerts_per_hour                 INTEGER NOT NULL DEFAULT 10 CHECK (max_alerts_per_hour > 0),
    max_alerts_per_day                  INTEGER NOT NULL DEFAULT 50 CHECK (max_alerts_per_day > 0),
    dedup_window_minutes                INTEGER NOT NULL DEFAULT 60 CHECK (dedup_window_minutes >= 15),
    
    -- Severity-based delivery
    critical_delivery_mode              VARCHAR(20) NOT NULL DEFAULT 'real_time',
    warning_delivery_mode               VARCHAR(20) NOT NULL DEFAULT 'batched',
    info_delivery_mode                  VARCHAR(20) NOT NULL DEFAULT 'batched',
    
    -- ═══════════════════════════════════════════════════════════════
    -- DO-NOT-DISTURB WINDOWS
    -- ═══════════════════════════════════════════════════════════════
    
    dnd_enabled                         BOOLEAN NOT NULL DEFAULT FALSE,
    dnd_start_time                      TIME DEFAULT NULL, -- e.g., '20:00:00'
    dnd_end_time                        TIME DEFAULT NULL, -- e.g., '08:00:00'
    dnd_timezone                        VARCHAR(50) DEFAULT 'UTC',
    dnd_allow_critical                   BOOLEAN NOT NULL DEFAULT TRUE, -- Critical alerts break through DND
    
    -- ═══════════════════════════════════════════════════════════════
    -- STORE METRICS (for intelligent presets)
    -- ═══════════════════════════════════════════════════════════════
    
    -- Cached store metrics for preset calculations
    store_avg_order_value               NUMERIC(12, 2) DEFAULT NULL,
    store_median_order_value            NUMERIC(12, 2) DEFAULT NULL,
    store_avg_conversion_rate           NUMERIC(6, 4) DEFAULT NULL,
    store_avg_return_rate               NUMERIC(6, 4) DEFAULT NULL,
    store_metrics_updated_at            TIMESTAMPTZ DEFAULT NULL,
    
    -- ═══════════════════════════════════════════════════════════════
    -- AUDIT & METADATA
    -- ═══════════════════════════════════════════════════════════════
    
    -- Version for optimistic locking
    version                             INTEGER NOT NULL DEFAULT 1,
    
    -- Timestamps
    created_at                          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Who last modified
    last_modified_by                    UUID DEFAULT NULL,
    
    -- Is this using default config (vs customized)
    is_customized                       BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Soft delete
    deleted_at                          TIMESTAMPTZ DEFAULT NULL
);

-- Comment for documentation
COMMENT ON TABLE public.alert_rules IS 
'Store-level alert configuration for the Real-Time Sales Alert System. Each store has one configuration record that controls alert types, thresholds, frequency, and delivery preferences.';

-- ═══════════════════════════════════════════════════════════════════
-- INDEXES
-- ═══════════════════════════════════════════════════════════════════

CREATE INDEX IF NOT EXISTS idx_alert_rules_store 
    ON public.alert_rules(store_id) 
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_alert_rules_modified 
    ON public.alert_rules(updated_at DESC) 
    WHERE deleted_at IS NULL;

-- ═══════════════════════════════════════════════════════════════════
-- TRIGGER FOR AUTOMATIC TIMESTAMP UPDATES
-- ═══════════════════════════════════════════════════════════════════

CREATE TRIGGER trg_alert_rules_updated_at
    BEFORE UPDATE ON public.alert_rules
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ═══════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE public.alert_rules ENABLE ROW LEVEL SECURITY;

-- Policy: Store owners can view their own store's alert config
CREATE POLICY "Store owners can view own alert config"
    ON public.alert_rules FOR SELECT
    USING (
        store_id IN (
            SELECT s.id 
            FROM public.stores s
            JOIN public.brand_managers bm ON bm.brand_id = s.brand_id
            WHERE bm.user_id = auth.uid() AND bm.is_active = TRUE
        )
    );

-- Policy: Store owners can insert their own store's alert config
CREATE POLICY "Store owners can insert own alert config"
    ON public.alert_rules FOR INSERT
    WITH CHECK (
        store_id IN (
            SELECT s.id 
            FROM public.stores s
            JOIN public.brand_managers bm ON bm.brand_id = s.brand_id
            WHERE bm.user_id = auth.uid() AND bm.is_active = TRUE
        )
    );

-- Policy: Store owners can update their own store's alert config
CREATE POLICY "Store owners can update own alert config"
    ON public.alert_rules FOR UPDATE
    USING (
        store_id IN (
            SELECT s.id 
            FROM public.stores s
            JOIN public.brand_managers bm ON bm.brand_id = s.brand_id
            WHERE bm.user_id = auth.uid() AND bm.is_active = TRUE
        )
    );

-- Policy: Service role has full access
CREATE POLICY "Service role has full alert config access"
    ON public.alert_rules FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- ═══════════════════════════════════════════════════════════════════
-- ALERT RULES HISTORY (Audit Trail)
-- ═══════════════════════════════════════════════════════════════════

-- Track changes to alert configuration for audit purposes
CREATE TABLE IF NOT EXISTS public.alert_rules_history (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_rules_id          UUID NOT NULL REFERENCES public.alert_rules(id) ON DELETE CASCADE,
    
    -- Snapshot of config at time of change
    config_snapshot         JSONB NOT NULL,
    
    -- What changed
    change_description      TEXT,
    changed_fields          TEXT[],
    
    -- Who made the change
    changed_by              UUID,
    
    -- When
    changed_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Version before change
    previous_version        INTEGER
);

CREATE INDEX IF NOT EXISTS idx_alert_rules_history_rules 
    ON public.alert_rules_history(alert_rules_id, changed_at DESC);

-- ═══════════════════════════════════════════════════════════════════
-- HELPER FUNCTIONS
-- ═══════════════════════════════════════════════════════════════════

-- Function to get or create default alert rules for a store
CREATE OR REPLACE FUNCTION public.get_or_create_alert_rules(p_store_id UUID)
RETURNS public.alert_rules AS $$
DECLARE
    v_rules public.alert_rules;
BEGIN
    -- Try to get existing rules
    SELECT * INTO v_rules 
    FROM public.alert_rules 
    WHERE store_id = p_store_id AND deleted_at IS NULL;
    
    -- If not found, create default
    IF NOT FOUND THEN
        INSERT INTO public.alert_rules (store_id)
        VALUES (p_store_id)
        RETURNING * INTO v_rules;
    END IF;
    
    RETURN v_rules;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if an alert should be delivered based on DND
CREATE OR REPLACE FUNCTION public.should_deliver_alert(
    p_store_id UUID,
    p_severity VARCHAR(20),
    p_current_time TIMESTAMPTZ DEFAULT NOW()
)
RETURNS BOOLEAN AS $$
DECLARE
    v_rules public.alert_rules;
    v_current_time TIME;
    v_in_dnd_window BOOLEAN;
BEGIN
    -- Get alert rules
    SELECT * INTO v_rules 
    FROM public.alert_rules 
    WHERE store_id = p_store_id AND deleted_at IS NULL;
    
    -- If no rules, allow delivery
    IF NOT FOUND THEN
        RETURN TRUE;
    END IF;
    
    -- If DND not enabled, allow delivery
    IF NOT v_rules.dnd_enabled THEN
        RETURN TRUE;
    END IF;
    
    -- If critical and DND allows critical, allow delivery
    IF p_severity = 'critical' AND v_rules.dnd_allow_critical THEN
        RETURN TRUE;
    END IF;
    
    -- Check if current time is in DND window
    v_current_time := p_current_time::TIME;
    
    -- Handle overnight DND windows (e.g., 20:00 - 08:00)
    IF v_rules.dnd_start_time > v_rules.dnd_end_time THEN
        -- Overnight window
        v_in_dnd_window := v_current_time >= v_rules.dnd_start_time 
                           OR v_current_time < v_rules.dnd_end_time;
    ELSE
        -- Same-day window
        v_in_dnd_window := v_current_time >= v_rules.dnd_start_time 
                           AND v_current_time < v_rules.dnd_end_time;
    END IF;
    
    -- Block delivery if in DND window
    RETURN NOT v_in_dnd_window;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if alert type is enabled
CREATE OR REPLACE FUNCTION public.is_alert_type_enabled(
    p_store_id UUID,
    p_alert_type VARCHAR(50)
)
RETURNS BOOLEAN AS $$
DECLARE
    v_enabled BOOLEAN;
BEGIN
    EXECUTE format('
        SELECT %I_enabled 
        FROM public.alert_rules 
        WHERE store_id = $1 AND deleted_at IS NULL
    ', p_alert_type)
    INTO v_enabled
    USING p_store_id;
    
    -- Default to enabled if no config found
    RETURN COALESCE(v_enabled, TRUE);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get threshold for alert type
CREATE OR REPLACE FUNCTION public.get_alert_threshold(
    p_store_id UUID,
    p_threshold_name VARCHAR(50)
)
RETURNS NUMERIC AS $$
DECLARE
    v_value NUMERIC;
BEGIN
    EXECUTE format('
        SELECT %I 
        FROM public.alert_rules 
        WHERE store_id = $1 AND deleted_at IS NULL
    ', p_threshold_name)
    INTO v_value
    USING p_store_id;
    
    -- Return default if no config found
    RETURN COALESCE(v_value, 
        CASE p_threshold_name
            WHEN 'high_value_aov_multiplier' THEN 1.5
            WHEN 'inventory_threshold_units' THEN 10
            WHEN 'conversion_drop_threshold_percent' THEN 15.0
            WHEN 'conversion_rise_threshold_percent' THEN 20.0
            WHEN 'returns_spike_multiplier' THEN 3.0
            WHEN 'vip_inactive_days' THEN 30
            WHEN 'returning_inactive_days' THEN 45
            ELSE 0
        END
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ═══════════════════════════════════════════════════════════════════
-- GRANT PERMISSIONS
-- ═══════════════════════════════════════════════════════════════════

GRANT SELECT, INSERT, UPDATE ON public.alert_rules TO authenticated;
GRANT SELECT ON public.alert_rules_history TO authenticated;
GRANT INSERT ON public.alert_rules_history TO authenticated;

-- Service role has full access
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;

-- ═══════════════════════════════════════════════════════════════════
-- INITIAL ANALYSIS
-- ═══════════════════════════════════════════════════════════════════

ANALYZE public.alert_rules;
