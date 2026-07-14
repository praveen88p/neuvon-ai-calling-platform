from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class Appointment(SQLModel, table=True):
    """Appointment booked by an AI call — extracted from gathered_context."""

    __tablename__ = "appointments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    call_run_id: UUID = Field(foreign_key="call_runs.id", index=True)
    contact_name: str = Field(default="")
    contact_phone: str = Field(default="")  # E.164
    appointment_date: datetime | None = Field(default=None)
    notes: str = Field(default="")
    status: str = Field(default="scheduled")  # "scheduled"|"confirmed"|"cancelled"|"completed"
    created_at: datetime = Field(default_factory=datetime.utcnow)
