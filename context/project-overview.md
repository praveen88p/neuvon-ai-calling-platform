# Project Overview

## About the Project

Neuvon is a white-label AI calling platform built by Neuvon Software. The platform allows businesses and resellers to create AI voice agents, run outbound calling campaigns, monitor live calls in real-time and track detailed analytics - all through a branded dashboard.

The system is multi-tenant from the ground up. Each organization (direct client or reseller) operates in complete data isolation with their own agents, campaigns, phone numbers, and billing.

The voice engine is powered by a self-hosted Dograh instance at `dograh.neuvonsoftware.com`. The Neuvon backend (FastAPI) acts as the secure middleware layer between the React frontend and Dograh — handling authentication, RBAC, billing, usage tracking, and all business logic. Dograh handles the actual call orchestration, STT/TTS, and LLM conversation flow.

Telephony is handled through Plivo, configured inside Dograh via its telephony configurations API.

The entire process is tracked on a dashboard with PostHog-powered analytics and a recent activity feed.
---

## The Problem It Solves

Businesses need AI calling agents but lack the infrastructure to build, deploy, and manage them. Existing solutions are either too expensive, not customizable, or don't support white-labeling for agencies/resellers.

Neuvon eliminates this by providing:

- A complete calling platform that resellers can brand as their own
- Self-hosted voice infrastructure (Dograh) that keeps costs predictable
- Multi-tenant isolation so each client's data, agents, and campaigns are completely separate
- Usage-based billing that tracks every second of call time per organization

---

## Pages

### Client Pages (All Organizations)

```
/login              → Authentication (email/password)
/register           → New account registration
/                   → Dashboard — KPIs, recent activity, usage overview
/campaigns          → Campaign list — all outbound campaigns
/campaigns/:id      → Campaign details — progress, contact list, run results
/upload             → Upload Leads — CSV upload for campaign contacts
/live-calls         → Live Calls — real-time active call monitoring via WebSocket
/call-history       → Call History — paginated call log with filters
/call-details/:id   → Call Details — transcript, recording, gathered context, cost
/analytics          → Analytics — charts, trends, usage breakdown
/appointments       → Appointments — booked appointments from AI calls
/settings           → Organization settings, profile, API keys
/phone-numbers      → Phone number management per organization
```

### Admin Pages (Platform Admin Only)

```
/admin/pathways     → Agent workflow/pathway management
/admin/personas     → AI persona templates
/admin/knowledge    → Knowledge base management
/admin/logs         → System logs
/admin/audit        → Audit trail — all user actions across organizations
```

---

## Navigation

Left sidebar. Collapsible. Two sections:

**Main:** Dashboard, Campaigns, Upload Leads, Live Calls, Call History, Analytics, Appointments, Settings, Phone Numbers

**Footer:** Organization name, user email, sidebar toggle, logout button

---

## Core User Flows

### Authentication

- User registers with email/password via InsForge Auth
- User logs in → redirect to Dashboard
- JWT token stored, validated on every protected route
- Organization context loaded from user profile

### Agent Management (via Dograh)

- Platform admin creates AI agents (workflows) in Dograh
- Agents are assigned to organizations via the Neuvon backend
- Each agent has a workflow definition (conversation flow, prompts, LLM config, voice)
- Agents can be created from templates or explicit definitions via the Dograh API

### Campaign Lifecycle

