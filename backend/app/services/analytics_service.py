from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.core.logging import logger
from app.integrations.insforge_client import get_insforge_admin
from app.schemas.analytics import (
    AgentPerformanceItem,
    AgentPerformanceResponse,
    AnalyticsOverview,
    CallsOverTimeResponse,
    CampaignPerformanceItem,
    CampaignPerformanceResponse,
    DispositionBreakdownResponse,
    DispositionItem,
    TimeSeriesPoint,
)
from app.schemas.auth import UserContext


class AnalyticsService:
    """Server-side analytics aggregation from local call_runs data.

    All queries scoped to current organization. Supports date range
    filtering via start_date / end_date ISO strings.
    """

    def __init__(self) -> None:
        self.db = get_insforge_admin()

    async def get_overview(
        self,
        current_user: UserContext,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AnalyticsOverview:
        """KPI summary: total calls, minutes, success rate, cost."""
        org_id = current_user.organization_id
        runs = await self._fetch_runs(org_id, start_date, end_date)

        if not runs:
            return AnalyticsOverview()

        total_calls = len(runs)
        total_seconds = sum(r.get("duration_seconds", 0) or 0 for r in runs)
        total_minutes = round(total_seconds / 60, 2)
        avg_duration = round(total_seconds / total_calls, 1) if total_calls else 0.0

        completed = sum(1 for r in runs if r.get("status") == "completed")
        success_rate = round((completed / total_calls) * 100, 1) if total_calls else 0.0

        total_cost = 0.0
        for r in runs:
            cost_info = r.get("cost_info")
            if isinstance(cost_info, dict):
                total_cost += cost_info.get("total_cost", 0) or 0

        unique_agents = len({r.get("dograh_workflow_id") for r in runs if r.get("dograh_workflow_id")})
        unique_campaigns = len({str(r.get("campaign_id")) for r in runs if r.get("campaign_id")})

        return AnalyticsOverview(
            total_calls=total_calls,
            total_minutes=total_minutes,
            average_duration_seconds=avg_duration,
            success_rate=success_rate,
            total_campaigns=unique_campaigns,
            total_agents=unique_agents,
            total_cost_usd=round(total_cost, 2),
        )

    async def get_calls_over_time(
        self,
        current_user: UserContext,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> CallsOverTimeResponse:
        """Time series data for line/bar charts — grouped by day."""
        org_id = current_user.organization_id
        s_date, e_date = self._resolve_date_range(start_date, end_date)
        runs = await self._fetch_runs(org_id, s_date.isoformat(), e_date.isoformat())

        daily: dict[str, dict] = {}
        current = s_date
        while current <= e_date:
            key = current.isoformat()
            daily[key] = {"calls": 0, "minutes": 0.0, "success": 0, "failed": 0}
            current += timedelta(days=1)

        for r in runs:
            created = r.get("created_at", "")
            day_key = created[:10] if isinstance(created, str) else ""
            if day_key in daily:
                daily[day_key]["calls"] += 1
                dur = (r.get("duration_seconds", 0) or 0) / 60
                daily[day_key]["minutes"] = round(daily[day_key]["minutes"] + dur, 2)
                if r.get("status") == "completed":
                    daily[day_key]["success"] += 1
                elif r.get("status") == "failed":
                    daily[day_key]["failed"] += 1

        data = [
            TimeSeriesPoint(
                date=day,
                calls=vals["calls"],
                minutes=vals["minutes"],
                success_count=vals["success"],
                failed_count=vals["failed"],
            )
            for day, vals in sorted(daily.items())
        ]

        return CallsOverTimeResponse(
            data=data,
            start_date=s_date.isoformat(),
            end_date=e_date.isoformat(),
        )

    async def get_disposition_breakdown(
        self,
        current_user: UserContext,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> DispositionBreakdownResponse:
        """Call outcomes breakdown for pie/donut charts."""
        org_id = current_user.organization_id
        runs = await self._fetch_runs(org_id, start_date, end_date)

        total = len(runs)
        if total == 0:
            return DispositionBreakdownResponse()

        counts: dict[str, int] = defaultdict(int)
        for r in runs:
            disp = r.get("disposition") or r.get("status") or "unknown"
            counts[disp] += 1

        data = [
            DispositionItem(
                disposition=disp,
                count=count,
                percentage=round((count / total) * 100, 1),
            )
            for disp, count in sorted(counts.items(), key=lambda x: -x[1])
        ]

        return DispositionBreakdownResponse(data=data, total_calls=total)

    async def get_agent_performance(
        self,
        current_user: UserContext,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AgentPerformanceResponse:
        """Per-agent metrics table."""
        org_id = current_user.organization_id
        runs = await self._fetch_runs(org_id, start_date, end_date)

        agent_data: dict[int, dict] = {}
        for r in runs:
            wf_id = r.get("dograh_workflow_id")
            if not wf_id:
                continue
            if wf_id not in agent_data:
                agent_data[wf_id] = {
                    "calls": 0,
                    "seconds": 0,
                    "completed": 0,
                    "cost": 0.0,
                }
            bucket = agent_data[wf_id]
            bucket["calls"] += 1
            bucket["seconds"] += r.get("duration_seconds", 0) or 0
            if r.get("status") == "completed":
                bucket["completed"] += 1
            cost_info = r.get("cost_info")
            if isinstance(cost_info, dict):
                bucket["cost"] += cost_info.get("total_cost", 0) or 0

        agent_names = await self._get_agent_names(org_id, list(agent_data.keys()))

        data = []
        for wf_id, bucket in agent_data.items():
            total_calls = bucket["calls"]
            total_secs = bucket["seconds"]
            data.append(
                AgentPerformanceItem(
                    agent_id=wf_id,
                    agent_name=agent_names.get(wf_id, f"Agent {wf_id}"),
                    total_calls=total_calls,
                    total_minutes=round(total_secs / 60, 2),
                    average_duration_seconds=round(total_secs / total_calls, 1) if total_calls else 0.0,
                    success_rate=round((bucket["completed"] / total_calls) * 100, 1) if total_calls else 0.0,
                    total_cost_usd=round(bucket["cost"], 2),
                )
            )

        data.sort(key=lambda x: -x.total_calls)
        return AgentPerformanceResponse(data=data)

    async def get_campaign_performance(
        self,
        current_user: UserContext,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> CampaignPerformanceResponse:
        """Per-campaign metrics table."""
        org_id = current_user.organization_id
        runs = await self._fetch_runs(org_id, start_date, end_date)

        campaign_data: dict[str, dict] = {}
        for r in runs:
            c_id = r.get("campaign_id")
            if not c_id:
                continue
            c_id = str(c_id)
            if c_id not in campaign_data:
                campaign_data[c_id] = {"calls": 0, "seconds": 0, "completed": 0}
            bucket = campaign_data[c_id]
            bucket["calls"] += 1
            bucket["seconds"] += r.get("duration_seconds", 0) or 0
            if r.get("status") == "completed":
                bucket["completed"] += 1

        campaign_names = await self._get_campaign_names(org_id, list(campaign_data.keys()))

        data = []
        for c_id, bucket in campaign_data.items():
            total_calls = bucket["calls"]
            info = campaign_names.get(c_id, {})
            data.append(
                CampaignPerformanceItem(
                    campaign_id=c_id,
                    campaign_name=info.get("name", f"Campaign {c_id[:8]}"),
                    total_calls=total_calls,
                    total_minutes=round(bucket["seconds"] / 60, 2),
                    completed_calls=bucket["completed"],
                    success_rate=round((bucket["completed"] / total_calls) * 100, 1) if total_calls else 0.0,
                    status=info.get("status", "unknown"),
                )
            )

        data.sort(key=lambda x: -x.total_calls)
        return CampaignPerformanceResponse(data=data)

    # --- Internal helpers ---

    def _resolve_date_range(
        self, start_date: str | None, end_date: str | None
    ) -> tuple[date, date]:
        """Parse ISO date strings into date objects, defaulting to last 30 days."""
        today = date.today()
        if end_date:
            try:
                e = date.fromisoformat(end_date[:10])
            except ValueError:
                e = today
        else:
            e = today

        if start_date:
            try:
                s = date.fromisoformat(start_date[:10])
            except ValueError:
                s = e - timedelta(days=30)
        else:
            s = e - timedelta(days=30)

        return s, e

    async def _fetch_runs(
        self,
        org_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        """Fetch call_runs from InsForge scoped to org with optional date filter.

        Data enters call_runs via two paths:
        1. Direct call triggers (CallService.trigger_call)
        2. Dograh webhooks (WebhookService.process_dograh_webhook)
        3. Lazy sync backfill (CampaignService.get_campaign_runs)
        """
        try:
            query = self.db.database.from_("call_runs") \
                .select("*") \
                .eq("organization_id", org_id)

            if start_date:
                query = query.gte("created_at", start_date)
            if end_date:
                end_dt = end_date[:10] + "T23:59:59Z" if len(end_date) <= 10 else end_date
                query = query.lte("created_at", end_dt)

            rows = await query.execute()
            return rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("analytics.fetch_runs_failed", org_id=org_id, error=str(exc))
            return []

    async def _get_agent_names(
        self, org_id: str, workflow_ids: list[int]
    ) -> dict[int, str]:
        """Resolve workflow_id → agent display name from local agent mappings."""
        if not workflow_ids:
            return {}
        try:
            rows = await self.db.database.from_("dograh_agent_mappings") \
                .select("dograh_workflow_id, display_name") \
                .eq("organization_id", org_id) \
                .in_("dograh_workflow_id", workflow_ids) \
                .execute()
            rows = rows if isinstance(rows, list) else []
            return {
                r["dograh_workflow_id"]: r.get("display_name", f"Agent {r['dograh_workflow_id']}")
                for r in rows
            }
        except Exception as exc:
            logger.warning("analytics.agent_names_failed", error=str(exc))
            return {}

    async def _get_campaign_names(
        self, org_id: str, campaign_ids: list[str]
    ) -> dict[str, dict]:
        """Resolve campaign_id → {name, status} from local campaigns table."""
        if not campaign_ids:
            return {}
        try:
            rows = await self.db.database.from_("campaigns") \
                .select("id, name, status") \
                .eq("organization_id", org_id) \
                .in_("id", campaign_ids) \
                .execute()
            rows = rows if isinstance(rows, list) else []
            return {
                str(r["id"]): {"name": r.get("name", ""), "status": r.get("status", "")}
                for r in rows
            }
        except Exception as exc:
            logger.warning("analytics.campaign_names_failed", error=str(exc))
            return {}
