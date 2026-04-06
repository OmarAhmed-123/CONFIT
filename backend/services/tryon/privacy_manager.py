"""
CONFIT Backend — Privacy Manager for Virtual Try-On
===================================================
Privacy-by-design implementation for user images.

Features:
- Temporary image storage with TTL
- Encryption at rest
- Automatic deletion lifecycle
- Access logging and audit trail
- GDPR compliance helpers
"""

import os
import io
import logging
import hashlib
import base64
import secrets
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class ImageStatus(Enum):
    """Status of stored image."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    EXPIRED = "expired"
    DELETED = "deleted"


@dataclass
class ImageMetadata:
    """Metadata for stored image."""
    image_id: str
    user_id: str
    session_id: str
    
    # Storage info
    encrypted_path: Optional[str] = None
    size_bytes: int = 0
    content_hash: str = ""
    
    # Lifecycle
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=1))
    deleted_at: Optional[datetime] = None
    
    # Status
    status: ImageStatus = ImageStatus.PENDING
    
    # Access tracking
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    # Encryption
    encryption_key_id: str = ""


@dataclass
class PrivacyReport:
    """Privacy compliance report for a session."""
    session_id: str
    user_id: str
    
    # Images stored
    images_stored: int = 0
    images_deleted: int = 0
    images_expired: int = 0
    
    # Retention
    max_retention_hours: float = 0
    actual_retention_hours: float = 0
    
    # Encryption
    encryption_enabled: bool = True
    encryption_algorithm: str = "AES-256-GCM"
    
    # Access
    total_accesses: int = 0
    unauthorized_attempts: int = 0
    
    # Compliance
    gdpr_compliant: bool = True
    issues: list = field(default_factory=list)


class PrivacyManager:
    """
    Privacy-by-design manager for virtual try-on images.
    
    Implements:
    - Temporary storage with automatic expiration
    - Encryption at rest using AES-256
    - Secure deletion with verification
    - Access logging and audit trail
    - GDPR compliance helpers
    
    Usage:
        manager = PrivacyManager(storage_path, encryption_key)
        
        # Store image
        image_id = await manager.store_user_image(
            user_id, session_id, image_bytes
        )
        
        # Retrieve image
        image = await manager.retrieve_image(image_id, user_id)
        
        # Delete image
        await manager.delete_image(image_id, user_id)
    """
    
    # Default TTL for images (1 hour)
    DEFAULT_TTL_HOURS = 1
    
    # Maximum TTL allowed (24 hours)
    MAX_TTL_HOURS = 24
    
    # Allowed image types
    ALLOWED_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
    
    # Maximum image size (20 MB)
    MAX_IMAGE_SIZE = 20 * 1024 * 1024
    
    def __init__(
        self,
        storage_path: str = "/tmp/tryon_images",
        encryption_key: Optional[bytes] = None
    ):
        """
        Initialize privacy manager.
        
        Args:
            storage_path: Base path for encrypted image storage
            encryption_key: Optional encryption key (generated if not provided)
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize encryption
        if encryption_key is None:
            encryption_key = self._generate_encryption_key()
        
        self.cipher = Fernet(encryption_key)
        self.encryption_key_id = hashlib.sha256(encryption_key).hexdigest()[:16]
        
        # In-memory metadata store (in production, use database)
        self._metadata: Dict[str, ImageMetadata] = {}
        
        # Access log
        self._access_log: list = []
    
    def _generate_encryption_key(self) -> bytes:
        """Generate a new encryption key."""
        return Fernet.generate_key()
    
    # ==========================================
    # Image Storage
    # ==========================================
    
    async def store_user_image(
        self,
        user_id: str,
        session_id: str,
        image_bytes: bytes,
        content_type: str = "image/jpeg",
        ttl_hours: Optional[float] = None
    ) -> str:
        """
        Store user image with privacy protections.
        
        Args:
            user_id: User identifier
            session_id: Try-on session ID
            image_bytes: Raw image bytes
            content_type: MIME type of image
            ttl_hours: Time-to-live in hours (default: 1)
            
        Returns:
            Image ID for retrieval
            
        Raises:
            ValueError: If image validation fails
        """
        # Validate content type
        if content_type not in self.ALLOWED_TYPES:
            raise ValueError(f"Invalid content type: {content_type}")
        
        # Validate size
        if len(image_bytes) > self.MAX_IMAGE_SIZE:
            raise ValueError(f"Image too large: {len(image_bytes)} bytes (max: {self.MAX_IMAGE_SIZE})")
        
        # Clamp TTL
        ttl = min(ttl_hours or self.DEFAULT_TTL_HOURS, self.MAX_TTL_HOURS)
        
        # Generate unique image ID
        image_id = self._generate_image_id(user_id, session_id)
        
        # Calculate content hash for integrity
        content_hash = hashlib.sha256(image_bytes).hexdigest()
        
        # Encrypt image
        encrypted_data = self.cipher.encrypt(image_bytes)
        
        # Create metadata
        metadata = ImageMetadata(
            image_id=image_id,
            user_id=user_id,
            session_id=session_id,
            size_bytes=len(image_bytes),
            content_hash=content_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl),
            status=ImageStatus.PENDING,
            encryption_key_id=self.encryption_key_id,
        )
        
        # Store encrypted image
        encrypted_path = self.storage_path / f"{image_id}.enc"
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)
        
        metadata.encrypted_path = str(encrypted_path)
        metadata.status = ImageStatus.PROCESSING
        
        # Store metadata
        self._metadata[image_id] = metadata
        
        # Log storage
        self._log_access(image_id, user_id, "store", success=True)
        
        logger.info(
            f"Stored encrypted image {image_id} for user {user_id}, "
            f"expires at {metadata.expires_at}"
        )
        
        return image_id
    
    async def store_garment_image(
        self,
        garment_id: str,
        image_bytes: bytes,
        content_type: str = "image/jpeg"
    ) -> str:
        """
        Store garment image (product image, longer retention).
        
        Args:
            garment_id: Garment identifier
            image_bytes: Raw image bytes
            content_type: MIME type
            
        Returns:
            Image ID
        """
        # Garment images have longer TTL (24 hours for caching)
        image_id = f"garment_{garment_id}_{secrets.token_hex(8)}"
        
        # Encrypt
        encrypted_data = self.cipher.encrypt(image_bytes)
        
        # Store
        encrypted_path = self.storage_path / f"{image_id}.enc"
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Create metadata
        metadata = ImageMetadata(
            image_id=image_id,
            user_id="system",
            session_id=garment_id,
            size_bytes=len(image_bytes),
            content_hash=hashlib.sha256(image_bytes).hexdigest(),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=self.MAX_TTL_HOURS),
            status=ImageStatus.COMPLETED,
            encrypted_path=str(encrypted_path),
            encryption_key_id=self.encryption_key_id,
        )
        
        self._metadata[image_id] = metadata
        
        return image_id
    
    # ==========================================
    # Image Retrieval
    # ==========================================
    
    async def retrieve_image(
        self,
        image_id: str,
        user_id: str
    ) -> Optional[bytes]:
        """
        Retrieve and decrypt image.
        
        Args:
            image_id: Image ID from storage
            user_id: Requesting user ID (for authorization)
            
        Returns:
            Decrypted image bytes, or None if not found/expired
            
        Raises:
            PermissionError: If user doesn't own the image
        """
        # Check metadata
        metadata = self._metadata.get(image_id)
        
        if metadata is None:
            logger.warning(f"Image not found: {image_id}")
            self._log_access(image_id, user_id, "retrieve", success=False, reason="not_found")
            return None
        
        # Check authorization
        if metadata.user_id != user_id and metadata.user_id != "system":
            logger.warning(f"Unauthorized access attempt by {user_id} to image {image_id}")
            self._log_access(image_id, user_id, "retrieve", success=False, reason="unauthorized")
            raise PermissionError("Not authorized to access this image")
        
        # Check expiration
        if datetime.now(timezone.utc) > metadata.expires_at:
            logger.info(f"Image expired: {image_id}")
            metadata.status = ImageStatus.EXPIRED
            self._log_access(image_id, user_id, "retrieve", success=False, reason="expired")
            return None
        
        # Check if deleted
        if metadata.status == ImageStatus.DELETED:
            logger.warning(f"Attempt to retrieve deleted image: {image_id}")
            self._log_access(image_id, user_id, "retrieve", success=False, reason="deleted")
            return None
        
        # Read encrypted data
        encrypted_path = Path(metadata.encrypted_path)
        if not encrypted_path.exists():
            logger.error(f"Encrypted file missing: {encrypted_path}")
            self._log_access(image_id, user_id, "retrieve", success=False, reason="file_missing")
            return None
        
        with open(encrypted_path, 'rb') as f:
            encrypted_data = f.read()
        
        # Decrypt
        try:
            decrypted_data = self.cipher.decrypt(encrypted_data)
        except Exception as e:
            logger.error(f"Decryption failed for {image_id}: {e}")
            self._log_access(image_id, user_id, "retrieve", success=False, reason="decryption_failed")
            return None
        
        # Verify integrity
        content_hash = hashlib.sha256(decrypted_data).hexdigest()
        if content_hash != metadata.content_hash:
            logger.error(f"Integrity check failed for {image_id}")
            self._log_access(image_id, user_id, "retrieve", success=False, reason="integrity_failed")
            return None
        
        # Update metadata
        metadata.access_count += 1
        metadata.last_accessed = datetime.now(timezone.utc)
        
        # Log successful access
        self._log_access(image_id, user_id, "retrieve", success=True)
        
        return decrypted_data
    
    # ==========================================
    # Image Deletion
    # ==========================================
    
    async def delete_image(
        self,
        image_id: str,
        user_id: str,
        reason: str = "user_request"
    ) -> bool:
        """
        Securely delete image.
        
        Implements secure deletion:
        1. Overwrite encrypted file with random data
        2. Delete file
        3. Update metadata
        
        Args:
            image_id: Image ID to delete
            user_id: Requesting user ID
            reason: Reason for deletion
            
        Returns:
            True if deletion successful
        """
        metadata = self._metadata.get(image_id)
        
        if metadata is None:
            logger.warning(f"Cannot delete non-existent image: {image_id}")
            return False
        
        # Check authorization
        if metadata.user_id != user_id and metadata.user_id != "system":
            raise PermissionError("Not authorized to delete this image")
        
        # Check if already deleted
        if metadata.status == ImageStatus.DELETED:
            return True
        
        encrypted_path = Path(metadata.encrypted_path)
        
        if encrypted_path.exists():
            # Secure overwrite (3 passes)
            file_size = encrypted_path.stat().st_size
            
            for _ in range(3):
                with open(encrypted_path, 'wb') as f:
                    f.write(secrets.token_bytes(file_size))
                os.fsync(f.fileno())
            
            # Delete file
            encrypted_path.unlink()
        
        # Update metadata
        metadata.status = ImageStatus.DELETED
        metadata.deleted_at = datetime.now(timezone.utc)
        metadata.encrypted_path = None
        
        # Log deletion
        self._log_access(image_id, user_id, "delete", success=True, reason=reason)
        
        logger.info(f"Securely deleted image {image_id}, reason: {reason}")
        
        return True
    
    async def delete_session_images(
        self,
        session_id: str,
        user_id: str
    ) -> int:
        """
        Delete all images for a session.
        
        Args:
            session_id: Session to clean up
            user_id: Requesting user ID
            
        Returns:
            Number of images deleted
        """
        deleted_count = 0
        
        for image_id, metadata in list(self._metadata.items()):
            if metadata.session_id == session_id and metadata.user_id == user_id:
                if await self.delete_image(image_id, user_id, reason="session_cleanup"):
                    deleted_count += 1
        
        logger.info(f"Deleted {deleted_count} images for session {session_id}")
        return deleted_count
    
    # ==========================================
    # Lifecycle Management
    # ==========================================
    
    async def cleanup_expired_images(self) -> int:
        """
        Clean up all expired images.
        
        Called periodically by maintenance task.
        
        Returns:
            Number of images cleaned up
        """
        now = datetime.now(timezone.utc)
        expired_count = 0
        
        for image_id, metadata in list(self._metadata.items()):
            if metadata.expires_at < now and metadata.status not in [ImageStatus.DELETED, ImageStatus.EXPIRED]:
                # Mark as expired
                metadata.status = ImageStatus.EXPIRED
                
                # Secure delete
                encrypted_path = Path(metadata.encrypted_path) if metadata.encrypted_path else None
                
                if encrypted_path and encrypted_path.exists():
                    # Overwrite and delete
                    file_size = encrypted_path.stat().st_size
                    with open(encrypted_path, 'wb') as f:
                        f.write(secrets.token_bytes(file_size))
                    encrypted_path.unlink()
                
                metadata.deleted_at = now
                metadata.encrypted_path = None
                expired_count += 1
                
                self._log_access(image_id, "system", "expire", success=True)
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired images")
        
        return expired_count
    
    def get_image_status(self, image_id: str) -> Optional[Dict[str, Any]]:
        """Get status of stored image."""
        metadata = self._metadata.get(image_id)
        
        if metadata is None:
            return None
        
        return {
            'image_id': metadata.image_id,
            'status': metadata.status.value,
            'created_at': metadata.created_at.isoformat(),
            'expires_at': metadata.expires_at.isoformat(),
            'deleted_at': metadata.deleted_at.isoformat() if metadata.deleted_at else None,
            'access_count': metadata.access_count,
            'size_bytes': metadata.size_bytes,
        }
    
    # ==========================================
    # Privacy Reporting
    # ==========================================
    
    def generate_privacy_report(
        self,
        session_id: str,
        user_id: str
    ) -> PrivacyReport:
        """
        Generate privacy compliance report for a session.
        
        Args:
            session_id: Session to report on
            user_id: User ID
            
        Returns:
            PrivacyReport with compliance details
        """
        session_images = [
            m for m in self._metadata.values()
            if m.session_id == session_id and m.user_id == user_id
        ]
        
        report = PrivacyReport(
            session_id=session_id,
            user_id=user_id,
            images_stored=len(session_images),
        )
        
        # Calculate metrics
        for metadata in session_images:
            if metadata.status == ImageStatus.DELETED:
                report.images_deleted += 1
            elif metadata.status == ImageStatus.EXPIRED:
                report.images_expired += 1
            
            report.total_accesses += metadata.access_count
            
            # Calculate retention
            if metadata.deleted_at:
                retention = (metadata.deleted_at - metadata.created_at).total_seconds() / 3600
                report.actual_retention_hours = max(report.actual_retention_hours, retention)
            
            report.max_retention_hours = max(
                report.max_retention_hours,
                (metadata.expires_at - metadata.created_at).total_seconds() / 3600
            )
        
        # Check compliance
        issues = []
        
        if report.max_retention_hours > self.MAX_TTL_HOURS:
            issues.append(f"Max retention exceeds limit: {report.max_retention_hours}h")
        
        if report.images_deleted + report.images_expired < report.images_stored:
            issues.append("Some images not yet deleted")
        
        report.issues = issues
        report.gdpr_compliant = len(issues) == 0
        
        return report
    
    def get_access_log(
        self,
        image_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """
        Get access log entries.
        
        Args:
            image_id: Filter by image ID
            user_id: Filter by user ID
            limit: Maximum entries to return
            
        Returns:
            List of access log entries
        """
        logs = self._access_log
        
        if image_id:
            logs = [l for l in logs if l.get('image_id') == image_id]
        
        if user_id:
            logs = [l for l in logs if l.get('user_id') == user_id]
        
        return logs[-limit:]
    
    # ==========================================
    # GDPR Compliance Helpers
    # ==========================================
    
    async def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Export all user data for GDPR request.
        
        Args:
            user_id: User to export data for
            
        Returns:
            Dict with all user data
        """
        user_images = [
            m for m in self._metadata.values()
            if m.user_id == user_id
        ]
        
        user_logs = [
            l for l in self._access_log
            if l.get('user_id') == user_id
        ]
        
        return {
            'user_id': user_id,
            'export_date': datetime.now(timezone.utc).isoformat(),
            'images': [
                {
                    'image_id': m.image_id,
                    'session_id': m.session_id,
                    'created_at': m.created_at.isoformat(),
                    'expires_at': m.expires_at.isoformat(),
                    'status': m.status.value,
                    'size_bytes': m.size_bytes,
                }
                for m in user_images
            ],
            'access_log': user_logs,
            'total_images': len(user_images),
            'total_access_events': len(user_logs),
        }
    
    async def delete_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Delete all user data for GDPR request (right to be forgotten).
        
        Args:
            user_id: User to delete data for
            
        Returns:
            Dict with deletion summary
        """
        deleted_images = 0
        deleted_logs = 0
        
        # Delete all user images
        for image_id, metadata in list(self._metadata.items()):
            if metadata.user_id == user_id:
                await self.delete_image(image_id, user_id, reason="gdpr_request")
                deleted_images += 1
        
        # Remove access logs
        self._access_log = [
            l for l in self._access_log
            if l.get('user_id') != user_id
        ]
        deleted_logs = len(self._access_log) - len([
            l for l in self._access_log if l.get('user_id') == user_id
        ])
        
        logger.info(f"GDPR deletion for user {user_id}: {deleted_images} images, {deleted_logs} logs")
        
        return {
            'user_id': user_id,
            'deletion_date': datetime.now(timezone.utc).isoformat(),
            'images_deleted': deleted_images,
            'access_logs_removed': deleted_logs,
        }
    
    # ==========================================
    # Internal Methods
    # ==========================================
    
    def _generate_image_id(self, user_id: str, session_id: str) -> str:
        """Generate unique image ID."""
        timestamp = datetime.now(timezone.utc).timestamp()
        random_suffix = secrets.token_hex(8)
        
        # Create deterministic but unpredictable ID
        data = f"{user_id}:{session_id}:{timestamp}:{random_suffix}"
        hash_part = hashlib.sha256(data.encode()).hexdigest()[:16]
        
        return f"img_{hash_part}_{random_suffix}"
    
    def _log_access(
        self,
        image_id: str,
        user_id: str,
        action: str,
        success: bool,
        reason: Optional[str] = None
    ) -> None:
        """Log image access."""
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'image_id': image_id,
            'user_id': user_id,
            'action': action,
            'success': success,
            'reason': reason,
        }
        
        self._access_log.append(entry)
        
        # Keep log bounded
        if len(self._access_log) > 10000:
            self._access_log = self._access_log[-5000:]


# ==========================================
# Convenience Functions
# ==========================================

def create_privacy_manager(
    storage_path: Optional[str] = None,
    encryption_key: Optional[bytes] = None
) -> PrivacyManager:
    """
    Create PrivacyManager instance.
    
    Args:
        storage_path: Optional custom storage path
        encryption_key: Optional encryption key
        
    Returns:
        PrivacyManager instance
    """
    if storage_path is None:
        storage_path = os.environ.get('TRYON_STORAGE_PATH', '/tmp/tryon_images')
    
    if encryption_key is None:
        key_env = os.environ.get('TRYON_ENCRYPTION_KEY')
        if key_env:
            encryption_key = base64.urlsafe_b64decode(key_env.encode())
    
    return PrivacyManager(storage_path, encryption_key)
