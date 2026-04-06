"""
CONFIT Backend - AI Services API Endpoints
===========================================
FastAPI endpoints for MUSE, MIRROR, Visual Search, and Wardrobe services.

Features:
- Rate limiting via slowapi
- Cost tracking integration
- Authentication via JWT
- Request validation with Pydantic
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, 
    BackgroundTasks, Query, Path, Body
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from database.database import get_db
from core.redis_client import get_redis_client
from core.auth import get_current_user, get_current_user_id
from services.ai.muse_service import MuseService
from services.ai.mirror_service import MirrorService, TryOnRequest
from services.ai.visual_search_service import VisualSearchService
from services.ai.wardrobe_service import WardrobeService
from services.ai.cost_tracker import AICostTracker, get_cost_tracker

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Routers
muse_router = APIRouter(prefix="/muse", tags=["MUSE - Virtual Stylist"])
mirror_router = APIRouter(prefix="/mirror", tags=["MIRROR - Virtual Try-On"])
visualsearch_router = APIRouter(prefix="/visual-search", tags=["Visual Search"])
wardrobe_router = APIRouter(prefix="/wardrobe", tags=["MY CLOSET - Wardrobe"])
ai_admin_router = APIRouter(prefix="/ai-admin", tags=["AI Admin"])


# ==========================================
# Request/Response Models
# ==========================================

class MuseChatRequest(BaseModel):
    """MUSE chat request."""
    message: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="en", pattern="^(en|ar)$")
    session_id: Optional[str] = None


class MuseChatResponse(BaseModel):
    """MUSE chat response."""
    reply: str
    outfits: List[Dict[str, Any]] = []
    follow_ups: List[str] = []
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    session_id: str


class TryOnStartRequest(BaseModel):
    """Start try-on request."""
    product_id: str
    product_sku: str
    category: Optional[str] = "tops"


class TryOnStartResponse(BaseModel):
    """Start try-on response."""
    session_id: str
    status: str
    message: str


class TryOnStatusResponse(BaseModel):
    """Try-on status response."""
    session_id: str
    status: str
    result_url: Optional[str] = None
    quality_score: float = 0.0
    error_message: Optional[str] = None
    cost_usd: float = 0.0
    latency_ms: float = 0.0


class VisualSearchResponse(BaseModel):
    """Visual search response."""
    session_id: str
    query_attributes: Optional[Dict[str, Any]] = None
    results: List[Dict[str, Any]] = []
    total_results: int = 0
    processing_time_ms: float = 0.0


class WardrobeItemAdd(BaseModel):
    """Add wardrobe item request."""
    name: Optional[str] = None
    category: Optional[str] = None


class WardrobeItemResponse(BaseModel):
    """Wardrobe item response."""
    id: str
    name: str
    category: str
    subcategory: Optional[str] = None
    colors: List[str] = []
    patterns: List[str] = []
    materials: List[str] = []
    tags: List[str] = []
    image_url: Optional[str] = None
    is_favorite: bool = False


class DuplicateCheckResponse(BaseModel):
    """Duplicate check response."""
    alerts: List[Dict[str, Any]] = []
    has_duplicates: bool = False


class BudgetStatusResponse(BaseModel):
    """Budget status response."""
    daily_budget_usd: float
    spent_usd: float
    remaining_usd: float
    percent_used: float
    is_warning: bool
    is_exceeded: bool
    kill_switch_active: bool


class CostReportResponse(BaseModel):
    """Cost report response."""
    start_date: str
    end_date: str
    group_by: str
    total_cost_usd: float
    total_calls: int
    groups: List[Dict[str, Any]] = []


# ==========================================
# MUSE - Virtual Stylist Endpoints
# ==========================================

@muse_router.post("/chat", response_model=MuseChatResponse)
@limiter.limit("20/hour")
async def muse_chat(
    request: MuseChatRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """
    Chat with MUSE virtual stylist.
    
    Rate limit: 20 messages per hour (free tier).
    """
    user_id = str(current_user["id"])
    user_tier = current_user.get("tier", "free")
    
    redis = get_redis_client()
    service = MuseService(db, redis)
    
    # Set cost tracker
    cost_tracker = get_cost_tracker(db, redis)
    service.set_cost_tracker(cost_tracker)
    
    # Check rate limit
    allowed, retry_after = await service.check_rate_limit(user_id, user_tier)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds."
        )
    
    # Check budget kill-switch
    if cost_tracker.is_kill_switch_active():
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable due to budget limits."
        )
    
    response = await service.chat(
        user_id=user_id,
        message=request.message,
        language=request.language,
        session_id=request.session_id,
    )
    
    return MuseChatResponse(
        reply=response.reply,
        outfits=[{
            "outfit_id": o.outfit_id,
            "title": o.title,
            "items": o.items,
            "total_price": o.total_price,
            "occasion": o.occasion,
            "styling_tips": o.styling_tips,
        } for o in response.outfits],
        follow_ups=response.follow_ups,
        tokens_in=response.tokens_in,
        tokens_out=response.tokens_out,
        cost_usd=response.cost_usd,
        latency_ms=response.latency_ms,
        session_id=response.session_id,
    )


@muse_router.get("/session/{session_id}/history")
async def get_muse_session_history(
    session_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """Get conversation history for a MUSE session."""
    redis = get_redis_client()
    service = MuseService(db, redis)
    
    history = await service.get_session_history(session_id)
    
    return {"session_id": session_id, "messages": history}


@muse_router.delete("/session/{session_id}")
async def clear_muse_session(
    session_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """Clear a MUSE session's context."""
    redis = get_redis_client()
    service = MuseService(db, redis)
    
    success = await service.clear_session(session_id)
    
    return {"success": success, "session_id": session_id}


