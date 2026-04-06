"""
CONFIT Backend — Investor Pitch Deck Router
==============================================
Returns deterministic pitch-deck slide structures for the frontend.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from services.pitch_deck_service import generate_pitch_deck

router = APIRouter(prefix="/api/pitch", tags=["Investor Pitch"])


@router.get("/deck")
async def get_pitch_deck(
    variant: Literal["A", "B"] = Query("A"),
):
    """Get investor pitch deck slides."""
    return generate_pitch_deck(variant=variant)

