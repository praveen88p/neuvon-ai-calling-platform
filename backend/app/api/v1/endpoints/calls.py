from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_user
from app.schemas.auth import UserContext
from app.schemas.call import (
    CallHistoryResponse,
    CallRunResponse,
    CallTrigger,
    CallTriggerResponse,
    DownloadUrlResponse,
)
from app.services.call_service import CallService
from app.services.topup_service import TopUpService

router = APIRouter(prefix="/calls", tags=["calls"])


@router.post(
    "/trigger",
    response_model=CallTriggerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def trigger_call(
    data: CallTrigger,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> CallTriggerResponse:
    """Trigger an outbound call via Dograh agent.

    Pre-paid model: blocks if org has no remaining minutes.
    """
    # Check minute balance before allowing the call
    topup_service = TopUpService()
    _, balance = await topup_service._get_org_rate_and_balance(
        current_user.organization_id
    )
    if balance <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient minutes. Please purchase a minute pack to continue making calls.",
        )

    service = CallService()
    return await service.trigger_call(data, current_user)


@router.get("/history", response_model=CallHistoryResponse)
async def get_call_history(
    current_user: Annotated[UserContext, Depends(get_current_user)],
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    start_date: str | None = Query(None, description="Start date ISO 8601"),
    end_date: str | None = Query(None, description="End date ISO 8601"),
    agent_id: int | None = Query(None, description="Filter by workflow/agent ID"),
    campaign_id: str | None = Query(None, description="Filter by campaign ID"),
    caller_number: str | None = Query(None, description="Filter by caller number"),
    called_number: str | None = Query(None, description="Filter by called number"),
    disposition: list[str] | None = Query(None, description="Filter by disposition codes"),
    min_duration: int | None = Query(None, ge=0, description="Min call duration (seconds)"),
    max_duration: int | None = Query(None, ge=0, description="Max call duration (seconds)"),
) -> CallHistoryResponse:
    """Paginated call history with filters for the current organization."""
    service = CallService()
    return await service.list_history(
        current_user,
        page=page,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        agent_id=agent_id,
        campaign_id=campaign_id,
        caller_number=caller_number,
        called_number=called_number,
        disposition=disposition,
        min_duration=min_duration,
        max_duration=max_duration,
    )


@router.get("/{run_id}", response_model=CallRunResponse)
async def get_call_run(
    run_id: int,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> CallRunResponse:
    """Get full call run details (transcript, recording, context)."""
    service = CallService()
    return await service.get_call_run(run_id, current_user)


@router.get("/{run_id}/recording", response_model=DownloadUrlResponse)
async def get_call_recording(
    run_id: int,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> DownloadUrlResponse:
    """Get recording download URL for a call run."""
    service = CallService()
    return await service.get_recording_url(run_id, current_user)


@router.get("/{run_id}/transcript", response_model=DownloadUrlResponse)
async def get_call_transcript(
    run_id: int,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> DownloadUrlResponse:
    """Get transcript download URL for a call run."""
    service = CallService()
    return await service.get_transcript_url(run_id, current_user)
