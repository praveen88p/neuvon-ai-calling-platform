from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --- Request schemas ---

class OrganizationUpdate(BaseModel):
    """Input for updating organization settings."""

    name: str | None = Field(None, min_length=1, max_length=200)
    white_label: dict | None = None  # { display_name, logo_url, primary_color, favicon_url }


class MemberInvite(BaseModel):
    """Input for inviting a new member to the organization."""

    email: str = Field(min_length=5, max_length=255)
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="member")  # "admin" | "member"


class MemberRoleUpdate(BaseModel):
    """Input for updating a member's role."""

    role: str = Field(min_length=1)  # "admin" | "member"


# --- Response schemas ---

class OrganizationResponse(BaseModel):
    """Output schema for organization data."""

    id: str
    name: str
    slug: str
    org_type: str
    white_label: dict | None = None
    billing_plan: str
    usage_quota: dict | None = None
    is_active: bool
    created_at: str


class MemberResponse(BaseModel):
    """Output schema for organization member."""

    user_id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    last_login_at: str | None = None
    created_at: str


class MemberListResponse(BaseModel):
    """Output schema for listing members."""

    members: list[MemberResponse]
    total: int
