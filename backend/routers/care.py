"""
CONFIT Backend — CONFIT CARE Donation System Router
====================================================
Endpoints for donor campaigns, beneficiaries, and vouchers.
"""

import logging
import secrets
import string
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.session import SessionLocal
from database.models import (
    DonationCampaign,
    CampaignBeneficiary,
    CareVoucher,
    VoucherTransaction,
    DonationTransaction,
    CampaignStatus,
    VoucherStatus,
    User,
)
from utils.auth_deps import get_current_user
from services.auth_service import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/care", tags=["CONFIT CARE"])


# ===========================================
# Request/Response Models
# ===========================================

class CreateCampaignRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    target_amount: float = Field(..., gt=0)
    currency: str = Field("USD", max_length=10)
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class UpdateCampaignRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    target_amount: Optional[float] = Field(None, gt=0)
    status: Optional[str] = None
    end_date: Optional[str] = None


class CreateBeneficiaryRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    budget_cap: float = Field(..., gt=0)
    currency: str = Field("USD", max_length=10)
    restrictions: Optional[List[str]] = None


class CreateVoucherRequest(BaseModel):
    beneficiary_id: Optional[str] = None
    amount: float = Field(..., gt=0)
    currency: str = Field("USD", max_length=10)
    expires_at: Optional[str] = None


class ValidateVoucherRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=32)
    order_total: float = Field(..., ge=0)


class RedeemVoucherRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=32)
    order_id: str
    amount: float = Field(..., gt=0)


class CampaignResponse(BaseModel):
    id: str
    donor_id: str
    title: str
    description: Optional[str]
    target_amount: float
    current_amount: float
    currency: str
    status: str
    start_date: str
    end_date: Optional[str]
    created_at: str


class BeneficiaryResponse(BaseModel):
    id: str
    campaign_id: str
    name: str
    email: Optional[str]
    phone: Optional[str]
    budget_cap: float
    total_spent: float
    currency: str
    is_active: bool
    created_at: str


class VoucherResponse(BaseModel):
    id: str
    code: str
    campaign_id: str
    beneficiary_id: Optional[str]
    amount: float
    balance: float
    currency: str
    status: str
    expires_at: Optional[str]
    created_at: str


class DonorDashboardResponse(BaseModel):
    total_campaigns: int
    total_donated: float
    total_impact: float
    active_beneficiaries: int
    campaigns: List[CampaignResponse]
    recent_activity: List[dict]


# ===========================================
# Helper Functions
# ===========================================

def generate_voucher_code() -> str:
    """Generate a unique voucher code."""
    prefix = "CARE"
    chars = string.ascii_uppercase + string.digits
    # Remove ambiguous characters
    chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("L", "")
    suffix = ''.join(secrets.choice(chars) for _ in range(8))
    return f"{prefix}-{suffix}"


def campaign_to_response(campaign: DonationCampaign) -> CampaignResponse:
    return CampaignResponse(
        id=str(campaign.id),
        donor_id=str(campaign.donor_id),
        title=campaign.title,
        description=campaign.description,
        target_amount=float(campaign.target_amount),
        current_amount=float(campaign.current_amount),
        currency=campaign.currency,
        status=campaign.status.value,
        start_date=campaign.start_date.isoformat(),
        end_date=campaign.end_date.isoformat() if campaign.end_date else None,
        created_at=campaign.created_at.isoformat(),
    )


def beneficiary_to_response(beneficiary: CampaignBeneficiary) -> BeneficiaryResponse:
    return BeneficiaryResponse(
        id=str(beneficiary.id),
        campaign_id=str(beneficiary.campaign_id),
        name=beneficiary.name,
        email=beneficiary.email,
        phone=beneficiary.phone,
        budget_cap=float(beneficiary.budget_cap),
        total_spent=float(beneficiary.total_spent),
        currency=beneficiary.currency,
        is_active=beneficiary.is_active,
        created_at=beneficiary.created_at.isoformat(),
    )


def voucher_to_response(voucher: CareVoucher) -> VoucherResponse:
    return VoucherResponse(
        id=str(voucher.id),
        code=voucher.code,
        campaign_id=str(voucher.campaign_id),
        beneficiary_id=str(voucher.beneficiary_id) if voucher.beneficiary_id else None,
        amount=float(voucher.amount),
        balance=float(voucher.balance),
        currency=voucher.currency,
        status=voucher.status.value,
        expires_at=voucher.expires_at.isoformat() if voucher.expires_at else None,
        created_at=voucher.created_at.isoformat(),
    )


