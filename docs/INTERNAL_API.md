# CONFIT Internal API Documentation

This document describes internal-only API endpoints that are hidden from the public API documentation (`include_in_schema=False`). These endpoints are intended for:
- Internal ML operations
- Service-to-service communication
- Debugging and diagnostics
- Admin operations

---

## Internal Routers

### 1. Dataset Export (`/api/dataset/*`)
**Purpose:** Export backend-ready dataset scaffolding for ML pipeline integration.

**Endpoints:**
- `GET /api/dataset/sample` - Export sample dataset for model training

**Access:** Admin only  
**Frontend Usage:** None - ML pipeline only

---

### 2. Training Pipeline (`/api/training/*`)
**Purpose:** ML model training job management.

**Endpoints:**
- `POST /api/training/jobs` - Start a new training job
- `GET /api/training/jobs/{job_id}` - Get training job status

**Access:** Admin only  
**Frontend Usage:** None - Internal ML ops

---

### 3. Ecosystem (`/api/ecosystem/*`)
**Purpose:** Cross-feature orchestration and unified user journey.

**Endpoints:**
- `POST /api/ecosystem/events/emit` - Event ingestion for telemetry

**Access:** Internal service-to-service  
**Frontend Usage:** Limited - telemetry events only

---

### 4. Debug Logs (`/debug/logs/*`)
**Purpose:** Debug logging and diagnostics.

**Access:** Development/Staging only  
**Frontend Usage:** None

---

### 5. Debug Payments (`/debug/payments/*`)
**Purpose:** Payment integration debugging and health checks.

**Endpoints:** (27 routes total)
- Health checks for payment providers
- Payment log inspection
- Client error reporting

**Access:** Development/Staging only  
**Frontend Usage:** Limited - error reporting

**Environment Guard:** Disabled in production (returns 403)

---

### 6. Notification Analytics (`/api/notification-analytics/*`)
**Purpose:** ML-driven notification analytics.

**Access:** Admin/Internal  
**Frontend Usage:** `notificationAnalyticsApi.ts` (partial)

---

### 7. Notification ML (`/api/notification-ml/*`)
**Purpose:** ML notification optimization (delivery prediction, drift detection).

**Endpoints:** (12 routes)
- Delivery prediction models
- Drift detection
- Feature engineering

**Access:** Internal services  
**Frontend Usage:** None

---

## Data Compliance (Public but Internal-Focused)

### `/api/v1/me/data/*`
**Purpose:** GDPR compliance and data subject rights (Law 151/2020).

**Endpoints:**
- `GET /api/v1/me/data/summary` - Data summary for user
- `POST /api/v1/me/data/export` - Request data export
- `GET /api/v1/me/data/export/{export_id}/status` - Check export status
- `DELETE /api/v1/me/data/` - Request account deletion
- `GET /api/v1/me/data/retention-policies` - View retention policies
- `POST /api/v1/me/data/object` - Object to data processing
- `GET /api/v1/me/data/dpo-contact` - DPO contact info

**Access:** Authenticated users  
**Frontend Usage:** `/profile/data` page

---

## Brand Ecosystem (Internal)

### `/api/brand-ecosystem/*`
**Purpose:** Cross-group brand ecosystem integration.

**Access:** Internal brand intelligence  
**Frontend Usage:** None

---

## Router Configuration

```python
# In main.py - routers with include_in_schema=False:
app.include_router(dataset_export_router, include_in_schema=False)
app.include_router(training_pipeline_router, include_in_schema=False)
app.include_router(notification_analytics_router, include_in_schema=False)
app.include_router(notification_ml_router, include_in_schema=False)
app.include_router(ecosystem_router, include_in_schema=False)
app.include_router(debug_logs_router, include_in_schema=False)
app.include_router(debug_payments_router, include_in_schema=False)
```

---

## Related Audit Findings

- **A.1:** Payment Debug Endpoints (27 routes) - Documented as internal
- **A.3:** Training Pipeline Router - Documented as internal
- **A.6:** Ecosystem Router - Documented as internal
- **A.9:** Brand Ecosystem Router - Documented as internal

---

*Last updated: Phase E Cleanup (2026-04-25)*
