# Google Sheets Integration — Status & Context

> **Last Updated:** 2026-08-13  
> **Purpose:** Context snapshot so we can pause and resume work on the sheets integration without losing any history.  
> **Status:** Partially working — calls trigger correctly, but post-call writeback and stats are still not 100% verified end-to-end.

---

## 1. What This Feature Does

The Google Sheets integration allows organizations to:

1. **Connect** a Google Sheet (via service account JSON credentials)
2. **Map columns** (phone, name, email, etc.)
3. **Auto-call** every new lead row using a chosen Dograh AI agent
4. **Write back** call results (status, summary, tag) into the sheet
5. **Schedule callbacks** when a caller says "call me later"

---

## 2. Architecture / Data Flow

```
Google Sheet (new row added)
      ↓
Celery Beat (every 60s) → poll_for_new_leads()
      ↓
Read rows from Google Sheets API (start_row = last_row_processed + 1)
      ↓
Insert sheet_lead record (call_status = "pending")
      ↓
_trigger_lead_call() → Dograh API POST /public/agent/{uuid}
      ↓
Call goes out to the lead's phone number
      ↓
Call completes → Dograh fires webhook node → POST /api/v1/webhooks/dograh
      ↓
webhook_service.process_dograh_webhook()
      ↓
_find_sheet_lead_by_run_id() → write_call_results()
      ↓
Update: sheet_leads.call_status, call_runs.status + duration_seconds
Update: sheet_connections.total_leads_called
Write back result to Google Sheet (writeback_done = true)
```

---

## 3. Database Tables

### `sheet_connections`
One row per connected spreadsheet (org-scoped).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `organization_id` | UUID | Scoped per org |
| `provider` | TEXT | `google_sheets` only |
| `sheet_url` | TEXT | Full Google Sheets URL |
| `spreadsheet_id` | TEXT | Extracted from URL |
| `sheet_name` | TEXT | Default `Sheet1` |
| `column_mapping` | JSONB | `{"phone": "B", "name": "A"}` |
| `agent_workflow_id` | INT | Dograh workflow ID |
| `credentials_json` | TEXT | Service account JSON |
| `last_row_processed` | INT | Default `1` (header); polls from `last_row_processed + 1` |
| `polling_interval_secs` | INT | Default `60` |
| `is_active` | BOOL | Active/paused |
| `last_polled_at` | TIMESTAMPTZ | Updated after every poll |
| `last_error` | TEXT | Last error message |
| `total_leads_found` | INT | Count of leads detected |
| `total_leads_called` | INT | Count of calls triggered |
| `total_leads_qualified` | INT | Count of qualified leads |
| `needs_reauth` | BOOL | Set when auth fails |
| `consecutive_error_count` | INT | Resets on success |

### `sheet_leads`
One row per lead detected from a sheet row.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `connection_id` | UUID FK | → sheet_connections |
| `organization_id` | UUID | |
| `row_number` | INT | 1-indexed Google Sheet row number |
| `phone_number` | TEXT | |
| `lead_data` | JSONB | Full row data as key-value |
| `dograh_run_id` | INT | Set after call triggered |
| `call_status` | TEXT | `pending → calling → completed/failed` |
| `call_summary` | TEXT | Written back from webhook |
| `lead_tag` | TEXT | `qualified`, `not_interested`, etc. |
| `callback_at` | TIMESTAMPTZ | If callback requested |
| `writeback_done` | BOOL | True after Google Sheet writeback |
| UNIQUE | `(connection_id, row_number)` | Prevents duplicate processing |

### `scheduled_callbacks`
Tracks leads who asked to be called back later.

| Column | Notes |
|---|---|
| `callback_at` | When to trigger the call |
| `status` | `pending → triggered → completed` |
| `retry_count` | Max 3 retries |

---

## 4. Key Source Files

| File | Role |
|---|---|
| `backend/app/services/sheet_service.py` | Core logic — 1,250 lines |
| `backend/app/services/webhook_service.py` | Processes Dograh post-call webhooks |
| `backend/app/services/callback_service.py` | Handles scheduled callbacks |
| `backend/app/tasks/sheet_tasks.py` | Celery tasks (poll_all, check_callbacks) |
| `backend/app/integrations/google_sheets_client.py` | Google Sheets API wrapper |
| `backend/app/integrations/dograh_client.py` | Dograh API client |
| `backend/app/integrations/insforge_client.py` | InsForge (BaaS) client |
| `backend/app/api/v1/endpoints/sheets.py` | REST endpoints |
| `backend/app/schemas/webhook.py` | `DograhWebhookPayload` Pydantic model |
| `backend/migrations/009_sheet_connections.sql` | Table definitions |
| `backend/migrations/011_sheet_phase4.sql` | Phase 4 additions |

