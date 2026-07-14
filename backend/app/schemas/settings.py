from __future__ import annotations

from pydantic import BaseModel, Field


# --- Organization Settings ---

class OrgSettingsResponse(BaseModel):
    """Output schema for organization settings."""

    id: str
    name: str
    display_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    webhook_url: str | None = None
    timezone: str | None = None
    created_at: str | None = None


class OrgSettingsUpdate(BaseModel):
    """Input schema for updating organization settings."""

    display_name: str | None = Field(None, max_length=200)
    logo_url: str | None = Field(None, max_length=500)
    primary_color: str | None = Field(None, max_length=20)
    webhook_url: str | None = Field(None, max_length=500)
    timezone: str | None = Field(None, max_length=50)


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


# --- API Keys ---

class ApiKeyCreateRequest(BaseModel):
    """Input schema for creating an API key."""

    name: str = Field(..., min_length=1, max_length=100)
    expires_in_days: int | None = Field(None, ge=1, le=365)


class ApiKeyResponse(BaseModel):
    """Output schema for an API key (key is masked)."""

    id: str
    organization_id: str
    name: str
    key_prefix: str
    is_active: bool = True
    expires_at: str | None = None
    created_at: str | None = None
    last_used_at: str | None = None


class ApiKeyCreatedResponse(BaseModel):
    """Output schema returned only on creation — includes the full key."""

    id: str
    organization_id: str
    name: str
    key: str
    key_prefix: str
    expires_at: str | None = None
    created_at: str | None = None


class ApiKeyListResponse(BaseModel):
    """Paginated list of API keys."""

    keys: list[ApiKeyResponse] = []
    total: int = 0
