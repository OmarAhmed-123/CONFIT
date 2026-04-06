-- ============================================================
-- CONFIT — Sales Analytics Schema for Store Owner Dashboard
-- Created: 2026-04-10
-- Description: Production-grade sales transaction analytics engine
-- Version: 1.0.0
-- ============================================================

-- ═══════════════════════════════════════════════════════════════════
-- ENUMERATED TYPES FOR SALES ANALYTICS
-- ═══════════════════════════════════════════════════════════════════

-- Product category enum
CREATE TYPE sales_category_enum AS ENUM (
    'Clothes', 'Shoes', 'Accessories', 'Full Outfit'
);

-- Customer segment enum
CREATE TYPE customer_segment_enum AS ENUM (
    'New Customer', 'Returning', 'VIP', 'Wholesale'
);

-- Return status enum
CREATE TYPE return_status_enum AS ENUM (
    'Completed', 'Returned', 'Pending Return'
);

-- ═══════════════════════════════════════════════════════════════════
-- SALES TRANSACTIONS TABLE (Partitioned by storeId)
-- ═══════════════════════════════════════════════════════════════════

-- Create parent table for partitioning
CREATE TABLE IF NOT EXISTS public.sales_transactions (
    -- Primary Key (UUID for distributed systems compatibility)
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Store isolation (partition key)
    store_id                UUID NOT NULL,
    
    -- Product information
    product_name            VARCHAR(255) NOT NULL,
    category                sales_category_enum NOT NULL,
    product_type            VARCHAR(100),
    
    -- Pricing (DECIMAL for precise financial calculations)
    price                   NUMERIC(12, 2) NOT NULL CHECK (price >= 0),
    quantity                INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    total_amount            NUMERIC(12, 2) GENERATED ALWAYS AS (price * quantity) STORED,
    
    -- Customer information
    customer_name           VARCHAR(255),
    customer_segment        customer_segment_enum NOT NULL DEFAULT 'New Customer',
    customer_id             UUID,  -- Optional reference to users table
    
    -- Transaction details
    sale_date               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    profit_margin           NUMERIC(5, 2) CHECK (profit_margin >= 0 AND profit_margin <= 100),
    return_status           return_status_enum NOT NULL DEFAULT 'Completed',
    
    -- Order reference (links to existing orders table)
    order_id                VARCHAR(64),
    order_item_id           INTEGER,
    
    -- Additional metadata
    channel                 VARCHAR(50) DEFAULT 'in_store',  -- in_store, online, mobile
    region                  VARCHAR(100),
    notes                   TEXT,
    metadata                JSONB NOT NULL DEFAULT '{}',
    
    -- Audit fields
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Soft delete support
    deleted_at              TIMESTAMPTZ,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Version for optimistic locking
    version                 INTEGER NOT NULL DEFAULT 1
) PARTITION BY HASH (store_id);

-- Comment for documentation
COMMENT ON TABLE public.sales_transactions IS 
'Partitioned sales transaction table for store analytics. Each partition contains data for a subset of stores, enabling efficient store-scoped queries and data isolation.';

-- ═══════════════════════════════════════════════════════════════════
-- CREATE DEFAULT PARTITION (catches any unpartitioned data)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.sales_transactions_default
    PARTITION OF public.sales_transactions DEFAULT;

-- ═══════════════════════════════════════════════════════════════════
-- CREATE INITIAL PARTITIONS (4 partitions for hash distribution)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.sales_transactions_p0
    PARTITION OF public.sales_transactions
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);

CREATE TABLE IF NOT EXISTS public.sales_transactions_p1
    PARTITION OF public.sales_transactions
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);

CREATE TABLE IF NOT EXISTS public.sales_transactions_p2
    PARTITION OF public.sales_transactions
    FOR VALUES WITH (MODULUS 4, REMAINDER 2);

CREATE TABLE IF NOT EXISTS public.sales_transactions_p3
    PARTITION OF public.sales_transactions
    FOR VALUES WITH (MODULUS 4, REMAINDER 3);

-- ═══════════════════════════════════════════════════════════════════
-- INDEXES FOR QUERY OPTIMIZATION
-- ═══════════════════════════════════════════════════════════════════

