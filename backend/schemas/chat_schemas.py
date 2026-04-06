"""
CONFIT Backend — Chat API Schemas
==================================
Pydantic schemas for the AI Stylist Chat API.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator


# ═══════════════════════════════════════════════════════════════════
# CHAT MESSAGE SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class ConversationMessage(BaseModel):
    """A single message in the conversation history."""
    role: Literal["user", "assistant", "system"] = Field(
        ..., description="Message sender role"
    )
    content: str = Field(..., description="Message content", min_length=1, max_length=5000)


class ChatRequest(BaseModel):
    """Request to send a message to the AI stylist."""
    message: str = Field(
        ...,
        description="The user's message to the stylist",
        min_length=1,
        max_length=2000,
    )
    session_id: Optional[str] = Field(
        None,
        description="Existing session ID to continue conversation",
    )
    conversation_history: Optional[List[ConversationMessage]] = Field(
        None,
        description="Previous messages for context (optional if session_id provided)",
    )
    
    # Context hints
    occasion: Optional[str] = Field(None, description="Occasion hint (wedding, work, casual, etc.)")
    budget: Optional[str] = Field(None, description="Budget hint (budget, moderate, premium, luxury)")
    style_preference: Optional[str] = Field(None, description="Style preference hint")
    gender: Optional[str] = Field(None, description="Gender preference for recommendations")
    
    @validator('message')
    def sanitize_message(cls, v):
        """Sanitize message input."""
        # Remove potential script injection
        v = v.replace('<script>', '').replace('</script>', '')
        # Remove excessive whitespace
        v = ' '.join(v.split())
        return v


class OutfitSuggestion(BaseModel):
    """An outfit suggestion from the stylist."""
    id: str
    name: str
    price: float
    style_score: int = Field(..., alias="styleScore", ge=0, le=100)
    image: str
    
    class Config:
        populate_by_name = True


class ProductRecommendation(BaseModel):
    """A product recommendation from the stylist."""
    id: str
    product_id: str = Field(..., alias="productId")
    name: str
    brand: str
    price: float
    image: str
    match_score: float = Field(..., alias="matchScore", ge=0, le=1)
    category: Optional[str] = None
    color: Optional[str] = None
    url: Optional[str] = None
    
    class Config:
        populate_by_name = True


class WardrobeSuggestion(BaseModel):
    """A suggestion to use wardrobe items."""
    item_id: str = Field(..., alias="itemId")
    name: str
    category: str
    color: Optional[str] = None
    image_url: Optional[str] = Field(None, alias="imageUrl")
    styling_tip: Optional[str] = Field(None, alias="stylingTip")
    
    class Config:
        populate_by_name = True


class StyleTip(BaseModel):
    """A style tip from the stylist."""
    title: str
    description: str
    category: Optional[str] = None  # color, fit, occasion, trend


class ChatResponse(BaseModel):
    """Response from the AI stylist."""
    content: str = Field(..., description="The stylist's response message")
    session_id: str = Field(..., alias="sessionId", description="Session ID for continuing conversation")
    
    # Detected intent
    detected_occasion: Optional[str] = Field(None, alias="detectedOccasion")
    detected_budget: Optional[str] = Field(None, alias="detectedBudget")
    detected_style: Optional[str] = Field(None, alias="detectedStyle")
    detected_colors: Optional[List[str]] = Field(None, alias="detectedColors")
    
    # Recommendations
    outfit_suggestions: Optional[List[OutfitSuggestion]] = Field(None, alias="outfitSuggestions")
    product_recommendations: Optional[List[ProductRecommendation]] = Field(None, alias="productRecommendations")
    wardrobe_suggestions: Optional[List[WardrobeSuggestion]] = Field(None, alias="wardrobeSuggestions")
    style_tips: Optional[List[StyleTip]] = Field(None, alias="styleTips")
    
    # Metadata
    is_typing: bool = Field(False, alias="isTyping")
    cached: bool = Field(False, description="Whether response was from cache")
    
    class Config:
        populate_by_name = True


# ═══════════════════════════════════════════════════════════════════
# SESSION SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class ChatSessionCreate(BaseModel):
    """Request to create a new chat session."""
    title: Optional[str] = Field(None, description="Optional session title")
    initial_context: Optional[Dict[str, Any]] = Field(
        None,
        alias="initialContext",
        description="Initial context (occasion, budget, etc.)",
    )
    
    class Config:
        populate_by_name = True


class ChatSessionResponse(BaseModel):
    """Response for a chat session."""
    id: str
    title: Optional[str] = None
    message_count: int = Field(..., alias="messageCount")
    is_active: bool = Field(..., alias="isActive")
    detected_occasion: Optional[str] = Field(None, alias="detectedOccasion")
    detected_budget: Optional[str] = Field(None, alias="detectedBudget")
    detected_style: Optional[str] = Field(None, alias="detectedStyle")
    created_at: datetime = Field(..., alias="createdAt")
    last_message_at: Optional[datetime] = Field(None, alias="lastMessageAt")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class ChatSessionList(BaseModel):
    """List of chat sessions."""
    sessions: List[ChatSessionResponse]
    total: int


class ChatHistoryResponse(BaseModel):
    """Chat history for a session."""
    session_id: str = Field(..., alias="sessionId")
    messages: List[ConversationMessage]
    has_more: bool = Field(..., alias="hasMore")
    next_offset: Optional[int] = Field(None, alias="nextOffset")
    
    class Config:
        populate_by_name = True


# ═══════════════════════════════════════════════════════════════════
# FEEDBACK SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class MessageFeedback(BaseModel):
    """User feedback on a message."""
    message_id: str = Field(..., alias="messageId")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    notes: Optional[str] = Field(None, max_length=500)
    
    class Config:
        populate_by_name = True


class RecommendationInteraction(BaseModel):
    """User interaction with a recommendation."""
    recommendation_id: str = Field(..., alias="recommendationId")
    action: Literal["click", "add_to_cart", "add_to_wishlist", "dismiss"]
    
    class Config:
        populate_by_name = True


# ═══════════════════════════════════════════════════════════════════
# QUICK ACTION SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class QuickAction(BaseModel):
    """A quick action button for the chat UI."""
    id: str
    label: str
    icon: Optional[str] = None
    action_type: str = Field(..., alias="actionType")  # occasion, budget, style, regenerate
    value: Optional[str] = None


class QuickActionsResponse(BaseModel):
    """Available quick actions for the chat."""
    occasions: List[QuickAction]
    budgets: List[QuickAction]
    styles: List[QuickAction]
