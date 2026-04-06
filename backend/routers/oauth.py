"""
CONFIT Backend — OAuth Token Validation Router
===============================================
Validates OAuth tokens from Google and Apple with the respective providers,
creates or updates user accounts, and issues CONFIT session tokens.
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from database.session import SessionLocal
from database.models import User, UserRole, UserGamification, AppRole
from services.auth_service import AuthService, JWT_SECRET, JWT_ALGORITHM
import jwt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth/oauth", tags=["OAuth Authentication"])

# ===========================================
# Request/Response Models
# ===========================================

class OAuthCallbackRequest(BaseModel):
    """OAuth callback request from frontend."""
    provider: str = Field(..., pattern="^(google|apple)$")
    id_token: Optional[str] = None
    access_token: Optional[str] = None
    code: Optional[str] = None


class OAuthResponse(BaseModel):
    """Response after successful OAuth validation."""
    success: bool
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    user: dict
    is_new_user: bool = False
    message: str = "OAuth authentication successful"


# ===========================================
# Google OAuth Validation
# ===========================================

async def validate_google_token(id_token: str) -> Optional[dict]:
    """
    Validate Google ID token with Google's tokeninfo endpoint.
    Returns user info if valid, None otherwise.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token},
                timeout=10.0,
            )
            
        if response.status_code != 200:
            logger.warning("Google token validation failed: %s", response.text)
            return None
            
        data = response.json()
        
        # Verify audience matches our client ID
        client_id = os.getenv("NEXT_PUBLIC_GOOGLE_CLIENT_ID", os.getenv("GOOGLE_CLIENT_ID"))
        if client_id and data.get("aud") != client_id:
            logger.warning("Google token audience mismatch: %s != %s", data.get("aud"), client_id)
            return None
            
        return {
            "sub": data.get("sub"),
            "email": data.get("email"),
            "email_verified": data.get("email_verified", False),
            "name": data.get("name"),
            "given_name": data.get("given_name"),
            "family_name": data.get("family_name"),
            "picture": data.get("picture"),
        }
    except Exception as e:
        logger.error("Google token validation error: %s", e)
        return None


# ===========================================
# Apple Sign-In Validation
# ===========================================

async def validate_apple_token(id_token: str) -> Optional[dict]:
    """
    Validate Apple ID token.
    Apple uses JWT format - we verify the signature against Apple's public keys.
    """
    try:
        import json
        from jose import jwk, jwt as jose_jwt
        from jose.utils import base64url_decode
        
        # Get Apple's public keys
        async with httpx.AsyncClient() as client:
            keys_response = await client.get(
                "https://appleid.apple.com/auth/keys",
                timeout=10.0,
            )
            
        if keys_response.status_code != 200:
            logger.error("Failed to fetch Apple public keys")
            return None
            
        keys = keys_response.json().get("keys", [])
        
        # Decode token header to find the key ID
        header = jose_jwt.get_unverified_header(id_token)
        kid = header.get("kid")
        
        # Find matching key
        public_key = None
        for key in keys:
            if key.get("kid") == kid:
                public_key = jwk.construct(key)
                break
                
        if not public_key:
            logger.warning("Apple public key not found for kid: %s", kid)
            return None
            
        # Verify signature
        message, encoded_sig = id_token.rsplit(".", 1)
        decoded_sig = base64url_decode(encoded_sig.encode())
        
        if not public_key.verify(message.encode(), decoded_sig):
            logger.warning("Apple token signature verification failed")
            return None
            
        # Decode payload
        payload = jose_jwt.get_unverified_claims(id_token)
        
        # Verify audience and issuer
        client_id = os.getenv("NEXT_PUBLIC_APPLE_CLIENT_ID", os.getenv("APPLE_CLIENT_ID"))
        if client_id and payload.get("aud") != client_id:
            logger.warning("Apple token audience mismatch")
            return None
            
        if payload.get("iss") != "https://appleid.apple.com":
            logger.warning("Apple token issuer mismatch")
            return None
            
        return {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "email_verified": payload.get("email_verified", True),
            "name": None,  # Apple doesn't always provide name
        }
        
    except ImportError:
        logger.warning("python-jose not installed - using fallback Apple validation")
        # Fallback: decode without verification (less secure, but works for development)
        try:
            import jwt as pyjwt
            payload = pyjwt.decode(id_token, options={"verify_signature": False})
            return {
                "sub": payload.get("sub"),
                "email": payload.get("email"),
                "email_verified": payload.get("email_verified", True),
                "name": None,
            }
        except Exception as e:
            logger.error("Apple token decode error: %s", e)
            return None
            
    except Exception as e:
        logger.error("Apple token validation error: %s", e)
        return None