-- Primary lookup index (storeId + saleDate for partition pruning + range queries)
CREATE INDEX IF NOT EXISTS idx_sales_store_date 
    ON public.sales_transactions(store_id, sale_date DESC)
    WHERE deleted_at IS NULL AND is_active = TRUE;

-- Composite index for multi-field filtering (category + date + segment)
CREATE INDEX IF NOT EXISTS idx_sales_category_date_segment 
    ON public.sales_transactions(store_id, category, sale_date DESC, customer_segment)
    WHERE deleted_at IS NULL AND is_active = TRUE;

-- Price range filtering index
CREATE INDEX IF NOT EXISTS idx_sales_price_range 
    ON public.sales_transactions(store_id, price, sale_date DESC)
    WHERE deleted_at IS NULL AND is_active = TRUE;

-- Customer segment filtering index
CREATE INDEX IF NOT EXISTS idx_sales_segment 
    ON public.sales_transactions(store_id, customer_segment, sale_date DESC)
    WHERE deleted_at IS NULL AND is_active = TRUE;

-- Return status filtering index
CREATE INDEX IF NOT EXISTS idx_sales_return_status 
    ON public.sales_transactions(store_id, return_status, sale_date DESC)
    WHERE deleted_at IS NULL AND is_active = TRUE;

-- Sorting indexes (for ORDER BY operations)
CREATE INDEX IF NOT EXISTS idx_sales_sort_date 
    ON public.sales_transactions(store_id, sale_date DESC, id)
    WHERE deleted_at IS NULL AND is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_sales_sort_profit 
    ON public.sales_transactions(store_id, profit_margin DESC, sale_date DESC)
    WHERE deleted_at IS NULL AND is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_sales_sort_price 
    ON public.sales_transactions(store_id, price DESC, sale_date DESC)
    WHERE deleted_at IS NULL AND is_active = TRUE;

-- Covering index for common dashboard queries (reduces table lookups)
CREATE INDEX IF NOT EXISTS idx_sales_dashboard_covering 
    ON public.sales_transactions(store_id, sale_date DESC)
    INCLUDE (category, customer_segment, price, quantity, total_amount, profit_margin, return_status)
    WHERE deleted_at IS NULL AND is_active = TRUE;

-- Order reference index
CREATE INDEX IF NOT EXISTS idx_sales_order_ref 
    ON public.sales_transactions(order_id)
    WHERE order_id IS NOT NULL;

-- Customer lookup index
CREATE INDEX IF NOT EXISTS idx_sales_customer 
    ON public.sales_transactions(customer_id, sale_date DESC)
    WHERE customer_id IS NOT NULL AND deleted_at IS NULL;

-- ═══════════════════════════════════════════════════════════════════
-- MATERIALIZED VIEWS FOR ANALYTICS
-- ═══════════════════════════════════════════════════════════════════

-- Daily sales summary by store and category
CREATE MATERIALIZED VIEW IF NOT EXISTS public.mv_daily_sales_by_category AS
SELECT 
    store_id,
    DATE(sale_date) AS sale_date,
    category,
    COUNT(*) AS transaction_count,
    SUM(quantity) AS units_sold,
    SUM(total_amount) AS total_revenue,
    AVG(price) AS avg_price,
    AVG(profit_margin) AS avg_profit_margin,
    COUNT(*) FILTER (WHERE return_status = 'Returned') AS returns_count,
    SUM(total_amount) FILTER (WHERE return_status = 'Returned') AS returns_amount
FROM public.sales_transactions
WHERE deleted_at IS NULL AND is_active = TRUE
GROUP BY store_id, DATE(sale_date), category
WITH DATA;

-- Index on materialized view for fast lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_daily_sales_pk 
    ON public.mv_daily_sales_by_category(store_id, sale_date, category);

CREATE INDEX IF NOT EXISTS idx_mv_daily_sales_date 
    ON public.mv_daily_sales_by_category(sale_date DESC);

