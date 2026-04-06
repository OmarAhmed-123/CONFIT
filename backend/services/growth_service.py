"""
CONFIT Autonomous Growth Engine — core logic
============================================
Viral feed ranking, fashion graph, referrals, predictions, analytics.
"""

from __future__ import annotations

import hashlib
import math
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.growth_models import (
    EngagementScore,
    GrowthEvent,
    GrowthShareRateLimit,
    Referral,
    UserGraphEdge,
)
from database.models import Influencer, Outfit, SocialPost, SocialPostStats, User


# ── Weights: engagement · style similarity · trend momentum ─────────────────
W_ENGAGEMENT = 0.42
W_STYLE = 0.33
W_TREND = 0.25

SHARE_WINDOW = timedelta(hours=1)
MAX_SHARES_PER_WINDOW = 15
REFERRAL_REWARD_EACH = 50


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_tag(t: str) -> str:
    return t.strip().lower().replace("#", "")


def _user_tag_set(user: Optional[User]) -> Set[str]:
    if not user:
        return set()
    tags: Set[str] = set()
    if user.style_preference:
        tags.add(_normalize_tag(user.style_preference))
    pb = user.preferred_brands
    if isinstance(pb, list):
        tags.update(_normalize_tag(str(x)) for x in pb)
    elif isinstance(pb, dict):
        tags.update(_normalize_tag(str(k)) for k in pb.keys())
    occ = user.occasion_preferences
    if isinstance(occ, list):
        tags.update(_normalize_tag(str(x)) for x in occ)
    elif isinstance(occ, dict):
        tags.update(_normalize_tag(str(k)) for k in occ.keys())
    return {t for t in tags if t}


def _post_tag_set(post: SocialPost) -> Set[str]:
    tags: Set[str] = set()
    for raw in post.hashtags or []:
        tags.add(_normalize_tag(str(raw)))
    for raw in post.tags or []:
        if isinstance(raw, dict) and raw.get("type") == "style":
            tags.add(_normalize_tag(str(raw.get("id", ""))))
        else:
            tags.add(_normalize_tag(str(raw)))
    return {t for t in tags if t}


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 0.35
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _get_or_create_engagement_score(db: Session, user_id: str) -> EngagementScore:
    row = db.query(EngagementScore).filter(EngagementScore.user_id == user_id).first()
    if row:
        return row
    row = EngagementScore(user_id=user_id)
    db.add(row)
    db.flush()
    return row


def update_engagement_heuristic(db: Session, user: User) -> EngagementScore:
    """Refresh heuristic scores from profile + activity signals."""
    row = _get_or_create_engagement_score(db, user.id)
    budget = user.budget_range or {}
    spend_hint = 0.5
    if isinstance(budget, dict):
        mx = budget.get("max") or budget.get("monthly_max")
        if isinstance(mx, (int, float)):
            spend_hint = min(1.0, float(mx) / 2000.0)

    purchase = min(0.95, 0.25 + 0.5 * spend_hint + 0.1 * (1.0 if user.marketing_consent else 0.0))
    churn = max(0.05, 0.55 - 0.3 * spend_hint - 0.1 * (1.0 if user.data_sharing_consent else 0.0))
    share_p = min(0.9, 0.2 + 0.4 * jaccard(_user_tag_set(user), {"streetwear", "minimal", "classic"}))
    eng_idx = (purchase + share_p + (1.0 - churn)) / 3.0

    row.purchase_likelihood = float(purchase)
    row.churn_risk = float(churn)
    row.share_probability = float(share_p)
    row.engagement_index = float(eng_idx)
    row.style_vector_hint = {"tags": list(_user_tag_set(user))[:20]}
    row.updated_at = _now()
    return row


def _stats_map(db: Session, post_ids: Sequence[str]) -> Dict[str, SocialPostStats]:
    if not post_ids:
        return {}
    rows = (
        db.query(SocialPostStats)
        .filter(SocialPostStats.post_id.in_(post_ids))
        .all()
    )
    return {str(r.post_id): r for r in rows}


def _creator_public_dict(db: Session, user_id: str) -> dict:
    u = db.query(User).filter(User.id == user_id).first()
    inf = db.query(Influencer).filter(Influencer.user_id == user_id).first()
    name = u.name if u else "Creator"
    avatar = u.avatar_url if u else None
    handle = inf.display_name if inf else name
    return {
        "user_id": str(user_id),
        "display_name": handle,
        "avatar_url": avatar,
        "is_influencer": inf is not None,
        "influencer_id": str(inf.id) if inf else None,
    }


