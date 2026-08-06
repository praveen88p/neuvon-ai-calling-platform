-- Migration 007: Add inbound routing fields to phone_numbers table
-- Adds number_normalized (E.164 without spaces) and inbound_workflow_id so our
-- inbound router can do a fast local lookup without hitting Dograh on every call.

ALTER TABLE phone_numbers
    ADD COLUMN IF NOT EXISTS number_normalized TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS inbound_workflow_id INTEGER;

-- Index for fast inbound lookup: "which workflow handles calls to this number?"
CREATE INDEX IF NOT EXISTS idx_phone_numbers_number_normalized
    ON phone_numbers (number_normalized);

-- Backfill: strip spaces from existing `number` values
UPDATE phone_numbers
SET number_normalized = REGEXP_REPLACE(number, '\s+', '', 'g')
WHERE number_normalized = '';
