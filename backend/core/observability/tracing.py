"""
CONFIT Backend - OpenTelemetry Tracing
======================================
Distributed tracing with OpenTelemetry SDK.
"""

from __future__ import annotations

import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Global tracer instance
_tracer: Optional[trace.Tracer] = None
_propagator = TraceContextTextMapPropagator()


def setup_tracing(
    service_name: str = "confit-api",
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    console_export: bool = False,
) -> trace.Tracer:
    """
    Configure OpenTelemetry tracing.

    Args:
        service_name: Service name for traces
        service_version: Service version
        otlp_endpoint: OTLP collector endpoint (e.g., http://localhost:4317)
        console_export: Export traces to console (for development)

    Returns:
        Configured tracer instance
    """
    global _tracer

    # Create resource with service info
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add exporters
    if console_export:
        # Console exporter for development
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))

    if otlp_endpoint:
        # OTLP exporter for production (Jaeger, Honeycomb, etc.)
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        except ImportError:
            pass

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    # Create tracer
    _tracer = trace.get_tracer(service_name, service_version)

    return _tracer


def get_tracer() -> trace.Tracer:
    """Get the configured tracer instance."""
    global _tracer
    if _tracer is None:
        # Return a no-op tracer if not configured
        _tracer = trace.get_tracer(__name__)
    return _tracer


def inject_trace_headers(headers: dict) -> dict:
    """Inject trace context into headers for downstream calls."""
    _propagator.inject(headers)
    return headers


def extract_trace_headers(headers: dict) -> None:
    """Extract trace context from incoming headers."""
    ctx = _propagator.extract(headers)
    trace.set_span_in_context(trace.get_current_span(), ctx)


class traced:
    """Context manager for creating traced spans."""

    def __init__(self, name: str, attributes: Optional[dict] = None):
        self.name = name
        self.attributes = attributes or {}
        self._span = None

    def __enter__(self):
        tracer = get_tracer()
        self._span = tracer.start_span(self.name)
        for key, value in self.attributes.items():
            self._span.set_attribute(key, value)
        return self._span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._span:
            if exc_type:
                self._span.record_exception(exc_val)
                self._span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc_val)))
            self._span.end()
        return False  # Don't suppress exceptions


def trace_function(name: Optional[str] = None):
    """Decorator for tracing functions."""
    def decorator(func):
        import functools
        span_name = name or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with traced(span_name):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with traced(span_name):
                return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
