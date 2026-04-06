"""
Egypt Tax Service - VAT calculation for Egyptian transactions.

Egypt VAT Rate: 14% (as of 2024)

All amounts are in PIASTRES (smallest currency unit) to avoid floating-point errors.
1 EGP = 100 Piastres
"""

from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Egypt VAT rate (14%)
EGYPT_VAT_RATE = Decimal("0.14")

# Countries with VAT/sales tax
VAT_RATES: Dict[str, Decimal] = {
    "EG": Decimal("0.14"),  # Egypt - 14%
    "SA": Decimal("0.15"),  # Saudi Arabia - 15%
    "AE": Decimal("0.05"),  # UAE - 5%
    "KW": Decimal("0.05"),  # Kuwait - 5% (planned)
}


def calculate_vat(
    amount_piastres: int,
    country: str = "EG",
    include_vat: bool = False,
) -> Dict[str, int]:
    """
    Calculate VAT for a given amount.
    
    Args:
        amount_piastres: Amount in piastres (EGP * 100)
        country: ISO country code (default: EG for Egypt)
        include_vat: If True, amount already includes VAT (reverse calculate)
        
    Returns:
        Dict with subtotal_piastres, vat_piastres, total_piastres
    """
    rate = VAT_RATES.get(country.upper(), Decimal("0"))
    
    if include_vat:
        # Reverse calculate VAT from gross amount
        # gross = subtotal * (1 + rate)
        # subtotal = gross / (1 + rate)
        # vat = gross - subtotal
        gross = Decimal(amount_piastres)
        subtotal = (gross / (Decimal("1") + rate)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        vat = gross - subtotal
    else:
        # Calculate VAT on net amount
        subtotal = Decimal(amount_piastres)
        vat = (subtotal * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    
    return {
        "subtotal_piastres": int(subtotal),
        "vat_piastres": int(vat),
        "total_piastres": int(subtotal + vat),
        "vat_rate": float(rate),
        "country": country.upper(),
    }


def calculate_egypt_vat(amount_piastres: int, include_vat: bool = False) -> Dict[str, int]:
    """
    Calculate Egypt VAT (14%) for a given amount.
    
    Convenience function for Egypt-specific calculations.
    
    Args:
        amount_piastres: Amount in piastres (EGP * 100)
        include_vat: If True, amount already includes VAT (reverse calculate)
        
    Returns:
        Dict with subtotal_piastres, vat_piastres, total_piastres
    """
    return calculate_vat(amount_piastres, country="EG", include_vat=include_vat)


def calculate_order_tax(
    items: List[Dict[str, int]],
    country: str = "EG",
    shipping_piastres: int = 0,
    discount_piastres: int = 0,
) -> Dict[str, int]:
    """
    Calculate tax for an order with multiple items.
    
    Args:
        items: List of items with 'amount_piastres' key
        country: ISO country code
        shipping_piastres: Shipping cost in piastres
        discount_piastres: Discount amount in piastres
        
    Returns:
        Dict with subtotal, vat, shipping, discount, total
    """
    subtotal = sum(item.get("amount_piastres", 0) for item in items)
    subtotal_after_discount = max(0, subtotal - discount_piastres)
    
    # VAT applies to subtotal after discount, before shipping
    tax_result = calculate_vat(subtotal_after_discount, country=country)
    
    # Shipping is typically taxed as well in Egypt
    shipping_tax = calculate_vat(shipping_piastres, country=country)
    
    return {
        "subtotal_piastres": subtotal,
        "discount_piastres": discount_piastres,
        "taxable_amount_piastres": subtotal_after_discount,
        "vat_piastres": tax_result["vat_piastres"] + shipping_tax["vat_piastres"],
        "shipping_piastres": shipping_piastres,
        "total_piastres": (
            subtotal_after_discount 
            + tax_result["vat_piastres"] 
            + shipping_piastres 
            + shipping_tax["vat_piastres"]
        ),
        "vat_rate": float(VAT_RATES.get(country.upper(), Decimal("0"))),
        "country": country.upper(),
    }


def piastres_to_egp(piastres: int) -> float:
    """Convert piastres to EGP (divide by 100)."""
    return piastres / 100.0


def egp_to_piastres(egp: float) -> int:
    """Convert EGP to piastres (multiply by 100)."""
    return int(round(egp * 100))


def format_egp(piastres: int) -> str:
    """Format piastres as EGP string with 2 decimal places."""
    return f"{piastres_to_egp(piastres):.2f} EGP"


class TaxService:
    """
    Service class for tax calculations.
    
    Provides methods for calculating VAT for orders and payments.
    """
    
    def __init__(self, default_country: str = "EG"):
        self.default_country = default_country.upper()
    
    def calculate_for_order(
        self,
        subtotal_piastres: int,
        country: Optional[str] = None,
        shipping_piastres: int = 0,
        discount_piastres: int = 0,
    ) -> Dict[str, int]:
        """Calculate tax for an order."""
        return calculate_order_tax(
            items=[{"amount_piastres": subtotal_piastres}],
            country=country or self.default_country,
            shipping_piastres=shipping_piastres,
            discount_piastres=discount_piastres,
        )
    
    def get_vat_rate(self, country: Optional[str] = None) -> float:
        """Get VAT rate for a country."""
        rate = VAT_RATES.get((country or self.default_country).upper(), Decimal("0"))
        return float(rate)
    
    def is_vat_applicable(self, country: Optional[str] = None) -> bool:
        """Check if VAT applies for a country."""
        return (country or self.default_country).upper() in VAT_RATES


# Module-level service instance
tax_service = TaxService()
