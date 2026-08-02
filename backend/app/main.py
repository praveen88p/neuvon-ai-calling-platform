from __future__ import annotations

from contextlib import asynccontextmanager

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import logger, setup_logging
from app.core.middleware import setup_middleware


# ── Sentry Initialization ────────────────────────────────────────────────────
_settings = get_settings()
if _settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=_settings.SENTRY_DSN,
        environment=_settings.ENVIRONMENT,
        # Only load the integrations we actually use — avoids Celery/Kombu
        # entry_points scan that causes TimeoutError on Python 3.14.
        integrations=[
            FastApiIntegration(),
            StarletteIntegration(),
        ],
        auto_enabling_integrations=False,
        # Capture 20% of transactions for performance monitoring
        traces_sample_rate=0.2,
        # Capture all errors (100%)
        sample_rate=1.0,
        # Send user IP for debugging
        send_default_pii=True,
        # Attach request data to error events
        max_request_body_size="medium",
    )
    logger.info("sentry.initialized", environment=_settings.ENVIRONMENT)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown events."""
    setup_logging()
    logger.info("app.startup", message="Neuvon backend starting")
    yield
    logger.info("app.shutdown", message="Neuvon backend shutting down")


app = FastAPI(
    title="Neuvon AI Calling Platform",
    description="White-label AI calling platform API — backend middleware between frontend and Dograh voice engine.",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware
setup_middleware(app)

# Routes
app.include_router(api_router)
