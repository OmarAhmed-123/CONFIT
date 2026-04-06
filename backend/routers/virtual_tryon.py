"""
CONFIT Backend — Virtual Try-On Router
========================================
Routing layer for virtual try-on endpoints.

Endpoints:
- POST /process: Process virtual try-on (full pipeline)
- POST /live-update: Optimized garment switching for live preview
- GET /health: Service health check
- GET /sessions: Get user's try-on history
- GET /sessions/{id}: Get specific session
- GET /stats: Quality statistics
- WebSocket /ws/live: Real-time try-on streaming
"""

import asyncio
import logging
import json
import os
from typing import Optional, Any, Dict
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect, Header
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from controllers.tryon_controller import TryOnController
from models.tryon_models import TryOnRequest, TryOnResponse
from database.session import get_db
from core.api_response import ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/virtual-tryon", tags=["Virtual Try-On"])


class FashnKeyConfigRequest(BaseModel):
    apiKey: str = Field(..., min_length=8, description="FASHN API key")
    persistToEnv: bool = Field(default=False, description="Persist key in backend/.env")


def _update_env_file_var(env_path: Path, key: str, value: str) -> None:
    """
    Update or append KEY=value in .env (no logging of secret values).
    """
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    prefix = f"{key}="
    replaced = False
    out: list[str] = []
    for line in lines:
        if line.startswith(prefix):
            out.append(f"{prefix}{value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"{prefix}{value}")
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")


@router.post("/config/fashn-key")
async def configure_fashn_key(
    payload: FashnKeyConfigRequest,
    x_tryon_admin_token: Optional[str] = Header(default=None),
):
    """
    Secure runtime configuration for FASHN_API_KEY.
    Requires TRYON_ADMIN_TOKEN in server env and matching X-TryOn-Admin-Token header.
    """
    required = (os.getenv("TRYON_ADMIN_TOKEN") or "").strip()
    if not required:
        raise HTTPException(
            status_code=503,
            detail="TRYON_ADMIN_TOKEN is not configured on server.",
        )
    if (x_tryon_admin_token or "").strip() != required:
        raise HTTPException(status_code=403, detail="Invalid admin token.")

    key = payload.apiKey.strip()
    if len(key) < 8:
        raise HTTPException(status_code=400, detail="Invalid FASHN API key.")

    # Runtime update (takes effect immediately after router refresh).
    os.environ["FASHN_API_KEY"] = key

    if payload.persistToEnv:
        env_path = Path(__file__).resolve().parents[1] / ".env"
        _update_env_file_var(env_path, "FASHN_API_KEY", key)

    try:
        from services.mcp.pipeline import ModelControlPipeline
        from services.mcp.model_router import ModelBackend

        mcp = ModelControlPipeline.get_instance()
        mcp.router.refresh()
        fashn_available = mcp.router.is_available(ModelBackend.FASHN)
    except Exception:
        fashn_available = False

    return ok(
        {
            "configured": True,
            "persistedToEnv": bool(payload.persistToEnv),
            "fashnAvailable": bool(fashn_available),
        }
    )


@router.get("/diagnostics")
async def get_tryon_runtime_diagnostics() -> Dict[str, Any]:
    """
    Detailed runtime diagnostics to explain reject/failure causes quickly in UI.
    """
    from services.mcp.pipeline import ModelControlPipeline

    mcp = ModelControlPipeline.get_instance()
    stats = mcp.stats()
    from services.tryon_runtime import TryOnRuntimeManager

    caps = TryOnRuntimeManager.get_instance().get_capabilities()
    return ok(
        {
            "preview_available": bool(caps.get("preview_available")),
            "final_render_available": bool(caps.get("final_render_available")),
            "active_backend": caps.get("active_backend"),
            "backend_priority": caps.get("backend_priority", []),
            "failure_reason": caps.get("failure_reason"),
            "details": caps.get("details", {}),
            "mcp": stats,
        }
    )


# ── Main Try-On Endpoint ────────────────────────────────────────────────────

@router.post("/process", response_model=TryOnResponse)
async def virtual_try_on(request: TryOnRequest):
    """Process a virtual try-on request through the MCP pipeline.

    Takes a person image (base64) and a garment image (URL),
    routes through model selection, caching, and GPU scheduling,
    and returns a photorealistic result.
    """
    timeout_sec = float(os.getenv("TRYON_REQUEST_TIMEOUT_SEC", "300"))
    try:
        controller = TryOnController.get_instance()
        response = await asyncio.wait_for(controller.process(request), timeout=timeout_sec)
        if not response.success:
            detail = response.error or response.message
            if response.failureKind == "garment_fetch":
                raise HTTPException(
                    status_code=502,
                    detail=detail or "Garment image could not be loaded from the given URL.",
                )
            raise HTTPException(
                status_code=422,
                detail=detail or "Try-on could not produce an acceptable result.",
            )
        return response
    except asyncio.TimeoutError:
        logger.error("Try-on exceeded request timeout (%.0fs)", timeout_sec)
        raise HTTPException(
            status_code=504,
            detail=(
                "Try-on processing timed out. Increase TRYON_REQUEST_TIMEOUT_SEC on the server, "
                "or set TRYON_FABRIC_PHYSICS=0 on CPU, or enable GPU. MediaPipe Tasks models "
                "download on first run to ~/.cache/confit_mediapipe."
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ConnectionError as exc:
        logger.error("Connection error: %s", exc)
        raise HTTPException(status_code=503, detail="Try-on service temporarily unavailable.")
    except TimeoutError as exc:
        logger.error("Timeout error: %s", exc)
        raise HTTPException(status_code=504, detail="Try-on processing timed out.")
    except Exception as exc:
        logger.error("Try-on failed: %s", exc)
        raise HTTPException(status_code=500, detail="Try-on processing failed. Please try again.")


# ── Live Update Endpoint ────────────────────────────────────────────────────

@router.post("/live-update", response_model=TryOnResponse)
async def live_update(request: TryOnRequest):
    """Optimized try-on for instant garment switching.

    Uses higher priority in GPU scheduler and aggressive caching
    for sub-second response times when user is browsing garments.
    """
    timeout_sec = float(os.getenv("TRYON_REQUEST_TIMEOUT_SEC", "300"))
    try:
        controller = TryOnController.get_instance()
        response = await asyncio.wait_for(
            controller.process_live_update(
                user_image_base64=request.userImageBase64,
                garment_image_url=request.garmentImageUrl,
                garment_name=request.garmentName,
            ),
            timeout=timeout_sec,
        )
        if not response.success:
            detail = response.error or response.message
            if response.failureKind == "garment_fetch":
                raise HTTPException(
                    status_code=502,
                    detail=detail or "Garment image could not be loaded from the given URL.",
                )
            raise HTTPException(
                status_code=422,
                detail=detail or "Try-on could not produce an acceptable result.",
            )
        return response
    except asyncio.TimeoutError:
        logger.error("Live try-on exceeded request timeout (%.0fs)", timeout_sec)
        raise HTTPException(
            status_code=504,
            detail=(
                "Try-on processing timed out. Use a smaller photo or install MediaPipe on the API server."
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Live update failed: %s", exc)
        raise HTTPException(status_code=500, detail="Live update failed.")


# ── WebSocket Live Preview ──────────────────────────────────────────────────

@router.websocket("/ws/live")
async def websocket_live_preview(websocket: WebSocket):
    """Real-time try-on via WebSocket.

    Protocol:
    1. Client connects
    2. Client sends JSON: {"userImageBase64": "...", "garmentImageUrl": "...", "garmentName": "..."}
    3. Server sends JSON: {"type": "result", "resultImage": "...", "processingTimeMs": ...}
    4. Client can send new garment selections for instant updates
    5. Client disconnects when done

    The user image is sent once, then only garment changes are streamed.
    """
    await websocket.accept()
    logger.info("WebSocket live preview connected")

    user_image_base64: Optional[str] = None
    controller = TryOnController.get_instance()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "Invalid JSON"})
                continue

            # Update user image if provided
            if data.get("userImageBase64"):
                user_image_base64 = data["userImageBase64"]

            if not user_image_base64:
                await websocket.send_json({"type": "error", "error": "Please upload a photo first"})
                continue

            garment_url = data.get("garmentImageUrl", "")
            garment_name = data.get("garmentName", "garment")
            logger.info("WebSocket live update requested for garment: %s", garment_name)

            if not garment_url:
                await websocket.send_json({"type": "error", "error": "No garment selected"})
                continue

            # Send processing indicator
            await websocket.send_json({"type": "processing", "garmentName": garment_name})

            try:
                result = await controller.process_live_update(
                    user_image_base64=user_image_base64,
                    garment_image_url=garment_url,
                    garment_name=garment_name,
                )
                await websocket.send_json({
                    "type": "result",
                    "success": result.success,
                    "resultImage": result.resultImage,
                    "qualityScore": result.qualityScore,
                    "processingTimeMs": result.processingTimeMs,
                    "garmentCategory": result.garmentCategory,
                })
            except Exception as e:
                logger.error("WebSocket try-on error: %s", e)
                await websocket.send_json({"type": "error", "error": str(e)})

    except WebSocketDisconnect:
        logger.info("WebSocket live preview disconnected")


# ── Health Check ────────────────────────────────────────────────────────────

@router.get("/health")
async def tryon_health():
    """Health check for the try-on service including MCP stats."""
    return ok(TryOnController.health())


# ── Session History ─────────────────────────────────────────────────────────

@router.get("/sessions")
async def get_tryon_sessions(
    user_id: str = Query(..., description="User ID to get sessions for"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of sessions"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """Get try-on session history for a user."""
    try:
        from services.tryon_session_service import TryOnSessionService
        session_service = TryOnSessionService(db)
        sessions = session_service.get_user_sessions(user_id, limit, offset)
        return jsonable_encoder([
            {
                "id": str(s.id),
                "garmentName": s.garment_name,
                "garmentCategory": s.garment_category,
                "qualityScore": s.quality_score,
                "poseDetected": s.pose_detected,
                "processingMode": s.processing_mode,
                "processingTimeMs": s.processing_time_ms,
                "status": s.status,
                "createdAt": s.created_at.isoformat(),
            }
            for s in sessions
        ])
    except Exception as exc:
        logger.error("Failed to get sessions: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.get("/sessions/{session_id}")
async def get_tryon_session(session_id: str, db: Session = Depends(get_db)):
    """Get details of a specific try-on session."""
    try:
        from services.tryon_session_service import TryOnSessionService
        session_service = TryOnSessionService(db)
        session = session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return jsonable_encoder({
            "id": str(session.id),
            "userId": str(session.user_id) if session.user_id else None,
            "garmentName": session.garment_name,
            "garmentCategory": session.garment_category,
            "fitType": session.fit_type,
            "qualityScore": session.quality_score,
            "qualityMetrics": {
                "realismScore": session.realism_score,
                "edgeQuality": session.edge_quality,
                "colorConsistency": session.color_consistency,
                "proportionScore": session.proportion_score,
                "artifactScore": session.artifact_score,
            },
            "poseDetected": session.pose_detected,
            "processingMode": session.processing_mode,
            "processingTimeMs": session.processing_time_ms,
            "status": session.status,
            "warnings": session.warnings or [],
            "createdAt": session.created_at.isoformat(),
        })
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get session: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve session")


@router.get("/stats")
async def get_tryon_stats(
    user_id: Optional[str] = Query(None, description="Optional user ID to filter"),
    db: Session = Depends(get_db),
):
    """Get quality statistics for try-on sessions."""
    try:
        from services.tryon_session_service import TryOnSessionService
        session_service = TryOnSessionService(db)
        return session_service.get_quality_stats(user_id)
    except Exception as exc:
        logger.error("Failed to get stats: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")
