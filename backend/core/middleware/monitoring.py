"""
CONFIT Backend - Monitoring Middleware
======================================
Prometheus metrics collection and health checks.
"""

import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# PROMETHEUS METRICS
# ─────────────────────────────────────────────────────────────────────────────

# Request counter
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

# Request duration histogram
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Active requests gauge
ACTIVE_REQUESTS = Gauge(
    "http_requests_active",
    "Active HTTP requests"
)

# Error counter
ERROR_COUNT = Counter(
    "http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "error_type"]
)

# Database connection pool gauge
DB_CONNECTIONS = Gauge(
    "db_connections_active",
    "Active database connections"
)

# Redis connection gauge
REDIS_CONNECTIONS = Gauge(
    "redis_connections_active",
    "Active Redis connections"
)

# Celery queue length gauge
CELERY_QUEUE_LENGTH = Gauge(
    "celery_queue_length",
    "Celery queue length",
    ["queue"]
)


# ─────────────────────────────────────────────────────────────────────────────
# METRICS MIDDLEWARE
# ─────────────────────────────────────────────────────────────────────────────

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting Prometheus metrics."""
    
    # Paths to exclude from metrics
    EXCLUDED_PATHS = {"/health", "/metrics", "/favicon.ico"}
    
    # Paths to normalize (replace IDs with placeholders)
    NORMALIZE_PATTERNS = [
        # UUIDs
        (r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "{id}"),
        # Numeric IDs
        (r"/\d+(?=/|$)", "/{id}"),
    ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        
        # Skip excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Normalize endpoint path
        endpoint = self._normalize_path(request.url.path)
        method = request.method
        
        # Track active requests
        ACTIVE_REQUESTS.inc()
        
        # Start timing
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=response.status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            return response
            
        except Exception as exc:
            # Record error
            ERROR_COUNT.labels(
                method=method,
                endpoint=endpoint,
                error_type=type(exc).__name__
            ).inc()
            
            raise
            
        finally:
            ACTIVE_REQUESTS.dec()
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path by replacing dynamic segments."""
        import re
        
        normalized = path
        for pattern, replacement in self.NORMALIZE_PATTERNS:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        return normalized


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────

class HealthChecker:
    """Health check for all services."""
    
    def __init__(self):
        self._checks = {}
    
    def register_check(self, name: str, check_func: Callable):
        """Register a health check function."""
        self._checks[name] = check_func
    
    async def check_all(self) -> dict:
        """Run all health checks."""
        results = {}
        
        for name, check_func in self._checks.items():
            try:
                result = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
                results[name] = {
                    "status": "healthy" if result else "unhealthy",
                    "details": result,
                }
            except Exception as e:
                results[name] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
        
        # Overall status
        all_healthy = all(r["status"] == "healthy" for r in results.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": time.time(),
            "checks": results,
        }


# Create global health checker
health_checker = HealthChecker()


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

import asyncio


async def check_database():
    """Check database connectivity."""
    try:
        from infrastructure.database import async_engine
        
        async with async_engine.connect() as conn:
            await conn.execute("SELECT 1")
        
        return {"connected": True}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"connected": False, "error": str(e)}


async def check_redis():
    """Check Redis connectivity."""
    try:
        from infrastructure.redis_client import get_cache_client
        
        client = await get_cache_client()
        await client.ping()
        
        return {"connected": True}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {"connected": False, "error": str(e)}


async def check_elasticsearch():
    """Check Elasticsearch connectivity."""
    try:
        from infrastructure.elasticsearch import get_elasticsearch_client
        
        client = await get_elasticsearch_client()
        await client.info()
        
        return {"connected": True}
    except Exception as e:
        logger.error(f"Elasticsearch health check failed: {e}")
        return {"connected": False, "error": str(e)}


# Register default health checks
health_checker.register_check("database", check_database)
health_checker.register_check("redis", check_redis)
health_checker.register_check("elasticsearch", check_elasticsearch)


# ─────────────────────────────────────────────────────────────────────────────
# METRICS ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


async def health_endpoint():
    """Health check endpoint."""
    return await health_checker.check_all()


async def readiness_endpoint():
    """Readiness probe endpoint (Kubernetes)."""
    result = await health_checker.check_all()
    
    if result["status"] == "healthy":
        return result
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=result)


async def liveness_endpoint():
    """Liveness probe endpoint (Kubernetes)."""
    return {"status": "alive"}
