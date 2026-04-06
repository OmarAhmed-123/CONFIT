"""
CONFIT Backend — Sales Analytics Service V2
===========================================
Enhanced service layer using optimized partitioned queries.
Integrates with the new SalesTransaction model and query helpers.
"""

import logging
import hashlib
import json
import csv
import io
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, text

from database.sales_analytics_models import (
    SalesTransaction,
    StoreAnalyticsCache,
    SalesIngestionQueue,
    SalesCategory,
    CustomerSegment,
    ReturnStatus,
    DateRangePreset,
)
from database.sales_analytics_queries import (
    SalesQueryParams,
    build_sales_query,
    query_sales_list,
    query_sales_list_cursor,
    query_sales_summary,
    query_category_breakdown,
    query_segment_breakdown,
    query_top_products,
    query_realtime_metrics,
    get_cached_analytics,
    compute_and_cache_analytics,
    invalidate_analytics_cache,
    enqueue_sales_batch,
    process_ingestion_batch,
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
)
from services.sales_transforms import (
    format_currency,
    format_date,
    format_percentage,
    CATEGORY_CONFIG,
)
from repositories.sales_analytics_repository import SalesAnalyticsRepository
from services.analytics.sales_cache_backend import SalesCacheBackend

logger = logging.getLogger(__name__)

# ─── Cache Configuration ──────────────────────────────────────────────────────

CACHE_TTL_SECONDS = 300  # 5 minutes for list queries
CACHE_TTL_SUMMARY = 60   # 1 minute for summary (refreshed via materialized views)
CACHE_TTL_REALTIME = 30  # 30 seconds for real-time metrics


class SalesAnalyticsCacheV2:
    """
    Multi-layer cache for sales analytics.
    
    Layers:
    1. Application cache (Redis/in-memory) - Fast access
    2. Database cache (store_analytics_cache table) - Pre-computed summaries
    3. Materialized views - Aggregated analytics
    """
    
    _instance: Optional['SalesAnalyticsCacheV2'] = None
    
    def __init__(self, default_ttl: int = CACHE_TTL_SECONDS):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._default_ttl = default_ttl
        self._backend = SalesCacheBackend()
    
    @classmethod
    def get_instance(cls) -> 'SalesAnalyticsCacheV2':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _make_key(self, prefix: str, store_id: str, **kwargs) -> str:
        """Generate cache key with prefix."""
        key_data = {"store_id": store_id, **kwargs}
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        hash_part = hashlib.md5(key_string.encode()).hexdigest()[:12]
        return f"{prefix}:{store_id}:{hash_part}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        backend_value = self._backend.get(key)
        if backend_value is not None:
            return backend_value

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
        self._backend.set(key, value, ttl)
    
    def invalidate_store(self, store_id: str) -> int:
        """Invalidate all cache entries for a store."""
        keys_to_delete = [k for k in self._cache.keys() if store_id in k]
        for key in keys_to_delete:
            del self._cache[key]
        return len(keys_to_delete) + self._backend.invalidate_store(store_id)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()


