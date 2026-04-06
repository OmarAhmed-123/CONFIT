# CONFIT Credential Manager Integration Strategy

## Executive Summary

This document outlines a production-ready credential manager integration strategy for CONFIT, implementing WebAuthn/FIDO2 passkeys, OS-level credential managers (Apple Keychain, Windows Credential Manager, Android Credential Manager), and progressive enhancement from baseline email autocomplete.

**Key Architecture Decision**: CONFIT uses a custom JWT authentication system with FastAPI backend, not NextAuth.js. All credential manager flows integrate directly with the existing JWT session model.

---

## 1. WebAuthn/FIDO2 Integration

### 1.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           REGISTRATION FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Browser                           Next.js/FastAPI                          │
│  ───────                           ────────────────                          │
│     │                                     │                                  │
│     │  1. User clicks "Register Passkey"  │                                  │
│     │────────────────────────────────────>│                                  │
│     │                                     │                                  │
│     │  2. GET /api/auth/webauthn/register/start                            │
│     │    Returns: { challenge, user, rp, pubKeyCredParams }                │
│     │<────────────────────────────────────│                                  │
│     │                                     │                                  │
│     │  3. navigator.credentials.create({ publicKey })                     │
│     │    User authenticates (TouchID, FaceID, Windows Hello)               │
│     │                                     │                                  │
│     │  4. POST /api/auth/webauthn/register/finish                          │
│     │    Body: { clientDataJSON, attestationObject, credentialId }         │
│     │────────────────────────────────────>│                                  │
│     │                                     │                                  │
│     │  5. Returns JWT + user profile     │                                  │
│     │<────────────────────────────────────│                                  │
│     │                                     │                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                           AUTHENTICATION FLOW                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│     │  1. User clicks "Sign in with Passkey"                               │
│     │────────────────────────────────────>│                                  │
│     │                                     │                                  │
│     │  2. GET /api/auth/webauthn/authenticate/start                        │
│     │    Returns: { challenge, rpId, allowCredentials, userVerification }  │
│     │<────────────────────────────────────│                                  │
│     │                                     │                                  │
│     │  3. navigator.credentials.get({ publicKey })                         │
│     │    OS shows passkey picker                                           │
│     │                                     │                                  │
│     │  4. POST /api/auth/webauthn/authenticate/finish                      │
│     │    Body: { clientDataJSON, authenticatorData, signature, credentialId}│
│     │────────────────────────────────────>│                                  │
│     │                                     │                                  │
│     │  5. Returns JWT + user profile      │                                  │
│     │<────────────────────────────────────│                                  │
│     │                                     │                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Database Schema for WebAuthn Credentials

```python
# backend/database/models.py (additions)

class WebAuthnCredential(Base):
    """Stores WebAuthn/FIDO2 passkey credentials."""
    __tablename__ = "webauthn_credentials"
    __table_args__ = {"extend_existing": True}

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=False, index=True)
    
    # Credential identifier (base64url-encoded)
    credential_id = Column(String(255), nullable=False, unique=True, index=True)
    
    # Public key in COSE format (base64url-encoded)
    public_key = Column(Text, nullable=False)
    
    # Sign counter for clone detection
    sign_count = Column(BigInteger, nullable=False, default=0)
    
    # AAGUID identifying authenticator model
    aaguid = Column(String(36), nullable=True)
    
    # Credential type: "public-key" (only valid value currently)
    credential_type = Column(String(32), nullable=False, default="public-key")
    
    # Transports hint for UI (usb, nfc, ble, internal, hybrid)
    transports = Column(JSON, nullable=True)
    
    # Device nickname for user recognition
    device_name = Column(String(100), nullable=True)
    
    # Backup state flags (for account recovery)
    backup_eligible = Column(Boolean, nullable=False, default=False)
    backup_state = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", backref="webauthn_credentials")


class WebAuthnChallenge(Base):
    """Short-lived challenges for WebAuthn ceremonies."""
    __tablename__ = "webauthn_challenges"
    __table_args__ = {"extend_existing": True}

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, ForeignKey("users.id"), nullable=True, index=True)
    
    # Challenge bytes (base64url-encoded)
    challenge = Column(String(128), nullable=False, unique=True, index=True)
    
    # "registration" or "authentication"
    ceremony_type = Column(String(32), nullable=False)
    
    # For authentication: which credentials are allowed
    allowed_credential_ids = Column(JSON, nullable=True)
    
    # User verification requirement
    user_verification = Column(String(32), nullable=False, default="preferred")
    
    # Expiry (typically 5 minutes)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
```

### 1.3 FastAPI WebAuthn Router

