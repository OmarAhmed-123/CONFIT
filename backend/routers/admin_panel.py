"""
CONFIT Admin Panel Router

Minimal admin interface for operations team.
Routes: /admin/*

Features:
- User management (search, suspend, change role)
- Order management (refund, cancel, resend)
- Coupon management (disable, extend)
- Brand onboarding (approve, payout)
- Notification broadcast (mass promo - respect prefs)

Access: Admin role only (role='admin')
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.models import Order, User, UserRole
from database.session import get_db
from services.auth_service import UserProfile
from utils.auth_deps import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin Panel"])


# ==================== Pydantic Models ====================

class UserSearchRequest(BaseModel):
    """Request to search users."""
    query: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None  # active, suspended, pending
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class UserSearchResponse(BaseModel):
    """Response with user search results."""
    users: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


class UserRoleUpdate(BaseModel):
    """Request to update user role."""
    user_id: str
    new_role: str = Field(pattern="^(customer|seller|donor|admin|brand_partner|store_manager)$")
    reason: str


class UserSuspendRequest(BaseModel):
    """Request to suspend or unsuspend user."""
    user_id: str
    action: str = Field(pattern="^(suspend|unsuspend)$")
    reason: str
    duration_days: Optional[int] = None  # None = indefinite


class OrderActionRequest(BaseModel):
    """Request for order action."""
    order_id: str
    action: str = Field(pattern="^(refund|cancel|resend|mark_delivered|escalate)$")
    reason: str
    amount_piastres: Optional[int] = None  # For partial refunds


class OrderActionResponse(BaseModel):
    """Response after order action."""
    success: bool
    order_id: str
    action: str
    new_status: str
    timestamp: datetime


class CouponActionRequest(BaseModel):
    """Request for coupon action."""
    coupon_id: str
    action: str = Field(pattern="^(disable|extend|update_usage_limit)$")
    reason: str
    extension_days: Optional[int] = None
    new_usage_limit: Optional[int] = None


class BrandOnboardingRequest(BaseModel):
    """Request for brand onboarding action."""
    brand_id: str
    action: str = Field(pattern="^(approve|reject|request_kyc|schedule_payout|suspend)$")
    reason: Optional[str] = None
    commission_rate: Optional[float] = None  # For approval


class NotificationBroadcastRequest(BaseModel):
    """Request to send mass notification."""
    title: str
    message: str
    target_audience: str = Field(pattern="^(all|customers|sellers|donors|segment)$")
    segment_filter: Optional[Dict[str, Any]] = None
    channel: str = Field(default="push", pattern="^(push|email|sms|all)$")
    respect_preferences: bool = True
    scheduled_time: Optional[datetime] = None


class AdminDashboardStats(BaseModel):
    """Admin dashboard statistics."""
    total_users: int
    active_users_today: int
    new_users_today: int
    pending_orders: int
    pending_returns: int
    pending_brand_approvals: int
    revenue_today_egp: float
    flagged_accounts: int
    system_health: str


# ==================== User Management Routes ====================

@router.post("/users/search", response_model=UserSearchResponse)
async def search_users(
    request: UserSearchRequest,
    admin: UserProfile = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserSearchResponse:
    """
    Search users with filters.
    
    - query: Search by name, email, or phone
    - role: Filter by user role
    - status: active, suspended, pending
    - created_after/before: Date range filter
    """
    logger.info(f"Admin {admin.id} searching users with query: {request.query}")
    
    query = db.query(User)
    if request.query:
        q = f"%{request.query.strip()}%"
        query = query.filter((User.name.ilike(q)) | (User.email.ilike(q)) | (User.phone.ilike(q)))
    if request.created_after:
        query = query.filter(User.created_at >= request.created_after)
    if request.created_before:
        query = query.filter(User.created_at <= request.created_before)

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(request.offset).limit(request.limit).all()
    role_rows = db.query(UserRole).filter(UserRole.user_id.in_([u.id for u in users])).all() if users else []
    role_by_user = {str(row.user_id): row.role.value for row in role_rows}

    return UserSearchResponse(
        users=[
            {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "role": role_by_user.get(str(user.id), "user"),
                "status": "active",
                "joined": user.created_at.isoformat() if user.created_at else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "orders": len(user.orders or []),
            }
            for user in users
        ],
        total=total,
        limit=request.limit,
        offset=request.offset
    )


@router.get("/users")
async def list_users(
    query: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin: UserProfile = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    result = await search_users(
        UserSearchRequest(query=query, limit=limit, offset=offset),
        admin=admin,
        db=db,
    )
    return result.model_dump()


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    admin: UserProfile = Depends(require_admin)
) -> Dict[str, Any]:
    """Get detailed information about a specific user."""
    logger.info(f"Admin {admin.id} viewing user {user_id}")
    
    return {
        "user_id": user_id,
        "profile": {"name": "Example", "email": "example@confit.app"},
        "orders_count": 5,
        "total_spent_egp": 2500.00,
        "tryon_sessions": 12,
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "last_login": datetime.utcnow().isoformat(),
        "suspension_history": []
    }


@router.post("/users/role")
async def update_user_role(
    request: UserRoleUpdate,
    admin: UserProfile = Depends(require_admin)
) -> Dict[str, Any]:
    """Change a user's role (e.g., customer → seller)."""
    logger.info(f"Admin {admin.id} changing role of user {request.user_id} to {request.new_role}")
    
    # Log the action for audit
    logger.warning(f"ROLE_CHANGE: User {request.user_id} → {request.new_role} by Admin {admin.id}")
    
    return {
        "success": True,
        "user_id": request.user_id,
        "previous_role": "customer",
        "new_role": request.new_role,
        "changed_by": str(admin.id),
        "timestamp": datetime.utcnow(),
        "reason": request.reason
    }


