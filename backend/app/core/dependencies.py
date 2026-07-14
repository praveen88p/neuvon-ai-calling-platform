from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.security import CurrentUserDep, get_current_user
from app.schemas.auth import UserContext

# Canonical dependency type aliases — import from here, not from security.py
SettingsDep = Annotated[Settings, Depends(get_settings)]

__all__ = [
    "SettingsDep",
    "CurrentUserDep",
    "get_current_user",
    "UserContext",
]