-- Monthly sales summary by store and customer segment
CREATE MATERIALIZED VIEW IF NOT EXISTS public.mv_monthly_sales_by_segment AS
SELECT 
    store_id,
    DATE_TRUNC('month', sale_date) AS month,
    customer_segment,
    COUNT(*) AS transaction_count,
    COUNT(DISTINCT customer_id) AS unique_customers,
    SUM(quantity) AS units_sold,
    SUM(total_amount) AS total_revenue,
    AVG(total_amount) AS avg_order_value,
    AVG(profit_margin) AS avg_profit_margin
FROM public.sales_transactions
WHERE deleted_at IS NULL AND is_active = TRUE
GROUP BY store_id, DATE_TRUNC('month', sale_date), customer_segment
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_monthly_segment_pk 
    ON public.mv_monthly_sales_by_segment(store_id, month, customer_segment);

-- Real-time store metrics (refreshed frequently)
CREATE MATERIALIZED VIEW IF NOT EXISTS public.mv_store_realtime_metrics AS
SELECT 
    store_id,
    NOW() AS last_updated,
    COUNT(*) FILTER (WHERE sale_date >= CURRENT_DATE) AS today_transactions,
    SUM(total_amount) FILTER (WHERE sale_date >= CURRENT_DATE) AS today_revenue,
    COUNT(*) FILTER (WHERE sale_date >= CURRENT_DATE - INTERVAL '7 days') AS week_transactions,
    SUM(total_amount) FILTER (WHERE sale_date >= CURRENT_DATE - INTERVAL '7 days') AS week_revenue,
    COUNT(*) FILTER (WHERE sale_date >= DATE_TRUNC('month', CURRENT_DATE)) AS month_transactions,
    SUM(total_amount) FILTER (WHERE sale_date >= DATE_TRUNC('month', CURRENT_DATE)) AS month_revenue,
    AVG(profit_margin) FILTER (WHERE sale_date >= CURRENT_DATE - INTERVAL '30 days') AS avg_margin_30d
FROM public.sales_transactions
WHERE deleted_at IS NULL AND is_active = TRUE
GROUP BY store_id
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_realtime_store_pk 
    ON public.mv_store_realtime_metrics(store_id);

-- ═══════════════════════════════════════════════════════════════════
-- TRIGGERS FOR AUTOMATIC TIMESTAMP UPDATES
-- ═══════════════════════════════════════════════════════════════════

-- Create update trigger function if not exists
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to sales_transactions
CREATE TRIGGER trg_sales_transactions_updated_at
    BEFORE UPDATE ON public.sales_transactions
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ═══════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY FOR STORE ISOLATION
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE public.sales_transactions ENABLE ROW LEVEL SECURITY;

-- Policy: Store owners can only see their own store's data
CREATE POLICY "Store owners can view own store sales"
    ON public.sales_transactions FOR SELECT
    USING (
        store_id IN (
            SELECT s.id 
            FROM public.stores s
            JOIN public.brand_managers bm ON bm.brand_id = s.brand_id
            WHERE bm.user_id = auth.uid() AND bm.is_active = TRUE
        )
    );

-- Policy: Service role can access all data
CREATE POLICY "Service role has full access"
    ON public.sales_transactions FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- ═══════════════════════════════════════════════════════════════════
-- STORE ANALYTICS CACHE TABLE
-- ═══════════════════════════════════════════════════════════════════

