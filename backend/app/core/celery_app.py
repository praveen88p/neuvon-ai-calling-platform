from __future__ import annotations

from functools import lru_cache

from celery import Celery

from app.core.config import get_settings


@lru_cache
def get_celery_app() -> Celery:
    """Lazy-initialized Celery app singleton."""
    settings = get_settings()

    app = Celery(
        "neuvon",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
    )

    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )

    return app
