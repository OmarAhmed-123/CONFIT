"""
CONFIT Backend — Live Preview Service
=======================================
Manages WebSocket connections for real-time try-on streaming.

Features:
- Progressive rendering (low-res fast preview → high-res final)
- Garment switching without re-uploading user image
- Session-based connection management
- Cache integration for instant results on repeated garments
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class PreviewSession:
    """A single live preview WebSocket session."""
    session_id: str
    websocket: WebSocket
    user_image_base64: Optional[str] = None
    current_garment_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    frames_sent: int = 0


class LivePreviewManager:
    """Manages live preview sessions for real-time try-on streaming.

    Usage:
        manager = LivePreviewManager.get_instance()
        session = await manager.create_session(websocket)
        await manager.process_frame(session.session_id, garment_url, garment_name)
    """

    _instance: Optional["LivePreviewManager"] = None

    def __init__(self) -> None:
        self._sessions: Dict[str, PreviewSession] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    @classmethod
    def get_instance(cls) -> "LivePreviewManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def create_session(self, websocket: WebSocket) -> PreviewSession:
        """Create a new preview session for a WebSocket connection."""
        session_id = str(uuid.uuid4())[:8]
        session = PreviewSession(session_id=session_id, websocket=websocket)
        self._sessions[session_id] = session
        logger.info("Live preview session created: %s", session_id)

        # Start cleanup task if not running
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        return session

    async def remove_session(self, session_id: str) -> None:
        """Remove a session (on disconnect)."""
        self._sessions.pop(session_id, None)
        logger.info("Live preview session removed: %s", session_id)

    async def set_user_image(self, session_id: str, image_base64: str) -> None:
        """Update the user image for a session."""
        session = self._sessions.get(session_id)
        if session:
            session.user_image_base64 = image_base64
            session.last_activity = time.time()

    async def process_frame(
        self,
        session_id: str,
        garment_image_url: str,
        garment_name: str,
    ) -> Optional[dict]:
        """Process a try-on frame and return the result.

        Returns dict with result data, or None if session not found.
        """
        session = self._sessions.get(session_id)
        if not session or not session.user_image_base64:
            return None

        session.last_activity = time.time()
        session.current_garment_id = garment_name

        # Use TryOnOrchestrator for inference
        from services.mcp.orchestrator import TryOnOrchestrator
        orchestrator = TryOnOrchestrator.get_instance()

        result = await orchestrator.process_live_update(
            user_image_base64=session.user_image_base64,
            garment_image_url=garment_image_url,
            garment_name=garment_name,
        )

        session.frames_sent += 1

        return {
            "type": "result",
            "success": result.success,
            "resultImage": result.result_image,
            "qualityScore": result.quality_score,
            "processingTimeMs": result.processing_time_ms,
            "garmentCategory": result.garment_category,
            "cacheHit": result.cache_hit,
            "frameNumber": session.frames_sent,
        }

    async def _cleanup_loop(self) -> None:
        """Periodically remove stale sessions (inactive > 10 minutes)."""
        while self._sessions:
            await asyncio.sleep(60)
            now = time.time()
            stale = [
                sid for sid, s in self._sessions.items()
                if now - s.last_activity > 600
            ]
            for sid in stale:
                self._sessions.pop(sid, None)
                logger.info("Cleaned up stale session: %s", sid)

    def active_sessions(self) -> int:
        return len(self._sessions)

    def stats(self) -> dict:
        return {
            "active_sessions": self.active_sessions(),
            "total_frames_sent": sum(s.frames_sent for s in self._sessions.values()),
        }
