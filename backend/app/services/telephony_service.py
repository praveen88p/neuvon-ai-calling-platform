from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core.logging import logger
from app.integrations.dograh_client import DograhClient
from app.integrations.insforge_client import get_insforge_admin
from app.schemas.auth import UserContext
from app.schemas.telephony import (
    PhoneNumberCreate,
    PhoneNumberListResponse,
    PhoneNumberResponse,
    PhoneNumberUpdate,
    ProviderSync,
    TelephonyConfigCreate,
    TelephonyConfigListResponse,
    TelephonyConfigResponse,
    TelephonyConfigUpdate,
    TelephonyProviderField,
    TelephonyProviderMetadata,
    TelephonyProvidersResponse,
)


class TelephonyService:
    """Business logic for telephony configuration and phone number management.

    Dual-storage pattern (same as CampaignService):
    - Mutating operations (create, delete) → Dograh + local InsForge DB
    - Read operations (list) → local DB for org-scoping, Dograh for live data
    - Every operation verifies org ownership via local DB before touching Dograh

    The single global DOGRAH_API_KEY is used for all orgs. Multi-tenant
    isolation is enforced by Neuvon's local DB (telephony_configs and
    phone_numbers tables with organization_id).
    """

    def __init__(self) -> None:
        self.dograh = DograhClient()
        self.db = get_insforge_admin()

    # ── Ownership helpers ─────────────────────────────────────────────────

    async def _verify_config_ownership(
        self, config_id: int, org_id: str,
    ) -> dict:
        """Verify a Dograh config_id belongs to this org. Returns the local row."""
        try:
            rows = await self.db.database.from_("telephony_configs") \
                .select("*") \
                .eq("organization_id", str(org_id)) \
                .eq("dograh_config_id", config_id) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("telephony.ownership_check_failed", config_id=config_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to verify configuration ownership",
            ) from exc

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Telephony configuration not found",
            )
        return rows[0]

    async def _verify_phone_ownership(
        self, phone_number_id: int, org_id: str,
    ) -> dict:
        """Verify a Dograh phone_number_id belongs to this org. Returns the local row."""
        try:
            rows = await self.db.database.from_("phone_numbers") \
                .select("*") \
                .eq("organization_id", str(org_id)) \
                .eq("dograh_phone_id", phone_number_id) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("telephony.phone_ownership_check_failed", phone_id=phone_number_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to verify phone number ownership",
            ) from exc

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phone number not found",
            )
        return rows[0]

    # ── Telephony Provider Metadata ───────────────────────────────────────

    async def get_providers(self) -> TelephonyProvidersResponse:
        """List supported telephony providers and credential fields.

        Providers are global (not org-specific), so no ownership check needed.
        """
        try:
            result = await self.dograh.get_telephony_providers()
        except Exception as exc:
            logger.error("telephony.providers_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch telephony providers",
            ) from exc

        # Normalize response — Dograh returns { providers: [...] } or a list
        raw = result if isinstance(result, list) else result.get("providers", [])
        providers = []
        for p in raw:
            raw_fields = p.get("fields", p.get("credential_fields", []))
            fields = []
            for f in raw_fields:
                if isinstance(f, dict):
                    fields.append(TelephonyProviderField(
                        name=f.get("name", f.get("key", "")),
                        label=f.get("label", f.get("display_name")),
                        type=f.get("type", "text"),
                        required=f.get("required", True),
                        sensitive=f.get("sensitive", False),
                        description=f.get("description"),
                    ))
                else:
                    fields.append(TelephonyProviderField(name=str(f)))

            providers.append(TelephonyProviderMetadata(
                provider=p.get("provider", p.get("name", "")),
                display_name=p.get("display_name", p.get("label")),
                docs_url=p.get("docs_url"),
                fields=fields,
            ))
        return TelephonyProvidersResponse(providers=providers)

    # ── Telephony Configs ─────────────────────────────────────────────────

    async def list_configs(
        self, current_user: UserContext,
    ) -> TelephonyConfigListResponse:
        """List telephony configs for the organization.

        Reads from local DB (org-scoped). Does NOT call Dograh — the local
        DB is the source of truth for which org owns which config.
        """
        org_id = current_user.organization_id

        try:
            rows = await self.db.database.from_("telephony_configs") \
                .select("*") \
                .eq("organization_id", str(org_id)) \
                .order("created_at", desc=True) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("telephony.list_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to list telephony configurations",
            ) from exc

        configs = []
        for row in rows:
            configs.append(TelephonyConfigResponse(
                id=row.get("dograh_config_id", 0),
                provider=row.get("provider"),
                name=row.get("label"),
                is_default_outbound=row.get("is_default_outbound", False),
                phone_number_count=0,  # Will be populated when user expands the card
                created_at=row.get("created_at"),
                updated_at=None,
            ))
        return TelephonyConfigListResponse(configs=configs, total=len(configs))

    async def create_config(
        self, data: TelephonyConfigCreate, current_user: UserContext,
    ) -> TelephonyConfigResponse:
        """Create a telephony configuration.

        Dual-storage: create in Dograh, then save to local DB with org_id.
        """
        org_id = current_user.organization_id

        # 1. Create in Dograh (single global key)
        try:
            result = await self.dograh.create_telephony_config(data.model_dump())
        except Exception as exc:
            logger.error("telephony.create_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create telephony configuration",
            ) from exc

        dograh_config_id = result.get("id")

        # 2. Save to local DB with org ownership
        local_record = {
            "organization_id": str(org_id),
            "dograh_config_id": dograh_config_id,
            "provider": data.provider,
            "label": data.name,
            "is_default_outbound": data.is_default_outbound,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await self.db.database.from_("telephony_configs").insert([local_record])
        except Exception as exc:
            logger.error(
                "telephony.local_create_failed",
                org_id=org_id,
                dograh_config_id=dograh_config_id,
                error=str(exc),
            )
            # Don't fail the request — Dograh config was created successfully.
            # Local record can be synced later if needed.

        logger.info(
            "telephony.config_created",
            org_id=org_id,
            dograh_config_id=dograh_config_id,
        )
        return self._map_config(result)

    async def get_config(
        self, config_id: int, current_user: UserContext,
    ) -> TelephonyConfigResponse:
        """Get a specific telephony configuration.

        Verify ownership via local DB, then fetch live data from Dograh.
        """
        org_id = current_user.organization_id
        await self._verify_config_ownership(config_id, str(org_id))

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
        """Update a telephony configuration.

        Verify ownership → update in Dograh → update local DB.
        """
        org_id = current_user.organization_id
        await self._verify_config_ownership(config_id, str(org_id))

        update_data = data.model_dump(exclude_none=True)
        try:
            result = await self.dograh.update_telephony_config(config_id, update_data)
        except Exception as exc:
            logger.error("telephony.update_failed", config_id=config_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to update telephony configuration",
            ) from exc

        # Update local DB if name changed
        if data.name:
            try:
                await self.db.database.from_("telephony_configs") \
                    .update({"label": data.name}) \
                    .eq("organization_id", str(org_id)) \
                    .eq("dograh_config_id", config_id) \
                    .execute()
            except Exception as exc:
                logger.warning("telephony.local_update_failed", config_id=config_id, error=str(exc))

        logger.info("telephony.config_updated", config_id=config_id, org_id=org_id)
        return self._map_config(result)

    async def delete_config(
        self, config_id: int, current_user: UserContext,
    ) -> dict:
        """Delete a telephony configuration.

        Verify ownership → delete from Dograh → delete from local DB.
        """
        org_id = current_user.organization_id
        await self._verify_config_ownership(config_id, str(org_id))

        # 1. Delete from Dograh
        try:
            await self.dograh.delete_telephony_config(config_id)
        except Exception as exc:
            logger.error("telephony.delete_failed", config_id=config_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to delete telephony configuration",
            ) from exc

        # 2. Delete from local DB (cascade deletes phone_numbers too)
        try:
            await self.db.database.from_("telephony_configs") \
                .delete() \
                .eq("organization_id", str(org_id)) \
                .eq("dograh_config_id", config_id) \
                .execute()
        except Exception as exc:
            logger.warning("telephony.local_delete_failed", config_id=config_id, error=str(exc))

        logger.info("telephony.config_deleted", config_id=config_id, org_id=org_id)
        return {"status": "deleted", "config_id": config_id}

    async def set_default_outbound(
        self, config_id: int, current_user: UserContext,
    ) -> dict:
        """Set a config as the org-wide default outbound.

        Verify ownership → call Dograh → update local DB.
        """
        org_id = current_user.organization_id
        await self._verify_config_ownership(config_id, str(org_id))

        try:
            await self.dograh.set_default_outbound(config_id)
        except Exception as exc:
            logger.error("telephony.set_default_failed", config_id=config_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to set default outbound configuration",
            ) from exc

        # Update local DB: clear old default, set new
        try:
            # Clear all defaults for this org
            await self.db.database.from_("telephony_configs") \
                .update({"is_default_outbound": False}) \
                .eq("organization_id", str(org_id)) \
                .execute()
            # Set the new default
            await self.db.database.from_("telephony_configs") \
                .update({"is_default_outbound": True}) \
                .eq("organization_id", str(org_id)) \
                .eq("dograh_config_id", config_id) \
                .execute()
        except Exception as exc:
            logger.warning("telephony.local_default_update_failed", config_id=config_id, error=str(exc))

        logger.info("telephony.default_outbound_set", config_id=config_id, org_id=org_id)
        return {"status": "ok", "config_id": config_id, "is_default_outbound": True}

    # ── Phone Numbers ─────────────────────────────────────────────────────

    async def list_phone_numbers(
        self, config_id: int, current_user: UserContext,
    ) -> PhoneNumberListResponse:
        """List phone numbers for a config.

        Verify config ownership → fetch live data from Dograh.
        Phone numbers live in Dograh; local DB only tracks ownership.
        """
        org_id = current_user.organization_id
        await self._verify_config_ownership(config_id, str(org_id))

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
        """Add a phone number to a config.

        Verify config ownership → add to Dograh → save to local DB.
        """
        org_id = current_user.organization_id
        local_config = await self._verify_config_ownership(config_id, str(org_id))

        # 1. Add to Dograh
        try:
            result = await self.dograh.add_phone_number(config_id, data.model_dump(exclude_none=True))
        except Exception as exc:
            logger.error("telephony.add_number_failed", config_id=config_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to add phone number",
            ) from exc

        dograh_phone_id = result.get("id")

        # 2. Save to local DB with org ownership
        local_record = {
            "organization_id": str(org_id),
            "telephony_config_id": local_config["id"],
            "dograh_phone_id": dograh_phone_id,
            "number": data.address,
            "label": data.label or "",
            "is_default_caller": data.is_default_caller_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await self.db.database.from_("phone_numbers").insert([local_record])
        except Exception as exc:
            logger.error(
                "telephony.local_phone_create_failed",
                org_id=org_id,
                dograh_phone_id=dograh_phone_id,
                error=str(exc),
            )

        logger.info(
            "telephony.number_added",
            config_id=config_id,
            number_id=dograh_phone_id,
            org_id=org_id,
        )
        return self._map_phone_number(result)

    async def get_phone_number(
        self, config_id: int, phone_number_id: int, current_user: UserContext,
    ) -> PhoneNumberResponse:
        """Get a specific phone number.

        Verify config + phone ownership → fetch from Dograh.
        """
        org_id = current_user.organization_id
        await self._verify_config_ownership(config_id, str(org_id))
        await self._verify_phone_ownership(phone_number_id, str(org_id))

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
        """Update a phone number.

        Verify ownership → update in Dograh → update local DB.
        """
        org_id = current_user.organization_id
        await self._verify_config_ownership(config_id, str(org_id))
        await self._verify_phone_ownership(phone_number_id, str(org_id))

        update_data = data.model_dump(exclude_none=True)
        try:
            result = await self.dograh.update_phone_number(config_id, phone_number_id, update_data)
        except Exception as exc:
            logger.error("telephony.update_number_failed", number_id=phone_number_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to update phone number",
            ) from exc

        # Update local DB
        local_updates: dict = {}
        if data.label is not None:
            local_updates["label"] = data.label or ""
        if data.is_default_caller_id is not None:
            local_updates["is_default_caller"] = data.is_default_caller_id
        if local_updates:
            try:
                await self.db.database.from_("phone_numbers") \
                    .update(local_updates) \
                    .eq("organization_id", str(org_id)) \
                    .eq("dograh_phone_id", phone_number_id) \
                    .execute()
            except Exception as exc:
                logger.warning("telephony.local_phone_update_failed", phone_id=phone_number_id, error=str(exc))

        logger.info("telephony.number_updated", number_id=phone_number_id, org_id=org_id)
        return self._map_phone_number(result)

    async def delete_phone_number(
        self, config_id: int, phone_number_id: int, current_user: UserContext,
    ) -> dict:
        """Remove a phone number.

        Verify ownership → delete from Dograh → delete from local DB.
        """
        org_id = current_user.organization_id
        await self._verify_config_ownership(config_id, str(org_id))
        await self._verify_phone_ownership(phone_number_id, str(org_id))

        # 1. Delete from Dograh
        try:
            await self.dograh.delete_phone_number(config_id, phone_number_id)
        except Exception as exc:
            logger.error("telephony.delete_number_failed", number_id=phone_number_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to delete phone number",
            ) from exc

        # 2. Delete from local DB
        try:
            await self.db.database.from_("phone_numbers") \
                .delete() \
                .eq("organization_id", str(org_id)) \
                .eq("dograh_phone_id", phone_number_id) \
                .execute()
        except Exception as exc:
            logger.warning("telephony.local_phone_delete_failed", phone_id=phone_number_id, error=str(exc))

        logger.info("telephony.number_deleted", number_id=phone_number_id, org_id=org_id)
        return {"status": "deleted", "phone_number_id": phone_number_id}

    async def set_default_caller(
        self, config_id: int, phone_number_id: int, current_user: UserContext,
    ) -> dict:
        """Set a phone number as default caller ID for the config.

        Verify ownership → call Dograh → update local DB.
        """
        org_id = current_user.organization_id
        local_config = await self._verify_config_ownership(config_id, str(org_id))
        await self._verify_phone_ownership(phone_number_id, str(org_id))

        try:
            await self.dograh.set_default_caller(config_id, phone_number_id)
        except Exception as exc:
            logger.error("telephony.set_caller_failed", number_id=phone_number_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to set default caller",
            ) from exc

        # Update local DB: clear old default for this config, set new
        try:
            await self.db.database.from_("phone_numbers") \
                .update({"is_default_caller": False}) \
                .eq("telephony_config_id", local_config["id"]) \
                .execute()
            await self.db.database.from_("phone_numbers") \
                .update({"is_default_caller": True}) \
                .eq("organization_id", str(org_id)) \
                .eq("dograh_phone_id", phone_number_id) \
                .execute()
        except Exception as exc:
            logger.warning("telephony.local_caller_update_failed", phone_id=phone_number_id, error=str(exc))

        logger.info(
            "telephony.default_caller_set",
            config_id=config_id,
            number_id=phone_number_id,
            org_id=org_id,
        )
        return {"status": "ok", "phone_number_id": phone_number_id, "is_default_caller_id": True}

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _map_config(data: dict) -> TelephonyConfigResponse:
        """Map Dograh response to TelephonyConfigResponse."""
        return TelephonyConfigResponse(
            id=data.get("id", 0),
            provider=data.get("provider"),
            name=data.get("name"),
            is_default_outbound=data.get("is_default_outbound", False),
            phone_number_count=data.get("phone_number_count", 0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    @staticmethod
    def _map_phone_number(data: dict) -> PhoneNumberResponse:
        """Map Dograh response to PhoneNumberResponse."""
        sync_data = data.get("provider_sync")
        provider_sync = None
        if isinstance(sync_data, dict):
            provider_sync = ProviderSync(
                ok=sync_data.get("ok", True),
                message=sync_data.get("message"),
            )

        return PhoneNumberResponse(
            id=data.get("id", 0),
            telephony_configuration_id=data.get("telephony_configuration_id"),
            address=data.get("address", data.get("phone_number")),
            address_normalized=data.get("address_normalized"),
            address_type=data.get("address_type"),
            country_code=data.get("country_code"),
            label=data.get("label"),
            is_default_caller_id=data.get("is_default_caller_id", data.get("is_default_caller", False)),
            is_active=data.get("is_active", True),
            inbound_workflow_id=data.get("inbound_workflow_id"),
            inbound_workflow_name=data.get("inbound_workflow_name"),
            extra_metadata=data.get("extra_metadata"),
            provider_sync=provider_sync,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