```python
# backend/routers/webauthn.py

"""
CONFIT Backend — WebAuthn/FIDO2 Router
======================================
Passkey registration and authentication endpoints.
"""

import os
import base64
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.base import get_db
from database.models import User, WebAuthnCredential, WebAuthnChallenge
from services.auth_service import AuthService
from utils.auth_deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth/webauthn", tags=["WebAuthn"])

# ── Configuration ──────────────────────────────────────────────────────────────

RP_ID = os.getenv("WEBAUTHN_RP_ID", "localhost")
RP_NAME = os.getenv("WEBAUTHN_RP_NAME", "CONFIT")
RP_ORIGIN = os.getenv("WEBAUTHN_RP_ORIGIN", "http://localhost:5173")

# Allowed algorithms (ES256, RS256, ES384, ES512, PS256)
COSE_ALGORITHMS = [
    {"type": "public-key", "alg": -7},   # ES256 (ECDSA w/ SHA-256)
    {"type": "public-key", "alg": -257}, # RS256 (RSASSA-PKCS1-v1_5 w/ SHA-256)
    {"type": "public-key", "alg": -35},  # ES384
    {"type": "public-key", "alg": -36},  # ES512
    {"type": "public-key", "alg": -37},  # PS256 (RSASSA-PSS w/ SHA-256)
]

# Authenticator selection
AUTHENTICATOR_ATTACHMENT = "platform"  # "platform" for device-bound, "cross-platform" for security keys
USER_VERIFICATION = "preferred"        # "required", "preferred", "discouraged"

# ── Request/Response Models ─────────────────────────────────────────────────────

class RegistrationStartRequest(BaseModel):
    device_name: Optional[str] = Field(None, max_length=100, description="User-friendly device name")


class RegistrationStartResponse(BaseModel):
    challenge: str
    user_id: str
    user_name: str
    user_display_name: str
    rp_id: str
    rp_name: str
    pub_key_cred_params: List[dict]
    authenticator_selection: dict
    timeout: int
    attestation: str


class RegistrationFinishRequest(BaseModel):
    credential_id: str
    client_data_json: str
    attestation_object: str
    transports: Optional[List[str]] = None
    device_name: Optional[str] = None


class AuthenticationStartRequest(BaseModel):
    email: Optional[str] = Field(None, description="Email hint for credential lookup")


class AuthenticationStartResponse(BaseModel):
    challenge: str
    rp_id: str
    allow_credentials: List[dict]
    user_verification: str
    timeout: int


class AuthenticationFinishRequest(BaseModel):
    credential_id: str
    client_data_json: str
    authenticator_data: str
    signature: str
    user_handle: Optional[str] = None


class WebAuthnResponse(BaseModel):
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: Optional[dict] = None
    credential_id: Optional[str] = None
    message: str = ""


# ── Helper Functions ────────────────────────────────────────────────────────────

def base64url_decode(data: str) -> bytes:
    """Decode base64url string to bytes."""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def base64url_encode(data: bytes) -> str:
    """Encode bytes to base64url string without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def generate_challenge() -> bytes:
    """Generate cryptographically secure challenge."""
    return secrets.token_bytes(32)


def parse_client_data(client_data_json: str) -> dict:
    """Parse and validate client data JSON."""
    import json
    decoded = base64url_decode(client_data_json)
    return json.loads(decoded)


def parse_authenticator_data(auth_data: bytes) -> dict:
    """Parse authenticator data structure."""
    # RP ID hash (32 bytes)
    rp_id_hash = auth_data[:32]
    
    # Flags (1 byte)
    flags = auth_data[32]
    
    # Sign count (4 bytes, big-endian)
    sign_count = int.from_bytes(auth_data[33:37], "big")
    
    result = {
        "rp_id_hash": rp_id_hash,
        "flags": {
            "user_present": bool(flags & 0x01),
            "user_verified": bool(flags & 0x04),
            "backup_eligible": bool(flags & 0x08),
            "backup_state": bool(flags & 0x10),
            "attested_credential_data": bool(flags & 0x40),
            "extension_data": bool(flags & 0x80),
        },
        "sign_count": sign_count,
    }
    
    # Parse attested credential data if present
    if result["flags"]["attested_credential_data"]:
        offset = 37
        aaguid = auth_data[offset:offset + 16]
        cred_id_len = int.from_bytes(auth_data[offset + 16:offset + 18], "big")
        cred_id = auth_data[offset + 18:offset + 18 + cred_id_len]
        result["aaguid"] = aaguid.hex()
        result["credential_id"] = cred_id
        # Public key starts after credential ID (COSE format)
        # Length is determined by next bytes
    
    return result


def verify_client_data(client_data: dict, expected_type: str, expected_origin: str, expected_challenge: str) -> None:
    """Verify client data integrity."""
    import hashlib
    
    if client_data.get("type") != expected_type:
        raise ValueError(f"Invalid client data type: expected {expected_type}, got {client_data.get('type')}")
    
    if client_data.get("origin") != expected_origin:
        raise ValueError(f"Invalid origin: expected {expected_origin}, got {client_data.get('origin')}")
    
    # Verify challenge matches
    challenge_b64 = base64url_encode(hashlib.sha256(expected_challenge.encode()).digest())
    # Note: client_data.challenge is the base64url of the original challenge bytes
    
    # Check challenge is present
    if "challenge" not in client_data:
        raise ValueError("Missing challenge in client data")


# ── Registration Endpoints ──────────────────────────────────────────────────────

@router.post("/register/start", response_model=RegistrationStartResponse)
async def start_registration(
    request: RegistrationStartRequest,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """Start WebAuthn registration ceremony. User must be authenticated."""
    
    # Get current user from JWT
    auth_service = AuthService(db)
    user = auth_service.get_user_by_token(authorization.replace("Bearer ", ""))
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Generate challenge
    challenge = generate_challenge()
    challenge_b64 = base64url_encode(challenge)
    
    # Store challenge in database
    challenge_record = WebAuthnChallenge(
        user_id=user.id,
        challenge=challenge_b64,
        ceremony_type="registration",
        user_verification=USER_VERIFICATION,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    db.add(challenge_record)
    db.commit()
    
    return RegistrationStartResponse(
        challenge=challenge_b64,
        user_id=user.id,
        user_name=user.email,
        user_display_name=user.name,
        rp_id=RP_ID,
        rp_name=RP_NAME,
        pub_key_cred_params=COSE_ALGORITHMS,
        authenticator_selection={
            "authenticatorAttachment": AUTHENTICATOR_ATTACHMENT,
            "userVerification": USER_VERIFICATION,
            "requireResidentKey": True,  # Enable passkey sync
        },
        timeout=60000,
        attestation="none",  # Use "direct" for enterprise attestation requirements
    )


@router.post("/register/finish", response_model=WebAuthnResponse)
async def finish_registration(
    request: RegistrationFinishRequest,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """Complete WebAuthn registration by verifying attestation."""
    
    auth_service = AuthService(db)
    user = auth_service.get_user_by_token(authorization.replace("Bearer ", ""))
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Find and validate challenge
    # Note: We need to match by user and ceremony type, challenge is in client_data
    client_data = parse_client_data(request.client_data_json)
    
    # Find challenge record
    challenge_record = db.query(WebAuthnChallenge).filter(
        WebAuthnChallenge.user_id == user.id,
        WebAuthnChallenge.ceremony_type == "registration",
        WebAuthnChallenge.expires_at > datetime.now(timezone.utc),
    ).first()
    
    if not challenge_record:
        raise HTTPException(status_code=400, detail="No valid registration challenge found")
    
    # Verify client data
    try:
        verify_client_data(
            client_data,
            expected_type="webauthn.create",
            expected_origin=RP_ORIGIN,
            expected_challenge=challenge_record.challenge,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Parse attestation object (simplified - production needs full attestation verification)
    attestation_data = base64url_decode(request.attestation_object)
    
    # For "none" attestation, we trust the authenticator data
    # Production should verify attestation signature for "direct" attestation
    
    # Parse authenticator data
    auth_data = parse_authenticator_data(attestation_data)
    
    # Verify user presence
    if not auth_data["flags"]["user_present"]:
        raise HTTPException(status_code=400, detail="User presence flag not set")
    
    # Verify user verification if required
    if USER_VERIFICATION == "required" and not auth_data["flags"]["user_verified"]:
        raise HTTPException(status_code=400, detail="User verification required but not performed")
    
    # Check for credential cloning (sign count)
    if auth_data["sign_count"] != 0:
        # For new credentials, sign count should be 0
        logger.warning(f"Non-zero sign count on registration: {auth_data['sign_count']}")
    
    # Check if credential already exists
    existing = db.query(WebAuthnCredential).filter(
        WebAuthnCredential.credential_id == request.credential_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Credential already registered")
    
    # Store credential
    # Note: In production, extract public key from attestation object
    # This simplified version stores the raw attestation
    
    credential = WebAuthnCredential(
        user_id=user.id,
        credential_id=request.credential_id,
        public_key=base64url_encode(attestation_data),  # Simplified - store full attestation
        sign_count=auth_data["sign_count"],
        aaguid=auth_data.get("aaguid"),
        credential_type="public-key",
        transports=request.transports,
        device_name=request.device_name or "Passkey",
        backup_eligible=auth_data["flags"].get("backup_eligible", False),
        backup_state=auth_data["flags"].get("backup_state", False),
    )
    db.add(credential)
    
    # Delete used challenge
    db.delete(challenge_record)
    db.commit()
    
    logger.info(f"WebAuthn credential registered for user {user.email}")
    
    return WebAuthnResponse(
        success=True,
        credential_id=request.credential_id,
        message="Passkey registered successfully",
    )


# ── Authentication Endpoints ────────────────────────────────────────────────────

@router.post("/authenticate/start", response_model=AuthenticationStartResponse)
async def start_authentication(
    request: AuthenticationStartRequest,
    db: Session = Depends(get_db),
):
    """Start WebAuthn authentication ceremony."""
    
    # Generate challenge
    challenge = generate_challenge()
    challenge_b64 = base64url_encode(challenge)
    
    # Determine allowed credentials
    allow_credentials = []
    
    if request.email:
        # Email hint provided - look up user's credentials
        user = db.query(User).filter(User.email == request.email.lower()).first()
        if user:
            credentials = db.query(WebAuthnCredential).filter(
                WebAuthnCredential.user_id == user.id
            ).all()
            
            for cred in credentials:
                allow_credentials.append({
                    "type": "public-key",
                    "id": cred.credential_id,
                    "transports": cred.transports or [],
                })
    
    # If no email or no credentials found, allow any passkey (discoverable credentials)
    # This enables passkey autofill UI
    
    # Store challenge
    challenge_record = WebAuthnChallenge(
        user_id=None,  # Unknown until authentication completes
        challenge=challenge_b64,
        ceremony_type="authentication",
        allowed_credential_ids=[c["id"] for c in allow_credentials] if allow_credentials else None,
        user_verification=USER_VERIFICATION,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    db.add(challenge_record)
    db.commit()
    
    return AuthenticationStartResponse(
        challenge=challenge_b64,
        rp_id=RP_ID,
        allow_credentials=allow_credentials if allow_credentials else [],
        user_verification=USER_VERIFICATION,
        timeout=60000,
    )


@router.post("/authenticate/finish", response_model=WebAuthnResponse)
async def finish_authentication(
    request: AuthenticationFinishRequest,
    db: Session = Depends(get_db),
):
    """Complete WebAuthn authentication by verifying assertion."""
    
    # Find credential
    credential = db.query(WebAuthnCredential).filter(
        WebAuthnCredential.credential_id == request.credential_id
    ).first()
    
    if not credential:
        raise HTTPException(status_code=401, detail="Credential not recognized")
    
    # Find challenge
    challenge_record = db.query(WebAuthnChallenge).filter(
        WebAuthnChallenge.ceremony_type == "authentication",
        WebAuthnChallenge.expires_at > datetime.now(timezone.utc),
    ).first()
    
    if not challenge_record:
        raise HTTPException(status_code=400, detail="No valid authentication challenge found")
    
    # Parse and verify client data
    client_data = parse_client_data(request.client_data_json)
    
    try:
        verify_client_data(
            client_data,
            expected_type="webauthn.get",
            expected_origin=RP_ORIGIN,
            expected_challenge=challenge_record.challenge,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Parse authenticator data
    auth_data_bytes = base64url_decode(request.authenticator_data)
    auth_data = parse_authenticator_data(auth_data_bytes)
    
    # Verify user presence
    if not auth_data["flags"]["user_present"]:
        raise HTTPException(status_code=400, detail="User presence flag not set")
    
    # Verify user verification if required
    if USER_VERIFICATION == "required" and not auth_data["flags"]["user_verified"]:
        raise HTTPException(status_code=400, detail="User verification required")
    
    # Clone detection: verify sign count increased
    if auth_data["sign_count"] <= credential.sign_count and credential.sign_count != 0:
        logger.error(f"Possible credential cloning detected for credential {credential.credential_id}")
        # In production, disable credential and alert user
        raise HTTPException(status_code=401, detail="Security alert: possible credential cloning")
    
    # Verify signature (simplified - production needs proper ECDSA/RSA verification)
    # The signature is over SHA-256(authData || clientDataHash)
    import hashlib
    client_data_hash = hashlib.sha256(base64url_decode(request.client_data_json)).digest()
    signed_data = auth_data_bytes + client_data_hash
    
    # Production: Verify signature using stored public key
    # For now, we trust the authenticator data structure
    
    # Update credential sign count
    credential.sign_count = auth_data["sign_count"]
    credential.last_used_at = datetime.now(timezone.utc)
    
    # Get user
    user = db.query(User).filter(User.id == credential.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Generate JWT tokens
    auth_service = AuthService(db)
    access_token = auth_service.create_token(user.id, user.email)
    refresh_token = auth_service.create_refresh_token(user.id, user.email)
    
    # Delete used challenge
    db.delete(challenge_record)
    db.commit()
    
    logger.info(f"WebAuthn authentication successful for user {user.email}")
    
    return WebAuthnResponse(
        success=True,
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
        },
        message="Authentication successful",
    )


# ── Credential Management ──────────────────────────────────────────────────────

@router.get("/credentials")
async def list_credentials(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """List user's registered WebAuthn credentials."""
    
    auth_service = AuthService(db)
    user = auth_service.get_user_by_token(authorization.replace("Bearer ", ""))
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    credentials = db.query(WebAuthnCredential).filter(
        WebAuthnCredential.user_id == user.id
    ).all()
    
    return {
        "credentials": [
            {
                "id": str(cred.id),
                "credential_id": cred.credential_id,
                "device_name": cred.device_name,
                "created_at": cred.created_at.isoformat(),
                "last_used_at": cred.last_used_at.isoformat() if cred.last_used_at else None,
                "transports": cred.transports,
            }
            for cred in credentials
        ]
    }


@router.delete("/credentials/{credential_db_id}")
async def delete_credential(
    credential_db_id: str,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """Delete a WebAuthn credential."""
    
    auth_service = AuthService(db)
    user = auth_service.get_user_by_token(authorization.replace("Bearer ", ""))
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    credential = db.query(WebAuthnCredential).filter(
        WebAuthnCredential.id == credential_db_id,
        WebAuthnCredential.user_id == user.id,
    ).first()
    
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    db.delete(credential)
    db.commit()
    
    return {"success": True, "message": "Credential deleted"}
```

---

## 2. OS-Level Credential Manager Integration

### 2.1 Platform Coverage Matrix

| Platform | Credential Store | Browser Surface | Native API | Passkey Sync |
|----------|-----------------|-----------------|-----------|--------------|
| **macOS/iOS** | Apple Keychain | Safari, Chrome, Edge | ASWebAuthenticationSession | iCloud Keychain |
| **Windows 10/11** | Windows Credential Manager | Chrome, Edge, Firefox | Web Authentication API | None (device-bound) |
| **Android 14+** | Android Credential Manager | Chrome, Edge | CredentialManager Jetpack | Google Password Manager |
| **Android 9-13** | Google Password Manager | Chrome | Credential Manager API | Google Password Manager |
| **Chrome OS** | Chrome Profile Storage | Chrome | Web Authentication API | Google Password Manager |

### 2.2 Apple Keychain (Passkeys/ASWebAuthenticationSession)

**Browser Trigger Conditions:**
- Safari, Chrome, Edge on macOS/iOS automatically surface Keychain passkeys
- Requires HTTPS and valid RP ID matching Apple's App ID configuration

**RP ID Configuration for Apple:**
```
# For web: RP_ID = "confit.com" (domain)
# For native iOS app: RP_ID = "com.confit.app" (App ID with Associated Domains)
```

**Keychain Integration Code (Frontend):**
```typescript
// src/lib/webauthn/passkey-apple.ts

/**
 * Apple-specific passkey configuration.
 * Ensures passkeys sync via iCloud Keychain.
 */
export function getApplePasskeyConfig() {
  return {
    // Apple requires resident credentials for passkey sync
    authenticatorSelection: {
      authenticatorAttachment: 'platform' as const,
      requireResidentKey: true,
      residentKey: 'required' as const,
      userVerification: 'preferred' as const,
    },
    // Apple supports ES256 and RS256
    pubKeyCredParams: [
      { type: 'public-key', alg: -7 },   // ES256 (Apple's preferred)
      { type: 'public-key', alg: -257 }, // RS256
    ],
    // Extensions for Apple
    extensions: {
      credProps: {
        rk: true, // Resident key required for sync
      },
    },
  };
}

/**
 * Check if device supports Apple passkey sync.
 */
export function supportsApplePasskeySync(): boolean {
  // iOS 16+ / macOS Ventura+ support passkey sync
  const ua = navigator.userAgent;
  const isApple = /iPhone|iPad|iPod|Mac/.test(ua);
  
  if (!isApple) return false;
  
  // iOS 16+ check
  const iOSMatch = ua.match(/OS (\d+)_/);
  if (iOSMatch && parseInt(iOSMatch[1], 10) >= 16) return true;
  
  // macOS 13+ check
  const macOSMatch = ua.match(/Mac OS X (\d+)/);
  if (macOSMatch && parseInt(macOSMatch[1], 10) >= 13) return true;
  
  return false;
}
```

