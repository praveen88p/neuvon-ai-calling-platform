# Library Docs

Project-specific usage patterns for every third party library in this project. This file only covers how we use each library in this specific project — rules, patterns, and constraints specific to Neuvon.

Read the relevant section before implementing any feature that touches these libraries.

---

## Before Using Any Library

Before implementing any feature that uses a third party library:

1. **Check AGENTS.md** at the project root — it lists every skill installed for this project and how to use them. Skills contain up-to-date API documentation, usage patterns, and best practices specific to this codebase.

2. **Check if an MCP server is configured** for that library. Some tools have MCP servers that give the AI agent direct access to documentation, logs, and debugging tools. If an MCP server is available — use it before falling back to general knowledge.

3. **Read this file** for project-specific patterns that override general library knowledge.

The order of authority is:

```
MCP server (real-time docs) → Skills via AGENTS.md → This file (project rules) → General training knowledge
```

Never rely on general training knowledge alone for library APIs — they change frequently and training data may be outdated.

---

## InsForge

**Check first:** Check AGENTS.md for installed InsForge skills. If an InsForge MCP server is configured — use the `fetch-docs` or `fetch-sdk-docs` MCP tool to get the latest API patterns.

### Server-Side Client (Backend)

InsForge is used as the primary database and auth provider. The backend communicates with InsForge using the service key for admin operations and the anon key for user-scoped operations.

```python
# app/core/insforge.py

from insforge import create_client, Client

from app.core.config import get_settings


def get_insforge_client() -> Client:
    """InsForge client for user-scoped operations."""
    settings = get_settings()
    return create_client(
        base_url=settings.INSFORGE_URL,
        anon_key=settings.INSFORGE_ANON_KEY,
    )


def get_insforge_admin() -> Client:
    """InsForge client with service key for admin operations."""
    settings = get_settings()
    return create_client(
        base_url=settings.INSFORGE_URL,
        anon_key=settings.INSFORGE_SERVICE_KEY,
    )
```

### Database Operations

```python
# Read with organization scope
response = insforge.table("campaigns") \
    .select("*") \
    .eq("organization_id", str(org_id)) \
    .order("created_at", desc=True) \
    .execute()

# Insert
response = insforge.table("campaigns") \
    .insert({
        "organization_id": str(org_id),
        "name": campaign_name,
        "agent_id": agent_id,
        "status": "draft",
    }) \
    .execute()

# Update
response = insforge.table("campaigns") \
    .update({"status": "running"}) \
    .eq("id", str(campaign_id)) \
    .eq("organization_id", str(org_id)) \
    .execute()
```

**Rules:**

- Always scope queries to `organization_id` — never query without org filter
- Always handle the response — check for errors before using data
- Use `.single()` when expecting exactly one row
- Use the admin client only for cross-org operations (billing, platform admin)

### Auth

```python
# Verify JWT token from frontend
response = insforge.auth.get_user(jwt_token)
user = response.user

# Sign up new user
response = insforge.auth.sign_up({
    "email": email,
    "password": password,
    "options": {
        "data": {
            "organization_id": str(org_id),
            "role": "member",
        }
    }
})
```

### Storage

```python
# Upload file
response = insforge.storage \
    .from_("call-recordings") \
    .upload(
        path=f"{org_id}/{run_id}/recording.wav",
        file=file_buffer,
        file_options={"content-type": "audio/wav", "upsert": True},
    )

# Get public URL
url = insforge.storage \
    .from_("call-recordings") \
    .get_public_url(f"{org_id}/{run_id}/recording.wav")
```

---

## HTTPX

**Used for:** All external HTTP communication — Dograh API, Razorpay API, webhook delivery.

### Async Client Pattern

```python
import httpx


async def make_request(method: str, url: str, **kwargs) -> dict:
    """Make an async HTTP request with timeout and error handling."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
```

### Dograh API Calls

