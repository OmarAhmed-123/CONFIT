"""
CONFIT Backend — Enhanced Outfit Service
========================================
Outfit management with AI brain integration,
style scoring, and recommendation features.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal

from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from database.session import get_db

from database.models import Outfit as OutfitModel
from models.outfit_models import OutfitCreate, OutfitUpdate, OutfitResponse
from services.ai_brain_service import AIBrainService

logger = logging.getLogger(__name__)


# ── Style Scoring Constants ─────────────────────────────────────────

STYLE_SCORE_WEIGHTS = {
    "color_harmony": 0.20,
    "occasion_fit": 0.20,
    "style_alignment": 0.15,
    "trend_factor": 0.15,
    "budget_efficiency": 0.10,
    "wardrobe_synergy": 0.10,
    "completeness": 0.10,
}

OCCASION_CATEGORY_REQUIREMENTS = {
    "formal": {"required": ["top", "bottom", "shoes"], "optional": ["accessory", "outerwear"]},
    "work": {"required": ["top", "bottom", "shoes"], "optional": ["accessory", "outerwear"]},
    "party": {"required": ["top", "bottom", "shoes"], "optional": ["accessory"]},
    "date": {"required": ["top", "bottom", "shoes"], "optional": ["accessory", "outerwear"]},
    "casual": {"required": ["top", "bottom"], "optional": ["shoes", "accessory"]},
    "active": {"required": ["top", "bottom", "shoes"], "optional": ["accessory"]},
}

COLOR_HARMONY_MATRIX = {
    # Complementary pairs (high contrast)
    ("blue", "orange"): {"type": "complementary", "score": 0.95},
    ("red", "green"): {"type": "complementary", "score": 0.90},
    ("yellow", "purple"): {"type": "complementary", "score": 0.90},
    
    # Analogous pairs (harmonious)
    ("blue", "green"): {"type": "analogous", "score": 0.95},
    ("blue", "purple"): {"type": "analogous", "score": 0.92},
    ("red", "orange"): {"type": "analogous", "score": 0.92},
    ("yellow", "orange"): {"type": "analogous", "score": 0.90},
    ("green", "yellow"): {"type": "analogous", "score": 0.88},
    
    # Neutral pairs (safe)
    ("black", "white"): {"type": "neutral", "score": 0.98},
    ("black", "grey"): {"type": "neutral", "score": 0.95},
    ("navy", "white"): {"type": "neutral", "score": 0.95},
    ("beige", "black"): {"type": "neutral", "score": 0.92},
    ("grey", "white"): {"type": "neutral", "score": 0.90},
}


class EnhancedOutfitService:
    """
    Enhanced outfit service with AI-powered features:
    - Multi-dimensional style scoring
    - Color harmony validation
    - Occasion appropriateness checking
    - Trend alignment scoring
    - Budget efficiency calculation
    - Wardrobe synergy detection
    """
    
    def __init__(self, db: Session, ai_brain: AIBrainService = None):
        self._db = db
        self._ai_brain = ai_brain
    
    # ── Core CRUD Operations ─────────────────────────────────────────
    
    def create_outfit(
        self,
        user_id: str,
        payload: OutfitCreate,
        calculate_scores: bool = True,
    ) -> OutfitResponse:
        """Create outfit with optional AI scoring."""
        now = datetime.now(timezone.utc)
        outfit_id = f"outfit-{uuid.uuid4().hex[:8]}"
        share_slug = uuid.uuid4().hex[:10]
        
        items = [i.model_dump() for i in payload.items]
        total_price = self._compute_total_price(items)
        currency = payload.items[0].currency if payload.items else "USD"
        
        # Calculate style scores if AI brain available
        style_scores = {}
        overall_score = 0.0
        
        if calculate_scores and self._ai_brain:
            style_scores = self._calculate_style_scores(
                user_id, items, payload.occasion, total_price
            )
            overall_score = sum(
                style_scores.get(k, 0) * STYLE_SCORE_WEIGHTS.get(k, 0)
                for k in STYLE_SCORE_WEIGHTS
            )
        
        row = OutfitModel(
            id=outfit_id,
            owner_user_id=user_id,
            title=payload.title,
            items=items,
            occasion=payload.occasion,
            notes=payload.notes,
            budget_limit=payload.budget_limit,
            total_price=total_price,
            currency=currency,
            share_slug=share_slug,
            created_at=now,
            updated_at=now,
        )
        
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        
        # Track outfit creation as behavior signal
        if self._ai_brain:
            self._ai_brain.track_interaction(
                user_id=user_id,
                interaction_type="outfit_create",
                entity_type="outfit",
                entity_id=outfit_id,
                context={
                    "occasion": payload.occasion,
                    "item_count": len(items),
                    "total_price": total_price,
                    "style_score": overall_score,
                },
            )
        
        logger.info("Outfit created for %s: %s (score: %.1f)", user_id, outfit_id, overall_score)
        
        response = self._row_to_response(row)
        response.style_scores = style_scores
        response.overall_score = overall_score
        
        return response
    
    def list_outfits(
        self,
        user_id: str,
        occasion: str = None,
        min_score: float = None,
        limit: int = 50,
    ) -> List[OutfitResponse]:
        """List outfits with optional filtering."""
        query = self._db.query(OutfitModel).filter(
            OutfitModel.owner_user_id == user_id
        )
        
        if occasion:
            query = query.filter(OutfitModel.occasion == occasion)
        
        rows = query.order_by(OutfitModel.updated_at.desc()).limit(limit).all()
        
        return [self._row_to_response(r) for r in rows]
    
    def get_outfit(self, user_id: str, outfit_id: str) -> Optional[OutfitResponse]:
        """Get single outfit by ID."""
        row = self._db.query(OutfitModel).filter(
            and_(
                OutfitModel.id == outfit_id,
                OutfitModel.owner_user_id == user_id,
            )
        ).first()
        
        return self._row_to_response(row) if row else None
    
    def update_outfit(
        self,
        user_id: str,
        outfit_id: str,
        payload: OutfitUpdate,
        recalculate_scores: bool = True,
    ) -> Optional[OutfitResponse]:
        """Update outfit with optional score recalculation."""
        row = self._db.query(OutfitModel).filter(
            and_(
                OutfitModel.id == outfit_id,
                OutfitModel.owner_user_id == user_id,
            )
        ).first()
        
        if not row:
            return None
        
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        
        if "title" in updates:
            row.title = updates["title"]
        if "occasion" in updates:
            row.occasion = updates["occasion"]
        if "notes" in updates:
            row.notes = updates["notes"]
        if "budget_limit" in updates:
            row.budget_limit = updates["budget_limit"]
        if "items" in updates:
            raw = updates["items"]
            items = [i.model_dump() if hasattr(i, "model_dump") else i for i in raw]
            row.items = items
            row.total_price = self._compute_total_price(items)
            if items:
                row.currency = items[0].get("currency", "USD")
        
        row.updated_at = datetime.now(timezone.utc)
        
        self._db.commit()
        self._db.refresh(row)
        
        # Track update
        if self._ai_brain:
            self._ai_brain.track_interaction(
                user_id=user_id,
                interaction_type="outfit_update",
                entity_type="outfit",
                entity_id=outfit_id,
            )
        
        logger.info("Outfit updated for %s: %s", user_id, outfit_id)
        
        return self._row_to_response(row)
    
    def delete_outfit(self, user_id: str, outfit_id: str) -> bool:
        """Delete outfit and track deletion."""
        row = self._db.query(OutfitModel).filter(
            and_(
                OutfitModel.id == outfit_id,
                OutfitModel.owner_user_id == user_id,
            )
        ).first()
        
        if not row:
            return False
        
        # Track deletion before removing
        if self._ai_brain:
            self._ai_brain.track_interaction(
                user_id=user_id,
                interaction_type="outfit_delete",
                entity_type="outfit",
                entity_id=outfit_id,
            )
        
        self._db.delete(row)
        self._db.commit()
        
        logger.info("Outfit deleted for %s: %s", user_id, outfit_id)
        return True
    
    def get_outfit_by_slug(self, share_slug: str) -> Optional[OutfitResponse]:
        """Get outfit by share slug (public access)."""
        row = self._db.query(OutfitModel).filter(
            OutfitModel.share_slug == share_slug
        ).first()
        
        return self._row_to_response(row) if row else None
    
    # ── AI-Powered Features ───────────────────────────────────────────
    
    def _calculate_style_scores(
        self,
        user_id: str,
        items: List[dict],
        occasion: str,
        total_price: float,
    ) -> Dict[str, float]:
        """Calculate multi-dimensional style scores."""
        scores = {
            "color_harmony": 0.0,
            "occasion_fit": 0.0,
            "style_alignment": 0.0,
            "trend_factor": 0.0,
            "budget_efficiency": 0.0,
            "wardrobe_synergy": 0.0,
            "completeness": 0.0,
        }
        
        if not items:
            return scores
        
        # Color harmony score
        colors = [i.get("color", "").lower() for i in items if i.get("color")]
        scores["color_harmony"] = self._score_color_harmony(colors)
        
        # Occasion fit score
        if occasion:
            scores["occasion_fit"] = self._score_occasion_fit(items, occasion)
        
        # Style alignment (would use user's style vector)
        scores["style_alignment"] = 75.0  # Placeholder
        
        # Trend factor
        scores["trend_factor"] = self._score_trend_alignment(items)
        
        # Budget efficiency
        scores["budget_efficiency"] = 80.0  # Placeholder
        
        # Wardrobe synergy
        scores["wardrobe_synergy"] = 70.0  # Placeholder
        
        # Completeness
        scores["completeness"] = self._score_completeness(items, occasion)
        
        return scores
    
    def _score_color_harmony(self, colors: List[str]) -> float:
        """Score color combination harmony."""
        if len(colors) < 2:
            return 100.0  # Single color is always harmonious
        
        # Check each pair
        pair_scores = []
        for i, color1 in enumerate(colors):
            for color2 in colors[i+1:]:
                pair_key = tuple(sorted([color1, color2]))
                if pair_key in COLOR_HARMONY_MATRIX:
                    pair_scores.append(COLOR_HARMONY_MATRIX[pair_key]["score"] * 100)
                else:
                    # Check for neutral colors
                    neutral_colors = {"black", "white", "grey", "gray", "navy", "beige", "cream"}
                    if color1 in neutral_colors or color2 in neutral_colors:
                        pair_scores.append(85.0)
                    else:
                        pair_scores.append(60.0)  # Unknown combination
        
        return sum(pair_scores) / len(pair_scores) if pair_scores else 70.0
    
    def _score_occasion_fit(self, items: List[dict], occasion: str) -> float:
        """Score how well outfit fits the occasion."""
        requirements = OCCASION_CATEGORY_REQUIREMENTS.get(occasion, {})
        required = requirements.get("required", [])
        
        if not required:
            return 80.0
        
        # Check which required categories are filled
        item_categories = {i.get("category", "").lower() for i in items}
        
        filled_required = sum(1 for cat in required if cat in item_categories)
        completeness = filled_required / len(required) if required else 1.0
        
        return completeness * 100
    
    def _score_trend_alignment(self, items: List[dict]) -> float:
        """Score alignment with current trends."""
        # Would integrate with trend data from AI brain
        trending_keywords = {
            "oversized", "wide-leg", "chunky", "structured", "minimalist",
            "sage", "terracotta", "burgundy", "navy", "cream",
        }
        
        score = 50.0  # Base score
        
        for item in items:
            name = item.get("name", "").lower()
            for keyword in trending_keywords:
                if keyword in name:
                    score += 5
        
        return min(score, 100.0)
    
    def _score_completeness(self, items: List[dict], occasion: str) -> float:
        """Score outfit completeness."""
        requirements = OCCASION_CATEGORY_REQUIREMENTS.get(occasion, {})
        required = requirements.get("required", ["top", "bottom", "shoes"])
        
        item_categories = {i.get("category", "").lower() for i in items}
        
        filled = sum(1 for cat in required if cat in item_categories)
        
        return (filled / len(required)) * 100 if required else 100.0
    
    def get_style_suggestions(
        self,
        user_id: str,
        outfit_id: str,
    ) -> List[Dict[str, Any]]:
        """Get AI-powered style suggestions for improving an outfit."""
        outfit = self.get_outfit(user_id, outfit_id)
        
        if not outfit:
            return []
        
        suggestions = []
        items = outfit.items
        
        # Check for missing categories
        categories = {i.get("category", "").lower() for i in items}
        
        requirements = OCCASION_CATEGORY_REQUIREMENTS.get(outfit.occasion, {})
        required = requirements.get("required", [])
        optional = requirements.get("optional", [])
        
        for cat in required:
            if cat not in categories:
                suggestions.append({
                    "type": "missing_required",
                    "category": cat,
                    "message": f"Consider adding {cat} to complete this look",
                    "priority": "high",
                })
        
        for cat in optional:
            if cat not in categories:
                suggestions.append({
                    "type": "missing_optional",
                    "category": cat,
                    "message": f"A {cat} could elevate this outfit",
                    "priority": "medium",
                })
        
        # Color suggestions
        colors = [i.get("color", "").lower() for i in items if i.get("color")]
        if len(colors) >= 2:
            harmony = self._score_color_harmony(colors)
            if harmony < 70:
                suggestions.append({
                    "type": "color_improvement",
                    "message": "Consider adjusting colors for better harmony",
                    "current_score": harmony,
                    "priority": "medium",
                })
        
        return suggestions
    
    def get_similar_outfits(
        self,
        user_id: str,
        outfit_id: str,
        limit: int = 5,
    ) -> List[OutfitResponse]:
        """Find similar outfits the user has created."""
        outfit = self.get_outfit(user_id, outfit_id)
        
        if not outfit:
            return []
        
        # Find outfits with same occasion
        similar = self._db.query(OutfitModel).filter(
            and_(
                OutfitModel.owner_user_id == user_id,
                OutfitModel.id != outfit_id,
                OutfitModel.occasion == outfit.occasion,
            )
        ).limit(limit).all()
        
        return [self._row_to_response(r) for r in similar]
    
    def duplicate_outfit(
        self,
        user_id: str,
        outfit_id: str,
        new_title: str = None,
    ) -> Optional[OutfitResponse]:
        """Duplicate an existing outfit."""
        original = self.get_outfit(user_id, outfit_id)
        
        if not original:
            return None
        
        create_payload = OutfitCreate(
            title=new_title or f"{original.title} (Copy)",
            items=original.items,
            occasion=original.occasion,
            notes=original.notes,
            budget_limit=original.budget_limit,
        )
        
        return self.create_outfit(user_id, create_payload)
    
    # ── Helper Methods ───────────────────────────────────────────────
    
    def _compute_total_price(self, items: List[dict]) -> Optional[float]:
        """Calculate total price of items."""
        values = []
        for item in items:
            price = item.get("price")
            if price is None:
                continue
            try:
                values.append(float(price))
            except (TypeError, ValueError):
                continue
        return round(sum(values), 2) if values else None
    
    def _row_to_response(self, row: OutfitModel) -> OutfitResponse:
        """Convert ORM row to response model."""
        return OutfitResponse(
            id=row.id,
            owner_user_id=row.owner_user_id,
            title=row.title,
            items=row.items or [],
            occasion=row.occasion,
            notes=row.notes,
            budget_limit=row.budget_limit,
            total_price=row.total_price,
            currency=row.currency or "USD",
            created_at=row.created_at,
            updated_at=row.updated_at,
            share_slug=row.share_slug,
        )


def get_enhanced_outfit_service(db: Session = Depends(get_db)) -> EnhancedOutfitService:
    """Factory function for enhanced outfit service."""
    from services.ai_brain_service import get_ai_brain_service
    ai_brain = get_ai_brain_service(db)
    return EnhancedOutfitService(db, ai_brain)
