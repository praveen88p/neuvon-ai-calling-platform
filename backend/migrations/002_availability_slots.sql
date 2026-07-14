-- ============================================================================
-- 002: AVAILABILITY SLOTS & OVERRIDES
-- ============================================================================
-- Per-user weekly recurring availability and date-specific overrides.
-- Used by the AI agent (via Dograh Tool) to offer valid appointment times.
-- ============================================================================

-- Weekly recurring schedule (e.g., Mon-Fri 9am-5pm)
CREATE TABLE IF NOT EXISTS availability_slots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    day_of_week INT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),  -- 0=Sunday, 6=Saturday
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_time_range CHECK (start_time < end_time)
);

CREATE INDEX idx_availability_slots_org ON availability_slots(organization_id);
CREATE INDEX idx_availability_slots_user ON availability_slots(user_id);
CREATE INDEX idx_availability_slots_day ON availability_slots(organization_id, day_of_week);

-- Date-specific overrides (block holidays, add extra hours)
CREATE TABLE IF NOT EXISTS availability_overrides (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    override_date DATE NOT NULL,
    is_available BOOLEAN NOT NULL DEFAULT FALSE,  -- FALSE = blocked, TRUE = extra availability
    start_time TIME,       -- NULL when is_available=FALSE (entire day blocked)
    end_time TIME,         -- NULL when is_available=FALSE
    reason TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_availability_overrides_org ON availability_overrides(organization_id);
CREATE INDEX idx_availability_overrides_user_date ON availability_overrides(user_id, override_date);

-- RLS
ALTER TABLE availability_slots ENABLE ROW LEVEL SECURITY;
ALTER TABLE availability_overrides ENABLE ROW LEVEL SECURITY;

CREATE POLICY "availability_slots_org_isolation" ON availability_slots
    USING (organization_id = current_setting('app.current_organization_id')::uuid);

CREATE POLICY "availability_overrides_org_isolation" ON availability_overrides
    USING (organization_id = current_setting('app.current_organization_id')::uuid);
