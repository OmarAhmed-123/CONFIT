"""
Body DNA API — status, fit preview without full try-on, encrypted profile summary.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.tryon.body_dna import BodyDNAStore, predict_fit_preview
from services.tryon.body_dna.style_memory import top_style_signals

router = APIRouter(prefix="/api/body-dna", tags=["Body DNA"])


class FitPreviewBody(BaseModel):
    userId: str = Field(..., description="User id whose stored Body DNA to use")
    garmentCategory: str = Field(default="tops")
    fitType: str = Field(default="regular")


@router.get("/status")
async def body_dna_status(userId: str = Query(..., description="User id")) -> Dict[str, Any]:
    store = BodyDNAStore()
    return {"hasProfile": store.exists(userId), "userId": userId}


@router.get("/summary")
async def body_dna_summary(userId: str = Query(...)) -> Dict[str, Any]:
    """Measurements + mesh + style signals only (no raw photo; landmarks omitted by default)."""
    store = BodyDNAStore()
    prof = store.load(userId)
    if not prof:
        raise HTTPException(status_code=404, detail="No Body DNA stored for this user")
    sm = prof.get("style_memory") or {}
    return {
        "version": prof.get("version"),
        "measurements": prof.get("measurements"),
        "mesh": prof.get("mesh"),
        "styleSignals": top_style_signals(sm),
    }


@router.post("/fit-preview")
async def body_dna_fit_preview(body: FitPreviewBody) -> Dict[str, Any]:
    """Instant fit score + skeleton JSON without running the full render pipeline."""
    store = BodyDNAStore()
    prof = store.load(body.userId)
    if not prof:
        raise HTTPException(status_code=404, detail="No Body DNA stored for this user")
    return predict_fit_preview(prof, body.garmentCategory, body.fitType)


@router.delete("/profile")
async def delete_body_dna_profile(userId: str = Query(...)) -> Dict[str, bool]:
    store = BodyDNAStore()
    ok = store.delete(userId)
    if not ok:
        raise HTTPException(status_code=404, detail="No profile to delete")
    return {"deleted": True}
