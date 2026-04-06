"""
Mock Remote GPU Render Server (local/free).

Purpose:
- Emulate a remote neural try-on endpoint for end-to-end testing.
- Uses ``TryOnService.process_classical`` (same code as ``/api/tryon/*``), including the
  default affine + inpaint compositor when ``TRYON_LEGACY_MESH_PIPELINE`` is not set.

Run:
    python mock_remote_gpu_server.py

Default URL:
    http://127.0.0.1:8011
Endpoints:
    GET  /health
    POST /render
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, field_validator
import uvicorn

from services.tryon.alignment_config import final_render_classical_options
from services.tryon.tryon_service import TryOnService

# Load backend/.env
load_dotenv(dotenv_path=str(Path(__file__).resolve().parent / ".env"))

app = FastAPI(title="CONFIT Mock Remote GPU Server", version="1.0.0")


class RenderRequest(BaseModel):
    userImageBase64: str = Field(..., min_length=100)
    garmentImageUrl: str = Field(..., min_length=5)
    garmentName: str = Field(default="garment", max_length=200)
    garmentCategory: Optional[str] = Field(default=None)

    @field_validator("garmentImageUrl")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("garmentImageUrl must be HTTP/HTTPS")
        return value


def _verify_auth(authorization: Optional[str]) -> None:
    required_key = (os.getenv("TRYON_REMOTE_API_KEY") or "").strip()
    if not required_key:
        return
    scheme = (os.getenv("TRYON_REMOTE_AUTH_SCHEME") or "Bearer").strip()
    expected = f"{scheme} {required_key}" if scheme else required_key
    if (authorization or "").strip() != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "mock-remote-gpu", "mode": "mock"}


@app.post("/render")
async def render(
    payload: RenderRequest,
    authorization: Optional[str] = Header(default=None),
) -> dict:
    _verify_auth(authorization)

    svc = TryOnService()
    # Same classical alignment stack as preview; differs in quality/fabric only.
    final_opts = final_render_classical_options()
    final_opts["garment_category"] = payload.garmentCategory
    result = await svc.process_classical(
        user_image_base64=payload.userImageBase64,
        garment_image_url=payload.garmentImageUrl,
        garment_name=payload.garmentName,
        options=final_opts,
    )

    if not result.success or not result.result_image:
        raise HTTPException(
            status_code=422,
            detail={
                "success": False,
                "error_code": getattr(result, "failure_kind", None) or "MOCK_RENDER_FAILED",
                "message": result.error_message or "Mock render failed",
            },
        )

    return {
        "success": True,
        "resultImage": result.result_image,
        "warnings": list(result.warnings or []) + ["mock_remote_server_result"],
        "quality_score": result.quality_score,
        "alignment_diagnostics_json": result.alignment_diagnostics_json,
    }


if __name__ == "__main__":
    host = os.getenv("TRYON_REMOTE_MOCK_HOST", "127.0.0.1")
    port = int(os.getenv("TRYON_REMOTE_MOCK_PORT", "8011"))
    uvicorn.run("mock_remote_gpu_server:app", host=host, port=port, reload=False, log_level="info")