def _first_product_id_from_outfit(outfit: Optional[Outfit]) -> Optional[str]:
    if not outfit or not outfit.items:
        return None
    items = outfit.items
    if isinstance(items, list) and items:
        first = items[0]
        if isinstance(first, dict):
            return first.get("product_id") or first.get("id")
    return None


def rank_viral_posts(
    db: Session,
    user: Optional[User],
    offset: int,
    limit: int,
) -> Tuple[List[dict], int, bool]:
    """
    Personalized ranking: engagement probability, style similarity, trend momentum.
    """
    user_tags = _user_tag_set(user)

    pool_size = min(180, max(limit * 4, limit + offset + 20))
    q = (
        db.query(SocialPost)
        .filter(SocialPost.visibility == "public", SocialPost.is_archived.is_(False))
        .order_by(SocialPost.created_at.desc())
    )
    candidates = q.offset(0).limit(pool_size).all()

    ids = [str(p.id) for p in candidates]
    smap = _stats_map(db, ids)

    scored: List[Tuple[float, SocialPost]] = []
    for post in candidates:
        stats = smap.get(str(post.id))
        post_tags = _post_tag_set(post)
        sim = jaccard(user_tags, post_tags) if user_tags else 0.45

        if stats:
            eng = min(1.0, max(0.0, float(stats.engagement_rate or 0.0)))
            trend = min(1.0, max(0.0, float(stats.trending_score or 0.0)))
            if trend == 0.0:
                trend = min(1.0, 0.15 + math.log1p(float(stats.view_count or 0)) / 20.0)
        else:
            eng = 0.22
            trend = 0.2

        score = W_ENGAGEMENT * eng + W_STYLE * sim + W_TREND * trend
        scored.append((score, post))

    scored.sort(key=lambda x: x[0], reverse=True)

    slice_rows = scored[offset : offset + limit]
    has_more = offset + limit < len(scored)

    out: List[dict] = []
    for score, post in slice_rows:
        stats = smap.get(str(post.id))
        post_tags = list(_post_tag_set(post))
        imgs = post.image_urls or []
        outfit_img = imgs[0] if imgs else ""
        try_on = imgs[1] if len(imgs) > 1 else None
        sim = jaccard(user_tags, _post_tag_set(post)) if user_tags else 0.45
        if stats:
            eng = min(1.0, max(0.0, float(stats.engagement_rate or 0.0)))
            trend = min(1.0, max(0.0, float(stats.trending_score or 0.0)))
            if trend == 0.0:
                trend = min(1.0, 0.15 + math.log1p(float(stats.view_count or 0)) / 20.0)
        else:
            eng = 0.22
            trend = 0.2

        outfit = None
        shop_pid = None
        if post.outfit_id:
            outfit = db.query(Outfit).filter(Outfit.id == post.outfit_id).first()
            shop_pid = _first_product_id_from_outfit(outfit)

        shop_url = f"/product/{shop_pid}" if shop_pid else None

        out.append(
            {
                "id": str(post.id),
                "outfit_image_url": outfit_img,
                "try_on_preview_url": try_on,
                "style_tags": post_tags[:12],
                "caption": post.caption,
                "creator": _creator_public_dict(db, str(post.user_id)),
                "shop_product_id": shop_pid,
                "shop_url": shop_url,
                "rank_score": round(score, 4),
                "engagement_probability": round(eng, 4),
                "style_similarity": round(sim, 4),
                "trend_momentum": round(trend, 4),
                "created_at": post.created_at,
            }
        )

    return out, offset + len(out), has_more


def upsert_graph_edge(
    db: Session,
    user_id: str,
    target_type: str,
    target_id: str,
    delta: float = 1.0,
    meta: Optional[dict] = None,
) -> UserGraphEdge:
    edge = (
        db.query(UserGraphEdge)
        .filter(
            UserGraphEdge.user_id == user_id,
            UserGraphEdge.target_type == target_type,
            UserGraphEdge.target_id == target_id,
        )
        .first()
    )
    now = _now()
    if edge:
        edge.weight = min(500.0, edge.weight + delta)
        edge.interaction_count = int(edge.interaction_count or 0) + 1
        edge.last_interaction_at = now
        if meta:
            edge.meta = {**(edge.meta or {}), **meta}
    else:
        edge = UserGraphEdge(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            weight=delta,
            interaction_count=1,
            last_interaction_at=now,
            meta=meta,
        )
        db.add(edge)
    return edge


def _hour_window_start(now: datetime) -> datetime:
    return now.replace(minute=0, second=0, microsecond=0)


