"""
CONFIT Backend — Virtual Stylist Router
=========================================
Thin routing layer that delegates all business logic
to the StylistController (MVC pattern).
"""

import logging

from fastapi import APIRouter, HTTPException

from controllers.stylist_controller import StylistController
from models.stylist_models import StylistChatRequest, StylistChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stylist", tags=["Virtual Stylist"])


@router.post("/chat", response_model=StylistChatResponse)
async def stylist_chat(request: StylistChatRequest):
    """
    Send a message to the virtual stylist and receive
    personalized fashion advice and outfit suggestions.
    """
    try:
        controller = StylistController.get_instance()
        return await controller.chat(request)
    except Exception as exc:
        logger.error("Stylist chat error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Stylist service temporarily unavailable. Please try again.",
        )


@router.get("/health")
async def stylist_health():
    """Health check for the stylist service."""
    controller = StylistController.get_instance()
    return controller.health()