```python
async with httpx.AsyncClient(
    base_url=settings.DOGRAH_BASE_URL,
    headers={"X-API-Key": settings.DOGRAH_API_KEY},
    timeout=30.0,
) as client:
    # Trigger outbound call
    response = await client.post(
        f"/api/v1/public/agent/workflow/{workflow_uuid}",
        json={
            "phone_number": phone_number,
            "initial_context": {"customer_name": "Jane", "appointment_date": "March 15"},
            "telephony_configuration_id": telephony_config_id,
        },
    )
    result = response.json()
    # result: { "status": "...", "workflow_run_id": 123, "workflow_run_name": "..." }
```

**Rules:**

- Always use async client — never synchronous `httpx.get()`
- Always set a timeout — default 30 seconds
- Always use `response.raise_for_status()` and catch `httpx.HTTPStatusError`
- Prefer `async with httpx.AsyncClient()` context manager — auto-closes connections
- For Dograh: reuse the `DograhClient` wrapper class, never call httpx directly from services

---

## Dograh API

**Check first:** Check AGENTS.md for an installed Dograh skill. The skill contains the full API reference and patterns.

### Authentication

All Dograh API calls require `X-API-Key` header. Keys are organization-scoped.

### Key Endpoints

All paths below are relative to the base URL: `https://your-instance/api/v1`

#### Agents (Workflows)

| Endpoint | Method | Purpose |
|---|---|---|
| `/workflow/create/definition` | POST | Create agent from explicit workflow definition (nodes + edges) |
| `/workflow/create/template` | POST | Create agent from natural language description |
| `/workflow/fetch` | GET | List all agents in the organization |
| `/workflow/fetch/{workflow_id}` | GET | Get single agent with full workflow definition |
| `/workflow/count` | GET | Get agent count broken down by status |
| `/workflow/{workflow_id}` | PUT | Update agent name, definition, or configuration |
| `/workflow/{workflow_id}/status` | PUT | Archive or restore an agent |
| `/workflow/{workflow_id}/validate` | POST | Validate a workflow definition without executing |

#### Agent Runs (scoped to a specific workflow)

| Endpoint | Method | Purpose |
|---|---|---|
| `/workflow/{workflow_id}/runs` | POST | Create a test run (without placing a real call) |
| `/workflow/{workflow_id}/runs` | GET | List all runs for a specific workflow |
| `/workflow/{workflow_id}/runs/{run_id}` | GET | Get run details (transcript, recording, cost, context) |

#### Runs (organization-wide)

| Endpoint | Method | Purpose |
|---|---|---|
| `/public/agent/{uuid}` | POST | Trigger outbound call by API Trigger node UUID |
| `/public/agent/workflow/{workflow_uuid}` | POST | Trigger outbound call by Agent UUID (stable workflow UUID) |
| `/organizations/usage/runs` | GET | Paginated list of all runs with usage and cost data |
| `/public/download/workflow/{token}/{artifact_type}` | GET | Download recording or transcript via time-limited public URL |
| `/telephony/inbound/{workflow_id}` | POST | Inbound call webhook — telephony provider sends call events here |

#### Campaigns

| Endpoint | Method | Purpose |
|---|---|---|
| `/campaign/upload` | POST | Upload contacts CSV (multipart form data) |
| `/campaign/create` | POST | Create a campaign linked to a workflow and contact list |
| `/campaign/fetch` | GET | List all campaigns in the organization |
| `/campaign/fetch/{campaign_id}` | GET | Get a single campaign by ID |
| `/campaign/{campaign_id}` | PUT | Update campaign settings |
| `/campaign/{campaign_id}/start` | POST | Start dialing contacts |
| `/campaign/{campaign_id}/pause` | POST | Pause a running campaign |
| `/campaign/{campaign_id}/resume` | POST | Resume a paused campaign |
| `/campaign/{campaign_id}/progress` | GET | Get current campaign progress stats |
| `/campaign/{campaign_id}/runs` | GET | Get run records for each contact in the campaign |

#### Telephony Configurations

