# Workflow Definition Schema

A workflow definition is the JSON structure that defines a voice agent's conversation flow. It contains `nodes` (conversation steps) and `edges` (transitions between steps).

## Structure

```json
{
  "nodes": [...],
  "edges": [...]
}
```

## Creating an agent from a definition

```bash
curl -X POST https://api.dograh.com/api/v1/workflow/create/definition \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dg_your_api_key" \
  -d '{
    "name": "My Agent",
    "workflow_definition": {
      "nodes": [...],
      "edges": [...]
    }
  }'
```

## Nodes

Each node represents a step in the conversation.

```json
{
  "id": "uuid-string",
  "type": "agentNode",
  "position": { "x": 100, "y": 200 },
  "data": { ... }
}
```

### Node types

| Type | Description |
|---|---|
| `startCall` | Entry point for telephony calls |
| `endCall` | Terminates the call |
| `agentNode` | LLM-powered conversation step — the core building block |
| `globalNode` | Instructions that apply across all agent nodes (tone, language, fallbacks) |
| `trigger` | Entry point for API-triggered outbound calls |
| `webhook` | Sends an HTTP request when reached |
| `qa` | Runs quality analysis on the completed call |

### Common data fields (all node types)

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | string | required | Display name |
| `prompt` | string | required* | LLM system prompt (*not required for trigger, webhook, qa) |
| `allow_interrupt` | boolean | `false` | Allow caller to interrupt agent mid-speech |
| `wait_for_user_response` | boolean | `false` | Pause and wait for caller input |
| `wait_for_user_response_timeout` | number | `null` | Seconds to wait before timing out |
| `detect_voicemail` | boolean | `false` | Detect and handle voicemail on outbound calls |
| `add_global_prompt` | boolean | `true` | Merge the globalNode prompt into this node's prompt |

### agentNode — data extraction

Extract structured data from the conversation:

| Field | Type | Default | Description |
|---|---|---|---|
| `extraction_enabled` | boolean | `false` | Enable extraction |
| `extraction_prompt` | string | `null` | Custom prompt to guide extraction |
| `extraction_variables` | array | `[]` | Variables to extract |

Extraction variable format:

```json
{
  "name": "customer_intent",
  "type": "string",
  "prompt": "What did the customer want to achieve?"
}
```

`type` is one of `string`, `number`, or `boolean`.

### agentNode — tools

| Field | Type | Description |
|---|---|---|
| `tool_uuids` | string[] | IDs of tools (HTTP API, call transfer, etc.) to attach |
| `document_uuids` | string[] | IDs of knowledge base documents available to this node |

### trigger node

| Field | Type | Description |
|---|---|---|
| `trigger_path` | string | Unique UUID that becomes the API trigger endpoint path |

### webhook node

| Field | Type | Default | Description |
|---|---|---|---|
| `enabled` | boolean | `true` | Whether the webhook fires when reached |
| `http_method` | string | — | `GET`, `POST`, `PUT`, `PATCH`, or `DELETE` |
| `endpoint_url` | string | — | Target URL |
| `credential_uuid` | string | `null` | UUID of a stored auth credential |
| `custom_headers` | array | `[]` | Additional headers `[{"key": "...", "value": "..."}]` |
| `payload_template` | object | `null` | Request body template (supports template variables) |

### qa node

| Field | Type | Default | Description |
|---|---|---|---|
| `qa_enabled` | boolean | `true` | Enable QA analysis |
| `qa_system_prompt` | string | `null` | Custom evaluation prompt |
| `qa_model` | string | `null` | LLM model for evaluation |
| `qa_min_call_duration` | integer | `15` | Minimum call duration (seconds) to run QA |
| `qa_voicemail_calls` | boolean | `false` | Include voicemail calls in QA |
| `qa_sample_rate` | integer | `100` | Percentage of calls to analyse (1–100) |

## Edges

Each edge connects two nodes and defines when the transition fires.

