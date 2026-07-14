from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.core.dependencies import CurrentUserDep
from app.schemas.availability import (
    AvailabilityCheckResponse,
    AvailabilityOverrideRequest,
    AvailabilityOverrideResponse,
    OverrideListResponse,
    SetWeeklyScheduleRequest,
    WeeklyScheduleResponse,
)
from app.services.availability_service import AvailabilityService

router = APIRouter(prefix="/availability", tags=["availability"])


# ── Weekly Schedule (Authenticated) ─────────────────────────────────────────

@router.get("/schedule", response_model=WeeklyScheduleResponse)
async def get_weekly_schedule(
    current_user: CurrentUserDep,
) -> WeeklyScheduleResponse:
    """Get the current user's weekly recurring availability schedule."""
    service = AvailabilityService()
    return await service.get_weekly_schedule(current_user)


@router.put("/schedule", response_model=WeeklyScheduleResponse)
async def set_weekly_schedule(
    data: SetWeeklyScheduleRequest,
    current_user: CurrentUserDep,
) -> WeeklyScheduleResponse:
    """Bulk set the user's weekly recurring schedule.

    Replaces all existing slots with the provided list.
    """
    service = AvailabilityService()
    return await service.set_weekly_schedule(data, current_user)


# ── Date Overrides (Authenticated) ──────────────────────────────────────────

@router.post("/overrides", response_model=AvailabilityOverrideResponse)
async def add_override(
    data: AvailabilityOverrideRequest,
    current_user: CurrentUserDep,
) -> AvailabilityOverrideResponse:
    """Add a date-specific availability override (block a day or add extra hours)."""
    service = AvailabilityService()
    return await service.add_override(data, current_user)


@router.get("/overrides", response_model=OverrideListResponse)
async def list_overrides(
    current_user: CurrentUserDep,
    from_date: str | None = Query(None, description="YYYY-MM-DD"),
    to_date: str | None = Query(None, description="YYYY-MM-DD"),
) -> OverrideListResponse:
    """List date overrides for the current user."""
    service = AvailabilityService()
    return await service.list_overrides(current_user, from_date, to_date)


@router.delete("/overrides/{override_id}")
async def delete_override(
    override_id: str,
    current_user: CurrentUserDep,
) -> dict:
    """Delete a date override."""
    service = AvailabilityService()
    return await service.delete_override(override_id, current_user)


# ── Public Availability Check (No Auth — called by Dograh Tool) ─────────────

@router.api_route("/check", methods=["GET", "POST"], response_model=AvailabilityCheckResponse)
async def check_availability(
    request: Request,
    date: str | None = Query(None, description="YYYY-MM-DD"),
    org_id: str | None = Query(None, description="Organization UUID"),
) -> AvailabilityCheckResponse:
    """Public endpoint: check available appointment slots for a date.

    Called by the Dograh AI agent via Tool during a live call.
    No authentication required — handles both GET/POST and query/json bodies.
    """
    final_date = date
    final_org_id = org_id

    if request.method == "POST" and (not final_date or not final_org_id):
        try:
            body = await request.json()
            if isinstance(body, dict):
                final_date = final_date or body.get("date")
                final_org_id = final_org_id or body.get("org_id")
        except Exception:
            pass

    if not final_date or not final_org_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both 'date' and 'org_id' are required parameters.",
        )

    service = AvailabilityService()
    return await service.check_availability(final_org_id, final_date)


# ── Public Appointment Booking (No Auth — called by Dograh Tool) ────────────

@router.api_route("/book", methods=["GET", "POST"])
async def book_appointment(
    request: Request,
    org_id: str | None = Query(None, description="Organization UUID"),
    contact_name: str | None = Query(None, description="Lead's full name"),
    contact_phone: str | None = Query(None, description="Lead's phone number"),
    appointment_date: str | None = Query(None, description="YYYY-MM-DDTHH:MM:SS"),
    notes: str | None = Query(None, description="Any notes about the appointment"),
) -> dict:
    """Public endpoint: book an appointment directly during a live call.

    Called by the Dograh AI agent via Tool after confirming a time slot.
    No authentication required — org_id identifies the organization.
    """
    final_org_id = org_id
    final_name = contact_name
    final_phone = contact_phone
    final_date = appointment_date
    final_notes = notes

    # Also accept JSON body for POST
    if request.method == "POST":
        try:
            body = await request.json()
            if isinstance(body, dict):
                final_org_id = final_org_id or body.get("org_id")
                final_name = final_name or body.get("contact_name")
                final_phone = final_phone or body.get("contact_phone")
                final_date = final_date or body.get("appointment_date")
                final_notes = final_notes or body.get("notes")
        except Exception:
            pass

    if not final_org_id or not final_name or not final_date:
        from fastapi import HTTPException, status as http_status
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Required: org_id, contact_name, appointment_date.",
        )

    from app.core.logging import logger
    from app.integrations.insforge_client import get_insforge_admin

    record = {
        "organization_id": final_org_id,
        "contact_name": final_name or "",
        "contact_phone": final_phone or "",
        "appointment_date": str(final_date),
        "notes": final_notes or "",
        "status": "scheduled",
    }

    try:
        db = get_insforge_admin()
        result = await db.database.from_("appointments").insert([record])
        result = result if isinstance(result, list) else []
        logger.info(
            "appointments.booked_via_tool",
            org_id=final_org_id,
            contact_name=final_name,
            appointment_date=str(final_date),
        )
        return {
            "status": "success",
            "message": f"Appointment booked for {final_name} on {final_date}.",
            "appointment_id": result[0]["id"] if result else None,
        }
    except Exception as exc:
        logger.error("appointments.book_tool_failed", error=str(exc))
        return {
            "status": "error",
            "message": f"Failed to book appointment: {exc}",
        }

