# Architecture

## Stack

| Layer | Tool | Purpose |
|---|---|---|
| Frontend Framework | React 18 + Vite | Single-page application |
| Styling | Tailwind CSS 3.4 + shadcn/ui | UI components and design system |
| Backend Framework | FastAPI (Python 3.12+) | API server, business logic, RBAC |
| Auth + DB + Storage | InsForge | Authentication, PostgreSQL, file storage |
| Voice Orchestration | Dograh (self-hosted) | Call orchestration, STT/TTS, LLM conversation |
| Telephony | Plivo (via Dograh) | Phone numbers, outbound/inbound calls |
| Task Queue | Celery + Redis | Background jobs, webhook processing, usage sync |
| Caching / Pub-Sub | Redis (AWS) | WebSocket pub/sub, response caching |
| Billing | Razorpay | Subscription plans, usage billing |
| Analytics | PostHog (server-side) | Event tracking, usage dashboards |
| Language | TypeScript (frontend), Python (backend) | Throughout |

---

## Deployment Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                        DigitalOcean VPS                         │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │   Nginx      │    │   FastAPI    │    │   Dograh         │   │
│  │   (reverse   │───▶│   (Uvicorn)  │───▶│   (self-hosted)  │   │
│  │    proxy)    │    │   :8000      │    │   :3000          │   │
│  └──────────────┘    └──────────────┘    └──────────────────┘   │
│         │                   │                                   │
│         │            ┌──────────────┐                            │
│         │            │   Celery     │                            │
│         │            │   Workers    │                            │
│         │            └──────────────┘                            │
└─────────┼───────────────────┼───────────────────────────────────┘
          │                   │
          ▼                   ▼
   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
   │  Frontend   │    │  InsForge   │    │  Redis      │
   │  (CDN/S3)   │    │  (BaaS)    │    │  (AWS)      │
   └─────────────┘    └─────────────┘    └─────────────┘

Public URLs:
  - Frontend:  app.neuvonsoftware.com
  - Backend:   api.neuvonsoftware.com
  - Dograh:    dograh.neuvonsoftware.com (internal only)
