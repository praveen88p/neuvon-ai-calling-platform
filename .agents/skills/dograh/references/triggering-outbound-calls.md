# Triggering Outbound Calls

## Endpoint

```
POST /api/v1/public/agent/{uuid}
```

The `{uuid}` is the trigger UUID assigned when you add an API Trigger node to your workflow. Find it in the dashboard URL when viewing the agent, or in the trigger node settings.

## Authentication

Pass your API key in the `X-API-Key` header. Create keys in the dashboard under **Settings > API Keys**.

## Request

```bash
curl -X POST https://api.dograh.com/api/v1/public/agent/abc123-uuid \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dg_your_api_key" \
  -d '{
    "phone_number": "+14155550100",
    "initial_context": {
      "customer_name": "Jane",
      "appointment_date": "March 15"
    }
  }'
```

### Request body

| Field | Type | Required | Description |
|---|---|---|---|
| `phone_number` | string | Yes | Phone number to call (include country code) |
| `initial_context` | object | No | Key-value data available in the agent's prompt as template variables |

### initial_context and template variables

Values passed in `initial_context` are available in your agent's prompt using double-brace syntax:

```
You are calling {{customer_name}} about their appointment on {{appointment_date}}.
```

Nested values are supported:

```json
{
  "initial_context": {
    "user": { "name": "John", "plan": "premium" }
  }
}
```

Referenced as `{{initial_context.user.name}}` in prompts.

## Response

### Success (200)

```json
{
  "status": "initiated",
  "workflow_run_id": 12345,
  "workflow_run_name": "WR-API-7823"
}
```

Use `workflow_run_id` to retrieve call details, recordings, and transcripts:

```bash
curl https://api.dograh.com/api/v1/workflow/{workflow_id}/runs/{workflow_run_id} \
  -H "X-API-Key: dg_your_api_key"
```

### Errors

| Status | Cause |
|---|---|
| `400` | Telephony provider not configured, or call failed to initiate |
| `401` | Missing or invalid API key |
| `402` | Account quota exceeded |
| `403` | API key does not have access to this agent |
| `404` | Trigger not found, not active, or workflow has been removed |

## Prerequisites

- A configured telephony provider (Twilio, Vonage, etc.) — outbound calls fail without one
- An active API Trigger node in the workflow
- A valid API key belonging to the same organization as the agent

## Python example

```python
import requests

response = requests.post(
    "https://api.dograh.com/api/v1/public/agent/abc123-uuid",
    headers={
        "Content-Type": "application/json",
        "X-API-Key": "dg_your_api_key",
    },
    json={
        "phone_number": "+14155550100",
        "initial_context": {
            "customer_name": "Jane",
            "appointment_date": "March 15",
        },
    },
)

data = response.json()
print(f"Call initiated — run ID: {data['workflow_run_id']}")
```

## Node.js example

```javascript
const response = await fetch(
  "https://api.dograh.com/api/v1/public/agent/abc123-uuid",
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": "dg_your_api_key",
    },
    body: JSON.stringify({
      phone_number: "+14155550100",
      initial_context: {
        customer_name: "Jane",
        appointment_date: "March 15",
      },
    }),
  }
);

const data = await response.json();
console.log(`Call initiated — run ID: ${data.workflow_run_id}`);
```
