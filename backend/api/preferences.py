"""
CONFIT Backend - Notification Preferences API Routes
=====================================================
Preference synchronization, conflict resolution, and audit logging.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from api.deps import get_db, get_current_user, get_redis
from core.security.rbac import AuthContext, Role


router = APIRouter(prefix="/notifications/preferences", tags=["Notification Preferences"])


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class DeviceType(str, Enum):
    MOBILE_APP = "mobile_app"
    DESKTOP_BROWSER = "desktop_browser"
    TABLET_APP = "tablet_app"
    OTHER = "other"


class RecipientType(str, Enum):
    CUSTOMER = "customer"
    OWNER = "owner"


class ChannelType(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    TOAST = "toast"


class FrequencySetting(str, Enum):
    REAL_TIME = "real_time"
    DAILY_DIGEST = "daily_digest"
    WEEKLY_SUMMARY = "weekly_summary"
    DISABLED = "disabled"


class ChangeType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    CONFLICT_RESOLVED = "conflict_resolved"


class ConflictType(str, Enum):
    NO_CONFLICT = "no_conflict"
    VERSION_STALE = "version_stale"
    CONCURRENT_UPDATE = "concurrent_update"
    CHECKSUM_MISMATCH = "checksum_mismatch"


# ─────────────────────────────────────────────────────────────────────────────
# DTOS
# ─────────────────────────────────────────────────────────────────────────────

class NotificationTypeSettings(BaseModel):
    enabled: Optional[bool] = None
    channels: Optional[Dict[str, Dict[str, bool]]] = None


class BatchSettings(BaseModel):
    daily_digest: Optional[Dict[str, str]] = None
    weekly_summary: Optional[Dict[str, str]] = None


class PreferenceUpdate(BaseModel):
    global_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    toast_enabled: Optional[bool] = None
    in_app_frequency: Optional[FrequencySetting] = None
    email_frequency: Optional[FrequencySetting] = None
    push_frequency: Optional[FrequencySetting] = None
    toast_frequency: Optional[FrequencySetting] = None
    notification_types: Optional[Dict[str, Any]] = None
    batch_settings: Optional[Dict[str, Any]] = None


class PreferenceUpdateRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100)
    device_type: DeviceType
    device_name: Optional[str] = Field(None, max_length=100)
    base_sync_version: str = Field(..., min_length=1)
    base_checksum: str = Field(..., min_length=1)
    preferences: PreferenceUpdate
    client_timestamp: datetime


class DeviceRegistrationRequest(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100)
    device_type: DeviceType
    device_name: Optional[str] = Field(None, max_length=100)
    user_agent: Optional[str] = Field(None, max_length=500)
    push_token: Optional[str] = Field(None, max_length=500)


class PreferenceStateDTO(BaseModel):
    global_enabled: bool
    channels: Dict[str, Dict[str, Any]]
    notification_types: Dict[str, Any]
    batch_settings: Dict[str, Any]
    sync_version: Optional[str] = None
    checksum: Optional[str] = None
    last_modified: Optional[datetime] = None
    is_default: bool = False


class PreferenceQueryResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


class PreferenceUpdateResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class DeviceDTO(BaseModel):
    device_id: str
    device_type: DeviceType
    device_name: Optional[str]
    last_seen_at: datetime
    registered_at: datetime
    is_current: bool = False


class DeviceListResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


class AuditLogDTO(BaseModel):
    id: str
    timestamp: datetime
    change_type: ChangeType
    field_path: str
    old_value: Optional[Any]
    new_value: Optional[Any]
    device_id: str
    device_type: DeviceType
    ip_address: Optional[str]
    reason: Optional[str]
    conflict_resolution: Optional[str]


class AuditLogQueryResponse(BaseModel):
    success: bool = True
    data: Dict[str, Any]


# ─────────────────────────────────────────────────────────────────────────────
# CONFLICT RESOLVER
# ─────────────────────────────────────────────────────────────────────────────

class ConflictResolver:
    """Handles preference conflict detection and resolution."""
    
    DEVICE_PRIORITY = {
        DeviceType.MOBILE_APP: 4,
        DeviceType.DESKTOP_BROWSER: 3,
        DeviceType.TABLET_APP: 2,
        DeviceType.OTHER: 1,
    }
    
    @staticmethod
    def calculate_checksum(prefs: Dict[str, Any]) -> str:
        """Calculate SHA-256 checksum of preference state."""
        concat = (
            str(prefs.get('global_enabled', True)) + '|' +
            str(prefs.get('in_app_enabled', True)) + '|' +
            str(prefs.get('email_enabled', True)) + '|' +
            str(prefs.get('push_enabled', True)) + '|' +
            str(prefs.get('toast_enabled', True)) + '|' +
            str(prefs.get('in_app_frequency', 'real_time')) + '|' +
            str(prefs.get('email_frequency', 'real_time')) + '|' +
            str(prefs.get('push_frequency', 'real_time')) + '|' +
            str(prefs.get('toast_frequency', 'real_time')) + '|' +
            json.dumps(prefs.get('notification_types', {}), sort_keys=True) + '|' +
            json.dumps(prefs.get('batch_settings', {}), sort_keys=True)
        )
        return hashlib.sha256(concat.encode()).hexdigest()
    
    def detect_conflict(
        self,
        incoming: PreferenceUpdateRequest,
        current: Dict[str, Any]
    ) -> ConflictType:
        """Detect if incoming update conflicts with current state."""
        
        # Case 1: First write for this preference
        if not current or current.get('sync_version') is None:
            return ConflictType.NO_CONFLICT
        
        # Case 2: Same device updating - always accept
        if incoming.device_id == current.get('last_modified_by'):
            return ConflictType.NO_CONFLICT
        
        # Case 3: Checksum validation
        if incoming.base_checksum != current.get('checksum', ''):
            return ConflictType.CHECKSUM_MISMATCH
        
        # Case 4: Vector clock comparison
        incoming_clock = incoming.preferences.dict() if hasattr(incoming, 'vector_clock') else {}
        current_clock = current.get('vector_clock', {})
        
        comparison = self._compare_vector_clocks(incoming_clock, current_clock)
        
        if comparison < 0:
            return ConflictType.VERSION_STALE
        elif comparison > 0:
            return ConflictType.NO_CONFLICT
        else:
            return ConflictType.CONCURRENT_UPDATE
    
    def _compare_vector_clocks(
        self,
        clock_a: Dict[str, int],
        clock_b: Dict[str, int]
    ) -> int:
        """
        Compare two vector clocks.
        Returns: -1 (a older), 0 (concurrent), 1 (a newer)
        """
        all_keys = set(clock_a.keys()) | set(clock_b.keys())
        
        a_less = False
        b_less = False
        
        for key in all_keys:
            val_a = clock_a.get(key, 0)
            val_b = clock_b.get(key, 0)
            
            if val_a < val_b:
                a_less = True
            elif val_a > val_b:
                b_less = True
        
        if a_less and not b_less:
            return -1
        elif b_less and not a_less:
            return 1
        return 0
    
    def resolve(
        self,
        incoming: PreferenceUpdateRequest,
        current: Dict[str, Any],
        conflict_type: ConflictType
    ) -> Dict[str, Any]:
        """
        Resolve conflict and determine final preference state.
        Returns resolution result with action to take.
        """
        
        if conflict_type == ConflictType.VERSION_STALE:
            return {
                'action': 'reject',
                'reason': 'Client version is stale',
                'current_state': current,
                'client_must_resync': True
            }
        
        if conflict_type == ConflictType.CHECKSUM_MISMATCH:
            return {
                'action': 'force_resync',
                'reason': 'Client state diverged from server',
                'current_state': current,
                'client_must_resync': True
            }
        
        if conflict_type == ConflictType.CONCURRENT_UPDATE:
            winner = self._determine_winner(incoming, current)
            
            if winner == 'incoming':
                return {
                    'action': 'apply_incoming',
                    'reason': 'Incoming update is more recent',
                    'audit_note': f"Overrode concurrent update from {current.get('last_modified_by')}"
                }
            else:
                return {
                    'action': 'keep_current',
                    'reason': 'Current state is more recent',
                    'current_state': current,
                    'audit_note': f"Rejected concurrent update from {incoming.device_id}"
                }
        
        return {'action': 'apply_incoming'}
    
    def _determine_winner(
        self,
        incoming: PreferenceUpdateRequest,
        current: Dict[str, Any]
    ) -> str:
        """Determine winner in concurrent update scenario."""
        
        # Rule 1: Most recent timestamp wins
        current_modified = current.get('last_modified')
        if current_modified:
            if incoming.client_timestamp > current_modified:
                return 'incoming'
            elif incoming.client_timestamp < current_modified:
                return 'current'
        
        # Rule 2: Device priority (tiebreaker)
        incoming_priority = self.DEVICE_PRIORITY.get(incoming.device_type, 1)
        current_device_type = current.get('device_type', 'other')
        current_priority = self.DEVICE_PRIORITY.get(
            DeviceType(current_device_type) if current_device_type in [e.value for e in DeviceType] else DeviceType.OTHER,
            1
        )
        
        if incoming_priority > current_priority:
            return 'incoming'
        elif incoming_priority < current_priority:
            return 'current'
        
        # Rule 3: Lexicographic device_id (final tiebreaker)
        if incoming.device_id > current.get('last_modified_by', ''):
            return 'incoming'
        return 'current'


# ─────────────────────────────────────────────────────────────────────────────
# PREFERENCE SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class PreferenceService:
    """Service for managing notification preferences."""
    
    CACHE_TTL = 300  # 5 minutes
    CACHE_PREFIX = "notif:prefs"
    
    def __init__(self, db: AsyncSession, redis: redis.Redis):
        self.db = db
        self.redis = redis
        self.conflict_resolver = ConflictResolver()
    
    async def get_preferences(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current preferences with cache-first strategy."""
        
        cache_key = f"{self.CACHE_PREFIX}:{recipient_type.value}:{recipient_id}"
        
        # Try cache first
        cached = await self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Query database
        result = await self.db.execute(
            text("""
                SELECT * FROM get_effective_preferences(:recipient_id, :recipient_type)
            """),
            {'recipient_id': recipient_id, 'recipient_type': recipient_type.value}
        )
        row = result.fetchone()
        
        if row:
            prefs = row[0]
        else:
            prefs = self._get_default_preferences()
        
        # Update device last seen
        if device_id:
            await self._update_device_last_seen(recipient_id, device_id)
        
        # Cache the result
        await self._set_cache(cache_key, prefs)
        
        return prefs
    
    async def update_preferences(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
        update: PreferenceUpdateRequest,
        ip_address: str,
        user_agent: str
    ) -> Dict[str, Any]:
        """Update preferences with conflict detection."""
        
        # Get current preferences
        current = await self._get_current_preferences(recipient_id, recipient_type)
        
        # Detect conflicts
        conflict_type = self.conflict_resolver.detect_conflict(update, current)
        
        # Resolve conflict
        resolution = self.conflict_resolver.resolve(update, current, conflict_type)
        
        if resolution['action'] in ['reject', 'force_resync']:
            return {
                'success': False,
                'error': {
                    'code': 'CONFLICT_DETECTED',
                    'message': resolution['reason'],
                    'conflict_type': conflict_type.value,
                    'current_server_state': resolution.get('current_state'),
                }
            }
        
        if resolution['action'] == 'keep_current':
            return {
                'success': False,
                'error': {
                    'code': 'CONFLICT_DETECTED',
                    'message': 'Your preferences were updated on another device',
                    'conflict_type': conflict_type.value,
                    'current_server_state': resolution.get('current_state'),
                    'resolution': {
                        'type': 'server_wins',
                        'details': resolution.get('audit_note')
                    }
                }
            }
        
        # Apply update
        new_prefs = await self._apply_update(
            recipient_id, recipient_type, update, current
        )
        
        # Create audit log
        await self._create_audit_log(
            recipient_id, recipient_type, update, current, new_prefs,
            ip_address, user_agent, conflict_type, resolution
        )
        
        # Invalidate cache
        await self._invalidate_cache(recipient_id, recipient_type)
        
        return {
            'success': True,
            'data': {
                'preferences': new_prefs,
                'sync_version': new_prefs.get('sync_version'),
                'checksum': new_prefs.get('checksum'),
                'last_modified': new_prefs.get('last_modified'),
            }
        }
    
    async def _get_current_preferences(
        self,
        recipient_id: str,
        recipient_type: RecipientType
    ) -> Dict[str, Any]:
        """Get current preferences from database."""
        
        result = await self.db.execute(
            text("""
                SELECT * FROM notification_preferences
                WHERE recipient_id = :recipient_id AND recipient_type = :recipient_type
            """),
            {'recipient_id': recipient_id, 'recipient_type': recipient_type.value}
        )
        row = result.fetchone()
        
        if not row:
            return {}
        
        # Map row to dict
        cols = result.keys()
        return dict(zip(cols, row))
    
    async def _apply_update(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
        update: PreferenceUpdateRequest,
        current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply preference update to database."""
        
        prefs = update.preferences
        
        # Generate new sync version
        current_version = current.get('sync_version', '')
        new_version = await self._generate_sync_version(update.device_id, current_version)
        
        # Build update query
        update_fields = []
        params = {
            'recipient_id': recipient_id,
            'recipient_type': recipient_type.value,
            'sync_version': new_version,
            'last_modified_by': update.device_id,
            'last_modified': update.client_timestamp,
        }
        
        # Add preference fields
        if prefs.global_enabled is not None:
            update_fields.append("global_enabled = :global_enabled")
            params['global_enabled'] = prefs.global_enabled
        
        if prefs.in_app_enabled is not None:
            update_fields.append("in_app_enabled = :in_app_enabled")
            params['in_app_enabled'] = prefs.in_app_enabled
        
        if prefs.email_enabled is not None:
            update_fields.append("email_enabled = :email_enabled")
            params['email_enabled'] = prefs.email_enabled
        
        if prefs.push_enabled is not None:
            update_fields.append("push_enabled = :push_enabled")
            params['push_enabled'] = prefs.push_enabled
        
        if prefs.toast_enabled is not None:
            update_fields.append("toast_enabled = :toast_enabled")
            params['toast_enabled'] = prefs.toast_enabled
        
        if prefs.in_app_frequency is not None:
            update_fields.append("in_app_frequency = :in_app_frequency")
            params['in_app_frequency'] = prefs.in_app_frequency.value
        
        if prefs.email_frequency is not None:
            update_fields.append("email_frequency = :email_frequency")
            params['email_frequency'] = prefs.email_frequency.value
        
        if prefs.push_frequency is not None:
            update_fields.append("push_frequency = :push_frequency")
            params['push_frequency'] = prefs.push_frequency.value
        
        if prefs.toast_frequency is not None:
            update_fields.append("toast_frequency = :toast_frequency")
            params['toast_frequency'] = prefs.toast_frequency.value
        
        if prefs.notification_types is not None:
            update_fields.append("notification_types = :notification_types")
            params['notification_types'] = json.dumps(prefs.notification_types)
        
        if prefs.batch_settings is not None:
            update_fields.append("batch_settings = :batch_settings")
            params['batch_settings'] = json.dumps(prefs.batch_settings)
        
        if not current:
            # Insert new preferences
            query = text(f"""
                INSERT INTO notification_preferences (
                    recipient_id, recipient_type, sync_version, last_modified_by, last_modified,
                    global_enabled, in_app_enabled, email_enabled, push_enabled, toast_enabled,
                    in_app_frequency, email_frequency, push_frequency, toast_frequency,
                    notification_types, batch_settings
                ) VALUES (
                    :recipient_id, :recipient_type, :sync_version, :last_modified_by, :last_modified,
                    COALESCE(:global_enabled, true),
                    COALESCE(:in_app_enabled, true),
                    COALESCE(:email_enabled, true),
                    COALESCE(:push_enabled, true),
                    COALESCE(:toast_enabled, true),
                    COALESCE(:in_app_frequency, 'real_time'),
                    COALESCE(:email_frequency, 'real_time'),
                    COALESCE(:push_frequency, 'real_time'),
                    COALESCE(:toast_frequency, 'real_time'),
                    COALESCE(:notification_types, '{}'),
                    COALESCE(:batch_settings, '{}')
                )
                RETURNING *
            """)
        else:
            # Update existing preferences
            update_fields.append("updated_at = NOW()")
            update_fields.append("last_modified = :last_modified")
            update_fields.append("last_modified_by = :last_modified_by")
            update_fields.append("sync_version = :sync_version")
            
            query = text(f"""
                UPDATE notification_preferences
                SET {', '.join(update_fields)}
                WHERE recipient_id = :recipient_id AND recipient_type = :recipient_type
                RETURNING *
            """)
        
        result = await self.db.execute(query, params)
        await self.db.commit()
        
        row = result.fetchone()
        cols = result.keys()
        return dict(zip(cols, row))
    
    async def _generate_sync_version(self, device_id: str, current_version: str) -> str:
        """Generate new sync version."""
        result = await self.db.execute(
            text("SELECT generate_sync_version(:device_id, :current_version)"),
            {'device_id': device_id, 'current_version': current_version}
        )
        return result.scalar()
    
    async def _create_audit_log(
        self,
        recipient_id: str,
        recipient_type: RecipientType,
        update: PreferenceUpdateRequest,
        old_prefs: Dict[str, Any],
        new_prefs: Dict[str, Any],
        ip_address: str,
        user_agent: str,
        conflict_type: ConflictType,
        resolution: Dict[str, Any]
    ) -> None:
        """Create audit log entry for preference change."""
        
        change_type = 'create' if not old_prefs else 'update'
        if conflict_type == ConflictType.CONCURRENT_UPDATE:
            change_type = 'conflict_resolved'
        
        # Track what changed
        prefs = update.preferences
        changes = []
        
        if prefs.global_enabled is not None:
            changes.append(('global_enabled', old_prefs.get('global_enabled'), prefs.global_enabled))
        
        # Insert audit log for each change
        for field_path, old_val, new_val in changes:
            await self.db.execute(
                text("""
                    INSERT INTO notification_preference_audit (
                        recipient_id, recipient_type, change_type, field_path,
                        old_value, new_value, device_id, device_type, ip_address,
                        user_agent, reason, conflict_resolution,
                        sync_version_before, sync_version_after
                    ) VALUES (
                        :recipient_id, :recipient_type, :change_type, :field_path,
                        :old_value, :new_value, :device_id, :device_type, :ip_address,
                        :user_agent, :reason, :conflict_resolution,
                        :sync_version_before, :sync_version_after
                    )
                """),
                {
                    'recipient_id': recipient_id,
                    'recipient_type': recipient_type.value,
                    'change_type': change_type,
                    'field_path': field_path,
                    'old_value': json.dumps(old_val) if old_val is not None else None,
                    'new_value': json.dumps(new_val) if new_val is not None else None,
                    'device_id': update.device_id,
                    'device_type': update.device_type.value,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'reason': 'user_action' if conflict_type == ConflictType.NO_CONFLICT else 'conflict_resolution',
                    'conflict_resolution': resolution.get('audit_note'),
                    'sync_version_before': old_prefs.get('sync_version'),
                    'sync_version_after': new_prefs.get('sync_version'),
                }
            )
    
    async def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get preferences from Redis cache."""
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None
    
    async def _set_cache(self, key: str, value: Dict[str, Any]) -> None:
        """Set preferences in Redis cache."""
        try:
            await self.redis.setex(key, self.CACHE_TTL, json.dumps(value))
        except Exception:
            pass
    
    async def _invalidate_cache(
        self,
        recipient_id: str,
        recipient_type: RecipientType
    ) -> None:
        """Invalidate preference cache."""
        cache_key = f"{self.CACHE_PREFIX}:{recipient_type.value}:{recipient_id}"
        
        try:
            # Store stale copy for fallback
            data = await self.redis.get(cache_key)
            if data:
                await self.redis.set(f"{cache_key}:stale", data)
            
            # Delete current cache
            await self.redis.delete(cache_key)
            
            # Publish invalidation event
            await self.redis.publish(
                'preference:invalidate',
                json.dumps({
                    'recipient_id': recipient_id,
                    'recipient_type': recipient_type.value,
                    'timestamp': datetime.utcnow().isoformat()
                })
            )
        except Exception:
            pass
    
    async def _update_device_last_seen(
        self,
        user_id: str,
        device_id: str
    ) -> None:
        """Update device last seen timestamp."""
        try:
            await self.db.execute(
                text("""
                    UPDATE notification_devices
                    SET last_seen_at = NOW()
                    WHERE user_id = :user_id AND device_id = :device_id
                """),
                {'user_id': user_id, 'device_id': device_id}
            )
            await self.db.commit()
        except Exception:
            pass
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default preferences for new users."""
        return {
            'global_enabled': True,
            'channels': {
                'in_app': {'enabled': True, 'frequency': 'real_time'},
                'email': {'enabled': True, 'frequency': 'real_time'},
                'push': {'enabled': True, 'frequency': 'real_time'},
                'toast': {'enabled': True, 'frequency': 'real_time'}
            },
            'notification_types': {},
            'batch_settings': {},
            'is_default': True
        }


# ─────────────────────────────────────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=PreferenceQueryResponse,
    summary="Get current notification preferences",
)
async def get_preferences(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: redis.Redis = Depends(get_redis),
    current_user: AuthContext = Depends(get_current_user),
):
    """Get current notification preferences for the authenticated user."""
    
    device_id = request.headers.get('X-Device-ID')
    recipient_type = RecipientType.CUSTOMER
    
    # Check if user is store/factory owner
    if current_user.has_role(Role.STORE_OWNER) or current_user.has_role(Role.FACTORY_OWNER):
        recipient_type = RecipientType.OWNER
    
    service = PreferenceService(db, redis)
    prefs = await service.get_preferences(
        current_user.user_id,
        recipient_type,
        device_id
    )
    
    # Get registered devices
    devices_result = await db.execute(
        text("""
            SELECT device_id, device_type, device_name, last_seen_at, registered_at
            FROM notification_devices
            WHERE user_id = :user_id
            ORDER BY last_seen_at DESC
        """),
        {'user_id': current_user.user_id}
    )
    devices = []
    for row in devices_result.fetchall():
        devices.append({
            'device_id': row[0],
            'device_type': row[1],
            'device_name': row[2],
            'last_seen_at': row[3].isoformat(),
            'registered_at': row[4].isoformat(),
            'is_current': row[0] == device_id
        })
    
    return PreferenceQueryResponse(
        data={
            'preferences': prefs,
            'sync_version': prefs.get('sync_version'),
            'checksum': prefs.get('checksum'),
            'last_modified': prefs.get('last_modified'),
            'registered_devices': devices,
        }
    )


@router.post(
    "",
    response_model=PreferenceUpdateResponse,
    summary="Update notification preferences",
)
async def update_preferences(
    update_request: PreferenceUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: redis.Redis = Depends(get_redis),
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Update notification preferences with conflict detection.
    
    Supports partial updates - only include fields you want to change.
    """
    
    # Determine recipient type
    recipient_type = RecipientType.CUSTOMER
    if current_user.has_role(Role.STORE_OWNER) or current_user.has_role(Role.FACTORY_OWNER):
        recipient_type = RecipientType.OWNER
    
    # Get client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get('user-agent', '')
    
    service = PreferenceService(db, redis)
    result = await service.update_preferences(
        current_user.user_id,
        recipient_type,
        update_request,
        ip_address,
        user_agent
    )
    
    if not result['success']:
        raise HTTPException(
            status_code=409,
            detail=result['error']
        )
    
    return result


@router.post(
    "/devices",
    summary="Register a device for preference sync",
)
async def register_device(
    device_request: DeviceRegistrationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user),
):
    """Register a device for preference synchronization."""
    
    # Check if device already registered
    existing = await db.execute(
        text("""
            SELECT device_id FROM notification_devices
            WHERE user_id = :user_id AND device_id = :device_id
        """),
        {'user_id': current_user.user_id, 'device_id': device_request.device_id}
    )
    
    if existing.fetchone():
        # Update existing device
        await db.execute(
            text("""
                UPDATE notification_devices
                SET last_seen_at = NOW(),
                    device_name = COALESCE(:device_name, device_name),
                    user_agent = COALESCE(:user_agent, user_agent),
                    push_token = COALESCE(:push_token, push_token)
                WHERE user_id = :user_id AND device_id = :device_id
            """),
            {
                'user_id': current_user.user_id,
                'device_id': device_request.device_id,
                'device_name': device_request.device_name,
                'user_agent': device_request.user_agent,
                'push_token': device_request.push_token,
            }
        )
        is_new = False
    else:
        # Register new device
        await db.execute(
            text("""
                INSERT INTO notification_devices (
                    user_id, device_id, device_type, device_name, user_agent, push_token
                ) VALUES (
                    :user_id, :device_id, :device_type, :device_name, :user_agent, :push_token
                )
            """),
            {
                'user_id': current_user.user_id,
                'device_id': device_request.device_id,
                'device_type': device_request.device_type.value,
                'device_name': device_request.device_name,
                'user_agent': device_request.user_agent,
                'push_token': device_request.push_token,
            }
        )
        is_new = True
    
    await db.commit()
    
    return {
        'success': True,
        'data': {
            'device_id': device_request.device_id,
            'registered_at': datetime.utcnow().isoformat(),
            'is_new_device': is_new,
        }
    }


