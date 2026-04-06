"""CONFIT Backend — User Repository."""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from repositories.base import BaseRepository
from database.models import User, UserRole, AppRole


class UserRepository(BaseRepository[User]):
    """Repository for User entity operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, User)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self._db.query(User).filter(User.email == email.lower()).first()
    
    def get_with_relations(self, user_id: str) -> Optional[User]:
        """Get user with all relationships loaded."""
        return self._db.query(User).options(
            joinedload(User.orders),
            joinedload(User.wardrobe_items),
            joinedload(User.outfits),
            joinedload(User.digital_twins),
        ).filter(User.id == user_id).first()
    
    def search(self, query: str, limit: int = 20) -> List[User]:
        """Search users by name or email."""
        return self._db.query(User).filter(
            or_(
                User.name.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%"),
            )
        ).limit(limit).all()
    
    def get_by_role(self, role: AppRole, limit: int = 100) -> List[User]:
        """Get users by role."""
        return self._db.query(User).join(UserRole).filter(
            UserRole.role == role
        ).limit(limit).all()
    
    def add_role(self, user_id: str, role: AppRole) -> Optional[UserRole]:
        """Add role to user."""
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        user_role = UserRole(user_id=user_id, role=role)
        self._db.add(user_role)
        self._db.commit()
        self._db.refresh(user_role)
        return user_role
    
    def remove_role(self, user_id: str, role: AppRole) -> bool:
        """Remove role from user."""
        deleted = self._db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role == role,
        ).delete()
        self._db.commit()
        return deleted > 0
    
    def update_style_preference(
        self, user_id: str, style_preference: str
    ) -> Optional[User]:
        """Update user style preference."""
        return self.update(user_id, {"style_preference": style_preference})
    
    def update_body_profile(
        self, user_id: str, body_profile: Dict[str, Any]
    ) -> Optional[User]:
        """Update user body profile."""
        return self.update(user_id, {"body_profile": body_profile})
    
    def set_marketing_consent(self, user_id: str, consent: bool) -> Optional[User]:
        """Set marketing consent."""
        return self.update(user_id, {"marketing_consent": consent})
    
    def set_data_sharing_consent(self, user_id: str, consent: bool) -> Optional[User]:
        """Set data sharing consent."""
        return self.update(user_id, {"data_sharing_consent": consent})
