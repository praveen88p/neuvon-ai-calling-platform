from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import CurrentUserDep
from app.schemas.analytics import (
    AgentPerformanceResponse,
    AnalyticsOverview,
    CallsOverTimeResponse,
    CampaignPerformanceResponse,
    DispositionBreakdownResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def get_analytics_overview(
    current_user: CurrentUserDep,
    start_date: str | None = Query(None, description="ISO date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="ISO date (YYYY-MM-DD)"),
) -> AnalyticsOverview:
    """KPI cards — total calls, minutes, success rate, cost."""
    service = AnalyticsService()
    return await service.get_overview(current_user, start_date, end_date)


@router.get("/calls-over-time", response_model=CallsOverTimeResponse)
async def get_calls_over_time(
    current_user: CurrentUserDep,
    start_date: str | None = Query(None, description="ISO date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="ISO date (YYYY-MM-DD)"),
) -> CallsOverTimeResponse:
    """Time series data for line/bar charts — grouped by day."""
    service = AnalyticsService()
    return await service.get_calls_over_time(current_user, start_date, end_date)


@router.get("/disposition-breakdown", response_model=DispositionBreakdownResponse)
async def get_disposition_breakdown(
    current_user: CurrentUserDep,
    start_date: str | None = Query(None, description="ISO date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="ISO date (YYYY-MM-DD)"),
) -> DispositionBreakdownResponse:
    """Call outcomes breakdown for pie/donut charts."""
    service = AnalyticsService()
    return await service.get_disposition_breakdown(current_user, start_date, end_date)


@router.get("/agent-performance", response_model=AgentPerformanceResponse)
async def get_agent_performance(
    current_user: CurrentUserDep,
    start_date: str | None = Query(None, description="ISO date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="ISO date (YYYY-MM-DD)"),
) -> AgentPerformanceResponse:
    """Per-agent metrics table."""
    service = AnalyticsService()
    return await service.get_agent_performance(current_user, start_date, end_date)


@router.get("/campaign-performance", response_model=CampaignPerformanceResponse)
async def get_campaign_performance(
    current_user: CurrentUserDep,
    start_date: str | None = Query(None, description="ISO date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="ISO date (YYYY-MM-DD)"),
) -> CampaignPerformanceResponse:
    """Per-campaign metrics table."""
    service = AnalyticsService()
    return await service.get_campaign_performance(current_user, start_date, end_date)