@router.get(
    "/devices",
    response_model=DeviceListResponse,
    summary="List registered devices",
)
async def list_devices(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user),
):
    """List all devices registered for preference sync."""
    
    device_id = request.headers.get('X-Device-ID')
    
    result = await db.execute(
        text("""
            SELECT device_id, device_type, device_name, last_seen_at, registered_at
            FROM notification_devices
            WHERE user_id = :user_id
            ORDER BY last_seen_at DESC
        """),
        {'user_id': current_user.user_id}
    )
    
    devices = []
    for row in result.fetchall():
        devices.append({
            'device_id': row[0],
            'device_type': row[1],
            'device_name': row[2],
            'last_seen_at': row[3].isoformat(),
            'registered_at': row[4].isoformat(),
            'is_current': row[0] == device_id
        })
    
    return DeviceListResponse(
        data={
            'devices': devices,
            'total_count': len(devices),
        }
    )


@router.delete(
    "/devices/{device_id}",
    summary="Remove a registered device",
)
async def remove_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user),
):
    """Remove a device from preference sync registry."""
    
    result = await db.execute(
        text("""
            DELETE FROM notification_devices
            WHERE user_id = :user_id AND device_id = :device_id
            RETURNING device_id
        """),
        {'user_id': current_user.user_id, 'device_id': device_id}
    )
    
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Device not found")
    
    await db.commit()
    
    return {
        'success': True,
        'data': {
            'removed_device_id': device_id,
            'removed_at': datetime.utcnow().isoformat(),
        }
    }


