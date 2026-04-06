"""
CONFIT Backend — Social Post Service
====================================
Service layer for social post management.
"""

import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_

from database.session import get_db
from database.models import (
    SocialPost,
    SocialPostStats,
    SocialLike,
    SocialSave,
    SocialHashtag,
    SocialReport,
    SpamDetectionLog,
    User,
    Outfit,
)

logger = logging.getLogger(__name__)


# ── Spam Detection Constants ─────────────────────────────────────────────────────

SPAM_THRESHOLD_SCORE = 0.85
MAX_POSTS_PER_HOUR = 20
MAX_DUPLICATE_CONTENT = 3
BANNED_WORDS = set()  # Add banned words as needed


class SpamDetectionResult:
    """Result of spam detection analysis."""
    
    def __init__(self, is_spam: bool, confidence: float, method: str, metadata: Dict = None):
        self.is_spam = is_spam
        self.confidence = confidence
        self.method = method
        self.metadata = metadata or {}


class PostService:
    """Service for managing social posts."""
    
    def __init__(self, db: Session):
        self._db = db
    
    # ── Post CRUD ────────────────────────────────────────────────────────────────
    
    def create_post(
        self,
        user_id: str,
        image_urls: List[str],
        caption: str = None,
        outfit_id: str = None,
        hashtags: List[str] = None,
        post_type: str = "outfit",
        visibility: str = "public",
        location: str = None,
        tags: List[str] = None,
    ) -> SocialPost:
        """Create a new social post with spam detection."""
        
        # Spam detection
        spam_result = self._detect_spam(user_id, caption or "", image_urls)
        if spam_result.is_spam:
            logger.warning(f"Spam detected for user {user_id}: {spam_result.method}")
            raise ValueError("Post blocked due to spam detection")
        
        # Create post
        post = SocialPost(
            user_id=user_id,
            outfit_id=outfit_id,
            caption=caption,
            hashtags=hashtags or [],
            image_urls=image_urls,
            post_type=post_type,
            visibility=visibility,
            location=location,
            tags=tags or [],
        )
        self._db.add(post)
        self._db.flush()
        
        # Create stats
        stats = SocialPostStats(post_id=post.id)
        self._db.add(stats)
        
        # Update hashtags
        if hashtags:
            self._update_hashtags(hashtags)
        
        self._db.commit()
        self._db.refresh(post)
        
        return post
    
    def get_post(self, post_id: str, viewer_id: str = None) -> Optional[Dict[str, Any]]:
        """Get a single post with stats and user info."""
        
        post = self._db.query(SocialPost).options(
            joinedload(SocialPost.user)
        ).filter(SocialPost.id == post_id, SocialPost.is_archived == False).first()
        
        if not post:
            return None
        
        # Check visibility
        if not self._can_view_post(post, viewer_id):
            return None
        
        # Get stats
        stats = self._db.query(SocialPostStats).filter(
            SocialPostStats.post_id == post_id
        ).first()
        
        # Check if viewer liked/saved
        is_liked = False
        is_saved = False
        if viewer_id:
            is_liked = self._db.query(SocialLike).filter(
                SocialLike.user_id == viewer_id,
                SocialLike.entity_type == "post",
                SocialLike.entity_id == post_id,
            ).first() is not None
            
            is_saved = self._db.query(SocialSave).filter(
                SocialSave.user_id == viewer_id,
                SocialSave.post_id == post_id,
            ).first() is not None
        
        # Increment view count
        if stats:
            stats.view_count += 1
            self._db.commit()
        
        return self._serialize_post(post, stats, is_liked, is_saved)
    
    def update_post(
        self,
        post_id: str,
        user_id: str,
        caption: str = None,
        hashtags: List[str] = None,
        visibility: str = None,
        location: str = None,
    ) -> Optional[SocialPost]:
        """Update post details."""
        
        post = self._db.query(SocialPost).filter(
            SocialPost.id == post_id,
            SocialPost.user_id == user_id,
        ).first()
        
        if not post:
            return None
        
        if caption is not None:
            post.caption = caption
        if hashtags is not None:
            old_hashtags = set(post.hashtags or [])
            new_hashtags = set(hashtags)
            
            # Decrement old hashtags
            for tag in old_hashtags - new_hashtags:
                self._decrement_hashtag(tag)
            
            # Increment new hashtags
            for tag in new_hashtags - old_hashtags:
                self._increment_hashtag(tag)
            
            post.hashtags = hashtags
        if visibility is not None:
            post.visibility = visibility
        if location is not None:
            post.location = location
        
        self._db.commit()
        self._db.refresh(post)
        return post
    
    def delete_post(self, post_id: str, user_id: str) -> bool:
        """Delete a post (soft delete by archiving)."""
        
        post = self._db.query(SocialPost).filter(
            SocialPost.id == post_id,
            SocialPost.user_id == user_id,
        ).first()
        
        if not post:
            return False
        
        # Decrement hashtag counts
        if post.hashtags:
            for tag in post.hashtags:
                self._decrement_hashtag(tag)
        
        post.is_archived = True
        self._db.commit()
        return True
    
    # ── Post Listing ─────────────────────────────────────────────────────────────
    
    def get_user_posts(
        self,
        user_id: str,
        viewer_id: str = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get posts by a specific user."""
        
        query = self._db.query(SocialPost).options(
            joinedload(SocialPost.user)
        ).filter(
            SocialPost.user_id == user_id,
            SocialPost.is_archived == False,
        ).order_by(SocialPost.created_at.desc())
        
        posts = query.offset(skip).limit(limit).all()
        
        result = []
        for post in posts:
            if self._can_view_post(post, viewer_id):
                stats = self._db.query(SocialPostStats).filter(
                    SocialPostStats.post_id == post.id
                ).first()
                
                is_liked = False
                is_saved = False
                if viewer_id:
                    is_liked = self._db.query(SocialLike).filter(
                        SocialLike.user_id == viewer_id,
                        SocialLike.entity_type == "post",
                        SocialLike.entity_id == post.id,
                    ).first() is not None
                    
                    is_saved = self._db.query(SocialSave).filter(
                        SocialSave.user_id == viewer_id,
                        SocialSave.post_id == post.id,
                    ).first() is not None
                
                result.append(self._serialize_post(post, stats, is_liked, is_saved))
        
        return result
    
    def get_posts_by_hashtag(
        self,
        hashtag: str,
        viewer_id: str = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get posts by hashtag."""
        
        # Normalize hashtag
        tag = hashtag.lower().strip('#')
        
        query = self._db.query(SocialPost).options(
            joinedload(SocialPost.user)
        ).filter(
            SocialPost.hashtags.contains([tag]),
            SocialPost.is_archived == False,
            SocialPost.visibility == "public",
        ).order_by(SocialPost.created_at.desc())
        
        posts = query.offset(skip).limit(limit).all()
        
        return self._serialize_posts_list(posts, viewer_id)
    
    # ── Engagement ───────────────────────────────────────────────────────────────
    
    def like_post(self, post_id: str, user_id: str) -> bool:
        """Like a post."""
        
        # Check if already liked
        existing = self._db.query(SocialLike).filter(
            SocialLike.user_id == user_id,
            SocialLike.entity_type == "post",
            SocialLike.entity_id == post_id,
        ).first()
        
        if existing:
            return False
        
        # Create like
        like = SocialLike(
            user_id=user_id,
            entity_type="post",
            entity_id=post_id,
        )
        self._db.add(like)
        
        # Update stats
        stats = self._db.query(SocialPostStats).filter(
            SocialPostStats.post_id == post_id
        ).first()
        if stats:
            stats.like_count += 1
            stats.last_activity_at = datetime.now(timezone.utc)
            self._update_engagement_rate(stats)
        
        self._db.commit()
        return True
    
    def unlike_post(self, post_id: str, user_id: str) -> bool:
        """Unlike a post."""
        
        like = self._db.query(SocialLike).filter(
            SocialLike.user_id == user_id,
            SocialLike.entity_type == "post",
            SocialLike.entity_id == post_id,
        ).first()
        
        if not like:
            return False
        
        self._db.delete(like)
        
        # Update stats
        stats = self._db.query(SocialPostStats).filter(
            SocialPostStats.post_id == post_id
        ).first()
        if stats and stats.like_count > 0:
            stats.like_count -= 1
            stats.last_activity_at = datetime.now(timezone.utc)
            self._update_engagement_rate(stats)
        
        self._db.commit()
        return True
    
    def save_post(
        self,
        post_id: str,
        user_id: str,
        collection_name: str = None,
    ) -> bool:
        """Save a post to collection."""
        
        # Check if already saved
        existing = self._db.query(SocialSave).filter(
            SocialSave.user_id == user_id,
            SocialSave.post_id == post_id,
        ).first()
        
        if existing:
            return False
        
        # Create save
        save = SocialSave(
            user_id=user_id,
            post_id=post_id,
            collection_name=collection_name,
        )
        self._db.add(save)
        
        # Update stats
        stats = self._db.query(SocialPostStats).filter(
            SocialPostStats.post_id == post_id
        ).first()
        if stats:
            stats.save_count += 1
            stats.last_activity_at = datetime.now(timezone.utc)
            self._update_engagement_rate(stats)
        
        self._db.commit()
        return True
    
    def unsave_post(self, post_id: str, user_id: str) -> bool:
        """Unsave a post."""
        
        save = self._db.query(SocialSave).filter(
            SocialSave.user_id == user_id,
            SocialSave.post_id == post_id,
        ).first()
        
        if not save:
            return False
        
        self._db.delete(save)
        
        # Update stats
        stats = self._db.query(SocialPostStats).filter(
            SocialPostStats.post_id == post_id
        ).first()
        if stats and stats.save_count > 0:
            stats.save_count -= 1
            stats.last_activity_at = datetime.now(timezone.utc)
            self._update_engagement_rate(stats)
        
        self._db.commit()
        return True
    
    def share_post(
        self,
        post_id: str,
        user_id: str,
        platform: str = None,
    ) -> bool:
        """Track post share."""
        
        # Update stats
        stats = self._db.query(SocialPostStats).filter(
            SocialPostStats.post_id == post_id
        ).first()
        if stats:
            stats.share_count += 1
            stats.last_activity_at = datetime.now(timezone.utc)
            self._update_engagement_rate(stats)
        
        self._db.commit()
        return True
    
    # ── Reporting & Moderation ───────────────────────────────────────────────────
    
    def report_post(
        self,
        post_id: str,
        reporter_id: str,
        reason: str,
        description: str = None,
    ) -> SocialReport:
        """Report a post for moderation."""
        
        report = SocialReport(
            reporter_id=reporter_id,
            entity_type="post",
            entity_id=post_id,
            reason=reason,
            description=description,
        )
        self._db.add(report)
        self._db.commit()
        self._db.refresh(report)
        return report
    
    def get_user_saved_posts(
        self,
        user_id: str,
        collection_name: str = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get posts saved by user."""
        
        query = self._db.query(SocialSave).options(
            joinedload(SocialSave.post).joinedload(SocialPost.user)
        ).filter(SocialSave.user_id == user_id)
        
        if collection_name:
            query = query.filter(SocialSave.collection_name == collection_name)
        
        saves = query.order_by(SocialSave.created_at.desc()).offset(skip).limit(limit).all()
        
        result = []
        for save in saves:
            if save.post and not save.post.is_archived:
                stats = self._db.query(SocialPostStats).filter(
                    SocialPostStats.post_id == save.post.id
                ).first()
                
                is_liked = self._db.query(SocialLike).filter(
                    SocialLike.user_id == user_id,
                    SocialLike.entity_type == "post",
                    SocialLike.entity_id == save.post.id,
                ).first() is not None
                
                result.append(self._serialize_post(save.post, stats, is_liked, True))
        
        return result
    
    # ── Spam Detection ───────────────────────────────────────────────────────────
    
    def _detect_spam(
        self,
        user_id: str,
        content: str,
        image_urls: List[str],
    ) -> SpamDetectionResult:
        """Detect if content is spam."""
        
        # Rate limit check
        hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_posts = self._db.query(SocialPost).filter(
            SocialPost.user_id == user_id,
            SocialPost.created_at >= hour_ago,
        ).count()
        
        if recent_posts >= MAX_POSTS_PER_HOUR:
            return SpamDetectionResult(
                is_spam=True,
                confidence=1.0,
                method="rate_limit",
                metadata={"posts_last_hour": recent_posts},
            )
        
        # Duplicate content check
        content_hash = hashlib.md5(content.encode()).hexdigest()
        duplicate_count = self._db.query(SpamDetectionLog).filter(
            SpamDetectionLog.content_hash == content_hash,
            SpamDetectionLog.created_at >= datetime.now(timezone.utc) - timedelta(days=1),
        ).count()
        
        if duplicate_count >= MAX_DUPLICATE_CONTENT:
            return SpamDetectionResult(
                is_spam=True,
                confidence=0.9,
                method="duplicate_content",
                metadata={"duplicate_count": duplicate_count},
            )
        
        # Banned words check
        content_lower = content.lower()
        found_banned = [word for word in BANNED_WORDS if word in content_lower]
        if found_banned:
            return SpamDetectionResult(
                is_spam=True,
                confidence=0.95,
                method="banned_words",
                metadata={"found_words": found_banned},
            )
        
        # Log the check
        log = SpamDetectionLog(
            user_id=user_id,
            action_type="post_create",
            content_hash=content_hash,
            is_spam=False,
            confidence=0.0,
            detection_method="passed",
        )
        self._db.add(log)
        
        return SpamDetectionResult(
            is_spam=False,
            confidence=0.0,
            method="passed",
        )
    
    # ── Helper Methods ───────────────────────────────────────────────────────────
    
    def _can_view_post(self, post: SocialPost, viewer_id: str) -> bool:
        """Check if viewer can see the post."""
        
        if post.visibility == "public":
            return True
        
        if not viewer_id:
            return False
        
        if post.user_id == viewer_id:
            return True
        
        if post.visibility == "followers":
            from database.models import SocialFollow
            follow = self._db.query(SocialFollow).filter(
                SocialFollow.follower_id == viewer_id,
                SocialFollow.following_id == post.user_id,
                SocialFollow.status == "active",
            ).first()
            return follow is not None
        
        return False
    
    def _update_hashtags(self, hashtags: List[str]) -> None:
        """Update hashtag counts."""
        for tag in hashtags:
            tag_lower = tag.lower().strip('#')
            hashtag_obj = self._db.query(SocialHashtag).filter(
                SocialHashtag.tag == tag_lower
            ).first()
            
            if hashtag_obj:
                hashtag_obj.post_count += 1
                hashtag_obj.last_used_at = datetime.now(timezone.utc)
            else:
                hashtag_obj = SocialHashtag(
                    tag=tag_lower,
                    post_count=1,
                    last_used_at=datetime.now(timezone.utc),
                )
                self._db.add(hashtag_obj)
    
    def _increment_hashtag(self, tag: str) -> None:
        """Increment hashtag count."""
        tag_lower = tag.lower().strip('#')
        hashtag_obj = self._db.query(SocialHashtag).filter(
            SocialHashtag.tag == tag_lower
        ).first()
        
        if hashtag_obj:
            hashtag_obj.post_count += 1
            hashtag_obj.last_used_at = datetime.now(timezone.utc)
        else:
            hashtag_obj = SocialHashtag(
                tag=tag_lower,
                post_count=1,
                last_used_at=datetime.now(timezone.utc),
            )
            self._db.add(hashtag_obj)
    
    def _decrement_hashtag(self, tag: str) -> None:
        """Decrement hashtag count."""
        tag_lower = tag.lower().strip('#')
        hashtag_obj = self._db.query(SocialHashtag).filter(
            SocialHashtag.tag == tag_lower
        ).first()
        
        if hashtag_obj and hashtag_obj.post_count > 0:
            hashtag_obj.post_count -= 1
    
    def _update_engagement_rate(self, stats: SocialPostStats) -> None:
        """Calculate and update engagement rate."""
        if stats.view_count > 0:
            engagement = (
                (stats.like_count + stats.comment_count * 2 + stats.share_count * 3 + stats.save_count * 2)
                / stats.view_count
            ) * 100
            stats.engagement_rate = min(engagement, 100.0)
    
    def _serialize_post(
        self,
        post: SocialPost,
        stats: SocialPostStats,
        is_liked: bool,
        is_saved: bool,
    ) -> Dict[str, Any]:
        """Serialize post for API response."""
        
        return {
            "id": str(post.id),
            "user": {
                "id": str(post.user.id),
                "name": post.user.name,
                "avatar_url": post.user.avatar_url,
            },
            "outfit_id": post.outfit_id,
            "caption": post.caption,
            "hashtags": post.hashtags or [],
            "image_urls": post.image_urls or [],
            "video_url": post.video_url,
            "post_type": post.post_type,
            "visibility": post.visibility,
            "location": post.location,
            "tags": post.tags or [],
            "is_featured": post.is_featured,
            "created_at": post.created_at.isoformat(),
            "stats": {
                "like_count": stats.like_count if stats else 0,
                "comment_count": stats.comment_count if stats else 0,
                "share_count": stats.share_count if stats else 0,
                "save_count": stats.save_count if stats else 0,
                "view_count": stats.view_count if stats else 0,
                "engagement_rate": stats.engagement_rate if stats else 0.0,
                "trending_score": stats.trending_score if stats else 0.0,
            } if stats else None,
            "is_liked": is_liked,
            "is_saved": is_saved,
        }
    
    def _serialize_posts_list(
        self,
        posts: List[SocialPost],
        viewer_id: str = None,
    ) -> List[Dict[str, Any]]:
        """Serialize list of posts."""
        
        result = []
        for post in posts:
            stats = self._db.query(SocialPostStats).filter(
                SocialPostStats.post_id == post.id
            ).first()
            
            is_liked = False
            is_saved = False
            if viewer_id:
                is_liked = self._db.query(SocialLike).filter(
                    SocialLike.user_id == viewer_id,
                    SocialLike.entity_type == "post",
                    SocialLike.entity_id == post.id,
                ).first() is not None
                
                is_saved = self._db.query(SocialSave).filter(
                    SocialSave.user_id == viewer_id,
                    SocialSave.post_id == post.id,
                ).first() is not None
            
            result.append(self._serialize_post(post, stats, is_liked, is_saved))
        
        return result


def get_post_service(db: Session = Depends(get_db)) -> PostService:
    """Factory function for PostService dependency injection."""
    return PostService(db)
