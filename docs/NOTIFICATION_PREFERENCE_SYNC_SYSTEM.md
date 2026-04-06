# CONFIT — Notification Preference Synchronization System

**Version:** 1.0.0  
**Date:** April 2026  
**Author:** Backend Architecture Team

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Conflict Resolution Algorithm](#2-conflict-resolution-algorithm)
3. [Database Schema](#3-database-schema)
4. [API Contracts](#4-api-contracts)
5. [NotificationService Integration](#5-notificationservice-integration)
6. [Client-Side State Management](#6-client-side-state-management)
7. [Sync & Cache Strategy](#7-sync--cache-strategy)
8. [Audit Logging](#8-audit-logging)
9. [Failure Scenarios & Responses](#9-failure-scenarios--responses)

---

# 1. System Overview

## 1.1 Problem Statement

Users access CONFIT across multiple devices and browsers. When notification preferences are updated on one device, the system must:
- Resolve conflicts when concurrent updates occur
- Ensure NotificationService always queries current preferences before dispatch
- Provide optimistic UI updates while maintaining data consistency
- Recover gracefully from persistence failures
- Audit all changes for compliance and debugging

## 1.2 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PREFERENCE SYNCHRONIZATION SYSTEM                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      CLIENT LAYER (Multi-Device)                    │    │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐       │    │
│  │  │  Mobile   │  │  Desktop  │  │  Tablet   │  │  Browser  │       │    │
│  │  │  App      │  │  Web      │  │  App      │  │  Session  │       │    │
│  │  │           │  │           │  │           │  │           │       │    │
│  │  │ Optimistic│  │ Optimistic│  │ Optimistic│  │ Optimistic│       │    │
│  │  │ Updates   │  │ Updates   │  │ Updates   │  │ Updates   │       │    │
│  │  │ Offline   │  │ Offline   │  │ Offline   │  │ Offline   │       │    │
│  │  │ Queue     │  │ Queue     │  │ Queue     │  │ Queue     │       │    │
│  │  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘       │    │
│  └────────┼──────────────┼──────────────┼──────────────┼─────────────┘    │
│           │              │              │              │                  │
│           └──────────────┴──────────────┴──────────────┘                  │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         API GATEWAY                                  │    │
│  │  • Rate Limiting (10 req/min per user for preference updates)       │    │
│  │  • JWT Validation                                                    │    │
│  │  • Request Deduplication (idempotency keys)                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    PREFERENCE SERVICE (FastAPI)                      │    │
│  │                                                                      │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │    │
│  │  │ Conflict     │  │ Version      │  │ Audit        │               │    │
│  │  │ Resolver     │  │ Manager      │  │ Logger       │               │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │    │
│  │                                                                      │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │    │
│  │  │ Preference   │  │ Cache        │  │ Sync         │               │    │
│  │  │ Validator    │  │ Manager      │  │ Coordinator  │               │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                      │
│           ┌──────────────────────────┼──────────────────────────┐           │
│           │                          │                          │           │
│           ▼                          ▼                          ▼           │
│  ┌───────────────┐          ┌───────────────┐          ┌───────────────┐   │
│  │  PostgreSQL   │          │    Redis      │          │  Event Bus    │   │
│  │               │          │               │          │  (Pub/Sub)    │   │
│  │ • Preferences │          │ • Preference  │          │               │   │
│  │ • Versions    │          │   Cache       │          │ • Invalidate  │   │
│  │ • Audit Logs  │          │ • Sync State  │          │   Events      │   │
│  │ • Device Reg  │          │ • Locks       │          │               │   │
│  └───────────────┘          └───────────────┘          └───────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    NOTIFICATION SERVICE                              │    │
│  │                                                                      │    │
│  │  Before dispatch:                                                    │    │
│  │  1. Query current preferences from cache/DB                         │    │
│  │  2. Apply preference hierarchy (global → channel → type)            │    │
│  │  3. Check frequency settings                                         │    │
│  │  4. Dispatch only if enabled                                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 1.3 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Last-Write-Wins with Vector Clocks** | Simple for users to understand, with version tracking for conflict detection |
| **Optimistic Concurrency Control** | Low latency for UI, with rollback on failure |
| **Redis Cache with 5-min TTL** | Balance between freshness and DB load |
| **Event-Driven Invalidation** | Immediate cache refresh across instances |
| **Audit Log in Separate Table** | Compliance-friendly, queryable history |

---

# 2. Conflict Resolution Algorithm

## 2.1 Conflict Detection

Conflicts occur when:
1. Two devices update the same preference concurrently
2. An update arrives with an outdated `sync_version`
3. Network partition causes divergent states

### Version Tracking Structure

```typescript
interface PreferenceVersion {
  sync_version: string;        // Format: "deviceId:timestamp:sequence"
  vector_clock: Map<string, number>;  // deviceId → sequence number
  last_modified: Date;
  device_id: string;
  checksum: string;            // Hash of preference state for integrity
}
```

### Conflict Detection Logic

```python
def detect_conflict(incoming: PreferenceUpdate, current: Preference) -> ConflictType:
    """
    Detects if an incoming update conflicts with current state.
    
    Returns:
        - NO_CONFLICT: Safe to apply
        - VERSION_STALE: Incoming version is older, reject
        - CONCURRENT_UPDATE: Both versions are concurrent, resolve
        - CHECKSUM_MISMATCH: Data integrity issue, investigate
    """
    
    # Case 1: First write for this preference
    if current.sync_version is None:
        return ConflictType.NO_CONFLICT
    
    # Case 2: Same device updating - always accept
    if incoming.device_id == current.device_id:
        return ConflictType.NO_CONFLICT
    
    # Case 3: Checksum validation
    if incoming.base_checksum != current.checksum:
        # Client was working with stale data
        return ConflictType.CHECKSUM_MISMATCH
    
    # Case 4: Vector clock comparison
    comparison = compare_vector_clocks(incoming.vector_clock, current.vector_clock)
    
    if comparison == ClockComparison.BEFORE:
        return ConflictType.VERSION_STALE
    elif comparison == ClockComparison.AFTER:
        return ConflictType.NO_CONFLICT
    else:  # CONCURRENT
        return ConflictType.CONCURRENT_UPDATE
```

## 2.2 Conflict Resolution Strategy

### Primary Rule: Last-Write-Wins with Explicit Intent

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CONFLICT RESOLUTION FLOW                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  INCOMING UPDATE                                                         │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────┐     NO      ┌─────────────────────────────────────┐   │
│  │ Conflict?   │────────────▶│ Apply update, increment version     │   │
│  └─────────────┘             │ Return success with new state       │   │
│       │ YES                   └─────────────────────────────────────┘   │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    RESOLUTION MATRIX                             │    │
│  │                                                                  │    │
│  │  Conflict Type        │ Resolution Strategy                     │    │
│  │  ─────────────────────┼────────────────────────────────────────  │    │
│  │  VERSION_STALE        │ Reject, return current state            │    │
│  │  CONCURRENT_UPDATE    │ Apply LAST-WRITE-WINS                   │    │
│  │  CHECKSUM_MISMATCH    │ Return current state, force re-sync     │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│       │                                                                  │
│       ▼ (CONCURRENT_UPDATE)                                              │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              LAST-WRITE-WINS EVALUATION                         │    │
│  │                                                                  │    │
│  │  1. Compare timestamps (most recent wins)                        │    │
│  │  2. If timestamps equal, compare device priority:               │    │
│  │     - Mobile app > Desktop browser > Tablet > Other              │    │
│  │  3. If still equal, compare device_id lexicographically          │    │
│  │                                                                  │    │
│  │  Winner's preference becomes authoritative                       │    │
│  │  Loser's change is logged in audit trail                         │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Resolution Algorithm (Pseudocode)

```python
class ConflictResolver:
    DEVICE_PRIORITY = {
        'mobile_app': 4,
        'desktop_browser': 3,
        'tablet_app': 2,
        'other': 1
    }
    
    def resolve(self, incoming: PreferenceUpdate, current: Preference, 
                conflict_type: ConflictType) -> ResolutionResult:
        
        if conflict_type == ConflictType.VERSION_STALE:
            # Client has outdated version - reject and return current
            return ResolutionResult(
                action=ResolutionAction.REJECT,
                reason="Client version is stale",
                current_state=current,
                client_must_resync=True
            )
        
        if conflict_type == ConflictType.CHECKSUM_MISMATCH:
            # Data integrity issue - force full resync
            return ResolutionResult(
                action=ResolutionAction.FORCE_RESYNC,
                reason="Client state diverged from server",
                current_state=current,
                client_must_resync=True
            )
        
        if conflict_type == ConflictType.CONCURRENT_UPDATE:
            # Last-Write-Wins with tiebreaker
            winner = self._determine_winner(incoming, current)
            
            if winner == incoming:
                return ResolutionResult(
                    action=ResolutionAction.APPLY_INCOMING,
                    reason="Incoming update is more recent",
                    new_state=self._merge_preferences(incoming, current),
                    audit_note=f"Overrode concurrent update from {current.device_id}"
                )
            else:
                return ResolutionResult(
                    action=ResolutionAction.KEEP_CURRENT,
                    reason="Current state is more recent",
                    current_state=current,
                    audit_note=f"Rejected concurrent update from {incoming.device_id}"
                )
        
        # No conflict - apply normally
        return ResolutionResult(
            action=ResolutionAction.APPLY_INCOMING,
            new_state=self._apply_update(incoming, current)
        )
    
    def _determine_winner(self, incoming: PreferenceUpdate, 
                          current: Preference) -> PreferenceUpdate | Preference:
        
        # Rule 1: Most recent timestamp wins
        if incoming.last_modified > current.last_modified:
            return incoming
        elif incoming.last_modified < current.last_modified:
            return current
        
        # Rule 2: Device priority (tiebreaker for same timestamp)
        incoming_priority = self.DEVICE_PRIORITY.get(incoming.device_type, 1)
        current_priority = self.DEVICE_PRIORITY.get(current.device_type, 1)
        
        if incoming_priority > current_priority:
            return incoming
        elif incoming_priority < current_priority:
            return current
        
        # Rule 3: Lexicographic device_id (final tiebreaker)
        if incoming.device_id > current.device_id:
            return incoming
        return current
```

## 2.3 Partial Update Merging

When users change only specific fields, the system merges intelligently:

```python
def merge_partial_update(current: Preference, update: PreferenceUpdate) -> Preference:
    """
    Merges a partial update into current preference state.
    Only updates fields that are explicitly set in the update.
    """
    
    result = current.copy()
    
    # Track what changed for audit
    changes = []
    
    # Global settings
    if update.global_enabled is not None:
        if result.global_enabled != update.global_enabled:
            changes.append(('global_enabled', result.global_enabled, update.global_enabled))
            result.global_enabled = update.global_enabled
    
    # Channel preferences (merge at channel level)
    for channel in ['in_app', 'email', 'push', 'toast']:
        if hasattr(update, f'{channel}_enabled') and getattr(update, f'{channel}_enabled') is not None:
            current_val = getattr(result, f'{channel}_enabled')
            new_val = getattr(update, f'{channel}_enabled')
            if current_val != new_val:
                changes.append((f'{channel}_enabled', current_val, new_val))
                setattr(result, f'{channel}_enabled', new_val)
        
        if hasattr(update, f'{channel}_frequency') and getattr(update, f'{channel}_frequency') is not None:
            current_val = getattr(result, f'{channel}_frequency')
            new_val = getattr(update, f'{channel}_frequency')
            if current_val != new_val:
                changes.append((f'{channel}_frequency', current_val, new_val))
                setattr(result, f'{channel}_frequency', new_val)
    
    # Notification type preferences (merge at type level)
    if update.notification_types:
        for notif_type, settings in update.notification_types.items():
            if notif_type not in result.notification_types:
                result.notification_types[notif_type] = settings
                changes.append((f'notification_types.{notif_type}', None, settings))
            else:
                for key, value in settings.items():
                    if result.notification_types[notif_type].get(key) != value:
                        changes.append(
                            (f'notification_types.{notif_type}.{key}',
                             result.notification_types[notif_type].get(key),
                             value)
                        )
                        result.notification_types[notif_type][key] = value
    
    result.changes = changes
    return result
```

## 2.4 Preference Inheritance Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PREFERENCE HIERARCHY (Priority: High → Low)          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  LEVEL 1: GLOBAL ENABLE/DISABLE                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  global_enabled = false                                          │    │
│  │  → ALL notifications disabled regardless of lower-level settings │    │
│  │  → User must explicitly re-enable at global level first         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                          │                                               │
│                          ▼ (if global_enabled = true)                    │
│  LEVEL 2: NOTIFICATION TYPE TOGGLES                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  notification_types[type].enabled = false                       │    │
│  │  → That notification type disabled across ALL channels          │    │
│  │  → Example: Disable "order_updates" → no email/push/in-app      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                          │                                               │
│                          ▼ (if type enabled)                             │
│  LEVEL 3: CHANNEL TOGGLES                                                │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  {channel}_enabled = false                                       │    │
│  │  → That channel disabled for ALL notification types             │    │
│  │  → Example: Disable email → no emails for any notification type │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                          │                                               │
│                          ▼ (if channel enabled)                          │
│  LEVEL 4: TYPE-CHANNEL OVERRIDE                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  notification_types[type].channels[channel].enabled = false     │    │
│  │  → Specific type disabled for specific channel                  │    │
│  │  → Example: Disable "promotional" on "email" but keep "push"    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                          │                                               │
│                          ▼ (if all enabled)                              │
│  LEVEL 5: FREQUENCY SETTINGS                                             │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  {channel}_frequency = "daily_digest"                            │    │
│  │  → Controls batching/delivery timing                            │    │
│  │  → Options: real_time, daily_digest, weekly_summary, disabled  │    │
│  │  → If channel disabled, frequency is irrelevant                 │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Decision Tree for Notification Dispatch

```python
def should_send_notification(
    recipient_id: str,
    recipient_type: str,  # 'customer' or 'owner'
    notification_type: str,  # 'order_updates', 'promotional', etc.
    channel: str  # 'in_app', 'email', 'push', 'toast'
) -> tuple[bool, str]:
    """
    Evaluates the full preference hierarchy to determine if a notification
    should be sent.
    
    Returns: (should_send: bool, reason: str)
    """
    
    prefs = get_preferences(recipient_id, recipient_type)
    
    # Level 1: Global toggle
    if not prefs.global_enabled:
        return False, "Global notifications disabled"
    
    # Level 2: Notification type toggle
    type_prefs = prefs.notification_types.get(notification_type, {})
    if not type_prefs.get('enabled', True):
        return False, f"Notification type '{notification_type}' disabled"
    
    # Level 3: Channel toggle
    channel_enabled = getattr(prefs, f'{channel}_enabled', True)
    if not channel_enabled:
        return False, f"Channel '{channel}' disabled globally"
    
    # Level 4: Type-channel override
    type_channel_prefs = type_prefs.get('channels', {}).get(channel, {})
    if not type_channel_prefs.get('enabled', True):
        return False, f"Notification type '{notification_type}' disabled for channel '{channel}'"
    
    # Level 5: Frequency check
    frequency = getattr(prefs, f'{channel}_frequency', 'real_time')
    if frequency == 'disabled':
        return False, f"Frequency set to 'disabled' for channel '{channel}'"
    
    # Check frequency batching rules
    if frequency in ['daily_digest', 'weekly_summary']:
        # Add to batch queue instead of immediate dispatch
        return should_add_to_batch(prefs, notification_type, channel, frequency)
    
    return True, "All checks passed - send immediately"


def should_add_to_batch(prefs, notification_type, channel, frequency) -> tuple[bool, str]:
    """
    Determines if notification should be batched based on frequency setting.
    """
    batch_config = prefs.batch_settings.get(frequency, {})
    last_batch = batch_config.get('last_sent')
    
    if frequency == 'daily_digest':
        # Check if daily batch time has passed
        batch_time = batch_config.get('preferred_time', '18:00')
        if is_time_for_batch(batch_time, last_batch):
            return True, "Added to daily digest batch"
        return True, "Queued for next daily digest"
    
    if frequency == 'weekly_summary':
        # Check if weekly batch day has arrived
        batch_day = batch_config.get('preferred_day', 'sunday')
        if is_day_for_batch(batch_day, last_batch):
            return True, "Added to weekly summary batch"
        return True, "Queued for next weekly summary"
    
    return True, "Added to batch queue"
```

---

# 3. Database Schema

## 3.1 Core Preference Tables

```sql
-- ============================================================
-- CONFIT — Notification Preferences Schema Migration
-- Created: 2026-04-06
-- Description: Preference synchronization, versioning, and audit
-- ============================================================

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Device Registry ────────────────────────────────────────────────
-- Tracks devices that have registered for preference sync

CREATE TABLE IF NOT EXISTS public.notification_devices (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    device_id       TEXT NOT NULL,                    -- Client-generated unique ID
    device_type     TEXT NOT NULL CHECK (device_type IN ('mobile_app', 'desktop_browser', 'tablet_app', 'other')),
    device_name     TEXT,                             -- "John's iPhone", "Chrome on Windows"
    user_agent      TEXT,                             -- Full user agent string
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    registered_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, device_id)
);

CREATE INDEX IF NOT EXISTS idx_notification_devices_user_id 
    ON public.notification_devices(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_devices_device_id 
    ON public.notification_devices(device_id);

-- ── Notification Preferences ──────────────────────────────────────
-- Core preference state with versioning

CREATE TABLE IF NOT EXISTS public.notification_preferences (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_id            TEXT NOT NULL,                    -- User ID or owner ID
    recipient_type          TEXT NOT NULL CHECK (recipient_type IN ('customer', 'owner')),
    
    -- Global toggle (Level 1)
    global_enabled          BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Channel toggles (Level 3)
    in_app_enabled          BOOLEAN NOT NULL DEFAULT TRUE,
    email_enabled           BOOLEAN NOT NULL DEFAULT TRUE,
    push_enabled            BOOLEAN NOT NULL DEFAULT TRUE,
    toast_enabled           BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Frequency settings (Level 5)
    in_app_frequency        TEXT NOT NULL DEFAULT 'real_time' 
                              CHECK (in_app_frequency IN ('real_time', 'daily_digest', 'weekly_summary', 'disabled')),
    email_frequency         TEXT NOT NULL DEFAULT 'real_time' 
                              CHECK (email_frequency IN ('real_time', 'daily_digest', 'weekly_summary', 'disabled')),
    push_frequency          TEXT NOT NULL DEFAULT 'real_time' 
                              CHECK (push_frequency IN ('real_time', 'daily_digest', 'weekly_summary', 'disabled')),
    toast_frequency         TEXT NOT NULL DEFAULT 'real_time' 
                              CHECK (toast_frequency IN ('real_time', 'daily_digest', 'weekly_summary', 'disabled')),
    
    -- Notification type settings (Level 2 & 4)
    -- JSONB for flexibility: { "order_updates": { "enabled": true, "channels": { "email": { "enabled": true } } } }
    notification_types      JSONB NOT NULL DEFAULT '{}',
    
    -- Batch settings for digest/summary
    batch_settings          JSONB NOT NULL DEFAULT '{}',
    -- Example: { "daily_digest": { "preferred_time": "18:00", "last_sent": "2026-04-06T18:00:00Z" },
    --            "weekly_summary": { "preferred_day": "sunday", "preferred_time": "10:00", "last_sent": "..." } }
    
    -- Version tracking for conflict resolution
    sync_version            TEXT NOT NULL,                    -- Format: "deviceId:timestamp:sequence"
    vector_clock            JSONB NOT NULL DEFAULT '{}',      -- { "deviceA": 5, "deviceB": 3 }
    checksum                TEXT NOT NULL,                    -- SHA-256 of preference state
    last_modified           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_modified_by        TEXT NOT NULL,                    -- device_id that made last change
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(recipient_id, recipient_type)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_notification_preferences_recipient 
    ON public.notification_preferences(recipient_id, recipient_type);
CREATE INDEX IF NOT EXISTS idx_notification_preferences_sync_version 
    ON public.notification_preferences(sync_version);
CREATE INDEX IF NOT EXISTS idx_notification_preferences_last_modified 
    ON public.notification_preferences(last_modified DESC);

-- ── Preference Sync Queue ───────────────────────────────────────────
-- Pending sync operations for offline devices

CREATE TABLE IF NOT EXISTS public.notification_sync_queue (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_id    TEXT NOT NULL,
    recipient_type  TEXT NOT NULL,
    device_id       TEXT NOT NULL,
    operation_type  TEXT NOT NULL CHECK (operation_type IN ('update', 'delete', 'resync')),
    payload         JSONB NOT NULL,
    sync_version    TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    synced_at       TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'pending' 
                      CHECK (status IN ('pending', 'synced', 'failed', 'expired')),
    retry_count     INTEGER NOT NULL DEFAULT 0,
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS idx_notification_sync_queue_recipient 
    ON public.notification_sync_queue(recipient_id, recipient_type);
CREATE INDEX IF NOT EXISTS idx_notification_sync_queue_device 
    ON public.notification_sync_queue(device_id);
CREATE INDEX IF NOT EXISTS idx_notification_sync_queue_status 
    ON public.notification_sync_queue(status, created_at);

-- ── Preference Audit Log ───────────────────────────────────────────
-- Complete audit trail of all preference changes

CREATE TABLE IF NOT EXISTS public.notification_preference_audit (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_id        TEXT NOT NULL,
    recipient_type      TEXT NOT NULL,
    
    -- What changed
    change_type         TEXT NOT NULL CHECK (change_type IN ('create', 'update', 'delete', 'conflict_resolved')),
    field_path          TEXT NOT NULL,                    -- "global_enabled", "notification_types.order_updates.enabled"
    old_value           JSONB,
    new_value           JSONB,
    
    -- Who made the change
    device_id           TEXT NOT NULL,
    device_type         TEXT NOT NULL,
    ip_address          INET,
    user_agent          TEXT,
    
    -- When and why
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reason              TEXT,                             -- "user_action", "conflict_resolution", "system_reset"
    conflict_resolution TEXT,                             -- Details if this was a conflict resolution
    
    -- Version info
    sync_version_before TEXT,
    sync_version_after  TEXT,
    
    -- Retention
    retention_until     TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '2 years')
);

-- Indexes for audit queries
CREATE INDEX IF NOT EXISTS idx_notification_preference_audit_recipient 
    ON public.notification_preference_audit(recipient_id, recipient_type);
CREATE INDEX IF NOT EXISTS idx_notification_preference_audit_timestamp 
    ON public.notification_preference_audit(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_notification_preference_audit_device 
    ON public.notification_preference_audit(device_id);
CREATE INDEX IF NOT EXISTS idx_notification_preference_audit_retention 
    ON public.notification_preference_audit(retention_until);

-- ── RLS Policies ───────────────────────────────────────────────────

ALTER TABLE public.notification_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_sync_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_preference_audit ENABLE ROW LEVEL SECURITY;

-- Users can manage their own devices
CREATE POLICY "Users can manage own devices"
    ON public.notification_devices FOR ALL
    USING (auth.uid() = user_id);

-- Users can read/write own preferences
CREATE POLICY "Users can manage own preferences"
    ON public.notification_preferences FOR ALL
    USING (
        recipient_id = auth.uid()::text 
        OR EXISTS (
            SELECT 1 FROM public.user_roles ur
            WHERE ur.user_id = auth.uid() 
            AND ur.role IN ('admin', 'store_owner', 'factory_owner')
        )
    );

-- Service role can manage sync queue
CREATE POLICY "Service role can manage sync queue"
    ON public.notification_sync_queue FOR ALL
    USING (auth.role() = 'service_role');

-- Users can read own audit logs, admins can read all
CREATE POLICY "Users can read own audit logs"
    ON public.notification_preference_audit FOR SELECT
    USING (
        recipient_id = auth.uid()::text
        OR EXISTS (
            SELECT 1 FROM public.user_roles ur
            WHERE ur.user_id = auth.uid() 
            AND ur.role IN ('admin', 'analytics')
        )
    );

-- Service role can insert audit logs
CREATE POLICY "Service role can insert audit logs"
    ON public.notification_preference_audit FOR INSERT
    WITH (auth.role() = 'service_role');

-- ── Functions ──────────────────────────────────────────────────────

-- Calculate preference checksum
CREATE OR REPLACE FUNCTION public.calculate_preference_checksum(
    p_preferences JSONB
) RETURNS TEXT AS $$
BEGIN
    RETURN encode(
        sha256(p_preferences::text::bytea),
        'hex'
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Get effective preferences (resolved hierarchy)
CREATE OR REPLACE FUNCTION public.get_effective_preferences(
    p_recipient_id TEXT,
    p_recipient_type TEXT,
    p_notification_type TEXT DEFAULT NULL,
    p_channel TEXT DEFAULT NULL
) RETURNS JSONB AS $$
DECLARE
    prefs RECORD;
    result JSONB := '{}';
BEGIN
    SELECT * INTO prefs
    FROM public.notification_preferences
    WHERE recipient_id = p_recipient_id
      AND recipient_type = p_recipient_type;
    
    IF NOT FOUND THEN
        -- Return defaults
        RETURN jsonb_build_object(
            'global_enabled', true,
            'channels', jsonb_build_object(
                'in_app', jsonb_build_object('enabled', true, 'frequency', 'real_time'),
                'email', jsonb_build_object('enabled', true, 'frequency', 'real_time'),
                'push', jsonb_build_object('enabled', true, 'frequency', 'real_time'),
                'toast', jsonb_build_object('enabled', true, 'frequency', 'real_time')
            ),
            'notification_types', '{}'
        );
    END IF;
    
    -- Build result with hierarchy applied
    result := jsonb_build_object(
        'global_enabled', prefs.global_enabled,
        'channels', jsonb_build_object(
            'in_app', jsonb_build_object(
                'enabled', prefs.in_app_enabled,
                'frequency', prefs.in_app_frequency
            ),
            'email', jsonb_build_object(
                'enabled', prefs.email_enabled,
                'frequency', prefs.email_frequency
            ),
            'push', jsonb_build_object(
                'enabled', prefs.push_enabled,
                'frequency', prefs.push_frequency
            ),
            'toast', jsonb_build_object(
                'enabled', prefs.toast_enabled,
                'frequency', prefs.toast_frequency
            )
        ),
        'notification_types', prefs.notification_types,
        'batch_settings', prefs.batch_settings,
        'sync_version', prefs.sync_version,
        'last_modified', prefs.last_modified
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ── Triggers ────────────────────────────────────────────────────────

-- Auto-update updated_at
CREATE TRIGGER trg_notification_preferences_updated_at
    BEFORE UPDATE ON public.notification_preferences
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ── Comments for Documentation ──────────────────────────────────────

COMMENT ON TABLE public.notification_devices IS 
    'Registry of devices that have synced notification preferences';

COMMENT ON TABLE public.notification_preferences IS 
    'Core notification preference state with version tracking for conflict resolution';

COMMENT ON TABLE public.notification_sync_queue IS 
    'Queue of pending sync operations for offline devices';

COMMENT ON TABLE public.notification_preference_audit IS 
    'Complete audit trail of all preference modifications with 2-year retention';

-- ── Grants ──────────────────────────────────────────────────────────

GRANT SELECT ON public.notification_preferences TO authenticated;
GRANT SELECT ON public.notification_devices TO authenticated;
GRANT SELECT ON public.notification_preference_audit TO authenticated;
GRANT ALL ON public.notification_preferences TO service_role;
GRANT ALL ON public.notification_devices TO service_role;
GRANT ALL ON public.notification_sync_queue TO service_role;
GRANT ALL ON public.notification_preference_audit TO service_role;
```

## 3.2 Schema Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATABASE SCHEMA RELATIONSHIPS                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────┐         ┌──────────────────────────────────────┐  │
│  │ notification_devices │         │      notification_preferences        │  │
│  ├──────────────────────┤         ├──────────────────────────────────────┤  │
│  │ id (PK)              │         │ id (PK)                              │  │
│  │ user_id (FK→auth)    │         │ recipient_id                         │  │
│  │ device_id            │◄────────│ recipient_type                       │  │
│  │ device_type          │         │ global_enabled                       │  │
│  │ device_name          │         │ in_app_enabled, email_enabled, ...   │  │
│  │ user_agent           │         │ in_app_frequency, email_frequency... │  │
│  │ last_seen_at         │         │ notification_types (JSONB)           │  │
│  │ registered_at        │         │ batch_settings (JSONB)               │  │
│  └──────────────────────┘         │ sync_version                         │  │
│                                   │ vector_clock (JSONB)                 │  │
│                                   │ checksum                             │  │
│                                   │ last_modified                        │  │
│                                   │ last_modified_by → device_id         │──┼─┐
│                                   └──────────────────────────────────────┘  │ │
│                                                                              │ │
│  ┌──────────────────────┐         ┌──────────────────────────────────────┐  │ │
│  │ notification_sync_   │         │ notification_preference_audit        │  │ │
│  │ queue                │         ├──────────────────────────────────────┤  │ │
│  ├──────────────────────┤         │ id (PK)                              │  │ │
│  │ id (PK)              │         │ recipient_id                         │  │ │
│  │ recipient_id         │         │ recipient_type                       │  │ │
│  │ recipient_type       │         │ change_type                          │  │ │
│  │ device_id            │         │ field_path                           │  │ │
│  │ operation_type       │         │ old_value (JSONB)                    │  │ │
│  │ payload (JSONB)      │         │ new_value (JSONB)                    │  │ │
│  │ sync_version         │         │ device_id                            │◄─┼─┘
│  │ status               │         │ device_type                          │  │
│  │ retry_count          │         │ ip_address                           │  │
│  │ error_message        │         │ user_agent                           │  │
│  └──────────────────────┘         │ timestamp                            │  │
│                                   │ reason                               │  │
│                                   │ conflict_resolution                  │  │
│                                   │ sync_version_before                  │  │
│                                   │ sync_version_after                   │  │
│                                   │ retention_until                      │  │
│                                   └──────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 4. API Contracts

## 4.1 Preference Update API

### Request

```typescript
// POST /api/v1/notifications/preferences
// Content-Type: application/json
// Authorization: Bearer <jwt>
// X-Idempotency-Key: <uuid>  // Optional, for retry safety

interface PreferenceUpdateRequest {
  // Device identification
  device_id: string;              // Client-generated unique device ID
  device_type: 'mobile_app' | 'desktop_browser' | 'tablet_app' | 'other';
  device_name?: string;           // "John's iPhone 15"
  
  // Version tracking for conflict detection
  base_sync_version: string;      // Current version client knows about
  base_checksum: string;          // SHA-256 of client's current state
  
  // Preferences to update (partial updates supported)
  preferences: {
    global_enabled?: boolean;
    
    // Channel toggles
    in_app_enabled?: boolean;
    email_enabled?: boolean;
    push_enabled?: boolean;
    toast_enabled?: boolean;
    
    // Frequency settings
    in_app_frequency?: 'real_time' | 'daily_digest' | 'weekly_summary' | 'disabled';
    email_frequency?: 'real_time' | 'daily_digest' | 'weekly_summary' | 'disabled';
    push_frequency?: 'real_time' | 'daily_digest' | 'weekly_summary' | 'disabled';
    toast_frequency?: 'real_time' | 'daily_digest' | 'weekly_summary' | 'disabled';
    
    // Notification type settings
    notification_types?: {
      [type: string]: {
        enabled?: boolean;
        channels?: {
          [channel: string]: {
            enabled?: boolean;
          };
        };
      };
    };
    
    // Batch settings
    batch_settings?: {
      daily_digest?: {
        preferred_time?: string;    // "18:00"
      };
      weekly_summary?: {
        preferred_day?: string;    // "sunday"
        preferred_time?: string;   // "10:00"
      };
    };
  };
  
  // Client timestamp for conflict resolution
  client_timestamp: string;       // ISO 8601
}
```

### Response

```typescript
// Success (200 OK)
interface PreferenceUpdateResponse {
  success: true;
  data: {
    preferences: PreferenceState;
    sync_version: string;         // New version after update
    checksum: string;             // New checksum
    last_modified: string;        // ISO 8601
    changes_applied: Array<{
      field: string;
      old_value: any;
      new_value: any;
    }>;
  };
}

// Conflict Detected (409 Conflict)
interface PreferenceConflictResponse {
  success: false;
  error: {
    code: 'CONFLICT_DETECTED';
    message: 'Your preferences were updated on another device';
    conflict_type: 'VERSION_STALE' | 'CONCURRENT_UPDATE' | 'CHECKSUM_MISMATCH';
    current_server_state: PreferenceState;
    server_sync_version: string;
    server_checksum: string;
    resolution?: {
      type: 'server_wins' | 'client_wins' | 'merged';
      details: string;
    };
  };
}

// Validation Error (400 Bad Request)
interface PreferenceValidationErrorResponse {
  success: false;
  error: {
    code: 'VALIDATION_ERROR';
    message: 'Invalid preference values';
    details: Array<{
      field: string;
      message: string;
      value?: any;
    }>;
  };
}

// Rate Limited (429 Too Many Requests)
interface PreferenceRateLimitResponse {
  success: false;
  error: {
    code: 'RATE_LIMITED';
    message: 'Too many preference updates. Please wait before trying again.';
    retry_after: number;         // Seconds until retry is allowed
  };
}
```

## 4.2 Preference Query API

### Get Current Preferences

```typescript
// GET /api/v1/notifications/preferences
// Authorization: Bearer <jwt>
// X-Device-ID: <device_id>  // Optional, for last-seen tracking

interface PreferenceQueryResponse {
  success: true;
  data: {
    preferences: PreferenceState;
    sync_version: string;
    checksum: string;
    last_modified: string;
    
    // For conflict detection on updates
    vector_clock: { [device_id: string]: number };
    
    // Device info
    registered_devices: Array<{
      device_id: string;
      device_type: string;
      device_name: string;
      last_seen_at: string;
      is_current: boolean;
    }>;
  };
}

interface PreferenceState {
  global_enabled: boolean;
  
  channels: {
    in_app: { enabled: boolean; frequency: string; };
    email: { enabled: boolean; frequency: string; };
    push: { enabled: boolean; frequency: string; };
    toast: { enabled: boolean; frequency: string; };
  };
  
  notification_types: {
    [type: string]: {
      enabled: boolean;
      channels?: {
        [channel: string]: {
          enabled: boolean;
        };
      };
    };
  };
  
  batch_settings: {
    daily_digest?: {
      preferred_time: string;
      last_sent?: string;
    };
    weekly_summary?: {
      preferred_day: string;
      preferred_time: string;
      last_sent?: string;
    };
  };
}
```

### Get Effective Preferences (for NotificationService)

```typescript
// GET /api/v1/notifications/preferences/:recipient_id/effective
// Authorization: Bearer <service_jwt>
// Query params: ?recipient_type=customer|owner&notification_type=order_updates&channel=email

interface EffectivePreferenceResponse {
  success: true;
  data: {
    should_send: boolean;
    reason: string;
    
    // Resolved settings
    effective_settings: {
      global_enabled: boolean;
      type_enabled: boolean;
      channel_enabled: boolean;
      frequency: string;
    };
    
    // Cache info
    cache_hit: boolean;
    cache_age_ms: number;
  };
}
```

## 4.3 Device Management API

### Register Device

```typescript
// POST /api/v1/notifications/devices
// Authorization: Bearer <jwt>

interface DeviceRegistrationRequest {
  device_id: string;
  device_type: 'mobile_app' | 'desktop_browser' | 'tablet_app' | 'other';
  device_name?: string;
  user_agent?: string;
  push_token?: string;           // FCM/APNS token for push notifications
}

interface DeviceRegistrationResponse {
  success: true;
  data: {
    device_id: string;
    registered_at: string;
    is_new_device: boolean;
  };
}
```

### List Devices

```typescript
// GET /api/v1/notifications/devices
// Authorization: Bearer <jwt>

interface DeviceListResponse {
  success: true;
  data: {
    devices: Array<{
      device_id: string;
      device_type: string;
      device_name: string;
      last_seen_at: string;
      registered_at: string;
      is_current: boolean;       // Matches X-Device-ID header
    }>;
    total_count: number;
  };
}
```

### Remove Device

```typescript
// DELETE /api/v1/notifications/devices/:device_id
// Authorization: Bearer <jwt>

interface DeviceRemovalResponse {
  success: true;
  data: {
    removed_device_id: string;
    removed_at: string;
  };
}
```

## 4.4 Audit Log API

### Query Audit Logs

```typescript
// GET /api/v1/notifications/preferences/audit
// Authorization: Bearer <jwt> (users see own logs, admins see all)
// Query params: ?start_date=2026-01-01&end_date=2026-04-06&device_id=xxx&change_type=update

interface AuditLogQueryResponse {
  success: true;
  data: {
    logs: Array<{
      id: string;
      timestamp: string;
      change_type: 'create' | 'update' | 'delete' | 'conflict_resolved';
      field_path: string;
      old_value: any;
      new_value: any;
      device_id: string;
      device_type: string;
      ip_address: string;
      reason: string;
      conflict_resolution?: string;
    }>;
    pagination: {
      total: number;
      page: number;
      per_page: number;
      has_more: boolean;
    };
  };
}
```

### Export Audit Logs

```typescript
// GET /api/v1/notifications/preferences/audit/export
// Authorization: Bearer <jwt>
// Accept: text/csv | application/json

// Returns CSV or JSON file download
```

## 4.5 Error Codes Reference

| Code | HTTP Status | Description | User Message |
|------|-------------|-------------|--------------|
| `VALIDATION_ERROR` | 400 | Invalid preference values | "Please check your settings and try again" |
| `UNAUTHORIZED` | 401 | Missing or invalid JWT | "Please log in to continue" |
| `FORBIDDEN` | 403 | Not allowed to modify these preferences | "You don't have permission to change these settings" |
| `NOT_FOUND` | 404 | Preferences not found | "Settings not found. They will be created on first update." |
| `CONFLICT_DETECTED` | 409 | Concurrent update conflict | "Your settings were updated on another device. Please review." |
| `VERSION_STALE` | 409 | Client version is outdated | "Please refresh your settings and try again" |
| `CHECKSUM_MISMATCH` | 409 | Data integrity issue | "Your settings are out of sync. Please refresh." |
| `RATE_LIMITED` | 429 | Too many updates | "Too many changes. Please wait a moment." |
| `INTERNAL_ERROR` | 500 | Server error | "Something went wrong. Please try again." |
| `SERVICE_UNAVAILABLE` | 503 | Preference service down | "Settings are temporarily unavailable. Using cached values." |

---

# 5. NotificationService Integration

## 5.1 Preference Query Before Dispatch

```python
# backend/services/notification/dispatcher.py

from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from core.cache import CacheManager
from core.circuit_breaker import CircuitBreaker


class DispatchDecision(Enum):
    SEND_IMMEDIATELY = "send_immediately"
    ADD_TO_BATCH = "add_to_batch"
    SKIP_DISABLED = "skip_disabled"
    SKIP_FREQUENCY = "skip_frequency"


@dataclass
class PreferenceCheckResult:
    decision: DispatchDecision
    reason: str
    effective_settings: dict
    cache_hit: bool
    cache_age_ms: int
    fallback_used: bool


class PreferenceAwareDispatcher:
    """
    Notification dispatcher that queries and respects user preferences
    before every dispatch decision.
    """
    
    PREFERENCE_CACHE_TTL = 300  # 5 minutes
    PREFERENCE_QUERY_TIMEOUT = 0.5  # 500ms max for preference query
    CIRCUIT_BREAKER_THRESHOLD = 5  # Open after 5 failures
    CIRCUIT_BREAKER_RESET_TIMEOUT = 60  # Reset after 60 seconds
    
    def __init__(
        self,
        db: AsyncSession,
        cache: CacheManager,
        redis: redis.Redis,
        event_publisher: EventPublisher
    ):
        self.db = db
        self.cache = cache
        self.redis = redis
        self.event_publisher = event_publisher
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.CIRCUIT_BREAKER_THRESHOLD,
            reset_timeout=self.CIRCUIT_BREAKER_RESET_TIMEOUT
        )
    
    async def check_preferences(
        self,
        recipient_id: str,
        recipient_type: str,
        notification_type: str,
        channel: str
    ) -> PreferenceCheckResult:
        """
        Query current preferences and determine dispatch decision.
        Implements cache-first strategy with fallback to defaults.
        """
        
        cache_key = self._build_cache_key(recipient_id, recipient_type)
        cache_hit = False
        cache_age_ms = 0
        fallback_used = False
        
        # Step 1: Try cache first (fastest path)
        cached_prefs = await self._get_from_cache(cache_key)
        if cached_prefs:
            cache_hit = True
            cache_age_ms = int((datetime.utcnow() - cached_prefs['cached_at']).total_seconds() * 1000)
            prefs = cached_prefs['preferences']
        else:
            # Step 2: Query database with timeout
            try:
                prefs = await self._query_preferences_with_timeout(
                    recipient_id, recipient_type
                )
                # Cache the result
                await self._set_cache(cache_key, prefs)
            except asyncio.TimeoutError:
                # Step 3: Fallback to stale cache or defaults
                fallback_used = True
                prefs = await self._get_fallback_preferences(cache_key)
            except Exception as e:
                # Circuit breaker logic
                self.circuit_breaker.record_failure()
                fallback_used = True
                prefs = await self._get_fallback_preferences(cache_key)
        
        # Step 4: Evaluate preference hierarchy
        decision, reason = self._evaluate_hierarchy(
            prefs, notification_type, channel
        )
        
        return PreferenceCheckResult(
            decision=decision,
            reason=reason,
            effective_settings=prefs,
            cache_hit=cache_hit,
            cache_age_ms=cache_age_ms,
            fallback_used=fallback_used
        )
    
    async def dispatch(
        self,
        recipient_id: str,
        recipient_type: str,
        notification_type: str,
        channel: str,
        payload: dict
    ) -> bool:
        """
        Main dispatch method that respects preferences.
        Returns True if notification was sent/queued, False otherwise.
        """
        
        # Circuit breaker check
        if self.circuit_breaker.is_open():
            # Queue for later retry
            await self._queue_for_retry(
                recipient_id, recipient_type, notification_type, 
                channel, payload
            )
            return False
        
        # Check preferences
        pref_check = await self.check_preferences(
            recipient_id, recipient_type, notification_type, channel
        )
        
        # Log the check for analytics
        await self._log_preference_check(pref_check, notification_type, channel)
        
        if pref_check.decision == DispatchDecision.SKIP_DISABLED:
            # Preference disabled - don't send
            logger.info(
                "Notification skipped due to preference",
                extra={
                    'recipient_id': recipient_id,
                    'notification_type': notification_type,
                    'channel': channel,
                    'reason': pref_check.reason
                }
            )
            return False
        
        if pref_check.decision == DispatchDecision.SKIP_FREQUENCY:
            # Frequency setting prevents immediate dispatch
            logger.info(
                "Notification skipped due to frequency setting",
                extra={
                    'recipient_id': recipient_id,
                    'notification_type': notification_type,
                    'channel': channel,
                    'reason': pref_check.reason
                }
            )
            return False
        
        if pref_check.decision == DispatchDecision.ADD_TO_BATCH:
            # Add to batch queue
            await self._add_to_batch(
                recipient_id, recipient_type, notification_type,
                channel, payload, pref_check.effective_settings
            )
            return True
        
        # Dispatch immediately
        await self._send_immediately(
            recipient_id, recipient_type, channel, payload
        )
        return True
    
    def _evaluate_hierarchy(
        self,
        prefs: dict,
        notification_type: str,
        channel: str
    ) -> Tuple[DispatchDecision, str]:
        """
        Evaluate the full preference hierarchy.
        Returns (decision, reason) tuple.
        """
        
        # Level 1: Global toggle
        if not prefs.get('global_enabled', True):
            return DispatchDecision.SKIP_DISABLED, "Global notifications disabled"
        
        # Level 2: Notification type toggle
        type_settings = prefs.get('notification_types', {}).get(notification_type, {})
        if not type_settings.get('enabled', True):
            return DispatchDecision.SKIP_DISABLED, f"Notification type '{notification_type}' disabled"
        
        # Level 3: Channel toggle
        channel_settings = prefs.get('channels', {}).get(channel, {})
        if not channel_settings.get('enabled', True):
            return DispatchDecision.SKIP_DISABLED, f"Channel '{channel}' disabled"
        
        # Level 4: Type-channel override
        type_channel_settings = type_settings.get('channels', {}).get(channel, {})
        if not type_channel_settings.get('enabled', True):
            return DispatchDecision.SKIP_DISABLED, f"Type '{notification_type}' disabled for channel '{channel}'"
        
        # Level 5: Frequency check
        frequency = channel_settings.get('frequency', 'real_time')
        
        if frequency == 'disabled':
            return DispatchDecision.SKIP_FREQUENCY, f"Frequency set to 'disabled' for channel '{channel}'"
        
        if frequency == 'real_time':
            return DispatchDecision.SEND_IMMEDIATELY, "All checks passed - send immediately"
        
        # Batch frequency (daily_digest, weekly_summary)
        return DispatchDecision.ADD_TO_BATCH, f"Queued for {frequency}"
    
    def _build_cache_key(self, recipient_id: str, recipient_type: str) -> str:
        return f"notif:prefs:{recipient_type}:{recipient_id}"
    
    async def _get_from_cache(self, key: str) -> Optional[dict]:
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")
        return None
    
    async def _set_cache(self, key: str, prefs: dict) -> None:
        try:
            cache_data = {
                'preferences': prefs,
                'cached_at': datetime.utcnow().isoformat()
            }
            await self.redis.setex(
                key, 
                self.PREFERENCE_CACHE_TTL, 
                json.dumps(cache_data)
            )
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")
    
    async def _query_preferences_with_timeout(
        self, 
        recipient_id: str, 
        recipient_type: str
    ) -> dict:
        """
        Query preferences from database with timeout.
        """
        
        async with asyncio.timeout(self.PREFERENCE_QUERY_TIMEOUT):
            result = await self.db.execute(
                text("""
                    SELECT * FROM get_effective_preferences(
                        :recipient_id, :recipient_type
                    )
                """),
                {
                    'recipient_id': recipient_id,
                    'recipient_type': recipient_type
                }
            )
            row = result.fetchone()
            if row:
                return row[0]
            
            # Return defaults if not found
            return self._get_default_preferences()
    
    async def _get_fallback_preferences(self, cache_key: str) -> dict:
        """
        Get fallback preferences when DB query fails.
        Priority: stale cache → defaults
        """
        
        # Try stale cache (ignore TTL)
        try:
            stale_key = f"{cache_key}:stale"
            data = await self.redis.get(stale_key)
            if data:
                logger.info("Using stale cache for preferences")
                return json.loads(data)
        except Exception:
            pass
        
        # Return defaults
        logger.info("Using default preferences as fallback")
        return self._get_default_preferences()
    
    def _get_default_preferences(self) -> dict:
        """
        Default preferences when user has no custom settings.
        """
        return {
            'global_enabled': True,
            'channels': {
                'in_app': {'enabled': True, 'frequency': 'real_time'},
                'email': {'enabled': True, 'frequency': 'real_time'},
                'push': {'enabled': True, 'frequency': 'real_time'},
                'toast': {'enabled': True, 'frequency': 'real_time'}
            },
            'notification_types': {},
            'batch_settings': {}
        }
```

## 5.2 Cache Invalidation on Update

```python
# backend/services/notification/preference_service.py

class PreferenceService:
    """
    Service for managing notification preferences with cache invalidation.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        redis: redis.Redis,
        event_publisher: EventPublisher
    ):
        self.db = db
        self.redis = redis
        self.event_publisher = event_publisher
    
    async def update_preferences(
        self,
        recipient_id: str,
        recipient_type: str,
        update: PreferenceUpdateRequest,
        ip_address: str,
        user_agent: str
    ) -> PreferenceUpdateResult:
        """
        Update preferences with conflict detection and cache invalidation.
        """
        
        # Step 1: Get current preferences
        current = await self._get_current_preferences(recipient_id, recipient_type)
        
        # Step 2: Detect conflicts
        conflict = self.conflict_resolver.detect_conflict(update, current)
        
        if conflict == ConflictType.VERSION_STALE:
            return PreferenceUpdateResult.rejected(
                reason="Client version is stale",
                current_state=current
            )
        
        if conflict == ConflictType.CHECKSUM_MISMATCH:
            return PreferenceUpdateResult.force_resync(
                reason="Client state diverged",
                current_state=current
            )
        
        # Step 3: Apply update with conflict resolution
        new_prefs, changes = self.conflict_resolver.merge_update(
            current, update, conflict
        )
        
        # Step 4: Persist to database
        async with self.db.begin():
            await self._save_preferences(recipient_id, recipient_type, new_prefs)
            
            # Step 5: Create audit log
            await self._create_audit_log(
                recipient_id, recipient_type, changes,
                update.device_id, update.device_type,
                ip_address, user_agent, conflict
            )
        
        # Step 6: Invalidate cache across all instances
        await self._invalidate_cache(recipient_id, recipient_type)
        
        # Step 7: Publish invalidation event
        await self.event_publisher.publish(
            'preference.updated',
            {
                'recipient_id': recipient_id,
                'recipient_type': recipient_type,
                'sync_version': new_prefs['sync_version'],
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        
        return PreferenceUpdateResult.success(
            preferences=new_prefs,
            changes=changes
        )
    
    async def _invalidate_cache(
        self, 
        recipient_id: str, 
        recipient_type: str
    ) -> None:
        """
        Invalidate preference cache across all service instances.
        Uses Redis Pub/Sub for immediate propagation.
        """
        
        cache_key = f"notif:prefs:{recipient_type}:{recipient_id}"
        
        # Delete cache entry
        await self.redis.delete(cache_key)
        
        # Publish invalidation event to all instances
        await self.redis.publish(
            'preference:invalidate',
            json.dumps({
                'recipient_id': recipient_id,
                'recipient_type': recipient_type,
                'timestamp': datetime.utcnow().isoformat()
            })
        )
        
        logger.info(
            "Preference cache invalidated",
            extra={
                'recipient_id': recipient_id,
                'recipient_type': recipient_type
            }
        )
```

## 5.3 Cache Invalidation Listener

```python
# backend/services/notification/cache_listener.py

class PreferenceCacheListener:
    """
    Listens for preference invalidation events and refreshes local cache.
    Runs as a background task on each service instance.
    """
    
    def __init__(self, redis: redis.Redis, cache: CacheManager):
        self.redis = redis
        self.cache = cache
        self.pubsub = None
    
    async def start(self):
        """Start listening for invalidation events."""
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe('preference:invalidate')
        
        async for message in self.pubsub.listen():
            if message['type'] == 'message':
                await self._handle_invalidation(message)
    
    async def _handle_invalidation(self, message: dict):
        """Handle a cache invalidation event."""
        try:
            data = json.loads(message['data'])
            recipient_id = data['recipient_id']
            recipient_type = data['recipient_type']
            
            cache_key = f"notif:prefs:{recipient_type}:{recipient_id}"
            
            # Remove from local cache
            self.cache.delete(cache_key)
            
            logger.info(
                "Received cache invalidation event",
                extra={
                    'recipient_id': recipient_id,
                    'recipient_type': recipient_type
                }
            )
        except Exception as e:
            logger.error(f"Failed to handle invalidation: {e}")
```

---

# 6. Client-Side State Management

## 6.1 Optimistic Update Pattern

```typescript
// src/hooks/useNotificationPreferences.ts

import { useState, useCallback, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { notificationApi } from '@/api/notifications';

interface OptimisticPreferenceState {
  // Persisted state (from server)
  persisted: PreferenceState | null;
  
  // Optimistic state (local changes pending)
  optimistic: PreferenceState | null;
  
  // Pending operations queue
  pending: PendingOperation[];
  
  // Sync status
  isSyncing: boolean;
  lastSyncAt: Date | null;
  syncError: Error | null;
}

interface PendingOperation {
  id: string;
  type: 'update';
  payload: Partial<PreferenceState>;
  timestamp: Date;
  retryCount: number;
  status: 'pending' | 'syncing' | 'failed' | 'completed';
}

export function useNotificationPreferences() {
  const queryClient = useQueryClient();
  const deviceId = useDeviceId();
  const retryTimeoutRef = useRef<NodeJS.Timeout>();
  
  // Track optimistic state separately from persisted state
  const [optimisticState, setOptimisticState] = useState<PreferenceState | null>(null);
  const [pendingOperations, setPendingOperations] = useState<PendingOperation[]>([]);
  const [syncError, setSyncError] = useState<Error | null>(null);
  
  // Fetch current preferences from server
  const { data: serverData, isLoading } = useQuery({
    queryKey: ['notification-preferences'],
    queryFn: () => notificationApi.getPreferences(deviceId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
  
  // Persisted state from server
  const persistedState = serverData?.preferences;
  
  // Effective state = optimistic overrides persisted
  const effectiveState = optimisticState ?? persistedState;
  
  // Update mutation with optimistic update
  const updateMutation = useMutation({
    mutationFn: async (update: Partial<PreferenceState>) => {
      return notificationApi.updatePreferences({
        device_id: deviceId,
        device_type: getDeviceType(),
        base_sync_version: serverData?.sync_version ?? '',
        base_checksum: serverData?.checksum ?? '',
        client_timestamp: new Date().toISOString(),
        preferences: update,
      });
    },
    
    // Optimistic update - apply immediately before server response
    onMutate: async (update) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['notification-preferences'] });
      
      // Snapshot previous state for rollback
      const previousOptimistic = optimisticState;
      
      // Apply optimistic update
      const newOptimistic = applyPartialUpdate(effectiveState, update);
      setOptimisticState(newOptimistic);
      
      // Add to pending queue
      const operation: PendingOperation = {
        id: generateOperationId(),
        type: 'update',
        payload: update,
        timestamp: new Date(),
        retryCount: 0,
        status: 'syncing',
      };
      setPendingOperations(prev => [...prev, operation]);
      
      // Clear any previous error
      setSyncError(null);
      
      return { previousOptimistic, operation };
    },
    
    // Success - merge server response
    onSuccess: (data, variables, context) => {
      // Update persisted state with server response
      queryClient.setQueryData(['notification-preferences'], data);
      
      // Clear optimistic state (server state is now authoritative)
      setOptimisticState(null);
      
      // Mark operation as completed
      setPendingOperations(prev => 
        prev.map(op => 
          op.id === context.operation.id 
            ? { ...op, status: 'completed' } 
            : op
        )
      );
      
      // Remove completed operations after delay
      setTimeout(() => {
        setPendingOperations(prev => 
          prev.filter(op => op.id !== context.operation.id)
        );
      }, 1000);
    },
    
    // Error - rollback and show error
    onError: (error, variables, context) => {
      // Rollback optimistic state
      setOptimisticState(context.previousOptimistic);
      
      // Mark operation as failed
      setPendingOperations(prev => 
        prev.map(op => 
          op.id === context.operation.id 
            ? { ...op, status: 'failed' } 
            : op
        )
      );
      
      // Handle specific error types
      if (error instanceof ConflictError) {
        // Server has newer state - force resync
        handleConflictError(error);
      } else if (error instanceof NetworkError) {
        // Network issue - queue for retry
        scheduleRetry(context.operation);
      } else {
        // Other error - show to user
        setSyncError(error);
      }
    },
  });
  
  // Retry with exponential backoff
  const scheduleRetry = useCallback((operation: PendingOperation) => {
    const maxRetries = 3;
    const baseDelay = 1000; // 1 second
    
    if (operation.retryCount >= maxRetries) {
      // Max retries exceeded - show error
      setSyncError(new Error('Unable to sync preferences. Please try manually.'));
      return;
    }
    
    const delay = baseDelay * Math.pow(2, operation.retryCount);
    
    retryTimeoutRef.current = setTimeout(() => {
      // Update retry count
      setPendingOperations(prev => 
        prev.map(op => 
          op.id === operation.id 
            ? { ...op, retryCount: op.retryCount + 1, status: 'syncing' } 
            : op
        )
      );
      
      // Retry the operation
      updateMutation.mutate(operation.payload);
    }, delay);
  }, [updateMutation]);
  
  // Handle conflict error - server has newer state
  const handleConflictError = useCallback((error: ConflictError) => {
    // Show conflict resolution UI
    toast.show({
      type: 'warning',
      title: 'Settings updated elsewhere',
      message: 'Your notification settings were changed on another device. Your changes have been reverted.',
      actions: [
        {
          label: 'View current settings',
          onClick: () => {
            // Force refetch to get latest state
            queryClient.invalidateQueries({ queryKey: ['notification-preferences'] });
            setOptimisticState(null);
          }
        }
      ]
    });
  }, [queryClient]);
  
  // Update preference with optimistic UI
  const updatePreference = useCallback(
    (update: Partial<PreferenceState>) => {
      updateMutation.mutate(update);
    },
    [updateMutation]
  );
  
  // Manual retry for failed operations
  const retryFailedOperations = useCallback(() => {
    const failedOps = pendingOperations.filter(op => op.status === 'failed');
    failedOps.forEach(op => {
      updateMutation.mutate(op.payload);
    });
  }, [pendingOperations, updateMutation]);
  
  // Clear error and reset
  const clearError = useCallback(() => {
    setSyncError(null);
    setOptimisticState(null);
    setPendingOperations([]);
  }, []);
  
  return {
    // State
    preferences: effectiveState,
    persistedPreferences: persistedState,
    isPending: pendingOperations.some(op => op.status === 'syncing'),
    hasFailedOperations: pendingOperations.some(op => op.status === 'failed'),
    syncError,
    isLoading,
    
    // Actions
    updatePreference,
    retryFailedOperations,
    clearError,
    refresh: () => queryClient.invalidateQueries({ queryKey: ['notification-preferences'] }),
  };
}

// Helper to apply partial update
function applyPartialUpdate(
  current: PreferenceState | null,
  update: Partial<PreferenceState>
): PreferenceState {
  const base = current ?? getDefaultPreferences();
  
  return {
    ...base,
    ...update,
    notification_types: {
      ...base.notification_types,
      ...(update.notification_types ?? {}),
    },
    batch_settings: {
      ...base.batch_settings,
      ...(update.batch_settings ?? {}),
    },
  };
}
```

## 6.2 Offline Queue for Network Failures

```typescript
// src/services/offlinePreferenceQueue.ts

import { openDB, DBSchema, IDBPDatabase } from 'idb';

interface OfflineQueueDB extends DBSchema {
  pendingUpdates: {
    key: string;
    value: {
      id: string;
      payload: any;
      timestamp: Date;
      retryCount: number;
    };
  };
}

class OfflinePreferenceQueue {
  private db: IDBPDatabase<OfflineQueueDB> | null = null;
  private syncInProgress = false;
  
  async init() {
    this.db = await openDB<OfflineQueueDB>('confit-offline-queue', 1, {
      upgrade(db) {
        db.createObjectStore('pendingUpdates', { keyPath: 'id' });
      },
    });
    
    // Listen for online event to trigger sync
    window.addEventListener('online', () => this.syncPendingUpdates());
  }
  
  async enqueue(update: Partial<PreferenceState>): Promise<string> {
    const id = generateOperationId();
    
    await this.db?.put('pendingUpdates', {
      id,
      payload: update,
      timestamp: new Date(),
      retryCount: 0,
    });
    
    // Try to sync immediately if online
    if (navigator.onLine) {
      this.syncPendingUpdates();
    }
    
    return id;
  }
  
  async syncPendingUpdates(): Promise<void> {
    if (this.syncInProgress || !navigator.onLine) return;
    
    this.syncInProgress = true;
    
    try {
      const pending = await this.db?.getAll('pendingUpdates') ?? [];
      
      for (const item of pending) {
        try {
          await notificationApi.updatePreferences({
            ...item.payload,
            client_timestamp: item.timestamp.toISOString(),
          });
          
          // Success - remove from queue
          await this.db?.delete('pendingUpdates', item.id);
        } catch (error) {
          if (error instanceof ConflictError) {
            // Conflict - remove from queue, user must resolve
            await this.db?.delete('pendingUpdates', item.id);
            this.notifyConflict(error);
          } else if (item.retryCount < 3) {
            // Retry - increment count
            await this.db?.put('pendingUpdates', {
              ...item,
              retryCount: item.retryCount + 1,
            });
          } else {
            // Max retries - remove and notify
            await this.db?.delete('pendingUpdates', item.id);
            this.notifyFailed(item);
          }
        }
      }
    } finally {
      this.syncInProgress = false;
    }
  }
  
  private notifyConflict(error: ConflictError) {
    // Show notification to user
    showToast({
      type: 'warning',
      title: 'Settings conflict',
      message: 'Your offline changes conflict with newer settings. Please review.',
    });
  }
  
  private notifyFailed(item: any) {
    showToast({
      type: 'error',
      title: 'Sync failed',
      message: 'Could not sync some preference changes. Please try again.',
    });
  }
  
  async getPendingCount(): Promise<number> {
    return (await this.db?.count('pendingUpdates')) ?? 0;
  }
}

export const offlineQueue = new OfflinePreferenceQueue();
```

## 6.3 UI Feedback Components

```tsx
// src/components/notifications/PreferenceToggle.tsx

import { useNotificationPreferences } from '@/hooks/useNotificationPreferences';
import { Toggle } from '@/components/ui/Toggle';
import { SyncIndicator } from './SyncIndicator';

interface PreferenceToggleProps {
  field: string;  // "global_enabled", "email_enabled", etc.
  label: string;
  description?: string;
}

export function PreferenceToggle({ field, label, description }: PreferenceToggleProps) {
  const { preferences, updatePreference, isPending, hasFailedOperations, syncError } = 
    useNotificationPreferences();
  
  const value = getField(preferences, field);
  
  const handleToggle = (newValue: boolean) => {
    updatePreference({ [field]: newValue });
  };
  
  return (
    <div className="preference-toggle">
      <div className="preference-toggle__header">
        <Toggle
          checked={value ?? true}
          onChange={handleToggle}
          disabled={isPending}
        />
        <div className="preference-toggle__info">
          <span className="preference-toggle__label">{label}</span>
          {description && (
            <span className="preference-toggle__description">{description}</span>
          )}
        </div>
      </div>
      
      {/* Sync indicator */}
      <SyncIndicator 
        isPending={isPending}
        hasError={!!syncError || hasFailedOperations}
      />
      
      {/* Error message */}
      {syncError && (
        <div className="preference-toggle__error">
          <p>{syncError.message}</p>
          <button onClick={clearError}>Dismiss</button>
        </div>
      )}
    </div>
  );
}

// src/components/notifications/SyncIndicator.tsx

export function SyncIndicator({ isPending, hasError }: { isPending: boolean; hasError: boolean }) {
  if (!isPending && !hasError) return null;
  
  return (
    <div className={cn('sync-indicator', { 'sync-indicator--error': hasError })}>
      {isPending && (
        <>
          <Spinner size="sm" />
          <span>Syncing...</span>
        </>
      )}
      {hasError && (
        <>
          <WarningIcon />
          <span>Sync failed</span>
        </>
      )}
    </div>
  );
}
```

---

# 7. Sync & Cache Strategy

## 7.1 Query Timing & Caching

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PREFERENCE QUERY STRATEGY                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  NOTIFICATION DISPATCH FLOW                                                  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  1. PREFERENCE CHECK (before every dispatch)                        │    │
│  │     ┌──────────────────────────────────────────────────────────┐    │    │
│  │     │                    CACHE LAYER                           │    │    │
│  │     │  Key: notif:prefs:{recipient_type}:{recipient_id}       │    │    │
│  │     │  TTL: 5 minutes                                         │    │    │
│  │     │  Content: { preferences, cached_at, sync_version }      │    │    │
│  │     └──────────────────────────────────────────────────────────┘    │    │
│  │                           │                                         │    │
│  │              ┌────────────┴────────────┐                           │    │
│  │              │                         │                           │    │
│  │              ▼                         ▼                           │    │
│  │     ┌─────────────────┐       ┌─────────────────┐                 │    │
│  │     │ CACHE HIT       │       │ CACHE MISS      │                 │    │
│  │     │ (< 5 min old)   │       │                 │                 │    │
│  │     │                 │       │ Query DB        │                 │    │
│  │     │ Return cached   │       │ (500ms timeout) │                 │    │
│  │     │ preferences     │       │                 │                 │    │
│  │     └────────┬────────┘       └────────┬────────┘                 │    │
│  │              │                         │                           │    │
│  │              │                ┌────────┴────────┐                 │    │
│  │              │                │                 │                 │    │
│  │              │                ▼                 ▼                 │    │
│  │              │        ┌─────────────┐   ┌─────────────┐           │    │
│  │              │        │ DB SUCCESS  │   │ DB TIMEOUT  │           │    │
│  │              │        │             │   │             │           │    │
│  │              │        │ Cache       │   │ Use stale   │           │    │
│  │              │        │ result      │   │ cache or    │           │    │
│  │              │        │             │   │ defaults    │           │    │
│  │              │        └──────┬──────┘   └──────┬──────┘           │    │
│  │              │               │                 │                 │    │
│  │              └───────────────┴─────────────────┘                 │    │
│  │                              │                                   │    │
│  │                              ▼                                   │    │
│  │                    ┌─────────────────┐                           │    │
│  │                    │ EVALUATE        │                           │    │
│  │                    │ PREFERENCE      │                           │    │
│  │                    │ HIERARCHY       │                           │    │
│  │                    └────────┬────────┘                           │    │
│  │                             │                                    │    │
│  │              ┌──────────────┼──────────────┐                    │    │
│  │              │              │              │                    │    │
│  │              ▼              ▼              ▼                    │    │
│  │        ┌──────────┐  ┌──────────┐  ┌──────────┐                 │    │
│  │        │ SEND     │  │ BATCH    │  │ SKIP     │                 │    │
│  │        │ NOW      │  │ QUEUE    │  │ DISABLED │                 │    │
│  │        └──────────┘  └──────────┘  └──────────┘                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 7.2 Cache Key Structure

```
notif:prefs:{recipient_type}:{recipient_id}
│       │            │
│       │            └── "customer" | "owner"
│       └── "prefs" (distinguishes from other notification data)
└── "notif" (top-level namespace)

Examples:
- notif:prefs:customer:123e4567-e89b-12d3-a456-426614174000
- notif:prefs:owner:987e6543-e21b-43d3-b765-543210987654

Stale cache key (for fallback):
- notif:prefs:{recipient_type}:{recipient_id}:stale
  (No TTL, persists until explicitly updated)
```

## 7.3 TTL Recommendations

| Cache Type | TTL | Reasoning |
|------------|-----|-----------|
| **Preference Cache** | 5 minutes | Balance between freshness and DB load |
| **Stale Cache** | No TTL | Fallback when DB unavailable |
| **Device Registry** | 24 hours | Device info rarely changes |
| **Sync Lock** | 30 seconds | Prevent concurrent updates |

## 7.4 Invalidation Mechanism

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CACHE INVALIDATION FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PREFERENCE UPDATE                                                           │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  1. UPDATE DATABASE                                                 │    │
│  │     • Save new preference state                                     │    │
│  │     • Update sync_version                                           │    │
│  │     • Create audit log                                              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  2. INVALIDATE CACHE                                                │    │
│  │     • DELETE notif:prefs:{type}:{id}                                │    │
│  │     • Store stale copy for fallback                                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  3. PUBLISH INVALIDATION EVENT                                      │    │
│  │     • Redis Pub/Sub: preference:invalidate                          │    │
│  │     • Payload: { recipient_id, recipient_type, timestamp }         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                      │
│       ├──────────────────────────────────────────────────────────────┐      │
│       │                                                              │      │
│       ▼                                                              ▼      │
│  ┌─────────────────┐                                    ┌─────────────────┐   │
│  │ INSTANCE A      │                                    │ INSTANCE B      │   │
│  │ (Notification   │                                    │ (Notification   │   │
│  │  Service #1)    │                                    │  Service #2)    │   │
│  │                 │                                    │                 │   │
│  │ • Receive event │                                    │ • Receive event │   │
│  │ • Delete local  │                                    │ • Delete local  │   │
│  │   cache         │                                    │   cache         │   │
│  └─────────────────┘                                    └─────────────────┘   │
│                                                                              │
│  PROPAGATION LATENCY: < 10ms across all instances                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 7.5 Fallback Behavior

```python
class PreferenceFallbackStrategy:
    """
    Fallback behavior when preference queries fail.
    """
    
    async def get_preferences_with_fallback(
        self,
        recipient_id: str,
        recipient_type: str
    ) -> Tuple[dict, FallbackType]:
        """
        Returns preferences and indicates if fallback was used.
        """
        
        # Try 1: Fresh cache
        cached = await self.cache.get(f"notif:prefs:{recipient_type}:{recipient_id}")
        if cached:
            return cached['preferences'], FallbackType.NONE
        
        # Try 2: Database with timeout
        try:
            async with asyncio.timeout(0.5):
                prefs = await self.db.query_preferences(recipient_id, recipient_type)
                await self.cache.set(f"notif:prefs:{recipient_type}:{recipient_id}", prefs)
                return prefs, FallbackType.NONE
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.error(f"DB query failed: {e}")
        
        # Try 3: Stale cache (no TTL)
        stale = await self.cache.get(f"notif:prefs:{recipient_type}:{recipient_id}:stale")
        if stale:
            logger.warning(f"Using stale cache for {recipient_id}")
            return stale['preferences'], FallbackType.STALE_CACHE
        
        # Try 4: Circuit breaker - if open, use defaults
        if self.circuit_breaker.is_open():
            logger.warning(f"Circuit breaker open, using defaults for {recipient_id}")
            return self.get_default_preferences(), FallbackType.DEFAULTS
        
        # Fallback 5: Default preferences
        logger.warning(f"No preferences found, using defaults for {recipient_id}")
        return self.get_default_preferences(), FallbackType.DEFAULTS


class FallbackType(Enum):
    NONE = "none"                    # No fallback needed
    STALE_CACHE = "stale_cache"      # Using expired cache
    DEFAULTS = "defaults"            # Using default preferences
```

## 7.6 Propagation Latency

| Scenario | Latency | Mechanism |
|----------|---------|-----------|
| **Same instance** | < 1ms | Direct cache invalidation |
| **Different instances** | < 10ms | Redis Pub/Sub |
| **Cross-region** | < 100ms | Global Pub/Sub channel |
| **Offline → Online sync** | Variable | Client-initiated on reconnect |

---

# 8. Audit Logging

## 8.1 Audit Log Schema

```sql
-- Already defined in Section 3, but here's the detailed structure:

CREATE TABLE IF NOT EXISTS public.notification_preference_audit (
    -- Primary key
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Who (recipient)
    recipient_id        TEXT NOT NULL,
    recipient_type      TEXT NOT NULL,  -- 'customer' or 'owner'
    
    -- What changed
    change_type         TEXT NOT NULL CHECK (change_type IN (
        'create',        -- First time preferences created
        'update',        -- Normal update
        'delete',        -- Preferences deleted (user deleted account)
        'conflict_resolved'  -- Conflict was resolved
    )),
    field_path          TEXT NOT NULL,     -- Dot notation: "global_enabled" or "notification_types.order_updates.enabled"
    old_value           JSONB,              -- NULL for create
    new_value           JSONB,              -- NULL for delete
    
    -- Who made the change (device)
    device_id           TEXT NOT NULL,
    device_type         TEXT NOT NULL,
    ip_address          INET,               -- Anonymized for privacy
    user_agent          TEXT,               -- Stored for debugging
    
    -- When and why
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reason              TEXT,               -- "user_action", "conflict_resolution", "system_reset"
    conflict_resolution TEXT,               -- Details if this was a conflict resolution
    
    -- Version tracking
    sync_version_before TEXT,
    sync_version_after  TEXT,
    
    -- Retention (auto-delete after this date)
    retention_until     TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '2 years')
);

-- Example records:
-- 1. User enables email notifications
INSERT INTO notification_preference_audit (
    recipient_id, recipient_type, change_type, field_path,
    old_value, new_value, device_id, device_type, ip_address,
    reason, sync_version_before, sync_version_after
) VALUES (
    'user-123', 'customer', 'update', 'email_enabled',
    false, true, 'device-abc', 'mobile_app', '192.168.1.1',
    'user_action', 'v1', 'v2'
);

-- 2. Conflict resolved - server wins
INSERT INTO notification_preference_audit (
    recipient_id, recipient_type, change_type, field_path,
    old_value, new_value, device_id, device_type, ip_address,
    reason, conflict_resolution, sync_version_before, sync_version_after
) VALUES (
    'user-123', 'customer', 'conflict_resolved', 'global_enabled',
    false, true, 'device-xyz', 'desktop_browser', '10.0.0.1',
    'conflict_resolution', 'Server state (true) kept over client (false) - timestamp newer',
    'v2', 'v3'
);
```

## 8.2 Data Captured Per Log Entry

| Field | Description | Privacy Consideration |
|-------|-------------|----------------------|
| `recipient_id` | User ID | PII - restricted access |
| `recipient_type` | Customer or Owner | Non-sensitive |
| `change_type` | Type of change | Non-sensitive |
| `field_path` | Which setting changed | Non-sensitive |
| `old_value` | Previous value | May contain preferences |
| `new_value` | New value | May contain preferences |
| `device_id` | Client device ID | Anonymized identifier |
| `device_type` | Device category | Non-sensitive |
| `ip_address` | Client IP | Truncated to /24 for privacy |
| `user_agent` | Browser/App info | May contain version info |
| `timestamp` | When change occurred | Non-sensitive |
| `reason` | Why change happened | Non-sensitive |
| `conflict_resolution` | How conflict resolved | Non-sensitive |
| `sync_version_*` | Version tracking | Non-sensitive |

## 8.3 Access Control Rules

```python
class AuditLogAccessControl:
    """
    Access control for audit logs.
    """
    
    def can_view_logs(
        self,
        requester: AuthContext,
        target_recipient_id: str,
        target_recipient_type: str
    ) -> bool:
        """
        Determine if requester can view audit logs for target.
        """
        
        # Rule 1: Users can view their own logs
        if requester.user_id == target_recipient_id:
            return True
        
        # Rule 2: Admins can view all logs
        if requester.has_role(Role.ADMIN):
            return True
        
        # Rule 3: Analytics team can view aggregated logs (not individual)
        if requester.has_role(Role.ANALYTICS):
            # Must query aggregated data, not individual records
            return False  # Handled separately with aggregation queries
        
        # Rule 4: Store owners can view logs for their store's customers
        # (only for notification types related to their store)
        if requester.has_role(Role.STORE_OWNER):
            # Check if target is a customer of requester's store
            return self._is_customer_of_store(
                target_recipient_id, 
                requester.store_id
            )
        
        return False
    
    def can_export_logs(
        self,
        requester: AuthContext,
        target_recipient_id: str
    ) -> bool:
        """
        Determine if requester can export audit logs.
        More restrictive than viewing.
        """
        
        # Only admins and the user themselves can export
        if requester.user_id == target_recipient_id:
            return True
        
        if requester.has_role(Role.ADMIN):
            return True
        
        return False
```

## 8.4 Query Examples

```sql
-- Get all preference changes for a user in the last 30 days
SELECT 
    timestamp,
    change_type,
    field_path,
    old_value,
    new_value,
    device_type,
    reason
FROM notification_preference_audit
WHERE recipient_id = 'user-123'
  AND recipient_type = 'customer'
  AND timestamp >= NOW() - INTERVAL '30 days'
ORDER BY timestamp DESC;

-- Get all conflict resolutions in the last week
SELECT 
    recipient_id,
    recipient_type,
    field_path,
    conflict_resolution,
    timestamp
FROM notification_preference_audit
WHERE change_type = 'conflict_resolved'
  AND timestamp >= NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;

-- Get preference changes by device type (aggregated)
SELECT 
    device_type,
    COUNT(*) as change_count,
    COUNT(*) FILTER (WHERE change_type = 'conflict_resolved') as conflict_count
FROM notification_preference_audit
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY device_type;

-- Get most frequently changed preferences
SELECT 
    field_path,
    COUNT(*) as change_count
FROM notification_preference_audit
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY field_path
ORDER BY change_count DESC
LIMIT 10;
```

## 8.5 Retention Policy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AUDIT LOG RETENTION POLICY                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  ACTIVE STORAGE (PostgreSQL)                                        │    │
│  │  • Retention: 2 years                                               │    │
│  │  • Full detail: all fields available                               │    │
│  │  • Queryable: real-time queries supported                           │    │
│  │  • Indexed: optimized for time-range queries                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                      │
│       │ After 2 years                                                        │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  ARCHIVE STORAGE (S3/Glacier)                                       │    │
│  │  • Retention: 5 additional years (7 total)                          │    │
│  │  • Aggregated: PII removed, counts only                             │    │
│  │  • Cold storage: retrieval takes hours                              │    │
│  │  • Compliance: retained for legal requirements                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                      │
│       │ After 7 years                                                        │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  DELETION                                                           │    │
│  │  • Permanent deletion                                               │    │
│  │  • No recovery possible                                             │    │
│  │  • GDPR compliant                                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  AUTOMATED ARCHIVAL PROCESS:                                                 │
│  • Daily job: Move records where retention_until < NOW() to archive        │
│  • Monthly job: Delete archived records older than 7 years                 │
│  • User deletion request: Immediate deletion of all user's logs             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 9. Failure Scenarios & Responses

## 9.1 Timeout Thresholds

| Operation | Timeout | Reasoning |
|-----------|---------|-----------|
| **Preference DB Query** | 500ms | Fast enough for dispatch, slow enough for complex queries |
| **Preference Update** | 2s | Allows for conflict resolution and audit logging |
| **Cache Read** | 50ms | Redis should be very fast |
| **Cache Write** | 100ms | Slightly longer for persistence |
| **Pub/Sub Invalidation** | 1s | Should propagate quickly |
| **Client Retry** | 1s → 2s → 4s | Exponential backoff |

## 9.2 Partial Sync Failures

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PARTIAL SYNC FAILURE HANDLING                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SCENARIO: Update succeeds on client but never reaches server               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  CLIENT STATE                                                       │    │
│  │  • Optimistic update applied                                        │    │
│  │  • Pending operation in queue                                       │    │
│  │  • Sync indicator showing "Syncing..."                              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                      │
│       │ Network failure / timeout                                           │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  DETECTION                                                          │    │
│  │  • No response after timeout (2s)                                   │    │
│  │  • Network error event fired                                        │    │
│  │  • Retry counter incremented                                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                      │
│       ├──────────────────────────────────────────────────────────────┐      │
│       │ Retry 1 (1s delay)                                            │      │
│       │ └─► Fail                                                      │      │
│       │ Retry 2 (2s delay)                                            │      │
│       │ └─► Fail                                                       │      │
│       │ Retry 3 (4s delay)                                            │      │
│       │ └─► Fail                                                       │      │
│       └──────────────────────────────────────────────────────────────┘      │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  RECOVERY                                                           │    │
│  │  • Mark operation as "failed"                                       │    │
│  │  • Keep optimistic state visible                                    │    │
│  │  • Show error banner: "Changes not saved"                           │    │
│  │  • Offer retry button                                               │    │
│  │  • If user navigates away:                                          │    │
│  │    - Store in IndexedDB for later sync                              │    │
│  │    - Sync on next app load                                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 9.3 Offline Scenarios

```typescript
// Offline sync strategy

class OfflineSyncManager {
  private indexedDB: IDBPDatabase;
  private isOnline: boolean = navigator.onLine;
  
  constructor() {
    // Listen for online/offline events
    window.addEventListener('online', () => this.handleOnline());
    window.addEventListener('offline', () => this.handleOffline());
  }
  
  async queueUpdate(update: PreferenceUpdate): Promise<void> {
    // Store update in IndexedDB
    const operation: OfflineOperation = {
      id: generateUUID(),
      type: 'preference_update',
      payload: update,
      timestamp: new Date(),
      retryCount: 0,
      status: 'pending',
    };
    
    await this.indexedDB.put('offlineQueue', operation);
    
    // Show offline indicator
    this.showOfflineIndicator();
  }
  
  async handleOnline(): Promise<void> {
    this.isOnline = true;
    
    // Process all pending operations
    const pending = await this.indexedDB.getAll('offlineQueue');
    
    for (const op of pending) {
      try {
        await this.syncOperation(op);
        await this.indexedDB.delete('offlineQueue', op.id);
      } catch (error) {
        if (error instanceof ConflictError) {
          // Conflict detected - user must resolve
          await this.handleConflict(op, error);
        } else {
          // Retry later
          op.retryCount++;
          if (op.retryCount < 3) {
            await this.indexedDB.put('offlineQueue', op);
          } else {
            // Max retries - notify user
            this.showSyncFailedNotification(op);
          }
        }
      }
    }
    
    this.hideOfflineIndicator();
  }
  
  handleOffline(): void {
    this.isOnline = false;
    this.showOfflineIndicator();
  }
}
```

## 9.4 Cascading Failures

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CASCADING FAILURE RESPONSES                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  FAILURE: Preference Service Down                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  COMPONENT: API (Preference Update)                                 │    │
│  │  RESPONSE:                                                          │    │
│  │  • Return 503 Service Unavailable                                   │    │
│  │  • Include Retry-After header                                       │    │
│  │  • Client: Show "Settings temporarily unavailable"                  │    │
│  │  • Client: Queue updates locally for retry                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  COMPONENT: NotificationService (Dispatch)                          │    │
│  │  RESPONSE:                                                          │    │
│  │  • Circuit breaker opens after 5 failures                          │    │
│  │  • Use stale cache or default preferences                          │    │
│  │  • Log warning: "Preference service unavailable, using fallback"   │    │
│  │  • Continue dispatch with fallback preferences                      │    │
│  │  • Queue notifications for retry if critical                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  COMPONENT: UI (Client)                                             │    │
│  │  RESPONSE:                                                          │    │
│  │  • Show banner: "Some settings may not be current"                  │    │
│  │  • Disable preference editing                                       │    │
│  │  • Show cached preferences (read-only)                              │    │
│  │  • Poll for service recovery (every 30s)                            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  FAILURE: Database Down                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  COMPONENT: Preference Service                                      │    │
│  │  RESPONSE:                                                          │    │
│  │  • Return cached preferences (stale acceptable)                     │    │
│  │  • No updates accepted (503)                                        │    │
│  │  • Alert ops team immediately                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  COMPONENT: NotificationService                                     │    │
│  │  RESPONSE:                                                          │    │
│  │  • Use Redis cache exclusively                                      │    │
│  │  • If cache miss: use default preferences                           │    │
│  │  • Log: "Database unavailable, using cache/defaults"                │    │
│  │  • Continue dispatch (prefer sending over not sending)              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  FAILURE: Redis Down                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  COMPONENT: Preference Service                                      │    │
│  │  RESPONSE:                                                          │    │
│  │  • Query database directly (slower but functional)                  │    │
│  │  • No caching available                                             │    │
│  │  • Increase DB connection pool temporarily                          │    │
│  │  • Alert ops team                                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  COMPONENT: NotificationService                                     │    │
│  │  RESPONSE:                                                          │    │
│  │  • Query database for every dispatch (performance impact)           │    │
│  │  • If DB also slow: use local in-memory cache (per instance)        │    │
│  │  • Monitor latency closely                                          │    │
│  │  • Scale horizontally if needed                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 9.5 Circuit Breaker Pattern

```python
class CircuitBreaker:
    """
    Circuit breaker for preference service resilience.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: int = 60,
        half_open_requests: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_requests = half_open_requests
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.half_open_successes = 0
    
    def is_open(self) -> bool:
        """Check if circuit is open (should fail-fast)."""
        
        if self.state == CircuitState.OPEN:
            # Check if we should try half-open
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                return False
            return True
        
        return False
    
    def record_failure(self):
        """Record a failure."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            # Failure during half-open - back to open
            self.state = CircuitState.OPEN
            self.half_open_successes = 0
        elif self.failure_count >= self.failure_threshold:
            # Threshold reached - open circuit
            self.state = CircuitState.OPEN
    
    def record_success(self):
        """Record a success."""
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            if self.half_open_successes >= self.half_open_requests:
                # Enough successes - close circuit
                self.state = CircuitState.CLOSED
                self.half_open_successes = 0
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True
        
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.reset_timeout


enum CircuitState:
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Fail-fast, no requests
    HALF_OPEN = "half_open"  # Testing if service recovered
```

## 9.6 User-Facing Error Messages

| Error Code | User Message | Action |
|------------|--------------|--------|
| `NETWORK_ERROR` | "Unable to save settings. Check your connection." | Retry button |
| `VERSION_STALE` | "Your settings were updated on another device. Please review." | Show current settings |
| `CHECKSUM_MISMATCH` | "Your settings are out of sync. Refreshing..." | Auto-refresh |
| `RATE_LIMITED` | "Too many changes. Please wait a moment." | Show countdown |
| `SERVICE_UNAVAILABLE` | "Settings are temporarily unavailable. Your changes will be saved when service resumes." | Queue locally |
| `CONFLICT_DETECTED` | "Another device changed these settings. Which version do you want to keep?" | Show both versions |
| `VALIDATION_ERROR` | "Invalid setting value. Please correct and try again." | Highlight field |
| `PERMISSION_DENIED` | "You don't have permission to change these settings." | Contact support link |

---

# Appendix A: Implementation Checklist

## Backend Implementation

- [ ] Create database migration for preference tables
- [ ] Implement `PreferenceService` with conflict resolution
- [ ] Implement `ConflictResolver` with vector clock comparison
- [ ] Implement `PreferenceAwareDispatcher` for NotificationService
- [ ] Implement cache invalidation with Pub/Sub
- [ ] Implement audit logging service
- [ ] Add API routes for preference CRUD
- [ ] Add API routes for device management
- [ ] Add API routes for audit log queries
- [ ] Add circuit breaker for preference queries
- [ ] Add rate limiting for preference updates
- [ ] Write unit tests for conflict resolution
- [ ] Write integration tests for sync flow

## Frontend Implementation

- [ ] Create `useNotificationPreferences` hook
- [ ] Implement optimistic update state management
- [ ] Implement offline queue with IndexedDB
- [ ] Create preference toggle components
- [ ] Create sync indicator components
- [ ] Create conflict resolution UI
- [ ] Create error handling and retry UI
- [ ] Add device management UI
- [ ] Add audit log viewer (for admins)

## Testing

- [ ] Test conflict resolution with concurrent updates
- [ ] Test offline sync and recovery
- [ ] Test cache invalidation propagation
- [ ] Test circuit breaker behavior
- [ ] Test rate limiting
- [ ] Test audit log retention
- [ ] Load test preference queries
- [ ] Chaos test (simulate failures)

---

# Appendix B: Monitoring & Observability

## Key Metrics

| Metric | Type | Alert Threshold |
|--------|------|-----------------|
| `preference_query_latency_p99` | Histogram | > 500ms |
| `preference_update_latency_p99` | Histogram | > 2s |
| `preference_cache_hit_rate` | Gauge | < 80% |
| `preference_conflict_rate` | Counter | > 5% of updates |
| `preference_sync_queue_depth` | Gauge | > 100 |
| `preference_circuit_breaker_state` | State | Open |
| `audit_log_retention_violations` | Counter | > 0 |

## Logging Standards

```python
# Preference update log
logger.info(
    "Preference updated",
    extra={
        'event': 'preference_update',
        'recipient_id': recipient_id,
        'recipient_type': recipient_type,
        'device_id': device_id,
        'device_type': device_type,
        'sync_version': new_version,
        'changes': changes,
        'conflict': conflict_type.value if conflict else None,
        'latency_ms': latency_ms,
        'cache_hit': cache_hit
    }
)

# Conflict detected log
logger.warning(
    "Preference conflict detected",
    extra={
        'event': 'preference_conflict',
        'recipient_id': recipient_id,
        'incoming_device': incoming.device_id,
        'current_device': current.device_id,
        'conflict_type': conflict_type.value,
        'resolution': resolution.value
    }
)

# Cache invalidation log
logger.debug(
    "Cache invalidated",
    extra={
        'event': 'cache_invalidation',
        'recipient_id': recipient_id,
        'recipient_type': recipient_type,
        'source': 'update' | 'pubsub'
    }
)
```

---

**Document End**