@router.get(
    "/audit",
    response_model=AuditLogQueryResponse,
    summary="Query preference audit logs",
)
async def get_audit_logs(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    device_id: Optional[str] = Query(None),
    change_type: Optional[ChangeType] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user),
):
    """
    Query audit logs for preference changes.
    
    Users can only see their own logs. Admins can see all logs.
    """
    
    # Build query conditions
    conditions = ["recipient_id = :recipient_id"]
    params = {'recipient_id': current_user.user_id}
    
    # Admins can query all users
    if current_user.has_role(Role.ADMIN) and current_user.user_id != current_user.user_id:
        conditions = ["1=1"]
        params = {}
    
    if start_date:
        conditions.append("timestamp >= :start_date")
        params['start_date'] = start_date
    
    if end_date:
        conditions.append("timestamp < :end_date")
        params['end_date'] = end_date
    
    if device_id:
        conditions.append("device_id = :device_id")
        params['device_id'] = device_id
    
    if change_type:
        conditions.append("change_type = :change_type")
        params['change_type'] = change_type.value
    
    where_clause = " AND ".join(conditions)
    
    # Get total count
    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM notification_preference_audit WHERE {where_clause}"),
        params
    )
    total = count_result.scalar()
    
    # Get paginated results
    offset = (page - 1) * per_page
    params['limit'] = per_page
    params['offset'] = offset
    
    result = await db.execute(
        text(f"""
            SELECT id, timestamp, change_type, field_path, old_value, new_value,
                   device_id, device_type, ip_address, reason, conflict_resolution
            FROM notification_preference_audit
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset
        """),
        params
    )
    
    logs = []
    for row in result.fetchall():
        logs.append({
            'id': str(row[0]),
            'timestamp': row[1].isoformat(),
            'change_type': row[2],
            'field_path': row[3],
            'old_value': row[4],
            'new_value': row[5],
            'device_id': row[6],
            'device_type': row[7],
            'ip_address': str(row[8]) if row[8] else None,
            'reason': row[9],
            'conflict_resolution': row[10],
        })
    
    return AuditLogQueryResponse(
        data={
            'logs': logs,
            'pagination': {
                'total': total,
                'page': page,
                'per_page': per_page,
                'has_more': (page * per_page) < total,
            }
        }
    )


