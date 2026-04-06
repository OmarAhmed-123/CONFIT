# CONFIT Sales Analytics Database Architecture

## Executive Summary

This document defines the production-grade database layer powering the Store Owner Dashboard's Sales Analytics API. The architecture prioritizes:

- **Store-scoped data isolation** via partitioning and RLS
- **Sub-500ms query performance** for common dashboard operations
- **Real-time data freshness** with controlled staleness windows
- **Horizontal scalability** as store count and transaction volume grow

---

## 1. Data Model & Schema Design

### 1.1 Primary Key Strategy

**Decision: UUID primary keys**

| Aspect | UUID | Auto-increment |
|--------|------|----------------|
| Distributed systems | ✅ No coordination needed | ❌ Requires central sequence |
| Partitioning | ✅ Works across partitions | ❌ Conflicts between partitions |
| Security | ✅ Non-guessable | ❌ Exposes row count |
| Storage | ⚠️ 16 bytes | ✅ 4-8 bytes |
| Index fragmentation | ⚠️ Random inserts | ✅ Sequential inserts |

**Justification**: UUID is required for:
1. Hash partitioning compatibility (deterministic distribution)
2. Future multi-region deployment without key conflicts
3. Security (transaction IDs not guessable by store owners)

### 1.2 Table Schema

```sql
-- Core sales_transactions table (partitioned)
CREATE TABLE public.sales_transactions (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id                UUID NOT NULL,                    -- Partition key
    product_name            VARCHAR(255) NOT NULL,
    category                sales_category_enum NOT NULL,     -- ENUM for storage efficiency
    product_type            VARCHAR(100),
    price                   NUMERIC(12, 2) NOT NULL,          -- DECIMAL for financial precision
    quantity                INTEGER NOT NULL DEFAULT 1,
    total_amount            NUMERIC(12, 2) GENERATED ALWAYS AS (price * quantity) STORED,
    customer_name           VARCHAR(255),
    customer_segment        customer_segment_enum NOT NULL DEFAULT 'New Customer',
    customer_id             UUID,
    sale_date               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    profit_margin           NUMERIC(5, 2) CHECK (profit_margin >= 0 AND profit_margin <= 100),
    return_status           return_status_enum NOT NULL DEFAULT 'Completed',
    order_id                VARCHAR(64),
    order_item_id           INTEGER,
    channel                 VARCHAR(50) DEFAULT 'in_store',
    region                  VARCHAR(100),
    notes                   TEXT,
    metadata                JSONB NOT NULL DEFAULT '{}',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at              TIMESTAMPTZ,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    version                 INTEGER NOT NULL DEFAULT 1
) PARTITION BY HASH (store_id);
```

### 1.3 Data Type Rationale

| Column | Type | Rationale |
|--------|------|-----------|
| `price`, `total_amount` | `NUMERIC(12,2)` | Exact decimal arithmetic for financial data, avoids floating-point errors |
| `profit_margin` | `NUMERIC(5,2)` | Percentage 0-100 with 2 decimal precision |
| `category`, `segment`, `return_status` | `ENUM` | ~4 bytes vs 20+ for VARCHAR, constraint enforcement |
| `sale_date` | `TIMESTAMPTZ` | Timezone-aware for global stores |
| `metadata` | `JSONB` | Binary JSON for fast querying, flexible schema extension |
| `store_id` | `UUID` | Partition key, foreign key to stores table |

### 1.4 Constraints

```sql
-- Data integrity constraints
CHECK (price >= 0)                    -- No negative prices
CHECK (quantity > 0)                  -- At least 1 item per transaction
CHECK (profit_margin >= 0 AND profit_margin <= 100)  -- Valid percentage

-- Generated column (computed, indexed)
total_amount NUMERIC(12, 2) GENERATED ALWAYS AS (price * quantity) STORED
```

---

## 2. Indexing Strategy

### 2.1 Index Design Principles

1. **Partition-aware indexing**: All indexes include `store_id` as leading column for partition pruning
2. **Partial indexes**: Exclude soft-deleted rows to reduce index size by ~30%
3. **Covering indexes**: Include frequently accessed columns to avoid table lookups
4. **Composite ordering**: Match query patterns (filter → sort → paginate)

### 2.2 Index Specifications

#### Primary Lookup Index
```sql
CREATE INDEX idx_sales_store_date 
    ON sales_transactions(store_id, sale_date DESC)
    WHERE deleted_at IS NULL AND is_active = TRUE;
```
- **Type**: B-tree (default)
- **Purpose**: Partition pruning + date range queries
- **Cardinality**: High selectivity per store
- **Use case**: Default dashboard view (recent sales first)

