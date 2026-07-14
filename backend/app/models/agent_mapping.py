from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class DograhAgentMapping(SQLModel, table=True):
    """Maps Dograh workflows to organizations for multi-tenant agent visibility."""

    __tablename__ = "dograh_agent_mappings"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    dograh_workflow_id: int = Field(index=True)
    dograh_workflow_uuid: str = Field(default="")
    agent_name: str = Field(default="")
    agent_status: str = Field(default="active")  # "active" | "archived"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