def check_share_rate_limit(db: Session, user_id: str) -> Tuple[bool, int]:
    """Returns (allowed, remaining in window)."""
    now = _now()
    window_start = _hour_window_start(now)

    row = (
        db.query(GrowthShareRateLimit)
        .filter(
            GrowthShareRateLimit.user_id == user_id,
            GrowthShareRateLimit.window_start == window_start,
        )
        .first()
    )
    if not row:
        return True, MAX_SHARES_PER_WINDOW
    remaining = max(0, MAX_SHARES_PER_WINDOW - int(row.share_count or 0))
    return remaining > 0, remaining


def record_share(db: Session, user_id: str) -> int:
    now = _now()
    window_start = _hour_window_start(now)
    row = (
        db.query(GrowthShareRateLimit)
        .filter(
            GrowthShareRateLimit.user_id == user_id,
            GrowthShareRateLimit.window_start == window_start,
        )
        .first()
    )
    if not row:
        row = GrowthShareRateLimit(user_id=user_id, window_start=window_start, share_count=1)
        db.add(row)
    else:
        row.share_count = int(row.share_count or 0) + 1
    row.updated_at = now
    remaining = max(0, MAX_SHARES_PER_WINDOW - int(row.share_count))
    return remaining


def detect_suspicious_share(db: Session, user: User) -> None:
    """Lightweight fake-account / spam loop detection."""
    if not user.created_at:
        return
    ca = user.created_at
    if ca.tzinfo is None:
        ca = ca.replace(tzinfo=timezone.utc)
    age = _now() - ca
    row = (
        db.query(GrowthShareRateLimit)
        .filter(GrowthShareRateLimit.user_id == user.id)
        .order_by(GrowthShareRateLimit.window_start.desc())
        .first()
    )
    cnt = int(row.share_count or 0) if row else 0
    if age < timedelta(days=2) and cnt > 25:
        db.add(
            GrowthEvent(
                user_id=user.id,
                event_type="suspicious_share_burst",
                payload={"share_count": cnt, "account_age_hours": age.total_seconds() / 3600},
                severity="warn",
            )
        )


def generate_referral_code(user_id: str, outfit_id: Optional[str]) -> str:
    raw = f"{user_id}:{outfit_id or ''}:{secrets.token_hex(8)}"
    return "CF-" + hashlib.sha256(raw.encode()).hexdigest()[:10].upper()


def create_referral_row(
    db: Session,
    referrer_id: str,
    outfit_id: Optional[str],
    post_id: Optional[str],
) -> Referral:
    code = generate_referral_code(str(referrer_id), outfit_id)
    while db.query(Referral).filter(Referral.referral_code == code).first():
        code = generate_referral_code(str(referrer_id), outfit_id + secrets.token_hex(4))

    ref = Referral(
        referrer_user_id=referrer_id,
        referral_code=code,
        outfit_id=outfit_id,
        post_id=post_id,
        status="pending",
        reward_credits=0,
    )
    db.add(ref)
    db.flush()
    return ref


def claim_referral(db: Session, referee_id: str, code: str) -> Tuple[str, int, int]:
    ref = db.query(Referral).filter(Referral.referral_code == code.strip()).first()
    if not ref:
        return "invalid", 0, 0
    if ref.referee_user_id and str(ref.referee_user_id) != str(referee_id):
        return "already_used", 0, 0
    if str(ref.referrer_user_id) == str(referee_id):
        return "self_referral", 0, 0

    ref.referee_user_id = referee_id
    ref.status = "rewarded"
    ref.reward_credits = REFERRAL_REWARD_EACH * 2
    ref.completed_at = _now()

    db.add(
        GrowthEvent(
            user_id=referee_id,
            event_type="referral_completed",
            payload={"referrer": str(ref.referrer_user_id), "code": code},
            severity="info",
        )
    )
    return "ok", REFERRAL_REWARD_EACH, REFERRAL_REWARD_EACH


def build_notify_preview(db: Session, user: User) -> Dict[str, Any]:
    """AI marketing automation — preview only (no external send)."""
    score = update_engagement_heuristic(db, user)
    suppressed = score.churn_risk > 0.72

    banners: List[dict] = []
    push: List[dict] = []
    emails: List[dict] = []

    if not suppressed:
        if score.purchase_likelihood > 0.55:
            push.append(
                {
                    "id": "push_price_drop_style",
                    "title": "Your style picks are trending",
                    "body": "Open CONFIT to see pieces matched to your profile.",
                    "channel": "push",
                    "score": round(score.purchase_likelihood, 3),
                }
            )
        if score.churn_risk > 0.45:
            emails.append(
                {
                    "id": "email_we_miss_you",
                    "subject": "A fresh look based on your last session",
                    "template": "reactivation_heuristic",
                    "delay_hours": 24,
                }
            )
        banners.append(
            {
                "id": "banner_season_shift",
                "text": "New season — refresh your wardrobe graph in one tap.",
                "placement": "home_top",
            }
        )

    return {
        "push": push[:3],
        "email": emails[:2],
        "banners": banners[:2],
        "suppressed_due_to_churn_risk": suppressed,
    }


