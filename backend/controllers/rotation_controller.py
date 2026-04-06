"""
CONFIT Backend — Rotation Controller
======================================
Orchestrates 360-degree rotation-frame generation.
"""

import logging

from models.tryon_models import RotationRequest, RotationResponse
from services.rotation_service import RotationService

logger = logging.getLogger(__name__)


class RotationController:
    """Controller for the 360-degree rotation viewer feature."""

    _service = RotationService()

    async def generate_frames(self, request: RotationRequest) -> RotationResponse:
        """
        Generate perspective-transformed frames from a source image.
        """
        logger.info(
            "Generating %d rotation frames", request.frameCount,
        )

        frames = await self._service.generate_frames(
            source_image_base64=request.sourceImageBase64,
            frame_count=request.frameCount,
        )

        return RotationResponse(
            success=True,
            frames=frames,
            frameCount=len(frames),
            message=f"Generated {len(frames)} rotation frames successfully.",
        )

    @staticmethod
    def health() -> dict:
        """Return service health status."""
        return {"status": "ok", "service": "rotation-viewer"}
