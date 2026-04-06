"""
CONFIT Backend — Configuration Management
========================================
Centralized configuration with environment-based switching.

Features:
- Environment-based configuration loading
- Safe defaults for development
- Validation of critical settings
- GPU mode detection
"""

import os
import logging
from typing import Optional, List
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Application configuration."""
    # Core settings
    debug: bool = False
    log_level: str = "info"
    secret_key: str = "change-me-in-production"
    
    # Inference mode
    inference_mode: str = "mock"  # "mock" or "gpu"
    
    # Mock settings
    mock_delay_min: float = 2.0
    mock_delay_max: float = 5.0
    mock_quality_min: float = 0.70
    mock_quality_max: float = 0.95
    
    # Database
    database_url: str = "sqlite:///./confit.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False
    
    # CORS
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:5173"])
    cors_allow_credentials: bool = True
    
    # File storage
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 10
    
    # GPU settings (only used when inference_mode=gpu)
    cuda_visible_devices: str = "0"
    gpu_memory_fraction: float = 0.8
    model_weights_path: str = "./weights"
    
    # External services
    huggingface_token: Optional[str] = None
    huggingface_fallback_enabled: bool = False


def load_config(env_file: Optional[str] = None) -> AppConfig:
    """
    Load configuration from environment.
    
    Args:
        env_file: Optional path to .env file
        
    Returns:
        AppConfig with loaded settings
    """
    # Load from .env file if provided
    if env_file and Path(env_file).exists():
        _load_env_file(env_file)
    
    # Build config from environment
    config = AppConfig(
        debug=_get_bool("DEBUG", False),
        log_level=_get_str("LOG_LEVEL", "info"),
        secret_key=_get_str("SECRET_KEY", "change-me-in-production"),
        
        inference_mode=_get_str("INFERENCE_MODE", "mock").lower(),
        
        mock_delay_min=_get_float("MOCK_DELAY_MIN", 2.0),
        mock_delay_max=_get_float("MOCK_DELAY_MAX", 5.0),
        mock_quality_min=_get_float("MOCK_QUALITY_SCORE_MIN", 0.70),
        mock_quality_max=_get_float("MOCK_QUALITY_SCORE_MAX", 0.95),
        
        database_url=_get_str("DATABASE_URL", "sqlite:///./confit.db"),
        
        redis_url=_get_str("REDIS_URL", "redis://localhost:6379/0"),
        redis_enabled=_get_bool("REDIS_ENABLED", False),
        
        cors_origins=_get_list("CORS_ORIGINS", ["http://localhost:5173"]),
        cors_allow_credentials=_get_bool("CORS_ALLOW_CREDENTIALS", True),
        
        upload_dir=_get_str("UPLOAD_DIR", "./uploads"),
        max_upload_size_mb=_get_int("MAX_UPLOAD_SIZE_MB", 10),
        
        cuda_visible_devices=_get_str("CUDA_VISIBLE_DEVICES", "0"),
        gpu_memory_fraction=_get_float("GPU_MEMORY_FRACTION", 0.8),
        model_weights_path=_get_str("MODEL_WEIGHTS_PATH", "./weights"),
        
        huggingface_token=_get_str("HUGGINGFACE_TOKEN", None),
        huggingface_fallback_enabled=_get_bool("HUGGINGFACE_FALLBACK_ENABLED", False),
    )
    
    # Validate configuration
    _validate_config(config)
    
    # Log configuration
    _log_config(config)
    
    return config


def _load_env_file(env_file: str):
    """Load environment variables from .env file."""
    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, _, value = line.partition('=')
                    if key and value:
                        # Remove quotes if present
                        value = value.strip('"').strip("'")
                        os.environ.setdefault(key.strip(), value)
    except Exception as e:
        logger.warning(f"Failed to load env file {env_file}: {e}")


def _get_str(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get string from environment."""
    return os.getenv(key, default)


def _get_int(key: str, default: int) -> int:
    """Get integer from environment."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _get_float(key: str, default: float) -> float:
    """Get float from environment."""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def _get_bool(key: str, default: bool) -> bool:
    """Get boolean from environment."""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')


def _get_list(key: str, default: List[str]) -> List[str]:
    """Get list from environment (comma-separated)."""
    value = os.getenv(key)
    if value:
        return [item.strip() for item in value.split(',')]
    return default


def _validate_config(config: AppConfig):
    """Validate configuration settings."""
    errors = []
    
    # Validate inference mode
    if config.inference_mode not in ('mock', 'gpu'):
        errors.append(f"Invalid INFERENCE_MODE: {config.inference_mode}. Must be 'mock' or 'gpu'.")
    
    # Validate GPU settings if GPU mode
    if config.inference_mode == 'gpu':
        # Check CUDA availability
        try:
            import torch
            if not torch.cuda.is_available():
                errors.append("INFERENCE_MODE=gpu but CUDA is not available. Falling back to mock.")
                config.inference_mode = 'mock'
        except ImportError:
            errors.append("INFERENCE_MODE=gpu but PyTorch is not installed. Falling back to mock.")
            config.inference_mode = 'mock'
    
    # Validate mock delays
    if config.mock_delay_min > config.mock_delay_max:
        errors.append(f"MOCK_DELAY_MIN ({config.mock_delay_min}) > MOCK_DELAY_MAX ({config.mock_delay_max})")
    
    # Validate quality scores
    if not 0 <= config.mock_quality_min <= 1:
        errors.append(f"MOCK_QUALITY_SCORE_MIN must be between 0 and 1, got {config.mock_quality_min}")
    if not 0 <= config.mock_quality_max <= 1:
        errors.append(f"MOCK_QUALITY_SCORE_MAX must be between 0 and 1, got {config.mock_quality_max}")
    
    # Validate secret key in production
    if not config.debug and config.secret_key == "change-me-in-production":
        errors.append("SECRET_KEY must be changed in production mode")
    
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        if config.inference_mode == 'gpu':
            logger.warning("GPU mode validation failed, falling back to mock mode")
            config.inference_mode = 'mock'


def _log_config(config: AppConfig):
    """Log configuration (without sensitive data)."""
    logger.info("=" * 50)
    logger.info("CONFIT Configuration")
    logger.info("=" * 50)
    logger.info(f"Inference Mode: {config.inference_mode.upper()}")
    logger.info(f"Debug: {config.debug}")
    logger.info(f"Log Level: {config.log_level}")
    logger.info(f"Database: {'***' if 'postgresql' in config.database_url else config.database_url}")
    logger.info(f"Redis: {'enabled' if config.redis_enabled else 'disabled'}")
    
    if config.inference_mode == 'mock':
        logger.info(f"Mock Delay: {config.mock_delay_min}-{config.mock_delay_max}s")
        logger.info(f"Mock Quality: {config.mock_quality_min}-{config.mock_quality_max}")
    else:
        logger.info(f"CUDA Devices: {config.cuda_visible_devices}")
        logger.info(f"GPU Memory Fraction: {config.gpu_memory_fraction}")
        logger.info(f"Model Weights: {config.model_weights_path}")
    
    logger.info("=" * 50)


# Global config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        env_file = os.getenv('ENV_FILE', 'configs/dev.env')
        _config = load_config(env_file)
    return _config


def reload_config(env_file: Optional[str] = None):
    """Reload configuration from environment."""
    global _config
    _config = load_config(env_file)
    return _config