# ==========================================
# MIRROR - Virtual Try-On Endpoints
# ==========================================

@mirror_router.post("/start", response_model=TryOnStartResponse)
@limiter.limit("10/day")
async def start_tryon(
    request: TryOnStartRequest,
    person_image: UploadFile = File(..., description="User's photo"),
    garment_image: Optional[UploadFile] = File(None, description="Garment image (optional if product has image)"),
    background_tasks: BackgroundTasks = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """
    Start a virtual try-on session.
    
    Uploads user photo and queues processing via Celery.
    Rate limit: 10 per day (free tier).
    """
    user_id = str(current_user["id"])
    user_tier = current_user.get("tier", "free")
    
    # Validate image
    if not person_image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid image format")
    
    redis = get_redis_client()
    service = MirrorService(db, redis)
    
    # Check rate limit
    allowed, retry_after = await service.check_rate_limit(user_id, user_tier)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Daily try-on limit exceeded. Try again tomorrow."
        )
    
    # Read images
    person_bytes = await person_image.read()
    garment_bytes = await garment_image.read() if garment_image else None
    
    # Create request
    tryon_request = TryOnRequest(
        user_id=user_id,
        product_id=request.product_id,
        product_sku=request.product_sku,
        person_image_bytes=person_bytes,
        garment_image_bytes=garment_bytes,
        category=request.category,
    )
    
    # Start try-on
    session = await service.start_tryon(tryon_request, background_tasks)
    
    return TryOnStartResponse(
        session_id=session.session_id,
        status=session.status.value,
        message="Try-on session started. Poll /status for results.",
    )


