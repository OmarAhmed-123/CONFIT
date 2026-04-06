"""
CONFIT Backend — Sales Analytics Router
=======================================
RESTful API endpoints for the Sales Analytics Table component.

Features:
- Filtered sales data with server-side sorting and pagination
- Summary statistics for filtered data
- Filter options for UI components
- CSV/JSON export functionality
- Store-scoped data access via authentication
- Caching with automatic invalidation
"""

import logging
from datetime import datetime, timezone
from typing import Annotated, Optional, List

import hashlib
import json
from fastapi import APIRouter, HTTPException, Depends, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from database.session import get_db
from database.session import SessionLocal
from database.models import Store, User as UserModel, UserRole, AppRole
from services.sales_analytics_service_v2 import (
    SalesAnalyticsServiceV2,
    get_sales_analytics_service_v2,
)
from schemas.sales_analytics_schemas import (
    SalesFilterRequest,
    SalesSortRequest,
    PaginationRequest,
    SalesQueryRequest,
    SalesQueryResponse,
    SalesSummaryResponse,
    FilterOptionsResponse,
    ExportRequest,
    ExportResponse,
    SaleCategory,
    CustomerSegment,
    ReturnStatus,
    DateRangePreset,
    SaleSortField,
    SortDirection,
)
from utils.auth_deps import require_auth
from services.auth_service import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sales-analytics", tags=["Sales Analytics"])


# ─── Dependency Injection ─────────────────────────────────────────────────────

def get_service(db: Session = Depends(get_db)) -> SalesAnalyticsServiceV2:
    """Get SalesAnalyticsServiceV2 instance with DB session."""
    return get_sales_analytics_service_v2(db)


# ─── Main Query Endpoint ───────────────────────────────────────────────────────

@router.post(
    "/query",
    response_model=SalesQueryResponse,
    summary="Query sales records with filtering, sorting, and pagination",
    description="""
    Query sales records for the authenticated store owner with advanced filtering,
    server-side sorting, and pagination.
    
    **Authentication Required**: JWT token in Authorization header.
    
    **Store Scoping**: Results are automatically scoped to the authenticated user's store.
    
    **Caching**: Results are cached for 10 minutes. Use `skip_cache=true` to bypass.
    """,
)
async def query_sales(
    request: SalesQueryRequest,
    response: Response,
    user: UserProfile = Depends(require_auth),
    service: SalesAnalyticsServiceV2 = Depends(get_service),
    skip_cache: bool = Query(False, description="Skip cache and fetch fresh data"),
):
    """
    Query sales records with filtering, sorting, and pagination.
    
    Request body contains:
    - `filters`: Filter parameters (categories, date range, price, segments, etc.)
    - `sort`: Sort field and direction
    - `pagination`: Page number and limit
    
    Returns paginated sales records with formatted display fields.
    """
    # Get store_id from user profile (enforce store scoping)
    store_id = _get_user_store_id(user)
    if not store_id:
        raise HTTPException(
            status_code=403,
            detail="User does not have access to any store. Please contact support.",
        )
    
    try:
        query_response = service.query_sales(
            store_id=store_id,
            filters=request.filters,
            sort=request.sort,
            pagination=request.pagination,
            use_cache=not skip_cache,
        )
        _attach_cache_headers(
            response=response,
            store_id=store_id,
            payload={
                "filters": request.filters.model_dump(),
                "sort": request.sort.model_dump(),
                "pagination": request.pagination.model_dump(),
            },
            max_age_seconds=30 if query_response.cached else 15,
        )
        response.headers["X-Data-Freshness-Seconds"] = "30" if query_response.cached else "5"
        return query_response
    except Exception as e:
        logger.error("Failed to query sales for store %s: %s", store_id, e)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve sales data. Please try again.",
        )


