"""CONFIT Backend — Standardized Response Format."""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""
    
    success: bool = True
    data: List[T]
    total: int
    page: int
    per_page: int
    pages: int


def success_response(
    data: Any = None,
    message: str = None,
    meta: Dict = None,
) -> Dict[str, Any]:
    """Create a success response."""
    return {
        "success": True,
        "data": data,
        "message": message,
        "meta": meta,
    }


def error_response(
    message: str,
    error_code: str = "ERROR",
    details: Dict = None,
) -> Dict[str, Any]:
    """Create an error response."""
    return {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "details": details or {},
        },
    }


def paginated_response(
    data: List[Any],
    total: int,
    page: int = 1,
    per_page: int = 20,
) -> Dict[str, Any]:
    """Create a paginated response."""
    return {
        "success": True,
        "data": data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
    }
