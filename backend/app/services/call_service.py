from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core.logging import logger
from app.core.posthog import track_event
from app.integrations.dograh_client import DograhClient
from app.integrations.insforge_client import get_insforge_admin
from app.schemas.auth import UserContext
from app.schemas.call import (
    CallHistoryItem,
    CallHistoryResponse,
    CallRunResponse,
    CallTrigger,
    CallTriggerResponse,
    DownloadUrlResponse,
)


class CallService:
    """Business logic for outbound call triggering and run retrieval.

    Validates org access, checks usage quotas, proxies to Dograh,
    creates local call_runs records, and fires PostHog events.
    """

    def __init__(self) -> None:
        self.dograh = DograhClient()
        self.db = get_insforge_admin()

    async def trigger_call(
        self, data: CallTrigger, current_user: UserContext
    ) -> CallTriggerResponse:
        """Trigger an outbound call via Dograh."""

        mapping = await self._get_agent_mapping(data.workflow_id, current_user)
        workflow_uuid = mapping.get("dograh_workflow_uuid")
        if not workflow_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent has no workflow UUID — cannot trigger calls",
            )

        try:
            result = await self.dograh.trigger_call(
                workflow_uuid=workflow_uuid,
                phone_number=data.phone_number,
                initial_context=data.initial_context,
                telephony_configuration_id=data.telephony_configuration_id,
            )
        except Exception as exc:
            logger.error(
                "call.trigger_failed",
                org_id=current_user.organization_id,
                workflow_id=data.workflow_id,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to trigger call via Dograh",
            ) from exc

        run_id = result.get("workflow_run_id")
        run_name = result.get("workflow_run_name")
        call_status = result.get("status", "initiated")

        await self._create_call_run_record(
            run_id=run_id,
            workflow_id=data.workflow_id,
            phone_number=data.phone_number,
            initial_context=data.initial_context,
            org_id=current_user.organization_id,
            call_status=call_status,
        )

        track_event(
            distinct_id=current_user.organization_id,
            event="call_triggered",
            properties={
                "org_id": current_user.organization_id,
                "agent_id": str(data.workflow_id),
                "call_type": "outbound",
            },
        )

        logger.info(
            "call.triggered",
            org_id=current_user.organization_id,
            workflow_id=data.workflow_id,
            run_id=run_id,
        )

        return CallTriggerResponse(
            run_id=run_id,
            workflow_run_name=run_name,
            status=call_status,
            phone_number=data.phone_number,
            workflow_id=data.workflow_id,
            organization_id=current_user.organization_id,
        )

    async def get_call_run(
        self, run_id: int, current_user: UserContext
    ) -> CallRunResponse:
        """Get full call run details from Dograh, scoped to org."""
        local_run = await self._get_local_run_or_none(run_id, current_user.organization_id)

        if local_run:
            workflow_id = local_run["dograh_workflow_id"]
        else:
            # Campaign-originated calls have no local record.
            # Find the workflow_id by trying all agents mapped to this org.
            workflow_id = await self._find_workflow_for_run(run_id, current_user.organization_id)
            if not workflow_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Call run not found in this organization",
                )

        try:
            dograh_run = await self.dograh.get_run(workflow_id, run_id)
        except Exception as exc:
            logger.error("call.run_fetch_failed", run_id=run_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch call details from Dograh",
            ) from exc

        # Dograh nests phone/caller/disposition inside initial_context and gathered_context
        ic = dograh_run.get("initial_context") or {}
        gc = dograh_run.get("gathered_context") or {}
        ci = dograh_run.get("cost_info") or {}

        # Derive status
        if gc.get("error"):
            run_status = "failed"
        elif dograh_run.get("is_completed"):
            run_status = "completed"
        else:
            run_status = local_run.get("status", "in_progress") if local_run else "in_progress"

        phone_number = (
            (local_run.get("phone_number") if local_run else None)
            or ic.get("phone_number")
            or ic.get("called_number")
        )

        return CallRunResponse(
            run_id=dograh_run.get("id", run_id),
            workflow_id=workflow_id,
            organization_id=current_user.organization_id,
            name=dograh_run.get("name"),
            status=run_status,
            is_completed=dograh_run.get("is_completed", False),
            call_type=dograh_run.get("call_type"),
            phone_number=phone_number,
            caller_number=ic.get("caller_number", dograh_run.get("caller_number")),
            duration_seconds=ci.get("call_duration_seconds", dograh_run.get("call_duration_seconds")),
            initial_context=dograh_run.get("initial_context"),
            gathered_context=dograh_run.get("gathered_context"),
            transcript_url=dograh_run.get("transcript_url"),
            recording_url=dograh_run.get("recording_url"),
            transcript_public_url=dograh_run.get("transcript_public_url"),
            recording_public_url=dograh_run.get("recording_public_url"),
            public_access_token=dograh_run.get("public_access_token"),
            cost_info=dograh_run.get("cost_info"),
            annotations=dograh_run.get("annotations"),
            created_at=dograh_run.get("created_at"),
        )

    # --- Call History (Feature 09) ---

    async def list_history(
        self,
        current_user: UserContext,
        *,
        page: int = 1,
        limit: int = 20,
        start_date: str | None = None,
        end_date: str | None = None,
        agent_id: int | None = None,
        campaign_id: str | None = None,
        caller_number: str | None = None,
        called_number: str | None = None,
        disposition: list[str] | None = None,
        min_duration: int | None = None,
        max_duration: int | None = None,
    ) -> CallHistoryResponse:
        """Paginated call history from local DB, scoped to organization.

        Reads from the local call_runs table (not Dograh) to enforce
        multi-tenant isolation. Data enters call_runs via:
        1. Direct triggers (CallService.trigger_call)
        2. Dograh webhooks (WebhookService.process_dograh_webhook)
        3. Campaign sync backfill (CampaignService.get_campaign_runs)
        """
        org_id = current_user.organization_id

        try:
            # Build org-scoped query
            query = self.db.database.from_("call_runs") \
                .select("*") \
                .eq("organization_id", str(org_id)) \
                .order("created_at", desc=True)

            # Apply filters
            if start_date:
                query = query.gte("created_at", start_date)
            if end_date:
                end_dt = end_date[:10] + "T23:59:59Z" if len(end_date) <= 10 else end_date
                query = query.lte("created_at", end_dt)
            if agent_id is not None:
                query = query.eq("dograh_workflow_id", agent_id)
            if campaign_id is not None:
                query = query.eq("campaign_id", str(campaign_id))
            if caller_number:
                query = query.eq("caller_number", caller_number)
            if called_number:
                query = query.eq("phone_number", called_number)
            if disposition:
                query = query.in_("disposition", disposition)
            if min_duration is not None:
                query = query.gte("duration_seconds", min_duration)
            if max_duration is not None:
                query = query.lte("duration_seconds", max_duration)

            rows = await query.execute()
            rows = rows if isinstance(rows, list) else []

        except Exception as exc:
            logger.error("call.history_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch call history",
            ) from exc

        # Pagination in Python (InsForge client doesn't support .range())
        total = len(rows)
        offset = (page - 1) * limit
        paginated_rows = rows[offset:offset + limit]

        # Batch-resolve workflow names and campaign names
        workflow_ids = list({r.get("dograh_workflow_id") for r in paginated_rows if r.get("dograh_workflow_id")})
        campaign_ids = list({str(r.get("campaign_id")) for r in paginated_rows if r.get("campaign_id")})
        agent_names = await self._resolve_agent_names(str(org_id), workflow_ids)
        campaign_names = await self._resolve_campaign_names(str(org_id), campaign_ids)

        # Extract cost from cost_info JSON
        def _extract_cost(r: dict) -> float | None:
            ci = r.get("cost_info")
            if isinstance(ci, dict):
                return ci.get("total_cost")
            if isinstance(ci, str):
                try:
                    parsed = json.loads(ci)
                    return parsed.get("total_cost") if isinstance(parsed, dict) else None
                except (json.JSONDecodeError, TypeError):
                    pass
            return None

        runs = [
            CallHistoryItem(
                run_id=r.get("dograh_run_id", 0),
                workflow_id=r.get("dograh_workflow_id"),
                workflow_name=agent_names.get(r.get("dograh_workflow_id", 0)),
                campaign_id=r.get("campaign_id"),
                campaign_name=campaign_names.get(str(r.get("campaign_id", ""))),
                call_type=r.get("call_type"),
                status=r.get("status"),
                disposition_code=r.get("disposition"),
                phone_number=r.get("phone_number"),
                caller_number=r.get("caller_number"),
                duration_seconds=r.get("duration_seconds"),
                cost=_extract_cost(r),
                recording_url=r.get("recording_url"),
                transcript_url=r.get("transcript_url"),
                public_access_token=r.get("public_access_token"),
                created_at=r.get("created_at"),
                completed_at=r.get("completed_at"),
            )
            for r in paginated_rows
        ]

        return CallHistoryResponse(
            runs=runs,
            total=total,
            page=page,
            limit=limit,
            has_more=(page * limit) < total,
        )


    async def _resolve_agent_names(
        self, org_id: str, workflow_ids: list[int],
    ) -> dict[int, str]:
        """Batch-resolve workflow_id → agent display name from local mappings."""
        if not workflow_ids:
            return {}
        try:
            rows = await self.db.database.from_("dograh_agent_mappings") \
                .select("dograh_workflow_id, agent_name") \
                .eq("organization_id", org_id) \
                .in_("dograh_workflow_id", workflow_ids) \
                .execute()
            rows = rows if isinstance(rows, list) else []
            return {
                r["dograh_workflow_id"]: r.get("agent_name", f"Agent {r['dograh_workflow_id']}")
                for r in rows
            }
        except Exception as exc:
            logger.warning("call.agent_names_failed", error=str(exc))
            return {}

    async def _resolve_campaign_names(
        self, org_id: str, campaign_ids: list[str],
    ) -> dict[str, str]:
        """Batch-resolve campaign_id → campaign name from local campaigns table."""
        if not campaign_ids:
            return {}
        try:
            rows = await self.db.database.from_("campaigns") \
                .select("id, name") \
                .eq("organization_id", org_id) \
                .in_("id", campaign_ids) \
                .execute()
            rows = rows if isinstance(rows, list) else []
            return {str(r["id"]): r.get("name", "") for r in rows}
        except Exception as exc:
            logger.warning("call.campaign_names_failed", error=str(exc))
            return {}

    async def get_recording_url(
        self, run_id: int, current_user: UserContext,
    ) -> DownloadUrlResponse:
        """Get recording download URL for a call run."""
        local_run = await self._get_local_run(run_id, current_user.organization_id)
        workflow_id = local_run["dograh_workflow_id"]

        try:
            dograh_run = await self.dograh.get_run(workflow_id, run_id)
        except Exception as exc:
            logger.error("call.recording_url_failed", run_id=run_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch recording URL",
            ) from exc

        recording_url = (
            dograh_run.get("recording_public_url")
            or dograh_run.get("recording_url")
            or ""
        )
        if not recording_url:
            token = dograh_run.get("public_access_token", "")
            if token:
                recording_url = f"{self.dograh.base_url}/api/v1/public/download/workflow/{token}/recording"

        if not recording_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No recording available for this call",
            )

        return DownloadUrlResponse(url=recording_url, run_id=run_id, type="recording")

    async def get_transcript_url(
        self, run_id: int, current_user: UserContext,
    ) -> DownloadUrlResponse:
        """Get transcript download URL for a call run."""
        local_run = await self._get_local_run(run_id, current_user.organization_id)
        workflow_id = local_run["dograh_workflow_id"]

        try:
            dograh_run = await self.dograh.get_run(workflow_id, run_id)
        except Exception as exc:
            logger.error("call.transcript_url_failed", run_id=run_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch transcript URL",
            ) from exc

        transcript_url = (
            dograh_run.get("transcript_public_url")
            or dograh_run.get("transcript_url")
            or ""
        )
        if not transcript_url:
            token = dograh_run.get("public_access_token", "")
            if token:
                transcript_url = f"{self.dograh.base_url}/api/v1/public/download/workflow/{token}/transcript"

        if not transcript_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No transcript available for this call",
            )

        return DownloadUrlResponse(url=transcript_url, run_id=run_id, type="transcript")

    # --- Internal helpers ---

    async def _get_agent_mapping(
        self, workflow_id: int, current_user: UserContext
    ) -> dict:
        """Verify agent belongs to org and return the mapping."""
        try:
            rows = await self.db.database.from_("dograh_agent_mappings") \
                .select("dograh_workflow_uuid,dograh_workflow_id") \
                .eq("dograh_workflow_id", workflow_id) \
                .eq("organization_id", current_user.organization_id) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("call.agent_check_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify agent access",
            ) from exc

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found in this organization",
            )

        return rows[0]

    async def _create_call_run_record(
        self,
        run_id: int,
        workflow_id: int,
        phone_number: str,
        initial_context: dict | None,
        org_id: str,
        call_status: str,
    ) -> None:
        """Create local call_runs record for tracking."""

        try:
            await self.db.database.from_("call_runs").insert(
                [{
                    "organization_id": org_id,
                    "dograh_run_id": run_id,
                    "dograh_workflow_id": workflow_id,
                    "call_type": "outbound",
                    "status": call_status,
                    "phone_number": phone_number,
                    "initial_context": json.dumps(initial_context) if initial_context else None,
                }]
            )
        except Exception as exc:
            logger.warning("call.local_record_failed", run_id=run_id, error=str(exc))

    async def _get_local_run(self, run_id: int, org_id: str) -> dict:
        """Get local call_runs record, scoped to org."""
        try:
            rows = await self.db.database.from_("call_runs") \
                .select("*") \
                .eq("dograh_run_id", run_id) \
                .eq("organization_id", org_id) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("call.local_fetch_failed", run_id=run_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch call record",
            ) from exc

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Call run not found in this organization",
            )

        return rows[0]

    async def _get_local_run_or_none(self, run_id: int, org_id: str) -> dict | None:
        """Get local call_runs record if it exists, or None for campaign-originated calls."""
        try:
            rows = await self.db.database.from_("call_runs") \
                .select("*") \
                .eq("dograh_run_id", run_id) \
                .eq("organization_id", org_id) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.warning("call.local_fetch_failed", run_id=run_id, error=str(exc))
            return None

        return rows[0] if rows else None

    async def _find_workflow_for_run(self, run_id: int, org_id: str) -> int | None:
        """Find the workflow_id for a run by trying all agents mapped to this org.

        Campaign-originated calls have no local record, so we need to check
        each of the org's agents in Dograh to find which one owns this run.
        """
        try:
            mappings = await self.db.database.from_("dograh_agent_mappings") \
                .select("dograh_workflow_id") \
                .eq("organization_id", org_id) \
                .execute()
            mappings = mappings if isinstance(mappings, list) else []
        except Exception as exc:
            logger.error("call.workflow_lookup_failed", run_id=run_id, error=str(exc))
            return None

        for mapping in mappings:
            wf_id = mapping.get("dograh_workflow_id")
            if not wf_id:
                continue
            try:
                await self.dograh.get_run(wf_id, run_id)
                return wf_id
            except Exception:
                continue

        return None
