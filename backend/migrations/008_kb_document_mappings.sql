-- ============================================================================
-- Migration 008: Knowledge Base Document Mappings
--
-- PURPOSE: Isolate KB documents per organization using the same mapping-table
--          pattern as dograh_agent_mappings. Dograh uses a single shared API
--          key for all orgs, so isolation is enforced here in our database.
--
-- PATTERN: On upload → INSERT mapping here.
--          On list   → query our mappings for org, filter Dograh results.
--          On delete → DELETE from Dograh + DELETE mapping here.
--          On search → pass org's document_uuids to Dograh search filter.
--
-- Run this in InsForge SQL editor (Supabase dashboard → SQL Editor).
-- ============================================================================

CREATE TABLE IF NOT EXISTS kb_document_mappings (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    document_uuid   TEXT        NOT NULL UNIQUE,
    filename        TEXT        NOT NULL DEFAULT '',
    file_size_bytes BIGINT      NOT NULL DEFAULT 0,
    mime_type       TEXT        NOT NULL DEFAULT '',
    retrieval_mode  TEXT        NOT NULL DEFAULT 'full_document'
                                CHECK (retrieval_mode IN ('full_document', 'chunked')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kb_docs_org_id
    ON kb_document_mappings (organization_id);

CREATE INDEX IF NOT EXISTS idx_kb_docs_document_uuid
    ON kb_document_mappings (document_uuid);

-- RLS: same pattern as all other tables (dograh_agent_mappings, campaigns, etc.)
ALTER TABLE kb_document_mappings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kb_docs_org_isolation" ON kb_document_mappings
    USING (organization_id = (current_setting('app.current_org_id', TRUE))::uuid);

