"""
CONFIT Backend — Style DNA Security & Privacy
============================================
Security measures for protecting user style data.
"""

import os
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from core.security.secret_bootstrap import bootstrap_secret

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# ENCRYPTION SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class StyleDNAEncryption:
    """
    Handles encryption/decryption of sensitive style data.
    Uses Fernet (AES-128-CBC) for symmetric encryption.
    """
    
    _instance = None
    _fernet: Optional[Fernet] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._fernet is None:
            self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption with key from environment or generate new one."""
        encryption_key = os.getenv("STYLE_DNA_ENCRYPTION_KEY")
        
        if encryption_key:
            # Use provided key
            self._fernet = Fernet(encryption_key.encode())
            logger.info("Style DNA encryption initialized with provided key")
        else:
            # Generate key from secret - require SECRET_KEY in production
            # Stable across restarts in local dev (bootstrapped + persisted).
            # In production, this will fail fast if SECRET_KEY is missing/weak.
            secret = bootstrap_secret(
                "SECRET_KEY",
                min_length=32,
                placeholder_contains=(
                    "change-me",
                    "default",
                    "secret",
                    "password",
                ),
            )
            salt = b"style_dna_encryption_salt"  # Fixed salt for deterministic key
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
            self._fernet = Fernet(key)
            logger.info("Style DNA encryption initialized with derived key")
    
    def encrypt(self, data: Dict[str, Any]) -> str:
        """
        Encrypt style data dictionary.
        
        Args:
            data: Dictionary to encrypt
        
        Returns:
            Encrypted string
        """
        import json
        
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        
        json_data = json.dumps(data, default=str)
        encrypted = self._fernet.encrypt(json_data.encode())
        
        return encrypted.decode()
    
    def decrypt(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt style data.
        
        Args:
            encrypted_data: Encrypted string
        
        Returns:
            Decrypted dictionary
        """
        import json
        
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        
        try:
            decrypted = self._fernet.decrypt(encrypted_data.encode())
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt style data: {e}")
            return {}
    
    def encrypt_field(self, value: str) -> str:
        """Encrypt a single field value."""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        
        return self._fernet.encrypt(value.encode()).decode()
    
    def decrypt_field(self, encrypted_value: str) -> str:
        """Decrypt a single field value."""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        
        try:
            return self._fernet.decrypt(encrypted_value.encode()).decode()
        except Exception:
            return ""


