"""
CONFIT Backend — AI Stylist Chat Router
========================================
Enhanced chat API with context injection, rate limiting, and security.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models.chat_models import (
    ChatSession, ChatMessage, StylistRecommendation,
    MessageRoleEnum, RecommendationTypeEnum
)
from schemas.chat_schemas import (
    ChatRequest, ChatResponse, ChatSessionCreate, ChatSessionResponse,
    ChatSessionList, ChatHistoryResponse, MessageFeedback,
    RecommendationInteraction, QuickActionsResponse, QuickAction,
    OutfitSuggestion, ProductRecommendation, WardrobeSuggestion, StyleTip
)
from services.ai_stylist_service import AIStylistService, StylistContext
from services.stylist_service import OUTFIT_SUGGESTIONS

from core.slowapi_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stylist", tags=["AI Stylist Chat"])
security = HTTPBearer(auto_error=False)


# ═══════════════════════════════════════════════════════════════════
# QUICK ACTIONS DATA
# ═══════════════════════════════════════════════════════════════════

OCCASION_ACTIONS = [
    QuickAction(id="wedding", label="Wedding", icon="💒", actionType="occasion", value="wedding"),
    QuickAction(id="work", label="Work", icon="💼", actionType="occasion", value="work"),
    QuickAction(id="date", label="Date Night", icon="❤️", actionType="occasion", value="date"),
    QuickAction(id="party", label="Party", icon="🎉", actionType="occasion", value="party"),
    QuickAction(id="casual", label="Casual", icon="☀️", actionType="occasion", value="casual"),
    QuickAction(id="interview", label="Interview", icon="🎯", actionType="occasion", value="interview"),
    QuickAction(id="travel", label="Travel", icon="✈️", actionType="occasion", value="travel"),
    QuickAction(id="gym", label="Gym", icon="💪", actionType="occasion", value="gym"),
]

BUDGET_ACTIONS = [
    QuickAction(id="budget", label="Under $100", icon="💰", actionType="budget", value="budget"),
    QuickAction(id="moderate", label="$100-$300", icon="💵", actionType="budget", value="moderate"),
    QuickAction(id="premium", label="$300-$500", icon="💳", actionType="budget", value="premium"),
    QuickAction(id="luxury", label="$500+", icon="💎", actionType="budget", value="luxury"),
]

STYLE_ACTIONS = [
    QuickAction(id="classic", label="Classic", icon="🎩", actionType="style", value="classic"),
    QuickAction(id="modern", label="Modern", icon="🏙️", actionType="style", value="modern"),
    QuickAction(id="minimalist", label="Minimalist", icon="⬜", actionType="style", value="minimalist"),
    QuickAction(id="bohemian", label="Bohemian", icon="🌸", actionType="style", value="bohemian"),
    QuickAction(id="streetwear", label="Streetwear", icon="👟", actionType="style", value="streetwear"),
    QuickAction(id="edgy", label="Edgy", icon="⚡", actionType="style", value="edgy"),
]


# ═══════════════════════════════════════════════════════════════════
# DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Optional[str]:
    """Extract user ID from JWT token if available."""
    if not credentials:
        return None
    # In production, validate JWT and extract user_id
    # For now, return None (anonymous user)
    return None


def get_stylist_service(db: Session = Depends(get_db)) -> AIStylistService:
    """Get AI Stylist Service instance."""
    return AIStylistService(db=db)


# ═══════════════════════════════════════════════════════════════════
# CHAT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat(
    request: Request,
    chat_request: ChatRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    service: AIStylistService = Depends(get_stylist_service),
):
    """
    Send a message to the AI stylist and receive personalized fashion advice.
    
    Rate limited to 30 requests per minute per IP.
    """
    try:
        # Get or create session
        session = await _get_or_create_session(
            db, chat_request.session_id, user_id, chat_request.occasion, chat_request.budget
        )
        
        # Build context
        context = await _build_context(
            db, session, user_id, chat_request.conversation_history,
            chat_request.occasion, chat_request.budget, chat_request.style_preference
        )
        
        # Generate response
        response = await service.chat(chat_request.message, context)
        
        # Save messages to database (background task)
        background_tasks.add_task(
            _save_messages,
            db, session.id, chat_request.message, response
        )
        
        # Update session context
        if response.detected_occasion and not session.detected_occasion:
            session.detected_occasion = response.detected_occasion
        if response.detected_budget and not session.detected_budget:
            session.detected_budget = response.detected_budget
        db.commit()
        
        # Build response
        return ChatResponse(
            content=response.content,
            sessionId=str(session.id),
            detectedOccasion=response.detected_occasion,
            detectedBudget=response.detected_budget,
            detectedStyle=response.detected_style,
            detectedColors=response.detected_colors,
            outfitSuggestions=_format_outfit_suggestions(response.outfit_suggestions),
            productRecommendations=response.product_recommendations,
            wardrobeSuggestions=response.wardrobe_suggestions,
            styleTips=response.style_tips,
            cached=response.cached,
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Stylist service temporarily unavailable. Please try again."
        )


@router.get("/sessions", response_model=ChatSessionList)
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
    user_id: Optional[str] = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List chat sessions for the current user."""
    if not user_id:
        return ChatSessionList(sessions=[], total=0)
    
    query = db.query(ChatSession).filter(
        ChatSession.user_id == user_id,
        ChatSession.is_active == True
    ).order_by(ChatSession.last_message_at.desc())
    
    total = query.count()
    sessions = query.offset(offset).limit(limit).all()
    
    return ChatSessionList(
        sessions=[ChatSessionResponse.model_validate(s) for s in sessions],
        total=total
    )


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    session_create: ChatSessionCreate,
    user_id: Optional[str] = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Create a new chat session."""
    session = ChatSession(
        user_id=user_id,
        title=session_create.title,
        context=session_create.initial_context or {},
    )
    
    if session_create.initial_context:
        if "occasion" in session_create.initial_context:
            session.detected_occasion = session_create.initial_context["occasion"]
        if "budget" in session_create.initial_context:
            session.detected_budget = session_create.initial_context["budget"]
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return ChatSessionResponse.model_validate(session)


@router.get("/sessions/{session_id}/history", response_model=ChatHistoryResponse)
async def get_history(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    user_id: Optional[str] = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get chat history for a session."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check ownership if user is authenticated
    if user_id and session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc())
    
    total = query.count()
    messages = query.offset(offset).limit(limit).all()
    
    from schemas.chat_schemas import ConversationMessage
    
    return ChatHistoryResponse(
        sessionId=session_id,
        messages=[
            ConversationMessage(role=msg.role.value, content=msg.content)
            for msg in messages
        ],
        hasMore=(offset + limit) < total,
        nextOffset=offset + limit if (offset + limit) < total else None
    )


@router.post("/feedback", status_code=204)
async def submit_feedback(
    feedback: MessageFeedback,
    user_id: Optional[str] = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Submit feedback on a message."""
    message = db.query(ChatMessage).filter(ChatMessage.id == feedback.message_id).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message.user_feedback = feedback.rating
    message.feedback_notes = feedback.notes
    db.commit()