@router.get(
    "/audit/export",
    summary="Export audit logs",
)
async def export_audit_logs(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    format: str = Query('json', pattern='^(json|csv)$'),
    db: AsyncSession = Depends(get_db),
    current_user: AuthContext = Depends(get_current_user),
):
    """Export audit logs as JSON or CSV file."""
    
    # Build query
    conditions = ["recipient_id = :recipient_id"]
    params = {'recipient_id': current_user.user_id}
    
    if start_date:
        conditions.append("timestamp >= :start_date")
        params['start_date'] = start_date
    
    if end_date:
        conditions.append("timestamp < :end_date")
        params['end_date'] = end_date
    
    where_clause = " AND ".join(conditions)
    
    result = await db.execute(
        text(f"""
            SELECT timestamp, change_type, field_path, old_value, new_value,
                   device_id, device_type, reason
            FROM notification_preference_audit
            WHERE {where_clause}
            ORDER BY timestamp DESC
        """),
        params
    )
    
    rows = result.fetchall()
    
    if format == 'json':
        import io
        data = []
        for row in rows:
            data.append({
                'timestamp': row[0].isoformat(),
                'change_type': row[1],
                'field_path': row[2],
                'old_value': row[3],
                'new_value': row[4],
                'device_id': row[5],
                'device_type': row[6],
                'reason': row[7],
            })
        
        return Response(
            content=json.dumps(data, indent=2),
            media_type='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="preference-audit-{datetime.utcnow().date()}.json"'
            }
        )
    else:
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['timestamp', 'change_type', 'field_path', 'old_value', 'new_value', 'device_id', 'device_type', 'reason'])
        
        for row in rows:
            writer.writerow([
                row[0].isoformat(),
                row[1],
                row[2],
                row[3] or '',
                row[4] or '',
                row[5],
                row[6],
                row[7] or '',
            ])
        
        return Response(
            content=output.getvalue(),
            media_type='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="preference-audit-{datetime.utcnow().date()}.csv"'
            }
        )
