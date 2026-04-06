"""
CONFIT Backend — Sales Data Transformation Utilities
=====================================================
Reusable functions for formatting currency, dates, percentages, and other
data transformations for the Sales Analytics API.
"""

import locale
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from typing import Optional, Dict, Any, List, Union

# ─── Currency Formatting ───────────────────────────────────────────────────────

# Currency symbols and formatting patterns
CURRENCY_CONFIG: Dict[str, Dict[str, Any]] = {
    "EGP": {"symbol": "EGP", "position": "prefix", "decimals": 0, "thousands": ","},
    "USD": {"symbol": "$", "position": "prefix", "decimals": 2, "thousands": ","},
    "EUR": {"symbol": "€", "position": "suffix", "decimals": 2, "thousands": "."},
    "GBP": {"symbol": "£", "position": "prefix", "decimals": 2, "thousands": ","},
    "SAR": {"symbol": "ر.س", "position": "suffix", "decimals": 2, "thousands": ","},
    "AED": {"symbol": "د.إ", "position": "suffix", "decimals": 2, "thousands": ","},
}


def format_currency(
    value: Union[float, Decimal],
    currency: str = "EGP",
    locale_code: Optional[str] = None,
    include_symbol: bool = True,
) -> str:
    """
    Format a numeric value as a localized currency string.
    
    Args:
        value: The numeric value to format
        currency: ISO 4217 currency code (default: EGP for Egyptian Pound)
        locale_code: Optional locale override (e.g., 'en-US', 'ar-EG')
        include_symbol: Whether to include the currency symbol
    
    Returns:
        Formatted currency string (e.g., "EGP 1,250" or "$1,250.00")
    
    Examples:
        >>> format_currency(1250.0, "EGP")
        'EGP 1,250'
        >>> format_currency(1250.5, "USD")
        '$1,250.50'
        >>> format_currency(1250.0, "EUR")
        '1.250,00 €'
    """
    if value is None:
        return ""
    
    # Convert Decimal to float if needed
    if isinstance(value, Decimal):
        value = float(value)
    
    # Get currency configuration
    config = CURRENCY_CONFIG.get(currency, CURRENCY_CONFIG["EGP"])
    decimals = config["decimals"]
    thousands_sep = config["thousands"]
    
    # Format the number with appropriate decimals
    if decimals == 0:
        formatted_num = f"{int(round(value)):,}".replace(",", thousands_sep)
    else:
        formatted_num = f"{value:,.{decimals}f}".replace(",", thousands_sep)
    
    if not include_symbol:
        return formatted_num
    
    symbol = config["symbol"]
    position = config["position"]
    
    if position == "prefix":
        return f"{symbol} {formatted_num}"
    else:
        return f"{formatted_num} {symbol}"


def parse_currency(value: str, currency: str = "EGP") -> float:
    """
    Parse a formatted currency string back to a float.
    
    Args:
        value: Formatted currency string
        currency: Expected currency code
    
    Returns:
        Numeric value as float
    
    Examples:
        >>> parse_currency("EGP 1,250", "EGP")
        1250.0
        >>> parse_currency("$1,250.50", "USD")
        1250.5
    """
    if not value:
        return 0.0
    
    config = CURRENCY_CONFIG.get(currency, CURRENCY_CONFIG["EGP"])
    symbol = config["symbol"]
    
    # Remove currency symbol and whitespace
    cleaned = value.replace(symbol, "").strip()
    
    # Remove thousands separator and parse
    thousands_sep = config["thousands"]
    cleaned = cleaned.replace(thousands_sep, "")
    
    # Handle European decimal format
    if currency in ("EUR",) and "." in cleaned and "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


# ─── Date Formatting ───────────────────────────────────────────────────────────

# Date format patterns by locale
DATE_FORMATS: Dict[str, str] = {
    "en-US": "%b %d, %Y",      # Jan 15, 2024
    "en-GB": "%d %b %Y",       # 15 Jan 2024
    "ar-EG": "%d %b %Y",       # 15 يناير 2024 (Arabic months handled by locale)
    "default": "%b %d, %Y",    # Default format
}


