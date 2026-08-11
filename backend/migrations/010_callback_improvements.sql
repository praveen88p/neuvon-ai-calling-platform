-- ============================================================================
-- Migration 010: Callback scheduling improvements (Phase 3)
--
-- Adds retry_count, display_time, triggered_run_id, and 'failed' status
-- to the scheduled_callbacks table created in migration 009.
-- ============================================================================

-- Add retry_count for exponential backoff
ALTER TABLE scheduled_callbacks
    ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;

-- Add display_time for human-readable display in frontend
ALTER TABLE scheduled_callbacks
    ADD COLUMN IF NOT EXISTS display_time TEXT;

-- Add triggered_run_id to track which Dograh run fired the callback
-- (may already exist from 009 — use IF NOT EXISTS pattern)
ALTER TABLE scheduled_callbacks
    ADD COLUMN IF NOT EXISTS triggered_run_id INTEGER;

-- Expand status check constraint to include 'failed'
-- PostgreSQL: drop old constraint, add new one
ALTER TABLE scheduled_callbacks
    DROP CONSTRAINT IF EXISTS scheduled_callbacks_status_check;

ALTER TABLE scheduled_callbacks
    ADD CONSTRAINT scheduled_callbacks_status_check
    CHECK (status IN ('pending', 'triggered', 'completed', 'cancelled', 'failed'));

-- Expand sheet_leads call_status to include 'busy' and 'no_answer'
-- (already in our 009 migration, but may not be in the plan's original version)
ALTER TABLE sheet_leads
    DROP CONSTRAINT IF EXISTS sheet_leads_call_status_check;

ALTER TABLE sheet_leads
    ADD CONSTRAINT sheet_leads_call_status_check
    CHECK (call_status IN (
        'pending', 'calling', 'completed', 'failed',
        'busy', 'no_answer', 'callback_scheduled'
    ));

-- Index for retry polling: find due pending callbacks quickly
CREATE INDEX IF NOT EXISTS idx_scheduled_callbacks_pending_due
    ON scheduled_callbacks(callback_at, status, retry_count)
    WHERE status = 'pending';
