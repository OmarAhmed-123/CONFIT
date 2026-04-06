"""
CONFIT Backend — Dataset Export Router
========================================
Public endpoint for exporting backend-ready dataset JSON scaffolding.
Designed for ML pipeline integration and recommendation model training.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_async_session
from services.dataset_export_service import export_sample_dataset

router = APIRouter(prefix="/api/dataset", tags=["Dataset Export"])


@router.get("/sample")
async def get_sample_dataset(
    user_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    # Note: `events` are returned empty scaffolding by design.
    # Clicks/purchases/saves are already tracked across the platform via multiple engagement tables.
    return await export_sample_dataset(db, user_id=user_id)

