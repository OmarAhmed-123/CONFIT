# CONFIT Backup & Restore Runbook

**Classification:** Internal Operations  
**Last Updated:** April 2026  
**Owner:** DevOps Team  
**Test Schedule:** Monthly restore test (staging)

---

## 1. BACKUP OVERVIEW

### 1.1 Backup Types & Schedule

| Data Type | Frequency | Retention | Storage Location |
|-----------|-----------|-----------|------------------|
| PostgreSQL Database | Daily (incremental) + Weekly (full) | 30 days incremental, 90 days full | AWS S3 + Local replica |
| PostgreSQL (archival) | Monthly | 7 years (tax compliance) | Glacier Deep Archive |
| User Uploads (Photos) | Real-time sync | 7 years | S3 + CDN |
| AI Generated Images | Daily | 7 days | S3 Standard |
| Configuration/Code | On commit | 90 days | Git + S3 |
| Redis Cache | Weekly | 7 days | S3 |
| Logs | Continuous | 1 year hot, 7 years archive | CloudWatch + S3 |

### 1.2 Backup Verification

**Daily Automated Checks:**
- Backup size within expected range
- Backup integrity checksums
- S3 replication status
- Alert on failure

**Monthly Manual Test:**
- Restore to staging environment
- Verify data integrity
- Run smoke tests
- Document results

---

## 2. BACKUP LOCATIONS

### 2.1 Primary (AWS)
```
Bucket: confit-backups-prod
Region: eu-north-1 (Stockholm)
Structure:
  /database/
    /daily/YYYY-MM-DD/
    /weekly/YYYY-MM-DD/
    /monthly/YYYY-MM/
  /uploads/
    /photos/YYYY/MM/DD/
    /ai-generated/YYYY/MM/DD/
  /config/
  /logs/
```

### 2.2 Secondary (Local/On-Premise)
```
Location: /backups/confit-prod/
Retention: 7 days local
Replication: Daily sync from S3
```

### 2.3 Tertiary (Cold Storage)
```
AWS Glacier Deep Archive
Retention: 7 years (financial/tax records)
Retrieval: 12-48 hours
```

---

## 3. RESTORE PROCEDURES

### 3.1 DATABASE RESTORE

#### Scenario A: Point-in-Time Recovery (Partial Data Loss)

**When to use:**
- Accidental data deletion
- Corruption in recent data
- Rollback needed to specific time

**Steps:**

```bash
# 1. Identify target restore time
# Format: YYYY-MM-DD HH:MM:SS UTC
RESTORE_TIME="2026-04-25 14:30:00"

# 2. Create maintenance window
# Notify users via status page
kubectl set env deployment/api MAINTENANCE_MODE=true

# 3. Get latest full backup before restore time
LATEST_FULL=$(aws s3 ls s3://confit-backups-prod/database/weekly/ | tail -1 | awk '{print $2}')
aws s3 cp s3://confit-backups-prod/database/weekly/$LATEST_FULL ./restore/

# 4. Stop writes to database
kubectl scale deployment api --replicas=1

# 5. Create new RDS instance from snapshot
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier confit-prod \
  --target-db-instance-identifier confit-prod-restored \
  --restore-time "$RESTORE_TIME" \
  --use-latest-restorable-time

# 6. Wait for restoration
aws rds wait db-instance-available \
  --db-instance-identifier confit-prod-restored

# 7. Verify data integrity
psql -h confit-prod-restored.XXX.eu-north-1.rds.amazonaws.com \
  -U admin -c "SELECT count(*) FROM orders WHERE created_at > '2026-04-25';"

# 8. Switch application to new database
kubectl set env deployment/api \
  DATABASE_URL="postgresql://admin:XXX@confit-prod-restored.XXX.eu-north-1.rds.amazonaws.com:5432/confit"

# 9. Rolling restart
kubectl rollout restart deployment/api

# 10. Verify application health
./scripts/health_check.sh

# 11. Remove maintenance mode
kubectl set env deployment/api MAINTENANCE_MODE=false

# 12. Rename instances
aws rds modify-db-instance \
  --db-instance-identifier confit-prod \
  --new-db-instance-identifier confit-prod-old

aws rds modify-db-instance \
  --db-instance-identifier confit-prod-restored \
  --new-db-instance-identifier confit-prod
```