```

---

## Folder Structure

```
/
├── AGENTS.md
├── context/
│   ├── project-overview.md
│   ├── architecture.md          ← This file
│   ├── code-standards.md
│   ├── library-docs.md
│   ├── build-plan.md
│   └── progress-tracker.md
├── src/                         ← React frontend (Vite)
│   ├── App.tsx
│   ├── main.tsx
│   ├── index.css
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Register.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Campaigns.tsx
│   │   ├── CampaignDetails.tsx
│   │   ├── LiveCalls.tsx
│   │   ├── CallHistory.tsx
│   │   ├── CallDetails.tsx
│   │   ├── Analytics.tsx
│   │   ├── Appointments.tsx
│   │   ├── PhoneNumbers.tsx
│   │   ├── Settings.tsx
│   │   └── admin/
│   │       ├── Pathways.tsx
│   │       ├── Personas.tsx
│   │       └── AuditLog.tsx
│   ├── components/
│   │   ├── ui/                  ← shadcn/ui primitives
│   │   ├── layout/
│   │   ├── dashboard/
│   │   ├── campaigns/
│   │   ├── calls/
│   │   └── shared/
│   ├── lib/
│   │   ├── api-client.ts        ← Axios/fetch wrapper for backend API
│   │   ├── insforge-client.ts   ← InsForge browser client (auth only)
│   │   └── utils.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useWebSocket.ts
│   │   └── useApi.ts
│   ├── stores/                  ← Zustand stores
│   │   ├── authStore.ts
│   │   └── liveCallStore.ts
│   └── types/
│       └── index.ts
└── backend/                     ← FastAPI backend
    ├── main.py                  ← FastAPI app entry point
    ├── requirements.txt
    ├── alembic.ini
    ├── app/
    │   ├── __init__.py
    │   ├── core/
    │   │   ├── config.py        ← Pydantic Settings (env vars)
    │   │   ├── security.py      ← JWT validation, RBAC decorators
    │   │   ├── dependencies.py  ← FastAPI dependency injection
    │   │   ├── celery_app.py    ← Celery configuration
    │   │   └── middleware.py    ← CORS, logging, rate limiting
    │   ├── models/              ← SQLModel / Pydantic models
    │   │   ├── organization.py
    │   │   ├── user.py
    │   │   ├── agent_mapping.py
    │   │   ├── call_run.py
    │   │   ├── campaign.py
    │   │   ├── telephony.py
    │   │   ├── billing.py
    │   │   └── appointment.py
    │   ├── schemas/             ← Pydantic request/response schemas
    │   │   ├── auth.py
    │   │   ├── agent.py
    │   │   ├── call.py
    │   │   ├── campaign.py
    │   │   ├── telephony.py
    │   │   ├── billing.py
    │   │   └── analytics.py
    │   ├── services/            ← Business logic layer
    │   │   ├── auth_service.py
    │   │   ├── org_service.py
    │   │   ├── agent_service.py
    │   │   ├── call_service.py
    │   │   ├── campaign_service.py
    │   │   ├── telephony_service.py
    │   │   ├── billing_service.py
    │   │   ├── analytics_service.py
    │   │   └── usage_service.py
    │   ├── integrations/        ← External API clients
    │   │   ├── dograh_client.py
    │   │   ├── insforge_client.py
    │   │   ├── razorpay_client.py
    │   │   └── posthog_client.py
    │   ├── routes/              ← FastAPI routers
    │   │   ├── auth.py
    │   │   ├── organizations.py
    │   │   ├── agents.py
    │   │   ├── calls.py
    │   │   ├── campaigns.py
    │   │   ├── telephony.py
    │   │   ├── billing.py
    │   │   ├── analytics.py
    │   │   ├── webhooks.py
    │   │   └── websocket.py
    │   ├── tasks/               ← Celery background tasks
    │   │   ├── usage_tasks.py
    │   │   ├── webhook_tasks.py
    │   │   └── billing_tasks.py
    │   └── utils/
    │       ├── logging.py       ← structlog configuration
    │       └── pagination.py
    └── migrations/              ← Alembic migrations
        └── versions/
```

---

## System Boundaries

| Layer | Owns | Does NOT own |
|---|---|---|
| `src/pages/` | Page routing, layout composition | No business logic, no direct API calls to Dograh |
| `src/components/` | UI rendering, user interactions | No data fetching, no state mutations |
| `src/lib/api-client.ts` | HTTP calls to backend API only | No direct Dograh/InsForge calls (except auth) |
| `src/hooks/` | Data fetching, WebSocket connections | No UI rendering |
| `backend/app/routes/` | Request parsing, auth checks, response formatting | No business logic, no direct Dograh calls |
| `backend/app/services/` | All business logic, org-scoping, data enrichment | No HTTP request/response handling |
| `backend/app/integrations/` | External API communication (Dograh, Razorpay, etc.) | No business logic, no database writes |
| `backend/app/models/` | Database schema, ORM queries | No API or business logic |
| `backend/app/tasks/` | Background processing (usage sync, billing) | No HTTP handling |

---

## Multi-Tenancy Model

### Organization Hierarchy

```
Platform (Neuvon)
├── Organization A (direct client)
│   └── Users (owner, admin, member)
├── Organization B (reseller)
│   └── Users (owner, admin, member)
└── Organization C (direct client)
    └── Users (owner, admin, member)
