"""
CONFIT Backend - Error Handler Middleware
=========================================
Global exception handling with structured error responses.
"""

import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# ERROR RESPONSE
# ─────────────────────────────────────────────────────────────────────────────

class ErrorResponse:
    """Standardized error response with Arabic localization support."""
    
    @staticmethod
    def create(
        status_code: int,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        """Create error response dictionary with localization."""
        from core.error_messages import get_error_message
        
        # If error_code provided, use localized message
        if error_code:
            localized_message = get_error_message(error_code, language)
        else:
            localized_message = message
        
        return {
            "error": {
                "code": error_code or f"ERR_{status_code}",
                "message": localized_message,
                "original_message": message if error_code else None,
                "details": details,
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "language": language,
            },
            "status": status_code,
        }


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM EXCEPTIONS
# ─────────────────────────────────────────────────────────────────────────────

class AppException(Exception):
    """Base application exception."""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)


class NotFoundException(AppException):
    """Resource not found exception."""
    
    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id '{identifier}' not found"
        
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details={"resource": resource, "identifier": identifier},
        )


class UnauthorizedException(AppException):
    """Unauthorized access exception."""
    
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
        )


class ForbiddenException(AppException):
    """Forbidden access exception."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
        )


class ConflictException(AppException):
    """Conflict exception."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            details=details,
        )


class ValidationException(AppException):
    """Validation error exception."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class RateLimitException(AppException):
    """Rate limit exceeded exception."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after},
        )
        self.retry_after = retry_after


class ServiceUnavailableException(AppException):
    """Service unavailable exception."""
    
    def __init__(self, service: str, message: Optional[str] = None):
        super().__init__(
            message=message or f"{service} is temporarily unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
            details={"service": service},
        )


# ─────────────────────────────────────────────────────────────────────────────
# EXCEPTION HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_request_language(request: Request) -> str:
    """Extract language from request headers or query params."""
    # Check query parameter first
    language = request.query_params.get("lang")
    if language in ("en", "ar"):
        return language
    
    # Check Accept-Language header
    accept_lang = request.headers.get("Accept-Language", "")
    if accept_lang.startswith("ar"):
        return "ar"
    
    # Check X-Preferred-Language header (custom app header)
    preferred = request.headers.get("X-Preferred-Language", "")
    if preferred in ("en", "ar"):
        return preferred
    
    return "en"


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application exceptions with localization."""
    request_id = getattr(request.state, "request_id", str(uuid4()))
    language = _get_request_language(request)
    
    # Log error
    logger.error(
        f"Application error: {exc.error_code} - {exc.message}",
        extra={
            "request_id": request_id,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "language": language,
        }
    )
    
    response_data = ErrorResponse.create(
        status_code=exc.status_code,
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details,
        request_id=request_id,
        language=language,
    )
    
    headers = {}
    if isinstance(exc, RateLimitException):
        headers["Retry-After"] = str(exc.retry_after)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data,
        headers=headers,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions with localization."""
    request_id = getattr(request.state, "request_id", str(uuid4()))
    language = _get_request_language(request)
    
    # Log if server error
    if exc.status_code >= 500:
        logger.error(
            f"HTTP error: {exc.status_code} - {exc.detail}",
            extra={"request_id": request_id}
        )
    
    response_data = ErrorResponse.create(
        status_code=exc.status_code,
        message=str(exc.detail),
        error_code=f"HTTP_{exc.status_code}",
        request_id=request_id,
        language=language,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors with localization."""
    request_id = getattr(request.state, "request_id", str(uuid4()))
    language = _get_request_language(request)
    
    # Format validation errors
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    
    logger.warning(
        f"Validation error: {len(errors)} errors",
        extra={"request_id": request_id, "errors": errors}
    )
    
    response_data = ErrorResponse.create(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation failed",
        error_code="VALIDATION_ERROR",
        details={"errors": errors},
        request_id=request_id,
        language=language,
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_data,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with localization."""
    request_id = getattr(request.state, "request_id", str(uuid4()))
    language = _get_request_language(request)
    
    # Log full error
    logger.exception(
        f"Unexpected error: {type(exc).__name__} - {str(exc)}",
        extra={"request_id": request_id}
    )
    
    # Don't expose internal errors in production
    from core.config import settings
    
    if settings.is_production:
        message = "An unexpected error occurred"
        details = None
    else:
        message = str(exc)
        details = {
            "type": type(exc).__name__,
            "traceback": traceback.format_exc().split("\n"),
        }
    
    response_data = ErrorResponse.create(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=message,
        error_code="INTERNAL_ERROR",
        details=details,
        request_id=request_id,
        language=language,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_data,
    )


# ─────────────────────────────────────────────────────────────────────────────
# REGISTER HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    
    # Custom exceptions
    app.add_exception_handler(AppException, app_exception_handler)
    
    # HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    
    # Validation exceptions
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Generic exception (catch-all)
    app.add_exception_handler(Exception, generic_exception_handler)
