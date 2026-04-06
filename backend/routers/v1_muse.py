"""
CONFIT Backend — MUSE Virtual Stylist v1 Router
=================================================
POST /api/v1/muse/chat   — Chat with AI stylist
GET  /api/v1/muse/history — Get session history
DEL  /api/v1/muse/session — Clear session
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field

from database.session import get_db
from services.ai.muse_service import MuseService
from services.ai.cost_tracker import get_cost_tracker, AICostTracker
from utils.auth_deps import require_auth
from services.auth_service import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/muse", tags=["MUSE — Virtual Stylist"])


# ── Schemas ──────────────────────────────────────────────────────────

class MuseChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="en", pattern="^(en|ar)$")
    session_id: Optional[str] = None


class OutfitItemSchema(BaseModel):
    sku: str
    name: str
    brand: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None


class OutfitSchema(BaseModel):
    outfit_id: str
    title: str
    items: list[OutfitItemSchema]
    total_price: float
    occasion: Optional[str] = None
    styling_tips: list[str] = []
    from_closet: list[str] = []
    from_catalog: list[str] = []


class MuseChatResponse(BaseModel):
    reply: str
    outfits: list[OutfitSchema] = []
    follow_ups: list[str] = []
    session_id: str
    tokens_used: int = 0
    cost_usd: float = 0.0


class SessionHistoryResponse(BaseModel):
    session_id: str
    messages: list[dict]


# ── Helpers ──────────────────────────────────────────────────────────

def _get_muse_service(db=Depends(get_db)) -> MuseService:
    from core.redis_client import get_redis_client
    redis = get_redis_client()
    service = MuseService(db, redis)
    tracker = get_cost_tracker(db, redis)
    service.set_cost_tracker(tracker)
    return service


def _user_tier(user: UserProfile) -> str:
    role = getattr(user, "role", "user") or "user"
    if role in ("icon", "donor", "admin"):
        return "icon"
    if role in ("club", "wardrobe_club", "premium"):
        return "club"
    return "free"


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/chat", response_model=MuseChatResponse)
async def muse_chat(
    payload: MuseChatRequest,
    request: Request,
    user: UserProfile = Depends(require_auth),
    service: MuseService = Depends(_get_muse_service),
):
    """
    Chat with MUSE AI stylist.

    Rate-limited: 20/hr (free), 100/hr (Wardrobe Club), 500/hr (Icon).
    Every call is cost-tracked.
    """
    tier = _user_tier(user)
    allowed, retry_after = await service.check_rate_limit(str(user.id), tier)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Rate limit exceeded. Please wait before sending another message.",
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    # Budget kill-switch check
    tracker = service._cost_tracker
    if tracker and tracker.is_kill_switch_active():
        raise HTTPException(
            status_code=503,
            detail="AI services temporarily unavailable due to budget limits. Please try again later.",
        )

    response = await service.chat(
        user_id=str(user.id),
        message=payload.message,
        language=payload.language,
        session_id=payload.session_id,
    )

    return MuseChatResponse(
        reply=response.reply,
        outfits=[
            OutfitSchema(
                outfit_id=o.outfit_id,
                title=o.title,
                items=[
                    OutfitItemSchema(
                        sku=it.get("sku", it.get("id", "")),
                        name=it.get("name", ""),
                        brand=it.get("brand"),
                        price=it.get("price"),
                        image_url=it.get("image_url"),
                    )
                    for it in o.items
                ],
                total_price=o.total_price,
                occasion=o.occasion,
                styling_tips=o.styling_tips,
                from_closet=o.from_closet,
                from_catalog=o.from_catalog,
            )
            for o in response.outfits
        ],
        follow_ups=response.follow_ups,
        session_id=response.session_id,
        tokens_used=response.tokens_in + response.tokens_out,
        cost_usd=response.cost_usd,
    )


@router.get("/history/{session_id}", response_model=SessionHistoryResponse)
async def muse_history(
    session_id: str,
    user: UserProfile = Depends(require_auth),
    service: MuseService = Depends(_get_muse_service),
):
    """Retrieve conversation history for a session."""
    messages = await service.get_session_history(session_id)
    return SessionHistoryResponse(session_id=session_id, messages=messages)


@router.delete("/session/{session_id}")
async def muse_clear_session(
    session_id: str,
    user: UserProfile = Depends(require_auth),
    service: MuseService = Depends(_get_muse_service),
):
    """Clear a MUSE session's context."""
    ok = await service.clear_session(session_id)
    return {"success": ok, "session_id": session_id}
