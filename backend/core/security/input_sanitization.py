"""
CONFIT Backend - Input Sanitization
===================================
Comprehensive input validation and sanitization utilities.
"""

import re
import html
import unicodedata
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urlparse, urljoin


# ─────────────────────────────────────────────────────────────────────────────
# DANGEROUS PATTERNS
# ─────────────────────────────────────────────────────────────────────────────

# SQL Injection patterns
SQL_INJECTION_PATTERNS = [
    r"(?i)(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)\b)",
    r"(?i)(\b(UNION|JOIN|INNER|OUTER|LEFT|RIGHT)\b.*\b(SELECT|FROM)\b)",
    r"(?i)(--|#|/\*|\*/)",
    r"(?i)(\b(OR|AND)\b\s+\d+\s*=\s*\d+)",
    r"(?i)(\b(OR|AND)\b\s+'[^']*'\s*=\s*'[^']*')",
    r"(?i)(\b(EXEC|EXECUTE|EXECSP)\b)",
    r"(?i)(\b(XP_|SP_)\w+)",
    r"(?i)(CONCAT\s*\()",
    r"(?i)(CHAR\s*\(|NCHAR\s*\()",
    r"(?i)(\b(WAITFOR|DELAY)\b)",
    r"(?i)(\b(BENCHMARK|SLEEP)\s*\()",
    r"';",  # Common SQL termination
]

# XSS patterns
XSS_PATTERNS = [
    r"(?i)<\s*script[^>]*>.*?<\s*/\s*script\s*>",
    r"(?i)<\s*script[^>]*/?>",
    r"(?i)javascript\s*:",
    r"(?i)vbscript\s*:",
    r"(?i)on(load|error|click|mouse\w+|key\w+|focus|blur|change|submit|reset|select)\s*=",
    r"(?i)<\s*iframe[^>]*>.*?<\s*/\s*iframe\s*>",
    r"(?i)<\s*iframe[^>]*/?>",
    r"(?i)<\s*object[^>]*>.*?<\s*/\s*object\s*>",
    r"(?i)<\s*embed[^>]*/?>",
    r"(?i)<\s*form[^>]*>.*?<\s*/\s*form\s*>",
    r"(?i)expression\s*\(",
    r"(?i)@import\s+",
    r"(?i)url\s*\(",
    r"(?i)data\s*:",
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",
    r"\.\.\\",
    r"%2e%2e%2f",
    r"%2e%2e/",
    r"\.\.%2f",
    r"%2e%2e/",
    r"\.\./",
    r"\.\.%5c",
    r"%5c",
]

# Command injection patterns
COMMAND_INJECTION_PATTERNS = [
    r";\s*\w+",
    r"\|\s*\w+",
    r"&&\s*\w+",
    r"\|\|\s*\w+",
    r"\$\([^)]+\)",
    r"`[^`]+`",
    r">\s*\S+",
    r"<\s*\S+",
    r"(?i)\b(cat|ls|pwd|whoami|id|uname|wget|curl|nc|bash|sh|python|perl|ruby|php)\b",
]


