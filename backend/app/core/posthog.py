from __future__ import annotations

from functools import lru_cache

from posthog import Posthog

from app.core.config import get_settings


@lru_cache
def _get_posthog_client() -> Posthog:
    """Lazy-initialized PostHog client singleton."""
    settings = get_settings()
    return Posthog(
        project_api_key=settings.POSTHOG_API_KEY,
        host=settings.POSTHOG_HOST,
    )


def track_event(
    distinct_id: str,
    event: str,
    properties: dict | None = None,
) -> None:
    """Track a PostHog event server-side.

    Always use str(org_id) as distinct_id for org-level tracking.
    Event names must match code-standards.md PostHog events list.
    """
    client = _get_posthog_client()
    client.capture(
        distinct_id=distinct_id,
        event=event,
        properties=properties or {},
    )
