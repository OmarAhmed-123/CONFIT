# CONFIT Operations Runbook

## 1. Postgres Backups

### Daily `pg_dump` to S3 (30-day retention)

**Command (run from bastion / cron):**
```bash
# Daily at 02:00 UTC
pg_dump \
  --host="$DB_HOST" \
  --username="$DB_USER" \
  --dbname="$DB_NAME" \
  --format=custom \
  --file="/tmp/confit-$(date +%Y%m%d).dump"

aws s3 cp "/tmp/confit-$(date +%Y%m%d).dump" \
  s3://confit-backups-$(date +%Y%m)/confit-$(date +%Y%m%d).dump

# Retain only last 30 days
aws s3 ls s3://confit-backups- | awk '{print $2}' | sort | head -n -30 | xargs -I{} aws s3 rm --recursive s3://confit-backups-{}
```

**Environment variables required:**
- `DB_HOST`, `DB_USER`, `DB_NAME`, `PGPASSWORD`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (use `me-south-1`)

---

## 2. Point-in-Time Recovery (WAL Archiving)

**Enable WAL archiving in `postgresql.conf`:**
```ini
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://confit-wal-archive/wal/%f'
max_wal_size = 1GB
min_wal_size = 80MB
```

**Restore procedure:**
1. Stop application (`docker compose down api worker`)
2. Provision fresh Postgres instance
3. Restore base backup: `pg_restore -d confit confit-YYYYMMDD.dump`
4. Replay WAL segments: `pg_waldump` or restore via `pg_basebackup`
5. Verify with `/api/health/ready`
6. Resume traffic

---

## 3. Quarterly Restore Tests

**Schedule:** First Saturday of each quarter (Jan, Apr, Jul, Oct).

**Steps:**
1. Spin up isolated staging database from latest S3 backup
2. Run full test suite against restored DB
3. Verify `/api/health/deep` passes (all external providers reachable)
4. Document results in `#ops-restore-tests` Slack channel / ticket
5. Destroy isolated staging DB after test

**Acceptance criteria:**
- Data integrity check (row counts, checksums on critical tables)
- Application boots and serves requests
- No PII leakage in backup logs

---

## 4. Redis Persistence & Recovery

**RDB snapshots:**
```conf
save 900 1
save 300 10
save 60 10000
```

**AOF for durability:**
```conf
appendonly yes
appendfsync everysec
```

**Recovery:**
```bash
# Stop Redis, replace dump.rdb from S3 backup, restart
aws s3 cp s3://confit-backups/redis-dump.rdb /data/redis/dump.rdb
redis-server /etc/redis/redis.conf
```

---

## 5. Prometheus & Grafana Emergency Actions

### Disk full on Prometheus
```bash
# Retain 15 days of metrics only
curl -X POST http://prometheus:9090/api/v1/admin/tsdb/delete_series?match[]={__name__=~".+"}
curl -X POST http://prometheus:9090/api/v1/admin/tsdb/clean_tombstones
```

### Reset Grafana admin password
```bash
docker exec -it grafana grafana-cli admin reset-admin-password "NEW_STRONG_PASSWORD"
```

---

## 6. Escalation Matrix

| Severity | Condition | Action | Owner |
|----------|-----------|--------|-------|
| SEV-1 | `/api/health` 500 for >2 min | Page on-call immediately | Platform Lead |
| SEV-2 | Payment provider down (Paymob/Stripe) | Alert #payments-channel, enable fallback | Payments Lead |
| SEV-3 | Error rate >5% for >5 min | Auto-scale + notify SRE | SRE On-Call |
| SEV-4 | Disk / memory >85% | Create ticket, schedule resize | Infra Engineer |

---

## 7. Useful Commands

```bash
# Check all health tiers
curl -s http://localhost:8000/api/health | jq .
curl -s http://localhost:8000/api/health/ready | jq .
curl -s http://localhost:8000/api/health/deep | jq .

# Metrics (requires INTERNAL_API_KEY)
curl -s -H "x-internal-api-key: $INTERNAL_API_KEY" http://localhost:8000/api/metrics

# View structured logs (production JSON)
docker logs confit-api 2>&1 | jq -c '. | select(.level=="error")'

# Tail Sentry issues
open https://sentry.io/organizations/confit/issues/
```
