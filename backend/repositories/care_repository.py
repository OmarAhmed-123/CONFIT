"""
CONFIT Backend - Care Repository
================================
Repository layer for CONFIT CARE data access.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc

from database.care_models import (
    CareCampaign,
    CareBeneficiary,
    CareVoucher,
    CareSession,
    CareOrder,
    CareAnalytics,
    CareAuditLog,
    CareVoucherTransaction,
    CareCampaignStatus,
    CareVoucherStatus,
    CareSessionStatus,
)
from repositories.base import BaseRepository


class CareCampaignRepository(BaseRepository[CareCampaign]):
    """Repository for CareCampaign model."""
    
    def __init__(self, db: Session):
        super().__init__(db, CareCampaign)
    
    def get_by_donor(self, donor_id: str, status: Optional[CareCampaignStatus] = None,
                    skip: int = 0, limit: int = 20) -> Tuple[List[CareCampaign], int]:
        """Get campaigns by donor ID with optional status filter."""
        query = self.db.query(CareCampaign).filter(CareCampaign.donor_id == donor_id)
        
        if status:
            query = query.filter(CareCampaign.status == status)
        
        total = query.count()
        items = query.order_by(desc(CareCampaign.created_at)).offset(skip).limit(limit).all()
        
        return items, total
    
    def get_active_campaigns(self, skip: int = 0, limit: int = 20) -> List[CareCampaign]:
        """Get all active campaigns."""
        return self.db.query(CareCampaign).filter(
            CareCampaign.status == CareCampaignStatus.ACTIVE,
            or_(
                CareCampaign.end_date.is_(None),
                CareCampaign.end_date > datetime.now(timezone.utc)
            )
        ).order_by(desc(CareCampaign.created_at)).offset(skip).limit(limit).all()
    
    def get_campaign_with_analytics(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get campaign with analytics data."""
        campaign = self.get(campaign_id)
        if not campaign:
            return None
        
        analytics = self.db.query(CareAnalytics).filter(
            CareAnalytics.campaign_id == campaign_id
        ).first()
        
        return {
            "campaign": campaign,
            "analytics": analytics,
        }
    
    def update_budget_totals(self, campaign_id: str) -> None:
        """Update campaign budget totals from vouchers."""
        result = self.db.query(
            func.count(CareVoucher.id).label('total_vouchers'),
            func.sum(CareVoucher.budget_allocated).label('total_allocated'),
            func.sum(CareVoucher.budget_used).label('total_used'),
        ).filter(CareVoucher.campaign_id == campaign_id).first()
        
        campaign = self.get(campaign_id)
        if campaign:
            campaign.total_beneficiaries = result.total_vouchers or 0
            campaign.total_budget_allocated = result.total_allocated or Decimal("0")
            campaign.total_budget_used = result.total_used or Decimal("0")
            self.db.commit()


class CareBeneficiaryRepository(BaseRepository[CareBeneficiary]):
    """Repository for CareBeneficiary model."""
    
    def __init__(self, db: Session):
        super().__init__(db, CareBeneficiary)
    
    def get_by_campaign(self, campaign_id: str, is_active: bool = None,
                        skip: int = 0, limit: int = 20) -> Tuple[List[CareBeneficiary], int]:
        """Get beneficiaries by campaign ID."""
        query = self.db.query(CareBeneficiary).filter(
            CareBeneficiary.campaign_id == campaign_id
        )
        
        if is_active is not None:
            query = query.filter(CareBeneficiary.is_active == is_active)
        
        total = query.count()
        items = query.order_by(desc(CareBeneficiary.created_at)).offset(skip).limit(limit).all()
        
        return items, total
    
    def find_by_contact(self, campaign_id: str, phone: str = None,
                       email: str = None) -> Optional[CareBeneficiary]:
        """Find beneficiary by phone or email in a campaign."""
        conditions = [CareBeneficiary.campaign_id == campaign_id]
        
        if phone:
            conditions.append(CareBeneficiary.phone == phone)
        if email:
            conditions.append(CareBeneficiary.email == email)
        
        return self.db.query(CareBeneficiary).filter(and_(*conditions)).first()
    
    def get_with_voucher(self, beneficiary_id: str) -> Optional[Dict[str, Any]]:
        """Get beneficiary with voucher data."""
        beneficiary = self.get(beneficiary_id)
        if not beneficiary:
            return None
        
        voucher = self.db.query(CareVoucher).filter(
            CareVoucher.beneficiary_id == beneficiary_id
        ).first()
        
        return {
            "beneficiary": beneficiary,
            "voucher": voucher,
        }
    
    def update_access_times(self, beneficiary_id: str, is_first: bool = False) -> None:
        """Update access timestamps for a beneficiary."""
        beneficiary = self.get(beneficiary_id)
        if beneficiary:
            now = datetime.now(timezone.utc)
            if is_first:
                beneficiary.first_access_at = now
            beneficiary.last_access_at = now
            self.db.commit()


