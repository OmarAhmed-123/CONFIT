"""
CONFIT Backend — Social Router
==============================
API endpoints for social feed functionality.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.session import get_db
from services.social_post_service import PostService, get_post_service
from services.social_comment_service import CommentService, get_comment_service
from services.social_follow_service import FollowService, get_follow_service
from services.social_feed_service import FeedService, get_feed_service
from models.social_models import (
    SocialPostCreateV2,
    SocialPostResponseV2,
    SocialPostUpdate,
    SocialCommentCreate,
    SocialCommentUpdate,
    SocialCommentResponse,
    SocialFollowRequest,
    SocialFollowResponse,
    SocialFollowResponse,
    SocialFeedResponse,
    SocialStoryCreate,
    SocialStoryGroupResponse,
    SocialReportCreate,
    SocialReportResponse,
    SocialHashtagResponse,
    SocialSaveRequest,
    SocialShareRequest,
    FollowStatusResponse,
    SocialUserResponse,
)

router = APIRouter(prefix="/social", tags=["social"])


# ── Authentication Dependency ────────────────────────────────────────────────────

async def get_current_user_id() -> str:
    """
    Placeholder for authentication.
    In production, this would decode JWT and return user ID.
    """
    # TODO: Integrate with actual auth system
    from middleware.auth import require_auth
    # return await require_auth()
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated"
    )


def get_optional_user_id() -> Optional[str]:
    """Get user ID if authenticated, otherwise None."""
    try:
        # TODO: Implement optional auth
        return None
    except:
        return None


# ── Feed Endpoints ──────────────────────────────────────────────────────────────

@router.get("/feed", response_model=SocialFeedResponse)
async def get_feed(
    feed_type: str = Query("home", pattern="^(home|discover|following|trending)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    timeframe: Optional[str] = Query("day", pattern="^(hour|day|week)$"),
    user_id: str = Depends(get_current_user_id),
    feed_service: FeedService = Depends(get_feed_service),
):
    """Get personalized social feed."""
    
    if feed_type == "home":
        return feed_service.get_home_feed(user_id, skip, limit)
    elif feed_type == "discover":
        return feed_service.get_discover_feed(user_id, skip, limit)
    elif feed_type == "following":
        return feed_service.get_following_feed(user_id, skip, limit)
    elif feed_type == "trending":
        return feed_service.get_trending_feed(user_id, skip, limit, timeframe)
    
    raise HTTPException(status_code=400, detail="Invalid feed type")


@router.get("/stories", response_model=list[SocialStoryGroupResponse])
async def get_stories(
    limit: int = Query(20, ge=1, le=50),
    user_id: str = Depends(get_current_user_id),
    feed_service: FeedService = Depends(get_feed_service),
):
    """Get active stories from followed users."""
    
    return feed_service.get_stories(user_id, limit)


@router.post("/stories/{story_id}/view")
async def mark_story_viewed(
    story_id: str,
    user_id: str = Depends(get_current_user_id),
    feed_service: FeedService = Depends(get_feed_service),
):
    """Mark a story as viewed."""
    
    success = feed_service.mark_story_viewed(story_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Story not found")
    
    return {"success": True}


# ── Post Endpoints ──────────────────────────────────────────────────────────────

@router.post("/posts", response_model=SocialPostResponseV2, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: SocialPostCreateV2,
    user_id: str = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    """Create a new social post."""
    
    try:
        post = post_service.create_post(
            user_id=user_id,
            image_urls=post_data.image_urls,
            caption=post_data.caption,
            outfit_id=post_data.outfit_id,
            hashtags=post_data.hashtags,
            post_type=post_data.post_type,
            visibility=post_data.visibility,
            location=post_data.location,
            tags=post_data.tags,
        )
        
        # Get the full post data
        post_data = post_service.get_post(str(post.id), user_id)
        return post_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/posts/{post_id}", response_model=SocialPostResponseV2)
async def get_post(
    post_id: str,
    user_id: str = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    """Get a single post by ID."""
    
    post = post_service.get_post(post_id, user_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return post


@router.patch("/posts/{post_id}", response_model=SocialPostResponseV2)
async def update_post(
    post_id: str,
    post_data: SocialPostUpdate,
    user_id: str = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    """Update a post."""
    
    post = post_service.update_post(
        post_id=post_id,
        user_id=user_id,
        caption=post_data.caption,
        hashtags=post_data.hashtags,
        visibility=post_data.visibility,
        location=post_data.location,
    )
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found or not authorized")
    
    return post_service.get_post(post_id, user_id)


@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    user_id: str = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    """Delete a post."""
    
    success = post_service.delete_post(post_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Post not found or not authorized")
    
    return {"success": True}


# ── Post Engagement ─────────────────────────────────────────────────────────────

@router.post("/posts/{post_id}/like")
async def like_post(
    post_id: str,
    user_id: str = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    """Like a post."""
    
    success = post_service.like_post(post_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Already liked or post not found")
    
    return {"success": True, "liked": True}


@router.delete("/posts/{post_id}/like")
async def unlike_post(
    post_id: str,
    user_id: str = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    """Unlike a post."""
    
    success = post_service.unlike_post(post_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Not liked or post not found")
    
    return {"success": True, "liked": False}


@router.post("/posts/{post_id}/save")
async def save_post(
    post_id: str,
    save_data: SocialSaveRequest = None,
    user_id: str = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    """Save a post to collection."""
    
    collection_name = save_data.collection_name if save_data else None
    success = post_service.save_post(post_id, user_id, collection_name)
    
    if not success:
        raise HTTPException(status_code=400, detail="Already saved or post not found")
    
    return {"success": True, "saved": True}


@router.delete("/posts/{post_id}/save")
async def unsave_post(
    post_id: str,
    user_id: str = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    """Unsave a post."""
    
    success = post_service.unsave_post(post_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Not saved or post not found")
    
    return {"success": True, "saved": False}


@router.post("/posts/{post_id}/share")
async def share_post(
    post_id: str,
    share_data: SocialShareRequest,
    user_id: str = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    """Track post share."""
    
    success = post_service.share_post(post_id, user_id, share_data.platform)
    return {"success": success}


# ── Comment Endpoints ───────────────────────────────────────────────────────────

@router.post("/posts/{post_id}/comments", response_model=SocialCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: str,
    comment_data: SocialCommentCreate,
    user_id: str = Depends(get_current_user_id),
    comment_service: CommentService = Depends(get_comment_service),
):
    """Create a comment on a post."""
    
    try:
        comment = comment_service.create_comment(
            post_id=post_id,
            user_id=user_id,
            content=comment_data.content,
            parent_id=comment_data.parent_id,
            mentions=comment_data.mentions,
        )
        
        return comment_service.get_comment(str(comment.id))
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/posts/{post_id}/comments", response_model=list[SocialCommentResponse])
async def get_post_comments(
    post_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("newest", pattern="^(newest|oldest|top)$"),
    user_id: str = Depends(get_current_user_id),
    comment_service: CommentService = Depends(get_comment_service),
):
    """Get comments for a post."""
    
    return comment_service.get_post_comments(post_id, user_id, skip, limit, sort)


@router.patch("/comments/{comment_id}", response_model=SocialCommentResponse)
async def update_comment(
    comment_id: str,
    comment_data: SocialCommentUpdate,
    user_id: str = Depends(get_current_user_id),
    comment_service: CommentService = Depends(get_comment_service),
):
    """Update a comment."""
    
    try:
        comment = comment_service.update_comment(
            comment_id=comment_id,
            user_id=user_id,
            content=comment_data.content,
        )
        
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found or not authorized")
        
        return comment_service.get_comment(comment_id)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: str,
    user_id: str = Depends(get_current_user_id),
    comment_service: CommentService = Depends(get_comment_service),
):
    """Delete a comment."""
    
    success = comment_service.delete_comment(comment_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found or not authorized")
    
    return {"success": True}


@router.get("/comments/{comment_id}/replies", response_model=list[SocialCommentResponse])
async def get_comment_replies(
    comment_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user_id),
    comment_service: CommentService = Depends(get_comment_service),
):
    """Get replies to a comment."""
    
    return comment_service.get_comment_replies(comment_id, user_id, skip, limit)


@router.post("/comments/{comment_id}/like")
async def like_comment(
    comment_id: str,
    user_id: str = Depends(get_current_user_id),
    comment_service: CommentService = Depends(get_comment_service),
):
    """Like a comment."""
    
    success = comment_service.like_comment(comment_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Already liked or comment not found")
    
    return {"success": True, "liked": True}


@router.delete("/comments/{comment_id}/like")
async def unlike_comment(
    comment_id: str,
    user_id: str = Depends(get_current_user_id),
    comment_service: CommentService = Depends(get_comment_service),
):
    """Unlike a comment."""
    
    success = comment_service.unlike_comment(comment_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Not liked or comment not found")
    
    return {"success": True, "liked": False}


# ── Follow Endpoints ────────────────────────────────────────────────────────────

@router.post("/follow", response_model=SocialFollowResponse)
async def follow_user(
    follow_data: SocialFollowRequest,
    user_id: str = Depends(get_current_user_id),
    follow_service: FollowService = Depends(get_follow_service),
):
    """Follow a user."""
    
    try:
        result = follow_service.follow_user(user_id, follow_data.user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/follow/{target_user_id}")
async def unfollow_user(
    target_user_id: str,
    user_id: str = Depends(get_current_user_id),
    follow_service: FollowService = Depends(get_follow_service),
):
    """Unfollow a user."""
    
    success = follow_service.unfollow_user(user_id, target_user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Not following this user")
    
    return {"success": True, "following": False}


@router.post("/block/{target_user_id}")
async def block_user(
    target_user_id: str,
    user_id: str = Depends(get_current_user_id),
    follow_service: FollowService = Depends(get_follow_service),
):
    """Block a user."""
    
    try:
        success = follow_service.block_user(user_id, target_user_id)
        return {"success": success, "blocked": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/block/{target_user_id}")
async def unblock_user(
    target_user_id: str,
    user_id: str = Depends(get_current_user_id),
    follow_service: FollowService = Depends(get_follow_service),
):
    """Unblock a user."""
    
    success = follow_service.unblock_user(user_id, target_user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Not blocking this user")
    
    return {"success": True, "blocked": False}


@router.get("/users/{target_user_id}/follow-status", response_model=FollowStatusResponse)
async def get_follow_status(
    target_user_id: str,
    user_id: str = Depends(get_current_user_id),
    follow_service: FollowService = Depends(get_follow_service),
):
    """Get follow status between current user and target user."""
    
    return follow_service.get_follow_status(user_id, target_user_id)


@router.get("/users/{target_user_id}/followers", response_model=list[SocialUserResponse])
async def get_followers(
    target_user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    follow_service: FollowService = Depends(get_follow_service),
):
    """Get followers of a user."""
    
    return follow_service.get_followers(target_user_id, user_id, skip, limit)


@router.get("/users/{target_user_id}/following", response_model=list[SocialUserResponse])
async def get_following(
    target_user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    follow_service: FollowService = Depends(get_follow_service),
):
    """Get users that a user is following."""
    
    return follow_service.get_following(target_user_id, user_id, skip, limit)


@router.get("/suggestions", response_model=list[SocialUserResponse])
async def get_suggested_users(
    limit: int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user_id),
    follow_service: FollowService = Depends(get_follow_service),
):
    """Get suggested users to follow."""
    
    return follow_service.get_suggested_users(user_id, limit)


@router.get("/stylists/popular", response_model=list[SocialUserResponse])
async def get_popular_stylists(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    follow_service: FollowService = Depends(get_follow_service),
):
    """Get popular stylists ranked by followers."""
    
    return follow_service.get_popular_stylists(skip, limit)


# ── User Posts ──────────────────────────────────────────────────────────────────

@router.get("/users/{target_user_id}/posts", response_model=list[SocialPostResponseV2])
async def get_user_posts(
    target_user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    """Get posts by a specific user."""
    
    return post_service.get_user_posts(target_user_id, user_id, skip, limit)


@router.get("/saved", response_model=list[SocialPostResponseV2])
async def get_saved_posts(
    collection: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    """Get posts saved by the current user."""
    
    return post_service.get_user_saved_posts(user_id, collection, skip, limit)


# ── Hashtags ────────────────────────────────────────────────────────────────────

@router.get("/hashtags/trending", response_model=list[SocialHashtagResponse])
async def get_trending_hashtags(
    limit: int = Query(10, ge=1, le=50),
    feed_service: FeedService = Depends(get_feed_service),
):
    """Get trending hashtags."""
    
    return feed_service.get_trending_hashtags(limit)


@router.get("/hashtags/{hashtag}/posts", response_model=list[SocialPostResponseV2])
async def get_posts_by_hashtag(
    hashtag: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    """Get posts by hashtag."""
    
    return post_service.get_posts_by_hashtag(hashtag, user_id, skip, limit)


# ── Reports & Moderation ────────────────────────────────────────────────────────

@router.post("/reports", response_model=SocialReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    report_data: SocialReportCreate,
    user_id: str = Depends(get_current_user_id),
    post_service: PostService = Depends(get_post_service),
):
    """Report content for moderation."""
    
    if report_data.entity_type == "post":
        report = post_service.report_post(
            post_id=report_data.entity_id,
            reporter_id=user_id,
            reason=report_data.reason,
            description=report_data.description,
        )
    else:
        # TODO: Handle other entity types
        raise HTTPException(status_code=400, detail="Entity type not supported yet")
    
    return {
        "id": str(report.id),
        "reporter_id": str(report.reporter_id),
        "entity_type": report.entity_type,
        "entity_id": str(report.entity_id),
        "reason": report.reason,
        "description": report.description,
        "status": report.status,
        "created_at": report.created_at.isoformat(),
    }


# ── User Stats ──────────────────────────────────────────────────────────────────

@router.get("/users/{target_user_id}/stats")
async def get_user_stats(
    target_user_id: str,
    follow_service: FollowService = Depends(get_follow_service),
):
    """Get social stats for a user."""
    
    return follow_service.get_user_stats(target_user_id)
