"""
CONFIT Backend - SendGrid Email Client
=====================================
Transactional email integration using SendGrid.
Works in Egypt with proper SPF/DKIM configuration.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.integrations.base import BaseIntegration, IntegrationError

logger = logging.getLogger(__name__)


class SendGridClient(BaseIntegration):
    """
    SendGrid client for transactional emails.
    
    Features:
    - Dynamic templates for different email types
    - Batch sending
    - Attachment support
    - Email tracking and analytics
    
    Configuration:
        SENDGRID_API_KEY=SG.xxxxx
        SENDGRID_FROM_EMAIL=noreply@confit.app
        SENDGRID_FROM_NAME=CONFIT
    
    Email Templates (configure in SendGrid dashboard):
    - Order confirmation: d-xxxxx
    - Donor receipt: d-xxxxx
    - Coupon redeemed: d-xxxxx
    - Welcome email: d-xxxxx
    - Password reset: d-xxxxx
    
    Egypt Notes:
    - SendGrid works in Egypt
    - Ensure SPF/DKIM configured for confit.app domain
    - Arabic email templates supported
    """
    
    SENDGRID_API_BASE = "https://api.sendgrid.com/v3"
    
    # Template IDs (set these in environment or SendGrid dashboard)
    TEMPLATE_ORDER_CONFIRMATION = "order_confirmation"
    TEMPLATE_DONOR_RECEIPT = "donor_receipt"
    TEMPLATE_COUPON_REDEEMED = "coupon_redeemed"
    TEMPLATE_WELCOME = "welcome"
    TEMPLATE_PASSWORD_RESET = "password_reset"
    TEMPLATE_DELIVERY_UPDATE = "delivery_update"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        timeout_seconds: float = 15.0,
    ):
        super().__init__(
            provider="sendgrid",
            timeout_seconds=timeout_seconds,
            max_retries=3,
            base_url=self.SENDGRID_API_BASE,
        )
        self.api_key = api_key or os.getenv("SENDGRID_API_KEY")
        self.from_email = from_email or os.getenv("SENDGRID_FROM_EMAIL", "noreply@confit.app")
        self.from_name = from_name or os.getenv("SENDGRID_FROM_NAME", "CONFIT")
        
        if not self.api_key:
            raise IntegrationError(
                "SENDGRID_API_KEY required",
                provider="sendgrid",
            )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get SendGrid API headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        template_id: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, str]]] = None,
        reply_to: Optional[str] = None,
        categories: Optional[List[str]] = None,
        custom_args: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Send a transactional email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject (ignored if using template)
            html_content: HTML body content
            text_content: Plain text body content
            template_id: SendGrid dynamic template ID (e.g., "d-xxxxx")
            template_data: Data for dynamic template
            attachments: List of {"content": base64, "filename": "...", "type": "..."}
            reply_to: Reply-to email address
            categories: Categories for analytics
            custom_args: Custom arguments for tracking
            
        Returns:
            API response with message ID
            
        Raises:
            IntegrationError: On send failure
        """
        url = "/mail/send"
        
        # Build payload
        payload = {
            "from": {
                "email": self.from_email,
                "name": self.from_name,
            },
            "personalizations": [
                {
                    "to": [{"email": to_email}],
                }
            ],
        }
        
        # Add subject (required if not using template)
        if subject and not template_id:
            payload["personalizations"][0]["subject"] = subject
        
        # Add template
        if template_id:
            payload["template_id"] = template_id
            if template_data:
                payload["personalizations"][0]["dynamic_template_data"] = template_data
        
        # Add content
        content = []
        if text_content:
            content.append({"type": "text/plain", "value": text_content})
        if html_content:
            content.append({"type": "text/html", "value": html_content})
        if content:
            payload["content"] = content
        
        # Add reply-to
        if reply_to:
            payload["reply_to"] = {"email": reply_to}
        
        # Add attachments
        if attachments:
            payload["attachments"] = attachments
        
        # Add categories
        if categories:
            payload["categories"] = categories
        
        # Add custom args
        if custom_args:
            payload["personalizations"][0]["custom_args"] = custom_args
        
        response = await self._request(
            "POST",
            url,
            json=payload,
            headers=self._get_headers(),
        )
        
        if not response.is_success:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"raw": response.text}
            
            raise IntegrationError(
                f"SendGrid email failed: {response.status_code}",
                provider="sendgrid",
                status_code=response.status_code,
                response_data=error_data,
            )
        
        # Get message ID from headers
        message_id = response.headers.get("X-Message-Id", "")
        
        logger.info(
            f"[sendgrid] Email sent to {to_email} "
            f"(message_id: {message_id}, template: {template_id or 'none'})"
        )
        
        return {
            "success": True,
            "message_id": message_id,
            "to": to_email,
        }
    
    async def send_template_email(
        self,
        to_email: str,
        template_name: str,
        template_data: Dict[str, Any],
        template_id_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send email using a named template.
        
        Args:
            to_email: Recipient email
            template_name: Template name (e.g., "order_confirmation")
            template_data: Dynamic template data
            template_id_override: Override template ID
            
        Returns:
            Send result
        """
        # Get template ID from env or use override
        template_id = template_id_override or os.getenv(
            f"SENDGRID_TEMPLATE_{template_name.upper()}",
            ""
        )
        
        if not template_id:
            # Try to find in predefined templates
            template_map = {
                self.TEMPLATE_ORDER_CONFIRMATION: os.getenv("SENDGRID_TEMPLATE_ORDER_CONFIRMATION"),
                self.TEMPLATE_DONOR_RECEIPT: os.getenv("SENDGRID_TEMPLATE_DONOR_RECEIPT"),
                self.TEMPLATE_COUPON_REDEEMED: os.getenv("SENDGRID_TEMPLATE_COUPON_REDEEMED"),
                self.TEMPLATE_WELCOME: os.getenv("SENDGRID_TEMPLATE_WELCOME"),
                self.TEMPLATE_PASSWORD_RESET: os.getenv("SENDGRID_TEMPLATE_PASSWORD_RESET"),
                self.TEMPLATE_DELIVERY_UPDATE: os.getenv("SENDGRID_TEMPLATE_DELIVERY_UPDATE"),
            }
            template_id = template_map.get(template_name, "")
        
        if not template_id:
            raise IntegrationError(
                f"Template not found: {template_name}",
                provider="sendgrid",
            )
        
        return await self.send_email(
            to_email=to_email,
            subject="",  # Subject from template
            template_id=template_id,
            template_data=template_data,
            categories=[template_name],
        )
    
    async def send_order_confirmation(
        self,
        to_email: str,
        order_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send order confirmation email.
        
        Args:
            to_email: Customer email
            order_data: Order details (number, items, total, etc.)
            
        Returns:
            Send result
        """
        template_data = {
            "order_number": order_data.get("order_number"),
            "order_date": order_data.get("order_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            "customer_name": order_data.get("customer_name", ""),
            "items": order_data.get("items", []),
            "subtotal": order_data.get("subtotal", "0.00"),
            "shipping": order_data.get("shipping", "0.00"),
            "total": order_data.get("total", "0.00"),
            "currency": order_data.get("currency", "EGP"),
            "delivery_method": order_data.get("delivery_method", "shipping"),
            "estimated_delivery": order_data.get("estimated_delivery", ""),
            "tracking_url": order_data.get("tracking_url", ""),
        }
        
        return await self.send_template_email(
            to_email=to_email,
            template_name=self.TEMPLATE_ORDER_CONFIRMATION,
            template_data=template_data,
        )
    
    async def send_donor_receipt(
        self,
        to_email: str,
        donation_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send donation receipt email.
        
        Args:
            to_email: Donor email
            donation_data: Donation details
            
        Returns:
            Send result
        """
        template_data = {
            "donor_name": donation_data.get("donor_name", ""),
            "donation_amount": donation_data.get("amount", "0.00"),
            "currency": donation_data.get("currency", "EGP"),
            "donation_date": donation_data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            "recipient_name": donation_data.get("recipient_name", ""),
            "message": donation_data.get("message", ""),
            "receipt_number": donation_data.get("receipt_number", ""),
        }
        
        return await self.send_template_email(
            to_email=to_email,
            template_name=self.TEMPLATE_DONOR_RECEIPT,
            template_data=template_data,
        )
    
    async def send_coupon_redeemed(
        self,
        to_email: str,
        coupon_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send coupon redemption confirmation.
        
        Args:
            to_email: Customer email
            coupon_data: Coupon details
            
        Returns:
            Send result
        """
        template_data = {
            "customer_name": coupon_data.get("customer_name", ""),
            "coupon_code": coupon_data.get("code", ""),
            "discount": coupon_data.get("discount", ""),
            "order_number": coupon_data.get("order_number", ""),
            "expiry_date": coupon_data.get("expiry_date", ""),
        }
        
        return await self.send_template_email(
            to_email=to_email,
            template_name=self.TEMPLATE_COUPON_REDEEMED,
            template_data=template_data,
        )
    
    async def send_password_reset(
        self,
        to_email: str,
        reset_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send password reset email.
        
        Args:
            to_email: User email
            reset_data: Reset link and expiry
            
        Returns:
            Send result
        """
        template_data = {
            "name": reset_data.get("name", ""),
            "reset_link": reset_data.get("reset_link", ""),
            "expiry_hours": reset_data.get("expiry_hours", 24),
        }
        
        return await self.send_template_email(
            to_email=to_email,
            template_name=self.TEMPLATE_PASSWORD_RESET,
            template_data=template_data,
        )
    
    async def send_batch(
        self,
        emails: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Send multiple emails in batch.
        
        Args:
            emails: List of email payloads
            
        Returns:
            List of results
        """
        results = []
        for email in emails:
            try:
                result = await self.send_email(**email)
                results.append(result)
            except IntegrationError as e:
                results.append({
                    "success": False,
                    "to": email.get("to_email"),
                    "error": str(e),
                })
        return results
    
    async def get_email_status(self, message_id: str) -> Dict[str, Any]:
        """
        Get email delivery status.
        
        Args:
            message_id: Message ID from send response
            
        Returns:
            Status info
        """
        url = f"/messages/{message_id}"
        
        response = await self._request(
            "GET",
            url,
            headers=self._get_headers(),
        )
        
        if response.is_success:
            return response.json()
        
        return {"status": "unknown", "message_id": message_id}
    
    async def health_check(self) -> bool:
        """Check SendGrid API connectivity."""
        try:
            url = "/user/account"
            response = await self._request(
                "GET",
                url,
                headers=self._get_headers(),
            )
            
            if response.is_success:
                data = response.json()
                logger.info(
                    f"[sendgrid] Health check passed for account: {data.get('email', 'unknown')}"
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[sendgrid] Health check failed: {e}")
            return False


# Singleton instance
_sendgrid_client: Optional[SendGridClient] = None


def get_sendgrid_client() -> SendGridClient:
    """Get SendGrid client singleton."""
    global _sendgrid_client
    if _sendgrid_client is None:
        _sendgrid_client = SendGridClient()
    return _sendgrid_client
