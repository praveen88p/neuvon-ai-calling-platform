# Code Standards

Implementation rules and conventions for the Neuvon backend. The AI agent must follow these in every session without exception. These rules prevent pattern drift across sessions.

---

## Engineering Mindset

The AI agent on this project operates as a senior engineer. This means:

- **Think before implementing** — understand what is being built and why before writing a single line
- **Read context files first** — never assume, always verify against architecture.md and project-overview.md
- **Scope is sacred** — only build what the current feature requires. Never go beyond scope even if it seems helpful
- **Every feature must be testable** — if it cannot be verified immediately after implementation, it is incomplete
- **Clean over clever** — simple readable code that a junior developer can understand is always preferred over clever abstractions
- **One thing at a time** — complete one feature fully before touching the next
- **Failures are expected** — wrap external calls in try/except, log failures, never let one failure crash everything

---

## Python

- Python 3.12+ — use modern Python features throughout
- All functions must have type annotations for parameters and return types
- Use `str | None` union syntax — never `Optional[str]` from typing
- Use `list[str]` lowercase generics — never `List[str]` from typing
- Use `Annotated` for all dependency injection in FastAPI routes
- Use `async def` for all route handlers and service functions that do I/O
- Use `def` only for pure synchronous utility functions
- Never use `Any` — use `Unknown` or proper types
- All async functions must have proper error handling — never let coroutines float unhandled
- Use `from __future__ import annotations` at the top of every file

---

## FastAPI Conventions

### Route Handlers

```python
# app/api/v1/endpoints/campaigns.py

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_user, get_db
from app.schemas.campaign import CampaignCreate, CampaignResponse
from app.services.campaign_service import CampaignService

router = APIRouter()


@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_in: CampaignCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CampaignResponse:
    """Create a new outbound campaign."""
    service = CampaignService(db)
    return await service.create(campaign_in, current_user)
```

**Rules:**

- Every route handler uses `Annotated` for dependency injection
- Every route handler has a docstring
- Route handlers contain NO business logic — they delegate to services
- Always use explicit `status_code` for create operations
- Always use `response_model` for type-safe responses
- Guard clauses for authorization checks — fail fast

### Pydantic Schemas (RORO Pattern)

```python
# app/schemas/campaign.py

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class CampaignCreate(BaseModel):
    """Input schema for creating a campaign."""
    name: str = Field(..., min_length=1, max_length=200)
    agent_id: str
    phone_number_id: str | None = None
    scheduled_start: datetime | None = None

    model_config = {"strict": True}


class CampaignResponse(BaseModel):
    """Output schema for campaign data."""
    id: UUID
    organization_id: UUID
    name: str
    status: str
    agent_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

**Rules:**

- Receive an Object, Return an Object (RORO) — always
- Input schemas: `*Create`, `*Update` — with validation rules
- Output schemas: `*Response` — with `from_attributes = True`
- Use `Field(...)` for required fields with validation
- Use `Field(None)` or `| None = None` for optional fields
- Never expose internal IDs or sensitive data in response schemas

---

## Service Layer

```python
# app/services/campaign_service.py

from app.models.campaign import Campaign
from app.schemas.campaign import CampaignCreate, CampaignResponse
from app.integrations.dograh_client import DograhClient


