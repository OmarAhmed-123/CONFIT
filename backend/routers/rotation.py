"""
CONFIT Backend — Rotation Router
===================================
Endpoints for generating 360-degree rotation frames.
"""

import logging

from fastapi import APIRouter, HTTPException

from controllers.rotation_controller import RotationController
from models.tryon_models import RotationRequest, RotationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rotation", tags=["360° Rotation"])

_controller = RotationController()


@router.post("", response_model=RotationResponse)
async def generate_rotation_frames(request: RotationRequest):
    """
    Generate perspective-transformed frames from a source image
    for an interactive 360-degree rotation viewer.
    """
    try:
        return await _controller.generate_frames(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Rotation frame generation failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Frame generation failed: {str(exc)}",
        )


@router.get("/health")
async def rotation_health():
    """Health check for the rotation service."""
    return RotationController.health()
