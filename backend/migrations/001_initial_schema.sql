-- ============================================================================
-- Neuvon AI Calling Platform — InsForge Database Schema
-- Run this SQL in InsForge's SQL editor to create all tables with RLS policies.
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. ORGANIZATIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    org_type TEXT NOT NULL DEFAULT 'direct' CHECK (org_type IN ('direct', 'reseller')),
    white_label JSONB DEFAULT NULL,
    dograh_api_key TEXT DEFAULT NULL,
    billing_plan TEXT NOT NULL DEFAULT 'free' CHECK (billing_plan IN ('free', 'starter', 'growth', 'enterprise')),
    usage_quota JSONB DEFAULT '{"monthly_minutes": 1000, "max_agents": 5, "max_campaigns": 10}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_org_type ON organizations(org_type);

-- ============================================================================
-- 2. USERS
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('platform_admin', 'owner', 'admin', 'member')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_organization_id ON users(organization_id);
CREATE INDEX idx_users_email ON users(email);

-- ============================================================================
-- 3. DOGRAH AGENT MAPPINGS
-- ============================================================================
CREATE TABLE IF NOT EXISTS dograh_agent_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    dograh_workflow_id INTEGER NOT NULL,
    dograh_workflow_uuid TEXT NOT NULL DEFAULT '',
    agent_name TEXT NOT NULL DEFAULT '',
    agent_status TEXT NOT NULL DEFAULT 'active' CHECK (agent_status IN ('active', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_mappings_organization_id ON dograh_agent_mappings(organization_id);
CREATE INDEX idx_agent_mappings_workflow_id ON dograh_agent_mappings(dograh_workflow_id);

-- ============================================================================
-- 4. CAMPAIGNS
-- ============================================================================
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    dograh_campaign_id INTEGER NOT NULL,
    dograh_workflow_id INTEGER NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'running', 'paused', 'completed', 'failed')),
    total_contacts INTEGER NOT NULL DEFAULT 0,
    contacts_processed INTEGER NOT NULL DEFAULT 0,
    concurrency INTEGER NOT NULL DEFAULT 1,
    retry_config JSONB DEFAULT NULL,
    schedule_config JSONB DEFAULT NULL,
    contact_list_id TEXT DEFAULT NULL,
    started_at TIMESTAMPTZ DEFAULT NULL,
    completed_at TIMESTAMPTZ DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_campaigns_organization_id ON campaigns(organization_id);
CREATE INDEX idx_campaigns_dograh_campaign_id ON campaigns(dograh_campaign_id);

-- ============================================================================
-- 5. CALL RUNS
-- ============================================================================
CREATE TABLE IF NOT EXISTS call_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    dograh_run_id INTEGER NOT NULL UNIQUE,
    dograh_workflow_id INTEGER NOT NULL,
    campaign_id UUID DEFAULT NULL REFERENCES campaigns(id) ON DELETE SET NULL,
    call_type TEXT NOT NULL DEFAULT 'outbound' CHECK (call_type IN ('outbound', 'inbound')),
    status TEXT NOT NULL DEFAULT 'initiated',
    phone_number TEXT NOT NULL DEFAULT '',
    caller_number TEXT NOT NULL DEFAULT '',
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    initial_context JSONB DEFAULT NULL,
    gathered_context JSONB DEFAULT NULL,
    transcript_url TEXT DEFAULT NULL,
    recording_url TEXT DEFAULT NULL,
    public_access_token TEXT DEFAULT NULL,
    cost_info JSONB DEFAULT NULL,
    annotations JSONB DEFAULT NULL,
    disposition TEXT DEFAULT NULL,
    started_at TIMESTAMPTZ DEFAULT NULL,
    completed_at TIMESTAMPTZ DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_call_runs_organization_id ON call_runs(organization_id);
CREATE INDEX idx_call_runs_dograh_run_id ON call_runs(dograh_run_id);
CREATE INDEX idx_call_runs_dograh_workflow_id ON call_runs(dograh_workflow_id);
CREATE INDEX idx_call_runs_campaign_id ON call_runs(campaign_id);
CREATE INDEX idx_call_runs_created_at ON call_runs(created_at DESC);