# ===========================================
# Donor Dashboard Endpoints
# ===========================================

@router.get("/donor/dashboard", response_model=DonorDashboardResponse)
async def get_donor_dashboard(
    user: UserProfile = Depends(get_current_user),
):
    """Get donor dashboard summary."""
    db = SessionLocal()
    try:
        # Get donor's campaigns
        campaigns = db.query(DonationCampaign).filter(
            DonationCampaign.donor_id == user.id
        ).all()

        total_donated = sum(float(c.current_amount) for c in campaigns)
        total_impact = sum(
            float(b.total_spent)
            for c in campaigns
            for b in c.beneficiaries
        )

        active_beneficiaries = sum(
            1 for c in campaigns
            for b in c.beneficiaries
            if b.is_active
        )

        # Get recent transactions
        recent_tx = db.query(DonationTransaction).filter(
            DonationTransaction.donor_id == user.id
        ).order_by(DonationTransaction.created_at.desc()).limit(10).all()

        recent_activity = [
            {
                "id": str(tx.id),
                "type": "donation",
                "amount": float(tx.amount),
                "currency": tx.currency,
                "campaign_id": str(tx.campaign_id),
                "created_at": tx.created_at.isoformat(),
            }
            for tx in recent_tx
        ]

        return DonorDashboardResponse(
            total_campaigns=len(campaigns),
            total_donated=total_donated,
            total_impact=total_impact,
            active_beneficiaries=active_beneficiaries,
            campaigns=[campaign_to_response(c) for c in campaigns],
            recent_activity=recent_activity,
        )
    finally:
        db.close()


@router.get("/donor/campaigns", response_model=List[CampaignResponse])
async def get_donor_campaigns(
    user: UserProfile = Depends(get_current_user),
):
    """Get all campaigns for the current donor."""
    db = SessionLocal()
    try:
        campaigns = db.query(DonationCampaign).filter(
            DonationCampaign.donor_id == user.id
        ).order_by(DonationCampaign.created_at.desc()).all()
        return [campaign_to_response(c) for c in campaigns]
    finally:
        db.close()


# ===========================================
# Campaign Endpoints
# ===========================================

@router.get("/campaigns", response_model=List[CampaignResponse])
async def list_campaigns(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """List public campaigns (active only by default)."""
    db = SessionLocal()
    try:
        query = db.query(DonationCampaign)
        if status:
            query = query.filter(DonationCampaign.status == status)
        else:
            query = query.filter(DonationCampaign.status == CampaignStatus.active)

        campaigns = query.order_by(
            DonationCampaign.current_amount.desc()
        ).offset(offset).limit(limit).all()
        return [campaign_to_response(c) for c in campaigns]
    finally:
        db.close()


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: str):
    """Get campaign details."""
    db = SessionLocal()
    try:
        campaign = db.query(DonationCampaign).filter(
            DonationCampaign.id == campaign_id
        ).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return campaign_to_response(campaign)
    finally:
        db.close()


