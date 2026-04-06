"""
CONFIT Backend - Twilio WhatsApp Client
======================================
WhatsApp Business API integration via Twilio.
IMPORTANT: This is for WhatsApp ONLY, not SMS.
Twilio SMS to Egypt costs $0.065/msg vs local SMS $0.005/msg.
"""

import base64
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.integrations.base import BaseIntegration, IntegrationError

logger = logging.getLogger(__name__)


class TwilioWhatsAppClient(BaseIntegration):
    """
    Twilio WhatsApp Business API client.
    
    IMPORTANT: This client is for WhatsApp ONLY.
    Do NOT use for SMS in Egypt (use local SMS gateway instead).
    
    Features:
    - Send template messages (pre-approved by WhatsApp)
    - Send freeform messages (only within 24h service window)
    - Support for Arabic + English templates
    - Delivery status webhooks
    
    Configuration:
        TWILIO_ACCOUNT_SID=ACxxxxx
        TWILIO_AUTH_TOKEN=xxxxx
        TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
    
    Egypt Notes:
    - Get approved WhatsApp templates in Arabic + English
    - Template approval takes 1-2 business days
    - Freeform messages only work within 24h of user's last message
    """
    
    WHATSAPP_API_BASE = "https://api.twilio.com/2010-04-01/Accounts"
    
    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
        timeout_seconds: float = 15.0,
    ):
        super().__init__(
            provider="twilio_whatsapp",
            timeout_seconds=timeout_seconds,
            max_retries=3,
        )
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = from_number or os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
        
        if not self.account_sid or not self.auth_token:
            raise IntegrationError(
                "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN required",
                provider="twilio_whatsapp",
            )
    
    def _get_auth_header(self) -> Dict[str, str]:
        """Generate Basic Auth header for Twilio API."""
        credentials = f"{self.account_sid}:{self.auth_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}
    
    def _format_phone(self, phone: str) -> str:
        """
        Format phone number for WhatsApp.
        
        Args:
            phone: Phone number (e.g., "+201234567890" or "01234567890")
            
        Returns:
            Formatted WhatsApp address (e.g., "whatsapp:+201234567890")
        """
        # Remove any whatsapp: prefix
        phone = phone.replace("whatsapp:", "").replace("WhatsApp:", "")
        
        # Ensure + prefix
        if not phone.startswith("+"):
            if phone.startswith("00"):
                phone = "+" + phone[2:]
            elif phone.startswith("0"):
                # Egypt: convert 0 to +20
                phone = "+20" + phone[1:]
            else:
                phone = "+" + phone
        
        return f"whatsapp:{phone}"
    
    async def send_template(
        self,
        to_phone: str,
        template_sid: str,
        variables: Optional[Dict[str, str]] = None,
        language_code: str = "en_US",
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp template message.
        
        Template messages are pre-approved by WhatsApp and can be sent
        at any time (outside the 24h service window).
        
        Args:
            to_phone: Recipient phone number
            template_sid: Twilio template SID (e.g., "HXxxxxx")
            variables: Template variable substitutions {"1": "value", "2": "value"}
            language_code: Template language ("en_US", "ar", etc.)
            
        Returns:
            API response with message SID
            
        Raises:
            IntegrationError: On send failure
            
        Example:
            # Order confirmation template
            await client.send_template(
                to_phone="+201234567890",
                template_sid="HXorder_confirm",
                variables={"1": "ORD-12345", "2": "250 EGP"},
                language_code="ar",  # Arabic template
            )
        """
        url = f"{self.WHATSAPP_API_BASE}/{self.account_sid}/Messages.json"
        
        # Build content variables for template
        content_variables = {}
        if variables:
            for key, value in variables.items():
                # Twilio uses {{1}}, {{2}}, etc.
                content_variables[key] = value
        
        form_data = {
            "To": self._format_phone(to_phone),
            "From": self.from_number,
            "ContentSid": template_sid,
            "ContentVariables": str(content_variables) if content_variables else "{}",
        }
        
        headers = self._get_auth_header()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        
        response = await self._request(
            "POST",
            url,
            data=form_data,
            headers=headers,
        )
        
        if not response.is_success:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"raw": response.text}
            
            raise IntegrationError(
                f"Failed to send WhatsApp template: {response.status_code}",
                provider="twilio_whatsapp",
                status_code=response.status_code,
                response_data=error_data,
            )
        
        result = response.json()
        
        logger.info(
            f"[twilio_whatsapp] Template sent to {to_phone} "
            f"(sid: {result.get('sid')}, template: {template_sid})"
        )
        
        return result
    
    async def send_freeform(
        self,
        to_phone: str,
        body: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a freeform WhatsApp message.
        
        IMPORTANT: Freeform messages only work within 24 hours of the
        user's last message to your business (24h service window).
        
        For messages outside this window, use send_template() instead.
        
        Args:
            to_phone: Recipient phone number
            body: Message body text (supports Arabic UTF-8)
            media_url: Optional media URL (image, document, video)
            
        Returns:
            API response with message SID
            
        Raises:
            IntegrationError: On send failure (e.g., outside 24h window)
        """
        url = f"{self.WHATSAPP_API_BASE}/{self.account_sid}/Messages.json"
        
        form_data = {
            "To": self._format_phone(to_phone),
            "From": self.from_number,
            "Body": body,
        }
        
        if media_url:
            form_data["MediaUrl"] = media_url
        
        headers = self._get_auth_header()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        
        response = await self._request(
            "POST",
            url,
            data=form_data,
            headers=headers,
        )
        
        if not response.is_success:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"raw": response.text}
            
            # Check for 24h window error
            error_msg = error_data.get("message", "").lower()
            if "24" in error_msg or "window" in error_msg or "template" in error_msg:
                raise IntegrationError(
                    "Freeform message outside 24h service window. Use template message instead.",
                    provider="twilio_whatsapp",
                    status_code=response.status_code,
                    response_data=error_data,
                )
            
            raise IntegrationError(
                f"Failed to send WhatsApp message: {response.status_code}",
                provider="twilio_whatsapp",
                status_code=response.status_code,
                response_data=error_data,
            )
        
        result = response.json()
        
        logger.info(
            f"[twilio_whatsapp] Freeform message sent to {to_phone} "
            f"(sid: {result.get('sid')})"
        )
        
        return result
    
    async def send_interactive_button(
        self,
        to_phone: str,
        body: str,
        buttons: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Send an interactive message with buttons.
        
        Args:
            to_phone: Recipient phone number
            body: Message body text
            buttons: List of buttons [{"id": "btn1", "title": "Yes"}, ...]
            
        Returns:
            API response
        """
        url = f"{self.WHATSAPP_API_BASE}/{self.account_sid}/Messages.json"
        
        # Build interactive payload
        interactive = {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": btn["id"], "title": btn["title"]}
                    }
                    for btn in buttons[:3]  # Max 3 buttons
                ]
            }
        }
        
        form_data = {
            "To": self._format_phone(to_phone),
            "From": self.from_number,
            "Body": body,  # Fallback for non-interactive clients
        }
        
        headers = self._get_auth_header()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        
        response = await self._request(
            "POST",
            url,
            data=form_data,
            headers=headers,
        )
        
        if not response.is_success:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"raw": response.text}
            
            raise IntegrationError(
                f"Failed to send interactive message: {response.status_code}",
                provider="twilio_whatsapp",
                status_code=response.status_code,
                response_data=error_data,
            )
        
        return response.json()
    
    async def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Get delivery status of a sent message.
        
        Args:
            message_sid: Message SID from send response
            
        Returns:
            Status info: {"status": "delivered", "error_code": null, ...}
        """
        url = f"{self.WHATSAPP_API_BASE}/{self.account_sid}/Messages/{message_sid}.json"
        
        headers = self._get_auth_header()
        
        response = await self._request("GET", url, headers=headers)
        
        if not response.is_success:
            raise IntegrationError(
                f"Failed to get message status: {response.status_code}",
                provider="twilio_whatsapp",
                status_code=response.status_code,
            )
        
        data = response.json()
        
        return {
            "sid": data.get("sid"),
            "status": data.get("status"),  # queued, sent, delivered, read, failed
            "error_code": data.get("error_code"),
            "error_message": data.get("error_message"),
            "date_created": data.get("date_created"),
            "date_sent": data.get("date_sent"),
            "to": data.get("to"),
        }
    
    async def health_check(self) -> bool:
        """Check if Twilio credentials are valid."""
        try:
            url = f"{self.WHATSAPP_API_BASE}/{self.account_sid}.json"
            headers = self._get_auth_header()
            
            response = await self._request("GET", url, headers=headers)
            
            if response.is_success:
                data = response.json()
                logger.info(
                    f"[twilio_whatsapp] Health check passed for account: {data.get('friendly_name')}"
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[twilio_whatsapp] Health check failed: {e}")
            return False


# Singleton instance
_twilio_whatsapp_client: Optional[TwilioWhatsAppClient] = None


def get_twilio_whatsapp_client() -> TwilioWhatsAppClient:
    """Get Twilio WhatsApp client singleton."""
    global _twilio_whatsapp_client
    if _twilio_whatsapp_client is None:
        _twilio_whatsapp_client = TwilioWhatsAppClient()
    return _twilio_whatsapp_client
