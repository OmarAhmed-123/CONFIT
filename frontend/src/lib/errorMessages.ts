/**
 * CONFIT Frontend — Error Message Localization
 * =============================================
 * Maps backend error codes to localized Arabic messages.
 * Aligns with backend: backend/core/error_messages.py
 */

export interface LocalizedError {
  code: string;
  en: string;
  ar: string;
}

/**
 * Error message database with Arabic translations.
 * Keep this in sync with backend/core/error_messages.py
 */
export const ERROR_MESSAGES: Record<string, LocalizedError> = {
  // General Errors
  INTERNAL_ERROR: {
    code: "INTERNAL_ERROR",
    en: "An unexpected error occurred. Please try again later.",
    ar: "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى لاحقاً.",
  },
  SERVICE_UNAVAILABLE: {
    code: "SERVICE_UNAVAILABLE",
    en: "Service temporarily unavailable. Please try again later.",
    ar: "الخدمة غير متاحة مؤقتاً. يرجى المحاولة مرة أخرى لاحقاً.",
  },
  RATE_LIMIT: {
    code: "RATE_LIMIT",
    en: "Rate limit exceeded. Please wait before retrying.",
    ar: "تم تجاوز الحد المسموح. يرجى الانتظار قبل إعادة المحاولة.",
  },
  VALIDATION_ERROR: {
    code: "VALIDATION_ERROR",
    en: "Validation failed. Please check your input.",
    ar: "فشل التحقق. يرجى التحقق من المدخلات.",
  },

  // Authentication Errors
  AUTH_UNAUTHORIZED: {
    code: "AUTH_UNAUTHORIZED",
    en: "Unauthorized. Please log in.",
    ar: "غير مصرح. يرجى تسجيل الدخول.",
  },
  AUTH_FORBIDDEN: {
    code: "AUTH_FORBIDDEN",
    en: "Access denied. You don't have permission.",
    ar: "تم رفض الوصول. ليس لديك الإذن.",
  },
  AUTH_TOKEN_EXPIRED: {
    code: "AUTH_TOKEN_EXPIRED",
    en: "Session expired. Please log in again.",
    ar: "انتهت صلاحية الجلسة. يرجى تسجيل الدخول مرة أخرى.",
  },
  AUTH_INVALID_CREDENTIALS: {
    code: "AUTH_INVALID_CREDENTIALS",
    en: "Invalid email or password.",
    ar: "البريد الإلكتروني أو كلمة المرور غير صحيحة.",
  },
  AUTH_ACCOUNT_LOCKED: {
    code: "AUTH_ACCOUNT_LOCKED",
    en: "Account temporarily locked. Please try again later.",
    ar: "الحساب مقفل مؤقتاً. يرجى المحاولة مرة أخرى لاحقاً.",
  },

  // User Errors
  USER_NOT_FOUND: {
    code: "USER_NOT_FOUND",
    en: "User not found.",
    ar: "المستخدم غير موجود.",
  },
  USER_EMAIL_EXISTS: {
    code: "USER_EMAIL_EXISTS",
    en: "Email already registered.",
    ar: "البريد الإلكتروني مسجل بالفعل.",
  },
  USER_PHONE_EXISTS: {
    code: "USER_PHONE_EXISTS",
    en: "Phone number already registered.",
    ar: "رقم الهاتف مسجل بالفعل.",
  },
  USER_PROFILE_INCOMPLETE: {
    code: "USER_PROFILE_INCOMPLETE",
    en: "Please complete your profile first.",
    ar: "يرجى إكمال ملفك الشخصي أولاً.",
  },

  // Product Errors
  PRODUCT_NOT_FOUND: {
    code: "PRODUCT_NOT_FOUND",
    en: "Product not found.",
    ar: "المنتج غير موجود.",
  },
  PRODUCT_OUT_OF_STOCK: {
    code: "PRODUCT_OUT_OF_STOCK",
    en: "Product is out of stock.",
    ar: "المنتج غير متوفر في المخزون.",
  },
  PRODUCT_UNAVAILABLE: {
    code: "PRODUCT_UNAVAILABLE",
    en: "Product is currently unavailable.",
    ar: "المنتج غير متوفر حالياً.",
  },

  // Order/Checkout Errors
  ORDER_NOT_FOUND: {
    code: "ORDER_NOT_FOUND",
    en: "Order not found.",
    ar: "الطلب غير موجود.",
  },
  ORDER_INVALID_STATUS: {
    code: "ORDER_INVALID_STATUS",
    en: "Invalid order status for this operation.",
    ar: "حالة الطلب غير صالحة لهذه العملية.",
  },
  CHECKOUT_CART_EMPTY: {
    code: "CHECKOUT_CART_EMPTY",
    en: "Your cart is empty.",
    ar: "سلة التسوق فارغة.",
  },
  CHECKOUT_PAYMENT_FAILED: {
    code: "CHECKOUT_PAYMENT_FAILED",
    en: "Payment failed. Please try again.",
    ar: "فشل الدفع. يرجى المحاولة مرة أخرى.",
  },
  CHECKOUT_INVALID_ADDRESS: {
    code: "CHECKOUT_INVALID_ADDRESS",
    en: "Please provide a valid shipping address.",
    ar: "يرجى تقديم عنوان شحن صالح.",
  },

  // AI/MUSE Errors
  AI_SERVICE_UNAVAILABLE: {
    code: "AI_SERVICE_UNAVAILABLE",
    en: "AI service temporarily unavailable.",
    ar: "خدمة الذكاء الاصطناعي غير متاحة مؤقتاً.",
  },
  AI_RATE_LIMIT: {
    code: "AI_RATE_LIMIT",
    en: "AI usage limit reached. Please try again later.",
    ar: "تم الوصول إلى حد استخدام الذكاء الاصطناعي. يرجى المحاولة لاحقاً.",
  },
  AI_BUDGET_EXCEEDED: {
    code: "AI_BUDGET_EXCEEDED",
    en: "AI service budget exceeded. Please try again tomorrow.",
    ar: "تم تجاوز ميزانية خدمة الذكاء الاصطناعي. يرجى المحاولة غداً.",
  },
  MUSE_SESSION_NOT_FOUND: {
    code: "MUSE_SESSION_NOT_FOUND",
    en: "Chat session not found.",
    ar: "جلسة الدردشة غير موجودة.",
  },

  // MIRROR/Try-On Errors
  TRYON_INVALID_IMAGE: {
    code: "TRYON_INVALID_IMAGE",
    en: "Invalid image format. Please upload a valid image.",
    ar: "تنسيق صورة غير صالح. يرجى رفع صورة صالحة.",
  },
  TRYON_PROCESSING_FAILED: {
    code: "TRYON_PROCESSING_FAILED",
    en: "Try-on processing failed. Please try again.",
    ar: "فشل معالجة القياس. يرجى المحاولة مرة أخرى.",
  },
  TRYON_LIMIT_REACHED: {
    code: "TRYON_LIMIT_REACHED",
    en: "Daily try-on limit reached.",
    ar: "تم الوصول إلى الحد اليومي للقياس.",
  },

  // Wardrobe/Closet Errors
  WARDROBE_ITEM_NOT_FOUND: {
    code: "WARDROBE_ITEM_NOT_FOUND",
    en: "Wardrobe item not found.",
    ar: "عنصر خزانة الملابس غير موجود.",
  },
  WARDROBE_FULL: {
    code: "WARDROBE_FULL",
    en: "Wardrobe is full. Please upgrade your plan.",
    ar: "خزانة الملابس ممتلئة. يرجى ترقية خطتك.",
  },
  WARDROBE_DUPLICATE_ITEM: {
    code: "WARDROBE_DUPLICATE_ITEM",
    en: "Similar item already exists in your wardrobe.",
    ar: "عنصر مشابه موجود بالفعل في خزانة ملابسك.",
  },

  // Brand/Store Errors
  BRAND_NOT_FOUND: {
    code: "BRAND_NOT_FOUND",
    en: "Brand not found.",
    ar: "العلامة التجارية غير موجودة.",
  },
  STORE_NOT_FOUND: {
    code: "STORE_NOT_FOUND",
    en: "Store not found.",
    ar: "المتجر غير موجود.",
  },

  // File/Upload Errors
  FILE_TOO_LARGE: {
    code: "FILE_TOO_LARGE",
    en: "File is too large. Maximum size is 10MB.",
    ar: "الملف كبير جداً. الحد الأقصى 10 ميجابايت.",
  },
  FILE_INVALID_TYPE: {
    code: "FILE_INVALID_TYPE",
    en: "Invalid file type. Please upload a supported format.",
    ar: "نوع ملف غير صالح. يرجى رفع تنسيق مدعوم.",
  },
  UPLOAD_FAILED: {
    code: "UPLOAD_FAILED",
    en: "File upload failed. Please try again.",
    ar: "فشل رفع الملف. يرجى المحاولة مرة أخرى.",
  },

  // Notification Errors
  NOTIFICATION_NOT_FOUND: {
    code: "NOTIFICATION_NOT_FOUND",
    en: "Notification not found.",
    ar: "الإشعار غير موجود.",
  },
  NOTIFICATION_SEND_FAILED: {
    code: "NOTIFICATION_SEND_FAILED",
    en: "Failed to send notification.",
    ar: "فشل إرسال الإشعار.",
  },

  // Social Errors
  SOCIAL_POST_NOT_FOUND: {
    code: "SOCIAL_POST_NOT_FOUND",
    en: "Post not found.",
    ar: "المنشور غير موجود.",
  },
  SOCIAL_COMMENT_NOT_FOUND: {
    code: "SOCIAL_COMMENT_NOT_FOUND",
    en: "Comment not found.",
    ar: "التعليق غير موجود.",
  },
  SOCIAL_ALREADY_LIKED: {
    code: "SOCIAL_ALREADY_LIKED",
    en: "You have already liked this post.",
    ar: "لقد أعجبت بهذا المنشور بالفعل.",
  },
};

