# Build Plan: Spreadsheet Integration — Auto-Call Leads

## What We Learned from Reference Repositories

### Repo 1: kaymen99/leads-reactivation-with-AI-Voice-Agent

| Pattern | File | Adopt? | Notes |
|---|---|---|---|
| **ABC base class** for CRM connectors | `lead_loader_base.py` | ✅ Adopt concept | Two methods: `fetch_records()` + `update_record()`. Clean interface. We'll use a Protocol instead of ABC (more Pythonic for our stack) |
| **Google Sheets read** — header-based column detection | `google_sheets.py L32-58` | ✅ Adopt pattern | Reads row 1 as headers, zips with data rows. We use this for auto-detecting columns. Their `record["id"] = row_number` trick is good |
| **Batch update** — `batchUpdate` for writing multiple cells | `google_sheets.py L60-101` | ✅ Adopt pattern | Efficient: converts column name → letter via `chr(65 + col_index)`, sends one batch request. We use this for writing results back |
| **Auto-detect sheet name** from spreadsheet ID | `google_sheets.py L117-130` | ✅ Adopt | Calls `spreadsheets().get()` to list sheets, defaults to first tab |
| **Lead Pydantic model** | `utils.py L7-13` | ✅ Adapt | Good structure. We'll make ours dynamic (fields from column mapping, not hardcoded) |
| **Post-call → CRM update flow** | `vapi_automation.py L97-127` | ✅ Adopt flow | `evaluate_call_and_update_crm()`: extracts summary/interest/status → calls `update_record()` on loader. Exactly what our webhook extension does |
| Desktop OAuth (`InstalledAppFlow.run_local_server`) | `google_sheets.py L12-24` | ❌ Skip | Desktop-only auth. We need web redirect OAuth |
| `time.sleep(1)` between calls | `app.py L68` | ❌ Skip | Blocking sleep in async code. Bad practice. We use Celery task queuing |
| `print()` for logging | everywhere | ❌ Skip | We use structlog |
| `allow_origins=["*"]` in CORS | `app.py L19` | ❌ Skip | Insecure. Our CORS is restricted to frontend origin |
| Hardcoded column names ("First Name", "Phone") | `vapi_automation.py L31-43` | ❌ Skip | We use dynamic column mapping per connection |

### Repo 2: OthmanMohammad/Voice-TimeLogger-Agent

| Pattern | File | Adopt? | Notes |
|---|---|---|---|
| **`asyncio.to_thread()` for blocking IO** | `google_sheets_storage.py L136-143` | ✅ Adopt | Google Sheets API is synchronous. Wrapping in `asyncio.to_thread()` prevents blocking the event loop. Critical for FastAPI |
| **Sheet initialization** — create sheet + headers if missing | `google_sheets_storage.py L145-245` | ✅ Adopt concept | Checks if sheet tab exists, creates it, adds headers, formats. Useful for adding result columns to client sheets |
| **Column mapping config** (field → index mapping) | `config.py` | ✅ Adapt pattern | They use hardcoded `MEETING_DATA_TO_SHEET_MAPPING`. We'll make it dynamic per connection, stored in DB as JSONB |
| **Append row via API** — `values().append()` with `INSERT_ROWS` | `google_sheets_storage.py L377-414` | ✅ Adopt | Correct API usage for appending. We use this if we need to add result columns |
| **Custom error hierarchy** (`StorageError` + `ErrorCode`) | `google_sheets_storage.py L61-94` | ✅ Adopt pattern | We create `SheetConnectionError` with codes for API errors, auth expired, sheet not found |
| **Lazy initialization** of storage backend | `storage_manager.py L104-111` | ✅ Adopt | Good pattern — don't create Sheets API service until first use |
| Service account auth (static JSON file) | `google_sheets_storage.py L96-122` | ❌ Skip | We need per-client OAuth tokens, not a single service account |
| Hardcoded sheet headers | `config.py L7-15` | ❌ Skip | We read headers dynamically from the client's sheet |

---

## Architecture Decision: How It Fits Our Stack

