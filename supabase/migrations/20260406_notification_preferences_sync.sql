-- ============================================================
-- CONFIT — Notification Preferences Synchronization Schema
-- Created: 2026-04-06
-- Description: Preference synchronization, versioning, conflict
--              resolution, and audit logging for multi-device sync
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
    push_token      TEXT,                             -- FCM/APNS token for push notifications
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    registered_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, device_id)
);

CREATE INDEX IF NOT EXISTS idx_notification_devices_user_id 
    ON public.notification_devices(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_devices_device_id 
    ON public.notification_devices(device_id);
CREATE INDEX IF NOT EXISTS idx_notification_devices_last_seen 
    ON public.notification_devices(last_seen_at DESC);

-- ── Notification Preferences ──────────────────────────────────────
-- Core preference state with versioning for conflict resolution

CREATE TABLE IF NOT EXISTS public.notification_preferences (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_id            TEXT NOT NULL,                    -- User ID or owner ID
    recipient_type          TEXT NOT NULL CHECK (recipient_type IN ('customer', 'owner')),
    
    -- Global toggle (Level 1 - highest priority)
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
    -- JSONB structure for flexibility:
    -- {
    --   "order_updates": {
    --     "enabled": true,
    --     "channels": {
    --       "email": { "enabled": true },
    --       "push": { "enabled": false }
    --     }
    --   },
    --   "promotional": {
    --     "enabled": true,
    --     "channels": {}
    --   }
    -- }
    notification_types      JSONB NOT NULL DEFAULT '{}',
    
    -- Batch settings for digest/summary
    -- {
    --   "daily_digest": { "preferred_time": "18:00", "last_sent": "..." },
    --   "weekly_summary": { "preferred_day": "sunday", "preferred_time": "10:00", "last_sent": "..." }
    -- }
    batch_settings          JSONB NOT NULL DEFAULT '{}',
    
    -- Version tracking for conflict resolution
    sync_version            TEXT NOT NULL DEFAULT 'init:0:0',  -- Format: "deviceId:timestamp:sequence"
    vector_clock            JSONB NOT NULL DEFAULT '{}',       -- { "deviceA": 5, "deviceB": 3 }
    checksum                TEXT NOT NULL DEFAULT '',          -- SHA-256 of preference state
    last_modified           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_modified_by        TEXT NOT NULL DEFAULT '',          -- device_id that made last change
    
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
CREATE INDEX IF NOT EXISTS idx_notification_preferences_global_enabled 
    ON public.notification_preferences(global_enabled) WHERE NOT global_enabled;

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
                      CHECK (status IN ('pending', 'syncing', 'synced', 'failed', 'expired')),
    retry_count     INTEGER NOT NULL DEFAULT 0,
    max_retries     INTEGER NOT NULL DEFAULT 3,
    error_message   TEXT,
    expires_at      TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days')
);

CREATE INDEX IF NOT EXISTS idx_notification_sync_queue_recipient 
    ON public.notification_sync_queue(recipient_id, recipient_type);
CREATE INDEX IF NOT EXISTS idx_notification_sync_queue_device 
    ON public.notification_sync_queue(device_id);
CREATE INDEX IF NOT EXISTS idx_notification_sync_queue_status 
    ON public.notification_sync_queue(status, created_at);
CREATE INDEX IF NOT EXISTS idx_notification_sync_queue_expires 
    ON public.notification_sync_queue(expires_at) WHERE status IN ('pending', 'failed');

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
    
    -- Retention (auto-delete after this date)
    retention_until     TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '2 years')
);

-- Indexes for audit queries
CREATE INDEX IF NOT EXISTS idx_notification_preference_audit_recipient 
    ON public.notification_preference_audit(recipient_id, recipient_type);
