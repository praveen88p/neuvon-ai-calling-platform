from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUserDep
from app.schemas.admin import (
    AdminOrgListResponse,
    AdminUsageResponse,
    AuditLogListResponse,
    SystemLogListResponse,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/organizations", response_model=AdminOrgListResponse)
async def list_organizations(
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> AdminOrgListResponse:
    """List all organizations on the platform. Platform admin only."""
    service = AdminService()
    return await service.list_organizations(current_user, page, per_page)


@router.get("/usage", response_model=AdminUsageResponse)
async def get_platform_usage(current_user: CurrentUserDep) -> AdminUsageResponse:
    """Get platform-wide usage statistics. Platform admin only."""
    service = AdminService()
    return await service.get_platform_usage(current_user)


@router.get("/audit", response_model=AuditLogListResponse)
async def get_audit_log(
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
) -> AuditLogListResponse:
    """Get full audit trail across all organizations. Platform admin only."""
    service = AdminService()
    return await service.get_audit_log(current_user, page, per_page)


@router.get("/logs", response_model=SystemLogListResponse)
async def get_system_logs(
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    level: str | None = Query(None),
) -> SystemLogListResponse:
    """Get system-wide logs. Platform admin only."""
    service = AdminService()
    return await service.get_system_logs(current_user, page, per_page, level)
