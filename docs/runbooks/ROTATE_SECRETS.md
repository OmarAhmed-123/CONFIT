# CONFIT Secrets Rotation Runbook

**Classification:** Internal - Confidential  
**Last Updated:** April 2026  
**Owner:** Security Team  
**Rotation Frequency:** Quarterly (or immediately on compromise)

---

## 1. PRINCIPLES

- **Never commit secrets to git** - Use environment variables or secret management
- **Rotate regularly** - Quarterly for all production secrets
- **Rotate immediately** - If any secret is suspected compromised
- **Test after rotation** - Verify all services still function
- **Document everything** - Track what was rotated and when

---

## 2. SECRET CATEGORIES

| Category | Rotation Frequency | Storage |
|----------|---------------------|---------|
| Database passwords | Quarterly | AWS Secrets Manager / HashiCorp Vault |
| API keys (external) | Quarterly | Environment variables |
| JWT signing keys | Quarterly | Secure key store |
| SSL/TLS certificates | Annually / Auto | Certbot / ACM |
| OAuth credentials | Quarterly | Secure storage |
| Encryption keys | Semi-annually | HSM / KMS |
| Payment credentials | Quarterly | PCI-compliant vault |

---

## 3. SECRET STORAGE SYSTEMS

### 3.1 Production: AWS Secrets Manager
```bash
# List all secrets
aws secretsmanager list-secrets --region eu-north-1

# Get secret value (for verification)
aws secretsmanager get-secret-value --secret-id confit/prod/db-password
```

### 3.2 Development: .env files
- Stored in secure shared location
- Never commit to repository
- Encrypted at rest

### 3.3 CI/CD: GitHub Secrets / GitLab CI Variables
- Masked in logs
- Environment-specific
- Audit log available

---

## 4. ROTATION PROCEDURES BY SERVICE

### 4.1 DATABASE PASSWORDS (PostgreSQL)

**Pre-rotation:**
```bash
# 1. Verify current connections
psql -h $DB_HOST -U $DB_USER -c "SELECT count(*) FROM pg_stat_activity;"

# 2. Create backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
```

**Rotation Steps:**
```bash
# 1. Generate new password
NEW_DB_PASSWORD=$(openssl rand -base64 32 | tr -d '=+/')

# 2. Update password in database
psql -h $DB_HOST -U admin -c "ALTER USER app_user WITH PASSWORD '$NEW_DB_PASSWORD';"

# 3. Store in Secrets Manager
aws secretsmanager put-secret-value \
  --secret-id confit/prod/db-password \
  --secret-string "$NEW_DB_PASSWORD"

# 4. Update application environment
# Update K8s secret or environment variable
kubectl create secret generic db-credentials \
  --from-literal=password="$NEW_DB_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

# 5. Rolling restart of applications
kubectl rollout restart deployment/api
kubectl rollout status deployment/api

# 6. Verify connection
psql -h $DB_HOST -U app_user -c "SELECT 1;"
```

**Post-rotation:**
- Delete old backups after 7 days
- Update password manager entry
- Log rotation in security log

---

### 4.2 JWT SIGNING KEYS

**Pre-rotation:**
```bash
# Check token validation currently works
curl -H "Authorization: Bearer $TEST_TOKEN" $API_URL/me
```

**Rotation Steps:**
```bash
# 1. Generate new key pair
openssl genrsa -out new_jwt_private.pem 2048
openssl rsa -in new_jwt_private.pem -pubout -out new_jwt_public.pem

# 2. Store new keys in secret manager
aws secretsmanager put-secret-value \
  --secret-id confit/prod/jwt-private-key \
  --secret-string file://new_jwt_private.pem

aws secretsmanager put-secret-value \
  --secret-id confit/prod/jwt-public-key \
  --secret-string file://new_jwt_public.pem

# 3. Deploy with key rotation support
# Application should accept both old and new keys temporarily

# 4. Rolling restart
kubectl rollout restart deployment/api

# 5. Wait for all pods to use new key
kubectl get pods -l app=api

# 6. Revoke old tokens (force re-login)
redis-cli FLUSHDB  # Clear session cache

# 7. After 24 hours, remove old key support
# Deploy version that only accepts new key
```

**Post-rotation:**
- Securely delete old key files: `shred -u old_jwt_*.pem`
- Monitor for auth errors in Sentry

---

### 4.3 PAYMENT CREDENTIALS (Paymob)

**⚠️ CRITICAL: Coordinate with Paymob before rotation**

**Pre-rotation:**
- Schedule with Paymob support
- Prepare maintenance window
- Have rollback plan ready

**Rotation Steps:**
```bash
# 1. Request new credentials from Paymob
# Contact: support@paymob.com

# 2. Store new credentials
aws secretsmanager put-secret-value \
  --secret-id confit/prod/paymob-api-key \
  --secret-string "NEW_API_KEY"

aws secretsmanager put-secret-value \
  --secret-id confit/prod/paymob-secret \
  --secret-string "NEW_SECRET"

# 3. Test in staging first
./scripts/test_payment_flow.sh --environment=staging

# 4. Enable maintenance mode
kubectl set env deployment/api PAYMENT_MAINTENANCE=true

# 5. Deploy new credentials
kubectl create secret generic paymob-credentials \
  --from-literal=api_key="NEW_API_KEY" \
  --from-literal=secret="NEW_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

# 6. Rolling restart
kubectl rollout restart deployment/payment-service
kubectl rollout status deployment/payment-service

# 7. Test payment flow
./scripts/test_payment_flow.sh --environment=production

# 8. Disable maintenance mode
kubectl set env deployment/api PAYMENT_MAINTENANCE=false

# 9. Revoke old credentials with Paymob
# Contact: support@paymob.com
```

