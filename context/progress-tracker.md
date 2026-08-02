# Progress Tracker

Update this file after every completed feature. Any AI agent reading this should immediately know what is done, what is in progress, and what is next.

---

## Current Status

**Phase:** Settings Page Refactor (COMPLETE)
**Last completed:** Settings page refactored for production
**Next:** Super admin panel / data verification

---

## Progress

### Phase 1 — Foundation & Auth

- [x] 01 Backend Project Scaffolding
- [x] 02 InsForge Database Schema
- [x] 03 Authentication & RBAC
- [x] 04 Organization Management

### Phase 2 — Dograh Integration Core

- [x] 05 Dograh Client & Agent Management
- [x] 06 Outbound Call Triggering
- [x] 07 Webhook Receiver

### Phase 3 — Campaigns & Calls

- [x] 08 Campaign Management
- [x] 09 Call History & Details
- [x] 10 Live Calls — WebSocket

### Phase 4 — Phone Numbers & Telephony

- [x] 11 Telephony Configuration & Phone Numbers

### Phase 5 — Analytics & Billing

- [x] 12 Analytics API
- [x] 13 Billing Engine & Razorpay
- [x] 14 Appointments

### Phase 6 — Settings & Admin

- [x] 15 Settings (Client-Facing) — refactored: removed API keys + white-label, read-only org
- [x] 16 Admin Endpoints
- [x] 17 Frontend Integration

### Frontend Theme Overhaul

- [x] 18 CSS Theme Foundation — hex-based warm brown/amber tokens
- [x] 19 Inline HSL → hex migration (40 references)
- [x] 20 Hardcoded color removal (Login, Register, StatusBadge, LiveCalls, UploadLeads, CallHistory, ProtectedRoute)
- [x] 21 Brand identity → "Neuvon" + sidebar tagline
- [x] 22 Context files updated (ui-tokens.md, ui-rules.md, ui-registry.md)

---

## Decisions Made During Build

_Add decisions here as they are made during implementation._

