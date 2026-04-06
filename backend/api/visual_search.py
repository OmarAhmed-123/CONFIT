"""
CONFIT Backend - Visual Search API Routes
=========================================
AI-powered visual search with attribute detection.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import get_visual_search_service, get_current_user, get_current_user_optional
from application.services.visual_search_service import (
    VisualSearchService,
    VisualSearchRequestDTO,
    VisualSearchResponseDTO,
)
from core.security.rbac import AuthContext


router = APIRouter(prefix="/visual-search", tags=["Visual Search"])


@router.post(
    "",
    response_model=VisualSearchResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create visual search",
)
async def create_visual_search(
    request: VisualSearchRequestDTO,
    search_service: VisualSearchService = Depends(get_visual_search_service),
    current_user: Optional[AuthContext] = Depends(get_current_user_optional),
):
    """Create a new visual search session."""
    user_id = UUID(current_user.user_id) if current_user else None
    
    result, error = await search_service.create_search(
        user_id=user_id,
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
    response_model=VisualSearchResponseDTO,
    summary="Get search session",
)
async def get_visual_search(
    session_id: str,
    search_service: VisualSearchService = Depends(get_visual_search_service),
):
    """Get visual search session by ID."""
    result = await search_service.get_search(UUID(session_id))
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search session not found"
        )
    
    return result


@router.get(
    "/history",
    summary="Get search history",
)
async def get_search_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search_service: VisualSearchService = Depends(get_visual_search_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get user's visual search history."""
    from uuid import UUID
    return await search_service.get_user_searches(
        user_id=UUID(current_user.user_id),
        page=page,
        page_size=page_size,
    )