class CareVoucherRepository(BaseRepository[CareVoucher]):
    """Repository for CareVoucher model."""
    
    def __init__(self, db: Session):
        super().__init__(db, CareVoucher)
    
    def get_by_token(self, voucher_token: str) -> Optional[CareVoucher]:
        """Get voucher by token."""
        return self.db.query(CareVoucher).filter(
            CareVoucher.voucher_token == voucher_token
        ).first()
    
    def get_by_campaign(self, campaign_id: str, status: Optional[CareVoucherStatus] = None,
                        skip: int = 0, limit: int = 20) -> Tuple[List[CareVoucher], int]:
        """Get vouchers by campaign ID."""
        query = self.db.query(CareVoucher).filter(CareVoucher.campaign_id == campaign_id)
        
        if status:
            query = query.filter(CareVoucher.status == status)
        
        total = query.count()
        items = query.order_by(desc(CareVoucher.created_at)).offset(skip).limit(limit).all()
        
        return items, total
    
    def get_valid_voucher(self, voucher_token: str) -> Optional[CareVoucher]:
        """Get a valid (non-expired, usable) voucher by token."""
        voucher = self.get_by_token(voucher_token)
        
        if not voucher:
            return None
        
        if voucher.status in [CareVoucherStatus.EXPIRED, CareVoucherStatus.CANCELLED, CareVoucherStatus.COMPLETED]:
            return None
        
        if voucher.expires_at < datetime.now(timezone.utc):
            voucher.status = CareVoucherStatus.EXPIRED
            self.db.commit()
            return None
        
        return voucher
    
    def mark_accessed(self, voucher_id: str) -> None:
        """Mark voucher as accessed."""
        voucher = self.get(voucher_id)
        if voucher:
            voucher.accessed_at = datetime.now(timezone.utc)
            if voucher.status == CareVoucherStatus.SENT:
                voucher.status = CareVoucherStatus.ACCESSED
            self.db.commit()
    
    def update_balance(self, voucher_id: str, amount: Decimal) -> CareVoucher:
        """Update voucher balance after usage."""
        voucher = self.get(voucher_id)
        if voucher:
            voucher.budget_used = voucher.budget_used + amount
            voucher.budget_remaining = voucher.budget_remaining - amount
            
            if voucher.budget_remaining <= 0:
                voucher.status = CareVoucherStatus.COMPLETED
                voucher.completed_at = datetime.now(timezone.utc)
            else:
                voucher.status = CareVoucherStatus.PARTIALLY_USED
            
            self.db.commit()
        
        return voucher
    
    def get_expiring_vouchers(self, days: int = 7) -> List[CareVoucher]:
        """Get vouchers expiring within specified days."""
        expiry_threshold = datetime.now(timezone.utc) + timedelta(days=days)
        
        return self.db.query(CareVoucher).filter(
            CareVoucher.status.in_([
                CareVoucherStatus.ACTIVE,
                CareVoucherStatus.PARTIALLY_USED,
                CareVoucherStatus.SENT,
                CareVoucherStatus.ACCESSED
            ]),
            CareVoucher.expires_at <= expiry_threshold,
            CareVoucher.expires_at > datetime.now(timezone.utc)
        ).all()


