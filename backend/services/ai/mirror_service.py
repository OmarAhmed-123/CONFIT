"""
CONFIT Backend - MIRROR Virtual Try-On Service
==============================================
AI-powered virtual try-on using Replicate IDM-VTON model.

Features:
- Async processing via Celery
- S3 storage for user photos (encrypted)
- Presigned URLs for secure access
- Rate limiting per user/tier
- Cost tracking (~$0.05/call)
- GDPR/Egypt privacy compliance
- 30-day photo retention
"""

import base64
import hashlib
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Configuration
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
REPLICATE_MODEL = os.getenv("MIRROR_MODEL", "cuuupid/idm-vton:c871bb6b-dde7-4b6d-9e6c-5c5c5c5c5c5c")
MIRROR_COST_USD = float(os.getenv("MIRROR_COST_USD", "0.05"))
S3_BUCKET = os.getenv("S3_BUCKET", "confit-tryon")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
PHOTO_RETENTION_DAYS = int(os.getenv("PHOTO_RETENTION_DAYS", "30"))


class TryOnStatus(str, Enum):
    """Status of try-on session."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class TryOnSession:
    """A virtual try-on session."""
    session_id: str
    user_id: str
    product_id: str
    status: TryOnStatus = TryOnStatus.PENDING
    person_image_key: Optional[str] = None
    garment_image_key: Optional[str] = None
    result_image_key: Optional[str] = None
    result_url: Optional[str] = None
    quality_score: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    replicate_id: Optional[str] = None
    cost_usd: float = 0.0
    latency_ms: float = 0.0


@dataclass
class TryOnRequest:
    """Request for virtual try-on."""
    user_id: str
    product_id: str
    product_sku: str
    person_image_bytes: bytes
    garment_image_url: Optional[str] = None
    garment_image_bytes: Optional[bytes] = None
    category: Optional[str] = "tops"


@dataclass
class TryOnResult:
    """Result from virtual try-on."""
    session_id: str
    status: TryOnStatus
    result_url: Optional[str] = None
    result_image_bytes: Optional[bytes] = None
    quality_score: float = 0.0
    error_message: Optional[str] = None
    cost_usd: float = 0.0
    latency_ms: float = 0.0


class MirrorService:
    """
    MIRROR Virtual Try-On Service.
    
    Usage:
        service = MirrorService(db, redis_client, s3_client)
        
        # Start try-on (async via Celery)
        session = await service.start_tryon(request)
        
        # Check status
        result = await service.get_result(session.session_id)
        
        # Or wait for completion
        result = await service.wait_for_result(session.session_id, timeout=60)
    """
    
    def __init__(self, db: Session, redis_client=None, s3_client=None):
        self.db = db
        self.redis = redis_client
        self.s3 = s3_client
        self._cost_tracker = None
    
    def set_cost_tracker(self, cost_tracker):
        """Set the cost tracker for logging AI calls."""
        self._cost_tracker = cost_tracker
    
    # ==========================================
    # Main Try-On Flow
    # ==========================================
    
    async def start_tryon(
        self,
        request: TryOnRequest,
        background_tasks=None
    ) -> TryOnSession:
        """
        Start a virtual try-on session.
        
        This queues the job via Celery for async processing.
        
        Args:
            request: TryOnRequest with user, product, and images
            background_tasks: FastAPI background tasks (optional)
            
        Returns:
            TryOnSession with session_id and pending status
        """
        session_id = f"tryon-{uuid.uuid4().hex[:12]}"
        
        # 1. Upload person image to S3 (encrypted)
        person_key = await self._upload_person_image(
            user_id=request.user_id,
            session_id=session_id,
            image_bytes=request.person_image_bytes
        )
        
        # 2. Get or upload garment image
        garment_key = await self._get_garment_image(
            product_id=request.product_id,
            product_sku=request.product_sku,
            garment_url=request.garment_image_url,
            garment_bytes=request.garment_image_bytes
        )
        
        # 3. Create session record in database
        session = TryOnSession(
            session_id=session_id,
            user_id=request.user_id,
            product_id=request.product_id,
            status=TryOnStatus.PENDING,
            person_image_key=person_key,
            garment_image_key=garment_key,
        )
        
        await self._save_session(session)
        
        # 4. Queue Celery task for processing
        await self._queue_tryon_task(session)
        
        return session
    
    async def get_result(self, session_id: str) -> TryOnResult:
        """
        Get the current status/result of a try-on session.
        
        Args:
            session_id: Session ID from start_tryon
            
        Returns:
            TryOnResult with current status and result if completed
        """
        session = await self._get_session(session_id)
        
        if not session:
            return TryOnResult(
                session_id=session_id,
                status=TryOnStatus.FAILED,
                error_message="Session not found"
            )
        
        result = TryOnResult(
            session_id=session_id,
            status=TryOnStatus(session.status) if isinstance(session.status, str) else session.status,
            cost_usd=session.cost_usd,
            latency_ms=session.latency_ms,
        )
        
        if session.status == TryOnStatus.COMPLETED:
            # Generate presigned URL for result
            result.result_url = await self._get_presigned_url(session.result_image_key)
            result.quality_score = session.quality_score
        
        if session.status == TryOnStatus.FAILED:
            result.error_message = session.error_message
        
        return result
    
    async def wait_for_result(
        self,
        session_id: str,
        timeout: int = 120,
        poll_interval: float = 2.0
    ) -> TryOnResult:
        """
        Wait for try-on completion with polling.
        
        Args:
            session_id: Session ID
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            TryOnResult when completed or timeout
        """
        import asyncio
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = await self.get_result(session_id)
            
            if result.status in (TryOnStatus.COMPLETED, TryOnStatus.FAILED):
                return result
            
            await asyncio.sleep(poll_interval)
        
        return TryOnResult(
            session_id=session_id,
            status=TryOnStatus.FAILED,
            error_message="Timeout waiting for result"
        )
    
    # ==========================================
    # Celery Task Processing
    # ==========================================
    
    async def process_tryon_task(self, session_id: str) -> None:
        """
        Process a try-on task (called by Celery worker).
        
        This calls Replicate IDM-VTON API.
        """
        start_time = time.perf_counter()
        
        session = await self._get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return
        
        try:
            # Update status
            await self._update_status(session_id, TryOnStatus.PROCESSING)
            
            # Get presigned URLs for images
            person_url = await self._get_presigned_url(session.person_image_key)
            garment_url = await self._get_presigned_url(session.garment_image_key)
            
            # Call Replicate API
            result_url, replicate_id = await self._call_replicate(
                person_url=person_url,
                garment_url=garment_url
            )
            
            # Download result and upload to S3
            result_bytes = await self._download_image(result_url)
            result_key = await self._upload_result_image(
                session_id=session_id,
                image_bytes=result_bytes
            )
            
            # Calculate quality score
            quality_score = await self._calculate_quality(result_bytes)
            
            # Calculate latency
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Update session
            await self._update_completed(
                session_id=session_id,
                result_key=result_key,
                replicate_id=replicate_id,
                quality_score=quality_score,
                latency_ms=latency_ms
            )
            
            # Track cost
            if self._cost_tracker:
                await self._cost_tracker.track(
                    service="mirror",
                    model="idm-vton",
                    user_id=session.user_id,
                    cost_usd=MIRROR_COST_USD,
                    latency_ms=latency_ms,
                    metadata={"session_id": session_id, "product_id": session.product_id}
                )
            
            # Track analytics
            await self._track_analytics(
                user_id=session.user_id,
                product_id=session.product_id,
                session_id=session_id,
                quality_score=quality_score
            )
            
        except Exception as e:
            logger.error(f"Try-on processing failed: {e}")
            await self._update_failed(session_id, str(e))
    
    async def _call_replicate(
        self,
        person_url: str,
        garment_url: str
    ) -> tuple[str, str]:
        """
        Call Replicate IDM-VTON API.
        
        Returns:
            (result_image_url, prediction_id)
        """
        import httpx
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Create prediction
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={
                    "Authorization": f"Token {REPLICATE_API_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "version": REPLICATE_MODEL.split(":")[-1],
                    "input": {
                        "human_img": person_url,
                        "garm_img": garment_url,
                        "category": "upper_body",  # or lower_body, full_body
                        "is_checked": False,
                        "denoise_steps": 30,
                    }
                }
            )
            
            if response.status_code != 201:
                raise Exception(f"Replicate API error: {response.text}")
            
            prediction = response.json()
            prediction_id = prediction["id"]
            
            # Poll for result
            result_url = await self._poll_replicate(client, prediction_id)
            
            return result_url, prediction_id
    
    async def _poll_replicate(
        self,
        client,
        prediction_id: str,
        timeout: int = 120,
        poll_interval: float = 2.0
    ) -> str:
        """Poll Replicate for prediction result."""
        import asyncio
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = await client.get(
                f"https://api.replicate.com/v1/predictions/{prediction_id}",
                headers={"Authorization": f"Token {REPLICATE_API_TOKEN}"}
            )
            
            if response.status_code != 200:
                raise Exception(f"Replicate poll error: {response.text}")
            
            data = response.json()
            status = data.get("status")
            
            if status == "succeeded":
                output = data.get("output")
                if isinstance(output, list) and len(output) > 0:
                    return output[0]
                return output
            
            if status == "failed":
                error = data.get("error", "Unknown error")
                raise Exception(f"Replicate prediction failed: {error}")
            
            if status == "canceled":
                raise Exception("Replicate prediction was canceled")
            
            await asyncio.sleep(poll_interval)
        
        raise Exception("Replicate prediction timeout")
    
    # ==========================================
    # S3 Storage Operations
    # ==========================================
    
    async def _upload_person_image(
        self,
        user_id: str,
        session_id: str,
        image_bytes: bytes
    ) -> str:
        """Upload person image to S3 with encryption."""
        if not self.s3:
            # Fallback: store in Redis temporarily
            return await self._store_in_redis(f"person:{session_id}", image_bytes)
        
        key = f"tryon/{user_id}/{session_id}/person.jpg"
        
        # Compute hash for deduplication
        image_hash = hashlib.sha256(image_bytes).hexdigest()[:16]
        
        try:
            self.s3.put_object(
                Bucket=S3_BUCKET,
                Key=key,
                Body=image_bytes,
                ContentType="image/jpeg",
                Metadata={
                    "user-id": user_id,
                    "session-id": session_id,
                    "image-hash": image_hash,
                    "created-at": datetime.now(timezone.utc).isoformat(),
                },
                # Enable server-side encryption
                ServerSideEncryption="AES256",
            )
            
            return key
            
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise
    
    async def _upload_result_image(
        self,
        session_id: str,
        image_bytes: bytes
    ) -> str:
        """Upload result image to S3."""
        # Extract user_id from session_id pattern
        key = f"tryon/results/{session_id}/result.jpg"
        
        if not self.s3:
            return await self._store_in_redis(f"result:{session_id}", image_bytes)
        
        try:
            self.s3.put_object(
                Bucket=S3_BUCKET,
                Key=key,
                Body=image_bytes,
                ContentType="image/jpeg",
                ServerSideEncryption="AES256",
            )
            
            return key
            
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise
    
    async def _get_garment_image(
        self,
        product_id: str,
        product_sku: str,
        garment_url: Optional[str] = None,
        garment_bytes: Optional[bytes] = None
    ) -> str:
        """Get garment image - either from URL or bytes."""
        if garment_url:
            # Download and store
            image_bytes = await self._download_image(garment_url)
            key = f"tryon/garments/{product_sku}.jpg"
            
            if self.s3:
                self.s3.put_object(
                    Bucket=S3_BUCKET,
                    Key=key,
                    Body=image_bytes,
                    ContentType="image/jpeg",
                )
                return key
            else:
                return await self._store_in_redis(f"garment:{product_sku}", image_bytes)
        
        if garment_bytes:
            key = f"tryon/garments/{product_sku}.jpg"
            
            if self.s3:
                self.s3.put_object(
                    Bucket=S3_BUCKET,
                    Key=key,
                    Body=garment_bytes,
                    ContentType="image/jpeg",
                )
                return key
            else:
                return await self._store_in_redis(f"garment:{product_sku}", garment_bytes)
        
        raise ValueError("No garment image provided")
    
    async def _get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600
    ) -> str:
        """Generate presigned URL for S3 object."""
        if not self.s3:
            # Fallback: return Redis key as-is (for development)
            return f"redis://{key}"
        
        try:
            url = self.s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": S3_BUCKET, "Key": key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            logger.error(f"Presigned URL generation failed: {e}")
            raise
    
    async def _download_image(self, url: str) -> bytes:
        """Download image from URL."""
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
    
    async def _store_in_redis(self, key: str, data: bytes) -> str:
        """Store data in Redis as fallback."""
        if not self.redis:
            raise ValueError("No storage backend available")
        
        # Store with 24h expiry
        self.redis.setex(f"tryon:storage:{key}", 86400, data)
        return key
    
    # ==========================================
    # Quality Assessment
    # ==========================================
    
    async def _calculate_quality(self, image_bytes: bytes) -> float:
        """
        Calculate quality score for try-on result.
        
        Uses image analysis to detect artifacts and blending quality.
        """
        try:
            import cv2
            import numpy as np
            from PIL import Image
            import io
            
            # Load image
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            img_array = np.array(image)
            
            # Convert to OpenCV format
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # 1. Check for artifacts at edges
            edges = cv2.Canny(cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY), 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            # Lower edge density in center = better blending
            h, w = edges.shape
            center_mask = np.zeros_like(edges)
            cv2.rectangle(center_mask, (w//4, h//4), (3*w//4, 3*h//4), 255, -1)
            center_edge_density = np.sum((edges > 0) & (center_mask > 0)) / np.sum(center_mask > 0)
            
            # 2. Check color consistency
            hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
            
            # Variance in saturation (lower = more consistent)
            s_var = np.var(hsv[:, :, 1])
            s_score = 1 - min(s_var / 5000, 1)  # Normalize
            
            # 3. Check brightness distribution
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            brightness_std = np.std(gray)
            b_score = 1 - min(brightness_std / 100, 1)
            
            # Combine scores
            quality = (
                0.3 * (1 - center_edge_density) +
                0.4 * s_score +
                0.3 * b_score
            )
            
            return float(np.clip(quality, 0, 1))
            
        except Exception as e:
            logger.debug(f"Quality calculation failed: {e}")
            return 0.7  # Default score
    
    # ==========================================
    # Database Operations
    # ==========================================
    
    async def _save_session(self, session: TryOnSession) -> None:
        """Save session to database."""
        try:
            sql = text("""
                INSERT INTO try_on_sessions (
                    id, user_id, product_id, status, person_image_key,
                    garment_image_key, created_at
                ) VALUES (
                    :id, :user_id, :product_id, :status, :person_image_key,
                    :garment_image_key, :created_at
                )
            """)
            
            self.db.execute(sql, {
                "id": session.session_id,
                "user_id": session.user_id,
                "product_id": session.product_id,
                "status": session.status.value,
                "person_image_key": session.person_image_key,
                "garment_image_key": session.garment_image_key,
                "created_at": session.created_at,
            })
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            self.db.rollback()
            raise
    
    async def _get_session(self, session_id: str) -> Optional[TryOnSession]:
        """Get session from database."""
        try:
            sql = text("""
                SELECT * FROM try_on_sessions WHERE id = :id
            """)
            
            result = self.db.execute(sql, {"id": session_id})
            row = result.fetchone()
            
            if not row:
                return None
            
            return TryOnSession(
                session_id=row.id,
                user_id=row.user_id,
                product_id=row.product_id,
                status=TryOnStatus(row.status),
                person_image_key=row.person_image_key,
                garment_image_key=row.garment_image_key,
                result_image_key=row.result_image_key,
                result_url=row.result_url,
                quality_score=row.quality_score or 0,
                created_at=row.created_at,
                completed_at=row.completed_at,
                error_message=row.error_message,
                replicate_id=row.replicate_id,
                cost_usd=row.cost_usd or 0,
                latency_ms=row.latency_ms or 0,
            )
            
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None
    
    async def _update_status(self, session_id: str, status: TryOnStatus) -> None:
        """Update session status."""
        try:
            sql = text("""
                UPDATE try_on_sessions SET status = :status WHERE id = :id
            """)
            self.db.execute(sql, {"id": session_id, "status": status.value})
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update status: {e}")
            self.db.rollback()
    
    async def _update_completed(
        self,
        session_id: str,
        result_key: str,
        replicate_id: str,
        quality_score: float,
        latency_ms: float
    ) -> None:
        """Update session as completed."""
        try:
            sql = text("""
                UPDATE try_on_sessions SET
                    status = :status,
                    result_image_key = :result_key,
                    replicate_id = :replicate_id,
                    quality_score = :quality_score,
                    latency_ms = :latency_ms,
                    cost_usd = :cost_usd,
                    completed_at = :completed_at
                WHERE id = :id
            """)
            
            self.db.execute(sql, {
                "id": session_id,
                "status": TryOnStatus.COMPLETED.value,
                "result_key": result_key,
                "replicate_id": replicate_id,
                "quality_score": quality_score,
                "latency_ms": latency_ms,
                "cost_usd": MIRROR_COST_USD,
                "completed_at": datetime.now(timezone.utc),
            })
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to update completed: {e}")
            self.db.rollback()
    
    async def _update_failed(self, session_id: str, error_message: str) -> None:
        """Update session as failed."""
        try:
            sql = text("""
                UPDATE try_on_sessions SET
                    status = :status,
                    error_message = :error_message
                WHERE id = :id
            """)
            
            self.db.execute(sql, {
                "id": session_id,
                "status": TryOnStatus.FAILED.value,
                "error_message": error_message,
            })
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to update failed: {e}")
            self.db.rollback()
    
    # ==========================================
    # Celery Task Queue
    # ==========================================
    
    async def _queue_tryon_task(self, session: TryOnSession) -> None:
        """Queue try-on task via Celery."""
        try:
            from workers.celery_app import celery_app
            
            celery_app.send_task(
                "workers.mirror_tasks.process_tryon",
                kwargs={"session_id": session.session_id},
                queue="mirror",
            )
            
        except Exception as e:
            logger.error(f"Failed to queue task: {e}")
            # Fallback: process synchronously (for development)
            await self.process_tryon_task(session.session_id)
    
    # ==========================================
    # Analytics Tracking
    # ==========================================
    
    async def _track_analytics(
        self,
        user_id: str,
        product_id: str,
        session_id: str,
        quality_score: float
    ) -> None:
        """Track try-on analytics."""
        try:
            from services.analytics_service import analytics_service
            
            await analytics_service.track(
                "try_on_completed",
                user_id=user_id,
                product_id=product_id,
                properties={
                    "session_id": session_id,
                    "quality_score": quality_score,
                }
            )
            
        except Exception as e:
            logger.debug(f"Analytics tracking failed: {e}")
    
    # ==========================================
    # Rate Limiting
    # ==========================================
    
    async def check_rate_limit(self, user_id: str, tier: str = "free") -> tuple[bool, int]:
        """
        Check if user is within rate limits.
        
        Free: 10/day
        Club: 50/day
        Icon (donors): 200/day
        """
        if not self.redis:
            return True, 0
        
        limits = {
            "free": 10,
            "club": 50,
            "icon": 200,
        }
        
        limit = limits.get(tier, 10)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"mirror:ratelimit:{user_id}:{today}"
        
        try:
            current = self.redis.get(key)
            if current is None:
                self.redis.setex(key, 86400, 1)
                return True, 0
            
            count = int(current)
            if count >= limit:
                return False, 86400  # Retry tomorrow
            
            self.redis.incr(key)
            return True, 0
            
        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")
            return True, 0
    
    # ==========================================
    # Cleanup / GDPR Compliance
    # ==========================================
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions and photos.
        
        Called by scheduled task (daily).
        Returns count of cleaned sessions.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=PHOTO_RETENTION_DAYS)
        
        try:
            # Get expired sessions
            sql = text("""
                SELECT id, person_image_key, result_image_key
                FROM try_on_sessions
                WHERE created_at < :cutoff AND status != 'expired'
            """)
            
            result = self.db.execute(sql, {"cutoff": cutoff})
            sessions = result.fetchall()
            
            cleaned = 0
            
            for session in sessions:
                # Delete S3 objects
                if self.s3:
                    if session.person_image_key:
                        try:
                            self.s3.delete_object(
                                Bucket=S3_BUCKET,
                                Key=session.person_image_key
                            )
                        except Exception:
                            pass
                    
                    if session.result_image_key:
                        try:
                            self.s3.delete_object(
                                Bucket=S3_BUCKET,
                                Key=session.result_image_key
                            )
                        except Exception:
                            pass
                
                # Mark as expired
                update_sql = text("""
                    UPDATE try_on_sessions SET status = 'expired' WHERE id = :id
                """)
                self.db.execute(update_sql, {"id": session.id})
                
                cleaned += 1
            
            self.db.commit()
            return cleaned
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            self.db.rollback()
            return 0
    
    async def delete_user_data(self, user_id: str) -> bool:
        """
        Delete all user try-on data (GDPR/Right to be Forgotten).
        """
        try:
            # Get all user sessions
            sql = text("""
                SELECT id, person_image_key, result_image_key
                FROM try_on_sessions WHERE user_id = :user_id
            """)
            
            result = self.db.execute(sql, {"user_id": user_id})
            sessions = result.fetchall()
            
            # Delete S3 objects
            if self.s3:
                for session in sessions:
                    for key in [session.person_image_key, session.result_image_key]:
                        if key:
                            try:
                                self.s3.delete_object(Bucket=S3_BUCKET, Key=key)
                            except Exception:
                                pass
            
            # Delete database records
            delete_sql = text("DELETE FROM try_on_sessions WHERE user_id = :user_id")
            self.db.execute(delete_sql, {"user_id": user_id})
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"User data deletion failed: {e}")
            self.db.rollback()
            return False