```
┌──────────────── OUR EXISTING ARCHITECTURE ────────────────┐
│                                                            │
│  Route Layer           Service Layer         Integration   │
│  ┌─────────────┐       ┌───────────────┐     ┌──────────┐ │
│  │ routes/     │──────▶│ services/     │────▶│ integra- │ │
│  │ sheets.py   │       │ sheet_service │     │ tions/   │ │
│  │ [NEW]       │       │ .py [NEW]     │     │ google_  │ │
│  └─────────────┘       └───────┬───────┘     │ sheets_  │ │
│                                │              │ client.py│ │
│                                │              │ [NEW]    │ │
│                                │              └──────────┘ │
│                                │                           │
│                                ▼                           │
│  ┌─────────────┐       ┌───────────────┐                   │
│  │ tasks/      │       │ services/     │                   │
│  │ sheet_      │──────▶│ call_service  │ (existing)        │
│  │ polling.py  │       │ .py           │                   │
│  │ [NEW]       │       └───────────────┘                   │
│  └─────────────┘                                           │
│                                                            │
│  ┌─────────────┐       ┌───────────────┐                   │
│  │ services/   │       │ services/     │                   │
│  │ webhook_    │──────▶│ sheet_service │ (write-back)      │
│  │ service.py  │       │ .py           │                   │
│  │ [EXTEND]    │       └───────────────┘                   │
│  └─────────────┘                                           │
└────────────────────────────────────────────────────────────┘
```

### Key Architecture Decisions

| Decision | Choice | Why |
|---|---|---|
| **Auth method** | Service Account (Phase 1), OAuth2 (Phase 2) | Service account is much simpler: client shares sheet with our bot email. OAuth can come later for seamless UX |
| **New row detection** | Celery Beat polling every 60s | Reliable, zero client setup, acceptable latency for calling |
| **Google API wrapper** | `google-api-python-client` + `asyncio.to_thread()` | Same approach as Voice-TimeLogger repo. Not `gspread` — we want lower-level control |
| **Multi-tenancy** | `sheet_connections` table scoped by `organization_id` | Same pattern as `dograh_agent_mappings` |
| **Webhook extension** | Extend existing `WebhookService.process_dograh_webhook()` | Add check: "did this call come from a sheet connection?" → if yes, write back results |

---

## New Files to Create

### Backend

```
backend/app/
├── integrations/
│   └── google_sheets_client.py      [NEW] — Google Sheets API wrapper
├── services/
│   └── sheet_service.py             [NEW] — Business logic for connections, polling, write-back
├── schemas/
│   └── sheets.py                    [NEW] — Pydantic request/response schemas
├── routes/
│   └── sheets.py                    [NEW] — FastAPI router for /api/v1/sheets/*
├── tasks/
│   └── sheet_tasks.py               [NEW] — Celery polling + callback scheduling tasks
└── migrations/
    └── 009_sheet_connections.sql     [NEW] — DB tables
```

### Frontend

```
frontend/src/
├── pages/
│   └── Integrations.tsx             [NEW] — Integrations page
├── components/
│   └── integrations/
│       ├── ConnectSheetModal.tsx     [NEW] — Sheet URL + column mapping
│       ├── SheetConnectionCard.tsx   [NEW] — Active connection display
│       └── SheetLeadActivity.tsx     [NEW] — Lead call activity feed
└── lib/
    └── api-client.ts                [MODIFY] — Add sheets API methods
```

---

## Database: Migration 009

