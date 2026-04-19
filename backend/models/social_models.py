from datetime import datetime
from typing import List, Optional, Literal, Dict, Any

from pydantic import BaseModel, Field, HttpUrl


# ── Type Aliases ────────────────────────────────────────────────────────────────

Visibility = Literal["private", "link", "public", "followers"]
PostType = Literal["outfit", "lookbook", "story"]
FeedType = Literal["home", "discover", "following", "trending"]
VoteValue = Literal["hot", "cold"]
ReportReason = Literal["spam", "harassment", "inappropriate", "copyright", "other"]


# ── User Models ────────────────────────────────────────────────────────────────

class SocialUserResponse(BaseModel):
    id: str
    name: str
    avatar_url: Optional[str] = None
    style_preference: Optional[str] = None
    followers_count: Optional[int] = None
    following_count: Optional[int] = None
    is_following: Optional[bool] = None
    is_followed_by: Optional[bool] = None

    class Config:
        from_attributes = True


class FollowStatusResponse(BaseModel):
    is_following: bool
    is_followed_by: bool
    is_mutual: bool
    is_blocked: bool
    is_blocked_by: bool


# ── Post Models ────────────────────────────────────────────────────────────────

class SocialPostCreate(BaseModel):
    image_url: HttpUrl
    caption: Optional[str] = Field(None, max_length=500)
    visibility: Visibility = "private"


class SocialPostCreateV2(BaseModel):
    """Extended post creation model."""
    image_urls: List[str] = Field(..., min_length=1, max_length=10)
    caption: Optional[str] = Field(None, max_length=2000)
    outfit_id: Optional[str] = None
    hashtags: Optional[List[str]] = Field(None, max_items=30)
    post_type: PostType = "outfit"
    visibility: Literal["public", "followers", "private"] = "public"
    location: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = Field(None, max_items=20)


class SocialPostStats(BaseModel):
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    save_count: int = 0
    view_count: int = 0
    engagement_rate: float = 0.0
    trending_score: float = 0.0


class SocialPostResponse(BaseModel):
    id: str
    owner_user_id: str
    image_url: HttpUrl
    caption: Optional[str] = None
    visibility: Visibility
    created_at: datetime
    hot_count: int = 0
    cold_count: int = 0
    user_vote: Optional[VoteValue] = None

    class Config:
        from_attributes = True


class SocialPostResponseV2(BaseModel):
    """Extended post response model."""
    id: str
    user: SocialUserResponse
    outfit_id: Optional[str] = None
    caption: Optional[str] = None
    hashtags: List[str] = []
    image_urls: List[str] = []
    video_url: Optional[str] = None
    post_type: PostType = "outfit"
    visibility: str = "public"
    location: Optional[str] = None
    tags: List[str] = []
    is_featured: bool = False
    created_at: str
    stats: Optional[SocialPostStats] = None
    is_liked: bool = False
    is_saved: bool = False
    _score: Optional[float] = None

    class Config:
        from_attributes = True


class SocialPostUpdate(BaseModel):
    caption: Optional[str] = Field(None, max_length=2000)
    hashtags: Optional[List[str]] = Field(None, max_items=30)
    visibility: Optional[Literal["public", "followers", "private"]] = None
    location: Optional[str] = Field(None, max_length=255)


# ── Comment Models ──────────────────────────────────────────────────────────────

class SocialCommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)
    parent_id: Optional[str] = None
    mentions: Optional[List[str]] = Field(None, max_items=10)


class SocialCommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class SocialCommentResponse(BaseModel):
    id: str
    user: SocialUserResponse
    post_id: str
    parent_id: Optional[str] = None
    content: str
    mentions: List[str] = []
    is_edited: bool = False
    like_count: int = 0
    is_liked: bool = False
    reply_count: int = 0
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


# ── Like/Save Models ────────────────────────────────────────────────────────────

class SocialLikeRequest(BaseModel):
    entity_type: Literal["post", "comment"]
    entity_id: str


class SocialSaveRequest(BaseModel):
    post_id: str
    collection_name: Optional[str] = Field(None, max_length=100)


class SocialShareRequest(BaseModel):
    post_id: str
    platform: Optional[str] = Field(None, max_length=50)


# ── Follow Models ───────────────────────────────────────────────────────────────

class SocialFollowRequest(BaseModel):
    user_id: str


class SocialFollowResponse(BaseModel):
    status: str
    following: Optional[SocialUserResponse] = None
    message: Optional[str] = None


# ── Story Models ────────────────────────────────────────────────────────────────

class SocialStoryCreate(BaseModel):
    media_url: str
    media_type: Literal["image", "video"] = "image"
    outfit_id: Optional[str] = None
    caption: Optional[str] = Field(None, max_length=500)
    hashtags: Optional[List[str]] = Field(None, max_items=10)
    duration_secs: Optional[int] = None


class SocialStoryResponse(BaseModel):
    id: str
    media_url: str
    media_type: str
    caption: Optional[str] = None
    view_count: int = 0
    is_viewed: bool = False
    created_at: str
    expires_at: str


class SocialStoryGroupResponse(BaseModel):
    user: SocialUserResponse
    stories: List[SocialStoryResponse]
    has_unseen: bool


# ── Report Models ───────────────────────────────────────────────────────────────

class SocialReportCreate(BaseModel):
    entity_type: Literal["post", "comment", "user", "story"]
    entity_id: str
    reason: ReportReason
    description: Optional[str] = Field(None, max_length=1000)


class SocialReportResponse(BaseModel):
    id: str
    reporter_id: str
    entity_type: str
    entity_id: str
    reason: str
    description: Optional[str] = None
    status: str = "pending"
    created_at: str

    class Config:
        from_attributes = True


# ── Feed Models ─────────────────────────────────────────────────────────────────

class SocialFeedResponse(BaseModel):
    posts: List[SocialPostResponseV2]
    has_more: bool
    feed_type: FeedType = "home"
    timeframe: Optional[str] = None


class SocialFeedRequest(BaseModel):
    feed_type: FeedType = "home"
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)
    timeframe: Optional[Literal["hour", "day", "week"]] = "day"


# ── Hashtag Models ──────────────────────────────────────────────────────────────

class SocialHashtagResponse(BaseModel):
    tag: str
    post_count: int
    trending_score: float


# ── Legacy Models (kept for backward compatibility) ─────────────────────────────

class SocialVoteRequest(BaseModel):
    value: VoteValue


class SocialLookbookItem(BaseModel):
    product_id: str
    note: Optional[str] = Field(None, max_length=200)


class LookbookCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    items: List[SocialLookbookItem] = Field(..., min_items=1)
    commission_rate: float = Field(0.1, ge=0.0, le=0.5)
    visibility: Literal["public", "private"] = "public"


class LookbookResponse(BaseModel):
    id: str
    stylist_user_id: str
    title: str
    description: Optional[str]
    items: List[SocialLookbookItem]
    commission_rate: float
    visibility: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

