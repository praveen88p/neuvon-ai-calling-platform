from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import CurrentUserDep
from app.schemas.settings import (
    OrgSettingsResponse,
    ProfileResponse,
    ProfileUpdate,
)
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


# --- Organization Settings (read-only for clients) ---


@router.get("/organization", response_model=OrgSettingsResponse)
async def get_org_settings(current_user: CurrentUserDep) -> OrgSettingsResponse:
    """Get the current organization's settings (read-only)."""
    service = SettingsService()
    return await service.get_org_settings(current_user)


# --- User Profile ---


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(current_user: CurrentUserDep) -> ProfileResponse:
    """Get the current user's profile."""
    service = SettingsService()
    return await service.get_profile(current_user)


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(
    data: ProfileUpdate,
    current_user: CurrentUserDep,
) -> ProfileResponse:
    """Update the current user's profile."""
    service = SettingsService()
    return await service.update_profile(data, current_user)
