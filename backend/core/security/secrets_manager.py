"""
CONFIT Backend - Secrets Management
===================================
Secure secrets management with environment validation.
"""

import os
import secrets
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from functools import lru_cache


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# SECRET VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SecretConfig:
    """Configuration for a secret."""
    name: str
    required: bool = True
    min_length: int = 16
    pattern: Optional[str] = None
    default: Optional[str] = None
    sensitive: bool = True
    description: str = ""


# Required secrets for production
REQUIRED_SECRETS = [
    SecretConfig(
        name="JWT_SECRET",
        min_length=32,
        description="Secret key for JWT token signing",
    ),
    SecretConfig(
        name="DATABASE_URL",
        min_length=10,
        description="Database connection URL",
    ),
    SecretConfig(
        name="STRIPE_SECRET_KEY",
        required=False,  # Only required for payments
        min_length=20,
        pattern=r"^sk_(live|test)_",
        description="Stripe API secret key",
    ),
    SecretConfig(
        name="STRIPE_WEBHOOK_SECRET",
        required=False,
        min_length=20,
        pattern=r"^whsec_",
        description="Stripe webhook signing secret",
    ),
    SecretConfig(
        name="REDIS_URL",
        required=False,
        description="Redis connection URL",
    ),
    SecretConfig(
        name="ELASTICSEARCH_URL",
        required=False,
        description="Elasticsearch connection URL",
    ),
    SecretConfig(
        name="OPENAI_API_KEY",
        required=False,
        min_length=20,
        pattern=r"^sk-",
        description="OpenAI API key",
    ),
    SecretConfig(
        name="HF_TOKEN",
        required=False,
        min_length=20,
        description="Hugging Face token",
    ),
    SecretConfig(
        name="GROQ_API_KEY",
        required=False,
        min_length=20,
        description="Groq API key",
    ),
    SecretConfig(
        name="OAUTH_GOOGLE_CLIENT_ID",
        required=False,
        description="Google OAuth client ID",
    ),
    SecretConfig(
        name="OAUTH_GOOGLE_CLIENT_SECRET",
        required=False,
        min_length=20,
        description="Google OAuth client secret",
    ),
    SecretConfig(
        name="OAUTH_FACEBOOK_CLIENT_ID",
        required=False,
        description="Facebook OAuth client ID",
    ),
    SecretConfig(
        name="OAUTH_FACEBOOK_CLIENT_SECRET",
        required=False,
        min_length=20,
        description="Facebook OAuth client secret",
    ),
    SecretConfig(
        name="ENCRYPTION_KEY",
        required=False,
        min_length=32,
        description="AES-256 encryption key",
    ),
]


