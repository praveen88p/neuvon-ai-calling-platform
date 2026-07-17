from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


E164_PATTERN = re.compile(r"^\+[1-9]\d{6,14}$")


class CallTrigger(BaseModel):
    """Input schema for triggering an outbound call."""

    workflow_id: int = Field(..., description="Dograh workflow ID of the agent")
    phone_number: str = Field(..., description="Phone number in E.164 format")
    initial_context: dict | None = Field(
        None, description="Template variables for agent prompt"
    )
    telephony_configuration_id: int | None = Field(
        None, description="Override default telephony config"
    )

    @field_validator("phone_number")
    @classmethod
    def validate_e164(cls, v: str) -> str:
        """Ensure phone number is in E.164 format."""
        if not E164_PATTERN.match(v):
            msg = "Phone number must be in E.164 format (e.g. +14155550100)"
            raise ValueError(msg)
        return v


class CallTriggerResponse(BaseModel):
    """Response from triggering an outbound call."""

    run_id: int
    workflow_run_name: str | None = None
    status: str
    phone_number: str
    workflow_id: int
    organization_id: str


class CallRunResponse(BaseModel):
    """Full call run details."""

    run_id: int
    workflow_id: int
    organization_id: str
    name: str | None = None
    status: str | None = None
    is_completed: bool = False
    call_type: str | None = None
    phone_number: str | None = None
    caller_number: str | None = None
    duration_seconds: int | None = None
    initial_context: dict | None = None
    gathered_context: dict | None = None
    transcript_url: str | None = None
    recording_url: str | None = None
    transcript_public_url: str | None = None
    recording_public_url: str | None = None
    public_access_token: str | None = None
    cost_info: dict | None = None
    annotations: dict | None = None
    created_at: str | None = None


# --- Call History (Feature 09) ---


class CallHistoryItem(BaseModel):
    """Single call run in the paginated history list."""

    run_id: int
    workflow_id: int | None = None
    workflow_name: str | None = None
    campaign_id: str | None = None
    campaign_name: str | None = None
    call_type: str | None = None
    status: str | None = None
    disposition_code: str | None = None
    phone_number: str | None = None
    caller_number: str | None = None
    duration_seconds: int | None = None
    cost: float | None = None
    recording_url: str | None = None
    transcript_url: str | None = None
    public_access_token: str | None = None
    created_at: str | None = None
    completed_at: str | None = None


class CallHistoryResponse(BaseModel):
    """Paginated call history response."""

    runs: list[CallHistoryItem]
    total: int
    page: int
    limit: int
    has_more: bool


class DownloadUrlResponse(BaseModel):
    """Response with a download URL for recordings/transcripts."""

    url: str
    run_id: int
    type: str  # "recording" or "transcript"

