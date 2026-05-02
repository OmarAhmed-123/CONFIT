"""
CONFIT Backend — Prometheus Metrics Endpoint
=============================================
Serves /api/metrics behind INTERNAL_API_KEY auth.
Uses prometheus-fastapi-instrumentator for default metrics plus custom business metrics.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from starlette.responses import Response

from core.observability.prometheus_metrics import get_metrics_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/metrics", tags=["System"])


async def _require_internal_api_key(request: Request):
    token = request.headers.get("x-internal-api-key", "")
    expected = os.getenv("INTERNAL_API_KEY", "").strip()
    env = os.getenv("ENVIRONMENT", "development").lower()

    # In dev/staging, allow if no key is configured
    if not expected:
        if env in ("development", "dev", "staging", "stage", "test"):
            return
        raise HTTPException(status_code=403, detail="INTERNAL_API_KEY not configured")

    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid internal API key")


@router.get("", dependencies=[Depends(_require_internal_api_key)])
async def metrics_endpoint():
    """Prometheus metrics endpoint — protected by INTERNAL_API_KEY."""
    return Response(content=get_metrics_text(), media_type="text/plain; charset=utf-8")