@router.get(
    "",
    response_model=SalesQueryResponse,
    summary="Get sales records (GET variant for simple queries)",
    description="""
    GET endpoint for simple sales queries. Supports query parameters for basic filtering.
    For advanced filtering, use the POST /query endpoint.
    """,
)
async def get_sales(
    response: Response,
    user: UserProfile = Depends(require_auth),
    service: SalesAnalyticsServiceV2 = Depends(get_service),
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=500, description="Items per page"),
    # Sorting
    sort_by: SaleSortField = Query(SaleSortField.SALE_DATE, description="Sort field"),
    sort_order: SortDirection = Query(SortDirection.DESC, description="Sort direction"),
    # Filters
    categories: Optional[str] = Query(None, description="Comma-separated categories"),
    date_range: DateRangePreset = Query(DateRangePreset.THIS_MONTH, description="Date range preset"),
    product_types: Optional[str] = Query(None, description="Comma-separated product types"),
    price_min: Optional[float] = Query(None, ge=0, description="Minimum price"),
    price_max: Optional[float] = Query(None, ge=0, description="Maximum price"),
    customer_segments: Optional[str] = Query(None, description="Comma-separated segments"),
    return_statuses: Optional[str] = Query(None, description="Comma-separated return statuses"),
    search: Optional[str] = Query(None, max_length=200, description="Search query"),
    skip_cache: bool = Query(False, description="Skip cache"),
):
    """
    GET endpoint for simple sales queries with query parameters.
    """
    store_id = _get_user_store_id(user)
    if not store_id:
        return {
            "success": True,
            "data": [],
            "pagination": {
                "total_rows": 0,
                "current_page": page,
                "page_size": limit,
                "total_pages": 0,
                "has_next": False,
                "has_previous": False,
            },
            "filters_applied": {},
            "sort_applied": {"sort_by": str(sort_by), "sort_order": str(sort_order)},
            "cached": False,
            "cache_expires_at": None,
        }
    
    # Parse comma-separated parameters
    def parse_list(value: Optional[str]) -> Optional[List[str]]:
        return value.split(",") if value else None
    
    # Build filter request
    filters = SalesFilterRequest(
        categories=[SaleCategory(c) for c in parse_list(categories)] if categories else None,
        date_range_preset=date_range,
        product_types=parse_list(product_types),
        price_min=price_min,
        price_max=price_max,
        customer_segments=[CustomerSegment(s) for s in parse_list(customer_segments)] if customer_segments else None,
        return_statuses=[ReturnStatus(s) for s in parse_list(return_statuses)] if return_statuses else None,
        search=search,
    )
    
    sort = SalesSortRequest(sort_by=sort_by, sort_order=sort_order)
    pagination = PaginationRequest(page=page, limit=limit)
    
    try:
        query_response = service.query_sales(
            store_id=store_id,
            filters=filters,
            sort=sort,
            pagination=pagination,
            use_cache=not skip_cache,
        )
        _attach_cache_headers(
            response=response,
            store_id=store_id,
            payload={
                "filters": filters.model_dump(),
                "sort": sort.model_dump(),
                "pagination": pagination.model_dump(),
            },
            max_age_seconds=30 if query_response.cached else 15,
        )
        response.headers["X-Data-Freshness-Seconds"] = "30" if query_response.cached else "5"
        return query_response
    except Exception as e:
        logger.error("GET sales query failed for store %s: %s", store_id, e)
        return {
            "success": True,
            "data": [],
            "pagination": {
                "total_rows": 0,
                "current_page": page,
                "page_size": limit,
                "total_pages": 0,
                "has_next": False,
                "has_previous": False,
            },
            "filters_applied": {},
            "sort_applied": {"sort_by": str(sort_by), "sort_order": str(sort_order)},
            "cached": False,
            "cache_expires_at": None,
        }


# ─── Summary Statistics Endpoint ───────────────────────────────────────────────

@router.post(
    "/summary",
    response_model=SalesSummaryResponse,
    summary="Get summary statistics for filtered sales",
    description="""
    Get aggregated statistics for sales data matching the filter criteria.
    
    Returns:
    - Total sales count and revenue
    - Average order value and profit margin
    - Return rate percentage
    - Breakdown by category and customer segment
    """,
)
async def get_sales_summary(
    request: SalesFilterRequest,
    response: Response,
    user: UserProfile = Depends(require_auth),
    service: SalesAnalyticsServiceV2 = Depends(get_service),
    skip_cache: bool = Query(False, description="Skip cache"),
):
    """
    Get summary statistics for filtered sales data.
    """
    store_id = _get_user_store_id(user)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store access configured.")
    
    try:
        summary = service.get_summary(
            store_id=store_id,
            filters=request,
            use_cache=not skip_cache,
        )
        _attach_cache_headers(
            response=response,
            store_id=store_id,
            payload={"filters": request.model_dump(), "endpoint": "summary"},
            max_age_seconds=20,
        )
        response.headers["X-Data-Freshness-Seconds"] = "60"
        return summary
    except Exception as e:
        logger.error("Failed to get sales summary for store %s: %s", store_id, e)
        raise HTTPException(status_code=500, detail="Failed to calculate summary.")


