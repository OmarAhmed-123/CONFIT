"""
CONFIT Backend - Application Constants
=======================================
Centralized constants for the entire application.
"""

from enum import Enum
from typing import List, Dict, Any


# =============================================================================
# Application Metadata
# =============================================================================

APP_NAME = "CONFIT"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "AI-Powered Fashion Platform with CONFIT CARE"


# =============================================================================
# User Roles & Permissions
# =============================================================================

class UserRole(str, Enum):
    """User roles for RBAC."""
    USER = "user"
    DONOR = "donor"
    BRAND_PARTNER = "brand_partner"
    STYLIST = "stylist"
    ADMIN = "admin"


class Permission(str, Enum):
    """Granular permissions for RBAC."""
    # User permissions
    VIEW_OWN_PROFILE = "view_own_profile"
    EDIT_OWN_PROFILE = "edit_own_profile"
    MANAGE_WARDROBE = "manage_wardrobe"
    CREATE_OUTFITS = "create_outfits"
    PLACE_ORDERS = "place_orders"
    
    # Donor permissions
    CREATE_CAMPAIGN = "create_campaign"
    MANAGE_CAMPAIGN = "manage_campaign"
    VIEW_CAMPAIGN_ANALYTICS = "view_campaign_analytics"
    MANAGE_BENEFICIARIES = "manage_beneficiaries"
    
    # Brand partner permissions
    MANAGE_PRODUCTS = "manage_products"
    VIEW_BRAND_ANALYTICS = "view_brand_analytics"
    MANAGE_INVENTORY = "manage_inventory"
    
    # Admin permissions
    MANAGE_USERS = "manage_users"
    MANAGE_BRANDS = "manage_brands"
    VIEW_SYSTEM_ANALYTICS = "view_system_analytics"
    MANAGE_CAMPAIGNS = "manage_campaigns"
    AUDIT_ACCESS = "audit_access"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.USER: [
        Permission.VIEW_OWN_PROFILE,
        Permission.EDIT_OWN_PROFILE,
        Permission.MANAGE_WARDROBE,
        Permission.CREATE_OUTFITS,
        Permission.PLACE_ORDERS,
    ],
    UserRole.DONOR: [
        Permission.VIEW_OWN_PROFILE,
        Permission.EDIT_OWN_PROFILE,
        Permission.CREATE_CAMPAIGN,
        Permission.MANAGE_CAMPAIGN,
        Permission.VIEW_CAMPAIGN_ANALYTICS,
        Permission.MANAGE_BENEFICIARIES,
    ],
    UserRole.BRAND_PARTNER: [
        Permission.VIEW_OWN_PROFILE,
        Permission.EDIT_OWN_PROFILE,
        Permission.MANAGE_PRODUCTS,
        Permission.VIEW_BRAND_ANALYTICS,
        Permission.MANAGE_INVENTORY,
    ],
    UserRole.STYLIST: [
        Permission.VIEW_OWN_PROFILE,
        Permission.EDIT_OWN_PROFILE,
        Permission.CREATE_OUTFITS,
    ],
    UserRole.ADMIN: list(Permission),  # Admins have all permissions
}


# =============================================================================
# Order Status
# =============================================================================