#### Multi-Field Filtering Index
```sql
CREATE INDEX idx_sales_category_date_segment 
    ON sales_transactions(store_id, category, sale_date DESC, customer_segment)
    WHERE deleted_at IS NULL AND is_active = TRUE;
```
- **Column order rationale**:
  1. `store_id` - Partition pruning (mandatory)
  2. `category` - High cardinality filter (4 values)
  3. `sale_date` - Range/sort support
  4. `customer_segment` - Additional filter support
- **Use case**: "Show me Shoes sales this week for VIP customers"

#### Covering Index for Dashboard
```sql
CREATE INDEX idx_sales_dashboard_covering 
    ON sales_transactions(store_id, sale_date DESC)
    INCLUDE (category, customer_segment, price, quantity, total_amount, profit_margin, return_status)
    WHERE deleted_at IS NULL AND is_active = TRUE;
```
- **Purpose**: Index-only scan for common dashboard queries
- **Trade-off**: Larger index size (~2x) but eliminates table lookups
- **Expected improvement**: 40-60% faster for list queries

#### Sorting Indexes
```sql
-- For ORDER BY sale_date DESC
CREATE INDEX idx_sales_sort_date ON sales_transactions(store_id, sale_date DESC, id);

-- For ORDER BY profit_margin DESC
CREATE INDEX idx_sales_sort_profit ON sales_transactions(store_id, profit_margin DESC, sale_date DESC);

-- For ORDER BY price DESC
CREATE INDEX idx_sales_sort_price ON sales_transactions(store_id, price DESC, sale_date DESC);
```
- **Purpose**: Support API sort operations without filesort
- **Includes `id`**: For stable pagination cursors

### 2.3 Index Size Estimates

| Index | Estimated Size (per 1M rows) | Row Estimate |
|-------|------------------------------|--------------|
| `idx_sales_store_date` | ~50 MB | Full table |
| `idx_sales_category_date_segment` | ~60 MB | Full table |
| `idx_sales_dashboard_covering` | ~120 MB | Full table |
| `idx_sales_sort_*` (3 indexes) | ~45 MB each | Full table |

**Total index overhead**: ~315 MB per 1M transactions (~40% of table size)

### 2.4 Write Performance Impact

| Operation | Without Indexes | With All Indexes | Overhead |
|-----------|-----------------|------------------|----------|
| Single INSERT | ~0.5ms | ~2.5ms | 5x slower |
| Batch INSERT (1000 rows) | ~50ms | ~200ms | 4x slower |

**Mitigation**: Use batch inserts via ingestion queue (see Section 6)

---

## 3. Data Partitioning Strategy

### 3.1 Partitioning Approach: Hash Partitioning by `store_id`

**Why Hash Partitioning?**

| Approach | Pros | Cons |
|----------|------|------|
| **Hash by store_id** | Even distribution, automatic routing, no hotspots | Cannot prune by date range across stores |
| Range by sale_date | Time-based pruning, easy archival | Hot partition (current month), uneven sizes |
| List by store_id | Explicit store isolation | Manual management, rebalancing required |

**Decision**: Hash partitioning provides:
- Even data distribution across partitions
- Automatic query routing via partition pruning
- Simple scaling (add partitions as stores grow)

### 3.2 Partition Configuration

```sql
-- Parent table partitioned by hash
CREATE TABLE sales_transactions (...) PARTITION BY HASH (store_id);

-- 4 initial partitions (modulus 4)
CREATE TABLE sales_transactions_p0 PARTITION OF sales_transactions
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE sales_transactions_p1 PARTITION OF sales_transactions
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);
CREATE TABLE sales_transactions_p2 PARTITION OF sales_transactions
    FOR VALUES WITH (MODULUS 4, REMAINDER 2);
CREATE TABLE sales_transactions_p3 PARTITION OF sales_transactions
    FOR VALUES WITH (MODULUS 4, REMAINDER 3);

-- Default partition for safety
CREATE TABLE sales_transactions_default PARTITION OF sales_transactions DEFAULT;
```

### 3.3 Partition Pruning Behavior

```sql
-- Query with store_id filter
SELECT * FROM sales_transactions 
WHERE store_id = '550e8400-e29b-41d4-a716-446655440000'
  AND sale_date >= '2026-04-01';

-- Execution plan shows partition pruning:
-- -> Index Scan on sales_transactions_p2  (cost=... rows=...)
--    Index Cond: (store_id = '...' AND sale_date >= '...')
```

**Result**: Only 1 of 4 partitions scanned (75% reduction in I/O)