@router.get(
    "/summary",
    response_model=SalesSummaryResponse,
    summary="Get summary statistics (GET variant)",
)
async def get_sales_summary_get(
    response: Response,
    user: UserProfile = Depends(require_auth),
    service: SalesAnalyticsServiceV2 = Depends(get_service),
    date_range: DateRangePreset = Query(DateRangePreset.THIS_MONTH),
    categories: Optional[str] = Query(None),
    skip_cache: bool = Query(False),
):
    """GET variant for summary statistics."""
    store_id = _get_user_store_id(user)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store access configured.")
    
    filters = SalesFilterRequest(
        categories=[SaleCategory(c) for c in categories.split(",")] if categories else None,
        date_range_preset=date_range,
    )
    
    try:
        summary = service.get_summary(
            store_id=store_id,
            filters=filters,
            use_cache=not skip_cache,
        )
        _attach_cache_headers(
            response=response,
            store_id=store_id,
            payload={"filters": filters.model_dump(), "endpoint": "summary"},
            max_age_seconds=20,
        )
        response.headers["X-Data-Freshness-Seconds"] = "60"
        return summary
    except Exception as e:
        logger.error("GET summary failed for store %s: %s", store_id, e)
        raise HTTPException(status_code=500, detail="Failed to calculate summary.")


# ─── Filter Options Endpoint ───────────────────────────────────────────────────

@router.get(
    "/filter-options",
    response_model=FilterOptionsResponse,
    summary="Get available filter options",
    description="""
    Get available filter options for the sales analytics UI.
    
    Returns:
    - Categories with their available product types (for cascade filtering)
    - Customer segments
    - Return statuses
    - Price range (min/max from actual data)
    """,
)
async def get_filter_options(
    response: Response,
    user: UserProfile = Depends(require_auth),
    service: SalesAnalyticsServiceV2 = Depends(get_service),
):
    """
    Get available filter options for UI components.
    """
    store_id = _get_user_store_id(user)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store access configured.")
    
    try:
        filter_options = service.get_filter_options(store_id)
        _attach_cache_headers(
            response=response,
            store_id=store_id,
            payload={"endpoint": "filter-options"},
            max_age_seconds=300,
        )
        response.headers["X-Data-Freshness-Seconds"] = "300"
        return filter_options
    except Exception as e:
        logger.error("Failed to get filter options for store %s: %s", store_id, e)
        raise HTTPException(status_code=500, detail="Failed to retrieve filter options.")


# ─── Export Endpoints ──────────────────────────────────────────────────────────

