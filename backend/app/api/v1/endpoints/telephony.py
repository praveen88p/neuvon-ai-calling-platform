from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_current_user
from app.schemas.auth import UserContext
from app.schemas.telephony import (
    PhoneNumberCreate,
    PhoneNumberListResponse,
    PhoneNumberResponse,
    PhoneNumberUpdate,
    TelephonyConfigCreate,
    TelephonyConfigListResponse,
    TelephonyConfigResponse,
    TelephonyConfigUpdate,
    TelephonyProvidersResponse,
)
from app.services.telephony_service import TelephonyService

router = APIRouter(prefix="/telephony", tags=["telephony"])


# --- Provider Metadata ---


@router.get("/providers", response_model=TelephonyProvidersResponse)
async def get_providers(
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> TelephonyProvidersResponse:
    """List supported telephony providers and their required fields."""
    service = TelephonyService()
    return await service.get_providers()


# --- Telephony Configs ---


@router.get("/configs", response_model=TelephonyConfigListResponse)
async def list_configs(
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> TelephonyConfigListResponse:
    """List telephony configurations for the organization."""
    service = TelephonyService()
    return await service.list_configs(current_user)


@router.post(
    "/configs",
    response_model=TelephonyConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_config(
    data: TelephonyConfigCreate,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> TelephonyConfigResponse:
    """Create a telephony configuration."""
    service = TelephonyService()
    return await service.create_config(data, current_user)


@router.get("/configs/{config_id}", response_model=TelephonyConfigResponse)
async def get_config(
    config_id: int,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> TelephonyConfigResponse:
    """Get a specific telephony configuration."""
    service = TelephonyService()
    return await service.get_config(config_id, current_user)


@router.put("/configs/{config_id}", response_model=TelephonyConfigResponse)
async def update_config(
    config_id: int,
    data: TelephonyConfigUpdate,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> TelephonyConfigResponse:
    """Update a telephony configuration."""
    service = TelephonyService()
    return await service.update_config(config_id, data, current_user)


@router.delete("/configs/{config_id}")
async def delete_config(
    config_id: int,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> dict:
    """Delete a telephony configuration."""
    service = TelephonyService()
    return await service.delete_config(config_id, current_user)


@router.post("/configs/{config_id}/set-default-outbound")
async def set_default_outbound(
    config_id: int,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> dict:
    """Set a config as the org-wide default for outbound calls."""
    service = TelephonyService()
    return await service.set_default_outbound(config_id, current_user)


# --- Phone Numbers ---


@router.get(
    "/configs/{config_id}/phone-numbers",
    response_model=PhoneNumberListResponse,
)
async def list_phone_numbers(
    config_id: int,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> PhoneNumberListResponse:
    """List phone numbers for a telephony config."""
    service = TelephonyService()
    return await service.list_phone_numbers(config_id, current_user)


@router.post(
    "/configs/{config_id}/phone-numbers",
    response_model=PhoneNumberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_phone_number(
    config_id: int,
    data: PhoneNumberCreate,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> PhoneNumberResponse:
    """Add a phone number to a telephony config."""
    service = TelephonyService()
    return await service.add_phone_number(config_id, data, current_user)


@router.get(
    "/configs/{config_id}/phone-numbers/{phone_number_id}",
    response_model=PhoneNumberResponse,
)
async def get_phone_number(
    config_id: int,
    phone_number_id: int,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> PhoneNumberResponse:
    """Get a specific phone number."""
    service = TelephonyService()
    return await service.get_phone_number(config_id, phone_number_id, current_user)


@router.put(
    "/configs/{config_id}/phone-numbers/{phone_number_id}",
    response_model=PhoneNumberResponse,
)
async def update_phone_number(
    config_id: int,
    phone_number_id: int,
    data: PhoneNumberUpdate,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> PhoneNumberResponse:
    """Update a phone number."""
    service = TelephonyService()
    return await service.update_phone_number(config_id, phone_number_id, data, current_user)


@router.delete("/configs/{config_id}/phone-numbers/{phone_number_id}")
async def delete_phone_number(
    config_id: int,
    phone_number_id: int,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> dict:
    """Remove a phone number from a config."""
    service = TelephonyService()
    return await service.delete_phone_number(config_id, phone_number_id, current_user)


@router.post(
    "/configs/{config_id}/phone-numbers/{phone_number_id}/set-default-caller",
)
async def set_default_caller(
    config_id: int,
    phone_number_id: int,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> dict:
    """Set a phone number as the default outbound caller ID for this config."""
    service = TelephonyService()
    return await service.set_default_caller(config_id, phone_number_id, current_user)
