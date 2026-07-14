from __future__ import annotations

import json
from pydantic import BaseModel, Field, model_validator


class DograhWebhookPayload(BaseModel):
    """Incoming webhook payload from Dograh after call completion.

    The webhook node in a Dograh workflow sends structured call data
    to our endpoint. Fields are flexible since users can configure
    what variables are included in the webhook body.
    """

    run_id: int | None = Field(None, alias="workflow_run_id")
    workflow_id: int | None = None
    workflow_name: str | None = None
    status: str | None = None
    call_type: str | None = None
    phone_number: str | None = None
    caller_number: str | None = None
    duration_seconds: int | None = Field(None, alias="call_duration_seconds")
    transcript_url: str | None = None
    recording_url: str | None = None
    transcript_public_url: str | None = None
    recording_public_url: str | None = None
    public_access_token: str | None = None
    initial_context: dict | None = None
    gathered_context: dict | None = None
    cost_info: dict | None = None
    annotations: dict | None = None
    disposition: str | None = None
    campaign_id: int | None = None

    model_config = {"populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def parse_stringified_json(cls, data: any) -> any:
        if not isinstance(data, dict):
            return data

        # Dograh's webhook templating engine stringifies nested objects
        # e.g., "{{initial_context}}" becomes '{"foo": "bar"}' instead of {"foo": "bar"}
        dict_fields = ["initial_context", "gathered_context", "cost_info", "annotations"]
        for field in dict_fields:
            val = data.get(field)
            if isinstance(val, str) and val.strip():
                try:
                    data[field] = json.loads(val)
                except json.JSONDecodeError:
                    data[field] = {}

        # Convert empty strings to None for integer fields
        int_fields = ["workflow_run_id", "workflow_id", "call_duration_seconds", "campaign_id"]
        for field in int_fields:
            val = data.get(field)
            if val == "":
                data[field] = None
                
        return data


class WebhookAckResponse(BaseModel):
    """Acknowledge webhook receipt."""

    status: str = "ok"
    run_id: int | None = None
    message: str = "Webhook processed"