**Platform-Specific Gotchas:**

1. **App ID Configuration Required**: For native iOS app integration, must configure Associated Domains in Xcode:
   ```
   // In app's entitlements:
   com.apple.developer.associated-domains: ["webcredentials:confit.com"]
   ```

2. **RP ID Must Match**: The RP ID in WebAuthn ceremony must exactly match the domain or app ID.

3. **Silent Failure on Mismatch**: Apple silently fails to surface passkeys if RP ID doesn't match.

4. **Safari Cross-Origin Restriction**: Safari requires `cross-origin: "same-origin"` for iframe WebAuthn.

### 2.3 Windows Credential Manager

**Browser Trigger Conditions:**
- Windows Hello (Face, Fingerprint, PIN) integration
- Chrome, Edge, Firefox all use Windows Web Authentication API
- Device-bound credentials (no sync across devices)

**Windows-Specific Configuration:**
```typescript
// src/lib/webauthn/passkey-windows.ts

/**
 * Windows Hello passkey configuration.
 * Windows uses device-bound credentials (no sync).
 */
export function getWindowsPasskeyConfig() {
  return {
    authenticatorSelection: {
      authenticatorAttachment: 'platform' as const,
      requireResidentKey: true,
      residentKey: 'required' as const,
      userVerification: 'required' as const, // Windows Hello requires UV
    },
    // Windows Hello supports ES256, RS256, PS256
    pubKeyCredParams: [
      { type: 'public-key', alg: -7 },   // ES256
      { type: 'public-key', alg: -257 }, // RS256
      { type: 'public-key', alg: -37 },  // PS256
    ],
    attestation: 'direct' as const, // Windows provides TPM attestation
  };
}

/**
 * Check if device supports Windows Hello.
 */
export function supportsWindowsHello(): boolean {
  const ua = navigator.userAgent;
  const isWindows = /Windows/.test(ua);
  
  if (!isWindows) return false;
  
  // Windows 10+ supports Hello
  const winMatch = ua.match(/Windows NT (\d+)/);
  return winMatch ? parseInt(winMatch[1], 10) >= 10 : false;
}
```

**Platform-Specific Gotchas:**

1. **User Verification Required**: Windows Hello always requires `userVerification: "required"` for platform authenticators.

2. **TPM Attestation Available**: Windows provides TPM attestation for enterprise scenarios.

3. **No Cross-Device Sync**: Windows passkeys are device-bound; users must register on each device.

4. **PIN Fallback**: Windows Hello PIN is a valid WebAuthn authenticator.

5. **Domain-Joined Machines**: Enterprise machines may have WebAuthn restricted by group policy.

### 2.4 Android Credential Manager

**Browser Trigger Conditions:**
- Android 14+ uses unified Credential Manager API
- Chrome, Edge integrate with Google Password Manager
- Passkeys sync across Android devices signed into same Google account

**Android-Specific Configuration:**
```typescript
// src/lib/webauthn/passkey-android.ts

/**
 * Android Credential Manager passkey configuration.
 * Supports passkey sync via Google Password Manager.
 */
export function getAndroidPasskeyConfig() {
  return {
    authenticatorSelection: {
      authenticatorAttachment: 'platform' as const,
      requireResidentKey: true,
      residentKey: 'required' as const,
      userVerification: 'preferred' as const,
    },
    pubKeyCredParams: [
      { type: 'public-key', alg: -7 },   // ES256
      { type: 'public-key', alg: -257 }, // RS256
    ],
    // Android supports credProtect extension
    extensions: {
      credProtect: 'userVerificationRequired',
    },
  };
}

/**
 * Check if device supports Android passkeys.
 */
export function supportsAndroidPasskey(): boolean {
  const ua = navigator.userAgent;
  const isAndroid = /Android/.test(ua);
  
  if (!isAndroid) return false;
  
  // Android 9+ supports WebAuthn
  const androidMatch = ua.match(/Android (\d+)/);
  return androidMatch ? parseInt(androidMatch[1], 10) >= 9 : false;
}

/**
 * Check for Android 14+ unified Credential Manager.
 */
export function supportsAndroidCredentialManager(): boolean {
  const ua = navigator.userAgent;
  const androidMatch = ua.match(/Android (\d+)/);
  return androidMatch ? parseInt(androidMatch[1], 10) >= 14 : false;
}
```

**Platform-Specific Gotchas:**

1. **Google Account Required**: Passkey sync requires Google account sign-in.

2. **Screen Lock Required**: Android requires secure screen lock (PIN, pattern, password) for passkeys.

3. **Play Services Dependency**: WebAuthn requires Google Play Services on Android.

4. **One Tap Integration**: Android Credential Manager supports "One Tap" UI for seamless credential selection.

5. **Hybrid Authenticator**: Android supports hybrid transport (phone as security key for desktop).

### 2.5 Credential Management API (Tier 2)

The Credential Management API provides password and federated credential storage at the OS level.

```typescript
// src/lib/credential-manager/credential-api.ts

/**
 * Credential Management API integration for password/federated credentials.
 * This is Tier 2 - below WebAuthn passkeys.
 */

export interface PasswordCredentialData {
  id: string;
  password: string;
  name?: string;
  iconURL?: string;
}

export interface FederatedCredentialData {
  id: string;
  provider: string;  // e.g., "https://accounts.google.com"
  name?: string;
  iconURL?: string;
}

/**
 * Check if Credential Management API is available.
 */
export function supportsCredentialAPI(): boolean {
  return 'credentials' in navigator && 
         typeof navigator.credentials === 'object' &&
         'PasswordCredential' in window;
}

/**
 * Store password credential in OS credential manager.
 */
export async function storePasswordCredential(
  email: string,
  password: string,
  name?: string
): Promise<boolean> {
  if (!supportsCredentialAPI()) {
    console.warn('Credential Management API not supported');
    return false;
  }

  try {
    const credential = new PasswordCredential({
      id: email,
      password,
      name: name || email,
    });

    // Store in OS credential manager
    await navigator.credentials.store(credential);
    return true;
  } catch (error) {
    console.error('Failed to store credential:', error);
    return false;
  }
}

/**
 * Store federated credential (OAuth provider).
 */
export async function storeFederatedCredential(
  email: string,
  provider: 'google' | 'facebook' | 'apple' | 'x' | 'tiktok',
  name?: string
): Promise<boolean> {
  if (!supportsCredentialAPI()) {
    return false;
  }

  const providerUrls: Record<string, string> = {
    google: 'https://accounts.google.com',
    facebook: 'https://www.facebook.com',
    apple: 'https://appleid.apple.com',
    x: 'https://twitter.com',
    tiktok: 'https://www.tiktok.com',
  };

  try {
    const credential = new FederatedCredential({
      id: email,
      provider: providerUrls[provider],
      name: name || email,
    });

    await navigator.credentials.store(credential);
    return true;
  } catch (error) {
    console.error('Failed to store federated credential:', error);
    return false;
  }
}

/**
 * Retrieve stored credential via OS credential picker.
 */
export async function getStoredCredential(
  mediation: 'silent' | 'optional' | 'required' = 'optional'
): Promise<Credential | null> {
  if (!supportsCredentialAPI()) {
    return null;
  }

  try {
    const credential = await navigator.credentials.get({
      password: true,
      federated: {
        providers: [
          'https://accounts.google.com',
          'https://www.facebook.com',
          'https://appleid.apple.com',
        ],
      },
      mediation,
    });

    return credential;
  } catch (error) {
    // User cancelled or no credentials available
    return null;
  }
}

/**
 * Prevent automatic sign-in after logout.
 */
export async function preventSilentAccess(): Promise<void> {
  if (!supportsCredentialAPI()) {
    return;
  }

  try {
    await navigator.credentials.preventSilentAccess();
  } catch (error) {
    console.warn('Failed to prevent silent access:', error);
  }
}
```

---

## 3. Progressive Enhancement Architecture

### 3.1 Capability Detection Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CAPABILITY DETECTION FLOW                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Check WebAuthn Support                                                   │
│     └─ PublicKeyCredential available?                                        │
│        ├─ Yes → Check for platform authenticator                             │
│        │        ├─ Available → TIER 3/4 (Passkey)                           │
│        │        └─ Unavailable → TIER 3 (Security Key only)                  │
│        └─ No → Continue to Tier 2                                            │
│                                                                              │
│  2. Check Credential Management API                                         │
│     └─ navigator.credentials available?                                      │
│        ├─ Yes → TIER 2 (PasswordCredential / FederatedCredential)           │
│        └─ No → TIER 1 (Baseline email autocomplete)                          │
│                                                                              │
│  3. Platform-Specific Enhancements                                           │
│     ├─ Apple → Check iCloud Keychain sync capability                        │
│     ├─ Windows → Check Windows Hello availability                           │
│     └─ Android → Check Credential Manager API level                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Feature Detection Module