def format_date(
    value: Union[datetime, date, str],
    locale_code: str = "en-US",
    format_type: str = "medium",
) -> str:
    """
    Format a date/datetime value as a localized string.
    
    Args:
        value: Date value (datetime, date, or ISO string)
        locale_code: Locale for formatting (e.g., 'en-US')
        format_type: Format type ('short', 'medium', 'long', 'full')
    
    Returns:
        Formatted date string (e.g., "Jan 15, 2024")
    
    Examples:
        >>> format_date("2024-01-15T10:30:00Z")
        'Jan 15, 2024'
        >>> format_date(date(2024, 1, 15), format_type="long")
        'January 15, 2024'
    """
    if value is None:
        return ""
    
    # Parse ISO string if needed
    if isinstance(value, str):
        try:
            # Handle ISO format with timezone
            if "T" in value:
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            else:
                value = date.fromisoformat(value)
        except ValueError:
            return value  # Return as-is if parsing fails
    
    # Convert date to datetime if needed
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, datetime.min.time())
    
    # Select format pattern based on type
    format_patterns = {
        "short": "%m/%d/%Y",      # 01/15/2024
        "medium": "%b %d, %Y",    # Jan 15, 2024
        "long": "%B %d, %Y",      # January 15, 2024
        "full": "%A, %B %d, %Y",  # Monday, January 15, 2024
    }
    
    pattern = format_patterns.get(format_type, format_patterns["medium"])
    
    try:
        return value.strftime(pattern)
    except (AttributeError, ValueError):
        return str(value)


def format_datetime(
    value: Union[datetime, str],
    locale_code: str = "en-US",
    include_time: bool = True,
    time_format: str = "12h",
) -> str:
    """
    Format a datetime value with optional time component.
    
    Args:
        value: Datetime value or ISO string
        locale_code: Locale for formatting
        include_time: Whether to include time
        time_format: '12h' or '24h'
    
    Returns:
        Formatted datetime string
    
    Examples:
        >>> format_datetime("2024-01-15T14:30:00Z")
        'Jan 15, 2024, 2:30 PM'
        >>> format_datetime("2024-01-15T14:30:00Z", time_format="24h")
        'Jan 15, 2024, 14:30'
    """
    if value is None:
        return ""
    
    # Parse ISO string if needed
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    
    # Format date part
    date_str = format_date(value, locale_code)
    
    if not include_time:
        return date_str
    
    # Format time part
    if time_format == "12h":
        time_str = value.strftime("%I:%M %p").lstrip("0")
    else:
        time_str = value.strftime("%H:%M")
    
    return f"{date_str}, {time_str}"


