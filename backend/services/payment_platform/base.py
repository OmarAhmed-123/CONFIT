"""
Base integration class for payment providers.
All providers inherit from this to ensure consistent retries, logging, and timeouts.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


class PaymentProviderError(Exception):
    """Base exception for payment provider errors."""
    def __init__(self, message: str, provider: str, code: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message)
        self.provider = provider
        self.code = code
        self.details = details or {}


class BaseIntegration(ABC):
    """
    Abstract base class for payment provider integrations.
    
    Provides:
    - HTTP client with configurable timeout
    - Automatic retries with exponential backoff (3 attempts)
    - Consistent logging
    - Webhook signature verification interface
    """
    
    # Subclasses must define these
    PROVIDER_NAME: str = "base"
    DEFAULT_TIMEOUT: float = 30.0
    MAX_RETRIES: int = 3
    
    def __init__(self, timeout: Optional[float] = None):
        self.timeout = timeout or float(os.getenv("PAYMENT_PROVIDER_TIMEOUT", str(self.DEFAULT_TIMEOUT)))
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        idempotency_key: Optional[str] = None,
    ) -> httpx.Response:
        """
        Make an HTTP request with automatic retries.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL
            headers: Optional headers
            json_data: JSON body
            data: Form data or raw body
            idempotency_key: Optional idempotency key header
            
        Returns:
            httpx.Response
        """
        client = await self._get_client()
        req_headers = headers or {}
        
        # Add idempotency key header if provided
        if idempotency_key:
            # Different providers use different header names
            req_headers["Idempotency-Key"] = idempotency_key
            req_headers["X-Idempotency-Key"] = idempotency_key
        
        logger.debug(
            "[%s] %s %s (idempotency=%s)",
            self.PROVIDER_NAME,
            method,
            url.split("?")[0],  # Log URL without query params
            idempotency_key[:8] + "..." if idempotency_key else None,
        )
        
        response = await client.request(
            method,
            url,
            headers=req_headers,
            json=json_data,
            data=data,
        )
        
        return response
    
    def _mask_sensitive(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mask sensitive fields for logging.
        Never log full card numbers, CVV, or API keys.
        """
        sensitive_keys = {
            "card_number", "cardNumber", "pan", "cvv", "cvc",
            "api_key", "apiKey", "secret", "password", "token",
            "client_secret", "clientSecret",
        }
        masked = {}
        for key, value in data.items():
            if key.lower() in sensitive_keys or any(s in key.lower() for s in ["secret", "key", "password", "token"]):
                if isinstance(value, str) and len(value) > 4:
                    masked[key] = value[:4] + "****"
                else:
                    masked[key] = "****"
            elif isinstance(value, dict):
                masked[key] = self._mask_sensitive(value)
            else:
                masked[key] = value
        return masked
    
    @abstractmethod
    async def create_charge(
        self,
        amount_piastres: int,
        customer: Dict[str, Any],
        order_ref: str,
        payment_method: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a payment charge.
        
        Args:
            amount_piastres: Amount in smallest currency unit (piastres for EGP)
            customer: Customer details (email, phone, name, etc.)
            order_ref: Unique order reference
            payment_method: Payment method identifier
            **kwargs: Provider-specific options
            
        Returns:
            Dict with at least: charge_id, status, redirect_url (if applicable)
        """
        pass
    
    @abstractmethod
    def verify_webhook(self, payload: bytes, signature: str, headers: Optional[Dict[str, str]] = None) -> bool:
        """
        Verify webhook signature BEFORE parsing body.
        
        Args:
            payload: Raw request body bytes
            signature: Signature from webhook header
            headers: Optional additional headers for verification
            
        Returns:
            True if signature is valid
        """
        pass
    
    @abstractmethod
    async def refund(
        self,
        reference_number: str,
        amount_piastres: int,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refund a payment.
        
        Args:
            reference_number: Provider's transaction reference
            amount_piastres: Amount to refund in piastres
            reason: Optional refund reason
            
        Returns:
            Dict with refund details
        """
        pass
    
    @abstractmethod
    async def get_charge_status(self, charge_id: str) -> Dict[str, Any]:
        """
        Get current status of a charge.
        
        Args:
            charge_id: Provider's charge ID
            
        Returns:
            Dict with status and details
        """
        pass


def egp_to_piastres(egp: float) -> int:
    """Convert EGP to piastres (multiply by 100)."""
    return int(round(egp * 100))


def piastres_to_egp(piastres: int) -> float:
    """Convert piastres to EGP (divide by 100)."""
    return piastres / 100.0
