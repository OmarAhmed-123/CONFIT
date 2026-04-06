"""
CONFIT Backend - JWT Handler
============================
JWT token generation, validation, and refresh token management.
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

import jwt
from pydantic import BaseModel

from core.config import settings


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# Use secrets manager for production secrets
from core.security.secrets_manager import secrets_manager

JWT_SECRET = secrets_manager.get("JWT_SECRET") or os.getenv("JWT_SECRET", "change-me-in-production-min-32-chars")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
JWT_REFRESH_EXPIRY_DAYS = int(os.getenv("JWT_REFRESH_EXPIRY_DAYS", "7"))
JWT_ISSUER = "confit"
JWT_AUDIENCE = "confit-users"

# Validate JWT secret in production
if settings.is_production and len(JWT_SECRET) < 32:
    logger.critical("JWT_SECRET is too short for production! Minimum 32 characters required.")


# ─────────────────────────────────────────────────────────────────────────────
# TOKEN TYPES
# ─────────────────────────────────────────────────────────────────────────────

class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"
    RESET_PASSWORD = "reset_password"
    VERIFY_EMAIL = "verify_email"
    VERIFY_PHONE = "verify_phone"


# ─────────────────────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TokenPayload:
    """JWT token payload."""
    sub: str  # User ID
    email: str
    type: str = TokenType.ACCESS
    roles: list = None
    iat: datetime = None
    exp: datetime = None
    jti: str = None  # JWT ID for revocation
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = []
        if self.iat is None:
            self.iat = datetime.now(timezone.utc)
        if self.jti is None:
            self.jti = secrets.token_urlsafe(16)


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds
    refresh_expires_in: int  # seconds
    family_id: Optional[str] = None  # For refresh token rotation tracking


class DecodedToken(BaseModel):
    """Decoded JWT token."""
    user_id: str
    email: str
    roles: list[str] = []
    token_type: str
    jti: str
    exp: datetime
    iat: datetime
    valid: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# JWT HANDLER
# ─────────────────────────────────────────────────────────────────────────────

class JWTHandler:
    """JWT token handler with access and refresh token support."""
    
    def __init__(
        self,
        secret: str = JWT_SECRET,
        algorithm: str = JWT_ALGORITHM,
        access_expiry_hours: int = JWT_ACCESS_EXPIRY_HOURS,
        refresh_expiry_days: int = JWT_REFRESH_EXPIRY_DAYS,
        issuer: str = JWT_ISSUER,
        audience: str = JWT_AUDIENCE,
    ):
        self.secret = secret
        self.algorithm = algorithm
        self.access_expiry_hours = access_expiry_hours
        self.refresh_expiry_days = refresh_expiry_days
        self.issuer = issuer
        self.audience = audience
        self._blacklist = None
    
    async def _get_blacklist(self):
        """Get token blacklist lazily."""
        if self._blacklist is None:
            from core.security.token_blacklist import token_blacklist
            self._blacklist = token_blacklist
        return self._blacklist
    
    def _generate_jti(self) -> str:
        """Generate unique JWT ID."""
        return secrets.token_urlsafe(32)
    
    def _hash_token(self, token: str) -> str:
        """Hash token for storage (used for refresh tokens)."""
        return hashlib.sha256(token.encode()).hexdigest()
    
    # ─────────────────────────────────────────────────────────────────────────
    # ACCESS TOKEN
    # ─────────────────────────────────────────────────────────────────────────
    
    def create_access_token(
        self,
        user_id: str,
        email: str,
        roles: list[str] = None,
        additional_claims: Dict[str, Any] = None,
    ) -> str:
        """Create JWT access token."""
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=self.access_expiry_hours)
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": TokenType.ACCESS,
            "roles": roles or [],
            "iat": now,
            "exp": exp,
            "iss": self.issuer,
            "aud": self.audience,
            "jti": self._generate_jti(),
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)
    
    # ─────────────────────────────────────────────────────────────────────────
    # REFRESH TOKEN
    # ─────────────────────────────────────────────────────────────────────────
    
    def create_refresh_token(
        self,
        user_id: str,
        email: str,
        device_id: Optional[str] = None,
        family_id: Optional[str] = None,
    ) -> str:
        """Create JWT refresh token."""
        now = datetime.now(timezone.utc)
        exp = now + timedelta(days=self.refresh_expiry_days)
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": TokenType.REFRESH,
            "iat": now,
            "exp": exp,
            "iss": self.issuer,
            "aud": self.audience,
            "jti": self._generate_jti(),
            "device_id": device_id,
            "family_id": family_id or self._generate_jti(),  # Family ID for rotation tracking
        }
        
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)
    
    # ─────────────────────────────────────────────────────────────────────────
    # TOKEN PAIR
    # ─────────────────────────────────────────────────────────────────────────
    
    async def create_token_pair(
        self,
        user_id: str,
        email: str,
        roles: list[str] = None,
        device_id: Optional[str] = None,
    ) -> TokenPair:
        """Create access and refresh token pair with family tracking."""
        # Generate family ID for refresh token rotation
        family_id = self._generate_jti()
        
        access_token = self.create_access_token(user_id, email, roles)
        refresh_token = self.create_refresh_token(user_id, email, device_id, family_id)
        
        # Register token family for rotation tracking
        blacklist = await self._get_blacklist()
        decoded = self.decode_token(refresh_token)
        if decoded:
            await blacklist.create_token_family(
                family_id=family_id,
                refresh_jti=decoded.jti,
                user_id=user_id,
                expires_at=decoded.exp,
            )
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=self.access_expiry_hours * 3600,
            refresh_expires_in=self.refresh_expiry_days * 24 * 3600,
            family_id=family_id,
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # VALIDATION
    # ─────────────────────────────────────────────────────────────────────────
    
    def decode_token(
        self,
        token: str,
        expected_type: Optional[str] = None,
    ) -> Optional[DecodedToken]:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience,
            )
            
            decoded = DecodedToken(
                user_id=payload["sub"],
                email=payload["email"],
                roles=payload.get("roles", []),
                token_type=payload.get("type", TokenType.ACCESS),
                jti=payload.get("jti", ""),
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                valid=True,
            )
            
            # Verify token type if specified
            if expected_type and decoded.token_type != expected_type:
                decoded.valid = False
            
            return decoded
            
        except jwt.ExpiredSignatureError:
            return DecodedToken(
                user_id="",
                email="",
                token_type="",
                jti="",
                exp=datetime.now(timezone.utc),
                iat=datetime.now(timezone.utc),
                valid=False,
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    async def decode_token_with_blacklist_check(
        self,
        token: str,
        expected_type: Optional[str] = None,
    ) -> Optional[DecodedToken]:
        """Decode token and check if it's blacklisted."""
        decoded = self.decode_token(token, expected_type)
        
        if not decoded or not decoded.valid:
            return decoded
        
        # Check blacklist
        blacklist = await self._get_blacklist()
        if await blacklist.is_blacklisted(decoded.jti):
            logger.warning(f"Blacklisted token used: {decoded.jti[:8]}...")
            decoded.valid = False
        
        
        return decoded
    
    async def validate_access_token(self, token: str) -> Optional[DecodedToken]:
        """Validate access token with blacklist check."""
        return await self.decode_token_with_blacklist_check(token, expected_type=TokenType.ACCESS)
    
    async def validate_refresh_token(self, token: str) -> Optional[DecodedToken]:
        """Validate refresh token with blacklist check."""
        return await self.decode_token_with_blacklist_check(token, expected_type=TokenType.REFRESH)
    
    # ─────────────────────────────────────────────────────────────────────────
    # SPECIAL PURPOSE TOKENS
    # ─────────────────────────────────────────────────────────────────────────
    
    def create_password_reset_token(
        self,
        user_id: str,
        email: str,
        expiry_hours: int = 1,
    ) -> str:
        """Create password reset token."""
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=expiry_hours)
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": TokenType.RESET_PASSWORD,
            "iat": now,
            "exp": exp,
            "iss": self.issuer,
            "aud": self.audience,
            "jti": self._generate_jti(),
        }
        
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)
    
    def create_email_verification_token(
        self,
        user_id: str,
        email: str,
        expiry_hours: int = 24,
    ) -> str:
        """Create email verification token."""
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=expiry_hours)
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": TokenType.VERIFY_EMAIL,
            "iat": now,
            "exp": exp,
            "iss": self.issuer,
            "aud": self.audience,
            "jti": self._generate_jti(),
        }
        
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)
    
    def validate_password_reset_token(self, token: str) -> Optional[DecodedToken]:
        """Validate password reset token."""
        return self.decode_token(token, expected_type=TokenType.RESET_PASSWORD)
    
    def validate_email_verification_token(self, token: str) -> Optional[DecodedToken]:
        """Validate email verification token."""
        return self.decode_token(token, expected_type=TokenType.VERIFY_EMAIL)
    
    # ─────────────────────────────────────────────────────────────────────────
    # UTILITY METHODS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def refresh_access_token(
        self,
        refresh_token: str,
        roles: list[str] = None,
    ) -> Tuple[Optional[TokenPair], bool]:
        """
        Create new token pair from valid refresh token with rotation.
        
        Returns:
            Tuple of (TokenPair or None, security_breach_detected)
        """
        decoded = await self.validate_refresh_token(refresh_token)
        
        if not decoded or not decoded.valid:
            return None, False
        
        # Get family ID from token
        family_id = None
        try:
            payload = jwt.decode(
                refresh_token,
                self.secret,
                algorithms=[self.algorithm],
                options={"verify_exp": False},
            )
            family_id = payload.get("family_id")
        except Exception:
            pass
        
        # Check token family rotation
        if family_id:
            blacklist = await self._get_blacklist()
            success, breach_detected = await blacklist.rotate_refresh_token(
                family_id=family_id,
                old_jti=decoded.jti,
                new_jti=self._generate_jti(),
            )
            
            if breach_detected:
                logger.critical(f"Token reuse attack detected for user {decoded.user_id}")
                return None, True
            
            if not success:
                return None, False
        
        
        # Create new token pair
        new_pair = await self.create_token_pair(
            user_id=decoded.user_id,
            email=decoded.email,
            roles=roles,
        )
        
        # Blacklist old refresh token
        blacklist = await self._get_blacklist()
        await blacklist.add_token(
            jti=decoded.jti,
            expires_at=decoded.exp,
            user_id=decoded.user_id,
            reason="rotated",
        )
        
        return new_pair, False
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """Get token expiry datetime."""
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                options={"verify_exp": False},
            )
            return datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        except jwt.InvalidTokenError:
            return None
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired."""
        expiry = self.get_token_expiry(token)
        if expiry is None:
            return True
        return datetime.now(timezone.utc) > expiry
    
    async def revoke_token(
        self,
        jti: str,
        user_id: str,
        expires_at: datetime,
        reason: str = "logout",
    ) -> bool:
        """Revoke a token by adding to blacklist."""
        blacklist = await self._get_blacklist()
        return await blacklist.add_token(jti, expires_at, user_id, reason)
    
    async def revoke_all_user_tokens(
        self,
        user_id: str,
        reason: str = "security",
    ) -> int:
        """Revoke all tokens for a user."""
        blacklist = await self._get_blacklist()
        return await blacklist.revoke_all_user_tokens(user_id, reason)


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL INSTANCE
# ─────────────────────────────────────────────────────────────────────────────

jwt_handler = JWTHandler()
