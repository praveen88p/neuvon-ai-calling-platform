"""Business logic for the spreadsheet integration feature.

Handles: connection CRUD, column auto-detection, new-row polling,
call triggering via Dograh, and post-call result write-back.

Follows the project's RORO pattern — Pydantic schemas in, Pydantic
schemas out. Every query is scoped by ``organization_id``.

Phase 4 additions:
  - Rate limiting: max concurrent calls per connection (default 5)
  - Duplicate detection: skip phone numbers called within window
  - Error recovery: auth errors mark connection as needs_reauth and auto-pause
  - Audit logging: all significant events logged to sheet_audit_log
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.logging import logger
from app.integrations.dograh_client import DograhClient
from app.integrations.google_sheets_client import (
    CellUpdate,
    GoogleSheetsClient,
    SheetAuthError,
    SheetClientError,
    col_index_to_letter,
    extract_spreadsheet_id,
)
from app.integrations.insforge_client import get_insforge_admin
from app.schemas.sheets import (
    DetectColumnsRequest,
    SheetColumn,
    SheetColumnsResponse,
    SheetConnectionCreate,
    SheetConnectionResponse,
    SheetConnectionStats,
    SheetConnectionUpdate,
    SheetLeadResponse,
    SheetLeadsListResponse,
)
from app.services.sheet_audit_service import AuditEvent, SheetAuditService

# Max consecutive poll errors before auto-pausing the connection
_MAX_CONSECUTIVE_ERRORS = 5


class SheetService:
    """Business logic for spreadsheet connections.

    All methods receive ``org_id`` from the auth layer — this enforces
    multi-tenant data isolation (same pattern as every other service).
    """

    def __init__(self) -> None:
        self.db = get_insforge_admin()
        self.dograh = DograhClient()
        self.audit = SheetAuditService()

    # ── Connection CRUD ───────────────────────────────────────────────

    async def create_connection(
        self, data: SheetConnectionCreate, org_id: str
    ) -> SheetConnectionResponse:
        """Create a new sheet connection for the organization."""

        spreadsheet_id = extract_spreadsheet_id(data.sheet_url)

        # Auto-detect sheet name if not provided
        sheet_name = data.sheet_name
        if not sheet_name:
            client = GoogleSheetsClient(data.credentials_json, spreadsheet_id)
            await client.connect()
            names = await client.get_sheet_names()
            sheet_name = names[0] if names else "Sheet1"

        # Verify the agent belongs to this org
        await self._verify_agent_ownership(data.agent_workflow_id, org_id)

        row = {
            "organization_id": org_id,
            "provider": "google_sheets",
            "sheet_url": data.sheet_url,
            "spreadsheet_id": spreadsheet_id,
            "sheet_name": sheet_name,
            "column_mapping": json.dumps(data.column_mapping),
            "agent_workflow_id": data.agent_workflow_id,
            "credentials_json": data.credentials_json,
            "polling_interval_secs": data.polling_interval_secs,
            "is_active": True,
            "last_row_processed": 1,  # header row; data starts at row 2
        }

        result = (
            await self.db.database.from_("sheet_connections")
            .insert([row], return_representation=True)
        )
        created = result[0] if result else row
        conn_id = str(created.get("id", ""))
        logger.info(
            "sheet.connection_created",
            org_id=org_id,
            connection_id=conn_id,
            spreadsheet_id=spreadsheet_id,
        )
        await self.audit.log(
            org_id=org_id,
            event_type=AuditEvent.CONNECTION_CREATED,
            connection_id=conn_id,
            details={"spreadsheet_id": spreadsheet_id, "sheet_name": sheet_name},
        )

        # Auto-configure the Dograh agent's webhook node so that
        # call results are posted back to our backend automatically.
        await self._sync_dograh_webhook(data.agent_workflow_id)

        return self._to_connection_response(created)

    async def list_connections(
        self, org_id: str
    ) -> list[SheetConnectionResponse]:
        """List all sheet connections for the organization."""

        result = (
            await self.db.database.from_("sheet_connections")
            .select("*")
            .eq("organization_id", org_id)
            .order("created_at", desc=True)
            .execute()
        )
        rows = (result if isinstance(result, list) else [])
        return [self._to_connection_response(r) for r in rows]

    async def get_connection(
        self, connection_id: str, org_id: str
    ) -> SheetConnectionResponse:
        """Get a single connection (org-scoped)."""

        conn = await self._get_connection_row(connection_id, org_id)
        return self._to_connection_response(conn)

    async def update_connection(
        self, connection_id: str, data: SheetConnectionUpdate, org_id: str
    ) -> SheetConnectionResponse:
        """Update connection settings."""

        # Verify it exists and belongs to this org
        await self._get_connection_row(connection_id, org_id)

        updates: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
        if data.column_mapping is not None:
            updates["column_mapping"] = json.dumps(data.column_mapping)
        if data.agent_workflow_id is not None:
            await self._verify_agent_ownership(data.agent_workflow_id, org_id)
            updates["agent_workflow_id"] = data.agent_workflow_id
        if data.polling_interval_secs is not None:
            updates["polling_interval_secs"] = data.polling_interval_secs
        if data.is_active is not None:
            updates["is_active"] = data.is_active
        # Phase 4 settings
        if data.max_concurrent_calls is not None:
            updates["max_concurrent_calls"] = data.max_concurrent_calls
        if data.duplicate_window_hours is not None:
            updates["duplicate_window_hours"] = data.duplicate_window_hours

        result = (
            await self.db.database.from_("sheet_connections")
            .eq("id", connection_id)
            .eq("organization_id", org_id)
            .update(updates, return_representation=True)
        )
        updated = result[0] if result else {}
        return self._to_connection_response(updated)

    async def delete_connection(
        self, connection_id: str, org_id: str
    ) -> None:
        """Delete a connection and all its leads (CASCADE)."""

        await self._get_connection_row(connection_id, org_id)
        await (
            self.db.database.from_("sheet_connections")
            .eq("id", connection_id)
            .eq("organization_id", org_id)
            .delete()
        )
        logger.info(
            "sheet.connection_deleted",
            org_id=org_id,
            connection_id=connection_id,
        )

    async def pause_connection(
        self, connection_id: str, org_id: str
    ) -> SheetConnectionResponse:
        """Pause polling for a connection."""
        result = await self.update_connection(
            connection_id,
            SheetConnectionUpdate(is_active=False),
            org_id,
        )
        await self.audit.log(
            org_id=org_id,
            event_type=AuditEvent.CONNECTION_PAUSED,
            connection_id=connection_id,
        )
        return result

    async def resume_connection(
        self, connection_id: str, org_id: str
    ) -> SheetConnectionResponse:
        """Resume polling for a connection."""
        # Also clear needs_reauth flag on manual resume
        await (
            self.db.database.from_("sheet_connections")
            .eq("id", connection_id)
            .eq("organization_id", org_id)
            .update({"needs_reauth": False, "consecutive_error_count": 0}, return_representation=True)
        )
        result = await self.update_connection(
            connection_id,
            SheetConnectionUpdate(is_active=True),
            org_id,
        )
        await self.audit.log(
            org_id=org_id,
            event_type=AuditEvent.CONNECTION_RESUMED,
            connection_id=connection_id,
        )
        return result

    # ── Column detection ──────────────────────────────────────────────

    async def detect_columns(
        self, data: DetectColumnsRequest
    ) -> SheetColumnsResponse:
        """Auto-detect columns from a Google Sheet URL.

        Returns headers, sample values, and available sheet tabs.
        Raises HTTP 400 for auth errors with a clear user-facing message.
        """
        try:
            spreadsheet_id = extract_spreadsheet_id(data.sheet_url)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Google Sheets URL. Expected: https://docs.google.com/spreadsheets/d/...",
            )

        try:
            client = GoogleSheetsClient(data.credentials_json, spreadsheet_id)
            await client.connect()
        except SheetAuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Service account credentials are invalid or expired. "
                    "Please check your JSON key file."
                ),
            ) from exc
        except (SheetClientError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to initialise Google Sheets client: {exc}",
            ) from exc

        try:
            sheet_names = await client.get_sheet_names()
        except SheetAuthError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Permission denied (HTTP 403). "
                    "The service account does not have access to this spreadsheet. "
                    "Please share the sheet with the service account email "
                    "(found in 'client_email' in your JSON key) and give it Viewer or Editor access."
                ),
            )
        except SheetClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not read sheet structure: {exc}",
            ) from exc

        selected = data.sheet_name or (sheet_names[0] if sheet_names else "Sheet1")

        try:
            headers = await client.read_headers(selected)
            # Read first data row for sample values
            sample_rows = await client.read_rows(selected, start_row=2, end_row=2)
            samples = sample_rows[0] if sample_rows else []
            row_count = await client.get_row_count(selected)
        except SheetAuthError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Permission denied reading sheet data. "
                    "Make sure the service account has Viewer or Editor access to this spreadsheet."
                ),
            )
        except SheetClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read sheet data: {exc}",
            ) from exc

        columns = [
            SheetColumn(
                letter=col_index_to_letter(i),
                header=header,
                sample=samples[i] if i < len(samples) else "",
            )
            for i, header in enumerate(headers)
        ]

        return SheetColumnsResponse(
            spreadsheet_id=spreadsheet_id,
            sheet_names=sheet_names,
            selected_sheet=selected,
            columns=columns,
            row_count=max(0, row_count - 1),  # exclude header
        )

    # ── Polling — new lead detection ──────────────────────────────────

    async def poll_for_new_leads(self, connection_id: str) -> int:
        """Poll a connection for new rows and trigger calls.

        Phase 4 features active:
          - Rate limiting: skip call trigger if >= max_concurrent_calls active
          - Duplicate detection: skip phones seen within duplicate_window_hours
          - Error recovery: auth errors → mark needs_reauth + auto-pause
          - Audit logging: all skip/trigger events recorded

        Called by the Celery Beat task every polling_interval_secs.
        Returns the count of new leads found.
        """

        # Load connection (no org scope — task runs cross-org)
        result = (
            await self.db.database.from_("sheet_connections")
            .select("*")
            .eq("id", connection_id)
            .eq("is_active", True)
            .execute()
        )
        rows = (result if isinstance(result, list) else [])
        if not rows:
            return 0

        conn = rows[0]
        org_id = conn["organization_id"]
        column_mapping = (
            json.loads(conn["column_mapping"])
            if isinstance(conn["column_mapping"], str)
            else conn["column_mapping"]
        )
        last_row = conn["last_row_processed"]
        max_concurrent = conn.get("max_concurrent_calls", 5)
        dup_window_hours = conn.get("duplicate_window_hours", 24)

        try:
            client = GoogleSheetsClient(
                conn["credentials_json"], conn["spreadsheet_id"]
            )
            await client.connect()

            # Read new rows starting after the last processed row.
            # Row 1 is always the header, so data starts at row 2.
            # If last_row_processed == 0 (never polled), start from row 2.
            start_row = max(2, last_row + 1)
            new_rows = await client.read_rows(
                conn["sheet_name"], start_row=start_row
            )

            logger.info(
                "sheet.poll_rows",
                connection_id=connection_id,
                last_row_processed=last_row,
                start_row=start_row,
                rows_found=len(new_rows),
            )

            if not new_rows:
                # Update last_polled_at even if no new rows
                await self._update_poll_state(connection_id, last_row)
                return 0

            # Reset consecutive error count on successful read
            if conn.get("consecutive_error_count", 0) > 0:
                await (
                    self.db.database.from_("sheet_connections")
                    .eq("id", connection_id)
                    .update({"consecutive_error_count": 0, "needs_reauth": False}, return_representation=True)
                )

            headers = await client.read_headers(conn["sheet_name"])
            new_count = 0

            for offset, row_data in enumerate(new_rows):
                row_number = start_row + offset
                lead = self._extract_lead_from_row(
                    row_data, headers, column_mapping
                )

                if not lead.get("phone"):
                    logger.debug(
                        "sheet.skip_no_phone",
                        connection_id=connection_id,
                        row=row_number,
                    )
                    await self.audit.log(
                        org_id=org_id,
                        event_type=AuditEvent.LEAD_NO_PHONE_SKIP,
                        connection_id=connection_id,
                        details={"row": row_number},
                        severity="debug",
                    )
                    continue

                phone = lead["phone"]

                # ── Duplicate detection ─────────────────────────────────────
                # Skip if this phone was already called within duplicate_window_hours
                is_duplicate = await self._is_duplicate_phone(
                    phone, connection_id, dup_window_hours
                )
                if is_duplicate:
                    logger.info(
                        "sheet.skip_duplicate_phone",
                        connection_id=connection_id,
                        row=row_number,
                        phone=phone[:6] + "****",
                    )
                    await self.audit.log(
                        org_id=org_id,
                        event_type=AuditEvent.LEAD_DUPLICATE_SKIP,
                        connection_id=connection_id,
                        details={"row": row_number, "phone": phone[:6] + "****"},
                        severity="info",
                    )
                    continue

                # Insert lead (skip duplicates via UNIQUE constraint)
                try:
                    lead_row = {
                        "connection_id": connection_id,
                        "organization_id": org_id,
                        "row_number": row_number,
                        "phone_number": phone,
                        "lead_data": json.dumps(lead),
                        "call_status": "pending",
                    }
                    insert_result = (
                        await self.db.database.from_("sheet_leads")
                        .insert([lead_row], return_representation=True)
                    )
                    lead_record = (
                        insert_result[0]
                        if insert_result
                        else lead_row
                    )
                    new_count += 1

                    await self.audit.log(
                        org_id=org_id,
                        event_type=AuditEvent.LEAD_DETECTED,
                        connection_id=connection_id,
                        lead_id=str(lead_record.get("id", "")),
                        details={"row": row_number, "phone": phone[:6] + "****"},
                    )

                    # ── Rate limiting ───────────────────────────────────────
                    # Skip call trigger if too many concurrent calls active
                    active_calls = await self._count_active_calls(connection_id)
                    if active_calls >= max_concurrent:
                        logger.info(
                            "sheet.rate_limited",
                            connection_id=connection_id,
                            active=active_calls,
                            max=max_concurrent,
                        )
                        await self.audit.log(
                            org_id=org_id,
                            event_type=AuditEvent.LEAD_RATE_LIMITED,
                            connection_id=connection_id,
                            lead_id=str(lead_record.get("id", "")),
                            details={"active_calls": active_calls, "max": max_concurrent},
                            severity="warning",
                        )
                        # Leave lead in "pending" — Celery will retry next poll
                        continue

                    # Trigger the call
                    await self._trigger_lead_call(
                        lead_record, conn, lead, org_id
                    )

                except Exception as exc:
                    # Duplicate row or other DB error — skip
                    logger.warning(
                        "sheet.lead_insert_failed",
                        connection_id=connection_id,
                        row=row_number,
                        error=str(exc),
                    )

            # Update polling state — new_last_row is the actual sheet row number
            # of the last row we just processed (1-indexed, same as Google Sheets).
            # start_row is the first row we read, so last row = start_row + len - 1.
            new_last_row = start_row + len(new_rows) - 1
            await self._update_poll_state(connection_id, new_last_row)

            # Update stats
            if new_count > 0:
                await (
                    self.db.database.from_("sheet_connections")
                    .eq("id", connection_id)
                    .update({
                        "total_leads_found": conn.get("total_leads_found", 0)
                        + new_count,
                    }, return_representation=True)
                )

            # Retry any pending leads that never got a call triggered
            # (e.g. from when Celery was down or rate-limited on a previous poll)
            await self._retry_pending_leads(conn, org_id)

            logger.info(
                "sheet.poll_complete",
                connection_id=connection_id,
                new_leads=new_count,
                new_last_row=new_last_row,
            )
            return new_count

        except SheetAuthError as exc:
            # Auth failure → mark needs_reauth, increment error count
            new_error_count = conn.get("consecutive_error_count", 0) + 1
            update_fields: dict = {
                "last_error": str(exc),
                "last_polled_at": datetime.now(timezone.utc).isoformat(),
                "needs_reauth": True,
                "consecutive_error_count": new_error_count,
            }
            # Auto-pause after too many consecutive failures
            if new_error_count >= _MAX_CONSECUTIVE_ERRORS:
                update_fields["is_active"] = False
                logger.warning(
                    "sheet.auto_paused",
                    connection_id=connection_id,
                    error_count=new_error_count,
                )
                await self.audit.log(
                    org_id=conn.get("organization_id", ""),
                    event_type=AuditEvent.POLL_AUTO_PAUSED,
                    connection_id=connection_id,
                    details={"error_count": new_error_count, "reason": str(exc)},
                    severity="error",
                )
            else:
                await self.audit.log(
                    org_id=conn.get("organization_id", ""),
                    event_type=AuditEvent.POLL_ERROR_AUTH,
                    connection_id=connection_id,
                    details={"error": str(exc), "consecutive": new_error_count},
                    severity="error",
                )
            await (
                self.db.database.from_("sheet_connections")
                .eq("id", connection_id)
                .update(update_fields, return_representation=True)
            )
            logger.error(
                "sheet.poll_auth_error",
                connection_id=connection_id,
                error=str(exc),
            )
            return 0

        except SheetClientError as exc:
            # Non-auth sheet error — record and increment error count
            new_error_count = conn.get("consecutive_error_count", 0) + 1
            update_fields = {
                "last_error": str(exc),
                "last_polled_at": datetime.now(timezone.utc).isoformat(),
                "consecutive_error_count": new_error_count,
            }
            if new_error_count >= _MAX_CONSECUTIVE_ERRORS:
                update_fields["is_active"] = False
                await self.audit.log(
                    org_id=conn.get("organization_id", ""),
                    event_type=AuditEvent.POLL_AUTO_PAUSED,
                    connection_id=connection_id,
                    details={"error_count": new_error_count, "reason": str(exc)},
                    severity="error",
                )
            else:
                await self.audit.log(
                    org_id=conn.get("organization_id", ""),
                    event_type=AuditEvent.POLL_ERROR_NETWORK,
                    connection_id=connection_id,
                    details={"error": str(exc), "consecutive": new_error_count},
                    severity="warning",
                )
            await (
                self.db.database.from_("sheet_connections")
                .eq("id", connection_id)
                .update(update_fields, return_representation=True)
            )
            logger.error(
                "sheet.poll_error",
                connection_id=connection_id,
                error=str(exc),
            )
            return 0

    async def _retry_pending_leads(self, conn: dict, org_id: str) -> None:
        """Retry calling any leads stuck in 'pending' status.

        Leads get stuck in pending when:
        - The Celery worker was down when they were first detected
        - They were rate-limited on a previous poll cycle
        - The call trigger failed transiently

        Runs on every poll cycle. Respects rate limits.
        """
        connection_id = conn["id"]
        max_concurrent = conn.get("max_concurrent_calls", 5)

        try:
            result = (
                await self.db.database.from_("sheet_leads")
                .select("*")
                .eq("connection_id", connection_id)
                .eq("call_status", "pending")
                .execute()
            )
            pending_leads = result if isinstance(result, list) else []

            if not pending_leads:
                return

            logger.info(
                "sheet.retry_pending",
                connection_id=connection_id,
                count=len(pending_leads),
            )

            for lead_record in pending_leads:
                active_calls = await self._count_active_calls(connection_id)
                if active_calls >= max_concurrent:
                    break  # Respect rate limit — try again next poll

                try:
                    lead_data = (
                        json.loads(lead_record["lead_data"])
                        if isinstance(lead_record.get("lead_data"), str)
                        else (lead_record.get("lead_data") or {})
                    )
                    lead_data["phone"] = lead_record.get("phone_number", lead_data.get("phone", ""))
                    if not lead_data.get("phone"):
                        continue

                    await self._trigger_lead_call(lead_record, conn, lead_data, org_id)
                except Exception as exc:
                    logger.warning(
                        "sheet.retry_pending_failed",
                        lead_id=lead_record.get("id"),
                        error=str(exc),
                    )

        except Exception as exc:
            logger.warning("sheet.retry_pending_error", connection_id=connection_id, error=str(exc))

    # ── Post-call write-back ──────────────────────────────────────────

    async def write_call_results(
        self,
        lead_id: str,
        call_status: str,
        call_summary: str | None = None,
        lead_tag: str | None = None,
        callback_time: str | None = None,
        duration_seconds: int | None = None,
    ) -> None:
        """Write call results back to the Google Sheet and update local DB.

        Called from webhook_service when a call with a sheet_lead completes.
        """

        # 1. Load the lead and its connection
        lead_result = (
            await self.db.database.from_("sheet_leads")
            .select("*, sheet_connections(*)")
            .eq("id", lead_id)
            .execute()
        )
        leads = (lead_result if isinstance(lead_result, list) else [])
        if not leads:
            logger.warning("sheet.writeback_lead_not_found", lead_id=lead_id)
            return

        lead = leads[0]
        conn = lead.get("sheet_connections")
        if not conn:
            logger.warning(
                "sheet.writeback_no_connection", lead_id=lead_id
            )
            return

        # 2. Update local DB
        updates: dict = {
            "call_status": call_status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if call_summary:
            updates["call_summary"] = call_summary
        if lead_tag:
            updates["lead_tag"] = lead_tag
        if callback_time:
            updates["callback_at"] = callback_time
            updates["call_status"] = "callback_scheduled"

        await (
            self.db.database.from_("sheet_leads")
            .eq("id", lead_id)
            .update(updates, return_representation=True)
        )

        # 3. Write back to Google Sheet
        try:
            column_mapping = (
                json.loads(conn["column_mapping"])
                if isinstance(conn["column_mapping"], str)
                else conn["column_mapping"]
            )
            client = GoogleSheetsClient(
                conn["credentials_json"], conn["spreadsheet_id"]
            )
            await client.connect()

            headers = await client.read_headers(conn["sheet_name"])
            cell_updates = []
            row_num = lead["row_number"]

            # Write results to mapped or appended columns
            writeback_fields = {
                "Call Status": call_status or "",
                "Call Summary": call_summary or "",
                "Lead Tag": lead_tag or "",
                "Callback Time": callback_time or "",
                "Call Duration": str(duration_seconds or ""),
            }

            for field_name, value in writeback_fields.items():
                if not value:
                    continue
                if field_name in headers:
                    col_idx = headers.index(field_name)
                    col_letter = col_index_to_letter(col_idx)
                else:
                    # Append new column with this header
                    headers.append(field_name)
                    col_idx = len(headers) - 1
                    col_letter = col_index_to_letter(col_idx)
                    # Write header
                    cell_updates.append(
                        CellUpdate(
                            conn["sheet_name"], col_letter, 1, field_name
                        )
                    )

                cell_updates.append(
                    CellUpdate(conn["sheet_name"], col_letter, row_num, value)
                )

            if cell_updates:
                await client.update_cells(conn["sheet_name"], cell_updates)

            # Mark writeback as done
            await (
                self.db.database.from_("sheet_leads")
                .eq("id", lead_id)
                .update({"writeback_done": True}, return_representation=True)
            )

            # Update connection stats
            stat_updates: dict = {
                "total_leads_called": conn.get("total_leads_called", 0) + 1,
            }
            if lead_tag and lead_tag.lower() in ("qualified", "interested"):
                stat_updates["total_leads_qualified"] = (
                    conn.get("total_leads_qualified", 0) + 1
                )
            await (
                self.db.database.from_("sheet_connections")
                .eq("id", conn["id"])
                .update(stat_updates, return_representation=True)
            )

            logger.info(
                "sheet.writeback_done",
                lead_id=lead_id,
                row=row_num,
                fields=list(writeback_fields.keys()),
            )

        except Exception as exc:
            logger.error(
                "sheet.writeback_failed",
                lead_id=lead_id,
                error=str(exc),
            )

        # 4. Schedule callback if requested
        if callback_time:
            await self._schedule_callback(lead, conn, callback_time)

    # ── Leads listing ─────────────────────────────────────────────────

    async def list_leads(
        self,
        connection_id: str,
        org_id: str,
        page: int = 1,
        limit: int = 20,
    ) -> SheetLeadsListResponse:
        """List leads for a connection with pagination."""

        # Verify connection belongs to org
        await self._get_connection_row(connection_id, org_id)

        offset = (page - 1) * limit

        # Get total count
        count_result = (
            await self.db.database.from_("sheet_leads")
            .select("id")
            .eq("connection_id", connection_id)
            .execute()
        )
        total = (len(count_result) if isinstance(count_result, list) else 0)

        # Get page
        result = (
            await self.db.database.from_("sheet_leads")
            .select("*")
            .eq("connection_id", connection_id)
            .order("row_number", desc=False)
            .offset(offset).limit(limit)
            .execute()
        )
        rows = (result if isinstance(result, list) else [])

        return SheetLeadsListResponse(
            leads=[self._to_lead_response(r) for r in rows],
            total=total,
            page=page,
            limit=limit,
        )

    async def get_connection_stats(
        self, connection_id: str, org_id: str
    ) -> SheetConnectionStats:
        """Get aggregated stats for a connection."""

        await self._get_connection_row(connection_id, org_id)

        # Count by status
        result = (
            await self.db.database.from_("sheet_leads")
            .select("call_status")
            .eq("connection_id", connection_id)
            .execute()
        )
        rows = (result if isinstance(result, list) else [])

        counts: dict[str, int] = {
            "pending": 0,
            "calling": 0,
            "completed": 0,
            "failed": 0,
            "callback_scheduled": 0,
        }
        for r in rows:
            s = r.get("call_status", "pending")
            if s in counts:
                counts[s] += 1

        conn_result = (
            await self.db.database.from_("sheet_connections")
            .select(
                "total_leads_found, total_leads_called, total_leads_qualified"
            )
            .eq("id", connection_id)
            .execute()
        )
        conn = conn_result[0] if conn_result else {}

        return SheetConnectionStats(
            total_leads_found=conn.get("total_leads_found", 0),
            total_leads_called=conn.get("total_leads_called", 0),
            total_leads_qualified=conn.get("total_leads_qualified", 0),
            **counts,
        )

    # ── Internal helpers ──────────────────────────────────────────────

    async def _get_connection_row(
        self, connection_id: str, org_id: str
    ) -> dict:
        """Fetch a connection row, scoped to org. Raises 404 if not found."""
        from fastapi import HTTPException, status

        result = (
            await self.db.database.from_("sheet_connections")
            .select("*")
            .eq("id", connection_id)
            .eq("organization_id", org_id)
            .execute()
        )
        rows = (result if isinstance(result, list) else [])
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sheet connection not found",
            )
        return rows[0]

    async def _verify_agent_ownership(
        self, workflow_id: int, org_id: str
    ) -> None:
        """Verify agent belongs to the organization."""
        from fastapi import HTTPException, status

        result = (
            await self.db.database.from_("dograh_agent_mappings")
            .select("id")
            .eq("dograh_workflow_id", workflow_id)
            .eq("organization_id", org_id)
            .execute()
        )
        rows = (result if isinstance(result, list) else [])
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agent {workflow_id} not found in your organization",
            )

    async def _sync_dograh_webhook(self, workflow_id: int) -> None:
        """Ensure the Dograh agent has a webhook node pointing to our backend.

        This is called once after a sheet connection is created/resumed so that
        every call made via that agent automatically posts results back to us.
        Failures are logged but do not block connection creation.
        """
        from app.integrations.dograh_client import DograhClient

        settings = get_settings()
        public_url = getattr(settings, "BACKEND_PUBLIC_URL", "").rstrip("/")
        if not public_url:
            logger.warning(
                "sheet.webhook_sync_skipped",
                reason="BACKEND_PUBLIC_URL not set",
            )
            return

        webhook_url = f"{public_url}/api/v1/webhooks/dograh"
        client = DograhClient()
        added = await client.ensure_webhook_node(workflow_id, webhook_url)
        logger.info(
            "sheet.webhook_sync_done",
            workflow_id=workflow_id,
            webhook_url=webhook_url,
            was_added=added,
        )

    async def _trigger_lead_call(
        self,
        lead_record: dict,
        conn: dict,
        lead_data: dict,
        org_id: str,
    ) -> None:
        """Trigger a Dograh call for a sheet lead."""

        # Look up agent UUID
        agent_result = (
            await self.db.database.from_("dograh_agent_mappings")
            .select("dograh_workflow_uuid")
            .eq("dograh_workflow_id", conn["agent_workflow_id"])
            .eq("organization_id", org_id)
            .execute()
        )
        agents = (agent_result if isinstance(agent_result, list) else [])
        if not agents or not agents[0].get("dograh_workflow_uuid"):
            logger.warning(
                "sheet.agent_not_found",
                workflow_id=conn["agent_workflow_id"],
                org_id=org_id,
            )
            return

        workflow_uuid = agents[0]["dograh_workflow_uuid"]

        # Build initial_context from mapped lead data for personalized calls
        initial_context = {
            "source": "google_sheets",
            "connection_id": conn["id"],
            "sheet_lead_id": lead_record.get("id", ""),
        }
        # Add all lead fields to context (name, email, etc.)
        for key, value in lead_data.items():
            if key != "phone" and value:
                initial_context[f"lead_{key}"] = value

        try:
            result = await self.dograh.trigger_call(
                workflow_uuid=workflow_uuid,
                phone_number=lead_data["phone"],
                initial_context=initial_context,
            )

            run_id = result.get("workflow_run_id")

            # Update sheet_lead with run ID and status
            await (
                self.db.database.from_("sheet_leads")
                .eq("id", lead_record.get("id"))
                .update({
                    "dograh_run_id": run_id,
                    "call_status": "calling",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }, return_representation=True)
            )

            # Also create a call_runs record (maintains dual storage pattern)
            await (
                self.db.database.from_("call_runs")
                .insert([{
                    "dograh_run_id": run_id,
                    "dograh_workflow_id": conn["agent_workflow_id"],
                    "organization_id": org_id,
                    "call_type": "outbound",
                    "status": "initiated",
                    "phone_number": lead_data["phone"],
                    "initial_context": json.dumps(initial_context),
                }])
            )

            # Audit the call trigger
            await self.audit.log(
                org_id=org_id,
                event_type=AuditEvent.LEAD_CALL_TRIGGERED,
                connection_id=str(conn.get("id", "")),
                lead_id=str(lead_record.get("id", "")),
                details={
                    "run_id": run_id,
                    "phone": lead_data["phone"][:6] + "****",
                    "agent_workflow_id": conn["agent_workflow_id"],
                },
            )

            logger.info(
                "sheet.call_triggered",
                lead_id=lead_record.get("id"),
                run_id=run_id,
                phone=lead_data["phone"][:6] + "****",
            )

        except Exception as exc:
            logger.error(
                "sheet.call_trigger_failed",
                lead_id=lead_record.get("id"),
                error=str(exc),
            )
            await (
                self.db.database.from_("sheet_leads")
                .eq("id", lead_record.get("id"))
                .update({
                    "call_status": "failed",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }, return_representation=True)
            )

    async def _update_poll_state(
        self, connection_id: str, last_row: int
    ) -> None:
        """Update connection polling state."""
        await (
            self.db.database.from_("sheet_connections")
            .eq("id", connection_id)
            .update({
                "last_row_processed": last_row,
                "last_polled_at": datetime.now(timezone.utc).isoformat(),
                "last_error": None,
            }, return_representation=True)
        )

    async def _is_duplicate_phone(
        self,
        phone: str,
        connection_id: str,
        window_hours: int,
    ) -> bool:
        """Return True if this phone number was already called within the window.

        Duplicate window prevents re-calling leads that appear multiple times
        in a sheet or were added again after a data import.
        """
        if window_hours <= 0:
            return False

        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=window_hours)
        ).isoformat()

        result = (
            await self.db.database.from_("sheet_leads")
            .select("id")
            .eq("connection_id", connection_id)
            .eq("phone_number", phone)
            .neq("call_status", "pending")   # already processed
            .gte("created_at", cutoff)
            .limit(1)
            .execute()
        )
        return bool(result)

    async def _count_active_calls(self, connection_id: str) -> int:
        """Count leads currently being called for this connection.

        Used for rate limiting — we cap at max_concurrent_calls to avoid
        hammering the Dograh API and the lead's phone.
        """
        result = (
            await self.db.database.from_("sheet_leads")
            .select("id")
            .eq("connection_id", connection_id)
            .eq("call_status", "calling")
            .execute()
        )
        return (len(result) if isinstance(result, list) else 0)


    async def _schedule_callback(
        self, lead: dict, conn: dict, callback_time: str
    ) -> None:
        """Insert a scheduled callback record."""
        try:
            lead_data = (
                json.loads(lead["lead_data"])
                if isinstance(lead["lead_data"], str)
                else lead.get("lead_data", {})
            )
            await (
                self.db.database.from_("scheduled_callbacks")
                .insert([{
                    "organization_id": lead["organization_id"],
                    "sheet_lead_id": lead["id"],
                    "phone_number": lead["phone_number"],
                    "workflow_id": conn["agent_workflow_id"],
                    "initial_context": json.dumps(lead_data),
                    "callback_at": callback_time,
                    "status": "pending",
                }])
            )
            logger.info(
                "sheet.callback_scheduled",
                lead_id=lead["id"],
                callback_at=callback_time,
            )
        except Exception as exc:
            logger.warning(
                "sheet.callback_schedule_failed",
                lead_id=lead["id"],
                error=str(exc),
            )

    def _extract_lead_from_row(
        self,
        row_data: list[str],
        headers: list[str],
        column_mapping: dict[str, str],
    ) -> dict:
        """Extract lead fields from a sheet row using column mapping."""
        lead: dict = {}
        for field_name, col_letter in column_mapping.items():
            col_idx = ord(col_letter.upper()) - 65
            if col_idx < len(row_data):
                lead[field_name] = row_data[col_idx]
            else:
                lead[field_name] = ""
        return lead

    def _to_connection_response(self, row: dict) -> SheetConnectionResponse:
        """Convert a DB row to a response schema."""
        col_map = row.get("column_mapping", {})
        if isinstance(col_map, str):
            col_map = json.loads(col_map)
        return SheetConnectionResponse(
            id=str(row.get("id", "")),
            organization_id=str(row.get("organization_id", "")),
            provider=row.get("provider", "google_sheets"),
            sheet_url=row.get("sheet_url", ""),
            spreadsheet_id=row.get("spreadsheet_id", ""),
            sheet_name=row.get("sheet_name", ""),
            column_mapping=col_map,
            agent_workflow_id=row.get("agent_workflow_id", 0),
            is_active=row.get("is_active", True),
            last_row_processed=row.get("last_row_processed", 1),
            last_polled_at=row.get("last_polled_at"),
            last_error=row.get("last_error"),
            polling_interval_secs=row.get("polling_interval_secs", 60),
            total_leads_found=row.get("total_leads_found", 0),
            total_leads_called=row.get("total_leads_called", 0),
            total_leads_qualified=row.get("total_leads_qualified", 0),
            # Phase 4
            needs_reauth=row.get("needs_reauth", False),
            max_concurrent_calls=row.get("max_concurrent_calls", 5),
            duplicate_window_hours=row.get("duplicate_window_hours", 24),
            consecutive_error_count=row.get("consecutive_error_count", 0),
            created_at=row.get("created_at", datetime.now(timezone.utc)),
            updated_at=row.get("updated_at", datetime.now(timezone.utc)),
        )

    def _to_lead_response(self, row: dict) -> SheetLeadResponse:
        """Convert a DB row to a lead response schema."""
        lead_data = row.get("lead_data", {})
        if isinstance(lead_data, str):
            lead_data = json.loads(lead_data)
        return SheetLeadResponse(
            id=str(row.get("id", "")),
            connection_id=str(row.get("connection_id", "")),
            row_number=row.get("row_number", 0),
            phone_number=row.get("phone_number", ""),
            lead_data=lead_data,
            call_status=row.get("call_status", "pending"),
            call_summary=row.get("call_summary"),
            lead_tag=row.get("lead_tag"),
            callback_at=row.get("callback_at"),
            writeback_done=row.get("writeback_done", False),
            dograh_run_id=row.get("dograh_run_id"),
            created_at=row.get("created_at", datetime.now(timezone.utc)),
            updated_at=row.get("updated_at", datetime.now(timezone.utc)),
        )