### 3.4 Scaling Strategy

| Store Count | Recommended Partitions | Action |
|-------------|------------------------|--------|
| 1-100 | 4 | Default configuration |
| 100-500 | 8 | Re-partition with modulus 8 |
| 500-2000 | 16 | Re-partition with modulus 16 |
| 2000+ | 32+ | Consider sharding (see 3.5) |

**Re-partitioning Process**:
1. Create new parent table with higher modulus
2. Copy data from old partitions
3. Swap table names in transaction
4. Drop old partitions

### 3.5 Future Sharding Consideration

For extreme scale (10,000+ stores, 100M+ transactions/day):

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           Shard Router (by store_id)                 │    │
│  │   hash(store_id) % num_shards → shard_connection    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
    ┌─────────┐       ┌─────────┐       ┌─────────┐
    │ Shard 0 │       │ Shard 1 │       │ Shard N │
    │Stores   │       │Stores   │       │Stores   │
    │0-333    │       │334-666  │       │667-999  │
    └─────────┘       └─────────┘       └─────────┘
```

**Shard Key**: `store_id` (consistent with partitioning strategy)

**Application Layer Routing**:
```python
def get_shard_for_store(store_id: UUID) -> str:
    shard_index = int(store_id) % NUM_SHARDS
    return f"shard_{shard_index}"
```

---

## 4. Query Patterns & Optimization

### 4.1 Multi-Field Filtering with Date Presets

```sql
-- Template: Sales list with all filters
SELECT 
    id, product_name, category, price, quantity, total_amount,
    customer_name, customer_segment, sale_date, profit_margin, return_status
FROM sales_transactions
WHERE store_id = $1                                    -- Partition pruning
  AND sale_date <@ public.get_date_range($2)           -- Date preset (TODAY, THIS_WEEK, etc.)
  AND ($3::sales_category_enum[] IS NULL OR category = ANY($3))  -- Multi-select category
  AND ($4::customer_segment_enum[] IS NULL OR customer_segment = ANY($4))  -- Multi-select segment
  AND ($5::NUMERIC IS NULL OR price >= $5)             -- Min price
  AND ($6::NUMERIC IS NULL OR price <= $6)             -- Max price
  AND ($7::return_status_enum IS NULL OR return_status = $7)  -- Return status
  AND deleted_at IS NULL
  AND is_active = TRUE
ORDER BY sale_date DESC
LIMIT $8 OFFSET $9;
```

**Index Usage**:
- `idx_sales_store_date` for date range + partition pruning
- `idx_sales_category_date_segment` if category + segment filters present
- `idx_sales_price_range` if price bounds present

**Parameterized Query Benefits**:
- Prepared statement caching
- Plan stability
- SQL injection prevention

### 4.2 Pagination with Sorting

#### Offset/Limit Pagination
```sql
-- Simple pagination (good for first N pages)
SELECT id, product_name, sale_date, total_amount
FROM sales_transactions
WHERE store_id = $1
  AND sale_date >= $2
  AND deleted_at IS NULL
ORDER BY sale_date DESC, id  -- id for stable ordering
LIMIT 20 OFFSET $3;
```

**Performance**:
- Pages 1-10: <10ms
- Pages 100-110: ~50ms (offset scan)
- Pages 1000+: Consider cursor pagination

#### Cursor-Based Pagination (Keyset)
```sql
-- Cursor pagination (O(1) for any page)
SELECT id, product_name, sale_date, total_amount
FROM sales_transactions
WHERE store_id = $1
  AND deleted_at IS NULL
  AND (sale_date, id) < ($2, $3)  -- Cursor: previous page's last row
ORDER BY sale_date DESC, id DESC
LIMIT 20;
```

**Performance**: Constant ~5ms for any page depth

### 4.3 Summary Statistics Query

```sql
-- Dashboard summary (single query)
SELECT 
    COUNT(*) AS total_transactions,
    SUM(total_amount) AS total_revenue,
    AVG(total_amount) AS avg_order_value,
    AVG(profit_margin) AS avg_profit_margin,
    COUNT(*) FILTER (WHERE return_status = 'Returned') AS returns_count,
    SUM(total_amount) FILTER (WHERE return_status = 'Returned') AS returns_amount,
    COUNT(DISTINCT customer_id) AS unique_customers,
    COUNT(*) FILTER (WHERE customer_segment = 'New Customer') AS new_customers
FROM sales_transactions
WHERE store_id = $1
  AND sale_date >= $2
  AND sale_date < $3
  AND deleted_at IS NULL
  AND is_active = TRUE;
