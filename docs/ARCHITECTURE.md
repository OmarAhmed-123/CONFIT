# CONFIT Payment System - Architecture & Deployment Guide

## Overview

This document describes the production-ready payment system architecture for CONFIT, including background jobs, event system, observability, security, and deployment procedures.

---

## Architecture Summary

### Payment Providers

| Provider | Region | Currency | Flow |
|----------|--------|----------|------|
| **Stripe** | Global | USD, EUR, etc. | Checkout Session → Webhook |
| **Paymob** | MENA | EGP, SAR, AED | Iframe → Webhook/Polling |
| **PayPal** | Global | USD, EUR, etc. | Redirect → Capture → Webhook |

### System Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Checkout  │  │   Lottie    │  │    OAuth    │  │   Payment   │    │
│  │    Flow     │  │   Status    │  │   Buttons   │  │   Methods   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     API LAYER                                    │   │
│  │  /api/payments/unified/session  →  Create payment session       │   │
│  │  /api/payments/unified/webhooks →  Handle provider webhooks     │   │
│  │  /api/auth/oauth/*             →  OAuth login flows             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   MIDDLEWARE LAYER                               │   │
│  │  • Security Headers (CSP, HSTS, X-Frame-Options)                │   │
│  │  • Input Validation (SQL injection, XSS, path traversal)        │   │
│  │  • Rate Limiting (Redis token bucket)                           │   │
│  │  • Request Size Limits                                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   SERVICE LAYER                                  │   │
│  │  • PaymentOrchestrator - Unified payment interface              │   │
│  │  • InvoiceService - PDF generation                              │   │
│  │  • OAuthHandler - Multi-provider auth                           │   │
│  │  • AsyncEventBus - Redis-backed event dispatcher                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   BACKGROUND JOBS (Celery)                       │   │
│  │  • process_payment_success - Invoice, email, pickup            │   │
│  │  • process_payment_failed - Log, notify, metrics                │   │
│  │  • send_payment_receipt_email - SES/SendGrid                    │   │
│  │  • replay_dlq_task - Dead letter queue recovery                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   OBSERVABILITY                                   │   │
│  │  • Structured Logging (JSON, correlation IDs)                   │   │
│  │  • OpenTelemetry Tracing                                        │   │
│  │  • Prometheus Metrics                                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ PostgreSQL  │  │    Redis    │  │ Elasticsearch│ │    S3       │    │
│  │  (Orders,   │  │  (Cache,   │  │   (Search)   │  │  (Assets)   │    │
│  │  Payments)  │  │   Queue)   │  │              │  │             │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Environment Variables

### Required

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/confit

# Redis
CELERY_BROKER_URL=redis://localhost:6379/0

# Stripe
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Paymob
PAYMOB_API_KEY=xxx
PAYMOB_INTEGRATION_ID=12345
PAYMOB_IFRAME_ID=67890
PAYMOB_HMAC_SECRET=xxx

# PayPal
PAYPAL_CLIENT_ID=xxx
PAYPAL_CLIENT_SECRET=xxx
PAYPAL_MODE=live

# OAuth - Google
OAUTH_GOOGLE_CLIENT_ID=xxx
OAUTH_GOOGLE_CLIENT_SECRET=xxx
OAUTH_GOOGLE_REDIRECT_URI=https://api.confit.app/api/auth/oauth/google/callback

# OAuth - Facebook
OAUTH_FACEBOOK_CLIENT_ID=xxx
OAUTH_FACEBOOK_CLIENT_SECRET=xxx

# OAuth - Apple
OAUTH_APPLE_CLIENT_ID=xxx
OAUTH_APPLE_CLIENT_SECRET=xxx

# OAuth - X (Twitter)
OAUTH_X_CLIENT_ID=xxx
OAUTH_X_CLIENT_SECRET=xxx

# OAuth - TikTok
OAUTH_TIKTOK_CLIENT_ID=xxx
OAUTH_TIKTOK_CLIENT_SECRET=xxx

# Email
EMAIL_PROVIDER=ses  # or sendgrid
SES_SENDER_EMAIL=noreply@confit.app
AWS_SES_REGION=us-east-1
```

### Optional

```bash
# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
ASYNC_EVENT_BUS=1

# Security
ENVIRONMENT=production
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] **Database Migrations**
  ```bash
  alembic upgrade head
  ```

- [ ] **Redis Connectivity**
  ```bash
  redis-cli ping  # Should return PONG
  ```

- [ ] **Environment Variables**
  - All required secrets configured
  - Webhook secrets match provider settings

- [ ] **SSL Certificates**
  - Valid TLS certificate for API domain
  - HTTPS enforced

### Deployment Steps

1. **Deploy Backend**
   ```bash
   # Build and deploy
   docker-compose build api
   docker-compose up -d api

   # Run migrations
   docker-compose exec api alembic upgrade head
   ```

2. **Start Celery Workers**
   ```bash
   docker-compose up -d celery_worker
   docker-compose up -d celery_beat  # For scheduled tasks
   ```

3. **Configure Webhooks**

   | Provider | Webhook URL |
   |----------|-------------|
   | Stripe | `https://api.confit.app/api/stripe/webhook` |
   | Paymob | `https://api.confit.app/api/payments/unified/webhooks/paymob` |
   | PayPal | `https://api.confit.app/api/payments/unified/webhooks/paypal` |

4. **Verify Health**
   ```bash
   curl https://api.confit.app/health
   ```

5. **Run Validation**
   ```bash
   python scripts/validate_payment_flow.py --all
   ```

### Post-Deployment

- [ ] Monitor logs for errors
- [ ] Verify webhook delivery in provider dashboards
- [ ] Test payment flow end-to-end
- [ ] Check Prometheus metrics endpoint

---

## Monitoring & Alerting

### Key Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `confit_payment_requests_total` | Payment requests by provider/status | Error rate > 5% |
| `confit_payment_latency_seconds` | Payment processing time | p99 > 5s |
| `confit_payment_errors_total` | Payment errors by type | Any spike |
| `confit_celery_queue_depth` | Pending tasks in queue | > 1000 |
| `confit_webhook_processing_seconds` | Webhook processing time | p99 > 2s |

### Log Queries

```bash
# Payment errors
kubectl logs -l app=api | jq 'select(.level=="ERROR" and .message | contains("payment"))'

# Webhook failures
kubectl logs -l app=api | jq 'select(.message | contains("webhook") and .level=="WARNING")'

# DLQ entries
redis-cli LRANGE dead_letter:payments 0 -1
```

---

## Security Checklist

### Input Validation

- [x] SQL injection patterns detected
- [x] XSS patterns blocked
- [x] Path traversal prevented
- [x] Request body size limited

### Headers

- [x] `Content-Security-Policy` configured
- [x] `X-Frame-Options: DENY`
- [x] `Strict-Transport-Security` enabled
- [x] `X-Content-Type-Options: nosniff`

### Rate Limiting

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/payments/unified/session` | 10 | 1 minute |
| `/api/auth/login` | 5 | 1 minute |
| `/api/auth/register` | 3 | 1 hour |

### Webhook Security

- [x] Stripe signature verification
- [x] Paymob HMAC validation
- [x] PayPal signature verification
- [x] Replay attack prevention

---

## Troubleshooting

### Payment Stuck in Pending

1. Check webhook delivery in provider dashboard
2. Verify webhook secret matches
3. Check Celery worker logs
4. Manually trigger status check:
   ```bash
   curl -X POST https://api.confit.app/api/payments/{payment_id}/sync
   ```

### Celery Task Failures

1. Check DLQ:
   ```bash
   redis-cli LRANGE dead_letter:payments 0 -1
   ```

2. Replay failed tasks:
   ```bash
   celery -A workers.celery_app call workers.payment_tasks.replay_dlq_task
   ```

### High Error Rate

1. Check provider API status
2. Verify credentials not expired
3. Review recent deployments
4. Check database connectivity

---

## File Reference

### Backend Files Created/Modified

| File | Purpose |
|------|---------|
| `backend/workers/payment_tasks.py` | Celery tasks with DLQ, idempotency |
| `backend/services/payment_platform/async_event_bus.py` | Redis-backed event bus |
| `backend/services/payment_platform/event_bus.py` | Dual-mode event dispatcher |
| `backend/core/security/oauth_handler.py` | OAuth providers (Google, Facebook, Apple, X, TikTok) |
| `backend/core/observability/logging.py` | Structured JSON logging |
| `backend/core/observability/tracing.py` | OpenTelemetry tracing |
| `backend/core/observability/metrics.py` | Prometheus metrics |
| `backend/core/middleware/security.py` | Security headers, input validation |
| `backend/tests/test_payment_integration.py` | Integration tests |
| `backend/scripts/validate_payment_flow.py` | E2E validation script |

### Frontend Files Created/Modified

| File | Purpose |
|------|---------|
| `src/components/checkout/LottieStatus.tsx` | Real Lottie animations |
| `src/assets/lottie/payment-success.json` | Success animation |
| `src/assets/lottie/payment-error.json` | Error animation |
| `src/assets/lottie/payment-loading.json` | Loading spinner |

---

## Quick Reference Commands

```bash
# Start all services
docker-compose up -d

# View API logs
docker-compose logs -f api

# View Celery logs
docker-compose logs -f celery_worker

# Run tests
pytest backend/tests/test_payment_integration.py -v

# Validate payment flows
python backend/scripts/validate_payment_flow.py --all

# Check metrics
curl http://localhost:9090/metrics

# Monitor Celery
flower --port=5555
```

---

## Support Contacts

- **Stripe Support**: https://support.stripe.com
- **Paymob Support**: https://support.paymob.com
- **PayPal Support**: https://developer.paypal.com/support