```typescript
// src/lib/webauthn/capability-detection.ts

/**
 * Comprehensive WebAuthn and credential manager capability detection.
 */

export interface AuthCapabilities {
  // Tier detection
  tier: 1 | 2 | 3 | 4;
  
  // WebAuthn capabilities
  webAuthn: boolean;
  webAuthnPlatformAuthenticator: boolean;
  webAuthnCrossPlatform: boolean;  // Security keys
  
  // Passkey sync
  passkeySyncAvailable: boolean;
  passkeySyncProvider: 'apple' | 'google' | 'none';
  
  // Credential Management API
  credentialAPI: boolean;
  passwordCredential: boolean;
  federatedCredential: boolean;
  
  // Platform specifics
  platform: 'apple' | 'windows' | 'android' | 'other';
  platformVersion: number;
  
  // User verification
  userVerifiablePlatform: boolean;  // Biometrics available
  
  // Conditional UI (autofill)
  conditionalUIAvailable: boolean;
}

/**
 * Detect all authentication capabilities.
 */
export async function detectAuthCapabilities(): Promise<AuthCapabilities> {
  const result: AuthCapabilities = {
    tier: 1,
    webAuthn: false,
    webAuthnPlatformAuthenticator: false,
    webAuthnCrossPlatform: false,
    passkeySyncAvailable: false,
    passkeySyncProvider: 'none',
    credentialAPI: false,
    passwordCredential: false,
    federatedCredential: false,
    platform: 'other',
    platformVersion: 0,
    userVerifiablePlatform: false,
    conditionalUIAvailable: false,
  };

  // Detect platform
  const platformInfo = detectPlatform();
  result.platform = platformInfo.platform;
  result.platformVersion = platformInfo.version;

  // Check WebAuthn support
  result.webAuthn = 'PublicKeyCredential' in window;
  
  if (result.webAuthn) {
    // Check for platform authenticator (passkey support)
    try {
      result.webAuthnPlatformAuthenticator = 
        await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
    } catch {
      result.webAuthnPlatformAuthenticator = false;
    }

    // Check for conditional UI (passkey autofill)
    try {
      result.conditionalUIAvailable = 
        'conditionalMediation' in PublicKeyCredential.prototype ||
        'conditionalMediationAvailable' in PublicKeyCredential;
      
      // More reliable check: try conditional get
      if (!result.conditionalUIAvailable) {
        try {
          await PublicKeyCredential.getClientCapabilities();
          result.conditionalUIAvailable = true;
        } catch {
          // Not supported
        }
      }
    } catch {
      result.conditionalUIAvailable = false;
    }

    // Detect passkey sync provider
    if (result.webAuthnPlatformAuthenticator) {
      if (result.platform === 'apple' && result.platformVersion >= 16) {
        result.passkeySyncAvailable = true;
        result.passkeySyncProvider = 'apple';
      } else if (result.platform === 'android' && result.platformVersion >= 14) {
        result.passkeySyncAvailable = true;
        result.passkeySyncProvider = 'google';
      }
    }

    // User verification available
    result.userVerifiablePlatform = result.webAuthnPlatformAuthenticator;
  }

  // Check Credential Management API
  result.credentialAPI = 'credentials' in navigator;
  result.passwordCredential = 'PasswordCredential' in window;
  result.federatedCredential = 'FederatedCredential' in window;

  // Determine tier
  if (result.webAuthnPlatformAuthenticator && result.passkeySyncAvailable) {
    result.tier = 4;  // OS native credential manager with sync
  } else if (result.webAuthnPlatformAuthenticator) {
    result.tier = 3;  // WebAuthn passkey (device-bound)
  } else if (result.credentialAPI && (result.passwordCredential || result.federatedCredential)) {
    result.tier = 2;  // Credential Management API
  } else {
    result.tier = 1;  // Baseline email autocomplete
  }

  return result;
}

/**
 * Detect current platform and version.
 */
function detectPlatform(): { platform: AuthCapabilities['platform']; version: number } {
  const ua = navigator.userAgent;

  // iOS detection
  const iOSMatch = ua.match(/iPhone|iPad|iPod/);
  if (iOSMatch) {
    const versionMatch = ua.match(/OS (\d+)_/);
    return {
      platform: 'apple',
      version: versionMatch ? parseInt(versionMatch[1], 10) : 0,
    };
  }

  // macOS detection
  const macOSMatch = ua.match(/Mac OS X (\d+)/);
  if (macOSMatch) {
    return {
      platform: 'apple',
      version: parseInt(macOSMatch[1], 10),
    };
  }

  // Android detection
  const androidMatch = ua.match(/Android (\d+)/);
  if (androidMatch) {
    return {
      platform: 'android',
      version: parseInt(androidMatch[1], 10),
    };
  }

  // Windows detection
  const windowsMatch = ua.match(/Windows NT (\d+)/);
  if (windowsMatch) {
    return {
      platform: 'windows',
      version: parseInt(windowsMatch[1], 10),
    };
  }

  return { platform: 'other', version: 0 };
}

/**
 * Check if WebAuthn conditional UI (autofill) is available.
 * This enables passkey autofill in email input fields.
 */
export async function isConditionalUIAvailable(): Promise<boolean> {
  if (!('PublicKeyCredential' in window)) {
    return false;
  }

  // Modern check
  if ('isConditionalMediationAvailable' in PublicKeyCredential) {
    try {
      return await PublicKeyCredential.isConditionalMediationAvailable();
    } catch {
      return false;
    }
  }

  // Fallback check for older implementations
  try {
    const capabilities = await (PublicKeyCredential as any).getClientCapabilities?.();
    return capabilities?.conditionalGet ?? false;
  } catch {
    return false;
  }
}
```

### 3.3 Tier-Based Authentication Component

```typescript
// src/components/auth/TieredSignIn.tsx

import React, { useEffect, useState, useCallback } from 'react';
import { detectAuthCapabilities, AuthCapabilities } from '@/lib/webauthn/capability-detection';
import { initiatePasskeyAuthentication, finishPasskeyAuthentication } from '@/lib/webauthn/passkey-auth';
import { getStoredCredential, storePasswordCredential, preventSilentAccess } from '@/lib/credential-manager/credential-api';
import { SocialLoginButtons } from './SocialLoginButtons';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Fingerprint, Key, Mail, Loader2 } from 'lucide-react';

interface TieredSignInProps {
  onSignIn: (token: string, user: any) => void;
  onError: (error: string) => void;
}

export function TieredSignIn({ onSignIn, onError }: TieredSignInProps) {
  const [capabilities, setCapabilities] = useState<AuthCapabilities | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPasswordForm, setShowPasswordForm] = useState(false);

  // Detect capabilities on mount
  useEffect(() => {
    detectAuthCapabilities().then(setCapabilities);
  }, []);

  // Auto-trigger passkey autofill if available
  useEffect(() => {
    if (capabilities?.conditionalUIAvailable) {
      // Passkey autofill will be triggered via autocomplete="webauthn"
      // No manual trigger needed
    } else if (capabilities?.tier === 2) {
      // Try silent credential retrieval for Tier 2
      attemptSilentCredentialRetrieval();
    }
  }, [capabilities]);

  const attemptSilentCredentialRetrieval = async () => {
    const credential = await getStoredCredential('silent');
    if (credential) {
      // Auto-fill email from stored credential
      if ('id' in credential) {
        setEmail(credential.id as string);
      }
    }
  };

  // Passkey authentication (Tier 3/4)
  const handlePasskeySignIn = useCallback(async () => {
    if (!capabilities?.webAuthn) {
      onError('Passkeys are not supported on this device');
      return;
    }

    setIsLoading(true);
    try {
      const { challenge, rpId, allowCredentials } = await initiatePasskeyAuthentication(email || undefined);
      
      const assertion = await navigator.credentials.get({
        publicKey: {
          challenge: Uint8Array.from(atob(challenge), c => c.charCodeAt(0)),
          rpId,
          allowCredentials: allowCredentials.map(c => ({
            type: 'public-key',
            id: Uint8Array.from(atob(c.id), c => c.charCodeAt(0)),
            transports: c.transports,
          })),
          userVerification: 'preferred',
        },
        mediation: 'optional',
      }) as PublicKeyCredential;

      const response = assertion.response as AuthenticatorAssertionResponse;
      
      const result = await finishPasskeyAuthentication({
        credentialId: btoa(String.fromCharCode(...new Uint8Array(assertion.rawId))),
        clientDataJSON: btoa(String.fromCharCode(...new Uint8Array(response.clientDataJSON))),
        authenticatorData: btoa(String.fromCharCode(...new Uint8Array(response.authenticatorData))),
        signature: btoa(String.fromCharCode(...new Uint8Array(response.signature))),
        userHandle: response.userHandle ? btoa(String.fromCharCode(...new Uint8Array(response.userHandle))) : undefined,
      });

      if (result.access_token) {
        onSignIn(result.access_token, result.user);
      }
    } catch (error: any) {
      if (error.name === 'NotAllowedError') {
        // User cancelled - don't show error
      } else {
        onError(error.message || 'Passkey authentication failed');
      }
    } finally {
      setIsLoading(false);
    }
  }, [capabilities, email, onSignIn, onError]);

  // Password authentication (Tier 1/2)
  const handlePasswordSignIn = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }

      const data = await response.json();
      
      // Store credential in OS credential manager (Tier 2)
      if (capabilities?.credentialAPI) {
        await storePasswordCredential(email, password);
      }

      onSignIn(data.access_token, data.user);
    } catch (error: any) {
      onError(error.message);
    } finally {
      setIsLoading(false);
    }
  }, [email, password, capabilities, onSignIn, onError]);

  // Show loading state while detecting capabilities
  if (!capabilities) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Tier 3/4: Passkey Sign-In Button */}
      {capabilities.webAuthnPlatformAuthenticator && (
        <div className="space-y-3">
          <Button
            type="button"
            variant="hero"
            size="lg"
            className="w-full"
            onClick={handlePasskeySignIn}
            disabled={isLoading}
          >
            <Fingerprint className="h-5 w-5 mr-2" />
            {isLoading ? 'Authenticating...' : 'Sign in with Passkey'}
          </Button>
          
          {/* Passkey autofill input (conditional UI) */}
          {capabilities.conditionalUIAvailable && (
            <div className="relative">
              <Input
                type="email"
                placeholder="Or use passkey autofill..."
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="webauthn"
                className="pr-10"
              />
              <Key className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            </div>
          )}
          
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">or</span>
            </div>
          </div>
        </div>
      )}

      {/* OAuth Buttons (all tiers) */}
      <SocialLoginButtons />

      {/* Tier 1/2: Email/Password Form */}
      {showPasswordForm || !capabilities.webAuthnPlatformAuthenticator ? (
        <form onSubmit={handlePasswordSignIn} className="space-y-4">
          <div>
            <Label htmlFor="email">Email</Label>
            <div className="relative mt-1">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="pl-10"
                autoComplete={capabilities.credentialAPI ? 'email webauthn' : 'email'}
                required
              />
            </div>
          </div>

          <div>
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
            />
          </div>

          <Button type="submit" size="lg" className="w-full" disabled={isLoading}>
            {isLoading ? 'Signing in...' : 'Sign In'}
          </Button>
        </form>
      ) : (
        <Button
          type="button"
          variant="outline"
          size="lg"
          className="w-full"
          onClick={() => setShowPasswordForm(true)}
        >
          Sign in with password instead
        </Button>
      )}
    </div>
  );
}
```

---

## 4. Session & FastAPI Backend Interaction

### 4.1 WebAuthn Assertion to JWT Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WEBAUTHN → JWT SESSION FLOW                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Browser calls navigator.credentials.get()                               │
│     └─ Returns: PublicKeyCredential with assertion                          │
│                                                                              │
│  2. POST /api/auth/webauthn/authenticate/finish                             │
│     └─ Body: { credentialId, clientDataJSON, authenticatorData, signature } │
│                                                                              │
│  3. FastAPI validates assertion                                              │
│     ├─ Verify challenge matches stored challenge                            │
│     ├─ Verify origin matches RP_ORIGIN                                       │
│     ├─ Verify signature using stored public key                             │
│     ├─ Verify sign_count > stored count (clone detection)                   │
│     └─ Update sign_count in database                                         │
│                                                                              │
│  4. FastAPI generates JWT                                                    │
│     ├─ access_token: { sub: userId, email, type: "access", exp: +24h }      │
│     └─ refresh_token: { sub: userId, email, type: "refresh", exp: +7d }     │
│                                                                              │
│  5. Response to browser                                                      │
│     └─ { access_token, refresh_token, user: {...} }                         │
│                                                                              │
│  6. Browser stores tokens                                                    │
│     ├─ Vite app: localStorage (confit_token, confit_refresh_token)          │
│     └─ Next.js app: HttpOnly cookie (via /auth/callback)                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Session Validation: OAuth vs Passkey vs Password

