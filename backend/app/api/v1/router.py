from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import admin, agents, analytics, appointments, auth, availability, billing, calls, campaigns, health, live_calls, organizations, settings, telephony, topup, webhooks

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(agents.router)
api_router.include_router(calls.router)
api_router.include_router(campaigns.router)
api_router.include_router(analytics.router)
api_router.include_router(billing.router)
api_router.include_router(topup.router)
api_router.include_router(appointments.router)
api_router.include_router(availability.router)
api_router.include_router(settings.router)
api_router.include_router(live_calls.router)
api_router.include_router(telephony.router)
api_router.include_router(webhooks.router)
api_router.include_router(admin.router)




