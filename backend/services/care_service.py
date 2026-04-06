"""
CONFIT Backend - CONFIT CARE Service
====================================
Core service for the charitable giving feature including:
- Campaign management
- Voucher generation and management
- Beneficiary access with OTP verification
- Device fingerprinting for security
- Audit logging for compliance
"""

import hashlib
import logging
import secrets
import string
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from fastapi import HTTPException, status

from database.care_models import (
    CareCampaign,
    CareBeneficiary,
    CareVoucher,
    CareSession,
    CareOrder,
    CareAnalytics,
    CareAuditLog,
    CareVoucherTransaction,
    CareCampaignType,
    CareCampaignStatus,
    CareVoucherStatus,
    CareSessionStatus,
    CareOrderStatus,
    generate_device_fingerprint,
    generate_otp_secret,
    hash_otp,
    generate_session_token,
    AuditAction,
)
from schemas.care_schemas import (
    BeneficiaryCreate,
    BeneficiaryUpdate,
    CampaignCreate,
    CampaignUpdate,
    CampaignActivate,
    VoucherCreate,
    SessionInitiate,
    OTPVerify,
    CareOrderCreate,
    CSVUploadResponse,
    CSVValidationError,
)
from core.constants import (
    CARE_MIN_BUDGET_PER_PERSON,
    CARE_MAX_BUDGET_PER_PERSON,
    VOUCHER_CODE_LENGTH,
    OTP_LENGTH,
    OTP_MAX_ATTEMPTS,
    OTP_EXPIRY_MINUTES,
    CARE_SESSION_EXPIRY_HOURS,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================

class CareException(Exception):
    """Base exception for CARE-related errors."""
    def __init__(self, message: str, error_code: str = "CARE_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class VoucherNotFoundException(CareException):
    def __init__(self, message: str = "Voucher not found"):
        super().__init__(message, "CARE_002")


class VoucherExpiredException(CareException):
    def __init__(self, message: str = "Voucher has expired"):
        super().__init__(message, "CARE_003")


class VoucherUsedException(CareException):
    def __init__(self, message: str = "Voucher has already been used"):
        super().__init__(message, "CARE_004")


class BudgetExceededException(CareException):
    def __init__(self, message: str = "Budget exceeded"):
        super().__init__(message, "CARE_005")


class OTPInvalidException(CareException):
    def __init__(self, message: str = "Invalid OTP code"):
        super().__init__(message, "CARE_007")


class OTPExpiredException(CareException):
    def __init__(self, message: str = "OTP has expired"):
        super().__init__(message, "CARE_008")


class SessionInvalidException(CareException):
    def __init__(self, message: str = "Invalid or expired session"):
        super().__init__(message, "CARE_009")


class CampaignNotFoundException(CareException):
    def __init__(self, message: str = "Campaign not found"):
        super().__init__(message, "CARE_001")


class BeneficiaryNotFoundException(CareException):
    def __init__(self, message: str = "Beneficiary not found"):
        super().__init__(message, "CARE_006")


# =============================================================================
# Campaign Service
# =============================================================================

class CampaignService:
    """Service for managing donation campaigns."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_campaign(self, donor_id: str, campaign_data: CampaignCreate) -> CareCampaign:
        """Create a new donation campaign."""
        campaign = CareCampaign(
            donor_id=donor_id,
            campaign_name=campaign_data.campaign_name,
            campaign_type=campaign_data.campaign_type,
            description=campaign_data.description,
            budget_per_person=Decimal(str(campaign_data.budget_per_person)),
            currency=campaign_data.currency,
            allowed_categories=campaign_data.allowed_categories,
            excluded_brands=campaign_data.excluded_brands,
            occasion_filter=campaign_data.occasion_filter,
            end_date=campaign_data.end_date,
            voucher_expiry_days=campaign_data.voucher_expiry_days,
            invitation_message=campaign_data.invitation_message,
            confirmation_message=campaign_data.confirmation_message,
            status=CareCampaignStatus.DRAFT,
        )
        
        self.db.add(campaign)
        
        # Create analytics record
        analytics = CareAnalytics(campaign_id=campaign.id)
        self.db.add(analytics)
        
        self.db.commit()
        self.db.refresh(campaign)
        
        # Log audit
        self._log_audit(
            campaign_id=campaign.id,
            action=AuditAction.CAMPAIGN_CREATED,
            action_category="campaign",
            actor_type="donor",
            actor_id=donor_id,
            new_state={"name": campaign.campaign_name, "type": campaign.campaign_type.value}
        )
        
        logger.info(f"Created campaign {campaign.id} for donor {donor_id}")
        return campaign
    
    def update_campaign(self, campaign_id: str, donor_id: str, 
                       update_data: CampaignUpdate) -> CareCampaign:
        """Update an existing campaign."""
        campaign = self.get_campaign_by_id(campaign_id)
        
        if campaign.donor_id != donor_id:
            raise CareException("Not authorized to update this campaign", "AUTH_001")
        
        if campaign.status == CareCampaignStatus.COMPLETED:
            raise CareException("Cannot update completed campaign", "CARE_010")
        
        previous_state = {
            "name": campaign.campaign_name,
            "description": campaign.description,
            "budget_per_person": float(campaign.budget_per_person),
        }
        
        # Update fields
        if update_data.campaign_name:
            campaign.campaign_name = update_data.campaign_name
        if update_data.description is not None:
            campaign.description = update_data.description
        if update_data.budget_per_person:
            campaign.budget_per_person = Decimal(str(update_data.budget_per_person))
        if update_data.allowed_categories is not None:
            campaign.allowed_categories = update_data.allowed_categories
        if update_data.excluded_brands is not None:
            campaign.excluded_brands = update_data.excluded_brands
        if update_data.occasion_filter is not None:
            campaign.occasion_filter = update_data.occasion_filter
        if update_data.end_date is not None:
            campaign.end_date = update_data.end_date
        if update_data.voucher_expiry_days:
            campaign.voucher_expiry_days = update_data.voucher_expiry_days
        if update_data.invitation_message is not None:
            campaign.invitation_message = update_data.invitation_message
        if update_data.confirmation_message is not None:
            campaign.confirmation_message = update_data.confirmation_message
        if update_data.status:
            campaign.status = update_data.status
        
        self.db.commit()
        self.db.refresh(campaign)
        
        # Log audit
        self._log_audit(
            campaign_id=campaign.id,
            action=AuditAction.CAMPAIGN_UPDATED,
            action_category="campaign",
            actor_type="donor",
            actor_id=donor_id,
            previous_state=previous_state,
            new_state={"name": campaign.campaign_name}
        )
        
        return campaign
    
    def activate_campaign(self, campaign_id: str, donor_id: str,
                         activation_data: CampaignActivate) -> CareCampaign:
        """Activate a campaign with beneficiaries."""
        campaign = self.get_campaign_by_id(campaign_id)
        
        if campaign.donor_id != donor_id:
            raise CareException("Not authorized to activate this campaign", "AUTH_001")
        
        if campaign.status != CareCampaignStatus.DRAFT:
            raise CareException("Can only activate draft campaigns", "CARE_011")
        
        # Add beneficiaries
        beneficiary_service = BeneficiaryService(self.db)
        for beneficiary_data in activation_data.beneficiaries:
            beneficiary_service.add_beneficiary(
                campaign_id=campaign.id,
                beneficiary_data=beneficiary_data,
                create_voucher=True
            )
        
        # Update campaign status
        campaign.status = CareCampaignStatus.ACTIVE
        campaign.total_beneficiaries = len(activation_data.beneficiaries)
        campaign.total_budget_allocated = campaign.budget_per_person * campaign.total_beneficiaries
        
        self.db.commit()
        self.db.refresh(campaign)
        
        # Update analytics
        self._update_analytics(campaign.id)
        
        # Log audit
        self._log_audit(
            campaign_id=campaign.id,
            action=AuditAction.CAMPAIGN_ACTIVATED,
            action_category="campaign",
            actor_type="donor",
            actor_id=donor_id,
            new_state={"beneficiaries_added": len(activation_data.beneficiaries)}
        )
        
        # Send invitations if requested
        if activation_data.send_invitations:
            self._send_invitations(campaign)
        
        return campaign
    
    def get_campaign_by_id(self, campaign_id: str) -> CareCampaign:
        """Get a campaign by ID."""
        campaign = self.db.query(CareCampaign).filter(
            CareCampaign.id == campaign_id
        ).first()
        
        if not campaign:
            raise CampaignNotFoundException()
        
        return campaign
    
    def get_campaigns_by_donor(self, donor_id: str, 
                               status: Optional[CareCampaignStatus] = None,
                               page: int = 1, page_size: int = 20) -> Tuple[List[CareCampaign], int]:
        """Get all campaigns for a donor."""
        query = self.db.query(CareCampaign).filter(CareCampaign.donor_id == donor_id)
        
        if status:
            query = query.filter(CareCampaign.status == status)
        
        total = query.count()
        campaigns = query.order_by(CareCampaign.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        return campaigns, total
    
    def get_campaign_summary(self, campaign_id: str) -> Dict[str, Any]:
        """Get summary statistics for a campaign."""
        campaign = self.get_campaign_by_id(campaign_id)
        analytics = self.db.query(CareAnalytics).filter(
            CareAnalytics.campaign_id == campaign.id
        ).first()
        
        days_remaining = None
        if campaign.end_date:
            delta = campaign.end_date - datetime.now(timezone.utc)
            days_remaining = max(0, delta.days)
        
        return {
            "campaign_id": str(campaign.id),
            "campaign_name": campaign.campaign_name,
            "status": campaign.status.value,
            "total_beneficiaries": campaign.total_beneficiaries,
            "active_beneficiaries": analytics.vouchers_accessed if analytics else 0,
            "completed_beneficiaries": analytics.vouchers_completed if analytics else 0,
            "total_budget_allocated": float(campaign.total_budget_allocated),
            "total_budget_used": float(campaign.total_budget_used),
            "budget_utilization_rate": round(
                float(campaign.total_budget_used) / float(campaign.total_budget_allocated) * 100, 2
            ) if campaign.total_budget_allocated > 0 else 0,
            "engagement_rate": float(analytics.engagement_rate) if analytics else 0,
            "completion_rate": float(analytics.completion_rate) if analytics else 0,
            "days_remaining": days_remaining,
            "average_time_to_completion_hours": float(analytics.average_time_to_completion_hours) 
                if analytics and analytics.average_time_to_completion_hours else None,
        }
    
    def _send_invitations(self, campaign: CareCampaign) -> None:
        """Send invitations to all beneficiaries."""
        # TODO: Integrate with SMS/Email service
        for beneficiary in campaign.beneficiaries:
            if beneficiary.voucher:
                beneficiary.voucher.status = CareVoucherStatus.SENT
                beneficiary.voucher.sent_at = datetime.now(timezone.utc)
                beneficiary.invitation_sent_at = datetime.now(timezone.utc)
                
                self._log_audit(
                    campaign_id=campaign.id,
                    voucher_id=beneficiary.voucher.id,
                    action=AuditAction.VOUCHER_SENT,
                    action_category="voucher",
                    actor_type="system",
                    details={"recipient": beneficiary.phone or beneficiary.email}
                )
        
        self.db.commit()
        logger.info(f"Sent invitations for campaign {campaign.id}")
    
    def _update_analytics(self, campaign_id: str) -> None:
        """Update analytics for a campaign."""
        analytics = self.db.query(CareAnalytics).filter(
            CareAnalytics.campaign_id == campaign_id
        ).first()
        
        if not analytics:
            analytics = CareAnalytics(campaign_id=campaign_id)
            self.db.add(analytics)
        
        # Count vouchers
        vouchers = self.db.query(CareVoucher).filter(
            CareVoucher.campaign_id == campaign_id
        ).all()
        
        analytics.total_vouchers_created = len(vouchers)
        analytics.vouchers_sent = sum(1 for v in vouchers if v.status in [
            CareVoucherStatus.SENT, CareVoucherStatus.ACCESSED, 
            CareVoucherStatus.ACTIVE, CareVoucherStatus.COMPLETED, CareVoucherStatus.PARTIALLY_USED
        ])
        analytics.vouchers_accessed = sum(1 for v in vouchers if v.accessed_at is not None)
        analytics.vouchers_completed = sum(1 for v in vouchers if v.status == CareVoucherStatus.COMPLETED)
        analytics.vouchers_expired = sum(1 for v in vouchers if v.status == CareVoucherStatus.EXPIRED)
        
        # Calculate engagement rate
        if analytics.total_vouchers_created > 0:
            analytics.engagement_rate = Decimal(str(
                round(analytics.vouchers_accessed / analytics.total_vouchers_created * 100, 2)
            ))
        
        # Calculate completion rate
        if analytics.vouchers_accessed > 0:
            analytics.completion_rate = Decimal(str(
                round(analytics.vouchers_completed / analytics.vouchers_accessed * 100, 2)
            ))
        
        self.db.commit()
    
    def _log_audit(self, campaign_id: str = None, voucher_id: str = None,
                  session_id: str = None, beneficiary_id: str = None,
                  order_id: str = None, action: str = None,
                  action_category: str = None, actor_type: str = None,
                  actor_id: str = None, actor_ip: str = None,
                  previous_state: Dict = None, new_state: Dict = None,
                  details: Dict = None) -> CareAuditLog:
        """Create an audit log entry."""
        log = CareAuditLog(
            campaign_id=campaign_id,
            voucher_id=voucher_id,
            session_id=session_id,
            beneficiary_id=beneficiary_id,
            order_id=order_id,
            action=action,
            action_category=action_category,
            actor_type=actor_type,
            actor_id=actor_id,
            actor_ip=actor_ip,
            previous_state=previous_state,
            new_state=new_state,
            details=details,
        )
        
        self.db.add(log)
        self.db.commit()
        
        return log


# =============================================================================
# Beneficiary Service
# =============================================================================

class BeneficiaryService:
    """Service for managing beneficiaries."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def add_beneficiary(self, campaign_id: str, beneficiary_data: BeneficiaryCreate,
                       create_voucher: bool = True) -> CareBeneficiary:
        """Add a beneficiary to a campaign."""
        campaign = self.db.query(CareCampaign).filter(
            CareCampaign.id == campaign_id
        ).first()
        
        if not campaign:
            raise CampaignNotFoundException()
        
        # Check for duplicates
        existing = self.db.query(CareBeneficiary).filter(
            and_(
                CareBeneficiary.campaign_id == campaign_id,
                or_(
                    CareBeneficiary.phone == beneficiary_data.phone,
                    CareBeneficiary.email == beneficiary_data.email
                )
            )
        ).first()
        
        if existing:
            raise CareException("Beneficiary already exists in this campaign", "CARE_012")
        
        beneficiary = CareBeneficiary(
            campaign_id=campaign_id,
            name=beneficiary_data.name,
            email=beneficiary_data.email,
            phone=beneficiary_data.phone,
            age_group=beneficiary_data.age_group,
            size_preference=beneficiary_data.size_preference,
            style_preference=beneficiary_data.style_preference,
            occasion_needs=beneficiary_data.occasion_needs,
            budget_allocated=campaign.budget_per_person,
            budget_remaining=campaign.budget_per_person,
            currency=campaign.currency,
        )
        
        self.db.add(beneficiary)
        self.db.flush()
        
        # Create voucher if requested
        if create_voucher:
            voucher_service = VoucherService(self.db)
            voucher_service.create_voucher(
                campaign_id=campaign_id,
                beneficiary_id=beneficiary.id
            )
        
        self.db.commit()
        self.db.refresh(beneficiary)
        
        # Log audit
        CampaignService(self.db)._log_audit(
            campaign_id=campaign_id,
            beneficiary_id=beneficiary.id,
            action=AuditAction.BENEFICIARY_ADDED,
            action_category="beneficiary",
            actor_type="donor",
            new_state={"name": beneficiary.name}
        )
        
        return beneficiary
    
    def bulk_add_beneficiaries(self, campaign_id: str, 
                               beneficiaries: List[BeneficiaryCreate]) -> CSVUploadResponse:
        """Bulk add beneficiaries from CSV upload."""
        valid_rows = []
        errors = []
        
        for i, beneficiary_data in enumerate(beneficiaries, start=1):
            try:
                beneficiary = self.add_beneficiary(
                    campaign_id=campaign_id,
                    beneficiary_data=beneficiary_data,
                    create_voucher=True
                )
                valid_rows.append(beneficiary)
            except CareException as e:
                errors.append({
                    "row_number": i,
                    "error": e.message,
                    "data": beneficiary_data.dict()
                })
        
        return CSVUploadResponse(
            total_rows=len(beneficiaries),
            valid_rows=len(valid_rows),
            invalid_rows=len(errors),
            errors=errors,
            beneficiaries=[BeneficiaryCreate(**b.dict()) for b in valid_rows]
        )
    
    def update_beneficiary(self, beneficiary_id: str, 
                          update_data: BeneficiaryUpdate) -> CareBeneficiary:
        """Update a beneficiary."""
        beneficiary = self.get_beneficiary_by_id(beneficiary_id)
        
        if update_data.name:
            beneficiary.name = update_data.name
        if update_data.email is not None:
            beneficiary.email = update_data.email
        if update_data.phone is not None:
            beneficiary.phone = update_data.phone
        if update_data.age_group is not None:
            beneficiary.age_group = update_data.age_group
        if update_data.size_preference is not None:
            beneficiary.size_preference = update_data.size_preference
        if update_data.style_preference is not None:
            beneficiary.style_preference = update_data.style_preference
        if update_data.occasion_needs is not None:
            beneficiary.occasion_needs = update_data.occasion_needs
        if update_data.is_active is not None:
            beneficiary.is_active = update_data.is_active
        
        self.db.commit()
        self.db.refresh(beneficiary)
        
        return beneficiary
    
    def get_beneficiary_by_id(self, beneficiary_id: str) -> CareBeneficiary:
        """Get a beneficiary by ID."""
        beneficiary = self.db.query(CareBeneficiary).filter(
            CareBeneficiary.id == beneficiary_id
        ).first()
        
        if not beneficiary:
            raise BeneficiaryNotFoundException()
        
        return beneficiary
    
    def get_beneficiaries_by_campaign(self, campaign_id: str, page: int = 1,
                                      page_size: int = 20) -> Tuple[List[CareBeneficiary], int]:
        """Get all beneficiaries for a campaign."""
        query = self.db.query(CareBeneficiary).filter(
            CareBeneficiary.campaign_id == campaign_id
        )
        
        total = query.count()
        beneficiaries = query.order_by(CareBeneficiary.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        return beneficiaries, total


# =============================================================================
# Voucher Service
# =============================================================================

class VoucherService:
    """Service for managing vouchers."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_voucher(self, campaign_id: str, beneficiary_id: str,
                      budget_override: Decimal = None) -> CareVoucher:
        """Create a new voucher for a beneficiary."""
        campaign = self.db.query(CareCampaign).filter(
            CareCampaign.id == campaign_id
        ).first()
        
        if not campaign:
            raise CampaignNotFoundException()
        
        budget = budget_override or campaign.budget_per_person
        expiry_date = datetime.now(timezone.utc) + timedelta(days=campaign.voucher_expiry_days)
        
        voucher = CareVoucher(
            campaign_id=campaign_id,
            beneficiary_id=beneficiary_id,
            voucher_token=self._generate_voucher_token(),
            budget_allocated=budget,
            budget_remaining=budget,
            currency=campaign.currency,
            status=CareVoucherStatus.PENDING,
            expires_at=expiry_date,
        )
        
        self.db.add(voucher)
        self.db.commit()
        self.db.refresh(voucher)
        
        # Log audit
        CampaignService(self.db)._log_audit(
            campaign_id=campaign_id,
            voucher_id=voucher.id,
            beneficiary_id=beneficiary_id,
            action=AuditAction.VOUCHER_CREATED,
            action_category="voucher",
            actor_type="system",
            new_state={"token": voucher.voucher_token, "budget": float(budget)}
        )
        
        return voucher
    
    def validate_voucher(self, voucher_token: str) -> CareVoucher:
        """Validate a voucher token and return the voucher."""
        voucher = self.db.query(CareVoucher).filter(
            CareVoucher.voucher_token == voucher_token
        ).first()
        
        if not voucher:
            raise VoucherNotFoundException()
        
        if voucher.status == CareVoucherStatus.EXPIRED or voucher.expires_at < datetime.now(timezone.utc):
            raise VoucherExpiredException()
        
        if voucher.status == CareVoucherStatus.COMPLETED:
            raise VoucherUsedException()
        
        return voucher
    
    def get_voucher_by_id(self, voucher_id: str) -> CareVoucher:
        """Get a voucher by ID."""
        voucher = self.db.query(CareVoucher).filter(
            CareVoucher.id == voucher_id
        ).first()
        
        if not voucher:
            raise VoucherNotFoundException()
        
        return voucher
    
    def record_voucher_usage(self, voucher_id: str, amount: Decimal,
                            order_id: str = None) -> CareVoucherTransaction:
        """Record a voucher usage transaction."""
        voucher = self.get_voucher_by_id(voucher_id)
        
        if amount > voucher.budget_remaining:
            raise BudgetExceededException()
        
        balance_before = voucher.budget_remaining
        voucher.budget_used = voucher.budget_used + amount
        voucher.budget_remaining = voucher.budget_remaining - amount
        
        # Update status
        if voucher.budget_remaining == 0:
            voucher.status = CareVoucherStatus.COMPLETED
            voucher.completed_at = datetime.now(timezone.utc)
        else:
            voucher.status = CareVoucherStatus.PARTIALLY_USED
        
        # Create transaction record
        transaction = CareVoucherTransaction(
            voucher_id=voucher_id,
            transaction_type="redemption",
            amount=amount,
            balance_before=balance_before,
            balance_after=voucher.budget_remaining,
            currency=voucher.currency,
            order_id=order_id,
            actor_type="beneficiary",
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        # Update campaign analytics
        CampaignService(self.db)._update_analytics(voucher.campaign_id)
        
        return transaction
    
    def _generate_voucher_token(self) -> str:
        """Generate a unique voucher token."""
        prefix = "CARE"
        chars = string.ascii_uppercase + string.digits
        chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("L", "")
        
        while True:
            suffix = ''.join(secrets.choice(chars) for _ in range(VOUCHER_CODE_LENGTH - len(prefix) - 1))
            token = f"{prefix}-{suffix}"
            
            # Check uniqueness
            existing = self.db.query(CareVoucher).filter(
                CareVoucher.voucher_token == token
            ).first()
            
            if not existing:
                return token


# =============================================================================
# Session Service (OTP & Device Fingerprinting)
# =============================================================================

class SessionService:
    """Service for managing beneficiary sessions with OTP verification."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def initiate_session(self, voucher_token: str, ip_address: str = None,
                        user_agent: str = None) -> CareSession:
        """Initiate a new session for a beneficiary."""
        voucher_service = VoucherService(self.db)
        voucher = voucher_service.validate_voucher(voucher_token)
        
        # Check for existing active session
        existing_session = self.db.query(CareSession).filter(
            and_(
                CareSession.voucher_id == voucher.id,
                CareSession.status.in_([
                    CareSessionStatus.ACTIVE, 
                    CareSessionStatus.OTP_SENT,
                    CareSessionStatus.OTP_VERIFIED
                ])
            )
        ).first()
        
        if existing_session and existing_session.expires_at > datetime.now(timezone.utc):
            return existing_session
        
        # Generate device fingerprint
        device_fingerprint = generate_device_fingerprint(
            ip_address or "", 
            user_agent or ""
        )
        
        # Create new session
        session = CareSession(
            voucher_id=voucher.id,
            session_token=generate_session_token(),
            device_fingerprint=device_fingerprint,
            ip_address=ip_address,
            user_agent=user_agent,
            status=CareSessionStatus.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=CARE_SESSION_EXPIRY_HOURS),
            otp_secret=generate_otp_secret(),
        )
        
        self.db.add(session)
        
        # Update voucher status
        voucher.status = CareVoucherStatus.ACCESSED
        voucher.accessed_at = datetime.now(timezone.utc)
        
        # Update beneficiary
        if voucher.beneficiary:
            voucher.beneficiary.first_access_at = voucher.beneficiary.first_access_at or datetime.now(timezone.utc)
            voucher.beneficiary.last_access_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(session)
        
        # Log audit
        CampaignService(self.db)._log_audit(
            campaign_id=voucher.campaign_id,
            voucher_id=voucher.id,
            session_id=session.id,
            beneficiary_id=voucher.beneficiary_id,
            action=AuditAction.SESSION_CREATED,
            action_category="session",
            actor_type="beneficiary",
            actor_id=voucher.beneficiary_id,
            actor_ip=ip_address,
            details={"device_fingerprint": device_fingerprint[:16] + "..."}
        )
        
        return session
    
    def send_otp(self, session_id: str) -> str:
        """Generate and send OTP for a session."""
        session = self.get_session_by_id(session_id)
        
        if session.status == CareSessionStatus.LOCKED:
            raise SessionInvalidException("Session is locked due to too many failed attempts")
        
        if session.otp_attempts >= OTP_MAX_ATTEMPTS:
            session.status = CareSessionStatus.LOCKED
            self.db.commit()
            raise SessionInvalidException("Too many failed OTP attempts")
        
        # Generate OTP
        otp_code = self._generate_otp()
        session.otp_code = hash_otp(otp_code, session.otp_secret)
        session.otp_sent_at = datetime.now(timezone.utc)
        session.status = CareSessionStatus.OTP_SENT
        
        self.db.commit()
        
        # Get beneficiary contact
        voucher = self.db.query(CareVoucher).filter(
            CareVoucher.id == session.voucher_id
        ).first()
        
        # TODO: Send OTP via SMS/Email
        # For now, return the OTP (in production, this would be sent via SMS)
        logger.info(f"OTP for session {session_id}: {otp_code}")
        
        # Log audit
        CampaignService(self.db)._log_audit(
            campaign_id=voucher.campaign_id if voucher else None,
            voucher_id=session.voucher_id,
            session_id=session.id,
            action=AuditAction.OTP_SENT,
            action_category="session",
            actor_type="system",
        )
        
        return otp_code  # In production, this would not be returned
    
    def verify_otp(self, session_id: str, otp_code: str) -> CareSession:
        """Verify OTP for a session."""
        session = self.get_session_by_id(session_id)
        
        if session.status == CareSessionStatus.LOCKED:
            raise SessionInvalidException("Session is locked")
        
        # Check OTP expiry
        if session.otp_sent_at and session.otp_sent_at < datetime.now(timezone.utc) - timedelta(minutes=OTP_EXPIRY_MINUTES):
            raise OTPExpiredException()
        
        # Verify OTP
        expected_hash = hash_otp(otp_code, session.otp_secret)
        if session.otp_code != expected_hash:
            session.otp_attempts += 1
            self.db.commit()
            
            # Log failed attempt
            voucher = self.db.query(CareVoucher).filter(
                CareVoucher.id == session.voucher_id
            ).first()
            
            CampaignService(self.db)._log_audit(
                campaign_id=voucher.campaign_id if voucher else None,
                voucher_id=session.voucher_id,
                session_id=session.id,
                action=AuditAction.OTP_FAILED,
                action_category="session",
                actor_type="beneficiary",
                details={"attempt": session.otp_attempts}
            )
            
            raise OTPInvalidException()
        
        # OTP verified
        session.otp_verified = True
        session.otp_verified_at = datetime.now(timezone.utc)
        session.status = CareSessionStatus.ACTIVE
        session.otp_attempts = 0
        
        self.db.commit()
        self.db.refresh(session)
        
        # Log audit
        voucher = self.db.query(CareVoucher).filter(
            CareVoucher.id == session.voucher_id
        ).first()
        
        CampaignService(self.db)._log_audit(
            campaign_id=voucher.campaign_id if voucher else None,
            voucher_id=session.voucher_id,
            session_id=session.id,
            action=AuditAction.OTP_VERIFIED,
            action_category="session",
            actor_type="beneficiary",
        )
        
        return session
    
    def get_session_by_id(self, session_id: str) -> CareSession:
        """Get a session by ID."""
        session = self.db.query(CareSession).filter(
            CareSession.id == session_id
        ).first()
        
        if not session:
            raise SessionInvalidException()
        
        return session
    
    def get_session_by_token(self, session_token: str) -> CareSession:
        """Get a session by token."""
        session = self.db.query(CareSession).filter(
            CareSession.session_token == session_token
        ).first()
        
        if not session:
            raise SessionInvalidException()
        
        if session.expires_at < datetime.now(timezone.utc):
            session.status = CareSessionStatus.EXPIRED
            self.db.commit()
            raise SessionInvalidException("Session has expired")
        
        return session
    
    def validate_session(self, session_token: str) -> Dict[str, Any]:
        """Validate a session and return full context."""
        session = self.get_session_by_token(session_token)
        
        if session.status != CareSessionStatus.ACTIVE:
            raise SessionInvalidException("Session is not active")
        
        # Update last activity
        session.last_activity_at = datetime.now(timezone.utc)
        self.db.commit()
        
        # Get related entities
        voucher = self.db.query(CareVoucher).filter(
            CareVoucher.id == session.voucher_id
        ).first()
        
        beneficiary = self.db.query(CareBeneficiary).filter(
            CareBeneficiary.id == voucher.beneficiary_id
        ).first() if voucher else None
        
        campaign = self.db.query(CareCampaign).filter(
            CareCampaign.id == voucher.campaign_id
        ).first() if voucher else None
        
        return {
            "session": session,
            "voucher": voucher,
            "beneficiary": beneficiary,
            "campaign": campaign,
            "budget_remaining": float(voucher.budget_remaining) if voucher else 0,
            "allowed_categories": campaign.allowed_categories if campaign else None,
            "excluded_brands": campaign.excluded_brands if campaign else None,
            "occasion_filter": campaign.occasion_filter if campaign else None,
        }
    
    def update_session_cart(self, session_id: str, cart_data: Dict[str, Any]) -> CareSession:
        """Update cart data in session."""
        session = self.get_session_by_id(session_id)
        session.cart_data = cart_data
        self.db.commit()
        return session
    
    def _generate_otp(self) -> str:
        """Generate a random OTP code."""
        return ''.join(secrets.choice(string.digits) for _ in range(OTP_LENGTH))