```

**Optimization**: Uses covering index `idx_sales_dashboard_covering` for index-only scan

### 4.4 Category Breakdown Query

```sql
-- Revenue by category (uses materialized view)
SELECT 
    category,
    transaction_count,
    units_sold,
    total_revenue,
    avg_price,
    avg_profit_margin,
    returns_count,
    returns_amount
FROM mv_daily_sales_by_category
WHERE store_id = $1
  AND sale_date >= $2
ORDER BY total_revenue DESC;
```

**Performance**: <5ms (pre-aggregated data)

### 4.5 Expected Execution Plans

#### Multi-Filter Query Plan
```
┌─────────────────────────────────────────────────────────────────┐
│ Index Scan using idx_sales_category_date_segment                 │
│   Index Cond: (store_id = $1 AND category = ANY($2))             │
│   Filter: (sale_date >= $3 AND customer_segment = ANY($4))      │
│   Rows Removed by Filter: ~15%                                   │
│   Rows: ~500 (est)                                               │
│   Cost: 12.5..125.3                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Caching Strategy

### 5.1 Multi-Layer Cache Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Client (Browser)                          │
│  Cache-Control: max-age=60, stale-while-revalidate=300           │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                         CDN Layer                                 │
│  Edge caching for static summaries                                │
│  TTL: 60s for real-time, 300s for daily summaries                │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Application Cache (Redis)                      │
│  Key: sales:{store_id}:summary:{date_range_hash}                 │
│  TTL: 30s for real-time, 300s for historical                     │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                  Database Cache Layer                             │
│  - store_analytics_cache table (pre-computed summaries)          │
│  - Materialized views (aggregated analytics)                      │
│  - PostgreSQL shared_buffers (row-level caching)                 │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Cache Key Structure

```python
# Application cache keys
def build_cache_key(store_id: UUID, filters: dict) -> str:
    filter_hash = hashlib.md5(
        json.dumps(filters, sort_keys=True).encode()
    ).hexdigest()[:8]
    return f"sales:{store_id}:list:{filter_hash}"

# Examples:
# sales:550e8400:list:a3b2c1d8           # Filtered list
# sales:550e8400:summary:today           # Today's summary
# sales:550e8400:summary:this_month      # Monthly summary
```

### 5.3 Cache TTL Strategy

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| Real-time metrics (today) | 30s | Balance freshness vs load |
| Daily summaries | 5 min | Less time-sensitive |
| Historical data (>7 days) | 1 hour | Rarely changes |
| Category breakdowns | 5 min | Updated via materialized view |

### 5.4 Materialized Views

#### Daily Sales by Category
```sql
CREATE MATERIALIZED VIEW mv_daily_sales_by_category AS
SELECT 
    store_id, DATE(sale_date) AS sale_date, category,
    COUNT(*) AS transaction_count,
    SUM(quantity) AS units_sold,
    SUM(total_amount) AS total_revenue,
    AVG(price) AS avg_price,
    AVG(profit_margin) AS avg_profit_margin,
    COUNT(*) FILTER (WHERE return_status = 'Returned') AS returns_count
FROM sales_transactions
WHERE deleted_at IS NULL AND is_active = TRUE
GROUP BY store_id, DATE(sale_date), category;
```

**Refresh Schedule**: Every 5 minutes via cron job

#### Store Real-time Metrics
```sql
CREATE MATERIALIZED VIEW mv_store_realtime_metrics AS
SELECT 
    store_id,
    NOW() AS last_updated,
    COUNT(*) FILTER (WHERE sale_date >= CURRENT_DATE) AS today_transactions,
    SUM(total_amount) FILTER (WHERE sale_date >= CURRENT_DATE) AS today_revenue,
    -- ... additional metrics
FROM sales_transactions
WHERE deleted_at IS NULL AND is_active = TRUE
GROUP BY store_id;
```

**Refresh Schedule**: Every 30 seconds for real-time dashboard

### 5.5 Cache Invalidation

```sql
-- Trigger-based invalidation
CREATE OR REPLACE FUNCTION invalidate_analytics_cache()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE store_analytics_cache
    SET is_stale = TRUE
    WHERE store_id = NEW.store_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_invalidate_cache_on_sale
    AFTER INSERT OR UPDATE OR DELETE ON sales_transactions
    FOR EACH ROW EXECUTE FUNCTION invalidate_analytics_cache();
```

### 5.6 Client-Side Caching Headers

