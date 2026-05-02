from __future__ import annotations

from typing import Any, Dict, Optional
import logging
import os
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from services.tryon_runtime import TryOnRuntimeManager

router = APIRouter(prefix="/api/tryon", tags=["Try-On Runtime"])
logger = logging.getLogger(__name__)


class TryOnRuntimeRequest(BaseModel):
    userImageBase64: str = Field(..., min_length=100)
    garmentImageUrl: str = Field(..., min_length=5)
    garmentName: str = Field(default="garment", max_length=200)
    garmentCategory: Optional[str] = None


@router.get("/capabilities")
async def get_tryon_capabilities() -> Dict[str, Any]:
    manager = TryOnRuntimeManager.get_instance()
    return {"success": True, **manager.get_capabilities()}


@router.post("")
@router.post("/")
async def tryon_preview_legacy(payload: TryOnRuntimeRequest) -> Dict[str, Any]:
    """Compatibility endpoint for older frontend hooks that post to /api/tryon."""
    return await tryon_live_preview(payload)


@router.post("/preview/live")
async def tryon_live_preview(payload: TryOnRuntimeRequest) -> Dict[str, Any]:
    request_id = str(uuid.uuid4())
    t0 = time.time()
    manager = TryOnRuntimeManager.get_instance()
    result = await manager.generate_preview(
        user_image_base64=payload.userImageBase64,
        garment_image_url=payload.garmentImageUrl,
        garment_name=payload.garmentName,
        garment_category=payload.garmentCategory,
    )
    if not result.get("success"):
        logger.warning(
            "tryon_preview_failed request_id=%s garment=%s failure=%s",
            request_id,
            payload.garmentName,
            result.get("failure_kind") or "PREVIEW_FAILED",
        )
        code = result.get("failure_kind") or "PREVIEW_FAILED"
        raise HTTPException(
            status_code=422,
            detail={
                "success": False,
                "error_code": code,
                "message": result.get("error_message") or "Live preview failed.",
            },
        )
    logger.info(
        "tryon_preview_ok request_id=%s garment=%s timing_ms=%s cache_hit=%s",
        request_id,
        payload.garmentName,
        result.get("timing_ms"),
        bool(result.get("cache_hit")),
    )
    return {
        "success": True,
        "render_kind": "preview",
        "backend_name": result.get("backend_name", "preview_local"),
        "image_url": result.get("result_image"),
        "timing_ms": result.get("timing_ms"),
        "cache_hit": bool(result.get("cache_hit")),
        "warnings": result.get("warnings", []),
        "request_id": request_id,
        "total_timing_ms": round((time.time() - t0) * 1000, 1),
        "alignment_diagnostics_json": result.get("alignment_diagnostics_json"),
    }


@router.post("/render")
async def enqueue_tryon_render(payload: TryOnRuntimeRequest) -> Dict[str, Any]:
    request_id = str(uuid.uuid4())
    manager = TryOnRuntimeManager.get_instance()
    result = manager.enqueue_final_render(
        user_image_base64=payload.userImageBase64,
        garment_image_url=payload.garmentImageUrl,
        garment_name=payload.garmentName,
        garment_category=payload.garmentCategory,
    )
    if not result.get("success"):
        logger.warning(
            "tryon_render_unavailable request_id=%s garment=%s reason=%s",
            request_id,
            payload.garmentName,
            result.get("error_code"),
        )
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error_code": result.get("error_code") or "FINAL_RENDER_UNAVAILABLE",
                "message": result.get("message") or "Final render unavailable.",
                "details": result.get("details") or {},
            },
        )
    logger.info(
        "tryon_render_enqueued request_id=%s garment=%s job_id=%s",
        request_id,
        payload.garmentName,
        result.get("job_id"),
    )
    return {
        "success": True,
        "job_id": result.get("job_id"),
        "status": result.get("status"),
        "render_kind": "final",
    }


