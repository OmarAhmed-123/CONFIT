"""
CONFIT Backend — Stylist Controller
=====================================
Orchestrates virtual stylist chat requests.
"""

import logging
import os
from typing import Optional

from models.stylist_models import StylistChatRequest, StylistChatResponse
from services.stylist_service import VirtualStylistService

logger = logging.getLogger(__name__)


class StylistController:
    """Controller for the virtual stylist chat feature."""

    _instance: Optional["StylistController"] = None

    def __init__(self) -> None:
        groq_key = os.getenv("GROQ_API_KEY")
        self._service = VirtualStylistService(
            groq_api_key=groq_key if groq_key else None,
        )

    @classmethod
    def get_instance(cls) -> "StylistController":
        """Return a singleton controller instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def chat(self, request: StylistChatRequest) -> StylistChatResponse:
        """
        Process a stylist chat message and return styling advice.
        """
        history = None
        if request.conversationHistory:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversationHistory
            ]

        result = await self._service.chat(
            user_message=request.message,
            conversation_history=history,
            occasion=request.occasion,
            budget=request.budget,
            style_preference=request.stylePreference,
            style_dna_context=request.styleDNAContext,
        )

        return StylistChatResponse(
            content=result["content"],
            outfitSuggestions=result.get("outfitSuggestions"),
            detectedOccasion=result.get("detectedOccasion"),
        )

    def health(self) -> dict:
        """Return service health status."""
        return {
            "status": "ok",
            "service": "virtual-stylist",
            "mode": "groq" if self._service._has_ai else "rule-based",
        }
