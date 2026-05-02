"""CONFIT Backend — Email Templates with Arabic Localization
===========================================================
Localized email templates for all notification types.
Supports both English and Arabic with RTL layout for Arabic.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Literal

EmailLanguage = Literal["en", "ar"]


@dataclass
class EmailTemplate:
    """Email template with localization support."""
    subject_en: str
    subject_ar: str
    template_id_en: Optional[str] = None
    template_id_ar: Optional[str] = None


class EmailTemplates:
    """Collection of localized email templates."""

    # ═══════════════════════════════════════════════════════════════════════════
    # AUTHENTICATION EMAILS
    # ═══════════════════════════════════════════════════════════════════════════

    WELCOME = EmailTemplate(
        subject_en="Welcome to CONFIT - Your AI-Powered Fashion Journey Begins!",
        subject_ar="مرحباً بك في CONFIT - رحلتك مع الموضة بالذكاء الاصطناعي تبدأ الآن!",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",  # SendGrid template IDs
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    EMAIL_VERIFICATION = EmailTemplate(
        subject_en="Verify Your Email Address",
        subject_ar="تحقق من بريدك الإلكتروني",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    PASSWORD_RESET = EmailTemplate(
        subject_en="Reset Your Password",
        subject_ar="إعادة تعيين كلمة المرور",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    PASSWORD_CHANGED = EmailTemplate(
        subject_en="Your Password Has Been Changed",
        subject_ar="تم تغيير كلمة المرور",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ORDER EMAILS
    # ═══════════════════════════════════════════════════════════════════════════

    ORDER_CONFIRMATION = EmailTemplate(
        subject_en="Order Confirmation - #{order_number}",
        subject_ar="تأكيد الطلب - #{order_number}",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    ORDER_SHIPPED = EmailTemplate(
        subject_en="Your Order Has Been Shipped!",
        subject_ar="تم شحن طلبك!",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    ORDER_DELIVERED = EmailTemplate(
        subject_en="Your Order Has Been Delivered",
        subject_ar="تم توصيل طلبك",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    ORDER_CANCELLED = EmailTemplate(
        subject_en="Order Cancellation - #{order_number}",
        subject_ar="إلغاء الطلب - #{order_number}",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    ORDER_REFUNDED = EmailTemplate(
        subject_en="Refund Processed - #{order_number}",
        subject_ar="تم معالجة الاسترداد - #{order_number}",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # AI SERVICE EMAILS
    # ═══════════════════════════════════════════════════════════════════════════

    AI_BUDGET_WARNING = EmailTemplate(
        subject_en="AI Usage Budget Alert",
        subject_ar="تنبيه ميزانية استخدام الذكاء الاصطناعي",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    STYLE_REPORT_READY = EmailTemplate(
        subject_en="Your Style Analysis Report is Ready!",
        subject_ar="تقرير تحليل أسلوبك جاهز!",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # MARKETING EMAILS
    # ═══════════════════════════════════════════════════════════════════════════

    WEEKLY_DIGEST = EmailTemplate(
        subject_en="Your Weekly Style Digest",
        subject_ar="ملخص أسبوعي للأناقة",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    NEW_ARRIVALS = EmailTemplate(
        subject_en="New Arrivals Just For You",
        subject_ar="وصل حديثاً مخصص لك",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    SPECIAL_OFFER = EmailTemplate(
        subject_en="Exclusive Offer Inside!",
        subject_ar="عرض حصري لك!",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    ABANDONED_CART = EmailTemplate(
        subject_en="Don't Forget Your Items!",
        subject_ar="لا تنسَ منتجاتك!",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # ACCOUNT EMAILS
    # ═══════════════════════════════════════════════════════════════════════════

    ACCOUNT_SECURITY_ALERT = EmailTemplate(
        subject_en="Security Alert - New Login Detected",
        subject_ar="تنبيه أمني - تم اكتشاف تسجيل دخول جديد",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    PROFILE_UPDATED = EmailTemplate(
        subject_en="Your Profile Has Been Updated",
        subject_ar="تم تحديث ملفك الشخصي",
        template_id_en="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_id_ar="d-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def get_subject(cls, template: EmailTemplate, language: EmailLanguage = "en") -> str:
        """Get localized subject for template."""
        return template.subject_ar if language == "ar" else template.subject_en

    @classmethod
    def get_template_id(cls, template: EmailTemplate, language: EmailLanguage = "en") -> Optional[str]:
        """Get SendGrid template ID for language."""
        return template.template_id_ar if language == "ar" else template.template_id_en


# ═══════════════════════════════════════════════════════════════════════════════
# HTML EMAIL TEMPLATES (Fallback for non-SendGrid)
# ═══════════════════════════════════════════════════════════════════════════════

HTML_TEMPLATES: Dict[str, Dict[EmailLanguage, str]] = {
    "welcome": {
        "en": """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to CONFIT</title>
    <style>
        body { font-family: 'Inter', Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #D4AF37 0%, #F5E6C8 100%); padding: 30px; text-align: center; }
        .content { background: #fff; padding: 30px; }
        .button { display: inline-block; background: #D4AF37; color: #fff; padding: 12px 30px; 
                  text-decoration: none; border-radius: 6px; margin: 20px 0; }
        .footer { background: #f8f8f8; padding: 20px; text-align: center; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to CONFIT!</h1>
            <p>Your AI-Powered Fashion Journey Begins</p>
        </div>
        <div class="content">
            <h2>Hi {{first_name}},</h2>
            <p>Welcome to the future of fashion! We're thrilled to have you join CONFIT, where AI meets style to create your perfect wardrobe.</p>
            <p>Here's what you can do:</p>
            <ul>
                <li>🤖 Chat with MUSE, your AI stylist</li>
                <li>👗 Try on clothes virtually with MIRROR</li>
                <li>👔 Build your digital wardrobe</li>
                <li>🛍️ Shop curated collections</li>
            </ul>
            <center>
                <a href="{{dashboard_url}}" class="button">Get Started</a>
            </center>
            <p>If you have any questions, our support team is always here to help!</p>
            <p>Best regards,<br>The CONFIT Team</p>
        </div>
        <div class="footer">
            <p>© 2024 CONFIT. All rights reserved.</p>
            <p><a href="{{unsubscribe_url}}">Unsubscribe</a> | <a href="{{privacy_url}}">Privacy Policy</a></p>
        </div>
    </div>
</body>
</html>
""",
        "ar": """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مرحباً بك في CONFIT</title>
    <style>
        body { font-family: 'Inter', 'Tajawal', Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #D4AF37 0%, #F5E6C8 100%); padding: 30px; text-align: center; }
        .content { background: #fff; padding: 30px; }
        .button { display: inline-block; background: #D4AF37; color: #fff; padding: 12px 30px; 
                  text-decoration: none; border-radius: 6px; margin: 20px 0; }
        .footer { background: #f8f8f8; padding: 20px; text-align: center; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>مرحباً بك في CONFIT!</h1>
            <p>رحلتك مع الموضة بالذكاء الاصطناعي تبدأ الآن</p>
        </div>
        <div class="content">
            <h2>مرحباً {{first_name}}،</h2>
            <p>أهلاً بك في مستقبل الموضة! نحن سعداء بانضمامك لـ CONFIT، حيث يلتقي الذكاء الاصطناعي بالأناقة ليصنع لك خزانة ملابس مثالية.</p>
            <p>إليك ما يمكنك فعله:</p>
            <ul>
                <li>🤖 تحدث مع MUSE، مصممك بالذكاء الاصطناعي</li>
                <li>👗 جرب الملابس افتراضياً مع MIRROR</li>
                <li>👔 ابنِ خزانة ملابسك الرقمية</li>
                <li>🛍️ تسوق من مجموعاتنا المختارة</li>
            </ul>
            <center>
                <a href="{{dashboard_url}}" class="button">ابدأ الآن</a>
            </center>
            <p>إذا كان لديك أي أسئلة، فريق الدعم لدينا دائماً متواجد للمساعدة!</p>
            <p>مع أطيب التحيات،<br>فريق CONFIT</p>
        </div>
        <div class="footer">
            <p>© 2024 CONFIT. جميع الحقوق محفوظة.</p>
            <p><a href="{{unsubscribe_url}}">إلغاء الاشتراك</a> | <a href="{{privacy_url}}">سياسة الخصوصية</a></p>
        </div>
    </div>
</body>
</html>
""",
    },
    "order_confirmation": {
        "en": """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Order Confirmation</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #D4AF37; color: white; padding: 20px; text-align: center; }
        .order-details { background: #f9f9f9; padding: 20px; margin: 20px 0; }
        .item { border-bottom: 1px solid #ddd; padding: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Order Confirmed!</h1>
            <p>Order #{{order_number}}</p>
        </div>
        <p>Hi {{first_name}},</p>
        <p>Thank you for your order. We've received it and are preparing it for shipment.</p>
        <div class="order-details">
            <h3>Order Details</h3>
            <div class="items">{{order_items}}</div>
            <p><strong>Total:</strong> {{order_total}}</p>
        </div>
        <p>We'll notify you when your order ships.</p>
    </div>
</body>
</html>
""",
        "ar": """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>تأكيد الطلب</title>
    <style>
        body { font-family: Arial, 'Tajawal', sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #D4AF37; color: white; padding: 20px; text-align: center; }
        .order-details { background: #f9f9f9; padding: 20px; margin: 20px 0; }
        .item { border-bottom: 1px solid #ddd; padding: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>تم تأكيد الطلب!</h1>
            <p>طلب #{{order_number}}</p>
        </div>
        <p>مرحباً {{first_name}}،</p>
        <p>شكراً لطلبك. لقد استلمناه ونعمل على تحضيره للشحن.</p>
        <div class="order-details">
            <h3>تفاصيل الطلب</h3>
            <div class="items">{{order_items}}</div>
            <p><strong>الإجمالي:</strong> {{order_total}}</p>
        </div>
        <p>سنُعلمك عند شحن طلبك.</p>
    </div>
</body>
</html>
""",
    },
}


def get_html_template(template_name: str, language: EmailLanguage = "en") -> str:
    """Get HTML email template by name and language."""
    templates = HTML_TEMPLATES.get(template_name, {})
    return templates.get(language, templates.get("en", ""))