# ─────────────────────────────────────────────────────────────────────────────
# PRIVACY MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class StyleDNAPrivacyManager:
    """
    Manages privacy settings and data access controls for Style DNA.
    """
    
    # Privacy levels
    PRIVACY_LEVELS = {
        "public": {
            "share_style": True,
            "share_colors": True,
            "share_brands": True,
            "share_budget": False,
            "share_fit": True,
            "allow_similarity_matching": True,
            "allow_clustering": True,
        },
        "friends": {
            "share_style": True,
            "share_colors": True,
            "share_brands": True,
            "share_budget": False,
            "share_fit": True,
            "allow_similarity_matching": True,
            "allow_clustering": True,
        },
        "private": {
            "share_style": False,
            "share_colors": False,
            "share_brands": False,
            "share_budget": False,
            "share_fit": False,
            "allow_similarity_matching": False,
            "allow_clustering": False,
        },
    }
    
    # Sensitive fields that require encryption
    SENSITIVE_FIELDS = [
        "budget_range",
        "encrypted_preferences",
        "browsing_behavior",
        "purchase_patterns",
    ]
    
    def __init__(self):
        self.encryption = StyleDNAEncryption()
    
    def get_privacy_settings(self, level: str) -> Dict[str, bool]:
        """Get privacy settings for a given level."""
        return self.PRIVACY_LEVELS.get(level, self.PRIVACY_LEVELS["private"]).copy()
    
    def filter_profile_for_sharing(
        self,
        profile_data: Dict[str, Any],
        privacy_settings: Dict[str, bool],
        viewer_id: Optional[UUID] = None,
        owner_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Filter profile data based on privacy settings.
        
        Args:
            profile_data: Full profile data
            privacy_settings: Privacy settings to apply
            viewer_id: ID of user viewing the profile
            owner_id: ID of profile owner
        
        Returns:
            Filtered profile data safe for sharing
        """
        filtered = {}
        
        # Always include basic info
        filtered["id"] = profile_data.get("id")
        filtered["user_id"] = profile_data.get("user_id")
        filtered["profile_completeness"] = profile_data.get("profile_completeness")
        filtered["updated_at"] = profile_data.get("updated_at")
        
        # Apply privacy filters
        if privacy_settings.get("share_style"):
            filtered["primary_style"] = profile_data.get("primary_style")
            filtered["secondary_styles"] = profile_data.get("secondary_styles")
            filtered["style_confidence"] = profile_data.get("style_confidence")
        
        if privacy_settings.get("share_colors"):
            filtered["color_preferences"] = profile_data.get("color_preferences")
        
        if privacy_settings.get("share_brands"):
            # Anonymize brand IDs for privacy
            brands = profile_data.get("brand_affinity", [])
            filtered["brand_affinity"] = [
                {"affinity_score": b.get("affinity_score")}
                for b in brands
            ]
        
        if privacy_settings.get("share_budget"):
            # Budget is sensitive - show level only
            filtered["budget_level"] = profile_data.get("budget_level")
        
        if privacy_settings.get("share_fit"):
            filtered["fit_preference"] = profile_data.get("fit_preference")
        
        # Never include sensitive fields
        for field in self.SENSITIVE_FIELDS:
            filtered.pop(field, None)
        
        return filtered
    
    def anonymize_for_analytics(
        self,
        profile_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Anonymize profile data for analytics use.
        
        Removes all personally identifiable information.
        """
        anonymized = {
            "primary_style": profile_data.get("primary_style"),
            "secondary_styles": profile_data.get("secondary_styles"),
            "color_preferences": profile_data.get("color_preferences", {}).get("primary", []),
            "fit_preference": profile_data.get("fit_preference"),
            "budget_level": profile_data.get("budget_level"),
            "profile_completeness": profile_data.get("profile_completeness"),
            "style_confidence": profile_data.get("style_confidence"),
        }
        
        # Hash user ID for tracking without identification
        user_id = profile_data.get("user_id", "unknown")
        anonymized["anonymous_id"] = hashlib.sha256(
            f"style_dna_{user_id}".encode()
        ).hexdigest()[:16]
        
        return anonymized
    
    def should_allow_similarity_matching(
        self,
        user_id: UUID,
        privacy_settings: Dict[str, bool],
    ) -> bool:
        """Check if similarity matching is allowed for user."""
        return privacy_settings.get("allow_similarity_matching", False)
    
    def should_allow_clustering(
        self,
        user_id: UUID,
        privacy_settings: Dict[str, bool],
    ) -> bool:
        """Check if clustering is allowed for user."""
        return privacy_settings.get("allow_clustering", False)


# ─────────────────────────────────────────────────────────────────────────────
# DATA RETENTION MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class StyleDNADataRetention:
    """
    Manages data retention and deletion for Style DNA.
    """
    
    # Retention periods (in days)
    RETENTION_PERIODS = {
        "style_vectors": 365,  # 1 year
        "style_signals": 90,   # 90 days
        "evolution_history": 730,  # 2 years
        "similarity_cache": 1,  # 1 day
        "quiz_responses": 365,  # 1 year
    }
    
    def __init__(self, session):
        self.session = session
    
    async def cleanup_expired_data(self) -> Dict[str, int]:
        """
        Clean up expired Style DNA data.
        
        Returns:
            Dictionary with counts of deleted records per type
        """
        from models.style_dna_models import (
            StyleVector,
            StyleSignal,
            StyleSimilarityCache,
        )
        
        deleted_counts = {}
        now = datetime.now(timezone.utc)
        
        # Clean up expired style signals
        signals_cutoff = now - timedelta(days=self.RETENTION_PERIODS["style_signals"])
        signals_query = """
            DELETE FROM style_signals
            WHERE expires_at < :cutoff
            OR created_at < :cutoff
        """
        result = await self.session.execute(signals_query, {"cutoff": signals_cutoff})
        deleted_counts["style_signals"] = result.rowcount
        
        # Clean up old style vectors (keep latest 10 per user)
        vectors_query = """
            DELETE FROM style_vectors
            WHERE id NOT IN (
                SELECT id FROM style_vectors sv
                WHERE sv.user_id = style_vectors.user_id
                ORDER BY created_at DESC
                LIMIT 10
            )
            AND created_at < :cutoff
        """
        vectors_cutoff = now - timedelta(days=self.RETENTION_PERIODS["style_vectors"])
        result = await self.session.execute(vectors_query, {"cutoff": vectors_cutoff})
        deleted_counts["style_vectors"] = result.rowcount
        
        # Clean up expired similarity cache
        cache_query = """
            DELETE FROM style_similarity_cache
            WHERE expires_at < :now
        """
        result = await self.session.execute(cache_query, {"now": now})
        deleted_counts["similarity_cache"] = result.rowcount
        
        await self.session.commit()
        
        logger.info(f"Cleaned up Style DNA data: {deleted_counts}")
        
        return deleted_counts
    
    async def delete_user_data(self, user_id: UUID) -> Dict[str, int]:
        """
        Delete all Style DNA data for a user (GDPR compliance).
        
        Args:
            user_id: User ID to delete data for
        
        Returns:
            Dictionary with counts of deleted records per table
        """
        deleted_counts = {}
        
        tables = [
            "style_dna_profiles",
            "style_vectors",
            "style_preferences",
            "style_signals",
            "style_evolution_history",
            "user_cluster_assignments",
            "style_quiz_responses",
        ]
        
        for table in tables:
            query = f"""
                DELETE FROM {table}
                WHERE user_id = :user_id
            """
            result = await self.session.execute(query, {"user_id": str(user_id)})
            deleted_counts[table] = result.rowcount
        
        # Delete from similarity cache (both user_id_1 and user_id_2)
        cache_query = """
            DELETE FROM style_similarity_cache
            WHERE user_id_1 = :user_id OR user_id_2 = :user_id
        """
        result = await self.session.execute(cache_query, {"user_id": str(user_id)})
        deleted_counts["style_similarity_cache"] = result.rowcount
        
        await self.session.commit()
        
        logger.info(f"Deleted Style DNA data for user {user_id}: {deleted_counts}")
        
        return deleted_counts
    
    async def export_user_data(self, user_id: UUID) -> Dict[str, Any]:
        """
        Export all Style DNA data for a user (GDPR compliance).
        
        Args:
            user_id: User ID to export data for
        
        Returns:
            Dictionary containing all user's Style DNA data
        """
        from models.style_dna_models import (
            StyleDNAProfile,
            StyleVector,
            StylePreference,
            StyleSignal,
            StyleEvolutionHistory,
            StyleQuizResponse,
        )
        
        export_data = {"user_id": str(user_id), "exported_at": datetime.now(timezone.utc).isoformat()}
        
        # Export profile
        profile_query = """
            SELECT * FROM style_dna_profiles WHERE user_id = :user_id
        """
        result = await self.session.execute(profile_query, {"user_id": str(user_id)})
        rows = result.fetchall()
        if rows:
            export_data["profile"] = [dict(row) for row in rows]
        
        # Export vectors
        vectors_query = """
            SELECT id, vector_type, confidence_score, created_at
            FROM style_vectors WHERE user_id = :user_id
            ORDER BY created_at DESC
        """
        result = await self.session.execute(vectors_query, {"user_id": str(user_id)})
        rows = result.fetchall()
        if rows:
            export_data["vectors"] = [dict(row) for row in rows]
        
        # Export preferences
        prefs_query = """
            SELECT * FROM style_preferences WHERE user_id = :user_id
        """
        result = await self.session.execute(prefs_query, {"user_id": str(user_id)})
        rows = result.fetchall()
        if rows:
            export_data["preferences"] = [dict(row) for row in rows]
        
        # Export evolution history
        evolution_query = """
            SELECT * FROM style_evolution_history WHERE user_id = :user_id
            ORDER BY created_at DESC
        """
        result = await self.session.execute(evolution_query, {"user_id": str(user_id)})
        rows = result.fetchall()
        if rows:
            export_data["evolution_history"] = [dict(row) for row in rows]
        
        # Export quiz responses
        quiz_query = """
            SELECT * FROM style_quiz_responses WHERE user_id = :user_id
            ORDER BY completed_at DESC
        """
        result = await self.session.execute(quiz_query, {"user_id": str(user_id)})
        rows = result.fetchall()
        if rows:
            export_data["quiz_responses"] = [dict(row) for row in rows]
        
        return export_data


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT LOGGING
# ─────────────────────────────────────────────────────────────────────────────

class StyleDNAAuditLogger:
    """
    Audit logging for Style DNA data access and modifications.
    """
    
    def __init__(self, session=None):
        self.session = session
    
    async def log_access(
        self,
        user_id: UUID,
        accessor_id: Optional[UUID],
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Log an access event for Style DNA data.
        
        Args:
            user_id: User whose data was accessed
            accessor_id: User who accessed the data (None for system)
            action: Action performed (read, update, delete, export)
            resource_type: Type of resource (profile, vector, signal)
            resource_id: Specific resource ID
            details: Additional details
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": str(user_id),
            "accessor_id": str(accessor_id) if accessor_id else "system",
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
        }
        
        logger.info(f"STYLE_DNA_AUDIT: {log_entry}")
        
        # In production, this would write to a dedicated audit table
        # await self._write_audit_log(log_entry)
    
    async def log_modification(
        self,
        user_id: UUID,
        modifier_id: Optional[UUID],
        modification_type: str,
        previous_value: Optional[Any],
        new_value: Any,
        reason: Optional[str] = None,
    ):
        """
        Log a modification event for Style DNA data.
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": str(user_id),
            "modifier_id": str(modifier_id) if modifier_id else "system",
            "modification_type": modification_type,
            "previous_value": previous_value,
            "new_value": new_value,
            "reason": reason,
        }
        
        logger.info(f"STYLE_DNA_MODIFICATION: {log_entry}")


# ─────────────────────────────────────────────────────────────────────────────
# SECURITY VALIDATORS
# ─────────────────────────────────────────────────────────────────────────────

class StyleDNAValidators:
    """
    Input validation for Style DNA data.
    """
    
    VALID_STYLE_CATEGORIES = {
        "classic", "trendy", "minimalist", "maximalist",
        "feminine", "masculine", "edgy", "romantic",
        "bohemian", "preppy", "sporty", "avant_garde",
        "streetwear", "vintage", "luxury", "casual",
    }
    
    VALID_BUDGET_LEVELS = {
        "budget_conscious", "moderate", "premium", "luxury", "ultra_luxury",
    }
    
    VALID_FIT_PREFERENCES = {
        "tight", "slim", "regular", "relaxed", "oversized", "loose",
    }
    
    VALID_OCCASIONS = {
        "everyday", "work", "formal", "casual", "date_night",
        "weekend", "vacation", "party", "athletic", "special_event",
    }
    
    MAX_SECONDARY_STYLES = 5
    MAX_PRIMARY_COLORS = 10
    MAX_BRAND_AFFINITIES = 20
    
    @classmethod
    def validate_style_category(cls, style: str) -> bool:
        """Validate style category."""
        return style.lower() in cls.VALID_STYLE_CATEGORIES
    
    @classmethod
    def validate_budget_level(cls, level: str) -> bool:
        """Validate budget level."""
        return level.lower() in cls.VALID_BUDGET_LEVELS
    
    @classmethod
    def validate_fit_preference(cls, fit: str) -> bool:
        """Validate fit preference."""
        return fit.lower() in cls.VALID_FIT_PREFERENCES
    
    @classmethod
    def validate_occasion_preferences(cls, occasions: Dict[str, float]) -> Dict[str, List[str]]:
        """Validate occasion preferences."""
        errors = []
        
        for occasion, weight in occasions.items():
            if occasion.lower() not in cls.VALID_OCCASIONS:
                errors.append(f"Invalid occasion: {occasion}")
            if not 0 <= weight <= 1:
                errors.append(f"Invalid weight for {occasion}: {weight}")
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    @classmethod
    def validate_color_preferences(cls, colors: Dict[str, List[str]]) -> Dict[str, Any]:
        """Validate color preferences."""
        errors = []
        warnings = []
        
        primary = colors.get("primary", [])
        if len(primary) > cls.MAX_PRIMARY_COLORS:
            warnings.append(f"Too many primary colors ({len(primary)}), max is {cls.MAX_PRIMARY_COLORS}")
        
        # Check for invalid color names
        valid_color_pattern = r"^[a-zA-Z\s\-]+$"
        import re
        
        for color in primary:
            if not re.match(valid_color_pattern, color):
                errors.append(f"Invalid color name: {color}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    @classmethod
    def validate_brand_affinity(cls, brands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate brand affinity list."""
        errors = []
        warnings = []
        
        if len(brands) > cls.MAX_BRAND_AFFINITIES:
            warnings.append(f"Too many brand affinities ({len(brands)}), max is {cls.MAX_BRAND_AFFINITIES}")
        
        for brand in brands:
            if "brand_id" not in brand:
                errors.append("Brand missing brand_id")
            
            score = brand.get("affinity_score", 0)
            if not 0 <= score <= 1:
                errors.append(f"Invalid affinity score: {score}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    @classmethod
    def validate_profile_update(cls, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete profile update."""
        all_errors = []
        all_warnings = []
        
        # Validate style categories
        if "primary_style" in update_data:
            if not cls.validate_style_category(update_data["primary_style"]):
                all_errors.append(f"Invalid primary_style: {update_data['primary_style']}")
        
        if "secondary_styles" in update_data:
            styles = update_data["secondary_styles"]
            if len(styles) > cls.MAX_SECONDARY_STYLES:
                all_warnings.append(f"Too many secondary styles")
            for style in styles:
                if not cls.validate_style_category(style):
                    all_errors.append(f"Invalid secondary style: {style}")
        
        # Validate budget level
        if "budget_level" in update_data:
            if not cls.validate_budget_level(update_data["budget_level"]):
                all_errors.append(f"Invalid budget_level: {update_data['budget_level']}")
        
        # Validate fit preference
        if "fit_preference" in update_data:
            if not cls.validate_fit_preference(update_data["fit_preference"]):
                all_errors.append(f"Invalid fit_preference: {update_data['fit_preference']}")
        
        # Validate occasion preferences
        if "occasion_preferences" in update_data:
            result = cls.validate_occasion_preferences(update_data["occasion_preferences"])
            all_errors.extend(result.get("errors", []))
        
        # Validate color preferences
        if "color_preferences" in update_data:
            result = cls.validate_color_preferences(update_data["color_preferences"])
            all_errors.extend(result.get("errors", []))
            all_warnings.extend(result.get("warnings", []))
        
        # Validate brand affinity
        if "brand_affinity" in update_data:
            result = cls.validate_brand_affinity(update_data["brand_affinity"])
            all_errors.extend(result.get("errors", []))
            all_warnings.extend(result.get("warnings", []))
        
        return {
            "valid": len(all_errors) == 0,
            "errors": all_errors,
            "warnings": all_warnings,
        }


# ─────────────────────────────────────────────────────────────────────────────
# FACTORY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_encryption() -> StyleDNAEncryption:
    """Get encryption service instance."""
    return StyleDNAEncryption()


def get_privacy_manager() -> StyleDNAPrivacyManager:
    """Get privacy manager instance."""
    return StyleDNAPrivacyManager()


def get_data_retention(session) -> StyleDNADataRetention:
    """Get data retention manager instance."""
    return StyleDNADataRetention(session)


def get_audit_logger(session=None) -> StyleDNAAuditLogger:
    """Get audit logger instance."""
    return StyleDNAAuditLogger(session)
