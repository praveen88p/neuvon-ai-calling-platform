from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # InsForge
    INSFORGE_URL: str
    INSFORGE_ANON_KEY: str
    INSFORGE_SERVICE_KEY: str

    # Dograh
    DOGRAH_BASE_URL: str
    DOGRAH_API_KEY: str

    # Security
    SECRET_KEY: str

    # Razorpay
    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # PostHog
    POSTHOG_API_KEY: str
    POSTHOG_HOST: str = "https://us.i.posthog.com"

    # Redis
    REDIS_URL: str

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://localhost:3000",
    ]

    # Webhook
    WEBHOOK_SECRET: str = ""

    # Sentry
    SENTRY_DSN: str = ""
    ENVIRONMENT: str = "development"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