```python
# API response headers
def get_cache_headers(data_type: str, store_id: UUID) -> dict:
    if data_type == "realtime":
        return {
            "Cache-Control": "private, max-age=30, stale-while-revalidate=60",
            "ETag": generate_etag(store_id, datetime.now().minute),
            "X-Data-Freshness": "real-time",
        }
    elif data_type == "summary":
        return {
            "Cache-Control": "private, max-age=300, stale-while-revalidate=600",
            "ETag": generate_etag(store_id, date.today()),
            "X-Data-Freshness": "cached",
        }
```

---

## 6. Real-Time Data Ingestion

### 6.1 Ingestion Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Sales Event Sources                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │ POS     │  │ Mobile  │  │ Online  │  │ Import  │            │
│  │ System  │  │ App     │  │ Store   │  │ Jobs    │            │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘            │
└───────┼────────────┼────────────┼────────────┼─────────────────┘
        │            │            │            │
        └────────────┴────────────┴────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Ingestion Queue (PostgreSQL)                     │
│  sales_ingestion_queue table                                      │
│  - Batch grouping by batch_id                                     │
│  - Idempotency via idempotency_key                                │
│  - Retry logic with max_attempts                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Batch Processor (Worker)                        │
│  - Polls queue every 5 seconds                                    │
│  - Processes batches of 100-1000 rows                             │
│  - Uses COPY for bulk insert                                      │
│  - Updates ingestion status                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Batch Insertion Strategy

```python
# Batch processor implementation
class SalesIngestionWorker:
    BATCH_SIZE = 500
    FLUSH_INTERVAL = 5  # seconds
    
    async def process_batch(self, batch_id: UUID):
        # Fetch pending items
        items = await self.fetch_pending_items(batch_id)
        
        # Bulk insert using COPY
        async with self.db.transaction():
            await self.db.execute(
                """
                COPY sales_transactions (
                    store_id, product_name, category, price, quantity,
                    customer_name, customer_segment, sale_date, profit_margin,
                    return_status, metadata
                ) FROM STDIN WITH (FORMAT BINARY)
                """,
                self.prepare_copy_data(items)
            )
            
            # Mark items as completed
            await self.mark_completed(batch_id)
```

### 6.3 Read-Write Concurrency

**Problem**: Analytics queries blocking during bulk inserts

**Solution**: PostgreSQL MVCC (Multi-Version Concurrency Control)

```
┌─────────────────────────────────────────────────────────────────┐
│                     Transaction Timeline                         │
│                                                                  │
│  T1 (Read): SELECT * FROM sales WHERE ...                       │
│             ↓ Sees snapshot at transaction start                 │
│             ↓ Not blocked by concurrent writes                   │
│                                                                  │
│  T2 (Write): INSERT INTO sales ... (batch)                      │
│             ↓ Creates new row versions                          │
│             ↓ Does not block readers                            │
│                                                                  │
│  T1 completes with consistent snapshot                           │
│  T2 commits, new rows become visible to new transactions        │
└─────────────────────────────────────────────────────────────────┘
```

**Best Practices**:
- Use `INSERT ... VALUES` for <100 rows
- Use `COPY` for 100+ rows (10x faster)
- Avoid `VACUUM FULL` during peak hours
- Monitor `pg_stat_activity` for long transactions

### 6.4 Eventual Consistency Model

| Query Type | Acceptable Staleness | Data Freshness Indicator |
|------------|---------------------|--------------------------|
| Real-time dashboard | 30 seconds | `X-Data-Freshness: real-time` |
| Daily summary | 5 minutes | `X-Data-Freshness: cached` |
| Historical reports | 1 hour | `X-Data-Freshness: historical` |
| Export/Analytics | 24 hours | `X-Data-Freshness: batch` |

### 6.5 Data Refresh Cadence

```yaml
# Refresh schedule configuration
refresh_intervals:
  realtime_metrics:
    interval: 30s
    method: incremental  # Only new data
    target: mv_store_realtime_metrics
    
  daily_summaries:
    interval: 5m
    method: refresh_concurrently
    target: mv_daily_sales_by_category
    
  cache_invalidation:
    trigger: on_write  # Trigger-based
    target: store_analytics_cache
    
  full_analytics:
    interval: 1h
    method: compute_store_analytics()
    target: store_analytics_cache
```

---

## 7. Migration Scripts & Schema Versioning

### 7.1 Initial Schema Migration

File: `20260410_sales_analytics_schema.sql` (created in Section 2)

### 7.2 Example Migration: Add Region Column

