"""
CONFIT — Autonomous Growth Engine API
=====================================
/growth/* — viral feed, referrals, predictions, notifications preview, analytics.
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from core.api_response import ok
from core.slowapi_limiter import limiter
from database.models import User
from database.session import get_db
from models.growth_schemas import (
    CreatorMatchResponse,
    CreatorSuggestion,
    GraphTouchBody,
    GrowthAnalyticsSummary,
    GrowthNotifyPreview,
    PredictResponse,
    ReferralClaimBody,
    ReferralClaimResponse,
    ReferralCreateBody,
    ShareOutfitBody,
    ShareOutfitResponse,
    UserGraphResponse,
    ViralFeedPost,
    ViralFeedResponse,
)
from services import growth_service as gs
from services.auth_service import UserProfile
from utils.auth_deps import optional_auth, require_auth

router = APIRouter(prefix="/api/growth", tags=["Growth Engine"])

FRONTEND_BASE = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")


def _user_row(db: Session, profile: UserProfile) -> Optional[User]:
    return db.query(User).filter(User.id == profile.id).first()


@router.get("/feed", response_model=ViralFeedResponse)
async def viral_outfit_feed(
    offset: int = Query(0, ge=0, le=10_000),
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
    user: Optional[UserProfile] = Depends(optional_auth),
):
    """
    Instagram-style viral outfit feed with personalized ranking:
    engagement probability, style similarity, trend momentum.
    """
    u = db.query(User).filter(User.id == user.id).first() if user else None
    posts, next_off, has_more = gs.rank_viral_posts(db, u, offset, limit)
    items = [ViralFeedPost.model_validate(p) for p in posts]
    return ViralFeedResponse(posts=items, next_offset=next_off, has_more=has_more)


@router.post("/share", response_model=ShareOutfitResponse)
@limiter.limit("20/minute")
async def growth_share_outfit(
    request: Request,
    body: ShareOutfitBody,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """
    Create a shareable referral link for an outfit/post. Rate-limited to reduce spam loops.
    """
    urow = _user_row(db, user)
    if not urow:
        raise HTTPException(status_code=404, detail="User not found")

    allowed, remaining = gs.check_share_rate_limit(db, user.id)
    if not allowed:
        raise HTTPException(status_code=429, detail="Share rate limit exceeded. Try again later.")

    ref = gs.create_referral_row(db, user.id, body.outfit_id, body.post_id)
    remaining = gs.record_share(db, user.id)
    gs.detect_suspicious_share(db, urow)

    if body.outfit_id:
        gs.upsert_graph_edge(db, user.id, "outfit", body.outfit_id, 2.0, {"via": "share"})
    if body.post_id:
        gs.upsert_graph_edge(db, user.id, "outfit", f"post:{body.post_id}", 1.0, {"via": "share"})

    share_url = f"{FRONTEND_BASE}/join?ref={ref.referral_code}"
    db.commit()

    return ShareOutfitResponse(
        share_url=share_url,
        referral_code=ref.referral_code,
        rate_limit_remaining=remaining,
    )


@router.post("/referral", response_model=dict)
async def growth_create_referral(
    body: ReferralCreateBody,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Explicit referral row (for outfit share flows)."""
    ref = gs.create_referral_row(db, user.id, body.outfit_id, body.post_id)
    db.commit()
    return ok(
        {
            "referral_code": ref.referral_code,
            "share_url": f"{FRONTEND_BASE}/join?ref={ref.referral_code}",
        }
    )


@router.post("/referral/claim", response_model=ReferralClaimResponse)
async def growth_claim_referral(
    body: ReferralClaimBody,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """New user completes referral — rewards both sides (credits tracked server-side)."""
    status, ref_amt, refee_amt = gs.claim_referral(db, user.id, body.referral_code)
    if status == "invalid":
        raise HTTPException(status_code=400, detail="Invalid referral code")
    if status == "already_used":
        raise HTTPException(status_code=409, detail="Referral already used")
    if status == "self_referral":
        raise HTTPException(status_code=400, detail="Cannot use your own referral")
    db.commit()
    return ReferralClaimResponse(
        status="completed",
        reward_credits_referrer=ref_amt,
        reward_credits_referee=refee_amt,
    )


@router.get("/predict", response_model=PredictResponse)
async def growth_predict(
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Engagement prediction engine — purchase, churn, share; drives downstream automation."""
    urow = _user_row(db, user)
    if not urow:
        raise HTTPException(status_code=404, detail="User not found")
    score = gs.update_engagement_heuristic(db, urow)
    db.commit()

    actions: list[str] = []
    if score.churn_risk > 0.55:
        actions.append("trigger_soft_reactivation_sequence")
    if score.purchase_likelihood > 0.62:
        actions.append("surface_high_intent_merchandising")
    if score.share_probability > 0.5:
        actions.append("prompt_timed_referral_after_try_on")

    return PredictResponse(
        purchase_likelihood=round(float(score.purchase_likelihood), 4),
        churn_risk=round(float(score.churn_risk), 4),
        share_probability=round(float(score.share_probability), 4),
        engagement_index=round(float(score.engagement_index), 4),
        suggested_actions=actions,
    )


@router.get("/notify", response_model=GrowthNotifyPreview)
async def growth_notify_preview(
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """
    AI marketing automation preview (push / email / in-app banners).
    Does not send externally — uses engagement prediction to avoid spam.
    """
    urow = _user_row(db, user)
    if not urow:
        raise HTTPException(status_code=404, detail="User not found")
    payload = gs.build_notify_preview(db, urow)
    db.commit()
    return GrowthNotifyPreview.model_validate(payload)


@router.get("/analytics", response_model=GrowthAnalyticsSummary)
async def growth_analytics_brain(
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Growth Analytics Brain — viral KPIs, bottlenecks, auto-suggested optimizations."""
    data = gs.growth_analytics_summary(db)
    return GrowthAnalyticsSummary.model_validate(data)


@router.get("/creators", response_model=CreatorMatchResponse)
async def growth_creator_matches(
    limit: int = Query(8, ge=1, le=30),
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Influencer AI matching — Creators you may follow."""
    urow = _user_row(db, user)
    if not urow:
        raise HTTPException(status_code=404, detail="User not found")
    raw = gs.match_influencers(db, urow, limit=limit)
    items = [CreatorSuggestion.model_validate(x) for x in raw]
    return CreatorMatchResponse(creators=items)


@router.get("/graph", response_model=UserGraphResponse)
async def growth_fashion_graph(
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Social Fashion Graph — top weighted edges for the current user."""
    edges = gs.graph_edges_for_user(db, user.id, limit=50)
    return UserGraphResponse(
        edges=[
            {
                "target_type": e.target_type,
                "target_id": e.target_id,
                "weight": float(e.weight),
                "interaction_count": int(e.interaction_count or 0),
            }
            for e in edges
        ]
    )


@router.post("/graph/touch")
async def growth_graph_touch(
    body: GraphTouchBody,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """Record a graph edge (e.g. follow brand, save style) for recommendations."""
    gs.upsert_graph_edge(db, user.id, body.target_type, body.target_id, 1.5)
    db.commit()
    return ok({"recorded": True})