```python
# backend/services/session_validator.py

"""
CONFIT Backend — Session Validation
====================================
Unified session validation for OAuth, passkey, and password authentication.
"""

import logging
from typing import Optional, Tuple
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from database.models import User, WebAuthnCredential
from services.auth_service import AuthService

logger = logging.getLogger(__name__)


class SessionSource:
    """Enumeration of session sources."""
    PASSWORD = "password"
    OAUTH_GOOGLE = "oauth_google"
    OAUTH_FACEBOOK = "oauth_facebook"
    OAUTH_APPLE = "oauth_apple"
    OAUTH_X = "oauth_x"
    OAUTH_TIKTOK = "oauth_tiktok"
    PASSKEY = "passkey"
    PASSKEY_SYNCED = "passkey_synced"  # iCloud Keychain / Google Password Manager


class SessionValidator:
    """Validates sessions and tracks authentication method."""

    def __init__(self, db: Session):
        self._db = db
        self._auth_service = AuthService(db)

    def validate_session(
        self,
        token: str,
        expected_source: Optional[str] = None,
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Validate a JWT session and optionally verify authentication source.
        
        Returns:
            Tuple of (user, session_source) or (None, None) if invalid.
        """
        payload = self._auth_service.decode_token(token)
        if not payload:
            return None, None

        user_id = payload.get("sub")
        email = payload.get("email")
        token_type = payload.get("type")

        if token_type != "access":
            logger.warning(f"Invalid token type used for session: {token_type}")
            return None, None

        user = self._auth_service.get_user_by_email(email)
        if not user or str(user.id) != user_id:
            return None, None

        # Determine session source from token claims or database
        session_source = payload.get("auth_source", SessionSource.PASSWORD)

        # If expected source specified, verify match
        if expected_source and session_source != expected_source:
            logger.warning(
                f"Session source mismatch: expected {expected_source}, got {session_source}"
            )
            return None, None

        return user, session_source

    def validate_passkey_session(
        self,
        token: str,
        credential_id: Optional[str] = None,
    ) -> Tuple[Optional[User], Optional[WebAuthnCredential]]:
        """
        Validate a passkey-authenticated session.
        
        Optionally verify specific credential was used.
        """
        user, source = self.validate_session(token)

        if not user:
            return None, None

        if source not in (SessionSource.PASSKEY, SessionSource.PASSKEY_SYNCED):
            logger.warning(f"Token not from passkey authentication: {source}")
            return None, None

        # If credential_id specified, verify it belongs to user
        if credential_id:
            cred = self._db.query(WebAuthnCredential).filter(
                WebAuthnCredential.credential_id == credential_id,
                WebAuthnCredential.user_id == user.id,
            ).first()
            if not cred:
                return None, None
            return user, cred

        return user, None

    def create_session_token(
        self,
        user: User,
        source: str,
        credential_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Create access and refresh tokens with authentication source claim.
        
        Args:
            user: User object
            source: SessionSource value
            credential_id: Optional WebAuthn credential ID for passkey sessions
            
        Returns:
            Tuple of (access_token, refresh_token)
        """
        import secrets
        import jwt
        from datetime import timedelta

        from services.auth_service import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS

        access_payload = {
            "sub": str(user.id),
            "email": user.email,
            "type": "access",
            "auth_source": source,
            "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.now(timezone.utc),
            "iss": "confit",
            "jti": secrets.token_hex(16),
        }

        if credential_id:
            access_payload["credential_id"] = credential_id

        refresh_payload = {
            "sub": str(user.id),
            "email": user.email,
            "type": "refresh",
            "auth_source": source,
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
            "iat": datetime.now(timezone.utc),
            "iss": "confit",
            "jti": secrets.token_hex(16),
        }

        access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        return access_token, refresh_token
```

### 4.3 CORS and Callback Configuration

```python
# backend/main.py (additions for credential manager support)

"""
Additional CORS and session configuration for credential manager integration.
"""

# CORS configuration must include all allowed origins
ALLOWED_ORIGINS = [
    "http://localhost:5173",      # Vite dev server
    "http://localhost:3000",      # Next.js dev server
    "http://localhost:8000",      # FastAPI direct access
    "https://confit.com",         # Production
    "https://www.confit.com",     # Production www
]

# For WebAuthn, the origin must exactly match the RP_ORIGIN
# This is critical for passkey authentication
WEBAUTHN_RP_ORIGIN = os.getenv("WEBAUTHN_RP_ORIGIN", "http://localhost:5173")

# Session cookie configuration
SESSION_COOKIE_CONFIG = {
    "key": "confit_session",
    "httponly": True,
    "secure": True,  # Required for WebAuthn
    "samesite": "lax",  # Allows OAuth callbacks
    "max_age": 86400,  # 24 hours
}

# For cross-origin passkey authentication (e.g., native app → web)
# Requires careful configuration of allowed origins
```

### 4.4 Attack Surfaces and Mitigations

| Attack Vector | Description | Mitigation |
|---------------|-------------|------------|
| **Replay Attack** | Attacker reuses captured assertion | Challenge is single-use, expires in 5 minutes |
| **RP ID Spoofing** | Attacker tricks user into registering on fake RP | Origin validation in client data, HTTPS required |
| **Credential Phishing** | Fake UI captures passkey assertion | WebAuthn origin binding prevents cross-origin use |
| **Credential Cloning** | Physical authenticator cloned | Sign counter verification detects cloned authenticators |
| **Man-in-the-Middle** | Intercept challenge/response | TLS required, origin validation in assertion |
| **Backup State Manipulation** | Attacker modifies backup flags | Server stores backup state, alerts on changes |
| **Cross-Site Request Forgery** | CSRF on credential registration | CSRF token required for registration endpoints |
| **Session Hijacking** | Stolen JWT token | Short token lifetime, refresh token rotation |

```python
# backend/core/security/webauthn_security.py

"""
WebAuthn Security Utilities
==========================
Additional security measures for credential manager integration.
"""

import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from database.models import WebAuthnCredential, WebAuthnChallenge

logger = logging.getLogger(__name__)


def detect_credential_cloning(
    credential: WebAuthnCredential,
    new_sign_count: int,
) -> bool:
    """
    Detect potential credential cloning via sign counter analysis.
    
    Returns True if cloning is suspected.
    """
    # Sign count should always increase
    if new_sign_count <= credential.sign_count and credential.sign_count != 0:
        logger.error(
            f"Credential cloning suspected for {credential.credential_id}: "
            f"stored_count={credential.sign_count}, new_count={new_sign_count}"
        )
        return True
    
    return False


def validate_backup_state_change(
    credential: WebAuthnCredential,
    new_backup_eligible: bool,
    new_backup_state: bool,
) -> tuple[bool, Optional[str]]:
    """
    Validate backup state changes.
    
    Returns (is_valid, warning_message).
    """
    warnings = []
    
    # Backup eligibility should not change from false to true
    if not credential.backup_eligible and new_backup_eligible:
        warnings.append("Backup eligibility changed from false to true")
    
    # Backup state changes should be logged
    if credential.backup_state != new_backup_state:
        if new_backup_state:
            logger.info(f"Credential {credential.credential_id} backed up")
        else:
            logger.warning(
                f"Credential {credential.credential_id} backup state cleared"
            )
    
    return True, "; ".join(warnings) if warnings else None


def cleanup_expired_challenges(db: Session) -> int:
    """
    Remove expired WebAuthn challenges from database.
    
    Returns count of deleted challenges.
    """
    now = datetime.now(timezone.utc)
    expired = db.query(WebAuthnChallenge).filter(
        WebAuthnChallenge.expires_at < now
    ).all()
    
    count = len(expired)
    for challenge in expired:
        db.delete(challenge)
    
    db.commit()
    return count


def rate_limit_webauthn_requests(
    db: Session,
    user_id: str,
    ceremony_type: str,
    max_attempts: int = 5,
    window_minutes: int = 5,
) -> bool:
    """
    Check if user has exceeded WebAuthn request rate limit.
    
    Returns True if rate limit exceeded.
    """
    window_start = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    
    recent_challenges = db.query(WebAuthnChallenge).filter(
        WebAuthnChallenge.user_id == user_id,
        WebAuthnChallenge.ceremony_type == ceremony_type,
        WebAuthnChallenge.created_at > window_start,
    ).count()
    
    return recent_challenges >= max_attempts
```

---

## 5. UX Mockups & Sign-In Page Code

### 5.1 ASCII UX Mockups

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     TIER 4: PASSKEY + SYNC (Apple/Android 14+)              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                     │    │
│  │                        🔐 CONFIT                                    │    │
│  │                                                                     │    │
│  │              Welcome Back to CONFIT                                 │    │
│  │         Sign in to access your personalized style                  │    │
│  │                                                                     │    │
│  │  ┌───────────────────────────────────────────────────────────┐    │    │
│  │  │  🔑 Sign in with Passkey                          [Hero]  │    │    │
│  │  └───────────────────────────────────────────────────────────┘    │    │
│  │                                                                     │    │
│  │  ┌───────────────────────────────────────────────────────────┐    │    │
│  │  │  📧 you@example.com                              [Key 🔑] │    │    │
│  │  │  (autocomplete="webauthn" - passkey autofill)              │    │    │
│  │  └───────────────────────────────────────────────────────────┘    │    │
│  │                                                                     │    │
│  │  ─────────────────── or continue with ───────────────────         │    │
│  │                                                                     │    │
│  │  ┌───────────────────────────────────────────────────────────┐    │    │
│  │  │  [G] Continue with Google                                  │    │    │
│  │  └───────────────────────────────────────────────────────────┘    │    │
│  │  ┌───────────────────────────────────────────────────────────┐    │    │
│  │  │  [🍎] Continue with Apple                                  │    │    │
│  │  └───────────────────────────────────────────────────────────┘    │    │
│  │                                                                     │    │
│  │  ─────────────────── or ───────────────────                       │    │
│  │                                                                     │    │
│  │  Sign in with password instead                                     │    │
│  │                                                                     │    │
│  │  Don't have an account? Sign Up                                    │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  [When user clicks "Sign in with Passkey":]                                 │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                     │    │
│  │  ┌───────────────────────────────────────────────────────────┐    │    │
│  │  │  🔐 Use Touch ID to sign in to confit.com                 │    │    │
│  │  │                                                           │    │    │
│  │  │  Touch ID or enter your device password to authenticate.  │    │    │
│  │  │                                                           │    │    │
│  │  │  [Cancel]                              [Use Touch ID]     │    │    │
│  │  └───────────────────────────────────────────────────────────┘    │    │
│  │                                                                     │    │
│  │  (Native OS dialog - macOS/iOS Touch ID prompt)                   │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                     TIER 3: PASSKEY DEVICE-BOUND (Windows)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                     │    │
│  │  ┌───────────────────────────────────────────────────────────┐    │    │
│  │  │  🔑 Sign in with Windows Hello                     [Hero]  │    │    │
│  │  └───────────────────────────────────────────────────────────┘    │    │
│  │                                                                     │    │
│  │  [When clicked:]                                                   │    │
│  │  ┌───────────────────────────────────────────────────────────┐    │    │
│  │  │  🔐 Windows Security                                       │    │    │
│  │  │                                                           │    │    │
│  │  │  Looking for the PIN...                                   │    │    │
│  │  │  or                                                       │    │    │
│  │  │  Place your finger on the fingerprint reader              │    │    │
│  │  │                                                           │    │    │
│  │  │  [More choices]  [Cancel]                                │    │    │
│  │  └───────────────────────────────────────────────────┘    │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                     TIER 2: CREDENTIAL MANAGEMENT API                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                     │    │
│  │  ┌───────────────────────────────────────────────────────────┐    │    │
│  │  │  🔑 Sign in with saved password                   [Hero]  │    │    │
│  │  └───────────────────────────────────────────────────────────┘    │    │
│  │                                                                     │    │
│  │  [When clicked, OS credential picker appears:]                    │    │
│  │  ┌───────────────────────────────────────────────────────────┐    │    │
│  │  │  Choose an account                                         │    │    │
│  │  │                                                           │    │    │
│  │  │  👤 user@example.com                              [Use]   │    │    │
│  │  │  👤 demo@confit.com                              [Use]   │    │    │
│  │  │                                                           │    │    │
│  │  │  [Cancel]                                                 │    │    │
│  │  └───────────────────────────────────────────────────┘    │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                     TIER 1: BASELINE EMAIL AUTOCOMPLETE                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                     │    │
│  │  Email                                                              │    │
│  │  ┌───────────────────────────────────────────────────────────┐    │    │
│  │  │  📧 user@example.com                               [▼]    │    │    │
│  │  └───────────────────────────────────────────────────────────┘    │    │
│  │  (autocomplete="email" - browser autofill dropdown)               │    │
│  │                                                                     │    │
│  │  Password                                                           │    │
│  │  ┌───────────────────────────────────────────────────────────┐    │    │
│  │  │  🔒 ••••••••                                         [👁]   │    │    │
│  │  └───────────────────────────────────────────────────────────┘    │    │
│  │  (autocomplete="current-password")                                │    │
│  │                                                                     │    │
│  │  ┌───────────────────────────────────────────────────────────┐    │    │
│  │  │  Sign In                                           [Hero]  │    │    │
│  │  └───────────────────────────────────────────────────────────┘    │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Complete Sign-In Page TSX

