-- ============================================================================
-- 003: MAKE call_run_id NULLABLE ON appointments
-- ============================================================================
-- Appointments can now be booked directly via Dograh Tool during a live call
-- (before the call_run record exists) or without any call at all.
-- ============================================================================

ALTER TABLE appointments ALTER COLUMN call_run_id DROP NOT NULL;
