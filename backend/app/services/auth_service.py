from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.logging import logger
from app.core.posthog import track_event
from app.integrations.insforge_client import get_insforge_admin, get_insforge_client
from app.schemas.auth import (
    AuthTokens,
    LoginRequest,
    LoginResponse,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    UserContext,
)


class AuthService:
    """Business logic for authentication and user management."""

    def __init__(self) -> None:
        self.insforge = get_insforge_client()
        self.insforge_admin = get_insforge_admin()

    async def register(self, data: RegisterRequest) -> RegisterResponse:
        """Register a new user and create their organization.

        Flow:
        1. Create user in InsForge Auth
        2. Create organization in local DB
        3. Create user record in local DB with owner role
        4. Return tokens + user context
        """
        # 1. Create InsForge auth user
        try:
            auth_result = await self.insforge.auth.create_user(
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
            logger.error("auth.register_failed", email=data.email, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create account",
            ) from exc

        insforge_user_id = str(auth_result.user.id) if auth_result.user else None
        if not insforge_user_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Account creation returned no user ID",
            )

        # 2. Create organization via InsForge query builder
        org_id = str(uuid4())
        slug = self._generate_slug(data.organization_name)

        try:
            await self.insforge_admin.database.from_("organizations").insert(
                [{
                    "id": org_id,
                    "name": data.organization_name,
                    "slug": slug,
                    "org_type": "direct",
                    "billing_plan": "free",
                    "is_active": True,
                }]
            )
        except Exception as exc:
            logger.error("auth.org_creation_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create organization",
            ) from exc

        # 3. Create user record with owner role
        try:
            await self.insforge_admin.database.from_("users").insert(
                [{
                    "id": insforge_user_id,
                    "organization_id": org_id,
                    "email": data.email,
                    "full_name": data.full_name,
                    "role": "owner",
                    "is_active": True,
                }]
            )
        except Exception as exc:
            logger.error("auth.user_record_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user record",
            ) from exc

        tokens = AuthTokens(
            access_token=auth_result.access_token,
            refresh_token=auth_result.refresh_token,
        )
        user_context = UserContext(
            user_id=insforge_user_id,
            organization_id=org_id,
            email=data.email,
            full_name=data.full_name,
            role="owner",
        )

        track_event(
            distinct_id=org_id,
            event="user_registered",
            properties={"user_id": insforge_user_id, "org_id": org_id},
        )

        logger.info("auth.registered", user_id=insforge_user_id, org_id=org_id)
        return RegisterResponse(tokens=tokens, user=user_context)

    async def login(self, data: LoginRequest) -> LoginResponse:
        """Authenticate user and return tokens + context."""
        try:
            auth_result = await self.insforge.auth.sign_in_with_password(
                email=data.email,
                password=data.password,
            )
        except Exception as exc:
            logger.warning("auth.login_failed", email=data.email, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            ) from exc

        # Get user record for org context
        try:
            session = await self.insforge.auth.get_current_session(
                access_token=auth_result.access_token,
            )
            insforge_user_id = str(session.user.id)

            rows = await self.insforge_admin.database.from_("users") \
                .select("id,organization_id,email,full_name,role,is_active") \
                .eq("id", insforge_user_id) \
                .execute()

            rows = rows if isinstance(rows, list) else []

            if not rows:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User not registered in any organization",
                )

            user_row = rows[0]
            if not user_row.get("is_active", True):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is deactivated",
                )

            # Update last_login_at
            now_iso = datetime.now(timezone.utc).isoformat()
            try:
                await self.insforge_admin.database.from_("users") \
                    .eq("id", insforge_user_id) \
                    .update({"last_login_at": now_iso}, return_representation=True)
            except json.JSONDecodeError:
                pass

        except HTTPException:
            raise
        except Exception as exc:
            logger.error("auth.context_lookup_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user context",
            ) from exc

        tokens = AuthTokens(
            access_token=auth_result.access_token,
            refresh_token=auth_result.refresh_token,
        )
        user_context = UserContext(
            user_id=str(user_row["id"]),
            organization_id=str(user_row["organization_id"]),
            email=user_row["email"],
            full_name=user_row.get("full_name", ""),
            role=user_row["role"],
        )

        track_event(
            distinct_id=str(user_row["organization_id"]),
            event="user_logged_in",
            properties={
                "user_id": str(user_row["id"]),
                "org_id": str(user_row["organization_id"]),
            },
        )

        logger.info("auth.logged_in", user_id=str(user_row["id"]))
        return LoginResponse(tokens=tokens, user=user_context)

    async def refresh(self, data: RefreshRequest) -> AuthTokens:
        """Refresh the JWT token pair using a valid refresh token."""
        try:
            result = await self.insforge.auth.refresh(refresh_token=data.refresh_token)
            return AuthTokens(
                access_token=result.access_token,
                refresh_token=result.refresh_token,
            )
        except Exception as exc:
            logger.warning("auth.refresh_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            ) from exc

    async def logout(self, access_token: str) -> dict:
        """Invalidate the current session."""
        try:
            await self.insforge.auth.logout()
        except Exception as exc:
            logger.warning("auth.logout_failed", error=str(exc))
        return {"message": "Logged out successfully"}

    async def get_me(self, current_user: UserContext) -> MeResponse:
        """Return current user context — already resolved by dependency."""
        return MeResponse(user=current_user)

    @staticmethod
    def _generate_slug(name: str) -> str:
        """Generate a URL-friendly slug from an organization name."""
        slug = name.lower().strip()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        # Append short uuid suffix for uniqueness
        suffix = uuid4().hex[:6]
        return f"{slug}-{suffix}"
