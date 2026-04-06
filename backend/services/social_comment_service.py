"""
CONFIT Backend — Social Comment Service
=======================================
Service layer for social comment management.
"""

import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from database.session import get_db
from database.models import (
    SocialComment,
    SocialLike,
    SocialPost,
    SocialPostStats,
    SpamDetectionLog,
    User,
)

logger = logging.getLogger(__name__)


# ── Rate Limits ─────────────────────────────────────────────────────────────────

MAX_COMMENTS_PER_HOUR = 50
MAX_COMMENT_LENGTH = 1000


class CommentService:
    """Service for managing social comments."""
    
    def __init__(self, db: Session):
        self._db = db
    
    # ── Comment CRUD ─────────────────────────────────────────────────────────────
    
    def create_comment(
        self,
        post_id: str,
        user_id: str,
        content: str,
        parent_id: str = None,
        mentions: List[str] = None,
    ) -> SocialComment:
        """Create a new comment with spam detection."""
        
        # Validate content length
        if len(content) > MAX_COMMENT_LENGTH:
            raise ValueError(f"Comment exceeds maximum length of {MAX_COMMENT_LENGTH}")
        
        # Check if post exists
        post = self._db.query(SocialPost).filter(SocialPost.id == post_id).first()
        if not post:
            raise ValueError("Post not found")
        
        # Spam detection
        spam_result = self._detect_spam(user_id, content)
        if spam_result.is_spam:
            logger.warning(f"Spam comment detected for user {user_id}")
            raise ValueError("Comment blocked due to spam detection")
        
        # Create comment
        comment = SocialComment(
            post_id=post_id,
            user_id=user_id,
            parent_id=parent_id,
            content=content,
            mentions=mentions or [],
        )
        self._db.add(comment)
        
        # Update post stats
        stats = self._db.query(SocialPostStats).filter(
            SocialPostStats.post_id == post_id
        ).first()
        if stats:
            stats.comment_count += 1
            stats.last_activity_at = datetime.now(timezone.utc)
        
        self._db.commit()
        self._db.refresh(comment)
        
        return comment
    
    def get_comment(self, comment_id: str) -> Optional[Dict[str, Any]]:
        """Get a single comment."""
        
        comment = self._db.query(SocialComment).options(
            joinedload(SocialComment.user)
        ).filter(SocialComment.id == comment_id).first()
        
        if not comment:
            return None
        
        return self._serialize_comment(comment)
    
    def update_comment(
        self,
        comment_id: str,
        user_id: str,
        content: str,
    ) -> Optional[SocialComment]:
        """Update comment content."""
        
        comment = self._db.query(SocialComment).filter(
            SocialComment.id == comment_id,
            SocialComment.user_id == user_id,
        ).first()
        
        if not comment:
            return None
        
        if len(content) > MAX_COMMENT_LENGTH:
            raise ValueError(f"Comment exceeds maximum length of {MAX_COMMENT_LENGTH}")
        
        comment.content = content
        comment.is_edited = True
        comment.updated_at = datetime.now(timezone.utc)
        
        self._db.commit()
        self._db.refresh(comment)
        return comment
    
    def delete_comment(self, comment_id: str, user_id: str) -> bool:
        """Delete a comment."""
        
        comment = self._db.query(SocialComment).filter(
            SocialComment.id == comment_id,
            SocialComment.user_id == user_id,
        ).first()
        
        if not comment:
            return False
        
        # Update post stats
        stats = self._db.query(SocialPostStats).filter(
            SocialPostStats.post_id == comment.post_id
        ).first()
        if stats and stats.comment_count > 0:
            stats.comment_count -= 1
            stats.last_activity_at = datetime.now(timezone.utc)
        
        self._db.delete(comment)
        self._db.commit()
        return True
    
    def hide_comment(self, comment_id: str, moderator_id: str) -> bool:
        """Hide a comment (moderation)."""
        
        comment = self._db.query(SocialComment).filter(
            SocialComment.id == comment_id
        ).first()
        
        if not comment:
            return False
        
        comment.is_hidden = True
        
        # Update post stats
        stats = self._db.query(SocialPostStats).filter(
            SocialPostStats.post_id == comment.post_id
        ).first()
        if stats and stats.comment_count > 0:
            stats.comment_count -= 1
        
        self._db.commit()
        return True
    
    # ── Comment Listing ──────────────────────────────────────────────────────────
    
    def get_post_comments(
        self,
        post_id: str,
        viewer_id: str = None,
        skip: int = 0,
        limit: int = 20,
        sort: str = "newest",
    ) -> List[Dict[str, Any]]:
        """Get comments for a post with pagination."""
        
        query = self._db.query(SocialComment).options(
            joinedload(SocialComment.user)
        ).filter(
            SocialComment.post_id == post_id,
            SocialComment.is_hidden == False,
            SocialComment.parent_id == None,  # Only top-level comments
        )
        
        # Sorting
        if sort == "newest":
            query = query.order_by(SocialComment.created_at.desc())
        elif sort == "oldest":
            query = query.order_by(SocialComment.created_at.asc())
        elif sort == "top":
            query = query.order_by(SocialComment.like_count.desc())
        
        comments = query.offset(skip).limit(limit).all()
        
        return [self._serialize_comment(c, viewer_id) for c in comments]
    
    def get_comment_replies(
        self,
        parent_id: str,
        viewer_id: str = None,
        skip: int = 0,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get replies to a comment."""
        
        replies = self._db.query(SocialComment).options(
            joinedload(SocialComment.user)
        ).filter(
            SocialComment.parent_id == parent_id,
            SocialComment.is_hidden == False,
        ).order_by(SocialComment.created_at.asc()).offset(skip).limit(limit).all()
        
        return [self._serialize_comment(r, viewer_id) for r in replies]
    
    def get_user_comments(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get comments by a user."""
        
        comments = self._db.query(SocialComment).options(
            joinedload(SocialComment.user),
            joinedload(SocialComment.post),
        ).filter(
            SocialComment.user_id == user_id,
            SocialComment.is_hidden == False,
        ).order_by(SocialComment.created_at.desc()).offset(skip).limit(limit).all()
        
        return [self._serialize_comment(c) for c in comments]
    
    # ── Engagement ───────────────────────────────────────────────────────────────
    
    def like_comment(self, comment_id: str, user_id: str) -> bool:
        """Like a comment."""
        
        # Check if already liked
        existing = self._db.query(SocialLike).filter(
            SocialLike.user_id == user_id,
            SocialLike.entity_type == "comment",
            SocialLike.entity_id == comment_id,
        ).first()
        
        if existing:
            return False
        
        # Create like
        like = SocialLike(
            user_id=user_id,
            entity_type="comment",
            entity_id=comment_id,
        )
        self._db.add(like)
        
        # Update comment like count
        comment = self._db.query(SocialComment).filter(
            SocialComment.id == comment_id
        ).first()
        if comment:
            comment.like_count += 1
        
        self._db.commit()
        return True
    
    def unlike_comment(self, comment_id: str, user_id: str) -> bool:
        """Unlike a comment."""
        
        like = self._db.query(SocialLike).filter(
            SocialLike.user_id == user_id,
            SocialLike.entity_type == "comment",
            SocialLike.entity_id == comment_id,
        ).first()
        
        if not like:
            return False
        
        self._db.delete(like)
        
        # Update comment like count
        comment = self._db.query(SocialComment).filter(
            SocialComment.id == comment_id
        ).first()
        if comment and comment.like_count > 0:
            comment.like_count -= 1
        
        self._db.commit()
        return True
    
    # ── Helper Methods ───────────────────────────────────────────────────────────
    
    def _detect_spam(self, user_id: str, content: str) -> Dict[str, Any]:
        """Detect if comment is spam."""
        
        # Rate limit check
        hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_comments = self._db.query(SocialComment).filter(
            SocialComment.user_id == user_id,
            SocialComment.created_at >= hour_ago,
        ).count()
        
        if recent_comments >= MAX_COMMENTS_PER_HOUR:
            return {
                "is_spam": True,
                "confidence": 1.0,
                "method": "rate_limit",
            }
        
        # Duplicate content check
        content_hash = hashlib.md5(content.encode()).hexdigest()
        duplicate_count = self._db.query(SpamDetectionLog).filter(
            SpamDetectionLog.content_hash == content_hash,
            SpamDetectionLog.created_at >= datetime.now(timezone.utc) - timedelta(hours=1),
        ).count()
        
        if duplicate_count >= 3:
            return {
                "is_spam": True,
                "confidence": 0.9,
                "method": "duplicate_content",
            }
        
        # Log the check
        log = SpamDetectionLog(
            user_id=user_id,
            action_type="comment_create",
            content_hash=content_hash,
            is_spam=False,
            confidence=0.0,
            detection_method="passed",
        )
        self._db.add(log)
        
        return {
            "is_spam": False,
            "confidence": 0.0,
            "method": "passed",
        }
    
    def _serialize_comment(
        self,
        comment: SocialComment,
        viewer_id: str = None,
    ) -> Dict[str, Any]:
        """Serialize comment for API response."""
        
        is_liked = False
        if viewer_id:
            is_liked = self._db.query(SocialLike).filter(
                SocialLike.user_id == viewer_id,
                SocialLike.entity_type == "comment",
                SocialLike.entity_id == comment.id,
            ).first() is not None
        
        return {
            "id": str(comment.id),
            "user": {
                "id": str(comment.user.id),
                "name": comment.user.name,
                "avatar_url": comment.user.avatar_url,
            },
            "post_id": str(comment.post_id),
            "parent_id": str(comment.parent_id) if comment.parent_id else None,
            "content": comment.content,
            "mentions": comment.mentions or [],
            "is_edited": comment.is_edited,
            "like_count": comment.like_count,
            "is_liked": is_liked,
            "reply_count": self._db.query(SocialComment).filter(
                SocialComment.parent_id == comment.id
            ).count() if not comment.parent_id else 0,
            "created_at": comment.created_at.isoformat(),
            "updated_at": comment.updated_at.isoformat() if comment.is_edited else None,
        }


def get_comment_service(db: Session = Depends(get_db)) -> CommentService:
    """Factory function for CommentService dependency injection."""
    return CommentService(db)