```sql
-- Migration: 20260415_add_sales_region.sql
-- Description: Add region field for geographic analytics

-- Version tracking
INSERT INTO schema_migrations (version, applied_at)
VALUES ('20260415_add_sales_region', NOW());

-- Add column with default
ALTER TABLE sales_transactions
ADD COLUMN IF NOT EXISTS region VARCHAR(100) DEFAULT NULL;

-- Add index for region filtering
CREATE INDEX IF NOT EXISTS idx_sales_region
ON sales_transactions(store_id, region, sale_date DESC)
WHERE region IS NOT NULL AND deleted_at IS NULL;

-- Update materialized view to include region
CREATE OR REPLACE VIEW mv_daily_sales_by_region AS
SELECT 
    store_id, DATE(sale_date) AS sale_date, region,
    COUNT(*) AS transaction_count,
    SUM(total_amount) AS total_revenue
FROM sales_transactions
WHERE deleted_at IS NULL AND is_active = TRUE AND region IS NOT NULL
GROUP BY store_id, DATE(sale_date), region;

-- Analyze new column
ANALYZE sales_transactions;
```

### 7.3 Example Migration: Add Composite Index

```sql
-- Migration: 20260420_add_composite_index.sql
-- Description: Optimize category+segment+date filtering

INSERT INTO schema_migrations (version, applied_at)
VALUES ('20260420_add_composite_index', NOW());

-- Create index CONCURRENTLY to avoid locking
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sales_cat_seg_date
ON sales_transactions(store_id, category, customer_segment, sale_date DESC)
WHERE deleted_at IS NULL AND is_active = TRUE;

-- Monitor index creation
SELECT 
    schemaname, tablename, indexname, 
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_indexes
WHERE tablename = 'sales_transactions';
```

### 7.4 Schema Version Management

```sql
-- Schema migrations tracking table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version         VARCHAR(100) PRIMARY KEY,
    applied_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    description     TEXT,
    checksum        VARCHAR(64),  -- SHA-256 of migration file
    execution_time  INTERVAL,
    success         BOOLEAN NOT NULL DEFAULT TRUE
);

-- Check applied migrations
SELECT version, applied_at, description
FROM schema_migrations
ORDER BY applied_at DESC;
```

### 7.5 Alembic Integration

```python
# backend/migrations/versions/20260410_sales_analytics.py
"""Sales analytics schema

Revision ID: 20260410_sales
Revises: 20260405_notification_analytics
Create Date: 2026-04-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20260410_sales'
down_revision = '20260405_notification_analytics'
branch_labels = None
depends_on = None

def upgrade():
    # Create enums
    op.execute("CREATE TYPE sales_category_enum AS ENUM ('Clothes', 'Shoes', 'Accessories', 'Full Outfit')")
    op.execute("CREATE TYPE customer_segment_enum AS ENUM ('New Customer', 'Returning', 'VIP', 'Wholesale')")
    op.execute("CREATE TYPE return_status_enum AS ENUM ('Completed', 'Returned', 'Pending Return')")
    
    # Create partitioned table
    op.execute("""
        CREATE TABLE sales_transactions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            store_id UUID NOT NULL,
            -- ... rest of schema
        ) PARTITION BY HASH (store_id)
    """)
    
    # Create partitions
    for i in range(4):
        op.execute(f"""
            CREATE TABLE sales_transactions_p{i}
            PARTITION OF sales_transactions
            FOR VALUES WITH (MODULUS 4, REMAINDER {i})
        """)

def downgrade():
    op.execute("DROP TABLE IF EXISTS sales_transactions CASCADE")
    op.execute("DROP TYPE IF EXISTS return_status_enum")
    op.execute("DROP TYPE IF EXISTS customer_segment_enum")
    op.execute("DROP TYPE IF EXISTS sales_category_enum")
```

---

## 8. Monitoring, Alerting & Performance Troubleshooting

### 8.1 Query Performance Monitoring

#### Metrics to Track

```sql
-- Slow query log view
CREATE OR REPLACE VIEW v_slow_sales_queries AS
SELECT 
    query,
    calls,
    total_exec_time / 1000 AS total_seconds,
    mean_exec_time / 1000 AS avg_seconds,
    rows,
    100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0) AS cache_hit_ratio
FROM pg_stat_statements
WHERE query ILIKE '%sales_transactions%'
ORDER BY mean_exec_time DESC
LIMIT 20;
```

#### Key Metrics Dashboard

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Query latency (p50) | <50ms | >100ms |
| Query latency (p99) | <200ms | >500ms |
| Index hit ratio | >95% | <90% |
| Cache hit ratio | >98% | <95% |
| Active connections | <50 | >80 |

### 8.2 Database Health Metrics