1. User creates a campaign — selects agent, phone number, scheduling rules
2. User uploads contacts CSV (via Dograh's `/campaign/upload` endpoint, multipart form data)
3. User starts the campaign — Dograh begins dialing contacts
4. Campaign can be paused/resumed
5. Real-time progress tracked via polling or WebSocket
6. Each contact gets a "run" — one call execution with transcript, recording, cost
7. Campaign completes when all contacts are processed

### Live Call Monitoring

- WebSocket connection to backend for real-time call status
- Shows active calls across all agents for the organization
- Call status updates: pending → in_progress → completed/failed
- Can see caller/called numbers, duration, agent name

### Call History & Details

- Paginated list of all completed runs for the organization
- Filterable by agent, campaign, date range, duration, disposition
- Call details page shows: full transcript, recording playback, gathered context, cost breakdown, initial context

### Analytics Dashboard

- Total calls, total minutes, average call duration, success rate
- Calls over time (line chart)
- Call disposition breakdown (bar chart)
- Agent performance comparison
- Campaign performance metrics
- All scoped to the current organization

### Phone Number Management

- Organizations manage their phone numbers
- Numbers are registered in Dograh via telephony configurations API
- Each number can be assigned as default outbound caller
- Numbers can be bound to inbound workflows for receiving calls

### Billing & Usage

- Usage tracked per organization: call minutes, number of calls, Dograh token usage
- Razorpay integration for payment processing
- Flexible pricing models per organization (per-minute tiers, flat fees, custom)
- Usage dashboard shows current period consumption vs plan limits

---

## Data Architecture

### Source of Truth Split

| Data Domain | Source of Truth | Why |
|---|---|---|
| Users, orgs, RBAC | InsForge (PostgreSQL) | Auth and multi-tenancy live here |
| Agent definitions | Dograh | Workflow schema owned by Dograh |
| Call runs & transcripts | Dograh + InsForge | Dograh produces them; backend syncs and enriches |
| Campaigns | Dograh + InsForge | Created in Dograh; metadata/billing tracked in InsForge |
| Billing & usage | InsForge | Business logic owned by our backend |
| Phone numbers | Dograh + InsForge | Configured in Dograh; mapped to orgs in InsForge |
| Analytics events | PostHog | Event-level tracking for dashboard charts |

### Multi-Tenancy Model

- Every database row is scoped to an `organization_id`
- Row Level Security (RLS) enforced at the InsForge/PostgreSQL level
- Users belong to exactly one organization
- Organizations have roles: `owner`, `admin`, `member`
- Resellers and direct clients are differentiated by `org_type` — no sub-organizations

---

## Features In Scope

- Multi-tenant authentication with RBAC (owner/admin/member)
- Organization management with white-label branding support
- Reseller model — resellers operate as independent organizations with white-label branding
- Agent management via Dograh API (create, update, list, archive)
- Campaign creation, CSV upload, start/pause/resume, progress tracking
- Single outbound call triggering via Dograh API
- Live call monitoring via WebSocket
- Call history with filters, pagination, search
- Call detail view with transcript, recording, gathered context
- Analytics dashboard with charts (PostHog-powered)
- Phone number management via Dograh telephony configs API
- Appointment tracking from AI-gathered context
- Usage tracking per organization (minutes, calls, tokens)
- Billing engine with Razorpay integration
- PostHog event tracking for all key actions
- Webhook receiver for Dograh post-call data sync
- Settings page — organization profile, API key management

---

## Features Out of Scope (v1)

- Agent workflow visual builder in the dashboard (use Dograh UI directly)
- SMS/WhatsApp channels
- Inbound call routing configuration from the dashboard
- CRM integration (Salesforce, HubSpot, etc.)
- Mobile app
- Email notifications for call results
- Custom domain per organization (future)
- Self-service reseller signup
- A/B testing of agent prompts
- Call recording transcription by our backend (Dograh handles this)

---

## PostHog Events

```python
campaign_started       # { org_id, campaign_id, agent_id, contact_count }
campaign_completed     # { org_id, campaign_id, total_calls, total_minutes }
call_triggered         # { org_id, agent_id, call_type: "outbound" | "inbound" }
call_completed         # { org_id, run_id, duration_seconds, disposition }
leads_uploaded         # { org_id, campaign_id, lead_count }
user_logged_in         # { user_id, org_id }
agent_created          # { org_id, agent_id, creation_method: "template" | "definition" }
phone_number_added     # { org_id, provider, number }
```

These events power the analytics dashboard charts and usage reports. Do not add events without updating this list first.

---

## Target User

**Direct clients:** Small-to-medium businesses that need AI calling agents for lead qualification, appointment booking, follow-ups, and outbound sales — but don't have the technical team to build their own.

**Resellers/Agencies:** AI automation agencies that want to offer AI calling as a white-labeled service to their own clients, each operating as an independent organization with branded dashboards.

**Platform admin:** Neuvon Software team managing the infrastructure, agent templates, and global platform settings.

---

## Success Criteria

- New organization can be onboarded and making their first call within 30 minutes
- Campaign with 100 contacts completes without manual intervention
- Live calls page shows real-time status updates within 2 seconds
- Call history loads paginated results in under 500ms
- Analytics dashboard renders meaningful charts from real PostHog data
- Billing accurately tracks usage per organization to the second
- Platform admin can onboard a new reseller organization within 10 minutes
- All data is fully isolated between organizations — zero cross-tenant data leakage
- Backend handles 50+ concurrent calls without degradation
- Dograh webhook data syncs to InsForge within 5 seconds of call completion