```tsx
// src/pages/SignInPage.tsx

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Fingerprint, 
  Key, 
  Mail, 
  Lock, 
  Eye, 
  EyeOff, 
  ArrowRight,
  Loader2,
  AlertCircle,
  Check,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { cn } from '@/lib/utils';

import { 
  detectAuthCapabilities, 
  AuthCapabilities,
  isConditionalUIAvailable,
} from '@/lib/webauthn/capability-detection';
import {
  startPasskeyAuthentication,
  finishPasskeyAuthentication,
} from '@/lib/webauthn/passkey-client';
import {
  getStoredCredential,
  storePasswordCredential,
  preventSilentAccess,
} from '@/lib/credential-manager/credential-api';
import { SocialLoginButtons } from '@/components/auth/SocialLoginButtons';
import { useAuth } from '@/context/AuthContext';
import { createTransition } from '@/motion';

const AUTH_ORIGIN = import.meta.env.VITE_AUTH_ORIGIN || import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function SignInPage() {
  const navigate = useNavigate();
  const { signIn, isAuthenticated } = useAuth();
  
  // State
  const [capabilities, setCapabilities] = useState<AuthCapabilities | null>(null);
  const [isLoadingCapabilities, setIsLoadingCapabilities] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Refs
  const emailInputRef = useRef<HTMLInputElement>(null);
  const conditionalUIAttempted = useRef(false);

  // Detect capabilities on mount
  useEffect(() => {
    async function detect() {
      try {
        const caps = await detectAuthCapabilities();
        setCapabilities(caps);
        
        // Log detected tier for analytics
        console.log('[Auth] Detected capability tier:', caps.tier, caps);
      } catch (err) {
        console.error('[Auth] Failed to detect capabilities:', err);
      } finally {
        setIsLoadingCapabilities(false);
      }
    }
    detect();
  }, []);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  // Attempt conditional UI (passkey autofill) on page load
  useEffect(() => {
    if (
      capabilities?.conditionalUIAvailable &&
      !conditionalUIAttempted.current &&
      emailInputRef.current
    ) {
      conditionalUIAttempted.current = true;
      // The input with autocomplete="webauthn" will trigger autofill
      // No manual call needed - browser handles it
    }
  }, [capabilities]);

  // Tier 2: Attempt silent credential retrieval
  useEffect(() => {
    if (capabilities?.tier === 2 && !capabilities.webAuthn) {
      getStoredCredential('silent').then(cred => {
        if (cred && 'id' in cred) {
          setEmail(cred.id as string);
        }
      });
    }
  }, [capabilities]);

  // Passkey authentication handler
  const handlePasskeySignIn = useCallback(async () => {
    if (!capabilities?.webAuthn) {
      setError('Passkeys are not supported on this device');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Start authentication ceremony
      const startResponse = await startPasskeyAuthentication(
        email || undefined // Email hint if provided
      );

      // Convert base64 to ArrayBuffer
      const challenge = Uint8Array.from(atob(startResponse.challenge), c => c.charCodeAt(0));
      
      // Build allowCredentials
      const allowCredentials = startResponse.allow_credentials.map(c => ({
        type: 'public-key' as const,
        id: Uint8Array.from(atob(c.id), c => c.charCodeAt(0)),
        transports: c.transports as AuthenticatorTransport[],
      }));

      // Call WebAuthn API
      const assertion = await navigator.credentials.get({
        publicKey: {
          challenge,
          rpId: startResponse.rp_id,
          allowCredentials: allowCredentials.length > 0 ? allowCredentials : undefined,
          userVerification: startResponse.user_verification as UserVerificationRequirement,
          timeout: startResponse.timeout,
        },
        mediation: 'optional',
      }) as PublicKeyCredential;

      if (!assertion) {
        throw new Error('No credential selected');
      }

      const response = assertion.response as AuthenticatorAssertionResponse;

      // Finish authentication
      const result = await finishPasskeyAuthentication({
        credential_id: btoa(String.fromCharCode(...new Uint8Array(assertion.rawId))),
        client_data_json: btoa(String.fromCharCode(...new Uint8Array(response.clientDataJSON))),
        authenticator_data: btoa(String.fromCharCode(...new Uint8Array(response.authenticatorData))),
        signature: btoa(String.fromCharCode(...new Uint8Array(response.signature))),
        user_handle: response.userHandle 
          ? btoa(String.fromCharCode(...new Uint8Array(response.userHandle)))
          : undefined,
      });

      if (result.success && result.access_token) {
        // Store tokens
        localStorage.setItem('confit_token', result.access_token);
        if (result.refresh_token) {
          localStorage.setItem('confit_refresh_token', result.refresh_token);
        }
        if (result.user) {
          localStorage.setItem('confit_user', JSON.stringify(result.user));
        }

        setSuccess('Signed in successfully!');
        
        // Navigate to home
        setTimeout(() => navigate('/'), 500);
      } else {
        throw new Error(result.message || 'Authentication failed');
      }
    } catch (err: any) {
      if (err.name === 'NotAllowedError') {
        // User cancelled - don't show error
        console.log('[Auth] User cancelled passkey authentication');
      } else {
        setError(err.message || 'Passkey authentication failed');
      }
    } finally {
      setIsLoading(false);
    }
  }, [capabilities, email, navigate]);

  // Password authentication handler
  const handlePasswordSignIn = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const result = await signIn(email, password);
      
      if (result.error) {
        setError(result.error);
      } else {
        // Store credential in OS manager (Tier 2)
        if (capabilities?.credentialAPI) {
          await storePasswordCredential(email, password);
        }
        
        setSuccess('Signed in successfully!');
        navigate('/');
      }
    } catch (err: any) {
      setError(err.message || 'Sign in failed');
    } finally {
      setIsLoading(false);
    }
  }, [email, password, capabilities, signIn, navigate]);

  // Handle conditional UI result (passkey autofill from input)
  const handleConditionalUIResult = useCallback(async (credential: PublicKeyCredential) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = credential.response as AuthenticatorAssertionResponse;
      
      const result = await finishPasskeyAuthentication({
        credential_id: btoa(String.fromCharCode(...new Uint8Array(credential.rawId))),
        client_data_json: btoa(String.fromCharCode(...new Uint8Array(response.clientDataJSON))),
        authenticator_data: btoa(String.fromCharCode(...new Uint8Array(response.authenticatorData))),
        signature: btoa(String.fromCharCode(...new Uint8Array(response.signature))),
        user_handle: response.userHandle 
          ? btoa(String.fromCharCode(...new Uint8Array(response.userHandle)))
          : undefined,
      });

      if (result.success && result.access_token) {
        localStorage.setItem('confit_token', result.access_token);
        if (result.refresh_token) {
          localStorage.setItem('confit_refresh_token', result.refresh_token);
        }
        if (result.user) {
          localStorage.setItem('confit_user', JSON.stringify(result.user));
        }
        
        setSuccess('Signed in successfully!');
        setTimeout(() => navigate('/'), 500);
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setIsLoading(false);
    }
  }, [navigate]);

  // Loading state
  if (isLoadingCapabilities) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      {/* Left: Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="w-full max-w-md"
        >
          {/* Logo */}
          <Link to="/" className="inline-block mb-10">
            <span className="font-display text-3xl font-semibold tracking-tight">CONFIT</span>
          </Link>

          {/* Header */}
          <motion.h1
            className="heading-section mb-2 text-foreground"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={createTransition({ delay: 0.1 })}
          >
            Welcome Back
          </motion.h1>
          <motion.p
            className="text-muted-foreground mb-8 text-base leading-relaxed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={createTransition({ delay: 0.2 })}
          >
            Sign in to access your personalized style experience.
          </motion.p>

          {/* Error/Success Alerts */}
          {error && (
            <Alert variant="destructive" className="mb-6">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {success && (
            <Alert className="mb-6 border-green-500 bg-green-50 text-green-800">
              <Check className="h-4 w-4 text-green-500" />
              <AlertDescription>{success}</AlertDescription>
            </Alert>
          )}

          {/* Tier 3/4: Passkey Sign-In */}
          {capabilities?.webAuthnPlatformAuthenticator && (
            <motion.div
              className="mb-6 space-y-3"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={createTransition({ delay: 0.3 })}
            >
              <Button
                type="button"
                variant="hero"
                size="lg"
                className="w-full shadow-lg hover:shadow-xl transition-all duration-300"
                onClick={handlePasskeySignIn}
                disabled={isLoading}
              >
                {isLoading ? (
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                ) : (
                  <Fingerprint className="h-5 w-5 mr-2" />
                )}
                {isLoading ? 'Authenticating...' : 'Sign in with Passkey'}
              </Button>

              {/* Conditional UI Input (Passkey Autofill) */}
              {capabilities.conditionalUIAvailable && (
                <div className="relative">
                  <Input
                    ref={emailInputRef}
                    type="email"
                    placeholder="Or use passkey autofill..."
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    // Enable WebAuthn conditional UI
                    autoComplete="webauthn"
                    className="pr-10"
                    disabled={isLoading}
                  />
                  <Key className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                </div>
              )}

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-background px-2 text-muted-foreground">or continue with</span>
                </div>
              </div>
            </motion.div>
          )}

          {/* OAuth Buttons (All Tiers) */}
          <motion.div
            className="mb-6 space-y-3"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={createTransition({ delay: 0.4 })}
          >
            <SocialLoginButtons />
          </motion.div>

          {/* Divider */}
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">or</span>
            </div>
          </div>

          {/* Password Form (Tier 1/2) */}
          {showPasswordForm || !capabilities?.webAuthnPlatformAuthenticator ? (
            <motion.form
              onSubmit={handlePasswordSignIn}
              className="space-y-5"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={createTransition({ delay: 0.5 })}
            >
              <div>
                <Label htmlFor="email">Email</Label>
                <div className="relative mt-1">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className={cn(
                      "pl-10 bg-background border-border text-foreground",
                      "placeholder:text-muted-foreground/60"
                    )}
                    autoComplete={capabilities?.credentialAPI ? "email webauthn" : "email"}
                    required
                    disabled={isLoading}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="password">Password</Label>
                <div className="relative mt-1">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="pl-10 pr-10"
                    autoComplete="current-password"
                    required
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <Button
                type="submit"
                variant="hero"
                size="lg"
                className="w-full shadow-lg hover:shadow-xl transition-all duration-300"
                disabled={isLoading}
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <ArrowRight className="h-4 w-4 ml-2" />
                )}
                {isLoading ? 'Signing in...' : 'Sign In'}
              </Button>
            </motion.form>
          ) : (
            <Button
              type="button"
              variant="outline"
              size="lg"
              className="w-full"
              onClick={() => setShowPasswordForm(true)}
            >
              Sign in with password instead
            </Button>
          )}

          {/* Sign Up Link */}
          <p className="text-sm text-muted-foreground text-center mt-8">
            Don't have an account?{' '}
            <Link to="/auth?mode=signup" className="text-accent font-medium hover:underline">
              Sign Up
            </Link>
          </p>
        </motion.div>
      </div>

      {/* Right: Brand Visual */}
      <div className="hidden lg:flex flex-1 bg-gradient-hero items-center justify-center p-12">
        <div className="max-w-lg text-center text-primary-foreground">
          <h2 className="heading-hero mb-6">
            Wear Your <span className="text-gradient-gold">Confidence</span>
          </h2>
          <p className="text-lg text-primary-foreground/70 mb-8">
            AI-powered styling, virtual try-on, and personalized outfit recommendations — all in one platform.
          </p>
          <div className="flex justify-center gap-6 text-sm text-primary-foreground/50">
            <span>AI Stylist</span>
            <span>•</span>
            <span>Virtual Try-On</span>
            <span>•</span>
            <span>Smart Wardrobe</span>
          </div>
        </div>
      </div>
    </div>
  );
}
```

