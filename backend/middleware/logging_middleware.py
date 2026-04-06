"""
CONFIT Backend - Enhanced Logging Middleware
============================================
Comprehensive request/response logging with performance tracking.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass, field

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.config import settings


logger = logging.getLogger(__name__)


@dataclass
class RequestLog:
    """Log entry for a request."""
    request_id: str
    method: str
    path: str
    query_params: Dict[str, Any]
    client_ip: str
    user_agent: str
    user_id: Optional[str] = None
    request_body: Optional[Dict[str, Any]] = None
    request_headers: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ResponseLog:
    """Log entry for a response."""
    request_id: str
    status_code: int
    response_time_ms: float
    response_size: int
    response_headers: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PerformanceMetrics:
    """Performance metrics for a request."""
    request_id: str
    path: str
    method: str
    response_time_ms: float
    db_queries: int = 0
    db_time_ms: float = 0
    cache_hits: int = 0
    cache_misses: int = 0
    external_calls: int = 0
    external_time_ms: float = 0


# Paths to exclude from detailed logging
EXCLUDED_PATHS = {
    "/health",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
}

# Headers to sanitize (remove sensitive data)
SENSITIVE_HEADERS = {
    "authorization",
    "x-api-key",
    "x-auth-token",
    "cookie",
    "set-cookie",
}

# Fields to sanitize in request body
SENSITIVE_BODY_FIELDS = {
    "password",
    "password_confirm",
    "current_password",
    "new_password",
    "otp_code",
    "otp_secret",
    "token",
    "refresh_token",
    "api_key",
    "secret",
}


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Remove sensitive headers from log."""
    sanitized = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADERS:
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = value
    return sanitized


def sanitize_body(body: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive fields from request body."""
    if not isinstance(body, dict):
        return body
    
    sanitized = {}
    for key, value in body.items():
        if key.lower() in SENSITIVE_BODY_FIELDS:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_body(value)
        else:
            sanitized[key] = value
    return sanitized


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Enhanced logging middleware with:
    - Request/response logging
    - Performance tracking
    - Error logging with stack traces
    - Audit trail for sensitive operations
    - Structured JSON logging
    """
    
    def __init__(
        self,
        app: ASGIApp,
        log_requests: bool = True,
        log_responses: bool = True,
        log_body: bool = True,
        log_headers: bool = True,
        slow_request_threshold_ms: float = 1000.0,
    ):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_body = log_body and settings.ENVIRONMENT != "production"
        self.log_headers = log_headers
        self.slow_request_threshold_ms = slow_request_threshold_ms
        
        # Performance tracking
        self._performance_metrics: Dict[str, PerformanceMetrics] = {}
    
    def _should_log_detailed(self, path: str) -> bool:
        """Check if path should have detailed logging."""
        return path not in EXCLUDED_PATHS
    
    def _get_request_id(self, request: Request) -> str:
        """Get or generate request ID."""
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        return request_id
    
    async def _get_request_body(self, request: Request) -> Optional[Dict[str, Any]]:
        """Safely get request body."""
        if not self.log_body:
            return None
        
        try:
            body = await request.body()
            if not body:
                return None
            
            # Try to parse as JSON
            try:
                return sanitize_body(json.loads(body))
            except json.JSONDecodeError:
                return {"raw": f"[{len(body)} bytes]"}
        except Exception:
            return None
    
    def _log_request(self, request: Request, request_id: str, body: Optional[Dict[str, Any]]):
        """Log request details."""
        if not self.log_requests:
            return
        
        path = request.url.path
        
        # Skip detailed logging for excluded paths
        if not self._should_log_detailed(path):
            logger.debug(f"Request: {request.method} {path}")
            return
        
        # Build log entry
        client_ip = request.client.host if request.client else "unknown"
        
        log_entry = RequestLog(
            request_id=request_id,
            method=request.method,
            path=path,
            query_params=dict(request.query_params),
            client_ip=client_ip,
            user_agent=request.headers.get("User-Agent", ""),
            user_id=getattr(request.state, "user_id", None),
            request_body=body,
            request_headers=sanitize_headers(dict(request.headers)) if self.log_headers else {},
        )
        
        # Log as structured JSON
        logger.info(
            f"Request started: {request.method} {path}",
            extra={
                "request_id": request_id,
                "request": {
                    "method": log_entry.method,
                    "path": log_entry.path,
                    "query": log_entry.query_params,
                    "client_ip": log_entry.client_ip,
                    "user_id": log_entry.user_id,
                },
                "type": "request_start",
            }
        )
    
    def _log_response(
        self,
        request: Request,
        request_id: str,
        response: Response,
        response_time_ms: float,
    ):
        """Log response details."""
        if not self.log_responses:
            return
        
        path = request.url.path
        
        # Build log entry
        log_entry = ResponseLog(
            request_id=request_id,
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            response_size=int(response.headers.get("content-length", 0)),
            response_headers=sanitize_headers(dict(response.headers)) if self.log_headers else {},
        )
        
        # Determine log level based on status and response time
        log_level = logging.INFO
        extra_data = {
            "request_id": request_id,
            "response": {
                "status_code": log_entry.status_code,
                "response_time_ms": round(response_time_ms, 2),
                "response_size": log_entry.response_size,
            },
            "type": "response",
        }
        
        # Slow request warning
        if response_time_ms > self.slow_request_threshold_ms:
            log_level = logging.WARNING
            extra_data["slow_request"] = True
            logger.warning(
                f"Slow request: {request.method} {path} took {response_time_ms:.2f}ms",
                extra=extra_data,
            )
        
        # Error responses
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        
        logger.log(
            log_level,
            f"Response: {response.status_code} for {request.method} {path} ({response_time_ms:.2f}ms)",
            extra=extra_data,
        )
    
    def _log_error(
        self,
        request: Request,
        request_id: str,
        error: Exception,
        response_time_ms: float,
    ):
        """Log error details."""
        logger.error(
            f"Error processing request: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "error": {
                    "type": type(error).__name__,
                    "message": str(error),
                },
                "response_time_ms": round(response_time_ms, 2),
                "type": "error",
            },
            exc_info=True,
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging."""
        # Generate request ID
        request_id = self._get_request_id(request)
        
        # Store request ID in state for use in handlers
        request.state.request_id = request_id
        
        # Get request body (for logging)
        body = await self._get_request_body(request) if self._should_log_detailed(request.url.path) else None
        
        # Log request
        self._log_request(request, request_id, body)
        
        # Track start time
        start_time = time.perf_counter()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            response_time_ms = (time.perf_counter() - start_time) * 1000
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Log response
            self._log_response(request, request_id, response, response_time_ms)
            
            return response
            
        except Exception as e:
            # Calculate response time
            response_time_ms = (time.perf_counter() - start_time) * 1000
            
            # Log error
            self._log_error(request, request_id, e, response_time_ms)
            
            # Re-raise for error handlers
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get logging metrics."""
        return {
            "total_requests_logged": len(self._performance_metrics),
        }


