"""CONFIT Backend — Input Validators."""

import re
import uuid
from typing import Optional


def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.lower()))


def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """Validate password strength.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if len(password) > 128:
        return False, "Password must be less than 128 characters"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    return True, None


def validate_phone(phone: str) -> bool:
    """Validate phone number format."""
    if not phone:
        return True  # Phone is optional
    
    # Allow various phone formats
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    return bool(re.match(r'^\d{7,15}$', cleaned))


def validate_uuid(value: str) -> bool:
    """Validate UUID format."""
    if not value:
        return False
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def sanitize_string(value: str, max_length: int = None) -> str:
    """Sanitize string input.
    
    - Strips leading/trailing whitespace
    - Normalizes internal whitespace
    - Optionally truncates to max_length
    """
    if not value:
        return ""
    
    # Strip and normalize whitespace
    sanitized = " ".join(value.split())
    
    # Truncate if needed
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def validate_hex_color(color: str) -> bool:
    """Validate hex color format."""
    if not color:
        return True  # Optional
    return bool(re.match(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', color))


def validate_url(url: str, allowed_schemes: list = None) -> bool:
    """Validate URL format."""
    if not url:
        return True  # Optional
    
    allowed_schemes = allowed_schemes or ['http', 'https']
    pattern = r'^(' + '|'.join(allowed_schemes) + r')://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url, re.IGNORECASE))


def validate_price(price: float) -> bool:
    """Validate price value."""
    if price is None:
        return True  # Optional
    return isinstance(price, (int, float)) and price >= 0 and price <= 999999.99


def validate_quantity(quantity: int) -> bool:
    """Validate quantity value."""
    if quantity is None:
        return False
    return isinstance(quantity, int) and 1 <= quantity <= 1000
