# CONFIT Deployment Runbook

**Classification:** Internal Operations  
**Last Updated:** April 2026  
**Owner:** DevOps Team  
**Environments:** Staging → Production

---

## 1. DEPLOYMENT OVERVIEW

### 1.1 Deployment Environments

| Environment | Purpose | Auto-Deploy | Protection |
|-------------|---------|-------------|------------|
| Local | Development | No | None |
| Dev | Feature testing | Yes (branches) | Basic |
| Staging | Pre-production | Yes (main) | Moderate |
| Production | Live | No (manual) | High |
| DR | Disaster recovery | No | Mirrored |

### 1.2 Deployment Frequency

- **Staging:** On every merge to `main`
- **Production:** Planned releases (weekly/bi-weekly)
- **Hotfixes:** As needed (skip staging for urgent fixes)

### 1.3 Deployment Tools

- **CI/CD:** GitHub Actions
- **Container Registry:** AWS ECR
- **Orchestration:** Kubernetes (EKS)
- **GitOps:** ArgoCD (optional)
- **Secrets:** AWS Secrets Manager + Sealed Secrets

---

## 2. PRE-DEPLOYMENT CHECKLIST

### 2.1 Code Preparation

- [ ] All tests passing (`pytest`, `npm test`)
- [ ] Security scan clean (`bandit`, `npm audit`)
- [ ] Code review approved (min 2 reviewers)
- [ ] CHANGELOG.md updated
- [ ] Version bumped (`pyproject.toml`, `package.json`)
- [ ] Database migrations prepared (if applicable)
- [ ] Feature flags configured (for gradual rollout)

### 2.2 Infrastructure Preparation

- [ ] Infrastructure as Code reviewed (Terraform)
- [ ] New resources provisioned in staging
- [ ] Resource limits checked (CPU/Memory/Storage)
- [ ] SSL certificates valid (not expiring soon)
- [ ] Secrets rotated (if required)

### 2.3 Communication

- [ ] Deployment window scheduled
- [ ] Stakeholders notified (Product, Support)
- [ ] Status page prepared (if maintenance window)
- [ ] Rollback plan reviewed

---

## 3. STANDARD DEPLOYMENT PROCEDURE

### 3.1 Staging Deployment

```bash
# Automated via GitHub Actions
# Triggered on merge to main branch

# Verify deployment
kubectl get pods -n staging
kubectl rollout status deployment/api -n staging

# Run smoke tests
./scripts/smoke_tests.sh --env=staging

# Run integration tests
./scripts/integration_tests.sh --env=staging

# Verify database migrations
./scripts/check_migrations.sh --env=staging
```

### 3.2 Production Deployment

#### Step 1: Pre-Deployment (T-30 min)

```bash
# 1. Verify staging is stable
curl -sf https://api-staging.confit.app/health || exit 1

# 2. Check production current state
kubectl get pods -n production
kubectl top nodes

# 3. Backup database (precautionary)
./scripts/backup_db.sh production

# 4. Enable maintenance banner (optional)
kubectl set env deployment/api MAINTENANCE_BANNER="Deploying updates, brief interruption expected"
```

#### Step 2: Deployment (T-0)

**Option A: Blue/Green Deployment (Preferred)**

```bash
# 1. Tag current deployment as "blue"
kubectl label deployment/api version=blue -n production --overwrite

# 2. Deploy "green" version
kubectl apply -f k8s/production/api-deployment-green.yaml

# 3. Wait for green to be ready
kubectl rollout status deployment/api-green -n production --timeout=300s

# 4. Test green deployment
./scripts/smoke_tests.sh --env=production-green

# 5. Switch traffic to green
kubectl patch service api -n production -p '{"spec":{"selector":{"version":"green"}}}'

# 6. Monitor for 10 minutes
./scripts/monitor_deployment.sh --duration=600

# 7. If issues detected, rollback to blue
# kubectl patch service api -n production -p '{"spec":{"selector":{"version":"blue"}}}'

# 8. Clean up blue (after 24 hours of stability)
# kubectl delete deployment api-blue -n production
```

**Option B: Rolling Update (Default)**

```bash
# 1. Start rolling update
kubectl set image deployment/api \
  api=123456789012.dkr.ecr.eu-north-1.amazonaws.com/confit/api:v1.2.3 \
  -n production

# 2. Monitor rollout
kubectl rollout status deployment/api -n production --timeout=300s

# 3. Watch pod status
kubectl get pods -n production -l app=api -w

# 4. Check application logs
kubectl logs -f deployment/api -n production

# 5. Verify health endpoints
curl -sf https://api.confit.app/health
curl -sf https://api.confit.app/health/db
curl -sf https://api.confit.app/health/redis
```

