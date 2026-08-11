"""Audit logging service for spreadsheet integration.

Provides a fire-and-forget audit trail for all significant events:
- Connection lifecycle (created, paused, deleted)
- Lead processing (call triggered, skipped, duplicate)
- Call results (completed, failed, writeback)
- Error conditions (auth failure, rate limit, network)

Never raises — audit failures are logged to structlog but never bubble up.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from app.core.logging import logger
from app.integrations.insforge_client import get_insforge_admin

AuditSeverity = Literal["debug", "info", "warning", "error"]

# ── Event type constants ───────────────────────────────────────────────────────

class AuditEvent:
    # Connection lifecycle
    CONNECTION_CREATED    = "connection.created"
    CONNECTION_UPDATED    = "connection.updated"
    CONNECTION_PAUSED     = "connection.paused"
    CONNECTION_RESUMED    = "connection.resumed"
    CONNECTION_DELETED    = "connection.deleted"

    # Polling
    POLL_STARTED          = "poll.started"
    POLL_COMPLETED        = "poll.completed"
    POLL_ERROR_AUTH       = "poll.error_auth"
    POLL_ERROR_NETWORK    = "poll.error_network"
    POLL_ERROR_GENERIC    = "poll.error"
    POLL_AUTO_PAUSED      = "poll.auto_paused"      # too many consecutive errors

    # Lead processing
    LEAD_DETECTED         = "lead.detected"
    LEAD_DUPLICATE_SKIP   = "lead.duplicate_skipped"
    LEAD_NO_PHONE_SKIP    = "lead.no_phone_skipped"
    LEAD_RATE_LIMITED     = "lead.rate_limit_queued"
    LEAD_CALL_TRIGGERED   = "lead.call_triggered"
    LEAD_CALL_FAILED      = "lead.call_failed"
    LEAD_CALL_COMPLETED   = "lead.call_completed"
    LEAD_WRITEBACK_DONE   = "lead.writeback_done"
    LEAD_WRITEBACK_FAILED = "lead.writeback_failed"

    # Callbacks
    CALLBACK_SCHEDULED    = "callback.scheduled"
    CALLBACK_TRIGGERED    = "callback.triggered"
    CALLBACK_CANCELLED    = "callback.cancelled"
    CALLBACK_FAILED       = "callback.failed"
    CALLBACK_RETRY        = "callback.retry"


class SheetAuditService:
    """Append-only audit log for sheet integration events."""

    def __init__(self) -> None:
        self.db = get_insforge_admin()

    async def log(
        self,
        *,
        org_id: str,
        event_type: str,
        details: dict | None = None,
        connection_id: str | None = None,
        lead_id: str | None = None,
        severity: AuditSeverity = "info",
    ) -> None:
        """Append an audit log entry.

        Never raises — any DB error is silently logged to structlog.
        """
        try:
            row: dict = {
                "organization_id": org_id,
                "event_type": event_type,
                "details": details or {},
                "severity": severity,
            }
            if connection_id:
                row["connection_id"] = connection_id
            if lead_id:
                row["lead_id"] = lead_id

            await self.db.database.from_("sheet_audit_log").insert([row])

        except Exception as exc:
            # Audit failure must never break the main flow
            logger.warning(
                "audit.write_failed",
                event_type=event_type,
                org_id=org_id,
                error=str(exc),
            )

    async def list_events(
        self,
        org_id: str,
        connection_id: str | None = None,
        event_type: str | None = None,
        severity: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query audit log for a given org (optionally scoped to a connection)."""
        query = (
            self.db.database.from_("sheet_audit_log")
            .select("*")
            .eq("organization_id", org_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if connection_id:
            query = query.eq("connection_id", connection_id)
        if event_type:
            query = query.eq("event_type", event_type)
        if severity:
            query = query.eq("severity", severity)

        result = await query.execute()
        return (result if isinstance(result, list) else [])
