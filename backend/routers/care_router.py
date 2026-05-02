"""
CONFIT Backend - CONFIT CARE Router
====================================
Enhanced API endpoints for the charitable giving feature.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database.session import SessionLocal
from database.care_models import CareBeneficiary, CareVoucher, CareVoucherStatus
from schemas.care_schemas import (
    # Enums
    CampaignStatus,
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


from pydantic import BaseModel, Field

# =============================================================================
# Exception Handlers (must be registered on app, not router)
# =============================================================================

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
@router.patch("/campaigns/{campaign_id}", response_model=CampaignResponse)
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


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Delete a draft campaign."""
    service = CampaignService(db)
    campaign = service.get_campaign_by_id(campaign_id)
    if str(campaign.donor_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this campaign"
        )
    if campaign.status != CampaignStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft campaigns can be deleted"
        )
    db.delete(campaign)
    db.commit()
    return


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


@router.patch("/campaigns/{campaign_id}/beneficiaries/{beneficiary_id}", response_model=BeneficiaryResponse)
async def update_campaign_beneficiary(
    campaign_id: str,
    beneficiary_id: str,
    update_data: BeneficiaryUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Update a beneficiary within a campaign (frontend-compatible path)."""
    # Verify campaign ownership
    campaign_service = CampaignService(db)
    campaign = campaign_service.get_campaign_by_id(campaign_id)
    if str(campaign.donor_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign"
        )
    service = BeneficiaryService(db)
    beneficiary = service.update_beneficiary(
        beneficiary_id=beneficiary_id,
        update_data=update_data
    )
    return BeneficiaryResponse.from_orm(beneficiary)


@router.delete("/campaigns/{campaign_id}/beneficiaries/{beneficiary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign_beneficiary(
    campaign_id: str,
    beneficiary_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Remove a beneficiary from a campaign."""
    # Verify campaign ownership
    campaign_service = CampaignService(db)
    campaign = campaign_service.get_campaign_by_id(campaign_id)
    if str(campaign.donor_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign"
        )
    beneficiary = db.query(CareBeneficiary).filter(
        CareBeneficiary.id == beneficiary_id,
        CareBeneficiary.campaign_id == campaign_id
    ).first()
    if not beneficiary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beneficiary not found")
    db.delete(beneficiary)
    db.commit()
    return


# =============================================================================
# Voucher Endpoints
# =============================================================================

class VoucherBatchCreate(BaseModel):
    vouchers: List[VoucherCreate]


@router.post("/campaigns/{campaign_id}/vouchers", response_model=List[VoucherResponse], status_code=status.HTTP_201_CREATED)
async def create_vouchers(
    campaign_id: str,
    batch: VoucherBatchCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Create vouchers for beneficiaries in a campaign."""
    # Verify campaign ownership
    campaign_service = CampaignService(db)
    campaign = campaign_service.get_campaign_by_id(campaign_id)
    if str(campaign.donor_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign"
        )

    service = VoucherService(db)
    created = []
    for voucher_data in batch.vouchers:
        voucher = service.create_voucher(
            campaign_id=campaign_id,
            beneficiary_id=voucher_data.beneficiary_id,
            budget_override=Decimal(str(voucher_data.budget_override)) if voucher_data.budget_override else None
        )
        created.append(voucher)
    return [VoucherResponse.from_orm(v) for v in created]


class VoucherRedeemRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=32)
    order_id: str
    amount: float = Field(..., gt=0)


class VoucherRedeemResponse(BaseModel):
    success: bool
    amount_applied: float
    new_balance: float
    voucher: VoucherResponse


@router.post("/vouchers/validate", response_model=VoucherResponse)
async def validate_voucher(
    validate_data: VoucherValidate,
    db: Session = Depends(get_db),
):
    """Validate a voucher token (public endpoint for beneficiaries)."""
    service = VoucherService(db)
    voucher = service.validate_voucher(validate_data.voucher_token)
    return VoucherResponse.from_orm(voucher)


@router.post("/vouchers/redeem", response_model=VoucherRedeemResponse)
async def redeem_voucher(
    request: VoucherRedeemRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Redeem a voucher for an order."""
    voucher = db.query(CareVoucher).filter(
        CareVoucher.voucher_token == request.code.upper()
    ).first()

    if not voucher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voucher not found")

    if voucher.status != CareVoucherStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Voucher is {voucher.status.value}")

    if voucher.expires_at and voucher.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Voucher has expired")

    if request.amount > float(voucher.budget_remaining):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount exceeds voucher balance")

    # Apply redemption
    balance_before = float(voucher.budget_remaining)
    voucher.budget_remaining = Decimal(str(balance_before - request.amount))

    # Update status if fully used
    if float(voucher.budget_remaining) <= 0:
        voucher.status = CareVoucherStatus.COMPLETED
        voucher.used_at = datetime.now(timezone.utc)
    else:
        voucher.status = CareVoucherStatus.PARTIALLY_USED

    db.commit()
    db.refresh(voucher)

    return VoucherRedeemResponse(
        success=True,
        amount_applied=request.amount,
        new_balance=float(voucher.budget_remaining),
        voucher=VoucherResponse.from_orm(voucher)
    )


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
    try:
        context = service.validate_session(session_token)
    except SessionInvalidException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except CareException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    
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
    try:
        order = service.get_order_by_id(order_id)
    except CareException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return CareOrderResponse.from_orm(order)


# =============================================================================
# Dashboard Endpoints (Donor)
# =============================================================================

@router.get("/donor/campaigns", response_model=CampaignListResponse)
async def get_donor_campaigns_list(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    page: int = 1,
    page_size: int = 20,
):
    """Get all campaigns for the current donor."""
    service = CampaignService(db)
    campaigns, total = service.get_campaigns_by_donor(
        donor_id=str(current_user.id),
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


@router.get("/campaigns/{campaign_id}/stats")
async def get_campaign_stats(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get campaign statistics."""
    campaign_service = CampaignService(db)
    campaign = campaign_service.get_campaign_by_id(campaign_id)

    if str(campaign.donor_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this campaign"
        )

    # Get beneficiaries summary
    beneficiaries = campaign_service.db.query(CareBeneficiary).filter(
        CareBeneficiary.campaign_id == campaign_id
    ).all()

    total_spent = sum(float(b.budget_used) for b in beneficiaries)
    active_beneficiaries = sum(1 for b in beneficiaries if b.is_active)

    # Get vouchers summary
    voucher_service = VoucherService(db)
    vouchers = db.query(CareVoucher).filter(CareVoucher.campaign_id == campaign_id).all()
    active_vouchers = sum(1 for v in vouchers if v.status == CareVoucherStatus.ACTIVE)
    completed_vouchers = sum(1 for v in vouchers if v.status == CareVoucherStatus.COMPLETED)

    return {
        "total_donated": float(campaign.total_budget_allocated),
        "total_spent": total_spent,
        "total_beneficiaries": len(beneficiaries),
        "active_beneficiaries": active_beneficiaries,
        "active_vouchers": active_vouchers,
        "completed_vouchers": completed_vouchers,
        "campaign_name": campaign.campaign_name,
        "status": campaign.status.value,
    }


@router.get("/dashboard", response_model=DonorDashboardResponse)
async def get_donor_dashboard(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get complete donor dashboard data."""
    service = CareAnalyticsService(db)
    dashboard = service.get_donor_dashboard(str(current_user.id))
    return DonorDashboardResponse(**dashboard)


@router.get("/donor/dashboard", response_model=DonorDashboardResponse)
async def get_donor_dashboard_alias(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Compatibility alias for older frontend CARE clients."""
    return await get_donor_dashboard(db=db, current_user=current_user)


@router.get("/csr/stats")
async def get_csr_stats_alias(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """CSR dashboard alias backed by donor dashboard data."""
    dashboard = await get_donor_dashboard(db=db, current_user=current_user)
    data = dashboard.model_dump() if hasattr(dashboard, "model_dump") else dict(dashboard)
    return {
        "brand": {"id": "care", "name": "CONFIT CARE", "csr_level": "Active"},
        "stats": {
            "impact_score": min(100, int(data.get("active_beneficiaries", 0) or 0)),
            "impact_level": "Active",
            "next_level": "Growth",
            "progress_to_next": min(100, int(data.get("active_beneficiaries", 0) or 0)),
            "next_level_points": 100,
            "total_campaigns": data.get("total_campaigns", 0),
            "active_campaigns": data.get("active_campaigns", 0),
            "total_beneficiaries": data.get("active_beneficiaries", 0),
            "total_donated": data.get("total_donated", 0),
            "budget_utilization": 0,
            "engagement_rate": 0,
            "completion_rate": 0,
            "impact_distribution": {},
        },
        "campaigns": data.get("campaigns", []),
    }


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