class OrderStatus(str, Enum):
    """Order status lifecycle."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    RETURN_REQUESTED = "return_requested"
    RETURN_APPROVED = "return_approved"
    RETURNED = "returned"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


ORDER_STATUS_TRANSITIONS: Dict[OrderStatus, List[OrderStatus]] = {
    OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
    OrderStatus.CONFIRMED: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
    OrderStatus.PROCESSING: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
    OrderStatus.SHIPPED: [OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED],
    OrderStatus.OUT_FOR_DELIVERY: [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [OrderStatus.RETURN_REQUESTED],
    OrderStatus.RETURN_REQUESTED: [OrderStatus.RETURN_APPROVED, OrderStatus.DELIVERED],
    OrderStatus.RETURN_APPROVED: [OrderStatus.RETURNED, OrderStatus.REFUNDED],
    OrderStatus.RETURNED: [OrderStatus.REFUNDED],
    OrderStatus.CANCELLED: [OrderStatus.REFUNDED],
    OrderStatus.REFUNDED: [],  # Terminal state
}


# =============================================================================
# Payment Status
# =============================================================================

class PaymentStatus(str, Enum):
    """Payment status."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    """Supported payment methods."""
    CARD = "card"
    CASH_ON_DELIVERY = "cod"
    BNPL = "bnpl"  # Buy Now Pay Later
    WALLET = "wallet"
    CARE_VOUCHER = "care_voucher"


class BNPLProvider(str, Enum):
    """BNPL providers."""
    TELR = "telr"
    FAWRY = "fawry"
    PAYMOB = "paymob"
    VALU = "valu"
    SYMPLE = "symple"


# =============================================================================
# CONFIT CARE Constants
# =============================================================================

class CampaignType(str, Enum):
    """Types of donation campaigns."""
    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"
    SEASONAL = "seasonal"
    CORPORATE = "corporate"
    EMERGENCY = "emergency"


class VoucherType(str, Enum):
    """Types of care vouchers."""
    STANDARD = "standard"
    OCCASION_SPECIFIC = "occasion_specific"
    ESSENTIALS_ONLY = "essentials_only"
    FULL_OUTFIT = "full_outfit"


class BeneficiaryStatus(str, Enum):
    """Beneficiary status."""
    PENDING = "pending"
    INVITED = "invited"
    ACTIVE = "active"
    SHOPPING = "shopping"
    COMPLETED = "completed"
    EXPIRED = "expired"


# Budget limits for CARE (in EGP)
CARE_MIN_BUDGET_PER_PERSON = 500.0
CARE_MAX_BUDGET_PER_PERSON = 5000.0
CARE_DEFAULT_BUDGET_PER_PERSON = 1500.0

# Voucher settings
VOUCHER_CODE_LENGTH = 12
VOUCHER_CODE_PREFIX = "CARE"
VOUCHER_DEFAULT_EXPIRY_DAYS = 30

# OTP settings
OTP_LENGTH = 6
OTP_MAX_ATTEMPTS = 3
OTP_EXPIRY_MINUTES = 10

# Session settings
CARE_SESSION_EXPIRY_HOURS = 24
CARE_MAX_SESSION_DURATION_HOURS = 48


# =============================================================================
# Product & Category Constants
# =============================================================================

class ProductCategory(str, Enum):
    """Product categories."""
    TOPS = "tops"
    BOTTOMS = "bottoms"
    DRESSES = "dresses"
    OUTERWEAR = "outerwear"
    FOOTWEAR = "footwear"
    ACCESSORIES = "accessories"
    BAGS = "bags"
    JEWELRY = "jewelry"
    ACTIVEWEAR = "activewear"
    SWIMWEAR = "swimwear"
    UNDERGARMENTS = "undergarments"
    SLEEPWEAR = "sleepwear"


class ProductStatus(str, Enum):
    """Product status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"
    COMING_SOON = "coming_soon"


class SizeCategory(str, Enum):
    """Size categories."""
    XS = "XS"
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"
    XXL = "XXL"
    XXXL = "XXXL"
    ONE_SIZE = "ONE_SIZE"


# Standard size charts
SIZE_CHARTS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "tops": {
        "XS": {"chest": "81-86", "waist": "66-71"},
        "S": {"chest": "86-91", "waist": "71-76"},
        "M": {"chest": "91-96", "waist": "76-81"},
        "L": {"chest": "96-101", "waist": "81-86"},
        "XL": {"chest": "101-106", "waist": "86-91"},
        "XXL": {"chest": "106-111", "waist": "91-96"},
    },
    "bottoms": {
        "XS": {"waist": "66-71", "hip": "81-86"},
        "S": {"waist": "71-76", "hip": "86-91"},
        "M": {"waist": "76-81", "hip": "91-96"},
        "L": {"waist": "81-86", "hip": "96-101"},
        "XL": {"waist": "86-91", "hip": "101-106"},
        "XXL": {"waist": "91-96", "hip": "106-111"},
    },
}


# =============================================================================
# Style & Fashion Constants
# =============================================================================

class StylePersonality(str, Enum):
    """Style personality types."""
    CLASSIC = "classic"
    TRENDY = "trendy"
    MINIMALIST = "minimalist"
    BOHEMIAN = "bohemian"
    EDGY = "edgy"
    ROMANTIC = "romantic"
    SPORTY = "sporty"
    PROFESSIONAL = "professional"
    ECLECTIC = "eclectic"


