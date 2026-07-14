from __future__ import annotations

from pydantic import BaseModel, Field


class AppointmentResponse(BaseModel):
    """Single appointment returned from API."""

    id: str
    organization_id: str
    call_run_id: str
    contact_name: str = ""
    contact_phone: str = ""
    appointment_date: str | None = None
    notes: str = ""
    status: str = "scheduled"
    created_at: str
    campaign_name: str | None = None


class AppointmentListResponse(BaseModel):
    """Paginated list of appointments."""

    appointments: list[AppointmentResponse] = Field(default_factory=list)
    total: int = 0


class AppointmentUpdateRequest(BaseModel):
    """Update fields for an existing appointment."""

    contact_name: str | None = None
    contact_phone: str | None = None
    appointment_date: str | None = Field(None, description="ISO datetime string")
    notes: str | None = None
    status: str | None = Field(None, description="scheduled|confirmed|cancelled|completed")


class AppointmentCreateRequest(BaseModel):
    """Manual appointment creation (not auto-extracted from call)."""

    call_run_id: str = Field(..., description="UUID of the associated call run")
    contact_name: str = Field(default="")
    contact_phone: str = Field(default="")
    appointment_date: str | None = Field(None, description="ISO datetime string")
    notes: str = Field(default="")
