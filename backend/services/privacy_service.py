"""
CONFIT Backend — Privacy Service
================================
GDPR compliance and data management.
"""

import logging
import json
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from database.session import get_db
from sqlalchemy import func

from models.profile_models import (
    UserConsentHistory,
    UserDataExportRequest,
    UserDeletionRequest,
    UserProfileAuditLog,
    UserStyleProfile,
    UserBodyProfile,
    UserBudgetProfile,
    UserBrandAffinity,
    UserContextualPreference,
    UserConfidenceProfile,
    UserConfidenceHistory,
    UserBehaviorSignal,
    UserStyleEvolution,
    UserOnboardingSession,
    ConsentUpdate,
    ConsentHistoryResponse,
    DataExportResponse,
    DeletionRequest,
    DeletionConfirm,
)
from database.models import User

logger = logging.getLogger(__name__)


CONSENT_VERSION = 1

CONSENT_TYPES = {
    "marketing_email": {"required": False, "default": False},
    "marketing_sms": {"required": False, "default": False},
    "data_sharing_partners": {"required": False, "default": False},
    "ai_training": {"required": False, "default": False},
    "personalization": {"required": False, "default": True},
    "analytics": {"required": False, "default": True},
    "third_party_integrations": {"required": False, "default": False},
}

DATA_RETENTION_DAYS = {
    "standard": 365,
    "minimal": 90,
    "aggressive": 30,
}


