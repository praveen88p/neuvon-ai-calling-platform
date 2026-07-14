from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, UploadFile, status

from app.core.dependencies import get_current_user
from app.schemas.auth import UserContext
from app.schemas.campaign import (
    CampaignActionResponse,
    CampaignCreate,
    CampaignListResponse,
    CampaignProgressResponse,
    CampaignResponse,
    CampaignUpdate,
    ContactListUploadResponse,
)
from app.services.campaign_service import CampaignService

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post(
    "/upload-contacts",
    response_model=ContactListUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_contacts(
    file: UploadFile,
    current_user: Annotated[UserContext, Depends(get_current_user)],
    country_code: str = Form(default=""),
) -> ContactListUploadResponse:
    """Upload contacts CSV for campaign creation.

    Optionally provide a country_code (e.g. '+91', '+1') to prepend
    to phone numbers that don't already have a country code.
    """
    content = await file.read()
    service = CampaignService()
    return await service.upload_contacts(
        content,
        file.filename or "contacts.csv",
        current_user,
        default_country_code=country_code.strip() if country_code else "",
    )


@router.post(
    "/",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    data: CampaignCreate,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> CampaignResponse:
    """Create a new outbound campaign."""
    service = CampaignService()
    return await service.create_campaign(data, current_user)


@router.get("/", response_model=CampaignListResponse)
async def list_campaigns(
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> CampaignListResponse:
    """List all campaigns for the current organization."""
    service = CampaignService()
    return await service.list_campaigns(current_user)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> CampaignResponse:
    """Get campaign details with live progress from Dograh."""
    service = CampaignService()
    return await service.get_campaign(campaign_id, current_user)


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    data: CampaignUpdate,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> CampaignResponse:
    """Update campaign settings (name, concurrency, retry, schedule)."""
    service = CampaignService()
    return await service.update_campaign(campaign_id, data, current_user)


@router.post("/{campaign_id}/start", response_model=CampaignActionResponse)
async def start_campaign(
    campaign_id: str,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> CampaignActionResponse:
    """Start a draft or paused campaign."""
    service = CampaignService()
    return await service.start_campaign(campaign_id, current_user)


@router.post("/{campaign_id}/pause", response_model=CampaignActionResponse)
async def pause_campaign(
    campaign_id: str,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> CampaignActionResponse:
    """Pause a running campaign."""
    service = CampaignService()
    return await service.pause_campaign(campaign_id, current_user)


@router.post("/{campaign_id}/resume", response_model=CampaignActionResponse)
async def resume_campaign(
    campaign_id: str,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> CampaignActionResponse:
    """Resume a paused campaign."""
    service = CampaignService()
    return await service.resume_campaign(campaign_id, current_user)


@router.get("/{campaign_id}/progress", response_model=CampaignProgressResponse)
async def get_campaign_progress(
    campaign_id: str,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> CampaignProgressResponse:
    """Get current campaign progress stats."""
    service = CampaignService()
    return await service.get_progress(campaign_id, current_user)


@router.get("/{campaign_id}/runs")
async def get_campaign_runs(
    campaign_id: str,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> dict:
    """Get call run records for all contacts in this campaign."""
    service = CampaignService()
    return await service.get_campaign_runs(campaign_id, current_user)
