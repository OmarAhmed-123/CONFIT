"""Pydantic schemas for the Autonomous Growth Engine API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ViralFeedPost(BaseModel):
    id: str
    outfit_image_url: str
    try_on_preview_url: Optional[str] = None
    style_tags: List[str] = Field(default_factory=list)
    caption: Optional[str] = None
    creator: Dict[str, Any]
    shop_product_id: Optional[str] = None
    shop_url: Optional[str] = None
    rank_score: float = 0.0
    engagement_probability: float = 0.0
    style_similarity: float = 0.0
    trend_momentum: float = 0.0
    created_at: datetime


class ViralFeedResponse(BaseModel):
    posts: List[ViralFeedPost]
    next_offset: int
    has_more: bool
    personalization: str = "engagement+style+trend"


class ShareOutfitBody(BaseModel):
    outfit_id: Optional[str] = None
    post_id: Optional[str] = None


class ShareOutfitResponse(BaseModel):
    share_url: str
    referral_code: str
    rate_limit_remaining: int


class ReferralCreateBody(BaseModel):
    outfit_id: Optional[str] = None
    post_id: Optional[str] = None


class ReferralClaimBody(BaseModel):
    referral_code: str = Field(..., min_length=4, max_length=64)


class ReferralClaimResponse(BaseModel):
    status: str
    reward_credits_referrer: int
    reward_credits_referee: int


class PredictResponse(BaseModel):
    purchase_likelihood: float
    churn_risk: float
    share_probability: float
    engagement_index: float
    suggested_actions: List[str] = Field(default_factory=list)


class GrowthNotifyPreview(BaseModel):
    push: List[dict] = Field(default_factory=list)
    email: List[dict] = Field(default_factory=list)
    banners: List[dict] = Field(default_factory=list)
    suppressed_due_to_churn_risk: bool = False


class GrowthAnalyticsSummary(BaseModel):
    viral_coefficient_estimate: float
    outfit_share_rate: float
    conversion_per_outfit: float
    try_on_engagement_rate: float
    bottlenecks: List[str] = Field(default_factory=list)
    optimizations: List[str] = Field(default_factory=list)


class CreatorSuggestion(BaseModel):
    influencer_id: str
    display_name: str
    avatar_url: Optional[str] = None
    style_dna_score: float
    engagement_overlap: float
    budget_alignment: float
    composite_score: float


class CreatorMatchResponse(BaseModel):
    creators: List[CreatorSuggestion]


class GraphEdgeOut(BaseModel):
    target_type: str
    target_id: str
    weight: float
    interaction_count: int


class UserGraphResponse(BaseModel):
    edges: List[GraphEdgeOut]


class GraphTouchBody(BaseModel):
    target_type: str = Field(pattern="^(style|creator|brand|outfit)$")
    target_id: str = Field(..., min_length=1, max_length=128)
