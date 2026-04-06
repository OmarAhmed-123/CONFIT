"""
CONFIT Backend - Virtual Try-On Application Service
=====================================================
AI-powered virtual try-on with async processing.
"""

import os
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities import TryOnSession
from domain.base import TryOnStatus
from database.models import TryOnSession as TryOnSessionModel


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DTOs
# ─────────────────────────────────────────────────────────────────────────────

class TryOnRequestDTO(BaseModel):
    """Virtual try-on request."""
    user_image_url: str
    garment_image_url: str
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    category: Optional[str] = None  # tops, bottoms, dresses, etc.


class TryOnResultDTO(BaseModel):
    """Virtual try-on result."""
    id: str
    user_id: str
    status: str
    user_image_url: str
    garment_image_url: str
    result_image_url: Optional[str] = None
    quality_score: Optional[float] = None
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class TryOnSessionDTO(BaseModel):
    """Try-on session with multiple attempts."""
    id: str
    user_id: str
    attempts: List[TryOnResultDTO]
    total_attempts: int
    best_result: Optional[TryOnResultDTO] = None


# ─────────────────────────────────────────────────────────────────────────────
# VIRTUAL TRY-ON SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class VirtualTryOnService:
    """Virtual try-on service with async processing."""
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
    SUPPORTED_CATEGORIES = ["tops", "bottoms", "dresses", "outerwear", "full_body"]
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._celery_app = None
    
    @property
    def celery_app(self):
        """Get Celery app for async tasks."""
        if self._celery_app is None:
            from workers.celery_app import celery_app
            self._celery_app = celery_app
        return self._celery_app
    
    # ─────────────────────────────────────────────────────────────────────────
    # TRY-ON OPERATIONS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def create_try_on(
        self,
        user_id: UUID,
        request: TryOnRequestDTO,
    ) -> Tuple[Optional[TryOnResultDTO], Optional[str]]:
        """
        Create a new virtual try-on session.
        
        The processing is done asynchronously via Celery.
        """
        # Validate images
        validation_error = await self._validate_images(request)
        if validation_error:
            return None, validation_error
        
        # Create session
        session = TryOnSessionModel(
            user_id=str(user_id),
            product_id=request.product_id,
            variant_id=request.variant_id,
            user_image_url=request.user_image_url,
            garment_image_url=request.garment_image_url,
            status=TryOnStatus.PENDING.value,
            metadata={"category": request.category},
        )
        
        self.session.add(session)
        await self.session.flush()
        await self.session.refresh(session)
        
        # Queue async processing task
        task = self.celery_app.send_task(
            "workers.tryon_tasks.process_tryon",
            args=[str(session.id)],
            queue="tryon",
        )
        
        session.task_id = task.id
        await self.session.flush()
        
        logger.info(f"Try-on session created: {session.id}, task: {task.id}")
        
        return self._to_dto(session), None
    
    async def get_try_on(self, session_id: UUID) -> Optional[TryOnResultDTO]:
        """Get try-on session by ID."""
        session = await self._get_session(session_id)
        return self._to_dto(session) if session else None
    
    async def get_user_try_ons(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Get user's try-on sessions."""
        query = select(TryOnSessionModel).where(
            TryOnSessionModel.user_id == str(user_id)
        )
        
        if status:
            query = query.where(TryOnSessionModel.status == status)
        
        # Count
        from sqlalchemy import func
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Paginate
        query = query.order_by(TryOnSessionModel.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.session.execute(query)
        sessions = result.scalars().all()
        
        return {
            "items": [self._to_dto(s) for s in sessions],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    
    async def cancel_try_on(self, session_id: UUID, user_id: UUID) -> Tuple[bool, Optional[str]]:
        """Cancel pending try-on session."""
        session = await self._get_session(session_id)
        
        if not session:
            return False, "Session not found"
        
        if session.user_id != str(user_id):
            return False, "Unauthorized"
        
        if session.status not in [TryOnStatus.PENDING.value, TryOnStatus.PROCESSING.value]:
            return False, "Cannot cancel completed session"
        
        # Revoke Celery task if pending
        if session.task_id:
            self.celery_app.control.revoke(session.task_id, terminate=True)
        
        session.status = TryOnStatus.EXPIRED.value
        await self.session.flush()
        
        return True, None
    
    async def retry_try_on(self, session_id: UUID, user_id: UUID) -> Tuple[Optional[TryOnResultDTO], Optional[str]]:
        """Retry failed try-on session."""
        session = await self._get_session(session_id)
        
        if not session:
            return None, "Session not found"
        
        if session.user_id != str(user_id):
            return None, "Unauthorized"
        
        if session.status != TryOnStatus.FAILED.value:
            return None, "Can only retry failed sessions"
        
        # Reset status and queue new task
        session.status = TryOnStatus.PENDING.value
        session.error_message = None
        
        task = self.celery_app.send_task(
            "workers.tryon_tasks.process_tryon",
            args=[str(session.id)],
            queue="tryon",
        )
        
        session.task_id = task.id
        await self.session.flush()
        await self.session.refresh(session)
        
        return self._to_dto(session), None
    
    # ─────────────────────────────────────────────────────────────────────────
    # PROCESSING (Called by Celery workers)
    # ─────────────────────────────────────────────────────────────────────────
    
    async def process_try_on(self, session_id: UUID) -> None:
        """
        Process virtual try-on (called by Celery worker).
        
        This method performs the actual AI processing.
        """
        session = await self._get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return
        
        start_time = datetime.now(timezone.utc)
        session.status = TryOnStatus.PROCESSING.value
        session.processing_started_at = start_time
        await self.session.flush()
        
        try:
            # Get processing service
            from services.tryon_service import TryOnProcessingService
            processor = TryOnProcessingService()
            
            # Process images
            result = await processor.process(
                user_image_url=session.user_image_url,
                garment_image_url=session.garment_image_url,
                category=session.metadata.get("category") if session.metadata else None,
            )
            
            # Update session with result
            session.result_image_url = result["result_url"]
            session.quality_score = Decimal(str(result.get("quality_score", 0.85)))
            session.model_used = result.get("model", "idm_vton")
            session.status = TryOnStatus.COMPLETED.value
            session.processing_completed_at = datetime.now(timezone.utc)
            session.processing_time_ms = int(
                (session.processing_completed_at - start_time).total_seconds() * 1000
            )
            
            await self.session.flush()
            
            logger.info(f"Try-on completed: {session_id}")
            
        except Exception as e:
            logger.error(f"Try-on failed: {session_id} - {e}")
            session.status = TryOnStatus.FAILED.value
            session.error_message = str(e)
            session.processing_completed_at = datetime.now(timezone.utc)
            await self.session.flush()
    
    # ─────────────────────────────────────────────────────────────────────────
    # QUALITY VALIDATION
    # ─────────────────────────────────────────────────────────────────────────
    
    async def validate_result(self, session_id: UUID) -> Dict[str, Any]:
        """Validate try-on result quality."""
        session = await self._get_session(session_id)
        if not session or not session.result_image_url:
            return {"valid": False, "reason": "No result available"}
        
        # Quality metrics
        metrics = {
            "realism_score": float(session.quality_score) if session.quality_score else 0.0,
            "edge_quality": 0.85,  # Placeholder
            "color_consistency": 0.90,  # Placeholder
            "proportion_match": 0.88,  # Placeholder
            "artifact_score": 0.95,  # Placeholder (higher is better)
        }
        
        # Calculate overall quality
        weights = {
            "realism_score": 0.30,
            "edge_quality": 0.25,
            "color_consistency": 0.20,
            "proportion_match": 0.15,
            "artifact_score": 0.10,
        }
        
        overall = sum(metrics[k] * weights[k] for k in metrics)
        
        return {
            "valid": overall >= 0.65,
            "overall_quality": overall,
            "metrics": metrics,
            "recommendations": self._get_quality_recommendations(metrics),
        }
    
    def _get_quality_recommendations(self, metrics: Dict[str, float]) -> List[str]:
        """Get recommendations for improving quality."""
        recommendations = []
        
        if metrics["realism_score"] < 0.7:
            recommendations.append("Try using a clearer front-facing photo")
        
        if metrics["edge_quality"] < 0.7:
            recommendations.append("Ensure the garment image has a clean background")
        
        if metrics["color_consistency"] < 0.7:
            recommendations.append("Use better lighting in your photo")
        
        if metrics["proportion_match"] < 0.7:
            recommendations.append("Stand in a natural pose for better fit visualization")
        
        return recommendations
    
    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE METHODS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _get_session(self, session_id: UUID) -> Optional[TryOnSessionModel]:
        """Get try-on session model."""
        query = select(TryOnSessionModel).where(TryOnSessionModel.id == str(session_id))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def _validate_images(self, request: TryOnRequestDTO) -> Optional[str]:
        """Validate input images."""
        # Check URLs are valid
        if not request.user_image_url.startswith(("http://", "https://", "data:")):
            return "Invalid user image URL"
        
        if not request.garment_image_url.startswith(("http://", "https://", "data:")):
            return "Invalid garment image URL"
        
        # In production, you would:
        # 1. Download images and check file size
        # 2. Verify image format
        # 3. Check image dimensions
        # 4. Verify pose detection works on user image
        
        return None
    
    def _to_dto(self, model: TryOnSessionModel) -> TryOnResultDTO:
        """Convert model to DTO."""
        return TryOnResultDTO(
            id=model.id,
            user_id=model.user_id,
            status=model.status,
            user_image_url=model.user_image_url,
            garment_image_url=model.garment_image_url,
            result_image_url=model.result_image_url,
            quality_score=float(model.quality_score) if model.quality_score else None,
            processing_time_ms=model.processing_time_ms,
            error_message=model.error_message,
            created_at=model.created_at,
            completed_at=model.processing_completed_at,
        )
