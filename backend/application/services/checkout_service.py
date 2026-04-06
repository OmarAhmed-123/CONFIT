"""
CONFIT Backend - Checkout Application Service
==============================================
Order creation, payment processing with Stripe, and BNPL support.
"""

import os
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import stripe
from pydantic import BaseModel, validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities import Order, OrderItem
from domain.base import Money, Address, OrderStatus, PaymentStatus, PaymentMethod, ShippingMethod
from application.services.product_service import ProductService
from core.security.input_sanitization import (
    sanitize_string,
    sanitize_phone,
    sanitize_integer,
    detect_sql_injection,
    detect_xss,
    SecurityValidationError,
)
from core.security.secrets_manager import secrets_manager
from database.models import (
    Order as OrderModel,
    OrderItem as OrderItemModel,
    Product as ProductModel,
    ProductVariant as ProductVariantModel,
    User as UserModel,
    Payment as PaymentModel,
    PaymentMethod as PaymentMethodModel,
    Cart as CartModel,
    CartItem as CartItemModel,
)
from models.profile_models import UserAddress as UserAddressModel


logger = logging.getLogger(__name__)

# Stripe configuration - use secrets manager
stripe.api_key = secrets_manager.get("STRIPE_SECRET_KEY") or os.getenv("STRIPE_SECRET_KEY", "")


# ─────────────────────────────────────────────────────────────────────────────
# DTOs
# ─────────────────────────────────────────────────────────────────────────────

class CartItemDTO(BaseModel):
    """Cart item DTO."""
    product_id: str
    variant_id: Optional[str] = None
    quantity: int = 1
    
    @validator('quantity')
    def quantity_positive(cls, v):
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v


class AddressDTO(BaseModel):
    """Address DTO."""
    line1: str
    line2: Optional[str] = None
    city: str
    state_province: Optional[str] = None
    postal_code: str
    country_code: str
    recipient_name: str
    phone: Optional[str] = None
    
    @validator('line1', 'line2', 'city', 'state_province', 'postal_code')
    def sanitize_address_fields(cls, v):
        if v is None:
            return v
        return sanitize_string(v, max_length=200)
    
    @validator('recipient_name')
    def sanitize_name(cls, v):
        return sanitize_string(v, max_length=100, allow_unicode=True)
    
    @validator('phone')
    def sanitize_phone_field(cls, v):
        if v is None:
            return v
        return sanitize_phone(v)
    
    @validator('country_code')
    def validate_country_code(cls, v):
        v = sanitize_string(v, max_length=2)
        if len(v) != 2:
            raise ValueError("Country code must be 2 characters")
        return v.upper()


class CheckoutRequest(BaseModel):
    """Checkout request DTO."""
    items: List[CartItemDTO]
    shipping_address: AddressDTO
    billing_address: Optional[AddressDTO] = None
    shipping_method: str = "standard"
    promo_code: Optional[str] = None
    notes: Optional[str] = None
    
    @validator('shipping_method')
    def sanitize_shipping_method(cls, v):
        allowed = ['standard', 'express', 'overnight', 'pickup']
        v = sanitize_string(v, max_length=20).lower()
        if v not in allowed:
            raise ValueError(f"Invalid shipping method. Allowed: {allowed}")
        return v
    
    @validator('promo_code')
    def sanitize_promo_code(cls, v):
        if v is None:
            return v
        v = sanitize_string(v, max_length=50)
        # Check for injection attempts
        if detect_sql_injection(v) or detect_xss(v):
            raise ValueError("Invalid promo code")
        return v
    
    @validator('notes')
    def sanitize_notes(cls, v):
        if v is None:
            return v
        return sanitize_string(v, max_length=500)


class PaymentRequest(BaseModel):
    """Payment request DTO."""
    order_id: str
    payment_method: str  # card, apple_pay, google_pay, paypal, bnpl_affirm, bnpl_klarna, bnpl_afterpay
    payment_method_id: Optional[str] = None  # Stripe payment method ID
    save_payment_method: bool = False
    
    @validator('order_id')
    def validate_order_id(cls, v):
        v = sanitize_string(v, max_length=50)
        # Validate UUID format
        try:
            UUID(v)
        except ValueError:
            raise ValueError("Invalid order ID format")
        return v
    
    @validator('payment_method')
    def validate_payment_method(cls, v):
        allowed = ['card', 'apple_pay', 'google_pay', 'paypal', 'bnpl_affirm', 'bnpl_klarna', 'bnpl_afterpay']
        v = sanitize_string(v, max_length=20).lower()
        if v not in allowed:
            raise ValueError(f"Invalid payment method. Allowed: {allowed}")
        return v
    
    @validator('payment_method_id')
    def sanitize_payment_method_id(cls, v):
        if v is None:
            return v
        v = sanitize_string(v, max_length=100)
        # Validate Stripe format (pm_ or src_)
        if not (v.startswith('pm_') or v.startswith('src_') or v.startswith('tok_')):
            raise ValueError("Invalid payment method ID format")
        return v


