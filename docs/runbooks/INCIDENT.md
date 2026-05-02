# CONFIT Incident Response Runbook

**Classification:** Internal Operations  
**Last Updated:** April 2026  
**Owner:** Platform Operations Team  
**Review Cycle:** Quarterly

---

## 1. INCIDENT SEVERITY LEVELS

| Level | Name | Response Time | Example |
|-------|------|---------------|---------|
| P0 | Critical | 15 minutes | Platform down, data breach, payment fraud |
| P1 | High | 1 hour | Major feature failure, security vulnerability |
| P2 | Medium | 4 hours | Partial functionality loss, performance degradation |
| P3 | Low | 24 hours | Minor bugs, documentation issues |

---

## 2. INCIDENT RESPONSE TEAM

**On-Call Schedule:** [Link to PagerDuty/Opsgenie]  
**Emergency Hotline:** +20-XXX-XXXX-XXX  
**Slack Channel:** #incidents-confidential  
**War Room:** https://meet.google.com/confit-war-room

| Role | Primary | Backup |
|------|---------|--------|
| Incident Commander | CTO | VP Engineering |
| Technical Lead | Senior DevOps | DevOps Lead |
| Communications | Head of Product | Marketing Lead |
| Security | CISO | Security Engineer |
| DPO (for data incidents) | dpo@confit.app | Legal Counsel |

---

## 3. GENERAL INCIDENT PROCEDURE

### 3.1 Detection Phase
1. **Alert Sources:**
   - Sentry alerts (application errors)
   - Grafana alerts (infrastructure)
   - Pingdom (uptime monitoring)
   - User reports (support tickets)
   - Manual discovery

2. **Initial Assessment:**
   - Determine severity level
   - Identify affected services
   - Estimate user impact
   - Check if related to known issues

### 3.2 Response Phase
1. **Declare Incident:**
   - Post in #incidents-confidential
   - Page on-call engineer if P0/P1
   - Create incident ticket (template below)

2. **Assemble Response Team:**
   - P0/P1: All hands on deck
   - P2/P3: On-call + relevant team

3. **Communication Protocol:**
   ```
   Incident: [P-level] - [Brief Description]
   Affected: [Services/Users]
   Status: [Investigating/Identified/Monitoring/Resolved]
   ETA: [Estimated time to fix]
   Updates: Every 15 min (P0), 30 min (P1), 1 hour (P2)
   ```

### 3.3 Resolution Phase
1. Apply temporary fix if available
2. Deploy permanent fix through standard process
3. Verify resolution
4. Monitor for 1-4 hours post-fix

### 3.4 Post-Incident Phase
1. Write incident report within 24 hours
2. Conduct blameless postmortem within 48 hours (P0/P1)
3. Update runbooks if needed
4. Schedule follow-up tasks

---

## 4. SPECIFIC INCIDENT SCENARIOS

### 4.1 PLATFORM DOWN (P0)

**Detection:** Uptime alerts, user reports spike  
**Impact:** Complete service unavailability

**Response Steps:**
1. Check status of critical services:
   ```bash
   # Run from bastion host
   ./scripts/check_service_health.sh
   ```

2. Check infrastructure status:
   - AWS/DigitalOcean dashboard
   - Load balancer health
   - Database connectivity
   - CDN status (Cloudflare)

3. Common causes & fixes:
   - **Database connection pool exhausted:**
     ```bash
     # Scale database connection pool
     kubectl patch deployment api --patch='{"spec":{"template":{"spec":{"containers":[{"name":"api","env":[{"name":"DB_POOL_SIZE","value":"50"}]}]}}}}'
     ```
   - **Out of memory:**
     ```bash
     # Scale up pods
     kubectl scale deployment api --replicas=5
     ```
   - **Certificate expired:**
     ```bash
     # Emergency cert renewal
     certbot renew --force-renewal
     ```

4. If cannot resolve quickly:
   - Activate disaster recovery site
   - Switch to static maintenance page
   - Notify users via status page

**Communication Template:**
```
🚨 INCIDENT ALERT [P0]
Status: Platform unavailable
Started: [Timestamp]
Impact: All users unable to access CONFIT
Investigating: Root cause analysis in progress
Updates: Every 15 minutes
```

### 4.2 PAYMENT SYSTEM FAILURE (P0)

**Detection:** Payment errors spike, Paymob/Fawry alerts  
**Impact:** Users cannot complete purchases

**Response Steps:**
1. Check payment gateway status:
   - Paymob status page
   - Fawry status page
   - Our payment service logs

2. If gateway is down:
   - Enable offline payment mode (Fawry reference generation)
   - Display explanatory banner to users
   - Pause paid order processing

3. If our service issue:
   - Check payment service logs: `kubectl logs -f deployment/payment-service`
   - Verify webhook endpoints responding
   - Check database connection for payment logs

4. Security check:
   - Review for fraud attempts
   - Check if DDoS related
   - Verify payment credentials not exposed

**Communication Template:**
```
🚨 PAYMENT INCIDENT [P1]
Status: Payment processing delays
Started: [Timestamp]
Impact: Some users experiencing payment failures
Workaround: Fawry payment codes still working
ETA: Resolution expected within 1 hour
```

### 4.3 DATA BREACH / SECURITY INCIDENT (P0)