-- Pre-computed analytics for dashboard widgets
CREATE TABLE IF NOT EXISTS public.store_analytics_cache (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id                UUID NOT NULL UNIQUE,
    
    -- Period identifiers
    period_type             VARCHAR(20) NOT NULL DEFAULT 'current',  -- current, previous, ytd
    
    -- Revenue metrics
    total_revenue           NUMERIC(14, 2) DEFAULT 0,
    revenue_change_pct      NUMERIC(6, 2),
    avg_order_value         NUMERIC(10, 2) DEFAULT 0,
    aov_change_pct          NUMERIC(6, 2),
    
    -- Transaction metrics
    total_transactions      INTEGER DEFAULT 0,
    transactions_change_pct NUMERIC(6, 2),
    total_units_sold        INTEGER DEFAULT 0,
    
    -- Profit metrics
    total_profit            NUMERIC(14, 2) DEFAULT 0,
    avg_profit_margin       NUMERIC(5, 2) DEFAULT 0,
    profit_change_pct       NUMERIC(6, 2),
    
    -- Customer metrics
    unique_customers        INTEGER DEFAULT 0,
    new_customers           INTEGER DEFAULT 0,
    returning_customers     INTEGER DEFAULT 0,
    vip_customers           INTEGER DEFAULT 0,
    
    -- Return metrics
    return_rate             NUMERIC(5, 2) DEFAULT 0,
    returns_count           INTEGER DEFAULT 0,
    returns_amount          NUMERIC(12, 2) DEFAULT 0,
    
    -- Category breakdown (JSONB for flexibility)
    category_breakdown      JSONB NOT NULL DEFAULT '[]',
    
    -- Top products
    top_products            JSONB NOT NULL DEFAULT '[]',
    
    -- Segment breakdown
    segment_breakdown       JSONB NOT NULL DEFAULT '[]',
    
    -- Time period
    period_start            TIMESTAMPTZ,
    period_end              TIMESTAMPTZ,
    
    -- Cache metadata
    computed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at              TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '5 minutes',
    is_stale                BOOLEAN NOT NULL DEFAULT FALSE,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for cache lookups
CREATE INDEX IF NOT EXISTS idx_analytics_cache_store 
    ON public.store_analytics_cache(store_id);

CREATE INDEX IF NOT EXISTS idx_analytics_cache_expires 
    ON public.store_analytics_cache(expires_at)
    WHERE is_stale = FALSE;

-- Trigger for updated_at
CREATE TRIGGER trg_analytics_cache_updated_at
    BEFORE UPDATE ON public.store_analytics_cache
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- RLS for analytics cache
ALTER TABLE public.store_analytics_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Store owners can view own store analytics"
    ON public.store_analytics_cache FOR SELECT
    USING (
        store_id IN (
            SELECT s.id 
            FROM public.stores s
            JOIN public.brand_managers bm ON bm.brand_id = s.brand_id
            WHERE bm.user_id = auth.uid() AND bm.is_active = TRUE
        )
    );

-- ═══════════════════════════════════════════════════════════════════
-- SALES DATA INGESTION QUEUE
-- ═══════════════════════════════════════════════════════════════════

-- Queue table for batch ingestion
CREATE TABLE IF NOT EXISTS public.sales_ingestion_queue (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id                UUID NOT NULL,
    
    -- Batch identifier
    batch_id                UUID NOT NULL DEFAULT uuid_generate_v4(),
    batch_sequence          INTEGER NOT NULL DEFAULT 1,
    
    -- Raw payload
    payload                 JSONB NOT NULL,
    payload_hash            VARCHAR(64) GENERATED ALWAYS AS (
        encode(sha256(convert_to(payload::text, 'UTF8')), 'hex')
    ) STORED,
    
    -- Processing status
    status                  VARCHAR(20) NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    attempts                INTEGER NOT NULL DEFAULT 0,
    max_attempts            INTEGER NOT NULL DEFAULT 3,
    last_error              TEXT,
    
    -- Processing metadata
    processed_at            TIMESTAMPTZ,
    processed_by            VARCHAR(100),
    rows_inserted           INTEGER DEFAULT 0,
    
    -- Deduplication
    idempotency_key         VARCHAR(128),
    
    -- Audit
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for ingestion queue
CREATE INDEX IF NOT EXISTS idx_ingestion_status 
    ON public.sales_ingestion_queue(status, created_at)
    WHERE status IN ('pending', 'processing');

CREATE INDEX IF NOT EXISTS idx_ingestion_batch 
    ON public.sales_ingestion_queue(batch_id, batch_sequence);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ingestion_idempotency 
    ON public.sales_ingestion_queue(idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_ingestion_store 
    ON public.sales_ingestion_queue(store_id, created_at DESC);

-- ═══════════════════════════════════════════════════════════════════
-- FUNCTIONS FOR QUERY OPTIMIZATION
-- ═══════════════════════════════════════════════════════════════════

-- Function to get date range from preset
CREATE OR REPLACE FUNCTION public.get_date_range(preset TEXT)
RETURNS TSTZRANGE AS $$
DECLARE
    result TSTZRANGE;
BEGIN
    CASE preset
        WHEN 'TODAY' THEN
            result := TSTZRANGE(CURRENT_DATE, CURRENT_DATE + INTERVAL '1 day');
        WHEN 'YESTERDAY' THEN
            result := TSTZRANGE(CURRENT_DATE - INTERVAL '1 day', CURRENT_DATE);
        WHEN 'THIS_WEEK' THEN
            result := TSTZRANGE(DATE_TRUNC('week', CURRENT_DATE), CURRENT_DATE + INTERVAL '1 day');
        WHEN 'LAST_WEEK' THEN
            result := TSTZRANGE(
                DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week',
                DATE_TRUNC('week', CURRENT_DATE)
            );
        WHEN 'THIS_MONTH' THEN
            result := TSTZRANGE(DATE_TRUNC('month', CURRENT_DATE), CURRENT_DATE + INTERVAL '1 day');
        WHEN 'LAST_MONTH' THEN
            result := TSTZRANGE(
                DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month',
                DATE_TRUNC('month', CURRENT_DATE)
            );
        WHEN 'LAST_7_DAYS' THEN
            result := TSTZRANGE(CURRENT_DATE - INTERVAL '7 days', CURRENT_DATE + INTERVAL '1 day');
        WHEN 'LAST_30_DAYS' THEN
            result := TSTZRANGE(CURRENT_DATE - INTERVAL '30 days', CURRENT_DATE + INTERVAL '1 day');
        WHEN 'LAST_90_DAYS' THEN
            result := TSTZRANGE(CURRENT_DATE - INTERVAL '90 days', CURRENT_DATE + INTERVAL '1 day');
        WHEN 'YTD' THEN
            result := TSTZRANGE(DATE_TRUNC('year', CURRENT_DATE), CURRENT_DATE + INTERVAL '1 day');
        ELSE
            RAISE EXCEPTION 'Unknown date preset: %', preset;
    END CASE;
    RETURN result;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to refresh materialized views
CREATE OR REPLACE FUNCTION public.refresh_sales_analytics_views(
    p_store_id UUID DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    -- Refresh daily summary
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_daily_sales_by_category;
    
    -- Refresh monthly summary
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_monthly_sales_by_segment;
    
    -- Refresh realtime metrics
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_store_realtime_metrics;
END;
$$ LANGUAGE plpgsql;

-- Function to compute and cache store analytics
CREATE OR REPLACE FUNCTION public.compute_store_analytics(
    p_store_id UUID,
    p_period_start TIMESTAMPTZ DEFAULT NULL,
    p_period_end TIMESTAMPTZ DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_cache_id UUID;
    v_period_start TIMESTAMPTZ := COALESCE(p_period_start, DATE_TRUNC('month', CURRENT_DATE));
    v_period_end TIMESTAMPTZ := COALESCE(p_period_end, NOW());
BEGIN
    -- Insert or update analytics cache
    INSERT INTO public.store_analytics_cache (
        store_id,
        period_type,
        period_start,
        period_end,
        total_revenue,
        total_transactions,
        total_units_sold,
        avg_order_value,
        avg_profit_margin,
        unique_customers,
        new_customers,
        returning_customers,
        vip_customers,
        return_rate,
        returns_count,
        returns_amount,
        category_breakdown,
        segment_breakdown,
        computed_at,
        expires_at
    )
    SELECT 
        p_store_id,
        'current',
        v_period_start,
        v_period_end,
        COALESCE(SUM(total_amount), 0),
        COUNT(*),
        COALESCE(SUM(quantity), 0),
        COALESCE(AVG(total_amount), 0),
        COALESCE(AVG(profit_margin), 0),
        COUNT(DISTINCT customer_id),
        COUNT(*) FILTER (WHERE customer_segment = 'New Customer'),
        COUNT(*) FILTER (WHERE customer_segment = 'Returning'),
        COUNT(*) FILTER (WHERE customer_segment = 'VIP'),
        CASE WHEN COUNT(*) > 0 
            THEN ROUND(100.0 * COUNT(*) FILTER (WHERE return_status IN ('Returned', 'Pending Return')) / COUNT(*), 2)
            ELSE 0 
        END,
        COUNT(*) FILTER (WHERE return_status = 'Returned'),
        COALESCE(SUM(total_amount) FILTER (WHERE return_status = 'Returned'), 0),
        (
            SELECT jsonb_agg(jsonb_build_object(
                'category', category,
                'revenue', total_revenue,
                'units', units_sold,
                'transactions', transaction_count
            ))
            FROM (
                SELECT 
                    category,
                    SUM(total_amount) AS total_revenue,
                    SUM(quantity) AS units_sold,
                    COUNT(*) AS transaction_count
                FROM public.sales_transactions
                WHERE store_id = p_store_id
                    AND sale_date >= v_period_start
                    AND sale_date <= v_period_end
                    AND deleted_at IS NULL
                    AND is_active = TRUE
                GROUP BY category
            ) cat_data
        ),
        (
            SELECT jsonb_agg(jsonb_build_object(
                'segment', customer_segment,
                'revenue', total_revenue,
                'customers', unique_customers,
                'transactions', transaction_count
            ))
            FROM (
                SELECT 
                    customer_segment,
                    SUM(total_amount) AS total_revenue,
                    COUNT(DISTINCT customer_id) AS unique_customers,
                    COUNT(*) AS transaction_count
                FROM public.sales_transactions
                WHERE store_id = p_store_id
                    AND sale_date >= v_period_start
                    AND sale_date <= v_period_end
                    AND deleted_at IS NULL
                    AND is_active = TRUE
                GROUP BY customer_segment
            ) seg_data
        ),
        NOW(),
        NOW() + INTERVAL '5 minutes'
    FROM public.sales_transactions
    WHERE store_id = p_store_id
        AND sale_date >= v_period_start
        AND sale_date <= v_period_end
        AND deleted_at IS NULL
        AND is_active = TRUE
    ON CONFLICT (store_id) 
    DO UPDATE SET
        total_revenue = EXCLUDED.total_revenue,
        total_transactions = EXCLUDED.total_transactions,
        total_units_sold = EXCLUDED.total_units_sold,
        avg_order_value = EXCLUDED.avg_order_value,
        avg_profit_margin = EXCLUDED.avg_profit_margin,
        unique_customers = EXCLUDED.unique_customers,
        new_customers = EXCLUDED.new_customers,
        returning_customers = EXCLUDED.returning_customers,
        vip_customers = EXCLUDED.vip_customers,
        return_rate = EXCLUDED.return_rate,
        returns_count = EXCLUDED.returns_count,
        returns_amount = EXCLUDED.returns_amount,
        category_breakdown = EXCLUDED.category_breakdown,
        segment_breakdown = EXCLUDED.segment_breakdown,
        period_start = EXCLUDED.period_start,
        period_end = EXCLUDED.period_end,
        computed_at = EXCLUDED.computed_at,
        expires_at = EXCLUDED.expires_at,
        is_stale = FALSE,
        updated_at = NOW()
    RETURNING id INTO v_cache_id;
    
    RETURN v_cache_id;
END;
$$ LANGUAGE plpgsql;

-- ═══════════════════════════════════════════════════════════════════
-- GRANT PERMISSIONS
-- ═══════════════════════════════════════════════════════════════════

GRANT SELECT, INSERT, UPDATE, DELETE ON public.sales_transactions TO authenticated;
GRANT SELECT ON public.mv_daily_sales_by_category TO authenticated;
GRANT SELECT ON public.mv_monthly_sales_by_segment TO authenticated;
GRANT SELECT ON public.mv_store_realtime_metrics TO authenticated;
GRANT SELECT ON public.store_analytics_cache TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.sales_ingestion_queue TO authenticated;

-- Service role has full access
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;

-- ═══════════════════════════════════════════════════════════════════
-- INITIAL ANALYSIS
-- ═══════════════════════════════════════════════════════════════════

ANALYZE public.sales_transactions;
