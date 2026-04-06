"""
CONFIT Backend — Dataset Export Service
========================================
Builds a backend-ready dataset JSON structure with:
- Users
- Products
- Outfits
- Events

This is designed for ML pipelines and recommendation model training.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database.models import User as UserModel, Product as ProductModel, Outfit as OutfitModel


def _now_ms() -> int:
    return int(time.time() * 1000)


async def export_sample_dataset(db: AsyncSession, user_id: Optional[str] = None) -> Dict[str, Any]:
    # Users (optional)
    users: List[Dict[str, Any]] = []
    if user_id:
        user = (await db.execute(select(UserModel).where(UserModel.id == user_id))).scalar_one_or_none()
        if user:
            users.append(
                {
                    "id": user.id,
                    "style_preferences": user.style_preference or {},
                    "budget_range": user.budget_range or {},
                    "history": [],
                }
            )

    # Products (top by created_at)
    products: List[Dict[str, Any]] = []
    prod_result = await db.execute(select(ProductModel).where(ProductModel.is_active == True).order_by(desc(ProductModel.created_at)).limit(10))
    for p in prod_result.scalars().all():
        products.append(
            {
                "id": str(p.id),
                "category": p.category,
                "color": p.color,
                "style": list(p.tags or []) if isinstance(p.tags, list) else [],
                "price": float(p.price) if p.price is not None else None,
                "brand": None,
            }
        )

    # Outfits (optional: for user)
    outfits: List[Dict[str, Any]] = []
    outfit_q = select(OutfitModel)
    if user_id:
        outfit_q = outfit_q.where(OutfitModel.owner_user_id == user_id)
    outfit_q = outfit_q.order_by(desc(OutfitModel.created_at)).limit(5)
    outfit_result = await db.execute(outfit_q)
    for o in outfit_result.scalars().all():
        outfits.append(
            {
                "id": str(o.id),
                "combination_rules": {"occasion": o.occasion, "season": o.occasion},
                "compatibility_scores": {},
            }
        )

    # Events (scaffolding only)
    # Production event streams are derived from:
    # - Outfit ratings/likes/saves/shares
    # - Product views and affiliate clicks
    events: List[Dict[str, Any]] = []

    return {"users": users, "products": products, "outfits": outfits, "events": events}