class CareSessionRepository(BaseRepository[CareSession]):
    """Repository for CareSession model."""
    
    def __init__(self, db: Session):
        super().__init__(db, CareSession)
    
    def get_by_token(self, session_token: str) -> Optional[CareSession]:
        """Get session by token."""
        return self.db.query(CareSession).filter(
            CareSession.session_token == session_token
        ).first()
    
    def get_active_session(self, voucher_id: str) -> Optional[CareSession]:
        """Get active session for a voucher."""
        return self.db.query(CareSession).filter(
            CareSession.voucher_id == voucher_id,
            CareSession.status.in_([
                CareSessionStatus.ACTIVE,
                CareSessionStatus.OTP_SENT,
                CareSessionStatus.OTP_VERIFIED
            ]),
            CareSession.expires_at > datetime.now(timezone.utc)
        ).first()
    
    def get_valid_session(self, session_token: str) -> Optional[CareSession]:
        """Get a valid (non-expired) session by token."""
        session = self.get_by_token(session_token)
        
        if not session:
            return None
        
        if session.expires_at < datetime.now(timezone.utc):
            session.status = CareSessionStatus.EXPIRED
            self.db.commit()
            return None
        
        return session
    
    def update_activity(self, session_id: str) -> None:
        """Update last activity timestamp."""
        session = self.get(session_id)
        if session:
            session.last_activity_at = datetime.now(timezone.utc)
            self.db.commit()
    
    def increment_otp_attempts(self, session_id: str) -> int:
        """Increment OTP attempts and return new count."""
        session = self.get(session_id)
        if session:
            session.otp_attempts += 1
            self.db.commit()
            return session.otp_attempts
        return 0
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count."""
        result = self.db.query(CareSession).filter(
            CareSession.expires_at < datetime.now(timezone.utc),
            CareSession.status.notin_([
                CareSessionStatus.COMPLETED,
                CareSessionStatus.EXPIRED
            ])
        ).update({
            "status": CareSessionStatus.EXPIRED
        }, synchronize_session=False)
        
        self.db.commit()
        return result


class CareOrderRepository(BaseRepository[CareOrder]):
    """Repository for CareOrder model."""
    
    def __init__(self, db: Session):
        super().__init__(db, CareOrder)
    
    def get_by_voucher(self, voucher_id: str, skip: int = 0, 
                       limit: int = 20) -> Tuple[List[CareOrder], int]:
        """Get orders by voucher ID."""
        query = self.db.query(CareOrder).filter(CareOrder.voucher_id == voucher_id)
        
        total = query.count()
        items = query.order_by(desc(CareOrder.created_at)).offset(skip).limit(limit).all()
        
        return items, total
    
    def get_by_campaign(self, campaign_id: str, skip: int = 0,
                        limit: int = 20) -> Tuple[List[CareOrder], int]:
        """Get orders by campaign ID."""
        query = self.db.query(CareOrder).join(CareVoucher).filter(
            CareVoucher.campaign_id == campaign_id
        )
        
        total = query.count()
        items = query.order_by(desc(CareOrder.created_at)).offset(skip).limit(limit).all()
        
        return items, total
    
    def get_by_beneficiary(self, beneficiary_id: str, skip: int = 0,
                           limit: int = 20) -> Tuple[List[CareOrder], int]:
        """Get orders by beneficiary ID."""
        query = self.db.query(CareOrder).filter(CareOrder.beneficiary_id == beneficiary_id)
        
        total = query.count()
        items = query.order_by(desc(CareOrder.created_at)).offset(skip).limit(limit).all()
        
        return items, total
    
    def get_order_totals(self, campaign_id: str) -> Dict[str, Any]:
        """Get order totals for a campaign."""
        result = self.db.query(
            func.count(CareOrder.id).label('total_orders'),
            func.sum(CareOrder.total_amount).label('total_amount'),
            func.sum(CareOrder.items_count).label('total_items'),
            func.avg(CareOrder.total_amount).label('avg_order_value'),
        ).join(CareVoucher).filter(
            CareVoucher.campaign_id == campaign_id
        ).first()
        
        return {
            "total_orders": result.total_orders or 0,
            "total_amount": float(result.total_amount or 0),
            "total_items": result.total_items or 0,
            "avg_order_value": float(result.avg_order_value or 0),
        }


class CareAnalyticsRepository(BaseRepository[CareAnalytics]):
    """Repository for CareAnalytics model."""
    
    def __init__(self, db: Session):
        super().__init__(db, CareAnalytics)
    
    def get_by_campaign(self, campaign_id: str) -> Optional[CareAnalytics]:
        """Get analytics by campaign ID."""
        return self.db.query(CareAnalytics).filter(
            CareAnalytics.campaign_id == campaign_id
        ).first()
    
    def recalculate_analytics(self, campaign_id: str) -> CareAnalytics:
        """Recalculate all analytics for a campaign."""
        analytics = self.get_by_campaign(campaign_id)
        
        if not analytics:
            analytics = CareAnalytics(campaign_id=campaign_id)
            self.db.add(analytics)
        
        # Get voucher counts
        voucher_stats = self.db.query(
            func.count(CareVoucher.id).label('total'),
            func.sum(
                func.case(
                    [(CareVoucher.status == CareVoucherStatus.SENT, 1)],
                    else_=0
                )
            ).label('sent'),
            func.sum(
                func.case(
                    [CareVoucher.accessed_at.isnot(None), 1],
                    else_=0
                )
            ).label('accessed'),
            func.sum(
                func.case(
                    [(CareVoucher.status == CareVoucherStatus.COMPLETED, 1)],
                    else_=0
                )
            ).label('completed'),
            func.sum(
                func.case(
                    [(CareVoucher.status == CareVoucherStatus.EXPIRED, 1)],
                    else_=0
                )
            ).label('expired'),
        ).filter(CareVoucher.campaign_id == campaign_id).first()
        
        analytics.total_vouchers_created = voucher_stats.total or 0
        analytics.vouchers_sent = voucher_stats.sent or 0
        analytics.vouchers_accessed = voucher_stats.accessed or 0
        analytics.vouchers_completed = voucher_stats.completed or 0
        analytics.vouchers_expired = voucher_stats.expired or 0
        
        # Get financial stats
        financial_stats = self.db.query(
            func.sum(CareVoucher.budget_allocated).label('allocated'),
            func.sum(CareVoucher.budget_used).label('used'),
            func.avg(CareVoucher.budget_used).label('avg_spend'),
        ).filter(CareVoucher.campaign_id == campaign_id).first()
        
        analytics.total_budget_allocated = financial_stats.allocated or Decimal("0")
        analytics.total_budget_used = financial_stats.used or Decimal("0")
        analytics.average_spend_per_beneficiary = financial_stats.avg_spend or Decimal("0")
        
        # Calculate rates
        if analytics.total_vouchers_created > 0:
            analytics.engagement_rate = Decimal(str(
                round(analytics.vouchers_accessed / analytics.total_vouchers_created * 100, 2)
            ))
        
        if analytics.vouchers_accessed > 0:
            analytics.completion_rate = Decimal(str(
                round(analytics.vouchers_completed / analytics.vouchers_accessed * 100, 2)
            ))
        
        # Get order stats
        order_stats = self.db.query(
            func.count(CareOrder.id).label('total_orders'),
            func.avg(CareOrder.total_amount).label('avg_order'),
            func.sum(CareOrder.items_count).label('total_items'),
        ).join(CareVoucher).filter(
            CareVoucher.campaign_id == campaign_id
        ).first()
        
        analytics.total_products_purchased = order_stats.total_items or 0
        analytics.average_order_value = order_stats.avg_order or Decimal("0")
        analytics.total_sessions = order_stats.total_orders or 0
        
        self.db.commit()
        return analytics


class CareAuditLogRepository(BaseRepository[CareAuditLog]):
    """Repository for CareAuditLog model."""
    
    def __init__(self, db: Session):
        super().__init__(db, CareAuditLog)
    
    def get_by_campaign(self, campaign_id: str, action_category: str = None,
                        skip: int = 0, limit: int = 50) -> Tuple[List[CareAuditLog], int]:
        """Get audit logs by campaign ID."""
        query = self.db.query(CareAuditLog).filter(
            CareAuditLog.campaign_id == campaign_id
        )
        
        if action_category:
            query = query.filter(CareAuditLog.action_category == action_category)
        
        total = query.count()
        items = query.order_by(desc(CareAuditLog.timestamp)).offset(skip).limit(limit).all()
        
        return items, total
    
    def get_by_voucher(self, voucher_id: str, skip: int = 0,
                       limit: int = 50) -> Tuple[List[CareAuditLog], int]:
        """Get audit logs by voucher ID."""
        query = self.db.query(CareAuditLog).filter(
            CareAuditLog.voucher_id == voucher_id
        )
        
        total = query.count()
        items = query.order_by(desc(CareAuditLog.timestamp)).offset(skip).limit(limit).all()
        
        return items, total
    
    def get_by_date_range(self, campaign_id: str, start_date: datetime,
                          end_date: datetime, skip: int = 0,
                          limit: int = 100) -> Tuple[List[CareAuditLog], int]:
        """Get audit logs within a date range."""
        query = self.db.query(CareAuditLog).filter(
            CareAuditLog.campaign_id == campaign_id,
            CareAuditLog.timestamp >= start_date,
            CareAuditLog.timestamp <= end_date
        )
        
        total = query.count()
        items = query.order_by(desc(CareAuditLog.timestamp)).offset(skip).limit(limit).all()
        
        return items, total
    
    def get_action_summary(self, campaign_id: str) -> Dict[str, int]:
        """Get summary of actions by type for a campaign."""
        result = self.db.query(
            CareAuditLog.action,
            func.count(CareAuditLog.id).label('count')
        ).filter(
            CareAuditLog.campaign_id == campaign_id
        ).group_by(CareAuditLog.action).all()
        
        return {row.action: row.count for row in result}