class Occasion(str, Enum):
    """Occasion types for outfit recommendations."""
    WORK = "work"
    CASUAL = "casual"
    FORMAL = "formal"
    PARTY = "party"
    DATE_NIGHT = "date_night"
    WEDDING = "wedding"
    VACATION = "vacation"
    WORKOUT = "workout"
    WEEKEND = "weekend"
    BUSINESS_CASUAL = "business_causal"
    COCKTAIL = "cocktail"
    OUTDOOR = "outdoor"


class ColorFamily(str, Enum):
    """Color families for styling."""
    NEUTRALS = "neutrals"  # Black, white, gray, beige
    EARTH_TONES = "earth_tones"  # Brown, tan, olive
    PASTELS = "pastels"  # Light pinks, blues, lavenders
    JEWEL_TONES = "jewel_tones"  # Emerald, ruby, sapphire
    BRIGHTS = "brights"  # Bold, saturated colors
    MONOCHROMATIC = "monochromatic"  # Single color variations


# Color harmony rules
COLOR_HARMONY_RULES = {
    "complementary": ["red-green", "blue-orange", "yellow-purple"],
    "analogous": ["red-orange-yellow", "blue-green-teal"],
    "triadic": ["red-yellow-blue", "green-orange-purple"],
    "monochromatic": "single_color_variations",
}


# =============================================================================
# Body Profile Constants
# =============================================================================

class BodyType(str, Enum):
    """Body type classifications."""
    HOURGLASS = "hourglass"
    PEAR = "pear"
    APPLE = "apple"
    RECTANGLE = "rectangle"
    INVERTED_TRIANGLE = "inverted_triangle"


class SkinTone(str, Enum):
    """Skin tone categories."""
    FAIR = "fair"
    LIGHT = "light"
    MEDIUM = "medium"
    OLIVE = "olive"
    TAN = "tan"
    DARK = "dark"


class SkinUndertone(str, Enum):
    """Skin undertone categories."""
    WARM = "warm"
    COOL = "cool"
    NEUTRAL = "neutral"


# =============================================================================
# Delivery & Shipping Constants
# =============================================================================

class DeliveryMethod(str, Enum):
    """Delivery methods."""
    STANDARD_SHIPPING = "standard_shipping"
    EXPRESS_SHIPPING = "express_shipping"
    SAME_DAY = "same_day"
    BOPIS = "bopis"  # Buy Online, Pick Up In Store


class DeliveryStatus(str, Enum):
    """Delivery tracking status."""
    PROCESSING = "processing"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED_DELIVERY = "failed_delivery"
    RETURNED_TO_SENDER = "returned_to_sender"


# Shipping costs (in EGP)
SHIPPING_COSTS = {
    DeliveryMethod.STANDARD_SHIPPING: 50.0,
    DeliveryMethod.EXPRESS_SHIPPING: 100.0,
    DeliveryMethod.SAME_DAY: 150.0,
    DeliveryMethod.BOPIS: 0.0,
}

FREE_SHIPPING_THRESHOLD = 500.0  # Free shipping for orders above this amount


# =============================================================================
# Notification Constants
# =============================================================================

class NotificationType(str, Enum):
    """Notification types."""
    ORDER_CONFIRMATION = "order_confirmation"
    ORDER_SHIPPED = "order_shipped"
    ORDER_DELIVERED = "order_delivered"
    ORDER_CANCELLED = "order_cancelled"
    RETURN_PROCESSED = "return_processed"
    
    # CARE notifications
    CARE_INVITATION = "care_invitation"
    CARE_VOUCHER_ISSUED = "care_voucher_issued"
    CARE_ORDER_CONFIRMED = "care_order_confirmed"
    CARE_CAMPAIGN_UPDATE = "care_campaign_update"
    
    # Style notifications
    STYLE_RECOMMENDATION = "style_recommendation"
    NEW_ARRIVAL = "new_arrival"
    PRICE_DROP = "price_drop"
    BACK_IN_STOCK = "back_in_stock"
    
    # Social notifications
    NEW_FOLLOWER = "new_follower"
    OUTFIT_LIKED = "outfit_liked"
    OUTFIT_COMMENTED = "outfit_commented"
    
    # System notifications
    SYSTEM_UPDATE = "system_update"
    SECURITY_ALERT = "security_alert"
    MARKETING = "marketing"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


