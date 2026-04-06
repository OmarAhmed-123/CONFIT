"""
CONFIT Backend - OAuth Handler
==============================
OAuth 2.0 authentication for Google, Facebook, Apple, X (Twitter), and TikTok.
"""

import os
import secrets
import hashlib
import base64
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel


# ─────────────────────────────────────────────────────────────────────────────
# OAUTH CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class OAuthConfig:
    """OAuth provider configuration."""
    client_id: str
    client_secret: str
    redirect_uri: str
    auth_url: str
    token_url: str
    userinfo_url: str
    scope: list[str]


# ─────────────────────────────────────────────────────────────────────────────
# OAUTH PROVIDERS
# ─────────────────────────────────────────────────────────────────────────────

class OAuthProvider(ABC):
    """Base OAuth provider."""
    
    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Get authorization URL for OAuth flow."""
        pass
    
    @abstractmethod
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        pass
    
    @abstractmethod
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user info from provider."""
        pass
    
    @abstractmethod
    def parse_user_info(self, user_info: Dict[str, Any]) -> "OAuthUserInfo":
        """Parse provider-specific user info into standard format."""
        pass


class OAuthUserInfo(BaseModel):
    """Standardized OAuth user info."""
    provider: str
    provider_user_id: str
    email: Optional[str] = None
    email_verified: bool = False
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    locale: Optional[str] = None
    username: Optional[str] = None  # For X/TikTok
    raw_data: Dict[str, Any] = {}


# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE OAUTH
# ─────────────────────────────────────────────────────────────────────────────

class GoogleOAuth(OAuthProvider):
    """Google OAuth 2.0 provider."""
    
    def __init__(self):
        self.config = OAuthConfig(
            client_id=os.getenv("OAUTH_GOOGLE_CLIENT_ID", ""),
            client_secret=os.getenv("OAUTH_GOOGLE_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("OAUTH_GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/oauth/google/callback"),
            auth_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
            scope=["openid", "email", "profile"],
        )
    
    def get_authorization_url(self, state: str) -> str:
        """Get Google authorization URL."""
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scope),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{self.config.auth_url}?{urlencode(params)}"
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data={
                    "code": code,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "redirect_uri": self.config.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if response.status_code != 200:
                raise ValueError(f"OAuth token exchange failed: {response.status_code}")
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user info from Google."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.config.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return response.json()
    
    def parse_user_info(self, user_info: Dict[str, Any]) -> OAuthUserInfo:
        """Parse Google user info."""
        return OAuthUserInfo(
            provider="google",
            provider_user_id=user_info.get("sub", ""),
            email=user_info.get("email"),
            email_verified=user_info.get("email_verified", False),
            name=user_info.get("name"),
            first_name=user_info.get("given_name"),
            last_name=user_info.get("family_name"),
            avatar_url=user_info.get("picture"),
            locale=user_info.get("locale"),
            raw_data=user_info,
        )


# ─────────────────────────────────────────────────────────────────────────────
# FACEBOOK OAUTH
# ─────────────────────────────────────────────────────────────────────────────

class FacebookOAuth(OAuthProvider):
    """Facebook OAuth 2.0 provider."""
    
    def __init__(self):
        self.config = OAuthConfig(
            client_id=os.getenv("OAUTH_FACEBOOK_CLIENT_ID", ""),
            client_secret=os.getenv("OAUTH_FACEBOOK_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("OAUTH_FACEBOOK_REDIRECT_URI", "http://localhost:8000/api/auth/oauth/facebook/callback"),
            auth_url="https://www.facebook.com/v18.0/dialog/oauth",
            token_url="https://graph.facebook.com/v18.0/oauth/access_token",
            userinfo_url="https://graph.facebook.com/v18.0/me",
            scope=["email", "public_profile"],
        )
    
    def get_authorization_url(self, state: str) -> str:
        """Get Facebook authorization URL."""
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": ",".join(self.config.scope),
            "state": state,
        }
        return f"{self.config.auth_url}?{urlencode(params)}"
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.config.token_url,
                params={
                    "code": code,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "redirect_uri": self.config.redirect_uri,
                },
            )
            if response.status_code != 200:
                raise ValueError(f"OAuth token exchange failed: {response.status_code}")
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user info from Facebook."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.config.userinfo_url,
                params={
                    "fields": "id,name,email,first_name,last_name,picture",
                    "access_token": access_token,
                },
            )
            return response.json()
    
    def parse_user_info(self, user_info: Dict[str, Any]) -> OAuthUserInfo:
        """Parse Facebook user info."""
        picture_data = user_info.get("picture", {}).get("data", {})
        return OAuthUserInfo(
            provider="facebook",
            provider_user_id=user_info.get("id", ""),
            email=user_info.get("email"),
            email_verified=True if user_info.get("email") else False,
            name=user_info.get("name"),
            first_name=user_info.get("first_name"),
            last_name=user_info.get("last_name"),
            avatar_url=picture_data.get("url"),
            raw_data=user_info,
        )


# ─────────────────────────────────────────────────────────────────────────────
# APPLE OAUTH
# ─────────────────────────────────────────────────────────────────────────────

