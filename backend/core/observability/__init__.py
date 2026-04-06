"""
CONFIT Observability Module
===========================
Structured logging, OpenTelemetry tracing, and metrics collection.
"""

from core.observability.logging import get_logger, setup_logging
from core.observability.tracing import get_tracer, setup_tracing
from core.observability.metrics import metrics, setup_metrics

__all__ = [
    "get_logger",
    "setup_logging",
    "get_tracer",
    "setup_tracing",
    "metrics",
    "setup_metrics",
]
