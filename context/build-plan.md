# Build Plan

## Core Principle

Backend-first development. Each phase builds a complete vertical slice — from database schema to service layer to API endpoint to frontend integration. Every feature must be testable end-to-end before moving to the next. No invisible infrastructure phases without verifiable outputs.

---

## Phase 1 — Foundation & Auth

### 01 Backend Project Scaffolding

Set up the FastAPI project structure with all core infrastructure.

**Infrastructure:**

- FastAPI application with lifespan events (startup/shutdown)
- CORS middleware configured for frontend origin
- Pydantic Settings for environment configuration
- Async database engine with SQLModel/SQLAlchemy
- Alembic migration setup
- Structlog configuration
- Health check endpoint at `/api/v1/health`
- Root router mounting at `/api/v1`

**Folder structure:**

```
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   ├── dependencies.py
│   │   ├── logging.py
│   │   ├── celery_app.py
│   │   └── posthog.py
│   ├── models/
│   ├── schemas/
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/
│   ├── services/
│   ├── integrations/
│   │   ├── dograh_client.py
│   │   └── razorpay_client.py
│   ├── tasks/
│   └── middleware/
├── alembic/
├── tests/
├── .env.example
├── requirements.txt
└── pyproject.toml
```

**Verification:** `GET /api/v1/health` returns `{"status": "ok"}`.

---

### 02 InsForge Database Schema

All InsForge tables created via SQL migrations or InsForge MCP before any data is written.

**Tables:**

- `organizations` — multi-tenant root entity
- `users` — extends InsForge auth.users with org membership and role
- `organization_members` — join table: user → org with role (owner/admin/member)
- `dograh_agent_mappings` — maps Dograh workflow IDs to organizations
- `campaigns` — local campaign metadata + billing tracking
- `call_runs` — synced from Dograh, enriched with org/billing context
- `phone_number_mappings` — maps Dograh phone numbers to organizations
- `usage_records` — per-organization usage aggregation
- `billing_plans` — pricing tiers and plan definitions
- `invoices` — billing history per organization
- `api_keys` — organization API keys for external integrations
- `audit_log` — all user actions for compliance

**Rules:**

- Every table has `organization_id` column (except `organizations` itself)
- Row Level Security (RLS) policies on all tables — filter by `organization_id`
- UUID primary keys everywhere — never auto-increment integers
- `created_at` and `updated_at` timestamps on every table

**Verification:** All tables visible in InsForge dashboard with RLS enabled.

---

### 03 Authentication & RBAC

InsForge Auth integration + JWT-based session management + role-based access control.

**Endpoints:**

- `POST /api/v1/auth/register` — Create account with email/password via InsForge
- `POST /api/v1/auth/login` — Authenticate and return JWT
- `POST /api/v1/auth/refresh` — Refresh JWT token
- `POST /api/v1/auth/logout` — Invalidate session
- `GET /api/v1/auth/me` — Get current user with org context

**Dependencies:**

- `get_current_user` — validates JWT, returns user with org_id and role
- `require_role("admin")` — guard for admin-only endpoints
- `require_role("owner")` — guard for owner-only endpoints

**Logic:**

- User registers → InsForge creates auth record → backend creates org membership
- JWT contains: user_id, organization_id, role
- Every protected endpoint injects `current_user` via dependency
- Frontend stores JWT in localStorage, sends as `Authorization: Bearer {token}`

**Verification:** Can register, login, and hit `/auth/me` with valid token.

---

### 04 Organization Management

Multi-tenant organization CRUD with member management.

**Endpoints:**

- `POST /api/v1/organizations` — Create organization (becomes owner)
- `GET /api/v1/organizations/me` — Get current user's organization
- `PATCH /api/v1/organizations/me` — Update organization settings
- `POST /api/v1/organizations/me/members` — Invite member (admin+)
- `GET /api/v1/organizations/me/members` — List members
- `PATCH /api/v1/organizations/me/members/{user_id}` — Update member role (owner only)
- `DELETE /api/v1/organizations/me/members/{user_id}` — Remove member (admin+)

**Logic:**

- Organization created on first user registration
- White-label settings stored: display_name, logo_url, primary_color
- Resellers differentiated by `org_type` — no sub-organizations

**Verification:** Can create org, invite member, member can login with org context.

---

## Phase 2 — Dograh Integration Core

### 05 Dograh Client & Agent Management

HTTP client wrapper for Dograh API + agent CRUD endpoints.

**Endpoints:**

