from __future__ import annotations

from pydantic import BaseModel, Field


# --- Organization Settings (read-only for clients) ---

class OrgSettingsResponse(BaseModel):
    """Output schema for organization settings (read-only for clients)."""

    id: str
    name: str
    created_at: str | None = None


# --- User Profile ---

class ProfileResponse(BaseModel):
    """Output schema for user profile."""

    user_id: str
    email: str
    full_name: str
    role: str
    organization_id: str
    phone: str | None = None
    avatar_url: str | None = None
    notification_preferences: dict | None = None
    created_at: str | None = None


class ProfileUpdate(BaseModel):
    """Input schema for updating user profile."""

    full_name: str | None = Field(None, min_length=1, max_length=200)
    phone: str | None = Field(None, max_length=20)
    avatar_url: str | None = Field(None, max_length=500)
    notification_preferences: dict | None = None
