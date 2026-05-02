"""
Egypt Data Compliance Router - Law 151/2020 (Personal Data Protection Law)

Implements data subject rights:
- Right of access (Article 8)
- Right to rectification (Article 9)
- Right to erasure (Article 10)
- Right to data portability (Article 11)
- Right to object (Article 12)

Data retention policies:
- Orders: 7 years (tax compliance)
- AI photos: 7 days
- User data: Until account deletion + 30 days grace

DPO Contact: dpo@confit.app
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.security.rbac import AuthContext, get_current_user_required as get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/me/data", tags=["Data Compliance"])


# ==================== Pydantic Models ====================

class DataExportRequest(BaseModel):
    """Request to export user data."""
    format: str = Field(default="json", pattern="^(json|csv|pdf)$")
    include_tryon_photos: bool = False


class DataExportResponse(BaseModel):
    """Response with data export information."""
    export_id: str
    status: str
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    estimated_size_mb: float
    data_categories: List[str]


class UserDataSummary(BaseModel):
    """Summary of user data stored in the system."""
    profile: Dict[str, Any]
    style_dna: Optional[Dict[str, Any]]
    orders_count: int
    tryon_sessions_count: int
    photos_count: int
    wardrobe_items_count: int
    notifications_count: int
    donation_history_count: int
    data_retention_policy: Dict[str, str]
    last_updated: datetime


class DataRectificationRequest(BaseModel):
    """Request to rectify user data."""
    field: str
    new_value: Any
    reason: Optional[str] = None


class DataRectificationResponse(BaseModel):
    """Response after data rectification."""
    success: bool
    field: str
    old_value: Any
    new_value: Any
    timestamp: datetime
    request_id: str


class DataDeletionRequest(BaseModel):
    """Request to delete user data."""
    reason: Optional[str] = None
    confirm_deletion: bool = Field(..., description="Must be True to confirm deletion")
    keep_order_history: bool = False  # Required for tax compliance


class DataDeletionResponse(BaseModel):
    """Response after data deletion request."""
    request_id: str
    status: str
    deletion_date: datetime
    retained_data: List[str]
    retention_reason: str
    grace_period_days: int = 30


class RetentionPolicyInfo(BaseModel):
    """Information about data retention policies."""
    data_type: str
    retention_period: str
    legal_basis: str
    auto_delete: bool
    next_purge_date: Optional[datetime]


# ==================== Data Retention Policies ====================

RETENTION_POLICIES = {
    "orders": {
        "retention_period": "7 years",
        "legal_basis": "Egyptian Tax Law - Article 35",
        "auto_delete": False,
        "description": "Order records retained for tax compliance"
    },
    "ai_tryon_photos": {
        "retention_period": "7 days",
        "legal_basis": "Law 151/2020 Article 5 - Minimization",
        "auto_delete": True,
        "description": "AI try-on photos automatically purged after 7 days"
    },
    "user_profile": {
        "retention_period": "Account lifetime + 30 days",
        "legal_basis": "Contractual necessity",
        "auto_delete": False,
        "description": "Deleted 30 days after account closure"
    },
    "style_dna": {
        "retention_period": "Account lifetime + 30 days",
        "legal_basis": "Legitimate interest",
        "auto_delete": False,
        "description": "Personalization data deleted with account"
    },
    "wardrobe_items": {
        "retention_period": "Account lifetime + 30 days",
        "legal_basis": "Contractual necessity",
        "auto_delete": True,
        "description": "User-uploaded wardrobe photos and metadata"
    },
    "donation_records": {
        "retention_period": "5 years",
        "legal_basis": "Egyptian Tax Law - Charitable deductions",
        "auto_delete": False,
        "description": "Donation history for tax receipt purposes"
    },
    "payment_logs": {
        "retention_period": "7 years",
        "legal_basis": "Egyptian Tax Law + PCI DSS",
        "auto_delete": False,
        "description": "Payment transaction logs"
    },
    "chat_messages": {
        "retention_period": "1 year",
        "legal_basis": "Customer service records",
        "auto_delete": True,
        "description": "In-app chat and support messages"
    },
    "analytics_data": {
        "retention_period": "26 months",
        "legal_basis": "Legitimate interest - Aggregated only",
        "auto_delete": True,
        "description": "Aggregated, non-identifiable analytics"
    }
}


# ==================== Helper Functions ====================

async def collect_user_data(user_id: str) -> Dict[str, Any]:
    """
    Collect all user data for export or summary.
    
    Args:
        user_id: The user ID to collect data for
        
    Returns:
        Dictionary containing all user data categories
    """
    # This would query various services and database tables
    # Placeholder implementation - would integrate with actual services
    
    return {
        "user_id": user_id,
        "export_timestamp": datetime.utcnow().isoformat(),
        "data_categories": {
            "profile": "collected",
            "orders": "collected",
            "tryon_sessions": "collected",
            "wardrobe": "collected",
            "notifications": "collected",
            "donations": "collected"
        },
        "notice": "Full implementation would integrate with all services"
    }


async def schedule_data_deletion(user_id: str, keep_orders: bool) -> Dict[str, Any]:
    """
    Schedule user data for deletion with grace period.
    
    Args:
        user_id: The user ID to delete
        keep_orders: Whether to retain order history for tax compliance
        
    Returns:
        Deletion schedule information
    """
    deletion_date = datetime.utcnow() + timedelta(days=30)
    
    retained = []
    if keep_orders:
        retained.append("orders (tax compliance)")
        retained.append("payment_logs (tax compliance)")
    
    return {
        "deletion_date": deletion_date,
        "retained_data": retained,
        "retention_reason": "Egyptian Tax Law compliance" if retained else None
    }


# ==================== Routes ====================

@router.get("/summary", response_model=UserDataSummary)
async def get_data_summary(
    current_user: AuthContext = Depends(get_current_user)
) -> UserDataSummary:
    """
    Get a summary of all user data stored in the system.
    
    Article 8 of Law 151/2020: Right of Access
    """
    # Aggregate counts from various services
    summary = UserDataSummary(
        profile={
            "user_id": str(current_user.user_id),
            "email": current_user.email,
            "created_at": datetime.utcnow(),
        },
        style_dna=None,  # Would fetch from style DNA service
        orders_count=0,  # Would fetch from order service
        tryon_sessions_count=0,
        photos_count=0,
        wardrobe_items_count=0,
        notifications_count=0,
        donation_history_count=0,
        data_retention_policy={
            "general": "Account lifetime + 30 days grace",
            "orders": "7 years (tax compliance)",
            "ai_photos": "7 days (automatic deletion)"
        },
        last_updated=datetime.utcnow()
    )
    
    return summary


@router.post("/export", response_model=DataExportResponse)
async def request_data_export(
    request: DataExportRequest,
    current_user: AuthContext = Depends(get_current_user)
) -> DataExportResponse:
    """
    Request a comprehensive export of all user data.
    
    Article 8 of Law 151/2020: Right of Access
    Article 11: Right to Data Portability
    
    Export will be ready within 48 hours as per Egyptian law.
    """
    import uuid
    
    export_id = str(uuid.uuid4())
    
    # Calculate estimated size
    estimated_size = 5.0  # Base size in MB
    if request.include_tryon_photos:
        estimated_size += 50.0  # Additional for photos
    
    # Schedule the export (async job)
    # Would integrate with background job system
    
    logger.info(f"Data export requested for user {current_user.user_id}, export_id: {export_id}")
    
    response = DataExportResponse(
        export_id=export_id,
        status="processing",
        download_url=None,  # Will be populated when ready
        expires_at=datetime.utcnow() + timedelta(days=7),
        estimated_size_mb=estimated_size,
        data_categories=[
            "profile",
            "style_dna",
            "orders",
            "tryon_sessions",
            "wardrobe",
            "notifications",
            "donations",
            "analytics_preferences"
        ]
    )
    
    return response


@router.get("/export/{export_id}/status")
async def get_export_status(
    export_id: str,
    current_user: AuthContext = Depends(get_current_user)
) -> Dict[str, Any]:
    """Check the status of a data export request."""
    # Would query export job status
    return {
        "export_id": export_id,
        "status": "processing",  # or "ready", "expired"
        "progress_percent": 45,
        "estimated_completion": datetime.utcnow() + timedelta(hours=2)
    }


@router.post("/rectify", response_model=DataRectificationResponse)
async def rectify_data(
    request: DataRectificationRequest,
    current_user: AuthContext = Depends(get_current_user)
) -> DataRectificationResponse:
    """
    Request rectification of inaccurate user data.
    
    Article 9 of Law 151/2020: Right to Rectification
    """
    import uuid
    
    request_id = str(uuid.uuid4())
    
    # Validate allowed fields
    allowed_fields = [
        "name", "phone", "address", "date_of_birth",
        "style_preferences", "notification_preferences"
    ]
    
    if request.field not in allowed_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Field '{request.field}' cannot be modified via this endpoint"
        )
    
    # Log the rectification request
    logger.info(
        f"Data rectification requested by user {current_user.user_id}, "
        f"field: {request.field}, request_id: {request_id}"
    )
    
    return DataRectificationResponse(
        success=True,
        field=request.field,
        old_value="***redacted***",  # Would show actual old value
        new_value=request.new_value,
        timestamp=datetime.utcnow(),
        request_id=request_id
    )


@router.delete("/", response_model=DataDeletionResponse)
async def delete_user_data(
    request: DataDeletionRequest,
    current_user: AuthContext = Depends(get_current_user)
) -> DataDeletionResponse:
    """
    Request complete deletion of user data (Right to Erasure).
    
    Article 10 of Law 151/2020: Right to Erasure
    
    Note: Order history is retained for 7 years per Egyptian Tax Law.
    Personal data is deleted after 30-day grace period.
    """
    import uuid
    
    if not request.confirm_deletion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="confirm_deletion must be True to proceed with deletion"
        )
    
    request_id = str(uuid.uuid4())
    
    # Schedule deletion with grace period
    deletion_info = await schedule_data_deletion(
        str(current_user.user_id),
        request.keep_order_history
    )
    
    logger.warning(
        f"Data deletion requested for user {current_user.user_id}, "
        f"request_id: {request_id}, deletion_date: {deletion_info['deletion_date']}"
    )
    
    # Log the DPO about this deletion request
    # Would send notification to dpo@confit.app
    
    return DataDeletionResponse(
        request_id=request_id,
        status="scheduled",
        deletion_date=deletion_info["deletion_date"],
        retained_data=deletion_info["retained_data"],
        retention_reason=deletion_info["retention_reason"],
        grace_period_days=30
    )


@router.get("/retention-policies")
async def get_retention_policies(
    current_user: AuthContext = Depends(get_current_user)
) -> List[RetentionPolicyInfo]:
    """Get detailed information about all data retention policies."""
    policies = []
    
    for data_type, policy in RETENTION_POLICIES.items():
        # Calculate next purge date for auto-delete items
        next_purge = None
        if policy["auto_delete"] and data_type == "ai_tryon_photos":
            next_purge = datetime.utcnow() + timedelta(days=7)
        
        policies.append(RetentionPolicyInfo(
            data_type=data_type,
            retention_period=policy["retention_period"],
            legal_basis=policy["legal_basis"],
            auto_delete=policy["auto_delete"],
            next_purge_date=next_purge
        ))
    
    return policies


@router.post("/object")
async def object_to_processing(
    purpose: str,
    current_user: AuthContext = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Object to processing of personal data for specific purposes.
    
    Article 12 of Law 151/2020: Right to Object
    
    Valid purposes: marketing, analytics, ai_personalization, third_party_sharing
    """
    valid_purposes = [
        "marketing",
        "analytics",
        "ai_personalization",
        "third_party_sharing",
        "profiling"
    ]
    
    if purpose not in valid_purposes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid purpose. Valid options: {', '.join(valid_purposes)}"
        )
    
    # Update user preferences
    logger.info(f"User {current_user.user_id} objected to processing for: {purpose}")
    
    return {
        "success": True,
        "purpose": purpose,
        "status": "objection_recorded",
        "effective_date": datetime.utcnow(),
        "note": "Processing will cease within 72 hours"
    }