@mirror_router.get("/status/{session_id}", response_model=TryOnStatusResponse)
async def get_tryon_status(
    session_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """Get the status of a try-on session."""
    redis = get_redis_client()
    service = MirrorService(db, redis)
    
    result = await service.get_result(session_id)
    
    return TryOnStatusResponse(
        session_id=result.session_id,
        status=result.status.value,
        result_url=result.result_url,
        quality_score=result.quality_score,
        error_message=result.error_message,
        cost_usd=result.cost_usd,
        latency_ms=result.latency_ms,
    )


@mirror_router.get("/wait/{session_id}", response_model=TryOnStatusResponse)
async def wait_for_tryon(
    session_id: str = Path(...),
    timeout: int = Query(default=120, ge=10, le=300),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """Wait for try-on completion (long polling)."""
    redis = get_redis_client()
    service = MirrorService(db, redis)
    
    result = await service.wait_for_result(session_id, timeout=timeout)
    
    return TryOnStatusResponse(
        session_id=result.session_id,
        status=result.status.value,
        result_url=result.result_url,
        quality_score=result.quality_score,
        error_message=result.error_message,
        cost_usd=result.cost_usd,
        latency_ms=result.latency_ms,
    )


# ==========================================
# Visual Search Endpoints
# ==========================================

@visualsearch_router.post("/image", response_model=VisualSearchResponse)
@limiter.limit("30/day")
async def search_by_image(
    image: UploadFile = File(..., description="Query image"),
    category: Optional[str] = Query(None),
    max_price: Optional[float] = Query(None),
    min_price: Optional[float] = Query(None),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """
    Search for similar products by image.
    
    Rate limit: 30 per day (free tier).
    """
    user_id = str(current_user["id"])
    
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid image format")
    
    redis = get_redis_client()
    service = VisualSearchService(db, redis)
    
    # Set cost tracker
    cost_tracker = get_cost_tracker(db, redis)
    service.set_cost_tracker(cost_tracker)
    
    # Check rate limit
    allowed, retry_after = await service.check_rate_limit(user_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Daily search limit exceeded. Try again tomorrow."
        )
    
    image_bytes = await image.read()
    
    filters = {}
    if category:
        filters["category"] = category
    if max_price:
        filters["max_price"] = max_price
    if min_price:
        filters["min_price"] = min_price
    
    response = await service.search_by_image(
        image_bytes=image_bytes,
        user_id=user_id,
        filters=filters,
        limit=limit,
    )
    
    return VisualSearchResponse(
        session_id=response.session_id,
        query_attributes={
            "category": response.query_attributes.category if response.query_attributes else None,
            "colors": response.query_attributes.colors if response.query_attributes else [],
            "patterns": response.query_attributes.patterns if response.query_attributes else [],
        } if response.query_attributes else None,
        results=[{
            "product_id": r.product_id,
            "sku": r.sku,
            "name": r.name,
            "brand": r.brand,
            "price": r.price,
            "currency": r.currency,
            "image_url": r.image_url,
            "similarity_score": r.similarity_score,
        } for r in response.results],
        total_results=response.total_results,
        processing_time_ms=response.processing_time_ms,
    )


@visualsearch_router.post("/text", response_model=VisualSearchResponse)
@limiter.limit("50/day")
async def search_by_text(
    query: str = Body(..., embed=True),
    category: Optional[str] = Query(None),
    max_price: Optional[float] = Query(None),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """Search for products by text query."""
    user_id = str(current_user["id"])
    
    redis = get_redis_client()
    service = VisualSearchService(db, redis)
    
    allowed, _ = await service.check_rate_limit(user_id)
    if not allowed:
        raise HTTPException(status_code=429, detail="Daily search limit exceeded.")
    
    filters = {}
    if category:
        filters["category"] = category
    if max_price:
        filters["max_price"] = max_price
    
    response = await service.search_by_text(
        query=query,
        user_id=user_id,
        filters=filters,
        limit=limit,
    )
    
    return VisualSearchResponse(
        session_id=response.session_id,
        query_attributes={
            "category": response.query_attributes.category if response.query_attributes else None,
            "colors": response.query_attributes.colors if response.query_attributes else [],
        } if response.query_attributes else None,
        results=[{
            "product_id": r.product_id,
            "sku": r.sku,
            "name": r.name,
            "brand": r.brand,
            "price": r.price,
            "similarity_score": r.similarity_score,
        } for r in response.results],
        total_results=response.total_results,
        processing_time_ms=response.processing_time_ms,
    )


# ==========================================
# MY CLOSET - Wardrobe Endpoints
# ==========================================

@wardrobe_router.post("/items", response_model=WardrobeItemResponse)
@limiter.limit("100/day")
async def add_wardrobe_item(
    image: UploadFile = File(..., description="Item photo"),
    name: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """
    Add an item to user's wardrobe.
    
    Auto-tags using Google Vision API.
    Rate limit: 100 per day.
    """
    user_id = str(current_user["id"])
    user_tier = current_user.get("tier", "free")
    
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid image format")
    
    redis = get_redis_client()
    service = WardrobeService(db, redis)
    
    # Check quota
    allowed, remaining = await service.check_quota(user_id, user_tier)
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Wardrobe is full. Upgrade to add more items."
        )
    
    image_bytes = await image.read()
    
    item = await service.add_item(
        user_id=user_id,
        image_bytes=image_bytes,
        name=name,
        category=category,
    )
    
    # Get image URL
    image_url = await service.get_image_url(item)
    
    return WardrobeItemResponse(
        id=item.id,
        name=item.name,
        category=item.category,
        subcategory=item.subcategory,
        colors=item.colors,
        patterns=item.patterns,
        materials=item.materials,
        tags=item.tags,
        image_url=image_url,
        is_favorite=item.is_favorite,
    )


@wardrobe_router.get("/items", response_model=List[WardrobeItemResponse])
async def list_wardrobe_items(
    category: Optional[str] = Query(None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """List user's wardrobe items."""
    user_id = str(current_user["id"])
    
    redis = get_redis_client()
    service = WardrobeService(db, redis)
    
    items = await service.list_items(
        user_id=user_id,
        category=category,
        limit=limit,
        offset=offset,
    )
    
    results = []
    for item in items:
        image_url = await service.get_image_url(item)
        results.append(WardrobeItemResponse(
            id=item.id,
            name=item.name,
            category=item.category,
            subcategory=item.subcategory,
            colors=item.colors,
            patterns=item.patterns,
            materials=item.materials,
            tags=item.tags,
            image_url=image_url,
            is_favorite=item.is_favorite,
        ))
    
    return results


@wardrobe_router.get("/items/{item_id}", response_model=WardrobeItemResponse)
async def get_wardrobe_item(
    item_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """Get a specific wardrobe item."""
    user_id = str(current_user["id"])
    
    redis = get_redis_client()
    service = WardrobeService(db, redis)
    
    item = await service.get_item(item_id, user_id)
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    image_url = await service.get_image_url(item)
    
    return WardrobeItemResponse(
        id=item.id,
        name=item.name,
        category=item.category,
        subcategory=item.subcategory,
        colors=item.colors,
        patterns=item.patterns,
        materials=item.materials,
        tags=item.tags,
        image_url=image_url,
        is_favorite=item.is_favorite,
    )


@wardrobe_router.delete("/items/{item_id}")
async def delete_wardrobe_item(
    item_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """Delete a wardrobe item."""
    user_id = str(current_user["id"])
    
    redis = get_redis_client()
    service = WardrobeService(db, redis)
    
    success = await service.delete_item(item_id, user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return {"success": True, "message": "Item deleted"}


@wardrobe_router.post("/check-duplicates", response_model=DuplicateCheckResponse)
async def check_duplicates(
    product_sku: str = Body(...),
    product_name: Optional[str] = Body(None),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """
    Check if user already owns similar items.
    
    Called before purchase to alert about duplicates.
    """
    user_id = str(current_user["id"])
    
    redis = get_redis_client()
    service = WardrobeService(db, redis)
    
    alerts = await service.check_duplicates(
        user_id=user_id,
        product_sku=product_sku,
        product_name=product_name,
    )
    
    return DuplicateCheckResponse(
        alerts=[{
            "existing_item_id": a.existing_item.id,
            "existing_item_name": a.existing_item.name,
            "similarity_score": a.similarity_score,
            "message": a.message,
        } for a in alerts],
        has_duplicates=len(alerts) > 0,
    )


@wardrobe_router.get("/outfits/suggestions")
async def suggest_outfits(
    occasion: Optional[str] = Query(None),
    limit: int = Query(default=5, ge=1, le=10),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """Get outfit suggestions from user's wardrobe."""
    user_id = str(current_user["id"])
    
    redis = get_redis_client()
    service = WardrobeService(db, redis)
    
    outfits = await service.suggest_outfits(
        user_id=user_id,
        occasion=occasion,
        limit=limit,
    )
    
    return {
        "outfits": [{
            "outfit_id": o.outfit_id,
            "name": o.name,
            "items": [{
                "id": i.id,
                "name": i.name,
                "category": i.category,
            } for i in o.items],
            "occasion": o.occasion,
            "color_harmony_score": o.color_harmony_score,
            "style_match_score": o.style_match_score,
            "tips": o.tips,
        } for o in outfits]
    }


# ==========================================
# AI Admin Endpoints
# ==========================================

@ai_admin_router.get("/budget", response_model=BudgetStatusResponse)
async def get_budget_status(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """Get current AI budget status. Requires admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    redis = get_redis_client()
    tracker = get_cost_tracker(db, redis)
    
    status = await tracker.get_budget_status()
    
    return BudgetStatusResponse(
        daily_budget_usd=status.daily_budget_usd,
        spent_usd=status.spent_usd,
        remaining_usd=status.remaining_usd,
        percent_used=status.percent_used,
        is_warning=status.is_warning,
        is_exceeded=status.is_exceeded,
        kill_switch_active=status.kill_switch_active,
    )


@ai_admin_router.post("/kill-switch/activate")
async def activate_kill_switch(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """Manually activate AI kill-switch. Requires admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    redis = get_redis_client()
    tracker = get_cost_tracker(db, redis)
    tracker.activate_kill_switch()
    
    return {"success": True, "message": "Kill-switch activated"}


@ai_admin_router.post("/kill-switch/deactivate")
async def deactivate_kill_switch(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """Deactivate AI kill-switch. Requires admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    redis = get_redis_client()
    tracker = get_cost_tracker(db, redis)
    tracker.deactivate_kill_switch()
    
    return {"success": True, "message": "Kill-switch deactivated"}


@ai_admin_router.get("/costs/daily")
async def get_daily_costs(
    target_date: Optional[date] = Query(None),
    service: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """Get daily cost summary. Requires admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    redis = get_redis_client()
    tracker = get_cost_tracker(db, redis)
    
    summaries = await tracker.get_daily_summary(
        target_date=target_date,
        service=service,
    )
    
    return {
        "date": target_date or date.today().isoformat(),
        "summaries": [{
            "service": s.service,
            "total_cost_usd": s.total_cost_usd,
            "total_calls": s.total_calls,
            "total_tokens_in": s.total_tokens_in,
            "total_tokens_out": s.total_tokens_out,
            "avg_latency_ms": s.avg_latency_ms,
            "success_rate": s.success_rate,
            "unique_users": s.unique_users,
        } for s in summaries]
    }


@ai_admin_router.get("/costs/report", response_model=CostReportResponse)
async def get_cost_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    group_by: str = Query(default="service"),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """Get cost report for date range. Requires admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    redis = get_redis_client()
    tracker = get_cost_tracker(db, redis)
    
    report = await tracker.get_cost_report(
        start_date=start_date,
        end_date=end_date,
        group_by=group_by,
    )
    
    return CostReportResponse(**report)


@ai_admin_router.get("/costs/user/{user_id}")
async def get_user_costs(
    user_id: str = Path(...),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """Get cost history for a specific user. Requires admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    redis = get_redis_client()
    tracker = get_cost_tracker(db, redis)
    
    entries = await tracker.get_user_cost_history(user_id, limit)
    
    return {
        "user_id": user_id,
        "entries": [{
            "id": e.id,
            "service": e.service,
            "model": e.model,
            "cost_usd": e.cost_usd,
            "tokens_in": e.tokens_in,
            "tokens_out": e.tokens_out,
            "latency_ms": e.latency_ms,
            "success": e.success,
            "created_at": e.created_at.isoformat(),
        } for e in entries]
    }


# ==========================================
# Register Routers
# ==========================================

def include_ai_routers(app):
    """Include all AI routers in the FastAPI app."""
    app.include_router(muse_router, prefix="/api/ai")
    app.include_router(mirror_router, prefix="/api/ai")
    app.include_router(visualsearch_router, prefix="/api/ai")
    app.include_router(wardrobe_router, prefix="/api/ai")
    app.include_router(ai_admin_router, prefix="/api/ai")