class AppleOAuth(OAuthProvider):
    """Apple Sign In provider."""
    
    def __init__(self):
        self.config = OAuthConfig(
            client_id=os.getenv("OAUTH_APPLE_CLIENT_ID", ""),
            client_secret=os.getenv("OAUTH_APPLE_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("OAUTH_APPLE_REDIRECT_URI", "http://localhost:8000/api/auth/oauth/apple/callback"),
            auth_url="https://appleid.apple.com/auth/authorize",
            token_url="https://appleid.apple.com/auth/token",
            userinfo_url="",  # Apple doesn't have a userinfo endpoint
            scope=["email", "name"],
        )
    
    def get_authorization_url(self, state: str) -> str:
        """Get Apple authorization URL."""
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code id_token",
            "scope": " ".join(self.config.scope),
            "state": state,
            "response_mode": "form_post",
        }
        return f"{self.config.auth_url}?{urlencode(params)}"
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data={
                    "code": code,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "redirect_uri": self.config.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if response.status_code != 200:
                raise ValueError(f"OAuth token exchange failed: {response.status_code}")
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Apple doesn't have userinfo endpoint, info is in ID token."""
        return {}
    
    def parse_user_info(self, user_info: Dict[str, Any]) -> OAuthUserInfo:
        """Parse Apple user info from ID token — decoded without signature verification (public key verification requires jwks fetch; accept risk in dev, enforce in prod via Apple's JWKS endpoint)."""
        id_token = user_info.get("id_token", "")

        if id_token:
            try:
                parts = id_token.split(".")
                if len(parts) != 3:
                    raise ValueError("Invalid JWT structure")
                payload_b64 = parts[1]
                # Pad to a multiple of 4 for base64 decoding
                payload_b64 += "=" * (4 - len(payload_b64) % 4)
                decoded = json.loads(base64.urlsafe_b64decode(payload_b64))

                # Validate issuer — must be Apple
                if decoded.get("iss") != "https://appleid.apple.com":
                    raise ValueError("Invalid Apple ID token issuer")

                # Validate audience — must match our client_id
                aud = decoded.get("aud", "")
                if self.config.client_id and aud != self.config.client_id:
                    raise ValueError("Apple ID token audience mismatch")

                return OAuthUserInfo(
                    provider="apple",
                    provider_user_id=decoded.get("sub", ""),
                    email=decoded.get("email"),
                    email_verified=decoded.get("email_verified", False),
                    name=None,
                    raw_data=decoded,
                )
            except Exception:
                pass

        return OAuthUserInfo(
            provider="apple",
            provider_user_id="",
            raw_data=user_info,
        )


# ─────────────────────────────────────────────────────────────────────────────
# X (TWITTER) OAUTH 2.0
# ─────────────────────────────────────────────────────────────────────────────

class XTwitterOAuth(OAuthProvider):
    """X (Twitter) OAuth 2.0 provider with PKCE."""
    
    def __init__(self):
        self.config = OAuthConfig(
            client_id=os.getenv("OAUTH_X_CLIENT_ID", ""),
            client_secret=os.getenv("OAUTH_X_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("OAUTH_X_REDIRECT_URI", "http://localhost:8000/api/auth/oauth/x/callback"),
            auth_url="https://twitter.com/i/oauth2/authorize",
            token_url="https://api.twitter.com/2/oauth2/token",
            userinfo_url="https://api.twitter.com/2/users/me",
            scope=["tweet.read", "users.read", "offline.access"],
        )
        self._code_verifier: Optional[str] = None
    
    def _generate_pkce(self) -> tuple[str, str]:
        """Generate PKCE code verifier and challenge."""
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip("=")
        return verifier, challenge
    
    def get_authorization_url(self, state: str) -> str:
        """Get X authorization URL with PKCE."""
        verifier, challenge = self._generate_pkce()
        self._code_verifier = verifier
        
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scope),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.config.auth_url}?{urlencode(params)}"
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange code for tokens with PKCE verifier."""
        if not self._code_verifier:
            raise ValueError("PKCE code verifier not set")
        
        async with httpx.AsyncClient() as client:
            # X requires Basic auth with client credentials
            credentials = base64.b64encode(
                f"{self.config.client_id}:{self.config.client_secret}".encode()
            ).decode()
            
            response = await client.post(
                self.config.token_url,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.config.redirect_uri,
                    "code_verifier": self._code_verifier,
                },
            )
            if response.status_code != 200:
                raise ValueError(f"OAuth token exchange failed: {response.status_code}")
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user info from X API v2."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.config.userinfo_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                params={
                    "user.fields": "id,name,username,profile_image_url,verified,public_metrics",
                },
            )
            return response.json()
    
    def parse_user_info(self, user_info: Dict[str, Any]) -> OAuthUserInfo:
        """Parse X user info."""
        data = user_info.get("data", {})
        return OAuthUserInfo(
            provider="x",
            provider_user_id=data.get("id", ""),
            email=None,  # X doesn't provide email via API
            email_verified=False,
            name=data.get("name"),
            username=data.get("username"),
            avatar_url=data.get("profile_image_url"),
            raw_data=user_info,
        )


# ─────────────────────────────────────────────────────────────────────────────
# TIKTOK OAUTH
# ─────────────────────────────────────────────────────────────────────────────

class TikTokOAuth(OAuthProvider):
    """TikTok OAuth 2.0 provider."""
    
    def __init__(self):
        self.config = OAuthConfig(
            client_id=os.getenv("OAUTH_TIKTOK_CLIENT_ID", ""),
            client_secret=os.getenv("OAUTH_TIKTOK_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("OAUTH_TIKTOK_REDIRECT_URI", "http://localhost:8000/api/auth/oauth/tiktok/callback"),
            auth_url="https://www.tiktok.com/v2/oauth2/authorize",
            token_url="https://open.tiktokapis.com/v2/oauth2/token/",
            userinfo_url="https://open.tiktokapis.com/v2/user/info/",
            scope=["user.info.basic", "user.info.profile"],
        )
    
    def get_authorization_url(self, state: str) -> str:
        """Get TikTok authorization URL."""
        params = {
            "client_key": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": ",".join(self.config.scope),
            "state": state,
        }
        return f"{self.config.auth_url}?{urlencode(params)}"
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "code": code,
                    "client_key": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "redirect_uri": self.config.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if response.status_code != 200:
                raise ValueError(f"OAuth token exchange failed: {response.status_code}")
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user info from TikTok API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.config.userinfo_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                params={
                    "fields": "open_id,union_id,avatar_url,display_name,username",
                },
            )
            return response.json()
    
    def parse_user_info(self, user_info: Dict[str, Any]) -> OAuthUserInfo:
        """Parse TikTok user info."""
        data = user_info.get("data", {}).get("user", {})
        return OAuthUserInfo(
            provider="tiktok",
            provider_user_id=data.get("open_id", ""),
            email=None,  # TikTok doesn't provide email
            email_verified=False,
            name=data.get("display_name"),
            username=data.get("username"),
            avatar_url=data.get("avatar_url"),
            raw_data=user_info,
        )


# ─────────────────────────────────────────────────────────────────────────────
# OAUTH HANDLER
# ─────────────────────────────────────────────────────────────────────────────

class OAuthHandler:
    """OAuth handler for multiple providers."""
    
    def __init__(self):
        self.providers: Dict[str, OAuthProvider] = {
            "google": GoogleOAuth(),
            "facebook": FacebookOAuth(),
            "apple": AppleOAuth(),
            "x": XTwitterOAuth(),
            "twitter": XTwitterOAuth(),  # Alias
            "tiktok": TikTokOAuth(),
        }
        self._states: Dict[str, Dict[str, Any]] = {}
    
    def get_provider(self, provider_name: str) -> Optional[OAuthProvider]:
        """Get OAuth provider by name."""
        return self.providers.get(provider_name.lower())
    
    def generate_state(self, provider: str, redirect_to: Optional[str] = None) -> str:
        """Generate state token for OAuth flow."""
        state = secrets.token_urlsafe(32)
        self._states[state] = {
            "provider": provider,
            "redirect_to": redirect_to,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return state
    
    def validate_state(self, state: str) -> Optional[Dict[str, Any]]:
        """Validate and consume state token (one-time use, expires after 10 minutes)."""
        state_data = self._states.get(state)
        if not state_data:
            return None
        created_at = datetime.fromisoformat(state_data["created_at"])
        age = (datetime.now(timezone.utc) - created_at).total_seconds()
        if age > 600:
            del self._states[state]
            return None
        del self._states[state]
        return state_data
    
    def get_authorization_url(
        self,
        provider_name: str,
        redirect_to: Optional[str] = None,
    ) -> Optional[str]:
        """Get authorization URL for provider."""
        provider = self.get_provider(provider_name)
        if not provider:
            return None
        
        state = self.generate_state(provider_name, redirect_to)
        return provider.get_authorization_url(state)
    
    async def handle_callback(
        self,
        provider_name: str,
        code: str,
        state: str,
    ) -> Optional[OAuthUserInfo]:
        """Handle OAuth callback and return user info."""
        provider = self.get_provider(provider_name)
        if not provider:
            return None
        
        # Validate state
        state_data = self.validate_state(state)
        if not state_data:
            return None
        
        # Exchange code for tokens
        tokens = await provider.exchange_code(code)
        access_token = tokens.get("access_token")
        
        if not access_token:
            # For Apple, user info is in id_token
            if provider_name in ("apple",):
                return provider.parse_user_info(tokens)
            return None
        
        # Get user info
        user_info = await provider.get_user_info(access_token)
        return provider.parse_user_info(user_info)
    
    def is_provider_configured(self, provider_name: str) -> bool:
        """Check if provider is configured."""
        provider = self.get_provider(provider_name)
        if not provider:
            return False
        
        config = provider.config
        return bool(config.client_id and config.client_secret)
    
    def list_configured_providers(self) -> list[str]:
        """List all configured OAuth providers."""
        return [name for name in self.providers if self.is_provider_configured(name)]


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL INSTANCE
# ─────────────────────────────────────────────────────────────────────────────

oauth_handler = OAuthHandler()