@router.post(
    "/export",
    response_model=ExportResponse,
    summary="Export sales data",
    description="""
    Export filtered sales data to CSV or JSON format.
    
    Returns a download URL or the file content directly.
    Maximum 10,000 rows per export.
    """,
)
async def export_sales(
    request: ExportRequest,
    user: UserProfile = Depends(require_auth),
    service: SalesAnalyticsServiceV2 = Depends(get_service),
):
    """
    Export sales data to CSV or JSON format.
    """
    store_id = _get_user_store_id(user)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store access configured.")
    
    try:
        if request.format == "csv":
            content, row_count = service.export_sales_csv(
                store_id=store_id,
                filters=request.filters,
            )
            file_name = f"sales-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
        else:
            content, row_count = service.export_sales_json(
                store_id=store_id,
                filters=request.filters,
            )
            file_name = f"sales-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        
        return ExportResponse(
            success=True,
            file_name=file_name,
            format=request.format,
            row_count=row_count,
            generated_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error("Export failed for store %s: %s", store_id, e)
        raise HTTPException(status_code=500, detail="Failed to export sales data.")


@router.get(
    "/export/csv",
    summary="Download sales data as CSV",
    description="Download filtered sales data as a CSV file directly.",
    response_class=StreamingResponse,
)
async def download_sales_csv(
    user: UserProfile = Depends(require_auth),
    service: SalesAnalyticsServiceV2 = Depends(get_service),
    date_range: DateRangePreset = Query(DateRangePreset.THIS_MONTH),
    categories: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """
    Download sales data as CSV file.
    """
    store_id = _get_user_store_id(user)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store access configured.")
    
    filters = SalesFilterRequest(
        categories=[SaleCategory(c) for c in categories.split(",")] if categories else None,
        date_range_preset=date_range,
        search=search,
    )
    
    try:
        content, row_count = service.export_sales_csv(
            store_id=store_id,
            filters=filters,
        )
        
        if row_count == 0:
            raise HTTPException(status_code=404, detail="No data to export for the selected filters.")
        
        file_name = f"sales-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{file_name}"',
                "X-Row-Count": str(row_count),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("CSV download failed for store %s: %s", store_id, e)
        raise HTTPException(status_code=500, detail="Failed to generate CSV export.")


@router.get(
    "/export/json",
    summary="Download sales data as JSON",
    description="Download filtered sales data as a JSON file directly.",
    response_class=StreamingResponse,
)
async def download_sales_json(
    user: UserProfile = Depends(require_auth),
    service: SalesAnalyticsServiceV2 = Depends(get_service),
    date_range: DateRangePreset = Query(DateRangePreset.THIS_MONTH),
    categories: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """
    Download sales data as JSON file.
    """
    store_id = _get_user_store_id(user)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store access configured.")
    
    filters = SalesFilterRequest(
        categories=[SaleCategory(c) for c in categories.split(",")] if categories else None,
        date_range_preset=date_range,
        search=search,
    )
    
    try:
        content, row_count = service.export_sales_json(
            store_id=store_id,
            filters=filters,
        )
        
        if row_count == 0:
            raise HTTPException(status_code=404, detail="No data to export for the selected filters.")
        
        file_name = f"sales-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{file_name}"',
                "X-Row-Count": str(row_count),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("JSON download failed for store %s: %s", store_id, e)
        raise HTTPException(status_code=500, detail="Failed to generate JSON export.")


# ─── Cache Management Endpoints ────────────────────────────────────────────────

@router.delete(
    "/cache",
    summary="Invalidate sales analytics cache",
    description="""
    Invalidate all cached sales analytics data for the authenticated store.
    Call this after sales data is updated or when fresh data is required.
    """,
)
async def invalidate_cache(
    user: UserProfile = Depends(require_auth),
    service: SalesAnalyticsServiceV2 = Depends(get_service),
):
    """
    Invalidate cache for the authenticated user's store.
    """
    store_id = _get_user_store_id(user)
    if not store_id:
        raise HTTPException(status_code=403, detail="No store access configured.")
    
    try:
        invalidated = service.invalidate_cache(store_id)
        return {
            "success": True,
            "message": f"Invalidated {invalidated} cache entries for store {store_id}",
            "store_id": store_id,
            "invalidated_count": invalidated,
        }
    except Exception as e:
        logger.error("Cache invalidation failed for store %s: %s", store_id, e)
        raise HTTPException(status_code=500, detail="Failed to invalidate cache.")


# ─── Health Check ──────────────────────────────────────────────────────────────

@router.get(
    "/health",
    include_in_schema=False,
)
async def sales_analytics_health():
    """Health check endpoint for the sales analytics service."""
    return {
        "status": "ok",
        "service": "sales-analytics",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─── Helper Functions ──────────────────────────────────────────────────────────

def _get_user_store_id(user: UserProfile) -> Optional[str]:
    """
    Extract store_id from user profile for data scoping.
    
    In production, this would be derived from:
    - User's role assignment (brand_manager, store_manager)
    - User's associated store(s)
    - JWT claims containing store_id
    
    For now, we check for store_id in the user profile or use a default.
    """
    # Check if user profile has store_id
    if hasattr(user, 'store_id') and user.store_id:
        return user.store_id
    
    # Check if user has stores in their profile
    if hasattr(user, 'stores') and user.stores:
        return user.stores[0].get('id') if isinstance(user.stores[0], dict) else user.stores[0].id
    
    # For brand managers, they might have access to multiple stores
    # In that case, we'd need a store selector in the UI
    # For now, return None to indicate no store access
    # This will trigger a 403 error prompting the user to configure store access
    
    # DB-backed fallback: read roles from persisted user_roles and map owners/admins.
    db = SessionLocal()
    try:
        row = db.query(UserModel).filter(UserModel.email == user.email).first()
        if row:
            roles = {r.role for r in db.query(UserRole).filter(UserRole.user_id == row.id).all()}
            if AppRole.admin in roles or AppRole.brand_manager in roles:
                store = db.query(Store).first()
                if store:
                    return str(store.id)
    finally:
        db.close()
    
    return None


def _attach_cache_headers(
    response: Response,
    store_id: str,
    payload: dict,
    max_age_seconds: int,
) -> None:
    raw = json.dumps({"store_id": store_id, **payload}, sort_keys=True, default=str).encode("utf-8")
    etag = hashlib.md5(raw).hexdigest()
    response.headers["ETag"] = f'W/"{etag}"'
    response.headers["Cache-Control"] = f"private, max-age={max_age_seconds}, stale-while-revalidate=30"