| Endpoint | Method | Purpose |
|---|---|---|
| `/organizations/telephony-providers/metadata` | GET | List supported telephony providers and their required credential fields |
| `/organizations/telephony-configs` | GET | List all telephony configurations |
| `/organizations/telephony-configs` | POST | Create a telephony configuration |
| `/organizations/telephony-configs/{config_id}` | GET | Get a specific configuration |
| `/organizations/telephony-configs/{config_id}` | PUT | Update configuration (rename or rotate credentials) |
| `/organizations/telephony-configs/{config_id}` | DELETE | Delete a configuration |
| `/organizations/telephony-configs/{config_id}/set-default-outbound` | POST | Set as org-wide default for outbound calls |

#### Phone Numbers (nested under telephony configs)

| Endpoint | Method | Purpose |
|---|---|---|
| `/organizations/telephony-configs/{config_id}/phone-numbers` | GET | List phone numbers for a config |
| `/organizations/telephony-configs/{config_id}/phone-numbers` | POST | Add a phone number to a config |
| `/organizations/telephony-configs/{config_id}/phone-numbers/{phone_number_id}` | GET | Get a specific phone number |
| `/organizations/telephony-configs/{config_id}/phone-numbers/{phone_number_id}` | PUT | Update phone number (label, inbound binding, activation) |
| `/organizations/telephony-configs/{config_id}/phone-numbers/{phone_number_id}` | DELETE | Remove a phone number |
| `/organizations/telephony-configs/{config_id}/phone-numbers/{phone_number_id}/set-default-caller` | POST | Set as default outbound caller ID for this config |

#### API Keys

| Endpoint | Method | Purpose |
|---|---|---|
| `/user/api-keys` | POST | Create a new API key |
| `/user/api-keys` | GET | List all API keys |
| `/user/api-keys/{api_key_id}` | DELETE | Archive (deactivate) an API key |
| `/user/api-keys/{api_key_id}/reactivate` | PUT | Reactivate an archived API key |

### Run Status Values

| Status | Description |
|---|---|
| `pending` | Run queued but not yet connected |
| `in_progress` | Run is live |
| `completed` | Run ended normally |
| `failed` | Run failed before or during execution |

### Campaign Status Values

| Status | Description |
|---|---|
| `draft` | Created but not started |
| `running` | Actively dialing contacts |
| `paused` | Temporarily stopped; can be resumed |
| `completed` | All contacts processed |
| `failed` | Campaign encountered a fatal error |

### Trigger Request Body

Both trigger endpoints (`/public/agent/{uuid}` and `/public/agent/workflow/{workflow_uuid}`) accept the same request body:

```python
{
    "phone_number": "+14155550100",           # Required — E.164 format
    "initial_context": {                       # Optional — template variables for agent prompt
        "customer_name": "Jane",
        "appointment_date": "March 15",
        "property_address": "123 Main St"
    },
    "telephony_configuration_id": 5            # Optional — override default telephony config
}
```

Agent prompt can reference `{{customer_name}}`, `{{appointment_date}}`, etc. via double-brace syntax.

### Trigger Response

```python
{
    "status": "initiated",
    "workflow_run_id": 12345,
    "workflow_run_name": "WR-API-7823"
}
```

Use `workflow_run_id` to retrieve full run details via `GET /workflow/{workflow_id}/runs/{workflow_run_id}`.

### Run Details Response (GET /workflow/{id}/runs/{run_id})

```python
{
    "id": 123,
    "workflow_id": 42,
    "name": "WR-API-7823",
    "mode": "phone",
    "created_at": "2026-06-20T12:00:00Z",
    "is_completed": True,
    "call_type": "outbound",                    # "outbound" or "inbound"
    "definition_id": 7,
    "transcript_url": "...",                     # Internal URL — use download endpoint
    "recording_url": "...",                      # Internal URL — use download endpoint
    "user_recording_url": "...",                 # Caller-side recording
    "bot_recording_url": "...",                  # Agent-side recording
    "transcript_public_url": "...",              # Time-limited public URL
    "recording_public_url": "...",               # Time-limited public URL
    "user_recording_public_url": "...",
    "bot_recording_public_url": "...",
    "public_access_token": "abc123",             # Token for /public/download/workflow/{token}/...
    "cost_info": {},
    "usage_info": {},
    "initial_context": {"customer_name": "Jane"},
    "gathered_context": {"interested": True, "appointment_time": "2pm Tuesday"},
    "logs": {},
    "annotations": {}                            # QA analysis results if qa node configured
}
```

