"""CONFIT Backend — Centralized Error Handling."""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class AppError(Exception):
    """Base application error."""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "APP_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_http_exception(self) -> HTTPException:
        return HTTPException(
            status_code=self.status_code,
            detail={
                "error": self.error_code,
                "message": self.message,
                "details": self.details,
            }
        )


class ValidationError(AppError):
    """Input validation error."""
    
    def __init__(self, message: str, field: str = None, details: Dict = None):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class NotFoundError(AppError):
    """Resource not found error."""
    
    def __init__(self, resource: str, identifier: str = None):
        details = {"resource": resource}
        if identifier:
            details["identifier"] = identifier
        super().__init__(
            message=f"{resource} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details=details,
        )


class AuthError(AppError):
    """Authentication/authorization error."""
    
    def __init__(self, message: str = "Unauthorized", error_code: str = "AUTH_ERROR"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code,
        )


class ForbiddenError(AppError):
    """Permission denied error."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
        )


class ConflictError(AppError):
    """Resource conflict error."""
    
    def __init__(self, message: str, resource: str = None):
        details = {"resource": resource} if resource else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            details=details,
        )


class RateLimitError(AppError):
    """Rate limit exceeded error."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT",
            details={"retry_after": retry_after},
        )
