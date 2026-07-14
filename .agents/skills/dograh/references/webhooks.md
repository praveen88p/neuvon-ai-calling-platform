# Webhooks

Webhook nodes fire after a call completes, sending the run data to your endpoint. Use them to sync results to your CRM, trigger downstream workflows in n8n or Zapier, or store transcripts.

## How it works

1. A call completes (or a run finishes)
2. Dograh executes any `webhook` nodes in the workflow asynchronously
3. The payload template is rendered with the run's context variables
4. Dograh sends the request to your endpoint

## Payload template variables

Use double-brace syntax in your `payload_template`:

| Variable | Type | Description |
|---|---|---|
| `{{workflow_run_id}}` | integer | ID of the completed run |
| `{{workflow_run_name}}` | string | Name of the run |
| `{{workflow_id}}` | integer | ID of the workflow |
| `{{workflow_name}}` | string | Name of the workflow |
| `{{initial_context.*}}` | object | Context passed when the call was initiated |
| `{{gathered_context.*}}` | object | Data extracted during the call |
| `{{cost_info.*}}` | object | Call cost breakdown |
| `{{annotations.*}}` | object | QA analysis results (if qa node configured) |
| `{{recording_url}}` | string/null | Download URL for the call recording |
| `{{transcript_url}}` | string/null | Download URL for the call transcript |

### Example payload template

```json
{
  "run_id": "{{workflow_run_id}}",
  "customer": "{{initial_context.customer_name}}",
  "outcome": "{{gathered_context.resolution}}",
  "recording": "{{recording_url}}",
  "duration": "{{cost_info.call_duration_seconds}}"
}
```

## Webhook authentication methods

| Type | Description |
|---|---|
| `NONE` | No authentication |
| `API_KEY` | Sends the key in a custom header (e.g. `X-API-Key`) |
| `BEARER_TOKEN` | Sends `Authorization: Bearer <token>` |
| `BASIC_AUTH` | HTTP Basic authentication (username + password) |
| `CUSTOM_HEADER` | Any custom header key-value pair |

## Webhook node in a workflow definition

```json
{
  "id": "webhook-1",
  "type": "webhook",
  "position": { "x": 600, "y": 0 },
  "data": {
    "name": "Notify CRM",
    "enabled": true,
    "http_method": "POST",
    "endpoint_url": "https://your-service.com/webhook/dograh",
    "payload_template": {
      "run_id": "{{workflow_run_id}}",
      "customer": "{{initial_context.customer_name}}",
      "outcome": "{{gathered_context.resolution}}"
    }
  }
}
```

## Receiving webhooks

Your endpoint should:

- Accept `POST` requests with `Content-Type: application/json`
- Respond with a `2xx` status code within 30 seconds
- Handle duplicate deliveries idempotently (retries may send the same payload more than once)

### Python receiver example

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhook/dograh")
async def handle_dograh_webhook(request: Request):
    payload = await request.json()
    run_id = payload.get("run_id")
    outcome = payload.get("outcome")
    # process the call result...
    return {"status": "ok"}
```

### Node.js receiver example

```javascript
const express = require("express");
const app = express();
app.use(express.json());

app.post("/webhook/dograh", (req, res) => {
  const { run_id, outcome, recording } = req.body;
  // process the call result...
  res.json({ status: "ok" });
});

app.listen(3000);
```

## Multiple webhooks

You can have multiple webhook nodes in a single workflow to sync results to different systems (e.g. one to your CRM, another to a Slack notification).