@router.post("/campaigns", response_model=CampaignResponse)
async def create_campaign(
    request: CreateCampaignRequest,
    user: UserProfile = Depends(get_current_user),
):
    """Create a new donation campaign."""
    db = SessionLocal()
    try:
        campaign = DonationCampaign(
            donor_id=user.id,
            title=request.title,
            description=request.description,
            target_amount=Decimal(str(request.target_amount)),
            current_amount=Decimal("0"),
            currency=request.currency,
            status=CampaignStatus.draft,
            start_date=datetime.fromisoformat(request.start_date) if request.start_date else datetime.now(timezone.utc),
            end_date=datetime.fromisoformat(request.end_date) if request.end_date else None,
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        logger.info("Created campaign %s for donor %s", campaign.id, user.id)
        return campaign_to_response(campaign)
    finally:
        db.close()


@router.patch("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    request: UpdateCampaignRequest,
    user: UserProfile = Depends(get_current_user),
):
    """Update campaign details."""
    db = SessionLocal()
    try:
        campaign = db.query(DonationCampaign).filter(
            DonationCampaign.id == campaign_id,
            DonationCampaign.donor_id == user.id,
        ).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        if request.title:
            campaign.title = request.title
        if request.description is not None:
            campaign.description = request.description
        if request.target_amount:
            campaign.target_amount = Decimal(str(request.target_amount))
        if request.status:
            try:
                campaign.status = CampaignStatus(request.status)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid status")
        if request.end_date:
            campaign.end_date = datetime.fromisoformat(request.end_date)

        db.commit()
        db.refresh(campaign)
        return campaign_to_response(campaign)
    finally:
        db.close()


@router.get("/campaigns/{campaign_id}/stats")
async def get_campaign_stats(
    campaign_id: str,
    user: UserProfile = Depends(get_current_user),
):
    """Get campaign statistics."""
    db = SessionLocal()
    try:
        campaign = db.query(DonationCampaign).filter(
            DonationCampaign.id == campaign_id,
            DonationCampaign.donor_id == user.id,
        ).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Calculate stats
        total_spent = sum(float(b.total_spent) for b in campaign.beneficiaries)
        active_vouchers = sum(
            1 for v in campaign.vouchers
            if v.status == VoucherStatus.active
        )

        # Recent transactions
        recent_tx = db.query(VoucherTransaction).join(
            CareVoucher
        ).filter(
            CareVoucher.campaign_id == campaign_id
        ).order_by(VoucherTransaction.created_at.desc()).limit(20).all()

        return {
            "total_donated": float(campaign.current_amount),
            "total_spent": total_spent,
            "total_beneficiaries": len(campaign.beneficiaries),
            "active_vouchers": active_vouchers,
            "recent_transactions": [
                {
                    "id": str(tx.id),
                    "type": tx.transaction_type,
                    "amount": float(tx.amount),
                    "created_at": tx.created_at.isoformat(),
                }
                for tx in recent_tx
            ],
        }
    finally:
        db.close()


# ===========================================
# Beneficiary Endpoints
# ===========================================

@router.get("/campaigns/{campaign_id}/beneficiaries", response_model=List[BeneficiaryResponse])
async def get_beneficiaries(
    campaign_id: str,
    user: UserProfile = Depends(get_current_user),
):
    """Get all beneficiaries for a campaign."""
    db = SessionLocal()
    try:
        campaign = db.query(DonationCampaign).filter(
            DonationCampaign.id == campaign_id,
            DonationCampaign.donor_id == user.id,
        ).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        return [beneficiary_to_response(b) for b in campaign.beneficiaries]
    finally:
        db.close()


@router.post("/campaigns/{campaign_id}/beneficiaries", response_model=BeneficiaryResponse)
async def add_beneficiary(
    campaign_id: str,
    request: CreateBeneficiaryRequest,
    user: UserProfile = Depends(get_current_user),
):
    """Add a beneficiary to a campaign."""
    db = SessionLocal()
    try:
        campaign = db.query(DonationCampaign).filter(
            DonationCampaign.id == campaign_id,
            DonationCampaign.donor_id == user.id,
        ).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        beneficiary = CampaignBeneficiary(
            campaign_id=campaign_id,
            name=request.name,
            email=request.email,
            phone=request.phone,
            budget_cap=Decimal(str(request.budget_cap)),
            currency=request.currency,
            restrictions=request.restrictions or [],
        )
        db.add(beneficiary)
        db.commit()
        db.refresh(beneficiary)
        logger.info("Added beneficiary %s to campaign %s", beneficiary.id, campaign_id)
        return beneficiary_to_response(beneficiary)
    finally:
        db.close()


# ===========================================
# Voucher Endpoints
# ===========================================

@router.get("/campaigns/{campaign_id}/vouchers", response_model=List[VoucherResponse])
async def get_vouchers(
    campaign_id: str,
    user: UserProfile = Depends(get_current_user),
):
    """Get all vouchers for a campaign."""
    db = SessionLocal()
    try:
        campaign = db.query(DonationCampaign).filter(
            DonationCampaign.id == campaign_id,
            DonationCampaign.donor_id == user.id,
        ).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        return [voucher_to_response(v) for v in campaign.vouchers]
    finally:
        db.close()


@router.post("/campaigns/{campaign_id}/vouchers")
async def create_vouchers(
    campaign_id: str,
    vouchers: List[CreateVoucherRequest],
    user: UserProfile = Depends(get_current_user),
):
    """Create vouchers for a campaign."""
    db = SessionLocal()
    try:
        campaign = db.query(DonationCampaign).filter(
            DonationCampaign.id == campaign_id,
            DonationCampaign.donor_id == user.id,
        ).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        created = []
        for voucher_req in vouchers:
            # Generate unique code
            code = generate_voucher_code()
            while db.query(CareVoucher).filter(CareVoucher.code == code).first():
                code = generate_voucher_code()

            voucher = CareVoucher(
                code=code,
                campaign_id=campaign_id,
                beneficiary_id=voucher_req.beneficiary_id,
                amount=Decimal(str(voucher_req.amount)),
                balance=Decimal(str(voucher_req.amount)),
                currency=voucher_req.currency,
                expires_at=datetime.fromisoformat(voucher_req.expires_at) if voucher_req.expires_at else None,
            )
            db.add(voucher)
            created.append(voucher)

        db.commit()
        logger.info("Created %d vouchers for campaign %s", len(created), campaign_id)
        return {"vouchers": [voucher_to_response(v) for v in created]}
    finally:
        db.close()


@router.post("/vouchers/validate")
async def validate_voucher(request: ValidateVoucherRequest):
    """Validate a voucher code for checkout."""
    db = SessionLocal()
    try:
        voucher = db.query(CareVoucher).filter(
            CareVoucher.code == request.code.upper()
        ).first()

        if not voucher:
            return {"valid": False, "message": "Invalid voucher code"}

        if voucher.status != VoucherStatus.active:
            return {"valid": False, "message": f"Voucher is {voucher.status.value}"}

        if voucher.expires_at and voucher.expires_at < datetime.now(timezone.utc):
            return {"valid": False, "message": "Voucher has expired"}

        # Calculate max usable amount
        max_usable = min(float(voucher.balance), request.order_total)

        return {
            "valid": True,
            "voucher": voucher_to_response(voucher),
            "max_usable": max_usable,
            "message": f"Voucher valid for up to {voucher.currency} {max_usable}",
        }
    finally:
        db.close()


@router.post("/vouchers/redeem")
async def redeem_voucher(
    request: RedeemVoucherRequest,
    user: UserProfile = Depends(get_current_user),
):
    """Redeem a voucher for an order."""
    db = SessionLocal()
    try:
        voucher = db.query(CareVoucher).filter(
            CareVoucher.code == request.code.upper()
        ).first()

        if not voucher:
            raise HTTPException(status_code=404, detail="Voucher not found")

        if voucher.status != VoucherStatus.active:
            raise HTTPException(status_code=400, detail=f"Voucher is {voucher.status.value}")

        if voucher.expires_at and voucher.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Voucher has expired")

        if request.amount > float(voucher.balance):
            raise HTTPException(status_code=400, detail="Amount exceeds voucher balance")

        # Create transaction
        balance_before = voucher.balance
        voucher.balance = Decimal(str(float(voucher.balance) - request.amount))
        balance_after = voucher.balance

        # Update status if fully used
        if voucher.balance == 0:
            voucher.status = VoucherStatus.used
            voucher.used_at = datetime.now(timezone.utc)

        transaction = VoucherTransaction(
            voucher_id=voucher.id,
            transaction_type="redemption",
            amount=Decimal(str(request.amount)),
            balance_before=balance_before,
            balance_after=balance_after,
            order_id=request.order_id,
            metadata_json={"user_id": user.id},
        )
        db.add(transaction)

        # Update beneficiary total spent
        if voucher.beneficiary_id:
            beneficiary = db.query(CampaignBeneficiary).filter(
                CampaignBeneficiary.id == voucher.beneficiary_id
            ).first()
            if beneficiary:
                beneficiary.total_spent = Decimal(str(float(beneficiary.total_spent) + request.amount))

        db.commit()
        logger.info("Redeemed voucher %s for order %s, amount: %s", voucher.code, request.order_id, request.amount)

        return {
            "success": True,
            "amount_applied": request.amount,
            "new_balance": float(voucher.balance),
            "voucher": voucher_to_response(voucher),
        }
    finally:
        db.close()


@router.get("/health")
async def care_health():
    """Health check for CONFIT CARE service."""
    return {"status": "ok", "service": "confit_care"}