CREATE INDEX IF NOT EXISTS idx_notification_preference_audit_timestamp 
    ON public.notification_preference_audit(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_notification_preference_audit_device 
    ON public.notification_preference_audit(device_id);
CREATE INDEX IF NOT EXISTS idx_notification_preference_audit_change_type 
    ON public.notification_preference_audit(change_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_notification_preference_audit_retention 
    ON public.notification_preference_audit(retention_until);

-- ── Preference Batches (for digest/summary) ─────────────────────────
-- Stores notifications queued for batch delivery

CREATE TABLE IF NOT EXISTS public.notification_batches (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_id    TEXT NOT NULL,
    recipient_type  TEXT NOT NULL,
    channel         TEXT NOT NULL CHECK (channel IN ('in_app', 'email', 'push', 'toast')),
    frequency       TEXT NOT NULL CHECK (frequency IN ('daily_digest', 'weekly_summary')),
    
    -- Batch content
    notifications   JSONB NOT NULL DEFAULT '[]',  -- Array of notification payloads
    count           INTEGER NOT NULL DEFAULT 0,
    
    -- Timing
    scheduled_for   TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at         TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'pending' 
                      CHECK (status IN ('pending', 'processing', 'sent', 'failed')),
    
    UNIQUE(recipient_id, recipient_type, channel, frequency, scheduled_for)
);

CREATE INDEX IF NOT EXISTS idx_notification_batches_recipient 
    ON public.notification_batches(recipient_id, recipient_type);
CREATE INDEX IF NOT EXISTS idx_notification_batches_scheduled 
    ON public.notification_batches(scheduled_for) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_notification_batches_status 
    ON public.notification_batches(status, scheduled_for);

-- ── Functions ──────────────────────────────────────────────────────

-- Calculate preference checksum for integrity verification
CREATE OR REPLACE FUNCTION public.calculate_preference_checksum(
    p_global_enabled BOOLEAN,
    p_in_app_enabled BOOLEAN,
    p_email_enabled BOOLEAN,
    p_push_enabled BOOLEAN,
    p_toast_enabled BOOLEAN,
    p_in_app_frequency TEXT,
    p_email_frequency TEXT,
    p_push_frequency TEXT,
    p_toast_frequency TEXT,
    p_notification_types JSONB,
    p_batch_settings JSONB
) RETURNS TEXT AS $$
DECLARE
    concat_string TEXT;
BEGIN
    concat_string := p_global_enabled::text || '|' ||
                     p_in_app_enabled::text || '|' ||
                     p_email_enabled::text || '|' ||
                     p_push_enabled::text || '|' ||
                     p_toast_enabled::text || '|' ||
                     p_in_app_frequency || '|' ||
                     p_email_frequency || '|' ||
                     p_push_frequency || '|' ||
                     p_toast_frequency || '|' ||
                     COALESCE(p_notification_types::text, '{}') || '|' ||
                     COALESCE(p_batch_settings::text, '{}');
    
    RETURN encode(sha256(concat_string::bytea), 'hex');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Get effective preferences with hierarchy resolved
CREATE OR REPLACE FUNCTION public.get_effective_preferences(
    p_recipient_id TEXT,
    p_recipient_type TEXT
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
        -- Return defaults for new users
        RETURN jsonb_build_object(
            'global_enabled', true,
            'channels', jsonb_build_object(
                'in_app', jsonb_build_object('enabled', true, 'frequency', 'real_time'),
                'email', jsonb_build_object('enabled', true, 'frequency', 'real_time'),
                'push', jsonb_build_object('enabled', true, 'frequency', 'real_time'),
                'toast', jsonb_build_object('enabled', true, 'frequency', 'real_time')
            ),
            'notification_types', '{}',
            'batch_settings', '{}',
            'is_default', true
        );
    END IF;
    
    -- Build result with all preference data
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
        'checksum', prefs.checksum,
        'last_modified', prefs.last_modified,
        'last_modified_by', prefs.last_modified_by,
        'is_default', false
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Check if notification should be sent based on preference hierarchy
CREATE OR REPLACE FUNCTION public.should_send_notification(
    p_recipient_id TEXT,
    p_recipient_type TEXT,
    p_notification_type TEXT,
    p_channel TEXT
) RETURNS TABLE (
    should_send BOOLEAN,
    reason TEXT,
    frequency TEXT
) AS $$
DECLARE
    prefs JSONB;
    type_settings JSONB;
    channel_settings JSONB;
    type_channel_settings JSONB;
BEGIN
    -- Get preferences
    prefs := public.get_effective_preferences(p_recipient_id, p_recipient_type);
    
    -- Level 1: Global toggle
    IF NOT (prefs->>'global_enabled')::boolean THEN
        RETURN QUERY SELECT false, 'Global notifications disabled', 'disabled'::text;
        RETURN;
    END IF;
    
    -- Level 2: Notification type toggle
    type_settings := prefs->'notification_types'->p_notification_type;
    IF type_settings IS NOT NULL AND NOT COALESCE((type_settings->>'enabled')::boolean, true) THEN
        RETURN QUERY SELECT false, 'Notification type disabled', 'disabled'::text;
        RETURN;
    END IF;
    
    -- Level 3: Channel toggle
    channel_settings := prefs->'channels'->p_channel;
    IF channel_settings IS NULL OR NOT COALESCE((channel_settings->>'enabled')::boolean, true) THEN
        RETURN QUERY SELECT false, 'Channel disabled globally', 'disabled'::text;
        RETURN;
    END IF;
    
    -- Level 4: Type-channel override
    IF type_settings IS NOT NULL AND type_settings->'channels' IS NOT NULL THEN
        type_channel_settings := type_settings->'channels'->p_channel;
        IF type_channel_settings IS NOT NULL AND NOT COALESCE((type_channel_settings->>'enabled')::boolean, true) THEN
            RETURN QUERY SELECT false, 'Notification type disabled for channel', 'disabled'::text;
            RETURN;
        END IF;
    END IF;
    
    -- Level 5: Frequency check
    IF channel_settings IS NOT NULL THEN
        RETURN QUERY SELECT true, 'All checks passed', COALESCE(channel_settings->>'frequency', 'real_time');
    ELSE
        RETURN QUERY SELECT true, 'All checks passed', 'real_time'::text;
    END IF;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Generate new sync version
CREATE OR REPLACE FUNCTION public.generate_sync_version(
    p_device_id TEXT,
    p_current_version TEXT DEFAULT NULL
) RETURNS TEXT AS $$
DECLARE
    timestamp_part TEXT;
    sequence_part INTEGER := 0;
BEGIN
    timestamp_part := EXTRACT(EPOCH FROM NOW())::bigint::text;
    
    IF p_current_version IS NOT NULL THEN
        -- Extract sequence from current version and increment
        sequence_part := COALESCE(
            CAST(SPLIT_PART(p_current_version, ':', 3) AS INTEGER), 
            0
        ) + 1;
    END IF;
    
    RETURN p_device_id || ':' || timestamp_part || ':' || sequence_part;
END;
$$ LANGUAGE plpgsql VOLATILE;

-- Update vector clock
CREATE OR REPLACE FUNCTION public.update_vector_clock(
    p_current_clock JSONB,
    p_device_id TEXT
) RETURNS JSONB AS $$
DECLARE
    current_seq INTEGER;
BEGIN
    current_seq := COALESCE((p_current_clock->>p_device_id)::integer, 0);
    RETURN jsonb_set(p_current_clock, ARRAY[p_device_id], (current_seq + 1)::text::jsonb);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Compare vector clocks for conflict detection
-- Returns: -1 if a < b (a is older), 0 if concurrent, 1 if a > b (a is newer)
CREATE OR REPLACE FUNCTION public.compare_vector_clocks(
    p_clock_a JSONB,
    p_clock_b JSONB
) RETURNS INTEGER AS $$
DECLARE
    key TEXT;
    val_a INTEGER;
    val_b INTEGER;
    a_less BOOLEAN := false;
    b_less BOOLEAN := false;
BEGIN
    -- Check all keys in both clocks
    FOR key IN SELECT DISTINCT jsonb_object_keys(p_clock_a) UNION SELECT DISTINCT jsonb_object_keys(p_clock_b)
    LOOP
        val_a := COALESCE((p_clock_a->>key)::integer, 0);
        val_b := COALESCE((p_clock_b->>key)::integer, 0);
        
        IF val_a < val_b THEN
            a_less := true;
        ELSIF val_a > val_b THEN
            b_less := true;
        END IF;
    END LOOP;
    
    -- Determine relationship
    IF a_less AND NOT b_less THEN
        RETURN -1;  -- a is older
    ELSIF b_less AND NOT a_less THEN
        RETURN 1;   -- a is newer
    ELSE
        RETURN 0;   -- concurrent (both have changes the other doesn't)
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Clean up expired sync queue entries
CREATE OR REPLACE FUNCTION public.cleanup_expired_sync_queue()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM public.notification_sync_queue
    WHERE expires_at < NOW() OR (status = 'failed' AND retry_count >= max_retries);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Archive old audit logs
CREATE OR REPLACE FUNCTION public.archive_old_audit_logs()
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    -- Delete logs past retention period
    DELETE FROM public.notification_preference_audit
    WHERE retention_until < NOW();
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ── Triggers ────────────────────────────────────────────────────────

-- Auto-update updated_at timestamp
CREATE TRIGGER trg_notification_preferences_updated_at
    BEFORE UPDATE ON public.notification_preferences
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Auto-update checksum on preference changes
CREATE OR REPLACE FUNCTION public.update_preference_checksum()
RETURNS TRIGGER AS $$
BEGIN
    NEW.checksum := public.calculate_preference_checksum(
        NEW.global_enabled,
        NEW.in_app_enabled,
        NEW.email_enabled,
        NEW.push_enabled,
        NEW.toast_enabled,
        NEW.in_app_frequency,
        NEW.email_frequency,
        NEW.push_frequency,
        NEW.toast_frequency,
        NEW.notification_types,
        NEW.batch_settings
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_notification_preferences_checksum
    BEFORE INSERT OR UPDATE ON public.notification_preferences
    FOR EACH ROW EXECUTE FUNCTION public.update_preference_checksum();

-- ── RLS Policies ───────────────────────────────────────────────────

ALTER TABLE public.notification_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_sync_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_preference_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_batches ENABLE ROW LEVEL SECURITY;

-- Users can manage their own devices
CREATE POLICY "Users can read own devices"
    ON public.notification_devices FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own devices"
    ON public.notification_devices FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own devices"
    ON public.notification_devices FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own devices"
    ON public.notification_devices FOR DELETE
    USING (auth.uid() = user_id);

-- Users can read/write own preferences
CREATE POLICY "Users can read own preferences"
    ON public.notification_preferences FOR SELECT
    USING (
        recipient_id = auth.uid()::text 
        OR EXISTS (
            SELECT 1 FROM public.user_roles ur
            WHERE ur.user_id = auth.uid() 
            AND ur.role IN ('admin', 'store_owner', 'factory_owner')
        )
    );

CREATE POLICY "Users can insert own preferences"
    ON public.notification_preferences FOR INSERT
    WITH CHECK (
        recipient_id = auth.uid()::text
    );

CREATE POLICY "Users can update own preferences"
    ON public.notification_preferences FOR UPDATE
    USING (
        recipient_id = auth.uid()::text
        OR EXISTS (
            SELECT 1 FROM public.user_roles ur
            WHERE ur.user_id = auth.uid() 
            AND ur.role IN ('admin')
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

-- Service role can manage batches
CREATE POLICY "Service role can manage batches"
    ON public.notification_batches FOR ALL
    USING (auth.role() = 'service_role');

-- ── Comments for Documentation ──────────────────────────────────────

COMMENT ON TABLE public.notification_devices IS 
    'Registry of devices that have synced notification preferences. Tracks device type, last seen, and push tokens.';

COMMENT ON TABLE public.notification_preferences IS 
    'Core notification preference state with version tracking for conflict resolution. Supports 5-level preference hierarchy.';

COMMENT ON TABLE public.notification_sync_queue IS 
    'Queue of pending sync operations for offline devices. Supports retry with exponential backoff.';

COMMENT ON TABLE public.notification_preference_audit IS 
    'Complete audit trail of all preference modifications with 2-year retention. Tracks who, what, when, and why.';

COMMENT ON TABLE public.notification_batches IS 
    'Stores notifications queued for batch delivery (daily digest, weekly summary).';

COMMENT ON FUNCTION public.calculate_preference_checksum IS 
    'Calculates SHA-256 checksum of preference state for integrity verification.';

COMMENT ON FUNCTION public.get_effective_preferences IS 
    'Returns effective preferences for a recipient, with defaults for new users.';

COMMENT ON FUNCTION public.should_send_notification IS 
    'Evaluates full preference hierarchy to determine if notification should be sent. Returns decision with reason.';

COMMENT ON FUNCTION public.compare_vector_clocks IS 
    'Compares two vector clocks for conflict detection. Returns -1 (older), 0 (concurrent), or 1 (newer).';

-- ── Grants ──────────────────────────────────────────────────────────

GRANT SELECT ON public.notification_preferences TO authenticated;
GRANT SELECT ON public.notification_devices TO authenticated;
GRANT SELECT ON public.notification_preference_audit TO authenticated;

GRANT ALL ON public.notification_preferences TO service_role;
GRANT ALL ON public.notification_devices TO service_role;
GRANT ALL ON public.notification_sync_queue TO service_role;
GRANT ALL ON public.notification_preference_audit TO service_role;
GRANT ALL ON public.notification_batches TO service_role;

-- Grant execute on functions
GRANT EXECUTE ON FUNCTION public.calculate_preference_checksum TO service_role;
GRANT EXECUTE ON FUNCTION public.get_effective_preferences TO service_role;
GRANT EXECUTE ON FUNCTION public.should_send_notification TO service_role;
GRANT EXECUTE ON FUNCTION public.generate_sync_version TO service_role;
GRANT EXECUTE ON FUNCTION public.update_vector_clock TO service_role;
GRANT EXECUTE ON FUNCTION public.compare_vector_clocks TO service_role;
GRANT EXECUTE ON FUNCTION public.cleanup_expired_sync_queue TO service_role;
GRANT EXECUTE ON FUNCTION public.archive_old_audit_logs TO service_role;
