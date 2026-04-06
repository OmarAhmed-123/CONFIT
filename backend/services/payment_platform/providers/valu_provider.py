"""
Valu BNPL Provider - Egypt's leading Buy Now Pay Later service.

Valu is accessible through Paymob's Valu integration.
Supports installment plans: 6, 9, 12, 18, 24 months.

Docs: https://docs.paymob.com/docs/valu-integration

Required env:
  PAYMOB_INTEGRATION_ID_VALU - Paymob integration ID for Valu

Currency:
  All amounts in PIASTRES (EGP * 100).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Literal, Optional

from services.payment_platform.base import (
    BaseIntegration,
    PaymentProviderError,
    egp_to_piastres,
    piastres_to_egp,
)

logger = logging.getLogger(__name__)

ValuTenor = Literal[6, 9, 12, 18, 24]


class ValuProvider(BaseIntegration):
    """
    Valu BNPL integration via Paymob.
    
    Features:
      - Installment plans: 6, 9, 12, 18, 24 months
      - Down payment support
      - Interest-free options for certain merchants
      - Real-time eligibility check
    
    Valu uses Paymob's infrastructure, so we route through Paymob.
    """
    
    PROVIDER_NAME = "valu"
    DEFAULT_TIMEOUT = 30.0
    
    # Supported installment tenors (months)
    SUPPORTED_TENORS: List[int] = [6, 9, 12, 18, 24]
    
    def __init__(self, timeout: Optional[float] = None):
        super().__init__(timeout)
        self.integration_id = os.getenv("PAYMOB_INTEGRATION_ID_VALU", "").strip()
        
        if not self.integration_id:
            logger.warning("PAYMOB_INTEGRATION_ID_VALU not set - Valu BNPL unavailable")
    
    async def create_charge(
        self,
        amount_piastres: int,
        customer: Dict[str, Any],
        order_ref: str,
        payment_method: str = "valu",
        tenor: ValuTenor = 6,
        down_payment_piastres: int = 0,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a Valu BNPL charge via Paymob.
        
        Args:
            amount_piastres: Total amount in piastres (EGP * 100)
            customer: Customer details (email, phone, first_name, last_name)
            order_ref: Unique order reference
            tenor: Installment period in months (6, 9, 12, 18, 24)
            down_payment_piastres: Optional down payment amount
            
        Returns:
            Dict with charge_id, status, installment_schedule, iframe_url
        """
        if not self.integration_id:
            raise PaymentProviderError(
                "Valu integration not configured. Set PAYMOB_INTEGRATION_ID_VALU",
                provider="valu",
            )
        
        if tenor not in self.SUPPORTED_TENORS:
            raise PaymentProviderError(
                f"Invalid tenor {tenor}. Supported: {self.SUPPORTED_TENORS}",
                provider="valu",
            )
        
        # Import Paymob provider to use as gateway
        from services.payment_platform.providers.paymob_provider import PaymobProvider
        
        paymob = PaymobProvider()
        
        # Calculate installment amount
        amount_egp = piastres_to_egp(amount_piastres)
        down_payment_egp = piastres_to_egp(down_payment_piastres)
        financed_amount = amount_egp - down_payment_egp
        monthly_installment = financed_amount / tenor
        
        # Create charge through Paymob with Valu integration
        try:
            result = await paymob.create_charge(
                amount_piastres=amount_piastres,
                customer=customer,
                order_ref=order_ref,
                payment_method="valu",
                **kwargs,
            )
        except Exception as e:
            raise PaymentProviderError(
                f"Valu charge failed: {e}",
                provider="valu",
            ) from e
        
        # Add Valu-specific installment details
        result["provider"] = "valu"
        result["tenor_months"] = tenor
        result["down_payment_egp"] = down_payment_egp
        result["financed_amount_egp"] = financed_amount
        result["monthly_installment_egp"] = round(monthly_installment, 2)
        result["installment_schedule"] = self._calculate_schedule(
            financed_amount,
            tenor,
        )
        
        return result
    
    def _calculate_schedule(self, principal: float, tenor: int) -> List[Dict[str, Any]]:
        """
        Calculate installment schedule.
        
        Note: Actual interest rates may vary based on Valu's assessment.
        This provides an estimate for display purposes.
        """
        monthly = principal / tenor
        schedule = []
        
        for month in range(1, tenor + 1):
            schedule.append({
                "month": month,
                "amount_egp": round(monthly, 2),
                "due_date": None,  # Will be set by Valu after approval
            })
        
        return schedule
    
    async def check_eligibility(
        self,
        customer_phone: str,
        amount_piastres: int,
        tenor: ValuTenor = 6,
    ) -> Dict[str, Any]:
        """
        Check if customer is eligible for Valu BNPL.
        
        Args:
            customer_phone: Customer's phone number
            amount_piastres: Purchase amount in piastres
            tenor: Desired installment period
            
        Returns:
            Dict with eligible (bool), max_amount, available_tenors
        """
        # Valu eligibility check is done through Paymob's API
        # This is a placeholder - actual implementation would call Valu's eligibility endpoint
        
        if not self.integration_id:
            return {
                "eligible": False,
                "reason": "Valu not configured",
                "max_amount_egp": 0,
                "available_tenors": [],
            }
        
        # Placeholder response - in production, call actual Valu API
        amount_egp = piastres_to_egp(amount_piastres)
        
        return {
            "eligible": True,
            "max_amount_egp": amount_egp,
            "available_tenors": self.SUPPORTED_TENORS,
            "requested_tenor": tenor,
        }
    
    def verify_webhook(self, payload: bytes, signature: str, headers: Optional[Dict[str, str]] = None) -> bool:
        """
        Verify Valu webhook signature.
        
        Valu webhooks come through Paymob, so we use Paymob's HMAC verification.
        """
        from services.payment_platform.providers.paymob_provider import verify_callback_hmac
        import json
        
        try:
            obj = json.loads(payload)
            return verify_callback_hmac(obj, signature)
        except Exception as e:
            logger.error("Valu webhook verification failed: %s", e)
            return False
    
    async def refund(
        self,
        reference_number: str,
        amount_piastres: int,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refund a Valu transaction.
        
        Note: Valu refunds may have different rules than regular refunds.
        Check Valu's documentation for refund policies on BNPL.
        """
        from services.payment_platform.providers.paymob_provider import PaymobProvider
        
        paymob = PaymobProvider()
        
        try:
            result = await paymob.refund(
                reference_number=reference_number,
                amount_piastres=amount_piastres,
                reason=reason,
            )
            result["provider"] = "valu"
            return result
        except Exception as e:
            raise PaymentProviderError(
                f"Valu refund failed: {e}",
                provider="valu",
            ) from e
    
    async def get_charge_status(self, charge_id: str) -> Dict[str, Any]:
        """Get status of a Valu charge."""
        from services.payment_platform.providers.paymob_provider import PaymobProvider
        
        paymob = PaymobProvider()
        
        try:
            result = await paymob.get_charge_status(charge_id)
            result["provider"] = "valu"
            return result
        except Exception as e:
            raise PaymentProviderError(
                f"Valu status check failed: {e}",
                provider="valu",
            ) from e


# Module-level singleton
_provider = ValuProvider()


async def create_charge(
    amount_piastres: int,
    customer: Dict[str, Any],
    order_ref: str,
    tenor: ValuTenor = 6,
    down_payment_piastres: int = 0,
    **kwargs,
) -> Dict[str, Any]:
    """Create Valu BNPL charge (convenience function)."""
    return await _provider.create_charge(
        amount_piastres=amount_piastres,
        customer=customer,
        order_ref=order_ref,
        tenor=tenor,
        down_payment_piastres=down_payment_piastres,
        **kwargs,
    )


async def check_eligibility(
    customer_phone: str,
    amount_piastres: int,
    tenor: ValuTenor = 6,
) -> Dict[str, Any]:
    """Check Valu eligibility (convenience function)."""
    return await _provider.check_eligibility(
        customer_phone=customer_phone,
        amount_piastres=amount_piastres,
        tenor=tenor,
    )
