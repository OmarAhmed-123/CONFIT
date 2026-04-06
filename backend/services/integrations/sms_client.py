"""
CONFIT Backend - SMS Client
===========================
Provider-agnostic SMS client with adapter pattern.
Picks adapter based on SMS_PROVIDER environment variable.
"""

import logging
import os
from enum import Enum
from typing import Any, Dict, List, Optional

from services.integrations.sms.base import (
    BaseSmsAdapter,
    SmsMessage,
    SmsResult,
    SmsStatus,
)
from services.integrations.sms.infobip_adapter import InfobipSmsAdapter
from services.integrations.sms.vodafone_adapter import VodafoneSmsAdapter
from services.integrations.sms.victorylink_adapter import VictoryLinkSmsAdapter
from services.integrations.base import IntegrationError

logger = logging.getLogger(__name__)


class SmsProvider(str, Enum):
    """Supported SMS providers."""
    INFOBIP = "infobip"
    VODAFONE = "vodafone"
    VICTORYLINK = "victorylink"


class SmsClient:
    """
    Provider-agnostic SMS client.
    
    Routes SMS through configured provider adapter.
    Supports multiple Egyptian SMS providers with automatic fallback.
    
    Configuration:
        SMS_PROVIDER=infobip  (or vodafone, victorylink)
        
    Provider-specific config:
        Infobip: INFOBIP_API_KEY, INFOBIP_BASE_URL, INFOBIP_SENDER_ID
        Vodafone: VODAFONE_SMS_USERNAME, VODAFONE_SMS_PASSWORD, VODAFONE_SENDER
        VictoryLink: VICTORYLINK_API_KEY, VICTORYLINK_SENDER_ID
    
    Usage:
        client = get_sms_client()
        result = await client.send_otp("+201234567890", "123456")
    
    Egypt Notes:
        - DO NOT use Twilio for SMS (10x more expensive)
        - Infobip recommended for reliability
        - VictoryLink good for OTP (cheapest)
        - Vodafone good for Vodafone subscribers
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        fallback_providers: Optional[List[str]] = None,
    ):
        """
        Initialize SMS client with provider.
        
        Args:
            provider: Primary SMS provider (from SMS_PROVIDER env if not set)
            fallback_providers: List of fallback providers if primary fails
        """
        self.provider_name = provider or os.getenv("SMS_PROVIDER", "infobip").lower()
        self.fallback_providers = fallback_providers or []
        
        self._adapter: Optional[BaseSmsAdapter] = None
        self._fallback_adapters: List[BaseSmsAdapter] = []
    
    @property
    def adapter(self) -> BaseSmsAdapter:
        """Get primary SMS adapter lazily."""
        if self._adapter is None:
            self._adapter = self._create_adapter(self.provider_name)
        return self._adapter
    
    def _create_adapter(self, provider: str) -> BaseSmsAdapter:
        """Create adapter for specified provider."""
        provider_lower = provider.lower()
        
        if provider_lower == SmsProvider.INFOBIP.value:
            return InfobipSmsAdapter()
        elif provider_lower == SmsProvider.VODAFONE.value:
            return VodafoneSmsAdapter()
        elif provider_lower == SmsProvider.VICTORYLINK.value:
            return VictoryLinkSmsAdapter()
        else:
            raise IntegrationError(
                f"Unknown SMS provider: {provider}. "
                f"Supported: {[p.value for p in SmsProvider]}",
                provider="sms_client",
            )
    
    def _get_fallback_adapters(self) -> List[BaseSmsAdapter]:
        """Get fallback adapters lazily."""
        if not self._fallback_adapters and self.fallback_providers:
            for provider in self.fallback_providers:
                try:
                    self._fallback_adapters.append(self._create_adapter(provider))
                except Exception as e:
                    logger.warning(f"Failed to create fallback adapter {provider}: {e}")
        return self._fallback_adapters
    
    async def send(
        self,
        to: str,
        body: str,
        sender_id: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> SmsResult:
        """
        Send SMS message.
        
        Args:
            to: Recipient phone number
            body: Message body (supports Arabic)
            sender_id: Optional sender ID override
            reference_id: Optional reference ID for tracking
            
        Returns:
            SmsResult with delivery status
        """
        message = SmsMessage(
            to=to,
            body=body,
            sender_id=sender_id,
            reference_id=reference_id,
        )
        
        # Try primary adapter
        try:
            result = await self.adapter.send(message)
            if result.success:
                return result
        except Exception as e:
            logger.error(f"[sms] Primary provider {self.provider_name} failed: {e}")
            result = SmsResult(
                success=False,
                status=SmsStatus.FAILED,
                error_message=str(e),
            )
        
        # Try fallback adapters
        for fallback_adapter in self._get_fallback_adapters():
            try:
                logger.info(f"[sms] Trying fallback provider: {fallback_adapter.provider_name}")
                fallback_result = await fallback_adapter.send(message)
                if fallback_result.success:
                    logger.info(
                        f"[sms] Fallback provider {fallback_adapter.provider_name} succeeded"
                    )
                    return fallback_result
            except Exception as e:
                logger.error(f"[sms] Fallback {fallback_adapter.provider_name} failed: {e}")
        
        return result
    
    async def send_otp(
        self,
        to: str,
        otp_code: str,
        expiry_minutes: int = 5,
        language: str = "en",
    ) -> SmsResult:
        """
        Send OTP message (optimized for Egypt).
        
        Args:
            to: Recipient phone number
            otp_code: OTP code to send
            expiry_minutes: OTP expiry in minutes
            language: Message language ("en" or "ar")
            
        Returns:
            SmsResult with delivery status
        """
        if language == "ar":
            body = f"CONFIT: {otp_code} - {expiry_minutes} {expiry_minutes == 1 and 'minute' or 'minutes'}"
        else:
            body = f"Your CONFIT verification code is {otp_code}. Valid for {expiry_minutes} minutes."
        
        return await self.send(
            to=to,
            body=body,
            reference_id=f"otp-{otp_code}",
        )
    
    async def send_order_code(
        self,
        to: str,
        order_number: str,
        pickup_code: str,
        language: str = "en",
    ) -> SmsResult:
        """
        Send order pickup code.
        
        Args:
            to: Recipient phone number
            order_number: Order number
            pickup_code: Pickup verification code
            language: Message language
            
        Returns:
            SmsResult
        """
        if language == "ar":
            body = f"CONFIT: Order {order_number} - Pickup code: {pickup_code}"
        else:
            body = f"CONFIT Order {order_number}: Your pickup code is {pickup_code}"
        
        return await self.send(
            to=to,
            body=body,
            reference_id=f"order-{order_number}",
        )
    
    async def send_delivery_alert(
        self,
        to: str,
        order_number: str,
        status: str,
        tracking_url: Optional[str] = None,
        language: str = "en",
    ) -> SmsResult:
        """
        Send delivery status alert.
        
        Args:
            to: Recipient phone number
            order_number: Order number
            status: Delivery status message
            tracking_url: Optional tracking URL
            language: Message language
            
        Returns:
            SmsResult
        """
        if language == "ar":
            body = f"CONFIT: Order {order_number} - {status}"
        else:
            body = f"CONFIT Order {order_number}: {status}"
        
        if tracking_url:
            body += f" Track: {tracking_url}"
        
        return await self.send(
            to=to,
            body=body,
            reference_id=f"delivery-{order_number}",
        )
    
    async def send_batch(
        self,
        messages: List[Dict[str, str]],
    ) -> List[SmsResult]:
        """
        Send multiple SMS messages.
        
        Args:
            messages: List of {"to": "...", "body": "..."}
            
        Returns:
            List of SmsResult for each message
        """
        sms_messages = [
            SmsMessage(
                to=msg["to"],
                body=msg["body"],
                sender_id=msg.get("sender_id"),
                reference_id=msg.get("reference_id"),
            )
            for msg in messages
        ]
        
        return await self.adapter.send_batch(sms_messages)
    
    async def get_delivery_status(self, message_id: str) -> SmsStatus:
        """Get delivery status for a sent message."""
        return await self.adapter.get_delivery_status(message_id)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of primary and fallback providers.
        
        Returns:
            Dict with health status for each provider
        """
        results = {}
        
        # Check primary
        try:
            results[self.provider_name] = await self.adapter.health_check()
        except Exception as e:
            results[self.provider_name] = {"healthy": False, "error": str(e)}
        
        # Check fallbacks
        for adapter in self._get_fallback_adapters():
            try:
                results[adapter.provider_name] = await adapter.health_check()
            except Exception as e:
                results[adapter.provider_name] = {"healthy": False, "error": str(e)}
        
        return results
    
    async def close(self) -> None:
        """Close all adapter connections."""
        if self._adapter:
            await self._adapter.close()
        for adapter in self._fallback_adapters:
            await adapter.close()


# Singleton instance
_sms_client: Optional[SmsClient] = None


def get_sms_client() -> SmsClient:
    """Get SMS client singleton."""
    global _sms_client
    if _sms_client is None:
        _sms_client = SmsClient()
    return _sms_client
