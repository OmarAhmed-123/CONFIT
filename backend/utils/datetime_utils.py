"""CONFIT Backend — DateTime Utilities."""

from datetime import datetime, timezone, timedelta
from typing import Optional


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def parse_iso_datetime(value: str) -> Optional[datetime]:
    """Parse ISO format datetime string."""
    if not value:
        return None
    
    try:
        # Handle various ISO formats
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        
        # Try with timezone
        if '+' in value or value.count('-') > 2:
            return datetime.fromisoformat(value)
        
        # Try without timezone (assume UTC)
        dt = datetime.fromisoformat(value)
        return dt.replace(tzinfo=timezone.utc)
    
    except (ValueError, TypeError):
        return None


def format_iso_datetime(dt: datetime, include_ms: bool = False) -> Optional[str]:
    """Format datetime to ISO string."""
    if not dt:
        return None
    
    # Ensure timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    if include_ms:
        return dt.isoformat()
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def days_ago(days: int) -> datetime:
    """Get datetime N days ago in UTC."""
    return utc_now() - timedelta(days=days)


def days_from_now(days: int) -> datetime:
    """Get datetime N days from now in UTC."""
    return utc_now() + timedelta(days=days)


def hours_ago(hours: int) -> datetime:
    """Get datetime N hours ago in UTC."""
    return utc_now() - timedelta(hours=hours)


def hours_from_now(hours: int) -> datetime:
    """Get datetime N hours from now in UTC."""
    return utc_now() + timedelta(hours=hours)


def is_expired(dt: datetime) -> bool:
    """Check if datetime is in the past."""
    if not dt:
        return False
    
    # Ensure both have timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt < utc_now()


def days_between(dt1: datetime, dt2: datetime = None) -> int:
    """Calculate days between two datetimes."""
    if dt2 is None:
        dt2 = utc_now()
    
    # Ensure timezones
    if dt1.tzinfo is None:
        dt1 = dt1.replace(tzinfo=timezone.utc)
    if dt2.tzinfo is None:
        dt2 = dt2.replace(tzinfo=timezone.utc)
    
    delta = dt2 - dt1
    return abs(delta.days)


def get_season(month: int = None) -> str:
    """Get current season based on month."""
    if month is None:
        month = utc_now().month
    
    if month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    elif month in [9, 10, 11]:
        return "fall"
    return "winter"


def get_quarter(month: int = None) -> int:
    """Get current quarter (1-4)."""
    if month is None:
        month = utc_now().month
    return (month - 1) // 3 + 1