@router.get("/render/{job_id}")
async def get_tryon_job(job_id: str) -> Dict[str, Any]:
    manager = TryOnRuntimeManager.get_instance()
    job = manager.jobs.get(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error_code": "JOB_NOT_FOUND",
                "message": "Try-on job was not found.",
            },
        )
    return {
        "success": True,
        "job_id": job.id,
        "status": job.status,
        "render_kind": "final",
        "backend_name": job.backend_name,
        "image_url": job.result_image,
        "quality_score": job.quality_score,
        "progress": job.progress,
        "failure_kind": job.failure_kind,
        "error_code": job.error_code,
        "message": job.message,
        "alignment_diagnostics_json": job.alignment_diagnostics_json,
    }


@router.get("/jobs/{job_id}")
async def get_tryon_job_legacy(job_id: str) -> Dict[str, Any]:
    return await get_tryon_job(job_id)


@router.get("/status/{job_id}")
async def get_tryon_status(job_id: str) -> Dict[str, Any]:
    """Alias for /render/{job_id} — frontend polls this path."""
    return await get_tryon_job(job_id)


@router.post("/cancel/{job_id}")
async def cancel_tryon_job(job_id: str) -> Dict[str, Any]:
    manager = TryOnRuntimeManager.get_instance()
    ok = manager.jobs.cancel(job_id)
    if not ok:
        raise HTTPException(
            status_code=409,
            detail={
                "success": False,
                "error_code": "CANCEL_REJECTED",
                "message": "Job cannot be cancelled in its current state.",
            },
        )
    return {"success": True, "data": {"jobId": job_id, "status": "cancelled"}, "error": None}


@router.get("/debug/list")
async def tryon_debug_list() -> Dict[str, Any]:
    """List recent DEBUG_TRYON bundles (folders under DEBUG_TRYON_DIR / debug_output)."""
    root = Path(os.getenv("DEBUG_TRYON_DIR", "debug_output")).resolve()
    if not root.is_dir():
        return {"success": True, "debug_root": str(root), "bundles": []}
    bundles = []
    for p in sorted(root.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:64]:
        if p.is_dir():
            files = sorted(f.name for f in p.iterdir() if f.is_file())
            bundles.append({"id": p.name, "files": files, "mtime": p.stat().st_mtime})
    return {"success": True, "debug_root": str(root), "bundles": bundles}


@router.get("/debug/viewer", response_class=HTMLResponse)
async def tryon_debug_viewer() -> HTMLResponse:
    """Minimal visual dashboard: lists debug bundles and shows images via relative paths (use with same host)."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>CONFIT Try-On Debug</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 1rem 1.5rem; background: #0f1115; color: #e8eaed; }
    h1 { font-size: 1.1rem; font-weight: 600; }
    .meta { color: #9aa0a6; font-size: 0.85rem; margin-bottom: 1rem; }
    ul { list-style: none; padding: 0; }
    li { margin: 0.5rem 0; padding: 0.75rem; background: #1a1d24; border-radius: 8px; }
    code { background: #2d3139; padding: 0.1rem 0.35rem; border-radius: 4px; }
    .grid { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
    .grid img { max-height: 140px; border-radius: 6px; border: 1px solid #333; }
    a { color: #8ab4f8; }
  </style>
</head>
<body>
  <h1>Try-on debug bundles</h1>
  <p class="meta">Set <code>DEBUG_TRYON=1</code> and run a try-on. Files are written under <code>debug_output/&lt;request_id&gt;/</code>.
  This page loads the list from <code>/api/tryon/debug/list</code>. Images are not served by the API; open files from disk or mount a static route.</p>
  <div id="root"></div>
  <script>
  fetch('/api/tryon/debug/list')
    .then(r => r.json())
    .then(data => {
      const el = document.getElementById('root');
      if (!data.bundles || !data.bundles.length) {
        el.innerHTML = '<p>No bundles yet. Root: <code>' + (data.debug_root || '') + '</code></p>';
        return;
      }
      el.innerHTML = '<p class="meta">Root: <code>' + data.debug_root + '</code></p><ul>' +
        data.bundles.map(b => '<li><strong>' + b.id + '</strong><br/><small>' + b.files.join(', ') + '</small></li>').join('') +
        '</ul>';
    })
    .catch(e => { document.getElementById('root').textContent = 'Failed to load: ' + e; });
  </script>
</body>
</html>"""
    return HTMLResponse(html)

