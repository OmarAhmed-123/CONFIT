"""
CONFIT Backend - CONFIT CARE Router
====================================
Enhanced API endpoints for the charitable giving feature.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database.session import SessionLocal
from schemas.care_schemas import (
    # Request schemas
    BeneficiaryCreate,
    BeneficiaryUpdate,
    BeneficiaryBulkUpload,
    CampaignCreate,
    CampaignUpdate,
    CampaignActivate,
    VoucherCreate,
    VoucherValidate,
    SessionInitiate,
    OTPVerify,
    CareOrderCreate,
    CareReportRequest,
    PaginationParams,
    # Response schemas
    BeneficiaryResponse,
    BeneficiaryListResponse,
    CampaignResponse,
    CampaignListResponse,
    CampaignSummary,
    VoucherResponse,
    VoucherListResponse,
    SessionResponse,
    BeneficiarySessionContext,
    CareOrderResponse,
    CareOrderConfirmation,
    CareAnalyticsResponse,
    DonorDashboardResponse,
    AuditLogResponse,
    AuditLogListResponse,
    CareReportResponse,
    CareError,
    CSVUploadResponse,
)
from services.care_service import (
    CampaignService,
    BeneficiaryService,
    VoucherService,
    SessionService,
    CareOrderService,
    CareAnalyticsService,
    CareException,
    VoucherNotFoundException,
    VoucherExpiredException,
    BudgetExceededException,
    OTPInvalidException,
    SessionInvalidException,
)
from utils.auth_deps import get_current_user, get_optional_user
from core.constants import ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/care", tags=["CONFIT CARE"])


# =============================================================================
# Dependency Injection
# =============================================================================

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_client_info(request: Request) -> dict:
    """Extract client information from request."""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", ""),
    }


# =============================================================================
# Exception Handlers
# =============================================================================

@router.exception_handler(CareException)
async def care_exception_handler(request: Request, exc: CareException):
    """Handle CARE-specific exceptions."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
        }
    )


# =============================================================================
# Campaign Endpoints (Donor)
# =============================================================================

@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: CampaignCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Create a new donation campaign."""
    service = CampaignService(db)
    campaign = service.create_campaign(
        donor_id=str(current_user.id),
        campaign_data=campaign_data
    )
    return CampaignResponse.from_orm(campaign)


@router.get("/campaigns", response_model=CampaignListResponse)
async def list_campaigns(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """List all campaigns for the current donor."""
    service = CampaignService(db)
    campaigns, total = service.get_campaigns_by_donor(
        donor_id=str(current_user.id),
        status=status,
        page=page,
        page_size=page_size
    )
    
    return CampaignListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        has_next=page * page_size < total,
        has_prev=page > 1,
        campaigns=[CampaignResponse.from_orm(c) for c in campaigns]
    )


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get a specific campaign by ID."""
    service = CampaignService(db)
    campaign = service.get_campaign_by_id(campaign_id)
    
    # Verify ownership
    if str(campaign.donor_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign"
        )
    
    return CampaignResponse.from_orm(campaign)


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    update_data: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Update a campaign."""
    service = CampaignService(db)
    campaign = service.update_campaign(
        campaign_id=campaign_id,
        donor_id=str(current_user.id),
        update_data=update_data
    )
    return CampaignResponse.from_orm(campaign)


@router.post("/campaigns/{campaign_id}/activate", response_model=CampaignResponse)
async def activate_campaign(
    campaign_id: str,
    activation_data: CampaignActivate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Activate a campaign with beneficiaries."""
    service = CampaignService(db)
    campaign = service.activate_campaign(
        campaign_id=campaign_id,
        donor_id=str(current_user.id),
        activation_data=activation_data
    )
    
    # Send invitations in background if requested
    if activation_data.send_invitations:
        # TODO: Add background task for sending SMS/Email
        pass
    
    return CampaignResponse.from_orm(campaign)


