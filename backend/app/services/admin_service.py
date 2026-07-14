from __future__ import annotations

import json

from fastapi import HTTPException, status

from app.core.logging import logger
from app.integrations.insforge_client import get_insforge_admin
from app.schemas.admin import (
    AdminOrgItem,
    AdminOrgListResponse,
    AdminUsageResponse,
    AuditLogItem,
    AuditLogListResponse,
    SystemLogItem,
    SystemLogListResponse,
)
from app.schemas.auth import UserContext


class AdminService:
    """Business logic for platform admin operations.

    Cross-organization visibility — requires platform_admin role.
    """

    def __init__(self) -> None:
        self.db = get_insforge_admin()

    async def list_organizations(
        self,
        current_user: UserContext,
        page: int = 1,
        per_page: int = 20,
    ) -> AdminOrgListResponse:
        """List all organizations on the platform."""
        self._require_platform_admin(current_user)

        try:
            all_rows = await self.db.database.from_("organizations") \
                .select("*") \
                .order("created_at", desc=True) \
                .execute()
            all_rows = all_rows if isinstance(all_rows, list) else []
        except Exception as exc:
            logger.error("admin.orgs_list_failed", error=str(exc))
            all_rows = []

        total = len(all_rows)
        offset = (page - 1) * per_page
        rows = all_rows[offset: offset + per_page]

        orgs = []
        for r in rows:
            org_id = str(r.get("id", ""))

            # Member count
            member_count = await self._count_table("users", org_id)

            # Call stats
            call_stats = await self._get_call_stats(org_id)

            orgs.append(AdminOrgItem(
                id=org_id,
                name=r.get("name", ""),
                plan=r.get("plan"),
                member_count=member_count,
                total_calls=call_stats.get("total_calls", 0),
                total_minutes=call_stats.get("total_minutes", 0.0),
                is_active=r.get("is_active", True),
                created_at=str(r.get("created_at", "")) if r.get("created_at") else None,
            ))

        return AdminOrgListResponse(organizations=orgs, total=total)

    async def get_platform_usage(self, current_user: UserContext) -> AdminUsageResponse:
        """Get platform-wide usage statistics."""
        self._require_platform_admin(current_user)

        total_orgs = await self._count_all("organizations")
        total_users = await self._count_all("users")
        total_calls = await self._count_all("call_runs")
        total_campaigns = await self._count_all("campaigns")

        # Active campaigns
        try:
            active_rows = await self.db.database.from_("campaigns") \
                .select("id") \
                .eq("status", "running") \
                .execute()
            active_campaigns = len(active_rows) if isinstance(active_rows, list) else 0
        except Exception:
            active_campaigns = 0

        # Total minutes
        try:
            all_calls = await self.db.database.from_("call_runs") \
                .select("duration_seconds") \
                .execute()
            all_calls = all_calls if isinstance(all_calls, list) else []
            total_minutes = sum(
                float(c.get("duration_seconds", 0)) for c in all_calls
            ) / 60.0
        except Exception:
            total_minutes = 0.0

        # Total agents from mappings
        total_agents = await self._count_all("dograh_agent_mappings")

        return AdminUsageResponse(
            total_organizations=total_orgs,
            total_users=total_users,
            total_calls=total_calls,
            total_minutes=round(total_minutes, 2),
            total_campaigns=total_campaigns,
            active_campaigns=active_campaigns,
            total_agents=total_agents,
        )

    async def get_audit_log(
        self,
        current_user: UserContext,
        page: int = 1,
        per_page: int = 50,
    ) -> AuditLogListResponse:
        """Get full audit trail across all organizations."""
        self._require_platform_admin(current_user)

        try:
            all_rows = await self.db.database.from_("audit_log") \
                .select("*") \
                .order("created_at", desc=True) \
                .execute()
            all_rows = all_rows if isinstance(all_rows, list) else []
        except Exception as exc:
            logger.error("admin.audit_log_failed", error=str(exc))
            all_rows = []

        total = len(all_rows)
        offset = (page - 1) * per_page
        rows = all_rows[offset: offset + per_page]

        logs = []
        for r in rows:
            details = r.get("details")
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except (json.JSONDecodeError, TypeError):
                    details = None

            logs.append(AuditLogItem(
                id=str(r.get("id", "")),
                organization_id=str(r.get("organization_id", "")) if r.get("organization_id") else None,
                user_id=str(r.get("user_id", "")) if r.get("user_id") else None,
                action=r.get("action", ""),
                resource_type=r.get("resource_type"),
                resource_id=str(r.get("resource_id", "")) if r.get("resource_id") else None,
                details=details,
                ip_address=r.get("ip_address"),
                created_at=str(r.get("created_at", "")) if r.get("created_at") else None,
            ))

        return AuditLogListResponse(logs=logs, total=total)

    async def get_system_logs(
        self,
        current_user: UserContext,
        page: int = 1,
        per_page: int = 50,
        level: str | None = None,
    ) -> SystemLogListResponse:
        """Get system-wide logs."""
        self._require_platform_admin(current_user)

        try:
            query = self.db.database.from_("system_logs") \
                .select("*") \
                .order("created_at", desc=True)

            if level:
                query = query.eq("level", level)

            all_rows = await query.execute()
            all_rows = all_rows if isinstance(all_rows, list) else []
        except Exception as exc:
            logger.error("admin.system_logs_failed", error=str(exc))
            all_rows = []

        total = len(all_rows)
        offset = (page - 1) * per_page
        rows = all_rows[offset: offset + per_page]

        logs = []
        for r in rows:
            details = r.get("details")
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except (json.JSONDecodeError, TypeError):
                    details = None

            logs.append(SystemLogItem(
                id=str(r.get("id", "")),
                level=r.get("level", "info"),
                message=r.get("message", ""),
                source=r.get("source"),
                details=details,
                created_at=str(r.get("created_at", "")) if r.get("created_at") else None,
            ))

        return SystemLogListResponse(logs=logs, total=total)

    # ------------------------------------------------------------------ #
    #  Private helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _require_platform_admin(current_user: UserContext) -> None:
        """Guard: only platform_admin can access admin endpoints."""
        if current_user.role != "platform_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform admin access required",
            )

    async def _count_table(self, table: str, org_id: str) -> int:
        """Count rows in a table scoped to an org."""
        try:
            rows = await self.db.database.from_(table) \
                .select("id") \
                .eq("organization_id", org_id) \
                .execute()
            return len(rows) if isinstance(rows, list) else 0
        except Exception:
            return 0

    async def _count_all(self, table: str) -> int:
        """Count all rows in a table (cross-org)."""
        try:
            rows = await self.db.database.from_(table) \
                .select("id") \
                .execute()
            return len(rows) if isinstance(rows, list) else 0
        except Exception:
            return 0

    async def _get_call_stats(self, org_id: str) -> dict:
        """Get call count and total minutes for an org."""
        try:
            rows = await self.db.database.from_("call_runs") \
                .select("id,duration_seconds") \
                .eq("organization_id", org_id) \
                .execute()
            rows = rows if isinstance(rows, list) else []
            total_calls = len(rows)
            total_minutes = sum(float(r.get("duration_seconds", 0)) for r in rows) / 60.0
            return {"total_calls": total_calls, "total_minutes": round(total_minutes, 2)}
        except Exception:
            return {"total_calls": 0, "total_minutes": 0.0}
