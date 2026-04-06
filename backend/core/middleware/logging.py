"""
CONFIT Backend - Logging Middleware
===================================
Request/response logging with structured logging.
"""

import time
import json
import logging
from datetime import datetime, timezone
from typing import Callable, Optional
from uuid import uuid4

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message


logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""
    
    # Paths to exclude from logging
    EXCLUDED_PATHS = {"/health", "/metrics", "/favicon.ico"}
    
    # Sensitive headers to redact
    SENSITIVE_HEADERS = {
        "authorization", "cookie", "set-cookie", "x-api-key",
        "x-auth-token", "x-refresh-token"
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        
        # Skip logging for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Generate request ID
        request_id = request.headers.get("x-request-id", str(uuid4()))
        
        # Start timing
        start_time = time.time()
        
        # Log request
        await self._log_request(request, request_id)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response
            self._log_response(request, response, request_id, duration_ms)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as exc:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            self._log_error(request, exc, request_id, duration_ms)
            
            # Re-raise exception
            raise
    
    async def _log_request(self, request: Request, request_id: str) -> None:
        """Log incoming request."""
        # Get client info
        client_host = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else 0
        
        # Get headers (redact sensitive)
        headers = dict(request.headers)
        for key in self.SENSITIVE_HEADERS:
            if key in headers:
                headers[key] = "[REDACTED]"
        
        # Get query params
        query_params = dict(request.query_params)
        
        # Build log data
        log_data = {
            "event": "request",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": query_params,
            "client_ip": client_host,
            "user_agent": request.headers.get("user-agent", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Log request body for POST/PUT/PATCH (be careful with large bodies)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if len(body) < 1000:  # Only log small bodies
                    try:
                        log_data["body_size"] = len(body)
                    except:
                        pass
            except:
                pass
        
        logger.info(json.dumps(log_data))
    
    def _log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        duration_ms: float,
    ) -> None:
        """Log outgoing response."""
        log_data = {
            "event": "response",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Determine log level based on status code
        if response.status_code >= 500:
            logger.error(json.dumps(log_data))
        elif response.status_code >= 400:
            logger.warning(json.dumps(log_data))
        else:
            logger.info(json.dumps(log_data))
    
    def _log_error(
        self,
        request: Request,
        exc: Exception,
        request_id: str,
        duration_ms: float,
    ) -> None:
        """Log error during request processing."""
        log_data = {
            "event": "error",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "duration_ms": round(duration_ms, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        logger.error(json.dumps(log_data), exc_info=True)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add unique request ID."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID to request state."""
        request_id = request.headers.get("x-request-id", str(uuid4()))
        
        # Store in request state
        request.state.request_id = request_id
        
        response = await call_next(request)
        
        # Add to response
        response.headers["X-Request-ID"] = request_id
        
        return response


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware for correlation ID tracking across services."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track correlation ID for distributed tracing."""
        correlation_id = request.headers.get(
            "x-correlation-id",
            request.headers.get("x-request-id", str(uuid4()))
        )
        
        request.state.correlation_id = correlation_id
        
        response = await call_next(request)
        
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