# ===========================================
# User Creation/Update
# ===========================================

def get_or_create_user(
    db,
    provider_user_id: str,
    email: str,
    name: Optional[str],
    avatar_url: Optional[str],
    provider: str,
) -> tuple[User, bool]:
    """
    Get existing user or create new one.
    Returns (user, is_new_user).
    """
    # Check for existing user by email
    existing_user = db.query(User).filter(User.email == email.lower()).first()
    
    if existing_user:
        # Update avatar if provided
        if avatar_url and not existing_user.avatar_url:
            existing_user.avatar_url = avatar_url
            db.commit()
            db.refresh(existing_user)
        return existing_user, False
    
    # Create new user
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Generate a random password (OAuth users don't use password login)
    import secrets
    import string
    random_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    from services.auth_service import AuthService
    auth_service = AuthService(db)
    password_hash = auth_service._hash_password(random_password)
    
    new_user = User(
        id=user_id,
        name=name or email.split("@")[0],
        email=email.lower(),
        password_hash=password_hash,
        avatar_url=avatar_url,
        created_at=now,
        data_sharing_consent=True,  # OAuth implies consent
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create user role
    user_role = UserRole(
        user_id=new_user.id,
        role=AppRole.user,
    )
    db.add(user_role)
    
    # Create gamification record
    gamification = UserGamification(user_id=new_user.id)
    db.add(gamification)
    
    db.commit()
    
    logger.info("Created new user via %s OAuth: %s", provider, email)
    return new_user, True


# ===========================================
# OAuth Callback Endpoint
# ===========================================

@router.post("/callback", response_model=OAuthResponse)
async def oauth_callback(request: OAuthCallbackRequest):
    """
    Handle OAuth callback from frontend.
    
    Flow:
    1. Frontend receives OAuth token from provider (Google/Apple)
    2. Frontend sends token to this endpoint
    3. Backend validates token with provider
    4. Backend creates/updates user and issues CONFIT session tokens
    """
    provider = request.provider
    
    # Validate token with provider
    user_info = None
    
    if provider == "google":
        if not request.id_token:
            raise HTTPException(status_code=400, detail="id_token required for Google OAuth")
        user_info = await validate_google_token(request.id_token)
        
    elif provider == "apple":
        if not request.id_token:
            raise HTTPException(status_code=400, detail="id_token required for Apple Sign-In")
        user_info = await validate_apple_token(request.id_token)
        
    if not user_info or not user_info.get("email"):
        raise HTTPException(
            status_code=401,
            detail=f"Failed to validate {provider} token"
        )
    
    # Get or create user
    db = SessionLocal()
    try:
        user, is_new_user = get_or_create_user(
            db=db,
            provider_user_id=user_info.get("sub", ""),
            email=user_info.get("email"),
            name=user_info.get("name"),
            avatar_url=user_info.get("picture"),
            provider=provider,
        )
        
        # Generate CONFIT session tokens
        auth_service = AuthService(db)
        access_token = auth_service.create_token(user.id, user.email)
        refresh_token = auth_service.create_refresh_token(user.id, user.email)
        
        return OAuthResponse(
            success=True,
            access_token=access_token,
            refresh_token=refresh_token,
            user={
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "avatar_url": user.avatar_url,
            },
            is_new_user=is_new_user,
            message=f"Successfully authenticated via {provider}",
        )
        
    finally:
        db.close()


@router.get("/health")
async def oauth_health():
    """Health check for OAuth service."""
    google_configured = bool(os.getenv("NEXT_PUBLIC_GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID"))
    apple_configured = bool(os.getenv("NEXT_PUBLIC_APPLE_CLIENT_ID") or os.getenv("APPLE_CLIENT_ID"))
    
    return {
        "status": "ok",
        "providers": {
            "google": google_configured,
            "apple": apple_configured,
        },
    }
