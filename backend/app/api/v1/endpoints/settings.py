from __future__ import annotations

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUserDep
from app.schemas.settings import (
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeyListResponse,
    OrgSettingsResponse,
    OrgSettingsUpdate,
    ProfileResponse,
    ProfileUpdate,
)
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


# --- Organization Settings ---


@router.get("/organization", response_model=OrgSettingsResponse)
async def get_org_settings(current_user: CurrentUserDep) -> OrgSettingsResponse:
    """Get the current organization's settings."""
    service = SettingsService()
    return await service.get_org_settings(current_user)


@router.patch("/organization", response_model=OrgSettingsResponse)
async def update_org_settings(
    data: OrgSettingsUpdate,
    current_user: CurrentUserDep,
) -> OrgSettingsResponse:
    """Update organization settings. Requires admin or owner role."""
    service = SettingsService()
    return await service.update_org_settings(data, current_user)


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


# --- API Keys ---


@router.post(
    "/api-keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    data: ApiKeyCreateRequest,
    current_user: CurrentUserDep,
) -> ApiKeyCreatedResponse:
    """Create a new API key for the organization. Admin/owner only."""
    service = SettingsService()
    return await service.create_api_key(data, current_user)


@router.get("/api-keys", response_model=ApiKeyListResponse)
async def list_api_keys(current_user: CurrentUserDep) -> ApiKeyListResponse:
    """List all API keys for the organization."""
    service = SettingsService()
    return await service.list_api_keys(current_user)


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_200_OK)
async def revoke_api_key(
    key_id: str,
    current_user: CurrentUserDep,
) -> dict:
    """Revoke an API key. Admin/owner only."""
    service = SettingsService()
    return await service.revoke_api_key(key_id, current_user)
