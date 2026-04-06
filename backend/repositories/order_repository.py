"""CONFIT Backend — Order Repository."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from repositories.base import BaseRepository
from database.models import Order, OrderItem, ReturnRequest


class OrderRepository(BaseRepository[Order]):
    """Repository for Order entity operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, Order)
    
    def get_with_items(self, order_id: str) -> Optional[Order]:
        """Get order with items loaded."""
        return self._db.query(Order).options(
            joinedload(Order.items),
        ).filter(Order.id == order_id).first()
    
    def get_by_user(
        self,
        user_id: str,
        status: str = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Order]:
        """Get orders by user with optional status filter."""
        query = self._db.query(Order).filter(Order.user_id == user_id)
        
        if status:
            query = query.filter(Order.status == status)
        
        return query.order_by(Order.placed_at.desc()).offset(offset).limit(limit).all()
    
    def get_recent(self, days: int = 30, limit: int = 100) -> List[Order]:
        """Get recent orders within specified days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        return self._db.query(Order).filter(
            Order.placed_at >= cutoff,
        ).order_by(Order.placed_at.desc()).limit(limit).all()
    
    def get_by_status(self, status: str, limit: int = 100) -> List[Order]:
        """Get orders by status."""
        return self._db.query(Order).filter(
            Order.status == status,
        ).order_by(Order.placed_at.desc()).limit(limit).all()
    
    def get_revenue_by_period(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Decimal:
        """Calculate total revenue for a period."""
        result = self._db.query(
            func.sum(Order.total),
        ).filter(
            Order.placed_at >= start_date,
            Order.placed_at <= end_date,
            Order.status.in_(["paid", "shipped", "delivered"]),
        ).scalar()
        
        return Decimal(str(result or 0))
    
    def count_by_status(self) -> Dict[str, int]:
        """Count orders by status."""
        results = self._db.query(
            Order.status,
            func.count(Order.id),
        ).group_by(Order.status).all()
        
        return {status: count for status, count in results}
    
    def add_item(
        self,
        order_id: str,
        product_id: str,
        quantity: int,
        price: Decimal,
    ) -> Optional[OrderItem]:
        """Add item to order."""
        order = self.get_by_id(order_id)
        if not order:
            return None
        
        item = OrderItem(
            order_id=order_id,
            product_id=product_id,
            quantity=quantity,
            price=price,
        )
        self._db.add(item)
        self._db.commit()
        self._db.refresh(item)
        return item
    
    def update_status(self, order_id: str, status: str) -> Optional[Order]:
        """Update order status."""
        return self.update(order_id, {"status": status})
    
    def create_return_request(
        self,
        order_id: str,
        items: List[Dict[str, Any]],
        reason: str,
    ) -> Optional[ReturnRequest]:
        """Create return request for order."""
        order = self.get_by_id(order_id)
        if not order:
            return None
        
        return_request = ReturnRequest(
            order_id=order_id,
            items=items,
            reason=reason,
        )
        self._db.add(return_request)
        self._db.commit()
        self._db.refresh(return_request)
        return return_request
    
    def get_pending_returns(self, limit: int = 50) -> List[ReturnRequest]:
        """Get pending return requests."""
        return self._db.query(ReturnRequest).filter(
            ReturnRequest.status == "pending",
        ).order_by(ReturnRequest.requested_at.desc()).limit(limit).all()
