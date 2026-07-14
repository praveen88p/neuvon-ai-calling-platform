from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core.logging import logger
from app.integrations.insforge_client import get_insforge_admin
from app.schemas.auth import UserContext
from app.schemas.organization import (
    MemberInvite,
    MemberListResponse,
    MemberResponse,
    MemberRoleUpdate,
    OrganizationResponse,
    OrganizationUpdate,
)


class OrgService:
    """Business logic for organization and member management."""

    def __init__(self) -> None:
        self.db = get_insforge_admin()

    async def get_organization(self, current_user: UserContext) -> OrganizationResponse:
        """Get the current user's organization."""
        try:
            rows = await self.db.database.from_("organizations") \
                .select("*") \
                .eq("id", current_user.organization_id) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("org.fetch_failed", org_id=current_user.organization_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch organization",
            ) from exc

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )

        return self._to_org_response(rows[0])

    async def update_organization(
        self, data: OrganizationUpdate, current_user: UserContext
    ) -> OrganizationResponse:
        """Update organization settings. Owner or admin only."""
        updates: dict = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.white_label is not None:
            updates["white_label"] = json.dumps(data.white_label)

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            await self.db.database.from_("organizations") \
                .eq("id", current_user.organization_id) \
                .update(updates, return_representation=True)
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            logger.error("org.update_failed", org_id=current_user.organization_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update organization",
            ) from exc

        logger.info("org.updated", org_id=current_user.organization_id, fields=list(updates.keys()))
        return await self.get_organization(current_user)

    async def list_members(self, current_user: UserContext) -> MemberListResponse:
        """List all members of the current organization."""
        try:
            rows = await self.db.database.from_("users") \
                .select("id,email,full_name,role,is_active,last_login_at,created_at") \
                .eq("organization_id", current_user.organization_id) \
                .order("created_at") \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("org.list_members_failed", org_id=current_user.organization_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list members",
            ) from exc

        members = [self._to_member_response(row) for row in rows]
        return MemberListResponse(members=members, total=len(members))

    async def invite_member(
        self, data: MemberInvite, current_user: UserContext
    ) -> MemberResponse:
        """Invite a new member to the organization.

        Creates InsForge auth user + local user record with specified role.
        """
        if data.role not in ("admin", "member"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be 'admin' or 'member'",
            )

        from app.integrations.insforge_client import get_insforge_client
        insforge = get_insforge_client()

        # 1. Create InsForge auth user
        try:
            auth_result = await insforge.auth.create_user(
                email=data.email,
                password=data.password,
                name=data.full_name,
            )
        except Exception as exc:
            error_msg = str(exc).lower()
            if "already" in error_msg or "exists" in error_msg or "duplicate" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An account with this email already exists",
                ) from exc
            logger.error("org.invite_auth_failed", email=data.email, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create auth account for member",
            ) from exc

        insforge_user_id = str(auth_result.user.id) if auth_result.user else None
        if not insforge_user_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Account creation returned no user ID",
            )

        # 2. Create local user record
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            inserted = await self.db.database.from_("users").insert(
                [{
                    "id": insforge_user_id,
                    "organization_id": current_user.organization_id,
                    "email": data.email,
                    "full_name": data.full_name,
                    "role": data.role,
                    "is_active": True,
                }],
                return_representation=True,
            )
        except Exception as exc:
            logger.error("org.invite_record_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create member record",
            ) from exc

        # 3. Create audit log entry
        await self._audit(
            current_user,
            action="member_invited",
            resource_type="member",
            resource_id=insforge_user_id,
            metadata_={"email": data.email, "role": data.role},
        )

        logger.info(
            "org.member_invited",
            org_id=current_user.organization_id,
            invited_email=data.email,
            role=data.role,
        )

        # Return inserted record or construct from input
        if inserted and len(inserted) > 0:
            return self._to_member_response(inserted[0])

        return MemberResponse(
            user_id=insforge_user_id,
            email=data.email,
            full_name=data.full_name,
            role=data.role,
            is_active=True,
            last_login_at=None,
            created_at=now_iso,
        )

    async def update_member_role(
        self, user_id: str, data: MemberRoleUpdate, current_user: UserContext
    ) -> MemberResponse:
        """Update a member's role. Owner only."""
        if data.role not in ("admin", "member"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be 'admin' or 'member'",
            )

        # Cannot change own role
        if user_id == current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change your own role",
            )

        # Verify target user belongs to same org
        try:
            rows = await self.db.database.from_("users") \
                .select("id,email,full_name,role,is_active,last_login_at,created_at") \
                .eq("id", user_id) \
                .eq("organization_id", current_user.organization_id) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("org.role_lookup_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to look up member",
            ) from exc

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this organization",
            )

        target_user = rows[0]

        # Cannot demote owner
        if target_user.get("role") == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change the owner's role",
            )

        try:
            await self.db.database.from_("users") \
                .eq("id", user_id) \
                .eq("organization_id", current_user.organization_id) \
                .update({"role": data.role}, return_representation=True)
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            logger.error("org.role_update_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update role",
            ) from exc

        await self._audit(
            current_user,
            action="member_role_changed",
            resource_type="member",
            resource_id=user_id,
            metadata_={"old_role": target_user["role"], "new_role": data.role},
        )

        logger.info("org.role_updated", user_id=user_id, new_role=data.role)
        target_user["role"] = data.role
        return self._to_member_response(target_user)

    async def remove_member(
        self, user_id: str, current_user: UserContext
    ) -> dict:
        """Remove a member from the organization. Admin+ only."""
        # Cannot remove self
        if user_id == current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove yourself",
            )

        # Verify target exists and is not owner
        try:
            rows = await self.db.database.from_("users") \
                .select("id,role,email") \
                .eq("id", user_id) \
                .eq("organization_id", current_user.organization_id) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("org.remove_lookup_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to look up member",
            ) from exc

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this organization",
            )

        target = rows[0]
        if target.get("role") == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the organization owner",
            )

        # Soft-deactivate rather than hard delete
        try:
            await self.db.database.from_("users") \
                .eq("id", user_id) \
                .eq("organization_id", current_user.organization_id) \
                .update({"is_active": False}, return_representation=True)
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            logger.error("org.remove_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove member",
            ) from exc

        await self._audit(
            current_user,
            action="member_removed",
            resource_type="member",
            resource_id=user_id,
            metadata_={"email": target.get("email", "")},
        )

        logger.info("org.member_removed", user_id=user_id, org_id=current_user.organization_id)
        return {"message": "Member removed successfully"}

    # --- Helpers ---

    async def _audit(
        self,
        current_user: UserContext,
        action: str,
        resource_type: str,
        resource_id: str,
        metadata_: dict | None = None,
    ) -> None:
        """Create an audit log entry."""
        try:
            await self.db.database.from_("audit_log").insert(
                [{
                    "organization_id": current_user.organization_id,
                    "user_id": current_user.user_id,
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "metadata": json.dumps(metadata_) if metadata_ else None,
                }]
            )
        except Exception as exc:
            logger.warning("audit.write_failed", action=action, error=str(exc))

    @staticmethod
    def _to_org_response(row: dict) -> OrganizationResponse:
        white_label = row.get("white_label")
        if isinstance(white_label, str):
            try:
                white_label = json.loads(white_label)
            except (json.JSONDecodeError, TypeError):
                white_label = None

        return OrganizationResponse(
            id=str(row["id"]),
            name=row.get("name", ""),
            slug=row.get("slug", ""),
            org_type=row.get("org_type", "direct"),
            white_label=white_label,
            billing_plan=row.get("billing_plan", "free"),
            usage_quota=row.get("usage_quota"),
            is_active=row.get("is_active", True),
            created_at=str(row.get("created_at", "")),
        )

    @staticmethod
    def _to_member_response(row: dict) -> MemberResponse:
        return MemberResponse(
            user_id=str(row["id"]),
            email=row.get("email", ""),
            full_name=row.get("full_name", ""),
            role=row.get("role", "member"),
            is_active=row.get("is_active", True),
            last_login_at=str(row["last_login_at"]) if row.get("last_login_at") else None,
            created_at=str(row.get("created_at", "")),
        )
