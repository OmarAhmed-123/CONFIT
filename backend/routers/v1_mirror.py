"""
CONFIT Backend — MIRROR Virtual Try-On v1 Router
=================================================
POST /api/v1/mirror/try-on       — Start try-on (async, returns task_id)
GET  /api/v1/mirror/try-on/{id}  — Poll result
GET  /api/v1/mirror/sessions     — List user sessions
DEL  /api/v1/mirror/data         — GDPR delete all user try-on data
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, Field

from database.session import get_db
from services.ai.mirror_service import MirrorService, TryOnStatus
from services.ai.cost_tracker import get_cost_tracker
from utils.auth_deps import require_auth
from services.auth_service import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mirror", tags=["MIRROR — Virtual Try-On"])

MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB


# ── Schemas ──────────────────────────────────────────────────────────

class TryOnStartResponse(BaseModel):
    task_id: str
    status: str = "queued"


class TryOnResultResponse(BaseModel):
    task_id: str
    status: str
    result_image_url: Optional[str] = None
    fit_score: float = 0.0
    processing_time_ms: float = 0.0
    error_message: Optional[str] = None


class SessionSummary(BaseModel):
    session_id: str
    product_id: str
    status: str
    created_at: str
    result_image_url: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────

def _get_mirror_service(db=Depends(get_db)) -> MirrorService:
    from core.redis_client import get_redis_client
    redis = get_redis_client()
    s3 = None
    try:
        from core.s3_client import get_s3_client
        s3 = get_s3_client()
    except Exception:
        pass
    service = MirrorService(db, redis, s3)
    tracker = get_cost_tracker(db, redis)
    service.set_cost_tracker(tracker)
    return service


def _user_tier(user: UserProfile) -> str:
    role = getattr(user, "role", "user") or "user"
    if role in ("icon", "donor", "admin"):
        return "icon"
    if role in ("club", "wardrobe_club", "premium"):
        return "club"
    return "free"


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/try-on", response_model=TryOnStartResponse)
async def start_tryon(
    user_photo: UploadFile = File(..., description="User's photo (JPEG/PNG)"),
    product_variant_id: str = Form(..., description="Product variant UUID"),
    category: str = Form(default="upper_body", description="Garment category: upper_body | lower_body | full_body"),
    user: UserProfile = Depends(require_auth),
    service: MirrorService = Depends(_get_mirror_service),
):
    """
    Start a virtual try-on session.

    Returns a task_id for polling. Rate-limited:
    - Free: 10/day  - Club: 50/day  - Icon: 200/day
    Cost: ~$0.05/call. User photos encrypted at rest, deleted after 7 days.
    """
    tier = _user_tier(user)
    allowed, retry_after = await service.check_rate_limit(str(user.id), tier)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Daily try-on limit reached. Upgrade to Wardrobe Club for more.",
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    # Budget kill-switch
    if service._cost_tracker and service._cost_tracker.is_kill_switch_active():
        raise HTTPException(status_code=503, detail="AI services temporarily unavailable due to budget limits.")

    # Validate photo
    if not user_photo.content_type or not user_photo.content_type.startswith("image/"):
        raise HTTPException(400, "Invalid file type. Please upload a JPEG or PNG image.")

    photo_bytes = await user_photo.read()
    if len(photo_bytes) > MAX_PHOTO_SIZE:
        raise HTTPException(400, f"Photo too large. Maximum size: {MAX_PHOTO_SIZE // (1024*1024)} MB")
    if len(photo_bytes) < 100:
        raise HTTPException(400, "Photo appears to be empty or too small.")

    # Get product image
    from services.product_service import ProductService
    product_svc = ProductService(service.db)
    product = product_svc.get_product(product_variant_id)
    if not product:
        raise HTTPException(404, "Product not found")

    garment_url = None
    garment_bytes = None
    if isinstance(product, dict):
        garment_url = product.get("image_url") or product.get("images", [None])[0] if product.get("images") else None
    else:
        garment_url = getattr(product, "image_url", None) or (
            getattr(product, "images", [None])[0] if hasattr(product, "images") and product.images else None
        )

    from services.ai.mirror_service import TryOnRequest
    request = TryOnRequest(
        user_id=str(user.id),
        product_id=product_variant_id,
        product_sku=getattr(product, "sku", None) or (product.get("sku") if isinstance(product, dict) else product_variant_id),
        person_image_bytes=photo_bytes,
        garment_image_url=garment_url,
        category=category,
    )

    session = await service.start_tryon(request)

    return TryOnStartResponse(task_id=session.session_id, status="queued")


@router.get("/try-on/{task_id}", response_model=TryOnResultResponse)
async def get_tryon_result(
    task_id: str,
    user: UserProfile = Depends(require_auth),
    service: MirrorService = Depends(_get_mirror_service),
):
    """Poll for try-on result by task_id."""
    result = await service.get_result(task_id)

    return TryOnResultResponse(
        task_id=result.session_id,
        status=result.status.value if hasattr(result.status, "value") else str(result.status),
        result_image_url=result.result_url,
        fit_score=result.quality_score,
        processing_time_ms=result.latency_ms,
        error_message=result.error_message,
    )


@router.get("/sessions", response_model=list[SessionSummary])
async def list_tryon_sessions(
    user: UserProfile = Depends(require_auth),
    service: MirrorService = Depends(_get_mirror_service),
    limit: int = 20,
):
    """List user's recent try-on sessions."""
    from sqlalchemy import text
    sql = text("""
        SELECT id, product_id, status, created_at, result_image_key
        FROM try_on_sessions
        WHERE user_id = :uid
        ORDER BY created_at DESC
        LIMIT :lim
    """)
    rows = service.db.execute(sql, {"uid": str(user.id), "lim": limit}).fetchall()

    summaries = []
    for r in rows:
        result_url = None
        if r.result_image_key:
            try:
                result_url = await service._get_presigned_url(r.result_image_key)
            except Exception:
                pass
        summaries.append(SessionSummary(
            session_id=r.id,
            product_id=r.product_id,
            status=r.status,
            created_at=r.created_at.isoformat() if r.created_at else "",
            result_image_url=result_url,
        ))
    return summaries


@router.delete("/data")
async def delete_user_tryon_data(
    user: UserProfile = Depends(require_auth),
    service: MirrorService = Depends(_get_mirror_service),
):
    """GDPR: Delete all try-on data for the authenticated user."""
    success = await service.delete_user_data(str(user.id))
    if not success:
        raise HTTPException(500, "Failed to delete user data")
    return {"success": True, "message": "All try-on data deleted"}
