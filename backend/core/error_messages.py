"""CONFIT Backend — Error Messages with Arabic Localization.

This module provides centralized error messages with support for Arabic translation.
All API errors should use error codes from this module for consistent localization.
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ErrorMessage:
    """Error message with English and Arabic translations."""
    code: str
    en: str
    ar: str
    status_code: int = 400


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR MESSAGES DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

ERROR_MESSAGES: Dict[str, ErrorMessage] = {
    # ── General Errors ─────────────────────────────────────────────────────────
    "INTERNAL_ERROR": ErrorMessage(
        code="INTERNAL_ERROR",
        en="An unexpected error occurred. Please try again later.",
        ar="حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى لاحقاً.",
        status_code=500
    ),
    "SERVICE_UNAVAILABLE": ErrorMessage(
        code="SERVICE_UNAVAILABLE",
        en="Service temporarily unavailable. Please try again later.",
        ar="الخدمة غير متاحة مؤقتاً. يرجى المحاولة مرة أخرى لاحقاً.",
        status_code=503
    ),
    "RATE_LIMIT": ErrorMessage(
        code="RATE_LIMIT",
        en="Rate limit exceeded. Please wait before retrying.",
        ar="تم تجاوز الحد المسموح. يرجى الانتظار قبل إعادة المحاولة.",
        status_code=429
    ),
    "VALIDATION_ERROR": ErrorMessage(
        code="VALIDATION_ERROR",
        en="Validation failed. Please check your input.",
        ar="فشل التحقق. يرجى التحقق من المدخلات.",
        status_code=422
    ),
    
    # ── Authentication Errors ────────────────────────────────────────────────
    "AUTH_UNAUTHORIZED": ErrorMessage(
        code="AUTH_UNAUTHORIZED",
        en="Unauthorized. Please log in.",
        ar="غير مصرح. يرجى تسجيل الدخول.",
        status_code=401
    ),
    "AUTH_FORBIDDEN": ErrorMessage(
        code="AUTH_FORBIDDEN",
        en="Access denied. You don't have permission.",
        ar="تم رفض الوصول. ليس لديك الإذن.",
        status_code=403
    ),
    "AUTH_TOKEN_EXPIRED": ErrorMessage(
        code="AUTH_TOKEN_EXPIRED",
        en="Session expired. Please log in again.",
        ar="انتهت صلاحية الجلسة. يرجى تسجيل الدخول مرة أخرى.",
        status_code=401
    ),
    "AUTH_INVALID_CREDENTIALS": ErrorMessage(
        code="AUTH_INVALID_CREDENTIALS",
        en="Invalid email or password.",
        ar="البريد الإلكتروني أو كلمة المرور غير صحيحة.",
        status_code=401
    ),
    "AUTH_ACCOUNT_LOCKED": ErrorMessage(
        code="AUTH_ACCOUNT_LOCKED",
        en="Account temporarily locked. Please try again later.",
        ar="الحساب مقفل مؤقتاً. يرجى المحاولة مرة أخرى لاحقاً.",
        status_code=403
    ),
    
    # ── User Errors ──────────────────────────────────────────────────────────
    "USER_NOT_FOUND": ErrorMessage(
        code="USER_NOT_FOUND",
        en="User not found.",
        ar="المستخدم غير موجود.",
        status_code=404
    ),
    "USER_EMAIL_EXISTS": ErrorMessage(
        code="USER_EMAIL_EXISTS",
        en="Email already registered.",
        ar="البريد الإلكتروني مسجل بالفعل.",
        status_code=409
    ),
    "USER_PHONE_EXISTS": ErrorMessage(
        code="USER_PHONE_EXISTS",
        en="Phone number already registered.",
        ar="رقم الهاتف مسجل بالفعل.",
        status_code=409
    ),
    "USER_PROFILE_INCOMPLETE": ErrorMessage(
        code="USER_PROFILE_INCOMPLETE",
        en="Please complete your profile first.",
        ar="يرجى إكمال ملفك الشخصي أولاً.",
        status_code=400
    ),
    
    # ── Product Errors ───────────────────────────────────────────────────────
    "PRODUCT_NOT_FOUND": ErrorMessage(
        code="PRODUCT_NOT_FOUND",
        en="Product not found.",
        ar="المنتج غير موجود.",
        status_code=404
    ),
    "PRODUCT_OUT_OF_STOCK": ErrorMessage(
        code="PRODUCT_OUT_OF_STOCK",
        en="Product is out of stock.",
        ar="المنتج غير متوفر في المخزون.",
        status_code=400
    ),
    "PRODUCT_UNAVAILABLE": ErrorMessage(
        code="PRODUCT_UNAVAILABLE",
        en="Product is currently unavailable.",
        ar="المنتج غير متوفر حالياً.",
        status_code=400
    ),
    
    # ── Order/Checkout Errors ────────────────────────────────────────────────
    "ORDER_NOT_FOUND": ErrorMessage(
        code="ORDER_NOT_FOUND",
        en="Order not found.",
        ar="الطلب غير موجود.",
        status_code=404
    ),
    "ORDER_INVALID_STATUS": ErrorMessage(
        code="ORDER_INVALID_STATUS",
        en="Invalid order status for this operation.",
        ar="حالة الطلب غير صالحة لهذه العملية.",
        status_code=400
    ),
    "CHECKOUT_CART_EMPTY": ErrorMessage(
        code="CHECKOUT_CART_EMPTY",
        en="Your cart is empty.",
        ar="سلة التسوق فارغة.",
        status_code=400
    ),
    "CHECKOUT_PAYMENT_FAILED": ErrorMessage(
        code="CHECKOUT_PAYMENT_FAILED",
        en="Payment failed. Please try again.",
        ar="فشل الدفع. يرجى المحاولة مرة أخرى.",
        status_code=400
    ),
    "CHECKOUT_INVALID_ADDRESS": ErrorMessage(
        code="CHECKOUT_INVALID_ADDRESS",
        en="Please provide a valid shipping address.",
        ar="يرجى تقديم عنوان شحن صالح.",
        status_code=422
    ),
    
    # ── AI/MUSE Errors ───────────────────────────────────────────────────────
    "AI_SERVICE_UNAVAILABLE": ErrorMessage(
        code="AI_SERVICE_UNAVAILABLE",
        en="AI service temporarily unavailable.",
        ar="خدمة الذكاء الاصطناعي غير متاحة مؤقتاً.",
        status_code=503
    ),
    "AI_RATE_LIMIT": ErrorMessage(
        code="AI_RATE_LIMIT",
        en="AI usage limit reached. Please try again later.",
        ar="تم الوصول إلى حد استخدام الذكاء الاصطناعي. يرجى المحاولة لاحقاً.",
        status_code=429
    ),
    "AI_BUDGET_EXCEEDED": ErrorMessage(
        code="AI_BUDGET_EXCEEDED",
        en="AI service budget exceeded. Please try again tomorrow.",
        ar="تم تجاوز ميزانية خدمة الذكاء الاصطناعي. يرجى المحاولة غداً.",
        status_code=503
    ),
    "MUSE_SESSION_NOT_FOUND": ErrorMessage(
        code="MUSE_SESSION_NOT_FOUND",
        en="Chat session not found.",
        ar="جلسة الدردشة غير موجودة.",
        status_code=404
    ),
    
    # ── MIRROR/Try-On Errors ─────────────────────────────────────────────────
    "TRYON_INVALID_IMAGE": ErrorMessage(
        code="TRYON_INVALID_IMAGE",
        en="Invalid image format. Please upload a valid image.",
        ar="تنسيق صورة غير صالح. يرجى رفع صورة صالحة.",
        status_code=400
    ),
    "TRYON_PROCESSING_FAILED": ErrorMessage(
        code="TRYON_PROCESSING_FAILED",
        en="Try-on processing failed. Please try again.",
        ar="فشل معالجة القياس. يرجى المحاولة مرة أخرى.",
        status_code=500
    ),
    "TRYON_LIMIT_REACHED": ErrorMessage(
        code="TRYON_LIMIT_REACHED",
        en="Daily try-on limit reached.",
        ar="تم الوصول إلى الحد اليومي للقياس.",
        status_code=429
    ),
    
    # ── Wardrobe/Closet Errors ───────────────────────────────────────────────
    "WARDROBE_ITEM_NOT_FOUND": ErrorMessage(
        code="WARDROBE_ITEM_NOT_FOUND",
        en="Wardrobe item not found.",
        ar="عنصر خزانة الملابس غير موجود.",
        status_code=404
    ),
    "WARDROBE_FULL": ErrorMessage(
        code="WARDROBE_FULL",
        en="Wardrobe is full. Please upgrade your plan.",
        ar="خزانة الملابس ممتلئة. يرجى ترقية خطتك.",
        status_code=403
    ),
    "WARDROBE_DUPLICATE_ITEM": ErrorMessage(
        code="WARDROBE_DUPLICATE_ITEM",
        en="Similar item already exists in your wardrobe.",
        ar="عنصر مشابه موجود بالفعل في خزانة ملابسك.",
        status_code=409
    ),
    
    # ── Brand/Store Errors ───────────────────────────────────────────────────
    "BRAND_NOT_FOUND": ErrorMessage(
        code="BRAND_NOT_FOUND",
        en="Brand not found.",
        ar="العلامة التجارية غير موجودة.",
        status_code=404
    ),
    "STORE_NOT_FOUND": ErrorMessage(
        code="STORE_NOT_FOUND",
        en="Store not found.",
        ar="المتجر غير موجود.",
        status_code=404
    ),
    
    # ── File/Upload Errors ───────────────────────────────────────────────────
    "FILE_TOO_LARGE": ErrorMessage(
        code="FILE_TOO_LARGE",
        en="File is too large. Maximum size is 10MB.",
        ar="الملف كبير جداً. الحد الأقصى 10 ميجابايت.",
        status_code=413
    ),
    "FILE_INVALID_TYPE": ErrorMessage(
        code="FILE_INVALID_TYPE",
        en="Invalid file type. Please upload a supported format.",
        ar="نوع ملف غير صالح. يرجى رفع تنسيق مدعوم.",
        status_code=400
    ),
    "UPLOAD_FAILED": ErrorMessage(
        code="UPLOAD_FAILED",
        en="File upload failed. Please try again.",
        ar="فشل رفع الملف. يرجى المحاولة مرة أخرى.",
        status_code=500
    ),
    
    # ── Notification Errors ──────────────────────────────────────────────────
    "NOTIFICATION_NOT_FOUND": ErrorMessage(
        code="NOTIFICATION_NOT_FOUND",
        en="Notification not found.",
        ar="الإشعار غير موجود.",
        status_code=404
    ),
    "NOTIFICATION_SEND_FAILED": ErrorMessage(
        code="NOTIFICATION_SEND_FAILED",
        en="Failed to send notification.",
        ar="فشل إرسال الإشعار.",
        status_code=500
    ),
    
    # ── Social Errors ─────────────────────────────────────────────────────────
    "SOCIAL_POST_NOT_FOUND": ErrorMessage(
        code="SOCIAL_POST_NOT_FOUND",
        en="Post not found.",
        ar="المنشور غير موجود.",
        status_code=404
    ),
    "SOCIAL_COMMENT_NOT_FOUND": ErrorMessage(
        code="SOCIAL_COMMENT_NOT_FOUND",
        en="Comment not found.",
        ar="التعليق غير موجود.",
        status_code=404
    ),
    "SOCIAL_ALREADY_LIKED": ErrorMessage(
        code="SOCIAL_ALREADY_LIKED",
        en="You have already liked this post.",
        ar="لقد أعجبت بهذا المنشور بالفعل.",
        status_code=409
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_error_message(error_code: str, language: str = "en") -> str:
    """
    Get error message by code and language.
    
    Args:
        error_code: The error code (e.g., "USER_NOT_FOUND")
        language: Language code ("en" or "ar")
        
    Returns:
        Error message in the requested language
    """
    error = ERROR_MESSAGES.get(error_code)
    if not error:
        # Return generic message if code not found
        if language == "ar":
            return "حدث خطأ غير متوقع."
        return "An unexpected error occurred."
    
    return error.ar if language == "ar" else error.en


def get_error_details(error_code: str) -> Optional[ErrorMessage]:
    """
    Get full error details by code.
    
    Args:
        error_code: The error code
        
    Returns:
        ErrorMessage object or None
    """
    return ERROR_MESSAGES.get(error_code)


def format_error_response(
    error_code: str,
    language: str = "en",
    details: Optional[dict] = None,
    request_id: Optional[str] = None
) -> dict:
    """
    Format a standardized error response.
    
    Args:
        error_code: The error code
        language: Language code ("en" or "ar")
        details: Additional error details
        request_id: Request ID for tracking
        
    Returns:
        Standardized error response dictionary
    """
    error = ERROR_MESSAGES.get(error_code)
    if not error:
        error = ERROR_MESSAGES["INTERNAL_ERROR"]
    
    return {
        "error": {
            "code": error.code,
            "message": error.ar if language == "ar" else error.en,
            "details": details or {},
            "request_id": request_id,
        },
        "status": error.status_code
    }


def get_all_error_codes() -> list:
    """
    Get list of all available error codes.
    
    Returns:
        List of error codes
    """
    return list(ERROR_MESSAGES.keys())