/**
 * Get localized error message by code
 */
export function getErrorMessage(
  errorCode: string | undefined,
  language: "en" | "ar" = "en"
): string {
  if (!errorCode) {
    return language === "ar"
      ? "حدث خطأ غير متوقع"
      : "An unexpected error occurred";
  }

  const error = ERROR_MESSAGES[errorCode];
  if (!error) {
    return language === "ar"
      ? "حدث خطأ غير متوقع"
      : "An unexpected error occurred";
  }

  return error[language];
}

/**
 * Parse API error response and extract localized message
 */
export function parseApiError(
  error: unknown,
  language: "en" | "ar" = "en"
): { message: string; code: string; status?: number } {
  // Handle API error response format
  if (error && typeof error === "object") {
    const apiError = error as {
      error?: {
        code?: string;
        message?: string;
        status?: number;
      };
      response?: {
        data?: {
          error?: {
            code?: string;
            message?: string;
          };
        };
        status?: number;
      };
    };

    // Check for error.error format (our format)
    if (apiError.error?.code) {
      return {
        code: apiError.error.code,
        message: getErrorMessage(apiError.error.code, language),
        status: apiError.error.status,
      };
    }

    // Check for axios error response format
    if (apiError.response?.data?.error?.code) {
      return {
        code: apiError.response.data.error.code,
        message: getErrorMessage(apiError.response.data.error.code, language),
        status: apiError.response.status,
      };
    }

    // Check for error message directly
    if (apiError.error?.message) {
      return {
        code: apiError.error.code || "UNKNOWN_ERROR",
        message:
          language === "ar"
            ? apiError.error.message
            : apiError.error.message,
        status: apiError.error.status,
      };
    }
  }

  // Fallback
  return {
    code: "UNKNOWN_ERROR",
    message:
      language === "ar"
        ? "حدث خطأ غير متوقع"
        : "An unexpected error occurred",
  };
}
