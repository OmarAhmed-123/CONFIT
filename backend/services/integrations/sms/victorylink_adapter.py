"""
CONFIT Backend - VictoryLink SMS Adapter
======================================
VictoryLink Egypt local SMS provider adapter.
Good for OTP and transactional SMS in Egypt.
"""

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


class VictoryLinkSmsAdapter(BaseSmsAdapter):
    """
    VictoryLink Egypt SMS provider adapter.
    
    VictoryLink is a local Egyptian SMS provider with good rates
    for OTP and transactional messages.
    
    Features:
    - Local Egyptian provider
    - Good rates for OTP (~$0.005/msg)
    - Arabic support
    - Fast delivery within Egypt
    
    Configuration:
        VICTORYLINK_API_KEY=your-api-key
        VICTORYLINK_SENDER_ID=CONFIT
        VICTORYLINK_BASE_URL=https://api.victorylink.com
    
    Egypt Notes:
    - Excellent for OTP delivery
    - Good coverage for all Egyptian carriers
    - Competitive local rates
    """
    
    PROVIDER = "victorylink"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        sender_id: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 15.0,
    ):
        self.api_key = api_key or os.getenv("VICTORYLINK_API_KEY")
        self.sender_id = sender_id or os.getenv("VICTORYLINK_SENDER_ID", "CONFIT")
        self.base_url = (base_url or os.getenv(
            "VICTORYLINK_BASE_URL",
            "https://api.victorylink.com"
        )).rstrip("/")
        self.timeout_seconds = timeout_seconds
        
        if not self.api_key:
            raise IntegrationError(
                "VICTORYLINK_API_KEY required",
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
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
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
        Send single SMS via VictoryLink.
        
        VictoryLink API format (typical):
        POST /sms/send
        {
            "to": "201234567890",
            "message": "Your OTP is 123456",
            "sender": "CONFIT"
        }
        """
        url = f"{self.base_url}/sms/send"
        
        payload = {
            "to": self.format_phone(message.to).lstrip("+"),
            "message": message.body,
            "sender": message.sender_id or self.sender_id,
        }
        
        if message.reference_id:
            payload["reference"] = message.reference_id
        
        try:
            response = await self.client.post(url, json=payload)
            
            if not response.is_success:
                error_data = {}
                try:
                    error_data = response.json()
                except Exception:
                    error_data = {"raw": response.text}
                
                return SmsResult(
                    success=False,
                    status=SmsStatus.FAILED,
                    error_code=str(response.status_code),
                    error_message=error_data.get("message", str(error_data)),
                    provider_response=error_data,
                )
            
            data = response.json()
            
            result = SmsResult(
                success=data.get("success", True),
                message_id=data.get("messageId") or data.get("id"),
                status=SmsStatus.SENT if data.get("success", True) else SmsStatus.FAILED,
                segments=message.segment_count,
                cost=float(data.get("cost", 0)),
                currency="EGP",  # VictoryLink typically bills in EGP
                provider_response=data,
            )
            
            logger.info(
                f"[victorylink] SMS sent to {message.to} "
                f"(message_id: {result.message_id}, cost: {result.cost} EGP)"
            )
            
            return result
            
        except httpx.TimeoutException as e:
            raise IntegrationError(
                "VictoryLink SMS timeout",
                provider=self.PROVIDER,
                original_error=e,
            )
        except httpx.NetworkError as e:
            raise IntegrationError(
                f"VictoryLink network error: {e}",
                provider=self.PROVIDER,
                original_error=e,
            )
    
    async def send_batch(self, messages: List[SmsMessage]) -> List[SmsResult]:
        """Send multiple SMS via VictoryLink."""
        url = f"{self.base_url}/sms/bulk"
        
        payload = {
            "messages": [
                {
                    "to": self.format_phone(msg.to).lstrip("+"),
                    "message": msg.body,
                    "sender": msg.sender_id or self.sender_id,
                    "reference": msg.reference_id,
                }
                for msg in messages
            ]
        }
        
        try:
            response = await self.client.post(url, json=payload)
            
            if not response.is_success:
                # Fall back to individual sends
                logger.warning(
                    f"[victorylink] Batch failed, falling back to individual sends"
                )
                return [await self.send(msg) for msg in messages]
            
            data = response.json()
            results_data = data.get("results", [])
            
            results = []
            for i, msg in enumerate(messages):
                msg_data = results_data[i] if i < len(results_data) else {}
                
                results.append(SmsResult(
                    success=msg_data.get("success", True),
                    message_id=msg_data.get("messageId"),
                    status=SmsStatus.SENT if msg_data.get("success", True) else SmsStatus.FAILED,
                    segments=msg.segment_count,
                    cost=float(msg_data.get("cost", 0)),
                    currency="EGP",
                    provider_response=msg_data,
                ))
            
            return results
            
        except Exception as e:
            # Fall back to individual sends
            logger.warning(f"[victorylink] Batch error, using fallback: {e}")
            return [await self.send(msg) for msg in messages]
    
    async def get_delivery_status(self, message_id: str) -> SmsStatus:
        """Get delivery status from VictoryLink."""
        url = f"{self.base_url}/sms/status/{message_id}"
        
        try:
            response = await self.client.get(url)
            
            if not response.is_success:
                return SmsStatus.PENDING
            
            data = response.json()
            return self._map_status(data.get("status", ""))
            
        except Exception:
            return SmsStatus.PENDING
    
    async def health_check(self) -> bool:
        """Check VictoryLink API connectivity."""
        try:
            url = f"{self.base_url}/account/balance"
            response = await self.client.get(url)
            return response.is_success
        except Exception as e:
            logger.error(f"[victorylink] Health check failed: {e}")
            return False
    
    async def get_balance(self) -> Dict[str, Any]:
        """Get account balance (VictoryLink specific)."""
        url = f"{self.base_url}/account/balance"
        
        try:
            response = await self.client.get(url)
            
            if response.is_success:
                data = response.json()
                return {
                    "balance": data.get("balance", 0),
                    "currency": data.get("currency", "EGP"),
                }
            
            return {"balance": None, "error": "Failed to fetch balance"}
            
        except Exception as e:
            return {"balance": None, "error": str(e)}
    
    def _map_status(self, status: str) -> SmsStatus:
        """Map VictoryLink status to SmsStatus."""
        status_map = {
            "delivered": SmsStatus.DELIVERED,
            "sent": SmsStatus.SENT,
            "pending": SmsStatus.PENDING,
            "queued": SmsStatus.PENDING,
            "failed": SmsStatus.FAILED,
            "rejected": SmsStatus.REJECTED,
            "undelivered": SmsStatus.FAILED,
        }
        return status_map.get(status.lower(), SmsStatus.PENDING)