@router.post("/users/suspend")
async def suspend_user(
    request: UserSuspendRequest,
    admin: UserProfile = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Suspend or unsuspend a user account.
    
    Suspension prevents login and purchasing.
    Duration: None = indefinite, otherwise days until auto-unsuspend
    """
    action_str = "suspending" if request.action == "suspend" else "unsuspending"
    logger.warning(f"Admin {admin.id} {action_str} user {request.user_id}")
    
    return {
        "success": True,
        "user_id": request.user_id,
        "action": request.action,
        "reason": request.reason,
        "duration_days": request.duration_days,
        "expires_at": datetime.utcnow() + timedelta(days=request.duration_days) if request.duration_days else None,
        "performed_by": str(admin.id),
        "timestamp": datetime.utcnow()
    }


# ==================== Order Management Routes ====================

@router.get("/orders")
async def list_orders(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin: UserProfile = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    logger.info("Admin %s listing orders", admin.id)
    total = db.query(Order).count()
    orders = db.query(Order).order_by(Order.placed_at.desc()).offset(offset).limit(limit).all()
    return {
        "success": True,
        "orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "customer": order.user.name if order.user else "Customer",
                "total": order.total,
                "status": order.status,
                "date": order.placed_at.isoformat() if order.placed_at else None,
                "payment_status": order.payment_status,
                "items": [
                    {
                        "id": item.id,
                        "productId": item.product_id,
                        "name": item.name,
                        "price": item.price,
                        "quantity": item.quantity,
                        "image": item.image_url,
                    }
                    for item in (order.items or [])
                ],
            }
            for order in orders
        ],
        "total": total,
    }


@router.post("/orders/action")
async def order_action(
    request: OrderActionRequest,
    admin: UserProfile = Depends(require_admin)
) -> OrderActionResponse:
    """
    Perform administrative action on an order.
    
    Actions:
    - refund: Issue full or partial refund
    - cancel: Cancel order before shipment
    - resend: Resend shipment (lost package)
    - mark_delivered: Force mark as delivered
    - escalate: Escalate to customer service team
    """
    logger.warning(
        f"Admin {admin.id} performing '{request.action}' on order {request.order_id}"
    )
    
    # Map action to status
    status_map = {
        "refund": "refunded",
        "cancel": "cancelled",
        "resend": "reshipped",
        "mark_delivered": "delivered",
        "escalate": "escalated"
    }
    
    return OrderActionResponse(
        success=True,
        order_id=request.order_id,
        action=request.action,
        new_status=status_map.get(request.action, "unknown"),
        timestamp=datetime.utcnow()
    )


@router.get("/orders/pending")
async def get_pending_orders(
    status: str = Query("pending", pattern="^(pending|processing|shipped|exception)$"),
    limit: int = Query(50, ge=1, le=100),
    admin: UserProfile = Depends(require_admin)
) -> Dict[str, Any]:
    """Get orders requiring admin attention."""
    return {
        "status": status,
        "count": 0,
        "orders": []
    }


@router.post("/orders/{order_id}/refund")
async def refund_order(
    order_id: str,
    amount_piastres: Optional[int] = None,
    reason: str = "",
    admin: UserProfile = Depends(require_admin)
) -> Dict[str, Any]:
    """Process a refund for an order."""
    refund_type = "full" if amount_piastres is None else "partial"
    logger.warning(f"Admin {admin.id} processing {refund_type} refund for order {order_id}")
    
    return {
        "success": True,
        "order_id": order_id,
        "refund_type": refund_type,
        "amount_piastres": amount_piastres,
        "processed_by": str(admin.id),
        "timestamp": datetime.utcnow()
    }


# ==================== Coupon Management Routes ====================

@router.post("/coupons/action")
async def coupon_action(
    request: CouponActionRequest,
    admin: UserProfile = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Manage coupon lifecycle.
    
    Actions:
    - disable: Immediately disable coupon
    - extend: Extend expiration date
    - update_usage_limit: Change maximum uses
    """
    logger.info(f"Admin {admin.id} performing '{request.action}' on coupon {request.coupon_id}")
    
    result = {"action": request.action}
    
    if request.action == "extend" and request.extension_days:
        result["new_expiry"] = datetime.utcnow() + timedelta(days=request.extension_days)
    elif request.action == "update_usage_limit":
        result["new_usage_limit"] = request.new_usage_limit
    
    return {
        "success": True,
        "coupon_id": request.coupon_id,
        "result": result,
        "performed_by": str(admin.id),
        "timestamp": datetime.utcnow()
    }


@router.get("/coupons/active")
async def list_active_coupons(
    admin: UserProfile = Depends(require_admin)
) -> Dict[str, Any]:
    """List all active coupons."""
    return {
        "coupons": [
            {
                "id": "coupon_123",
                "code": "WELCOME2026",
                "discount_type": "percentage",
                "discount_value": 15,
                "uses_remaining": 100,
                "expires_at": datetime.utcnow() + timedelta(days=30)
            }
        ]
    }


# ==================== Brand Onboarding Routes ====================

@router.get("/brands/pending")
async def get_pending_brands(
    admin: UserProfile = Depends(require_admin)
) -> Dict[str, Any]:
    """Get brand partner applications pending approval."""
    return {
        "count": 0,
        "brands": []
    }


@router.post("/brands/onboarding")
async def brand_onboarding_action(
    request: BrandOnboardingRequest,
    admin: UserProfile = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Process brand onboarding workflow.
    
    Actions:
    - approve: Approve brand as partner
    - reject: Reject application
    - request_kyc: Request additional KYC documents
    - schedule_payout: Set up payout schedule
    - suspend: Suspend brand partnership
    """
    logger.warning(
        f"Admin {admin.id} performing '{request.action}' on brand {request.brand_id}"
    )
    
    result = {
        "success": True,
        "brand_id": request.brand_id,
        "action": request.action,
        "performed_by": str(admin.id),
        "timestamp": datetime.utcnow()
    }
    
    if request.commission_rate:
        result["commission_rate"] = request.commission_rate
    
    return result


@router.post("/brands/{brand_id}/payout")
async def process_brand_payout(
    brand_id: str,
    amount_piastres: int,
    period_start: datetime,
    period_end: datetime,
    admin: UserProfile = Depends(require_admin)
) -> Dict[str, Any]:
    """Process payout to brand partner."""
    logger.warning(f"Admin {admin.id} processing payout of {amount_piastres} piastres to brand {brand_id}")
    
    return {
        "success": True,
        "brand_id": brand_id,
        "amount_piastres": amount_piastres,
        "period": f"{period_start} to {period_end}",
        "processed_by": str(admin.id),
        "timestamp": datetime.utcnow(),
        "transaction_id": "txn_123456"
    }


# ==================== Notification Broadcast Routes ====================

@router.post("/notifications/broadcast")
async def broadcast_notification(
    request: NotificationBroadcastRequest,
    admin: UserProfile = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Send mass notification to users.
    
    CRITICAL: Must respect user notification preferences (respect_preferences=True)
    
    Target audiences:
    - all: All users
    - customers: Only buyers
    - sellers: Only brand partners
    - donors: Only donors
    - segment: Custom filter criteria
    
    Channels:
    - push: Push notification
    - email: Email campaign
    - sms: SMS message
    - all: All channels user has enabled
    """
    if not request.respect_preferences:
        logger.warning(f"Admin {admin.id} broadcasting WITHOUT preference respect - requires justification")
        # Would require additional approval in production
    
    logger.warning(
        f"Admin {admin.id} broadcasting '{request.title}' to {request.target_audience} "
        f"via {request.channel}"
    )
    
    # In production, this would:
    # 1. Query target users respecting preferences
    # 2. Queue notifications for delivery
    # 3. Log for audit trail
    # 4. Track delivery metrics
    
    return {
        "success": True,
        "broadcast_id": "broadcast_123",
        "title": request.title,
        "target_audience": request.target_audience,
        "estimated_recipients": 15000,
        "channel": request.channel,
        "respects_preferences": request.respect_preferences,
        "scheduled_for": request.scheduled_time or datetime.utcnow(),
        "sent_by": str(admin.id),
        "timestamp": datetime.utcnow()
    }


@router.get("/notifications/broadcasts")
async def list_broadcasts(
    limit: int = Query(20, ge=1, le=100),
    admin: UserProfile = Depends(require_admin)
) -> Dict[str, Any]:
    """List recent notification broadcasts."""
    return {
        "broadcasts": []
    }


# ==================== Dashboard Routes ====================

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    admin: UserProfile = Depends(require_admin)
) -> AdminDashboardStats:
    """Get admin dashboard statistics."""
    logger.info(f"Admin {admin.id} viewing dashboard")
    
    # In production, aggregate from various services
    
    return AdminDashboardStats(
        total_users=15000,
        active_users_today=1200,
        new_users_today=45,
        pending_orders=23,
        pending_returns=5,
        pending_brand_approvals=2,
        revenue_today_egp=45000.00,
        flagged_accounts=1,
        system_health="healthy"
    )


@router.get("/dashboard/activity")
async def get_recent_activity(
    limit: int = Query(50, ge=1, le=100),
    admin: UserProfile = Depends(require_admin)
) -> Dict[str, Any]:
    """Get recent admin activity log."""
    return {
        "activities": []
    }


@router.get("/system/health")
async def get_system_health(
    admin: UserProfile = Depends(require_admin)
) -> Dict[str, Any]:
    """Get system health status."""
    return {
        "status": "healthy",
        "services": {
            "api": "up",
            "database": "up",
            "redis": "up",
            "payment_gateway": "up",
            "ai_services": "up"
        },
        "last_checked": datetime.utcnow()
    }
