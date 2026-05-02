# CONFIT Deployment Guide

## Overview

This document outlines the deployment strategy for the CONFIT fashion-tech platform backend and frontend, with a focus on **Egypt-close hosting** to minimize latency for our primary user base.

---

## Recommended Hosting Options (Egypt-Optimized)

### Option 1: AWS `me-south-1` (Bahrain) — Recommended
- **Latency to Cairo**: ~25-40ms
- **Why**: Closest AWS region to Egypt. Full managed services (RDS, ElastiCache, ECS/Fargate, S3).
- **Best for**: Teams already using AWS; need managed Postgres/Redis.
- **Cost estimate**: Medium-High

### Option 2: Hetzner Cloud Falkenstein (Germany)
- **Latency to Cairo**: ~80ms
- **Why**: Cost-effective bare-metal and cloud VMs. Great bandwidth pricing.
- **Best for**: Cost-conscious early stage; comfortable self-managing Docker.
- **Cost estimate**: Low

### Option 3: DigitalOcean Frankfurt (Germany)
- **Latency to Cairo**: ~85ms
- **Why**: Simple managed Kubernetes (DOKS) and managed Postgres. Easier than AWS.
- **Best for**: Teams wanting managed services without AWS complexity.
- **Cost estimate**: Low-Medium

### Option to Avoid
- **AWS `us-east-1` (N. Virginia)**: 200ms+ latency to Cairo. Only use for multi-region failover, never as primary.

---

## Architecture (Docker Compose → Production)

### Local Development
```bash
cd backend
docker compose up --build
```
Services: Postgres 16, Redis 7, API (FastAPI), Celery Worker + Beat, Prometheus, Grafana.

### Production (Docker → ECS/K8s)
1. Build multi-stage image (`backend/Dockerfile`)
2. Push to registry (ECR / DOCR / Hetzner)
3. Run with:
   - **API**: 2+ replicas behind ALB/nginx
   - **Worker**: Celery workers scaled horizontally
   - **DB**: Managed Postgres (RDS / DO Managed DB)
   - **Cache**: Managed Redis (ElastiCache / DO Managed Redis)
   - **Object Storage**: S3-compatible (AWS S3 / DO Spaces)

---

## Environment Variables Checklist

Copy from `backend/.env.example` and set at least:

| Variable | Purpose |
|----------|---------|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Postgres connection string |
| `REDIS_URL` | Redis connection string |
| `SECRET_KEY` | JWT signing key (≥32 bytes) |
| `SENTRY_DSN` | Error/performance monitoring |
| `PAYMOB_API_KEY` | Egypt payment provider |
| `STRIPE_SECRET_KEY` | Global card payments |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | S3 backups / ECR push |
| `INTERNAL_API_KEY` | Protects `/api/metrics` |

---

## CI/CD

GitHub Actions workflow `.github/workflows/ci.yml` runs on every push to `main` or `develop`:

1. `pytest` with coverage ≥ 80%
2. `ruff check`
3. `mypy --strict`
4. `bandit` security scan
5. `safety check` dependency audit
6. Docker image build + push to ECR (only on `main`)

---

## Monitoring Stack

| Service | Local URL | Purpose |
|---------|-----------|---------|
| Grafana | http://localhost:3000 | Dashboards & alerts |
| Prometheus | http://localhost:9090 | Metrics scraping |
| API Metrics | `/api/metrics` | Protected by `INTERNAL_API_KEY` |
| Health | `/api/health` | Kubernetes liveness |
| Readiness | `/api/health/ready` | DB + Redis check |
| Deep Health | `/api/health/deep` | External provider check |

---

## Security Checklist

- [ ] `INTERNAL_API_KEY` is set and rotated
- [ ] Sentry PII scrubbing enabled (`before_send` strips emails/phones)
- [ ] CORS `allow_credentials=True` never paired with `"*"` origins
- [ ] Database credentials not committed to source control
- [ ] `ENVIRONMENT=production` disables debug endpoints

---

## Rollback Plan

1. ECR keeps last 5 tagged images
2. Blue/green or rolling deploy with health checks (`/api/health/ready`)
3. If error rate > 1% for 2 minutes, auto-rollback to previous image

---

## Support & Escalation

- Alerts routed to Sentry + Grafana alertmanager
- On-call rotation documented in `docs/RUNBOOK.md`
