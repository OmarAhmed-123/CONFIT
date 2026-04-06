"""
Notification ML Retraining Scheduler
===================================
Runs weekly/on-demand retraining by calling internal ML API endpoints and
captures lightweight status/accuracy snapshots for observability.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    HAS_APSCHEDULER = True
except Exception:  # pragma: no cover
    HAS_APSCHEDULER = False

_scheduler: Optional["BackgroundScheduler"] = None


def _is_enabled() -> bool:
    return os.getenv("NOTIFICATION_ML_RETRAIN_ENABLED", "true").strip().lower() in ("1", "true", "yes")


def _base_url() -> str:
    return os.getenv("NOTIFICATION_ML_INTERNAL_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _snapshot_path() -> Path:
    return Path(os.getenv("NOTIFICATION_ML_SNAPSHOT_PATH", "backend/storage/notification_ml_accuracy_snapshots.jsonl"))


def _schedule() -> Dict[str, str]:
    return {
        "day_of_week": os.getenv("NOTIFICATION_ML_RETRAIN_DAY_OF_WEEK", "sun"),
        "hour": os.getenv("NOTIFICATION_ML_RETRAIN_HOUR_UTC", "03"),
        "minute": os.getenv("NOTIFICATION_ML_RETRAIN_MINUTE_UTC", "00"),
    }


def _append_snapshot(payload: Dict[str, Any]) -> None:
    path = _snapshot_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        import json
        f.write(json.dumps(payload) + "\n")


def _safe_get_json(url: str) -> Dict[str, Any]:
    if requests is None:
        return {"error": "requests_not_installed"}
    try:
        resp = requests.get(url, timeout=10)
        return {"status_code": resp.status_code, "json": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}}
    except Exception as exc:
        return {"error": str(exc)}


def run_notification_ml_retrain_job() -> None:
    """
    Executes one retraining cycle by calling:
      - POST /ml/train
      - GET /ml/status
      - GET /ml/accuracy?days=30
    and appending a snapshot to local JSONL for auditability.
    """
    ts = datetime.now(timezone.utc).isoformat()
    base = _base_url()
    logger.info("Notification ML retrain job started at %s", ts)

    result: Dict[str, Any] = {"timestamp_utc": ts, "base_url": base}

    if requests is None:
        result["retrain"] = {"error": "requests_not_installed"}
        _append_snapshot(result)
        logger.warning("Notification ML retrain skipped: requests not installed")
        return

    try:
        train_resp = requests.post(f"{base}/ml/train", json={}, timeout=120)
        result["retrain"] = {
            "status_code": train_resp.status_code,
            "ok": train_resp.ok,
            "body": train_resp.json() if train_resp.headers.get("content-type", "").startswith("application/json") else {},
        }
    except Exception as exc:
        result["retrain"] = {"error": str(exc)}

    result["status"] = _safe_get_json(f"{base}/ml/status")
    result["accuracy_30d"] = _safe_get_json(f"{base}/ml/accuracy?days=30")
    _append_snapshot(result)

    logger.info("Notification ML retrain job finished")


def start_notification_ml_scheduler() -> Optional["BackgroundScheduler"]:
    global _scheduler
    if not HAS_APSCHEDULER:
        logger.warning("APScheduler not installed — notification ML scheduler disabled")
        return None
    if not _is_enabled():
        logger.info("Notification ML scheduler disabled by env")
        return None

    if _scheduler is None:
        _scheduler = BackgroundScheduler(daemon=True, timezone="UTC")
    if _scheduler.running:
        return _scheduler

    sched = _schedule()
    _scheduler.add_job(
        id="notification_ml_weekly_retrain",
        func=run_notification_ml_retrain_job,
        trigger=CronTrigger(
            day_of_week=sched["day_of_week"],
            hour=sched["hour"],
            minute=sched["minute"],
        ),
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info(
        "Notification ML scheduler started (UTC %s %s:%s)",
        sched["day_of_week"],
        sched["hour"],
        sched["minute"],
    )
    return _scheduler


def stop_notification_ml_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Notification ML scheduler stopped")
