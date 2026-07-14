from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LiveCallUpdate(BaseModel):
    """Real-time call status update pushed via WebSocket."""

    type: str = "call_update"
    run_id: int
    workflow_id: int | None = None
    agent_name: str | None = None
    status: str
    phone_number: str | None = None
    caller_number: str | None = None
    duration_seconds: int = 0
    disposition_code: str | None = None
    campaign_id: int | None = None
    timestamp: str | None = None


class LiveCallHeartbeat(BaseModel):
    """Heartbeat message to keep WebSocket alive."""

    type: str = "heartbeat"
    timestamp: str
    active_calls: int = 0