def get_date_range_preset(preset: str) -> Dict[str, datetime]:
    """
    Calculate start and end datetime for a date range preset.
    
    Args:
        preset: Preset name ('today', 'this_week', 'this_month', 'custom')
    
    Returns:
        Dict with 'start' and 'end' datetime objects (UTC)
    
    Examples:
        >>> get_date_range_preset("today")
        {'start': datetime(...), 'end': datetime(...)}
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    presets = {
        "today": {
            "start": today_start,
            "end": now,
        },
        "this_week": {
            "start": today_start - timedelta(days=now.weekday()),
            "end": now,
        },
        "this_month": {
            "start": today_start.replace(day=1),
            "end": now,
        },
        "last_7_days": {
            "start": today_start - timedelta(days=7),
            "end": now,
        },
        "last_30_days": {
            "start": today_start - timedelta(days=30),
            "end": now,
        },
        "last_90_days": {
            "start": today_start - timedelta(days=90),
            "end": now,
        },
    }
    
    return presets.get(preset, presets["this_month"])


# ─── Percentage Formatting ─────────────────────────────────────────────────────

def format_percentage(
    value: Union[float, Decimal],
    decimals: int = 1,
    include_symbol: bool = True,
) -> str:
    """
    Format a numeric value as a percentage string.
    
    Args:
        value: The numeric value (0-100 scale)
        decimals: Number of decimal places
        include_symbol: Whether to include % symbol
    
    Returns:
        Formatted percentage string (e.g., "45.5%")
    
    Examples:
        >>> format_percentage(45.5)
        '45.5%'
        >>> format_percentage(45.467, decimals=2)
        '45.47%'
        >>> format_percentage(100, include_symbol=False)
        '100'
    """
    if value is None:
        return ""
    
    if isinstance(value, Decimal):
        value = float(value)
    
    formatted = f"{value:.{decimals}f}%"
    
    if not include_symbol:
        return formatted.rstrip("%")
    
    return formatted


def format_ratio(
    numerator: Union[float, Decimal, int],
    denominator: Union[float, Decimal, int],
    decimals: int = 1,
) -> str:
    """
    Calculate and format a ratio as a percentage.
    
    Args:
        numerator: The numerator value
        denominator: The denominator value
        decimals: Number of decimal places
    
    Returns:
        Formatted percentage string
    
    Examples:
        >>> format_ratio(45, 100)
        '45.0%'
        >>> format_ratio(3, 4, decimals=2)
        '75.00%'
    """
    if denominator == 0:
        return "0%"
    
    percentage = (float(numerator) / float(denominator)) * 100
    return format_percentage(percentage, decimals)


# ─── Return Status Formatting ─────────────────────────────────────────────────

RETURN_STATUS_CONFIG: Dict[str, Dict[str, Any]] = {
    "Completed": {
        "label": "Completed",
        "color": "green",
        "icon": "check-circle",
        "description": "Sale completed successfully",
    },
    "Returned": {
        "label": "Returned",
        "color": "red",
        "icon": "rotate-ccw",
        "description": "Item has been returned",
    },
    "Pending Return": {
        "label": "Pending Return",
        "color": "amber",
        "icon": "clock",
        "description": "Return request pending",
    },
}


def format_return_status(status: str) -> Dict[str, Any]:
    """
    Get display configuration for a return status.
    
    Args:
        status: Return status string
    
    Returns:
        Dict with label, color, icon, and description
    
    Examples:
        >>> format_return_status("Completed")
        {'label': 'Completed', 'color': 'green', ...}
    """
    return RETURN_STATUS_CONFIG.get(status, {
        "label": status,
        "color": "gray",
        "icon": "help-circle",
        "description": "Unknown status",
    })


# ─── Category Formatting ───────────────────────────────────────────────────────

CATEGORY_CONFIG: Dict[str, Dict[str, Any]] = {
    "Clothes": {
        "label": "Clothes",
        "color": "purple",
        "icon": "shirt",
        "product_types": ["Tops", "Bottoms", "Dresses", "Blazers", "T-Shirts", "Jackets"],
    },
    "Shoes": {
        "label": "Shoes",
        "color": "blue",
        "icon": "footprints",
        "product_types": ["Formal", "Casual", "Sneakers", "Heels", "Boots"],
    },
    "Accessories": {
        "label": "Accessories",
        "color": "amber",
        "icon": "gem",
        "product_types": ["Jewelry", "Bags", "Watches", "Belts", "Scarves"],
    },
    "Full Outfit": {
        "label": "Full Outfit",
        "color": "accent",
        "icon": "sparkles",
        "product_types": ["Casual Set", "Formal Set", "Evening Set", "Bridal Set"],
    },
}


def format_category(category: str) -> Dict[str, Any]:
    """
    Get display configuration for a product category.
    
    Args:
        category: Category string
    
    Returns:
        Dict with label, color, icon, and product_types
    
    Examples:
        >>> format_category("Clothes")
        {'label': 'Clothes', 'color': 'purple', ...}
    """
    return CATEGORY_CONFIG.get(category, {
        "label": category,
        "color": "gray",
        "icon": "package",
        "product_types": [],
    })


def get_product_types_for_categories(categories: List[str]) -> List[str]:
    """
    Get all available product types for a list of categories.
    
    Args:
        categories: List of category names
    
    Returns:
        List of product types for those categories
    
    Examples:
        >>> get_product_types_for_categories(["Clothes", "Shoes"])
        ['Tops', 'Bottoms', 'Dresses', ...]
    """
    product_types = []
    for cat in categories:
        config = CATEGORY_CONFIG.get(cat, {})
        product_types.extend(config.get("product_types", []))
    return list(set(product_types))


# ─── Customer Segment Formatting ─────────────────────────────────────────────

CUSTOMER_SEGMENT_CONFIG: Dict[str, Dict[str, Any]] = {
    "New Customer": {
        "label": "New Customer",
        "color": "blue",
        "icon": "user-plus",
        "description": "First-time buyer",
    },
    "Returning": {
        "label": "Returning",
        "color": "green",
        "icon": "user-check",
        "description": "Repeat customer",
    },
    "VIP": {
        "label": "VIP",
        "color": "purple",
        "icon": "crown",
        "description": "High-value customer",
    },
    "Wholesale": {
        "label": "Wholesale",
        "color": "amber",
        "icon": "building-2",
        "description": "Bulk/wholesale buyer",
    },
}


def format_customer_segment(segment: str) -> Dict[str, Any]:
    """
    Get display configuration for a customer segment.
    
    Args:
        segment: Customer segment string
    
    Returns:
        Dict with label, color, icon, and description
    """
    return CUSTOMER_SEGMENT_CONFIG.get(segment, {
        "label": segment,
        "color": "gray",
        "icon": "user",
        "description": "Unknown segment",
    })


# ─── Profit Margin Color Coding ───────────────────────────────────────────────

def get_profit_margin_color(margin: float) -> str:
    """
    Get the color class for profit margin display.
    
    Args:
        margin: Profit margin percentage (0-100)
    
    Returns:
        Color class string ('green', 'amber', or 'red')
    
    Examples:
        >>> get_profit_margin_color(45)
        'green'
        >>> get_profit_margin_color(15)
        'red'
    """
    if margin >= 40:
        return "green"
    elif margin >= 20:
        return "amber"
    return "red"


def format_profit_margin_with_indicator(margin: float) -> Dict[str, Any]:
    """
    Format profit margin with color indicator.
    
    Args:
        margin: Profit margin percentage
    
    Returns:
        Dict with formatted value and color
    """
    return {
        "value": margin,
        "formatted": format_percentage(margin, 1),
        "color": get_profit_margin_color(margin),
        "indicator": "high" if margin >= 40 else "medium" if margin >= 20 else "low",
    }


# ─── Export Data Transformation ───────────────────────────────────────────────

def transform_record_for_export(record: Any, format_type: str = "csv") -> Dict[str, Any]:
    """
    Transform a sales record for export (CSV/JSON).
    
    Args:
        record: SalesRecord ORM instance
        format_type: Export format ('csv' or 'json')
    
    Returns:
        Dict suitable for export
    """
    return {
        "Sale ID": str(record.id),
        "Product Name": record.product_name,
        "SKU": record.sku or "",
        "Category": record.category.value if hasattr(record.category, 'value') else str(record.category),
        "Product Type": record.product_type or "",
        "Price": float(record.price),
        "Currency": record.currency,
        "Quantity": record.quantity,
        "Total": float(record.price) * record.quantity,
        "Customer Name": record.customer_name,
        "Customer Email": record.customer_email or "",
        "Customer Segment": record.customer_segment.value if hasattr(record.customer_segment, 'value') else str(record.customer_segment),
        "Sale Date": format_date(record.sale_date),
        "Sale Time": record.sale_date.strftime("%H:%M") if record.sale_date else "",
        "Profit Margin (%)": float(record.profit_margin),
        "Return Status": record.return_status.value if hasattr(record.return_status, 'value') else str(record.return_status),
        "Brand": record.brand_name or "",
        "Store Name": record.store_name or "",
        "Store Address": record.store_address or "",
        "Payment Method": record.payment_method or "",
        "Delivery Method": record.delivery_method or "",
        "Order ID": record.order_id or "",
    }


# ─── Summary Statistics Formatting ─────────────────────────────────────────────

def format_summary_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format summary statistics with display-friendly values.
    
    Args:
        stats: Raw statistics dict
    
    Returns:
        Dict with formatted values
    """
    return {
        "total_sales": stats.get("total_sales", 0),
        "total_revenue": stats.get("total_revenue", 0),
        "total_revenue_formatted": format_currency(stats.get("total_revenue", 0)),
        "total_quantity": stats.get("total_quantity", 0),
        "avg_order_value": stats.get("avg_order_value", 0),
        "avg_order_value_formatted": format_currency(stats.get("avg_order_value", 0)),
        "avg_profit_margin": stats.get("avg_profit_margin", 0),
        "avg_profit_margin_formatted": format_percentage(stats.get("avg_profit_margin", 0)),
        "return_rate": stats.get("return_rate", 0),
        "return_rate_formatted": format_percentage(stats.get("return_rate", 0)),
        "sales_by_category": stats.get("sales_by_category", {}),
        "revenue_by_category": {
            k: format_currency(v) for k, v in stats.get("revenue_by_category", {}).items()
        },
        "sales_by_segment": stats.get("sales_by_segment", {}),
    }
