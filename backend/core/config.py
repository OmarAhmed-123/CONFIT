"""CONFIT Backend — Centralized Configuration."""

import os
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Application settings loaded from environment."""
    
    # Environment
    ENVIRONMENT: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    DEBUG: bool = field(default_factory=lambda: os.getenv("DEBUG", "true").lower() == "true")
    
    # Server
    HOST: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    PORT: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    
    # Database
    DATABASE_URL: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./confit.db"))
    
    # Security
    JWT_SECRET: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "change-me-in-production-min-32-chars"))
    JWT_ALGORITHM: str = field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    JWT_EXPIRY_HOURS: int = field(default_factory=lambda: int(os.getenv("JWT_EXPIRY_HOURS", "24")))

    def __post_init__(self) -> None:
        if self.ENVIRONMENT.lower() == "production" and len(self.JWT_SECRET) < 32:
            raise RuntimeError(
                "JWT_SECRET must be at least 32 characters in production. "
                "Set a strong JWT_SECRET environment variable before starting the server."
            )
    
    # CORS
    FRONTEND_URL: str = field(default_factory=lambda: os.getenv("FRONTEND_URL", "http://localhost:5173"))
    ALLOWED_ORIGINS: List[str] = field(default_factory=list)
    
    # External APIs
    HF_TOKEN: Optional[str] = field(default_factory=lambda: os.getenv("HF_TOKEN"))
    GROQ_API_KEY: Optional[str] = field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    OPENAI_API_KEY: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_KEY")
    )
    
    # Feature Flags
    ENABLE_RATE_LIMITING: bool = field(default_factory=lambda: os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true")
    ENABLE_AI_FEATURES: bool = field(default_factory=lambda: os.getenv("ENABLE_AI_FEATURES", "true").lower() == "true")
    ENABLE_TRY_ON: bool = field(default_factory=lambda: os.getenv("ENABLE_TRY_ON", "true").lower() == "true")
    
    # Rate Limits
    RATE_LIMIT_DEFAULT: str = field(default_factory=lambda: os.getenv("RATE_LIMIT_DEFAULT", "60/minute"))
    RATE_LIMIT_TRY_ON: str = field(default_factory=lambda: os.getenv("RATE_LIMIT_TRY_ON", "10/minute"))
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def cors_origins(self) -> List[str]:
        origins = [self.FRONTEND_URL]
        if self.ALLOWED_ORIGINS:
            origins.extend(self.ALLOWED_ORIGINS)
        # Never return ["*"] — wildcards with credentials=true are rejected by browsers
        # and constitute a security misconfiguration (A05: Security Misconfiguration)
        if not self.is_production:
            origins.extend([
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:5174",
                "http://localhost:8080",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:8080",
            ])
        return origins


settings = Settings()