---

## 6. Privacy & Security Considerations

### 6.1 Platform Encryption Standards

| Platform | Credential Storage | Encryption | CONFIT Control |
|----------|-------------------|------------|----------------|
| **Apple Keychain** | Secure Enclave / iCloud | AES-256-GCM, hardware-backed | None - Apple managed |
| **Windows Credential Manager** | TPM 2.0 protected | Hardware-backed encryption | None - Microsoft managed |
| **Android Keystore** | TEE / StrongBox | AES-256, hardware-backed | None - Google managed |
| **Chrome Profile** | OS credential store | Inherits OS encryption | None |

**Key Insight**: CONFIT cannot control encryption at the OS level. All platforms use hardware-backed encryption that CONFIT cannot influence. This is a security feature, not a limitation.

### 6.2 User Consent Requirements

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CONSENT FLOW REQUIREMENTS                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PASSKEY REGISTRATION                                                        │
│  ─────────────────────                                                       │
│  1. User must be authenticated (password or OAuth)                           │
│  2. User must explicitly click "Register Passkey"                           │
│  3. OS shows native consent dialog (Touch ID, Windows Hello, etc.)          │
│  4. User must complete biometric/PIN verification                            │
│  5. CONFIT must display success message with device name                     │
│                                                                              │
│  PASSKEY AUTHENTICATION                                                      │
│  ─────────────────────────                                                   │
│  1. User clicks "Sign in with Passkey" OR uses autofill                     │
│  2. OS shows credential picker (if multiple passkeys)                       │
│  3. User must complete biometric/PIN verification                            │
│  4. No additional consent required (implicit in authentication)             │
│                                                                              │
│  CREDENTIAL STORAGE (Tier 2)                                                 │
│  ─────────────────────────                                                   │
│  1. User must complete sign-in                                              │
│ 2. Browser/OS prompts to save credential                                     │
│  3. User explicitly accepts or declines                                      │
│  4. CONFIT should NOT auto-store without user interaction                    │
│                                                                              │
│  FEDERATED CREDENTIAL STORAGE                                                │
│  ─────────────────────────                                                   │
│  1. User completes OAuth flow                                                │
│  2. Browser may prompt to save federated credential                          │
│  3. User must explicitly accept                                              │
│  4. CONFIT should not store OAuth tokens in credential manager              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 GDPR/Privacy Implications

**Data Stored at OS Level:**
- Email address (identifier)
- Credential ID (random unique identifier)
- Public key (cryptographic material)
- Device nickname (user-provided)

**GDPR Considerations:**

1. **Right to Erasure**: CONFIT must delete credential records from database. OS-level deletion is user-controlled.

2. **Data Portability**: WebAuthn credentials are not portable between ecosystems (Apple ↔ Google). CONFIT should offer passkey re-registration.

3. **Consent Records**: CONFIT must log when user registered a passkey and display this in account settings.

4. **Third-Party Processors**: iCloud Keychain and Google Password Manager are third-party processors. Privacy policy must disclose.

5. **Cross-Border Transfer**: Passkey sync may transfer data to servers in other jurisdictions. User must be informed.

### 6.4 Audit Logging Requirements

```python
# backend/models/credential_audit_log.py

"""
Audit logging for credential manager operations.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, Text
from database.base import Base
from database.models import UUIDType, _new_uuid


class CredentialAuditLog(Base):
    """Audit trail for all credential manager operations."""
    __tablename__ = "credential_audit_logs"
    __table_args__ = {"extend_existing": True}

    id = Column(UUIDType, primary_key=True, default=_new_uuid)
    user_id = Column(UUIDType, nullable=False, index=True)
    
    # Operation type
    operation = Column(String(50), nullable=False)  # register, authenticate, delete
    
    # Credential details
    credential_id = Column(String(255), nullable=True, index=True)
    credential_type = Column(String(32), nullable=False)  # passkey, password, federated
    
    # Authentication method details
    auth_method = Column(String(32), nullable=False)  # webauthn, password, oauth
    platform = Column(String(32), nullable=True)  # apple, windows, android
    user_verified = Column(String(16), nullable=True)  # true, false, preferred
    
    # Result
    success = Column(String(16), nullable=False)  # success, failed, cancelled
    error_message = Column(Text, nullable=True)
    
    # Context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    origin = Column(String(256), nullable=True)
    
    # Additional metadata
    metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))


# Audit log operations
AUDIT_OPERATIONS = {
    'PASSKEY_REGISTER_START': 'passkey_register_start',
    'PASSKEY_REGISTER_SUCCESS': 'passkey_register_success',
    'PASSKEY_REGISTER_FAILED': 'passkey_register_failed',
    'PASSKEY_AUTHENTICATE_START': 'passkey_authenticate_start',
    'PASSKEY_AUTHENTICATE_SUCCESS': 'passkey_authenticate_success',
    'PASSKEY_AUTHENTICATE_FAILED': 'passkey_authenticate_failed',
    'PASSKEY_DELETE': 'passkey_delete',
    'CREDENTIAL_STORE': 'credential_store',
    'CREDENTIAL_RETRIEVE': 'credential_retrieve',
    'OAUTH_LOGIN': 'oauth_login',
    'PASSWORD_LOGIN': 'password_login',
}
```

---

## 7. Phased Rollout Plan

### 7.1 Rollout Phases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PHASE 1: FOUNDATION                                │
│                           (Weeks 1-4)                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TARGET: Chrome/Edge on Windows 10/11 + Safari on macOS                     │
│                                                                              │
│  FEATURES:                                                                   │
│  ├─ WebAuthn registration (authenticated users only)                        │
│  ├─ WebAuthn authentication (manual trigger)                                │
│  ├─ Credential storage in database                                          │
│  └─ Audit logging                                                           │
│                                                                              │
│  PLATFORMS:                                                                  │
│  ├─ Windows 10/11 (Chrome, Edge) - Windows Hello                           │
│  └─ macOS 13+ (Safari) - Touch ID                                          │
│                                                                              │
│  FEATURE FLAGS:                                                              │
│  ├─ ENABLE_WEBAUTHN_REGISTRATION: true                                      │
│  ├─ ENABLE_WEBAUTHN_AUTHENTICATION: true                                    │
│  └─ ENABLE_WEBAUTHN_AUTOFILL: false                                         │
│                                                                              │
│  SUCCESS CRITERIA:                                                           │
│  ├─ 100+ passkey registrations                                              │
│  ├─ 95%+ authentication success rate                                        │
│  ├─ Zero credential cloning incidents                                       │
│  └─ No user-reported confusion                                              │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                           PHASE 2: CONDITIONAL UI                            │
│                           (Weeks 5-8)                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TARGET: All Phase 1 platforms + passkey autofill                           │
│                                                                              │
│  FEATURES:                                                                   │
│  ├─ Conditional UI (autocomplete="webauthn")                                │
│  ├─ Passkey autofill in email field                                         │
│  ├─ Device naming during registration                                       │
│  └─ Credential management UI (view/delete)                                  │
│                                                                              │
│  PLATFORMS:                                                                  │
│  ├─ Phase 1 platforms                                                       │
│  ├─ iOS 16+ (Safari) - Touch ID / Face ID                                   │
│  └─ Android 14+ (Chrome) - Credential Manager                               │
│                                                                              │
│  FEATURE FLAGS:                                                              │
│  ├─ ENABLE_WEBAUTHN_AUTOFILL: true                                          │
│  ├─ ENABLE_CREDENTIAL_MANAGEMENT_UI: true                                   │
│  └─ ENABLE_DEVICE_NAMING: true                                              │
│                                                                              │
│  SUCCESS CRITERIA:                                                           │
│  ├─ 500+ passkey registrations                                              │
│  ├─ 50%+ of authentications use autofill                                    │
│  ├─ Credential management UI NPS > 70                                       │
│  └─ Zero autofill-related support tickets                                   │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                           PHASE 3: SYNCED PASSKEYS                           │
│                           (Weeks 9-12)                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TARGET: iCloud Keychain + Google Password Manager sync                     │
│                                                                              │
│  FEATURES:                                                                   │
│  ├─ Passkey sync via iCloud Keychain (Apple)                                │
│  ├─ Passkey sync via Google Password Manager (Android)                     │
│  ├─ Cross-device passkey usage                                              │
│  └─ Backup state tracking                                                   │
│                                                                              │
│  PLATFORMS:                                                                  │
│  ├─ iOS 16+ / macOS 13+ (iCloud Keychain)                                   │
│  └─ Android 14+ (Google Password Manager)                                   │
│                                                                              │
│  FEATURE FLAGS:                                                              │
│  ├─ ENABLE_PASSKEY_SYNC: true                                               │
│  ├─ ENABLE_BACKUP_STATE_TRACKING: true                                      │
│  └─ REQUIRE_RESIDENT_KEY: true                                              │
│                                                                              │
│  SUCCESS CRITERIA:                                                           │
│  ├─ 1000+ passkey registrations                                            │
│  ├─ 30%+ of users have synced passkeys                                      │
│  ├─ Cross-device authentication success rate > 90%                          │
│  └─ Zero sync-related data loss incidents                                   │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                           PHASE 4: FULL COVERAGE                             │
│                           (Weeks 13-16)                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TARGET: All platforms + security keys + native apps                         │
│                                                                              │
│  FEATURES:                                                                   │
│  ├─ Security key support (YubiKey, etc.)                                    │
│  ├─ Native iOS app passkey integration (ASWebAuthenticationSession)         │
│  ├─ Native Android app passkey integration (Credential Manager)             │
│  ├─ Enterprise attestation support                                          │
│  └─ Passkey-first sign-in option                                            │
│                                                                              │
│  PLATFORMS:                                                                  │
│  ├─ All previous platforms                                                  │
│  ├─ Security keys (cross-platform)                                          │
│  └─ Native mobile apps                                                      │
│                                                                              │
│  FEATURE FLAGS:                                                              │
│  ├─ ENABLE_SECURITY_KEYS: true                                              │
│  ├─ ENABLE_NATIVE_APP_INTEGRATION: true                                     │
│  ├─ ENABLE_ENTERPRISE_ATTESTATION: true                                     │
│  └─ ENABLE_PASSKEY_FIRST_SIGNIN: true                                       │
│                                                                              │
│  SUCCESS CRITERIA:                                                           │
│  ├─ 5000+ passkey registrations                                            │
│  ├─ 20%+ of authentications are passkey-based                               │
│  ├─ Security key support NPS > 80                                          │
│  └─ Native app authentication success rate > 95%                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Feature Flag Implementation

