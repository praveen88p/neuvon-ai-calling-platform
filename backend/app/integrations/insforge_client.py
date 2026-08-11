from __future__ import annotations

from functools import lru_cache

from insforge import InsforgeClient

from app.core.config import get_settings


@lru_cache
def get_insforge_client() -> InsforgeClient:
    """Cached InsForge client using anon key for user-scoped operations.

    Safe to cache because FastAPI has a persistent event loop.
    """
    settings = get_settings()
    return InsforgeClient(
        base_url=settings.INSFORGE_URL,
        api_key=settings.INSFORGE_ANON_KEY,
    )


# NOTE: NOT cached — Celery tasks run each in a fresh event loop.
# A cached httpx.AsyncClient would be bound to the previous (closed) loop,
# causing RuntimeError('Event loop is closed') on the second task run.
def get_insforge_admin() -> InsforgeClient:
    """Fresh InsForge client with service key for admin/cross-org operations.

    Returns a new client each call so Celery tasks always get an httpx client
    bound to the current (live) event loop.
    """
    settings = get_settings()
    return InsforgeClient(
        base_url=settings.INSFORGE_URL,
        api_key=settings.INSFORGE_SERVICE_KEY,
    )
