from __future__ import annotations

from fastapi import HTTPException, status

from app.core.logging import logger
from app.integrations.dograh_client import DograhClient
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
    TelephonyProviderMetadata,
    TelephonyProvidersResponse,
)


class TelephonyService:
    """Business logic for telephony configuration and phone number management.

    Pure proxy to Dograh's telephony APIs. All Dograh telephony endpoints
    are org-scoped by the API key, so our backend simply proxies with
    proper error handling and logging.
    """

    def __init__(self) -> None:
        self.dograh = DograhClient()

    # --- Telephony Provider Metadata ---

    async def get_providers(self) -> TelephonyProvidersResponse:
        """List supported telephony providers and credential fields."""
        try:
            result = await self.dograh.get_telephony_providers()
        except Exception as exc:
            logger.error("telephony.providers_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch telephony providers",
            ) from exc

        # Normalize response
        raw = result if isinstance(result, list) else result.get("providers", [])
        providers = [
            TelephonyProviderMetadata(
                provider=p.get("provider", p.get("name", "")),
                display_name=p.get("display_name", p.get("label")),
                credential_fields=p.get("credential_fields", p.get("fields", [])),
            )
            for p in raw
        ]
        return TelephonyProvidersResponse(providers=providers)

    # --- Telephony Configs ---

    async def list_configs(
        self, current_user: UserContext,
    ) -> TelephonyConfigListResponse:
        """List telephony configs for the organization."""
        try:
            result = await self.dograh.list_telephony_configs()
        except Exception as exc:
            logger.error("telephony.list_failed", org_id=current_user.organization_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to list telephony configurations",
            ) from exc

        raw = result if isinstance(result, list) else result.get("configs", result.get("data", []))
        configs = [self._map_config(c) for c in raw]
        return TelephonyConfigListResponse(configs=configs, total=len(configs))

    async def create_config(
        self, data: TelephonyConfigCreate, current_user: UserContext,
    ) -> TelephonyConfigResponse:
        """Create a telephony configuration."""
        try:
            result = await self.dograh.create_telephony_config(data.model_dump())
        except Exception as exc:
            logger.error("telephony.create_failed", org_id=current_user.organization_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create telephony configuration",
            ) from exc

        logger.info(
            "telephony.config_created",
            org_id=current_user.organization_id,
            config_id=result.get("id"),
        )
        return self._map_config(result)

    async def get_config(
        self, config_id: int, current_user: UserContext,
    ) -> TelephonyConfigResponse:
        """Get a specific telephony configuration."""
        try:
            result = await self.dograh.get_telephony_config(config_id)
        except Exception as exc:
            logger.error("telephony.get_failed", config_id=config_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch telephony configuration",
            ) from exc

        return self._map_config(result)

    async def update_config(
        self, config_id: int, data: TelephonyConfigUpdate, current_user: UserContext,
    ) -> TelephonyConfigResponse:
        """Update a telephony configuration."""
        update_data = data.model_dump(exclude_none=True)
        try:
            result = await self.dograh.update_telephony_config(config_id, update_data)
        except Exception as exc:
            logger.error("telephony.update_failed", config_id=config_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to update telephony configuration",
            ) from exc

        logger.info("telephony.config_updated", config_id=config_id, org_id=current_user.organization_id)
        return self._map_config(result)

    async def delete_config(
        self, config_id: int, current_user: UserContext,
    ) -> dict:
        """Delete a telephony configuration."""
        try:
            result = await self.dograh.delete_telephony_config(config_id)
        except Exception as exc:
            logger.error("telephony.delete_failed", config_id=config_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to delete telephony configuration",
            ) from exc

        logger.info("telephony.config_deleted", config_id=config_id, org_id=current_user.organization_id)
        return {"status": "deleted", "config_id": config_id}

    async def set_default_outbound(
        self, config_id: int, current_user: UserContext,
    ) -> dict:
        """Set a config as the org-wide default outbound."""
        try:
            result = await self.dograh.set_default_outbound(config_id)
        except Exception as exc:
            logger.error("telephony.set_default_failed", config_id=config_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to set default outbound configuration",
            ) from exc

        logger.info("telephony.default_outbound_set", config_id=config_id, org_id=current_user.organization_id)
        return {"status": "ok", "config_id": config_id, "is_default_outbound": True}

    # --- Phone Numbers ---

    async def list_phone_numbers(
        self, config_id: int, current_user: UserContext,
    ) -> PhoneNumberListResponse:
        """List phone numbers for a config."""
        try:
            result = await self.dograh.list_phone_numbers(config_id)
        except Exception as exc:
            logger.error("telephony.list_numbers_failed", config_id=config_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to list phone numbers",
            ) from exc

        raw = result if isinstance(result, list) else result.get("phone_numbers", result.get("data", []))
        numbers = [self._map_phone_number(n) for n in raw]
        return PhoneNumberListResponse(phone_numbers=numbers, total=len(numbers))

    async def add_phone_number(
        self, config_id: int, data: PhoneNumberCreate, current_user: UserContext,
    ) -> PhoneNumberResponse:
        """Add a phone number to a config."""
        try:
            result = await self.dograh.add_phone_number(config_id, data.model_dump(exclude_none=True))
        except Exception as exc:
            logger.error("telephony.add_number_failed", config_id=config_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to add phone number",
            ) from exc

        logger.info(
            "telephony.number_added",
            config_id=config_id,
            number_id=result.get("id"),
            org_id=current_user.organization_id,
        )
        return self._map_phone_number(result)

    async def get_phone_number(
        self, config_id: int, phone_number_id: int, current_user: UserContext,
    ) -> PhoneNumberResponse:
        """Get a specific phone number."""
        try:
            result = await self.dograh.get_phone_number(config_id, phone_number_id)
        except Exception as exc:
            logger.error("telephony.get_number_failed", number_id=phone_number_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch phone number",
            ) from exc

        return self._map_phone_number(result)

    async def update_phone_number(
        self, config_id: int, phone_number_id: int, data: PhoneNumberUpdate, current_user: UserContext,
    ) -> PhoneNumberResponse:
        """Update a phone number."""
        update_data = data.model_dump(exclude_none=True)
        try:
            result = await self.dograh.update_phone_number(config_id, phone_number_id, update_data)
        except Exception as exc:
            logger.error("telephony.update_number_failed", number_id=phone_number_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to update phone number",
            ) from exc

        logger.info("telephony.number_updated", number_id=phone_number_id, org_id=current_user.organization_id)
        return self._map_phone_number(result)

    async def delete_phone_number(
        self, config_id: int, phone_number_id: int, current_user: UserContext,
    ) -> dict:
        """Remove a phone number."""
        try:
            result = await self.dograh.delete_phone_number(config_id, phone_number_id)
        except Exception as exc:
            logger.error("telephony.delete_number_failed", number_id=phone_number_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to delete phone number",
            ) from exc

        logger.info("telephony.number_deleted", number_id=phone_number_id, org_id=current_user.organization_id)
        return {"status": "deleted", "phone_number_id": phone_number_id}

    async def set_default_caller(
        self, config_id: int, phone_number_id: int, current_user: UserContext,
    ) -> dict:
        """Set a phone number as default caller ID for the config."""
        try:
            result = await self.dograh.set_default_caller(config_id, phone_number_id)
        except Exception as exc:
            logger.error("telephony.set_caller_failed", number_id=phone_number_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to set default caller",
            ) from exc

        logger.info(
            "telephony.default_caller_set",
            config_id=config_id,
            number_id=phone_number_id,
            org_id=current_user.organization_id,
        )
        return {"status": "ok", "phone_number_id": phone_number_id, "is_default_caller": True}

    # --- Helpers ---

    @staticmethod
    def _map_config(data: dict) -> TelephonyConfigResponse:
        """Map Dograh response to TelephonyConfigResponse."""
        return TelephonyConfigResponse(
            id=data.get("id", 0),
            provider=data.get("provider"),
            name=data.get("name"),
            is_default_outbound=data.get("is_default_outbound", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    @staticmethod
    def _map_phone_number(data: dict) -> PhoneNumberResponse:
        """Map Dograh response to PhoneNumberResponse."""
        return PhoneNumberResponse(
            id=data.get("id", 0),
            phone_number=data.get("phone_number"),
            label=data.get("label"),
            is_default_caller=data.get("is_default_caller", False),
            is_active=data.get("is_active", True),
            inbound_workflow_id=data.get("inbound_workflow_id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
