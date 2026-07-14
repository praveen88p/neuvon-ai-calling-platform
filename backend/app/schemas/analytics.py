from __future__ import annotations

from pydantic import BaseModel, Field


class AnalyticsOverview(BaseModel):
    """KPI summary cards for the analytics dashboard."""

    total_calls: int = Field(default=0, description="Total calls in the period")
    total_minutes: float = Field(default=0.0, description="Total call duration in minutes")
    average_duration_seconds: float = Field(default=0.0, description="Average call duration")
    success_rate: float = Field(default=0.0, description="Percentage of successful calls")
    total_campaigns: int = Field(default=0, description="Active campaigns in the period")
    total_agents: int = Field(default=0, description="Active agents used")
    total_cost_usd: float = Field(default=0.0, description="Total cost in USD")


class TimeSeriesPoint(BaseModel):
    """A single data point on a time-series chart."""

    date: str = Field(..., description="ISO date string (YYYY-MM-DD)")
    calls: int = Field(default=0)
    minutes: float = Field(default=0.0)
    success_count: int = Field(default=0)
    failed_count: int = Field(default=0)


class CallsOverTimeResponse(BaseModel):
    """Time series data for line/bar charts."""

    data: list[TimeSeriesPoint] = Field(default_factory=list)
    start_date: str
    end_date: str


class DispositionItem(BaseModel):
    """Single disposition bucket in the breakdown."""

    disposition: str = Field(..., description="Disposition code or label")
    count: int = Field(default=0)
    percentage: float = Field(default=0.0)


class DispositionBreakdownResponse(BaseModel):
    """Call outcomes breakdown for pie/donut charts."""

    data: list[DispositionItem] = Field(default_factory=list)
    total_calls: int = Field(default=0)


class AgentPerformanceItem(BaseModel):
    """Per-agent metrics row."""

    agent_id: int
    agent_name: str = Field(default="Unknown Agent")
    total_calls: int = Field(default=0)
    total_minutes: float = Field(default=0.0)
    average_duration_seconds: float = Field(default=0.0)
    success_rate: float = Field(default=0.0)
    total_cost_usd: float = Field(default=0.0)


class AgentPerformanceResponse(BaseModel):
    """Per-agent metrics table."""

    data: list[AgentPerformanceItem] = Field(default_factory=list)


class CampaignPerformanceItem(BaseModel):
    """Per-campaign metrics row."""

    campaign_id: str
    campaign_name: str = Field(default="Unknown Campaign")
    total_calls: int = Field(default=0)
    total_minutes: float = Field(default=0.0)
    completed_calls: int = Field(default=0)
    success_rate: float = Field(default=0.0)
    status: str = Field(default="unknown")


class CampaignPerformanceResponse(BaseModel):
    """Per-campaign metrics table."""

    data: list[CampaignPerformanceItem] = Field(default_factory=list)