```

Flat structure — every tenant is a top-level organization. There are no sub-organizations. Resellers and direct clients are differentiated by `org_type` but share the same hierarchy level.

### RBAC Roles

| Role | Scope | Permissions |
|---|---|---|
| `platform_admin` | Global | Everything — manage all orgs, agents, billing |
| `owner` | Organization | Full org control — settings, billing, members, agents |
| `admin` | Organization | Manage members, agents, campaigns — no billing |
| `member` | Organization | Trigger calls, view campaigns, view history — no management |

### Data Isolation

Every database table that holds tenant data includes an `organization_id` column. All queries are scoped by this column — enforced at the service layer via dependency injection:

```python
# Every service method receives org_id from the auth dependency
async def list_campaigns(self, org_id: str) -> list[CampaignResponse]:
    campaigns = await self.db.query(Campaign).filter(
        Campaign.organization_id == org_id
    ).all()
    return campaigns
```

InsForge Row-Level Security (RLS) provides a second layer of isolation at the database level.

---

## Data Flow Patterns

### 1. Frontend → Backend → Dograh (Proxy Pattern)

All Dograh API calls are proxied through the backend. The frontend never talks to Dograh directly.

```
React Frontend                FastAPI Backend               Dograh
     │                             │                          │
     │  POST /api/v1/calls/trigger │                          │
     │────────────────────────────▶│                          │
     │                             │  Validate auth + RBAC    │
     │                             │  Validate phone (E.164)  │
     │                             │  Check usage quota        │
     │                             │                          │
     │                             │  POST /public/agent/     │
     │                             │  workflow/{uuid}         │
     │                             │─────────────────────────▶│
     │                             │                          │
     │                             │  { workflow_run_id: 123 }│
     │                             │◀─────────────────────────│
     │                             │                          │
     │                             │  Create local call_run   │
     │                             │  Fire PostHog event      │
     │                             │                          │
     │  { run_id: 123, status }    │                          │
     │◀────────────────────────────│                          │
```

### 2. Dograh Webhook → Backend → DB + WebSocket

Dograh sends post-call results to our webhook endpoint. We sync data locally and push real-time updates.

```
Dograh                    FastAPI Backend              Redis          Frontend
  │                             │                       │               │
  │  POST /api/v1/webhooks/     │                       │               │
  │  dograh                     │                       │               │
  │────────────────────────────▶│                       │               │
  │                             │                       │               │
  │                             │  Validate webhook     │               │
  │                             │  Update call_run      │               │
  │                             │  Calculate usage      │               │
  │                             │                       │               │
  │                             │  PUBLISH call_update  │               │
  │                             │──────────────────────▶│               │
  │                             │                       │  Push to WS   │
  │                             │                       │──────────────▶│
  │                             │                       │               │
  │                             │  Fire PostHog event   │               │
  │                             │  Queue billing task   │               │
```

### 3. Live Call Monitoring (WebSocket)

Dograh provides a **status callback** webhook (`/api/v1/telephony/status-callback/{workflow_run_id}`) that fires on each call state transition: `initiated → ringing → answered → completed`. Our backend receives these status callbacks, updates the local DB, and broadcasts via Redis pub/sub to connected WebSocket clients.

```
Telephony Provider        Dograh                  FastAPI Backend       Frontend (WS)
     │                      │                          │                     │
     │  Call status change   │                          │                     │
     │─────────────────────▶│                          │                     │
     │                      │  POST status-callback    │                     │
     │                      │─────────────────────────▶│                     │
     │                      │                          │                     │
     │                      │                          │  Update call_run    │
     │                      │                          │  PUBLISH to Redis   │
     │                      │                          │────────────────────▶│
     │                      │                          │  { type: "status",  │
     │                      │                          │    run_id: 123,     │
     │                      │                          │    status: "answered"│
     │                      │                          │    duration: 45 }   │
