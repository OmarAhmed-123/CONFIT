"""
CONFIT Backend — Sales Analytics Service
========================================
Service layer for sales analytics with filtering, sorting, pagination,
caching, and store-scoped data access.
"""

import logging
import hashlib
import json
import csv
import io
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal

from sqlalchemy.orm import Session, Query
from sqlalchemy import and_, or_, func, desc, asc

from database.models import (
    SalesRecord,
    SaleCategory,
    CustomerSegment,
    ReturnStatus,
    Store,
    User,
)
from schemas.sales_analytics_schemas import (
    SalesFilterRequest,
    SalesSortRequest,
    PaginationRequest,
    SaleRecordResponse,
    PaginationMeta,
    SalesQueryResponse,
    SalesSummaryResponse,
    FilterOptionsResponse,
    CategoryProductTypes,
    create_sale_record_response,
)
from services.sales_transforms import (
    format_currency,
    format_date,
    format_percentage,
    get_date_range_preset,
    transform_record_for_export,
    format_summary_stats,
    CATEGORY_CONFIG,
)

logger = logging.getLogger(__name__)

# ─── Cache Configuration ──────────────────────────────────────────────────────

CACHE_TTL_SECONDS = 600  # 10 minutes default TTL
CACHE_TTL_SUMMARY = 300  # 5 minutes for summary stats
CACHE_TTL_FILTERS = 3600  # 1 hour for filter options


