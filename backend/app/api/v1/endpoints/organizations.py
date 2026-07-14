from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.security import CurrentUserDep, require_role
from app.schemas.organization import (
    MemberInvite,
    MemberListResponse,
    MemberResponse,
    MemberRoleUpdate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.services.org_service import OrgService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/me")
async def get_my_organization(current_user: CurrentUserDep) -> OrganizationResponse:
    """Get the current user's organization details."""
    service = OrgService()
    return await service.get_organization(current_user)


@router.patch("/me")
async def update_my_organization(
    data: OrganizationUpdate,
    current_user: CurrentUserDep,
    _: None = Depends(require_role("owner", "admin")),
) -> OrganizationResponse:
    """Update organization settings. Owner or admin only."""
    service = OrgService()
    return await service.update_organization(data, current_user)


@router.get("/me/members")
async def list_members(current_user: CurrentUserDep) -> MemberListResponse:
    """List all members of the current organization."""
    service = OrgService()
    return await service.list_members(current_user)


@router.post("/me/members", status_code=status.HTTP_201_CREATED)
async def invite_member(
    data: MemberInvite,
    current_user: CurrentUserDep,
    _: None = Depends(require_role("owner", "admin")),
) -> MemberResponse:
    """Invite a new member to the organization. Admin+ only."""
    service = OrgService()
    return await service.invite_member(data, current_user)


@router.patch("/me/members/{user_id}")
async def update_member_role(
    user_id: str,
    data: MemberRoleUpdate,
    current_user: CurrentUserDep,
    _: None = Depends(require_role("owner")),
) -> MemberResponse:
    """Update a member's role. Owner only."""
    service = OrgService()
    return await service.update_member_role(user_id, data, current_user)


@router.delete("/me/members/{user_id}")
async def remove_member(
    user_id: str,
    current_user: CurrentUserDep,
    _: None = Depends(require_role("owner", "admin")),
) -> dict:
    """Remove a member from the organization. Admin+ only."""
    service = OrgService()
    return await service.remove_member(user_id, current_user)
