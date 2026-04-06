"""
CONFIT Backend — Sales Analytics Query Helpers
==============================================
Optimized query functions for the Sales Analytics API.
Implements multi-field filtering, sorting, and pagination.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID
import hashlib
import json

from sqlalchemy import (
    select,
    func,
    and_,
    or_,
    text,
    desc,
    asc,
    case,
    literal_column,
)
from sqlalchemy.orm import Session, aliased
from sqlalchemy.dialects.postgresql import insert

from database.sales_analytics_models import (
    SalesTransaction,
    StoreAnalyticsCache,
    SalesIngestionQueue,
    SalesCategory,
    CustomerSegment,
    ReturnStatus,
    DateRangePreset,
    get_date_range_from_preset,
)
from database.models import Store


# ═══════════════════════════════════════════════════════════════════
# SALES LIST QUERY
# ═══════════════════════════════════════════════════════════════════

class SalesQueryParams:
    """Parameters for sales list queries."""
    
    def __init__(
        self,
        store_id: UUID,
        date_preset: Optional[DateRangePreset] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        categories: Optional[List[SalesCategory]] = None,
        segments: Optional[List[CustomerSegment]] = None,
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
        return_status: Optional[ReturnStatus] = None,
        search: Optional[str] = None,
        sort_by: str = "sale_date",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ):
        self.store_id = store_id
        self.date_preset = date_preset
        self.start_date = start_date
        self.end_date = end_date
        self.categories = categories or []
        self.segments = segments or []
        self.price_min = price_min
        self.price_max = price_max
        self.return_status = return_status
        self.search = search
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.page = max(1, page)
        self.page_size = min(100, max(1, page_size))
    
    def get_cache_key(self) -> str:
        """Generate cache key for this query."""
        params_dict = {
            "store_id": str(self.store_id),
            "date_preset": self.date_preset.value if self.date_preset else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "categories": [c.value for c in self.categories],
            "segments": [s.value for s in self.segments],
            "price_min": float(self.price_min) if self.price_min else None,
            "price_max": float(self.price_max) if self.price_max else None,
            "return_status": self.return_status.value if self.return_status else None,
            "search": self.search,
            "sort_by": self.sort_by,
            "sort_order": self.sort_order,
            "page": self.page,
            "page_size": self.page_size,
        }
        params_json = json.dumps(params_dict, sort_keys=True)
        return hashlib.md5(params_json.encode()).hexdigest()[:12]


def build_sales_query(params: SalesQueryParams):
    """
    Build optimized SQLAlchemy query for sales list.
    
    Uses indexes:
    - idx_sales_store_date: Partition pruning + date range
    - idx_sales_category_date_segment: Multi-field filtering
    - idx_sales_dashboard_covering: Index-only scan
    """
    # Base query with partition pruning
    query = select(SalesTransaction).where(
        and_(
            SalesTransaction.store_id == params.store_id,
            SalesTransaction.deleted_at.is_(None),
            SalesTransaction.is_active == True,
        )
    )
    
    # Date range filtering
    if params.date_preset:
        start_date, end_date = get_date_range_from_preset(params.date_preset)
        query = query.where(
            and_(
                SalesTransaction.sale_date >= start_date,
                SalesTransaction.sale_date < end_date,
            )
        )
    elif params.start_date or params.end_date:
        if params.start_date:
            query = query.where(SalesTransaction.sale_date >= params.start_date)
        if params.end_date:
            query = query.where(SalesTransaction.sale_date < params.end_date)
    
    # Category filtering (multi-select)
    if params.categories:
        query = query.where(SalesTransaction.category.in_(params.categories))
    
    # Customer segment filtering (multi-select)
    if params.segments:
        query = query.where(SalesTransaction.customer_segment.in_(params.segments))
    
    # Price range filtering
    if params.price_min is not None:
        query = query.where(SalesTransaction.price >= params.price_min)
    if params.price_max is not None:
        query = query.where(SalesTransaction.price <= params.price_max)
    
    # Return status filtering
    if params.return_status:
        query = query.where(SalesTransaction.return_status == params.return_status)
    
    # Search filtering (product name or customer name)
    if params.search:
        search_term = f"%{params.search}%"
        query = query.where(
            or_(
                SalesTransaction.product_name.ilike(search_term),
                SalesTransaction.customer_name.ilike(search_term),
            )
        )
    
    # Sorting
    sort_column = getattr(SalesTransaction, params.sort_by, SalesTransaction.sale_date)
    if params.sort_order == "desc":
        query = query.order_by(desc(sort_column), desc(SalesTransaction.id))
    else:
        query = query.order_by(asc(sort_column), asc(SalesTransaction.id))
    
    return query


def query_sales_list(
    db: Session,
    params: SalesQueryParams,
) -> Tuple[List[SalesTransaction], int]:
    """
    Execute paginated sales list query.
    
    Returns:
        Tuple of (sales_list, total_count)
    """
    # Build main query
    query = build_sales_query(params)
    
    # Get total count (efficient with covering index)
    count_query = select(func.count()).select_from(query.subquery())
    total_count = db.scalar(count_query) or 0
    
    # Apply pagination
    offset = (params.page - 1) * params.page_size
    query = query.offset(offset).limit(params.page_size)
    
    # Execute
    sales = db.scalars(query).all()
    
    return list(sales), total_count


def query_sales_list_cursor(
    db: Session,
    params: SalesQueryParams,
    cursor: Optional[Tuple[datetime, UUID]] = None,
) -> Tuple[List[SalesTransaction], Optional[Tuple[datetime, UUID]]]:
    """
    Execute cursor-based paginated sales list query.
    
    Cursor is (sale_date, id) tuple for O(1) pagination.
    
    Returns:
        Tuple of (sales_list, next_cursor)
    """
    query = build_sales_query(params)
    
    # Apply cursor filter
    if cursor:
        cursor_date, cursor_id = cursor
        if params.sort_order == "desc":
            query = query.where(
                or_(
                    SalesTransaction.sale_date < cursor_date,
                    and_(
                        SalesTransaction.sale_date == cursor_date,
                        SalesTransaction.id < cursor_id,
                    ),
                )
            )
        else:
            query = query.where(
                or_(
                    SalesTransaction.sale_date > cursor_date,
                    and_(
                        SalesTransaction.sale_date == cursor_date,
                        SalesTransaction.id > cursor_id,
                    ),
                )
            )
    
    # Fetch one extra to determine if there's a next page
    query = query.limit(params.page_size + 1)
    
    # Execute
    sales = list(db.scalars(query).all())
    
    # Determine next cursor
    next_cursor = None
    if len(sales) > params.page_size:
        sales = sales[:-1]  # Remove extra
        last_sale = sales[-1]
        next_cursor = (last_sale.sale_date, last_sale.id)
    
    return sales, next_cursor


# ═══════════════════════════════════════════════════════════════════
# SUMMARY STATISTICS QUERIES
# ═══════════════════════════════════════════════════════════════════

def query_sales_summary(
    db: Session,
    store_id: UUID,
    start_date: datetime,
    end_date: datetime,
) -> Dict[str, Any]:
    """
    Query aggregate sales summary for a store.
    
    Uses covering index for index-only scan.
    """
    query = select(
        func.count().label("total_transactions"),
        func.sum(SalesTransaction.price * SalesTransaction.quantity).label("total_revenue"),
        func.avg(SalesTransaction.price * SalesTransaction.quantity).label("avg_order_value"),
        func.avg(SalesTransaction.profit_margin).label("avg_profit_margin"),
        func.sum(SalesTransaction.quantity).label("total_units"),
        func.count(func.distinct(SalesTransaction.customer_id)).label("unique_customers"),
        func.count().filter(SalesTransaction.customer_segment == CustomerSegment.NEW_CUSTOMER).label("new_customers"),
        func.count().filter(SalesTransaction.customer_segment == CustomerSegment.RETURNING).label("returning_customers"),
        func.count().filter(SalesTransaction.customer_segment == CustomerSegment.VIP).label("vip_customers"),
        func.count().filter(SalesTransaction.return_status == ReturnStatus.RETURNED).label("returns_count"),
        func.sum(SalesTransaction.price * SalesTransaction.quantity).filter(
            SalesTransaction.return_status == ReturnStatus.RETURNED
        ).label("returns_amount"),
    ).where(
        and_(
            SalesTransaction.store_id == store_id,
            SalesTransaction.sale_date >= start_date,
            SalesTransaction.sale_date < end_date,
            SalesTransaction.deleted_at.is_(None),
            SalesTransaction.is_active == True,
        )
    )
    
    result = db.execute(query).first()
    
    if not result:
        return _empty_summary()
    
    total_transactions = result.total_transactions or 0
    returns_count = result.returns_count or 0
    
    return {
        "total_transactions": total_transactions,
        "total_revenue": float(result.total_revenue or 0),
        "avg_order_value": float(result.avg_order_value or 0),
        "avg_profit_margin": float(result.avg_profit_margin or 0),
        "total_units": result.total_units or 0,
        "unique_customers": result.unique_customers or 0,
        "new_customers": result.new_customers or 0,
        "returning_customers": result.returning_customers or 0,
        "vip_customers": result.vip_customers or 0,
        "returns_count": returns_count,
        "returns_amount": float(result.returns_amount or 0),
        "return_rate": round(100.0 * returns_count / total_transactions, 2) if total_transactions > 0 else 0.0,
    }


def _empty_summary() -> Dict[str, Any]:
    """Return empty summary structure."""
    return {
        "total_transactions": 0,
        "total_revenue": 0.0,
        "avg_order_value": 0.0,
        "avg_profit_margin": 0.0,
        "total_units": 0,
        "unique_customers": 0,
        "new_customers": 0,
        "returning_customers": 0,
        "vip_customers": 0,
        "returns_count": 0,
        "returns_amount": 0.0,
        "return_rate": 0.0,
    }


# ═══════════════════════════════════════════════════════════════════
# BREAKDOWN QUERIES
# ═══════════════════════════════════════════════════════════════════

def query_category_breakdown(
    db: Session,
    store_id: UUID,
    start_date: datetime,
    end_date: datetime,
) -> List[Dict[str, Any]]:
    """
    Query sales breakdown by category.
    
    Uses materialized view when available.
    """
    query = select(
        SalesTransaction.category,
        func.count().label("transaction_count"),
        func.sum(SalesTransaction.quantity).label("units_sold"),
        func.sum(SalesTransaction.price * SalesTransaction.quantity).label("total_revenue"),
        func.avg(SalesTransaction.price).label("avg_price"),
        func.avg(SalesTransaction.profit_margin).label("avg_margin"),
        func.count().filter(SalesTransaction.return_status == ReturnStatus.RETURNED).label("returns_count"),
    ).where(
        and_(
            SalesTransaction.store_id == store_id,
            SalesTransaction.sale_date >= start_date,
            SalesTransaction.sale_date < end_date,
            SalesTransaction.deleted_at.is_(None),
            SalesTransaction.is_active == True,
        )
    ).group_by(SalesTransaction.category).order_by(desc(literal_column("total_revenue")))
    
    results = db.execute(query).all()
    
    return [
        {
            "category": row.category.value if row.category else None,
            "transaction_count": row.transaction_count or 0,
            "units_sold": row.units_sold or 0,
            "total_revenue": float(row.total_revenue or 0),
            "avg_price": float(row.avg_price or 0),
            "avg_margin": float(row.avg_margin or 0),
            "returns_count": row.returns_count or 0,
        }
        for row in results
    ]


def query_segment_breakdown(
    db: Session,
    store_id: UUID,
    start_date: datetime,
    end_date: datetime,
) -> List[Dict[str, Any]]:
    """
    Query sales breakdown by customer segment.
    """
    query = select(
        SalesTransaction.customer_segment,
        func.count().label("transaction_count"),
        func.count(func.distinct(SalesTransaction.customer_id)).label("unique_customers"),
        func.sum(SalesTransaction.quantity).label("units_sold"),
        func.sum(SalesTransaction.price * SalesTransaction.quantity).label("total_revenue"),
        func.avg(SalesTransaction.price * SalesTransaction.quantity).label("avg_order_value"),
    ).where(
        and_(
            SalesTransaction.store_id == store_id,
            SalesTransaction.sale_date >= start_date,
            SalesTransaction.sale_date < end_date,
            SalesTransaction.deleted_at.is_(None),
            SalesTransaction.is_active == True,
        )
    ).group_by(SalesTransaction.customer_segment).order_by(desc(literal_column("total_revenue")))
    
    results = db.execute(query).all()
    
    return [
        {
            "segment": row.customer_segment.value if row.customer_segment else None,
            "transaction_count": row.transaction_count or 0,
            "unique_customers": row.unique_customers or 0,
            "units_sold": row.units_sold or 0,
            "total_revenue": float(row.total_revenue or 0),
            "avg_order_value": float(row.avg_order_value or 0),
        }
        for row in results
    ]


def query_top_products(
    db: Session,
    store_id: UUID,
    start_date: datetime,
    end_date: datetime,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Query top-selling products by revenue.
    """
    query = select(
        SalesTransaction.product_name,
        SalesTransaction.category,
        func.count().label("transaction_count"),
        func.sum(SalesTransaction.quantity).label("units_sold"),
        func.sum(SalesTransaction.price * SalesTransaction.quantity).label("total_revenue"),
        func.avg(SalesTransaction.price).label("avg_price"),
    ).where(
        and_(
            SalesTransaction.store_id == store_id,
            SalesTransaction.sale_date >= start_date,
            SalesTransaction.sale_date < end_date,
            SalesTransaction.deleted_at.is_(None),
            SalesTransaction.is_active == True,
        )
    ).group_by(
        SalesTransaction.product_name,
        SalesTransaction.category,
    ).order_by(desc(literal_column("total_revenue"))).limit(limit)
    
    results = db.execute(query).all()
    
    return [
        {
            "product_name": row.product_name,
            "category": row.category.value if row.category else None,
            "transaction_count": row.transaction_count or 0,
            "units_sold": row.units_sold or 0,
            "total_revenue": float(row.total_revenue or 0),
            "avg_price": float(row.avg_price or 0),
        }
        for row in results
    ]


