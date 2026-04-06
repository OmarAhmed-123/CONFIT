"""
CONFIT Backend — Experiments (A/B Testing) Router
===================================================
Lightweight event tracking endpoint for frontend A/B experiments.

This is intentionally minimal and safe for local dev:
- Stores events in-memory (process memory).
- Always returns 204 on success.
- Never blocks user flows on tracking failure (client-side should still treat it as best-effort).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/experiments", tags=["Experiments"])

logger = logging.getLogger(__name__)


@dataclass
class ExperimentEvent:
    experiment_id: str
    variant: str
    event: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    ts_ms: int = 0


_events: List[ExperimentEvent] = []


def _now_ms() -> int:
    return int(time.time() * 1000)


@router.post("/track", status_code=204)
async def track_experiment_event(payload: Dict[str, Any]) -> None:
    """
    Track an A/B experiment event.

    Expected JSON shape:
      {
        "experimentId": "hero-cta",
        "variant": "A",
        "event": "cta_click",
        "metadata": { ...optional }
      }
    """
    try:
        experiment_id: Optional[str] = payload.get("experimentId")  # type: ignore[assignment]
        variant: Optional[str] = payload.get("variant")  # type: ignore[assignment]
        event: Optional[str] = payload.get("event")  # type: ignore[assignment]
        metadata: Dict[str, Any] = payload.get("metadata") or {}  # type: ignore[assignment]

        if not experiment_id or not variant or not event:
            raise HTTPException(status_code=400, detail="Missing experimentId/variant/event")

        _events.append(
            ExperimentEvent(
                experiment_id=experiment_id,
                variant=variant,
                event=event,
                metadata=metadata,
                ts_ms=_now_ms(),
            )
        )

        # Keep memory bounded (simple ring-buffer behavior).
        if len(_events) > 10_000:
            del _events[:1_000]
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Experiment tracking failed (ignored): %s", e)
        # Still return 204 to avoid breaking UX.
        return None


@router.get("/events", status_code=200)
async def list_events(limit: int = 50) -> Dict[str, Any]:
    """Dev-only helper for inspection of tracked events."""
    safe_limit = max(1, min(500, limit))
    recent = _events[-safe_limit:]
    return {
        "count": len(_events),
        "recent": [
            {
                "experimentId": e.experiment_id,
                "variant": e.variant,
                "event": e.event,
                "metadata": e.metadata,
                "tsMs": e.ts_ms,
            }
            for e in recent
        ],
    }

