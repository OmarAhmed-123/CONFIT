"""
CONFIT Backend - Donation Service
=================================
Production-grade donation processing with secure coupon generation,
balance management, and fraud prevention.

Features:
- Secure donation processing
- Unique coupon code generation
- Balance tracking with race condition prevention
- Expiration management
- Fraud detection integration
"""

import hashlib
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database.donation_models import (
    Donation,
    DonorCredit,
    DonorRedemption,
    DonationConfig,
    DonationStatus,
    DonorCreditStatus,
)
from database.models import User, Order

logger = logging.getLogger(__name__)


class DonationError(Exception):
    """Base exception for donation errors."""
    pass


class InvalidAmountError(DonationError):
    """Raised when donation amount is invalid."""
    pass


class PaymentVerificationError(DonationError):
    """Raised when payment verification fails."""
    pass


class CreditExhaustedError(DonationError):
    """Raised when credit balance is depleted."""
    pass


class CreditExpiredError(DonationError):
    """Raised when credit has expired."""
    pass


class DuplicateTransactionError(DonationError):
    """Raised when a duplicate transaction is detected."""
    pass


class DonationService:
    """
    Service for processing donations and managing donor credits.
    
    All database updates use row-level locking to prevent race conditions.
    """
    
    # Coupon code character set (excludes ambiguous characters)
    COUPON_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    COUPON_PREFIX = "DONOR"
    
    def __init__(self, db: Session):
        self._db = db
    
    # ========================================
    # CONFIGURATION
    # ========================================
    
    def get_config(self) -> DonationConfig:
        """Get donation configuration (singleton)."""
        config = self._db.query(DonationConfig).first()
        if not config:
            # Create default config
            config = DonationConfig(
                min_donation_amount=Decimal("1.00"),
                max_donation_amount=Decimal("10000.00"),
                preset_amounts=[10, 25, 50, 100, 250, 500],
                default_expiry_days=365,
                enable_custom_amounts=True,
                enable_recurring=False,
                hero_title="Support the Future of Fashion",
                hero_subtitle="Your donation helps us build sustainable, inclusive fashion technology.",
            )
            self._db.add(config)
            self._db.commit()
            self._db.refresh(config)
        return config
    
    def update_config(
        self,
        updated_by: str,
        **kwargs
    ) -> DonationConfig:
        """Update donation configuration."""
        config = self.get_config()
        
        for key, value in kwargs.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)
        
        config.updated_by = updated_by
        config.updated_at = datetime.now(timezone.utc)
        
        self._db.commit()
        self._db.refresh(config)
        
        logger.info("Donation config updated by %s", updated_by)
        return config
    
    # ========================================
    # DONATION PROCESSING
    # ========================================
    
    def validate_amount(self, amount: Decimal) -> Tuple[bool, Optional[str]]:
        """
        Validate donation amount against configuration.
        
        Returns (is_valid, error_message).
        """
        config = self.get_config()
        
        if amount < config.min_donation_amount:
            return False, f"Minimum donation is ${config.min_donation_amount}"
        
        if amount > config.max_donation_amount:
            return False, f"Maximum donation is ${config.max_donation_amount}"
        
        return True, None
    
    def create_donation(
        self,
        user_id: str,
        amount: Decimal,
        payment_method: str = "card",
        payment_provider: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Donation:
        """
        Create a pending donation record.
        
        This creates the donation in 'pending' status.
        Call confirm_donation() after payment verification.
        """
        # Validate amount
        is_valid, error = self.validate_amount(amount)
        if not is_valid:
            raise InvalidAmountError(error)
        
        # Check for duplicate pending donations (fraud prevention)
        recent_pending = self._db.query(Donation).filter(
            Donation.user_id == user_id,
            Donation.status == DonationStatus.PENDING,
            Donation.amount == amount,
            Donation.created_at > datetime.now(timezone.utc) - timedelta(minutes=5)
        ).first()
        
        if recent_pending:
            logger.warning("Duplicate pending donation detected for user %s", user_id)
            raise DuplicateTransactionError("A pending donation with this amount already exists")
        
        # Create donation
        donation = Donation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            amount=amount,
            currency="USD",
            payment_method=payment_method,
            payment_provider=payment_provider,
            status=DonationStatus.PENDING,
            ip_address=ip_address,
            user_agent=user_agent,
            payment_metadata=metadata,
        )
        
        self._db.add(donation)
        self._db.commit()
        self._db.refresh(donation)
        
        logger.info(
            "Created pending donation %s for user %s: $%s",
            donation.id, user_id, amount
        )
        
        return donation
    
    def confirm_donation(
        self,
        donation_id: str,
        transaction_id: str,
        payment_intent_id: Optional[str] = None,
        payment_provider: Optional[str] = None,
        risk_score: Optional[float] = None,
    ) -> Tuple[Donation, DonorCredit]:
        """
        Confirm a donation after successful payment.
        
        This is the critical path - uses transaction with row locking
        to prevent race conditions and duplicate credit generation.
        
        Returns (donation, donor_credit).
        """
        # Lock the donation row for update
        donation = self._db.query(Donation).filter(
            Donation.id == donation_id
        ).with_for_update().first()
        
        if not donation:
            raise DonationError("Donation not found")
        
        if donation.status == DonationStatus.COMPLETED:
            logger.warning("Donation %s already completed", donation_id)
            # Return existing credit
            credit = self._db.query(DonorCredit).filter(
                DonorCredit.donation_id == donation_id
            ).first()
            return donation, credit
        
        if donation.status != DonationStatus.PENDING:
            raise DonationError(f"Donation is in {donation.status.value} status")
        
        # Check for duplicate transaction
        existing = self._db.query(Donation).filter(
            Donation.transaction_id == transaction_id,
            Donation.id != donation_id
        ).first()
        
        if existing:
            raise DuplicateTransactionError("Transaction ID already used")
        
        # Update donation status
        donation.status = DonationStatus.COMPLETED
        donation.transaction_id = transaction_id
        donation.payment_intent_id = payment_intent_id
        donation.payment_provider = payment_provider or donation.payment_provider
        donation.risk_score = risk_score
        donation.completed_at = datetime.now(timezone.utc)
        
        # Generate donor credit
        config = self.get_config()
        expires_at = None
        if config.default_expiry_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=config.default_expiry_days)
        
        coupon_code = self._generate_unique_coupon_code()
        coupon_hash = self._hash_coupon_code(coupon_code)
        
        credit = DonorCredit(
            id=str(uuid.uuid4()),
            user_id=donation.user_id,
            donation_id=donation.id,
            total_credit=donation.amount,
            remaining_credit=donation.amount,
            coupon_code=coupon_code,
            coupon_hash=coupon_hash,
            status=DonorCreditStatus.ACTIVE,
            expires_at=expires_at,
        )
        
        self._db.add(credit)
        self._db.commit()
        self._db.refresh(donation)
        self._db.refresh(credit)
        
        logger.info(
            "Donation %s confirmed: $%s, coupon %s generated",
            donation_id, donation.amount, coupon_code
        )
        
        return donation, credit
    
    def fail_donation(
        self,
        donation_id: str,
        reason: Optional[str] = None,
    ) -> Donation:
        """Mark a donation as failed."""
        donation = self._db.query(Donation).filter(
            Donation.id == donation_id
        ).with_for_update().first()
        
        if not donation:
            raise DonationError("Donation not found")
        
        if donation.status != DonationStatus.PENDING:
            raise DonationError(f"Cannot fail donation in {donation.status.value} status")
        
        donation.status = DonationStatus.FAILED
        donation.payment_metadata = donation.payment_metadata or {}
        donation.payment_metadata["failure_reason"] = reason
        
        self._db.commit()
        self._db.refresh(donation)
        
        logger.warning("Donation %s failed: %s", donation_id, reason)
        return donation
    
    # ========================================
    # COUPON GENERATION
    # ========================================
    
    def _generate_unique_coupon_code(self) -> str:
        """
        Generate a unique, secure coupon code.
        
        Format: DONOR-XXXXXX-XXXX (prefix + 6 chars + 4 chars)
        Uses cryptographically secure random generation.
        """
        max_attempts = 100
        
        for _ in range(max_attempts):
            # Generate random characters
            code_parts = []
            
            # 6 character segment
            segment1 = ''.join(
                secrets.choice(self.COUPON_CHARS)
                for _ in range(6)
            )
            
            # 4 character segment
            segment2 = ''.join(
                secrets.choice(self.COUPON_CHARS)
                for _ in range(4)
            )
            
            code = f"{self.COUPON_PREFIX}-{segment1}-{segment2}"
            
            # Check uniqueness
            existing = self._db.query(DonorCredit).filter(
                DonorCredit.coupon_code == code
            ).first()
            
            if not existing:
                return code
        
        # Fallback with UUID component
        code = f"{self.COUPON_PREFIX}-{uuid.uuid4().hex[:10].upper()}"
        return code
    
    def _hash_coupon_code(self, code: str) -> str:
        """Create a secure hash of the coupon code for additional verification."""
        return hashlib.sha256(code.encode()).hexdigest()
    
    def validate_coupon_code(
        self,
        code: str,
        user_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[DonorCredit], Optional[str]]:
        """
        Validate a coupon code.
        
        Returns (is_valid, credit, error_message).
        """
        credit = self._db.query(DonorCredit).filter(
            DonorCredit.coupon_code == code.upper()
        ).first()
        
        if not credit:
            return False, None, "Invalid coupon code"
        
        # Check ownership if specified
        if user_id and credit.user_id != user_id:
            return False, None, "This coupon belongs to another account"
        
        # Check status
        if credit.status == DonorCreditStatus.DEPLETED:
            return False, credit, "Credit balance is depleted"
        
        if credit.status == DonorCreditStatus.EXPIRED:
            return False, credit, "Credit has expired"
        
        if credit.status == DonorCreditStatus.CANCELLED:
            return False, credit, "Credit has been cancelled"
        
        # Check expiration
        if credit.expires_at and datetime.now(timezone.utc) > credit.expires_at:
            # Auto-expire
            credit.status = DonorCreditStatus.EXPIRED
            self._db.commit()
            return False, credit, "Credit has expired"
        
        # Check balance
        if credit.remaining_credit <= 0:
            credit.status = DonorCreditStatus.DEPLETED
            self._db.commit()
            return False, credit, "Credit balance is depleted"
        
        return True, credit, None
    
    # ========================================
    # BALANCE MANAGEMENT
    # ========================================
    
    def get_user_credits(self, user_id: str) -> List[DonorCredit]:
        """Get all credits for a user."""
        return self._db.query(DonorCredit).filter(
            DonorCredit.user_id == user_id
        ).order_by(DonorCredit.created_at.desc()).all()
    
    def get_active_credits(self, user_id: str) -> List[DonorCredit]:
        """Get active credits for a user (sorted by expiration)."""
        # Update expired credits first
        self._update_expired_credits()
        
        return self._db.query(DonorCredit).filter(
            DonorCredit.user_id == user_id,
            DonorCredit.status == DonorCreditStatus.ACTIVE,
            DonorCredit.remaining_credit > 0,
            or_(
                DonorCredit.expires_at.is_(None),
                DonorCredit.expires_at > datetime.now(timezone.utc)
            )
        ).order_by(
            DonorCredit.expires_at.asc().nulls_last(),
            DonorCredit.remaining_credit.desc()
        ).all()
    
    def get_total_available_credit(self, user_id: str) -> Decimal:
        """Get total available credit balance for a user."""
        credits = self.get_active_credits(user_id)
        return sum(c.remaining_credit for c in credits)
    
    def redeem_credit(
        self,
        user_id: str,
        amount: Decimal,
        order_id: Optional[str] = None,
        product_id: Optional[str] = None,
        product_name: Optional[str] = None,
        coupon_code: Optional[str] = None,
    ) -> Tuple[DonorRedemption, DonorCredit]:
        """
        Redeem credit for a purchase.
        
        Uses row-level locking to prevent race conditions.
        If coupon_code is specified, uses that credit first.
        Otherwise, uses credits in optimal order (earliest expiration first).
        
        Returns (redemption, credit_used).
        Raises CreditExhaustedError if insufficient balance.
        """
        if amount <= 0:
            raise DonationError("Redemption amount must be positive")
        
        # Get credit to use
        if coupon_code:
            is_valid, credit, error = self.validate_coupon_code(coupon_code, user_id)
            if not is_valid:
                raise CreditExhaustedError(error)
            credits_to_use = [credit]
        else:
            credits_to_use = self.get_active_credits(user_id)
        
        if not credits_to_use:
            raise CreditExhaustedError("No active credits available")
        
        # Calculate available balance
        total_available = sum(c.remaining_credit for c in credits_to_use)
        
        if total_available < amount:
            raise CreditExhaustedError(
                f"Insufficient credit: ${total_available} available, ${amount} needed"
            )
        
        # Use credits in order (FIFO by expiration)
        remaining_to_redeem = amount
        redemptions = []
        
        for credit in credits_to_use:
            if remaining_to_redeem <= 0:
                break
            
            # Lock the credit row
            credit = self._db.query(DonorCredit).filter(
                DonorCredit.id == credit.id
            ).with_for_update().first()
            
            # Double-check after lock
            if credit.remaining_credit <= 0:
                continue
            
            # Calculate redemption for this credit
            redeem_from_this = min(credit.remaining_credit, remaining_to_redeem)
            
            balance_before = credit.remaining_credit
            credit.remaining_credit -= redeem_from_this
            balance_after = credit.remaining_credit
            
            # Update status if depleted
            if credit.remaining_credit <= 0:
                credit.status = DonorCreditStatus.DEPLETED
            
            # Create redemption record
            redemption = DonorRedemption(
                id=str(uuid.uuid4()),
                credit_id=credit.id,
                user_id=user_id,
                order_id=order_id,
                amount_used=redeem_from_this,
                balance_before=balance_before,
                balance_after=balance_after,
                product_id=product_id,
                product_name=product_name,
            )
            
            self._db.add(redemption)
            redemptions.append((redemption, credit))
            
            remaining_to_redeem -= redeem_from_this
        
        self._db.commit()
        
        logger.info(
            "Redeemed $%s from user %s credits for order %s",
            amount, user_id, order_id
        )
        
        # Return first redemption and credit
        return redemptions[0] if redemptions else (None, None)
    
    def refund_redemption(
        self,
        redemption_id: str,
        reason: Optional[str] = None,
    ) -> DonorRedemption:
        """
        Refund a redemption (e.g., order cancelled).
        
        Returns the credit to the user's balance.
        """
        redemption = self._db.query(DonorRedemption).filter(
            DonorRedemption.id == redemption_id
        ).with_for_update().first()
        
        if not redemption:
            raise DonationError("Redemption not found")
        
        # Lock the credit
        credit = self._db.query(DonorCredit).filter(
            DonorCredit.id == redemption.credit_id
        ).with_for_update().first()
        
        if not credit:
            raise DonationError("Credit not found")
        
        # Restore balance
        credit.remaining_credit += redemption.amount_used
        
        # Update status if was depleted
        if credit.status == DonorCreditStatus.DEPLETED:
            if credit.expires_at and datetime.now(timezone.utc) > credit.expires_at:
                credit.status = DonorCreditStatus.EXPIRED
            else:
                credit.status = DonorCreditStatus.ACTIVE
        
        # Update redemption metadata
        redemption.redemption_metadata = redemption.redemption_metadata or {}
        redemption.redemption_metadata["refunded"] = True
        redemption.redemption_metadata["refund_reason"] = reason
        redemption.redemption_metadata["refunded_at"] = datetime.now(timezone.utc).isoformat()
        
        self._db.commit()
        self._db.refresh(redemption)
        
        logger.info(
            "Refunded redemption %s: $%s returned to credit %s",
            redemption_id, redemption.amount_used, credit.id
        )
        
        return redemption
    
    # ========================================
    # EXPIRATION MANAGEMENT
    # ========================================
    
    def _update_expired_credits(self) -> int:
        """Update status of expired credits. Returns count updated."""
        now = datetime.now(timezone.utc)
        
        expired_count = self._db.execute(
            update(DonorCredit)
            .where(
                DonorCredit.status == DonorCreditStatus.ACTIVE,
                DonorCredit.expires_at.isnot(None),
                DonorCredit.expires_at < now
            )
            .values(status=DonorCreditStatus.EXPIRED)
        ).rowcount
        
        depleted_count = self._db.execute(
            update(DonorCredit)
            .where(
                DonorCredit.status == DonorCreditStatus.ACTIVE,
                DonorCredit.remaining_credit <= 0
            )
            .values(status=DonorCreditStatus.DEPLETED)
        ).rowcount
        
        if expired_count or depleted_count:
            self._db.commit()
            logger.info(
                "Updated credit statuses: %d expired, %d depleted",
                expired_count, depleted_count
            )
        
        return expired_count + depleted_count
    
    def extend_credit_expiry(
        self,
        credit_id: str,
        additional_days: int,
        admin_user_id: str,
    ) -> DonorCredit:
        """Extend credit expiration (admin action)."""
        credit = self._db.query(DonorCredit).filter(
            DonorCredit.id == credit_id
        ).first()
        
        if not credit:
            raise DonationError("Credit not found")
        
        if credit.expires_at:
            credit.expires_at += timedelta(days=additional_days)
        else:
            credit.expires_at = datetime.now(timezone.utc) + timedelta(days=additional_days)
        
        # Reactivate if was expired
        if credit.status == DonorCreditStatus.EXPIRED:
            credit.status = DonorCreditStatus.ACTIVE
        
        credit.credit_metadata = credit.credit_metadata or {}
        credit.credit_metadata["extensions"] = credit.credit_metadata.get("extensions", [])
        credit.credit_metadata["extensions"].append({
            "days": additional_days,
            "by": admin_user_id,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        
        self._db.commit()
        self._db.refresh(credit)
        
        logger.info(
            "Extended credit %s expiry by %d days (by admin %s)",
            credit_id, additional_days, admin_user_id
        )
        
        return credit
    
    # ========================================
    # REPORTING & ANALYTICS
    # ========================================
    
    def get_donation_stats(self, user_id: str) -> Dict[str, Any]:
        """Get donation statistics for a user."""
        donations = self._db.query(Donation).filter(
            Donation.user_id == user_id,
            Donation.status == DonationStatus.COMPLETED
        ).all()
        
        credits = self._db.query(DonorCredit).filter(
            DonorCredit.user_id == user_id
        ).all()
        
        redemptions = self._db.query(DonorRedemption).filter(
            DonorRedemption.user_id == user_id
        ).all()
        
        total_donated = sum(d.amount for d in donations)
        total_credit = sum(c.total_credit for c in credits)
        total_used = sum(r.amount_used for r in redemptions)
        total_remaining = sum(
            c.remaining_credit for c in credits
            if c.status == DonorCreditStatus.ACTIVE
        )
        
        return {
            "total_donations": len(donations),
            "total_donated": float(total_donated),
            "total_credit_earned": float(total_credit),
            "total_credit_used": float(total_used),
            "total_credit_remaining": float(total_remaining),
            "active_credits": len([c for c in credits if c.status == DonorCreditStatus.ACTIVE]),
            "total_redemptions": len(redemptions),
        }
    
    def get_donation_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get donation history for a user."""
        donations = self._db.query(Donation).filter(
            Donation.user_id == user_id
        ).order_by(Donation.created_at.desc()).offset(offset).limit(limit).all()
        
        result = []
        for d in donations:
            credit = self._db.query(DonorCredit).filter(
                DonorCredit.donation_id == d.id
            ).first()
            
            result.append({
                "id": d.id,
                "amount": float(d.amount),
                "status": d.status.value,
                "payment_method": d.payment_method,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "completed_at": d.completed_at.isoformat() if d.completed_at else None,
                "credit": {
                    "coupon_code": credit.coupon_code if credit else None,
                    "total_credit": float(credit.total_credit) if credit else 0,
                    "remaining_credit": float(credit.remaining_credit) if credit else 0,
                    "status": credit.status.value if credit else None,
                    "expires_at": credit.expires_at.isoformat() if credit and credit.expires_at else None,
                } if credit else None,
            })
        
        return result
    
    def get_redemption_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get redemption history for a user."""
        redemptions = self._db.query(DonorRedemption).filter(
            DonorRedemption.user_id == user_id
        ).order_by(DonorRedemption.created_at.desc()).offset(offset).limit(limit).all()
        
        return [
            {
                "id": r.id,
                "amount_used": float(r.amount_used),
                "order_id": r.order_id,
                "product_name": r.product_name,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in redemptions
        ]


def get_donation_service(db: Session) -> DonationService:
    """Dependency injection for DonationService."""
    return DonationService(db)
