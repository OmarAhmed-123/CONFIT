-- CONFIT Donation System Migration
-- Creates tables for donations, donor credits, and redemptions
-- Production-ready schema with proper indexing and constraints

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- DONATIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS donations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Amount
    amount DECIMAL(12, 2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    
    -- Payment tracking
    payment_method VARCHAR(32) NOT NULL DEFAULT 'card',
    payment_provider VARCHAR(32),
    transaction_id VARCHAR(128) UNIQUE,
    payment_intent_id VARCHAR(128),
    payment_metadata JSONB,
    
    -- Status
    status VARCHAR(32) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'refunded', 'cancelled')),
    
    -- Fraud prevention
    ip_address VARCHAR(45),
    user_agent TEXT,
    risk_score FLOAT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Indexes for donations
CREATE INDEX IF NOT EXISTS ix_donations_user_id ON donations(user_id);
CREATE INDEX IF NOT EXISTS ix_donations_status ON donations(status);
CREATE INDEX IF NOT EXISTS ix_donations_transaction_id ON donations(transaction_id);
CREATE INDEX IF NOT EXISTS ix_donations_created_at ON donations(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_donations_payment_provider ON donations(payment_provider);

-- ============================================
-- DONOR CREDITS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS donor_credits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    donation_id UUID NOT NULL UNIQUE REFERENCES donations(id) ON DELETE CASCADE,
    
    -- Credit amounts
    total_credit DECIMAL(12, 2) NOT NULL CHECK (total_credit > 0),
    remaining_credit DECIMAL(12, 2) NOT NULL DEFAULT 0 CHECK (remaining_credit >= 0),
    
    -- Coupon code (unique, secure)
    coupon_code VARCHAR(24) NOT NULL UNIQUE,
    coupon_hash VARCHAR(64),
    
    -- Status and expiration
    status VARCHAR(32) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'depleted', 'expired', 'cancelled')),
    expires_at TIMESTAMPTZ,
    
    -- Metadata
    notes TEXT,
    metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for donor_credits
CREATE INDEX IF NOT EXISTS ix_donor_credits_user_id ON donor_credits(user_id);
CREATE INDEX IF NOT EXISTS ix_donor_credits_coupon_code ON donor_credits(coupon_code);
CREATE INDEX IF NOT EXISTS ix_donor_credits_status ON donor_credits(status);
CREATE INDEX IF NOT EXISTS ix_donor_credits_expires_at ON donor_credits(expires_at);

