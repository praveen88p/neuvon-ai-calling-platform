from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core.logging import logger
from app.integrations.insforge_client import get_insforge_admin
from app.schemas.auth import UserContext
from app.schemas.settings import (
    OrgSettingsResponse,
    ProfileResponse,
    ProfileUpdate,
)


class SettingsService:
    """Business logic for organization settings (read-only) and user profiles.

    All operations scoped to current user's organization.
    API keys and org updates are managed from the super admin panel (separate).
    """

    def __init__(self) -> None:
        self.db = get_insforge_admin()

    # ------------------------------------------------------------------ #
    #  Organization Settings (read-only for clients)
    # ------------------------------------------------------------------ #

    async def get_org_settings(self, current_user: UserContext) -> OrgSettingsResponse:
        """Get the current user's organization settings (read-only)."""
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

        row = rows[0]
        return OrgSettingsResponse(
            id=str(row.get("id", "")),
            name=row.get("name", ""),
            created_at=str(row.get("created_at", "")),
        )

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
    #  Private helpers
    # ------------------------------------------------------------------ #

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
