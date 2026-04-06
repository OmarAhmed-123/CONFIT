"""
CONFIT Backend - Donation Payment Flow Integration (Phase 4)
============================================================
Integration between payment orchestrator and donor service.

Hooks into payment webhooks to process donations on successful payment.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.donation_models import Donor, DonationRecord, Coupon
from database.payment_platform_models import Payment, PaymentStatus
from database.models import User
from services.donor_service import DonorService

logger = logging.getLogger(__name__)


@dataclass
class DonationPaymentRequest:
    """Request to create a donation payment."""
    user_id: str
    amount_egp: Decimal
    currency: str = "EGP"
    is_anonymous: bool = False
    display_name: Optional[str] = None
    message: Optional[str] = None
    coupon_config: Optional[Dict[str, Any]] = None
    billing: Optional[Dict[str, str]] = None


@dataclass
class DonationPaymentResult:
    """Result of donation payment creation."""
    payment_id: str
    donor_id: str
    payment_session: Dict[str, Any]
    provider: str


class DonationPaymentFlow:
    """
    Handles donation payment flow integration.
    
    Flow:
    1. create_donation_payment() - Creates payment session and donor if needed
    2. on_payment_webhook() - Called by webhook handler on payment success
    3. process_successful_donation() - Creates donation record and coupon
    """
    
    # Donation-specific metadata keys
    METADATA_DONATION = "is_donation"
    METADATA_DONOR_ID = "donor_id"
    METADATA_COUPON_CONFIG = "coupon_config"
    METADATA_MESSAGE = "donation_message"
    
    def __init__(self, db: AsyncSession):
        self._db = db
        self._donor_service = DonorService(db)
    
    async def create_donation_payment(
        self,
        request: DonationPaymentRequest,
        provider: str = "paymob",  # Default to Paymob for Egypt
        idempotency_key: Optional[str] = None,
    ) -> DonationPaymentResult:
        """
        Create a donation payment session.
        
        This:
        1. Registers donor if not exists
        2. Creates a payment session via payment orchestrator
        3. Stores donation metadata in payment record
        
        Args:
            request: Donation payment request details
            provider: Payment provider (paymob, fawry, stripe)
            idempotency_key: Optional idempotency key
            
        Returns:
            DonationPaymentResult with payment session details
        """
        # Get or create donor
        donor = await self._donor_service.get_donor_by_user_id(request.user_id)
        if not donor:
            donor = await self._donor_service.register_donor(
                user_id=request.user_id,
                display_name=request.display_name,
                is_anonymous=request.is_anonymous,
            )
        
        # Create payment via orchestrator
        from services.payment_platform.orchestrator import create_payment_session
        
        # Create a virtual order for the donation
        # In production, this would create a DonationOrder record
        order_id = await self._create_donation_order(
            donor_id=donor.id,
            amount_egp=request.amount_egp,
            currency=request.currency,
        )
        
        # Build billing info
        billing = request.billing or {}
        billing["currency"] = request.currency
        
        # Create payment session
        payment_session = await create_payment_session(
            db=self._db.sync_session,  # type: ignore
            order_id=order_id,
            provider=provider,
            user_id=request.user_id,
            idempotency_key=idempotency_key,
            billing=billing,
        )
        
        # Store donation metadata in payment
        payment_id = payment_session.get("payment_record_id")
        if payment_id:
            await self._store_donation_metadata(
                payment_id=payment_id,
                donor_id=donor.id,
                coupon_config=request.coupon_config,
                message=request.message,
            )
        
        logger.info(
            "Created donation payment %s for donor %s (%.2f EGP via %s)",
            payment_id, donor.id, request.amount_egp, provider
        )
        
        return DonationPaymentResult(
            payment_id=payment_id,
            donor_id=donor.id,
            payment_session=payment_session,
            provider=provider,
        )
    
    async def on_payment_webhook(
        self,
        payment_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> bool:
        """
        Handle payment webhook for donation.
        
        Called by webhook handler when payment event is received.
        Routes to appropriate handler based on event type.
        
        Args:
            payment_id: Payment record ID
            event_type: Webhook event type (e.g., "payment_succeeded")
            payload: Webhook payload
            
        Returns:
            True if donation was processed, False if not a donation
        """
        # Check if this is a donation payment
        payment = await self._get_payment(payment_id)
        if not payment:
            return False
        
        # Check donation metadata
        metadata = payment.client_payload or {}
        if not metadata.get(self.METADATA_DONATION):
            return False  # Not a donation payment
        
        donor_id = metadata.get(self.METADATA_DONOR_ID)
        if not donor_id:
            logger.warning("Donation payment %s missing donor_id", payment_id)
            return False
        
        if event_type == "payment_succeeded":
            await self.process_successful_donation(
                payment_id=payment_id,
                donor_id=donor_id,
                metadata=metadata,
            )
            return True
        
        elif event_type == "payment_failed":
            await self._handle_failed_donation(payment_id, donor_id)
            return True
        
        return False
    
    async def process_successful_donation(
        self,
        payment_id: str,
        donor_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a successful donation payment.
        
        Creates donation record, updates donor tier, creates coupon if configured.
        
        Args:
            payment_id: Payment record ID
            donor_id: Donor ID
            metadata: Donation metadata from payment
            
        Returns:
            Dict with donation_id and coupon_id (if created)
        """
        payment = await self._get_payment(payment_id)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")
        
        # Convert amount from cents to EGP
        amount_egp = Decimal(payment.amount_cents) / 100
        
        # Get coupon config from metadata
        coupon_config = None
        message = None
        if metadata:
            coupon_config = metadata.get(self.METADATA_COUPON_CONFIG)
            message = metadata.get(self.METADATA_MESSAGE)
        
        # Process donation via donor service
        donation, coupon = await self._donor_service.on_payment_success(
            payment_id=payment_id,
            donor_id=donor_id,
            amount_egp=amount_egp,
            coupon_config=coupon_config,
            message=message,
        )
        
        result = {
            "donation_id": donation.id,
            "donor_id": donor_id,
            "amount_egp": float(amount_egp),
            "tier": (await self._donor_service.get_donor_by_id(donor_id)).tier.value,
        }
        
        if coupon:
            result["coupon_id"] = coupon.id
            result["coupon_code"] = coupon.code
        
        logger.info(
            "Processed successful donation %s (%.2f EGP) for donor %s",
            donation.id, amount_egp, donor_id
        )
        
        return result
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    async def _create_donation_order(
        self,
        donor_id: str,
        amount_egp: Decimal,
        currency: str,
    ) -> str:
        """
        Create a virtual order for donation.
        
        In production, this would create a DonationOrder record
        that links to the payments table.
        """
        import uuid
        order_id = f"DON-{uuid.uuid4().hex[:12]}"
        
        # For now, we'll use the donor_id as the order reference
        # The actual order creation would depend on the Order model
        logger.debug("Created virtual donation order %s", order_id)
        return order_id
    
    async def _store_donation_metadata(
        self,
        payment_id: str,
        donor_id: str,
        coupon_config: Optional[Dict[str, Any]],
        message: Optional[str],
    ) -> None:
        """Store donation metadata in payment record."""
        from database.payment_platform_models import Payment
        from sqlalchemy import update
        
        # Update payment with donation metadata
        stmt = (
            update(Payment)
            .where(Payment.id == payment_id)
            .values(
                client_payload={
                    self.METADATA_DONATION: True,
                    self.METADATA_DONOR_ID: donor_id,
                    self.METADATA_COUPON_CONFIG: coupon_config,
                    self.METADATA_MESSAGE: message,
                }
            )
        )
        await self._db.execute(stmt)
        await self._db.commit()
    
    async def _get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID."""
        from database.payment_platform_models import Payment
        
        result = await self._db.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()
    
    async def _handle_failed_donation(
        self,
        payment_id: str,
        donor_id: str,
    ) -> None:
        """Handle failed donation payment."""
        logger.warning(
            "Donation payment %s failed for donor %s",
            payment_id, donor_id
        )
        # No donor record created yet, so nothing to clean up
        # Could send notification to user about failed donation


# ========================================
# WEBHOOK ROUTER INTEGRATION
# ========================================

async def handle_donation_webhook(
    db: AsyncSession,
    payment_id: str,
    event_type: str,
    payload: Dict[str, Any],
) -> bool:
    """
    Entry point for webhook handler to route donation payments.
    
    Usage in webhook handler:
        from services.donation_payment_flow import handle_donation_webhook
        
        is_donation = await handle_donation_webhook(
            db=db,
            payment_id=payment_id,
            event_type=event_type,
            payload=payload,
        )
        if is_donation:
            return  # Donation handled, skip regular order processing
    """
    flow = DonationPaymentFlow(db)
    return await flow.on_payment_webhook(payment_id, event_type, payload)


async def get_donation_payment_flow(db: AsyncSession) -> DonationPaymentFlow:
    """Dependency injection for DonationPaymentFlow."""
    return DonationPaymentFlow(db)
