"""
CONFIT — Fashion OS (intelligence layer)
========================================
Style DNA, behavior learning, outfit generation, smart closet, daily automation, stylist.
"""

import json
import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from controllers.stylist_controller import StylistController
from database.session import get_db
from models.stylist_models import ConversationMessage, StylistChatRequest
from services.fashion_os_engine import FashionOSEngine
from services.auth_service import UserProfile
from utils.auth_deps import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fashion-os", tags=["Fashion OS"])


def _dna_prompt_block(identity: dict) -> str:
    safe = {k: v for k, v in identity.items() if k != "style_vector"}
    return json.dumps(safe, indent=2)[:6000]


class StyleUpdateBody(BaseModel):
    signals: Optional[dict[str, float]] = None
    identity_dna_patch: Optional[dict[str, Any]] = None
    feedback: Optional[dict[str, Any]] = None


class RecommendBody(BaseModel):
    limit: int = Field(default=12, ge=1, le=50)


class OutfitGenerateBody(BaseModel):
    occasion: Optional[str] = "everyday"
    budget_max: Optional[float] = None
    prefer_closet: bool = True
    count: int = Field(default=4, ge=1, le=8)


class BehaviorLogBody(BaseModel):
    event_type: str = "view"
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    session_id: Optional[str] = None
    hover_ms: Optional[float] = None
    scroll_velocity: Optional[float] = None
    view_repetition: Optional[int] = None
    try_on_attempts: Optional[int] = None
    session_duration_sec: Optional[float] = None


class StylistChatBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversationHistory: Optional[List[ConversationMessage]] = None
    occasion: Optional[str] = None
    budget: Optional[str] = None
    stylePreference: Optional[str] = None


@router.get("/health")
async def fashion_os_health():
    return {
        "status": "ok",
        "layer": "CONFIT Fashion OS",
        "modules": [
            "style-dna",
            "ai-stylist",
            "behavior-learning",
            "outfit-generation",
            "smart-closet",
            "daily-style",
            "feedback-loop",
        ],
    }


@router.post("/style/update")
def style_update(
    body: StyleUpdateBody,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    engine = FashionOSEngine(db)
    return engine.update_style(user.id, body.model_dump(exclude_none=True))


@router.post("/style/recommend")
def style_recommend(
    body: RecommendBody,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    engine = FashionOSEngine(db)
    return engine.recommend(user.id, body.model_dump())


@router.post("/outfit/generate")
def outfit_generate(
    body: OutfitGenerateBody,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    engine = FashionOSEngine(db)
    return engine.generate_outfits(user.id, body.model_dump())


@router.post("/behavior/log")
def behavior_log(
    body: BehaviorLogBody,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    engine = FashionOSEngine(db)
    return engine.log_behavior(user.id, body.model_dump(exclude_none=True))


@router.get("/closet/insights")
def closet_insights(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    engine = FashionOSEngine(db)
    return engine.closet_insights(user.id)


@router.get("/daily-outfit")
def daily_outfit(
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    engine = FashionOSEngine(db)
    return engine.daily_outfit(user.id)


@router.post("/stylist/chat")
async def stylist_chat(
    body: StylistChatBody,
    user: UserProfile = Depends(require_auth),
    db: Session = Depends(get_db),
):
    engine = FashionOSEngine(db)
    identity = engine.get_identity_dna(user.id)
    dna_text = _dna_prompt_block(identity)

    req = StylistChatRequest(
        message=body.message,
        conversationHistory=body.conversationHistory,
        occasion=body.occasion,
        budget=body.budget,
        stylePreference=body.stylePreference,
        styleDNAContext=dna_text,
    )
    controller = StylistController.get_instance()
    try:
        return await controller.chat(req)
    except Exception as exc:
        logger.error("Fashion OS stylist chat: %s", exc)
        raise HTTPException(status_code=500, detail="Stylist service failed") from exc