---

## 5. Bugs Fixed (Chronological)

### Bug 1 — `RuntimeError: Event loop is closed` in Celery (FIXED)
**Symptom:** Celery worker crashed on every second task run.

**Root Cause A:** `@lru_cache` on `get_insforge_admin()` — the cached `InsforgeClient`
held an `httpx.AsyncClient` bound to the first event loop. After `_run_async` closed
the loop, the cached client had dead connections.

**Root Cause B:** `asyncio.new_event_loop()` was created but not set as the current loop.

**Fix in `insforge_client.py`:** Removed `@lru_cache`.

**Fix in `sheet_tasks.py`:**
```python
def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)   # ← critical
    try:
        return loop.run_until_complete(coro)
    finally:
        asyncio.set_event_loop(None)  # cleanup
```

---

### Bug 2 — `return_representation=True` injected into wrong calls (FIXED)
**Symptom:** Stats showed 0, `last_polled_at` never updated — but no errors.

**Root Cause:** Regex that added `return_representation=True` to all `.update()` calls was
too greedy and also corrupted:
- `conn.get("total_leads_found", 0, return_representation=True)` — `dict.get()` with extra kwarg → **TypeError**
- `datetime.now(timezone.utc, return_representation=True)` → **TypeError**

These TypeErrors were swallowed by `except Exception` blocks silently.

**Fix:** Manually removed the flag from all non-`.update()` calls.

---

### Bug 3 — Multi-line `.update()` blocks missing `return_representation=True` (FIXED)
**Symptom:** Same as Bug 2.

4 multi-line update blocks were missed:
1. `total_leads_found` increment
2. `call_status: "calling"` update in `_trigger_lead_call`
3. `call_status: "failed"` error handler
4. `last_row_processed` + `last_polled_at` in `_update_poll_state`

> **InsForge rule:** Without `return_representation=True`, `.update()` returns empty 204.
> The internal `response.json()` crashes on an empty body. Always add this flag.

---

### Bug 4 — Auto-poll silently skipped (FIXED)
**Symptom:** User had to click ⚡ every time. Celery Beat didn't auto-detect leads.

**Root Cause:** `_poll_all` had:
```python
if elapsed < polling_interval_secs:
    continue  # double-gate with Celery Beat schedule
```
After clicking ⚡, `last_polled_at` reset to NOW → next beat cycle saw `elapsed ≈ 0 < 60` → skipped.

**Fix:** Removed the `elapsed < interval` check. Beat schedule is the single source of truth.

---

### Bug 5 — `start_row` / `new_last_row` formula errors (FIXED)
**Symptom:** Header row processed as lead; row tracking off.

```python
# WRONG
start_row = last_row + 1       # gives 1 (header) when last_row = 0
new_last_row = last_row + len(new_rows)  # incorrect offset

# CORRECT
start_row = max(2, last_row + 1)         # always skip header at row 1
new_last_row = start_row + len(new_rows) - 1  # actual sheet row number
```

---

### Bug 6 — `_find_sheet_lead_by_run_id` used old Supabase API (FIXED)
**Symptom:** Call history stuck at `initiated` / `0s`. Stats never incremented.

**Root Cause:** Webhook arrived but `_find_sheet_lead_by_run_id` used `self.db.table()` +
`result.data` (Supabase pattern). With InsForge this returned nothing, exception was
swallowed → `sheet_lead` was always `None` → `write_call_results` never called.

```python
# WRONG (Supabase):
result = await self.db.table("sheet_leads").select("*").eq(...).execute()
rows = result.data or []

# CORRECT (InsForge):
result = await self.db.database.from_("sheet_leads").select("*").eq(...).execute()
rows = result if isinstance(result, list) else []
```

---

### Bug 7 — `insert()` without `return_representation=True` → `lead_id=None` (FIXED)
**Symptom:**
```
PATCH failed: invalid input syntax for type uuid: "null"
```

**Root Cause:** `insert([lead_row])` without `return_representation=True` returns empty 204
→ `insert_result` is empty → `lead_record.get("id")` = `None` → PATCH with `id="null"` crashes.

**Fix:** Added `return_representation=True` to:
- `sheet_connections` insert
- `sheet_leads` insert

---

### Bug 8 — Webhook node added to Dograh agent (VERIFIED)
The agent `workflow_id=9458` already had a webhook node `neuvon-webhook` correctly configured.

Added `ensure_webhook_node()` to `DograhClient` + `_sync_dograh_webhook()` to
`SheetService.create_connection()` so **future connections auto-inject the webhook node**.

---

## 6. InsForge API — Golden Rules

