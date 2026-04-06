"""
CONFIT Backend - Authentication Application Service
====================================================
High-level authentication orchestration using domain and infrastructure layers.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities import User
from domain.base import Email, PaginatedResult, PaginationParams, UserRole
from infrastructure.repositories.user_repository import UserRepository
from core.security.jwt_handler import JWTHandler, TokenPair
from core.security.password_handler import PasswordHandler, PasswordValidationResult
from core.security.oauth_handler import OAuthHandler, OAuthUserInfo
from core.security.rbac import Role, RBACManager
from core.security.input_sanitization import (
    sanitize_string,
    sanitize_email,
    sanitize_phone,
    detect_sql_injection,
    detect_xss,
    SecurityValidationError,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DTOs
# ─────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, EmailStr, validator
from typing import List, Dict, Any


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    
    @validator('password')
    def password_strength(cls, v):
        result = PasswordHandler().validate_password(v)
        if not result.valid:
            raise ValueError(result.errors[0])
        return v


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str
    device_id: Optional[str] = None
    remember_me: bool = False


class LoginResponse(BaseModel):
    """Login response with tokens and user info."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: "UserDTO"


class UserDTO(BaseModel):
    """User data transfer object."""
    id: str
    email: str
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    roles: List[str] = []
    email_verified: bool = False
    phone_verified: bool = False
    is_verified: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str
    
    @validator('new_password')
    def password_strength(cls, v):
        result = PasswordHandler().validate_password(v)
        if not result.valid:
            raise ValueError(result.errors[0])
        return v


class ResetPasswordRequest(BaseModel):
    """Reset password request."""
    email: EmailStr


class ResetPasswordConfirmRequest(BaseModel):
    """Reset password confirmation."""
    token: str
    new_password: str
    
    @validator('new_password')
    def password_strength(cls, v):
        result = PasswordHandler().validate_password(v)
        if not result.valid:
            raise ValueError(result.errors[0])
        return v


class OAuthLoginRequest(BaseModel):
    """OAuth login request."""
    provider: str
    code: str
    state: str


