"""CONFIT Backend — Base Schema."""

from typing import Optional, List, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, validator
from pydantic import ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None},
        use_enum_values=True,
        validate_assignment=True,
    )


class PaginationParams(BaseModel):
    """Pagination parameters."""
    skip: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=20, ge=1, le=500, description="Number of items to return")


class PaginatedResponse(BaseModel):
    """Generic paginated response."""
    total: int
    skip: int
    limit: int
    items: List[Any]


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: str
    code: str = "ERROR"
    details: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseModel):
    """Standard success response."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
