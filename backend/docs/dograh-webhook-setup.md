# Dograh Webhook Setup Guide

## Overview

Dograh must send a POST request to our backend after every call completes.
This ensures local `call_runs` records are created with proper `organization_id`,
enabling analytics, billing, and call detail pages to work correctly.

## Webhook Endpoint

```
POST https://<your-backend-url>/api/v1/webhooks/dograh
```

For **local development**, use ngrok to expose your backend:
```bash
ngrok http 8000
```
This gives you a public URL like `https://abc123.ngrok-free.app`.
Your webhook URL becomes: `https://abc123.ngrok-free.app/api/v1/webhooks/dograh`

## Payload Template

Add a **Webhook Node** to your Dograh Voice Agent workflow with this payload template:

```json
{
  "workflow_run_id": "{{workflow_run_id}}",
  "workflow_id": "{{workflow_id}}",
  "workflow_name": "{{workflow_name}}",
  "status": "completed",
  "call_type": "outbound",
  "phone_number": "{{initial_context.phone_number}}",
  "caller_number": "{{initial_context.caller_number}}",
  "call_duration_seconds": "{{cost_info.call_duration_seconds}}",
  "disposition": "{{gathered_context.mapped_call_disposition}}",
  "recording_url": "{{recording_url}}",
  "transcript_url": "{{transcript_url}}",
  "initial_context": "{{initial_context}}",
  "gathered_context": "{{gathered_context}}",
  "cost_info": "{{cost_info}}",
  "annotations": "{{annotations}}",
  "campaign_id": "{{initial_context.campaign_id}}"
}
```

## Authentication

Set webhook authentication to one of:
- **API_KEY**: Use `WEBHOOK_SECRET` from your `.env` file, sent as `x-webhook-signature` header
- **NONE**: For local development (signature verification is skipped when `WEBHOOK_SECRET` is a placeholder)

## How to Add the Webhook Node in Dograh Dashboard

1. Go to **Voice Agents** → Click your agent → **Edit Workflow**
2. Add a new **Webhook** node
3. Set:
   - **HTTP Method**: `POST`
   - **Endpoint URL**: Your backend webhook URL
   - **Payload Template**: The JSON above
   - **Authentication**: As configured above
4. Connect the webhook node to fire after the conversation ends
5. **Save/Publish** the agent

## What Happens When a Webhook Fires

1. Dograh sends POST with call data to our endpoint
2. Backend validates signature (if configured)
3. Backend checks if a local `call_runs` record exists (dedup via `dograh_run_id`)
4. If exists: updates with new data (transcript, recording, disposition)
5. If not exists: resolves `organization_id` from `workflow_id` via agent mappings, creates new record
6. Publishes live call update via WebSocket
7. Fires PostHog analytics event
8. Extracts appointment data from gathered_context (if present)

## Verification

After setup, trigger a test call. You should see in your backend logs:
```
webhook.processed  run_id=123456  org_id=<your-org-id>  status=completed
```

Then check the dashboard — KPIs, call history, and campaign details should all populate.