```

**Call status values from Dograh's telephony webhook:**

| Status | Description |
|---|---|
| `initiated` | Call request received by telephony provider |
| `ringing` | Call is ringing on the recipient's phone |
| `answered` | Call was answered, agent pipeline starts |
| `completed` | Call ended normally |
| `busy` | Line was busy |
| `no-answer` | Call was not answered |
| `failed` | Call failed (network/provider error) |

### 4. Authentication Flow (InsForge Auth)

```
React Frontend                InsForge Auth              FastAPI Backend
     │                             │                          │
     │  insforge.auth.signIn()     │                          │
     │────────────────────────────▶│                          │
     │                             │                          │
     │  JWT access_token           │                          │
     │◀────────────────────────────│                          │
     │                             │                          │
     │  GET /api/v1/agents         │                          │
     │  Authorization: Bearer JWT  │                          │
     │─────────────────────────────────────────────────────▶│
     │                             │                          │
     │                             │  Verify JWT (InsForge)   │
     │                             │  Extract user_id + org   │
     │                             │  Check RBAC role         │
     │                             │                          │
     │  { agents: [...] }          │                          │
     │◀─────────────────────────────────────────────────────│
```

The frontend handles auth via InsForge's client SDK. The backend validates InsForge JWTs on every request, extracting `user_id` and `organization_id` for scoping.

---

## Database Schema (InsForge PostgreSQL)

### `organizations`

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| name | text | Display name |
| slug | text | URL-friendly identifier, unique |
| org_type | text | `direct` / `reseller` |
| white_label | jsonb | `{ display_name, logo_url, primary_color, favicon_url }` |
| dograh_api_key | text | Encrypted — org-specific Dograh API key |
| billing_plan | text | `free` / `starter` / `growth` / `enterprise` |
| usage_quota | jsonb | `{ monthly_minutes: 1000, max_agents: 5, max_campaigns: 10 }` |
| is_active | boolean | Soft disable toggle |
| created_at | timestamptz | |
| updated_at | timestamptz | |

### `users`

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK — references InsForge auth.users |
| organization_id | uuid | FK → organizations |
| email | text | From InsForge auth |
| full_name | text | |
| role | text | `platform_admin` / `owner` / `admin` / `member` |
| is_active | boolean | |
| last_login_at | timestamptz | |
| created_at | timestamptz | |

### `dograh_agent_mappings`

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| organization_id | uuid | FK → organizations |
| dograh_workflow_id | integer | Dograh's internal workflow ID |
| dograh_workflow_uuid | text | Stable agent UUID for API triggers |
| agent_name | text | Display name (synced from Dograh) |
| agent_status | text | `active` / `archived` |
| created_at | timestamptz | |
| updated_at | timestamptz | |

### `call_runs`

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| organization_id | uuid | FK → organizations |
| dograh_run_id | integer | Dograh's workflow_run_id |
| dograh_workflow_id | integer | FK reference to agent mapping |
| campaign_id | uuid | FK → campaigns (null for single calls) |
| call_type | text | `outbound` / `inbound` |
| status | text | `initiated` / `ringing` / `answered` / `completed` / `failed` / `busy` / `no-answer` |
| phone_number | text | E.164 format — called number |
| caller_number | text | E.164 format — from number |
| duration_seconds | integer | Call duration |
| initial_context | jsonb | Data passed at trigger time |
| gathered_context | jsonb | Data extracted by AI during call |
| transcript_url | text | Dograh transcript URL |
| recording_url | text | Dograh recording URL |
| public_access_token | text | For time-limited public download URLs |
| cost_info | jsonb | Dograh cost breakdown |
| annotations | jsonb | QA analysis results |
| disposition | text | Disposition code (if configured) |
| started_at | timestamptz | |
| completed_at | timestamptz | |
| created_at | timestamptz | |

### `campaigns`

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| organization_id | uuid | FK → organizations |
| dograh_campaign_id | integer | Dograh's campaign ID |
| dograh_workflow_id | integer | Linked agent |
| name | text | Campaign display name |
| status | text | `draft` / `running` / `paused` / `completed` / `failed` |
| total_contacts | integer | Total contacts in CSV |
| contacts_processed | integer | Contacts dialed so far |
| concurrency | integer | Max simultaneous calls |
| retry_config | jsonb | `{ max_attempts, retry_interval_minutes }` |
| schedule_config | jsonb | `{ timezone, time_slots: [...] }` |
| contact_list_id | text | Dograh contact list reference |
| started_at | timestamptz | |
| completed_at | timestamptz | |
| created_at | timestamptz | |

### `telephony_configs`

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| organization_id | uuid | FK → organizations |
| dograh_config_id | integer | Dograh's telephony config ID |
| provider | text | `plivo` / `twilio` / `vonage` / `telnyx` |
| label | text | Friendly name |
| is_default_outbound | boolean | Default for this org's outbound calls |
| created_at | timestamptz | |

### `phone_numbers`

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| organization_id | uuid | FK → organizations |
| telephony_config_id | uuid | FK → telephony_configs |
| dograh_phone_id | integer | Dograh's phone number ID |
| number | text | E.164 format |
| label | text | Friendly name |
| is_default_caller | boolean | Default caller ID for this config |
| created_at | timestamptz | |

### `billing_records`

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| organization_id | uuid | FK → organizations |
| period_start | date | Billing period start |
| period_end | date | Billing period end |
| total_minutes | decimal | Total call minutes consumed |
| total_calls | integer | Total calls made |
| total_cost_usd | decimal | Cost calculated from usage |
| razorpay_invoice_id | text | Razorpay invoice reference |
| status | text | `pending` / `paid` / `overdue` |
| created_at | timestamptz | |

### `appointments`

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| organization_id | uuid | FK → organizations |
| call_run_id | uuid | FK → call_runs (the call that booked it) |
| contact_name | text | From gathered_context |
| contact_phone | text | E.164 |
| appointment_date | timestamptz | Scheduled date/time |
| notes | text | AI-extracted notes |
| status | text | `scheduled` / `confirmed` / `cancelled` / `completed` |
| created_at | timestamptz | |

### `audit_log`

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| organization_id | uuid | FK → organizations |
| user_id | uuid | FK → users |
| action | text | `call_triggered` / `campaign_started` / `member_invited` / etc. |
| resource_type | text | `call` / `campaign` / `agent` / `member` / `telephony` |
| resource_id | text | ID of affected resource |
| metadata | jsonb | Action-specific details |
| ip_address | text | Request IP |
| created_at | timestamptz | |

---

## InsForge Storage

| Bucket | Path | Contents |
|---|---|---|
| `call-recordings` | `{org_id}/{run_id}/recording.wav` | Cached call recordings |
| `campaign-csvs` | `{org_id}/{campaign_id}/contacts.csv` | Uploaded contact CSVs (backup) |
| `org-assets` | `{org_id}/logo.png` | White-label logos and branding assets |

Access: Authenticated users only, scoped to their organization's path via RLS policies.

---

## Authentication

- **Provider:** InsForge Auth
- **Methods:** Email/password (primary), Google OAuth (future)
- **Token flow:** Frontend gets JWT from InsForge → sends as `Authorization: Bearer <token>` to backend → backend verifies JWT with InsForge's JWKS endpoint
- **User metadata:** `organization_id` and `role` stored in InsForge `auth.users.user_metadata`
- **Protected routes (frontend):** Everything except `/login` and `/register`
- **Backend auth dependency:** Every route uses `get_current_user()` dependency that returns `user_id`, `org_id`, and `role`

---

## Dograh Integration Pattern

```python
# All Dograh communication goes through DograhClient
# Never call Dograh directly from services or routes

