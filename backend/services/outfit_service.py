"""
CONFIT Backend — Outfit Service
=================================
Outfit management backed by the database.
Use via dependency injection with a DB session.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from database.models import Outfit as OutfitModel
from models.outfit_models import OutfitCreate, OutfitUpdate, OutfitResponse

logger = logging.getLogger(__name__)


def _compute_total_price(items: List[dict]) -> Optional[float]:
    values: List[float] = []
    for item in items:
        price = item.get("price")
        if price is None:
            continue
        try:
            values.append(float(price))
        except (TypeError, ValueError):
            continue
    return round(sum(values), 2) if values else None


def _outfit_row_to_response(row: OutfitModel) -> OutfitResponse:
    """Map ORM row to OutfitResponse."""
    items = row.items or []
    return OutfitResponse(
        id=row.id,
        owner_user_id=row.owner_user_id,
        title=row.title,
        items=items,
        occasion=row.occasion,
        notes=row.notes,
        budget_limit=row.budget_limit,
        total_price=row.total_price,
        currency=row.currency or "USD",
        created_at=row.created_at,
        updated_at=row.updated_at,
        share_slug=row.share_slug,
    )


class OutfitService:
    """Outfit management with database persistence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_outfit(self, user_id: str, payload: OutfitCreate) -> OutfitResponse:
        now = datetime.now(timezone.utc)
        outfit_id = f"outfit-{uuid.uuid4().hex[:8]}"
        share_slug = uuid.uuid4().hex[:10]

        items = [i.model_dump() for i in payload.items]
        total_price = _compute_total_price(items)
        currency = payload.items[0].currency if payload.items else "USD"

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
        logger.info("Outfit created for %s: %s", user_id, outfit_id)
        return _outfit_row_to_response(row)

    def list_outfits(self, user_id: str) -> List[OutfitResponse]:
        rows = (
            self._db.query(OutfitModel)
            .filter(OutfitModel.owner_user_id == user_id)
            .order_by(OutfitModel.updated_at.desc())
            .all()
        )
        return [_outfit_row_to_response(r) for r in rows]

    def get_outfit(self, user_id: str, outfit_id: str) -> Optional[OutfitResponse]:
        row = (
            self._db.query(OutfitModel)
            .filter(OutfitModel.id == outfit_id, OutfitModel.owner_user_id == user_id)
            .first()
        )
        return _outfit_row_to_response(row) if row else None

    def update_outfit(
        self,
        user_id: str,
        outfit_id: str,
        payload: OutfitUpdate,
    ) -> Optional[OutfitResponse]:
        row = (
            self._db.query(OutfitModel)
            .filter(OutfitModel.id == outfit_id, OutfitModel.owner_user_id == user_id)
            .first()
        )
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
            row.total_price = _compute_total_price(items)
            if items:
                row.currency = items[0].get("currency", "USD")

        row.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(row)
        logger.info("Outfit updated for %s: %s", user_id, outfit_id)
        return _outfit_row_to_response(row)

    def delete_outfit(self, user_id: str, outfit_id: str) -> bool:
        row = (
            self._db.query(OutfitModel)
            .filter(OutfitModel.id == outfit_id, OutfitModel.owner_user_id == user_id)
            .first()
        )
        if not row:
            return False
        self._db.delete(row)
        self._db.commit()
        logger.info("Outfit deleted for %s: %s", user_id, outfit_id)
        return True

    def get_outfit_by_slug(self, share_slug: str) -> Optional[OutfitResponse]:
        """Look up an outfit by its shareable slug (public, no owner)."""
        row = self._db.query(OutfitModel).filter(OutfitModel.share_slug == share_slug).first()
        if not row:
            return None
        resp = _outfit_row_to_response(row)
        # Optionally hide owner in shared view
        return resp
