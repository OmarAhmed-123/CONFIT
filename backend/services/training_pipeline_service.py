from __future__ import annotations

import json
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from database.session import SessionLocal
from models.profile_models import UserBehaviorSignal
from database.models import Outfit as OutfitModel
from services.behavior_signal_service import BehaviorSignalService, SIGNAL_CONFIG


@dataclass(frozen=True)
class TrainingParams:
    lookback_days: int
    max_pairs: int
    apply_overrides: bool
    candidate_signal_types: Optional[List[str]] = None
    pairs_seed: int = 42


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_artifacts_dir() -> Path:
    # backend/services/... -> backend/
    backend_dir = Path(__file__).resolve().parents[1]
    return backend_dir / "data" / "training_jobs"


def _default_overrides_path() -> Path:
    backend_dir = Path(__file__).resolve().parents[1]
    return backend_dir / "data" / "training" / "signal_config_overrides.json"


class TrainingPipelineService:
    """
    Training pipeline scaffold:
    - Build preference dataset (chosen vs rejected outfits) from `user_behavior_signals`
    - Compute reward-calibrated `signal_config_overrides` (lightweight "fine-tune" stand-in)
    - Optionally apply overrides for immediate behavior learning

    Note: this repo doesn't include a full HF/TRL training runtime yet; this
    scaffolds the full data+job lifecycle safely.
    """

    def __init__(self) -> None:
        self._rng = random.Random(42)

    def run_job_sync(self, job_id: str, params: TrainingParams) -> Dict[str, Any]:
        artifacts_dir = _default_artifacts_dir() / job_id
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Always create a stable output schema so the frontend can display it.
        dataset_path = artifacts_dir / "train_preferences.jsonl"
        meta_path = artifacts_dir / "training_meta.json"
        overrides_path = artifacts_dir / "signal_config_overrides.json"

        lookback_cutoff = datetime.now(timezone.utc) - timedelta(days=params.lookback_days)

        with SessionLocal() as db:
            # 1) Build preference pairs: outfits accepted vs rejected.
            pairs, pair_stats = self._build_preference_pairs(
                db=db,
                cutoff=lookback_cutoff,
                max_pairs=params.max_pairs,
                pairs_seed=params.pairs_seed,
            )

            dataset_path.write_text("", encoding="utf-8")
            written = 0
            if pairs:
                outfit_ids = {p["chosen_outfit_id"] for p in pairs} | {p["rejected_outfit_id"] for p in pairs}
                outfit_map = self._fetch_outfits(db=db, outfit_ids=outfit_ids)
                with dataset_path.open("a", encoding="utf-8") as f:
                    for p in pairs:
                        chosen_outfit = outfit_map.get(p["chosen_outfit_id"])
                        rejected_outfit = outfit_map.get(p["rejected_outfit_id"])
                        context = {
                            "chosen_occasion": getattr(chosen_outfit, "occasion", None),
                            "rejected_occasion": getattr(rejected_outfit, "occasion", None),
                            "chosen_item_count": self._safe_len(getattr(chosen_outfit, "items", None)),
                            "rejected_item_count": self._safe_len(getattr(rejected_outfit, "items", None)),
                            "chosen_budget_limit": self._safe_float(getattr(chosen_outfit, "budget_limit", None)),
                            "rejected_budget_limit": self._safe_float(getattr(rejected_outfit, "budget_limit", None)),
                            "source": "user_behavior_signals",
                        }
                        sample = {
                            "user_id": p["user_id"],
                            "chosen_outfit_id": p["chosen_outfit_id"],
                            "rejected_outfit_id": p["rejected_outfit_id"],
                            "context": context,
                            "created_at": p["created_at"].isoformat(),
                        }
                        f.write(json.dumps(sample, ensure_ascii=False) + "\n")
                        written += 1

            # 2) Compute signal overrides from reward statistics.
            candidate_types = params.candidate_signal_types
            if not candidate_types:
                # Use the current signal config keys as candidates.
                candidate_types = list(SIGNAL_CONFIG.keys())

            overrides = self._compute_signal_weight_overrides(
                db=db,
                cutoff=lookback_cutoff,
                candidate_signal_types=candidate_types,
            )
            overrides_payload = {
                "updated_at": _iso_now(),
                "signal_config": overrides,
            }
            overrides_path.parent.mkdir(parents=True, exist_ok=True)
            overrides_path.write_text(json.dumps(overrides_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            applied = False
            if params.apply_overrides:
                default_path = _default_overrides_path()
                default_path.parent.mkdir(parents=True, exist_ok=True)
                default_path.write_text(
                    json.dumps(overrides_payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                applied = True

            meta_path.write_text(
                json.dumps(
                    {
                        "job_id": job_id,
                        "created_at": _iso_now(),
                        "params": {
                            "lookback_days": params.lookback_days,
                            "max_pairs": params.max_pairs,
                            "apply_overrides": params.apply_overrides,
                            "candidate_signal_types_count": len(candidate_types or []),
                        },
                        "dataset": {
                            "path": str(dataset_path),
                            "pairs_requested": params.max_pairs,
                            "pairs_written": written,
                            "pair_stats": pair_stats,
                        },
                        "overrides": {
                            "path": str(overrides_path),
                            "applied_to_runtime": applied,
                            "overrides_count": len(overrides),
                        },
                        "success": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

        return {
            "success": True,
            "artifacts": {
                "dataset_preferences": str(dataset_path),
                "training_meta": str(meta_path),
                "signal_config_overrides": str(overrides_path),
                "applied": params.apply_overrides,
            },
            "message": "Training job completed (dataset + reward calibration artifacts built).",
        }

    def _safe_len(self, items: Any) -> Optional[int]:
        if items is None:
            return None
        try:
            return len(items)
        except Exception:
            return None

    def _safe_float(self, v: Any) -> Optional[float]:
        if v is None:
            return None
        try:
            return float(v)
        except Exception:
            return None

    def _fetch_outfits(self, db: Session, outfit_ids: Set[str]) -> Dict[str, Any]:
        if not outfit_ids:
            return {}
        rows = db.query(OutfitModel).filter(OutfitModel.id.in_(list(outfit_ids))).all()
        return {str(r.id): r for r in rows}

    def _build_preference_pairs(
        self,
        db: Session,
        cutoff: datetime,
        max_pairs: int,
        pairs_seed: int,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Preference pairs from explicit outfit feedback signals:
        - `outfit_accepted`: chosen
        - `outfit_rejected`: rejected
        """
        accepted_types = {"outfit_accepted"}
        rejected_types = {"outfit_rejected"}

        signals = (
            db.query(UserBehaviorSignal)
            .filter(
                UserBehaviorSignal.entity_type == "outfit",
                UserBehaviorSignal.signal_type.in_(list(accepted_types | rejected_types)),
                UserBehaviorSignal.created_at >= cutoff,
            )
            .all()
        )

        # Latest label per (user_id, outfit_id).
        accepted_ts: Dict[Tuple[str, str], datetime] = {}
        rejected_ts: Dict[Tuple[str, str], datetime] = {}
        for s in signals:
            key = (str(s.user_id), str(s.entity_id))
            ts = s.created_at if isinstance(s.created_at, datetime) else cutoff
            if s.signal_type in accepted_types:
                prev = accepted_ts.get(key)
                if not prev or ts >= prev:
                    accepted_ts[key] = ts
            elif s.signal_type in rejected_types:
                prev = rejected_ts.get(key)
                if not prev or ts >= prev:
                    rejected_ts[key] = ts

        # Build user->accepted/rejected outfit ids (paired by user).
        user_accepted: Dict[str, List[Tuple[str, datetime]]] = defaultdict(list)
        user_rejected: Dict[str, List[Tuple[str, datetime]]] = defaultdict(list)

        for (user_id, outfit_id), ts in accepted_ts.items():
            user_accepted[user_id].append((outfit_id, ts))
        for (user_id, outfit_id), ts in rejected_ts.items():
            user_rejected[user_id].append((outfit_id, ts))

        # Sort by recency.
        for uid in user_accepted:
            user_accepted[uid].sort(key=lambda x: x[1], reverse=True)
        for uid in user_rejected:
            user_rejected[uid].sort(key=lambda x: x[1], reverse=True)

        pair_rng = random.Random(pairs_seed)
        pairs: List[Dict[str, Any]] = []
        for uid, accepted_list in user_accepted.items():
            rejected_list = user_rejected.get(uid) or []
            if not rejected_list:
                continue

            # Sample: for each accepted outfit, pair with a few rejected ones.
            # Keep dataset balanced and avoid explosion.
            max_accepted = min(len(accepted_list), max_pairs)  # safety
            accepted_sample = accepted_list[:max_accepted]

            # Use up to K rejected per accepted, but keep total bounded by max_pairs.
            rejected_cursor_max = min(len(rejected_list), 10)
            rejected_pool = rejected_list[:rejected_cursor_max]

            for chosen_outfit_id, chosen_ts in accepted_sample:
                if len(pairs) >= max_pairs:
                    break
                rejected_outfit_id, _rej_ts = pair_rng.choice(rejected_pool)

                pairs.append(
                    {
                        "user_id": uid,
                        "chosen_outfit_id": chosen_outfit_id,
                        "rejected_outfit_id": rejected_outfit_id,
                        "created_at": chosen_ts,
                    }
                )
                if len(pairs) >= max_pairs:
                    break

            if len(pairs) >= max_pairs:
                break

        pair_stats = {
            "users_with_accepted": len(user_accepted),
            "users_with_rejected": len(user_rejected),
            "pairs_generated": len(pairs),
            "accepted_signals": len(accepted_ts),
            "rejected_signals": len(rejected_ts),
        }

        return pairs, pair_stats

    def _compute_signal_weight_overrides(
        self,
        db: Session,
        cutoff: datetime,
        candidate_signal_types: List[str],
    ) -> Dict[str, Any]:
        """
        Reward calibration heuristic:
        - For each (user_id, outfit_id) labeled as accepted/rejected,
          measure whether a candidate signal type appears for that outfit.
        - Increase/decrease the candidate signal weight based on acceptance likelihood.
        """
        label_types = {"outfit_accepted", "outfit_rejected"}
        candidate_types = list(dict.fromkeys(candidate_signal_types))
        # Avoid trivial correlation: accepted/rejected are labels and should not be used as features.
        candidate_types = [
            t for t in candidate_types if t not in ["outfit_accepted", "outfit_rejected"]
        ]

        # Build labels per (user,outfit) based on latest accepted/rejected timestamp.
        label_signals = (
            db.query(UserBehaviorSignal)
            .filter(
                UserBehaviorSignal.entity_type == "outfit",
                UserBehaviorSignal.signal_type.in_(list(label_types)),
                UserBehaviorSignal.created_at >= cutoff,
            )
            .all()
        )
        accepted_ts: Dict[Tuple[str, str], datetime] = {}
        rejected_ts: Dict[Tuple[str, str], datetime] = {}
        for s in label_signals:
            key = (str(s.user_id), str(s.entity_id))
            ts = s.created_at if isinstance(s.created_at, datetime) else cutoff
            if s.signal_type == "outfit_accepted":
                prev = accepted_ts.get(key)
                if not prev or ts >= prev:
                    accepted_ts[key] = ts
            elif s.signal_type == "outfit_rejected":
                prev = rejected_ts.get(key)
                if not prev or ts >= prev:
                    rejected_ts[key] = ts

        label_examples: Dict[Tuple[str, str], int] = {}
        for key in set(accepted_ts.keys()) | set(rejected_ts.keys()):
            a_ts = accepted_ts.get(key)
            r_ts = rejected_ts.get(key)
            if a_ts and r_ts:
                label_examples[key] = 1 if a_ts >= r_ts else -1
            elif a_ts:
                label_examples[key] = 1
            else:
                label_examples[key] = -1

        if not label_examples:
            # Nothing to learn from, keep default config.
            return {k: v for k, v in SIGNAL_CONFIG.items()}

        pos_examples = sum(1 for v in label_examples.values() if v == 1)
        neg_examples = sum(1 for v in label_examples.values() if v == -1)

        # Presence of candidate signals per labeled example.
        presence: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
        if candidate_types:
            signals = (
                db.query(UserBehaviorSignal)
                .filter(
                    UserBehaviorSignal.entity_type == "outfit",
                    UserBehaviorSignal.signal_type.in_(list(set(candidate_types + list(label_types)))),
                    UserBehaviorSignal.created_at >= cutoff,
                )
                .all()
            )
            for s in signals:
                example_key = (str(s.user_id), str(s.entity_id))
                if example_key not in label_examples:
                    continue
                if s.signal_type in candidate_types:
                    presence[example_key].add(str(s.signal_type))

        overrides: Dict[str, Any] = {}
        for stype in candidate_types:
            base_cfg = SIGNAL_CONFIG.get(stype) or {"weight": 0.1, "decay_days": 30}
            base_weight = float(base_cfg.get("weight", 0.1))
            decay_days = base_cfg.get("decay_days", 30)

            pos_with = 0
            neg_with = 0
            for example_key, label in label_examples.items():
                has = stype in presence.get(example_key, set())
                if not has:
                    continue
                if label == 1:
                    pos_with += 1
                else:
                    neg_with += 1

            denom = pos_with + neg_with
            p = (pos_with / denom) if denom > 0 else 0.5

            # Map p in [0,1] to multiplier in [0.5,1.5].
            multiplier = 0.5 + p
            new_weight = _clamp(base_weight * multiplier, -2.0, 2.0)

            overrides[stype] = {
                "weight": new_weight,
                "decay_days": decay_days,
            }

        # Always keep explicit feedback signals stable.
        overrides["outfit_accepted"] = {"weight": 0.8, "decay_days": 60}
        overrides["outfit_rejected"] = {"weight": -0.6, "decay_days": 60}

        return overrides