class OrderDTO(BaseModel):
    """Order response DTO."""
    id: str
    order_number: str
    user_id: str
    status: str
    items: List[Dict[str, Any]]
    subtotal: float
    discount_amount: float
    tax_amount: float
    shipping_amount: float
    total: float
    currency: str
    shipping_address: Dict[str, Any]
    billing_address: Dict[str, Any]
    shipping_method: str
    tracking_number: Optional[str] = None
    payment_status: str
    payment_method: Optional[str] = None
    created_at: datetime


class PaymentIntentDTO(BaseModel):
    """Payment intent DTO."""
    client_secret: str
    payment_intent_id: str
    amount: float
    currency: str
    status: str


class BNPLPlanDTO(BaseModel):
    """BNPL payment plan DTO."""
    provider: str
    total_amount: float
    installment_count: int
    installment_amount: float
    first_payment_due: datetime
    subsequent_payments_due: List[datetime]
    apr: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# CHECKOUT SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class CheckoutService:
    """Checkout and payment processing service."""
    
    # Shipping rates
    SHIPPING_RATES = {
        ShippingMethod.STANDARD.value: {"rate": 5.99, "days": "5-7"},
        ShippingMethod.EXPRESS.value: {"rate": 12.99, "days": "2-3"},
        ShippingMethod.OVERNIGHT.value: {"rate": 24.99, "days": "1"},
        ShippingMethod.SAME_DAY.value: {"rate": 39.99, "days": "0"},
        ShippingMethod.BOPIS.value: {"rate": 0.0, "days": "0"},
    }
    
    # Tax rate (simplified - in production use tax service)
    TAX_RATE = 0.08  # 8%
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.product_service = ProductService(session)
    
    # ─────────────────────────────────────────────────────────────────────────
    # CART OPERATIONS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def get_cart(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user's cart."""
        query = (
            select(CartModel)
            .options(selectinload(CartModel.items))
            .where(CartModel.user_id == str(user_id))
        )
        result = await self.session.execute(query)
        cart = result.scalar_one_or_none()
        
        if not cart:
            return None
        
        return await self._cart_to_dict(cart)
    
    async def add_to_cart(
        self,
        user_id: UUID,
        product_id: UUID,
        variant_id: Optional[UUID] = None,
        quantity: int = 1,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Add item to cart."""
        # Get or create cart
        cart = await self._get_or_create_cart(user_id)
        
        # Validate product and inventory
        product = await self.product_service._get_model_by_id(product_id)
        if not product:
            return None, "Product not found"
        
        if product.status != "active":
            return None, "Product is not available"
        
        # Check inventory
        variant = None
        if variant_id:
            variant = await self.product_service._get_variant_model(variant_id)
            if not variant or variant.product_id != str(product_id):
                return None, "Invalid variant"
            
            available = variant.inventory_quantity - variant.reserved_quantity
            if available < quantity:
                return None, f"Insufficient inventory. Available: {available}"
        else:
            # Get default variant or check total inventory
            total_available = sum(
                v.inventory_quantity - v.reserved_quantity 
                for v in product.variants
            )
            if total_available < quantity:
                return None, f"Insufficient inventory. Available: {total_available}"
        
        # Add or update cart item
        existing_item = None
        for item in cart.items:
            if item.product_id == str(product_id) and item.variant_id == str(variant_id) if variant_id else item.variant_id is None:
                existing_item = item
                break
        
        if existing_item:
            existing_item.quantity += quantity
        else:
            cart_item = CartItemModel(
                cart_id=cart.id,
                product_id=str(product_id),
                variant_id=str(variant_id) if variant_id else None,
                quantity=quantity,
                price=float(product.base_price),
            )
            self.session.add(cart_item)
        
        await self.session.flush()
        await self.session.refresh(cart)
        
        return await self._cart_to_dict(cart), None
    
    async def update_cart_item(
        self,
        user_id: UUID,
        item_id: UUID,
        quantity: int,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Update cart item quantity."""
        cart = await self._get_or_create_cart(user_id)
        
        item = None
        for i in cart.items:
            if i.id == str(item_id):
                item = i
                break
        
        if not item:
            return None, "Cart item not found"
        
        if quantity <= 0:
            await self.session.delete(item)
        else:
            # Check inventory
            if item.variant_id:
                variant = await self.product_service._get_variant_model(UUID(item.variant_id))
                available = variant.inventory_quantity - variant.reserved_quantity
                if available < quantity:
                    return None, f"Insufficient inventory. Available: {available}"
            
            item.quantity = quantity
        
        await self.session.flush()
        await self.session.refresh(cart)
        
        return await self._cart_to_dict(cart), None
    
    async def remove_from_cart(
        self,
        user_id: UUID,
        item_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        """Remove item from cart."""
        cart = await self._get_or_create_cart(user_id)
        
        for item in cart.items:
            if item.id == str(item_id):
                await self.session.delete(item)
                break
        
        await self.session.flush()
        await self.session.refresh(cart)
        
        return await self._cart_to_dict(cart)
    
    async def clear_cart(self, user_id: UUID) -> None:
        """Clear user's cart."""
        cart = await self._get_or_create_cart(user_id)
        
        for item in cart.items:
            await self.session.delete(item)
        
        await self.session.flush()
    
    # ─────────────────────────────────────────────────────────────────────────
    # CHECKOUT
    # ─────────────────────────────────────────────────────────────────────────
    
    async def create_order(
        self,
        user_id: UUID,
        request: CheckoutRequest,
    ) -> Tuple[Optional[OrderDTO], Optional[str]]:
        """Create order from checkout request."""
        # Validate items and inventory
        order_items = []
        subtotal = Decimal("0")
        
        for item in request.items:
            product = await self.product_service._get_model_by_id(UUID(item.product_id))
            if not product:
                return None, f"Product {item.product_id} not found"
            
            variant = None
            if item.variant_id:
                variant = await self.product_service._get_variant_model(UUID(item.variant_id))
                if not variant:
                    return None, f"Variant {item.variant_id} not found"
            
            # Reserve inventory
            variant_id = UUID(item.variant_id) if item.variant_id else None
            success, error = await self.product_service.reserve_inventory(
                variant_id, item.quantity
            ) if variant_id else (True, None)
            
            if not success:
                return None, error
            
            price = float(variant.price_adjustment) + float(product.base_price) if variant else float(product.base_price)
            total = Decimal(str(price)) * item.quantity
            subtotal += total
            
            order_items.append({
                "product_id": str(item.product_id),
                "variant_id": str(item.variant_id) if item.variant_id else None,
                "product_name": product.name,
                "variant_name": f"{variant.size} / {variant.color}" if variant else None,
                "quantity": item.quantity,
                "unit_price": price,
                "total_price": float(total),
                "image_url": product.primary_image_url,
            })
        
        # Calculate shipping
        shipping_info = self.SHIPPING_RATES.get(request.shipping_method, self.SHIPPING_RATES["standard"])
        shipping_amount = Decimal(str(shipping_info["rate"]))
        
        # Calculate tax
        tax_amount = subtotal * Decimal(str(self.TAX_RATE))
        
        # Apply promo code if provided
        discount_amount = Decimal("0")
        if request.promo_code:
            discount_amount = await self._apply_promo_code(request.promo_code, subtotal)
        
        # Calculate total
        total = subtotal + shipping_amount + tax_amount - discount_amount
        
        # Generate order number
        order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{UUID(int=int(datetime.now().timestamp() % 1e10)).hex[:8].upper()}"
        
        # Create order
        order = OrderModel(
            user_id=str(user_id),
            order_number=order_number,
            status=OrderStatus.PENDING.value,
            subtotal=subtotal,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            shipping_amount=shipping_amount,
            total=total,
            currency="USD",
            shipping_method=request.shipping_method,
            shipping_address=self._address_to_dict(request.shipping_address),
            billing_address=self._address_to_dict(request.billing_address or request.shipping_address),
            notes=request.notes,
        )
        
        self.session.add(order)
        await self.session.flush()
        await self.session.refresh(order)
        
        # Create order items
        for item_data in order_items:
            order_item = OrderItemModel(
                order_id=order.id,
                product_id=item_data["product_id"],
                variant_id=item_data["variant_id"],
                product_name=item_data["product_name"],
                variant_name=item_data["variant_name"],
                quantity=item_data["quantity"],
                unit_price=Decimal(str(item_data["unit_price"])),
                total_price=Decimal(str(item_data["total_price"])),
                image_url=item_data["image_url"],
            )
            self.session.add(order_item)
        
        await self.session.flush()
        
        logger.info(f"Order created: {order_number}")
        
        return self._to_dto(order), None
    
    # ─────────────────────────────────────────────────────────────────────────
    # PAYMENT PROCESSING
    # ─────────────────────────────────────────────────────────────────────────
    
    async def create_payment_intent(
        self,
        order_id: UUID,
        payment_method: str,
    ) -> Tuple[Optional[PaymentIntentDTO], Optional[str]]:
        """Create Stripe payment intent."""
        order = await self._get_order_model(order_id)
        if not order:
            return None, "Order not found"
        
        if order.status != OrderStatus.PENDING.value:
            return None, "Order cannot be paid"
        
        try:
            # Create Stripe payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(order.total * 100),  # Convert to cents
                currency=order.currency.lower(),
                payment_method_types=self._get_payment_method_types(payment_method),
                metadata={
                    "order_id": str(order_id),
                    "order_number": order.order_number,
                    "user_id": order.user_id,
                },
            )
            
            # Store payment intent ID
            order.payment_intent_id = intent.id
            await self.session.flush()
            
            return PaymentIntentDTO(
                client_secret=intent.client_secret,
                payment_intent_id=intent.id,
                amount=float(order.total),
                currency=order.currency,
                status=intent.status,
            ), None
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return None, str(e)
    
    async def confirm_payment(
        self,
        order_id: UUID,
        payment_intent_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """Confirm payment from Stripe webhook."""
        order = await self._get_order_model(order_id)
        if not order:
            return False, "Order not found"
        
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status == "succeeded":
                # Update order status
                order.status = OrderStatus.PROCESSING.value
                order.payment_status = PaymentStatus.COMPLETED.value
                order.paid_at = datetime.now(timezone.utc)
                
                # Fulfill inventory
                for item in order.items:
                    if item.variant_id:
                        await self.product_service.fulfill_inventory(
                            UUID(item.variant_id),
                            item.quantity,
                        )
                
                await self.session.flush()
                
                logger.info(f"Payment confirmed for order: {order.order_number}")
                
                return True, None
            else:
                order.payment_status = PaymentStatus.FAILED.value
                await self.session.flush()
                return False, f"Payment status: {intent.status}"
                
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error confirming payment: {e}")
            return False, str(e)
    
    async def process_refund(
        self,
        order_id: UUID,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Process refund for order."""
        order = await self._get_order_model(order_id)
        if not order:
            return False, "Order not found"
        
        if order.payment_status != PaymentStatus.COMPLETED.value:
            return False, "Order cannot be refunded"
        
        refund_amount = amount or order.total
        
        try:
            refund = stripe.Refund.create(
                payment_intent=order.payment_intent_id,
                amount=int(refund_amount * 100),  # Convert to cents
                reason="requested_by_customer",
                metadata={
                    "order_id": str(order_id),
                    "reason": reason or "",
                },
            )
            
            if refund.status == "succeeded":
                order.payment_status = PaymentStatus.REFUNDED.value if refund_amount >= order.total else PaymentStatus.PARTIALLY_REFUNDED.value
                order.status = OrderStatus.REFUNDED.value if refund_amount >= order.total else order.status
                
                # Restore inventory
                for item in order.items:
                    if item.variant_id:
                        variant = await self.product_service._get_variant_model(UUID(item.variant_id))
                        if variant:
                            variant.inventory_quantity += item.quantity
                
                await self.session.flush()
                
                logger.info(f"Refund processed for order: {order.order_number}")
                
                return True, None
            else:
                return False, f"Refund status: {refund.status}"
                
        except stripe.error.StripeError as e:
            logger.error(f"Stripe refund error: {e}")
            return False, str(e)
    
    # ─────────────────────────────────────────────────────────────────────────
    # BNPL (Buy Now Pay Later)
    # ─────────────────────────────────────────────────────────────────────────
    
    async def create_bnpl_checkout(
        self,
        order_id: UUID,
        provider: str,  # affirm, klarna, afterpay
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Create BNPL checkout session."""
        order = await self._get_order_model(order_id)
        if not order:
            return None, "Order not found"
        
        if order.total < Decimal("50") or order.total > Decimal("10000"):
            return None, "Order amount must be between $50 and $10,000 for BNPL"
        
        try:
            if provider == "affirm":
                return await self._create_affirm_checkout(order)
            elif provider == "klarna":
                return await self._create_klarna_checkout(order)
            elif provider == "afterpay":
                return await self._create_afterpay_checkout(order)
            else:
                return None, f"Unsupported BNPL provider: {provider}"
                
        except Exception as e:
            logger.error(f"BNPL checkout error: {e}")
            return None, str(e)
    
    async def _create_affirm_checkout(self, order: OrderModel) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Create Affirm checkout."""
        # In production, integrate with Affirm API
        checkout_data = {
            "provider": "affirm",
            "checkout_token": f"affirm_{UUID().hex}",
            "redirect_url": f"https://www.affirm.com/checkout/{order.id}",
            "plan": {
                "installment_count": 4,
                "installment_amount": float(order.total / 4),
                "apr": 0.0,
            }
        }
        
        return checkout_data, None
    
    async def _create_klarna_checkout(self, order: OrderModel) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Create Klarna checkout."""
        # In production, integrate with Klarna API
        checkout_data = {
            "provider": "klarna",
            "session_id": f"klarna_{UUID().hex}",
            "redirect_url": f"https://www.klarna.com/checkout/{order.id}",
            "plan": {
                "installment_count": 4,
                "installment_amount": float(order.total / 4),
                "apr": 0.0,
            }
        }
        
        return checkout_data, None
    
    async def _create_afterpay_checkout(self, order: OrderModel) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Create Afterpay checkout."""
        # In production, integrate with Afterpay API
        checkout_data = {
            "provider": "afterpay",
            "token": f"afterpay_{UUID().hex}",
            "redirect_url": f"https://www.afterpay.com/checkout/{order.id}",
            "plan": {
                "installment_count": 4,
                "installment_amount": float(order.total / 4),
                "apr": 0.0,
            }
        }
        
        return checkout_data, None
    
    async def get_bnpl_plans(
        self,
        amount: Decimal,
        provider: Optional[str] = None,
    ) -> List[BNPLPlanDTO]:
        """Get available BNPL payment plans."""
        plans = []
        
        # Affirm
        if not provider or provider == "affirm":
            plans.append(BNPLPlanDTO(
                provider="affirm",
                total_amount=float(amount),
                installment_count=4,
                installment_amount=float(amount / 4),
                first_payment_due=datetime.now(timezone.utc),
                subsequent_payments_due=[],
                apr=0.0 if amount <= Decimal("250") else 10.0,
            ))
        
        # Klarna
        if not provider or provider == "klarna":
            plans.append(BNPLPlanDTO(
                provider="klarna",
                total_amount=float(amount),
                installment_count=4,
                installment_amount=float(amount / 4),
                first_payment_due=datetime.now(timezone.utc),
                subsequent_payments_due=[],
                apr=0.0,
            ))
        
        # Afterpay
        if not provider or provider == "afterpay":
            plans.append(BNPLPlanDTO(
                provider="afterpay",
                total_amount=float(amount),
                installment_count=4,
                installment_amount=float(amount / 4),
                first_payment_due=datetime.now(timezone.utc),
                subsequent_payments_due=[],
                apr=0.0,
            ))
        
        return plans
    
    # ─────────────────────────────────────────────────────────────────────────
    # ORDER MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────
    
    async def get_order(self, order_id: UUID) -> Optional[OrderDTO]:
        """Get order by ID."""
        order = await self._get_order_model(order_id)
        return self._to_dto(order) if order else None
    
    async def get_user_orders(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Get user's orders."""
        query = (
            select(OrderModel)
            .options(selectinload(OrderModel.items))
            .where(OrderModel.user_id == str(user_id))
        )
        
        if status:
            query = query.where(OrderModel.status == status)
        
        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Paginate
        query = query.order_by(OrderModel.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.session.execute(query)
        orders = result.scalars().all()
        
        return {
            "items": [self._to_dto(o) for o in orders],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    
    async def cancel_order(
        self,
        order_id: UUID,
        user_id: UUID,
        reason: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Cancel order."""
        order = await self._get_order_model(order_id)
        if not order:
            return False, "Order not found"
        
        if order.user_id != str(user_id):
            return False, "Unauthorized"
        
        if order.status not in [OrderStatus.PENDING.value, OrderStatus.CONFIRMED.value]:
            return False, "Order cannot be cancelled"
        
        # Release inventory
        for item in order.items:
            if item.variant_id:
                await self.product_service.release_inventory(
                    UUID(item.variant_id),
                    item.quantity,
                )
        
        # Refund if paid
        if order.payment_status == PaymentStatus.COMPLETED.value:
            await self.process_refund(order_id, reason=reason)
        
        order.status = OrderStatus.CANCELLED.value
        order.notes = f"{order.notes or ''}\nCancelled: {reason or 'No reason provided'}"
        
        await self.session.flush()
        
        return True, None
    
    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE METHODS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _get_or_create_cart(self, user_id: UUID) -> CartModel:
        """Get or create user's cart."""
        query = (
            select(CartModel)
            .options(selectinload(CartModel.items))
            .where(CartModel.user_id == str(user_id))
        )
        result = await self.session.execute(query)
        cart = result.scalar_one_or_none()
        
        if not cart:
            cart = CartModel(
                user_id=str(user_id),
            )
            self.session.add(cart)
            await self.session.flush()
            await self.session.refresh(cart)
        
        return cart
    
    async def _get_order_model(self, order_id: UUID) -> Optional[OrderModel]:
        """Get order model by ID."""
        query = (
            select(OrderModel)
            .options(selectinload(OrderModel.items))
            .where(OrderModel.id == str(order_id))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def _cart_to_dict(self, cart: CartModel) -> Dict[str, Any]:
        """Convert cart to dictionary."""
        items = []
        total = Decimal("0")
        
        for item in cart.items:
            product = await self.product_service._get_model_by_id(UUID(item.product_id))
            if product:
                price = Decimal(str(item.price))
                item_total = price * item.quantity
                total += item_total
                
                items.append({
                    "id": item.id,
                    "product_id": item.product_id,
                    "variant_id": item.variant_id,
                    "product_name": product.name,
                    "quantity": item.quantity,
                    "unit_price": float(price),
                    "total_price": float(item_total),
                    "image_url": product.primary_image_url,
                })
        
        return {
            "id": cart.id,
            "items": items,
            "subtotal": float(total),
            "item_count": sum(i["quantity"] for i in items),
        }
    
    async def _apply_promo_code(self, code: str, subtotal: Decimal) -> Decimal:
        """Apply promo code and return discount amount."""
        # TODO: Implement promo code validation and calculation
        return Decimal("0")
    
    def _address_to_dict(self, address: AddressDTO) -> Dict[str, Any]:
        """Convert address DTO to dictionary."""
        return {
            "line1": address.line1,
            "line2": address.line2,
            "city": address.city,
            "state_province": address.state_province,
            "postal_code": address.postal_code,
            "country_code": address.country_code,
            "recipient_name": address.recipient_name,
            "phone": address.phone,
        }
    
    def _get_payment_method_types(self, payment_method: str) -> List[str]:
        """Get Stripe payment method types."""
        mapping = {
            "card": ["card"],
            "apple_pay": ["apple_pay", "card"],
            "google_pay": ["google_pay", "card"],
            "paypal": ["paypal"],
            "bnpl_affirm": ["affirm"],
            "bnpl_klarna": ["klarna"],
            "bnpl_afterpay": ["afterpay_clearpay"],
        }
        return mapping.get(payment_method, ["card"])
    
    def _to_dto(self, model: OrderModel) -> OrderDTO:
        """Convert order model to DTO."""
        return OrderDTO(
            id=model.id,
            order_number=model.order_number,
            user_id=model.user_id,
            status=model.status,
            items=[
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "variant_id": item.variant_id,
                    "product_name": item.product_name,
                    "variant_name": item.variant_name,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "total_price": float(item.total_price),
                    "image_url": item.image_url,
                }
                for item in model.items
            ],
            subtotal=float(model.subtotal),
            discount_amount=float(model.discount_amount),
            tax_amount=float(model.tax_amount),
            shipping_amount=float(model.shipping_amount),
            total=float(model.total),
            currency=model.currency,
            shipping_address=model.shipping_address,
            billing_address=model.billing_address,
            shipping_method=model.shipping_method,
            tracking_number=model.tracking_number,
            payment_status=model.payment_status,
            payment_method=model.payment_method,
            created_at=model.created_at,
        )
