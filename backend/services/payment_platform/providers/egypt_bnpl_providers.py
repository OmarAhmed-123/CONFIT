"""
Egypt BNPL Provider Stubs - Aman, Contact, Sympl.

These are stub implementations for Egypt's alternative BNPL providers.
Currently Valu is the primary BNPL via Paymob integration.

Providers:
  - Aman: https://amanpay.com/ (installments up to 12 months)
  - Contact: https://contactpay.com.eg/ (installments up to 24 months)
  - Sympl: https://sympl.ai/ (interest-free installments)

Status: Interface only - not yet integrated.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from services.payment_platform.base import (
    BaseIntegration,
    PaymentProviderError,
)

logger = logging.getLogger(__name__)


class AmanProvider(BaseIntegration):
    """
    Aman BNPL Provider - Stub implementation.
    
    Aman offers installment payments up to 12 months.
    Requires separate merchant agreement with Aman.
    
    Status: NOT INTEGRATED - Interface only
    """
    
    PROVIDER_NAME = "aman"
    
    async def create_charge(
        self,
        amount_piastres: int,
        customer: Dict[str, Any],
        order_ref: str,
        payment_method: str = "aman",
        **kwargs,
    ) -> Dict[str, Any]:
        raise PaymentProviderError(
            "Aman BNPL not yet integrated. Contact support to enable.",
            provider="aman",
            code="NOT_INTEGRATED",
        )
    
    def verify_webhook(self, payload: bytes, signature: str, headers: Optional[Dict[str, str]] = None) -> bool:
        logger.warning("Aman webhook verification called but provider not integrated")
        return False
    
    async def refund(
        self,
        reference_number: str,
        amount_piastres: int,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise PaymentProviderError(
            "Aman BNPL not yet integrated",
            provider="aman",
            code="NOT_INTEGRATED",
        )
    
    async def get_charge_status(self, charge_id: str) -> Dict[str, Any]:
        raise PaymentProviderError(
            "Aman BNPL not yet integrated",
            provider="aman",
            code="NOT_INTEGRATED",
        )


class ContactProvider(BaseIntegration):
    """
    Contact Pay BNPL Provider - Stub implementation.
    
    Contact offers installments up to 24 months.
    Popular for electronics and appliances.
    
    Status: NOT INTEGRATED - Interface only
    """
    
    PROVIDER_NAME = "contact"
    
    async def create_charge(
        self,
        amount_piastres: int,
        customer: Dict[str, Any],
        order_ref: str,
        payment_method: str = "contact",
        **kwargs,
    ) -> Dict[str, Any]:
        raise PaymentProviderError(
            "Contact BNPL not yet integrated. Contact support to enable.",
            provider="contact",
            code="NOT_INTEGRATED",
        )
    
    def verify_webhook(self, payload: bytes, signature: str, headers: Optional[Dict[str, str]] = None) -> bool:
        logger.warning("Contact webhook verification called but provider not integrated")
        return False
    
    async def refund(
        self,
        reference_number: str,
        amount_piastres: int,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise PaymentProviderError(
            "Contact BNPL not yet integrated",
            provider="contact",
            code="NOT_INTEGRATED",
        )
    
    async def get_charge_status(self, charge_id: str) -> Dict[str, Any]:
        raise PaymentProviderError(
            "Contact BNPL not yet integrated",
            provider="contact",
            code="NOT_INTEGRATED",
        )


class SymplProvider(BaseIntegration):
    """
    Sympl BNPL Provider - Stub implementation.
    
    Sympl offers interest-free installments (3-4 payments).
    Partners with major Egyptian retailers.
    
    Status: NOT INTEGRATED - Interface only
    """
    
    PROVIDER_NAME = "sympl"
    
    # Sympl typically offers 3 or 4 interest-free installments
    SUPPORTED_INSTALLMENTS = [3, 4]
    
    async def create_charge(
        self,
        amount_piastres: int,
        customer: Dict[str, Any],
        order_ref: str,
        payment_method: str = "sympl",
        installments: int = 4,
        **kwargs,
    ) -> Dict[str, Any]:
        raise PaymentProviderError(
            "Sympl BNPL not yet integrated. Contact support to enable.",
            provider="sympl",
            code="NOT_INTEGRATED",
        )
    
    def verify_webhook(self, payload: bytes, signature: str, headers: Optional[Dict[str, str]] = None) -> bool:
        logger.warning("Sympl webhook verification called but provider not integrated")
        return False
    
    async def refund(
        self,
        reference_number: str,
        amount_piastres: int,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise PaymentProviderError(
            "Sympl BNPL not yet integrated",
            provider="sympl",
            code="NOT_INTEGRATED",
        )
    
    async def get_charge_status(self, charge_id: str) -> Dict[str, Any]:
        raise PaymentProviderError(
            "Sympl BNPL not yet integrated",
            provider="sympl",
            code="NOT_INTEGRATED",
        )


# Provider registry for Egypt BNPL
EGYPT_BNPL_PROVIDERS = {
    "valu": None,  # Valu is implemented in valu_provider.py
    "aman": AmanProvider,
    "contact": ContactProvider,
    "sympl": SymplProvider,
}


def get_bnpl_provider(name: str) -> Optional[BaseIntegration]:
    """
    Get a BNPL provider instance by name.
    
    Args:
        name: Provider name (valu, aman, contact, sympl)
        
    Returns:
        Provider instance or None if not found
    """
    if name == "valu":
        from services.payment_platform.providers.valu_provider import ValuProvider
        return ValuProvider()
    
    provider_class = EGYPT_BNPL_PROVIDERS.get(name)
    if provider_class:
        return provider_class()
    
    return None


def list_available_bnpl_providers() -> List[Dict[str, Any]]:
    """List all Egypt BNPL providers with their status."""
    return [
        {
            "name": "valu",
            "display_name": "Valu",
            "status": "available",
            "tenors": [6, 9, 12, 18, 24],
            "description": "Egypt's leading BNPL with flexible installments",
        },
        {
            "name": "aman",
            "display_name": "Aman",
            "status": "not_integrated",
            "tenors": [3, 6, 9, 12],
            "description": "Installments up to 12 months",
        },
        {
            "name": "contact",
            "display_name": "Contact Pay",
            "status": "not_integrated",
            "tenors": [3, 6, 9, 12, 18, 24],
            "description": "Installments up to 24 months",
        },
        {
            "name": "sympl",
            "display_name": "Sympl",
            "status": "not_integrated",
            "tenors": [3, 4],
            "description": "Interest-free split payments",
        },
    ]
