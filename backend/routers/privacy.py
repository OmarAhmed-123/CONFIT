"""
CONFIT Backend — Privacy Router
==============================
GDPR compliance and data management endpoints.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database.session import get_db
from services.privacy_service import PrivacyService, get_privacy_service
from models.profile_models import (
    ConsentUpdate,
    ConsentHistoryResponse,
    DataExportRequest,
    DataExportResponse,
    DeletionRequest,
    DeletionConfirm,
)
from utils.auth_deps import require_auth
from services.auth_service import UserProfile

router = APIRouter(prefix="/api/privacy", tags=["Privacy"])


def get_client_info(request: Request) -> dict:
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


@router.get("/consents")
async def get_consents(
    user: UserProfile = Depends(require_auth),
    privacy_service: PrivacyService = Depends(get_privacy_service),
):
    return privacy_service.get_consents(user.id)


@router.post("/consents", response_model=ConsentHistoryResponse)
async def update_consent(
    data: ConsentUpdate,
    request: Request,
    user: UserProfile = Depends(require_auth),
    privacy_service: PrivacyService = Depends(get_privacy_service),
):
    client = get_client_info(request)
    return privacy_service.update_consent(
        user_id=user.id,
        consent_type=data.consent_type,
        granted=data.granted,
        ip_address=client["ip_address"],
        user_agent=client["user_agent"],
    )


@router.get("/consents/history", response_model=list[ConsentHistoryResponse])
async def get_consent_history(
    limit: int = 50,
    user: UserProfile = Depends(require_auth),
    privacy_service: PrivacyService = Depends(get_privacy_service),
):
    return privacy_service.get_consent_history(user.id, limit=limit)


@router.post("/export", response_model=DataExportResponse)
async def request_data_export(
    data: DataExportRequest = Depends(),
    user: UserProfile = Depends(require_auth),
    privacy_service: PrivacyService = Depends(get_privacy_service),
):
    return privacy_service.request_data_export(user.id, format=data.format)


@router.get("/export/{export_id}", response_model=DataExportResponse)
async def get_export_status(
    export_id: str,
    user: UserProfile = Depends(require_auth),
    privacy_service: PrivacyService = Depends(get_privacy_service),
):
    result = privacy_service.get_export_status(export_id)
    if not result:
        raise HTTPException(status_code=404, detail="Export request not found")
    return result


@router.get("/export/{export_id}/download")
async def download_export(
    export_id: str,
    user: UserProfile = Depends(require_auth),
    privacy_service: PrivacyService = Depends(get_privacy_service),
):
    data = privacy_service.get_export_data(export_id)
    if not data:
        raise HTTPException(status_code=404, detail="Export not found or expired")
    
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="confit_data_export_{export_id}.json"'
        }
    )


@router.post("/delete", response_model=DataExportResponse)
async def request_deletion(
    data: DeletionRequest = Depends(),
    user: UserProfile = Depends(require_auth),
    privacy_service: PrivacyService = Depends(get_privacy_service),
):
    result = privacy_service.request_deletion(user.id, reason=data.reason)
    if hasattr(result, '_confirmation_code_plain'):
        result._confirmation_code_sent = result._confirmation_code_plain
    return result


@router.post("/delete/{request_id}/confirm")
async def confirm_deletion(
    request_id: str,
    data: DeletionConfirm,
    user: UserProfile = Depends(require_auth),
    privacy_service: PrivacyService = Depends(get_privacy_service),
):
    success = privacy_service.confirm_deletion(user.id, data.confirmation_code)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid confirmation code")
    return {"success": True, "message": "Account deletion completed"}


@router.post("/delete/cancel")
async def cancel_deletion(
    user: UserProfile = Depends(require_auth),
    privacy_service: PrivacyService = Depends(get_privacy_service),
):
    success = privacy_service.cancel_deletion(user.id)
    if not success:
        raise HTTPException(status_code=404, detail="No pending deletion request found")
    return {"success": True, "message": "Deletion request cancelled"}


@router.get("/settings")
async def get_privacy_settings(
    user: UserProfile = Depends(require_auth),
    privacy_service: PrivacyService = Depends(get_privacy_service),
):
    return privacy_service.get_privacy_settings(user.id)


@router.post("/retention/{policy}")
async def apply_retention_policy(
    policy: str,
    user: UserProfile = Depends(require_auth),
    privacy_service: PrivacyService = Depends(get_privacy_service),
):
    if policy not in ["standard", "minimal", "aggressive"]:
        raise HTTPException(status_code=400, detail="Invalid retention policy")
    
    privacy_service.apply_retention_policy(user.id, policy)
    return {"success": True, "policy": policy}
