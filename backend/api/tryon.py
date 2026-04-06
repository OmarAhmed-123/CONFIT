"""
CONFIT Backend - Virtual Try-On API Routes
==========================================
AI-powered virtual try-on with async processing.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import get_tryon_service, get_current_user, get_current_user_optional
from application.services.tryon_service import (
    VirtualTryOnService,
    TryOnRequestDTO,
    TryOnResultDTO,
)
from core.security.rbac import AuthContext


router = APIRouter(prefix="/try-on", tags=["Virtual Try-On"])


@router.post(
    "",
    response_model=TryOnResultDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create virtual try-on",
)
async def create_try_on(
    request: TryOnRequestDTO,
    tryon_service: VirtualTryOnService = Depends(get_tryon_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Create a new virtual try-on session."""
    from uuid import UUID
    result, error = await tryon_service.create_try_on(
        user_id=UUID(current_user.user_id),
        request=request,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return result


@router.get(
    "/{session_id}",
    response_model=TryOnResultDTO,
    summary="Get try-on session",
)
async def get_try_on(
    session_id: str,
    tryon_service: VirtualTryOnService = Depends(get_tryon_service),
    current_user: Optional[AuthContext] = Depends(get_current_user_optional),
):
    """Get try-on session by ID."""
    result = await tryon_service.get_try_on(UUID(session_id))
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Try-on session not found"
        )
    
    return result


@router.get(
    "",
    summary="Get user's try-on sessions",
)
async def get_user_try_ons(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tryon_service: VirtualTryOnService = Depends(get_tryon_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get user's try-on session history."""
    from uuid import UUID
    return await tryon_service.get_user_try_ons(
        user_id=UUID(current_user.user_id),
        status=status,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{session_id}/cancel",
    summary="Cancel try-on",
)
async def cancel_try_on(
    session_id: str,
    tryon_service: VirtualTryOnService = Depends(get_tryon_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Cancel pending try-on session."""
    from uuid import UUID
    success, error = await tryon_service.cancel_try_on(
        session_id=UUID(session_id),
        user_id=UUID(current_user.user_id),
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Try-on cancelled"}


@router.post(
    "/{session_id}/retry",
    response_model=TryOnResultDTO,
    summary="Retry failed try-on",
)
async def retry_try_on(
    session_id: str,
    tryon_service: VirtualTryOnService = Depends(get_tryon_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Retry a failed try-on session."""
    from uuid import UUID
    result, error = await tryon_service.retry_try_on(
        session_id=UUID(session_id),
        user_id=UUID(current_user.user_id),
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return result


@router.get(
    "/{session_id}/quality",
    summary="Validate try-on quality",
)
async def validate_quality(
    session_id: str,
    tryon_service: VirtualTryOnService = Depends(get_tryon_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Validate quality of completed try-on."""
    from uuid import UUID
    return await tryon_service.validate_result(UUID(session_id))