- `GET /api/v1/agents` — List agents for current org (proxies Dograh `GET /workflow/fetch`, filtered by org)
- `GET /api/v1/agents/count` — Get agent count by status (proxies Dograh `GET /workflow/count`)
- `GET /api/v1/agents/{workflow_id}` — Get agent details with full workflow definition (proxies Dograh `GET /workflow/fetch/{workflow_id}`)
- `POST /api/v1/agents` — Create agent (proxies Dograh `POST /workflow/create/definition` or `/workflow/create/template`) and map to org
- `PUT /api/v1/agents/{workflow_id}` — Update agent (proxies Dograh `PUT /workflow/{workflow_id}`)
- `PUT /api/v1/agents/{workflow_id}/archive` — Archive/restore agent (proxies Dograh `PUT /workflow/{workflow_id}/status`)
- `POST /api/v1/agents/{workflow_id}/validate` — Validate workflow definition (proxies Dograh `POST /workflow/{workflow_id}/validate`)
- `POST /api/v1/agents/{workflow_id}/test-run` — Create test run without real call (proxies Dograh `POST /workflow/{workflow_id}/runs`)
- `GET /api/v1/agents/{workflow_id}/runs` — List runs for this agent (proxies Dograh `GET /workflow/{workflow_id}/runs`)

**Logic:**

- Backend proxies Dograh API calls, adding org-scoping
- Agent-to-org mapping stored in `dograh_agent_mappings` table
- Only agents mapped to current org are visible
- Platform admin can assign agents across orgs
- Supports both definition-based and template-based agent creation

**Verification:** Can create agent via API, see it in list, get full definition, validate workflow.

---

### 06 Outbound Call Triggering

Trigger single outbound calls via Dograh + track in local DB.

**Endpoints:**

- `POST /api/v1/calls/trigger` — Trigger outbound call
- `GET /api/v1/calls/{run_id}` — Get call run details (transcript, recording, context)

**Logic:**

- Validates phone number format (E.164)
- Calls Dograh `POST /public/agent/workflow/{workflow_uuid}` (by Agent UUID) or `POST /public/agent/{uuid}` (by API Trigger node UUID)
- Passes `initial_context` and optional `telephony_configuration_id`
- Creates local `call_runs` record with org context
- Returns `workflow_run_id` and `workflow_run_name` for tracking

**PostHog event:** `call_triggered`

**Verification:** Can trigger a call, get run ID back, poll for completion.

---

### 07 Webhook Receiver

Receive post-call data from Dograh webhooks + sync to local DB.

**Endpoints:**

- `POST /api/v1/webhooks/dograh` — Receive Dograh post-call webhook

**Logic:**

- Receives webhook payload after each call completes
- Extracts: run_id, duration, transcript, recording URLs, gathered_context, cost_info
- Updates local `call_runs` record with full data
- Triggers Celery task for usage aggregation
- Fires PostHog `call_completed` event

**Verification:** Dograh sends webhook after test call → data appears in local DB.

---

## Phase 3 — Campaigns & Calls

### 08 Campaign Management

Full campaign lifecycle — create, upload contacts, start/pause/resume, monitor.

**Endpoints:**

- `POST /api/v1/campaigns/upload-contacts` — Upload contacts CSV (proxies Dograh `POST /campaign/upload` as multipart form data)
- `POST /api/v1/campaigns` — Create campaign (proxies Dograh `POST /campaign/create`)
- `GET /api/v1/campaigns` — List campaigns for current org (proxies Dograh `GET /campaign/fetch`, filtered)
- `GET /api/v1/campaigns/{id}` — Get campaign details (proxies Dograh `GET /campaign/fetch/{campaign_id}`)
- `PATCH /api/v1/campaigns/{id}` — Update campaign settings (proxies Dograh `PUT /campaign/{campaign_id}`)
- `POST /api/v1/campaigns/{id}/start` — Start campaign (proxies Dograh `POST /campaign/{campaign_id}/start`)
- `POST /api/v1/campaigns/{id}/pause` — Pause campaign (proxies Dograh `POST /campaign/{campaign_id}/pause`)
- `POST /api/v1/campaigns/{id}/resume` — Resume campaign (proxies Dograh `POST /campaign/{campaign_id}/resume`)
- `GET /api/v1/campaigns/{id}/progress` — Get current progress (proxies Dograh `GET /campaign/{campaign_id}/progress`)
- `GET /api/v1/campaigns/{id}/runs` — Get campaign call runs (proxies Dograh `GET /campaign/{campaign_id}/runs`)

**Logic:**

- Creates campaign in both Dograh and local DB
- CSV upload via Dograh's `/campaign/upload` endpoint (multipart form data, NOT presigned S3)
- Start/pause/resume proxied to Dograh with org validation
- Progress polling from Dograh, enriched with local data

**PostHog events:** `campaign_started`, `campaign_completed`, `leads_uploaded`

**Verification:** Can create campaign, upload CSV, start it, see progress, see individual runs.

---

### 09 Call History & Details

Paginated call history with filters + detailed call view.

**Endpoints:**