```sql
-- Connection pool monitoring
SELECT 
    state,
    COUNT(*) AS connections,
    MAX(query_start) AS oldest_query
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY state;

-- Lock contention
SELECT 
    locktype,
    relation::regclass,
    mode,
    COUNT(*) AS lock_count,
    AVG(EXTRACT(EPOCH FROM (now() - query_start))) AS avg_wait_seconds
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
WHERE NOT l.granted
GROUP BY locktype, relation, mode;

-- Table bloat
SELECT 
    schemaname, tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    n_dead_tup,
    n_live_tup,
    ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_ratio
FROM pg_stat_user_tables
WHERE tablename LIKE 'sales_%'
ORDER BY n_dead_tup DESC;
```

### 8.3 Alert Configuration

```yaml
# Alerting rules (Prometheus/Grafana format)
groups:
  - name: sales_analytics_alerts
    rules:
      - alert: SlowSalesQuery
        expr: histogram_quantile(0.99, rate(db_query_duration_seconds_bucket{table="sales_transactions"}[5m])) > 0.5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Slow sales query detected"
          description: "P99 query latency {{ $value }}s exceeds 500ms threshold"
      
      - alert: LowCacheHitRatio
        expr: db_cache_hit_ratio{table="sales_transactions"} < 0.90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit ratio on sales_transactions"
      
      - alert: HighConnectionCount
        expr: db_active_connections > 80
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool near capacity"
      
      - alert: PartitionImbalance
        expr: max(db_partition_rows) / min(db_partition_rows) > 1.5
        for: 10m
        labels:
          severity: info
        annotations:
          summary: "Sales partitions are unbalanced"
```

### 8.4 Debugging Process

#### Step 1: Identify Slow Queries
```sql
-- Enable pg_stat_statements if not enabled
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Find slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE query ILIKE '%sales_transactions%'
ORDER BY mean_exec_time DESC
LIMIT 10;
```

#### Step 2: Analyze Execution Plan
```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM sales_transactions
WHERE store_id = '550e8400-e29b-41d4-a716-446655440000'
  AND sale_date >= '2026-04-01'
  AND category = 'Shoes'
ORDER BY sale_date DESC
LIMIT 20;
```

**Look for**:
- `Seq Scan` (should be `Index Scan`)
- `Sort` (should use index for ordering)
- `Rows Removed by Filter` (high = wrong index)
- `Heap Fetches` (high = consider covering index)

#### Step 3: Index Optimization
```sql
-- Check if index is being used
SELECT 
    indexrelname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE relname = 'sales_transactions'
ORDER BY idx_scan DESC;

-- Unused indexes (candidates for removal)
SELECT indexrelname
FROM pg_stat_user_indexes
WHERE relname = 'sales_transactions' AND idx_scan = 0;
```

### 8.5 Maintenance Tasks

```sql
-- Weekly maintenance (automated via cron)
VACUUM ANALYZE sales_transactions;

-- Refresh materialized views
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_sales_by_category;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_sales_by_segment;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_store_realtime_metrics;

-- Reindex if needed (during low-traffic window)
REINDEX TABLE CONCURRENTLY sales_transactions_p0;
```

---

## 9. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONFIT SALES ANALYTICS                             │
│                              DATA FLOW ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              INGESTION LAYER                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────────────────┐   │
│  │   POS   │  │ Mobile  │  │ Online  │  │     Batch Import Jobs       │   │
│  │ System  │  │   App   │  │ Checkout│  │  (CSV, API, Third-party)    │   │
│  └────┬────┘  └────┬────┘  └────┬────┘  └─────────────┬───────────────┘   │
└───────┼────────────┼────────────┼─────────────────────┼────────────────────┘
        │            │            │                     │
        └────────────┴────────────┴─────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INGESTION QUEUE (PostgreSQL)                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  sales_ingestion_queue                                               │   │
