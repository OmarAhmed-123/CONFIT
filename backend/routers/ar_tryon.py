"""
CONFIT Backend — AR Virtual Try-On Router
=========================================
WebSocket and REST endpoints for real-time AR try-on.

Endpoints:
- POST /sessions: Create AR session
- DELETE /sessions/{id}: End session
- POST /sessions/{id}/frame: Process video frame
- POST /sessions/{id}/screenshot: Capture screenshot
- GET /health: Service health check
- GET /metrics: Performance metrics
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from services.ar_tryon_service import (
    get_ar_tryon_service,
    ARProcessingMode,
    ARTryOnService
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ar-tryon", tags=["AR Virtual Try-On"])


# ==========================================
# Request/Response Models
# ==========================================

class CreateSessionRequest(BaseModel):
    """Request to create AR session."""
    garment_id: str
    garment_image_base64: str
    user_id: Optional[str] = None
    garment_category: Optional[str] = None
    mode: str = "balanced"  # realtime, quality, balanced


class ProcessFrameRequest(BaseModel):
    """Request to process a video frame."""
    frame_base64: str
    return_overlay: bool = True


class SessionResponse(BaseModel):
    """AR session response."""
    success: bool
    session_id: Optional[str] = None
    garment_category: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class FrameResponse(BaseModel):
    """Frame processing response."""
    success: bool
    pose: Optional[dict] = None
    overlay_image: Optional[str] = None
    processing_time_ms: Optional[float] = None
    frame_number: Optional[int] = None
    error: Optional[str] = None


class ScreenshotResponse(BaseModel):
    """Screenshot capture response."""
    success: bool
    screenshot: Optional[str] = None
    garment_id: Optional[str] = None
    garment_category: Optional[str] = None
    pose_confidence: Optional[float] = None
    timestamp: Optional[str] = None
    privacy_note: Optional[str] = None
    error: Optional[str] = None


# ==========================================
# REST Endpoints
# ==========================================

@router.post("/sessions", response_model=SessionResponse)
async def create_ar_session(request: CreateSessionRequest):
    """
    Create a new AR try-on session.
    
    Initializes a session for real-time virtual try-on.
    The session handles:
    - Garment image processing
    - Pose tracking state
    - Privacy-compliant processing
    
    Returns session ID for subsequent frame processing.
    """
    try:
        service = get_ar_tryon_service()
        
        # Decode garment image
        import base64
        garment_image = base64.b64decode(
            request.garment_image_base64.split(',')[-1]
            if ',' in request.garment_image_base64 
            else request.garment_image_base64
        )
        
        # Create session
        session = await service.create_session(
            garment_id=request.garment_id,
            garment_image=garment_image,
            user_id=request.user_id,
            garment_category=request.garment_category
        )
        
        return SessionResponse(
            success=True,
            session_id=session.session_id,
            garment_category=session.garment_category,
            message="AR session created successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to create AR session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def end_ar_session(session_id: str):
    """
    End an AR session and cleanup resources.
    
    Privacy: Ensures all session data is deleted.
    Returns privacy compliance report.
    """
    try:
        service = get_ar_tryon_service()
        result = await service.end_session(session_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail="Session not found")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to end AR session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/frame", response_model=FrameResponse)
async def process_ar_frame(session_id: str, request: ProcessFrameRequest):
    """
    Process a single video frame for AR try-on.
    
    Real-time processing:
    1. Detects body pose
    2. Applies temporal smoothing
    3. Generates garment overlay
    4. Returns composited result
    
    Performance: Optimized for 30 FPS on mobile devices.
    """
    try:
        service = get_ar_tryon_service()
        result = await service.process_frame(
            session_id=session_id,
            frame_base64=request.frame_base64,
            return_overlay=request.return_overlay
        )
        
        return FrameResponse(**result)
        
    except Exception as e:
        logger.error(f"Frame processing failed: {e}")
        return FrameResponse(
            success=False,
            error=str(e)
        )


@router.post("/sessions/{session_id}/screenshot", response_model=ScreenshotResponse)
async def capture_ar_screenshot(session_id: str, request: ProcessFrameRequest):
    """
    Capture a screenshot from AR session.
    
    Privacy: Screenshot is returned to client, NOT stored on server.
    Uses quality mode for best output.
    """
    try:
        service = get_ar_tryon_service()
        result = await service.capture_screenshot(
            session_id=session_id,
            frame_base64=request.frame_base64
        )
        
        return ScreenshotResponse(**result)
        
    except Exception as e:
        logger.error(f"Screenshot capture failed: {e}")
        return ScreenshotResponse(
            success=False,
            error=str(e)
        )


@router.get("/health")
async def ar_tryon_health():
    """
    Health check for AR try-on service.
    
    Returns status of:
    - Pose detection model
    - Active sessions
    - Performance metrics
    """
    service = get_ar_tryon_service()
    metrics = service.get_metrics()
    
    return {
        "status": "healthy",
        "pose_detection": "available",
        "active_sessions": metrics.get("active_sessions", 0),
        "mode": metrics.get("mode", "balanced"),
        "average_processing_time_ms": round(metrics.get("average_processing_time_ms", 0), 2)
    }


@router.get("/metrics")
async def get_ar_metrics():
    """
    Get AR service performance metrics.
    
    Returns:
    - Total frames processed
    - Average processing time
    - Active sessions count
    """
    service = get_ar_tryon_service()
    return service.get_metrics()


# ==========================================
# WebSocket for Real-time Streaming
# ==========================================

class ARWebSocketManager:
    """Manages WebSocket connections for AR streaming."""
    
    def __init__(self):
        self._connections: dict = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and register WebSocket connection."""
        await websocket.accept()
        self._connections[session_id] = websocket
        logger.info(f"WebSocket connected for session {session_id}")
    
    def disconnect(self, session_id: str):
        """Remove WebSocket connection."""
        if session_id in self._connections:
            del self._connections[session_id]
            logger.info(f"WebSocket disconnected for session {session_id}")


ws_manager = ARWebSocketManager()


@router.websocket("/ws/{session_id}")
async def ar_tryon_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time AR streaming.
    
    Protocol:
    - Client sends: { "type": "frame", "data": "<base64>" }
    - Server sends: { "type": "result", "pose": {...}, "overlay": "<base64>" }
    
    Optimized for low-latency streaming.
    """
    service = get_ar_tryon_service()
    
    # Check if session exists
    if session_id not in service._sessions:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    await ws_manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive frame data
            data = await websocket.receive_json()
            
            if data.get("type") == "frame":
                # Process frame
                result = await service.process_frame(
                    session_id=session_id,
                    frame_base64=data.get("data", ""),
                    return_overlay=data.get("return_overlay", True)
                )
                
                # Send result
                await websocket.send_json({
                    "type": "result",
                    **result
                })
            
            elif data.get("type") == "screenshot":
                # Capture screenshot
                result = await service.capture_screenshot(
                    session_id=session_id,
                    frame_base64=data.get("data", "")
                )
                
                await websocket.send_json({
                    "type": "screenshot",
                    **result
                })
            
            elif data.get("type") == "ping":
                # Keepalive
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(session_id)
