# Inbound Calls

Inbound calls let callers reach your Dograh agent by dialing a phone number. Your telephony provider routes the call to Dograh via a webhook, and the agent handles the conversation automatically.

## How it works

1. A caller dials your configured phone number
2. Your telephony provider sends a webhook to Dograh
3. Dograh activates the configured voice agent workflow
4. Real-time audio streams between the caller and agent via WebSocket
5. When the call ends, a run record is created with the transcript, recording, and gathered context

## Webhook URL

Configure your telephony provider to send inbound call webhooks to:

```
POST https://api.dograh.com/api/v1/telephony/inbound/{workflow_id}
```

- `workflow_id` is the numeric ID of the agent that should handle the call
- Find it in the dashboard URL: `app.dograh.com/workflow/3` means workflow_id is `3`
- For self-hosted instances, replace `api.dograh.com` with your own domain

## Provider setup

Each telephony provider requires specific configuration to route calls to Dograh.

### Twilio

In the Twilio console, set the webhook URL on your phone number:

1. Go to **Phone Numbers > Manage > Active Numbers**
2. Select your number
3. Under **Voice Configuration**, set the webhook URL to your Dograh inbound endpoint
4. Set the HTTP method to `POST`

### Cloudonix

Configure a SIP trunk to forward calls to your Dograh inbound webhook URL.

### Vobiz

Set the inbound webhook URL in your Vobiz dashboard under the number configuration.

### Asterisk ARI

Configure your Asterisk dialplan to route calls to Dograh via the ARI interface.

## Prerequisites

- A telephony provider configured in Dograh (same configuration used for outbound)
- A phone number purchased from your provider
- The phone number's webhook pointed at the Dograh inbound endpoint
- A workflow (agent) to handle the call

## Supported providers

| Provider | Inbound support |
|---|---|
| Twilio | Supported |
| Cloudonix | Supported |
| Vobiz | Supported |
| Asterisk ARI | Supported |
| Vonage | Coming soon |

## Troubleshooting

| Problem | Solution |
|---|---|
| Calls go to voicemail | Verify webhook URL is correct and publicly accessible |
| Agent doesn't respond | Check workflow ID exists and workflow is active |
| Provider mismatch error | Ensure phone number provider matches Dograh telephony config |
| Signature validation failed | Verify auth tokens match between provider and Dograh |
| Quota exceeded | Check account limits or upgrade plan |
