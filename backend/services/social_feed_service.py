"""
CONFIT Backend — Social Feed Service
====================================
Service layer for personalized feed generation with ranking algorithm.
"""

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from fastapi import Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_, or_

from database.session import get_db
from database.models import (
    SocialPost,
    SocialPostStats,
    SocialFollow,
    SocialFeedCache,
    SocialHashtag,
    SocialStory,
    SocialStoryView,
    User,
    UserStyleProfile,
)

logger = logging.getLogger(__name__)


class FeedType(str, Enum):
    HOME = "home"
    DISCOVER = "discover"
    FOLLOWING = "following"
    TRENDING = "trending"


# ── Ranking Weights ─────────────────────────────────────────────────────────────

RANKING_WEIGHTS = {
    "recency": 0.15,
    "engagement": 0.25,
    "relevance": 0.20,
    "social": 0.25,
    "quality": 0.15,
}

ENGAGEMENT_WEIGHTS = {
    "like": 1.0,
    "comment": 2.0,
    "share": 3.0,
    "save": 2.5,
    "view": 0.1,
}

# Time decay constants
RECENCY_HALF_LIFE_HOURS = 24  # Score halves every 24 hours
TRENDING_WINDOW_HOURS = 48


class FeedService:
    """Service for generating personalized social feeds."""
    
    def __init__(self, db: Session):
        self._db = db
    
    # ── Main Feed Endpoints ──────────────────────────────────────────────────────
    
    def get_home_feed(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Get personalized home feed combining:
        - Posts from followed users
        - Recommended trending posts
        - Style-relevant content
        """
        
        # Try cache first
        if use_cache:
            cached = self._get_cached_feed(user_id, FeedType.HOME, skip, limit)
            if cached:
                return {
                    "posts": cached,
                    "has_more": len(cached) == limit,
                    "feed_type": FeedType.HOME,
                }
        
        # Get following IDs
        following_ids = self._get_following_ids(user_id)
        
        # Build feed with ranking
        posts = []
        
        # 1. Posts from followed users (higher priority)
        if following_ids:
            following_posts = self._get_posts_from_users(
                user_ids=following_ids,
                viewer_id=user_id,
                limit=min(limit, 15),
            )
            posts.extend(following_posts)
        
        # 2. Trending posts (fill remaining)
        remaining = limit - len(posts)
        if remaining > 0:
            trending = self._get_trending_posts(
                viewer_id=user_id,
                exclude_post_ids=[p["id"] for p in posts],
                limit=remaining,
            )
            posts.extend(trending)
        
        # 3. Apply final ranking
        ranked_posts = self._rank_posts(posts, user_id)
        
        # 4. Paginate
        paginated = ranked_posts[skip:skip + limit]
        
        # Cache the results
        if use_cache and skip == 0:
            self._cache_feed(user_id, FeedType.HOME, paginated)
        
        return {
            "posts": paginated,
            "has_more": len(ranked_posts) > skip + limit,
            "feed_type": FeedType.HOME,
        }
    
    def get_discover_feed(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Get discover feed with:
        - Trending outfits
        - Popular stylists
        - New styles matching preferences
        """
        
        # Get user style profile for personalization
        style_profile = self._get_style_profile(user_id)
        
        posts = []
        
        # 1. Trending posts
        trending = self._get_trending_posts(
            viewer_id=user_id,
            limit=min(limit, 10),
        )
        posts.extend(trending)
        
        # 2. Style-relevant posts
        remaining = limit - len(posts)
        if remaining > 0 and style_profile:
            style_posts = self._get_style_relevant_posts(
                style_profile=style_profile,
                viewer_id=user_id,
                exclude_post_ids=[p["id"] for p in posts],
                limit=remaining,
            )
            posts.extend(style_posts)
        
        # 3. Featured posts
        remaining = limit - len(posts)
        if remaining > 0:
            featured = self._get_featured_posts(
                viewer_id=user_id,
                exclude_post_ids=[p["id"] for p in posts],
                limit=remaining,
            )
            posts.extend(featured)
        
        # Apply ranking
        ranked_posts = self._rank_posts(posts, user_id, prioritize_discover=True)
        
        paginated = ranked_posts[skip:skip + limit]
        
        return {
            "posts": paginated,
            "has_more": len(ranked_posts) > skip + limit,
            "feed_type": FeedType.DISCOVER,
        }
    
    def get_following_feed(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Get feed of only followed users' posts."""
        
        following_ids = self._get_following_ids(user_id)
        
        if not following_ids:
            return {
                "posts": [],
                "has_more": False,
                "feed_type": FeedType.FOLLOWING,
            }
        
        posts = self._get_posts_from_users(
            user_ids=following_ids,
            viewer_id=user_id,
            skip=skip,
            limit=limit,
        )
        
        # Sort by recency for following feed
        posts.sort(key=lambda p: p["created_at"], reverse=True)
        
        return {
            "posts": posts,
            "has_more": len(posts) == limit,
            "feed_type": FeedType.FOLLOWING,
        }
    
    def get_trending_feed(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        timeframe: str = "day",
    ) -> Dict[str, Any]:
        """Get trending posts based on engagement velocity."""
        
        posts = self._get_trending_posts(
            viewer_id=user_id,
            timeframe=timeframe,
            skip=skip,
            limit=limit,
        )
        
        return {
            "posts": posts,
            "has_more": len(posts) == limit,
            "feed_type": FeedType.TRENDING,
            "timeframe": timeframe,
        }
    
    # ── Stories ──────────────────────────────────────────────────────────────────
    
    def get_stories(
        self,
        user_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get active stories from followed users."""
        
        following_ids = self._get_following_ids(user_id)
        
        if not following_ids:
            # Return featured/public stories
            return self._get_public_stories(user_id, limit)
        
        stories = self._db.query(SocialStory).options(
            joinedload(SocialStory.user)
        ).filter(
            SocialStory.user_id.in_(following_ids),
            SocialStory.expires_at > datetime.now(timezone.utc),
        ).order_by(SocialStory.created_at.desc()).limit(limit * 3).all()
        
        # Group by user
        user_stories = {}
        for story in stories:
            uid = str(story.user_id)
            if uid not in user_stories:
                user_stories[uid] = {
                    "user": {
                        "id": uid,
                        "name": story.user.name,
                        "avatar_url": story.user.avatar_url,
                    },
                    "stories": [],
                    "has_unseen": False,
                }
            
            # Check if viewed
            is_viewed = self._db.query(SocialStoryView).filter(
                SocialStoryView.story_id == story.id,
                SocialStoryView.user_id == user_id,
            ).first() is not None
            
            if not is_viewed:
                user_stories[uid]["has_unseen"] = True
            
            user_stories[uid]["stories"].append({
                "id": str(story.id),
                "media_url": story.media_url,
                "media_type": story.media_type,
                "caption": story.caption,
                "view_count": story.view_count,
                "is_viewed": is_viewed,
                "created_at": story.created_at.isoformat(),
                "expires_at": story.expires_at.isoformat(),
            })
        
        # Sort by has_unseen first, then by most recent story
        result = sorted(
            user_stories.values(),
            key=lambda x: (not x["has_unseen"], x["stories"][0]["created_at"] if x["stories"] else ""),
            reverse=True,
        )
        
        return result[:limit]
    
    def mark_story_viewed(self, story_id: str, user_id: str) -> bool:
        """Mark a story as viewed."""
        
        # Check if already viewed
        existing = self._db.query(SocialStoryView).filter(
            SocialStoryView.story_id == story_id,
            SocialStoryView.user_id == user_id,
        ).first()
        
        if existing:
            return True
        
        # Create view record
        view = SocialStoryView(
            story_id=story_id,
            user_id=user_id,
        )
        self._db.add(view)
        
        # Update view count
        story = self._db.query(SocialStory).filter(SocialStory.id == story_id).first()
        if story:
            story.view_count += 1
        
        self._db.commit()
        return True
    
    # ── Trending Hashtags ────────────────────────────────────────────────────────
    
    def get_trending_hashtags(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending hashtags."""
        
        hashtags = self._db.query(SocialHashtag).filter(
            SocialHashtag.is_trending == True,
            SocialHashtag.post_count > 0,
        ).order_by(desc(SocialHashtag.trending_score)).limit(limit).all()
        
        return [
            {
                "tag": h.tag,
                "post_count": h.post_count,
                "trending_score": h.trending_score,
            }
            for h in hashtags
        ]
    
    # ── Ranking Algorithm ────────────────────────────────────────────────────────
    
    def _rank_posts(
        self,
        posts: List[Dict[str, Any]],
        user_id: str,
        prioritize_discover: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Rank posts using multi-factor scoring:
        - Recency: Time decay function
        - Engagement: Likes, comments, shares, saves
        - Relevance: Style match, hashtags
        - Social: From followed users, mutual connections
        - Quality: Image quality, caption length
        """
        
        scored_posts = []
        
        for post in posts:
            score = self._calculate_post_score(post, user_id, prioritize_discover)
            post["_score"] = score
            scored_posts.append(post)
        
        # Sort by score descending
        scored_posts.sort(key=lambda p: p["_score"], reverse=True)
        
        return scored_posts
    
    def _calculate_post_score(
        self,
        post: Dict[str, Any],
        user_id: str,
        prioritize_discover: bool = False,
    ) -> float:
        """Calculate overall score for a post."""
        
        # Recency score (time decay)
        recency_score = self._calculate_recency_score(post["created_at"])
        
        # Engagement score
        stats = post.get("stats", {}) or {}
        engagement_score = self._calculate_engagement_score(stats)
        
        # Relevance score (style match)
        relevance_score = self._calculate_relevance_score(post, user_id)
        
        # Social score (relationship)
        social_score = self._calculate_social_score(post, user_id)
        
        # Quality score
        quality_score = self._calculate_quality_score(post)
        
        # Weighted sum
        weights = RANKING_WEIGHTS.copy()
        if prioritize_discover:
            weights["relevance"] = 0.30
            weights["social"] = 0.15
        
        total_score = (
            recency_score * weights["recency"] +
            engagement_score * weights["engagement"] +
            relevance_score * weights["relevance"] +
            social_score * weights["social"] +
            quality_score * weights["quality"]
        )
        
        return total_score
    
    def _calculate_recency_score(self, created_at: str) -> float:
        """Calculate recency score with exponential decay."""
        
        try:
            post_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except:
            return 0.0
        
        age_hours = (datetime.now(timezone.utc) - post_time).total_seconds() / 3600
        
        # Exponential decay: score = e^(-ln(2) * age / half_life)
        decay_factor = math.log(2) * age_hours / RECENCY_HALF_LIFE_HOURS
        score = math.exp(-decay_factor)
        
        return max(0.0, min(1.0, score))
    
    def _calculate_engagement_score(self, stats: Dict[str, Any]) -> float:
        """Calculate engagement score normalized by views."""
        
        if not stats:
            return 0.0
        
        view_count = max(stats.get("view_count", 1), 1)
        
        weighted_engagement = (
            stats.get("like_count", 0) * ENGAGEMENT_WEIGHTS["like"] +
            stats.get("comment_count", 0) * ENGAGEMENT_WEIGHTS["comment"] +
            stats.get("share_count", 0) * ENGAGEMENT_WEIGHTS["share"] +
            stats.get("save_count", 0) * ENGAGEMENT_WEIGHTS["save"]
        )
        
        # Normalize by views
        engagement_rate = weighted_engagement / view_count
        
        # Normalize to 0-1 range (cap at 100% engagement rate)
        return min(1.0, engagement_rate / 100)
    
    def _calculate_relevance_score(
        self,
        post: Dict[str, Any],
        user_id: str,
    ) -> float:
        """Calculate style relevance score."""
        
        style_profile = self._get_style_profile(user_id)
        if not style_profile:
            return 0.5  # Neutral score if no profile
        
        # Check hashtag overlap
        post_hashtags = set(h.lower() for h in post.get("hashtags", []))
        
        # Simple relevance based on style archetype matching
        # In production, this would use ML embeddings
        score = 0.5
        
        # Boost for style-related hashtags
        style_tags = {"minimalist", "classic", "trendy", "bohemian", "edgy", "romantic"}
        matching_tags = post_hashtags & style_tags
        if matching_tags:
            score += 0.2
        
        return min(1.0, score)
    
    def _calculate_social_score(
        self,
        post: Dict[str, Any],
        user_id: str,
    ) -> float:
        """Calculate social relationship score."""
        
        post_user_id = post.get("user", {}).get("id")
        
        if not post_user_id or post_user_id == user_id:
            return 0.5
        
        # Check if following
        is_following = self._db.query(SocialFollow).filter(
            SocialFollow.follower_id == user_id,
            SocialFollow.following_id == post_user_id,
            SocialFollow.status == "active",
        ).first() is not None
        
        if is_following:
            return 1.0
        
        # Check mutual connections
        following_ids = set(self._get_following_ids(user_id))
        poster_followers = self._db.query(SocialFollow.follower_id).filter(
            SocialFollow.following_id == post_user_id,
            SocialFollow.status == "active",
        ).all()
        poster_follower_ids = set(str(f[0]) for f in poster_followers)
        
        mutual_count = len(following_ids & poster_follower_ids)
        
        if mutual_count > 0:
            return min(0.9, 0.5 + mutual_count * 0.1)
        
        return 0.3
    
    def _calculate_quality_score(self, post: Dict[str, Any]) -> float:
        """Calculate content quality score."""
        
        score = 0.5
        
        # Image count (more images = higher quality)
        image_count = len(post.get("image_urls", []))
        if image_count > 1:
            score += 0.1
        if image_count > 3:
            score += 0.1
        
        # Caption quality
        caption = post.get("caption", "")
        if caption:
            # Good caption length
            if 20 <= len(caption) <= 500:
                score += 0.15
            # Has hashtags
            if post.get("hashtags"):
                score += 0.1
        else:
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    # ── Helper Methods ───────────────────────────────────────────────────────────
    
    def _get_following_ids(self, user_id: str) -> List[str]:
        """Get list of user IDs that the user follows."""
        
        following = self._db.query(SocialFollow.following_id).filter(
            SocialFollow.follower_id == user_id,
            SocialFollow.status == "active",
        ).all()
        
        return [str(f[0]) for f in following]
    
    def _get_style_profile(self, user_id: str) -> Optional[UserStyleProfile]:
        """Get user style profile."""
        
        return self._db.query(UserStyleProfile).filter(
            UserStyleProfile.user_id == user_id
        ).first()
    
    def _get_posts_from_users(
        self,
        user_ids: List[str],
        viewer_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get posts from specified users."""
        
        posts = self._db.query(SocialPost).options(
            joinedload(SocialPost.user)
        ).filter(
            SocialPost.user_id.in_(user_ids),
            SocialPost.is_archived == False,
            SocialPost.visibility.in_(["public", "followers"]),
        ).order_by(SocialPost.created_at.desc()).offset(skip).limit(limit).all()
        
        return self._serialize_posts(posts, viewer_id)
    
    def _get_trending_posts(
        self,
        viewer_id: str,
        timeframe: str = "day",
        exclude_post_ids: List[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get trending posts based on engagement velocity."""
        
        # Calculate time window
        if timeframe == "hour":
            window = timedelta(hours=1)
        elif timeframe == "day":
            window = timedelta(hours=TRENDING_WINDOW_HOURS)
        elif timeframe == "week":
            window = timedelta(weeks=1)
        else:
            window = timedelta(hours=TRENDING_WINDOW_HOURS)
        
        cutoff = datetime.now(timezone.utc) - window
        
        query = self._db.query(SocialPost).options(
            joinedload(SocialPost.user)
        ).join(
            SocialPostStats,
            SocialPostStats.post_id == SocialPost.id,
        ).filter(
            SocialPost.is_archived == False,
            SocialPost.visibility == "public",
            SocialPostStats.last_activity_at >= cutoff,
        )
        
        if exclude_post_ids:
            query = query.filter(SocialPost.id.notin_(exclude_post_ids))
        
        posts = query.order_by(
            desc(SocialPostStats.trending_score),
            desc(SocialPostStats.engagement_rate),
        ).offset(skip).limit(limit).all()
        
        return self._serialize_posts(posts, viewer_id)
    
    def _get_style_relevant_posts(
        self,
        style_profile: UserStyleProfile,
        viewer_id: str,
        exclude_post_ids: List[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get posts relevant to user style preferences."""
        
        # Get style-related hashtags
        archetype = style_profile.primary_archetype or "classic_chic"
        
        # Map archetypes to hashtags
        archetype_hashtags = {
            "classic_chic": ["classic", "timeless", "elegant"],
            "urban_edge": ["streetwear", "urban", "edgy"],
            "bohemian_spirit": ["boho", "bohemian", "free"],
            "modern_minimalist": ["minimalist", "minimal", "clean"],
            "romantic_feminine": ["romantic", "feminine", "soft"],
            "sport_luxe": ["sporty", "athleisure", "active"],
            "avant_garde": ["avantgarde", "experimental", "bold"],
            "preppy_polished": ["preppy", "polished", "refined"],
        }
        
        tags = archetype_hashtags.get(archetype, ["fashion"])
        
        query = self._db.query(SocialPost).options(
            joinedload(SocialPost.user)
        ).filter(
            SocialPost.is_archived == False,
            SocialPost.visibility == "public",
            or_(*[SocialPost.hashtags.contains([tag]) for tag in tags]),
        )
        
        if exclude_post_ids:
            query = query.filter(SocialPost.id.notin_(exclude_post_ids))
        
        posts = query.order_by(SocialPost.created_at.desc()).limit(limit).all()
        
        return self._serialize_posts(posts, viewer_id)
    
    def _get_featured_posts(
        self,
        viewer_id: str,
        exclude_post_ids: List[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get featured/curated posts."""
        
        query = self._db.query(SocialPost).options(
            joinedload(SocialPost.user)
        ).join(
            SocialPostStats,
            SocialPostStats.post_id == SocialPost.id,
        ).filter(
            SocialPost.is_featured == True,
            SocialPost.is_archived == False,
            SocialPost.visibility == "public",
        )
        
        if exclude_post_ids:
            query = query.filter(SocialPost.id.notin_(exclude_post_ids))
        
        posts = query.order_by(SocialPost.created_at.desc()).limit(limit).all()
        
        return self._serialize_posts(posts, viewer_id)
    
    def _get_public_stories(
        self,
        viewer_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get public stories for non-following users."""
        
        stories = self._db.query(SocialStory).options(
            joinedload(SocialStory.user)
        ).filter(
            SocialStory.expires_at > datetime.now(timezone.utc),
        ).order_by(SocialStory.view_count.desc()).limit(limit).all()
        
        # Group by user
        user_stories = {}
        for story in stories:
            uid = str(story.user_id)
            if uid not in user_stories:
                user_stories[uid] = {
                    "user": {
                        "id": uid,
                        "name": story.user.name,
                        "avatar_url": story.user.avatar_url,
                    },
                    "stories": [],
                    "has_unseen": True,
                }
            
            user_stories[uid]["stories"].append({
                "id": str(story.id),
                "media_url": story.media_url,
                "media_type": story.media_type,
                "caption": story.caption,
                "view_count": story.view_count,
                "is_viewed": False,
                "created_at": story.created_at.isoformat(),
                "expires_at": story.expires_at.isoformat(),
            })
        
        return list(user_stories.values())[:limit]
    
    def _serialize_posts(
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
                from database.models import SocialLike, SocialSave
                is_liked = self._db.query(SocialLike).filter(
                    SocialLike.user_id == viewer_id,
                    SocialLike.entity_type == "post",
                    SocialLike.entity_id == post.id,
                ).first() is not None
                
                is_saved = self._db.query(SocialSave).filter(
                    SocialSave.user_id == viewer_id,
                    SocialSave.post_id == post.id,
                ).first() is not None
            
            result.append({
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
            })
        
        return result
    
    # ── Caching ──────────────────────────────────────────────────────────────────
    
    def _get_cached_feed(
        self,
        user_id: str,
        feed_type: FeedType,
        skip: int,
        limit: int,
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached feed if available and not expired."""
        
        cache_entries = self._db.query(SocialFeedCache).options(
            joinedload(SocialFeedCache.post).joinedload(SocialPost.user)
        ).filter(
            SocialFeedCache.user_id == user_id,
            SocialFeedCache.feed_type == feed_type,
            SocialFeedCache.expires_at > datetime.now(timezone.utc),
        ).order_by(SocialFeedCache.position).offset(skip).limit(limit).all()
        
        if not cache_entries:
            return None
        
        return self._serialize_posts([c.post for c in cache_entries], user_id)
    
    def _cache_feed(
        self,
        user_id: str,
        feed_type: FeedType,
        posts: List[Dict[str, Any]],
    ) -> None:
        """Cache feed entries for performance."""
        
        # Clear old cache
        self._db.query(SocialFeedCache).filter(
            SocialFeedCache.user_id == user_id,
            SocialFeedCache.feed_type == feed_type,
        ).delete()
        
        # Add new cache entries
        expires = datetime.now(timezone.utc) + timedelta(minutes=15)
        
        for i, post in enumerate(posts):
            cache_entry = SocialFeedCache(
                user_id=user_id,
                post_id=post["id"],
                feed_type=feed_type,
                position=i,
                score=post.get("_score", 0.0),
                expires_at=expires,
            )
            self._db.add(cache_entry)
        
        self._db.commit()
    
    def invalidate_feed_cache(self, user_id: str, feed_type: FeedType = None) -> None:
        """Invalidate feed cache for user."""
        
        query = self._db.query(SocialFeedCache).filter(
            SocialFeedCache.user_id == user_id,
        )
        
        if feed_type:
            query = query.filter(SocialFeedCache.feed_type == feed_type)
        
        query.delete()
        self._db.commit()


def get_feed_service(db: Session = Depends(get_db)) -> FeedService:
    """Factory function for FeedService dependency injection."""
    return FeedService(db)
