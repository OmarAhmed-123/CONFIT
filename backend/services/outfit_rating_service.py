"""
CONFIT Backend — Outfit Rating Service
======================================
Service for managing outfit ratings, likes, saves, shares, and computing
ranking algorithms for trending, popularity, and style relevance scores.
"""

import logging
import math
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import func, and_, desc, or_
from sqlalchemy.orm import Session

from database.models import (
    Outfit,
    OutfitRating,
    OutfitLike,
    OutfitPopularity,
    OutfitSave,
    OutfitShare,
    OutfitRatingRateLimit,
    User,
)
from schemas.outfit_rating_schemas import (
    OutfitRatingCreate,
    OutfitRatingUpdate,
    OutfitRatingResponse,
    OutfitLikeCreate,
    OutfitLikeResponse,
    OutfitLikeToggleResponse,
    OutfitSaveCreate,
    OutfitSaveResponse,
    OutfitShareCreate,
    OutfitShareResponse,
    OutfitPopularityResponse,
    OutfitWithRatingsResponse,
    TrendingOutfitItem,
    TrendingOutfitsResponse,
    OutfitRankingFilters,
    UserOutfitEngagementSummary,
)

logger = logging.getLogger(__name__)


# ── Rate Limiting Configuration ────────────────────────────────────────────────

RATE_LIMITS = {
    "rate": {"max_actions": 50, "window_minutes": 60},      # 50 ratings per hour
    "like": {"max_actions": 100, "window_minutes": 60},     # 100 likes per hour
    "save": {"max_actions": 30, "window_minutes": 60},      # 30 saves per hour
    "share": {"max_actions": 20, "window_minutes": 60},     # 20 shares per hour
}


# ── Ranking Algorithm Constants ────────────────────────────────────────────────

# Trending score weights
TRENDING_WEIGHTS = {
    "recent_likes": 0.25,      # Weight for likes in time window
    "recent_ratings": 0.20,    # Weight for ratings in time window
    "recent_saves": 0.15,      # Weight for saves in time window
    "recent_shares": 0.15,     # Weight for shares in time window
    "avg_rating": 0.15,        # Weight for average rating
    "velocity": 0.10,          # Weight for engagement velocity
}

# Popularity score weights
POPULARITY_WEIGHTS = {
    "total_likes": 0.20,
    "total_ratings": 0.15,
    "avg_rating": 0.25,
    "total_saves": 0.20,
    "total_shares": 0.10,
    "total_views": 0.10,
}

# Time decay factor (older interactions have less weight)
TIME_DECAY_FACTOR = 0.95