# ─────────────────────────────────────────────────────────────────────────────
# SANITIZATION FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def sanitize_string(
    value: str,
    max_length: Optional[int] = None,
    allowed_chars: Optional[Set[str]] = None,
    strip_html: bool = True,
    escape_html: bool = True,
) -> str:
    """
    Sanitize a string value.
    
    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length
        allowed_chars: Set of allowed characters (None = all printable)
        strip_html: Remove HTML tags
        escape_html: Escape HTML special characters
        
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return ""
    
    # Normalize unicode
    value = unicodedata.normalize("NFKC", value)
    
    # Remove null bytes
    value = value.replace("\x00", "")
    
    # Strip HTML tags if requested
    if strip_html:
        value = re.sub(r"<[^>]+>", "", value)
    
    # Escape HTML if requested
    if escape_html:
        value = html.escape(value, quote=True)
    
    # Filter to allowed characters if specified
    if allowed_chars:
        value = "".join(c for c in value if c in allowed_chars)
    
    # Truncate to max length
    if max_length and len(value) > max_length:
        value = value[:max_length]
    
    return value.strip()


def sanitize_html(value: str, allowed_tags: Optional[List[str]] = None) -> str:
    """
    Sanitize HTML content, allowing only specified tags.
    
    Args:
        value: HTML content to sanitize
        allowed_tags: List of allowed HTML tags (default: none)
        
    Returns:
        Sanitized HTML with only allowed tags
    """
    if not isinstance(value, str):
        return ""
    
    # Default: strip all HTML
    if not allowed_tags:
        return html.escape(value, quote=True)
    
    # Remove all tags except allowed ones
    allowed_pattern = "|".join(allowed_tags)
    
    # Remove script and style content completely
    value = re.sub(r"(?i)<script[^>]*>.*?</script>", "", value, flags=re.DOTALL)
    value = re.sub(r"(?i)<style[^>]*>.*?</style>", "", value, flags=re.DOTALL)
    
    # Remove event handlers
    value = re.sub(r'(?i)\s+on\w+\s*=\s*["\'][^"\']*["\']', "", value)
    value = re.sub(r'(?i)\s+on\w+\s*=\s*[^\s>]+', "", value)
    
    # Remove javascript: URLs
    value = re.sub(r'(?i)javascript\s*:', "", value)
    
    # Keep only allowed tags
    def clean_tag(match):
        tag = match.group(1)
        if tag.lower() in [t.lower() for t in allowed_tags]:
            return match.group(0)
        return ""
    
    value = re.sub(r"<(/?(\w+)[^>]*)>", clean_tag, value)
    
    return value


def sanitize_url(
    url: str,
    allowed_schemes: Optional[List[str]] = None,
    allow_relative: bool = False,
) -> Optional[str]:
    """
    Sanitize and validate a URL.
    
    Args:
        url: URL to sanitize
        allowed_schemes: Allowed URL schemes (default: http, https)
        allow_relative: Allow relative URLs
        
    Returns:
        Sanitized URL or None if invalid
    """
    if not isinstance(url, str):
        return None
    
    url = url.strip()
    
    if not url:
        return None
    
    # Default allowed schemes
    if allowed_schemes is None:
        allowed_schemes = ["http", "https"]
    
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme:
            if parsed.scheme.lower() not in [s.lower() for s in allowed_schemes]:
                return None
        elif not allow_relative:
            return None
        
        # Check for javascript: and other dangerous schemes
        if parsed.scheme.lower() in ["javascript", "vbscript", "data"]:
            return None
        
        # Check for path traversal
        if ".." in parsed.path:
            return None
        
        # Reconstruct clean URL
        clean_url = parsed.geturl()
        
        return clean_url
        
    except Exception:
        return None


def sanitize_email(email: str) -> Optional[str]:
    """
    Sanitize and validate an email address.
    
    Args:
        email: Email address to sanitize
        
    Returns:
        Sanitized email or None if invalid
    """
    if not isinstance(email, str):
        return None
    
    email = email.strip().lower()
    
    # Basic email pattern
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    
    if not re.match(email_pattern, email):
        return None
    
    # Check for dangerous characters
    if any(c in email for c in ["<", ">", '"', "'", ";", "(", ")", "\\"]):
        return None
    
    # Limit length
    if len(email) > 254:
        return None
    
    return email


def sanitize_phone(phone: str) -> Optional[str]:
    """
    Sanitize a phone number.
    
    Args:
        phone: Phone number to sanitize
        
    Returns:
        Sanitized phone number (digits only) or None if invalid
    """
    if not isinstance(phone, str):
        return None
    
    # Remove all non-digit characters
    digits = re.sub(r"[^\d+]", "", phone)
    
    # Must have at least 10 digits
    if len(digits) < 10:
        return None
    
    # Limit length
    if len(digits) > 15:
        return None
    
    return digits


def sanitize_filename(filename: str, max_length: int = 255) -> Optional[str]:
    """
    Sanitize a filename for safe storage.
    
    Args:
        filename: Filename to sanitize
        max_length: Maximum filename length
        
    Returns:
        Sanitized filename or None if invalid
    """
    if not isinstance(filename, str):
        return None
    
    filename = filename.strip()
    
    if not filename:
        return None
    
    # Remove path separators
    filename = filename.replace("/", "_").replace("\\", "_")
    
    # Remove null bytes
    filename = filename.replace("\x00", "")
    
    # Remove dangerous characters
    dangerous_chars = '<>:"|?*\x00-\x1f'
    for char in dangerous_chars:
        filename = filename.replace(char, "_")
    
    # Remove leading dots (hidden files)
    filename = filename.lstrip(".")
    
    # Limit length
    if len(filename) > max_length:
        # Preserve extension
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        max_name = max_length - len(ext) - 1 if ext else max_length
        filename = f"{name[:max_name]}.{ext}" if ext else name[:max_name]
    
    return filename if filename else None


def sanitize_int(
    value: Any,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
    default: Optional[int] = None,
) -> Optional[int]:
    """
    Sanitize and validate an integer.
    
    Args:
        value: Value to sanitize
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        default: Default value if invalid
        
    Returns:
        Sanitized integer or default
    """
    try:
        result = int(value)
        
        if min_value is not None and result < min_value:
            return default if default is not None else min_value
        
        if max_value is not None and result > max_value:
            return default if default is not None else max_value
        
        return result
        
    except (ValueError, TypeError):
        return default


def sanitize_float(
    value: Any,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    default: Optional[float] = None,
) -> Optional[float]:
    """
    Sanitize and validate a float.
    
    Args:
        value: Value to sanitize
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        default: Default value if invalid
        
    Returns:
        Sanitized float or default
    """
    try:
        result = float(value)
        
        # Check for NaN or infinity
        if not (result == result):  # NaN check
            return default
        
        if min_value is not None and result < min_value:
            return default if default is not None else min_value
        
        if max_value is not None and result > max_value:
            return default if default is not None else max_value
        
        return result
        
    except (ValueError, TypeError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
# DETECTION FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def detect_sql_injection(value: str) -> bool:
    """Check if value contains SQL injection patterns."""
    if not isinstance(value, str):
        return False
    
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, value):
            return True
    
    return False


def detect_xss(value: str) -> bool:
    """Check if value contains XSS patterns."""
    if not isinstance(value, str):
        return False
    
    for pattern in XSS_PATTERNS:
        if re.search(pattern, value):
            return True
    
    return False


def detect_path_traversal(value: str) -> bool:
    """Check if value contains path traversal patterns."""
    if not isinstance(value, str):
        return False
    
    # Decode URL encoding
    decoded = value
    from urllib.parse import unquote
    try:
        decoded = unquote(value)
    except Exception:
        pass
    
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE) or re.search(pattern, decoded, re.IGNORECASE):
            return True
    
    return False


def detect_command_injection(value: str) -> bool:
    """Check if value contains command injection patterns."""
    if not isinstance(value, str):
        return False
    
    for pattern in COMMAND_INJECTION_PATTERNS:
        if re.search(pattern, value):
            return True
    
    return False


def is_malicious_input(value: str) -> Dict[str, bool]:
    """
    Check input for all malicious patterns.
    
    Returns:
        Dictionary of detection results
    """
    return {
        "sql_injection": detect_sql_injection(value),
        "xss": detect_xss(value),
        "path_traversal": detect_path_traversal(value),
        "command_injection": detect_command_injection(value),
    }


# ─────────────────────────────────────────────────────────────────────────────
# OBJECT SANITIZATION
# ─────────────────────────────────────────────────────────────────────────────

def sanitize_dict(
    data: Dict[str, Any],
    schema: Optional[Dict[str, Any]] = None,
    strip_unknown: bool = False,
) -> Dict[str, Any]:
    """
    Sanitize a dictionary based on schema.
    
    Args:
        data: Dictionary to sanitize
        schema: Schema defining field sanitization rules
        strip_unknown: Remove fields not in schema
        
    Returns:
        Sanitized dictionary
    """
    if not isinstance(data, dict):
        return {}
    
    result = {}
    
    for key, value in data.items():
        # Sanitize key
        clean_key = sanitize_string(key, max_length=100)
        
        if not clean_key:
            continue
        
        # Check schema
        if schema and clean_key in schema:
            field_schema = schema[clean_key]
            
            # Apply field-specific sanitization
            field_type = field_schema.get("type", "string")
            
            if field_type == "string":
                result[clean_key] = sanitize_string(
                    value,
                    max_length=field_schema.get("max_length"),
                    allowed_chars=field_schema.get("allowed_chars"),
                )
            elif field_type == "int":
                result[clean_key] = sanitize_int(
                    value,
                    min_value=field_schema.get("min"),
                    max_value=field_schema.get("max"),
                    default=field_schema.get("default"),
                )
            elif field_type == "float":
                result[clean_key] = sanitize_float(
                    value,
                    min_value=field_schema.get("min"),
                    max_value=field_schema.get("max"),
                    default=field_schema.get("default"),
                )
            elif field_type == "email":
                result[clean_key] = sanitize_email(value)
            elif field_type == "url":
                result[clean_key] = sanitize_url(
                    value,
                    allowed_schemes=field_schema.get("allowed_schemes"),
                    allow_relative=field_schema.get("allow_relative", False),
                )
            elif field_type == "html":
                result[clean_key] = sanitize_html(
                    value,
                    allowed_tags=field_schema.get("allowed_tags"),
                )
            elif field_type == "bool":
                result[clean_key] = bool(value) if isinstance(value, (bool, int)) else None
            elif field_type == "list":
                if isinstance(value, list):
                    result[clean_key] = [
                        sanitize_string(item) if isinstance(item, str) else item
                        for item in value
                    ]
            else:
                result[clean_key] = value
                
        elif not strip_unknown:
            # Keep unknown fields with basic sanitization
            if isinstance(value, str):
                result[clean_key] = sanitize_string(value)
            elif isinstance(value, dict):
                result[clean_key] = sanitize_dict(value)
            elif isinstance(value, list):
                result[clean_key] = [
                    sanitize_string(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                result[clean_key] = value
    
    return result


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION DECORATORS
# ─────────────────────────────────────────────────────────────────────────────

def validate_input(*fields: str):
    """
    Decorator to validate input fields for malicious content.
    
    Usage:
        @validate_input("email", "name")
        async def register(request: RegisterRequest):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get request object
            request = None
            for arg in args:
                if hasattr(arg, "__dict__"):
                    request = arg
                    break
            
            if request:
                for field in fields:
                    value = getattr(request, field, None)
                    if isinstance(value, str):
                        detections = is_malicious_input(value)
                        if any(detections.values()):
                            from fastapi import HTTPException, status
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Invalid input detected in field: {field}"
                            )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
