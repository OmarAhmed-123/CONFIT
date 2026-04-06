"""
CONFIT Fashion OS — Intelligence layer above catalog/wardrobe.
Orchestrates Style DNA, behavior, outfits, closet insights, daily automation, feedback RL.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import desc
from sqlalchemy.orm import Session

from database.models import Product, WardrobeItem
from models.style_dna_models import (
    InteractionLog,
    RecommendationScore,
    StyleDNAProfile,
    StyleSignal,
)
from models.wardrobe_analytics_models import OutfitHistory
from services.style_dna_security import StyleDNAEncryption

logger = logging.getLogger(__name__)

_DEFAULT_IDENTITY_DNA: Dict[str, Any] = {
    "elegance_score": 0.5,
    "minimalism_score": 0.5,
    "boldness_score": 0.5,
    "color_affinity": {"warm": 0.33, "cool": 0.33, "neutral": 0.34},
    "fit_preference": "regular",
    "budget_behavior": {"research_weight": 0.5, "splurge_tendency": 0.5},
    "seasonal_patterns": {"spring": 0.25, "summer": 0.25, "fall": 0.25, "winter": 0.25},
}

_INTEREST_ALPHA = 0.12
_RL_POS = 0.03
_RL_NEG = 0.045


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _merge_identity_dna(raw: Optional[dict]) -> Dict[str, Any]:
    out = dict(_DEFAULT_IDENTITY_DNA)
    if raw:
        for k, v in raw.items():
            if isinstance(v, dict) and k in out and isinstance(out[k], dict):
                merged = dict(out[k])
                merged.update(v)
                out[k] = merged
            else:
                out[k] = v
    return out


def _get_or_create_profile(db: Session, user_id: str) -> StyleDNAProfile:
    p = db.query(StyleDNAProfile).filter(StyleDNAProfile.user_id == user_id).first()
    if p:
        if not p.identity_dna:
            p.identity_dna = _merge_identity_dna(None)
        else:
            p.identity_dna = _merge_identity_dna(p.identity_dna)
        return p
    p = StyleDNAProfile(
        user_id=user_id,
        identity_dna=_merge_identity_dna(None),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _public_identity_dna(profile: StyleDNAProfile) -> Dict[str, Any]:
    """Never expose embeddings or encrypted blobs."""
    d = _merge_identity_dna(profile.identity_dna)
    d.pop("style_vector", None)
    d.pop("embedding", None)
    return d


def _reinforce_dna(
    dna: Dict[str, Any],
    signal_type: str,
    positive: bool,
    magnitude: float = 1.0,
) -> Dict[str, Any]:
    """Feedback learning loop — adjust interpretable scores."""
    delta = _RL_POS * magnitude if positive else -_RL_NEG * magnitude
    st = (signal_type or "").lower()
    if "like" in st or "purchase" in st or "save" in st:
        dna["elegance_score"] = _clamp01(float(dna.get("elegance_score", 0.5)) + delta * 0.5)
        dna["boldness_score"] = _clamp01(float(dna.get("boldness_score", 0.5)) + delta * 0.3)
    if "skip" in st or "negative" in st or "dislike" in st:
        dna["boldness_score"] = _clamp01(float(dna.get("boldness_score", 0.5)) - abs(delta) * 0.4)
    if "minimal" in st or "clean" in st:
        dna["minimalism_score"] = _clamp01(float(dna.get("minimalism_score", 0.5)) + delta)
    if "scroll" in st or "hover" in st:
        dna["boldness_score"] = _clamp01(float(dna.get("boldness_score", 0.5)) + delta * 0.15)
    return dna


def _color_bucket(color: Optional[str]) -> str:
    if not color:
        return "neutral"
    c = color.lower()
    warm = ("red", "orange", "yellow", "coral", "gold", "amber", "brown", "tan", "beige")
    cool = ("blue", "navy", "green", "teal", "purple", "lavender", "pink", "silver")
    if any(w in c for w in warm):
        return "warm"
    if any(w in c for w in cool):
        return "cool"
    return "neutral"


def _score_product_for_dna(
    product: Product,
    identity: Dict[str, Any],
    profile: StyleDNAProfile,
    interest_by_id: Dict[str, float],
) -> Tuple[float, Dict[str, float]]:
    breakdown: Dict[str, float] = {}
    score = 0.55
    bucket = _color_bucket(product.color)
    aff = identity.get("color_affinity") or {}
    breakdown["color_match"] = float(aff.get(bucket, 0.33))
    score += 0.2 * breakdown["color_match"]

    tags = product.tags or []
    tag_s = " ".join(str(t).lower() for t in tags) if isinstance(tags, list) else ""
    name_desc = f"{product.name} {product.description or ''} {tag_s}".lower()
    if float(identity.get("minimalism_score", 0.5)) > 0.6 and any(
        x in name_desc for x in ("minimal", "clean", "classic", "basic")
    ):
        breakdown["minimalism"] = 0.85
        score += 0.1
    elif float(identity.get("boldness_score", 0.5)) > 0.6 and any(
        x in name_desc for x in ("bold", "statement", "print", "graphic")
    ):
        breakdown["boldness"] = 0.82
        score += 0.1

    if profile.primary_style and profile.primary_style.value in name_desc:
        breakdown["style_archetype"] = 0.9
        score += 0.08

    pid = str(product.id)
    if pid in interest_by_id:
        breakdown["interest"] = interest_by_id[pid]
        score += 0.15 * interest_by_id[pid]

    br = identity.get("budget_behavior") or {}
    splurge = float(br.get("splurge_tendency", 0.5))
    price = float(product.price or 0)
    if price < 80:
        breakdown["price_fit"] = 1.0 - splurge * 0.3
    elif price < 200:
        breakdown["price_fit"] = 0.75
    else:
        breakdown["price_fit"] = 0.55 + splurge * 0.35
    score += 0.08 * float(breakdown["price_fit"])

    score = _clamp01(score)
    return score, breakdown


def _outfit_hash(item_ids: Sequence[str]) -> str:
    s = "|".join(sorted(str(x) for x in item_ids))
    return hashlib.sha256(s.encode()).hexdigest()[:20]


def _recent_ai_hashes(db: Session, user_id: str, limit: int = 80) -> set:
    rows = (
        db.query(OutfitHistory)
        .filter(
            OutfitHistory.user_id == user_id,
            OutfitHistory.ai_generated.is_(True),
        )
        .order_by(desc(OutfitHistory.worn_at))
        .limit(limit)
        .all()
    )
    out: set = set()
    for r in rows:
        ids = r.item_ids or []
        if isinstance(ids, list) and ids:
            out.add(_outfit_hash(ids))
    return out


class FashionOSEngine:
    """Sync engine using SQLAlchemy Session (FastAPI threadpool)."""

    def __init__(self, db: Session):
        self.db = db
        self._enc = StyleDNAEncryption()

    def get_identity_dna(self, user_id: str) -> Dict[str, Any]:
        profile = _get_or_create_profile(self.db, user_id)
        return _public_identity_dna(profile)

    # --- Module 1 & 7: Style DNA + feedback ---

    def update_style(
        self,
        user_id: str,
        payload: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        profile = _get_or_create_profile(self.db, user_id)
        dna = _merge_identity_dna(profile.identity_dna)

        if payload:
            signals = payload.get("signals") or {}
            explicit = payload.get("identity_dna_patch") or {}
            for k, v in explicit.items():
                if k in dna and isinstance(dna[k], dict) and isinstance(v, dict):
                    dna[k].update(v)
                else:
                    dna[k] = v

            for key, delta in signals.items():
                if key in dna and isinstance(dna[key], (int, float)):
                    dna[key] = _clamp01(float(dna[key]) + float(delta))

            fb = payload.get("feedback")
            if isinstance(fb, dict):
                dna = _reinforce_dna(
                    dna,
                    str(fb.get("type", "")),
                    bool(fb.get("positive", True)),
                    float(fb.get("magnitude", 1.0)),
                )

        profile.identity_dna = dna
        profile.updated_at = datetime.now(timezone.utc)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)

        return {
            "identity_dna": _public_identity_dna(profile),
            "profile_version": profile.profile_version,
            "updated_at": profile.updated_at.isoformat(),
        }

    # --- Module 3: behavior ---

    def log_behavior(
        self,
        user_id: str,
        payload: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not payload:
            return {"ok": True, "interest_score": None}

        profile = _get_or_create_profile(self.db, user_id)
        event_type = str(payload.get("event_type", "interaction"))
        entity_type = payload.get("entity_type")
        entity_id = payload.get("entity_id")
        session_id = payload.get("session_id")

        sensitive = {
            "hover_ms": payload.get("hover_ms"),
            "scroll_velocity": payload.get("scroll_velocity"),
            "view_repetition": payload.get("view_repetition"),
            "try_on_attempts": payload.get("try_on_attempts"),
            "session_duration_sec": payload.get("session_duration_sec"),
        }
        metrics_public = {k: v for k, v in sensitive.items() if v is not None}

        enc_blob = None
        try:
            enc_blob = self._enc.encrypt(sensitive)
        except Exception as e:
            logger.warning("behavior encrypt skipped: %s", e)

        # interest_score(entity)
        interest_score: Optional[float] = None
        if entity_id:
            raw_signal = 0.0
            if sensitive.get("hover_ms"):
                raw_signal += min(1.0, float(sensitive["hover_ms"]) / 8000.0)
            if sensitive.get("view_repetition"):
                raw_signal += min(1.0, float(sensitive["view_repetition"]) * 0.15)
            if sensitive.get("try_on_attempts"):
                raw_signal += min(1.0, float(sensitive["try_on_attempts"]) * 0.25)
            if event_type in ("like", "purchase", "save"):
                raw_signal += 0.5
            if event_type in ("skip", "dislike"):
                raw_signal -= 0.4

            raw_signal = _clamp01(0.5 + raw_signal * 0.5)
            existing = (
                self.db.query(RecommendationScore)
                .filter(
                    RecommendationScore.user_id == user_id,
                    RecommendationScore.entity_type == "item_interest",
                    RecommendationScore.entity_id == str(entity_id),
                )
                .first()
            )
            if existing:
                old = float(existing.score)
                interest_score = _clamp01(old * (1 - _INTEREST_ALPHA) + raw_signal * _INTEREST_ALPHA)
                existing.score = Decimal(str(interest_score))
                existing.score_breakdown = {"prev": old, "signal": raw_signal, "event": event_type}
                existing.computed_at = datetime.now(timezone.utc)
            else:
                interest_score = raw_signal
                self.db.add(
                    RecommendationScore(
                        user_id=user_id,
                        entity_type="item_interest",
                        entity_id=str(entity_id),
                        score=Decimal(str(interest_score)),
                        score_breakdown={"signal": raw_signal, "event": event_type},
                        computed_at=datetime.now(timezone.utc),
                    )
                )

            # Implicit preference retraining
            dna = _merge_identity_dna(profile.identity_dna)
            if raw_signal > 0.62:
                dna = _reinforce_dna(dna, event_type, True, magnitude=0.7)
            elif raw_signal < 0.35:
                dna = _reinforce_dna(dna, event_type, False, magnitude=0.6)
            profile.identity_dna = dna

        log = InteractionLog(
            user_id=user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            metrics=metrics_public,
            payload_encrypted=enc_blob,
            interest_delta=Decimal(str((interest_score or 0.5) - 0.5)),
            session_id=session_id,
        )
        self.db.add(log)

        sig = StyleSignal(
            user_id=user_id,
            signal_type=event_type,
            signal_category="behavior",
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            signal_data={"metrics": metrics_public},
            base_weight=Decimal("0.5"),
            computed_weight=Decimal("0.5"),
        )
        self.db.add(sig)
        self.db.commit()

        return {
            "ok": True,
            "interest_score": interest_score,
            "event_type": event_type,
        }

    # --- Module 4 & caching ---

    def recommend(
        self,
        user_id: str,
        payload: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        profile = _get_or_create_profile(self.db, user_id)
        identity = _public_identity_dna(profile)
        limit = int((payload or {}).get("limit") or 12)

        interests = (
            self.db.query(RecommendationScore)
            .filter(
                RecommendationScore.user_id == user_id,
                RecommendationScore.entity_type == "item_interest",
            )
            .all()
        )
        interest_map = {r.entity_id: float(r.score) for r in interests}

        q = self.db.query(Product).filter(Product.is_active.is_(True))
        products = q.limit(200).all()
        ranked: List[Dict[str, Any]] = []
        for p in products:
            s, br = _score_product_for_dna(p, identity, profile, interest_map)
            ranked.append(
                {
                    "id": str(p.id),
                    "name": p.name,
                    "category": p.category,
                    "color": p.color,
                    "price": p.price,
                    "image_url": p.image_url,
                    "brand_id": p.brand_id,
                    "score": round(s, 4),
                    "score_breakdown": br,
                }
            )
        ranked.sort(key=lambda x: x["score"], reverse=True)
        top = ranked[:limit]

        for row in top:
            rs = (
                self.db.query(RecommendationScore)
                .filter(
                    RecommendationScore.user_id == user_id,
                    RecommendationScore.entity_type == "product",
                    RecommendationScore.entity_id == row["id"],
                )
                .first()
            )
            if not rs:
                rs = RecommendationScore(
                    user_id=user_id,
                    entity_type="product",
                    entity_id=row["id"],
                    score=Decimal(str(row["score"])),
                    score_breakdown=row["score_breakdown"],
                    computed_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=6),
                )
                self.db.add(rs)
            else:
                rs.score = Decimal(str(row["score"]))
                rs.score_breakdown = row["score_breakdown"]
                rs.computed_at = datetime.now(timezone.utc)
        self.db.commit()

        ms = (time.perf_counter() - t0) * 1000.0
        return {
            "items": top,
            "latency_ms": round(ms, 2),
            "identity_dna": identity,
        }

    # --- Module 4 & 5: outfits ---

    def generate_outfits(
        self,
        user_id: str,
        payload: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        profile = _get_or_create_profile(self.db, user_id)
        identity = _public_identity_dna(profile)
        p = payload or {}
        occasion = str(p.get("occasion") or "everyday")
        budget_max = p.get("budget_max")
        prefer_closet = bool(p.get("prefer_closet", True))
        count = min(int(p.get("count") or 4), 8)

        banned = _recent_ai_hashes(self.db, user_id)

        wardrobe = (
            self.db.query(WardrobeItem)
            .filter(WardrobeItem.owner_user_id == user_id)
            .all()
        )
        by_cat: Dict[str, List[WardrobeItem]] = {}
        for w in wardrobe:
            c = (w.category or "other").lower()
            by_cat.setdefault(c, []).append(w)

        def pick_items() -> List[Dict[str, Any]]:
            tops = by_cat.get("tops", []) + by_cat.get("shirt", []) + by_cat.get("t-shirt", [])
            bottoms = by_cat.get("bottoms", []) + by_cat.get("pants", []) + by_cat.get("jeans", [])
            shoes = by_cat.get("shoes", [])
            dresses = by_cat.get("dresses", []) + by_cat.get("dress", [])

            chosen: List[WardrobeItem] = []
            if dresses and random.random() > 0.35:
                chosen.append(random.choice(dresses))
            else:
                if tops:
                    chosen.append(random.choice(tops))
                if bottoms:
                    chosen.append(random.choice(bottoms))
            if shoes:
                chosen.append(random.choice(shoes))

            if not chosen and wardrobe:
                chosen = random.sample(wardrobe, min(3, len(wardrobe)))

            item_ids = [x.id for x in chosen]
            return [
                {
                    "id": x.id,
                    "name": x.name,
                    "category": x.category,
                    "color": x.color,
                    "image_url": x.image_url,
                }
                for x in chosen
            ], item_ids

        outfits: List[Dict[str, Any]] = []
        attempts = 0
        while len(outfits) < count and attempts < count * 6:
            attempts += 1
            if prefer_closet and wardrobe:
                items, ids = pick_items()
                source = "closet"
            else:
                # fallback: synthetic combo from catalog
                products = (
                    self.db.query(Product)
                    .filter(Product.is_active.is_(True))
                    .limit(40)
                    .all()
                )
                if len(products) < 2:
                    break
                sample = random.sample(products, min(3, len(products)))
                ids = [str(x.id) for x in sample]
                items = [
                    {
                        "id": str(x.id),
                        "name": x.name,
                        "category": x.category,
                        "color": x.color,
                        "image_url": x.image_url,
                    }
                    for x in sample
                ]
                source = "catalog"
            oh = _outfit_hash(ids)
            if oh in banned:
                continue
            banned.add(oh)

            harmony = 0.75
            colors = [_color_bucket(i.get("color")) for i in items]
            if len(set(colors)) <= 2:
                harmony += 0.15

            total_price = 0.0
            for i in items:
                wi = self.db.query(WardrobeItem).filter(WardrobeItem.id == i["id"]).first()
                if wi and wi.price:
                    total_price += float(wi.price)

            if budget_max is not None and total_price and total_price > float(budget_max):
                continue

            outfits.append(
                {
                    "items": items,
                    "occasion": occasion,
                    "source": source,
                    "color_harmony_score": round(harmony, 3),
                    "style_alignment": round(
                        float(identity.get("elegance_score", 0.5)) * 0.4
                        + float(identity.get("minimalism_score", 0.5)) * 0.3
                        + float(identity.get("boldness_score", 0.5)) * 0.3,
                        3,
                    ),
                    "signature": oh,
                }
            )

        return {
            "outfits": outfits,
            "identity_dna": identity,
            "smart_closet": {
                "wardrobe_items": len(wardrobe),
                "prefer_owned": prefer_closet,
            },
        }

    # --- Module 5: closet intelligence ---

    def closet_insights(self, user_id: str) -> Dict[str, Any]:
        wardrobe = (
            self.db.query(WardrobeItem)
            .filter(WardrobeItem.owner_user_id == user_id)
            .all()
        )
        id_counts: Dict[str, int] = {}
        hist = (
            self.db.query(OutfitHistory)
            .filter(OutfitHistory.user_id == user_id)
            .order_by(desc(OutfitHistory.worn_at))
            .limit(200)
            .all()
        )
        for h in hist:
            for iid in h.item_ids or []:
                id_counts[str(iid)] = id_counts.get(str(iid), 0) + 1

        overused = []
        unused = []
        for w in wardrobe:
            c = id_counts.get(w.id, 0)
            if c >= 8:
                overused.append({"id": w.id, "name": w.name, "wear_count_proxy": c})
            if c == 0:
                unused.append({"id": w.id, "name": w.name, "category": w.category})

        essentials = ["tops", "bottoms", "shoes"]
        have = {((w.category or "").lower()) for w in wardrobe}
        missing = [e for e in essentials if not any(e in h for h in have)]

        return {
            "overused_items": overused[:15],
            "unused_items": unused[:30],
            "missing_essentials": missing,
            "sustainability_note": "Prioritizing owned pieces reduces waste and deepens your signature look.",
        }

    # --- Module 6: daily ---

    def daily_outfit(self, user_id: str) -> Dict[str, Any]:
        profile = _get_or_create_profile(self.db, user_id)
        identity = _public_identity_dna(profile)
        today = date.today()
        season = (
            "winter"
            if today.month in (12, 1, 2)
            else "spring"
            if today.month in (3, 4, 5)
            else "summer"
            if today.month in (6, 7, 8)
            else "fall"
        )
        sp = identity.get("seasonal_patterns") or {}
        season_weight = float(sp.get(season, 0.25))

        gen = self.generate_outfits(
            user_id,
            {"occasion": "everyday", "prefer_closet": True, "count": 1},
        )
        outfit = (gen.get("outfits") or [None])[0]
        return {
            "date": today.isoformat(),
            "season": season,
            "season_weight": round(season_weight, 3),
            "weather_placeholder": "Configure weather API for live conditions.",
            "calendar_placeholder": "Connect calendar for event-aware styling.",
            "today_outfit": outfit,
            "identity_dna": identity,
        }
