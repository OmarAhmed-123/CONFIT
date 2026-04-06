"""
CONFIT Backend - Vodafone Egypt SMS Adapter
==========================================
Vodafone Egypt SMS API adapter.
Local Egyptian carrier with good rates for Vodafone numbers.
"""

import hashlib
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from services.integrations.sms.base import (
    BaseSmsAdapter,
    SmsMessage,
    SmsResult,
    SmsStatus,
)
from services.integrations.base import IntegrationError

logger = logging.getLogger(__name__)


class VodafoneSmsAdapter(BaseSmsAdapter):
    """
    Vodafone Egypt SMS provider adapter.
    
    Features:
    - Direct Vodafone Egypt integration
    - Good rates for Vodafone subscribers
    - Arabic support
    
    Configuration:
        VODAFONE_SMS_USERNAME=your-username
        VODAFONE_SMS_PASSWORD=your-password
        VODAFONE_SENDER=CONFIT
    
    Egypt Notes:
    - Best delivery for Vodafone numbers
    - Register sender ID with Vodafone Egypt
    - Supports bulk SMS
    """
    
    PROVIDER = "vodafone_egypt"
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        sender: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 15.0,
    ):
        self.username = username or os.getenv("VODAFONE_SMS_USERNAME")
        self.password = password or os.getenv("VODAFONE_SMS_PASSWORD")
        self.sender = sender or os.getenv("VODAFONE_SENDER", "CONFIT")
        self.base_url = (base_url or os.getenv(
            "VODAFONE_SMS_URL",
            "https://sms.vodafone.com.eg"
        )).rstrip("/")
        self.timeout_seconds = timeout_seconds
        
        if not self.username or not self.password:
            raise IntegrationError(
                "VODAFONE_SMS_USERNAME and VODAFONE_SMS_PASSWORD required",
                provider=self.PROVIDER,
            )
        
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def provider_name(self) -> str:
        return self.PROVIDER
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds),
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _build_auth_params(self) -> Dict[str, str]:
        """Build authentication parameters."""
        # Vodafone Egypt typically uses username/password in request
        return {
            "username": self.username,
            "password": self.password,
            "sender": self.sender,
        }
    
    async def send(self, message: SmsMessage) -> SmsResult:
        """Send single SMS via Vodafone Egypt."""
        url = f"{self.base_url}/api/sms/send"
        
        params = self._build_auth_params()
        params["mobile"] = self.format_phone(message.to).lstrip("+")
        params["message"] = message.body
        params["reference"] = message.reference_id or ""
        
        try:
            response = await self.client.post(url, data=params)
            
            if not response.is_success:
                return SmsResult(
                    success=False,
                    status=SmsStatus.FAILED,
                    error_message=f"HTTP {response.status_code}: {response.text}",
                    provider_response={"raw": response.text},
                )
            
            # Parse response (format varies by provider)
            data = self._parse_response(response.text)
            
            result = SmsResult(
                success=data.get("success", False),
                message_id=data.get("message_id"),
                status=SmsStatus.SENT if data.get("success") else SmsStatus.FAILED,
                error_code=data.get("error_code"),
                error_message=data.get("error_message"),
                segments=message.segment_count,
                provider_response=data,
            )
            
            logger.info(
                f"[vodafone] SMS sent to {message.to} "
                f"(message_id: {result.message_id})"
            )
            
            return result
            
        except httpx.TimeoutException as e:
            raise IntegrationError(
                "Vodafone SMS timeout",
                provider=self.PROVIDER,
                original_error=e,
            )
        except httpx.NetworkError as e:
            raise IntegrationError(
                f"Vodafone network error: {e}",
                provider=self.PROVIDER,
                original_error=e,
            )
    
    async def send_batch(self, messages: List[SmsMessage]) -> List[SmsResult]:
        """Send multiple SMS via Vodafone (may require separate calls)."""
        # Vodafone Egypt may not have true batch API - send individually
        results = []
        for msg in messages:
            try:
                result = await self.send(msg)
                results.append(result)
            except Exception as e:
                results.append(SmsResult(
                    success=False,
                    status=SmsStatus.FAILED,
                    error_message=str(e),
                ))
        return results
    
    async def get_delivery_status(self, message_id: str) -> SmsStatus:
        """Get delivery status from Vodafone."""
        url = f"{self.base_url}/api/sms/status"
        
        params = self._build_auth_params()
        params["message_id"] = message_id
        
        try:
            response = await self.client.get(url, params=params)
            
            if not response.is_success:
                return SmsStatus.PENDING
            
            data = self._parse_response(response.text)
            return self._map_status(data.get("status", ""))
            
        except Exception:
            return SmsStatus.PENDING
    
    async def health_check(self) -> bool:
        """Check Vodafone API connectivity."""
        try:
            # Try to get account balance or similar
            url = f"{self.base_url}/api/account/balance"
            params = self._build_auth_params()
            response = await self.client.get(url, params=params)
            return response.is_success
        except Exception as e:
            logger.error(f"[vodafone] Health check failed: {e}")
            return False
    
    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parse Vodafone response (format varies)."""
        # Try JSON first
        try:
            import json
            return json.loads(text)
        except Exception:
            pass
        
        # Try parsing common formats
        # Format: "OK:message_id" or "ERROR:code:message"
        if ":" in text:
            parts = text.split(":", 2)
            if parts[0].upper() == "OK":
                return {"success": True, "message_id": parts[1] if len(parts) > 1 else None}
            elif parts[0].upper() == "ERROR":
                return {
                    "success": False,
                    "error_code": parts[1] if len(parts) > 1 else "UNKNOWN",
                    "error_message": parts[2] if len(parts) > 2 else parts[1],
                }
        
        return {"success": False, "error_message": text}
    
    def _map_status(self, status: str) -> SmsStatus:
        """Map Vodafone status to SmsStatus."""
        status_map = {
            "delivered": SmsStatus.DELIVERED,
            "sent": SmsStatus.SENT,
            "pending": SmsStatus.PENDING,
            "failed": SmsStatus.FAILED,
            "rejected": SmsStatus.REJECTED,
        }
        return status_map.get(status.lower(), SmsStatus.PENDING)
