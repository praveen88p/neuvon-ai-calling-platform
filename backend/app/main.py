from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.logging import logger, setup_logging
from app.core.middleware import setup_middleware


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
