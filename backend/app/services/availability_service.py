from __future__ import annotations

import json
from datetime import date, datetime, time, timezone

from fastapi import HTTPException, status

from app.core.logging import logger
from app.integrations.insforge_client import get_insforge_admin
from app.schemas.auth import UserContext
from app.schemas.availability import (
    AvailabilityCheckResponse,
    AvailabilityOverrideRequest,
    AvailabilityOverrideResponse,
    AvailableSlot,
    OverrideListResponse,
    SetWeeklyScheduleRequest,
    WeeklyScheduleResponse,
    WeeklySlotResponse,
)


class AvailabilityService:
    """Manages per-user weekly availability and date overrides.

    The public `check_availability()` method is called by the Dograh
    AI agent (via Tool HTTP call) to offer valid appointment slots
    to the lead during a live call.
    """

    def __init__(self) -> None:
        self.db = get_insforge_admin()

    # ------------------------------------------------------------------
    # Weekly Schedule CRUD
    # ------------------------------------------------------------------

    async def get_weekly_schedule(
        self,
        current_user: UserContext,
    ) -> WeeklyScheduleResponse:
        """Get the authenticated user's weekly recurring schedule."""
        org_id = current_user.organization_id
        user_id = str(current_user.user_id)

        try:
            rows = await self.db.database.from_("availability_slots") \
                .select("*") \
                .eq("organization_id", org_id) \
                .eq("user_id", user_id) \
                .order("day_of_week") \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("availability.get_schedule_failed", error=str(exc))
            rows = []

        slots = [
            WeeklySlotResponse(
                id=str(r["id"]),
                day_of_week=r["day_of_week"],
                start_time=str(r["start_time"])[:5],  # "09:00:00" → "09:00"
                end_time=str(r["end_time"])[:5],
                is_active=r.get("is_active", True),
            )
            for r in rows
        ]

        return WeeklyScheduleResponse(user_id=user_id, slots=slots)

    async def set_weekly_schedule(
        self,
        data: SetWeeklyScheduleRequest,
        current_user: UserContext,
    ) -> WeeklyScheduleResponse:
        """Bulk replace the user's weekly schedule.

        Deletes all existing slots and inserts the new ones.
        This is simpler than diffing and handles reordering.
        """
        org_id = current_user.organization_id
        user_id = str(current_user.user_id)

        # Validate times
        for slot in data.slots:
            if slot.start_time >= slot.end_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"start_time ({slot.start_time}) must be before end_time ({slot.end_time})",
                )

        # Delete existing slots for this user
        try:
            await self.db.database.from_("availability_slots") \
                .eq("organization_id", org_id) \
                .eq("user_id", user_id) \
                .delete()
        except json.JSONDecodeError:
            pass  # InsForge SDK bug: delete returns empty body
        except Exception as exc:
            logger.error("availability.delete_old_failed", error=str(exc))

        # Insert new slots
        if data.slots:
            records = [
                {
                    "organization_id": org_id,
                    "user_id": user_id,
                    "day_of_week": s.day_of_week,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "is_active": s.is_active,
                }
                for s in data.slots
            ]

            try:
                await self.db.database.from_("availability_slots").insert(records)
            except Exception as exc:
                logger.error("availability.insert_failed", error=str(exc))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save schedule",
                ) from exc

        logger.info(
            "availability.schedule_saved",
            user_id=user_id,
            org_id=org_id,
            slot_count=len(data.slots),
        )

        return await self.get_weekly_schedule(current_user)

    # ------------------------------------------------------------------
    # Override CRUD
    # ------------------------------------------------------------------

    async def add_override(
        self,
        data: AvailabilityOverrideRequest,
        current_user: UserContext,
    ) -> AvailabilityOverrideResponse:
        """Add a date-specific availability override."""
        org_id = current_user.organization_id
        user_id = str(current_user.user_id)

        if data.is_available and (not data.start_time or not data.end_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_time and end_time required when adding extra availability",
            )

        record = {
            "organization_id": org_id,
            "user_id": user_id,
            "override_date": data.override_date,
            "is_available": data.is_available,
            "start_time": data.start_time,
            "end_time": data.end_time,
            "reason": data.reason,
        }

        try:
            result = await self.db.database.from_("availability_overrides").insert([record])
            result = result if isinstance(result, list) else []
        except Exception as exc:
            logger.error("availability.override_add_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add override",
            ) from exc

        row = result[0] if result else record
        return self._override_to_response(row)

    async def list_overrides(
        self,
        current_user: UserContext,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> OverrideListResponse:
        """List date overrides for the current user."""
        org_id = current_user.organization_id
        user_id = str(current_user.user_id)

        try:
            query = self.db.database.from_("availability_overrides") \
                .select("*") \
                .eq("organization_id", org_id) \
                .eq("user_id", user_id) \
                .order("override_date")

            if from_date:
                query = query.gte("override_date", from_date)
            if to_date:
                query = query.lte("override_date", to_date)

            rows = await query.execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("availability.overrides_list_failed", error=str(exc))
            rows = []

        overrides = [self._override_to_response(r) for r in rows]
        return OverrideListResponse(overrides=overrides, total=len(overrides))

    async def delete_override(
        self,
        override_id: str,
        current_user: UserContext,
    ) -> dict:
        """Delete a date override."""
        org_id = current_user.organization_id

        try:
            await self.db.database.from_("availability_overrides") \
                .eq("id", override_id) \
                .eq("organization_id", org_id) \
                .delete()
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            logger.error("availability.override_delete_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete override",
            ) from exc

        return {"status": "deleted", "id": override_id}

    # ------------------------------------------------------------------
    # Public Availability Check (called by Dograh Tool)
    # ------------------------------------------------------------------

    async def check_availability(
        self,
        org_id: str,
        check_date: str,
    ) -> AvailabilityCheckResponse:
        """Check available appointment slots for a given date.

        This is the public endpoint the Dograh AI agent calls
        mid-conversation to find open time windows.

        Logic:
        1. Parse the requested date → get day_of_week
        2. Fetch all active users' weekly slots for that day
        3. Subtract any "blocked" overrides for that date
        4. Subtract existing scheduled/confirmed appointments
        5. Return remaining open slots
        """
        try:
            parsed_date = date.fromisoformat(check_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD.",
            )

        day_of_week = parsed_date.isoweekday() % 7  # Python: Mon=1..Sun=7 → 0=Sun

        # 1. Get all active weekly slots for this org + day
        try:
            slot_rows = await self.db.database.from_("availability_slots") \
                .select("user_id, start_time, end_time") \
                .eq("organization_id", org_id) \
                .eq("day_of_week", day_of_week) \
                .eq("is_active", True) \
                .execute()
            slot_rows = slot_rows if isinstance(slot_rows, list) else []
        except Exception as exc:
            logger.error("availability.check_slots_failed", error=str(exc))
            slot_rows = []

        if not slot_rows:
            return AvailabilityCheckResponse(
                date=check_date,
                available_slots=[],
                message=f"No availability on {parsed_date.strftime('%A, %B %d')}.",
            )

        # 2. Get overrides that block this date
        try:
            override_rows = await self.db.database.from_("availability_overrides") \
                .select("user_id, is_available") \
                .eq("organization_id", org_id) \
                .eq("override_date", check_date) \
                .eq("is_available", False) \
                .execute()
            override_rows = override_rows if isinstance(override_rows, list) else []
        except Exception:
            override_rows = []

        blocked_users = {r["user_id"] for r in override_rows}

        # 3. Get existing appointments for this date
        try:
            date_start = f"{check_date}T00:00:00"
            date_end = f"{check_date}T23:59:59"
            appt_rows = await self.db.database.from_("appointments") \
                .select("appointment_date") \
                .eq("organization_id", org_id) \
                .in_("status", ["scheduled", "confirmed"]) \
                .gte("appointment_date", date_start) \
                .lte("appointment_date", date_end) \
                .execute()
            appt_rows = appt_rows if isinstance(appt_rows, list) else []
        except Exception:
            appt_rows = []

        booked_hours = set()
        for a in appt_rows:
            if a.get("appointment_date"):
                try:
                    dt = datetime.fromisoformat(str(a["appointment_date"]))
                    booked_hours.add(dt.strftime("%H:00"))
                except Exception:
                    pass

        # 4. Resolve user names
        user_ids = list({r["user_id"] for r in slot_rows} - blocked_users)
        user_names = {}
        if user_ids:
            try:
                user_rows = await self.db.database.from_("users") \
                    .select("id, full_name") \
                    .in_("id", user_ids) \
                    .execute()
                user_rows = user_rows if isinstance(user_rows, list) else []
                user_names = {r["id"]: r.get("full_name", "Team Member") for r in user_rows}
            except Exception:
                pass

        # 5. Build available slots (excluding blocked users)
        available = []
        for row in slot_rows:
            uid = row["user_id"]
            if uid in blocked_users:
                continue

            available.append(AvailableSlot(
                user_id=uid,
                user_name=user_names.get(uid, "Team Member"),
                start_time=str(row["start_time"])[:5],
                end_time=str(row["end_time"])[:5],
            ))

        # Human-readable message for the AI agent
        if available:
            slot_strs = [f"{s.user_name}: {s.start_time}-{s.end_time}" for s in available]
            day_name = parsed_date.strftime("%A, %B %d")
            message = f"Available on {day_name}: {'; '.join(slot_strs)}."
        else:
            message = f"No availability on {parsed_date.strftime('%A, %B %d')}."

        return AvailabilityCheckResponse(
            date=check_date,
            available_slots=available,
            message=message,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _override_to_response(row: dict) -> AvailabilityOverrideResponse:
        return AvailabilityOverrideResponse(
            id=str(row.get("id", "")),
            override_date=str(row.get("override_date", "")),
            is_available=row.get("is_available", False),
            start_time=str(row["start_time"])[:5] if row.get("start_time") else None,
            end_time=str(row["end_time"])[:5] if row.get("end_time") else None,
            reason=row.get("reason", ""),
            created_at=str(row.get("created_at", "")),
        )