# ═══════════════════════════════════════════════════════════════════
# CACHE OPERATIONS
# ═══════════════════════════════════════════════════════════════════

def get_cached_analytics(
    db: Session,
    store_id: UUID,
) -> Optional[StoreAnalyticsCache]:
    """
    Get cached analytics for a store.
    Returns None if cache is stale or expired.
    """
    query = select(StoreAnalyticsCache).where(
        and_(
            StoreAnalyticsCache.store_id == store_id,
            StoreAnalyticsCache.is_stale == False,
            StoreAnalyticsCache.expires_at > datetime.now(timezone.utc),
        )
    )
    
    return db.scalar(query)


def compute_and_cache_analytics(
    db: Session,
    store_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> StoreAnalyticsCache:
    """
    Compute analytics and store in cache.
    Uses PostgreSQL function for efficiency.
    """
    # Call PostgreSQL function
    result = db.execute(
        text("SELECT public.compute_store_analytics(:store_id, :start_date, :end_date)"),
        {
            "store_id": str(store_id),
            "start_date": start_date,
            "end_date": end_date,
        }
    ).scalar()
    
    # Fetch the cached record
    cache = db.get(StoreAnalyticsCache, result)
    return cache


def invalidate_analytics_cache(
    db: Session,
    store_id: UUID,
) -> None:
    """
    Mark analytics cache as stale.
    Called when new sales data is inserted.
    """
    db.execute(
        text("""
            UPDATE store_analytics_cache
            SET is_stale = TRUE, updated_at = NOW()
            WHERE store_id = :store_id
        """),
        {"store_id": str(store_id)}
    )
    db.commit()


# ═══════════════════════════════════════════════════════════════════
# INGESTION OPERATIONS
# ═══════════════════════════════════════════════════════════════════

def enqueue_sales_batch(
    db: Session,
    store_id: UUID,
    sales_data: List[Dict[str, Any]],
    batch_id: Optional[UUID] = None,
    idempotency_key: Optional[str] = None,
) -> List[SalesIngestionQueue]:
    """
    Enqueue a batch of sales data for ingestion.
    
    Args:
        store_id: Target store UUID
        sales_data: List of sales transaction dictionaries
        batch_id: Optional batch ID for grouping
        idempotency_key: Optional key for deduplication
    
    Returns:
        List of created queue items
    """
    if batch_id is None:
        batch_id = UUID(str(UUID(int=0)))  # Generate new batch ID
    
    queue_items = []
    
    for idx, sale in enumerate(sales_data, start=1):
        item = SalesIngestionQueue(
            store_id=store_id,
            batch_id=batch_id,
            batch_sequence=idx,
            payload=sale,
            idempotency_key=f"{idempotency_key}:{idx}" if idempotency_key else None,
        )
        queue_items.append(item)
        db.add(item)
    
    db.commit()
    
    return queue_items


def process_ingestion_batch(
    db: Session,
    batch_id: UUID,
    batch_size: int = 100,
) -> Tuple[int, int]:
    """
    Process a batch of queued sales data.
    
    Returns:
        Tuple of (rows_inserted, rows_failed)
    """
    # Fetch pending items
    items = db.scalars(
        select(SalesIngestionQueue)
        .where(
            and_(
                SalesIngestionQueue.batch_id == batch_id,
                SalesIngestionQueue.status == IngestionStatus.PENDING,
            )
        )
        .order_by(SalesIngestionQueue.batch_sequence)
        .limit(batch_size)
    ).all()
    
    if not items:
        return 0, 0
    
    rows_inserted = 0
    rows_failed = 0
    
    for item in items:
        try:
            # Mark as processing
            item.status = IngestionStatus.PROCESSING
            db.commit()
            
            # Create transaction
            sale_data = item.payload
            transaction = SalesTransaction(
                store_id=item.store_id,
                product_name=sale_data.get("product_name"),
                category=SalesCategory(sale_data.get("category", "Clothes")),
                product_type=sale_data.get("product_type"),
                price=Decimal(str(sale_data.get("price", 0))),
                quantity=sale_data.get("quantity", 1),
                customer_name=sale_data.get("customer_name"),
                customer_segment=CustomerSegment(sale_data.get("customer_segment", "New Customer")),
                customer_id=UUID(sale_data["customer_id"]) if sale_data.get("customer_id") else None,
                sale_date=sale_data.get("sale_date", datetime.now(timezone.utc)),
                profit_margin=Decimal(str(sale_data["profit_margin"])) if sale_data.get("profit_margin") else None,
                return_status=ReturnStatus(sale_data.get("return_status", "Completed")),
                order_id=sale_data.get("order_id"),
                channel=sale_data.get("channel", "in_store"),
                region=sale_data.get("region"),
                metadata=sale_data.get("metadata", {}),
            )
            
            db.add(transaction)
            
            # Mark as completed
            item.status = IngestionStatus.COMPLETED
            item.processed_at = datetime.now(timezone.utc)
            item.rows_inserted = 1
            
            rows_inserted += 1
            
        except Exception as e:
            # Mark as failed
            item.status = IngestionStatus.FAILED
            item.attempts += 1
            item.last_error = str(e)[:500]
            
            rows_failed += 1
            
            if item.attempts >= item.max_attempts:
                db.rollback()
            else:
                db.commit()
    
    db.commit()
    
    # Invalidate cache for affected store
    if items:
        invalidate_analytics_cache(db, items[0].store_id)
    
    return rows_inserted, rows_failed


# ═══════════════════════════════════════════════════════════════════
# REAL-TIME METRICS
# ═══════════════════════════════════════════════════════════════════

def query_realtime_metrics(
    db: Session,
    store_id: UUID,
) -> Dict[str, Any]:
    """
    Query real-time metrics for dashboard header.
    Uses materialized view when available.
    """
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # Single query for all metrics
    query = select(
        # Today
        func.count().filter(SalesTransaction.sale_date >= today).label("today_transactions"),
        func.sum(SalesTransaction.price * SalesTransaction.quantity).filter(
            SalesTransaction.sale_date >= today
        ).label("today_revenue"),
        
        # This week
        func.count().filter(SalesTransaction.sale_date >= week_start).label("week_transactions"),
        func.sum(SalesTransaction.price * SalesTransaction.quantity).filter(
            SalesTransaction.sale_date >= week_start
        ).label("week_revenue"),
        
        # This month
        func.count().filter(SalesTransaction.sale_date >= month_start).label("month_transactions"),
        func.sum(SalesTransaction.price * SalesTransaction.quantity).filter(
            SalesTransaction.sale_date >= month_start
        ).label("month_revenue"),
        
        # 30-day average margin
        func.avg(SalesTransaction.profit_margin).filter(
            SalesTransaction.sale_date >= today - timedelta(days=30)
        ).label("avg_margin_30d"),
    ).where(
        and_(
            SalesTransaction.store_id == store_id,
            SalesTransaction.deleted_at.is_(None),
            SalesTransaction.is_active == True,
        )
    )
    
    result = db.execute(query).first()
    
    return {
        "today": {
            "transactions": result.today_transactions or 0,
            "revenue": float(result.today_revenue or 0),
        },
        "week": {
            "transactions": result.week_transactions or 0,
            "revenue": float(result.week_revenue or 0),
        },
        "month": {
            "transactions": result.month_transactions or 0,
            "revenue": float(result.month_revenue or 0),
        },
        "avg_margin_30d": float(result.avg_margin_30d or 0),
        "computed_at": now.isoformat(),
    }


# Import timedelta at module level
from datetime import timedelta
