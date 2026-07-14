from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class Campaign(SQLModel, table=True):
    """Local campaign metadata — mirrors Dograh campaign with org-scoping."""

    __tablename__ = "campaigns"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    dograh_campaign_id: int = Field(index=True)
    dograh_workflow_id: int = Field(index=True)
    name: str = Field(default="")
    status: str = Field(default="draft")  # "draft"|"running"|"paused"|"completed"|"failed"
    total_contacts: int = Field(default=0)
    contacts_processed: int = Field(default=0)
    concurrency: int = Field(default=1)
    retry_config: dict | None = Field(default=None, sa_column=sa.Column(sa.JSON, nullable=True))
    schedule_config: dict | None = Field(default=None, sa_column=sa.Column(sa.JSON, nullable=True))
    contact_list_id: str | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