│  │  - Batches grouped by batch_id                                       │   │
│  │  - Idempotency via idempotency_key                                   │   │
│  │  - Retry logic (max 3 attempts)                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BATCH PROCESSOR WORKER                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  - Polls queue every 5 seconds                                       │   │
│  │  - Processes 500 rows per batch                                      │   │
│  │  - Uses COPY for bulk insert (10x faster)                            │   │
│  │  - Invalidates cache on write                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DATABASE LAYER (PostgreSQL + Supabase)                   │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │              sales_transactions (HASH PARTITIONED by store_id)         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │ Partition 0 │  │ Partition 1 │  │ Partition 2 │  │ Partition 3 │  │  │
│  │  │ stores:     │  │ stores:     │  │ stores:     │  │ stores:     │  │  │
│  │  │ hash%4=0    │  │ hash%4=1    │  │ hash%4=2    │  │ hash%4=3    │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        INDEXES (B-tree)                                │  │
│  │  idx_sales_store_date          - Partition pruning + date range        │  │
│  │  idx_sales_category_date_seg   - Multi-field filtering                │  │
│  │  idx_sales_dashboard_covering  - Index-only scans                     │  │
│  │  idx_sales_sort_*              - ORDER BY optimization                │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    MATERIALIZED VIEWS                                   │  │
│  │  mv_daily_sales_by_category    - Refresh: 5 min                        │  │
│  │  mv_monthly_sales_by_segment   - Refresh: 15 min                       │  │
│  │  mv_store_realtime_metrics     - Refresh: 30 sec                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    store_analytics_cache                                │  │
│  │  Pre-computed dashboard metrics (invalidated on write)                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    ROW LEVEL SECURITY                                   │  │
│  │  Policies ensure store owners only see their own store's data          │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CACHING LAYERS                                     │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Redis Application Cache                             │  │
│  │  Key: sales:{store_id}:{query_type}:{filter_hash}                     │  │
│  │  TTL: 30s (realtime) → 1h (historical)                                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    CDN Edge Cache                                       │  │
│  │  Cache-Control headers for browser/CDN caching                         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API LAYER                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Sales Analytics API                                  │  │
│  │  GET /api/stores/{store_id}/sales                                      │  │
│  │  GET /api/stores/{store_id}/sales/summary                              │  │
│  │  GET /api/stores/{store_id}/sales/categories                           │  │
│  │  GET /api/stores/{store_id}/sales/segments                             │  │
│  │                                                                         │  │
│  │  Query Parameters:                                                      │  │
│  │  - dateRange: TODAY | THIS_WEEK | THIS_MONTH | custom                  │  │
│  │  - category[]: Clothes | Shoes | Accessories | Full Outfit            │  │
│  │  - customerSegment[]: New Customer | Returning | VIP | Wholesale       │  │
│  │  - priceRange: { min, max }                                            │  │
│  │  - returnStatus: Completed | Returned | Pending Return                 │  │
│  │  - sort: saleDate | profitMargin | price                              │  │
│  │  - page, pageSize                                                      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        STORE OWNER DASHBOARD                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │   Revenue   │  │ Transactions│  │   Returns   │  │  Customers  │  │  │
│  │  │   $12,450   │  │    156      │  │    3.2%     │  │    89       │  │  │
│  │  │   +12.5%    │  │   +8%       │  │   -0.5%     │  │   +15       │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  │                                                                         │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                    Sales Transaction List                        │  │  │
│  │  │  Filters: [Category ▼] [Segment ▼] [Date Range ▼] [Price Range] │  │  │
│  │  │  ─────────────────────────────────────────────────────────────  │  │  │
│  │  │  │ Product      │ Category │ Price │ Qty │ Date    │ Margin │  │  │  │
│  │  │  │ Silk Blouse  │ Clothes  │ $89   │ 2   │ Apr 10  │ 45%    │  │  │  │
│  │  │  │ Leather Belt │ Access.  │ $45   │ 1   │ Apr 10  │ 60%    │  │  │  │
│  │  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Summary & Recommendations

### Key Design Decisions

1. **UUID Primary Keys**: Required for partitioning compatibility and distributed systems
2. **Hash Partitioning by store_id**: Even distribution, automatic pruning, simple scaling
3. **Partial Indexes**: Exclude soft-deleted rows for smaller, faster indexes
4. **Covering Indexes**: Enable index-only scans for common dashboard queries
5. **Materialized Views**: Pre-aggregate expensive analytics, refresh on schedule
6. **Row-Level Security**: Enforce store isolation at database level

### Performance Targets

| Operation | Target Latency | Strategy |
|-----------|---------------|----------|
| List sales (filtered) | <100ms | Composite indexes + covering |
| Summary statistics | <50ms | Materialized view |
| Category breakdown | <30ms | Pre-computed cache |
| Real-time metrics | <30ms | 30s refresh cycle |
| Batch insert (500 rows) | <200ms | COPY command |

### Scaling Path

1. **Phase 1** (Current): 4 partitions, single PostgreSQL instance
2. **Phase 2** (100+ stores): 8 partitions, add read replica
3. **Phase 3** (500+ stores): 16 partitions, connection pooling (PgBouncer)
4. **Phase 4** (2000+ stores): Consider sharding by store_id

### Next Steps

1. Apply migration: `20260410_sales_analytics_schema.sql`
2. Create ingestion worker service
3. Set up monitoring dashboard (Grafana)
4. Configure alerting rules
5. Load test with realistic data volumes
