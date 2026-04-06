"""
CONFIT Backend — Social Follow Service
=====================================
Service layer for user follow relationships.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_

from database.session import get_db
from database.models import (
    SocialFollow,
    User,
)

logger = logging.getLogger(__name__)


class FollowService:
    """Service for managing follow relationships."""
    
    def __init__(self, db: Session):
        self._db = db
    
    # ── Follow Actions ───────────────────────────────────────────────────────────
    
    def follow_user(
        self,
        follower_id: str,
        following_id: str,
    ) -> Dict[str, Any]:
        """Follow a user."""
        
        # Cannot follow yourself
        if follower_id == following_id:
            raise ValueError("Cannot follow yourself")
        
        # Check if already following
        existing = self._db.query(SocialFollow).filter(
            SocialFollow.follower_id == follower_id,
            SocialFollow.following_id == following_id,
        ).first()
        
        if existing:
            if existing.status == "active":
                raise ValueError("Already following this user")
            elif existing.status == "blocked":
                raise ValueError("Cannot follow this user")
            elif existing.status == "pending":
                return {"status": "pending", "message": "Follow request already pending"}
        
        # Check if target user exists
        target_user = self._db.query(User).filter(User.id == following_id).first()
        if not target_user:
            raise ValueError("User not found")
        
        # Create follow relationship
        # In a real app, you might have private accounts that require approval
        status = "active"
        
        follow = SocialFollow(
            follower_id=follower_id,
            following_id=following_id,
            status=status,
        )
        self._db.add(follow)
        self._db.commit()
        self._db.refresh(follow)
        
        return {
            "status": status,
            "following": self._serialize_user(target_user),
        }
    
    def unfollow_user(
        self,
        follower_id: str,
        following_id: str,
    ) -> bool:
        """Unfollow a user."""
        
        follow = self._db.query(SocialFollow).filter(
            SocialFollow.follower_id == follower_id,
            SocialFollow.following_id == following_id,
            SocialFollow.status == "active",
        ).first()
        
        if not follow:
            return False
        
        self._db.delete(follow)
        self._db.commit()
        return True
    
    def block_user(
        self,
        blocker_id: str,
        blocked_id: str,
    ) -> bool:
        """Block a user."""
        
        # Cannot block yourself
        if blocker_id == blocked_id:
            raise ValueError("Cannot block yourself")
        
        # Check for existing relationship
        existing = self._db.query(SocialFollow).filter(
            SocialFollow.follower_id == blocker_id,
            SocialFollow.following_id == blocked_id,
        ).first()
        
        if existing:
            existing.status = "blocked"
        else:
            # Create blocked relationship
            block = SocialFollow(
                follower_id=blocker_id,
                following_id=blocked_id,
                status="blocked",
            )
            self._db.add(block)
        
        # Remove any follow from blocked user to blocker
        reverse_follow = self._db.query(SocialFollow).filter(
            SocialFollow.follower_id == blocked_id,
            SocialFollow.following_id == blocker_id,
        ).first()
        
        if reverse_follow:
            self._db.delete(reverse_follow)
        
        self._db.commit()
        return True
    
    def unblock_user(
        self,
        blocker_id: str,
        blocked_id: str,
    ) -> bool:
        """Unblock a user."""
        
        block = self._db.query(SocialFollow).filter(
            SocialFollow.follower_id == blocker_id,
            SocialFollow.following_id == blocked_id,
            SocialFollow.status == "blocked",
        ).first()
        
        if not block:
            return False
        
        self._db.delete(block)
        self._db.commit()
        return True
    
    # ── Follow Status ────────────────────────────────────────────────────────────
    
    def get_follow_status(
        self,
        user_id: str,
        target_id: str,
    ) -> Dict[str, Any]:
        """Get follow status between two users."""
        
        is_following = self._db.query(SocialFollow).filter(
            SocialFollow.follower_id == user_id,
            SocialFollow.following_id == target_id,
            SocialFollow.status == "active",
        ).first() is not None
        
        is_followed_by = self._db.query(SocialFollow).filter(
            SocialFollow.follower_id == target_id,
            SocialFollow.following_id == user_id,
            SocialFollow.status == "active",
        ).first() is not None
        
        is_blocked = self._db.query(SocialFollow).filter(
            SocialFollow.follower_id == user_id,
            SocialFollow.following_id == target_id,
            SocialFollow.status == "blocked",
        ).first() is not None
        
        is_blocked_by = self._db.query(SocialFollow).filter(
            SocialFollow.follower_id == target_id,
            SocialFollow.following_id == user_id,
            SocialFollow.status == "blocked",
        ).first() is not None
        
        return {
            "is_following": is_following,
            "is_followed_by": is_followed_by,
            "is_mutual": is_following and is_followed_by,
            "is_blocked": is_blocked,
            "is_blocked_by": is_blocked_by,
        }
    
    # ── Followers/Following Lists ────────────────────────────────────────────────
    
    def get_followers(
        self,
        user_id: str,
        viewer_id: str = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get list of followers."""
        
        followers = self._db.query(SocialFollow).options(
            joinedload(SocialFollow.follower)
        ).filter(
            SocialFollow.following_id == user_id,
            SocialFollow.status == "active",
        ).order_by(SocialFollow.created_at.desc()).offset(skip).limit(limit).all()
        
        result = []
        for follow in followers:
            user_data = self._serialize_user(follow.follower)
            if viewer_id:
                user_data["follow_status"] = self.get_follow_status(viewer_id, str(follow.follower.id))
            result.append(user_data)
        
        return result
    
    def get_following(
        self,
        user_id: str,
        viewer_id: str = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get list of users being followed."""
        
        following = self._db.query(SocialFollow).options(
            joinedload(SocialFollow.following)
        ).filter(
            SocialFollow.follower_id == user_id,
            SocialFollow.status == "active",
        ).order_by(SocialFollow.created_at.desc()).offset(skip).limit(limit).all()
        
        result = []
        for follow in following:
            user_data = self._serialize_user(follow.following)
            if viewer_id:
                user_data["follow_status"] = self.get_follow_status(viewer_id, str(follow.following.id))
            result.append(user_data)
        
        return result
    
    # ── Counts ───────────────────────────────────────────────────────────────────
    
    def get_follower_count(self, user_id: str) -> int:
        """Get number of followers."""
        return self._db.query(SocialFollow).filter(
            SocialFollow.following_id == user_id,
            SocialFollow.status == "active",
        ).count()
    
    def get_following_count(self, user_id: str) -> int:
        """Get number of users being followed."""
        return self._db.query(SocialFollow).filter(
            SocialFollow.follower_id == user_id,
            SocialFollow.status == "active",
        ).count()
    
    def get_user_stats(self, user_id: str) -> Dict[str, int]:
        """Get follow stats for a user."""
        return {
            "followers_count": self.get_follower_count(user_id),
            "following_count": self.get_following_count(user_id),
        }
    
    # ── Popular Stylists ─────────────────────────────────────────────────────────
    
    def get_popular_stylists(
        self,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get popular stylists ranked by follower count."""
        
        # Query users with their follower counts
        popular = self._db.query(
            User,
            func.count(SocialFollow.id).label("follower_count")
        ).join(
            SocialFollow,
            SocialFollow.following_id == User.id,
        ).filter(
            SocialFollow.status == "active",
        ).group_by(User.id).order_by(
            func.count(SocialFollow.id).desc()
        ).offset(skip).limit(limit).all()
        
        result = []
        for user, follower_count in popular:
            user_data = self._serialize_user(user)
            user_data["followers_count"] = follower_count
            user_data["following_count"] = self.get_following_count(str(user.id))
            result.append(user_data)
        
        return result
    
    def get_suggested_users(
        self,
        user_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get suggested users to follow based on mutual connections."""
        
        # Get users followed by people the current user follows
        following_ids = self._db.query(SocialFollow.following_id).filter(
            SocialFollow.follower_id == user_id,
            SocialFollow.status == "active",
        ).all()
        following_ids = [f[0] for f in following_ids]
        
        if not following_ids:
            # If not following anyone, return popular users
            return self.get_popular_stylists(0, limit)
        
        # Find users followed by the same people (excluding already followed)
        suggested = self._db.query(
            User,
            func.count(SocialFollow.id).label("mutual_count")
        ).join(
            SocialFollow,
            SocialFollow.following_id == User.id,
        ).filter(
            SocialFollow.follower_id.in_(following_ids),
            SocialFollow.status == "active",
            User.id != user_id,
            ~User.id.in_(following_ids),  # Exclude already followed
        ).group_by(User.id).order_by(
            func.count(SocialFollow.id).desc()
        ).limit(limit).all()
        
        result = []
        for user, mutual_count in suggested:
            user_data = self._serialize_user(user)
            user_data["mutual_connections"] = mutual_count
            user_data["followers_count"] = self.get_follower_count(str(user.id))
            result.append(user_data)
        
        return result
    
    # ── Helper Methods ───────────────────────────────────────────────────────────
    
    def _serialize_user(self, user: User) -> Dict[str, Any]:
        """Serialize user for API response."""
        return {
            "id": str(user.id),
            "name": user.name,
            "avatar_url": user.avatar_url,
            "style_preference": user.style_preference,
        }


def get_follow_service(db: Session = Depends(get_db)) -> FollowService:
    """Factory function for FollowService dependency injection."""
    return FollowService(db)
