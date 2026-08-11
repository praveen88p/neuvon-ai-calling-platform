"""API endpoints for spreadsheet integration.

Routes follow the project convention: prefix under /api/v1,
auth via ``get_current_user``, service instantiation per-request.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_current_user
from app.schemas.auth import UserContext
from app.schemas.sheets import (
    DetectColumnsRequest,
    SheetColumnsResponse,
    SheetConnectionCreate,
    SheetConnectionResponse,
    SheetConnectionStats,
    SheetConnectionUpdate,
    SheetLeadsListResponse,
)
from app.services.sheet_service import SheetService

router = APIRouter(prefix="/sheets", tags=["sheets"])


# ── Connection CRUD ───────────────────────────────────────────────────────


@router.post(
    "/connections",
    response_model=SheetConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_connection(
    data: SheetConnectionCreate,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> SheetConnectionResponse:
    """Connect a new Google Sheet to the organization."""
    service = SheetService()
    return await service.create_connection(data, current_user.organization_id)


@router.get("/connections", response_model=list[SheetConnectionResponse])
async def list_connections(
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> list[SheetConnectionResponse]:
    """List all sheet connections for the current organization."""
    service = SheetService()
    return await service.list_connections(current_user.organization_id)


@router.get(
    "/connections/{connection_id}",
    response_model=SheetConnectionResponse,
)
async def get_connection(
    connection_id: str,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> SheetConnectionResponse:
    """Get a single sheet connection."""
    service = SheetService()
    return await service.get_connection(
        connection_id, current_user.organization_id
    )


@router.patch(
    "/connections/{connection_id}",
    response_model=SheetConnectionResponse,
)
async def update_connection(
    connection_id: str,
    data: SheetConnectionUpdate,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> SheetConnectionResponse:
    """Update a sheet connection's settings."""
    service = SheetService()
    return await service.update_connection(
        connection_id, data, current_user.organization_id
    )


@router.delete(
    "/connections/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_connection(
    connection_id: str,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> None:
    """Disconnect a sheet and delete all associated leads."""
    service = SheetService()
    await service.delete_connection(
        connection_id, current_user.organization_id
    )


# ── Pause / Resume ───────────────────────────────────────────────────────


@router.post(
    "/connections/{connection_id}/pause",
    response_model=SheetConnectionResponse,
)
async def pause_connection(
    connection_id: str,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> SheetConnectionResponse:
    """Pause polling for a sheet connection."""
    service = SheetService()
    return await service.pause_connection(
        connection_id, current_user.organization_id
    )


@router.post(
    "/connections/{connection_id}/resume",
    response_model=SheetConnectionResponse,
)
async def resume_connection(
    connection_id: str,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> SheetConnectionResponse:
    """Resume polling for a paused sheet connection."""
    service = SheetService()
    return await service.resume_connection(
        connection_id, current_user.organization_id
    )


@router.post(
    "/connections/{connection_id}/poll-now",
    summary="Manually poll a sheet connection for new leads",
)
async def poll_now(
    connection_id: str,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> dict:
    """Immediately poll this sheet connection for new rows.

    Useful for testing or triggering a call without waiting for the
    60-second Celery Beat cycle. Runs synchronously in-request.
    """
    # Verify ownership first
    service = SheetService()
    await service.get_connection(connection_id, current_user.organization_id)

    new_count = await service.poll_for_new_leads(connection_id)
    return {"new_leads_found": new_count, "connection_id": connection_id}


# ── Column detection ─────────────────────────────────────────────────────


@router.post("/detect-columns", response_model=SheetColumnsResponse)
async def detect_columns(
    data: DetectColumnsRequest,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> SheetColumnsResponse:
    """Auto-detect columns from a Google Sheet URL.

    Returns headers, sample values, and available sheet tabs so the
    frontend can render a column mapping UI.
    """
    service = SheetService()
    return await service.detect_columns(data)


# ── Leads ─────────────────────────────────────────────────────────────────


@router.get(
    "/connections/{connection_id}/leads",
    response_model=SheetLeadsListResponse,
)
async def list_leads(
    connection_id: str,
    current_user: Annotated[UserContext, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> SheetLeadsListResponse:
    """List leads for a sheet connection with pagination."""
    service = SheetService()
    return await service.list_leads(
        connection_id, current_user.organization_id, page, limit
    )


# ── Stats ─────────────────────────────────────────────────────────────────


@router.get(
    "/connections/{connection_id}/stats",
    response_model=SheetConnectionStats,
)
async def get_connection_stats(
    connection_id: str,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> SheetConnectionStats:
    """Get aggregated stats for a sheet connection."""
    service = SheetService()
    return await service.get_connection_stats(
        connection_id, current_user.organization_id
    )


# ── Callbacks ──────────────────────────────────────────────────────────────


@router.get("/connections/{connection_id}/callbacks")
async def list_connection_callbacks(
    connection_id: str,
    current_user: Annotated[UserContext, Depends(get_current_user)],
    status: str | None = Query(None, description="Filter by status: pending, triggered, completed, cancelled, failed"),
) -> dict:
    """List scheduled callbacks for a specific sheet connection."""
    from app.services.callback_service import CallbackService

    svc = CallbackService()
    if status:
        callbacks = await svc.list_callbacks(
            org_id=current_user.organization_id,
            status=status,
            connection_id=connection_id,
        )
    else:
        callbacks = await svc.list_pending_for_connection(
            connection_id=connection_id,
            org_id=current_user.organization_id,
        )
    return {"callbacks": callbacks, "total": len(callbacks)}


@router.post(
    "/callbacks/{callback_id}/cancel",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_callback(
    callback_id: str,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> None:
    """Cancel a pending scheduled callback."""
    from app.services.callback_service import CallbackService

    svc = CallbackService()
    await svc.cancel_callback(
        callback_id=callback_id,
        org_id=current_user.organization_id,
    )


@router.get("/callbacks")
async def list_all_callbacks(
    current_user: Annotated[UserContext, Depends(get_current_user)],
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List all scheduled callbacks for the organization."""
    from app.services.callback_service import CallbackService

    svc = CallbackService()
    callbacks = await svc.list_callbacks(
        org_id=current_user.organization_id,
        status=status,
        limit=limit,
    )
    return {"callbacks": callbacks, "total": len(callbacks)}


# ── Audit Log ──────────────────────────────────────────────────────────────


@router.get("/connections/{connection_id}/audit")
async def get_connection_audit(
    connection_id: str,
    current_user: Annotated[UserContext, Depends(get_current_user)],
    event_type: str | None = Query(None, description="Filter by event type"),
    severity: str | None = Query(None, description="Filter by severity: debug, info, warning, error"),
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    """Get audit trail for a specific sheet connection.

    Returns events in reverse-chronological order.
    Useful for debugging polling errors and call issues.
    """
    from app.services.sheet_audit_service import SheetAuditService

    svc = SheetAuditService()
    events = await svc.list_events(
        org_id=current_user.organization_id,
        connection_id=connection_id,
        event_type=event_type,
        severity=severity,
        limit=limit,
    )
    return {"events": events, "total": len(events)}


@router.get("/audit")
async def get_org_audit_log(
    current_user: Annotated[UserContext, Depends(get_current_user)],
    event_type: str | None = Query(None),
    severity: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    """Get org-wide sheet integration audit log."""
    from app.services.sheet_audit_service import SheetAuditService

    svc = SheetAuditService()
    events = await svc.list_events(
        org_id=current_user.organization_id,
        event_type=event_type,
        severity=severity,
        limit=limit,
    )
    return {"events": events, "total": len(events)}
