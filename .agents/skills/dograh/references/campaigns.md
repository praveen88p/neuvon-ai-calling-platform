# Campaigns (Bulk Outbound Calls)

A campaign runs a workflow against a list of contacts automatically. Instead of triggering calls one by one, you upload a CSV and Dograh dials them for you — respecting scheduling windows, concurrency limits, and retry rules.

## How it works

1. Upload a contacts CSV
2. Create a campaign linked to a workflow
3. Start the campaign
4. Dograh dials contacts up to your concurrency limit
5. Monitor progress, pause/resume as needed

## Contacts CSV format

The CSV must have a `phone_number` column. Any extra columns automatically become `initial_context` for each call, making them available as template variables in your agent's prompt.

```csv
phone_number,customer_name,account_id,plan
+14155550100,Jane Smith,acc_001,premium
+14155550101,Bob Jones,acc_002,basic
```

With this CSV, each call's agent prompt can reference `{{customer_name}}`, `{{account_id}}`, and `{{plan}}`.

## API workflow

### 1. Upload contacts

```bash
curl -X POST https://api.dograh.com/api/v1/campaign/upload \
  -H "X-API-Key: dg_your_api_key" \
  -F "file=@contacts.csv"
```

### 2. Create the campaign

```bash
curl -X POST https://api.dograh.com/api/v1/campaign/create \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dg_your_api_key" \
  -d '{
    "name": "Renewal Reminders — April",
    "workflow_id": 3,
    "contact_list_id": "from-upload-response",
    "concurrency": 5,
    "retry_config": {
      "max_attempts": 3,
      "retry_interval_minutes": 60
    }
  }'
```

### 3. Start the campaign

```bash
curl -X POST https://api.dograh.com/api/v1/campaign/{campaign_id}/start \
  -H "X-API-Key: dg_your_api_key"
```

## Scheduling and time slots

Restrict when Dograh is allowed to dial — useful for business hours or regulatory compliance:

```json
{
  "timezone": "America/New_York",
  "time_slots": [
    { "day": "monday", "start": "09:00", "end": "17:00" },
    { "day": "tuesday", "start": "09:00", "end": "17:00" }
  ]
}
```

If no time slots are set, Dograh dials continuously once the campaign is started.

## Retry behaviour

Automatically retry contacts who didn't answer, were busy, or went to voicemail:

```json
{
  "retry_config": {
    "max_attempts": 3,
    "retry_interval_minutes": 60
  }
}
```

## Circuit breaker

Automatically pauses a campaign when the failure rate gets too high — protects against wasted spend and telephony reputation issues.

| Setting | Default | Description |
|---|---|---|
| Failure Threshold (%) | `50` | Pause when failure rate exceeds this |
| Window (seconds) | `120` | Rolling time window for failure rate calculation |
| Min Calls in Window | `5` | Minimum calls before circuit breaker can trip |

A campaign paused by the circuit breaker must be manually resumed after investigation.

## Campaign lifecycle

| Status | Meaning |
|---|---|
| `draft` | Created but not started |
| `running` | Actively dialing |
| `paused` | Stopped; resumes where it left off |
| `completed` | All contacts processed |
| `failed` | Fatal error encountered |

You can pause and resume at any time. In-flight calls complete normally before a pause takes effect.

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/campaign/upload` | Upload contacts CSV |
| `POST` | `/campaign/create` | Create a campaign |
| `GET` | `/campaign/fetch` | List campaigns |
| `GET` | `/campaign/fetch/{campaign_id}` | Get a campaign |
| `PUT` | `/campaign/{campaign_id}` | Update a campaign |
| `POST` | `/campaign/{campaign_id}/start` | Start dialing |
| `POST` | `/campaign/{campaign_id}/pause` | Pause dialing |
| `POST` | `/campaign/{campaign_id}/resume` | Resume dialing |
| `GET` | `/campaign/{campaign_id}/progress` | Get progress stats |
| `GET` | `/campaign/{campaign_id}/runs` | Get run records for all contacts |