**Detection:** Security alerts, unusual access patterns, user reports  
**Impact:** Potential personal data exposure

**Response Steps (CRITICAL):**
1. **STOP - DO NOT PANIC**
   - Isolate affected systems immediately
   - Preserve logs and evidence
   - Do NOT delete anything

2. **Invoke Security Protocol:**
   - Contact CISO immediately
   - Page DPO: dpo@confit.app
   - Invoke legal if needed
   - Secure war room

3. **Assessment:**
   - What data was accessed?
   - How many users affected?
   - When did breach start?
   - Is attack ongoing?

4. **Containment:**
   - Revoke compromised credentials
   - Block malicious IPs
   - Disable affected endpoints
   - Enable additional logging

5. **Required Notifications (Law 151/2020):**
   - Notify PDPC within 72 hours
   - Notify affected users without undue delay
   - Document breach and response

6. **Egypt-Specific Requirements:**
   - File report with PDPC: https://pdpc.gov.eg
   - Consult with Egyptian legal counsel
   - Prepare Arabic/English notifications

**Communication Template (External):**
```
Important Security Notice

We recently became aware of [brief description]. 
We have taken immediate action to [response].

What data was involved: [data categories]
Steps we took: [actions]
What you should do: [user recommendations]

Contact our DPO: dpo@confit.app
```

### 4.4 AI/SERVICES DOWN (P1)

**Detection:** Try-on failures, AI service errors  
**Impact:** Virtual try-on unavailable, style recommendations degraded

**Response Steps:**
1. Check GPU server status:
   ```bash
   # Check local GPU server
   ssh gpu-server "nvidia-smi && systemctl status tryon-service"
   
   # Check remote GPU cluster
   curl https://gpu-cluster.confit.app/health
   ```

2. If GPU server issue:
   - Check if thermal throttling: `nvidia-smi -q -d TEMPERATURE`
   - Restart tryon service: `systemctl restart tryon-service`
   - Check disk space: `df -h`

3. If load too high:
   - Enable request queue
   - Show "High demand" message to users
   - Scale GPU cluster if possible

4. Fallback mode:
   - Disable try-on feature
   - Show static recommendations
   - Queue requests for later processing

### 4.5 DATABASE PERFORMANCE (P1/P2)

**Detection:** Slow queries, connection timeouts, high CPU  
**Impact:** Slow response times, potential timeouts

**Response Steps:**
1. Check database metrics:
   ```sql
   -- Check active connections
   SELECT count(*) FROM pg_stat_activity;
   
   -- Check slow queries
   SELECT * FROM pg_stat_statements 
   ORDER BY mean_time DESC 
   LIMIT 10;
   
   -- Check locks
   SELECT * FROM pg_locks WHERE NOT granted;
   ```

2. Common fixes:
   - Kill long-running queries
   - Add index if missing query pattern identified
   - Scale database instance vertically
   - Enable read replica for queries

3. Emergency read-only mode:
   ```bash
   # If database at risk, enable maintenance mode
   kubectl set env deployment/api MAINTENANCE_MODE=true
   ```

### 4.6 CDN/DDoS ATTACK (P1)

**Detection:** Traffic spike, Cloudflare alerts, slow response  
**Impact:** Performance degradation, potential outage

**Response Steps:**
1. Check Cloudflare dashboard
2. Enable "Under Attack" mode if DDoS suspected
3. Review firewall rules
4. Enable rate limiting: 100 req/min per IP
5. Contact Cloudflare support if needed

### 4.7 THIRD-PARTY SERVICE DOWN (P2)

**Payment gateway, SMS provider, etc.**

**Response Steps:**
1. Check vendor status page
2. Enable fallback provider if configured
3. Queue non-critical operations
4. Update status page
5. Notify users of temporary limitations

---

## 5. INCIDENT TICKET TEMPLATE

```markdown
## INCIDENT-[ID]: [Title]

**Severity:** P0/P1/P2/P3  
**Status:** Open/Resolved  
**Started:** [Timestamp]  
**Resolved:** [Timestamp]  
**Duration:** [Duration]  

### Impact
- Affected Services: [List]
- Affected Users: [Count/Percentage]
- Revenue Impact: [EGP if known]

### Timeline
- [Time] - Issue detected via [source]
- [Time] - [Action taken]
- [Time] - Issue resolved

### Root Cause
[Detailed explanation]

### Resolution
[How it was fixed]

### Follow-up Actions
- [ ] [Action item] - Owner - Due date
- [ ] Update monitoring
- [ ] Runbook update
- [ ] Postmortem scheduled

### Lessons Learned
[What we learned]
```

---

## 6. CONTACTS & RESOURCES

**Internal:**
- Emergency Hotline: +20-XXX-XXXX-XXX
- Slack: #incidents-confidential
- Email: incidents@confit.app

**Vendors:**
- Paymob Support: support@paymob.com
- Fawry Support: [Number]
- Cloudflare: https://dash.cloudflare.com
- AWS Support: [Enterprise support]

**Authorities (for data incidents):**
- PDPC (Egypt): https://pdpc.gov.eg
- Legal Counsel: legal@confit.app
- DPO: dpo@confit.app

---

**Remember: Speed of response > Perfect response. Fix first, analyze later.**