#### Step 3: Post-Deployment (T+10 min)

```bash
# 1. Run smoke tests
./scripts/smoke_tests.sh --env=production

# 2. Verify critical user flows
./scripts/e2e_tests.sh --env=production --critical-only

# 3. Check error rates (Sentry)
# Verify no spike in errors

# 4. Check performance metrics (Grafana)
# Verify response times acceptable

# 5. Remove maintenance banner
kubectl set env deployment/api MAINTENANCE_BANNER=""

# 6. Notify team
# Post in #deployments channel
```

---

## 4. DATABASE MIGRATIONS

### 4.1 Migration Strategy: Expand/Contract Pattern

**Pre-deployment (Backward compatible changes):**
```sql
-- Example: Adding a column
-- Step 1: Add column as nullable
ALTER TABLE users ADD COLUMN style_preferences JSONB;

-- Step 2: Backfill data
UPDATE users SET style_preferences = '{}' WHERE style_preferences IS NULL;

-- Step 3: Make required (in next deployment)
-- ALTER TABLE users ALTER COLUMN style_preferences SET NOT NULL;
```

### 4.2 Running Migrations

```bash
# Before application deployment
# 1. Run migrations
kubectl run migration-$(date +%s) \
  --image=123456789012.dkr.ecr.eu-north-1.amazonaws.com/confit/api:v1.2.3 \
  --rm -i --restart=Never \
  -- alembic upgrade head

# 2. Verify migrations applied
kubectl run migration-check-$(date +%s) \
  --image=123456789012.dkr.ecr.eu-north-1.amazonaws.com/confit/api:v1.2.3 \
  --rm -i --restart=Never \
  -- alembic current
```

### 4.3 Rollback Migrations (Emergency)

```bash
# 1. Stop application writes
kubectl scale deployment api --replicas=0 -n production

# 2. Rollback migration
alembic downgrade -1

# 3. Restore previous application version
kubectl rollout undo deployment/api -n production

# 4. Scale application back up
kubectl scale deployment api --replicas=3 -n production
```

---

## 5. HOTFIX DEPLOYMENT (Urgent)

**When to use:** Critical bug in production requiring immediate fix

```bash
# 1. Create hotfix branch from production tag
git checkout -b hotfix/critical-bug v1.2.2

# 2. Apply minimal fix
git cherry-pick <commit-hash>

# 3. Fast-track review (security + tech lead)
# Min 1 reviewer for hotfixes

# 4. Tag and build
git tag v1.2.3-hotfix
git push origin v1.2.3-hotfix

# 5. Deploy directly to production (skip staging)
# Use Option B (Rolling Update) for speed
kubectl set image deployment/api \
  api=123456789012.dkr.ecr.eu-north-1.amazonaws.com/confit/api:v1.2.3-hotfix \
  -n production

# 6. Monitor closely
./scripts/monitor_deployment.sh --duration=1800 --critical

# 7. Merge hotfix back to main
git checkout main
git merge hotfix/critical-bug
git push origin main
```

---

## 6. ROLLBACK PROCEDURES

### 6.1 Automated Rollback (Kubernetes)

```bash
# Check rollout history
kubectl rollout history deployment/api -n production

# Rollback to previous version
kubectl rollout undo deployment/api -n production

# Rollback to specific revision
kubectl rollout undo deployment/api -n production --to-revision=3

# Verify rollback
kubectl rollout status deployment/api -n production
```

### 6.2 Manual Rollback (Image Tag)

```bash
# 1. Identify last known good version
LAST_GOOD_VERSION="v1.2.2"

# 2. Revert to previous image
kubectl set image deployment/api \
  api=123456789012.dkr.ecr.eu-north-1.amazonaws.com/confit/api:$LAST_GOOD_VERSION \
  -n production

# 3. Verify rollback
kubectl rollout status deployment/api -n production
./scripts/smoke_tests.sh --env=production

# 4. Rollback database migrations (if needed)
alembic downgrade -1  # Or to specific revision
```

### 6.3 Emergency Full Rollback

```bash
# If deployment causes system instability

# 1. Enable maintenance mode
kubectl set env deployment/api MAINTENANCE_MODE=true -n production

# 2. Scale to zero (if needed)
kubectl scale deployment api --replicas=0 -n production

# 3. Restore from database backup (if data corrupted)
# See RESTORE_BACKUP.md

# 4. Deploy last stable version
kubectl apply -f k8s/production/api-deployment-stable.yaml

# 5. Verify
kubectl rollout status deployment/api -n production
./scripts/full_test_suite.sh --env=production

# 6. Disable maintenance mode
kubectl set env deployment/api MAINTENANCE_MODE=false -n production
```

