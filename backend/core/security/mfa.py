"""
CONFIT Backend - Multi-Factor Authentication (MFA)
===================================================
TOTP-based MFA for admin and brand_owner roles using pyotp.
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Optional, Tuple

try:
    import pyotp
    import qrcode
    HAS_MFA = True
except ImportError:
    HAS_MFA = False

logger = logging.getLogger(__name__)


# MFA is required for these roles
MFA_REQUIRED_ROLES = {"admin", "brand_owner"}


def is_mfa_required(role: str) -> bool:
    """Check if MFA is required for the given role."""
    return role in MFA_REQUIRED_ROLES


def generate_totp_secret() -> str:
    """Generate a new TOTP secret (base32 encoded)."""
    if not HAS_MFA:
        raise RuntimeError("pyotp not installed — cannot generate TOTP secret")
    return pyotp.random_base32()


def get_totp(secret: str) -> pyotp.TOTP:
    """Get a TOTP instance for the given secret."""
    return pyotp.TOTP(secret, digits=6, interval=30)


def verify_totp(secret: str, code: str, valid_window: int = 1) -> bool:
    """
    Verify a TOTP code against the secret.

    Args:
        secret: Base32-encoded TOTP secret
        code: 6-digit code from authenticator app
        valid_window: Number of intervals to check before/after (default 1 for clock drift)

    Returns:
        True if the code is valid
    """
    if not HAS_MFA:
        logger.warning("pyotp not installed — MFA verification skipped")
        return False
    totp = get_totp(secret)
    return totp.verify(code, valid_window=valid_window)


def generate_provisioning_uri(
    secret: str,
    email: str,
    issuer: str = "CONFIT",
) -> str:
    """Generate the otpauth:// URI for QR code provisioning."""
    totp = get_totp(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def generate_qr_code_base64(uri: str) -> str:
    """Generate a QR code as a base64-encoded PNG image."""
    if not HAS_MFA:
        raise RuntimeError("qrcode not installed — cannot generate QR code")
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def generate_backup_codes(count: int = 10) -> list[str]:
    """Generate one-time backup codes for account recovery."""
    import secrets
    return [secrets.token_hex(4).upper() for _ in range(count)]


__all__ = [
    "HAS_MFA",
    "MFA_REQUIRED_ROLES",
    "is_mfa_required",
    "generate_totp_secret",
    "verify_totp",
    "generate_provisioning_uri",
    "generate_qr_code_base64",
    "generate_backup_codes",
]
