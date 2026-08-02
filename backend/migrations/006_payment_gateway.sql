-- ============================================================================
-- 006: Payment Gateway — minute_packs table + org billing columns
-- Supports pre-paid minute top-ups via Razorpay Orders API.
-- Minutes never expire. Calls blocked when balance = 0.
-- ============================================================================

-- ── New table: minute_packs ─────────────────────────────────────────────────
-- Each row = one purchased minute bundle

CREATE TABLE IF NOT EXISTS minute_packs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    minutes_purchased NUMERIC(10,2) NOT NULL,
    minutes_remaining NUMERIC(10,2) NOT NULL,
    rate_at_purchase NUMERIC(8,2) NOT NULL,
    amount_paid NUMERIC(10,2) NOT NULL,
    razorpay_order_id TEXT DEFAULT NULL,
    razorpay_payment_id TEXT DEFAULT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'paid', 'refunded', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_minute_packs_org_id ON minute_packs(organization_id);
CREATE INDEX idx_minute_packs_status ON minute_packs(organization_id, status);
CREATE INDEX idx_minute_packs_razorpay ON minute_packs(razorpay_order_id);

-- ── New columns on organizations ────────────────────────────────────────────
-- minute_balance: cached total of available minutes across all active packs
-- razorpay_customer_id: Razorpay customer ref (for future subscriptions)

ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS minute_balance NUMERIC(10,2) NOT NULL DEFAULT 0.00;

ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS razorpay_customer_id TEXT DEFAULT NULL;

-- ── New columns on billing_records ──────────────────────────────────────────
-- record_type: differentiates subscription vs topup vs usage records
-- razorpay_payment_id: payment ref
-- minutes_purchased: for topup records
-- description: human-readable

ALTER TABLE billing_records
    ADD COLUMN IF NOT EXISTS record_type TEXT DEFAULT 'usage'
        CHECK (record_type IN ('subscription', 'topup', 'usage'));

ALTER TABLE billing_records
    ADD COLUMN IF NOT EXISTS razorpay_payment_id TEXT DEFAULT NULL;

ALTER TABLE billing_records
    ADD COLUMN IF NOT EXISTS minutes_purchased NUMERIC(10,2) DEFAULT NULL;

ALTER TABLE billing_records
    ADD COLUMN IF NOT EXISTS description TEXT DEFAULT NULL;

-- ── RLS for minute_packs ────────────────────────────────────────────────────
ALTER TABLE minute_packs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "minute_packs_org_isolation" ON minute_packs
    USING (organization_id = current_setting('app.current_organization_id')::uuid);