class SalesAnalyticsServiceV2:
    """
    Enhanced service for sales analytics using partitioned queries.
    
    Features:
    - Store-scoped data access with partition pruning
    - Optimized multi-field filtering with composite indexes
    - Cursor-based pagination for deep queries
    - Multi-layer caching (application + database + materialized views)
    - Real-time metrics with controlled staleness
    """
    
    def __init__(self, db: Session, cache: Optional[SalesAnalyticsCacheV2] = None):
        self._db = db
        self._cache = cache or SalesAnalyticsCacheV2.get_instance()
    
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
        
        Uses optimized queries with:
        - Partition pruning by store_id
        - Composite indexes for multi-field filtering
        - Covering indexes for index-only scans
        """
        # Check application cache
        cache_key = self._cache._make_key(
            "list",
            store_id,
            filters=filters.model_dump(),
            sort=sort.model_dump(),
            page=pagination.page,
            limit=pagination.limit,
        )
        
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                if isinstance(cached, dict):
                    cached = SalesQueryResponse.model_validate(cached)
                cached.cached = True
                return cached
        
        # Build query parameters
        params = self._build_query_params(store_id, filters, sort, pagination)
        
        # Execute optimized query
        repo = SalesAnalyticsRepository(self._db, UUID(store_id))
        repo.apply_store_scope()
        (records, total_count), elapsed_ms, is_slow = repo.time_query(
            lambda: query_sales_list(self._db, params)
        )
        if is_slow:
            logger.warning(
                "Slow sales list query detected store=%s elapsed_ms=%s", store_id, elapsed_ms
            )
        
        # Transform records to response format
        data = [self._create_sale_record_response(r) for r in records]
        
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
            self._cache.set(cache_key, response.model_dump(mode="json"), CACHE_TTL_SECONDS)
        
        return response
    
    def query_sales_cursor(
        self,
        store_id: str,
        filters: SalesFilterRequest,
        sort: SalesSortRequest,
        page_size: int = 20,
        cursor: Optional[Tuple[datetime, str]] = None,
    ) -> Tuple[List[SaleRecordResponse], Optional[Tuple[datetime, str]]]:
        """
        Cursor-based pagination for deep queries.
        
        O(1) performance for any page depth.
        Cursor format: (sale_date, id)
        """
        params = self._build_query_params(store_id, filters, sort, PaginationRequest(page=1, limit=page_size))
        
        # Parse cursor if provided
        cursor_tuple = None
        if cursor:
            cursor_date, cursor_id = cursor
            cursor_tuple = (cursor_date, UUID(cursor_id))
        
        # Execute cursor query
        records, next_cursor = query_sales_list_cursor(self._db, params, cursor_tuple)
        
        # Transform records
        data = [self._create_sale_record_response(r) for r in records]
        
        # Format next cursor
        next_cursor_str = None
        if next_cursor:
            next_cursor_str = (next_cursor[0], str(next_cursor[1]))
        
        return data, next_cursor_str
    
    def get_summary(
        self,
        store_id: str,
        filters: SalesFilterRequest,
        use_cache: bool = True,
    ) -> SalesSummaryResponse:
        """
        Get summary statistics for filtered sales data.
        
        Uses materialized views when available, falls back to direct queries.
        """
        # Check application cache
        cache_key = self._cache._make_key("summary", store_id, filters=filters.model_dump())
        
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                if isinstance(cached, dict):
                    return SalesSummaryResponse.model_validate(cached)
                return cached
        
        # Check database cache (pre-computed analytics)
        repo = SalesAnalyticsRepository(self._db, UUID(store_id))
        repo.apply_store_scope()
        db_cache = get_cached_analytics(self._db, UUID(store_id))
        
        if db_cache and not db_cache.is_stale:
            # Use pre-computed analytics
            response = self._build_summary_from_cache(db_cache)
        else:
            # Compute from scratch
            start_date, end_date = self._resolve_date_range(filters)
            
            summary, elapsed_ms, is_slow = repo.time_query(
                lambda: query_sales_summary(
                    self._db,
                    UUID(store_id),
                    start_date,
                    end_date,
                )
            )
            if is_slow:
                logger.warning(
                    "Slow summary query detected store=%s elapsed_ms=%s", store_id, elapsed_ms
                )
            
            category_breakdown = query_category_breakdown(
                self._db,
                UUID(store_id),
                start_date,
                end_date,
            )
            
            segment_breakdown = query_segment_breakdown(
                self._db,
                UUID(store_id),
                start_date,
                end_date,
            )
            
            response = self._build_summary_response(summary, category_breakdown, segment_breakdown)
        
        # Cache the response
        if use_cache:
            self._cache.set(cache_key, response.model_dump(mode="json"), CACHE_TTL_SUMMARY)
        
        return response
    
    def get_realtime_metrics(
        self,
        store_id: str,
    ) -> Dict[str, Any]:
        """
        Get real-time metrics for dashboard header.
        
        Returns today/week/month revenue and transaction counts.
        TTL: 30 seconds
        """
        cache_key = self._cache._make_key("realtime", store_id)
        
        cached = self._cache.get(cache_key)
        if cached:
            return cached
        
        repo = SalesAnalyticsRepository(self._db, UUID(store_id))
        repo.apply_store_scope()
        metrics = query_realtime_metrics(self._db, UUID(store_id))
        
        self._cache.set(cache_key, metrics, CACHE_TTL_REALTIME)
        
        return metrics
    
    def get_filter_options(self, store_id: str) -> FilterOptionsResponse:
        """
        Get available filter options for a store.
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
            func.min(SalesTransaction.price).label('min_price'),
            func.max(SalesTransaction.price).label('max_price'),
        ).filter(
            SalesTransaction.store_id == UUID(store_id),
            SalesTransaction.deleted_at.is_(None),
            SalesTransaction.is_active == True,
        ).first()
        
        price_range = {
            "min": float(price_result.min_price) if price_result and price_result.min_price else 0,
            "max": float(price_result.max_price) if price_result and price_result.max_price else 50000,
        }
        
        return FilterOptionsResponse(
            categories=categories,
            customer_segments=list(CustomerSegment),
            return_statuses=list(ReturnStatus),
            price_range=price_range,
        )
    
    def get_category_breakdown(
        self,
        store_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Get sales breakdown by category."""
        return query_category_breakdown(
            self._db,
            UUID(store_id),
            start_date,
            end_date,
        )
    
    def get_segment_breakdown(
        self,
        store_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Get sales breakdown by customer segment."""
        return query_segment_breakdown(
            self._db,
            UUID(store_id),
            start_date,
            end_date,
        )
    
    def get_top_products(
        self,
        store_id: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top-selling products by revenue."""
        return query_top_products(
            self._db,
            UUID(store_id),
            start_date,
            end_date,
            limit,
        )
    
    # ─── Ingestion Methods ──────────────────────────────────────────────────────
    
    def ingest_sales_batch(
        self,
        store_id: str,
        sales_data: List[Dict[str, Any]],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Enqueue a batch of sales data for ingestion.
        
        Returns batch info with count of queued items.
        """
        items = enqueue_sales_batch(
            self._db,
            UUID(store_id),
            sales_data,
            idempotency_key=idempotency_key,
        )
        
        return {
            "batch_id": str(items[0].batch_id) if items else None,
            "queued_count": len(items),
            "store_id": store_id,
        }
    
    def process_ingestion(
        self,
        batch_id: str,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Process a batch of queued sales data.
        
        Returns processing results.
        """
        rows_inserted, rows_failed = process_ingestion_batch(
            self._db,
            UUID(batch_id),
            batch_size,
        )
        
        return {
            "batch_id": batch_id,
            "rows_inserted": rows_inserted,
            "rows_failed": rows_failed,
            "success": rows_failed == 0,
        }
    
    # ─── Export Methods ─────────────────────────────────────────────────────────
    
    def export_sales_csv(
        self,
        store_id: str,
        filters: SalesFilterRequest,
    ) -> Tuple[str, int]:
        """Export filtered sales data to CSV format."""
        params = self._build_query_params(
            store_id,
            filters,
            SalesSortRequest(),
            PaginationRequest(page=1, limit=10000),  # Max 10k rows
        )
        
        records, _ = query_sales_list(self._db, params)
        
        if not records:
            return "", 0
        
        # Transform records for export
        export_data = [self._transform_record_for_export(r, "csv") for r in records]
        
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
        """Export filtered sales data to JSON format."""
        params = self._build_query_params(
            store_id,
            filters,
            SalesSortRequest(),
            PaginationRequest(page=1, limit=10000),
        )
        
        records, _ = query_sales_list(self._db, params)
        
        if not records:
            return "[]", 0
        
        export_data = [self._transform_record_for_export(r, "json") for r in records]
        
        return json.dumps(export_data, indent=2, default=str), len(records)
    
    # ─── Cache Management ───────────────────────────────────────────────────────
    
    def invalidate_cache(self, store_id: str) -> int:
        """
        Invalidate all cached data for a store.
        
        Invalidates both application cache and database cache.
        """
        # Invalidate application cache
        app_count = self._cache.invalidate_store(store_id)
        
        # Invalidate database cache
        invalidate_analytics_cache(self._db, UUID(store_id))
        
        return app_count
    
    def refresh_analytics(self, store_id: str) -> Dict[str, Any]:
        """
        Force refresh of analytics cache.
        
        Computes fresh analytics and stores in cache.
        """
        cache = compute_and_cache_analytics(self._db, UUID(store_id))
        
        return {
            "store_id": store_id,
            "computed_at": cache.computed_at.isoformat() if cache else None,
            "expires_at": cache.expires_at.isoformat() if cache else None,
        }
    
    # ─── Private Helper Methods ─────────────────────────────────────────────────
    
    def _build_query_params(
        self,
        store_id: str,
        filters: SalesFilterRequest,
        sort: SalesSortRequest,
        pagination: PaginationRequest,
    ) -> SalesQueryParams:
        """Build query parameters from request."""
        # Resolve date range
        start_date, end_date = self._resolve_date_range(filters)
        
        # Convert category strings to enums
        categories = None
        if filters.categories:
            categories = [SalesCategory(c.value) for c in filters.categories]
        
        # Convert segment strings to enums
        segments = None
        if filters.customer_segments:
            segments = [CustomerSegment(s.value) for s in filters.customer_segments]
        
        # Convert return status to enum
        return_status = None
        if filters.return_statuses and len(filters.return_statuses) > 0:
            return_status = ReturnStatus(filters.return_statuses[0].value)
        
        # Map sort field
        sort_field_mapping = {
            "productName": "product_name",
            "category": "category",
            "price": "price",
            "quantity": "quantity",
            "customerName": "customer_name",
            "saleDate": "sale_date",
            "profitMargin": "profit_margin",
            "returnStatus": "return_status",
        }
        sort_by = sort_field_mapping.get(sort.sort_by.value, "sale_date")
        
        return SalesQueryParams(
            store_id=UUID(store_id),
            start_date=start_date,
            end_date=end_date,
            categories=categories,
            segments=segments,
            price_min=Decimal(str(filters.price_min)) if filters.price_min else None,
            price_max=Decimal(str(filters.price_max)) if filters.price_max else None,
            return_status=return_status,
            search=filters.search,
            sort_by=sort_by,
            sort_order=sort.sort_order.value,
            page=pagination.page,
            page_size=pagination.limit,
        )
    
    def _resolve_date_range(self, filters: SalesFilterRequest) -> Tuple[datetime, datetime]:
        """Resolve date range from preset or custom dates."""
        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if filters.date_range_preset == DateRangePreset.CUSTOM:
            start = datetime.combine(filters.custom_date_from or today, datetime.min.time()).replace(tzinfo=timezone.utc)
            end = datetime.combine(filters.custom_date_to or today, datetime.max.time()).replace(tzinfo=timezone.utc)
            return start, end
        
        preset_mapping = {
            DateRangePreset.TODAY: (today, today + timedelta(days=1)),
            DateRangePreset.THIS_WEEK: (today - timedelta(days=today.weekday()), today + timedelta(days=1)),
            DateRangePreset.THIS_MONTH: (today.replace(day=1), today + timedelta(days=1)),
        }
        
        return preset_mapping.get(filters.date_range_preset, (today.replace(day=1), today + timedelta(days=1)))
    
    def _create_sale_record_response(self, record: SalesTransaction) -> SaleRecordResponse:
        """Create SaleRecordResponse from SalesTransaction."""
        # Check if sale is recent (within 24 hours)
        is_recent = False
        if record.sale_date:
            now = datetime.now(timezone.utc)
            is_recent = (now - record.sale_date) < timedelta(hours=24)
        
        return SaleRecordResponse(
            id=str(record.id),
            product_name=record.product_name,
            thumbnail=None,  # Could be added via product join
            category=record.category,
            product_type=record.product_type,
            price=float(record.price) if record.price else 0,
            quantity=record.quantity,
            currency="EGP",  # Default currency
            customer_name=record.customer_name or "N/A",
            customer_email=None,
            customer_phone=None,
            customer_segment=record.customer_segment,
            sale_date=record.sale_date,
            profit_margin=float(record.profit_margin) if record.profit_margin else 0,
            return_status=record.return_status,
            sku=None,
            brand=None,
            store_name=None,
            store_address=None,
            payment_method=None,
            order_id=record.order_id,
            formatted_price=format_currency(float(record.price) if record.price else 0, "EGP"),
            formatted_date=format_date(record.sale_date),
            formatted_margin=format_percentage(float(record.profit_margin) if record.profit_margin else 0, 1),
            is_recent=is_recent,
        )
    
    def _build_summary_from_cache(self, cache: StoreAnalyticsCache) -> SalesSummaryResponse:
        """Build summary response from cached analytics."""
        return SalesSummaryResponse(
            total_sales=cache.total_transactions,
            total_revenue=float(cache.total_revenue),
            total_quantity=cache.total_units_sold,
            avg_order_value=float(cache.avg_order_value),
            avg_profit_margin=float(cache.avg_profit_margin),
            return_rate=float(cache.return_rate),
            sales_by_category={item.get("category"): item.get("transaction_count", 0) for item in cache.category_breakdown},
            revenue_by_category={item.get("category"): item.get("revenue", 0) for item in cache.category_breakdown},
            sales_by_segment={item.get("segment"): item.get("transactions", 0) for item in cache.segment_breakdown},
        )
    
    def _build_summary_response(
        self,
        summary: Dict[str, Any],
        category_breakdown: List[Dict[str, Any]],
        segment_breakdown: List[Dict[str, Any]],
    ) -> SalesSummaryResponse:
        """Build summary response from computed data."""
        return SalesSummaryResponse(
            total_sales=summary.get("total_transactions", 0),
            total_revenue=summary.get("total_revenue", 0),
            total_quantity=summary.get("total_units", 0),
            avg_order_value=summary.get("avg_order_value", 0),
            avg_profit_margin=summary.get("avg_profit_margin", 0),
            return_rate=summary.get("return_rate", 0),
            sales_by_category={item.get("category"): item.get("transaction_count", 0) for item in category_breakdown},
            revenue_by_category={item.get("category"): item.get("total_revenue", 0) for item in category_breakdown},
            sales_by_segment={item.get("segment"): item.get("transaction_count", 0) for item in segment_breakdown},
        )
    
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
    
    def _transform_record_for_export(self, record: SalesTransaction, format: str) -> Dict[str, Any]:
        """Transform record for export."""
        return {
            "id": str(record.id),
            "product_name": record.product_name,
            "category": record.category.value if record.category else None,
            "product_type": record.product_type,
            "price": float(record.price) if record.price else None,
            "quantity": record.quantity,
            "total_amount": float(record.total_amount),
            "customer_name": record.customer_name,
            "customer_segment": record.customer_segment.value if record.customer_segment else None,
            "sale_date": record.sale_date.isoformat() if record.sale_date else None,
            "profit_margin": float(record.profit_margin) if record.profit_margin else None,
            "return_status": record.return_status.value if record.return_status else None,
            "order_id": record.order_id,
            "channel": record.channel,
            "region": record.region,
        }


# ─── Service Factory ───────────────────────────────────────────────────────────

def get_sales_analytics_service_v2(db: Session) -> SalesAnalyticsServiceV2:
    """Factory function for dependency injection."""
    return SalesAnalyticsServiceV2(db)
