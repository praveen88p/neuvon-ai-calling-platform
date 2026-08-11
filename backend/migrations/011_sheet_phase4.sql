-- ============================================================================
-- Migration 011: Phase 4 — Audit logging table
--
-- Creates sheet_audit_log for tracking all significant events:
-- connection changes, lead calls, write-backs, errors.
-- ============================================================================

CREATE TABLE IF NOT EXISTS sheet_audit_log (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID        NOT NULL,
    connection_id   UUID        REFERENCES sheet_connections(id) ON DELETE SET NULL,
    lead_id         UUID        REFERENCES sheet_leads(id) ON DELETE SET NULL,

    -- What happened
    event_type      TEXT        NOT NULL,
    -- e.g. connection.created, connection.paused, lead.call_triggered,
    --      lead.call_completed, lead.writeback_done, lead.duplicate_skipped,
    --      lead.rate_limit_queued, poll.error_auth, poll.error_network

    -- Contextual data
    details         JSONB       NOT NULL DEFAULT '{}',
    -- e.g. {"phone": "91xxxxxx", "run_id": 123, "tag": "qualified"}

    severity        TEXT        NOT NULL DEFAULT 'info'
                    CHECK (severity IN ('debug', 'info', 'warning', 'error')),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Org-scoped queries
CREATE INDEX IF NOT EXISTS idx_sheet_audit_org
    ON sheet_audit_log(organization_id, created_at DESC);

-- Connection-scoped queries
CREATE INDEX IF NOT EXISTS idx_sheet_audit_connection
    ON sheet_audit_log(connection_id, created_at DESC)
    WHERE connection_id IS NOT NULL;

-- Event type filtering
CREATE INDEX IF NOT EXISTS idx_sheet_audit_event_type
    ON sheet_audit_log(event_type, created_at DESC);

-- RLS
ALTER TABLE sheet_audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY sheet_audit_log_org_isolation ON sheet_audit_log
    FOR ALL USING (TRUE);

-- Add concurrent_calls_limit column to sheet_connections (rate limiting)
ALTER TABLE sheet_connections
    ADD COLUMN IF NOT EXISTS max_concurrent_calls INTEGER NOT NULL DEFAULT 5;

-- Add duplicate_window_hours: skip re-calling same phone within N hours
ALTER TABLE sheet_connections
    ADD COLUMN IF NOT EXISTS duplicate_window_hours INTEGER NOT NULL DEFAULT 24;

-- Add needs_reauth flag (error recovery)
ALTER TABLE sheet_connections
    ADD COLUMN IF NOT EXISTS needs_reauth BOOLEAN NOT NULL DEFAULT FALSE;

-- Add consecutive_error_count for auto-pause on repeated failures
ALTER TABLE sheet_connections
    ADD COLUMN IF NOT EXISTS consecutive_error_count INTEGER NOT NULL DEFAULT 0;
