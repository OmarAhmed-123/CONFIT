"""
CONFIT Backend — Virtual Stylist Data Models
==============================================
Pydantic schemas for the styling-chat request/response contracts.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """A single message in the conversation history."""

    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class StylistChatRequest(BaseModel):
    """Validated input for a stylist chat turn."""

    message: str = Field(
        ...,
        description="The user's message to the stylist",
        min_length=1,
        max_length=2000,
    )
    conversationHistory: Optional[List[ConversationMessage]] = Field(
        default=None,
        description="Previous messages for conversational context",
    )
    occasion: Optional[str] = Field(
        default=None,
        description="Currently selected occasion type",
    )
    budget: Optional[str] = Field(
        default=None,
        description="User's budget preference",
    )
    stylePreference: Optional[str] = Field(
        default=None,
        description="User's style preference",
    )
    styleDNAContext: Optional[str] = Field(
        default=None,
        description="CONFIT Style DNA summary for identity-aware replies (server-injected)",
    )


class OutfitSuggestion(BaseModel):
    """An outfit suggestion returned by the stylist."""

    id: str
    name: str
    price: float
    styleScore: int
    image: str


class StylistChatResponse(BaseModel):
    """Standardised output for a stylist chat turn."""

    content: str = Field(..., description="Stylist's response message")
    outfitSuggestions: Optional[List[OutfitSuggestion]] = Field(
        default=None,
        description="Outfit suggestions if applicable",
    )
    detectedOccasion: Optional[str] = Field(
        default=None,
        description="Occasion detected from the user's message",
    )
