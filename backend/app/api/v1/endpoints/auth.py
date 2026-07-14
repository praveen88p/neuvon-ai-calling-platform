from __future__ import annotations

from fastapi import APIRouter, status

from app.core.security import CurrentUserDep
from app.schemas.auth import (
    AuthTokens,
    LoginRequest,
    LoginResponse,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest) -> RegisterResponse:
    """Create a new account with email/password.

    Creates InsForge auth user, a new organization, and a user record
    with the 'owner' role. Returns JWT tokens and user context.
    """
    service = AuthService()
    return await service.register(data)


@router.post("/login")
async def login(data: LoginRequest) -> LoginResponse:
    """Authenticate with email/password and return JWT tokens."""
    service = AuthService()
    return await service.login(data)


@router.post("/refresh")
async def refresh(data: RefreshRequest) -> AuthTokens:
    """Refresh the JWT access token using a valid refresh token."""
    service = AuthService()
    return await service.refresh(data)


@router.post("/logout")
async def logout(current_user: CurrentUserDep) -> dict:
    """Invalidate the current session."""
    service = AuthService()
    return await service.logout(access_token="")


@router.get("/me")
async def me(current_user: CurrentUserDep) -> MeResponse:
    """Get current authenticated user with organization context."""
    service = AuthService()
    return await service.get_me(current_user)
