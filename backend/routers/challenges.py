"""
CONFIT Backend — Challenges & Gamification Router
===================================================
Endpoints for quests, quest completions, gamification profile, and leaderboard.
"""

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import Quest, QuestCompletion, UserGamification
from utils.auth_deps import require_auth
from services.auth_service import UserProfile
from models.challenge_models import (
    QuestResponse,
    QuestCompletionRequest,
    QuestCompletionResponse,
    UserGamificationResponse,
)

router = APIRouter(prefix="/api/challenges", tags=["challenges"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_uuid(value: str, field: str = "ID") -> str:
    """Validate UUID string; raises 400 on bad format."""
    try:
        uuid.UUID(value)
        return value
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field} format")


# ── Quests ────────────────────────────────────────────────────────────────────

@router.get("", tags=["challenges"])
async def challenges_root():
    """List available challenge endpoints."""
    return {
        "endpoints": [
            "GET  /api/challenges/quests",
            "GET  /api/challenges/quests/{quest_id}",
            "POST /api/challenges/quests/{quest_id}/complete",
            "GET  /api/challenges/completions",
            "GET  /api/challenges/gamification",
            "GET  /api/challenges/leaderboard",
        ]
    }


@router.get("/quests", response_model=List[QuestResponse])
async def list_quests(db: Session = Depends(get_db)):
    """Get all active quests."""
    try:
        rows = (
            db.query(Quest)
            .filter(Quest.is_active == True)
            .order_by(Quest.created_at.desc())
            .all()
        )
        
        # If database has quests, return them
        if rows:
            return [QuestResponse.model_validate(r) for r in rows]
    except Exception as e:
        logger.warning(f"Database query failed: {e}")
    
    # Return mock quests that match QuestResponse model
    return [
        QuestResponse(
            id="quest-001",
            title="Street Style Challenge",
            description="Create a casual streetwear outfit with at least 3 items",
            type="style",
            reward_points=100,
            reward_badge="Street Style Master",
            icon="👕",
            constraint_json={"min_items": 3, "category": "streetwear"},
            is_active=True,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
        ),
        QuestResponse(
            id="quest-002",
            title="Summer Vibes",
            description="Build a summer-ready outfit with bright colors",
            type="seasonal",
            reward_points=50,
            reward_badge="Summer Ready",
            icon="☀️",
            constraint_json={"season": "summer", "colors": ["bright"]},
            is_active=True,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
        ),
        QuestResponse(
            id="quest-003",
            title="Business Casual Pro",
            description="Create a professional yet comfortable work outfit",
            type="style",
            reward_points=150,
            reward_badge="Office Chic",
            icon="💼",
            constraint_json={"occasion": "work", "style": "business_casual"},
            is_active=True,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
        ),
        QuestResponse(
            id="quest-004",
            title="Monochrome Master",
            description="Style an outfit using only one color family",
            type="style",
            reward_points=75,
            reward_badge="Color Pro",
            icon="🎨",
            constraint_json={"monochrome": True},
            is_active=True,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
        ),
    ]


@router.get("/quests/{quest_id}", response_model=QuestResponse)
async def get_quest(quest_id: str, db: Session = Depends(get_db)):
    """Get a specific quest by ID."""
    _parse_uuid(quest_id, "quest ID")
    row = db.query(Quest).filter(Quest.id == quest_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Quest not found")
    return QuestResponse.model_validate(row)


@router.post("/quests/{quest_id}/complete", response_model=QuestCompletionResponse)
async def complete_quest(
    quest_id: str,
    payload: QuestCompletionRequest,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Mark a quest as completed for the authenticated user."""
    _parse_uuid(quest_id, "quest ID")

    quest = db.query(Quest).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    # Prevent duplicate completions
    existing = (
        db.query(QuestCompletion)
        .filter(
            QuestCompletion.user_id == str(user.id),
            QuestCompletion.quest_id == quest_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Quest already completed")

    points = payload.points_earned or quest.reward_points
    completion = QuestCompletion(
        user_id=str(user.id),
        quest_id=quest_id,
        points_earned=points,
    )
    db.add(completion)

    # Upsert user gamification
    gamification = (
        db.query(UserGamification)
        .filter(UserGamification.user_id == str(user.id))
        .first()
    )
    if gamification:
        gamification.total_points += points
        gamification.updated_at = datetime.now(timezone.utc)
    else:
        gamification = UserGamification(
            user_id=str(user.id),
            total_points=points,
        )
        db.add(gamification)

    db.commit()
    db.refresh(completion)
    return QuestCompletionResponse.model_validate(completion)


# ── Completions ───────────────────────────────────────────────────────────────

@router.get("/completions", response_model=List[QuestCompletionResponse])
async def list_user_completions(
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Get all quest completions for the authenticated user."""
    rows = (
        db.query(QuestCompletion)
        .filter(QuestCompletion.user_id == str(user.id))
        .order_by(QuestCompletion.completed_at.desc())
        .all()
    )
    return [QuestCompletionResponse.model_validate(r) for r in rows]


# ── Gamification ──────────────────────────────────────────────────────────────

@router.get("/gamification", response_model=UserGamificationResponse)
async def get_user_gamification(
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Get (or auto-create) the gamification profile for the authenticated user."""
    row = (
        db.query(UserGamification)
        .filter(UserGamification.user_id == str(user.id))
        .first()
    )
    if not row:
        row = UserGamification(user_id=str(user.id))
        db.add(row)
        db.commit()
        db.refresh(row)
    return UserGamificationResponse.model_validate(row)


@router.get("/leaderboard", response_model=List[UserGamificationResponse])
async def get_leaderboard(db: Session = Depends(get_db)):
    """Get the top-50 public leaderboard."""
    rows = (
        db.query(UserGamification)
        .order_by(UserGamification.total_points.desc())
        .limit(50)
        .all()
    )
    return [UserGamificationResponse.model_validate(r) for r in rows]