#### Scenario B: Complete Database Rebuild (Full Loss)

**When to use:**
- Complete database failure
- Catastrophic corruption
- Region disaster recovery

**Steps:**

```bash
# 1. Declare major incident
# See INCIDENT.md for communication

# 2. Identify latest good backup
BACKUP_DATE="2026-04-25"
BACKUP_FILE="confit-prod-full-${BACKUP_DATE}.sql.gz"

# 3. Download from S3
aws s3 cp s3://confit-backups-prod/database/weekly/$BACKUP_FILE ./restore/

# 4. Create new database instance
aws rds create-db-instance \
  --db-instance-identifier confit-prod-new \
  --db-instance-class db.r6g.xlarge \
  --engine postgres \
  --master-username admin \
  --master-user-password $(openssl rand -base64 32) \
  --allocated-storage 500 \
  --backup-retention-period 7

# 5. Wait for instance ready
aws rds wait db-instance-available \
  --db-instance-identifier confit-prod-new

# 6. Restore from backup
gunzip -c $BACKUP_FILE | \
  psql -h confit-prod-new.XXX.eu-north-1.rds.amazonaws.com -U admin

# 7. Run migration scripts
# Ensure schema is current
psql $DATABASE_URL -f ./migrations/verify_schema.sql

# 8. Verify critical tables
echo "Checking critical data..."
psql $DATABASE_URL -c "SELECT count(*) FROM users;"
psql $DATABASE_URL -c "SELECT count(*) FROM orders WHERE status='pending';"

# 9. Update application connection strings
kubectl set env deployment/api DATABASE_URL="$DATABASE_URL"

# 10. Rolling restart all services
kubectl rollout restart deployment/api
kubectl rollout restart deployment/workers

# 11. Verify full functionality
./scripts/full_test_suite.sh
```

---

### 3.2 USER UPLOADS RESTORE (S3)

#### Individual User Files

```bash
# List available versions
aws s3api list-object-versions \
  --bucket confit-uploads-prod \
  --prefix users/user_123/photos/

# Restore specific version
aws s3api get-object \
  --bucket confit-uploads-prod \
  --key users/user_123/photos/profile.jpg \
  --version-id VERSION_ID \
  ./restored/profile.jpg

# Or restore from backup bucket
aws s3 cp s3://confit-backups-prod/uploads/2026/04/25/users/user_123/photos/profile.jpg \
  s3://confit-uploads-prod/users/user_123/photos/profile.jpg
```

#### Bulk Restore (Disaster Recovery)

```bash
# Sync entire bucket from backup
aws s3 sync \
  s3://confit-backups-prod/uploads/$BACKUP_DATE/ \
  s3://confit-uploads-prod/ \
  --storage-class STANDARD

# Verify sync
aws s3 ls s3://confit-uploads-prod/ --recursive --summarize
```

---

### 3.3 REDIS/ELASTICACHE RESTORE

**Note:** Redis data is mostly cache - full restore rarely needed

```bash
# If persistence enabled (RDB/AOF)
# 1. Identify latest backup
LATEST_RDB=$(aws s3 ls s3://confit-backups-prod/redis/ | tail -1)

# 2. Download and restore
aws s3 cp s3://confit-backups-prod/redis/$LATEST_RDB ./restore/dump.rdb

# 3. Upload to new ElastiCache instance
# (Requires manual steps via AWS console or custom script)

# Alternative: Warm cache from database
./scripts/warm_cache.sh
```

---

### 3.4 CONFIGURATION RESTORE

```bash
# Restore from Git
# All configuration should be in version control
git checkout $BACKUP_COMMIT -- kubernetes/
git checkout $BACKUP_COMMIT -- config/

# Restore environment files from S3
aws s3 cp s3://confit-backups-prod/config/production.env.sealed ./
kubeseal --recovery-unseal --controller-namespace kube-system < production.env.sealed > .env.production
```

---

## 4. DISASTER RECOVERY SCENARIOS

### 4.1 Complete AWS Region Failure