- **Feature 05:** Agent endpoints use dual-storage pattern. Create/update in Dograh first, then sync local `dograh_agent_mappings` table. All list/access-control queries hit local DB only for speed. Detail views proxy to Dograh for full workflow definitions. Two creation paths: `from-definition` (explicit nodes/edges) and `from-template` (natural language).
- **Feature 06:** Call trigger validates E.164 phone format via Pydantic field_validator. Resolves workflow_uuid from local mapping before calling Dograh. Creates local `call_runs` record for dual-storage tracking. PostHog `call_triggered` event fired on every successful trigger.
- **Feature 07:** Webhook is unauthenticated (uses HMAC signature instead). Idempotent via `dograh_run_id` dedup key. Resolves org from workflow_id via agent mappings. Skips local insert when org can't be resolved (orphan webhooks). Placeholder WEBHOOK_SECRET values bypass verification for development.
- **Feature 08:** Full campaign lifecycle via dual-storage pattern. 10 endpoints covering upload contacts CSV, create/list/get/update campaigns, start/pause/resume, progress stats, and run records. Agent ownership verified via local `dograh_agent_mappings` before campaign creation. InsForge `insert()` is async (no `.execute()` chaining). All operations org-scoped. 14/14 tests passed.
- **Feature 09:** Paginated call history with 11 filter params mapped to Dograh's filter API. Recording and transcript download URL endpoints. History route uses `GET /calls/history` placed before `/{run_id}` to avoid route conflicts. Dograh response normalization handles both list and dict formats. 14/14 tests passed.
- **Feature 10:** WebSocket endpoint at `/ws/live-calls` with JWT query param authentication. LiveCallManager singleton with Redis pub/sub support (falls back to in-memory for single-instance). Heartbeat every 30s, ping/pong support. Webhook service publishes LiveCallUpdate events when call status changes arrive. 6/6 tests passed.
- **Feature 11:** Pure proxy layer to Dograh telephony APIs. 13 endpoints: provider metadata, 6 config CRUD (create/list/get/update/delete + set-default-outbound), 6 phone number CRUD (add/list/get/update/delete + set-default-caller). DograhClient expanded with 14 telephony methods. All org-scoped via Dograh API key. 16/16 tests passed.
- **Feature 12:** Analytics API with 5 GET endpoints under `/analytics`: overview KPIs, calls-over-time timeseries, disposition breakdown, agent performance, campaign performance. All org-scoped, date-range filterable. Aggregates from local `call_runs` table with name resolution from `dograh_agent_mappings` and `campaigns`. Import verified — 5/5 routes loaded.
- **Feature 13:** Billing refactored from hardcoded plan tiers (free/starter/pro) to per-org custom `rate_per_minute` column (default ₹3.50). Cost = minutes × rate. Rate is set by Neuvon admin (super admin panel, built later). Removed `GET /billing/plan` endpoint and `PlanDetails` schema. `GET /billing/usage` now returns `rate_per_minute`, `total_cost`, `minutes_limit`, `minutes_remaining`. Razorpay order/verify/invoice endpoints kept for future use.
- **Feature 14:** Appointment management with 4 endpoints: GET list (paginated + status filter), GET by ID, POST create, PATCH update. Auto-extraction from call `gathered_context` integrated into webhook service — when a completed call has `appointment` or `booking` keys in gathered_context, an appointment is auto-created. AppointmentService validates call_run ownership before manual creation. Import verified — 4/4 routes loaded.
- **Feature 15:** Settings refactored for production. Removed API key endpoints (CRUD) and org update endpoint from client-facing settings. Org settings tab is now read-only (name, ID, member-since). Profile tab kept as-is (name, phone, role). Team tab fixed: URL changed from `/api/v1/settings/team` (404) to `/api/v1/organizations/me/members` (correct). Billing tab shows per-org custom rate × usage instead of plan tiers. API keys, white-labeling, and org editing deferred to super admin panel. Frontend Settings.tsx rewritten with 4 tabs (removed API Keys tab). Migration `004_billing_custom_rate.sql` adds `rate_per_minute` column.
- **Feature 16:** Admin endpoints with 4 GET routes under `/admin`: organizations listing with member counts and call stats, platform-wide usage stats (orgs, users, calls, minutes, campaigns, agents), full audit trail, and system-wide logs with level filtering. All routes guarded by `platform_admin` role check in AdminService. Cross-org visibility — no organization_id scoping. Pagination via fetch-all + Python slice. Import verified — 4/4 routes loaded.
- **Feature 17:** Frontend integration layer. Made `DEMO_MODE` env-driven via `VITE_DEMO_MODE` (defaults `true`). Created `apiPaths.ts` with centralized backend path constants. Added `resolvePath()` in `api.ts` that maps old demo-era `/api/*` paths to real `/api/v1/*` backend endpoints. Updated `AuthContext` to use `/api/v1/auth/*` paths and parse backend response format (`tokens.access_token` + `user` object). Rewrote `Settings.tsx` with full API integration — profile editing, org settings, API key CRUD with copy-to-clipboard. Created `.env` file for frontend. TypeScript and Vite build verified — zero errors.
- **Frontend Theme Overhaul:** Migrated CSS from HSL values to direct hex tokens. New color palette: primary warm brown (#644a40), secondary amber (#ffdfb5), background off-white (#f9f9f9). Removed all `hsl()` wrappers in tailwind.config.ts. Replaced 40+ inline `hsl(var(--xxx))` references. Eliminated all `slate-*`, `bg-status-*` hardcoded classes in favor of semantic tokens. Brand identity updated to "Neuvon". Login/Register pages use warm brown gradient backgrounds. Light mode only (dark mode deferred).

---

## Notes

_Add notes here as the build progresses — workarounds, patterns, anything that differs from the context files._

- **InsForge SDK update() bug (critical):** The InsForge Python SDK's `update()` method is async and returns a coroutine — `.eq()` filters must be chained BEFORE `.update()`, not after. Additionally, `update()` crashes with `json.JSONDecodeError` when the backend returns an empty body (204), even though the update succeeds. All services patched with `except json.JSONDecodeError: pass` to handle this. Correct pattern: `await db.from_("table").eq("col", val).update(data)`. The `insert()` method takes a list of dicts (`insert([{...}])`), not a single dict.
- **Missing `updated_at` column on `users` table:** Had to add `ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()` — the schema creation script didn't include it.

