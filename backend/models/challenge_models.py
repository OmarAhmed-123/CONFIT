"""
CONFIT Backend — Challenge & Gamification Pydantic Models
==========================================================
Shared response/request schemas used by routers/challenges.py.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Quest ─────────────────────────────────────────────────────────────────────

class QuestResponse(BaseModel):
    id: str
    title: str
    description: str
    type: str
    reward_points: int
    reward_badge: Optional[str] = None
    icon: str
    constraint_json: dict
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestCompletionRequest(BaseModel):
    points_earned: int = Field(default=0, ge=0)


class QuestCompletionResponse(BaseModel):
    id: str
    quest_id: str
    points_earned: int
    completed_at: datetime

    model_config = {"from_attributes": True}


# ── Gamification ──────────────────────────────────────────────────────────────

class UserGamificationResponse(BaseModel):
    id: str
    total_points: int
    confidence_score: float
    level: int
    badges: List[str]
    current_streak: int
    longest_streak: int
    updated_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Legacy models (kept for backward-compat with old challenge endpoints) ─────

class DailyQuestResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    conditions: dict = {}
    starts_at: datetime
    ends_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class QuestSubmitRequest(BaseModel):
    outfit_id: Optional[str] = None
    image_url: Optional[str] = None


class QuestSubmitResponse(BaseModel):
    success: bool
    submission_id: str
    score: float
    message: str


class LeaderboardEntry(BaseModel):
    user_id: str
    score: float
    created_at: datetime


class LeaderboardResponse(BaseModel):
    quest_id: str
    entries: List[LeaderboardEntry]