class SecretsManager:
    """
    Secure secrets management.
    
    Features:
    - Environment variable validation
    - Secret rotation support
    - Production secret validation
    - Secure defaults for development
    """
    
    def __init__(self):
        self._secrets: Dict[str, str] = {}
        self._validation_errors: List[str] = []
        self._loaded = False
    
    def load(self, environment: str = "development") -> Dict[str, Any]:
        """
        Load and validate secrets from environment.
        
        Args:
            environment: Current environment (development, production, etc.)
            
        Returns:
            Dictionary of validation results
        """
        self._secrets = {}
        self._validation_errors = []
        
        for config in REQUIRED_SECRETS:
            value = os.getenv(config.name)
            
            # Use default if not set
            if value is None and config.default:
                value = config.default
            
            # Check required
            if value is None:
                if config.required and environment == "production":
                    self._validation_errors.append(
                        f"Required secret {config.name} is not set"
                    )
                continue
            
            # Validate length
            if len(value) < config.min_length:
                self._validation_errors.append(
                    f"Secret {config.name} is too short (min: {config.min_length})"
                )
            
            # Validate pattern
            if config.pattern:
                import re
                if not re.match(config.pattern, value):
                    self._validation_errors.append(
                        f"Secret {config.name} does not match expected pattern"
                    )
            
            # Store secret
            self._secrets[config.name] = value
        
        self._loaded = True
        
        return {
            "valid": len(self._validation_errors) == 0,
            "errors": self._validation_errors,
            "loaded_count": len(self._secrets),
        }
    
    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a secret value.
        
        Args:
            name: Secret name
            default: Default value if not found
            
        Returns:
            Secret value or default
        """
        if not self._loaded:
            self.load()
        
        return self._secrets.get(name, default)
    
    def get_required(self, name: str) -> str:
        """
        Get a required secret, raising error if not found.
        
        Args:
            name: Secret name
            
        Returns:
            Secret value
            
        Raises:
            ValueError: If secret is not found
        """
        value = self.get(name)
        if value is None:
            raise ValueError(f"Required secret {name} is not set")
        return value
    
    def set(self, name: str, value: str) -> None:
        """
        Set a secret value (for runtime configuration).
        
        Args:
            name: Secret name
            value: Secret value
        """
        self._secrets[name] = value
    
    def validate_production(self) -> bool:
        """
        Validate secrets for production environment.
        
        Returns:
            True if all production secrets are valid
        """
        errors = []
        
        # JWT secret must be strong
        jwt_secret = self.get("JWT_SECRET")
        if jwt_secret:
            if len(jwt_secret) < 32:
                errors.append("JWT_SECRET must be at least 32 characters")
            
            # Check for weak secrets
            weak_secrets = [
                "change-me", "secret", "password", "jwt-secret",
                "production", "changeme", "default"
            ]
            if any(weak in jwt_secret.lower() for weak in weak_secrets):
                errors.append("JWT_SECRET appears to be a weak/placeholder value")
        
        # Database must not be SQLite in production
        db_url = self.get("DATABASE_URL", "")
        if db_url.startswith("sqlite"):
            errors.append("SQLite is not recommended for production")
        
        # Stripe must use live keys in production
        stripe_key = self.get("STRIPE_SECRET_KEY")
        if stripe_key and stripe_key.startswith("sk_test_"):
            logger.warning("Using Stripe test keys in production environment")
        
        if errors:
            for error in errors:
                logger.error(f"Production secret validation: {error}")
            return False
        
        return True
    
    def generate_secret(self, length: int = 32) -> str:
        """
        Generate a cryptographically secure secret.
        
        Args:
            length: Length in bytes (will be base64 encoded)
            
        Returns:
            URL-safe secret string
        """
        return secrets.token_urlsafe(length)
    
    def generate_encryption_key(self) -> str:
        """
        Generate an AES-256 encryption key.
        
        Returns:
            Base64-encoded 256-bit key
        """
        import base64
        key = secrets.token_bytes(32)  # 256 bits
        return base64.b64encode(key).decode()
    
    def mask_secret(self, value: str, show_length: int = 4) -> str:
        """
        Mask a secret for logging.
        
        Args:
            value: Secret value
            show_length: Number of characters to show
            
        Returns:
            Masked secret
        """
        if not value:
            return "***"
        
        if len(value) <= show_length * 2:
            return "*" * len(value)
        
        return f"{value[:show_length]}...{value[-show_length:]}"
    
    def audit_secrets(self) -> Dict[str, Any]:
        """
        Audit current secrets configuration.
        
        Returns:
            Audit report
        """
        if not self._loaded:
            self.load()
        
        report = {
            "total_secrets": len(self._secrets),
            "validation_errors": self._validation_errors,
            "secrets": {},
        }
        
        for name, value in self._secrets.items():
            config = next((c for c in REQUIRED_SECRETS if c.name == name), None)
            
            report["secrets"][name] = {
                "set": bool(value),
                "length": len(value) if value else 0,
                "masked_value": self.mask_secret(value) if value else None,
                "valid": len(value) >= (config.min_length if config else 16) if value else False,
                "sensitive": config.sensitive if config else True,
            }
        
        return report


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL INSTANCE
# ─────────────────────────────────────────────────────────────────────────────

secrets_manager = SecretsManager()


# ─────────────────────────────────────────────────────────────────────────────
# DECORATORS
# ─────────────────────────────────────────────────────────────────────────────

def require_secret(name: str):
    """
    Decorator to require a secret before executing function.
    
    Usage:
        @require_secret("STRIPE_SECRET_KEY")
        def process_payment():
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            value = secrets_manager.get(name)
            if not value:
                raise ValueError(f"Required secret {name} is not configured")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────

def init_secrets(environment: str = None) -> bool:
    """
    Initialize secrets manager.
    
    Args:
        environment: Environment name (defaults to ENVIRONMENT env var)
        
    Returns:
        True if secrets are valid
    """
    env = environment or os.getenv("ENVIRONMENT", "development")
    result = secrets_manager.load(env)
    
    if not result["valid"]:
        logger.warning(f"Secrets validation failed: {result['errors']}")
    
    if env == "production":
        if not secrets_manager.validate_production():
            logger.error("Production secrets validation failed!")
            return False
    
    return result["valid"]


# Auto-initialize on import in production
if os.getenv("ENVIRONMENT") == "production":
    init_secrets("production")
