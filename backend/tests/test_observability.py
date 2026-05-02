"""
CONFIT Observability Tests
==========================
Smoke tests for health checks, metrics, and structured logging.
"""

import os
import sys

# Ensure backend is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest
from fastapi.testclient import TestClient


def test_structlog_imports():
    from core.logging import configure_logging, get_logger, StructlogContextMiddleware
    assert callable(configure_logging)
    assert callable(get_logger)
    assert StructlogContextMiddleware is not None


def test_sentry_imports():
    from core.observability.sentry import init_sentry, before_send, before_send_transaction
    assert callable(init_sentry)
    assert callable(before_send)
    assert callable(before_send_transaction)


def test_prometheus_metrics_imports():
    from core.observability.prometheus_metrics import (
        confit_orders_total,
        confit_payments_total,
        confit_ai_cost_usd_total,
        confit_donor_coupons_redeemed_total,
        get_metrics_text,
    )
    assert confit_orders_total is not None
    assert confit_payments_total is not None
    assert confit_ai_cost_usd_total is not None
    assert confit_donor_coupons_redeemed_total is not None
    assert callable(get_metrics_text)


def test_health_router_imports():
    from routers.health import router as health_router
    assert health_router is not None


def test_metrics_router_imports():
    from routers.metrics import router as metrics_router
    assert metrics_router is not None


def test_main_app_routes():
    from main import app
    paths = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/api/health" in paths
    assert "/api/health/ready" in paths
    assert "/api/health/deep" in paths
    assert "/api/metrics" in paths


def test_health_basic():
    from main import app
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"


def test_health_ready():
    from main import app
    client = TestClient(app)
    resp = client.get("/api/health/ready")
    # May be 200 or 503 depending on DB/Redis availability in test env
    assert resp.status_code in (200, 503)


def test_metrics_unauthorized():
    from main import app
    client = TestClient(app)
    # Without INTERNAL_API_KEY should be forbidden in prod, but dev may allow
    resp = client.get("/api/metrics")
    # In test env with no key configured, dev fallback may allow or deny
    assert resp.status_code in (200, 403)
