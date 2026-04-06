"""
CONFIT Backend — Try-On Session Service
======================================
Manages persistence of virtual try-on sessions
for analytics, history, and quality tracking.
"""

import logging
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import desc

from database.models import TryOnSession

logger = logging.getLogger(__name__)


class TryOnSessionService:
    """Service for managing try-on session persistence."""

    def __init__(self, db: Session):
        self._db = db

    def _hash_image(self, image_data: str) -> str:
        """Generate SHA-256 hash of image data for privacy-preserving tracking."""
        # Remove data URI prefix if present
        if "," in image_data and image_data.startswith("data:"):
            image_data = image_data.split(",", 1)[1]
        return hashlib.sha256(image_data.encode("utf-8")).hexdigest()

    async def create_session(
        self,
        user_id: Optional[str],
        user_image_base64: str,
        garment_image_url: str,
        garment_name: str,
        garment_category: str,
        fit_type: str,
        result_image_base64: Optional[str],
        quality_score: float,
        pose_detected: bool,
        processing_mode: str,
        processing_time_ms: float,
        validation_result: Optional[Any] = None,
        warnings: Optional[List[str]] = None,
        error_message: Optional[str] = None,
    ) -> TryOnSession:
        """
        Create and persist a try-on session record.
        
        Args:
            user_id: Optional user ID
            user_image_base64: User's uploaded image
            garment_image_url: URL of the garment
            garment_name: Name of the garment
            garment_category: Detected category
            fit_type: Fit type used
            result_image_base64: Result image (base64)
            quality_score: Overall quality score
            pose_detected: Whether pose was detected
            processing_mode: Processing mode used
            processing_time_ms: Processing time
            validation_result: Optional validation result with detailed metrics
            warnings: List of warnings
            error_message: Error message if failed
            
        Returns:
            Created TryOnSession instance
        """
        session = TryOnSession(
            user_id=user_id,
            user_image_hash=self._hash_image(user_image_base64),
            garment_image_url=garment_image_url,
            garment_name=garment_name,
            garment_category=garment_category,
            fit_type=fit_type,
            result_image_url=None,  # Could be extended to store in cloud
            result_image_hash=self._hash_image(result_image_base64) if result_image_base64 else None,
            quality_score=quality_score,
            pose_detected=pose_detected,
            processing_mode=processing_mode,
            processing_time_ms=processing_time_ms,
            status="completed" if error_message is None else "failed",
            error_message=error_message,
            warnings=warnings or [],
        )

        # Add validation metrics if available
        if validation_result is not None:
            session.realism_score = getattr(validation_result, "realism_score", None)
            session.edge_quality = getattr(validation_result, "edge_quality_score", None)
            session.color_consistency = getattr(validation_result, "color_consistency_score", None)
            session.proportion_score = getattr(validation_result, "proportion_score", None)
            session.artifact_score = getattr(validation_result, "artifact_score", None)

        self._db.add(session)
        self._db.commit()
        self._db.refresh(session)

        logger.info(f"Created try-on session {session.id} (quality={quality_score:.2f})")

        return session

    def get_user_sessions(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[TryOnSession]:
        """
        Get try-on sessions for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of sessions to return
            offset: Offset for pagination
            
        Returns:
            List of TryOnSession instances
        """
        return self._db.query(TryOnSession).filter(
            TryOnSession.user_id == user_id
        ).order_by(
            desc(TryOnSession.created_at)
        ).offset(offset).limit(limit).all()

    def get_session(self, session_id: str) -> Optional[TryOnSession]:
        """Get a specific try-on session by ID."""
        return self._db.query(TryOnSession).filter(
            TryOnSession.id == session_id
        ).first()

    def get_quality_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get quality statistics for try-on sessions.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            Dictionary with quality statistics
        """
        query = self._db.query(TryOnSession)

        if user_id:
            query = query.filter(TryOnSession.user_id == user_id)

        sessions = query.all()

        if not sessions:
            return {
                "total_sessions": 0,
                "avg_quality_score": 0.0,
                "avg_processing_time_ms": 0.0,
                "pose_detection_rate": 0.0,
                "success_rate": 0.0,
            }

        total = len(sessions)
        successful = [s for s in sessions if s.status == "completed"]

        return {
            "total_sessions": total,
            "avg_quality_score": sum(s.quality_score for s in sessions) / total,
            "avg_processing_time_ms": sum(s.processing_time_ms for s in sessions) / total,
            "pose_detection_rate": sum(1 for s in sessions if s.pose_detected) / total,
            "success_rate": len(successful) / total,
            "by_processing_mode": self._get_mode_distribution(sessions),
            "by_category": self._get_category_distribution(sessions),
        }

    def _get_mode_distribution(self, sessions: List[TryOnSession]) -> Dict[str, int]:
        """Get distribution of processing modes."""
        distribution = {}
        for session in sessions:
            mode = session.processing_mode
            distribution[mode] = distribution.get(mode, 0) + 1
        return distribution

    def _get_category_distribution(self, sessions: List[TryOnSession]) -> Dict[str, int]:
        """Get distribution of garment categories."""
        distribution = {}
        for session in sessions:
            category = session.garment_category
            distribution[category] = distribution.get(category, 0) + 1
        return distribution

    def delete_old_sessions(self, days: int = 30) -> int:
        """
        Delete sessions older than specified days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of deleted sessions
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        deleted = self._db.query(TryOnSession).filter(
            TryOnSession.created_at < cutoff
        ).delete()

        self._db.commit()

        if deleted > 0:
            logger.info(f"Deleted {deleted} old try-on sessions")

        return deleted