# =============================================================================
# Analytics Constants
# =============================================================================

class MetricType(str, Enum):
    """Analytics metric types."""
    PAGE_VIEW = "page_view"
    PRODUCT_VIEW = "product_view"
    OUTFIT_VIEW = "outfit_view"
    ADD_TO_CART = "add_to_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    CHECKOUT_STARTED = "checkout_started"
    PURCHASE = "purchase"
    TRY_ON = "try_on"
    OUTFIT_CREATED = "outfit_created"
    WARDROBE_ITEM_ADDED = "wardrobe_item_added"
    SEARCH = "search"
    FILTER_APPLIED = "filter_applied"
    SHARE = "share"
    SAVE = "save"


class TimeGranularity(str, Enum):
    """Time granularity for analytics."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


# =============================================================================
# Error Codes
# =============================================================================

class ErrorCode(str, Enum):
    """Application error codes."""
    # Authentication errors
    INVALID_CREDENTIALS = "AUTH_001"
    TOKEN_EXPIRED = "AUTH_002"
    TOKEN_INVALID = "AUTH_003"
    OAUTH_FAILED = "AUTH_004"
    SESSION_EXPIRED = "AUTH_005"
    
    # User errors
    USER_NOT_FOUND = "USER_001"
    USER_ALREADY_EXISTS = "USER_002"
    INVALID_EMAIL = "USER_003"
    INVALID_PHONE = "USER_004"
    
    # Product errors
    PRODUCT_NOT_FOUND = "PROD_001"
    PRODUCT_OUT_OF_STOCK = "PROD_002"
    INVALID_SKU = "PROD_003"
    
    # Order errors
    ORDER_NOT_FOUND = "ORD_001"
    ORDER_CANNOT_CANCEL = "ORD_002"
    ORDER_ALREADY_PROCESSED = "ORD_003"
    INVALID_ORDER_STATUS = "ORD_004"
    
    # Payment errors
    PAYMENT_FAILED = "PAY_001"
    PAYMENT_DECLINED = "PAY_002"
    INSUFFICIENT_FUNDS = "PAY_003"
    PAYMENT_TIMEOUT = "PAY_004"
    
    # CARE errors
    CAMPAIGN_NOT_FOUND = "CARE_001"
    VOUCHER_INVALID = "CARE_002"
    VOUCHER_EXPIRED = "CARE_003"
    VOUCHER_ALREADY_USED = "CARE_004"
    BUDGET_EXCEEDED = "CARE_005"
    BENEFICIARY_NOT_FOUND = "CARE_006"
    OTP_INVALID = "CARE_007"
    OTP_EXPIRED = "CARE_008"
    SESSION_INVALID = "CARE_009"
    
    # System errors
    INTERNAL_ERROR = "SYS_001"
    SERVICE_UNAVAILABLE = "SYS_002"
    RATE_LIMIT_EXCEEDED = "SYS_003"
    INVALID_REQUEST = "SYS_004"


# =============================================================================
# Rate Limiting Constants
# =============================================================================

RATE_LIMITS = {
    "default": "60/minute",
    "default_authenticated": "120/minute",
    "default_anonymous": "30/minute",
    "auth": "5/minute",
    "try_on": "10/minute",
    "styling": "20/minute",
    "checkout": "5/minute",
    "payment": "10/minute",
    "webhook": "600/minute",
    "care_otp": "3/hour",
    "care_session": "10/hour",
}


# =============================================================================
# Currency & Locale Constants
# =============================================================================

SUPPORTED_CURRENCIES = ["EGP", "USD", "EUR", "SAR", "AED"]
DEFAULT_CURRENCY = "EGP"

CURRENCY_SYMBOLS = {
    "EGP": "E£",
    "USD": "$",
    "EUR": "",
    "SAR": "SR",
    "AED": "Dh",
}

SUPPORTED_LANGUAGES = ["en", "ar"]
DEFAULT_LANGUAGE = "en"


# =============================================================================
# Image & Media Constants
# =============================================================================

MAX_IMAGE_SIZE_MB = 10
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"]
MAX_IMAGE_DIMENSION = 4096
THUMBNAIL_SIZE = (300, 300)
PRODUCT_IMAGE_SIZE = (800, 800)


# =============================================================================
# Pagination Constants
# =============================================================================

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
