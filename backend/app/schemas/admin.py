from __future__ import annotations

from pydantic import BaseModel


# --- Admin Responses ---

class AdminOrgItem(BaseModel):
    """Organization item in admin listing."""

    id: str
    name: str
    plan: str | None = None
    member_count: int = 0
    total_calls: int = 0
    total_minutes: float = 0.0
    is_active: bool = True
    created_at: str | None = None


class AdminOrgListResponse(BaseModel):
    """Paginated list of all organizations."""

    organizations: list[AdminOrgItem] = []
    total: int = 0


class AdminUsageResponse(BaseModel):
    """Platform-wide usage statistics."""

    total_organizations: int = 0
    total_users: int = 0
    total_calls: int = 0
    total_minutes: float = 0.0
    total_campaigns: int = 0
    active_campaigns: int = 0
    total_agents: int = 0


class AuditLogItem(BaseModel):
    """Single audit log entry."""

    id: str
    organization_id: str | None = None
    user_id: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict | None = None
    ip_address: str | None = None
    created_at: str | None = None


class AuditLogListResponse(BaseModel):
    """Paginated audit log."""

    logs: list[AuditLogItem] = []
    total: int = 0


class SystemLogItem(BaseModel):
    """System log entry."""

    id: str
    level: str
    message: str
    source: str | None = None
    details: dict | None = None
    created_at: str | None = None


class SystemLogListResponse(BaseModel):
    """Paginated system logs."""

    logs: list[SystemLogItem] = []
    total: int = 0
