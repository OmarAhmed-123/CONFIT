-- ============================================================
-- CONFIT — Notification Preferences Schema
-- Created: 2026-04-05
-- Description: Granular notification preferences per user with
--              channel toggles, frequency settings, and batch options
-- ============================================================

-- Enable UUID extension if not already
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ═══════════════════════════════════════════════════════════════════
-- NOTIFICATION PREFERENCES TABLE
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.notification_preferences (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Recipient identification
    recipient_id            UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    recipient_type          VARCHAR(20) NOT NULL CHECK (recipient_type IN ('customer', 'store_owner')),
    
    -- Channel preferences (per-channel enable/disable)
    channel_preferences     JSONB NOT NULL DEFAULT '{"in_app": true, "email": true, "push": true}',
    
    -- Frequency settings per notification type
    -- Maps type -> frequency (real_time, daily_digest, weekly_summary, disabled)
    frequency_settings      JSONB NOT NULL DEFAULT '{}',
    
    -- Enabled notification types (array of strings)
    notification_types      JSONB NOT NULL DEFAULT '[]',
    
    -- Batch options (store owners only)
    batch_options           JSONB NOT NULL DEFAULT '{"enabled": false}',
    
    -- Versioning & Audit
    version                 INTEGER NOT NULL DEFAULT 1,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- One preferences record per user per recipient type
    UNIQUE(recipient_id, recipient_type)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_notification_preferences_recipient 
    ON public.notification_preferences(recipient_id);
CREATE INDEX IF NOT EXISTS idx_notification_preferences_type 
    ON public.notification_preferences(recipient_type);

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_notification_preferences_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notification_preferences_updated_at 
    ON public.notification_preferences;
CREATE TRIGGER trg_notification_preferences_updated_at
    BEFORE UPDATE ON public.notification_preferences
    FOR EACH ROW EXECUTE FUNCTION update_notification_preferences_updated_at();

-- ═══════════════════════════════════════════════════════════════════
-- NOTIFICATION QUEUE TABLE (for batch delivery)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.notification_queue (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Recipient
    recipient_id            UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    recipient_type          VARCHAR(20) NOT NULL CHECK (recipient_type IN ('customer', 'store_owner')),
    
    -- Batch type
    batch_type              VARCHAR(20) NOT NULL CHECK (batch_type IN ('daily_digest', 'weekly_summary')),
    
    -- Queued notification payload
    notification_payload    JSONB NOT NULL,
    
    -- Original notification metadata
    notification_type       VARCHAR(50) NOT NULL,
    channel                 VARCHAR(20) NOT NULL CHECK (channel IN ('in_app', 'email', 'push')),
    
    -- Scheduling
    scheduled_for           TIMESTAMPTZ NOT NULL,
    processed_at            TIMESTAMPTZ,
    
    -- Status
    status                  VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'sent', 'failed')),
    
    -- Timestamps
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Index for efficient batch processing
    CONSTRAINT chk_scheduled_for_future CHECK (scheduled_for > created_at)
);

-- Indexes for batch processing
CREATE INDEX IF NOT EXISTS idx_notification_queue_scheduled 
    ON public.notification_queue(scheduled_for) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_notification_queue_batch_type 
    ON public.notification_queue(batch_type, status);
CREATE INDEX IF NOT EXISTS idx_notification_queue_recipient 
    ON public.notification_queue(recipient_id, recipient_type);

-- ═══════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE public.notification_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own notification preferences"
    ON public.notification_preferences FOR SELECT
    USING (auth.uid() = recipient_id);

CREATE POLICY "Users can insert own notification preferences"
    ON public.notification_preferences FOR INSERT
    WITH CHECK (auth.uid() = recipient_id);

CREATE POLICY "Users can update own notification preferences"
    ON public.notification_preferences FOR UPDATE
    USING (auth.uid() = recipient_id);

-- ═══════════════════════════════════════════════════════════════════
-- DEFAULT PREFERENCES TRIGGER
-- ═══════════════════════════════════════════════════════════════════

-- Function to create default preferences for new users
CREATE OR REPLACE FUNCTION create_default_notification_preferences()
RETURNS TRIGGER AS $$
DECLARE
    customer_types TEXT[] := ARRAY['order_updates', 'promotions', 'style_recommendations', 'restock_alerts'];
    owner_types TEXT[] := ARRAY['new_orders', 'status_updates', 'customer_inquiries'];
    freq_settings JSONB;
    i INT;
BEGIN
    -- Create customer preferences
    freq_settings := '{}';
    FOR i IN 1..array_length(customer_types, 1) LOOP
        freq_settings := freq_settings || jsonb_build_object(customer_types[i], 'real_time');
    END LOOP;
    
    INSERT INTO public.notification_preferences (
        recipient_id, 
        recipient_type, 
        channel_preferences,
        frequency_settings,
        notification_types,
        batch_options
    ) VALUES (
        NEW.id,
        'customer',
        '{"in_app": true, "email": true, "push": true}',
        freq_settings,
        to_jsonb(customer_types),
        '{"enabled": false}'
    );
    
    -- Create store_owner preferences (default for brand managers)
    freq_settings := '{}';
    FOR i IN 1..array_length(owner_types, 1) LOOP
        freq_settings := freq_settings || jsonb_build_object(owner_types[i], 'real_time');
    END LOOP;
    
    INSERT INTO public.notification_preferences (
        recipient_id, 
        recipient_type, 
        channel_preferences,
        frequency_settings,
        notification_types,
        batch_options
    ) VALUES (
        NEW.id,
        'store_owner',
        '{"in_app": true, "email": true, "push": true}',
        freq_settings,
        to_jsonb(owner_types),
        '{"enabled": false}'
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if any
DROP TRIGGER IF EXISTS trg_create_default_notification_preferences ON public.users;

-- Create trigger for new users
CREATE TRIGGER trg_create_default_notification_preferences
    AFTER INSERT ON public.users
    FOR EACH ROW EXECUTE FUNCTION create_default_notification_preferences();

-- ═══════════════════════════════════════════════════════════════════
-- GRANT PERMISSIONS
-- ═══════════════════════════════════════════════════════════════════

GRANT ALL PRIVILEGES ON TABLE public.notification_preferences TO confit;
GRANT ALL PRIVILEGES ON TABLE public.notification_queue TO confit;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO confit;