```python
# Query
result = await self.db.database.from_("table").select("*").eq("col", val).execute()
rows = result if isinstance(result, list) else []

# Update (always return_representation=True)
await self.db.database.from_("table").eq("id", id).update(
    {"field": "value"}, return_representation=True
)

# Insert (when you need the created row back)
result = await self.db.database.from_("table").insert(
    [row_dict], return_representation=True
)
created = result[0] if result else row_dict
```

---

## 7. Current State (as of 2026-08-13)

### ✅ Working
- Sheet connection CRUD (create, list, delete, pause, resume)
- Celery Beat auto-polling every 60 seconds
- New lead detection from Google Sheet rows
- `sheet_leads` record inserted with correct UUID (after Bug 7 fix)
- Dograh outbound call triggered successfully
- `last_row_processed` and `last_polled_at` correctly updated
- `total_leads_found` incremented
- Dograh webhook node configured with correct ngrok URL
- Webhook endpoint `/api/v1/webhooks/dograh` receives and parses payload
- Frontend Integrations page renders connections, leads, callbacks tabs

### ⚠️ Not Yet Verified (Needs a Fresh Test)
- Post-call: `call_runs.status` → `completed` + `duration_seconds` populated
- Post-call: `total_leads_called` counter increments
- Google Sheet writeback — does `write_call_results` write back to the sheet cells?
- `check_callbacks` Celery task triggers callbacks on time

### ❌ Known Remaining Issues

**Issue 1 — 3 stuck "calling" leads from old broken sessions**  
Leads with `call_status = "calling"` that Dograh already called but our backend
never processed. Since Dograh only fires webhooks once, these will never auto-resolve.  
**Fix:** One-time script: query Dograh `GET /workflow/{id}/runs/{run_id}` for each
stuck lead → update DB to actual status.

**Issue 2 — No timeout for "calling" status**  
`_retry_pending_leads` only retries `pending` leads. If a lead gets stuck at `calling`
(e.g., Celery was down when webhook fired), it stays permanently stuck.  
**Fix:** Add logic: if `call_status = "calling"` for > 30 minutes → mark `failed`, retry.

**Issue 3 — `duration_seconds` may arrive as a string**  
Dograh webhook template sends `"{{cost_info.call_duration_seconds}}"` as a string.
If Pydantic can't coerce `"76"` to `int`, `duration_seconds` stays `None` → `0s` in UI.  
**Fix:** Add string→int coercion in `parse_stringified_json` model validator.

**Issue 4 — `needs_reauth` not shown in UI**  
When Google Sheets auth expires, `needs_reauth = true` is set in DB but the
Integrations page shows no warning.  
**Fix:** Add a "Reconnect" badge on connection cards where `needs_reauth = true`.

**Issue 5 — No guard against duplicate connections**  
Two active connections to the same sheet + agent will double-call every new row.  
**Fix:** Add unique constraint or backend check in `create_connection`.

---

## 8. How to Restart All Services

```bash
# Backend
cd "/path/to/backend" && source venv/bin/activate
python3 -m uvicorn app.main:app --reload --port 8000

# Frontend
cd "/path/to/frontend" && npm run dev

# ngrok (keep this URL in Dograh webhook config)
ngrok http --url=compacter-frigidity-everyone.ngrok-free.dev 8000

# Celery Worker
celery -A app.tasks.sheet_tasks:celery worker --loglevel=info --concurrency=2

# Celery Beat
celery -A app.tasks.sheet_tasks:celery beat --loglevel=info
```

> ⚠️ **After code changes**: Uvicorn auto-reloads. Celery **must be manually restarted**.

---

## 9. Resume Checklist (Next Session)

- [ ] Fix the 3 stuck "calling" leads with a one-time script
- [ ] Add a fresh lead to the sheet and verify full end-to-end (trigger → call → webhook → Call History updates)
- [ ] Add `duration_seconds` string→int coercion in `DograhWebhookPayload`
- [ ] Test Google Sheet writeback after call completion
- [ ] Add `needs_reauth` badge to Integrations UI
- [ ] Add duplicate connection guard in `create_connection`
- [ ] Add timeout mechanism for `call_status = "calling"` stuck leads

---

## 10. Dograh Webhook Node Config

**Agent:** `workflow_id = 9458`  
**Node ID:** `neuvon-webhook`  
**URL:** `https://compacter-frigidity-everyone.ngrok-free.dev/api/v1/webhooks/dograh`  
**Fields sent:** `workflow_run_id`, `workflow_id`, `status`, `call_duration_seconds`, `gathered_context`, `recording_url`, `transcript_url`, `initial_context`, `cost_info`, `annotations`

> ✅ The ngrok URL is a fixed subdomain (paid plan) — persists across ngrok restarts.

---

*End of context document.*
