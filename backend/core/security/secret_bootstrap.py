"""
CONFIT Backend — Secret Bootstrapping
======================================
Bootstraps missing/weak secrets for local development in a persistent way.

This avoids "ephemeral random key per process" behavior and removes noisy
startup warnings while still keeping production strict.
"""

from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger(__name__)


def _environment() -> str:
    # Project historically used both ENV and ENVIRONMENT.
    return (os.getenv("ENV") or os.getenv("ENVIRONMENT") or "development").strip().lower()


def _looks_like_placeholder(value: str, placeholder_contains: Iterable[str]) -> bool:
    v = value.lower()
    for token in placeholder_contains:
        if token and token.lower() in v:
            return True
    return False


def bootstrap_secret(
    secret_env_var: str,
    *,
    min_length: int,
    placeholder_contains: Optional[Iterable[str]] = None,
    file_name: Optional[str] = None,
    token_bytes: int = 48,
) -> str:
    """
    Return a strong secret for the given env var.

    Production:
      - requires a strong non-placeholder env value.
    Development / non-production:
      - if env is missing/weak, generate once and persist to a local file.
    """
    placeholder_contains = tuple(placeholder_contains or ())
    env = _environment()

    current = (os.getenv(secret_env_var) or "").strip()
    if current and len(current) >= min_length and not _looks_like_placeholder(current, placeholder_contains):
        return current

    if env == "production":
        raise RuntimeError(
            f"{secret_env_var} is missing/too short/placeholder. In production you must set it in .env."
        )

    # Persist generated secret to disk so token/cipher remain stable across restarts.
    backend_root = Path(__file__).resolve().parents[2]  # .../backend
    secrets_dir = Path(os.getenv("CONFIT_SECRETS_DIR") or (backend_root / ".generated_secrets"))
    secrets_dir.mkdir(parents=True, exist_ok=True)

    name = file_name or f"{secret_env_var}.txt"
    secret_path = secrets_dir / name
    if secret_path.exists():
        stored = secret_path.read_text(encoding="utf-8").strip()
        if stored and len(stored) >= min_length:
            return stored

    generated = secrets.token_urlsafe(token_bytes)
    # Never log the secret itself; only length for debugging.
    secret_path.write_text(generated, encoding="utf-8")
    logger.info(
        "%s bootstrapped for local development (stored to %s, len=%d).",
        secret_env_var,
        secret_path,
        len(generated),
    )
    return generated