@router.get("/campaigns/{campaign_id}/summary", response_model=CampaignSummary)
async def get_campaign_summary(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get summary statistics for a campaign."""
    service = CampaignService(db)
    campaign = service.get_campaign_by_id(campaign_id)
    
    # Verify ownership
    if str(campaign.donor_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign"
        )
    
    summary = service.get_campaign_summary(campaign_id)
    return CampaignSummary(**summary)


@router.get("/campaigns/{campaign_id}/analytics", response_model=CareAnalyticsResponse)
async def get_campaign_analytics(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get detailed analytics for a campaign."""
    campaign_service = CampaignService(db)
    campaign = campaign_service.get_campaign_by_id(campaign_id)
    
    # Verify ownership
    if str(campaign.donor_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign"
        )
    
    analytics_service = CareAnalyticsService(db)
    analytics = analytics_service.get_campaign_analytics(campaign_id)
    return CareAnalyticsResponse.from_orm(analytics)


@router.post("/campaigns/{campaign_id}/report", response_model=CareReportResponse)
async def generate_campaign_report(
    campaign_id: str,
    report_request: CareReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Generate a report for a campaign."""
    campaign_service = CampaignService(db)
    campaign = campaign_service.get_campaign_by_id(campaign_id)
    
    # Verify ownership
    if str(campaign.donor_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign"
        )
    
    analytics_service = CareAnalyticsService(db)
    report = analytics_service.generate_report(
        campaign_id=campaign_id,
        report_type=report_request.report_type,
        format=report_request.format
    )
    return CareReportResponse(**report)


# =============================================================================
# Beneficiary Endpoints (Donor)
# =============================================================================

@router.post("/campaigns/{campaign_id}/beneficiaries", 
             response_model=BeneficiaryResponse, 
             status_code=status.HTTP_201_CREATED)
async def add_beneficiary(
    campaign_id: str,
    beneficiary_data: BeneficiaryCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Add a beneficiary to a campaign."""
    # Verify campaign ownership
    campaign_service = CampaignService(db)
    campaign = campaign_service.get_campaign_by_id(campaign_id)
    
    if str(campaign.donor_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this campaign"
        )
    
    service = BeneficiaryService(db)
    beneficiary = service.add_beneficiary(
        campaign_id=campaign_id,
        beneficiary_data=beneficiary_data,
        create_voucher=True
    )
    return BeneficiaryResponse.from_orm(beneficiary)


@router.post("/campaigns/{campaign_id}/beneficiaries/bulk",
             response_model=CSVUploadResponse)
async def bulk_add_beneficiaries(
    campaign_id: str,
    beneficiaries_data: BeneficiaryBulkUpload,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Bulk add beneficiaries to a campaign."""
    # Verify campaign ownership
    campaign_service = CampaignService(db)
    campaign = campaign_service.get_campaign_by_id(campaign_id)
    
    if str(campaign.donor_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this campaign"
        )
    
    service = BeneficiaryService(db)
    result = service.bulk_add_beneficiaries(
        campaign_id=campaign_id,
        beneficiaries=beneficiaries_data.beneficiaries
    )
    return result


@router.get("/campaigns/{campaign_id}/beneficiaries",
            response_model=BeneficiaryListResponse)
async def list_beneficiaries(
    campaign_id: str,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """List all beneficiaries for a campaign."""
    # Verify campaign ownership
    campaign_service = CampaignService(db)
    campaign = campaign_service.get_campaign_by_id(campaign_id)
    
    if str(campaign.donor_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign"
        )
    
    service = BeneficiaryService(db)
    beneficiaries, total = service.get_beneficiaries_by_campaign(
        campaign_id=campaign_id,
        page=page,
        page_size=page_size
    )
    
    return BeneficiaryListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        has_next=page * page_size < total,
        has_prev=page > 1,
        beneficiaries=[BeneficiaryResponse.from_orm(b) for b in beneficiaries]
    )


@router.put("/beneficiaries/{beneficiary_id}", response_model=BeneficiaryResponse)
async def update_beneficiary(
    beneficiary_id: str,
    update_data: BeneficiaryUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Update a beneficiary."""
    service = BeneficiaryService(db)
    beneficiary = service.update_beneficiary(
        beneficiary_id=beneficiary_id,
        update_data=update_data
    )
    return BeneficiaryResponse.from_orm(beneficiary)


# =============================================================================
# Voucher Endpoints
# =============================================================================

@router.post("/vouchers", response_model=VoucherResponse, status_code=status.HTTP_201_CREATED)
async def create_voucher(
    voucher_data: VoucherCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Create an additional voucher for a beneficiary."""
    service = VoucherService(db)
    voucher = service.create_voucher(
        campaign_id=voucher_data.campaign_id,
        beneficiary_id=voucher_data.beneficiary_id,
        budget_override=voucher_data.budget_override
    )
    return VoucherResponse.from_orm(voucher)


@router.post("/vouchers/validate", response_model=VoucherResponse)
async def validate_voucher(
    validate_data: VoucherValidate,
    db: Session = Depends(get_db),
):
    """Validate a voucher token (public endpoint for beneficiaries)."""
    service = VoucherService(db)
    voucher = service.validate_voucher(validate_data.voucher_token)
    return VoucherResponse.from_orm(voucher)


@router.get("/campaigns/{campaign_id}/vouchers", response_model=VoucherListResponse)
async def list_vouchers(
    campaign_id: str,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """List all vouchers for a campaign."""
    # Verify campaign ownership
    campaign_service = CampaignService(db)
    campaign = campaign_service.get_campaign_by_id(campaign_id)
    
    if str(campaign.donor_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign"
        )
    
    from repositories.care_repository import CareVoucherRepository
    repo = CareVoucherRepository(db)
    vouchers, total = repo.get_by_campaign(
        campaign_id=campaign_id,
        status=status,
        skip=(page - 1) * page_size,
        limit=page_size
    )
    
    return VoucherListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        has_next=page * page_size < total,
        has_prev=page > 1,
        vouchers=[VoucherResponse.from_orm(v) for v in vouchers]
    )


# =============================================================================
# Session Endpoints (Beneficiary Access)
# =============================================================================

@router.post("/session/initiate", response_model=SessionResponse)
async def initiate_session(
    initiate_data: SessionInitiate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Initiate a new beneficiary session (public endpoint)."""
    client_info = get_client_info(request)
    
    service = SessionService(db)
    session = service.initiate_session(
        voucher_token=initiate_data.voucher_token,
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"]
    )
    
    return SessionResponse.from_orm(session)


@router.post("/session/{session_id}/otp/send")
async def send_otp(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Send OTP to beneficiary (public endpoint)."""
    service = SessionService(db)
    otp_code = service.send_otp(session_id)
    
    # In production, OTP would be sent via SMS
    # For development, return it (remove in production!)
    return {
        "message": "OTP sent successfully",
        "otp": otp_code  # Remove in production!
    }


@router.post("/session/{session_id}/otp/verify", response_model=SessionResponse)
async def verify_otp(
    session_id: str,
    verify_data: OTPVerify,
    db: Session = Depends(get_db),
):
    """Verify OTP for a session (public endpoint)."""
    service = SessionService(db)
    session = service.verify_otp(
        session_id=session_id,
        otp_code=verify_data.otp_code
    )
    return SessionResponse.from_orm(session)


@router.get("/session/{session_token}/context", response_model=BeneficiarySessionContext)
async def get_session_context(
    session_token: str,
    db: Session = Depends(get_db),
):
    """Get full context for an authenticated session (public endpoint)."""
    service = SessionService(db)
    context = service.validate_session(session_token)
    
    return BeneficiarySessionContext(
        session=SessionResponse.from_orm(context["session"]),
        voucher=VoucherResponse.from_orm(context["voucher"]),
        beneficiary=BeneficiaryResponse.from_orm(context["beneficiary"]),
        campaign=CampaignResponse.from_orm(context["campaign"]),
        budget_remaining=context["budget_remaining"],
        allowed_categories=context["allowed_categories"],
        excluded_brands=context["excluded_brands"],
        occasion_filter=context["occasion_filter"],
    )


@router.post("/session/{session_token}/cart")
async def update_session_cart(
    session_token: str,
    cart_data: dict,
    db: Session = Depends(get_db),
):
    """Update cart data in session."""
    service = SessionService(db)
    session = service.update_session_cart(
        session_id=service.get_session_by_token(session_token).id,
        cart_data=cart_data
    )
    return {"message": "Cart updated", "cart": session.cart_data}


# =============================================================================
# Order Endpoints (Beneficiary)
# =============================================================================

@router.post("/orders", response_model=CareOrderConfirmation, status_code=status.HTTP_201_CREATED)
async def create_care_order(
    order_data: CareOrderCreate,
    db: Session = Depends(get_db),
):
    """Create a care order from a session (public endpoint)."""
    import secrets
    
    # Generate order ID
    order_id = f"CARE-{secrets.token_hex(8).upper()}"
    
    service = CareOrderService(db)
    care_order = service.create_order(
        session_token=order_data.session_id,
        order_data=order_data,
        order_id=order_id
    )
    
    return CareOrderConfirmation(
        order=CareOrderResponse.from_orm(care_order),
        message="Order placed successfully! Your items will be delivered soon.",
        budget_remaining=float(care_order.voucher.budget_remaining),
        estimated_delivery="3-5 business days"
    )


@router.get("/orders/{order_id}", response_model=CareOrderResponse)
async def get_order(
    order_id: str,
    db: Session = Depends(get_db),
):
    """Get a care order by ID."""
    service = CareOrderService(db)
    order = service.get_order_by_id(order_id)
    return CareOrderResponse.from_orm(order)


# =============================================================================
# Dashboard Endpoints (Donor)
# =============================================================================

@router.get("/dashboard", response_model=DonorDashboardResponse)
async def get_donor_dashboard(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get complete donor dashboard data."""
    service = CareAnalyticsService(db)
    dashboard = service.get_donor_dashboard(str(current_user.id))
    return DonorDashboardResponse(**dashboard)


# =============================================================================
# Audit Log Endpoints
# =============================================================================

@router.get("/campaigns/{campaign_id}/audit-log", response_model=AuditLogListResponse)
async def get_campaign_audit_log(
    campaign_id: str,
    action_category: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get audit log for a campaign."""
    # Verify campaign ownership
    campaign_service = CampaignService(db)
    campaign = campaign_service.get_campaign_by_id(campaign_id)
    
    if str(campaign.donor_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign"
        )
    
    from repositories.care_repository import CareAuditLogRepository
    repo = CareAuditLogRepository(db)
    logs, total = repo.get_by_campaign(
        campaign_id=campaign_id,
        action_category=action_category,
        skip=(page - 1) * page_size,
        limit=page_size
    )
    
    return AuditLogListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
        has_next=page * page_size < total,
        has_prev=page > 1,
        logs=[AuditLogResponse.from_orm(log) for log in logs]
    )


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health")
async def health_check():
    """Health check endpoint for CARE service."""
    return {
        "status": "healthy",
        "service": "CONFIT CARE",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
