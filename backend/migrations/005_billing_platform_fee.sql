-- ============================================================================
-- 005: Add platform fee and plan label to organizations
-- Supports custom per-org fixed monthly fees and custom plan names.
-- ============================================================================

ALTER TABLE organizations
  ADD COLUMN IF NOT EXISTS platform_fee NUMERIC(10,2) NOT NULL DEFAULT 0.00;

ALTER TABLE organizations
  ADD COLUMN IF NOT EXISTS plan_label TEXT DEFAULT NULL;