@router.post("/interactions", status_code=204)
async def track_interaction(
    interaction: RecommendationInteraction,
    user_id: Optional[str] = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Track user interaction with a recommendation."""
    recommendation = db.query(StylistRecommendation).filter(
        StylistRecommendation.id == interaction.recommendation_id
    ).first()
    
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    if interaction.action == "click":
        recommendation.was_clicked = True
    elif interaction.action == "add_to_cart":
        recommendation.was_clicked = True
        recommendation.was_added_to_cart = True
    elif interaction.action == "add_to_wishlist":
        recommendation.was_clicked = True
        recommendation.was_added_to_wishlist = True
    elif interaction.action == "dismiss":
        recommendation.was_dismissed = True
    
    recommendation.interacted_at = datetime.now(timezone.utc)
    db.commit()


@router.get("/quick-actions", response_model=QuickActionsResponse)
async def get_quick_actions():
    """Get available quick actions for the chat UI."""
    return QuickActionsResponse(
        occasions=OCCASION_ACTIONS,
        budgets=BUDGET_ACTIONS,
        styles=STYLE_ACTIONS,
    )


@router.get("/health")
async def health_check(service: AIStylistService = Depends(get_stylist_service)):
    """Health check for the AI stylist service."""
    return service.health()


# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

async def _get_or_create_session(
    db: Session,
    session_id: Optional[str],
    user_id: Optional[str],
    occasion: Optional[str],
    budget: Optional[str],
) -> ChatSession:
    """Get existing session or create new one."""
    if session_id:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            return session
    
    # Create new session
    session = ChatSession(
        user_id=user_id,
        detected_occasion=occasion,
        detected_budget=budget,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


async def _build_context(
    db: Session,
    session: ChatSession,
    user_id: Optional[str],
    conversation_history: Optional[List],
    occasion: Optional[str],
    budget: Optional[str],
    style_preference: Optional[str],
) -> StylistContext:
    """Build context for the AI stylist."""
    context = StylistContext(
        session_id=str(session.id),
        user_id=user_id,
        detected_occasion=occasion or session.detected_occasion,
        detected_budget=budget or session.detected_budget,
        detected_style=style_preference,
    )
    
    # Get conversation history from session if not provided
    if not conversation_history:
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).order_by(ChatMessage.created_at.desc()).limit(10).all()
        
        context.conversation_history = [
            {"role": msg.role.value, "content": msg.content}
            for msg in reversed(messages)
        ]
    else:
        context.conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in conversation_history
        ]
    
    # Load user profile context if authenticated
    if user_id:
        await _load_user_context(db, user_id, context)
    
    return context


async def _load_user_context(db: Session, user_id: str, context: StylistContext):
    """Load user profile, wardrobe, and preferences into context."""
    from database.models import User, WardrobeItem, Outfit
    from models.profile_models import UserStyleProfile, UserBodyProfile, UserBudgetProfile, UserBrandAffinity
    
    # Load style profile
    style_profile = db.query(UserStyleProfile).filter(
        UserStyleProfile.user_id == user_id
    ).first()
    
    if style_profile:
        context.style_profile = {
            "primary_archetype": style_profile.primary_archetype,
            "fit_preference": style_profile.fit_preference,
            "skin_undertone": style_profile.skin_undertone,
            "preferred_colors": style_profile.preferred_colors,
            "avoided_colors": style_profile.avoided_colors,
        }
    
    # Load body profile
    body_profile = db.query(UserBodyProfile).filter(
        UserBodyProfile.user_id == user_id
    ).first()
    
    if body_profile:
        context.body_profile = {
            "body_shape": body_profile.body_shape,
            "height_cm": body_profile.height_cm,
        }
    
    # Load budget profile
    budget_profile = db.query(UserBudgetProfile).filter(
        UserBudgetProfile.user_id == user_id
    ).first()
    
    if budget_profile:
        context.budget_profile = {
            "per_item_max": float(budget_profile.per_item_max) if budget_profile.per_item_max else None,
        }
    
    # Load brand affinities
    brand_affinities = db.query(UserBrandAffinity).filter(
        UserBrandAffinity.user_id == user_id
    ).limit(5).all()
    
    context.brand_affinities = [
        {"brand_id": b.brand_id, "affinity_score": float(b.affinity_score)}
        for b in brand_affinities
    ]
    
    # Load wardrobe items
    wardrobe_items = db.query(WardrobeItem).filter(
        WardrobeItem.user_id == user_id,
        WardrobeItem.is_active == True
    ).limit(20).all()
    
    context.wardrobe_items = [
        {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "color": item.color,
            "brand": item.brand,
            "image_url": item.image_url,
        }
        for item in wardrobe_items
    ]
    
    # Load recent outfits
    recent_outfits = db.query(Outfit).filter(
        Outfit.user_id == user_id
    ).order_by(Outfit.created_at.desc()).limit(5).all()
    
    context.recent_outfits = [
        {
            "id": outfit.id,
            "title": outfit.title,
            "occasion": outfit.occasion,
            "item_ids": outfit.item_ids,
        }
        for outfit in recent_outfits
    ]


def _save_messages(
    db: Session,
    session_id: str,
    user_message: str,
    response,
):
    """Save messages to database (background task)."""
    try:
        # Save user message
        user_msg = ChatMessage(
            session_id=session_id,
            role=MessageRoleEnum.user,
            content=user_message,
        )
        db.add(user_msg)
        
        # Save assistant message
        assistant_msg = ChatMessage(
            session_id=session_id,
            role=MessageRoleEnum.assistant,
            content=response.content,
            detected_intent=response.detected_occasion,
            tokens_used=response.tokens_used,
            model_version=response.model_version,
            response_time_ms=response.response_time_ms,
        )
        db.add(assistant_msg)
        
        # Update session
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.message_count += 2
            session.last_message_at = datetime.now(timezone.utc)
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error saving messages: {e}")
        db.rollback()


def _format_outfit_suggestions(suggestions: List) -> List[OutfitSuggestion]:
    """Format outfit suggestions for response."""
    if not suggestions:
        return None
    
    formatted = []
    for item in suggestions:
        if isinstance(item, dict):
            formatted.append(OutfitSuggestion(
                id=item.get("id", ""),
                name=item.get("name", ""),
                price=item.get("price", 0),
                styleScore=item.get("styleScore", item.get("style_score", 0)),
                image=item.get("image", ""),
            ))
    
    return formatted if formatted else None