-- ============================================================================
-- 6. TELEPHONY CONFIGS
-- ============================================================================
CREATE TABLE IF NOT EXISTS telephony_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    dograh_config_id INTEGER NOT NULL,
    provider TEXT NOT NULL DEFAULT '',
    label TEXT NOT NULL DEFAULT '',
    is_default_outbound BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_telephony_configs_organization_id ON telephony_configs(organization_id);

-- ============================================================================
-- 7. PHONE NUMBERS
-- ============================================================================
CREATE TABLE IF NOT EXISTS phone_numbers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    telephony_config_id UUID NOT NULL REFERENCES telephony_configs(id) ON DELETE CASCADE,
    dograh_phone_id INTEGER NOT NULL,
    number TEXT NOT NULL DEFAULT '',
    label TEXT NOT NULL DEFAULT '',
    is_default_caller BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_phone_numbers_organization_id ON phone_numbers(organization_id);
CREATE INDEX idx_phone_numbers_telephony_config_id ON phone_numbers(telephony_config_id);

-- ============================================================================
-- 8. BILLING RECORDS
-- ============================================================================
CREATE TABLE IF NOT EXISTS billing_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_minutes NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_calls INTEGER NOT NULL DEFAULT 0,
    total_cost_usd NUMERIC(12,2) NOT NULL DEFAULT 0,
    razorpay_invoice_id TEXT DEFAULT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'overdue')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_billing_records_organization_id ON billing_records(organization_id);

-- ============================================================================
-- 9. APPOINTMENTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    call_run_id UUID NOT NULL REFERENCES call_runs(id) ON DELETE CASCADE,
    contact_name TEXT NOT NULL DEFAULT '',
    contact_phone TEXT NOT NULL DEFAULT '',
    appointment_date TIMESTAMPTZ DEFAULT NULL,
    notes TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'confirmed', 'cancelled', 'completed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_appointments_organization_id ON appointments(organization_id);
CREATE INDEX idx_appointments_call_run_id ON appointments(call_run_id);

-- ============================================================================
-- 10. AUDIT LOG
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL DEFAULT '',
    resource_id TEXT NOT NULL DEFAULT '',
    metadata JSONB DEFAULT NULL,
    ip_address TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_log_organization_id ON audit_log(organization_id);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- Every tenant table filtered by organization_id.
-- ============================================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE dograh_agent_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE telephony_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE phone_numbers ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- RLS policies — service role bypasses these; anon/authenticated scoped to org
CREATE POLICY "users_org_isolation" ON users
    USING (organization_id = (current_setting('app.current_org_id', TRUE))::uuid);

CREATE POLICY "agent_mappings_org_isolation" ON dograh_agent_mappings
    USING (organization_id = (current_setting('app.current_org_id', TRUE))::uuid);

CREATE POLICY "campaigns_org_isolation" ON campaigns
    USING (organization_id = (current_setting('app.current_org_id', TRUE))::uuid);

CREATE POLICY "call_runs_org_isolation" ON call_runs
    USING (organization_id = (current_setting('app.current_org_id', TRUE))::uuid);

CREATE POLICY "telephony_configs_org_isolation" ON telephony_configs
    USING (organization_id = (current_setting('app.current_org_id', TRUE))::uuid);

CREATE POLICY "phone_numbers_org_isolation" ON phone_numbers
    USING (organization_id = (current_setting('app.current_org_id', TRUE))::uuid);

CREATE POLICY "billing_records_org_isolation" ON billing_records
    USING (organization_id = (current_setting('app.current_org_id', TRUE))::uuid);

CREATE POLICY "appointments_org_isolation" ON appointments
    USING (organization_id = (current_setting('app.current_org_id', TRUE))::uuid);

CREATE POLICY "audit_log_org_isolation" ON audit_log
    USING (organization_id = (current_setting('app.current_org_id', TRUE))::uuid);

-- ============================================================================
-- UPDATED_AT TRIGGER (auto-update on row modification)
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at_organizations
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER set_updated_at_agent_mappings
    BEFORE UPDATE ON dograh_agent_mappings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
