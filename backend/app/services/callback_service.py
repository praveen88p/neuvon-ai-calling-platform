"""Callback scheduling service.

Handles the full lifecycle of a scheduled callback:
  - Parsing raw callback_time from gathered_context
  - Creating scheduled_callbacks records
  - Retrying failed callbacks (up to MAX_RETRIES)
  - Cancelling callbacks (lead opted out)
  - Listing callbacks for frontend display
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.core.logging import logger
from app.integrations.dograh_client import DograhClient
from app.integrations.insforge_client import get_insforge_admin
from app.utils.callback_parser import format_for_display, parse_callback_time

MAX_RETRIES = 2
RETRY_DELAY_MINUTES = 30


class CallbackService:
    """Lifecycle management for scheduled callbacks."""

    def __init__(self) -> None:
        self.db = get_insforge_admin()
        self.dograh = DograhClient()

    # ── Create ────────────────────────────────────────────────────────────

    async def schedule_from_raw(
        self,
        *,
        org_id: str,
        phone_number: str,
        workflow_id: int,
        raw_callback_time: str,
        initial_context: dict,
        sheet_lead_id: str | None = None,
        tz_offset_hours: float = 5.5,
    ) -> dict | None:
        """Parse a raw time string and insert a scheduled_callbacks row.

        Returns the created row dict, or None if the time could not be parsed.
        """
        callback_dt = parse_callback_time(
            raw_callback_time,
            reference_tz_offset_hours=tz_offset_hours,
        )
        if callback_dt is None:
            logger.warning(
                "callback.parse_failed",
                org_id=org_id,
                raw=raw_callback_time,
            )
            return None

        row = {
            "organization_id": org_id,
            "phone_number": phone_number,
            "workflow_id": workflow_id,
            "initial_context": json.dumps(initial_context),
            "callback_at": callback_dt.isoformat(),
            "status": "pending",
            "retry_count": 0,
            "display_time": format_for_display(callback_dt),
        }
        if sheet_lead_id:
            row["sheet_lead_id"] = sheet_lead_id

        result = await self.db.database.from_("scheduled_callbacks").insert([row])

        created = result[0] if result else row

        logger.info(
            "callback.scheduled",
            org_id=org_id,
            callback_id=created.get("id"),
            callback_at=callback_dt.isoformat(),
            phone=phone_number[:6] + "****",
        )
        return created

    # ── Trigger due callbacks ─────────────────────────────────────────────

    async def fire_due_callbacks(self) -> int:
        """Find all pending callbacks that are due and trigger Dograh calls.

        Returns the number of callbacks triggered.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        result = (
            await self.db.database.from_("scheduled_callbacks")
            .select("*")
            .eq("status", "pending")
            .lte("callback_at", now_iso)
            .limit(50)
            .execute()
        )
        callbacks = (result if isinstance(result, list) else [])

        if not callbacks:
            return 0

        logger.info("callback.due_count", count=len(callbacks))
        triggered = 0

        for cb in callbacks:
            try:
                await self._fire_one(cb)
                triggered += 1
            except Exception as exc:
                logger.error(
                    "callback.fire_failed",
                    callback_id=cb.get("id"),
                    error=str(exc),
                )
                await self._handle_fire_failure(cb)

        return triggered

    async def _fire_one(self, cb: dict) -> None:
        """Trigger a single callback call via Dograh."""
        # Resolve the agent's UUID
        agent_result = (
            await self.db.database.from_("dograh_agent_mappings")
            .select("dograh_workflow_uuid")
            .eq("dograh_workflow_id", cb["workflow_id"])
            .eq("organization_id", cb["organization_id"])
            .execute()
        )
        agents = (agent_result if isinstance(agent_result, list) else [])
        if not agents or not agents[0].get("dograh_workflow_uuid"):
            raise ValueError(
                f"Agent workflow_id={cb['workflow_id']} not found for org={cb['organization_id']}"
            )

        initial_context = (
            json.loads(cb["initial_context"])
            if isinstance(cb["initial_context"], str)
            else cb.get("initial_context", {})
        )
        initial_context["callback_retry"] = True
        initial_context["scheduled_callback_id"] = str(cb["id"])

        call_result = await self.dograh.trigger_call(
            workflow_uuid=agents[0]["dograh_workflow_uuid"],
            phone_number=cb["phone_number"],
            initial_context=initial_context,
        )
        run_id = call_result.get("workflow_run_id")

        now_iso = datetime.now(timezone.utc).isoformat()

        # Mark callback as triggered
        await (
            self.db.database.from_("scheduled_callbacks")
            .eq("id", cb["id"])
            .update({
                "status": "triggered",
                "triggered_run_id": run_id,
            }, return_representation=True)
        )

        # Update linked sheet_lead
        if cb.get("sheet_lead_id"):
            await (
                self.db.database.from_("sheet_leads")
                .eq("id", cb["sheet_lead_id"])
                .update({
                    "dograh_run_id": run_id,
                    "call_status": "calling",
                    "updated_at": now_iso,
                }, return_representation=True)
            )

        logger.info(
            "callback.triggered",
            callback_id=cb["id"],
            run_id=run_id,
            phone=cb["phone_number"][:6] + "****",
        )

    async def _handle_fire_failure(self, cb: dict) -> None:
        """On failure, retry up to MAX_RETRIES then mark as failed."""
        from datetime import timedelta

        retry_count = cb.get("retry_count", 0) + 1

        if retry_count <= MAX_RETRIES:
            # Reschedule RETRY_DELAY_MINUTES from now
            retry_at = (
                datetime.now(timezone.utc)
                + timedelta(minutes=RETRY_DELAY_MINUTES)
            ).isoformat()

            await (
                self.db.database.from_("scheduled_callbacks")
                .eq("id", cb["id"])
                .update({
                    "retry_count": retry_count,
                    "callback_at": retry_at,
                    "status": "pending",
                }, return_representation=True)
            )
            logger.info(
                "callback.retry_scheduled",
                callback_id=cb["id"],
                retry_count=retry_count,
                retry_at=retry_at,
            )
        else:
            # Exceeded retries — mark as failed
            await (
                self.db.database.from_("scheduled_callbacks")
                .eq("id", cb["id"])
                .update({"status": "failed"}, return_representation=True)
            )
            logger.warning(
                "callback.max_retries_exceeded",
                callback_id=cb["id"],
            )

    # ── Cancel ────────────────────────────────────────────────────────────

    async def cancel_callback(
        self, callback_id: str, org_id: str
    ) -> None:
        """Cancel a pending callback. Org-scoped."""
        result = (
            await self.db.database.from_("scheduled_callbacks")
            .select("id, status")
            .eq("id", callback_id)
            .eq("organization_id", org_id)
            .execute()
        )
        rows = (result if isinstance(result, list) else [])
        if not rows:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Callback not found",
            )

        cb = rows[0]
        if cb["status"] not in ("pending",):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel a callback with status '{cb['status']}'",
            )

        await (
            self.db.database.from_("scheduled_callbacks")
            .eq("id", callback_id)
            .eq("organization_id", org_id)
            .update({"status": "cancelled"}, return_representation=True)
        )

        # Also update the linked sheet_lead's call_status
        lead_result = (
            await self.db.database.from_("scheduled_callbacks")
            .select("sheet_lead_id")
            .eq("id", callback_id)
            .execute()
        )
        leads = (lead_result if isinstance(lead_result, list) else [])
        if leads and leads[0].get("sheet_lead_id"):
            await (
                self.db.database.from_("sheet_leads")
                .eq("id", leads[0]["sheet_lead_id"])
                .update({
                    "call_status": "failed",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }, return_representation=True)
            )

        logger.info(
            "callback.cancelled",
            callback_id=callback_id,
            org_id=org_id,
        )

    # ── List ──────────────────────────────────────────────────────────────

    async def list_callbacks(
        self,
        org_id: str,
        status: str | None = None,
        connection_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List scheduled callbacks for an organization."""
        query = (
            self.db.database.from_("scheduled_callbacks")
            .select("*, sheet_leads(connection_id, phone_number, lead_data)")
            .eq("organization_id", org_id)
            .order("callback_at", desc=False)
            .limit(limit)
        )
        if status:
            query = query.eq("status", status)

        result = await query.execute()
        callbacks = (result if isinstance(result, list) else [])

        # Filter by connection_id if requested
        if connection_id:
            callbacks = [
                cb for cb in callbacks
                if cb.get("sheet_leads", {}) and
                cb["sheet_leads"].get("connection_id") == connection_id
            ]

        return callbacks

    async def list_pending_for_connection(
        self, connection_id: str, org_id: str
    ) -> list[dict]:
        """Get pending callbacks for a specific sheet connection."""
        # Join via sheet_leads
        result = (
            await self.db.database.from_("scheduled_callbacks")
            .select("*")
            .eq("organization_id", org_id)
            .eq("status", "pending")
            .execute()
        )
        all_cbs = (result if isinstance(result, list) else [])

        # Filter by connection via sheet_leads
        lead_ids_result = (
            await self.db.database.from_("sheet_leads")
            .select("id")
            .eq("connection_id", connection_id)
            .execute()
        )
        lead_ids = {r["id"] for r in ((lead_ids_result if isinstance(lead_ids_result, list) else []))}

        return [
            cb for cb in all_cbs
            if cb.get("sheet_lead_id") in lead_ids
        ]
