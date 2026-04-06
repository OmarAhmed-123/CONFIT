"""
CONFIT Backend — Sales Analytics Schemas
========================================
Pydantic schemas for sales analytics API request/response models.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict

from schemas.base import BaseSchema


# ─── Enums ─────────────────────────────────────────────────────────────────────

class SaleCategory(str, Enum):
    """Product category enum."""
    CLOTHES = "Clothes"
    SHOES = "Shoes"
    ACCESSORIES = "Accessories"
    FULL_OUTFIT = "Full Outfit"


class CustomerSegment(str, Enum):
    """Customer segment enum."""
    NEW_CUSTOMER = "New Customer"
    RETURNING = "Returning"
    VIP = "VIP"
    WHOLESALE = "Wholesale"


class ReturnStatus(str, Enum):
    """Return status enum."""
    COMPLETED = "Completed"
    RETURNED = "Returned"
    PENDING_RETURN = "Pending Return"


class DateRangePreset(str, Enum):
    """Date range preset options."""
    TODAY = "today"
    THIS_WEEK = "this_week"
    THIS_MONTH = "this_month"
    CUSTOM = "custom"


class SortDirection(str, Enum):
    """Sort direction enum."""
    ASC = "asc"
    DESC = "desc"


class SaleSortField(str, Enum):
    """Sortable fields for sales records."""
    PRODUCT_NAME = "productName"
    CATEGORY = "category"
    PRICE = "price"
    QUANTITY = "quantity"
    CUSTOMER_NAME = "customerName"
    SALE_DATE = "saleDate"
    PROFIT_MARGIN = "profitMargin"
    RETURN_STATUS = "returnStatus"


# ─── Request Schemas ───────────────────────────────────────────────────────────

class SalesFilterRequest(BaseModel):
    """Filter parameters for sales analytics queries."""
    
    # Category filter (multi-select)
    categories: Optional[List[SaleCategory]] = Field(
        default=None,
        description="Filter by product categories (multi-select)",
        examples=[["Clothes", "Shoes"]]
    )
    
    # Date range filter
    date_range_preset: Optional[DateRangePreset] = Field(
        default=DateRangePreset.THIS_MONTH,
        description="Predefined date range or 'custom' for custom dates"
    )
    custom_date_from: Optional[date] = Field(
        default=None,
        description="Start date for custom range (ISO format)"
    )
    custom_date_to: Optional[date] = Field(
        default=None,
        description="End date for custom range (ISO format)"
    )
    
    # Product type filter (cascade based on category)
    product_types: Optional[List[str]] = Field(
        default=None,
        description="Filter by product types (e.g., Tops, Sneakers)",
        examples=[["Tops", "Dresses"]]
    )
    
    # Price range filter
    price_min: Optional[float] = Field(
        default=None,
        ge=0,
        description="Minimum price filter"
    )
    price_max: Optional[float] = Field(
        default=None,
        ge=0,
        description="Maximum price filter"
    )
    
    # Customer segment filter (multi-select)
    customer_segments: Optional[List[CustomerSegment]] = Field(
        default=None,
        description="Filter by customer segments (multi-select)",
        examples=[["New Customer", "VIP"]]
    )
    
    # Return status filter
    return_statuses: Optional[List[ReturnStatus]] = Field(
        default=None,
        description="Filter by return status (multi-select)",
        examples=[["Completed", "Pending Return"]]
    )
    
    # Search query
    search: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Search in product name, customer name, or SKU"
    )

    @field_validator('custom_date_to')
    @classmethod
    def validate_date_range(cls, v, info):
        """Validate that custom_date_to is after custom_date_from."""
        if v and info.data.get('custom_date_from'):
            if v < info.data['custom_date_from']:
                raise ValueError('custom_date_to must be after custom_date_from')
        return v

    @field_validator('price_max')
    @classmethod
    def validate_price_range(cls, v, info):
        """Validate that price_max is greater than price_min."""
        if v is not None and info.data.get('price_min') is not None:
            if v < info.data['price_min']:
                raise ValueError('price_max must be greater than price_min')
        return v


class SalesSortRequest(BaseModel):
    """Sorting parameters for sales queries."""
    
    sort_by: SaleSortField = Field(
        default=SaleSortField.SALE_DATE,
        description="Field to sort by"
    )
    sort_order: SortDirection = Field(
        default=SortDirection.DESC,
        description="Sort direction (asc or desc)"
    )


class PaginationRequest(BaseModel):
    """Pagination parameters."""
    
    page: int = Field(
        default=1,
        ge=1,
        le=10000,
        description="Page number (1-indexed)"
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=500,
        description="Number of items per page"
    )


class SalesQueryRequest(BaseModel):
    """Complete query parameters for sales analytics."""
    
    filters: SalesFilterRequest = Field(default_factory=SalesFilterRequest)
    sort: SalesSortRequest = Field(default_factory=SalesSortRequest)
    pagination: PaginationRequest = Field(default_factory=PaginationRequest)
    
    # Store context (populated from auth)
    store_id: Optional[str] = Field(
        default=None,
        description="Store ID for data scoping (from auth context)"
    )


class ExportRequest(BaseModel):
    """Request for exporting sales data."""
    
    filters: SalesFilterRequest = Field(default_factory=SalesFilterRequest)
    format: str = Field(
        default="csv",
        pattern="^(csv|json)$",
        description="Export format (csv or json)"
    )
    
    # Store context (populated from auth)
    store_id: Optional[str] = Field(
        default=None,
        description="Store ID for data scoping"
    )


# ─── Response Schemas ──────────────────────────────────────────────────────────

class SaleRecordResponse(BaseSchema):
    """Individual sale record response."""
    
    id: str
    product_name: str
    thumbnail: Optional[str] = None
    category: SaleCategory
    product_type: Optional[str] = None
    price: float
    quantity: int
    currency: str = "EGP"
    
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_segment: CustomerSegment
    
    sale_date: datetime
    profit_margin: float  # 0-100 percentage
    return_status: ReturnStatus
    
    sku: Optional[str] = None
    brand: Optional[str] = None
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    payment_method: Optional[str] = None
    order_id: Optional[str] = None
    
    # Formatted fields for display
    formatted_price: Optional[str] = None
    formatted_date: Optional[str] = None
    formatted_margin: Optional[str] = None
    is_recent: bool = False  # Within last 24 hours


class PaginationMeta(BaseModel):
    """Pagination metadata for responses."""
    
    total_rows: int
    current_page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class SalesQueryResponse(BaseModel):
    """Response for sales analytics query."""
    
    success: bool = True
    data: List[SaleRecordResponse]
    pagination: PaginationMeta
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    sort_applied: Dict[str, str] = Field(default_factory=dict)
    cached: bool = False
    cache_expires_at: Optional[datetime] = None


class CategoryProductTypes(BaseModel):
    """Product types available for each category."""
    
    category: SaleCategory
    product_types: List[str]


class FilterOptionsResponse(BaseModel):
    """Response for available filter options."""
    
    categories: List[CategoryProductTypes]
    customer_segments: List[CustomerSegment]
    return_statuses: List[ReturnStatus]
    price_range: Dict[str, Optional[float]]  # {min, max}


class SalesSummaryResponse(BaseModel):
    """Summary statistics for filtered sales data."""
    
    total_sales: int
    total_revenue: float
    total_quantity: int
    avg_order_value: float
    avg_profit_margin: float
    return_rate: float  # Percentage of returned items
    
    # Breakdown by category
    sales_by_category: Dict[str, int]
    revenue_by_category: Dict[str, float]
    
    # Breakdown by customer segment
    sales_by_segment: Dict[str, int]
    
    # Period comparison
    previous_period_revenue: Optional[float] = None
    revenue_change_percent: Optional[float] = None


class ExportResponse(BaseModel):
    """Response for export request."""
    
    success: bool = True
    download_url: Optional[str] = None
    file_name: str
    format: str
    row_count: int
    generated_at: datetime


# ─── Error Schemas ─────────────────────────────────────────────────────────────

class SalesAnalyticsError(BaseModel):
    """Error response for sales analytics."""
    
    success: bool = False
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    
    # Valid retry actions
    retry_available: bool = False
    fallback_data: Optional[Dict[str, Any]] = None


# ─── WebSocket / Real-time Schemas ─────────────────────────────────────────────

class SalesUpdateEvent(BaseModel):
    """Real-time sales update event."""
    
    event_type: str = "sale_created"  # sale_created, sale_updated, return_processed
    store_id: str
    sale_record: Optional[SaleRecordResponse] = None
    summary_update: Optional[SalesSummaryResponse] = None
    timestamp: datetime


# ─── Helper for creating responses ─────────────────────────────────────────────

def create_sale_record_response(record: Any, locale: str = "en-US") -> SaleRecordResponse:
    """
    Create a SaleRecordResponse from a database record with formatted fields.
    
    Args:
        record: SalesRecord ORM instance
        locale: Locale for formatting (default en-US)
    
    Returns:
        SaleRecordResponse with formatted display fields
    """
    from services.sales_transforms import format_currency, format_date, format_percentage
    
    # Check if sale is recent (within 24 hours)
    from datetime import datetime, timezone, timedelta
    is_recent = False
    if record.sale_date:
        now = datetime.now(timezone.utc)
        is_recent = (now - record.sale_date) < timedelta(hours=24)
    
    return SaleRecordResponse(
        id=str(record.id),
        product_name=record.product_name,
        thumbnail=record.thumbnail_url,
        category=record.category,
        product_type=record.product_type,
        price=float(record.price),
        quantity=record.quantity,
        currency=record.currency,
        customer_name=record.customer_name,
        customer_email=record.customer_email,
        customer_phone=record.customer_phone,
        customer_segment=record.customer_segment,
        sale_date=record.sale_date,
        profit_margin=float(record.profit_margin),
        return_status=record.return_status,
        sku=record.sku,
        brand=record.brand_name,
        store_name=record.store_name,
        store_address=record.store_address,
        payment_method=record.payment_method,
        order_id=record.order_id,
        formatted_price=format_currency(float(record.price), record.currency, locale),
        formatted_date=format_date(record.sale_date, locale),
        formatted_margin=format_percentage(float(record.profit_margin), 1),
        is_recent=is_recent,
    )
