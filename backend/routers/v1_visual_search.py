"""
CONFIT Backend — SNAP & STYLE Visual Search v1 Router
======================================================
POST /api/v1/search/visual  — Search by uploaded image
GET  /api/v1/search/text    — Search by text query
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from pydantic import BaseModel, Field

from database.session import get_db
from services.ai.visual_search_service import VisualSearchService
from services.ai.cost_tracker import get_cost_tracker
from utils.auth_deps import require_auth
from services.auth_service import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["SNAP & STYLE — Visual Search"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
VISUAL_SEARCH_DAILY_LIMIT = 30


# ── Schemas ──────────────────────────────────────────────────────────

class AttributeSchema(BaseModel):
    type: Optional[str] = None
    color: list[str] = []
    style: list[str] = []
    pattern: list[str] = []


class MatchedProduct(BaseModel):
    product_id: str
    sku: Optional[str] = None
    name: str
    brand: Optional[str] = None
    price: Optional[float] = None
    currency: str = "USD"
    image_url: Optional[str] = None
    similarity_score: float = 0.0
    matched_attributes: list[str] = []


class VisualSearchResponse(BaseModel):
    session_id: str
    attributes: AttributeSchema = AttributeSchema()
    matches: list[MatchedProduct] = []
    total_results: int = 0
    processing_time_ms: float = 0.0


class TextSearchResponse(BaseModel):
    results: list[MatchedProduct] = []
    total_results: int = 0


# ── Helpers ──────────────────────────────────────────────────────────

def _get_service(db=Depends(get_db)) -> VisualSearchService:
    from core.redis_client import get_redis_client
    redis = get_redis_client()
    service = VisualSearchService(db, redis)
    tracker = get_cost_tracker(db, redis)
    service.set_cost_tracker(tracker)
    return service


async def _check_visual_search_rate_limit(user_id: str, redis) -> tuple[bool, int]:
    """30/day per user."""
    if not redis:
        return True, 0
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"visual_search:ratelimit:{user_id}:{today}"
    try:
        current = redis.get(key)
        if current is None:
            redis.setex(key, 86400, 1)
            return True, 0
        count = int(current)
        if count >= VISUAL_SEARCH_DAILY_LIMIT:
            return False, 86400
        redis.incr(key)
        return True, 0
    except Exception:
        return True, 0


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/visual", response_model=VisualSearchResponse)
async def visual_search(
    file: UploadFile = File(..., description="Image to search (JPEG/PNG/WebP)"),
    limit: int = Query(20, ge=1, le=50),
    category: Optional[str] = Query(None),
    user: UserProfile = Depends(require_auth),
    service: VisualSearchService = Depends(_get_service),
):
    """
    SNAP & STYLE: Upload an image to find visually similar products.

    Uses Google Vision API for labels + CLIP embeddings + pgvector.
    Rate-limited: 30/day per user.
    """
    from core.redis_client import get_redis_client
    redis = get_redis_client()
    allowed, retry_after = await _check_visual_search_rate_limit(str(user.id), redis)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={"message": "Daily visual search limit reached.", "retry_after_seconds": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    # Budget kill-switch
    if service._cost_tracker and service._cost_tracker.is_kill_switch_active():
        raise HTTPException(503, "AI services temporarily unavailable due to budget limits.")

    # Validate file
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Invalid file type. Please upload an image.")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Maximum: {MAX_FILE_SIZE // (1024*1024)} MB")
    if len(contents) < 100:
        raise HTTPException(400, "File appears to be empty or too small.")

    filters = {}
    if category:
        filters["category"] = category

    result = await service.search_by_image(
        image_bytes=contents,
        user_id=str(user.id),
        filters=filters if filters else None,
        limit=limit,
    )

    attributes = AttributeSchema()
    if result.query_attributes:
        a = result.query_attributes
        attributes = AttributeSchema(
            type=a.category,
            color=a.colors,
            style=a.styles,
            pattern=a.patterns,
        )

    matches = [
        MatchedProduct(
            product_id=r.product_id,
            sku=r.sku,
            name=r.name,
            brand=r.brand,
            price=r.price,
            currency=r.currency,
            image_url=r.image_url,
            similarity_score=r.similarity_score,
            matched_attributes=r.matched_attributes,
        )
        for r in result.results
    ]

    return VisualSearchResponse(
        session_id=result.session_id,
        attributes=attributes,
        matches=matches,
        total_results=result.total_results,
        processing_time_ms=result.processing_time_ms,
    )


@router.get("/text", response_model=TextSearchResponse)
async def text_search(
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(20, ge=1, le=50),
    category: Optional[str] = Query(None),
    user: UserProfile = Depends(require_auth),
    service: VisualSearchService = Depends(_get_service),
):
    """
    Text-based product search using embeddings + pgvector.
    """
    from core.redis_client import get_redis_client
    redis = get_redis_client()
    allowed, retry_after = await _check_visual_search_rate_limit(str(user.id), redis)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={"message": "Daily search limit reached.", "retry_after_seconds": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    filters = {}
    if category:
        filters["category"] = category

    result = await service.search_by_text(
        query=q,
        user_id=str(user.id),
        filters=filters if filters else None,
        limit=limit,
    )

    return TextSearchResponse(
        results=[
            MatchedProduct(
                product_id=r.product_id,
                sku=r.sku,
                name=r.name,
                brand=r.brand,
                price=r.price,
                currency=r.currency,
                image_url=r.image_url,
                similarity_score=r.similarity_score,
                matched_attributes=r.matched_attributes,
            )
            for r in result.results
        ],
        total_results=result.total_results,
    )
