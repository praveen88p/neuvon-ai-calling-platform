from __future__ import annotations

from functools import lru_cache

from insforge import InsforgeClient

from app.core.config import get_settings


@lru_cache
def get_insforge_client() -> InsforgeClient:
    """Cached InsForge client using anon key for user-scoped operations."""
    settings = get_settings()
    return InsforgeClient(
        base_url=settings.INSFORGE_URL,
        api_key=settings.INSFORGE_ANON_KEY,
    )


@lru_cache
def get_insforge_admin() -> InsforgeClient:
    """Cached InsForge client with service key for admin/cross-org operations."""
    settings = get_settings()
    return InsforgeClient(
        base_url=settings.INSFORGE_URL,
        api_key=settings.INSFORGE_SERVICE_KEY,
    )
