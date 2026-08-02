-- ============================================================================
-- 004: Add per-org custom billing rate
-- Replaces hardcoded plan tiers with a flexible rate_per_minute column.
-- Rate is set by Neuvon (super admin panel, built later).
-- Default: ₹3.50/min for all existing orgs.
-- ============================================================================

ALTER TABLE organizations
  ADD COLUMN IF NOT EXISTS rate_per_minute NUMERIC(8,2) NOT NULL DEFAULT 3.50;

-- Ensure webhook_url and timezone columns exist
-- (referenced in code but may not be in initial migration)
ALTER TABLE organizations
  ADD COLUMN IF NOT EXISTS webhook_url TEXT DEFAULT NULL;

ALTER TABLE organizations
  ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'Asia/Kolkata';