```json
{
  "id": "edge-uuid",
  "source": "node-uuid-a",
  "target": "node-uuid-b",
  "data": {
    "label": "Customer confirms",
    "condition": "The customer has confirmed their appointment",
    "transition_speech": "Great, I've got that noted."
  }
}
```

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique edge ID |
| `source` | string | ID of the originating node |
| `target` | string | ID of the destination node |
| `data.label` | string | Short label shown in the workflow builder |
| `data.condition` | string | Natural language condition the LLM evaluates to trigger this edge |
| `data.transition_speech` | string | Optional speech the agent says before transitioning |

## Validation rules

- All `source` and `target` IDs in edges must reference existing node IDs
- All nodes except `trigger`, `webhook`, and `qa` must have a non-empty `prompt`
- Node IDs must be unique within the workflow
- Each workflow must have exactly one `startCall` or `trigger` node as the entry point

## Minimal example

```json
{
  "nodes": [
    {
      "id": "start-1",
      "type": "startCall",
      "position": { "x": 0, "y": 0 },
      "data": {
        "name": "Start",
        "prompt": "You are a friendly assistant. Greet the caller and ask how you can help."
      }
    },
    {
      "id": "end-1",
      "type": "endCall",
      "position": { "x": 400, "y": 0 },
      "data": {
        "name": "End",
        "prompt": "Thank the caller and say goodbye."
      }
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "source": "start-1",
      "target": "end-1",
      "data": {
        "label": "Done",
        "condition": "The caller's question has been answered and they want to end the call"
      }
    }
  ]
}
```

## Multi-node example with extraction

```json
{
  "nodes": [
    {
      "id": "start-1",
      "type": "startCall",
      "position": { "x": 0, "y": 0 },
      "data": {
        "name": "Greeting",
        "prompt": "You are calling {{customer_name}} about their {{plan}} plan renewal on {{renewal_date}}. Greet them warmly and ask if they'd like to renew.",
        "allow_interrupt": true
      }
    },
    {
      "id": "agent-1",
      "type": "agentNode",
      "position": { "x": 400, "y": 0 },
      "data": {
        "name": "Handle Objections",
        "prompt": "The customer has concerns. Address their questions about the plan. Be helpful and patient.",
        "allow_interrupt": true,
        "extraction_enabled": true,
        "extraction_variables": [
          {
            "name": "renewal_confirmed",
            "type": "boolean",
            "prompt": "Did the customer confirm they want to renew?"
          },
          {
            "name": "objection_reason",
            "type": "string",
            "prompt": "If the customer declined, what was their reason?"
          }
        ]
      }
    },
    {
      "id": "end-1",
      "type": "endCall",
      "position": { "x": 800, "y": 0 },
      "data": {
        "name": "End",
        "prompt": "Thank the customer for their time and say goodbye."
      }
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "source": "start-1",
      "target": "agent-1",
      "data": {
        "label": "Has concerns",
        "condition": "The customer has questions or concerns about renewing"
      }
    },
    {
      "id": "edge-2",
      "source": "start-1",
      "target": "end-1",
      "data": {
        "label": "Confirms immediately",
        "condition": "The customer confirms they want to renew without any concerns",
        "transition_speech": "Wonderful, your renewal is confirmed."
      }
    },
    {
      "id": "edge-3",
      "source": "agent-1",
      "target": "end-1",
      "data": {
        "label": "Resolved",
        "condition": "The customer's concerns have been addressed or they want to end the call"
      }
    }
  ]
}
```

## API endpoints for workflows

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/workflow/create/definition` | Create from a definition |
| `POST` | `/workflow/create/template` | Create from a natural language template |
| `GET` | `/workflow/fetch` | List all agents |
| `GET` | `/workflow/fetch/{workflow_id}` | Get a specific agent |
| `PUT` | `/workflow/{workflow_id}` | Update an agent |
| `PUT` | `/workflow/{workflow_id}/status` | Archive an agent |
| `POST` | `/workflow/{workflow_id}/validate` | Validate a workflow definition |