```sql
-- 009_sheet_connections.sql

-- Table 1: Sheet connections (one per connected spreadsheet per org)
CREATE TABLE IF NOT EXISTS sheet_connections (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id     UUID        NOT NULL,
    
    -- Sheet info
    provider            TEXT        NOT NULL DEFAULT 'google_sheets'
                        CHECK (provider IN ('google_sheets', 'excel_online')),
    sheet_url           TEXT        NOT NULL,
    spreadsheet_id      TEXT        NOT NULL,
    sheet_name          TEXT        DEFAULT 'Sheet1',
    
    -- Column mapping: {"phone": "B", "name": "A", "email": "C", ...}
    column_mapping      JSONB       NOT NULL DEFAULT '{}',
    
    -- Which agent handles calls from this sheet
    agent_workflow_id   INTEGER     NOT NULL,
    
    -- Service account or OAuth (Phase 1: service account)
    credentials_json    TEXT,           -- encrypted service account key or OAuth tokens
    
    -- Polling state
    last_row_processed  INTEGER     NOT NULL DEFAULT 1,
    polling_interval    INTEGER     NOT NULL DEFAULT 60,
    is_active           BOOLEAN     NOT NULL DEFAULT TRUE,
    
    -- Stats
    total_leads_called  INTEGER     NOT NULL DEFAULT 0,
    total_leads_qualified INTEGER   NOT NULL DEFAULT 0,
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table 2: Individual leads from sheets (tracks row → call mapping)
CREATE TABLE IF NOT EXISTS sheet_leads (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    connection_id       UUID        NOT NULL REFERENCES sheet_connections(id) ON DELETE CASCADE,
    organization_id     UUID        NOT NULL,
    
    row_number          INTEGER     NOT NULL,
    phone_number        TEXT        NOT NULL,
    lead_data           JSONB       DEFAULT '{}',
    
    -- Call tracking
    dograh_run_id       INTEGER,
    call_status         TEXT        DEFAULT 'pending'
                        CHECK (call_status IN ('pending','calling','completed','failed','callback_scheduled')),
    call_summary        TEXT,
    lead_tag            TEXT,
    callback_at         TIMESTAMPTZ,
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(connection_id, row_number)
);

-- Table 3: Scheduled callbacks
CREATE TABLE IF NOT EXISTS scheduled_callbacks (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id     UUID        NOT NULL,
    sheet_lead_id       UUID        REFERENCES sheet_leads(id),
    
    phone_number        TEXT        NOT NULL,
    workflow_id         INTEGER     NOT NULL,
    initial_context     JSONB       DEFAULT '{}',
    
    callback_at         TIMESTAMPTZ NOT NULL,
    status              TEXT        NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','triggered','completed','cancelled')),
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS policies
ALTER TABLE sheet_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE sheet_leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_callbacks ENABLE ROW LEVEL SECURITY;

CREATE POLICY sheet_connections_org_isolation ON sheet_connections
    FOR ALL USING (TRUE);

CREATE POLICY sheet_leads_org_isolation ON sheet_leads
    FOR ALL USING (TRUE);

CREATE POLICY scheduled_callbacks_org_isolation ON scheduled_callbacks
    FOR ALL USING (TRUE);
```

---

## File-by-File Implementation

### 1. `backend/app/integrations/google_sheets_client.py`

**Purpose:** Low-level Google Sheets API wrapper (like our `DograhClient`)

**Inspired by:** 
- Voice-TimeLogger: `asyncio.to_thread()` pattern, sheet initialization, error handling
- leads-reactivation: batch update, header detection

**What it does:**
```python
class GoogleSheetsClient:
    """Async wrapper around Google Sheets API v4.
    
    All blocking IO runs via asyncio.to_thread() to prevent
    blocking the FastAPI event loop.
    """
    
    async def connect(credentials_json: str, spreadsheet_id: str) -> Self
    async def read_headers(sheet_name: str) -> list[str]
    async def read_rows(sheet_name: str, start_row: int) -> list[list[str]]
    async def update_cells(sheet_name: str, updates: list[CellUpdate]) -> None
    async def get_sheet_names() -> list[str]
    async def get_row_count(sheet_name: str) -> int
```

**Key difference from repos:** Credentials come from DB per-connection, not from a file on disk.

---

### 2. `backend/app/services/sheet_service.py`

**Purpose:** All business logic for sheet connections (the "brain")

**Follows:** Our existing service pattern (RORO, org-scoped, no HTTP objects)

```python
class SheetService:
    """Business logic for spreadsheet connections.
    
    Handles: connection creation, column auto-detection,
    lead polling, call triggering, and post-call write-back.
    """
    
    # --- Connection management ---
    async def create_connection(data, org_id) -> SheetConnectionResponse
    async def list_connections(org_id) -> list[SheetConnectionResponse]
    async def update_connection(conn_id, data, org_id) -> SheetConnectionResponse
    async def delete_connection(conn_id, org_id) -> None
    async def pause_connection(conn_id, org_id) -> None
    async def resume_connection(conn_id, org_id) -> None
    
    # --- Sheet reading ---
    async def detect_columns(spreadsheet_url, credentials_json) -> SheetColumnsResponse
    async def poll_for_new_leads(connection_id) -> int
    
    # --- Call triggering ---
    async def trigger_lead_call(lead_id) -> None
    
    # --- Post-call write-back ---
    async def write_call_results(lead_id, results) -> None
    
    # --- Callback scheduling ---
    async def schedule_callback(lead_id, callback_at) -> None
```

**Key flows:**