# =============================================================================
# Care Order Service
# =============================================================================

class CareOrderService:
    """Service for managing care orders."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_order(self, session_token: str, order_data: CareOrderCreate,
                    order_id: str) -> CareOrder:
        """Create a care order from a session."""
        session_service = SessionService(self.db)
        context = session_service.validate_session(session_token)
        
        voucher = context["voucher"]
        beneficiary = context["beneficiary"]
        
        # Calculate total
        total_amount = Decimal(str(order_data.items[0].get("total", 0))) if order_data.items else Decimal("0")
        for item in order_data.items:
            total_amount += Decimal(str(item.get("price", 0))) * item.get("quantity", 1)
        
        # Check budget
        if total_amount > voucher.budget_remaining:
            raise BudgetExceededException()
        
        # Create care order
        care_order = CareOrder(
            voucher_id=voucher.id,
            beneficiary_id=beneficiary.id,
            order_id=order_id,
            subtotal=total_amount,
            shipping_cost=Decimal("0"),
            total_amount=total_amount,
            amount_from_voucher=total_amount,
            currency=voucher.currency,
            status=CareOrderStatus.PENDING,
            delivery_method=order_data.delivery_method,
            shipping_address=order_data.shipping_address,
            pickup_store_id=order_data.pickup_store_id,
            items_count=len(order_data.items),
            items_summary=order_data.items,
        )
        
        self.db.add(care_order)
        
        # Record voucher usage
        voucher_service = VoucherService(self.db)
        transaction = voucher_service.record_voucher_usage(
            voucher_id=voucher.id,
            amount=total_amount,
            order_id=care_order.id
        )
        
        # Update beneficiary budget
        beneficiary.budget_used = beneficiary.budget_used + total_amount
        beneficiary.budget_remaining = beneficiary.budget_remaining - total_amount
        
        # Update session
        session = context["session"]
        session.status = CareSessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(care_order)
        
        # Log audit
        CampaignService(self.db)._log_audit(
            campaign_id=voucher.campaign_id,
            voucher_id=voucher.id,
            session_id=session.id,
            beneficiary_id=beneficiary.id,
            order_id=care_order.id,
            action=AuditAction.ORDER_PLACED,
            action_category="order",
            actor_type="beneficiary",
            actor_id=beneficiary.id,
            new_state={"total": float(total_amount), "items": len(order_data.items)}
        )
        
        return care_order
    
    def get_order_by_id(self, order_id: str) -> CareOrder:
        """Get a care order by ID."""
        order = self.db.query(CareOrder).filter(
            CareOrder.id == order_id
        ).first()
        
        if not order:
            raise CareException("Order not found", "ORD_001")
        
        return order
    
    def update_order_status(self, order_id: str, new_status: CareOrderStatus) -> CareOrder:
        """Update order status."""
        order = self.get_order_by_id(order_id)
        order.status = new_status
        
        if new_status == CareOrderStatus.CONFIRMED:
            order.confirmed_at = datetime.now(timezone.utc)
        elif new_status == CareOrderStatus.DELIVERED:
            order.delivered_at = datetime.now(timezone.utc)
        
        self.db.commit()
        return order


# =============================================================================
# Analytics Service
# =============================================================================

class CareAnalyticsService:
    """Service for campaign analytics."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_campaign_analytics(self, campaign_id: str) -> CareAnalytics:
        """Get analytics for a campaign."""
        analytics = self.db.query(CareAnalytics).filter(
            CareAnalytics.campaign_id == campaign_id
        ).first()
        
        if not analytics:
            raise CampaignNotFoundException()
        
        return analytics
    
    def get_donor_dashboard(self, donor_id: str) -> Dict[str, Any]:
        """Get complete donor dashboard data."""
        campaigns, total_campaigns = CampaignService(self.db).get_campaigns_by_donor(
            donor_id, page_size=100
        )
        
        active_campaigns = [c for c in campaigns if c.status == CareCampaignStatus.ACTIVE]
        
        total_beneficiaries = sum(c.total_beneficiaries for c in campaigns)
        total_donated = sum(float(c.total_budget_allocated) for c in campaigns)
        total_impact = sum(float(c.total_budget_used) for c in campaigns)
        
        # Recent campaigns
        recent_campaigns = [
            CampaignService(self.db).get_campaign_summary(str(c.id))
            for c in campaigns[:5]
        ]
        
        # Recent orders
        recent_orders = self.db.query(CareOrder).join(CareVoucher).join(
            CareCampaign
        ).filter(
            CareCampaign.donor_id == donor_id
        ).order_by(CareOrder.created_at.desc()).limit(10).all()
        
        # Spending by category
        spending_by_category = self._get_spending_by_category(donor_id)
        
        return {
            "total_campaigns": total_campaigns,
            "active_campaigns": len(active_campaigns),
            "total_beneficiaries_supported": total_beneficiaries,
            "total_donated": total_donated,
            "total_impact_value": total_impact,
            "currency": "EGP",
            "recent_campaigns": recent_campaigns,
            "recent_orders": recent_orders,
            "spending_by_category": spending_by_category,
            "spending_by_date": [],
            "engagement_trend": [],
        }
    
    def _get_spending_by_category(self, donor_id: str) -> Dict[str, float]:
        """Get spending breakdown by category."""
        # Query all orders for donor's campaigns
        orders = self.db.query(CareOrder).join(CareVoucher).join(
            CareCampaign
        ).filter(
            CareCampaign.donor_id == donor_id
        ).all()
        
        category_totals = {}
        for order in orders:
            for item in (order.items_summary or []):
                category = item.get("category", "Other")
                price = float(item.get("price", 0))
                category_totals[category] = category_totals.get(category, 0) + price
        
        return category_totals
    
    def generate_report(self, campaign_id: str, report_type: str,
                       format: str) -> Dict[str, Any]:
        """Generate a report for a campaign."""
        # TODO: Implement PDF/CSV generation
        campaign = CampaignService(self.db).get_campaign_by_id(campaign_id)
        analytics = self.get_campaign_analytics(campaign_id)
        
        return {
            "report_id": str(secrets.token_hex(8)),
            "campaign_id": campaign_id,
            "report_type": report_type,
            "format": format,
            "download_url": f"/api/care/reports/{secrets.token_hex(8)}.{format}",
            "generated_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
        }
