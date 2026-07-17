from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core.logging import logger
from app.core.posthog import track_event
from app.integrations.insforge_client import get_insforge_admin
from app.schemas.appointment import (
    AppointmentCreateRequest,
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentUpdateRequest,
)
from app.schemas.auth import UserContext


class AppointmentService:
    """Business logic for appointment management.

    Appointments are extracted from call gathered_context or created
    manually. All queries scoped to organization_id.
    """

    def __init__(self) -> None:
        self.db = get_insforge_admin()

    async def list_appointments(
        self,
        current_user: UserContext,
        page: int = 1,
        per_page: int = 20,
        status_filter: str | None = None,
    ) -> AppointmentListResponse:
        """Paginated appointment list for the org."""
        org_id = current_user.organization_id

        try:
            query = self.db.database.from_("appointments") \
                .select("*") \
                .eq("organization_id", org_id) \
                .order("created_at", desc=True)

            if status_filter:
                query = query.eq("status", status_filter)

            all_rows = await query.execute()
            all_rows = all_rows if isinstance(all_rows, list) else []
        except Exception as exc:
            logger.error("appointments.list_failed", org_id=org_id, error=str(exc))
            all_rows = []

        # Resolve campaign names via call_runs → campaigns
        campaign_map: dict[str, str | None] = {}
        call_run_ids = list({r["call_run_id"] for r in all_rows if r.get("call_run_id")})
        if call_run_ids:
            try:
                run_rows = await self.db.database.from_("call_runs") \
                    .select("id, campaign_id") \
                    .in_("id", call_run_ids) \
                    .execute()
                run_rows = run_rows if isinstance(run_rows, list) else []

                campaign_ids = list({r["campaign_id"] for r in run_rows if r.get("campaign_id")})
                camp_names: dict[str, str] = {}
                if campaign_ids:
                    camp_rows = await self.db.database.from_("campaigns") \
                        .select("id, name") \
                        .in_("id", campaign_ids) \
                        .execute()
                    camp_rows = camp_rows if isinstance(camp_rows, list) else []
                    camp_names = {r["id"]: r.get("name", "") for r in camp_rows}

                for run in run_rows:
                    cid = run.get("campaign_id")
                    campaign_map[run["id"]] = camp_names.get(cid) if cid else None
            except Exception as exc:
                logger.warning("appointments.campaign_resolve_failed", error=str(exc))

        total = len(all_rows)
        offset = (page - 1) * per_page
        rows = all_rows[offset: offset + per_page]

        appointments = [self._row_to_response(r, campaign_map) for r in rows]
        return AppointmentListResponse(appointments=appointments, total=total)

    async def get_appointment(
        self,
        appointment_id: str,
        current_user: UserContext,
    ) -> AppointmentResponse:
        """Get a single appointment by ID."""
        org_id = current_user.organization_id

        try:
            rows = await self.db.database.from_("appointments") \
                .select("*") \
                .eq("id", appointment_id) \
                .eq("organization_id", org_id) \
                .limit(1) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            err = str(exc)
            logger.error("appointments.get_failed", id=appointment_id, error=err)
            # Invalid UUID format → treat as not found
            if "invalid input syntax" in err:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Appointment not found",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch appointment",
            )

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )

        return self._row_to_response(rows[0])

    async def create_appointment(
        self,
        data: AppointmentCreateRequest,
        current_user: UserContext,
    ) -> AppointmentResponse:
        """Manually create an appointment linked to a call run."""
        org_id = current_user.organization_id

        # Verify the call run belongs to this org
        try:
            cr_rows = await self.db.database.from_("call_runs") \
                .select("id") \
                .eq("id", data.call_run_id) \
                .eq("organization_id", org_id) \
                .limit(1) \
                .execute()
            cr_rows = cr_rows if isinstance(cr_rows, list) else []
            if not cr_rows:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Call run not found in this organization",
                )
        except HTTPException:
            raise
        except Exception as exc:
            err = str(exc)
            logger.error("appointments.call_run_verify_failed", error=err)
            if "invalid input syntax" in err:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Call run not found in this organization",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify call run",
            )

        record = {
            "organization_id": org_id,
            "call_run_id": data.call_run_id,
            "contact_name": data.contact_name,
            "contact_phone": data.contact_phone,
            "notes": data.notes,
            "status": "scheduled",
        }
        if data.appointment_date:
            record["appointment_date"] = data.appointment_date

        try:
            result = await self.db.database.from_("appointments").insert([record])
            result = result if isinstance(result, list) else []
        except Exception as exc:
            logger.error("appointments.create_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create appointment",
            )

        track_event(
            distinct_id=org_id,
            event="appointment_created",
            properties={
                "org_id": org_id,
                "call_run_id": data.call_run_id,
                "source": "manual",
            },
        )

        if result:
            return self._row_to_response(result[0])

        # Fallback: return from the data we just inserted
        return AppointmentResponse(
            id="pending",
            organization_id=org_id,
            call_run_id=data.call_run_id,
            contact_name=data.contact_name,
            contact_phone=data.contact_phone,
            appointment_date=data.appointment_date,
            notes=data.notes,
            status="scheduled",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    async def update_appointment(
        self,
        appointment_id: str,
        data: AppointmentUpdateRequest,
        current_user: UserContext,
    ) -> AppointmentResponse:
        """Update an existing appointment."""
        org_id = current_user.organization_id

        # Verify it exists and belongs to org
        await self.get_appointment(appointment_id, current_user)

        updates = {}
        if data.contact_name is not None:
            updates["contact_name"] = data.contact_name
        if data.contact_phone is not None:
            updates["contact_phone"] = data.contact_phone
        if data.appointment_date is not None:
            updates["appointment_date"] = data.appointment_date
        if data.notes is not None:
            updates["notes"] = data.notes
        if data.status is not None:
            valid_statuses = {"scheduled", "confirmed", "cancelled", "completed"}
            if data.status not in valid_statuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
                )
            updates["status"] = data.status

        if not updates:
            return await self.get_appointment(appointment_id, current_user)

        try:
            result = await self.db.database.from_("appointments") \
                .eq("id", appointment_id) \
                .eq("organization_id", org_id) \
                .update(updates, return_representation=True)
            result = result if isinstance(result, list) else []
        except json.JSONDecodeError:
            result = []
        except Exception as exc:
            logger.error("appointments.update_failed", id=appointment_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update appointment",
            )

        if result:
            return self._row_to_response(result[0])
        return await self.get_appointment(appointment_id, current_user)

    @staticmethod
    async def extract_from_gathered_context(
        org_id: str,
        call_run_id: str,
        gathered_context: dict,
    ) -> None:
        """Auto-extract appointment from a call's gathered_context.

        Called from webhook_service when a call completes.
        Supports two formats:
        1. Nested dict: gathered_context.appointment = { name, phone, date, notes }
        2. Flat variables: gathered_context.appointment_requested = true,
           appointment_name, appointment_phone, appointment_date, appointment_notes
        """
        # Try nested dict format first
        appointment_data = gathered_context.get("appointment") or gathered_context.get("booking")

        # Fall back to flat Dograh extraction variables
        if not appointment_data:
            requested = gathered_context.get("appointment_requested")
            # Accept truthy values: True, "true", "yes", "True", etc.
            if not requested or str(requested).lower() not in ("true", "yes", "1"):
                return
            appointment_data = {
                "name": gathered_context.get("appointment_name", ""),
                "phone": gathered_context.get("appointment_phone", ""),
                "date": gathered_context.get("appointment_date", ""),
                "notes": gathered_context.get("appointment_notes", ""),
            }

        if not isinstance(appointment_data, dict):
            return

        record = {
            "organization_id": org_id,
            "contact_name": appointment_data.get("name") or "",
            "contact_phone": appointment_data.get("phone") or "",
            "notes": appointment_data.get("notes") or "",
            "status": "scheduled",
        }

        appt_date = appointment_data.get("date") or appointment_data.get("datetime")
        if appt_date:
            record["appointment_date"] = str(appt_date)

        # Resolve the local call_runs UUID from the Dograh integer run_id
        # The call_run_id column is a UUID FK referencing call_runs(id)
        try:
            db = get_insforge_admin()
            run_rows = await db.database.from_("call_runs") \
                .select("id") \
                .eq("dograh_run_id", int(call_run_id)) \
                .execute()
            run_rows = run_rows if isinstance(run_rows, list) else []
            if run_rows:
                record["call_run_id"] = run_rows[0]["id"]
            else:
                logger.warning(
                    "appointments.no_local_run_found",
                    dograh_run_id=call_run_id,
                )
                # Skip call_run_id — insert without it if column allows,
                # or abort if it's required
                return
        except Exception as exc:
            logger.warning(
                "appointments.run_lookup_failed",
                dograh_run_id=call_run_id,
                error=str(exc),
            )
            return

        try:
            # Check if an appointment already exists (e.g. created by book_appointment tool)
            # Match on org_id + contact_phone + appointment_date
            contact_phone = record.get("contact_phone", "")
            appt_date_val = record.get("appointment_date")

            existing = []
            if contact_phone and appt_date_val:
                existing = await db.database.from_("appointments") \
                    .select("id, call_run_id") \
                    .eq("organization_id", org_id) \
                    .eq("contact_phone", contact_phone) \
                    .eq("appointment_date", appt_date_val) \
                    .limit(1) \
                    .execute()
                existing = existing if isinstance(existing, list) else []

            if existing:
                # Update the tool-booked appointment with the call_run_id
                # so it links to the campaign
                update_data = {"call_run_id": record["call_run_id"]}
                # Also update contact_name if it was empty
                if not existing[0].get("contact_name"):
                    update_data["contact_name"] = record.get("contact_name", "")
                await db.database.from_("appointments") \
                    .eq("id", existing[0]["id"]) \
                    .update(update_data)
                logger.info(
                    "appointments.linked_to_call_run",
                    appointment_id=existing[0]["id"],
                    call_run_id=record.get("call_run_id"),
                    dograh_run_id=call_run_id,
                )
            else:
                await db.database.from_("appointments").insert([record])
                logger.info(
                    "appointments.auto_extracted",
                    org_id=org_id,
                    call_run_id=record.get("call_run_id"),
                    dograh_run_id=call_run_id,
                )
        except Exception as exc:
            logger.warning(
                "appointments.auto_extract_failed",
                call_run_id=call_run_id,
                error=str(exc),
            )

    def _row_to_response(
        self, row: dict, campaign_map: dict[str, str | None] | None = None,
    ) -> AppointmentResponse:
        """Convert a DB row to response schema."""
        call_run_id = str(row.get("call_run_id", ""))
        campaign_name = None
        if campaign_map:
            campaign_name = campaign_map.get(call_run_id)

        return AppointmentResponse(
            id=str(row.get("id", "")),
            organization_id=str(row.get("organization_id", "")),
            call_run_id=call_run_id,
            contact_name=row.get("contact_name", ""),
            contact_phone=row.get("contact_phone", ""),
            appointment_date=str(row["appointment_date"]) if row.get("appointment_date") else None,
            notes=row.get("notes", ""),
            status=row.get("status", "scheduled"),
            created_at=str(row.get("created_at", "")),
            campaign_name=campaign_name,
        )
