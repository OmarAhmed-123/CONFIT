"""
CONFIT Backend — Promo Codes Router
=====================================
Validate promo codes for discounts.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/promo", tags=["Promo"])

class PromoRequest(BaseModel):
    code: str
    cartTotal: float

class PromoResponse(BaseModel):
    valid: bool
    discountAmount: float
    newTotal: float
    message: str

# Mock Promo Database
PROMOS = {
    "WELCOME10": {"type": "percent", "value": 0.10, "min_spend": 0},
    "SAVE20": {"type": "percent", "value": 0.20, "min_spend": 100},
    "FREESHIP": {"type": "fixed", "value": 15.0, "min_spend": 50},  # Assuming shipping is flat 15
    "CONFIT50": {"type": "fixed", "value": 50.0, "min_spend": 200},
}

@router.post("/validate", response_model=PromoResponse)
async def validate_promo(request: PromoRequest):
    code = request.code.upper().strip()
    
    if code not in PROMOS:
        return PromoResponse(
            valid=False,
            discountAmount=0,
            newTotal=request.cartTotal,
            message="Invalid promo code."
        )
    
    promo = PROMOS[code]
    
    if request.cartTotal < promo["min_spend"]:
        return PromoResponse(
            valid=False,
            discountAmount=0,
            newTotal=request.cartTotal,
            message=f"Minimum spend of ${promo['min_spend']} required."
        )

    discount = 0.0
    if promo["type"] == "percent":
        discount = request.cartTotal * promo["value"]
    elif promo["type"] == "fixed":
        discount = promo["value"]
    
    # Ensure discount doesn't exceed total
    discount = min(discount, request.cartTotal)
    new_total = request.cartTotal - discount

    return PromoResponse(
        valid=True,
        discountAmount=round(discount, 2),
        newTotal=round(new_total, 2),
        message="Promo code applied!"
    )
