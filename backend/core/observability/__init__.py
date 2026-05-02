"""
CONFIT Observability Module
===========================
Structured logging, OpenTelemetry tracing, metrics collection, Sentry, and Prometheus.
"""

from core.observability.logging import get_logger, setup_logging
from core.observability.tracing import get_tracer, setup_tracing
from core.observability.metrics import metrics, setup_metrics
from core.observability.sentry import init_sentry
from core.observability.prometheus_metrics import (
    confit_orders_total,
    confit_payments_total,
    confit_ai_cost_usd_total,
    confit_donor_coupons_redeemed_total,
    get_metrics_text,
)

__all__ = [
    "get_logger",
    "setup_logging",
    "get_tracer",
    "setup_tracing",
    "metrics",
    "setup_metrics",
    "init_sentry",
    "confit_orders_total",
    "confit_payments_total",
    "confit_ai_cost_usd_total",
    "confit_donor_coupons_redeemed_total",
    "get_metrics_text",
]
