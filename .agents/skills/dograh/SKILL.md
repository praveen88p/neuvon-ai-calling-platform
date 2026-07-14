---
name: dograh
description: Build voice AI agents, trigger outbound calls, handle inbound calls, run bulk campaigns, and process call results via webhooks using the Dograh REST API
tags:
  - dograh
  - voice-ai
  - telephony
  - agents
  - api
  - outbound-calls
  - inbound-calls
  - campaigns
  - webhooks
---

# Dograh

Dograh is an open-source voice AI platform. You define conversation flows (called workflows), connect a telephony provider, and Dograh handles STT, LLM, TTS, and call orchestration.

## When to apply

Use this skill when the developer is:

- Triggering outbound voice calls via the Dograh API
- Routing inbound calls to a Dograh agent
- Creating or updating voice agents (workflows) programmatically
- Running bulk outbound campaigns against a contact list
- Processing call results via webhooks
- Working with Dograh's workflow definition schema (nodes, edges, transitions)
- Integrating Dograh with external systems (CRMs, n8n, Zapier, etc.)

## Key concepts

- **Workflow** = an agent. The API uses `workflow`; the dashboard says "agent". They are the same thing.
- **Run** = one execution of a workflow (one call). Contains transcript, recording, gathered data, and cost.
- **initial_context** = data passed into a call at trigger time. Available in prompts as `{{variable_name}}` template variables.
- **gathered_context** = structured data extracted by the agent during a call. Returned in the run record and webhook payloads.

## API basics

**Base URL:**
- Hosted: `https://api.dograh.com/api/v1`
- Self-hosted: `https://your-instance/api/v1`

**Authentication:** pass the API key in the `X-API-Key` header on every request.

```bash
curl https://api.dograh.com/api/v1/workflow/fetch \
  -H "X-API-Key: dg_your_api_key"
```

All request bodies must be JSON with `Content-Type: application/json`.

## Common tasks

### Trigger an outbound call

> See [Triggering Outbound Calls](references/triggering-outbound-calls.md) for full details, examples, and error handling.

```bash
curl -X POST https://api.dograh.com/api/v1/public/agent/{uuid} \
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

### Handle inbound calls

> See [Inbound Calls](references/inbound-calls.md) for provider setup and troubleshooting.

Configure your telephony provider to route incoming calls to:

```
POST https://api.dograh.com/api/v1/telephony/inbound/{workflow_id}
```

The `workflow_id` is the numeric ID of the agent that should handle the call (visible in the dashboard URL, e.g. `app.dograh.com/workflow/3` means workflow_id is `3`).

### Create an agent from a workflow definition

> See [Workflow Schema](references/workflow-schema.md) for the full node/edge reference.

```bash
curl -X POST https://api.dograh.com/api/v1/workflow/create/definition \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dg_your_api_key" \
  -d '{
    "name": "Appointment Reminder",
    "workflow_definition": {
      "nodes": [...],
      "edges": [...]
    }
  }'
```

### Run a bulk campaign

> See [Campaigns](references/campaigns.md) for CSV format, scheduling, retries, and circuit breaker details.

Upload contacts, create a campaign linked to a workflow, then start it. Dograh dials contacts respecting concurrency limits and time slots.

### Process call results via webhooks

> See [Webhooks](references/webhooks.md) for payload variables, auth methods, and receiver examples.

Add a `webhook` node to your workflow. When a call completes, Dograh sends a POST with the run data (transcript, recording, gathered context) to your endpoint.