class PrivacyService:
    """Service for GDPR compliance and privacy management."""
    
    def __init__(self, db: Session):
        self._db = db
    
    def get_consents(self, user_id: str) -> Dict[str, Any]:
        history = self._db.query(UserConsentHistory).filter_by(user_id=user_id).order_by(
            UserConsentHistory.created_at.desc()
        ).all()
        
        consents = {}
        for consent_type, config in CONSENT_TYPES.items():
            consents[consent_type] = {
                "granted": config["default"],
                "required": config["required"],
                "timestamp": None,
            }
        
        for h in history:
            if h.consent_type not in consents or consents[h.consent_type]["timestamp"] is None:
                consents[h.consent_type] = {
                    "granted": h.granted,
                    "required": CONSENT_TYPES.get(h.consent_type, {}).get("required", False),
                    "timestamp": h.created_at.isoformat(),
                }
        
        return consents
    
    def update_consent(
        self,
        user_id: str,
        consent_type: str,
        granted: bool,
        ip_address: str = None,
        user_agent: str = None,
    ) -> ConsentHistoryResponse:
        if consent_type not in CONSENT_TYPES:
            raise ValueError(f"Invalid consent type: {consent_type}")
        
        history = UserConsentHistory(
            user_id=user_id,
            consent_type=consent_type,
            granted=granted,
            consent_version=CONSENT_VERSION,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        self._db.add(history)
        self._db.commit()
        self._db.refresh(history)
        
        return ConsentHistoryResponse(
            id=str(history.id),
            user_id=str(history.user_id),
            consent_type=history.consent_type,
            granted=history.granted,
            consent_version=history.consent_version,
            created_at=history.created_at,
        )
    
    def get_consent_history(self, user_id: str, limit: int = 50) -> List[ConsentHistoryResponse]:
        history = self._db.query(UserConsentHistory).filter_by(user_id=user_id).order_by(
            UserConsentHistory.created_at.desc()
        ).limit(limit).all()
        
        return [
            ConsentHistoryResponse(
                id=str(h.id),
                user_id=str(h.user_id),
                consent_type=h.consent_type,
                granted=h.granted,
                consent_version=h.consent_version,
                created_at=h.created_at,
            )
            for h in history
        ]
    
    def request_data_export(
        self,
        user_id: str,
        format: str = "json",
    ) -> DataExportResponse:
        existing_pending = self._db.query(UserDataExportRequest).filter_by(
            user_id=user_id,
            status="pending"
        ).first()
        
        if existing_pending:
            return DataExportResponse(
                id=str(existing_pending.id),
                user_id=str(existing_pending.user_id),
                status=existing_pending.status,
                format=existing_pending.format,
                requested_at=existing_pending.requested_at,
                completed_at=existing_pending.completed_at,
                download_url=existing_pending.download_url,
                expires_at=existing_pending.expires_at,
            )
        
        export_request = UserDataExportRequest(
            user_id=user_id,
            status="pending",
            format=format,
        )
        
        self._db.add(export_request)
        self._db.commit()
        self._db.refresh(export_request)
        
        self._execute_export(export_request.id)
        
        return DataExportResponse(
            id=str(export_request.id),
            user_id=str(export_request.user_id),
            status=export_request.status,
            format=export_request.format,
            requested_at=export_request.requested_at,
            completed_at=export_request.completed_at,
            download_url=export_request.download_url,
            expires_at=export_request.expires_at,
        )
    
    def _execute_export(self, export_id: str) -> None:
        export_request = self._db.query(UserDataExportRequest).get(export_id)
        if not export_request:
            return
        
        user_id = str(export_request.user_id)
        
        try:
            export_data = self._collect_user_data(user_id)
            
            export_request.status = "completed"
            export_request.completed_at = datetime.now(timezone.utc)
            export_request.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            export_request.download_url = f"/api/privacy/export/{export_id}/download"
            
            export_request.export_data = export_data
            
            self._db.commit()
            
        except Exception as e:
            logger.error(f"Export failed for user {user_id}: {e}")
            export_request.status = "failed"
            export_request.error_message = str(e)
            self._db.commit()
    
    def _collect_user_data(self, user_id: str) -> Dict[str, Any]:
        data = {
            "export_metadata": {
                "user_id": user_id,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "format_version": "1.0",
                "jurisdiction": "GDPR",
            }
        }
        
        user = self._db.query(User).filter_by(id=user_id).first()
        if user:
            data["user"] = {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "phone": user.phone,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
        
        style = self._db.query(UserStyleProfile).filter_by(user_id=user_id).first()
        if style:
            data["style_profile"] = {
                "primary_archetype": style.primary_archetype,
                "secondary_archetypes": style.secondary_archetypes,
                "style_dimensions": {
                    "classic": float(style.style_classic or 0.5),
                    "trendy": float(style.style_trendy or 0.5),
                    "minimalist": float(style.style_minimalist or 0.5),
                    "maximalist": float(style.style_maximalist or 0.5),
                    "feminine": float(style.style_feminine or 0.5),
                    "masculine": float(style.style_masculine or 0.5),
                    "edgy": float(style.style_edgy or 0.5),
                    "romantic": float(style.style_romantic or 0.5),
                },
                "preferred_colors": style.preferred_colors,
                "avoided_colors": style.avoided_colors,
                "created_at": style.created_at.isoformat(),
            }
        
        body = self._db.query(UserBodyProfile).filter_by(user_id=user_id).first()
        if body and body.profile_status != "not_set":
            data["body_profile"] = {
                "height_cm": body.height_cm,
                "weight_kg": body.weight_kg,
                "body_shape": body.body_shape,
                "sizes": {
                    "tops": body.size_tops,
                    "bottoms": body.size_bottoms,
                    "dresses": body.size_dresses,
                    "shoes": body.size_shoes,
                },
                "created_at": body.created_at.isoformat(),
            }
        
        budget = self._db.query(UserBudgetProfile).filter_by(user_id=user_id).first()
        if budget:
            data["budget_profile"] = {
                "per_item_min": float(budget.per_item_min) if budget.per_item_min else None,
                "per_item_max": float(budget.per_item_max) if budget.per_item_max else None,
                "currency": budget.currency,
                "created_at": budget.created_at.isoformat(),
            }
        
        brands = self._db.query(UserBrandAffinity).filter_by(user_id=user_id).all()
        if brands:
            data["brand_affinities"] = [
                {
                    "brand_id": b.brand_id,
                    "affinity_score": float(b.affinity_score or 0.5),
                    "created_at": b.created_at.isoformat(),
                }
                for b in brands
            ]
        
        context = self._db.query(UserContextualPreference).filter_by(user_id=user_id).first()
        if context:
            data["contextual_preferences"] = {
                "work_environment": context.work_environment,
                "climate_zone": context.climate_zone,
                "activity_level": context.activity_level,
                "occasion_weights": context.occasion_weights,
                "created_at": context.created_at.isoformat(),
            }
        
        confidence = self._db.query(UserConfidenceProfile).filter_by(user_id=user_id).first()
        if confidence:
            data["confidence_profile"] = {
                "overall_confidence": float(confidence.overall_confidence or 0),
                "dimensions": {
                    "fit_confidence": float(confidence.fit_confidence or 0),
                    "style_alignment": float(confidence.style_alignment or 0),
                    "budget_comfort": float(confidence.budget_comfort or 0),
                },
                "earned_badges": confidence.earned_badges,
                "created_at": confidence.created_at.isoformat(),
            }
        
        signals = self._db.query(UserBehaviorSignal).filter_by(user_id=user_id).limit(1000).all()
        if signals:
            data["behavior_signals"] = [
                {
                    "signal_type": s.signal_type,
                    "entity_type": s.entity_type,
                    "entity_id": s.entity_id,
                    "created_at": s.created_at.isoformat(),
                }
                for s in signals
            ]
        
        consent_history = self._db.query(UserConsentHistory).filter_by(user_id=user_id).all()
        if consent_history:
            data["consent_history"] = [
                {
                    "consent_type": c.consent_type,
                    "granted": c.granted,
                    "consent_version": c.consent_version,
                    "created_at": c.created_at.isoformat(),
                }
                for c in consent_history
            ]
        
        audit_log = self._db.query(UserProfileAuditLog).filter_by(user_id=user_id).limit(500).all()
        if audit_log:
            data["profile_audit_log"] = [
                {
                    "table_name": a.table_name,
                    "field_name": a.field_name,
                    "change_source": a.change_source,
                    "created_at": a.created_at.isoformat(),
                }
                for a in audit_log
            ]
        
        return data
    
    def get_export_status(self, export_id: str) -> Optional[DataExportResponse]:
        export_request = self._db.query(UserDataExportRequest).get(export_id)
        if not export_request:
            return None
        
        return DataExportResponse(
            id=str(export_request.id),
            user_id=str(export_request.user_id),
            status=export_request.status,
            format=export_request.format,
            requested_at=export_request.requested_at,
            completed_at=export_request.completed_at,
            download_url=export_request.download_url,
            expires_at=export_request.expires_at,
        )
    
    def get_export_data(self, export_id: str) -> Optional[Dict[str, Any]]:
        export_request = self._db.query(UserDataExportRequest).get(export_id)
        if not export_request or export_request.status != "completed":
            return None
        
        if export_request.expires_at and export_request.expires_at < datetime.now(timezone.utc):
            return None
        
        return getattr(export_request, 'export_data', None) or self._collect_user_data(str(export_request.user_id))
    
    def request_deletion(
        self,
        user_id: str,
        reason: str = None,
    ) -> DataExportResponse:
        existing_pending = self._db.query(UserDeletionRequest).filter_by(
            user_id=user_id,
            status="pending"
        ).first()
        
        if existing_pending:
            return DataExportResponse(
                id=str(existing_pending.id),
                user_id=str(existing_pending.user_id),
                status=existing_pending.status,
                format="deletion",
                requested_at=existing_pending.requested_at,
                completed_at=existing_pending.executed_at,
                download_url=None,
                expires_at=existing_pending.scheduled_for,
            )
        
        confirmation_code = secrets.token_hex(32)
        
        deletion_request = UserDeletionRequest(
            user_id=user_id,
            status="pending",
            reason=reason,
            confirmation_code=hashlib.sha256(confirmation_code.encode()).hexdigest(),
            scheduled_for=datetime.now(timezone.utc) + timedelta(days=30),
        )
        
        self._db.add(deletion_request)
        self._db.commit()
        self._db.refresh(deletion_request)
        
        deletion_request._confirmation_code_plain = confirmation_code
        
        return DataExportResponse(
            id=str(deletion_request.id),
            user_id=str(deletion_request.user_id),
            status=deletion_request.status,
            format="deletion",
            requested_at=deletion_request.requested_at,
            completed_at=deletion_request.executed_at,
            download_url=None,
            expires_at=deletion_request.scheduled_for,
        )
    
    def confirm_deletion(
        self,
        user_id: str,
        confirmation_code: str,
    ) -> bool:
        deletion_request = self._db.query(UserDeletionRequest).filter_by(
            user_id=user_id,
            status="pending"
        ).first()
        
        if not deletion_request:
            return False
        
        hashed_code = hashlib.sha256(confirmation_code.encode()).hexdigest()
        
        if deletion_request.confirmation_code != hashed_code:
            return False
        
        self._execute_deletion(user_id)
        
        deletion_request.status = "completed"
        deletion_request.executed_at = datetime.now(timezone.utc)
        self._db.commit()
        
        return True
    
    def cancel_deletion(self, user_id: str) -> bool:
        deletion_request = self._db.query(UserDeletionRequest).filter_by(
            user_id=user_id,
            status="pending"
        ).first()
        
        if not deletion_request:
            return False
        
        deletion_request.status = "cancelled"
        self._db.commit()
        
        return True
    
    def _execute_deletion(self, user_id: str) -> None:
        user = self._db.query(User).filter_by(id=user_id).first()
        if user:
            user.email = f"deleted_{user_id}@confit.anonymized"
            user.name = "Deleted User"
            user.password_hash = ""
            user.phone = None
            user.avatar_url = None
        
        self._db.query(UserStyleProfile).filter_by(user_id=user_id).delete()
        self._db.query(UserBodyProfile).filter_by(user_id=user_id).delete()
        self._db.query(UserBudgetProfile).filter_by(user_id=user_id).delete()
        self._db.query(UserBrandAffinity).filter_by(user_id=user_id).delete()
        self._db.query(UserContextualPreference).filter_by(user_id=user_id).delete()
        self._db.query(UserConfidenceProfile).filter_by(user_id=user_id).delete()
        self._db.query(UserConfidenceHistory).filter_by(user_id=user_id).delete()
        self._db.query(UserBehaviorSignal).filter_by(user_id=user_id).delete()
        self._db.query(UserStyleEvolution).filter_by(user_id=user_id).delete()
        self._db.query(UserConsentHistory).filter_by(user_id=user_id).delete()
        self._db.query(UserProfileAuditLog).filter_by(user_id=user_id).delete()
        self._db.query(UserOnboardingSession).filter_by(user_id=user_id).delete()
        self._db.query(UserDataExportRequest).filter_by(user_id=user_id).delete()
        
        self._db.commit()
    
    def apply_retention_policy(
        self,
        user_id: str,
        policy: str = "standard",
    ) -> None:
        days = DATA_RETENTION_DAYS.get(policy, 365)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        self._db.query(UserBehaviorSignal).filter(
            UserBehaviorSignal.user_id == user_id,
            UserBehaviorSignal.created_at < cutoff,
            UserBehaviorSignal.expires_at == None
        ).delete()
        
        self._db.query(UserStyleEvolution).filter(
            UserStyleEvolution.user_id == user_id,
            UserStyleEvolution.created_at < cutoff
        ).delete()
        
        self._db.query(UserProfileAuditLog).filter(
            UserProfileAuditLog.user_id == user_id,
            UserProfileAuditLog.created_at < cutoff
        ).delete()
        
        self._db.commit()
    
    def get_privacy_settings(self, user_id: str) -> Dict[str, Any]:
        consents = self.get_consents(user_id)
        
        pending_deletion = self._db.query(UserDeletionRequest).filter_by(
            user_id=user_id,
            status="pending"
        ).first()
        
        return {
            "consents": consents,
            "retention_policy": "standard",
            "pending_deletion": pending_deletion is not None,
            "deletion_scheduled_for": pending_deletion.scheduled_for.isoformat() if pending_deletion else None,
        }


def get_privacy_service(db: Session = Depends(get_db)) -> PrivacyService:
    return PrivacyService(db)