class AuditLogger:
    """
    Specialized logger for audit events.
    
    Used for logging sensitive operations like:
    - Authentication events
    - Permission changes
    - Data modifications
    - CARE operations
    """
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
    
    def log(
        self,
        action: str,
        actor_type: str,
        actor_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ):
        """
        Log an audit event.
        
        Args:
            action: The action performed (e.g., "user.login", "campaign.create")
            actor_type: Type of actor (e.g., "user", "system", "admin")
            actor_id: ID of the actor
            resource_type: Type of resource affected
            resource_id: ID of the resource
            details: Additional details
            request_id: Request ID for correlation
            ip_address: Client IP address
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "actor": {
                "type": actor_type,
                "id": actor_id,
            },
            "resource": {
                "type": resource_type,
                "id": resource_id,
            },
            "details": details or {},
            "request_id": request_id,
            "ip_address": ip_address,
        }
        
        self.logger.info(
            f"Audit: {action} by {actor_type}:{actor_id}",
            extra={
                "audit": True,
                "event": event,
            }
        )
    
    def log_auth(
        self,
        action: str,
        user_id: Optional[str],
        success: bool,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log authentication event."""
        self.log(
            action=f"auth.{action}",
            actor_type="user",
            actor_id=user_id,
            details={
                "success": success,
                **(details or {}),
            },
            ip_address=ip_address,
        )
    
    def log_care(
        self,
        action: str,
        actor_type: str,
        actor_id: Optional[str],
        campaign_id: Optional[str] = None,
        beneficiary_id: Optional[str] = None,
        voucher_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log CARE-related event."""
        self.log(
            action=f"care.{action}",
            actor_type=actor_type,
            actor_id=actor_id,
            resource_type="campaign" if campaign_id else None,
            resource_id=campaign_id,
            details={
                "beneficiary_id": beneficiary_id,
                "voucher_id": voucher_id,
                **(details or {}),
            },
        )


class PerformanceTracker:
    """
    Track performance metrics during request processing.
    
    Usage:
        with performance_tracker.track("db_query") as metric:
            # execute query
            metric.queries += 1
    """
    
    def __init__(self):
        self._metrics: Dict[str, PerformanceMetrics] = {}
    
    def start_request(self, request_id: str, path: str, method: str):
        """Start tracking a request."""
        self._metrics[request_id] = PerformanceMetrics(
            request_id=request_id,
            path=path,
            method=method,
            response_time_ms=0,
        )
    
    def end_request(self, request_id: str, response_time_ms: float):
        """End tracking a request."""
        if request_id in self._metrics:
            self._metrics[request_id].response_time_ms = response_time_ms
    
    def record_db_query(self, request_id: str, time_ms: float):
        """Record a database query."""
        if request_id in self._metrics:
            self._metrics[request_id].db_queries += 1
            self._metrics[request_id].db_time_ms += time_ms
    
    def record_cache_hit(self, request_id: str):
        """Record a cache hit."""
        if request_id in self._metrics:
            self._metrics[request_id].cache_hits += 1
    
    def record_cache_miss(self, request_id: str):
        """Record a cache miss."""
        if request_id in self._metrics:
            self._metrics[request_id].cache_misses += 1
    
    def record_external_call(self, request_id: str, time_ms: float):
        """Record an external API call."""
        if request_id in self._metrics:
            self._metrics[request_id].external_calls += 1
            self._metrics[request_id].external_time_ms += time_ms
    
    def get_metrics(self, request_id: str) -> Optional[PerformanceMetrics]:
        """Get metrics for a request."""
        return self._metrics.get(request_id)
    
    def clear_request(self, request_id: str):
        """Clear metrics for a request."""
        if request_id in self._metrics:
            del self._metrics[request_id]


# Global instances
audit_logger = AuditLogger()
performance_tracker = PerformanceTracker()


def setup_logging_middleware(app):
    """Setup logging middleware for the application."""
    app.add_middleware(
        LoggingMiddleware,
        log_requests=True,
        log_responses=True,
        log_body=settings.ENVIRONMENT != "production",
        log_headers=True,
        slow_request_threshold_ms=1000.0,
    )
    
    return audit_logger, performance_tracker