- `GET /api/v1/calls/history` — Paginated call history for current org (proxies Dograh `GET /organizations/usage/runs`)
- `GET /api/v1/calls/{run_id}` — Full call details (proxies Dograh `GET /workflow/{workflow_id}/runs/{run_id}`)
- `GET /api/v1/calls/{run_id}/recording` — Get recording download URL (uses Dograh `GET /public/download/workflow/{token}/recording`)
- `GET /api/v1/calls/{run_id}/transcript` — Get transcript download URL (uses Dograh `GET /public/download/workflow/{token}/transcript`)

**Query parameters (maps to Dograh's filter API):**

- `page`, `limit` — pagination (Dograh: `page` ≥1, `limit` 1–100)
- `start_date`, `end_date` — date range (ISO 8601 UTC → Dograh query params)
- `agent_id` — filter by workflow (Dograh filter: `{"attribute": "workflowId", "type": "number", "value": {"value": N}}`)
- `campaign_id` — filter by campaign (Dograh filter: `{"attribute": "campaignId", "type": "number", "value": {"value": N}}`)
- `caller_number`, `called_number` — text search on phone numbers (Dograh filter: `text` type)
- `disposition` — filter by disposition code (Dograh filter: `{"attribute": "dispositionCode", "type": "multiSelect", "value": {"codes": [...]}}`)
- `min_duration`, `max_duration` — duration range (Dograh filter: `{"attribute": "duration", "type": "numberRange", "value": {"min": N, "max": N}}`)

**Logic:**

- Queries Dograh's `GET /organizations/usage/runs` with `filters` query param (JSON-encoded array of filter objects)
- Enriches with local org data (billing, org name)
- Date filtering uses dedicated `start_date`/`end_date` query params, NOT a dateRange filter object

**Verification:** Can browse paginated call history with filters, view full call details.

---

### 10 Live Calls — WebSocket

Real-time call status updates via WebSocket for active calls.

**Endpoints:**

- `WS /api/v1/ws/live-calls` — WebSocket for live call status

**Logic:**

- WebSocket connection authenticated via JWT query param
- Redis pub/sub for broadcasting call status changes
- Dograh webhook triggers status update → published to Redis → pushed to connected clients
- Message format: `{ "type": "call_update", "data": { "run_id": 123, "status": "in_progress", "phone_number": "...", "agent_name": "...", "duration": 45 } }`
- Heartbeat every 30 seconds to keep connection alive
- Client reconnection with exponential backoff

**Verification:** Connect WebSocket, trigger a call, see real-time status updates.

---

## Phase 4 — Phone Numbers & Telephony

### 11 Telephony Configuration & Phone Numbers

Manage telephony providers and phone numbers per organization.

**Endpoints:**

- `GET /api/v1/telephony/providers` — List supported providers and required credential fields (proxies Dograh `GET /organizations/telephony-providers/metadata`)
- `GET /api/v1/telephony/configs` — List telephony configs for org (proxies Dograh `GET /organizations/telephony-configs`)
- `POST /api/v1/telephony/configs` — Create telephony configuration (proxies Dograh `POST /organizations/telephony-configs`)
- `GET /api/v1/telephony/configs/{id}` — Get config details (proxies Dograh `GET /organizations/telephony-configs/{config_id}`)
- `PUT /api/v1/telephony/configs/{id}` — Update config (proxies Dograh `PUT /organizations/telephony-configs/{config_id}`)
- `DELETE /api/v1/telephony/configs/{id}` — Delete config (proxies Dograh `DELETE /organizations/telephony-configs/{config_id}`)
- `POST /api/v1/telephony/configs/{id}/set-default-outbound` — Set as org-wide default outbound (proxies Dograh `POST /organizations/telephony-configs/{config_id}/set-default-outbound`)
- `GET /api/v1/telephony/configs/{id}/phone-numbers` — List phone numbers (proxies Dograh `GET /organizations/telephony-configs/{config_id}/phone-numbers`)
- `POST /api/v1/telephony/configs/{id}/phone-numbers` — Add phone number (proxies Dograh `POST /organizations/telephony-configs/{config_id}/phone-numbers`)
- `GET /api/v1/telephony/configs/{id}/phone-numbers/{num_id}` — Get phone number (proxies Dograh `GET .../phone-numbers/{phone_number_id}`)
- `PUT /api/v1/telephony/configs/{id}/phone-numbers/{num_id}` — Update number (proxies Dograh `PUT .../phone-numbers/{phone_number_id}`)
- `DELETE /api/v1/telephony/configs/{id}/phone-numbers/{num_id}` — Remove number (proxies Dograh `DELETE .../phone-numbers/{phone_number_id}`)
- `POST /api/v1/telephony/configs/{id}/phone-numbers/{num_id}/set-default-caller` — Set default caller ID (proxies Dograh `POST .../phone-numbers/{phone_number_id}/set-default-caller`)

**Logic:**

- Proxies Dograh `organizations/telephony-configs` and `organizations/telephony-providers/metadata` APIs with org scoping
- Maps configs and numbers to organizations in local DB
- Sensitive credentials (Plivo auth tokens) masked in responses by Dograh's API (GET responses redact secrets)

**Verification:** Can create Plivo config, add phone number, set as default.

---

## Phase 5 — Analytics & Billing

### 12 Analytics API

Server-side analytics aggregation for dashboard charts.

**Endpoints:**

- `GET /api/v1/analytics/overview` — KPI cards (total calls, minutes, success rate, etc.)
- `GET /api/v1/analytics/calls-over-time` — Time series data for line chart
- `GET /api/v1/analytics/disposition-breakdown` — Call outcomes breakdown
- `GET /api/v1/analytics/agent-performance` — Per-agent metrics
- `GET /api/v1/analytics/campaign-performance` — Per-campaign metrics

**Logic:**

- Queries combination of local DB + Dograh usage API + PostHog
- All scoped to current organization
- Supports date range filtering
- Caches results in Redis (5-minute TTL)

**Verification:** Dashboard renders real charts with data from API.

---

### 13 Billing Engine & Razorpay

Usage tracking + billing + payment processing.

**Endpoints:**

- `GET /api/v1/billing/usage` — Current period usage summary
- `GET /api/v1/billing/plan` — Current plan details and limits
- `POST /api/v1/billing/orders` — Create Razorpay payment order
- `POST /api/v1/billing/verify` — Verify payment after Razorpay callback
- `GET /api/v1/billing/invoices` — Invoice history
- `POST /api/v1/webhooks/razorpay` — Razorpay webhook for payment confirmations

**Logic:**

- Usage aggregation from call_runs: total_minutes, total_calls, total_cost
- Plan limits checked before campaign start and call trigger
- Razorpay order created with org context
- Payment verified via webhook signature validation
- Invoice generated after successful payment

**Verification:** Can see usage, create payment order, complete payment flow.

---

### 14 Appointments

Track appointments extracted from AI call gathered_context.

**Endpoints:**

- `GET /api/v1/appointments` — List appointments for current org
- `GET /api/v1/appointments/{id}` — Get appointment details
- `PATCH /api/v1/appointments/{id}` — Update appointment status (confirmed/cancelled)

**Logic:**

- Appointments auto-extracted from Dograh webhook `gathered_context`
- When webhook contains appointment-related fields → create appointment record
- Linked to the call run that generated it

**Verification:** AI call gathers appointment → appears in appointments list.

---

## Phase 6 — Settings & Admin

### 15 Settings & API Keys

Organization settings management + API key provisioning.

**Endpoints:**

- `GET /api/v1/settings/organization` — Get org settings
- `PATCH /api/v1/settings/organization` — Update org settings
- `GET /api/v1/settings/profile` — Get user profile
- `PATCH /api/v1/settings/profile` — Update user profile
- `POST /api/v1/settings/api-keys` — Create org API key
- `GET /api/v1/settings/api-keys` — List org API keys
- `DELETE /api/v1/settings/api-keys/{id}` — Revoke API key

**Verification:** Can update org settings, generate API key, use key to authenticate.

---

### 16 Admin Endpoints

Platform admin endpoints for cross-org management.

**Endpoints:**

- `GET /api/v1/admin/organizations` — List all organizations
- `GET /api/v1/admin/logs` — System-wide logs
- `GET /api/v1/admin/audit` — Full audit trail
- `GET /api/v1/admin/usage` — Platform-wide usage stats

**Logic:**

- Only accessible to platform admin role
- Cross-organization visibility
- Audit trail tracks: who did what, when, which org

**Verification:** Admin can see all orgs, view system logs, audit trail.

---

### 17 Frontend Integration

Connect existing React dashboard to real backend APIs.

**Logic:**

- Remove `DEMO_MODE` flag and all mock data utilities
- Update `AuthContext` to use real backend `/auth/*` endpoints
- Replace all `apiGet`/`apiPost` calls to point to real backend
- WebSocket connection for live calls page
- Razorpay checkout integration in billing page
- PostHog browser client initialization

**Verification:** Full end-to-end flow: login → create campaign → trigger calls → see live updates → view analytics.

---

## Feature Count

| Phase | Features |
|---|---|
| Phase 1 — Foundation & Auth | 4 |
| Phase 2 — Dograh Integration Core | 3 |
| Phase 3 — Campaigns & Calls | 3 |
| Phase 4 — Phone Numbers & Telephony | 1 |
| Phase 5 — Analytics & Billing | 3 |
| Phase 6 — Settings & Admin | 3 |
| **Total** | **17** |
