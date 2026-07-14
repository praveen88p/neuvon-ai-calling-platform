from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUserDep
from app.schemas.appointment import (
    AppointmentCreateRequest,
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentUpdateRequest,
)
from app.services.appointment_service import AppointmentService

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("", response_model=AppointmentListResponse)
async def list_appointments(
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
) -> AppointmentListResponse:
    """Paginated appointment list for the organization."""
    service = AppointmentService()
    return await service.list_appointments(current_user, page, per_page, status)


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: str,
    current_user: CurrentUserDep,
) -> AppointmentResponse:
    """Get a single appointment by ID."""
    service = AppointmentService()
    return await service.get_appointment(appointment_id, current_user)


@router.post("", response_model=AppointmentResponse)
async def create_appointment(
    data: AppointmentCreateRequest,
    current_user: CurrentUserDep,
) -> AppointmentResponse:
    """Manually create an appointment linked to a call run."""
    service = AppointmentService()
    return await service.create_appointment(data, current_user)


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: str,
    data: AppointmentUpdateRequest,
    current_user: CurrentUserDep,
) -> AppointmentResponse:
    """Update an existing appointment (status, date, notes, etc.)."""
    service = AppointmentService()
    return await service.update_appointment(appointment_id, data, current_user)