class OutfitRatingService:
    """Service for outfit rating operations and ranking algorithms."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Rate Limiting ────────────────────────────────────────────────────────────

    def _check_rate_limit(self, user_id: str, action_type: str) -> Tuple[bool, int]:
        """
        Check if user is within rate limit for an action type.
        Returns (is_allowed, remaining_actions).
        """
        limit_config = RATE_LIMITS.get(action_type, {"max_actions": 100, "window_minutes": 60})
        max_actions = limit_config["max_actions"]
        window_minutes = limit_config["window_minutes"]
        window_start = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

        # Get or create rate limit record
        rate_limit = (
            self._db.query(OutfitRatingRateLimit)
            .filter(
                OutfitRatingRateLimit.user_id == user_id,
                OutfitRatingRateLimit.action_type == action_type,
                OutfitRatingRateLimit.window_start >= window_start,
            )
            .first()
        )

        if rate_limit:
            if rate_limit.action_count >= max_actions:
                return False, 0
            return True, max_actions - rate_limit.action_count

        return True, max_actions

    def _record_rate_limit_action(self, user_id: str, action_type: str) -> None:
        """Record an action for rate limiting purposes."""
        limit_config = RATE_LIMITS.get(action_type, {"max_actions": 100, "window_minutes": 60})
        window_minutes = limit_config["window_minutes"]
        window_start = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

        # Find existing record in current window
        rate_limit = (
            self._db.query(OutfitRatingRateLimit)
            .filter(
                OutfitRatingRateLimit.user_id == user_id,
                OutfitRatingRateLimit.action_type == action_type,
                OutfitRatingRateLimit.window_start >= window_start,
            )
            .first()
        )

        if rate_limit:
            rate_limit.action_count += 1
            rate_limit.updated_at = datetime.now(timezone.utc)
        else:
            # Create new record
            rate_limit = OutfitRatingRateLimit(
                id=str(uuid.uuid4()),
                user_id=user_id,
                action_type=action_type,
                action_count=1,
                window_start=datetime.now(timezone.utc),
            )
            self._db.add(rate_limit)

        self._db.commit()

    # ── Rating Operations ────────────────────────────────────────────────────────

    def rate_outfit(
        self, user_id: str, outfit_id: str, payload: OutfitRatingCreate
    ) -> OutfitRatingResponse:
        """Rate an outfit (1-5 stars). Updates existing rating if present."""
        # Check rate limit
        is_allowed, remaining = self._check_rate_limit(user_id, "rate")
        if not is_allowed:
            raise ValueError("Rate limit exceeded for ratings. Please try again later.")

        # Verify outfit exists
        outfit = self._db.query(Outfit).filter(Outfit.id == outfit_id).first()
        if not outfit:
            raise ValueError("Outfit not found")

        # Prevent rating own outfit
        if outfit.owner_user_id == user_id:
            raise ValueError("Cannot rate your own outfit")

        # Check for existing rating
        existing = (
            self._db.query(OutfitRating)
            .filter(
                OutfitRating.outfit_id == outfit_id,
                OutfitRating.user_id == user_id,
            )
            .first()
        )

        now = datetime.now(timezone.utc)

        if existing:
            existing.rating = payload.rating
            existing.review = payload.review
            existing.updated_at = now
            rating = existing
            logger.info(f"Updated rating for outfit {outfit_id} by user {user_id}")
        else:
            rating = OutfitRating(
                id=str(uuid.uuid4()),
                outfit_id=outfit_id,
                user_id=user_id,
                rating=payload.rating,
                review=payload.review,
                created_at=now,
                updated_at=now,
            )
            self._db.add(rating)
            self._record_rate_limit_action(user_id, "rate")
            logger.info(f"Created rating for outfit {outfit_id} by user {user_id}")

        self._db.commit()
        self._db.refresh(rating)

        # Update popularity metrics
        self._update_popularity_metrics(outfit_id)

        return self._rating_to_response(rating)

    def get_user_rating(self, user_id: str, outfit_id: str) -> Optional[OutfitRatingResponse]:
        """Get the current user's rating for an outfit."""
        rating = (
            self._db.query(OutfitRating)
            .filter(
                OutfitRating.outfit_id == outfit_id,
                OutfitRating.user_id == user_id,
            )
            .first()
        )
        return self._rating_to_response(rating) if rating else None

    def get_outfit_ratings(
        self, outfit_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[OutfitRatingResponse], int]:
        """Get all ratings for an outfit with pagination."""
        query = (
            self._db.query(OutfitRating)
            .filter(OutfitRating.outfit_id == outfit_id)
            .order_by(desc(OutfitRating.created_at))
        )

        total = query.count()
        ratings = query.offset((page - 1) * page_size).limit(page_size).all()

        return [self._rating_to_response(r) for r in ratings], total

    def delete_rating(self, user_id: str, outfit_id: str) -> bool:
        """Delete user's rating for an outfit."""
        rating = (
            self._db.query(OutfitRating)
            .filter(
                OutfitRating.outfit_id == outfit_id,
                OutfitRating.user_id == user_id,
            )
            .first()
        )

        if not rating:
            return False

        self._db.delete(rating)
        self._db.commit()

        # Update popularity metrics
        self._update_popularity_metrics(outfit_id)

        logger.info(f"Deleted rating for outfit {outfit_id} by user {user_id}")
        return True

    # ── Like Operations ──────────────────────────────────────────────────────────

    def toggle_like(
        self, user_id: str, outfit_id: str, payload: OutfitLikeCreate
    ) -> OutfitLikeToggleResponse:
        """Toggle like/dislike for an outfit. Removes existing if same action."""
        # Check rate limit
        is_allowed, _ = self._check_rate_limit(user_id, "like")
        if not is_allowed:
            raise ValueError("Rate limit exceeded for likes. Please try again later.")

        # Verify outfit exists
        outfit = self._db.query(Outfit).filter(Outfit.id == outfit_id).first()
        if not outfit:
            raise ValueError("Outfit not found")

        # Prevent liking own outfit
        if outfit.owner_user_id == user_id:
            raise ValueError("Cannot like your own outfit")

        # Check for existing like/dislike
        existing = (
            self._db.query(OutfitLike)
            .filter(
                OutfitLike.outfit_id == outfit_id,
                OutfitLike.user_id == user_id,
            )
            .first()
        )

        now = datetime.now(timezone.utc)
        is_liked = None
        is_disliked = None

        if existing:
            if existing.is_like == payload.is_like:
                # Toggle off - remove the like/dislike
                self._db.delete(existing)
                logger.info(f"Removed {'like' if payload.is_like else 'dislike'} for outfit {outfit_id}")
            else:
                # Switch from like to dislike or vice versa
                existing.is_like = payload.is_like
                existing.created_at = now
                is_liked = payload.is_like
                is_disliked = not payload.is_like
                logger.info(f"Switched to {'like' if payload.is_like else 'dislike'} for outfit {outfit_id}")
        else:
            # Create new like/dislike
            like = OutfitLike(
                id=str(uuid.uuid4()),
                outfit_id=outfit_id,
                user_id=user_id,
                is_like=payload.is_like,
                created_at=now,
            )
            self._db.add(like)
            self._record_rate_limit_action(user_id, "like")
            is_liked = payload.is_like
            is_disliked = not payload.is_like
            logger.info(f"Created {'like' if payload.is_like else 'dislike'} for outfit {outfit_id}")

        self._db.commit()

        # Update popularity metrics
        self._update_popularity_metrics(outfit_id)

        # Get updated counts
        popularity = self._get_or_create_popularity(outfit_id)

        return OutfitLikeToggleResponse(
            outfit_id=outfit_id,
            is_liked=is_liked,
            is_disliked=is_disliked,
            like_count=popularity.like_count,
            dislike_count=popularity.dislike_count,
        )

    def get_user_like(self, user_id: str, outfit_id: str) -> Optional[OutfitLikeResponse]:
        """Get the current user's like status for an outfit."""
        like = (
            self._db.query(OutfitLike)
            .filter(
                OutfitLike.outfit_id == outfit_id,
                OutfitLike.user_id == user_id,
            )
            .first()
        )
        return self._like_to_response(like) if like else None

    # ── Save Operations ──────────────────────────────────────────────────────────

    def save_outfit(
        self, user_id: str, outfit_id: str, payload: OutfitSaveCreate
    ) -> OutfitSaveResponse:
        """Save an outfit to user's collection."""
        # Check rate limit
        is_allowed, _ = self._check_rate_limit(user_id, "save")
        if not is_allowed:
            raise ValueError("Rate limit exceeded for saves. Please try again later.")

        # Verify outfit exists
        outfit = self._db.query(Outfit).filter(Outfit.id == outfit_id).first()
        if not outfit:
            raise ValueError("Outfit not found")

        # Check if already saved
        existing = (
            self._db.query(OutfitSave)
            .filter(
                OutfitSave.outfit_id == outfit_id,
                OutfitSave.user_id == user_id,
            )
            .first()
        )

        if existing:
            # Update collection name if provided
            if payload.collection_name:
                existing.collection_name = payload.collection_name
                self._db.commit()
                self._db.refresh(existing)
            return self._save_to_response(existing)

        now = datetime.now(timezone.utc)
        save = OutfitSave(
            id=str(uuid.uuid4()),
            outfit_id=outfit_id,
            user_id=user_id,
            collection_name=payload.collection_name,
            created_at=now,
        )
        self._db.add(save)
        self._record_rate_limit_action(user_id, "save")
        self._db.commit()
        self._db.refresh(save)

        # Update popularity metrics
        self._update_popularity_metrics(outfit_id)

        logger.info(f"Saved outfit {outfit_id} for user {user_id}")
        return self._save_to_response(save)

    def unsave_outfit(self, user_id: str, outfit_id: str) -> bool:
        """Remove an outfit from user's saved collection."""
        save = (
            self._db.query(OutfitSave)
            .filter(
                OutfitSave.outfit_id == outfit_id,
                OutfitSave.user_id == user_id,
            )
            .first()
        )

        if not save:
            return False

        self._db.delete(save)
        self._db.commit()

        # Update popularity metrics
        self._update_popularity_metrics(outfit_id)

        logger.info(f"Unsaved outfit {outfit_id} for user {user_id}")
        return True

    def get_user_saved_outfits(
        self, user_id: str, collection_name: Optional[str] = None, page: int = 1, page_size: int = 20
    ) -> Tuple[List[OutfitSaveResponse], int]:
        """Get user's saved outfits with optional collection filter."""
        query = self._db.query(OutfitSave).filter(OutfitSave.user_id == user_id)

        if collection_name:
            query = query.filter(OutfitSave.collection_name == collection_name)

        query = query.order_by(desc(OutfitSave.created_at))

        total = query.count()
        saves = query.offset((page - 1) * page_size).limit(page_size).all()

        return [self._save_to_response(s) for s in saves], total

    def is_outfit_saved(self, user_id: str, outfit_id: str) -> bool:
        """Check if an outfit is saved by the user."""
        return (
            self._db.query(OutfitSave)
            .filter(
                OutfitSave.outfit_id == outfit_id,
                OutfitSave.user_id == user_id,
            )
            .first()
            is not None
        )

    # ── Share Operations ─────────────────────────────────────────────────────────

    def record_share(
        self, user_id: str, outfit_id: str, payload: OutfitShareCreate
    ) -> OutfitShareResponse:
        """Record an outfit share event."""
        # Check rate limit
        is_allowed, _ = self._check_rate_limit(user_id, "share")
        if not is_allowed:
            raise ValueError("Rate limit exceeded for shares. Please try again later.")

        # Verify outfit exists
        outfit = self._db.query(Outfit).filter(Outfit.id == outfit_id).first()
        if not outfit:
            raise ValueError("Outfit not found")

        now = datetime.now(timezone.utc)
        share = OutfitShare(
            id=str(uuid.uuid4()),
            outfit_id=outfit_id,
            user_id=user_id,
            platform=payload.platform,
            created_at=now,
        )
        self._db.add(share)
        self._record_rate_limit_action(user_id, "share")
        self._db.commit()
        self._db.refresh(share)

        # Update popularity metrics
        self._update_popularity_metrics(outfit_id)

        logger.info(f"Recorded share for outfit {outfit_id} on {payload.platform}")
        return self._share_to_response(share)

    # ── View Tracking ───────────────────────────────────────────────────────────

    def record_view(self, outfit_id: str) -> None:
        """Record a view for an outfit (for popularity calculations)."""
        popularity = self._get_or_create_popularity(outfit_id)
        popularity.view_count += 1
        popularity.last_activity_at = datetime.now(timezone.utc)
        self._db.commit()

    # ── Popularity & Ranking Algorithms ──────────────────────────────────────────

    def _get_or_create_popularity(self, outfit_id: str) -> OutfitPopularity:
        """Get or create popularity record for an outfit."""
        popularity = (
            self._db.query(OutfitPopularity)
            .filter(OutfitPopularity.outfit_id == outfit_id)
            .first()
        )

        if not popularity:
            popularity = OutfitPopularity(
                id=str(uuid.uuid4()),
                outfit_id=outfit_id,
            )
            self._db.add(popularity)
            self._db.commit()
            self._db.refresh(popularity)

        return popularity

    def _update_popularity_metrics(self, outfit_id: str) -> OutfitPopularity:
        """Update all popularity metrics for an outfit."""
        popularity = self._get_or_create_popularity(outfit_id)

        # Calculate rating metrics
        rating_stats = (
            self._db.query(
                func.count(OutfitRating.id).label("total"),
                func.sum(OutfitRating.rating).label("sum"),
                func.avg(OutfitRating.rating).label("avg"),
            )
            .filter(OutfitRating.outfit_id == outfit_id)
            .first()
        )

        popularity.total_ratings = rating_stats.total or 0
        popularity.rating_sum = rating_stats.sum or 0
        popularity.avg_rating = float(rating_stats.avg) if rating_stats.avg else 0.0

        # Calculate like/dislike counts
        like_count = (
            self._db.query(func.count(OutfitLike.id))
            .filter(OutfitLike.outfit_id == outfit_id, OutfitLike.is_like == True)
            .scalar()
        )
        dislike_count = (
            self._db.query(func.count(OutfitLike.id))
            .filter(OutfitLike.outfit_id == outfit_id, OutfitLike.is_like == False)
            .scalar()
        )
        popularity.like_count = like_count or 0
        popularity.dislike_count = dislike_count or 0

        # Calculate save count
        save_count = (
            self._db.query(func.count(OutfitSave.id))
            .filter(OutfitSave.outfit_id == outfit_id)
            .scalar()
        )
        popularity.save_count = save_count or 0

        # Calculate share count
        share_count = (
            self._db.query(func.count(OutfitShare.id))
            .filter(OutfitShare.outfit_id == outfit_id)
            .scalar()
        )
        popularity.share_count = share_count or 0

        # Calculate scores
        popularity.trending_score = self._calculate_trending_score(outfit_id)
        popularity.popularity_score = self._calculate_popularity_score(popularity)
        popularity.style_relevance_score = self._calculate_style_relevance_score(outfit_id)

        popularity.last_activity_at = datetime.now(timezone.utc)
        popularity.updated_at = datetime.now(timezone.utc)

        self._db.commit()
        self._db.refresh(popularity)

        return popularity

    def _calculate_trending_score(self, outfit_id: str) -> float:
        """
        Calculate trending score based on recent engagement velocity.
        
        Formula considers:
        - Recent likes, ratings, saves, shares (last 7 days)
        - Average rating quality
        - Engagement velocity (rate of change)
        """
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        day_ago = now - timedelta(days=1)

        # Recent likes
        recent_likes = (
            self._db.query(func.count(OutfitLike.id))
            .filter(
                OutfitLike.outfit_id == outfit_id,
                OutfitLike.is_like == True,
                OutfitLike.created_at >= week_ago,
            )
            .scalar()
        ) or 0

        # Recent ratings
        recent_ratings = (
            self._db.query(func.count(OutfitRating.id))
            .filter(
                OutfitRating.outfit_id == outfit_id,
                OutfitRating.created_at >= week_ago,
            )
            .scalar()
        ) or 0

        # Recent saves
        recent_saves = (
            self._db.query(func.count(OutfitSave.id))
            .filter(
                OutfitSave.outfit_id == outfit_id,
                OutfitSave.created_at >= week_ago,
            )
            .scalar()
        ) or 0

        # Recent shares
        recent_shares = (
            self._db.query(func.count(OutfitShare.id))
            .filter(
                OutfitShare.outfit_id == outfit_id,
                OutfitShare.created_at >= week_ago,
            )
            .scalar()
        ) or 0

        # Average rating
        avg_rating = (
            self._db.query(func.avg(OutfitRating.rating))
            .filter(OutfitRating.outfit_id == outfit_id)
            .scalar()
        ) or 0.0

        # Yesterday's engagement for velocity
        yesterday_likes = (
            self._db.query(func.count(OutfitLike.id))
            .filter(
                OutfitLike.outfit_id == outfit_id,
                OutfitLike.is_like == True,
                OutfitLike.created_at >= day_ago,
            )
            .scalar()
        ) or 0

        # Velocity: ratio of today's engagement to average daily engagement
        total_recent = recent_likes + recent_ratings + recent_saves + recent_shares
        avg_daily = total_recent / 7 if total_recent > 0 else 1
        velocity = yesterday_likes / avg_daily if avg_daily > 0 else 0
        velocity = min(velocity, 5.0)  # Cap velocity

        # Normalize components
        normalized_likes = min(recent_likes / 50, 1.0)  # Cap at 50 likes
        normalized_ratings = min(recent_ratings / 30, 1.0)  # Cap at 30 ratings
        normalized_saves = min(recent_saves / 20, 1.0)  # Cap at 20 saves
        normalized_shares = min(recent_shares / 15, 1.0)  # Cap at 15 shares
        normalized_avg_rating = (avg_rating / 5.0) if avg_rating else 0

        # Calculate weighted score
        trending_score = (
            TRENDING_WEIGHTS["recent_likes"] * normalized_likes +
            TRENDING_WEIGHTS["recent_ratings"] * normalized_ratings +
            TRENDING_WEIGHTS["recent_saves"] * normalized_saves +
            TRENDING_WEIGHTS["recent_shares"] * normalized_shares +
            TRENDING_WEIGHTS["avg_rating"] * normalized_avg_rating +
            TRENDING_WEIGHTS["velocity"] * (velocity / 5.0)
        )

        return round(trending_score * 100, 2)  # Scale to 0-100

    def _calculate_popularity_score(self, popularity: OutfitPopularity) -> float:
        """
        Calculate overall popularity score based on total engagement.
        
        Formula considers:
        - Total likes, ratings, saves, shares, views
        - Average rating quality
        """
        # Normalize components
        normalized_likes = min(popularity.like_count / 500, 1.0)
        normalized_ratings = min(popularity.total_ratings / 300, 1.0)
        normalized_avg_rating = popularity.avg_rating / 5.0 if popularity.avg_rating else 0
        normalized_saves = min(popularity.save_count / 200, 1.0)
        normalized_shares = min(popularity.share_count / 100, 1.0)
        normalized_views = min(popularity.view_count / 5000, 1.0)

        # Calculate weighted score
        popularity_score = (
            POPULARITY_WEIGHTS["total_likes"] * normalized_likes +
            POPULARITY_WEIGHTS["total_ratings"] * normalized_ratings +
            POPULARITY_WEIGHTS["avg_rating"] * normalized_avg_rating +
            POPULARITY_WEIGHTS["total_saves"] * normalized_saves +
            POPULARITY_WEIGHTS["total_shares"] * normalized_shares +
            POPULARITY_WEIGHTS["total_views"] * normalized_views
        )

        return round(popularity_score * 100, 2)  # Scale to 0-100

    def _calculate_style_relevance_score(self, outfit_id: str) -> float:
        """
        Calculate style relevance score based on outfit's style alignment.
        
        This considers:
        - Category diversity in outfit items
        - Color coordination
        - Occasion appropriateness
        - Brand synergy
        """
        outfit = self._db.query(Outfit).filter(Outfit.id == outfit_id).first()
        if not outfit or not outfit.items:
            return 0.0

        items = outfit.items
        score = 0.0

        # Category diversity (0-25 points)
        categories = set()
        for item in items:
            if item.get("category"):
                categories.add(item["category"])
        category_score = min(len(categories) * 5, 25)
        score += category_score

        # Color coordination (0-25 points) - simplified
        colors = []
        for item in items:
            if item.get("color"):
                colors.append(item["color"].lower())
        unique_colors = len(set(colors))
        # Optimal is 2-3 colors, penalize too many or too few
        if 2 <= unique_colors <= 3:
            score += 25
        elif unique_colors == 1:
            score += 15
        elif unique_colors == 4:
            score += 15
        else:
            score += max(0, 25 - (unique_colors - 3) * 5)

        # Occasion appropriateness (0-25 points)
        if outfit.occasion:
            # Bonus for having an occasion set
            score += 15
            # Check if items match the occasion
            occasion_lower = outfit.occasion.lower()
            if any(
                occasion_lower in ["work", "office", "business"]
                and item.get("category", "").lower() in ["tops", "bottoms", "shoes", "accessories"]
                for item in items
            ):
                score += 10
        else:
            score += 10  # Default score for no occasion

        # Brand synergy (0-25 points)
        brands = [item.get("brand") for item in items if item.get("brand")]
        if brands:
            unique_brands = len(set(brands))
            # Fewer brands = more cohesive
            brand_score = max(0, 25 - (unique_brands - 1) * 5)
            score += brand_score
        else:
            score += 15  # Default for no brand info

        return round(min(score, 100), 2)

    # ── Trending & Rankings ──────────────────────────────────────────────────────

    def get_trending_outfits(
        self, filters: OutfitRankingFilters
    ) -> TrendingOutfitsResponse:
        """Get trending outfits based on ranking algorithms."""
        # Determine time window
        time_window_map = {
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "all": timedelta(days=36500),  # 100 years
        }
        time_delta = time_window_map.get(filters.time_window, timedelta(days=7))
        cutoff = datetime.now(timezone.utc) - time_delta

        # Build query
        query = (
            self._db.query(Outfit, OutfitPopularity)
            .join(OutfitPopularity, Outfit.id == OutfitPopularity.outfit_id)
            .filter(OutfitPopularity.last_activity_at >= cutoff)
        )

        # Apply filters
        if filters.min_rating:
            query = query.filter(OutfitPopularity.avg_rating >= filters.min_rating)
        if filters.min_ratings_count:
            query = query.filter(OutfitPopularity.total_ratings >= filters.min_ratings_count)

        # Get category/occasion from outfit items (JSON field filtering is complex, simplified)
        # In production, would use proper JSON query or denormalized fields

        # Order by trending score
        query = query.order_by(desc(OutfitPopularity.trending_score))

        # Get total count
        total = query.count()

        # Paginate
        offset = (filters.page - 1) * filters.page_size
        results = query.offset(offset).limit(filters.page_size).all()

        # Build response
        outfits = []
        for rank, (outfit, popularity) in enumerate(results, start=offset + 1):
            outfits.append(
                TrendingOutfitItem(
                    outfit_id=outfit.id,
                    title=outfit.title,
                    items=outfit.items,
                    total_price=outfit.total_price,
                    currency=outfit.currency or "USD",
                    avg_rating=popularity.avg_rating,
                    total_ratings=popularity.total_ratings,
                    like_count=popularity.like_count,
                    trending_score=popularity.trending_score,
                    popularity_score=popularity.popularity_score,
                    rank=rank,
                )
            )

        return TrendingOutfitsResponse(
            outfits=outfits,
            time_window=filters.time_window,
            total_count=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    def get_popular_outfits(
        self, filters: OutfitRankingFilters
    ) -> TrendingOutfitsResponse:
        """Get popular outfits based on overall popularity score."""
        # Build query
        query = (
            self._db.query(Outfit, OutfitPopularity)
            .join(OutfitPopularity, Outfit.id == OutfitPopularity.outfit_id)
        )

        # Apply filters
        if filters.min_rating:
            query = query.filter(OutfitPopularity.avg_rating >= filters.min_rating)
        if filters.min_ratings_count:
            query = query.filter(OutfitPopularity.total_ratings >= filters.min_ratings_count)

        # Order by popularity score
        query = query.order_by(desc(OutfitPopularity.popularity_score))

        # Get total count
        total = query.count()

        # Paginate
        offset = (filters.page - 1) * filters.page_size
        results = query.offset(offset).limit(filters.page_size).all()

        # Build response
        outfits = []
        for rank, (outfit, popularity) in enumerate(results, start=offset + 1):
            outfits.append(
                TrendingOutfitItem(
                    outfit_id=outfit.id,
                    title=outfit.title,
                    items=outfit.items,
                    total_price=outfit.total_price,
                    currency=outfit.currency or "USD",
                    avg_rating=popularity.avg_rating,
                    total_ratings=popularity.total_ratings,
                    like_count=popularity.like_count,
                    trending_score=popularity.trending_score,
                    popularity_score=popularity.popularity_score,
                    rank=rank,
                )
            )

        return TrendingOutfitsResponse(
            outfits=outfits,
            time_window=filters.time_window,
            total_count=total,
            page=filters.page,
            page_size=filters.page_size,
        )

    def get_outfit_popularity(self, outfit_id: str) -> OutfitPopularityResponse:
        """Get popularity metrics for a specific outfit."""
        popularity = self._get_or_create_popularity(outfit_id)
        return OutfitPopularityResponse(
            outfit_id=outfit_id,
            total_ratings=popularity.total_ratings,
            avg_rating=popularity.avg_rating,
            like_count=popularity.like_count,
            dislike_count=popularity.dislike_count,
            save_count=popularity.save_count,
            share_count=popularity.share_count,
            view_count=popularity.view_count,
            trending_score=popularity.trending_score,
            popularity_score=popularity.popularity_score,
            style_relevance_score=popularity.style_relevance_score,
            last_activity_at=popularity.last_activity_at,
        )

    # ── User Engagement ──────────────────────────────────────────────────────────

    def get_user_engagement_summary(
        self, user_id: str, outfit_id: str
    ) -> UserOutfitEngagementSummary:
        """Get summary of user's engagement with an outfit."""
        rating = (
            self._db.query(OutfitRating)
            .filter(
                OutfitRating.outfit_id == outfit_id,
                OutfitRating.user_id == user_id,
            )
            .first()
        )

        like = (
            self._db.query(OutfitLike)
            .filter(
                OutfitLike.outfit_id == outfit_id,
                OutfitLike.user_id == user_id,
            )
            .first()
        )

        save = (
            self._db.query(OutfitSave)
            .filter(
                OutfitSave.outfit_id == outfit_id,
                OutfitSave.user_id == user_id,
            )
            .first()
        )

        share = (
            self._db.query(OutfitShare)
            .filter(
                OutfitShare.outfit_id == outfit_id,
                OutfitShare.user_id == user_id,
            )
            .first()
        )

        return UserOutfitEngagementSummary(
            outfit_id=outfit_id,
            has_rated=rating is not None,
            user_rating=rating.rating if rating else None,
            has_liked=like is not None,
            is_like=like.is_like if like else None,
            has_saved=save is not None,
            collection_name=save.collection_name if save else None,
            has_shared=share is not None,
        )

    def get_outfit_with_ratings(
        self, user_id: str, outfit_id: str
    ) -> Optional[OutfitWithRatingsResponse]:
        """Get outfit details with rating info for a user."""
        outfit = self._db.query(Outfit).filter(Outfit.id == outfit_id).first()
        if not outfit:
            return None

        popularity = self._get_or_create_popularity(outfit_id)
        engagement = self.get_user_engagement_summary(user_id, outfit_id)

        return OutfitWithRatingsResponse(
            id=outfit.id,
            owner_user_id=outfit.owner_user_id,
            title=outfit.title,
            items=outfit.items,
            occasion=outfit.occasion,
            notes=outfit.notes,
            budget_limit=outfit.budget_limit,
            total_price=outfit.total_price,
            currency=outfit.currency or "USD",
            created_at=outfit.created_at,
            updated_at=outfit.updated_at,
            share_slug=outfit.share_slug,
            popularity=OutfitPopularityResponse(
                outfit_id=outfit_id,
                total_ratings=popularity.total_ratings,
                avg_rating=popularity.avg_rating,
                like_count=popularity.like_count,
                dislike_count=popularity.dislike_count,
                save_count=popularity.save_count,
                share_count=popularity.share_count,
                view_count=popularity.view_count,
                trending_score=popularity.trending_score,
                popularity_score=popularity.popularity_score,
                style_relevance_score=popularity.style_relevance_score,
                last_activity_at=popularity.last_activity_at,
            ),
            user_rating=engagement.user_rating,
            user_liked=engagement.is_like,
            user_saved=engagement.has_saved,
        )

    # ── Helper Methods ───────────────────────────────────────────────────────────

    def _rating_to_response(self, rating: OutfitRating) -> OutfitRatingResponse:
        return OutfitRatingResponse(
            id=rating.id,
            outfit_id=rating.outfit_id,
            user_id=rating.user_id,
            rating=rating.rating,
            review=rating.review,
            created_at=rating.created_at,
            updated_at=rating.updated_at,
        )

    def _like_to_response(self, like: OutfitLike) -> OutfitLikeResponse:
        return OutfitLikeResponse(
            id=like.id,
            outfit_id=like.outfit_id,
            user_id=like.user_id,
            is_like=like.is_like,
            created_at=like.created_at,
        )

    def _save_to_response(self, save: OutfitSave) -> OutfitSaveResponse:
        return OutfitSaveResponse(
            id=save.id,
            outfit_id=save.outfit_id,
            user_id=save.user_id,
            collection_name=save.collection_name,
            created_at=save.created_at,
        )

    def _share_to_response(self, share: OutfitShare) -> OutfitShareResponse:
        return OutfitShareResponse(
            id=share.id,
            outfit_id=share.outfit_id,
            user_id=share.user_id,
            platform=share.platform,
            created_at=share.created_at,
        )
