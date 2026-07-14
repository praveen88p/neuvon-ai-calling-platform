from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class CallRun(SQLModel, table=True):
    """Local copy of Dograh run data — enriched with org context and billing."""

    __tablename__ = "call_runs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    dograh_run_id: int = Field(index=True, unique=True)
    dograh_workflow_id: int = Field(index=True)
    campaign_id: UUID | None = Field(default=None, foreign_key="campaigns.id", index=True)
    call_type: str = Field(default="outbound")  # "outbound" | "inbound"
    status: str = Field(default="initiated")
    phone_number: str = Field(default="")  # E.164 — called number
    caller_number: str = Field(default="")  # E.164 — from number
    duration_seconds: int = Field(default=0)
    initial_context: dict | None = Field(default=None, sa_column=sa.Column(sa.JSON, nullable=True))
    gathered_context: dict | None = Field(default=None, sa_column=sa.Column(sa.JSON, nullable=True))
    transcript_url: str | None = Field(default=None)
    recording_url: str | None = Field(default=None)
    public_access_token: str | None = Field(default=None)
    cost_info: dict | None = Field(default=None, sa_column=sa.Column(sa.JSON, nullable=True))
    annotations: dict | None = Field(default=None, sa_column=sa.Column(sa.JSON, nullable=True))
    disposition: str | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