class SalesAnalyticsCache:
    """
    In-memory cache for sales analytics with TTL support.
    Falls back gracefully if Redis is unavailable.
    """
    
    _instance: Optional['SalesAnalyticsCache'] = None
    
    def __init__(self, default_ttl: int = CACHE_TTL_SECONDS):
        self._cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expiry)
        self._default_ttl = default_ttl
    
    @classmethod
    def get_instance(cls) -> 'SalesAnalyticsCache':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _make_key(
        self,
        store_id: str,
        filters: SalesFilterRequest,
        sort: SalesSortRequest,
        pagination: PaginationRequest,
    ) -> str:
        """Generate a unique cache key from query parameters."""
        key_data = {
            "store_id": store_id,
            "filters": filters.model_dump(),
            "sort": sort.model_dump(),
            "pagination": {"page": pagination.page, "limit": pagination.limit},
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _make_summary_key(self, store_id: str, filters: SalesFilterRequest) -> str:
        """Generate cache key for summary statistics."""
        key_data = {"store_id": store_id, "filters": filters.model_dump()}
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return f"summary:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key not in self._cache:
            return None
        
        value, expiry = self._cache[key]
        if datetime.now(timezone.utc).timestamp() > expiry:
            del self._cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self._default_ttl
        expiry = datetime.now(timezone.utc).timestamp() + ttl
        self._cache[key] = (value, expiry)
    
    def invalidate_store(self, store_id: str) -> int:
        """Invalidate all cache entries for a store."""
        keys_to_delete = [
            k for k in self._cache.keys()
            if store_id in str(self._cache[k][0])
        ]
        for key in keys_to_delete:
            del self._cache[key]
        return len(keys_to_delete)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()


class SalesAnalyticsService:
    """
    Service for querying and transforming sales analytics data.
    
    Features:
    - Store-scoped data access (enforced from auth context)
    - Multi-field filtering with cascade support
    - Server-side sorting and pagination
    - Caching with TTL and invalidation
    - Summary statistics calculation
    - Export generation (CSV/JSON)
    """
    
    def __init__(self, db: Session, cache: Optional[SalesAnalyticsCache] = None):
        self._db = db
        self._cache = cache or SalesAnalyticsCache.get_instance()
    
    # ─── Main Query Methods ─────────────────────────────────────────────────────
    
    def query_sales(
        self,
        store_id: str,
        filters: SalesFilterRequest,
        sort: SalesSortRequest,
        pagination: PaginationRequest,
        use_cache: bool = True,
    ) -> SalesQueryResponse:
        """
        Query sales records with filtering, sorting, and pagination.
        
        Args:
            store_id: Store ID from auth context (required for data scoping)
            filters: Filter parameters
            sort: Sort parameters
            pagination: Pagination parameters
            use_cache: Whether to use cached results
        
        Returns:
            SalesQueryResponse with data and metadata
        """
        # Check cache first
        cache_key = self._cache._make_key(store_id, filters, sort, pagination)
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                cached.cached = True
                return cached
        
        # Build base query with store scoping
        query = self._db.query(SalesRecord).filter(SalesRecord.store_id == store_id)
        
        # Apply filters
        query = self._apply_filters(query, filters)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply sorting
        query = self._apply_sorting(query, sort)
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.limit
        records = query.offset(offset).limit(pagination.limit).all()
        
        # Transform records to response format
        data = [create_sale_record_response(record) for record in records]
        
        # Build pagination metadata
        total_pages = max(1, (total_count + pagination.limit - 1) // pagination.limit)
        pagination_meta = PaginationMeta(
            total_rows=total_count,
            current_page=pagination.page,
            page_size=pagination.limit,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1,
        )
        
        # Build response
        response = SalesQueryResponse(
            success=True,
            data=data,
            pagination=pagination_meta,
            filters_applied=self._get_applied_filters(filters),
            sort_applied={"field": sort.sort_by.value, "direction": sort.sort_order.value},
            cached=False,
            cache_expires_at=datetime.now(timezone.utc) + timedelta(seconds=CACHE_TTL_SECONDS),
        )
        
        # Cache the response
        if use_cache:
            self._cache.set(cache_key, response, CACHE_TTL_SECONDS)
        
        return response
    
    def get_summary(
        self,
        store_id: str,
        filters: SalesFilterRequest,
        use_cache: bool = True,
    ) -> SalesSummaryResponse:
        """
        Get summary statistics for filtered sales data.
        
        Args:
            store_id: Store ID from auth context
            filters: Filter parameters
            use_cache: Whether to use cached results
        
        Returns:
            SalesSummaryResponse with aggregated statistics
        """
        # Check cache
        cache_key = self._cache._make_summary_key(store_id, filters)
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                return cached
        
        # Build query with store scoping and filters
        query = self._db.query(SalesRecord).filter(SalesRecord.store_id == store_id)
        query = self._apply_filters(query, filters)
        
        # Calculate aggregates
        records = query.all()
        
        if not records:
            return SalesSummaryResponse(
                total_sales=0,
                total_revenue=0.0,
                total_quantity=0,
                avg_order_value=0.0,
                avg_profit_margin=0.0,
                return_rate=0.0,
                sales_by_category={},
                revenue_by_category={},
                sales_by_segment={},
            )
        
        # Calculate statistics
        total_sales = len(records)
        total_revenue = sum(float(r.price) * r.quantity for r in records)
        total_quantity = sum(r.quantity for r in records)
        avg_order_value = total_revenue / total_sales if total_sales > 0 else 0
        avg_profit_margin = sum(float(r.profit_margin) for r in records) / total_sales if total_sales > 0 else 0
        
        # Return rate (percentage of returned items)
        returned_count = sum(1 for r in records if r.return_status == ReturnStatus.RETURNED)
        return_rate = (returned_count / total_sales * 100) if total_sales > 0 else 0
        
        # Breakdown by category
        sales_by_category: Dict[str, int] = {}
        revenue_by_category: Dict[str, float] = {}
        for r in records:
            cat = r.category.value if hasattr(r.category, 'value') else str(r.category)
            sales_by_category[cat] = sales_by_category.get(cat, 0) + 1
            revenue_by_category[cat] = revenue_by_category.get(cat, 0) + float(r.price) * r.quantity
        
        # Breakdown by customer segment
        sales_by_segment: Dict[str, int] = {}
        for r in records:
            seg = r.customer_segment.value if hasattr(r.customer_segment, 'value') else str(r.customer_segment)
            sales_by_segment[seg] = sales_by_segment.get(seg, 0) + 1
        
        response = SalesSummaryResponse(
            total_sales=total_sales,
            total_revenue=total_revenue,
            total_quantity=total_quantity,
            avg_order_value=avg_order_value,
            avg_profit_margin=avg_profit_margin,
            return_rate=return_rate,
            sales_by_category=sales_by_category,
            revenue_by_category=revenue_by_category,
            sales_by_segment=sales_by_segment,
        )
        
        # Cache the response
        if use_cache:
            self._cache.set(cache_key, response, CACHE_TTL_SUMMARY)
        
        return response
    
    def get_filter_options(self, store_id: str) -> FilterOptionsResponse:
        """
        Get available filter options for a store.
        
        Args:
            store_id: Store ID from auth context
        
        Returns:
            FilterOptionsResponse with available categories, segments, etc.
        """
        # Build category options with product types
        categories = [
            CategoryProductTypes(
                category=cat,
                product_types=config.get("product_types", []),
            )
            for cat, config in CATEGORY_CONFIG.items()
        ]
        
        # Get price range from database
        price_result = self._db.query(
            func.min(SalesRecord.price).label('min_price'),
            func.max(SalesRecord.price).label('max_price'),
        ).filter(SalesRecord.store_id == store_id).first()
        
        price_range = {
            "min": float(price_result.min_price) if price_result.min_price else 0,
            "max": float(price_result.max_price) if price_result.max_price else 50000,
        }
        
        return FilterOptionsResponse(
            categories=categories,
            customer_segments=list(CustomerSegment),
            return_statuses=list(ReturnStatus),
            price_range=price_range,
        )
    
    # ─── Export Methods ─────────────────────────────────────────────────────────
    
    def export_sales_csv(
        self,
        store_id: str,
        filters: SalesFilterRequest,
    ) -> Tuple[str, int]:
        """
        Export filtered sales data to CSV format.
        
        Args:
            store_id: Store ID from auth context
            filters: Filter parameters
        
        Returns:
            Tuple of (CSV string, row count)
        """
        # Build query with store scoping and filters
        query = self._db.query(SalesRecord).filter(SalesRecord.store_id == store_id)
        query = self._apply_filters(query, filters)
        
        # Sort by sale date descending for export
        query = query.order_by(desc(SalesRecord.sale_date))
        
        records = query.all()
        
        if not records:
            return "", 0
        
        # Transform records for export
        export_data = [transform_record_for_export(r, "csv") for r in records]
        
        # Generate CSV
        output = io.StringIO()
        if export_data:
            writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
            writer.writeheader()
            writer.writerows(export_data)
        
        return output.getvalue(), len(records)
    
    def export_sales_json(
        self,
        store_id: str,
        filters: SalesFilterRequest,
    ) -> Tuple[str, int]:
        """
        Export filtered sales data to JSON format.
        
        Args:
            store_id: Store ID from auth context
            filters: Filter parameters
        
        Returns:
            Tuple of (JSON string, row count)
        """
        # Build query with store scoping and filters
        query = self._db.query(SalesRecord).filter(SalesRecord.store_id == store_id)
        query = self._apply_filters(query, filters)
        
        # Sort by sale date descending for export
        query = query.order_by(desc(SalesRecord.sale_date))
        
        records = query.all()
        
        if not records:
            return "[]", 0
        
        # Transform records for export
        export_data = [transform_record_for_export(r, "json") for r in records]
        
        return json.dumps(export_data, indent=2, default=str), len(records)
    
    # ─── Cache Management ───────────────────────────────────────────────────────
    
    def invalidate_cache(self, store_id: str) -> int:
        """
        Invalidate all cached data for a store.
        Call this when sales data is updated.
        
        Args:
            store_id: Store ID to invalidate
        
        Returns:
            Number of cache entries invalidated
        """
        return self._cache.invalidate_store(store_id)
    
    # ─── Private Helper Methods ─────────────────────────────────────────────────
    
    def _apply_filters(self, query: Query, filters: SalesFilterRequest) -> Query:
        """Apply all filters to the query."""
        
        # Category filter (multi-select)
        if filters.categories:
            category_values = [c.value if hasattr(c, 'value') else c for c in filters.categories]
            query = query.filter(SalesRecord.category.in_(category_values))
        
        # Date range filter
        date_range = self._resolve_date_range(filters)
        if date_range.get("start"):
            query = query.filter(SalesRecord.sale_date >= date_range["start"])
        if date_range.get("end"):
            query = query.filter(SalesRecord.sale_date <= date_range["end"])
        
        # Product type filter (cascade based on category)
        if filters.product_types:
            query = query.filter(SalesRecord.product_type.in_(filters.product_types))
        
        # Price range filter
        if filters.price_min is not None:
            query = query.filter(SalesRecord.price >= filters.price_min)
        if filters.price_max is not None:
            query = query.filter(SalesRecord.price <= filters.price_max)
        
        # Customer segment filter (multi-select)
        if filters.customer_segments:
            segment_values = [s.value if hasattr(s, 'value') else s for s in filters.customer_segments]
            query = query.filter(SalesRecord.customer_segment.in_(segment_values))
        
        # Return status filter (multi-select)
        if filters.return_statuses:
            status_values = [s.value if hasattr(s, 'value') else s for s in filters.return_statuses]
            query = query.filter(SalesRecord.return_status.in_(status_values))
        
        # Search filter (product name, customer name, or SKU)
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                or_(
                    SalesRecord.product_name.ilike(search_term),
                    SalesRecord.customer_name.ilike(search_term),
                    SalesRecord.sku.ilike(search_term),
                )
            )
        
        return query
    
    def _resolve_date_range(self, filters: SalesFilterRequest) -> Dict[str, Optional[datetime]]:
        """Resolve date range from preset or custom dates."""
        if filters.date_range_preset == "custom":
            return {
                "start": datetime.combine(filters.custom_date_from, datetime.min.time()).replace(tzinfo=timezone.utc) if filters.custom_date_from else None,
                "end": datetime.combine(filters.custom_date_to, datetime.max.time()).replace(tzinfo=timezone.utc) if filters.custom_date_to else None,
            }
        
        preset = get_date_range_preset(filters.date_range_preset.value)
        return preset
    
    def _apply_sorting(self, query: Query, sort: SalesSortRequest) -> Query:
        """Apply sorting to the query."""
        # Map sort field to database column
        field_mapping = {
            "productName": SalesRecord.product_name,
            "category": SalesRecord.category,
            "price": SalesRecord.price,
            "quantity": SalesRecord.quantity,
            "customerName": SalesRecord.customer_name,
            "saleDate": SalesRecord.sale_date,
            "profitMargin": SalesRecord.profit_margin,
            "returnStatus": SalesRecord.return_status,
        }
        
        column = field_mapping.get(sort.sort_by.value, SalesRecord.sale_date)
        
        if sort.sort_order.value == "desc":
            return query.order_by(desc(column))
        return query.order_by(asc(column))
    
    def _get_applied_filters(self, filters: SalesFilterRequest) -> Dict[str, Any]:
        """Get a summary of applied filters for response metadata."""
        applied = {}
        
        if filters.categories:
            applied["categories"] = [c.value for c in filters.categories]
        if filters.date_range_preset:
            applied["date_range"] = filters.date_range_preset.value
        if filters.product_types:
            applied["product_types"] = filters.product_types
        if filters.price_min is not None or filters.price_max is not None:
            applied["price_range"] = {
                "min": filters.price_min,
                "max": filters.price_max,
            }
        if filters.customer_segments:
            applied["customer_segments"] = [s.value for s in filters.customer_segments]
        if filters.return_statuses:
            applied["return_statuses"] = [s.value for s in filters.return_statuses]
        if filters.search:
            applied["search"] = filters.search
        
        return applied


# ─── Service Factory ───────────────────────────────────────────────────────────

def get_sales_analytics_service(db: Session) -> SalesAnalyticsService:
    """Factory function for dependency injection."""
    return SalesAnalyticsService(db)
