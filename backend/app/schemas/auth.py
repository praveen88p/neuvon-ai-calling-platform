from __future__ import annotations

from pydantic import BaseModel, Field


# --- Request schemas ---

class RegisterRequest(BaseModel):
    """Input for user registration."""

    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    organization_name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    """Input for user login."""

    email: str
    password: str


class RefreshRequest(BaseModel):
    """Input for token refresh."""

    refresh_token: str


# --- Response schemas ---

class AuthTokens(BaseModel):
    """JWT token pair returned on login/register/refresh."""

    access_token: str
    refresh_token: str


class UserContext(BaseModel):
    """Current user context — returned from /auth/me and injected by get_current_user."""

    user_id: str
    organization_id: str
    email: str
    full_name: str
    role: str  # "platform_admin" | "owner" | "admin" | "member"


class RegisterResponse(BaseModel):
    """Response after successful registration."""

    tokens: AuthTokens
    user: UserContext


class LoginResponse(BaseModel):
    """Response after successful login."""

    tokens: AuthTokens
    user: UserContext


class MeResponse(BaseModel):
    """Response for GET /auth/me."""

    user: UserContext