**Post-rotation:**
- Monitor payment success rate for 24 hours
- Check Paymob dashboard for errors

---

### 4.4 AWS/INFRASTRUCTURE ACCESS KEYS

**IAM User Keys:**
```bash
# 1. Create new access key
aws iam create-access-key --user-name confit-deployer

# 2. Update CI/CD with new key
# GitHub Actions / GitLab CI

# 3. Test deployment
./scripts/test_deploy.sh

# 4. Deactivate old key (don't delete yet)
aws iam update-access-key \
  --access-key-id OLD_KEY_ID \
  --status Inactive \
  --user-name confit-deployer

# 5. Wait 7 days, verify no issues

# 6. Delete old key
aws iam delete-access-key \
  --access-key-id OLD_KEY_ID \
  --user-name confit-deployer
```

---

### 4.5 SSL/TLS CERTIFICATES

**Auto-renewal (Preferred):**
```bash
# Check certbot renewal
certbot renew --dry-run

# Force renewal if needed
certbot renew --force-renewal
```

**Manual rotation:**
```bash
# 1. Generate new CSR
openssl req -new -newkey rsa:2048 -nodes -keyout new_domain.key -out new_domain.csr

# 2. Submit to CA
# Use certbot or submit to commercial CA

# 3. Install new certificate
# Update load balancer or web server

# 4. Test SSL
openssl s_client -connect api.confit.app:443 -servername api.confit.app

# 5. Monitor for 48 hours
```

---

### 4.6 REDIS/ELASTICACHE PASSWORD

```bash
# 1. Generate new password
NEW_REDIS_PASSWORD=$(openssl rand -base64 32)

# 2. Update Redis AUTH
# AWS ElastiCache: modify cluster
aws elasticache modify-replication-group \
  --replication-group-id confit-redis \
  --auth-token "$NEW_REDIS_PASSWORD" \
  --auth-token-update-strategy ROTATE

# 3. Update application
kubectl create secret generic redis-credentials \
  --from-literal=password="$NEW_REDIS_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

# 4. Rolling restart
kubectl rollout restart deployment/api

# 5. Verify connectivity
redis-cli -h $REDIS_HOST -a "$NEW_REDIS_PASSWORD" PING
```

---

### 4.7 EXTERNAL API KEYS

**OpenAI / AI Services:**
```bash
# 1. Generate new key in provider dashboard
# OpenAI: https://platform.openai.com/api-keys

# 2. Update secrets
aws secretsmanager put-secret-value \
  --secret-id confit/prod/openai-api-key \
  --secret-string "sk-NEW_KEY"

# 3. Deploy
kubectl rollout restart deployment/ai-service

# 4. Test AI endpoints
./scripts/test_ai_services.sh

# 5. Revoke old key in provider dashboard
```

**SMS Provider (Twilio/etc):**
```bash
# Similar process as above
# Test SMS delivery before revoking old key
```

---

## 5. EMERGENCY ROTATION (Compromise Suspected)

### Immediate Actions (First 15 minutes):

1. **Stop the bleeding:**
   ```bash
   # If specific key compromised, revoke immediately
   aws iam update-access-key --access-key-id COMPROMISED_KEY --status Inactive
   ```

2. **Isolate affected systems:**
   ```bash
   # If database credentials compromised
   # 1. Block connections from suspicious IPs
   # 2. Enable maintenance mode
   kubectl set env deployment/api EMERGENCY_MODE=true
   ```

3. **Generate new secrets immediately**

4. **Deploy emergency patch:**
   ```bash
   kubectl set image deployment/api api=confit/api:emergency-patch
   ```

5. **Notify:**
   - Security team
   - CTO
   - If customer data at risk: DPO and legal

6. **Create incident ticket** (see INCIDENT.md)

7. **Post-incident:**
   - Investigate how compromise occurred
   - Rotate ALL related secrets
   - Update access controls
   - Security audit

---

## 6. AUTOMATION SCRIPTS

### 6.1 Automated Rotation Script
```bash
#!/bin/bash
# rotate_secrets.sh

SERVICES=("db-password" "jwt-private-key" "redis-password")

for service in "${SERVICES[@]}"; do
  echo "Rotating $service..."
  ./scripts/rotate_$service.sh
  sleep 10
done

echo "Rotation complete. Verify all services."
./scripts/verify_all_services.sh
```

### 6.2 Verification Script
```bash
#!/bin/bash
# verify_secrets.sh

# Test database connectivity
psql $DATABASE_URL -c "SELECT 1;" || exit 1

# Test API JWT
./scripts/test_jwt.sh || exit 1

# Test payment flow
./scripts/test_payment.sh || exit 1

# Test AI services
./scripts/test_ai.sh || exit 1

echo "All verifications passed!"
```

---

## 7. AUDIT & COMPLIANCE

### Required Documentation:
- Date/time of rotation
- Which secrets were rotated
- Who performed rotation
- Any issues encountered
- Verification results

### Retention:
- Keep rotation logs for 2 years
- Store in secure, immutable storage
- Review quarterly for compliance

---

## 8. CONTACTS

**Security Team:** security@confit.app  
**DevOps On-Call:** [PagerDuty link]  
**AWS Support:** [Enterprise support portal]  
**Paymob:** support@paymob.com  
**Fawry:** [Support number]

---

**Golden Rule: If in doubt, rotate it out. Better safe than breached.**
