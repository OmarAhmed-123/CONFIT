"""
CONFIT Backend — Health Check Router
=====================================
Three tiers:
  /api/health       — Basic liveness (200 if alive)
  /api/health/ready — DB + Redis reachable
  /api/health/deep  — + external providers (Paymob, Firebase) pingable
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from core.api_response import ok, fail
from core.observability.prometheus_metrics import confit_active_users_gauge

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health", tags=["System"])


class HealthStatus(BaseModel):
    status: str
    timestamp: str
    version: str = "1.0.0"
    service: str = "confit-backend"


class ReadinessStatus(HealthStatus):
    checks: Dict[str, Any]


class DeepHealthStatus(ReadinessStatus):
    external_checks: Dict[str, Any]


# ── Helper: internal auth for /metrics ──────────────────────────────────

async def _metrics_auth(request: Request):
    token = request.headers.get("x-internal-api-key", "")
    expected = os.getenv("INTERNAL_API_KEY", "")
    if not expected:
        # If no key configured, allow in dev/staging only
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env not in ("development", "dev", "staging", "stage", "test"):
            raise HTTPException(status_code=403, detail="Metrics auth not configured")
        return
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid metrics API key")


# ── Basic Liveness ─────────────────────────────────────────────────────

@router.get("", response_model=HealthStatus)
async def health_basic():
    """Basic liveness probe — returns 200 if the process is alive."""
    import time
    return HealthStatus(
        status="ok",
        timestamp=str(time.time()),
    )


# ── Readiness (DB + Redis) ─────────────────────────────────────────────

@router.get("/ready", response_model=ReadinessStatus)
async def health_ready():
    """Readiness probe — checks database and Redis connectivity."""
    import time
    checks: Dict[str, Any] = {}
    all_healthy = True

    # Database check
    try:
        from database.session import SessionLocal
        db = SessionLocal()
        try:
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            checks["database"] = {"status": "healthy", "latency_ms": 0}
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        checks["database"] = {"status": "unhealthy", "error": str(exc)}
        all_healthy = False

    # Redis check
    try:
        import redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url, socket_connect_timeout=2)
        r.ping()
        checks["redis"] = {"status": "healthy"}
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        checks["redis"] = {"status": "unhealthy", "error": str(exc)}
        all_healthy = False

    status = "healthy" if all_healthy else "degraded"
    return ReadinessStatus(
        status=status,
        timestamp=str(time.time()),
        checks=checks,
    )


# ── Deep Health (+ external providers) ─────────────────────────────────

@router.get("/deep", response_model=DeepHealthStatus)
async def health_deep():
    """
    Deep health probe — includes external provider reachability.
    Returns degraded if any external service is unreachable.
    """
    import time
    start = time.time()

    # Start with readiness checks
    ready = await health_ready()
    checks = ready.checks
    external: Dict[str, Any] = {}

    # Paymob Accept health (lightweight auth ping)
    try:
        import httpx
        paymob_key = os.getenv("PAYMOB_API_KEY", "")
        if paymob_key:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    "https://accept.paymob.com/api/auth/tokens",
                    json={"api_key": paymob_key},
                )
            external["paymob"] = {
                "status": "healthy" if resp.status_code == 201 else "degraded",
                "status_code": resp.status_code,
            }
        else:
            external["paymob"] = {"status": "not_configured"}
    except Exception as exc:
        external["paymob"] = {"status": "unhealthy", "error": str(exc)}

    # Firebase health (lightweight project info)
    try:
        firebase_project = os.getenv("FIREBASE_PROJECT_ID", "")
        if firebase_project:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"https://firebasedynamiclinks.googleapis.com/v1/{firebase_project}/"
                )
            # We expect 403/401 — that means the service is reachable
            external["firebase"] = {
                "status": "healthy" if resp.status_code in (401, 403, 200) else "degraded",
                "status_code": resp.status_code,
            }
        else:
            external["firebase"] = {"status": "not_configured"}
    except Exception as exc:
        external["firebase"] = {"status": "unhealthy", "error": str(exc)}

    # Stripe API health
    try:
        stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
        if stripe_key:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://api.stripe.com/v1/",
                    headers={"Authorization": f"Bearer {stripe_key}"},
                )
            external["stripe"] = {
                "status": "healthy" if resp.status_code == 200 else "degraded",
                "status_code": resp.status_code,
            }
        else:
            external["stripe"] = {"status": "not_configured"}
    except Exception as exc:
        external["stripe"] = {"status": "unhealthy", "error": str(exc)}

    all_healthy = all(
        c.get("status") == "healthy" for c in list(checks.values()) + list(external.values())
    )
    any_unhealthy = any(
        c.get("status") == "unhealthy" for c in list(checks.values()) + list(external.values())
    )

    status = "healthy" if all_healthy else ("degraded" if not any_unhealthy else "unhealthy")

    return DeepHealthStatus(
        status=status,
        timestamp=str(time.time()),
        checks=checks,
        external_checks=external,
    )
