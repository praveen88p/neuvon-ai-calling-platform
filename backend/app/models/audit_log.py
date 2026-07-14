from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    """Audit trail — every state-changing operation creates an entry."""

    __tablename__ = "audit_log"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    action: str = Field(index=True)  # "call_triggered"|"campaign_started"|"member_invited"|etc.
    resource_type: str = Field(default="")  # "call"|"campaign"|"agent"|"member"|"telephony"
    resource_id: str = Field(default="")
    metadata_: dict | None = Field(default=None, sa_column=sa.Column("metadata", sa.JSON, nullable=True))
    ip_address: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