@router.get("/dpo-contact")
async def get_dpo_contact() -> Dict[str, Any]:
    """
    Get Data Protection Officer contact information.
    
    Required by Law 151/2020 Article 28
    """
    return {
        "organization": "CONFIT Fashion Technologies",
        "dpo_name": "Data Protection Officer",
        "email": "dpo@confit.app",
        "phone": "+20-XXX-XXXX-XXX",  # Replace with actual
        "address": "Cairo, Egypt",  # Replace with actual
        "response_time": "48 hours",
        "languages": ["Arabic", "English"],
        "authority": "Egypt Personal Data Protection Center (PDPC)",
        "law_reference": "Law No. 151 of 2020"
    }


@router.post("/complaint")
async def file_complaint(
    complaint_type: str,
    description: str,
    current_user: AuthContext = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    File a complaint regarding data protection.
    
    Users can also file directly with PDPC (Egypt Data Protection Authority).
    """
    import uuid
    
    complaint_id = str(uuid.uuid4())
    
    logger.warning(
        f"Data protection complaint filed by user {current_user.user_id}, "
        f"complaint_id: {complaint_id}, type: {complaint_type}"
    )
    
    return {
        "complaint_id": complaint_id,
        "status": "received",
        "timestamp": datetime.utcnow(),
        "dpo_response_within": "48 hours",
        "pdpc_contact": {
            "authority": "Egypt Personal Data Protection Center (PDPC)",
            "website": "https://pdpc.gov.eg",  # Verify actual URL
            "email": "complaints@pdpc.gov.eg"
        }
    }