def growth_analytics_summary(db: Session) -> Dict[str, Any]:
    """Aggregate KPIs + bottleneck hints for the Growth Analytics Brain."""
    total_posts = int(db.query(func.count(SocialPost.id)).scalar() or 0)

    total_shares = int(
        db.query(func.coalesce(func.sum(SocialPostStats.share_count), 0)).scalar() or 0
    )
    total_views = int(
        db.query(func.coalesce(func.sum(SocialPostStats.view_count), 0)).scalar() or 0
    )

    referrals_done = int(
        db.query(func.count(Referral.id)).filter(Referral.status == "rewarded").scalar() or 0
    )
    referrals_pending = int(
        db.query(func.count(Referral.id)).filter(Referral.status == "pending").scalar() or 0
    )

    share_rate = (total_shares / max(1, total_views)) if total_views else 0.0
    viral_k = min(3.0, referrals_done / max(1, referrals_pending + referrals_done) * 2.5)

    conv = min(1.0, referrals_done / max(1, total_posts) * 4.0)
    # Proxy: shares per post as stand-in for try-on / rich-post engagement
    try_on_rate = min(1.0, (total_shares / max(1, total_posts)) * 3.0)

    bottlenecks: List[str] = []
    opts: List[str] = []
    if share_rate < 0.02:
        bottlenecks.append("share_rate_low")
        opts.append("Surface one-tap share after try-on success; test referral CTA timing.")
    if try_on_rate < 0.35:
        bottlenecks.append("try_on_attach_rate_low")
        opts.append("Attach try-on preview to more outfit posts automatically.")
    if viral_k < 0.8:
        bottlenecks.append("referral_conversion_soft")
        opts.append("Reward both sides on first wishlist save, not only signup.")

    return {
        "viral_coefficient_estimate": round(float(viral_k), 4),
        "outfit_share_rate": round(float(share_rate), 4),
        "conversion_per_outfit": round(float(conv), 4),
        "try_on_engagement_rate": round(float(try_on_rate), 4),
        "bottlenecks": bottlenecks,
        "optimizations": opts,
    }


def match_influencers(db: Session, user: User, limit: int = 8) -> List[dict]:
    """Influencer AI matching — style DNA, engagement overlap, budget alignment."""
    u_tags = _user_tag_set(user)
    budget = user.budget_range if isinstance(user.budget_range, dict) else {}
    u_max = float(budget.get("max") or budget.get("monthly_max") or 500)

    rows = (
        db.query(Influencer)
        .filter(Influencer.status.in_(("approved", "pending")))
        .order_by(Influencer.total_engagement.desc())
        .limit(80)
        .all()
    )

    scored: List[Tuple[float, Influencer]] = []
    for inf in rows:
        stags = {_normalize_tag(x) for x in (inf.style_tags or [])}
        dna = jaccard(u_tags, stags) if u_tags else 0.4
        eng = min(1.0, math.log1p(float(inf.total_engagement or 0)) / 18.0)
        br = float(inf.default_commission_rate or 0.1)  # type: ignore[arg-type]
        budget_align = 1.0 - min(1.0, abs(u_max - 500) / 1500.0) * (0.5 + br)
        composite = 0.5 * dna + 0.35 * eng + 0.15 * budget_align
        scored.append((composite, inf))

    scored.sort(key=lambda x: x[0], reverse=True)
    out: List[dict] = []
    for composite, inf in scored[:limit]:
        stags = {_normalize_tag(x) for x in (inf.style_tags or [])}
        dna = jaccard(u_tags, stags) if u_tags else 0.4
        eng = min(1.0, math.log1p(float(inf.total_engagement or 0)) / 18.0)
        br = float(inf.default_commission_rate or 0.1)  # type: ignore[arg-type]
        budget_align = 1.0 - min(1.0, abs(u_max - 500) / 1500.0) * (0.5 + br)
        out.append(
            {
                "influencer_id": str(inf.id),
                "display_name": inf.display_name,
                "avatar_url": inf.avatar_url,
                "style_dna_score": round(dna, 4),
                "engagement_overlap": round(eng, 4),
                "budget_alignment": round(budget_align, 4),
                "composite_score": round(composite, 4),
            }
        )
    return out


def graph_edges_for_user(db: Session, user_id: str, limit: int = 40) -> List[UserGraphEdge]:
    return (
        db.query(UserGraphEdge)
        .filter(UserGraphEdge.user_id == user_id)
        .order_by(UserGraphEdge.weight.desc())
        .limit(limit)
        .all()
    )
