# Sales Analytics DB Runbook

## Execution Order

1. Phase 1: `V1`, `V2` (schema + RLS + core indexes + keyset pagination path)
2. Phase 2: enable `REDIS_URL`, deploy API headers (`ETag`, `Cache-Control`, freshness)
3. Phase 3: `V3` (materialized views, scheduled refresh every 1-5 min)
4. Phase 4: `V4` only after load tests prove table/IO bottleneck

## Flyway Commands

- `flyway -locations=filesystem:backend/db/migrations/flyway migrate`
- `flyway info`

## Store Isolation Contract

- API extracts `store_id` from auth context only.
- Repository always applies `set_config('app.current_store_id', <store_id>, true)`.
- Every query against `sales_transactions` includes `store_id` scope and is additionally protected by RLS policy.

## Keyset Pagination Contract

Use `(sale_date, id)` cursor:

```sql
SELECT *
FROM sales_transactions
WHERE store_id = :store_id
  AND sale_date >= :start_date
  AND sale_date < :end_date
  AND (sale_date, id) < (:cursor_date, :cursor_id)
ORDER BY sale_date DESC, id DESC
LIMIT :page_size;
```

## Materialized View Refresh

- `REFRESH MATERIALIZED VIEW CONCURRENTLY mv_sales_daily_store_category;`
- `REFRESH MATERIALIZED VIEW CONCURRENTLY mv_sales_monthly_store_segment;`
- Run from scheduler every 1-5 minutes for near real-time dashboards.

### Automatic Scheduler

- Implemented in `backend/services/analytics/sales_mv_scheduler.py`
- Started automatically from `backend/main.py`
- Env controls:
  - `SALES_MV_REFRESH_ENABLED=true|false` (default `true`)
  - `SALES_MV_REFRESH_INTERVAL_MINUTES=1..5` (default `5`)