class DograhClient:
    """Async HTTP client for Dograh API."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                f"{self.base_url}/api/v1{path}",
                headers={"X-API-Key": self.api_key},
                **kwargs,
            )
            response.raise_for_status()
            return response.json()

    # Agent methods
    async def list_agents(self) -> dict:
        return await self._request("GET", "/workflow/fetch")

    async def trigger_call(self, workflow_uuid: str, phone: str,
                           context: dict, telephony_config_id: int = None) -> dict:
        body = {"phone_number": phone, "initial_context": context}
        if telephony_config_id:
            body["telephony_configuration_id"] = telephony_config_id
        return await self._request(
            "POST", f"/public/agent/workflow/{workflow_uuid}", json=body
        )

    async def get_run(self, workflow_id: int, run_id: int) -> dict:
        return await self._request(
            "GET", f"/workflow/{workflow_id}/runs/{run_id}"
        )
```

---

## WebSocket Architecture

```python
# Backend WebSocket endpoint
@router.websocket("/api/v1/ws/live-calls")
async def live_calls_ws(websocket: WebSocket):
    # 1. Authenticate via JWT query param
    # 2. Extract org_id from token
    # 3. Subscribe to Redis channel: f"org:{org_id}:calls"
    # 4. Forward messages to client
    # 5. Heartbeat every 30s

# Message format pushed to clients:
{
    "type": "call_status",
    "data": {
        "run_id": 123,
        "status": "answered",        # From Dograh status callback
        "phone_number": "+14155550100",
        "agent_name": "Appointment Reminder",
        "duration_seconds": 45
    }
}
```

Redis pub/sub channel per organization ensures multi-tenant isolation for real-time events.

---

## Environment Variables

| Variable | Used By |
|---|---|
| `INSFORGE_URL` | InsForge client (auth, DB, storage) |
| `INSFORGE_ANON_KEY` | InsForge client (public operations) |
| `INSFORGE_SERVICE_KEY` | InsForge server (admin operations) |
| `DOGRAH_BASE_URL` | DograhClient (`https://dograh.neuvonsoftware.com`) |
| `DOGRAH_API_KEY` | DograhClient authentication |
| `SECRET_KEY` | JWT signing fallback, CSRF |
| `RAZORPAY_KEY_ID` | Razorpay billing integration |
| `RAZORPAY_KEY_SECRET` | Razorpay billing integration |
| `POSTHOG_API_KEY` | PostHog server-side analytics |
| `POSTHOG_HOST` | PostHog instance URL |
| `REDIS_URL` | Celery broker + pub/sub + caching |
| `CORS_ORIGINS` | Allowed frontend origins |
| `WEBHOOK_SECRET` | Dograh webhook signature validation |

---

## Invariants

Rules that must never be violated:

1. **Frontend never talks to Dograh.** All Dograh API calls go through the FastAPI backend.
2. **Every database query is org-scoped.** No query runs without `organization_id` filter — enforced by service layer dependencies.
3. **Routes contain no business logic.** Routes parse requests, call services, format responses. All logic lives in `services/`.
4. **Services never import from routes.** Services are framework-agnostic — they don't know about FastAPI request/response objects.
5. **All Dograh communication goes through `DograhClient`.** Services call `DograhClient` methods, never raw HTTPX.
6. **RORO pattern everywhere.** Every service method takes a Pydantic `*Create` / `*Update` schema and returns a `*Response` schema.
7. **Dual storage for all Dograh data.** Every agent, run, campaign, and telephony config that exists in Dograh also has a local record in InsForge DB (for fast queries, org-scoping, and billing enrichment).
8. **Webhook handlers are idempotent.** Processing the same webhook payload twice must produce the same result — use `dograh_run_id` as dedup key.
9. **All secrets come from environment variables.** No hardcoded API keys, URLs, or credentials anywhere in code.
10. **Celery tasks handle all background work.** Usage aggregation, billing calculations, and webhook-triggered sync always run as Celery tasks — never blocking the request cycle.
11. **Audit everything.** All state-changing operations (call trigger, campaign start, member invite, role change) create an `audit_log` entry.
12. **Flat org hierarchy.** Every tenant is a top-level organization. No sub-organizations or nesting — resellers and direct clients are differentiated by `org_type` only.