**Flow A: Poll for new leads** (called by Celery every 60s)
```
1. Load connection from DB (sheet_connections)
2. Build GoogleSheetsClient with stored credentials
3. Read rows from last_row_processed to end
4. For each new row:
   a. Map columns using column_mapping → extract phone, name, etc.
   b. Skip if phone is empty or already in sheet_leads
   c. INSERT into sheet_leads (status: pending)
   d. Call call_service.trigger_call() with initial_context from mapped data
   e. UPDATE sheet_leads (status: calling, dograh_run_id from response)
5. UPDATE sheet_connections.last_row_processed
```

**Flow B: Write results back** (called from webhook_service after call completes)
```
1. Lookup sheet_leads by dograh_run_id
2. If found → this call came from a sheet connection
3. Build GoogleSheetsClient with connection's credentials  
4. Use batch update to write: Status, Summary, Tag, Callback columns
5. UPDATE sheet_leads with call_summary, lead_tag, callback_at
6. If callback_at → INSERT into scheduled_callbacks
```

---

### 3. `backend/app/schemas/sheets.py`

**Pydantic schemas (RORO pattern):**

```python
# --- Request schemas ---
class SheetConnectionCreate(BaseModel):
    sheet_url: str                    # Full Google Sheets URL
    sheet_name: str | None = None     # Tab name (auto-detect if None)
    column_mapping: dict[str, str]    # {"phone": "B", "name": "A", ...}
    agent_workflow_id: int            # Which agent handles calls
    credentials_json: str             # Service account JSON (Phase 1)
    polling_interval: int = 60

class SheetConnectionUpdate(BaseModel):
    column_mapping: dict[str, str] | None = None
    agent_workflow_id: int | None = None
    polling_interval: int | None = None
    is_active: bool | None = None

# --- Response schemas ---
class SheetConnectionResponse(BaseModel):
    id: str
    provider: str
    sheet_url: str
    sheet_name: str
    column_mapping: dict[str, str]
    agent_workflow_id: int
    is_active: bool
    last_row_processed: int
    total_leads_called: int
    total_leads_qualified: int
    created_at: datetime

class SheetColumnsResponse(BaseModel):
    columns: list[SheetColumn]
    sheet_names: list[str]
    row_count: int

class SheetColumn(BaseModel):
    letter: str     # "A", "B", "C"
    header: str     # "Name", "Phone Number", "Email"
    sample: str     # first data value for preview

class SheetLeadResponse(BaseModel):
    id: str
    row_number: int
    phone_number: str
    lead_data: dict
    call_status: str
    call_summary: str | None
    lead_tag: str | None
    callback_at: datetime | None
```

---

### 4. `backend/app/routes/sheets.py`

**FastAPI router:**

```
POST   /api/v1/sheets/connections              — Create a new sheet connection
GET    /api/v1/sheets/connections              — List all connections for this org
PATCH  /api/v1/sheets/connections/{id}         — Update connection settings
DELETE /api/v1/sheets/connections/{id}         — Disconnect sheet
POST   /api/v1/sheets/connections/{id}/pause   — Pause polling
POST   /api/v1/sheets/connections/{id}/resume  — Resume polling
POST   /api/v1/sheets/detect-columns          — Auto-detect columns from sheet URL
GET    /api/v1/sheets/connections/{id}/leads   — List leads + call results
GET    /api/v1/sheets/connections/{id}/stats   — Connection stats
```

---

### 5. `backend/app/tasks/sheet_tasks.py`

**Celery tasks:**

```python
# Task 1: Poll all active connections (runs every 60s via Celery Beat)
@celery_app.task(name="sheets.poll_all")
def poll_all_active_connections():
    """Iterate all active sheet_connections, poll each for new rows."""

# Task 2: Poll a single connection
@celery_app.task(name="sheets.poll_one")
def poll_single_connection(connection_id: str):
    """Poll a specific connection for new leads and trigger calls."""

# Task 3: Check due callbacks (runs every 60s)
@celery_app.task(name="sheets.check_callbacks")  
def check_due_callbacks():
    """Find scheduled_callbacks where callback_at <= now, trigger calls."""
```

**Celery Beat schedule (add to celery_app.py):**
```python
app.conf.beat_schedule = {
    "poll-sheet-connections": {
        "task": "sheets.poll_all",
        "schedule": 60.0,
    },
    "check-callbacks": {
        "task": "sheets.check_callbacks",
        "schedule": 60.0,
    },
}
```

