"""
Fawry Payment Provider - Egypt's leading payment gateway.

Supports:
  - CARD: Credit/Debit cards
  - CASH_ON_DELIVERY: Pay when order arrives (40%+ of Egypt e-commerce)
  - WALLET: Mobile wallets (Vodafone Cash, Orange Money, etc.)
  - FAWRY_REF_NUMBER: Pay at Fawry kiosks/ATMs

Docs: https://developer.fawrystaging.com/docs

Required env:
  FAWRY_ENVIRONMENT=staging  # staging | production
  FAWRY_MERCHANT_CODE=your-merchant-code
  FAWRY_SECURITY_KEY=your-security-key
  FAWRY_CALLBACK_URL=https://api.confit.app/webhooks/fawry

Currency:
  All amounts in PIASTRES (EGP * 100).
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Any, Dict, Literal, Optional

import httpx

from services.payment_platform.base import (
    BaseIntegration,
    PaymentProviderError,
    egp_to_piastres,
    piastres_to_egp,
)

logger = logging.getLogger(__name__)

PaymentMethodFawry = Literal["CARD", "CASH_ON_DELIVERY", "WALLET", "FAWRY_REF_NUMBER"]


class FawryProvider(BaseIntegration):
    """
    Fawry payment integration for Egypt.
    
    Features:
      - Card payments with 3DS
      - Cash on Delivery (COD)
      - Mobile wallet payments
      - Fawry reference number (pay at kiosks/ATMs)
    
    Webhook signature uses MD5 hash of concatenated fields.
    """
    
    PROVIDER_NAME = "fawry"
    DEFAULT_TIMEOUT = 30.0
    
    # Fawry API endpoints
    STAGING_URL = "https://www.fawrystaging.com/fawrypay-api"
    PRODUCTION_URL = "https://www.fawry.com/fawrypay-api"
    
    def __init__(self, timeout: Optional[float] = None):
        super().__init__(timeout)
        self.merchant_code = os.getenv("FAWRY_MERCHANT_CODE", "").strip()
        self.security_key = os.getenv("FAWRY_SECURITY_KEY", "").strip()
        self.callback_url = os.getenv("FAWRY_CALLBACK_URL", "").strip()
        self.environment = os.getenv("FAWRY_ENVIRONMENT", "staging").lower()
        
        if not self.merchant_code or not self.security_key:
            logger.warning("FAWRY_MERCHANT_CODE or FAWRY_SECURITY_KEY not set")
    
    def _base_url(self) -> str:
        """Get API base URL based on environment."""
        if self.environment == "production":
            return self.PRODUCTION_URL
        return self.STAGING_URL
    
    def _build_signature(self, *parts: str) -> str:
        """
        Build Fawry MD5 signature.
        
        Fawry signature format: MD5(merchantCode + ...fields... + securityKey)
        """
        concat = "".join(str(p) for p in parts) + self.security_key
        return hashlib.md5(concat.encode("utf-8")).hexdigest()
    
    def _build_webhook_signature(
        self,
        merchant_code: str,
        reference_number: str,
        payment_method: str,
        amount: str,
        status: str,
    ) -> str:
        """
        Build signature for webhook verification.
        
        Format: MD5(merchantCode + referenceNumber + paymentMethod + amount + status + securityKey)
        """
        concat = f"{merchant_code}{reference_number}{payment_method}{amount}{status}{self.security_key}"
        return hashlib.md5(concat.encode("utf-8")).hexdigest()
    
    async def create_charge(
        self,
        amount_piastres: int,
        customer: Dict[str, Any],
        order_ref: str,
        payment_method: PaymentMethodFawry = "CARD",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a Fawry payment charge.
        
        Args:
            amount_piastres: Amount in piastres (EGP * 100)
            customer: Customer details (email, phone, name)
            order_ref: Unique order reference (merchantRefNumber)
            payment_method: One of CARD, CASH_ON_DELIVERY, WALLET, FAWRY_REF_NUMBER
            
        Returns:
            Dict with charge_id, status, reference_number, redirect_url (if CARD)
        """
        if not self.merchant_code or not self.security_key:
            raise PaymentProviderError(
                "Fawry credentials not configured",
                provider="fawry",
            )
        
        # Fawry expects amount in EGP (not piastres)
        amount_egp = piastres_to_egp(amount_piastres)
        
        # Build signature: merchantCode + merchantRefNumber + amount + securityKey
        signature = self._build_signature(
            self.merchant_code,
            order_ref,
            f"{amount_egp:.2f}",
        )
        
        payload = {
            "merchantCode": self.merchant_code,
            "merchantRefNum": order_ref,
            "customerMobile": customer.get("phone", ""),
            "customerEmail": customer.get("email", ""),
            "customerName": customer.get("name", customer.get("first_name", "Customer")),
            "paymentMethod": payment_method,
            "amount": f"{amount_egp:.2f}",
            "currencyCode": "EGP",
            "signature": signature,
            "description": kwargs.get("description", f"CONFIT Order {order_ref}"),
            "chargeItems": kwargs.get("items", []),
        }
        
        # Add callback URL for webhooks
        if self.callback_url:
            payload["callbackUrl"] = self.callback_url
        
        # For CARD payments, include card details (handled by frontend iframe)
        if payment_method == "CARD":
            # Card token from frontend
            if "card_token" in kwargs:
                payload["cardToken"] = kwargs["card_token"]
        
        # For WALLET payments, include wallet number
        if payment_method == "WALLET":
            payload["walletNumber"] = kwargs.get("wallet_number", "")
        
        # For COD, include delivery address
        if payment_method == "CASH_ON_DELIVERY":
            payload["deliveryAddress"] = kwargs.get("delivery_address", {})
        
        url = f"{self._base_url()}/payments/charge"
        
        try:
            client = await self._get_client()
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise PaymentProviderError(
                f"Fawry charge failed: HTTP {e.response.status_code}",
                provider="fawry",
                details={"response": e.response.text},
            ) from e
        except Exception as e:
            raise PaymentProviderError(
                f"Fawry charge failed: {e}",
                provider="fawry",
            ) from e
        
        # Parse response
        status = data.get("statusCode", "")
        reference_number = data.get("referenceNumber", "")
        
        result = {
            "charge_id": reference_number or order_ref,
            "status": self._map_status(status),
            "reference_number": reference_number,
            "merchant_ref": order_ref,
            "provider": "fawry",
            "payment_method": payment_method,
            "raw_response": data,
        }
        
        # For CARD payments, include redirect URL for 3DS
        if payment_method == "CARD" and "redirectUrl" in data:
            result["redirect_url"] = data["redirectUrl"]
        
        # For FAWRY_REF_NUMBER, include the reference to display to customer
        if payment_method == "FAWRY_REF_NUMBER" and reference_number:
            result["fawry_reference"] = reference_number
            result["instructions"] = f"Pay at any Fawry kiosk or ATM using reference: {reference_number}"
        
        return result
    
    def verify_webhook(self, payload: bytes, signature: str, headers: Optional[Dict[str, str]] = None) -> bool:
        """
        Verify Fawry webhook signature.
        
        Fawry sends signature in the request body or header.
        Format: MD5(merchantCode + referenceNumber + paymentMethod + amount + status + securityKey)
        """
        import json
        
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            logger.error("Fawry webhook: invalid JSON payload")
            return False
        
        # Extract required fields
        merchant_code = data.get("merchantCode", "")
        reference_number = data.get("referenceNumber", "")
        payment_method = data.get("paymentMethod", "")
        amount = data.get("amount", "")
        status = data.get("statusCode", data.get("status", ""))
        
        # Build expected signature
        expected = self._build_webhook_signature(
            merchant_code,
            reference_number,
            payment_method,
            str(amount),
            status,
        )
        
        # Compare signatures (case-insensitive for MD5 hex)
        return signature.lower() == expected.lower()
    
    async def refund(
        self,
        reference_number: str,
        amount_piastres: int,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refund a Fawry transaction.
        
        Args:
            reference_number: Fawry reference number
            amount_piastres: Amount to refund in piastres
            reason: Optional refund reason
            
        Returns:
            Dict with refund details
        """
        if not self.merchant_code or not self.security_key:
            raise PaymentProviderError(
                "Fawry credentials not configured",
                provider="fawry",
            )
        
        amount_egp = piastres_to_egp(amount_piastres)
        
        # Build refund signature
        signature = self._build_signature(
            self.merchant_code,
            reference_number,
            f"{amount_egp:.2f}",
        )
        
        payload = {
            "merchantCode": self.merchant_code,
            "referenceNumber": reference_number,
            "refundAmount": f"{amount_egp:.2f}",
            "reason": reason or "Customer request",
            "signature": signature,
        }
        
        url = f"{self._base_url()}/payments/refund"
        
        try:
            client = await self._get_client()
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise PaymentProviderError(
                f"Fawry refund failed: HTTP {e.response.status_code}",
                provider="fawry",
                details={"response": e.response.text},
            ) from e
        except Exception as e:
            raise PaymentProviderError(
                f"Fawry refund failed: {e}",
                provider="fawry",
            ) from e
        
        return {
            "refund_id": data.get("refundId"),
            "reference_number": reference_number,
            "amount_refunded": amount_egp,
            "status": data.get("statusCode"),
            "provider": "fawry",
            "raw_response": data,
        }
    
    async def get_charge_status(self, charge_id: str) -> Dict[str, Any]:
        """
        Get the status of a Fawry charge.
        
        Args:
            charge_id: Fawry reference number or merchant ref number
            
        Returns:
            Dict with status and details
        """
        if not self.merchant_code or not self.security_key:
            raise PaymentProviderError(
                "Fawry credentials not configured",
                provider="fawry",
            )
        
        # Build status check signature
        signature = self._build_signature(self.merchant_code, charge_id)
        
        url = f"{self._base_url()}/payments/status"
        params = {
            "merchantCode": self.merchant_code,
            "merchantRefNumber": charge_id,
            "signature": signature,
        }
        
        try:
            client = await self._get_client()
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise PaymentProviderError(
                f"Fawry status check failed: HTTP {e.response.status_code}",
                provider="fawry",
                details={"response": e.response.text},
            ) from e
        except Exception as e:
            raise PaymentProviderError(
                f"Fawry status check failed: {e}",
                provider="fawry",
            ) from e
        
        return {
            "charge_id": data.get("referenceNumber"),
            "merchant_ref": data.get("merchantRefNumber"),
            "status": self._map_status(data.get("statusCode", "")),
            "amount": data.get("amount"),
            "payment_method": data.get("paymentMethod"),
            "provider": "fawry",
            "raw_response": data,
        }
    
    def _map_status(self, fawry_status: str) -> str:
        """Map Fawry status codes to standard status."""
        status_map = {
            "UNPAID": "pending",
            "PAID": "succeeded",
            "FAILED": "failed",
            "EXPIRED": "expired",
            "REFUNDED": "refunded",
            "PARTIALLY_REFUNDED": "partially_refunded",
            "CANCELED": "canceled",
            "NEW": "pending",
            "PROCESSING": "processing",
            "SUCCESS": "succeeded",
            "DECLINED": "failed",
        }
        return status_map.get(fawry_status.upper(), "unknown")


# Module-level singleton for convenience
_provider = FawryProvider()


async def create_charge(
    amount_piastres: int,
    customer: Dict[str, Any],
    order_ref: str,
    payment_method: PaymentMethodFawry = "CARD",
    **kwargs,
) -> Dict[str, Any]:
    """Create Fawry charge (convenience function)."""
    return await _provider.create_charge(
        amount_piastres=amount_piastres,
        customer=customer,
        order_ref=order_ref,
        payment_method=payment_method,
        **kwargs,
    )


def verify_webhook(payload: bytes, signature: str, headers: Optional[Dict[str, str]] = None) -> bool:
    """Verify Fawry webhook (convenience function)."""
    return _provider.verify_webhook(payload, signature, headers)


async def refund(
    reference_number: str,
    amount_piastres: int,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Refund Fawry transaction (convenience function)."""
    return await _provider.refund(
        reference_number=reference_number,
        amount_piastres=amount_piastres,
        reason=reason,
    )


async def get_charge_status(charge_id: str) -> Dict[str, Any]:
    """Get Fawry charge status (convenience function)."""
    return await _provider.get_charge_status(charge_id)