### List Runs Response (GET /organizations/usage/runs)

```python
{
    "runs": [
        {
            "id": 123,
            "workflow_id": 42,
            "workflow_name": "Appointment Reminder",
            "name": "WR-API-7823",
            "created_at": "2026-06-20T12:00:00Z",
            "dograh_token_usage": 1500,
            "call_duration_seconds": 120,
            "phone_number": "+14155550100",
            "caller_number": "+14155550200",
            "called_number": "+14155550100",
            "call_type": "outbound",
            "mode": "phone",
            "disposition": "completed",
            "recording_url": "...",
            "transcript_url": "...",
            "recording_public_url": "...",
            "transcript_public_url": "...",
            "user_recording_url": "...",
            "bot_recording_url": "...",
            "user_recording_public_url": "...",
            "bot_recording_public_url": "...",
            "public_access_token": "abc123",
            "initial_context": {},
            "gathered_context": {},
            "charge_usd": 0.05
        }
    ],
    "total_dograh_tokens": 15000,
    "total_duration_seconds": 1200,
    "total_count": 50,
    "page": 1,
    "limit": 20,
    "total_pages": 3
}
```

**Query parameters:** `start_date`, `end_date` (ISO 8601 UTC), `page` (≥1), `limit` (1–100), `filters` (JSON-encoded array).

**Filter objects:** `{"attribute": "<name>", "type": "<type>", "value": <value>}`

| Attribute | Type | Value Example |
|---|---|---|
| `runId` | `number` | `{"value": 12345}` |
| `workflowId` | `number` | `{"value": 42}` |
| `campaignId` | `number` | `{"value": 7}` |
| `callerNumber` | `text` | `{"value": "415555"}` |
| `calledNumber` | `text` | `{"value": "9911848"}` |
| `dispositionCode` | `multiSelect` | `{"codes": ["XFER", "DNC"]}` |
| `duration` | `numberRange` | `{"min": 60, "max": 300}` |

### Download Recordings/Transcripts

Use the `public_access_token` from a run response to download artifacts:

```
GET /public/download/workflow/{token}/{artifact_type}
```

Where `artifact_type` is `recording` or `transcript`. Supports `?inline=true` query param to display in browser instead of download.

**Rules:**

- Never mix up Agent UUID (`workflow_uuid`) with API Trigger node UUID (`trigger_path`)
- Agent UUID → use `/public/agent/workflow/{workflow_uuid}`
- API Trigger UUID → use `/public/agent/{uuid}`
- Always check `is_completed` before accessing transcript/recording URLs
- `gathered_context` contains structured data extracted by the AI during the call — this is the main output
- Use `public_access_token` + download endpoint for time-limited public access to recordings/transcripts
- Campaign contacts CSV upload uses multipart form data via `/campaign/upload`, NOT a presigned S3 URL
- List runs filtering uses `start_date`/`end_date` query params for dates — NOT a `dateRange` filter object

---

## Celery + Redis

**Used for:** Background task processing — webhook handling, usage aggregation, billing calculations, campaign status sync.

### Task Definition

```python
# app/tasks/usage_tasks.py

from app.core.celery_app import celery_app
from app.services.usage_service import UsageService


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_call_usage(self, run_id: int, workflow_id: int, org_id: str):
    """Sync call usage data from Dograh to local DB."""
    try:
        service = UsageService()
        service.sync_run_usage(run_id, workflow_id, org_id)
    except Exception as exc:
        self.retry(exc=exc)
```

### Celery Configuration