---

## 7. DEPLOYMENT VERIFICATION

### 7.1 Automated Checks

```bash
#!/bin/bash
# verify_deployment.sh

APP_VERSION=$1
ENVIRONMENT=$2

echo "Verifying deployment of v$APP_VERSION to $ENVIRONMENT..."

# 1. Version check
DEPLOYED_VERSION=$(kubectl get deployment api -n $ENVIRONMENT -o jsonpath='{.spec.template.spec.containers[0].image}' | cut -d: -f2)
if [ "$DEPLOYED_VERSION" != "$APP_VERSION" ]; then
  echo "ERROR: Version mismatch. Expected $APP_VERSION, got $DEPLOYED_VERSION"
  exit 1
fi

# 2. Health checks
curl -sf https://api-$ENVIRONMENT.confit.app/health || exit 1
curl -sf https://api-$ENVIRONMENT.confit.app/health/db || exit 1
curl -sf https://api-$ENVIRONMENT.confit.app/health/redis || exit 1

# 3. Pod status
READY_PODS=$(kubectl get pods -n $ENVIRONMENT -l app=api -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}' | wc -w)
if [ "$READY_PODS" -lt 2 ]; then
  echo "ERROR: Only $READY_PODS pods ready"
  exit 1
fi

# 4. No CrashLoopBackOff
CRASHING=$(kubectl get pods -n $ENVIRONMENT -l app=api | grep -c CrashLoopBackOff)
if [ "$CRASHING" -gt 0 ]; then
  echo "ERROR: $CRASHING pods in CrashLoopBackOff"
  exit 1
fi

echo "All verification checks passed!"
```

### 7.2 Manual Verification Checklist

- [ ] Application responds to requests
- [ ] Database connections working
- [ ] Redis/cache connections working
- [ ] External APIs reachable (Paymob, Fawry)
- [ ] Background jobs processing
- [ ] No error spikes in logs
- [ ] Response times normal
- [ ] File uploads working
- [ ] Payment flows working (test transaction)

---

## 8. MONITORING & ALERTS

### 8.1 During Deployment

Monitor:
- Pod status: `kubectl get pods -n production -w`
- Deployment progress: `kubectl rollout status deployment/api`
- Application logs: `kubectl logs -f deployment/api`
- Error rates: Sentry dashboard
- Performance: Grafana dashboards

### 8.2 Post-Deployment (24 hours)

- Error rate < 0.1%
- 95th percentile response time < 500ms
- 99th percentile response time < 1000ms
- No increase in failed payments
- Customer support ticket volume normal

---

## 9. DEPLOYMENT COMMUNICATION

### 9.1 Pre-Deployment

```
📅 DEPLOYMENT SCHEDULED

Date: [Date]
Time: [Time] UTC+2 (Egypt)
Duration: ~30 minutes
Environment: Production
Version: v[X.Y.Z]
Changes: [Link to CHANGELOG]
Impact: Brief service interruption possible

No action required from users.
```

### 9.2 Post-Deployment

```
✅ DEPLOYMENT COMPLETE

Version v[X.Y.Z] successfully deployed to production.
All systems operational.

New Features:
- [Feature 1]
- [Feature 2]

Report issues: support@confit.app
```

---

## 10. CI/CD PIPELINE

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  workflow_dispatch:  # Manual trigger
  push:
    tags:
      - 'v*'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: pytest
      - name: Security scan
        run: bandit -r backend/

  deploy-staging:
    needs: test
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - name: Deploy to staging
        run: ./scripts/deploy.sh staging
      - name: Run smoke tests
        run: ./scripts/smoke_tests.sh --env=staging

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy to production
        run: ./scripts/deploy.sh production
      - name: Verify deployment
        run: ./scripts/verify_deployment.sh ${{ github.ref_name }} production
```

---

## 11. TROUBLESHOOTING

### Common Issues:

**Issue: Pods stuck in Pending**
```bash
# Check resource constraints
kubectl describe pod <pod-name> -n production
# Scale nodes or reduce resource requests
```

**Issue: ImagePullBackOff**
```bash
# Verify image exists
aws ecr describe-images --repository-name confit/api --image-ids imageTag=v1.2.3
# Check ECR authentication
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URL
```

**Issue: CrashLoopBackOff**
```bash
# Check logs
kubectl logs <pod-name> -n production --previous
# Common causes: DB connection, missing env vars, bad migration
```

---

**Golden Rule: Never deploy on Friday. Emergency fixes only.**