-- ============================================
-- DONOR REDEMPTIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS donor_redemptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    credit_id UUID NOT NULL REFERENCES donor_credits(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_id VARCHAR(64) REFERENCES orders(id) ON DELETE SET NULL,
    
    -- Redemption details
    amount_used DECIMAL(12, 2) NOT NULL CHECK (amount_used > 0),
    balance_before DECIMAL(12, 2) NOT NULL,
    balance_after DECIMAL(12, 2) NOT NULL CHECK (balance_after >= 0),
    
    -- Product details (for tracking)
    product_id VARCHAR(64),
    product_name VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for donor_redemptions
CREATE INDEX IF NOT EXISTS ix_donor_redemptions_credit_id ON donor_redemptions(credit_id);
CREATE INDEX IF NOT EXISTS ix_donor_redemptions_order_id ON donor_redemptions(order_id);
CREATE INDEX IF NOT EXISTS ix_donor_redemptions_user_id ON donor_redemptions(user_id);
CREATE INDEX IF NOT EXISTS ix_donor_redemptions_created_at ON donor_redemptions(created_at DESC);

-- ============================================
-- DONATION CONFIG TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS donation_config (
    id SERIAL PRIMARY KEY,
    
    -- Amount limits
    min_donation_amount DECIMAL(12, 2) NOT NULL DEFAULT 1.00,
    max_donation_amount DECIMAL(12, 2) NOT NULL DEFAULT 10000.00,
    
    -- Preset amounts (JSON array)
    preset_amounts JSONB NOT NULL DEFAULT '[10, 25, 50, 100]'::jsonb,
    
    -- Credit expiration (days from creation, null = no expiration)
    default_expiry_days INTEGER DEFAULT 365,
    
    -- Feature flags
    enable_custom_amounts BOOLEAN NOT NULL DEFAULT TRUE,
    enable_recurring BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Messaging
    hero_title VARCHAR(255),
    hero_subtitle TEXT,
    benefits_text JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by UUID
);

-- ============================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_donations_updated_at
    BEFORE UPDATE ON donations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_donor_credits_updated_at
    BEFORE UPDATE ON donor_credits
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_donation_config_updated_at
    BEFORE UPDATE ON donation_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- FUNCTIONS FOR COUPON GENERATION
-- ============================================
CREATE OR REPLACE FUNCTION generate_donor_coupon_code()
RETURNS VARCHAR(24) AS $$
DECLARE
    chars VARCHAR(62) := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    result VARCHAR(24) := 'DONOR-';
    i INTEGER;
BEGIN
    -- Generate 6 random characters after DONOR-
    FOR i IN 1..6 LOOP
        result := result || SUBSTRING(chars FROM (FLOOR(RANDOM() * LENGTH(chars))::INTEGER + 1) FOR 1);
    END LOOP;
    
    -- Add 4 more for uniqueness
    result := result || '-';
    FOR i IN 1..4 LOOP
        result := result || SUBSTRING(chars FROM (FLOOR(RANDOM() * LENGTH(chars))::INTEGER + 1) FOR 1);
    END LOOP;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- FUNCTION TO CHECK AND UPDATE EXPIRED CREDITS
-- ============================================
CREATE OR REPLACE FUNCTION check_expired_credits()
RETURNS void AS $$
BEGIN
    UPDATE donor_credits
    SET status = 'expired'
    WHERE status = 'active'
      AND expires_at IS NOT NULL
      AND expires_at < NOW();
      
    UPDATE donor_credits
    SET status = 'depleted'
    WHERE status = 'active'
      AND remaining_credit = 0;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- INITIAL CONFIGURATION
-- ============================================
INSERT INTO donation_config (
    min_donation_amount,
    max_donation_amount,
    preset_amounts,
    default_expiry_days,
    enable_custom_amounts,
    hero_title,
    hero_subtitle,
    benefits_text
) VALUES (
    1.00,
    10000.00,
    '[10, 25, 50, 100, 250, 500]'::jsonb,
    365,
    TRUE,
    'Support the Future of Fashion',
    'Your donation helps us build sustainable, inclusive fashion technology. As a thank you, receive 100% back as shopping credit.',
    '[
        {"title": "100% Shopping Credit", "description": "Every dollar donated becomes store credit"},
        {"title": "Exclusive Access", "description": "Early access to new collections and features"},
        {"title": "Support Sustainability", "description": "Help us reduce fashion waste and promote ethical practices"}
    ]'::jsonb
) ON CONFLICT DO NOTHING;

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================
ALTER TABLE donations ENABLE ROW LEVEL SECURITY;
ALTER TABLE donor_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE donor_redemptions ENABLE ROW LEVEL SECURITY;

-- Users can view their own donations
CREATE POLICY donations_select_own ON donations
    FOR SELECT USING (auth.uid()::uuid = user_id);

-- Users can insert their own donations (handled by backend)
CREATE POLICY donations_insert_own ON donations
    FOR INSERT WITH CHECK (auth.uid()::uuid = user_id);

-- Users can view their own credits
CREATE POLICY donor_credits_select_own ON donor_credits
    FOR SELECT USING (auth.uid()::uuid = user_id);

-- Users can view their own redemptions
CREATE POLICY donor_redemptions_select_own ON donor_redemptions
    FOR SELECT USING (auth.uid()::uuid = user_id);

-- Service role has full access (for backend operations)
CREATE POLICY donations_service_all ON donations
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY donor_credits_service_all ON donor_credits
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY donor_redemptions_service_all ON donor_redemptions
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- ============================================
-- GRANT PERMISSIONS
-- ============================================
GRANT SELECT, INSERT, UPDATE ON donations TO authenticated;
GRANT SELECT, INSERT, UPDATE ON donor_credits TO authenticated;
GRANT SELECT, INSERT ON donor_redemptions TO authenticated;
GRANT ALL ON donation_config TO authenticated;

-- ============================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================
COMMENT ON TABLE donations IS 'User donations with payment tracking. Each donation generates a donor credit.';
COMMENT ON TABLE donor_credits IS 'Shopping credit generated from donations. Tracks balance and expiration.';
COMMENT ON TABLE donor_redemptions IS 'Records of credit usage on purchases.';
COMMENT ON TABLE donation_config IS 'System configuration for donation feature.';
