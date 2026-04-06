-- CONFIT Metrics Aggregation Engine - Database Migration
-- Creates tables for pre-computed metrics storage
-- Version: 001
-- Date: 2026-04-05

-- ═══════════════════════════════════════════════════════════════════
-- ENUMERATED TYPES
-- ═══════════════════════════════════════════════════════════════════

-- Check if enum exists before creating
DO $$ BEGIN
    CREATE TYPE metric_granularity_enum AS ENUM ('hourly', 'daily', 'weekly', 'monthly');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE metric_status_enum AS ENUM ('fresh', 'stale', 'computing', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ═══════════════════════════════════════════════════════════════════
-- HOURLY METRICS TABLE
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS hourly_metrics (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Store isolation (required for all queries)
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    
    -- Time dimension (hour granularity)
    hour_key TIMESTAMPTZ NOT NULL,
    date_key DATE NOT NULL,
    hour_of_day SMALLINT NOT NULL,
    day_of_week SMALLINT NOT NULL,
    
    -- Revenue Metrics
    total_revenue NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    revenue_delta NUMERIC(14, 2),
    revenue_change_pct NUMERIC(6, 2),
    
    -- Transaction Metrics
    transaction_count INTEGER NOT NULL DEFAULT 0,
    transaction_count_delta INTEGER,
    transaction_count_change_pct NUMERIC(6, 2),
    units_sold INTEGER NOT NULL DEFAULT 0,
    units_sold_delta INTEGER,
    avg_transaction_value NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    atv_delta NUMERIC(10, 2),
    atv_change_pct NUMERIC(6, 2),
    
    -- Profitability Metrics
    total_profit NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    total_profit_delta NUMERIC(14, 2),
    avg_profit_margin NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    avg_profit_margin_delta NUMERIC(5, 2),
    profit_margin_change_pct NUMERIC(6, 2),
    
    -- Return Metrics
    return_count INTEGER NOT NULL DEFAULT 0,
    return_count_delta INTEGER,
    return_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    return_amount_delta NUMERIC(12, 2),
    return_rate NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    return_rate_delta NUMERIC(5, 2),
    
    -- Customer Metrics
    unique_customers INTEGER NOT NULL DEFAULT 0,
    unique_customers_delta INTEGER,
    new_customers INTEGER NOT NULL DEFAULT 0,
    new_customers_delta INTEGER,
    returning_customers INTEGER NOT NULL DEFAULT 0,
    returning_customers_delta INTEGER,
    vip_customers INTEGER NOT NULL DEFAULT 0,
    vip_customers_delta INTEGER,
    
    -- Breakdown Data (JSONB)
    category_breakdown JSONB NOT NULL DEFAULT '[]'::jsonb,
    segment_breakdown JSONB NOT NULL DEFAULT '[]'::jsonb,
    top_products JSONB NOT NULL DEFAULT '[]'::jsonb,
    bottom_products JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Metadata
    status metric_status_enum NOT NULL DEFAULT 'fresh',
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    computation_time_ms INTEGER,
    rows_processed INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_hourly_metric_store_hour UNIQUE (store_id, hour_key),
    CONSTRAINT chk_hour_of_day CHECK (hour_of_day >= 0 AND hour_of_day <= 23),
    CONSTRAINT chk_day_of_week CHECK (day_of_week >= 0 AND day_of_week <= 6)
);

-- Indexes for hourly_metrics
CREATE INDEX IF NOT EXISTS ix_hourly_metrics_store_date 
    ON hourly_metrics (store_id, hour_key);

CREATE INDEX IF NOT EXISTS ix_hourly_metrics_stale 
    ON hourly_metrics (store_id, status, computed_at) 
    WHERE status = 'stale';

CREATE INDEX IF NOT EXISTS ix_hourly_metrics_recent 
    ON hourly_metrics (store_id, hour_key) 
    WHERE hour_key >= CURRENT_DATE - INTERVAL '7 days';

CREATE INDEX IF NOT EXISTS ix_hourly_metrics_date_key 
    ON hourly_metrics (store_id, date_key);

-- ═══════════════════════════════════════════════════════════════════
-- DAILY METRICS TABLE
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS daily_metrics (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Store isolation
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    
    -- Time dimension (day granularity)
    date_key DATE NOT NULL,
    year_key SMALLINT NOT NULL,
    month_key SMALLINT NOT NULL,
    week_key SMALLINT,
    day_of_week SMALLINT NOT NULL,
    day_of_month SMALLINT NOT NULL,
    is_weekend BOOLEAN NOT NULL DEFAULT FALSE,
    is_holiday BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Revenue Metrics
    total_revenue NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    revenue_delta NUMERIC(14, 2),
    revenue_change_pct NUMERIC(6, 2),
    
    -- Transaction Metrics
    transaction_count INTEGER NOT NULL DEFAULT 0,
    transaction_count_delta INTEGER,
    transaction_count_change_pct NUMERIC(6, 2),
    units_sold INTEGER NOT NULL DEFAULT 0,
    units_sold_delta INTEGER,
    avg_transaction_value NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    atv_delta NUMERIC(10, 2),
    atv_change_pct NUMERIC(6, 2),
    
    -- Profitability Metrics
    total_profit NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    total_profit_delta NUMERIC(14, 2),
    avg_profit_margin NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    avg_profit_margin_delta NUMERIC(5, 2),
    profit_margin_change_pct NUMERIC(6, 2),
    
    -- Return Metrics
    return_count INTEGER NOT NULL DEFAULT 0,
    return_count_delta INTEGER,
    return_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    return_amount_delta NUMERIC(12, 2),
    return_rate NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    return_rate_delta NUMERIC(5, 2),
    
    -- Customer Metrics
    unique_customers INTEGER NOT NULL DEFAULT 0,
    unique_customers_delta INTEGER,
    new_customers INTEGER NOT NULL DEFAULT 0,
    new_customers_delta INTEGER,
    returning_customers INTEGER NOT NULL DEFAULT 0,
    returning_customers_delta INTEGER,
    vip_customers INTEGER NOT NULL DEFAULT 0,
    vip_customers_delta INTEGER,
    
    -- Comparison values (pre-computed)
    previous_day_revenue NUMERIC(14, 2),
    previous_week_revenue NUMERIC(14, 2),
    previous_month_revenue NUMERIC(14, 2),
    
    -- Breakdown Data
    category_breakdown JSONB NOT NULL DEFAULT '[]'::jsonb,
    segment_breakdown JSONB NOT NULL DEFAULT '[]'::jsonb,
    top_products JSONB NOT NULL DEFAULT '[]'::jsonb,
    bottom_products JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Metadata
    status metric_status_enum NOT NULL DEFAULT 'fresh',
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    computation_time_ms INTEGER,
    rows_processed INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_daily_metric_store_date UNIQUE (store_id, date_key),
    CONSTRAINT chk_month_key CHECK (month_key >= 1 AND month_key <= 12),
    CONSTRAINT chk_day_of_month CHECK (day_of_month >= 1 AND day_of_month <= 31)
);

-- Indexes for daily_metrics
CREATE INDEX IF NOT EXISTS ix_daily_metrics_store_date 
    ON daily_metrics (store_id, date_key);

CREATE INDEX IF NOT EXISTS ix_daily_metrics_month 
    ON daily_metrics (store_id, year_key, month_key);

CREATE INDEX IF NOT EXISTS ix_daily_metrics_stale 
    ON daily_metrics (store_id, status, computed_at) 
    WHERE status = 'stale';

CREATE INDEX IF NOT EXISTS ix_daily_metrics_week 
    ON daily_metrics (store_id, year_key, week_key);

-- ═══════════════════════════════════════════════════════════════════
-- WEEKLY METRICS TABLE
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS weekly_metrics (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Store isolation
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    
    -- Time dimension (ISO week)
    year_key SMALLINT NOT NULL,
    week_key SMALLINT NOT NULL,
    week_start_date DATE NOT NULL,
    week_end_date DATE NOT NULL,
    
    -- Revenue Metrics
    total_revenue NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    revenue_delta NUMERIC(14, 2),
    revenue_change_pct NUMERIC(6, 2),
    
    -- Transaction Metrics
    transaction_count INTEGER NOT NULL DEFAULT 0,
    transaction_count_delta INTEGER,
    transaction_count_change_pct NUMERIC(6, 2),
    units_sold INTEGER NOT NULL DEFAULT 0,
    units_sold_delta INTEGER,
    avg_transaction_value NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    atv_delta NUMERIC(10, 2),
    atv_change_pct NUMERIC(6, 2),
    
    -- Profitability Metrics
    total_profit NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    total_profit_delta NUMERIC(14, 2),
    avg_profit_margin NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    avg_profit_margin_delta NUMERIC(5, 2),
    profit_margin_change_pct NUMERIC(6, 2),
    
    -- Return Metrics
    return_count INTEGER NOT NULL DEFAULT 0,
    return_count_delta INTEGER,
    return_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    return_amount_delta NUMERIC(12, 2),
    return_rate NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    return_rate_delta NUMERIC(5, 2),
    
    -- Customer Metrics
    unique_customers INTEGER NOT NULL DEFAULT 0,
    unique_customers_delta INTEGER,
    new_customers INTEGER NOT NULL DEFAULT 0,
    new_customers_delta INTEGER,
    returning_customers INTEGER NOT NULL DEFAULT 0,
    returning_customers_delta INTEGER,
    vip_customers INTEGER NOT NULL DEFAULT 0,
    vip_customers_delta INTEGER,
    
    -- Comparison values
    previous_week_revenue NUMERIC(14, 2),
    previous_year_week_revenue NUMERIC(14, 2),
    
    -- Breakdown Data
    category_breakdown JSONB NOT NULL DEFAULT '[]'::jsonb,
    segment_breakdown JSONB NOT NULL DEFAULT '[]'::jsonb,
    top_products JSONB NOT NULL DEFAULT '[]'::jsonb,
    bottom_products JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Metadata
    status metric_status_enum NOT NULL DEFAULT 'fresh',
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    computation_time_ms INTEGER,
    rows_processed INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_weekly_metric_store_week UNIQUE (store_id, year_key, week_key),
    CONSTRAINT chk_week_key CHECK (week_key >= 1 AND week_key <= 53)
);

-- Indexes for weekly_metrics
CREATE INDEX IF NOT EXISTS ix_weekly_metrics_store_week 
    ON weekly_metrics (store_id, year_key, week_key);

CREATE INDEX IF NOT EXISTS ix_weekly_metrics_year 
    ON weekly_metrics (store_id, year_key);

-- ═══════════════════════════════════════════════════════════════════
-- MONTHLY METRICS TABLE
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS monthly_metrics (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Store isolation
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    
    -- Time dimension (month)
    year_key SMALLINT NOT NULL,
    month_key SMALLINT NOT NULL,
    month_start_date DATE NOT NULL,
    month_end_date DATE NOT NULL,
    days_in_month SMALLINT NOT NULL,
    
    -- Revenue Metrics
    total_revenue NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    revenue_delta NUMERIC(14, 2),
    revenue_change_pct NUMERIC(6, 2),
    
    -- Transaction Metrics
    transaction_count INTEGER NOT NULL DEFAULT 0,
    transaction_count_delta INTEGER,
    transaction_count_change_pct NUMERIC(6, 2),
    units_sold INTEGER NOT NULL DEFAULT 0,
    units_sold_delta INTEGER,
    avg_transaction_value NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    atv_delta NUMERIC(10, 2),
    atv_change_pct NUMERIC(6, 2),
    
    -- Profitability Metrics
    total_profit NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    total_profit_delta NUMERIC(14, 2),
    avg_profit_margin NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    avg_profit_margin_delta NUMERIC(5, 2),
    profit_margin_change_pct NUMERIC(6, 2),
    
    -- Return Metrics
    return_count INTEGER NOT NULL DEFAULT 0,
    return_count_delta INTEGER,
    return_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    return_amount_delta NUMERIC(12, 2),
    return_rate NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    return_rate_delta NUMERIC(5, 2),
    
    -- Customer Metrics
    unique_customers INTEGER NOT NULL DEFAULT 0,
    unique_customers_delta INTEGER,
    new_customers INTEGER NOT NULL DEFAULT 0,
    new_customers_delta INTEGER,
    returning_customers INTEGER NOT NULL DEFAULT 0,
    returning_customers_delta INTEGER,
    vip_customers INTEGER NOT NULL DEFAULT 0,
    vip_customers_delta INTEGER,
    
    -- Comparison values
    previous_month_revenue NUMERIC(14, 2),
    previous_year_month_revenue NUMERIC(14, 2),
    
    -- YTD accumulator
    ytd_revenue NUMERIC(14, 2),
    ytd_transactions INTEGER,
    
    -- Breakdown Data
    category_breakdown JSONB NOT NULL DEFAULT '[]'::jsonb,
    segment_breakdown JSONB NOT NULL DEFAULT '[]'::jsonb,
    top_products JSONB NOT NULL DEFAULT '[]'::jsonb,
    bottom_products JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Metadata
    status metric_status_enum NOT NULL DEFAULT 'fresh',
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    computation_time_ms INTEGER,
    rows_processed INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_monthly_metric_store_month UNIQUE (store_id, year_key, month_key),
    CONSTRAINT chk_monthly_month_key CHECK (month_key >= 1 AND month_key <= 12)
);

-- Indexes for monthly_metrics
CREATE INDEX IF NOT EXISTS ix_monthly_metrics_store_month 
    ON monthly_metrics (store_id, year_key, month_key);

CREATE INDEX IF NOT EXISTS ix_monthly_metrics_year 
    ON monthly_metrics (store_id, year_key);

-- ═══════════════════════════════════════════════════════════════════
-- REAL-TIME KPI CACHE TABLE
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS realtime_kpi_cache (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Store isolation (one row per store)
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    
    -- Today's metrics
    today_revenue NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    today_transactions INTEGER NOT NULL DEFAULT 0,
    today_units_sold INTEGER NOT NULL DEFAULT 0,
    today_new_customers INTEGER NOT NULL DEFAULT 0,
    
    -- This week
    week_revenue NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    week_transactions INTEGER NOT NULL DEFAULT 0,
    
    -- This month
    month_revenue NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    month_transactions INTEGER NOT NULL DEFAULT 0,
    
    -- Comparison values
    yesterday_revenue NUMERIC(14, 2),
    last_week_revenue NUMERIC(14, 2),
    last_month_revenue NUMERIC(14, 2),
    
    -- Quick stats
    avg_margin_30d NUMERIC(5, 2),
    return_rate_30d NUMERIC(5, 2),
    
    -- Top performers
    top_category_today VARCHAR(50),
    top_product_today VARCHAR(255),
    
    -- Alerts
    low_stock_alerts INTEGER NOT NULL DEFAULT 0,
    high_return_alerts INTEGER NOT NULL DEFAULT 0,
    
    -- Metadata
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_transaction_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Constraint
    CONSTRAINT uq_realtime_kpi_store UNIQUE (store_id)
);

-- ═══════════════════════════════════════════════════════════════════
-- METRIC COMPUTATION LOG TABLE
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS metric_computation_logs (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Store (null for system-wide)
    store_id UUID REFERENCES stores(id) ON DELETE SET NULL,
    
    -- Granularity
    granularity metric_granularity_enum NOT NULL,
    
    -- Period
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    
    -- Computation details
    computation_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    rows_processed INTEGER NOT NULL DEFAULT 0,
    rows_inserted INTEGER NOT NULL DEFAULT 0,
    rows_updated INTEGER NOT NULL DEFAULT 0,
    computation_time_ms INTEGER NOT NULL,
    
    -- Error tracking
    error_message TEXT,
    error_stack TEXT,
    
    -- Metadata
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    computed_by VARCHAR(100)
);

-- Indexes for computation logs
CREATE INDEX IF NOT EXISTS ix_computation_logs_store_time 
    ON metric_computation_logs (store_id, computed_at);

CREATE INDEX IF NOT EXISTS ix_computation_logs_granularity 
    ON metric_computation_logs (granularity, computed_at);

-- ═══════════════════════════════════════════════════════════════════
-- METRIC UPDATE QUEUE TABLE
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS metric_update_queue (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Store
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    
    -- Target metric
    granularity metric_granularity_enum NOT NULL,
    hour_key TIMESTAMPTZ,
    date_key DATE,
    
    -- Delta values
    delta_revenue NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    delta_transactions INTEGER NOT NULL DEFAULT 0,
    delta_units INTEGER NOT NULL DEFAULT 0,
    delta_returns INTEGER NOT NULL DEFAULT 0,
    delta_return_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    
    -- Transaction references
    transaction_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    scheduled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for update queue
CREATE INDEX IF NOT EXISTS ix_metric_queue_pending 
    ON metric_update_queue (status, scheduled_at);

CREATE INDEX IF NOT EXISTS ix_metric_queue_store_hour 
    ON metric_update_queue (store_id, hour_key);

-- ═══════════════════════════════════════════════════════════════════
-- TRIGGER FOR UPDATED_AT
-- ═══════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all metric tables
DROP TRIGGER IF EXISTS update_hourly_metrics_updated_at ON hourly_metrics;
CREATE TRIGGER update_hourly_metrics_updated_at
    BEFORE UPDATE ON hourly_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_daily_metrics_updated_at ON daily_metrics;
CREATE TRIGGER update_daily_metrics_updated_at
    BEFORE UPDATE ON daily_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_weekly_metrics_updated_at ON weekly_metrics;
CREATE TRIGGER update_weekly_metrics_updated_at
    BEFORE UPDATE ON weekly_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_monthly_metrics_updated_at ON monthly_metrics;
CREATE TRIGGER update_monthly_metrics_updated_at
    BEFORE UPDATE ON monthly_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ═══════════════════════════════════════════════════════════════════
-- COMMENTS
-- ═══════════════════════════════════════════════════════════════════

COMMENT ON TABLE hourly_metrics IS 'Pre-computed hourly metrics for real-time dashboard updates. Retention: 7 days.';
COMMENT ON TABLE daily_metrics IS 'Pre-computed daily metrics rolled up from hourly. Retention: 2 years.';
COMMENT ON TABLE weekly_metrics IS 'Pre-computed weekly metrics (ISO week). Retention: 3 years.';
COMMENT ON TABLE monthly_metrics IS 'Pre-computed monthly metrics with YTD accumulators. Retention: 5 years.';
COMMENT ON TABLE realtime_kpi_cache IS 'Ultra-fast cache for real-time dashboard KPIs. Single row per store. TTL: 30 seconds.';
COMMENT ON TABLE metric_computation_logs IS 'Audit log of metric computation runs for monitoring and debugging.';
COMMENT ON TABLE metric_update_queue IS 'Queue for debounced metric updates from streaming events.';
