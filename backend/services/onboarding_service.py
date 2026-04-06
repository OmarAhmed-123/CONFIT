"""
CONFIT Backend — Onboarding Service
===================================
Adaptive onboarding and style quiz system.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from database.session import get_db

from models.profile_models import (
    UserStyleProfile,
    UserOnboardingSession,
    StyleProfileCreate,
    StyleDimensions,
    OnboardingStatusResponse,
    StyleArchetypeResult,
    StyleQuizAnswer,
    StyleQuizSubmission,
)
from services.profile_service import ProfileService, STYLE_ARCHETYPES
from services.confidence_service import ConfidenceService

logger = logging.getLogger(__name__)


ONBOARDING_PHASES = {
    1: {"name": "quick_start", "required": True, "weight": 20},
    2: {"name": "style_quiz", "required": False, "weight": 30},
    3: {"name": "practical", "required": False, "weight": 20},
    4: {"name": "lifestyle", "required": False, "weight": 15},
    5: {"name": "first_outfit", "required": False, "weight": 15},
}

STYLE_QUIZ_QUESTIONS = [
    {
        "id": "q1",
        "type": "image_select",
        "question": "Which outfit speaks to you most?",
        "options": [
            {"id": "opt1", "image": "/quiz/classic-blazer.jpg", "style": "classic"},
            {"id": "opt2", "image": "/quiz/streetwear.jpg", "style": "edgy"},
            {"id": "opt3", "image": "/quiz/bohemian.jpg", "style": "romantic"},
            {"id": "opt4", "image": "/quiz/minimalist.jpg", "style": "minimalist"},
        ],
    },
    {
        "id": "q2",
        "type": "image_select",
        "question": "Pick your ideal weekend look:",
        "options": [
            {"id": "opt1", "image": "/quiz/casual-chic.jpg", "style": "classic"},
            {"id": "opt2", "image": "/quiz/athleisure.jpg", "style": "trendy"},
            {"id": "opt3", "image": "/quiz/flowy-dress.jpg", "style": "romantic"},
            {"id": "opt4", "image": "/quiz/all-black.jpg", "style": "edgy"},
        ],
    },
    {
        "id": "q3",
        "type": "multi_select",
        "question": "Which colors do you gravitate towards?",
        "options": [
            {"id": "neutral", "label": "Neutrals (black, white, beige)", "style": "minimalist"},
            {"id": "earth", "label": "Earth tones (brown, olive, rust)", "style": "romantic"},
            {"id": "bold", "label": "Bold colors (red, yellow, blue)", "style": "maximalist"},
            {"id": "pastel", "label": "Pastels (pink, lavender, mint)", "style": "feminine"},
        ],
    },
    {
        "id": "q4",
        "type": "single_select",
        "question": "How do you feel about patterns?",
        "options": [
            {"id": "solid", "label": "I prefer solid colors", "style": "minimalist"},
            {"id": "subtle", "label": "Subtle patterns are okay", "style": "classic"},
            {"id": "mix", "label": "I love mixing patterns", "style": "maximalist"},
            {"id": "statement", "label": "Statement prints only", "style": "edgy"},
        ],
    },
    {
        "id": "q5",
        "type": "image_select",
        "question": "Choose your power outfit:",
        "options": [
            {"id": "opt1", "image": "/quiz/tailored-suit.jpg", "style": "classic"},
            {"id": "opt2", "image": "/quiz/leather-jacket.jpg", "style": "edgy"},
            {"id": "opt3", "image": "/quiz/flowy-maxi.jpg", "style": "romantic"},
            {"id": "opt4", "image": "/quiz/designer-statement.jpg", "style": "trendy"},
        ],
    },
    {
        "id": "q6",
        "type": "single_select",
        "question": "What's your shopping philosophy?",
        "options": [
            {"id": "investment", "label": "Invest in timeless pieces", "style": "classic"},
            {"id": "trend", "label": "Follow the latest trends", "style": "trendy"},
            {"id": "unique", "label": "Find unique, one-of-a-kind items", "style": "romantic"},
            {"id": "quality", "label": "Quality over quantity", "style": "minimalist"},
        ],
    },
    {
        "id": "q7",
        "type": "multi_select",
        "question": "Which occasions do you dress for most?",
        "options": [
            {"id": "work", "label": "Work/Office"},
            {"id": "casual", "label": "Casual outings"},
            {"id": "date", "label": "Date nights"},
            {"id": "active", "label": "Active/Workout"},
            {"id": "social", "label": "Social events"},
        ],
    },
]


class OnboardingService:
    """Service for managing user onboarding flow."""
    
    def __init__(self, db: Session):
        self._db = db
        self._profile_service = ProfileService(db)
        self._confidence_service = ConfidenceService(db)
    
    def _ensure_session(self, user_id: str) -> UserOnboardingSession:
        session = self._db.query(UserOnboardingSession).filter_by(user_id=user_id).first()
        if not session:
            session = UserOnboardingSession(user_id=user_id)
            self._db.add(session)
            self._db.commit()
            self._db.refresh(session)
        return session
    
    def get_status(self, user_id: str) -> OnboardingStatusResponse:
        session = self._ensure_session(user_id)
        style_profile = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        
        completeness = 0.0
        if style_profile:
            completeness = float(style_profile.profile_completeness or 0)
        
        return OnboardingStatusResponse(
            user_id=user_id,
            current_phase=session.current_phase,
            total_phases=len(ONBOARDING_PHASES),
            completed=session.completed_at is not None,
            skipped_phases=session.skipped_phases or [],
            started_at=session.started_at,
            completed_at=session.completed_at,
            profile_completeness=completeness,
        )
    
    def start(self, user_id: str) -> OnboardingStatusResponse:
        session = self._ensure_session(user_id)
        session.started_at = datetime.now(timezone.utc)
        session.current_phase = 1
        session.last_activity_at = datetime.now(timezone.utc)
        self._db.commit()
        
        return self.get_status(user_id)
    
    def complete_phase(
        self,
        user_id: str,
        phase: int,
        data: Dict[str, Any],
    ) -> OnboardingStatusResponse:
        session = self._ensure_session(user_id)
        
        if phase != session.current_phase:
            logger.warning(f"Phase mismatch: current={session.current_phase}, requested={phase}")
        
        session.phase_data = session.phase_data or {}
        session.phase_data[f"phase_{phase}"] = data
        session.last_activity_at = datetime.now(timezone.utc)
        
        if phase == 1:
            self._process_phase1(user_id, data)
        elif phase == 2:
            self._process_phase2(user_id, data)
        elif phase == 3:
            self._process_phase3(user_id, data)
        elif phase == 4:
            self._process_phase4(user_id, data)
        elif phase == 5:
            self._process_phase5(user_id, data)
        
        if phase < len(ONBOARDING_PHASES):
            session.current_phase = phase + 1
        else:
            session.completed_at = datetime.now(timezone.utc)
            style_profile = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
            if style_profile:
                style_profile.onboarding_completed = True
                style_profile.onboarding_phase = phase
        
        self._db.commit()
        
        self._confidence_service.recalculate(user_id, trigger_event=f"onboarding_phase_{phase}")
        
        return self.get_status(user_id)
    
    def skip_phase(self, user_id: str, phase: int) -> OnboardingStatusResponse:
        session = self._ensure_session(user_id)
        
        skipped = session.skipped_phases or []
        if phase not in skipped:
            skipped.append(phase)
            session.skipped_phases = skipped
        
        if phase < len(ONBOARDING_PHASES):
            session.current_phase = phase + 1
        
        session.last_activity_at = datetime.now(timezone.utc)
        self._db.commit()
        
        return self.get_status(user_id)
    
    def get_quiz_questions(self) -> List[Dict[str, Any]]:
        return STYLE_QUIZ_QUESTIONS
    
    def submit_quiz(
        self,
        user_id: str,
        submission: StyleQuizSubmission,
    ) -> StyleArchetypeResult:
        session = self._ensure_session(user_id)
        
        session.quiz_answers = [a.model_dump() for a in submission.answers]
        
        style_scores = {
            "classic": 0.0,
            "trendy": 0.0,
            "minimalist": 0.0,
            "maximalist": 0.0,
            "feminine": 0.0,
            "masculine": 0.0,
            "edgy": 0.0,
            "romantic": 0.0,
        }
        
        total_selections = 0
        
        for answer in submission.answers:
            question = next((q for q in STYLE_QUIZ_QUESTIONS if q["id"] == answer.question_id), None)
            if not question:
                continue
            
            for opt_id in answer.selected_options:
                option = next((o for o in question["options"] if o["id"] == opt_id), None)
                if option and "style" in option:
                    style_scores[option["style"]] += 1
                    total_selections += 1
            
            for img_id in answer.image_selections:
                option = next((o for o in question["options"] if o["id"] == img_id), None)
                if option and "style" in option:
                    style_scores[option["style"]] += 1.5
                    total_selections += 1
        
        if total_selections > 0:
            for key in style_scores:
                style_scores[key] = min(style_scores[key] / total_selections * 2, 1.0)
        
        dims = StyleDimensions(**style_scores)
        result = self._profile_service.calculate_archetype(user_id)
        
        if result:
            result.dimensions = dims
        
        session.phase_data = session.phase_data or {}
        session.phase_data["phase_2"] = {
            "quiz_completed": True,
            "skipped": submission.skipped,
            "archetype": result.primary if result else None,
        }
        session.last_activity_at = datetime.now(timezone.utc)
        self._db.commit()
        
        return result
    
    def _process_phase1(self, user_id: str, data: Dict[str, Any]) -> None:
        profile_data = StyleProfileCreate()
        
        if "gender_identity" in data:
            pass
        
        if "goals" in data:
            goals = data["goals"]
            if "build_wardrobe" in goals:
                pass
            if "find_style" in goals:
                pass
        
        self._profile_service.update_style_profile(user_id, profile_data, source="onboarding")
    
    def _process_phase2(self, user_id: str, data: Dict[str, Any]) -> None:
        if "archetype" in data:
            profile_data = StyleProfileCreate(primary_archetype=data["archetype"])
            self._profile_service.update_style_profile(user_id, profile_data, source="onboarding")
    
    def _process_phase3(self, user_id: str, data: Dict[str, Any]) -> None:
        from models.profile_models import BodyProfileCreate, BudgetProfileCreate, BrandAffinityCreate
        
        if "body" in data:
            body_data = BodyProfileCreate(**data["body"])
            self._profile_service.update_body_profile(user_id, body_data, source="onboarding")
        
        if "budget" in data:
            budget_data = BudgetProfileCreate(**data["budget"])
            self._profile_service.update_budget_profile(user_id, budget_data, source="onboarding")
        
        if "brands" in data:
            for brand_id in data["brands"]:
                affinity = BrandAffinityCreate(brand_id=brand_id, affinity_score=0.7)
                self._profile_service.add_brand_affinity(user_id, affinity, source="onboarding")
    
    def _process_phase4(self, user_id: str, data: Dict[str, Any]) -> None:
        from models.profile_models import ContextualPreferenceCreate
        
        context_data = ContextualPreferenceCreate(**data)
        self._profile_service.update_contextual_preferences(user_id, context_data, source="onboarding")
    
    def _process_phase5(self, user_id: str, data: Dict[str, Any]) -> None:
        pass
    
    def complete(self, user_id: str) -> OnboardingStatusResponse:
        session = self._ensure_session(user_id)
        session.completed_at = datetime.now(timezone.utc)
        session.last_activity_at = datetime.now(timezone.utc)
        
        style_profile = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        if style_profile:
            style_profile.onboarding_completed = True
            style_profile.onboarding_phase = session.current_phase
        
        self._db.commit()
        
        self._confidence_service.recalculate(user_id, trigger_event="onboarding_complete")
        
        return self.get_status(user_id)


def get_onboarding_service(db: Session = Depends(get_db)) -> OnboardingService:
    return OnboardingService(db)
