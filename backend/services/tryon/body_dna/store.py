"""
Encrypted at-rest storage for Body DNA (per user). Uses same Fernet stack as Style DNA.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from services.style_dna_security import get_encryption

logger = logging.getLogger(__name__)


def _user_file_id(user_id: str) -> str:
    h = hashlib.sha256(f"body_dna:{user_id}".encode()).hexdigest()
    return h[:32]


class BodyDNAStore:
    """Persist encrypted body_profile dict; never stores raw images."""

    def __init__(self, base_path: Optional[str] = None) -> None:
        root = base_path or os.getenv("BODY_DNA_STORAGE_PATH") or os.path.join(
            os.getcwd(), "data", "body_dna"
        )
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._enc = get_encryption()

    def _path(self, user_id: str) -> Path:
        return self._root / f"{_user_file_id(user_id)}.enc"

    def exists(self, user_id: str) -> bool:
        return self._path(user_id).is_file()

    def save(self, user_id: str, profile: Dict[str, Any]) -> None:
        payload = {"user_id": user_id, "profile": profile}
        enc = self._enc.encrypt(payload)
        p = self._path(user_id)
        p.write_text(enc, encoding="utf-8")
        logger.info("Body DNA stored for user hash prefix %s", _user_file_id(user_id)[:8])

    def load(self, user_id: str) -> Optional[Dict[str, Any]]:
        p = self._path(user_id)
        if not p.is_file():
            return None
        try:
            raw = p.read_text(encoding="utf-8")
            data = self._enc.decrypt(raw)
            prof = data.get("profile")
            if isinstance(prof, dict):
                return prof
        except Exception as e:
            logger.error("Body DNA load failed: %s", e)
        return None

    def delete(self, user_id: str) -> bool:
        p = self._path(user_id)
        if p.is_file():
            try:
                p.unlink()
                return True
            except OSError as e:
                logger.warning("Body DNA delete failed: %s", e)
        return False