**RTO:** 4 hours  
**RPO:** 1 hour (last backup)

**Steps:**
1. Activate disaster recovery site (secondary region)
2. Update DNS to DR site (Cloudflare)
3. Restore database to secondary region
4. Sync S3 buckets to secondary region
5. Deploy application to secondary region
6. Notify users of reduced functionality
7. Queue non-essential operations

### 4.2 Database Complete Corruption

**RTO:** 2 hours  
**RPO:** 24 hours (last daily backup)

**Steps:**
1. Stop all database writes immediately
2. Identify last known good backup
3. Provision new database instance
4. Restore from backup
5. Apply WAL logs if available
6. Verify data integrity
7. Redirect traffic to new instance

### 4.3 Ransomware/Malicious Deletion

**Steps:**
1. Isolate affected systems
2. Preserve logs for forensics
3. Restore from pre-attack backup
4. Verify backup integrity (not infected)
5. Rotate all credentials
6. Security audit before full restore
7. Incident response per INCIDENT.md

---

## 5. VERIFICATION PROCEDURES

### 5.1 Post-Restore Checks

```bash
#!/bin/bash
# verify_restore.sh

echo "=== RESTORE VERIFICATION ==="

# 1. Database connectivity
echo "Checking database..."
psql $DATABASE_URL -c "SELECT 1;" || exit 1

# 2. Row counts
echo "Checking row counts..."
psql $DATABASE_URL <<EOF
SELECT 'users' as table, count(*) as rows FROM users
UNION ALL
SELECT 'orders', count(*) FROM orders
UNION ALL
SELECT 'products', count(*) FROM products
UNION ALL
SELECT 'payments', count(*) FROM payments;
EOF

# 3. Recent data
echo "Checking recent data..."
psql $DATABASE_URL -c "
SELECT count(*) FROM orders 
WHERE created_at > NOW() - INTERVAL '7 days';
"

# 4. Critical functions
echo "Testing critical functions..."
curl -f $API_URL/health || exit 1
curl -f $API_URL/health/db || exit 1

# 5. Smoke tests
echo "Running smoke tests..."
./scripts/smoke_tests.sh

echo "=== VERIFICATION COMPLETE ==="
```

### 5.2 Integrity Check

```sql
-- Check for data corruption
SELECT pg_database.datname, pg_database_size(pg_database.datname)
FROM pg_database WHERE datname = 'confit';

-- Check for missing indexes
SELECT schemaname, tablename, indexname
FROM pg_indexes 
WHERE tablename IN ('users', 'orders', 'products')
ORDER BY tablename;

-- Verify foreign key constraints
SELECT tc.table_name, kcu.column_name, ccu.table_name AS foreign_table
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY';
```

---

## 6. DOCUMENTATION REQUIREMENTS

### Post-Restore Documentation:

```markdown
## Restore Event: [Date]

**Reason:** [Why restore was needed]
**Source:** [Backup source and date]
**Started:** [Timestamp]
**Completed:** [Timestamp]
**Duration:** [Total time]

**Data Loss:** [Any data not recovered]
**Verification:** [Tests passed/failed]
**Issues:** [Any problems encountered]
**Follow-up:** [Action items]
```

---

## 7. PREVENTION & MONITORING

### 7.1 Backup Monitoring

```bash
# Check daily backup success
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name BackupTime \
  --dimensions Name=DBInstanceIdentifier,Value=confit-prod \
  --start-time 2026-04-25T00:00:00Z \
  --end-time 2026-04-26T00:00:00Z \
  --period 3600 \
  --statistics Average

# Check S3 backup sync
aws s3 ls s3://confit-backups-prod/database/daily/ | tail -5
```

### 7.2 Health Dashboards

- **Grafana:** https://grafana.confit.app/d/backups
- **AWS Backup Dashboard:** https://console.aws.amazon.com/backup
- **S3 Storage Lens:** S3 analytics

---

## 8. CONTACTS

**DevOps On-Call:** [PagerDuty]  
**Database Admin:** dba@confit.app  
**AWS Support:** Enterprise support portal  
**Backup Vendor:** [If using third-party]

---

**Golden Rule: Backups are worthless until tested. Run monthly restore tests.**
