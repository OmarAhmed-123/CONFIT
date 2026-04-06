"""
CONFIT Backend - Infobip SMS Adapter
===================================
Infobip SMS provider adapter (RECOMMENDED for Egypt).
Global SMS provider with competitive rates and good Arabic support.
"""

import logging
import os
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


class InfobipSmsAdapter(BaseSmsAdapter):
    """
    Infobip SMS provider adapter.
    
    Features:
    - Global coverage with competitive rates
    - Excellent Arabic/UCS-2 support
    - Delivery reports via webhook
    - Sender ID support (alpha and numeric)
    
    Configuration:
        INFOBIP_API_KEY=your-api-key
        INFOBIP_BASE_URL=https://api.infobip.com
        INFOBIP_SENDER_ID=CONFIT  (or your registered sender)
    
    Egypt Notes:
    - Sender ID registration required for alpha sender
    - Competitive rates for Egypt (~$0.01-0.02/msg)
    - Good delivery rates for Egyptian carriers
    """
    
    PROVIDER = "infobip"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        sender_id: Optional[str] = None,
        timeout_seconds: float = 15.0,
    ):
        self.api_key = api_key or os.getenv("INFOBIP_API_KEY")
        self.base_url = (base_url or os.getenv("INFOBIP_BASE_URL", "https://api.infobip.com")).rstrip("/")
        self.sender_id = sender_id or os.getenv("INFOBIP_SENDER_ID", "CONFIT")
        self.timeout_seconds = timeout_seconds
        
        if not self.api_key:
            raise IntegrationError(
                "INFOBIP_API_KEY required",
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
                headers={
                    "Authorization": f"App {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def send(self, message: SmsMessage) -> SmsResult:
        """
        Send single SMS via Infobip.
        
        Docs: https://www.infobip.com/docs/api#channels/sms/send-sms-message
        """
        url = f"{self.base_url}/sms/2/text/advanced"
        
        # Build request payload
        payload = {
            "messages": [
                {
                    "from": message.sender_id or self.sender_id,
                    "to": self.format_phone(message.to),
                    "text": message.body,
                    "messageId": message.reference_id,
                }
            ]
        }
        
        # Add scheduling if specified
        if message.scheduled_at:
            payload["messages"][0]["sendAt"] = message.scheduled_at.strftime(
                "%Y-%m-%dT%H:%M:%S%z"
            )
        
        try:
            response = await self.client.post(url, json=payload)
            
            if not response.is_success:
                error_data = response.json() if response.content else {}
                raise IntegrationError(
                    f"Infobip SMS failed: {response.status_code}",
                    provider=self.PROVIDER,
                    status_code=response.status_code,
                    response_data=error_data,
                )
            
            data = response.json()
            
            # Parse response
            message_info = data.get("messages", [{}])[0]
            
            result = SmsResult(
                success=message_info.get("status", {}).get("groupId", 0) in (1, 3),  # Pending, Sent
                message_id=message_info.get("messageId"),
                status=self._map_status(message_info.get("status", {}).get("groupId")),
                segments=message_info.get("smsCount", 1),
                cost=float(message_info.get("price", {}).get("pricePerMessage", 0)),
                currency=message_info.get("price", {}).get("currency", "USD"),
                provider_response=data,
            )
            
            logger.info(
                f"[infobip] SMS sent to {message.to} "
                f"(message_id: {result.message_id}, segments: {result.segments})"
            )
            
            return result
            
        except httpx.TimeoutException as e:
            raise IntegrationError(
                "Infobip request timeout",
                provider=self.PROVIDER,
                original_error=e,
            )
        except httpx.NetworkError as e:
            raise IntegrationError(
                f"Infobip network error: {e}",
                provider=self.PROVIDER,
                original_error=e,
            )
    
    async def send_batch(self, messages: List[SmsMessage]) -> List[SmsResult]:
        """Send multiple SMS in single API call."""
        url = f"{self.base_url}/sms/2/text/advanced"
        
        # Build batch payload
        payload = {
            "messages": [
                {
                    "from": msg.sender_id or self.sender_id,
                    "to": self.format_phone(msg.to),
                    "text": msg.body,
                    "messageId": msg.reference_id,
                }
                for msg in messages
            ]
        }
        
        try:
            response = await self.client.post(url, json=payload)
            
            if not response.is_success:
                error_data = response.json() if response.content else {}
                raise IntegrationError(
                    f"Infobip batch SMS failed: {response.status_code}",
                    provider=self.PROVIDER,
                    status_code=response.status_code,
                    response_data=error_data,
                )
            
            data = response.json()
            
            # Map responses to results
            results = []
            for i, msg in enumerate(messages):
                msg_info = data.get("messages", [{}])[i] if i < len(data.get("messages", [])) else {}
                
                results.append(SmsResult(
                    success=msg_info.get("status", {}).get("groupId", 0) in (1, 3),
                    message_id=msg_info.get("messageId"),
                    status=self._map_status(msg_info.get("status", {}).get("groupId")),
                    segments=msg_info.get("smsCount", 1),
                    cost=float(msg_info.get("price", {}).get("pricePerMessage", 0)),
                    currency=msg_info.get("price", {}).get("currency", "USD"),
                    provider_response=msg_info,
                ))
            
            logger.info(
                f"[infobip] Batch SMS sent: {len(results)} messages"
            )
            
            return results
            
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            raise IntegrationError(
                f"Infobip batch error: {e}",
                provider=self.PROVIDER,
                original_error=e,
            )
    
    async def get_delivery_status(self, message_id: str) -> SmsStatus:
        """Get delivery status from Infobip."""
        url = f"{self.base_url}/sms/2/logs?messageId={message_id}"
        
        try:
            response = await self.client.get(url)
            
            if not response.is_success:
                return SmsStatus.PENDING
            
            data = response.json()
            logs = data.get("results", [])
            
            if logs:
                status_group = logs[0].get("status", {}).get("groupId", 0)
                return self._map_status(status_group)
            
            return SmsStatus.PENDING
            
        except Exception:
            return SmsStatus.PENDING
    
    async def health_check(self) -> bool:
        """Check Infobip API connectivity."""
        try:
            url = f"{self.base_url}/sms/1/inbox/reports"
            response = await self.client.get(url)
            return response.is_success or response.status_code == 404  # 404 = no reports, but API OK
        except Exception as e:
            logger.error(f"[infobip] Health check failed: {e}")
            return False
    
    def _map_status(self, group_id: int) -> SmsStatus:
        """Map Infobip status group to SmsStatus."""
        # Infobip status groups:
        # 1 - PENDING
        # 2 - UNDELIVERABLE
        # 3 - DELIVERED
        # 4 - EXPIRED
        # 5 - REJECTED
        mapping = {
            1: SmsStatus.PENDING,
            2: SmsStatus.FAILED,
            3: SmsStatus.DELIVERED,
            4: SmsStatus.FAILED,
            5: SmsStatus.REJECTED,
        }
        return mapping.get(group_id, SmsStatus.PENDING)
