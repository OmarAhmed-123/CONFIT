"""
CONFIT — Commerce intelligence stubs
=====================================
Optional AI/commerce endpoints used by the checkout and cart flows.
Returns stable JSON so the SPA stops logging 404s when full ML services are not deployed.
"""

from typing import Any, Optional

from fastapi import APIRouter, Body, Depends
from utils.auth_deps import optional_auth
from services.auth_service import UserProfile

router = APIRouter(prefix="/api/commerce", tags=["Commerce"])


@router.post("/cart/track-event")
async def cart_track_event(
    payload: Optional[dict[str, Any]] = Body(default=None),
    _user: UserProfile | None = Depends(optional_auth),
):
    return {"ok": True, "received": bool(payload)}


@router.post("/cart/optimize")
async def cart_optimize(
    payload: Optional[dict[str, Any]] = Body(default=None),
    _user: UserProfile | None = Depends(optional_auth),
):
    return {
        "suggestions": [],
        "upsells": [],
        "bundle_discount": 0,
        "message": "stub",
    }


@router.post("/cart/abandonment-risk")
async def cart_abandonment(
    payload: Optional[dict[str, Any]] = Body(default=None),
    _user: UserProfile | None = Depends(optional_auth),
):
    return {"risk_level": "low", "score": 0.1, "message": "stub"}


@router.post("/confidence/calculate")
async def confidence_calculate(
    payload: Optional[dict[str, Any]] = Body(default=None),
    _user: UserProfile | None = Depends(optional_auth),
):
    return {
        "overall_score": 0.78,
        "dimensions": {
            "style_alignment": 0.8,
            "budget_fit": 0.75,
            "size_confidence": 0.7,
            "brand_affinity": 0.8,
            "occasion_match": 0.75,
            "return_risk": 0.2,
        },
        "recommendations": [],
        "confidence_level": "medium",
    }


@router.post("/delivery/recommend")
async def delivery_recommend(
    payload: Optional[dict[str, Any]] = Body(default=None),
    _user: UserProfile | None = Depends(optional_auth),
):
    return {
        "recommended_method": "standard",
        "alternatives": [],
        "estimated_arrival": "3-5 business days",
        "cost": 5.99,
        "eco_impact": 0,
        "reason": "stub",
    }


@router.post("/bnpl/check-eligibility")
async def bnpl_eligibility(
    payload: Optional[dict[str, Any]] = Body(default=None),
    _user: UserProfile | None = Depends(optional_auth),
):
    return {
        "eligible": True,
        "review_required": False,
        "confidence_score": 0.8,
        "risk_score": 0.15,
        "order_value_ok": True,
        "max_installments": 4,
        "reason": "stub",
    }