# ─────────────────────────────────────────────────────────────────────────────
# AUTH SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class AuthService:
    """Authentication application service."""
    
    def __init__(
        self,
        session: AsyncSession,
        jwt_handler: Optional[JWTHandler] = None,
        password_handler: Optional[PasswordHandler] = None,
        oauth_handler: Optional[OAuthHandler] = None,
        rbac_manager: Optional[RBACManager] = None,
    ):
        self.session = session
        self.user_repository = UserRepository(session)
        self.jwt_handler = jwt_handler or JWTHandler()
        self.password_handler = password_handler or PasswordHandler()
        self.oauth_handler = oauth_handler or OAuthHandler()
        self.rbac_manager = rbac_manager or RBACManager()
    
    # ─────────────────────────────────────────────────────────────────────────
    # REGISTRATION
    # ─────────────────────────────────────────────────────────────────────────
    
    async def register(
        self,
        email: str,
        password: str,
        name: str,
        **kwargs
    ) -> Tuple[Optional[UserDTO], Optional[str]]:
        """
        Register a new user.
        
        Returns:
            Tuple of (user_dto, error_message)
        """
        # Sanitize and validate inputs
        try:
            email = sanitize_email(email)
            name = sanitize_string(name, max_length=100, allow_unicode=True)
            
            # Sanitize optional fields
            if 'first_name' in kwargs and kwargs['first_name']:
                kwargs['first_name'] = sanitize_string(kwargs['first_name'], max_length=50, allow_unicode=True)
            if 'last_name' in kwargs and kwargs['last_name']:
                kwargs['last_name'] = sanitize_string(kwargs['last_name'], max_length=50, allow_unicode=True)
            if 'phone' in kwargs and kwargs['phone']:
                kwargs['phone'] = sanitize_phone(kwargs['phone'])
        except SecurityValidationError as e:
            return None, str(e)
        
        # Check for injection attempts in inputs
        if detect_sql_injection(name) or detect_xss(name):
            logger.warning(f"Injection attempt detected in registration: {email}")
            return None, "Invalid characters in name"
        
        # Check if user already exists
        existing = await self.user_repository.get_by_email(email)
        if existing:
            return None, "An account with this email already exists"
        
        # Validate password
        validation = self.password_handler.validate_password(password)
        if not validation.valid:
            return None, validation.errors[0]
        
        # Hash password
        password_hash = self.password_handler.hash_password(password)
        
        # Create user entity
        user = User.create(
            email=email,
            password_hash=password_hash,
            name=name,
            **kwargs
        )
        
        # Add default role
        user.add_role(UserRole.USER)
        
        # Persist user
        saved_user = await self.user_repository.add(user)
        
        logger.info(f"User registered: {email}")
        
        return self._to_dto(saved_user), None
    
    # ─────────────────────────────────────────────────────────────────────────
    # LOGIN
    # ─────────────────────────────────────────────────────────────────────────
    
    async def login(
        self,
        email: str,
        password: str,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[Optional[LoginResponse], Optional[str]]:
        """
        Authenticate user and return tokens.
        
        Returns:
            Tuple of (login_response, error_message)
        """
        # Sanitize email input
        try:
            email = sanitize_email(email)
            if device_id:
                device_id = sanitize_string(device_id, max_length=100)
        except SecurityValidationError as e:
            return None, "Invalid input format"
        
        # Get user by email
        user = await self.user_repository.get_by_email(email)
        if not user:
            return None, "Invalid email or password"
        
        # Check if user is active
        if not user.is_active:
            return None, "Account is deactivated"
        
        # Verify password
        if not self.password_handler.verify_password(password, user.password_hash):
            return None, "Invalid email or password"
        
        # Check if password needs rehash
        if self.password_handler.needs_rehash(user.password_hash):
            user.password_hash = self.password_handler.hash_password(password)
            await self.user_repository.update(user)
        
        # Get user roles
        roles = [r.role.value for r in user.roles if not r.is_expired()]
        
        # Create tokens (async with blacklist)
        token_pair = await self.jwt_handler.create_token_pair(
            user_id=str(user.id),
            email=user.email.address if hasattr(user.email, 'address') else user.email,
            roles=roles,
            device_id=device_id,
        )
        
        # Update login info
        await self.user_repository.update_last_login(
            user_id=user.id,
            ip_address=ip_address or "",
            user_agent=user_agent or "",
        )
        
        logger.info(f"User logged in: {email}")
        
        return LoginResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            token_type=token_pair.token_type,
            expires_in=token_pair.expires_in,
            user=self._to_dto(user),
        ), None
    
    # ─────────────────────────────────────────────────────────────────────────
    # OAUTH
    # ─────────────────────────────────────────────────────────────────────────
    
    async def oauth_login(
        self,
        provider: str,
        code: str,
        state: str,
        ip_address: Optional[str] = None,
    ) -> Tuple[Optional[LoginResponse], Optional[str]]:
        """
        Handle OAuth login/registration.
        
        Returns:
            Tuple of (login_response, error_message)
        """
        # Handle OAuth callback
        oauth_user = await self.oauth_handler.handle_callback(provider, code, state)
        if not oauth_user:
            return None, "OAuth authentication failed"
        
        # Check if user exists by email
        user = await self.user_repository.get_by_email(oauth_user.email)
        
        if not user:
            # Create new user from OAuth info
            password_hash = self.password_handler.hash_password(
                self.password_handler.generate_password()
            )
            
            user = User.create(
                email=oauth_user.email,
                password_hash=password_hash,
                name=oauth_user.name or oauth_user.email.split("@")[0],
                first_name=oauth_user.first_name,
                last_name=oauth_user.last_name,
                avatar_url=oauth_user.avatar_url,
            )
            
            if oauth_user.email_verified:
                user.verify_email()
            
            user.add_role(UserRole.USER)
            user = await self.user_repository.add(user)
            
            logger.info(f"New user registered via {provider}: {oauth_user.email}")
        
        # Get roles and create tokens
        roles = [r.role.value for r in user.roles if not r.is_expired()]
        token_pair = self.jwt_handler.create_token_pair(
            user_id=str(user.id),
            email=user.email.address if hasattr(user.email, 'address') else user.email,
            roles=roles,
        )
        
        # Update login info
        await self.user_repository.update_last_login(
            user_id=user.id,
            ip_address=ip_address or "",
            user_agent=f"OAuth/{provider}",
        )
        
        return LoginResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            token_type=token_pair.token_type,
            expires_in=token_pair.expires_in,
            user=self._to_dto(user),
        ), None
    
    def get_oauth_url(self, provider: str, redirect_to: Optional[str] = None) -> Optional[str]:
        """Get OAuth authorization URL."""
        return self.oauth_handler.get_authorization_url(provider, redirect_to)
    
    # ─────────────────────────────────────────────────────────────────────────
    # TOKEN MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────
    
    async def refresh_tokens(
        self,
        refresh_token: str,
    ) -> Tuple[Optional[TokenPair], Optional[str]]:
        """
        Refresh access token using refresh token.
        
        Returns:
            Tuple of (token_pair, error_message)
        """
        # Validate refresh token
        decoded = self.jwt_handler.validate_refresh_token(refresh_token)
        if not decoded or not decoded.valid:
            return None, "Invalid or expired refresh token"
        
        # Get user
        user = await self.user_repository.get_by_id(UUID(decoded.user_id))
        if not user or not user.is_active:
            return None, "User not found or deactivated"
        
        # Get roles
        roles = [r.role.value for r in user.roles if not r.is_expired()]
        
        # Create new token pair
        token_pair = self.jwt_handler.create_token_pair(
            user_id=str(user.id),
            email=user.email.address if hasattr(user.email, 'address') else user.email,
            roles=roles,
        )
        
        return token_pair, None
    
    async def logout(self, user_id: UUID, jti: str) -> None:
        """
        Logout user by invalidating token.
        
        In production, this would add the token JTI to a blacklist in Redis.
        """
        # TODO: Implement token blacklist in Redis
        logger.info(f"User logged out: {user_id}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # PASSWORD MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────
    
    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Change user password.
        
        Returns:
            Tuple of (success, error_message)
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            return False, "User not found"
        
        # Verify current password
        if not self.password_handler.verify_password(current_password, user.password_hash):
            return False, "Current password is incorrect"
        
        # Validate new password
        validation = self.password_handler.validate_password(new_password)
        if not validation.valid:
            return False, validation.errors[0]
        
        # Update password
        user.password_hash = self.password_handler.hash_password(new_password)
        await self.user_repository.update(user)
        
        logger.info(f"Password changed for user: {user_id}")
        
        return True, None
    
    async def request_password_reset(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Request password reset email.
        
        Returns:
            Tuple of (success, error_message)
        """
        user = await self.user_repository.get_by_email(email)
        if not user:
            # Don't reveal if email exists
            return True, None
        
        # Create reset token
        reset_token = self.jwt_handler.create_password_reset_token(
            user_id=str(user.id),
            email=user.email.address if hasattr(user.email, 'address') else user.email,
        )
        
        # TODO: Send email with reset link
        # await self.email_service.send_password_reset_email(user.email, reset_token)
        
        logger.info(f"Password reset requested for: {email}")
        
        return True, None
    
    async def confirm_password_reset(
        self,
        token: str,
        new_password: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Confirm password reset with token.
        
        Returns:
            Tuple of (success, error_message)
        """
        # Validate reset token
        decoded = self.jwt_handler.validate_password_reset_token(token)
        if not decoded or not decoded.valid:
            return False, "Invalid or expired reset token"
        
        # Get user
        user = await self.user_repository.get_by_id(UUID(decoded.user_id))
        if not user:
            return False, "User not found"
        
        # Validate new password
        validation = self.password_handler.validate_password(new_password)
        if not validation.valid:
            return False, validation.errors[0]
        
        # Update password
        user.password_hash = self.password_handler.hash_password(new_password)
        await self.user_repository.update(user)
        
        logger.info(f"Password reset completed for user: {user.id}")
        
        return True, None
    
    # ─────────────────────────────────────────────────────────────────────────
    # EMAIL VERIFICATION
    # ─────────────────────────────────────────────────────────────────────────
    
    async def request_email_verification(
        self,
        user_id: UUID,
    ) -> Tuple[bool, Optional[str]]:
        """Request email verification."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            return False, "User not found"
        
        if user.email_verified:
            return False, "Email already verified"
        
        # Create verification token
        verification_token = self.jwt_handler.create_email_verification_token(
            user_id=str(user.id),
            email=user.email.address if hasattr(user.email, 'address') else user.email,
        )
        
        # TODO: Send verification email
        # await self.email_service.send_verification_email(user.email, verification_token)
        
        return True, None
    
    async def verify_email(self, token: str) -> Tuple[bool, Optional[str]]:
        """Verify email with token."""
        decoded = self.jwt_handler.validate_email_verification_token(token)
        if not decoded or not decoded.valid:
            return False, "Invalid or expired verification token"
        
        await self.user_repository.verify_email(UUID(decoded.user_id))
        
        return True, None
    
    # ─────────────────────────────────────────────────────────────────────────
    # USER MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[UserDTO]:
        """Get user by ID."""
        user = await self.user_repository.get_by_id(user_id)
        return self._to_dto(user) if user else None
    
    async def get_user_by_email(self, email: str) -> Optional[UserDTO]:
        """Get user by email."""
        user = await self.user_repository.get_by_email(email)
        return self._to_dto(user) if user else None
    
    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    
    def _to_dto(self, user: User) -> UserDTO:
        """Convert user entity to DTO."""
        return UserDTO(
            id=str(user.id),
            email=user.email.address if hasattr(user.email, 'address') else user.email,
            name=user.name,
            first_name=user.first_name,
            last_name=user.last_name,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            roles=[r.role.value for r in user.roles if not r.is_expired()],
            email_verified=user.email_verified,
            phone_verified=user.phone_verified,
            is_verified=user.is_verified,
            created_at=user.created_at,
        )