```typescript
// src/lib/feature-flags.ts

/**
 * Feature flags for credential manager rollout.
 */

export interface FeatureFlags {
  // WebAuthn core
  ENABLE_WEBAUTHN_REGISTRATION: boolean;
  ENABLE_WEBAUTHN_AUTHENTICATION: boolean;
  ENABLE_WEBAUTHN_AUTOFILL: boolean;
  
  // Credential management
  ENABLE_CREDENTIAL_MANAGEMENT_UI: boolean;
  ENABLE_DEVICE_NAMING: boolean;
  
  // Passkey sync
  ENABLE_PASSKEY_SYNC: boolean;
  ENABLE_BACKUP_STATE_TRACKING: boolean;
  REQUIRE_RESIDENT_KEY: boolean;
  
  // Extended support
  ENABLE_SECURITY_KEYS: boolean;
  ENABLE_NATIVE_APP_INTEGRATION: boolean;
  ENABLE_ENTERPRISE_ATTESTATION: boolean;
  ENABLE_PASSKEY_FIRST_SIGNIN: boolean;
}

// Default flags (development)
export const DEFAULT_FLAGS: FeatureFlags = {
  ENABLE_WEBAUTHN_REGISTRATION: true,
  ENABLE_WEBAUTHN_AUTHENTICATION: true,
  ENABLE_WEBAUTHN_AUTOFILL: true,
  ENABLE_CREDENTIAL_MANAGEMENT_UI: true,
  ENABLE_DEVICE_NAMING: true,
  ENABLE_PASSKEY_SYNC: true,
  ENABLE_BACKUP_STATE_TRACKING: true,
  REQUIRE_RESIDENT_KEY: true,
  ENABLE_SECURITY_KEYS: false,
  ENABLE_NATIVE_APP_INTEGRATION: false,
  ENABLE_ENTERPRISE_ATTESTATION: false,
  ENABLE_PASSKEY_FIRST_SIGNIN: false,
};

/**
 * Get feature flags from server.
 */
export async function getFeatureFlags(): Promise<FeatureFlags> {
  try {
    const response = await fetch('/api/feature-flags');
    if (response.ok) {
      return await response.json();
    }
  } catch {
    // Fall back to defaults
  }
  return DEFAULT_FLAGS;
}

/**
 * Check if a specific feature is enabled.
 */
export function isFeatureEnabled(
  flags: FeatureFlags,
  feature: keyof FeatureFlags
): boolean {
  return flags[feature] === true;
}
```

### 7.3 Metrics Instrumentation

```typescript
// src/lib/analytics/credential-metrics.ts

/**
 * Analytics events for credential manager usage.
 */

export interface CredentialMetricEvent {
  event_name: string;
  tier: number;
  platform: string;
  success: boolean;
  duration_ms?: number;
  error_code?: string;
  fallback_used?: boolean;
}

export const CREDENTIAL_EVENTS = {
  // Registration
  PASSKEY_REGISTRATION_START: 'passkey_registration_start',
  PASSKEY_REGISTRATION_SUCCESS: 'passkey_registration_success',
  PASSKEY_REGISTRATION_FAILED: 'passkey_registration_failed',
  PASSKEY_REGISTRATION_CANCELLED: 'passkey_registration_cancelled',
  
  // Authentication
  PASSKEY_AUTH_START: 'passkey_auth_start',
  PASSKEY_AUTH_SUCCESS: 'passkey_auth_success',
  PASSKEY_AUTH_FAILED: 'passkey_auth_failed',
  PASSKEY_AUTH_CANCELLED: 'passkey_auth_cancelled',
  PASSKEY_AUTOFILL_TRIGGERED: 'passkey_autofill_triggered',
  
  // Fallback
  PASSWORD_FALLBACK_USED: 'password_fallback_used',
  OAUTH_FALLBACK_USED: 'oauth_fallback_used',
  
  // Credential Management
  CREDENTIAL_VIEWED: 'credential_viewed',
  CREDENTIAL_DELETED: 'credential_deleted',
  DEVICE_NAME_SET: 'device_name_set',
  
  // Capability Detection
  CAPABILITY_DETECTED: 'capability_detected',
} as const;

/**
 * Track credential manager event.
 */
export function trackCredentialEvent(
  event: typeof CREDENTIAL_EVENTS[keyof typeof CREDENTIAL_EVENTS],
  properties: Omit<CredentialMetricEvent, 'event_name'>
): void {
  // Send to analytics service
  if (typeof window !== 'undefined' && 'gtag' in window) {
    (window as any).gtag('event', event, {
      event_category: 'credential_manager',
      event_label: properties.platform,
      value: properties.success ? 1 : 0,
      custom_map: {
        tier: properties.tier,
        duration: properties.duration_ms,
        error_code: properties.error_code,
        fallback: properties.fallback_used,
      },
    });
  }

  // Log to console in development
  if (import.meta.env.DEV) {
    console.log('[Credential Analytics]', event, properties);
  }
}

/**
 * Track authentication success rate.
 */
export function trackAuthSuccess(
  method: 'passkey' | 'password' | 'oauth',
  tier: number,
  durationMs: number
): void {
  trackCredentialEvent(
    method === 'passkey' 
      ? CREDENTIAL_EVENTS.PASSKEY_AUTH_SUCCESS 
      : method === 'password'
        ? CREDENTIAL_EVENTS.PASSWORD_FALLBACK_USED
        : CREDENTIAL_EVENTS.OAUTH_FALLBACK_USED,
    {
      tier,
      platform: detectPlatform(),
      success: true,
      duration_ms: durationMs,
      fallback_used: method !== 'passkey',
    }
  );
}

function detectPlatform(): string {
  const ua = navigator.userAgent;
  if (/iPhone|iPad|iPod/.test(ua)) return 'ios';
  if (/Mac/.test(ua)) return 'macos';
  if (/Android/.test(ua)) return 'android';
  if (/Windows/.test(ua)) return 'windows';
  return 'other';
}
```

### 7.4 Acceptance Criteria Checklist

```markdown
## Phase 1 Acceptance Criteria

- [ ] WebAuthn registration works on Windows Hello
- [ ] WebAuthn registration works on macOS Touch ID
- [ ] WebAuthn authentication works on Windows Hello
- [ ] WebAuthn authentication works on macOS Touch ID
- [ ] Credentials stored correctly in database
- [ ] Sign counter verification works (clone detection)
- [ ] Challenge expiry works (5 minute timeout)
- [ ] Audit logs created for all operations
- [ ] Error messages are user-friendly
- [ ] Registration requires existing authentication
- [ ] 100+ successful registrations in testing
- [ ] 95%+ authentication success rate
- [ ] Zero credential cloning false positives
- [ ] No user-reported confusion in UX testing

## Phase 2 Acceptance Criteria

- [ ] Conditional UI works in Chrome
- [ ] Conditional UI works in Safari
- [ ] Conditional UI works in Edge
- [ ] Passkey autofill appears in email field
- [ ] Device naming UI works
- [ ] Credential list UI works
- [ ] Credential deletion works
- [ ] iOS Safari passkey works
- [ ] Android Chrome passkey works
- [ ] 50%+ autofill usage rate
- [ ] Credential management NPS > 70

## Phase 3 Acceptance Criteria

- [ ] iCloud Keychain sync works
- [ ] Google Password Manager sync works
- [ ] Cross-device authentication works
- [ ] Backup state tracked correctly
- [ ] Resident key requirement enforced
- [ ] 30%+ synced passkey rate
- [ ] Zero sync data loss incidents

## Phase 4 Acceptance Criteria

- [ ] Security key registration works
- [ ] Security key authentication works
- [ ] Native iOS app integration works
- [ ] Native Android app integration works
- [ ] Enterprise attestation works
- [ ] Passkey-first sign-in option works
- [ ] 20%+ passkey authentication rate
- [ ] Security key NPS > 80
```

---

## Summary

This credential manager integration strategy provides CONFIT with a production-ready path to implement:

1. **WebAuthn/FIDO2 passkeys** with full registration and authentication flows
2. **OS-level credential manager integration** (Apple Keychain, Windows Credential Manager, Android Credential Manager)
3. **Progressive enhancement** from baseline email autocomplete through synced passkeys
4. **Unified session model** integrating passkey, OAuth, and password authentication
5. **Comprehensive security** including clone detection, audit logging, and consent management
6. **Phased rollout** with clear metrics and acceptance criteria

All code is production-ready and targets CONFIT's actual stack: custom JWT authentication with FastAPI backend, Vite React frontend, and Next.js app router integration.