```python
# app/core/celery_app.py

from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "neuvon",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
```

**Rules:**

- Tasks always have `max_retries` and `default_retry_delay`
- Tasks must be idempotent — safe to retry
- Never pass database objects to tasks — pass IDs and re-query
- Use `bind=True` for tasks that need `self.retry()`
- Task functions must not import from FastAPI routes

---

## PostHog

**Used for:** Server-side event tracking for analytics dashboard.

### Server-Side Client

```python
# app/core/posthog.py

from posthog import Posthog
from app.core.config import get_settings

settings = get_settings()

posthog_client = Posthog(
    api_key=settings.POSTHOG_API_KEY,
    host=settings.POSTHOG_HOST,
)


def track_event(
    distinct_id: str,
    event: str,
    properties: dict | None = None,
) -> None:
    """Track a PostHog event server-side."""
    posthog_client.capture(
        distinct_id=distinct_id,
        event=event,
        properties=properties or {},
    )
```

### Usage in Services

```python
from app.core.posthog import track_event

# After campaign starts
track_event(
    distinct_id=str(org_id),
    event="campaign_started",
    properties={
        "org_id": str(org_id),
        "campaign_id": str(campaign_id),
        "agent_id": agent_id,
        "contact_count": contact_count,
    },
)
```

**Rules:**

- Always use `str(org_id)` as `distinct_id` — organization-level tracking
- Event names must match exactly the list in `code-standards.md`
- Always include `org_id` in properties
- PostHog client is a singleton — initialized once at startup
- Never call PostHog from route handlers directly — call from services

---

## Razorpay

**Used for:** Payment processing, subscription management, billing.

### Client Setup

```python
# app/integrations/razorpay_client.py

import razorpay
from app.core.config import get_settings


def get_razorpay_client() -> razorpay.Client:
    settings = get_settings()
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )
```

### Order Creation

```python
client = get_razorpay_client()

order = client.order.create({
    "amount": amount_in_paise,  # Razorpay uses paise (1 INR = 100 paise)
    "currency": "INR",
    "receipt": f"order_{org_id}_{period}",
    "notes": {
        "organization_id": str(org_id),
        "billing_period": period,
    },
})
```

**Rules:**

- Amounts are always in paise (smallest currency unit) — multiply INR by 100
- Always include `organization_id` in order notes for reconciliation
- Verify webhook signatures before processing payment confirmations
- Never store raw Razorpay keys in the database — only order/payment IDs

---

## SQLModel

**Check first:** Check AGENTS.md for an installed SQLModel or FastAPI skill. SQLModel integrates SQLAlchemy with Pydantic.

### Model Definition

```python
# app/models/organization.py

from sqlmodel import SQLModel, Field
from datetime import datetime
from uuid import UUID, uuid4


class Organization(SQLModel, table=True):
    """Organization model — multi-tenant root entity."""
    __tablename__ = "organizations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True)
    owner_id: UUID = Field(foreign_key="users.id")
    plan: str = Field(default="free")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### Database Session

```python
# app/core/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """Dependency for database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Rules:**

- Always use async sessions — never synchronous
- Always use `expire_on_commit=False` for async sessions
- Models use `table=True` parameter for database-backed models
- Use `uuid4` for primary keys — never auto-increment integers
- Always define `__tablename__` explicitly

---

## Structlog

**Used for:** Structured JSON logging throughout the backend.

```python
# app/core/logging.py

import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),  # JSON in production
    ],
)

logger = structlog.get_logger()

# Usage
logger.info("campaign.started", org_id=org_id, campaign_id=campaign_id)
logger.error("dograh.call_failed", org_id=org_id, error=str(e))
```

**Rules:**

- Never use `print()` — always use structlog
- Always include `org_id` in log context for multi-tenant debugging
- Use dot-notation event names: `domain.action` (e.g., `campaign.started`, `dograh.call_failed`)
- Log at appropriate levels: `info` for operations, `warning` for recoverable issues, `error` for failures
