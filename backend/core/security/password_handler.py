"""
CONFIT Backend - Password Handler
=================================
Secure password hashing and validation using bcrypt.
"""

import secrets
import string
import re
from typing import List, Optional, Tuple

import bcrypt

try:
    import argon2
    _HAS_ARGON2 = True
except ImportError:
    _HAS_ARGON2 = False


# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD REQUIREMENTS
# ─────────────────────────────────────────────────────────────────────────────

MIN_PASSWORD_LENGTH = 12  # OWASP 2024 recommendation
MAX_PASSWORD_LENGTH = 128
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_DIGIT = True
REQUIRE_SPECIAL = True
SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"


# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD VALIDATION RESULT
# ─────────────────────────────────────────────────────────────────────────────

class PasswordValidationResult:
    """Result of password validation."""
    
    def __init__(self, valid: bool, errors: List[str] = None):
        self.valid = valid
        self.errors = errors or []
    
    def __bool__(self) -> bool:
        return self.valid


# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD HANDLER
# ─────────────────────────────────────────────────────────────────────────────

class PasswordHandler:
    """Secure password hashing and validation.

    Uses argon2 as the primary hasher (OWASP recommended) with bcrypt
    fallback for legacy hash verification. New hashes are always argon2.
    """

    def __init__(
        self,
        rounds: int = 12,  # bcrypt work factor (10-12 is recommended)
        min_length: int = MIN_PASSWORD_LENGTH,
        max_length: int = MAX_PASSWORD_LENGTH,
        require_uppercase: bool = REQUIRE_UPPERCASE,
        require_lowercase: bool = REQUIRE_LOWERCASE,
        require_digit: bool = REQUIRE_DIGIT,
        require_special: bool = REQUIRE_SPECIAL,
    ):
        self.rounds = rounds
        self.min_length = min_length
        self.max_length = max_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special
        # Argon2 hasher (primary)
        self._argon2 = argon2.PasswordHasher() if _HAS_ARGON2 else None
    
    # ─────────────────────────────────────────────────────────────────────────
    # HASHING
    # ─────────────────────────────────────────────────────────────────────────
    
    def hash_password(self, password: str) -> str:
        """Hash password using argon2 (preferred) or bcrypt (fallback)."""
        if self._argon2:
            return self._argon2.hash(password)
        # Fallback to bcrypt if argon2 not available
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hashed value.

        Supports both argon2 and bcrypt hashes for migration.
        Returns True and sets a flag if the hash needs upgrading (bcrypt → argon2).
        """
        # Try argon2 first
        if hashed.startswith("$argon2") and self._argon2:
            try:
                self._argon2.verify(hashed, password)
                return True
            except argon2.exceptions.VerifyMismatchError:
                return False
            except argon2.exceptions.VerificationError:
                return False
        # Fall back to bcrypt for legacy hashes
        try:
            result = bcrypt.checkpw(
                password.encode("utf-8"),
                hashed.encode("utf-8")
            )
            return result
        except (ValueError, TypeError):
            return False
    
    def needs_rehash(self, hashed: str, new_rounds: Optional[int] = None) -> bool:
        """Check if password hash needs rehashing (e.g., bcrypt → argon2 migration)."""
        # Argon2 hashes never need rehashing to bcrypt
        if hashed.startswith("$argon2") and self._argon2:
            try:
                return self._argon2.check_needs_rehash(hashed)
            except Exception:
                return True
        # Any bcrypt hash needs rehashing to argon2
        if self._argon2:
            return True
        # Pure bcrypt: check rounds
        try:
            parts = hashed.split("$")
            if len(parts) < 4:
                return True
            current_rounds = int(parts[2])
            target_rounds = new_rounds or self.rounds
            return current_rounds != target_rounds
        except (ValueError, IndexError):
            return True
    
    # ─────────────────────────────────────────────────────────────────────────
    # VALIDATION
    # ─────────────────────────────────────────────────────────────────────────
    
    def validate_password(self, password: str) -> PasswordValidationResult:
        """Validate password against security requirements."""
        errors = []
        
        # Length check
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")
        
        if len(password) > self.max_length:
            errors.append(f"Password must not exceed {self.max_length} characters")
        
        # Uppercase check
        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        # Lowercase check
        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        # Digit check
        if self.require_digit and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        # Special character check
        if self.require_special and not any(c in SPECIAL_CHARS for c in password):
            errors.append(f"Password must contain at least one special character ({SPECIAL_CHARS})")
        
        # Common patterns check
        if self._has_common_patterns(password):
            errors.append("Password contains common patterns and is not secure")
        
        return PasswordValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )
    
    def _has_common_patterns(self, password: str) -> bool:
        """Check for common weak patterns."""
        password_lower = password.lower()
        
        # Common passwords
        common_passwords = [
            "password", "123456", "qwerty", "abc123", "monkey",
            "letmein", "trustno1", "dragon", "baseball", "iloveyou",
            "master", "sunshine", "ashley", "bailey", "passw0rd",
        ]
        
        if password_lower in common_passwords:
            return True
        
        # Sequential patterns
        sequences = [
            "0123456789", "abcdefghijklmnopqrstuvwxyz",
            "qwertyuiop", "asdfghjkl", "zxcvbnm",
        ]
        
        for seq in sequences:
            for i in range(len(seq) - 3):
                if seq[i:i+4] in password_lower:
                    return True
                if seq[i:i+4][::-1] in password_lower:
                    return True
        
        # Repeated characters
        if len(set(password)) < 3:
            return True
        
        return False
    
    # ─────────────────────────────────────────────────────────────────────────
    # GENERATION
    # ─────────────────────────────────────────────────────────────────────────
    
    def generate_password(
        self,
        length: int = 16,
        include_uppercase: bool = True,
        include_lowercase: bool = True,
        include_digits: bool = True,
        include_special: bool = True,
    ) -> str:
        """Generate a secure random password."""
        characters = ""
        
        if include_lowercase:
            characters += string.ascii_lowercase
        if include_uppercase:
            characters += string.ascii_uppercase
        if include_digits:
            characters += string.digits
        if include_special:
            characters += SPECIAL_CHARS
        
        if not characters:
            characters = string.ascii_letters + string.digits
        
        # Ensure at least one of each required type
        password = []
        
        if include_lowercase:
            password.append(secrets.choice(string.ascii_lowercase))
        if include_uppercase:
            password.append(secrets.choice(string.ascii_uppercase))
        if include_digits:
            password.append(secrets.choice(string.digits))
        if include_special:
            password.append(secrets.choice(SPECIAL_CHARS))
        
        # Fill remaining length
        remaining_length = length - len(password)
        password.extend(
            secrets.choice(characters) for _ in range(remaining_length)
        )
        
        # Shuffle to avoid predictable positions
        secrets.SystemRandom().shuffle(password)
        
        return "".join(password)
    
    def generate_reset_token(self, length: int = 32) -> str:
        """Generate a secure password reset token."""
        return secrets.token_urlsafe(length)


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL INSTANCE
# ─────────────────────────────────────────────────────────────────────────────

password_handler = PasswordHandler()
