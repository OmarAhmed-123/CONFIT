"""
CONFIT Backend - Donor Notifications Integration (Phase 4)
===========================================================
Integration with notification dispatcher for donor events.

Notification Types:
- coupon_live: New coupon created and active
- first_redemption: First time coupon is used
- milestone: Donation milestone reached (tier upgrade)
- monthly_report: Monthly donor impact summary
- coupon_expiring: Coupon about to expire
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.donation_models import Donor, DonationRecord, Coupon, CouponRedemption, DonorTier
from database.models import User
from services.notification.dispatcher import (
    NotificationDispatcher,
    NotificationRequest,
    Channel,
    NotificationPriority,
)

logger = logging.getLogger(__name__)


# Notification templates (Arabic + English)
DONOR_TEMPLATES = {
    "coupon_live": {
        "title": {"en": "Your Coupon is Live!", "ar": "  !"},
        "body": {
            "en": "Your coupon {code} is now live on CONFIT. Beneficiaries can start using it today!",
            "ar": "  {code}   CONFIT.   !",
        },
    },
    "first_redemption": {
        "title": {"en": "Your First Redemption!", "ar": "  !"},
        "body": {
            "en": "Someone just saved {discount_egp} EGP using your coupon {code}. Your generosity is making a difference!",
            "ar": "  {discount_egp}     {code}.   !",
        },
    },
    "milestone": {
        "title": {"en": "Milestone Reached: {tier}", "ar": " : {tier}"},
        "body": {
            "en": "Congratulations! You've reached {tier} status with {total_egp} EGP donated. Thank you for your incredible support!",
            "ar": "!   {tier}   {total_egp} .   !",
        },
    },
    "monthly_report": {
        "title": {"en": "Your Monthly Impact Report", "ar": "   "},
        "body": {
            "en": "This month: {donations} donations, {people_helped} people helped, {coupons_redeemed} coupons redeemed. Total impact: {total_egp} EGP.",
            "ar": " : {donations} , {people_helped} , {coupons_redeemed} .  : {total_egp} .",
        },
    },
    "coupon_expiring": {
        "title": {"en": "Coupon Expiring Soon", "ar": "  "},
        "body": {
            "en": "Your coupon {code} expires in {days} days. Consider extending it to continue helping beneficiaries!",
            "ar": "  {code}  {days} .    !",
        },
    },
}


class DonorNotificationService:
    """Service for sending donor-related notifications."""
    
    def __init__(self, db: AsyncSession):
        self._db = db
        self._dispatcher = NotificationDispatcher(db=self._db)
    
    async def send_coupon_live_notification(
        self,
        coupon: Coupon,
        donor: Donor,
    ) -> bool:
        """Send notification when coupon goes live."""
        if donor.is_anonymous:
            return False
        
        user = await self._get_user(donor.user_id)
        if not user:
            return False
        
        template = DONOR_TEMPLATES["coupon_live"]
        
        request = NotificationRequest(
            recipient_id=donor.user_id,
            recipient_email=user.email,
            recipient_phone=user.phone,
            title=template["title"]["en"],
            body=template["body"]["en"].format(code=coupon.code),
            notification_type="coupon_live",
            channels=[Channel.EMAIL, Channel.IN_APP],
            priority=NotificationPriority.NORMAL,
            metadata={
                "coupon_id": coupon.id,
                "coupon_code": coupon.code,
                "donor_id": donor.id,
            },
        )
        
        try:
            await self._dispatcher.dispatch(request)
            logger.info("Sent coupon_live notification for coupon %s", coupon.code)
            return True
        except Exception as e:
            logger.warning("Failed to send coupon_live notification: %s", e)
            return False
    
    async def send_first_redemption_notification(
        self,
        coupon: Coupon,
        discount_piastres: int,
    ) -> bool:
        """Send notification on first coupon redemption."""
        donor = await self._get_donor(coupon.donor_id)
        if not donor or donor.is_anonymous:
            return False
        
        user = await self._get_user(donor.user_id)
        if not user:
            return False
        
        template = DONOR_TEMPLATES["first_redemption"]
        discount_egp = discount_piastres / 100
        
        request = NotificationRequest(
            recipient_id=donor.user_id,
            recipient_email=user.email,
            recipient_phone=user.phone,
            title=template["title"]["en"],
            body=template["body"]["en"].format(
                code=coupon.code,
                discount_egp=f"{discount_egp:.2f}",
            ),
            notification_type="first_redemption",
            channels=[Channel.EMAIL, Channel.IN_APP, Channel.PUSH],
            priority=NotificationPriority.HIGH,
            metadata={
                "coupon_id": coupon.id,
                "coupon_code": coupon.code,
                "discount_egp": discount_egp,
            },
        )
        
        try:
            await self._dispatcher.dispatch(request)
            logger.info("Sent first_redemption notification for coupon %s", coupon.code)
            return True
        except Exception as e:
            logger.warning("Failed to send first_redemption notification: %s", e)
            return False
    
    async def send_milestone_notification(
        self,
        donor: Donor,
        new_tier: DonorTier,
    ) -> bool:
        """Send notification when donor reaches a milestone tier."""
        if donor.is_anonymous:
            return False
        
        user = await self._get_user(donor.user_id)
        if not user:
            return False
        
        template = DONOR_TEMPLATES["milestone"]
        total_egp = donor.total_donated_piastres / 100
        
        request = NotificationRequest(
            recipient_id=donor.user_id,
            recipient_email=user.email,
            recipient_phone=user.phone,
            title=template["title"]["en"].format(tier=new_tier.value.title()),
            body=template["body"]["en"].format(
                tier=new_tier.value.title(),
                total_egp=f"{total_egp:.2f}",
            ),
            notification_type="milestone",
            channels=[Channel.EMAIL, Channel.IN_APP, Channel.PUSH],
            priority=NotificationPriority.HIGH,
            metadata={
                "donor_id": donor.id,
                "tier": new_tier.value,
                "total_egp": total_egp,
            },
        )
        
        try:
            await self._dispatcher.dispatch(request)
            logger.info("Sent milestone notification for donor %s", donor.id)
            return True
        except Exception as e:
            logger.warning("Failed to send milestone notification: %s", e)
            return False
    
    async def send_monthly_report_notification(
        self,
        donor: Donor,
        month_stats: Dict[str, Any],
    ) -> bool:
        """Send monthly impact report to donor."""
        if donor.is_anonymous:
            return False
        
        user = await self._get_user(donor.user_id)
        if not user:
            return False
        
        template = DONOR_TEMPLATES["monthly_report"]
        
        request = NotificationRequest(
            recipient_id=donor.user_id,
            recipient_email=user.email,
            title=template["title"]["en"],
            body=template["body"]["en"].format(**month_stats),
            notification_type="monthly_report",
            channels=[Channel.EMAIL],
            priority=NotificationPriority.LOW,
            metadata={
                "donor_id": donor.id,
                "month": month_stats.get("month", ""),
                **month_stats,
            },
        )
        
        try:
            await self._dispatcher.dispatch(request)
            logger.info("Sent monthly_report notification for donor %s", donor.id)
            return True
        except Exception as e:
            logger.warning("Failed to send monthly_report notification: %s", e)
            return False
    
    async def send_coupon_expiring_notification(
        self,
        coupon: Coupon,
        days_remaining: int,
    ) -> bool:
        """Send notification when coupon is about to expire."""
        donor = await self._get_donor(coupon.donor_id)
        if not donor or donor.is_anonymous:
            return False
        
        user = await self._get_user(donor.user_id)
        if not user:
            return False
        
        template = DONOR_TEMPLATES["coupon_expiring"]
        
        request = NotificationRequest(
            recipient_id=donor.user_id,
            recipient_email=user.email,
            title=template["title"]["en"],
            body=template["body"]["en"].format(
                code=coupon.code,
                days=days_remaining,
            ),
            notification_type="coupon_expiring",
            channels=[Channel.EMAIL, Channel.IN_APP],
            priority=NotificationPriority.NORMAL,
            metadata={
                "coupon_id": coupon.id,
                "coupon_code": coupon.code,
                "days_remaining": days_remaining,
            },
        )
        
        try:
            await self._dispatcher.dispatch(request)
            logger.info("Sent coupon_expiring notification for coupon %s", coupon.code)
            return True
        except Exception as e:
            logger.warning("Failed to send coupon_expiring notification: %s", e)
            return False
    
    # ========================================
    # BULK NOTIFICATIONS
    # ========================================
    
    async def send_expiring_coupons_notifications(
        self,
        days_threshold: int = 7,
    ) -> int:
        """
        Send notifications for all coupons expiring within threshold.
        
        Returns count of notifications sent.
        """
        now = datetime.now(timezone.utc)
        threshold_date = now + timedelta(days=days_threshold)
        
        # Find active coupons expiring within threshold
        result = await self._db.execute(
            select(Coupon).where(and_(
                Coupon.is_active == True,
                Coupon.valid_until != None,
                Coupon.valid_until <= threshold_date,
                Coupon.valid_until > now,
            ))
        )
        coupons = result.scalars().all()
        
        sent_count = 0
        for coupon in coupons:
            days_remaining = (coupon.valid_until - now).days
            success = await self.send_coupon_expiring_notification(coupon, days_remaining)
            if success:
                sent_count += 1
        
        logger.info("Sent %d coupon expiring notifications", sent_count)
        return sent_count
    
    async def send_monthly_reports_to_all_donors(self) -> int:
        """
        Send monthly reports to all non-anonymous donors.
        
        Returns count of notifications sent.
        """
        result = await self._db.execute(
            select(Donor).where(Donor.is_anonymous == False)
        )
        donors = result.scalars().all()
        
        sent_count = 0
        for donor in donors:
            # Calculate monthly stats
            stats = await self._calculate_monthly_stats(donor)
            success = await self.send_monthly_report_notification(donor, stats)
            if success:
                sent_count += 1
        
        logger.info("Sent %d monthly report notifications", sent_count)
        return sent_count
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    async def _get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self._db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_donor(self, donor_id: str) -> Optional[Donor]:
        """Get donor by ID."""
        result = await self._db.execute(
            select(Donor).where(Donor.id == donor_id)
        )
        return result.scalar_one_or_none()
    
    async def _calculate_monthly_stats(self, donor: Donor) -> Dict[str, Any]:
        """Calculate monthly stats for donor."""
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Donations this month
        donations_result = await self._db.execute(
            select(func.count()).select_from(DonationRecord).where(and_(
                DonationRecord.donor_id == donor.id,
                DonationRecord.created_at >= month_start,
            ))
        )
        donations = donations_result.scalar() or 0
        
        # Coupons redeemed this month
        redeemed_result = await self._db.execute(
            select(func.count()).select_from(CouponRedemption)
            .join(Coupon).where(and_(
                Coupon.donor_id == donor.id,
                CouponRedemption.created_at >= month_start,
            ))
        )
        coupons_redeemed = redeemed_result.scalar() or 0
        
        return {
            "month": now.strftime("%B %Y"),
            "donations": donations,
            "people_helped": donor.people_helped,
            "coupons_redeemed": coupons_redeemed,
            "total_egp": f"{donor.total_donated_piastres / 100:.2f}",
        }


async def get_donor_notification_service(db: AsyncSession) -> DonorNotificationService:
    """Dependency injection for DonorNotificationService."""
    return DonorNotificationService(db)
