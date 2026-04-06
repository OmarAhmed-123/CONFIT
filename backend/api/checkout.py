"""
CONFIT Backend - Checkout API Routes
====================================
Cart, checkout, and payment processing.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import get_checkout_service, get_current_user, get_current_user_optional
from application.services.checkout_service import (
    CheckoutService,
    CheckoutRequest,
    OrderDTO,
    PaymentRequest,
    PaymentIntentDTO,
    BNPLPlanDTO,
    AddressDTO,
    CartItemDTO,
)
from core.security.rbac import AuthContext


router = APIRouter(prefix="/checkout", tags=["Checkout"])


# ─────────────────────────────────────────────────────────────────────────────
# CART
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/cart",
    summary="Get user's cart",
)
async def get_cart(
    checkout_service: CheckoutService = Depends(get_checkout_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get current user's shopping cart."""
    from uuid import UUID
    cart = await checkout_service.get_cart(UUID(current_user.user_id))
    
    if not cart:
        return {"items": [], "subtotal": 0, "item_count": 0}
    
    return cart


@router.post(
    "/cart/items",
    summary="Add item to cart",
)
async def add_to_cart(
    product_id: str,
    variant_id: Optional[str] = None,
    quantity: int = Query(1, ge=1),
    checkout_service: CheckoutService = Depends(get_checkout_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Add item to cart."""
    from uuid import UUID
    cart, error = await checkout_service.add_to_cart(
        user_id=UUID(current_user.user_id),
        product_id=UUID(product_id),
        variant_id=UUID(variant_id) if variant_id else None,
        quantity=quantity,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return cart


@router.patch(
    "/cart/items/{item_id}",
    summary="Update cart item",
)
async def update_cart_item(
    item_id: str,
    quantity: int,
    checkout_service: CheckoutService = Depends(get_checkout_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Update cart item quantity."""
    from uuid import UUID
    cart, error = await checkout_service.update_cart_item(
        user_id=UUID(current_user.user_id),
        item_id=UUID(item_id),
        quantity=quantity,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return cart


@router.delete(
    "/cart/items/{item_id}",
    summary="Remove item from cart",
)
async def remove_from_cart(
    item_id: str,
    checkout_service: CheckoutService = Depends(get_checkout_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Remove item from cart."""
    from uuid import UUID
    cart = await checkout_service.remove_from_cart(
        user_id=UUID(current_user.user_id),
        item_id=UUID(item_id),
    )
    
    return cart


@router.delete(
    "/cart",
    summary="Clear cart",
)
async def clear_cart(
    checkout_service: CheckoutService = Depends(get_checkout_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Clear all items from cart."""
    from uuid import UUID
    await checkout_service.clear_cart(UUID(current_user.user_id))
    
    return {"message": "Cart cleared"}


# ─────────────────────────────────────────────────────────────────────────────
# CHECKOUT
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/orders",
    response_model=OrderDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create order",
)
async def create_order(
    request: CheckoutRequest,
    checkout_service: CheckoutService = Depends(get_checkout_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Create order from checkout request."""
    from uuid import UUID
    order, error = await checkout_service.create_order(
        user_id=UUID(current_user.user_id),
        request=request,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return order


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENT
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/payment/intent",
    response_model=PaymentIntentDTO,
    summary="Create payment intent",
)
async def create_payment_intent(
    request: PaymentRequest,
    checkout_service: CheckoutService = Depends(get_checkout_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Create Stripe payment intent."""
    from uuid import UUID
    intent, error = await checkout_service.create_payment_intent(
        order_id=UUID(request.order_id),
        payment_method=request.payment_method,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return intent


@router.post(
    "/payment/bnpl/{provider}",
    summary="Create BNPL checkout",
)
async def create_bnpl_checkout(
    provider: str,  # affirm, klarna, afterpay
    order_id: str,
    checkout_service: CheckoutService = Depends(get_checkout_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Create Buy Now Pay Later checkout."""
    from uuid import UUID
    checkout, error = await checkout_service.create_bnpl_checkout(
        order_id=UUID(order_id),
        provider=provider,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return checkout


@router.get(
    "/bnpl/plans",
    response_model=list[BNPLPlanDTO],
    summary="Get BNPL plans",
)
async def get_bnpl_plans(
    amount: float,
    provider: Optional[str] = None,
    checkout_service: CheckoutService = Depends(get_checkout_service),
):
    """Get available BNPL payment plans."""
    from decimal import Decimal
    return await checkout_service.get_bnpl_plans(
        amount=Decimal(str(amount)),
        provider=provider,
    )


# ─────────────────────────────────────────────────────────────────────────────
# ORDERS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/orders",
    summary="Get user orders",
)
async def get_user_orders(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    checkout_service: CheckoutService = Depends(get_checkout_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get user's order history."""
    from uuid import UUID
    return await checkout_service.get_user_orders(
        user_id=UUID(current_user.user_id),
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/orders/{order_id}",
    response_model=OrderDTO,
    summary="Get order by ID",
)
async def get_order(
    order_id: str,
    checkout_service: CheckoutService = Depends(get_checkout_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get order details."""
    from uuid import UUID
    order = await checkout_service.get_order(UUID(order_id))
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Verify ownership
    if order.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return order


@router.post(
    "/orders/{order_id}/cancel",
    summary="Cancel order",
)
async def cancel_order(
    order_id: str,
    reason: Optional[str] = None,
    checkout_service: CheckoutService = Depends(get_checkout_service),
    current_user: AuthContext = Depends(get_current_user),
):
    """Cancel order."""
    from uuid import UUID
    success, error = await checkout_service.cancel_order(
        order_id=UUID(order_id),
        user_id=UUID(current_user.user_id),
        reason=reason,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Order cancelled"}
