from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.core.logging import logger
from app.core.posthog import track_event
from app.integrations.insforge_client import get_insforge_admin
from app.schemas.auth import UserContext
from app.schemas.settings import (
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeyListResponse,
    ApiKeyResponse,
    OrgSettingsResponse,
    OrgSettingsUpdate,
    ProfileResponse,
    ProfileUpdate,
)


class SettingsService:
    """Business logic for organization settings, user profiles, and API keys.

    All operations scoped to current user's organization.
    """

    def __init__(self) -> None:
        self.db = get_insforge_admin()

    # ------------------------------------------------------------------ #
    #  Organization Settings
    # ------------------------------------------------------------------ #

    async def get_org_settings(self, current_user: UserContext) -> OrgSettingsResponse:
        """Get the current user's organization settings."""
        org_id = current_user.organization_id

        try:
            rows = await self.db.database.from_("organizations") \
                .select("*") \
                .eq("id", org_id) \
                .limit(1) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("settings.org_fetch_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch organization settings",
            ) from exc

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )

        return self._to_org_settings(rows[0])

    async def update_org_settings(
        self,
        data: OrgSettingsUpdate,
        current_user: UserContext,
    ) -> OrgSettingsResponse:
        """Update organization settings. Requires admin or owner role."""
        org_id = current_user.organization_id

        if current_user.role not in ("owner", "admin", "platform_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins and owners can update organization settings",
            )

        updates: dict = {}
        white_label: dict = {}

        if data.display_name is not None:
            white_label["display_name"] = data.display_name
        if data.logo_url is not None:
            white_label["logo_url"] = data.logo_url
        if data.primary_color is not None:
            white_label["primary_color"] = data.primary_color
        if data.webhook_url is not None:
            updates["webhook_url"] = data.webhook_url
        if data.timezone is not None:
            updates["timezone"] = data.timezone

        if white_label:
            # Merge with existing white_label data
            try:
                existing = await self.db.database.from_("organizations") \
                    .select("white_label") \
                    .eq("id", org_id) \
                    .limit(1) \
                    .execute()
                existing = existing if isinstance(existing, list) else []
                existing_wl = {}
                if existing:
                    raw = existing[0].get("white_label")
                    if isinstance(raw, str):
                        existing_wl = json.loads(raw)
                    elif isinstance(raw, dict):
                        existing_wl = raw
                existing_wl.update(white_label)
                updates["white_label"] = json.dumps(existing_wl)
            except Exception:
                updates["white_label"] = json.dumps(white_label)

        if not updates:
            return await self.get_org_settings(current_user)

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            await self.db.database.from_("organizations") \
                .eq("id", org_id) \
                .update(updates)
        except json.JSONDecodeError:
            # InsForge SDK bug: update succeeds but returns empty body
            pass
        except Exception as exc:
            logger.error("settings.org_update_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update organization settings",
            ) from exc

        logger.info("settings.org_updated", org_id=org_id)
        return await self.get_org_settings(current_user)

    # ------------------------------------------------------------------ #
    #  User Profile
    # ------------------------------------------------------------------ #

    async def get_profile(self, current_user: UserContext) -> ProfileResponse:
        """Get the current user's profile."""
        try:
            rows = await self.db.database.from_("users") \
                .select("*") \
                .eq("id", current_user.user_id) \
                .eq("organization_id", current_user.organization_id) \
                .limit(1) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("settings.profile_fetch_failed", user_id=current_user.user_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch user profile",
            ) from exc

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found",
            )

        return self._to_profile_response(rows[0], current_user)

    async def update_profile(
        self,
        data: ProfileUpdate,
        current_user: UserContext,
    ) -> ProfileResponse:
        """Update the current user's profile."""
        updates: dict = {}
        if data.full_name is not None:
            updates["full_name"] = data.full_name
        if data.phone is not None:
            updates["phone"] = data.phone
        if data.avatar_url is not None:
            updates["avatar_url"] = data.avatar_url
        if data.notification_preferences is not None:
            updates["notification_preferences"] = json.dumps(data.notification_preferences)

        if not updates:
            return await self.get_profile(current_user)

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            await self.db.database.from_("users") \
                .eq("id", current_user.user_id) \
                .eq("organization_id", current_user.organization_id) \
                .update(updates)
        except json.JSONDecodeError:
            # InsForge SDK bug: update succeeds but returns empty body
            pass
        except Exception as exc:
            logger.error("settings.profile_update_failed", user_id=current_user.user_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user profile",
            ) from exc

        logger.info("settings.profile_updated", user_id=current_user.user_id)
        return await self.get_profile(current_user)

    # ------------------------------------------------------------------ #
    #  API Keys
    # ------------------------------------------------------------------ #

    async def create_api_key(
        self,
        data: ApiKeyCreateRequest,
        current_user: UserContext,
    ) -> ApiKeyCreatedResponse:
        """Generate a new API key for the organization."""
        org_id = current_user.organization_id

        if current_user.role not in ("owner", "admin", "platform_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins and owners can create API keys",
            )

        raw_key = f"nvn_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:12]

        expires_at = None
        if data.expires_in_days:
            expires_at = (
                datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)
            ).isoformat()

        record = {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": data.name,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "is_active": True,
            "expires_at": expires_at,
            "created_by": current_user.user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            await self.db.database.from_("api_keys") \
                .insert([record])
        except Exception as exc:
            logger.error("settings.api_key_create_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create API key",
            ) from exc

        track_event(
            current_user.user_id,
            "api_key_created",
            {"org_id": org_id, "key_name": data.name},
        )

        logger.info("settings.api_key_created", org_id=org_id, key_name=data.name)
        return ApiKeyCreatedResponse(
            id=record["id"],
            organization_id=org_id,
            name=data.name,
            key=raw_key,
            key_prefix=key_prefix,
            expires_at=expires_at,
            created_at=record["created_at"],
        )

    async def list_api_keys(self, current_user: UserContext) -> ApiKeyListResponse:
        """List all API keys for the organization."""
        org_id = current_user.organization_id

        try:
            rows = await self.db.database.from_("api_keys") \
                .select("*") \
                .eq("organization_id", org_id) \
                .order("created_at", desc=True) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("settings.api_keys_list_failed", org_id=org_id, error=str(exc))
            rows = []

        keys = [self._to_api_key_response(r) for r in rows]
        return ApiKeyListResponse(keys=keys, total=len(keys))

    async def revoke_api_key(
        self,
        key_id: str,
        current_user: UserContext,
    ) -> dict:
        """Revoke (soft-delete) an API key."""
        org_id = current_user.organization_id

        if current_user.role not in ("owner", "admin", "platform_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins and owners can revoke API keys",
            )

        try:
            rows = await self.db.database.from_("api_keys") \
                .select("id") \
                .eq("id", key_id) \
                .eq("organization_id", org_id) \
                .limit(1) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            err = str(exc)
            if "invalid input syntax" in err:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="API key not found",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to look up API key",
            ) from exc

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found",
            )

        try:
            await self.db.database.from_("api_keys") \
                .eq("id", key_id) \
                .eq("organization_id", org_id) \
                .update({"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()})
        except json.JSONDecodeError:
            # InsForge SDK bug: update succeeds but returns empty body
            pass
        except Exception as exc:
            logger.error("settings.api_key_revoke_failed", key_id=key_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to revoke API key",
            ) from exc

        logger.info("settings.api_key_revoked", org_id=org_id, key_id=key_id)
        return {"detail": "API key revoked"}

    # ------------------------------------------------------------------ #
    #  Private helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_org_settings(row: dict) -> OrgSettingsResponse:
        wl = row.get("white_label")
        if isinstance(wl, str):
            try:
                wl = json.loads(wl)
            except (json.JSONDecodeError, TypeError):
                wl = {}
        elif not isinstance(wl, dict):
            wl = {}

        return OrgSettingsResponse(
            id=str(row.get("id", "")),
            name=row.get("name", ""),
            display_name=wl.get("display_name"),
            logo_url=wl.get("logo_url"),
            primary_color=wl.get("primary_color"),
            webhook_url=row.get("webhook_url"),
            timezone=row.get("timezone"),
            created_at=str(row.get("created_at", "")),
        )

    @staticmethod
    def _to_profile_response(row: dict, ctx: UserContext) -> ProfileResponse:
        notif = row.get("notification_preferences")
        if isinstance(notif, str):
            try:
                notif = json.loads(notif)
            except (json.JSONDecodeError, TypeError):
                notif = None

        return ProfileResponse(
            user_id=str(row.get("id", "")),
            email=row.get("email", ""),
            full_name=row.get("full_name", ""),
            role=ctx.role,
            organization_id=ctx.organization_id,
            phone=row.get("phone"),
            avatar_url=row.get("avatar_url"),
            notification_preferences=notif,
            created_at=str(row.get("created_at", "")),
        )

    @staticmethod
    def _to_api_key_response(row: dict) -> ApiKeyResponse:
        return ApiKeyResponse(
            id=str(row.get("id", "")),
            organization_id=str(row.get("organization_id", "")),
            name=row.get("name", ""),
            key_prefix=row.get("key_prefix", ""),
            is_active=row.get("is_active", True),
            expires_at=str(row.get("expires_at", "")) if row.get("expires_at") else None,
            created_at=str(row.get("created_at", "")) if row.get("created_at") else None,
            last_used_at=str(row.get("last_used_at", "")) if row.get("last_used_at") else None,
        )