---

### 6. Extend `backend/app/services/webhook_service.py`

**Add after existing gathered_context processing (~line 130):**

```python
# Check if this call was triggered from a sheet connection
sheet_lead = await self._find_sheet_lead_by_run_id(run_id)
if sheet_lead:
    try:
        from app.services.sheet_service import SheetService
        sheet_svc = SheetService()
        await sheet_svc.write_call_results(
            lead_id=str(sheet_lead["id"]),
            results={
                "call_summary": (payload.gathered_context or {}).get("call_summary", ""),
                "lead_tag": (payload.gathered_context or {}).get("lead_tag", ""),
                "callback_time": (payload.gathered_context or {}).get("callback_time"),
                "call_status": payload.status,
                "duration_seconds": payload.duration_seconds,
            }
        )
    except Exception as exc:
        logger.warning("webhook.sheet_writeback_failed", run_id=run_id, error=str(exc))
```

---

## Implementation Phases

### Phase 1: Core Backend (3-4 days)

| Task | Files | Dependency |
|---|---|---|
| Create migration + run in InsForge SQL editor | `migrations/009_sheet_connections.sql` | None |
| Create Google Sheets client wrapper | `integrations/google_sheets_client.py` | None |
| Create Pydantic schemas | `schemas/sheets.py` | None |
| Create SheetService (connection CRUD + detect columns) | `services/sheet_service.py` | Client + Schemas |
| Create API routes | `routes/sheets.py` | SheetService |
| Add Celery polling task | `tasks/sheet_tasks.py` | SheetService |
| Extend webhook for write-back | `services/webhook_service.py` | SheetService |
| Add Celery Beat schedule | `core/celery_app.py` | Tasks |

### Phase 2: Frontend UI (2-3 days)

| Task | Files |
|---|---|
| Add "Integrations" to sidebar nav | `components/layout/Sidebar.tsx` |
| Create Integrations page | `pages/Integrations.tsx` |
| Create ConnectSheetModal (URL input + column mapping) | `components/integrations/ConnectSheetModal.tsx` |
| Create SheetConnectionCard (status, stats, pause/resume) | `components/integrations/SheetConnectionCard.tsx` |
| Create SheetLeadActivity (lead table with call results) | `components/integrations/SheetLeadActivity.tsx` |
| Add API client methods | `lib/api-client.ts` |

### Phase 3: Callback Scheduling (1 day)

| Task | Files |
|---|---|
| Add callback check in Celery Beat | `tasks/sheet_tasks.py` |
| Extend webhook to extract callback_time from gathered_context | `services/webhook_service.py` |
| Support "Call me at X" → auto-schedule | `services/sheet_service.py` |

### Phase 4: Polish (1-2 days)

| Task | Details |
|---|---|
| Rate limiting | Max 5 concurrent calls per connection to avoid overwhelming telephony |
| Error recovery | If Google API token expires, mark connection as "needs reauth" |
| Duplicate detection | Skip if same phone already called in last 24h |
| Audit logging | Log all connection changes and call triggers |

---

## Dependencies to Install

```bash
# Backend
pip install google-api-python-client google-auth google-auth-httplib2
```

No new frontend dependencies needed.

---

## Environment Variables to Add

```bash
# Phase 1: Global service account (simpler — all clients share one bot)
GOOGLE_SERVICE_ACCOUNT_EMAIL=neuvon-sheets-bot@neuvon-ai.iam.gserviceaccount.com

# Phase 2: OAuth (per-client consent)  
GOOGLE_OAUTH_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=xxx
GOOGLE_OAUTH_REDIRECT_URI=https://api.neuvonsoftware.com/api/v1/sheets/oauth/callback
```

---

## What This Plan Does NOT Include

These are explicitly deferred for future phases:

1. **Microsoft Excel Online** — Same architecture, different API (`msgraph-sdk-python`). Add as a second connector later
2. **Airtable** — Same architecture, simpler API
3. **OAuth2 user consent flow** — Phase 1 uses service account approach. Client shares their sheet with our bot email. Much simpler and faster to build
4. **Real-time detection** (Apps Script webhook) — Polling every 60s is sufficient. Can add Apps Script later for near-instant detection
5. **Frontend column auto-suggest** — AI-powered column mapping ("Phone" → phone_number) is nice-to-have, not MVP
