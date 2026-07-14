from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.logging import logger
from app.integrations.insforge_client import get_insforge_admin, get_insforge_client
from app.schemas.auth import UserContext

security_scheme = HTTPBearer()

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)],
) -> UserContext:
    """Validate InsForge JWT and return user context.

    Uses InsForge's get_current_session to verify the access token,
    then looks up the user's org membership and role from local DB.
    """
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    try:
        insforge = get_insforge_client()
        session = await insforge.auth.get_current_session(access_token=token)
    except Exception as exc:
        logger.warning("auth.token_invalid", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    if not session or not session.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        )

    insforge_user = session.user

    # Look up user record in our local users table via InsForge DB (admin bypasses RLS)
    try:
        admin_client = get_insforge_admin()
        response = await admin_client.database.from_("users") \
            .select("id,organization_id,email,full_name,role,is_active") \
            .eq("id", str(insforge_user.id)) \
            .execute()

        rows = response if isinstance(response, list) else []

        if not rows:
            logger.warning("auth.user_not_found", insforge_user_id=insforge_user.id)
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

        return UserContext(
            user_id=str(user_row["id"]),
            organization_id=str(user_row["organization_id"]),
            email=user_row["email"],
            full_name=user_row.get("full_name", ""),
            role=user_row["role"],
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("auth.user_lookup_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user context",
        ) from exc


def require_role(*allowed_roles: str):
    """Dependency factory that checks the user's role against allowed roles.

    Usage: dependencies=[Depends(require_role("owner", "admin"))]
    """

    async def role_checker(
        current_user: Annotated[UserContext, Depends(get_current_user)],
    ) -> UserContext:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker


# Reusable dependency aliases
CurrentUserDep = Annotated[UserContext, Depends(get_current_user)]
