-- ============================================================================
-- Migration 009: Sheet Connections & Lead Tracking
--
-- PURPOSE: Enable spreadsheet-to-call integration. Clients connect a Google
--          Sheet containing leads. The system polls for new rows, triggers
--          AI calls via Dograh, and writes results back to the sheet.
--
-- TABLES:
--   sheet_connections    — One row per connected spreadsheet (org-scoped)
--   sheet_leads          — One row per lead row (tracks row → call mapping)
--   scheduled_callbacks  — Scheduled re-calls ("Call me at X")
--
-- Run this in InsForge SQL editor (Supabase dashboard → SQL Editor).
-- ============================================================================

-- Table 1: Sheet connections
CREATE TABLE IF NOT EXISTS sheet_connections (
    id                      UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id         UUID        NOT NULL,

    -- Sheet provider + identification
    provider                TEXT        NOT NULL DEFAULT 'google_sheets'
                            CHECK (provider IN ('google_sheets', 'excel_online')),
    sheet_url               TEXT        NOT NULL,
    spreadsheet_id          TEXT        NOT NULL,
    sheet_name              TEXT        DEFAULT 'Sheet1',

    -- Column mapping (user-configured): {"phone": "B", "name": "A", "email": "C"}
    column_mapping          JSONB       NOT NULL DEFAULT '{}',

    -- Which Dograh agent handles calls for this sheet
    agent_workflow_id       INTEGER     NOT NULL,

    -- Auth: service account JSON (encrypted at rest by InsForge)
    credentials_json        TEXT,

    -- Polling state
    last_row_processed      INTEGER     NOT NULL DEFAULT 1,
    polling_interval_secs   INTEGER     NOT NULL DEFAULT 60,
    is_active               BOOLEAN     NOT NULL DEFAULT true,
    last_polled_at          TIMESTAMPTZ,
    last_error              TEXT,

    -- Stats
    total_leads_found       INTEGER     NOT NULL DEFAULT 0,
    total_leads_called      INTEGER     NOT NULL DEFAULT 0,
    total_leads_qualified   INTEGER     NOT NULL DEFAULT 0,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Table 2: Individual leads from sheets
CREATE TABLE IF NOT EXISTS sheet_leads (
    id                      UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    connection_id           UUID        NOT NULL REFERENCES sheet_connections(id) ON DELETE CASCADE,
    organization_id         UUID        NOT NULL,

    -- Source row tracking
    row_number              INTEGER     NOT NULL,
    phone_number            TEXT        NOT NULL,
    lead_data               JSONB       DEFAULT '{}',

    -- Call tracking
    dograh_run_id           INTEGER,
    call_status             TEXT        NOT NULL DEFAULT 'pending'
                            CHECK (call_status IN (
                                'pending', 'calling', 'completed', 'failed',
                                'busy', 'no_answer', 'callback_scheduled'
                            )),
    call_summary            TEXT,
    lead_tag                TEXT,
    callback_at             TIMESTAMPTZ,
    writeback_done          BOOLEAN     NOT NULL DEFAULT false,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Prevent duplicate processing of the same row in a connection
    UNIQUE(connection_id, row_number)
);

-- Table 3: Scheduled callbacks
CREATE TABLE IF NOT EXISTS scheduled_callbacks (
    id                      UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id         UUID        NOT NULL,
    sheet_lead_id           UUID        REFERENCES sheet_leads(id) ON DELETE SET NULL,

    phone_number            TEXT        NOT NULL,
    workflow_id             INTEGER     NOT NULL,
    initial_context         JSONB       DEFAULT '{}',

    callback_at             TIMESTAMPTZ NOT NULL,
    status                  TEXT        NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'triggered', 'completed', 'cancelled')),
    triggered_run_id        INTEGER,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Indexes ──────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_sheet_connections_org
    ON sheet_connections(organization_id);

CREATE INDEX IF NOT EXISTS idx_sheet_connections_active
    ON sheet_connections(is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_sheet_leads_connection
    ON sheet_leads(connection_id);

CREATE INDEX IF NOT EXISTS idx_sheet_leads_org
    ON sheet_leads(organization_id);

CREATE INDEX IF NOT EXISTS idx_sheet_leads_run_id
    ON sheet_leads(dograh_run_id) WHERE dograh_run_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_sheet_leads_status
    ON sheet_leads(call_status);

CREATE INDEX IF NOT EXISTS idx_scheduled_callbacks_due
    ON scheduled_callbacks(callback_at, status)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_scheduled_callbacks_org
    ON scheduled_callbacks(organization_id);

-- ── RLS ──────────────────────────────────────────────────────────────────

ALTER TABLE sheet_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE sheet_leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_callbacks ENABLE ROW LEVEL SECURITY;

-- Service-role bypass (our backend uses service key)
CREATE POLICY sheet_connections_service_all ON sheet_connections
    FOR ALL USING (true);

CREATE POLICY sheet_leads_service_all ON sheet_leads
    FOR ALL USING (true);

CREATE POLICY scheduled_callbacks_service_all ON scheduled_callbacks
    FOR ALL USING (true);