class CampaignService:
    """Business logic for campaign operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dograh = DograhClient()

    async def create(
        self, campaign_in: CampaignCreate, current_user: User
    ) -> Campaign:
        """Create campaign in both Dograh and local DB."""
        # 1. Create in Dograh
        dograh_campaign = await self.dograh.create_campaign(campaign_in)

        # 2. Save to local DB with org context
        campaign = Campaign(
            organization_id=current_user.organization_id,
            dograh_campaign_id=dograh_campaign.id,
            **campaign_in.model_dump(),
        )
        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)
        return campaign
```

**Rules:**

- Services contain ALL business logic — routes are thin
- Services receive validated Pydantic models — never raw dicts
- Services always scope operations to the current user's organization
- External API calls (Dograh, Razorpay) happen in services, never in routes
- Services never import from routes or schemas directly — they work with domain models

---

## Dograh Integration Layer

```python
# app/integrations/dograh_client.py

import httpx
from app.core.config import get_settings


class DograhClient:
    """HTTP client for Dograh API communication."""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.DOGRAH_BASE_URL
        self.api_key = settings.DOGRAH_API_KEY

    async def _request(
        self, method: str, path: str, **kwargs
    ) -> dict:
        """Make authenticated request to Dograh API."""
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{self.base_url}/api/v1{path}",
                headers={"X-API-Key": self.api_key},
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
```

**Rules:**

- All Dograh communication goes through `DograhClient` — never call Dograh directly from services
- Always use HTTPX async client — never `requests`
- Always pass `X-API-Key` header for authentication
- Handle Dograh errors gracefully — map to appropriate HTTP errors for the frontend
- Log all Dograh API calls for debugging

---

## File and Folder Naming

- Folders: snake_case — `call_history`, `agent_management`
- Python modules: snake_case — `campaign_service.py`, `dograh_client.py`
- Pydantic schemas: PascalCase classes — `CampaignCreate`, `UserResponse`
- SQLModel/SQLAlchemy models: PascalCase classes — `Campaign`, `Organization`
- One router per domain — never combine unrelated routes in one file
- Constants: UPPER_SNAKE_CASE — `MAX_CONCURRENT_CALLS`, `DEFAULT_PAGE_SIZE`

---

## Error Handling

```python
from fastapi import HTTPException, status


# Guard clause pattern — fail fast
async def get_campaign(campaign_id: UUID, current_user: User, db: AsyncSession):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return campaign
```

**Rules:**

- Never use empty except blocks — always log or handle
- Use guard clauses — check and fail early, keep happy path unindented
- Log errors with context: `logger.error("campaign.create failed", extra={"org_id": org_id})`
- User-facing errors must be human readable — never expose raw tracebacks
- External API errors (Dograh, Razorpay) must be caught and mapped to proper HTTP responses
- Use structured logging (JSON format) — never `print()`

---

## Multi-Tenancy Rules

Every database query, every API response, and every external call MUST be scoped to the current user's organization.

```python
# CORRECT — always filter by organization
campaigns = await db.execute(
    select(Campaign).where(Campaign.organization_id == current_user.organization_id)
)

# NEVER — unscoped query
campaigns = await db.execute(select(Campaign))
```

**Rules:**

- Every `SELECT` includes `WHERE organization_id = ...`
- Every `INSERT` includes `organization_id` from the current user context
- Never trust client-provided `organization_id` — always derive from the authenticated JWT
- Dograh API calls use organization-specific API keys where applicable
- RLS at the database level as a safety net, but application-level filtering is the primary guard

---

## Environment Variables

All environment variables defined in `.env` for development. Never hardcode any key, URL, or secret anywhere in the codebase.

| Variable | Used In |
|---|---|
| `DATABASE_URL` | Database connection |
| `INSFORGE_URL` | InsForge client |
| `INSFORGE_ANON_KEY` | InsForge client |
| `INSFORGE_SERVICE_KEY` | InsForge admin operations |
| `DOGRAH_BASE_URL` | Dograh API client |
| `DOGRAH_API_KEY` | Dograh API authentication |
| `SECRET_KEY` | JWT signing |
| `RAZORPAY_KEY_ID` | Razorpay payment integration |
| `RAZORPAY_KEY_SECRET` | Razorpay payment integration |
| `POSTHOG_API_KEY` | PostHog server-side events |
| `POSTHOG_HOST` | PostHog host URL |
| `REDIS_URL` | Redis for Celery + caching + WebSocket |
| `CORS_ORIGINS` | Allowed frontend origins |

Never prefix secrets with `NEXT_PUBLIC_` or expose them to the frontend.

---

## PostHog Events

All PostHog events must use these exact event names. Never invent new event names without adding them here first.

| Event | When | Key Properties |
|---|---|---|
| `campaign_started` | Campaign start button clicked | org_id, campaign_id, agent_id, contact_count |
| `campaign_completed` | All contacts in campaign processed | org_id, campaign_id, total_calls, total_minutes |
| `call_triggered` | Outbound call initiated | org_id, agent_id, call_type |
| `call_completed` | Call run finishes | org_id, run_id, duration_seconds, disposition |
| `leads_uploaded` | CSV contacts uploaded | org_id, campaign_id, lead_count |
| `user_logged_in` | Successful authentication | user_id, org_id |
| `agent_created` | New agent created | org_id, agent_id, creation_method |
| `phone_number_added` | Phone number registered | org_id, provider, number |

---

## Dependencies

Never install a new package without a clear reason. Before installing anything check:

1. Does the standard library already provide this?
2. Does FastAPI already provide this functionality?
3. Is there a simpler native solution?

Approved dependencies for this project:

- `fastapi` — Web framework
- `uvicorn` — ASGI server
- `sqlmodel` — ORM (SQLAlchemy + Pydantic)
- `asyncpg` — Async PostgreSQL driver
- `alembic` — Database migrations
- `httpx` — Async HTTP client (Dograh API, external calls)
- `python-jose[cryptography]` — JWT handling
- `passlib[bcrypt]` — Password hashing
- `pydantic-settings` — Settings management
- `celery[redis]` — Background task queue
- `redis` — Caching, WebSocket pub/sub, Celery broker
- `posthog` — Server-side analytics
- `razorpay` — Payment processing
- `python-multipart` — File upload handling
- `structlog` — Structured logging

Do not install any other packages without updating this list first.

---

## Comments

- No comments explaining what the code does — code must be self-explanatory
- Comments only for why — explaining a non-obvious decision
- Dograh integration functions may have a brief comment explaining the API mapping
- Never leave TODO comments in committed code
- Use docstrings for all public functions and classes

---

## Import Order

Always follow this import order, separated by blank lines:

```python
# 1. Standard library
from datetime import datetime
from uuid import UUID

# 2. Third-party libraries
from fastapi import APIRouter, Depends
from sqlmodel import select

# 3. Local application
from app.core.config import get_settings
from app.services.campaign_service import CampaignService
```
