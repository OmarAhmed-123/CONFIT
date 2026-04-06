import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import SocialPost, SocialVote, StylistLookbook
from models.social_models import (
    SocialPostCreate,
    SocialPostResponse,
    SocialVoteRequest,
    LookbookCreate,
    LookbookResponse,
    SocialLookbookItem,
)
from utils.auth_deps import require_auth, optional_auth
from services.auth_service import UserProfile

router = APIRouter(prefix="/api/social", tags=["social"])


def _post_to_response(
    row: SocialPost,
    hot: int,
    cold: int,
    user_vote: Optional[str],
) -> SocialPostResponse:
    return SocialPostResponse(
        id=row.id,
        owner_user_id=row.user_id,
        image_url=row.image_urls[0] if row.image_urls else None,
        caption=row.caption,
        visibility=row.visibility,
        created_at=row.created_at,
        hot_count=hot,
        cold_count=cold,
        user_vote=user_vote,  # type: ignore
    )


@router.post("/posts", response_model=SocialPostResponse)
async def create_post(
    payload: SocialPostCreate,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    post_id = f"post-{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow()

    row = SocialPost(
        id=post_id,
        user_id=user.id,
        image_urls=[str(payload.image_url)],
        caption=payload.caption,
        visibility=payload.visibility,
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _post_to_response(row, hot=0, cold=0, user_vote=None)


@router.get("/feed", response_model=List[SocialPostResponse])
async def get_feed(
    db: Session = Depends(get_db),
    user: Optional[UserProfile] = Depends(optional_auth),
    visibility: Optional[str] = Query(default="public"),
    limit: int = Query(default=30, ge=1, le=100),
):
    q = db.query(SocialPost)
    if visibility in {"public", "link"}:
        q = q.filter(SocialPost.visibility == visibility)
    else:
        q = q.filter(SocialPost.visibility == "public")

    rows = q.order_by(SocialPost.created_at.desc()).limit(limit).all()

    responses: List[SocialPostResponse] = []
    for r in rows:
        votes = db.query(SocialVote).filter(SocialVote.post_id == r.id).all()
        hot = sum(1 for v in votes if v.value == "hot")
        cold = sum(1 for v in votes if v.value == "cold")
        uv = None
        if user:
            mine = next((v for v in votes if v.voter_user_id == user.id), None)
            uv = mine.value if mine else None
        responses.append(_post_to_response(r, hot=hot, cold=cold, user_vote=uv))
    return responses


@router.get("/posts/{post_id}", response_model=SocialPostResponse)
async def get_post(
    post_id: str,
    db: Session = Depends(get_db),
    user: Optional[UserProfile] = Depends(optional_auth),
):
    row = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    votes = db.query(SocialVote).filter(SocialVote.post_id == row.id).all()
    hot = sum(1 for v in votes if v.value == "hot")
    cold = sum(1 for v in votes if v.value == "cold")
    uv = None
    if user:
        mine = next((v for v in votes if v.voter_user_id == user.id), None)
        uv = mine.value if mine else None
    return _post_to_response(row, hot=hot, cold=cold, user_vote=uv)


@router.post("/posts/{post_id}/vote", response_model=SocialPostResponse)
async def vote(
    post_id: str,
    payload: SocialVoteRequest,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing = (
        db.query(SocialVote)
        .filter(SocialVote.post_id == post_id, SocialVote.voter_user_id == user.id)
        .first()
    )
    if existing:
        existing.value = payload.value
    else:
        vote_id = f"vote-{uuid.uuid4().hex[:12]}"
        db.add(
            SocialVote(
                id=vote_id,
                post_id=post_id,
                voter_user_id=user.id,
                value=payload.value,
                created_at=datetime.utcnow(),
            )
        )
    db.commit()

    votes = db.query(SocialVote).filter(SocialVote.post_id == post_id).all()
    hot = sum(1 for v in votes if v.value == "hot")
    cold = sum(1 for v in votes if v.value == "cold")
    mine = next((v for v in votes if v.voter_user_id == user.id), None)
    return _post_to_response(post, hot=hot, cold=cold, user_vote=(mine.value if mine else None))


# ── Lookbooks (stylist-as-a-service) ───────────────────────────────


@router.post("/lookbooks", response_model=LookbookResponse)
async def create_lookbook(
    payload: LookbookCreate,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    lb_id = f"lookbook-{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow()
    row = StylistLookbook(
        id=lb_id,
        stylist_user_id=user.id,
        title=payload.title,
        description=payload.description,
        items=[i.model_dump() for i in payload.items],
        commission_rate=payload.commission_rate,
        visibility=payload.visibility,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return LookbookResponse(
        id=row.id,
        stylist_user_id=row.stylist_user_id,
        title=row.title,
        description=row.description,
        items=[SocialLookbookItem(**i) for i in (row.items or [])],
        commission_rate=row.commission_rate,
        visibility=row.visibility,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/lookbooks", response_model=List[LookbookResponse])
async def list_lookbooks(
    db: Session = Depends(get_db),
    visibility: str = Query(default="public"),
    limit: int = Query(default=50, ge=1, le=200),
):
    q = db.query(StylistLookbook)
    if visibility in {"public", "private"}:
        q = q.filter(StylistLookbook.visibility == visibility)
    else:
        q = q.filter(StylistLookbook.visibility == "public")

    rows = q.order_by(StylistLookbook.created_at.desc()).limit(limit).all()
    out: List[LookbookResponse] = []
    for r in rows:
        out.append(
            LookbookResponse(
                id=r.id,
                stylist_user_id=r.stylist_user_id,
                title=r.title,
                description=r.description,
                items=[SocialLookbookItem(**i) for i in (r.items or [])],
                commission_rate=r.commission_rate,
                visibility=r.visibility,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )
    return out

