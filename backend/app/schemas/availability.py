from __future__ import annotations

from pydantic import BaseModel, Field


# ── Weekly Schedule ──────────────────────────────────────────────────────────

class WeeklySlot(BaseModel):
    """A single recurring availability slot (e.g., Monday 9am-5pm)."""

    day_of_week: int = Field(..., ge=0, le=6, description="0=Sunday, 6=Saturday")
    start_time: str = Field(..., description="HH:MM format, e.g. '09:00'")
    end_time: str = Field(..., description="HH:MM format, e.g. '17:00'")
    is_active: bool = True


class SetWeeklyScheduleRequest(BaseModel):
    """Bulk set weekly recurring availability slots."""

    slots: list[WeeklySlot] = Field(default_factory=list)


class WeeklySlotResponse(BaseModel):
    """Single slot returned from API."""

    id: str
    day_of_week: int
    start_time: str
    end_time: str
    is_active: bool


class WeeklyScheduleResponse(BaseModel):
    """Full weekly schedule for a user."""

    user_id: str
    slots: list[WeeklySlotResponse] = Field(default_factory=list)


# ── Date Overrides ───────────────────────────────────────────────────────────

class AvailabilityOverrideRequest(BaseModel):
    """Create a date-specific availability override."""

    override_date: str = Field(..., description="YYYY-MM-DD")
    is_available: bool = Field(
        False,
        description="False = block entire day, True = add extra hours",
    )
    start_time: str | None = Field(None, description="HH:MM (required when is_available=True)")
    end_time: str | None = Field(None, description="HH:MM (required when is_available=True)")
    reason: str = ""


class AvailabilityOverrideResponse(BaseModel):
    """Single override returned from API."""

    id: str
    override_date: str
    is_available: bool
    start_time: str | None = None
    end_time: str | None = None
    reason: str = ""
    created_at: str


class OverrideListResponse(BaseModel):
    """List of overrides."""

    overrides: list[AvailabilityOverrideResponse] = Field(default_factory=list)
    total: int = 0


# ── Availability Check (Public — called by Dograh Tool) ─────────────────────

class AvailableSlot(BaseModel):
    """A single available time window."""

    user_id: str
    user_name: str
    start_time: str  # "09:00"
    end_time: str    # "17:00"


class AvailabilityCheckResponse(BaseModel):
    """Response for the public availability check endpoint.

    The 'message' field is a human-readable summary that the
    Dograh AI agent can read back to the caller.
    """

    date: str
    available_slots: list[AvailableSlot] = Field(default_factory=list)
    message: str = ""
