"""
CONFIT Backend - User Repository Implementation
===============================================
SQLAlchemy implementation of user repository.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities import User, UserRoleAssignment, UserAddress
from domain.base import PaginatedResult, PaginationParams, UserRole
from domain.repositories import IUserRepository
from infrastructure.repositories.base import BaseRepository
from database.models import User as UserModel, UserRole as UserRoleModel
from models.profile_models import UserAddress as UserAddressModel


class UserRepository(BaseRepository[UserModel, User], IUserRepository):
    """SQLAlchemy implementation of user repository."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, UserModel, User)
    
    def _model_to_entity(self, model: UserModel) -> User:
        """Convert ORM model to domain entity."""
        user = User(
            id=UUID(model.id) if isinstance(model.id, str) else model.id,
            email=model.email,
            password_hash=model.password_hash,
            name=model.name,
            first_name=model.first_name,
            last_name=model.last_name,
            display_name=model.display_name,
            avatar_url=model.avatar_url,
            bio=model.bio,
            phone=model.phone,
            date_of_birth=model.date_of_birth,
            gender=model.gender,
            country_code=model.country_code,
            timezone=model.timezone,
            language=model.language,
            currency=model.currency,
            email_verified=model.email_verified,
            phone_verified=model.phone_verified,
            is_verified=model.is_verified,
            is_staff=model.is_staff,
            is_active=model.is_active,
            settings=model.settings or {},
            notification_preferences=model.notification_preferences or {},
            last_login_at=model.last_login_at,
            last_login_ip=model.last_login_ip,
            login_count=model.login_count,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
        )
        
        # Convert roles
        user.roles = [
            UserRoleAssignment(
                id=UUID(r.id) if isinstance(r.id, str) else r.id,
                user_id=UUID(r.user_id) if isinstance(r.user_id, str) else r.user_id,
                role=UserRole(r.role),
                granted_by=UUID(r.granted_by) if r.granted_by else None,
                granted_at=r.granted_at,
                expires_at=r.expires_at,
            )
            for r in model.roles
        ]
        
        # Convert addresses
        user.addresses = [
            UserAddress(
                id=UUID(a.id) if isinstance(a.id, str) else a.id,
                user_id=UUID(a.user_id) if isinstance(a.user_id, str) else a.user_id,
                label=a.label,
                recipient_name=a.recipient_name,
                phone=a.phone,
                address=self._address_from_model(a),
                is_default_shipping=a.is_default_shipping,
                is_default_billing=a.is_default_billing,
                is_verified=a.is_verified,
            )
            for a in model.addresses
        ]
        
        return user
    
    def _entity_to_model(self, entity: User) -> UserModel:
        """Convert domain entity to ORM model."""
        model = UserModel(
            id=str(entity.id),
            email=entity.email.address if hasattr(entity.email, 'address') else entity.email,
            password_hash=entity.password_hash,
            name=entity.name,
            first_name=entity.first_name,
            last_name=entity.last_name,
            display_name=entity.display_name,
            avatar_url=entity.avatar_url,
            bio=entity.bio,
            phone=entity.phone,
            date_of_birth=entity.date_of_birth,
            gender=entity.gender,
            country_code=entity.country_code,
            timezone=entity.timezone,
            language=entity.language,
            currency=entity.currency,
            email_verified=entity.email_verified,
            phone_verified=entity.phone_verified,
            is_verified=entity.is_verified,
            is_staff=entity.is_staff,
            is_active=entity.is_active,
            settings=entity.settings,
            notification_preferences=entity.notification_preferences,
            last_login_at=entity.last_login_at,
            last_login_ip=entity.last_login_ip,
            login_count=entity.login_count,
            version=entity.version,
        )
        return model
    
    def _update_model_from_entity(self, model: UserModel, entity: User) -> None:
        """Update model fields from entity."""
        model.email = entity.email.address if hasattr(entity.email, 'address') else entity.email
        model.password_hash = entity.password_hash
        model.name = entity.name
        model.first_name = entity.first_name
        model.last_name = entity.last_name
        model.display_name = entity.display_name
        model.avatar_url = entity.avatar_url
        model.bio = entity.bio
        model.phone = entity.phone
        model.date_of_birth = entity.date_of_birth
        model.gender = entity.gender
        model.country_code = entity.country_code
        model.timezone = entity.timezone
        model.language = entity.language
        model.currency = entity.currency
        model.email_verified = entity.email_verified
        model.phone_verified = entity.phone_verified
        model.is_verified = entity.is_verified
        model.is_staff = entity.is_staff
        model.is_active = entity.is_active
        model.settings = entity.settings
        model.notification_preferences = entity.notification_preferences
        model.last_login_at = entity.last_login_at
        model.last_login_ip = entity.last_login_ip
        model.login_count = entity.login_count
        model.version = entity.version
        model.updated_at = datetime.now(timezone.utc)
    
    def _address_from_model(self, model: UserAddressModel):
        """Convert address model to value object."""
        from domain.base import Address
        return Address(
            line1=model.address_line1,
            line2=model.address_line2,
            city=model.city,
            state_province=model.state_province,
            postal_code=model.postal_code,
            country_code=model.country_code,
        )
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        return await self._get_by_field("email", email.lower())
    
    async def get_by_phone(self, phone: str) -> Optional[User]:
        """Get user by phone number."""
        return await self._get_by_field("phone", phone)
    
    async def search(
        self,
        query: str,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[User]:
        """Search users by name or email."""
        search_term = f"%{query.lower()}%"
        
        # Count query - cross-database compatible (func.lower + like instead of ilike)
        count_query = select(func.count()).select_from(UserModel).where(
            or_(
                func.lower(UserModel.name).like(search_term),
                func.lower(UserModel.email).like(search_term),
                func.lower(UserModel.first_name).like(search_term),
                func.lower(UserModel.last_name).like(search_term),
            )
        )
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Data query - cross-database compatible
        query_obj = select(UserModel).where(
            or_(
                func.lower(UserModel.name).like(search_term),
                func.lower(UserModel.email).like(search_term),
                func.lower(UserModel.first_name).like(search_term),
                func.lower(UserModel.last_name).like(search_term),
            )
        )
        
        if pagination:
            query_obj = query_obj.offset(pagination.offset).limit(pagination.limit)
        
        result = await self.session.execute(query_obj)
        models = result.scalars().all()
        
        entities = [self._model_to_entity(m) for m in models]
        
        total_pages = (total + (pagination.page_size if pagination else 20) - 1) // (pagination.page_size if pagination else 20)
        
        return PaginatedResult(
            items=entities,
            total=total,
            page=pagination.page if pagination else 1,
            page_size=pagination.page_size if pagination else len(entities),
            total_pages=total_pages
        )
    
    async def get_by_role(
        self,
        role: str,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[User]:
        """Get users by role."""
        # Join with roles table
        query = select(UserModel).join(UserRoleModel).where(UserRoleModel.role == role)
        
        # Count
        count_query = select(func.count()).select_from(UserModel).join(UserRoleModel).where(
            UserRoleModel.role == role
        )
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.limit)
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        entities = [self._model_to_entity(m) for m in models]
        
        total_pages = (total + (pagination.page_size if pagination else 20) - 1) // (pagination.page_size if pagination else 20)
        
        return PaginatedResult(
            items=entities,
            total=total,
            page=pagination.page if pagination else 1,
            page_size=pagination.page_size if pagination else len(entities),
            total_pages=total_pages
        )
    
    async def get_active_users(
        self,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResult[User]:
        """Get all active users."""
        return await self._get_all_by_field("is_active", True, pagination)
    
    async def update_last_login(
        self,
        user_id: UUID,
        ip_address: str,
        user_agent: str
    ) -> None:
        """Update user's last login information."""
        query = select(UserModel).where(UserModel.id == str(user_id))
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        if model:
            model.last_login_at = datetime.now(timezone.utc)
            model.last_login_ip = ip_address
            model.login_count += 1
            await self.session.flush()
    
    async def verify_email(self, user_id: UUID) -> None:
        """Mark user's email as verified."""
        query = select(UserModel).where(UserModel.id == str(user_id))
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        if model:
            model.email_verified = True
            model.is_verified = model.phone_verified or True
            await self.session.flush()
    
    async def verify_phone(self, user_id: UUID) -> None:
        """Mark user's phone as verified."""
        query = select(UserModel).where(UserModel.id == str(user_id))
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        if model:
            model.phone_verified = True
            model.is_verified = model.email_verified or True
            await self.session.flush()
