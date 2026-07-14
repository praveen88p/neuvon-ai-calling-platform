from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core.logging import logger
from app.core.posthog import track_event
from app.integrations.dograh_client import DograhClient
from app.integrations.insforge_client import get_insforge_admin
from app.schemas.auth import UserContext
from app.schemas.campaign import (
    CampaignActionResponse,
    CampaignCreate,
    CampaignListResponse,
    CampaignProgressResponse,
    CampaignResponse,
    CampaignUpdate,
    ContactListUploadResponse,
)

# Regex: only digits (with optional leading +)
_DIGITS_RE = re.compile(r"[^\d+]")


def _normalize_phone(raw: str, default_country_code: str = "") -> str:
    """Ensure a phone number starts with '+' country code.

    Args:
        raw: The raw phone number string from the CSV.
        default_country_code: Country code to prepend (e.g. '+91', '+1').
            If empty, numbers with 11+ digits get '+' prepended;
            shorter numbers are left for Dograh to validate.

    Rules:
    - Already starts with '+' → keep as-is
    - default_country_code provided → prepend it to bare digits
    - 11+ digits without '+' → prepend '+'  (likely includes country code)
    - Otherwise → prepend '+' and let Dograh validate
    """
    cleaned = _DIGITS_RE.sub("", raw.strip())
    if not cleaned:
        return raw.strip()
    if cleaned.startswith("+"):
        return cleaned
    digits_only = cleaned.lstrip("+")
    if default_country_code:
        # Ensure country code starts with '+'
        cc = default_country_code if default_country_code.startswith("+") else f"+{default_country_code}"
        return f"{cc}{digits_only}"
    # No default country code — best-effort
    if len(digits_only) >= 11:
        return f"+{digits_only}"
    return f"+{digits_only}"


def _normalize_csv(file_content: bytes, default_country_code: str = "") -> tuple[bytes, int]:
    """Parse CSV, normalize phone_number column, return (new_csv_bytes, contact_count).

    Args:
        file_content: Raw CSV bytes.
        default_country_code: Country code to prepend to numbers without one.

    Raises HTTPException if no 'phone_number' column is found.
    """
    try:
        text = file_content.decode("utf-8")
    except UnicodeDecodeError:
        text = file_content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CSV file appears to be empty or has no header row.",
        )

    # Find the phone column (case-insensitive)
    phone_col: str | None = None
    for col in reader.fieldnames:
        if col.strip().lower().replace(" ", "_") in ("phone_number", "phone", "phonenumber", "mobile", "cell"):
            phone_col = col
            break

    if not phone_col:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"CSV must contain a 'phone_number' column. "
                f"Found columns: {', '.join(reader.fieldnames)}"
            ),
        )

    # Rewrite CSV with normalized phone numbers
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames)
    writer.writeheader()

    count = 0
    for row in reader:
        raw = row.get(phone_col, "")
        row[phone_col] = _normalize_phone(raw, default_country_code)
        writer.writerow(row)
        count += 1

    return output.getvalue().encode("utf-8"), count


class CampaignService:
    """Business logic for campaign lifecycle operations.

    Dual-storage pattern: campaigns are created/managed in Dograh,
    with local InsForge records for org-scoped access control,
    billing tracking, and fast queries.
    """

    def __init__(self) -> None:
        self.dograh = DograhClient()
        self.db = get_insforge_admin()

    # ------------------------------------------------------------------
    # Upload contacts
    # ------------------------------------------------------------------

    async def upload_contacts(
        self,
        file_content: bytes,
        filename: str,
        current_user: UserContext,
        *,
        default_country_code: str = "",
    ) -> ContactListUploadResponse:
        """Upload contacts CSV via Dograh's presigned S3 URL flow.

        1. Normalize phone numbers (ensure '+' country code prefix)
        2. POST /s3/presigned-upload-url to get a presigned S3 URL + file_key
        3. PUT the normalized file directly to S3
        4. Return the file_key as source_id for campaign creation
        """
        org_id = current_user.organization_id
        logger.info("campaign.upload_contacts", org_id=org_id, filename=filename, country_code=default_country_code)

        # Normalize phone numbers in the CSV
        normalized_content, total_contacts = _normalize_csv(file_content, default_country_code)
        logger.info(
            "campaign.csv_normalized",
            org_id=org_id,
            total_contacts=total_contacts,
        )

        # Step 1: Get presigned upload URL
        try:
            presigned = await self.dograh.get_presigned_upload_url(
                file_name=filename,
                file_size=len(normalized_content),
                content_type="text/csv",
            )
        except Exception as exc:
            logger.error("campaign.presigned_url_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to get upload URL from voice provider",
            ) from exc

        upload_url = presigned.get("upload_url", "")
        file_key = presigned.get("file_key", "")

        if not upload_url or not file_key:
            logger.error("campaign.presigned_url_empty", org_id=org_id, presigned=presigned)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Voice provider returned invalid upload URL",
            )

        # Step 2: Upload normalized file to S3
        try:
            await self.dograh.upload_to_s3(upload_url, normalized_content)
        except Exception as exc:
            logger.error("campaign.s3_upload_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to upload contacts file",
            ) from exc

        track_event(
            distinct_id=str(org_id),
            event="leads_uploaded",
            properties={
                "org_id": str(org_id),
                "lead_count": total_contacts,
            },
        )

        return ContactListUploadResponse(
            contact_list_id=file_key,
            total_contacts=total_contacts,
        )

    # ------------------------------------------------------------------
    # Create campaign
    # ------------------------------------------------------------------

    async def create_campaign(
        self,
        data: CampaignCreate,
        current_user: UserContext,
    ) -> CampaignResponse:
        """Create campaign in both Dograh and local DB."""
        org_id = current_user.organization_id

        await self._verify_agent_ownership(data.workflow_id, org_id)

        dograh_payload: dict = {
            "name": data.name,
            "workflow_id": data.workflow_id,
            "source_type": "csv",
            "source_id": data.contact_list_id,
            "max_concurrency": data.concurrency,
        }
        if data.retry_config:
            dograh_payload["retry_config"] = data.retry_config.model_dump()
        if data.schedule_config:
            dograh_payload["schedule_config"] = data.schedule_config.model_dump()

        try:
            result = await self.dograh.create_campaign(dograh_payload)
        except Exception as exc:
            logger.error("campaign.create_failed", org_id=org_id, error=str(exc), payload=dograh_payload)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to create campaign in voice provider: {exc}",
            ) from exc

        dograh_campaign_id = result.get("id", result.get("campaign_id", 0))
        total_contacts = result.get("total_contacts", 0)

        local_record = {
            "organization_id": str(org_id),
            "dograh_campaign_id": dograh_campaign_id,
            "dograh_workflow_id": data.workflow_id,
            "name": data.name,
            "status": "draft",
            "total_contacts": total_contacts,
            "contacts_processed": 0,
            "concurrency": data.concurrency,
            "retry_config": data.retry_config.model_dump() if data.retry_config else None,
            "schedule_config": data.schedule_config.model_dump() if data.schedule_config else None,
            "contact_list_id": data.contact_list_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            rows = await self.db.database.from_("campaigns") \
                .insert([local_record])
            rows = rows if isinstance(rows, list) else []
            local = rows[0] if rows else local_record
        except Exception as exc:
            logger.error("campaign.local_create_failed", org_id=org_id, error=str(exc))
            local = local_record

        return self._to_response(local, org_id, dograh_campaign_id)

    # ------------------------------------------------------------------
    # List campaigns
    # ------------------------------------------------------------------

    async def list_campaigns(
        self,
        current_user: UserContext,
    ) -> CampaignListResponse:
        """List campaigns for the current org from local DB, enriched with live Dograh progress."""
        org_id = current_user.organization_id

        try:
            rows = await self.db.database.from_("campaigns") \
                .select("*") \
                .eq("organization_id", str(org_id)) \
                .order("created_at", desc=True) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("campaign.list_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to retrieve campaigns",
            ) from exc

        # Enrich all campaigns with live Dograh progress concurrently
        import asyncio

        async def enrich(row: dict) -> dict:
            dograh_id = row.get("dograh_campaign_id")
            if not dograh_id:
                return row
            try:
                progress = await self.dograh.get_campaign_progress(dograh_id)
                row = dict(row)  # don't mutate original
                row["total_contacts"] = progress.get("total_rows", row.get("total_contacts", 0))
                row["contacts_processed"] = progress.get("processed_rows", row.get("contacts_processed", 0))
                row["status"] = progress.get("state", row.get("status", "draft"))
            except Exception:
                pass
            return row

        enriched = await asyncio.gather(*[enrich(row) for row in rows])

        campaigns = [self._to_response(row, org_id) for row in enriched]
        return CampaignListResponse(campaigns=campaigns, total=len(campaigns))

    # ------------------------------------------------------------------
    # Get single campaign
    # ------------------------------------------------------------------

    async def get_campaign(
        self,
        campaign_id: str,
        current_user: UserContext,
    ) -> CampaignResponse:
        """Get campaign details — local record enriched with Dograh progress."""
        org_id = current_user.organization_id

        local = await self._get_local_campaign(campaign_id, org_id)

        try:
            progress = await self.dograh.get_campaign_progress(local["dograh_campaign_id"])
            local["total_contacts"] = progress.get("total_rows", local.get("total_contacts", 0))
            local["contacts_processed"] = progress.get("processed_rows", local.get("contacts_processed", 0))
            local["status"] = progress.get("state", local.get("status", "draft"))
        except Exception:
            pass

        return self._to_response(local, org_id)

    # ------------------------------------------------------------------
    # Update campaign
    # ------------------------------------------------------------------

    async def update_campaign(
        self,
        campaign_id: str,
        data: CampaignUpdate,
        current_user: UserContext,
    ) -> CampaignResponse:
        """Update campaign in both Dograh and local DB."""
        org_id = current_user.organization_id

        local = await self._get_local_campaign(campaign_id, org_id)

        dograh_update: dict = {}
        local_update: dict = {}

        if data.name is not None:
            dograh_update["name"] = data.name
            local_update["name"] = data.name
        if data.concurrency is not None:
            dograh_update["concurrency"] = data.concurrency
            local_update["concurrency"] = data.concurrency
        if data.retry_config is not None:
            dograh_update["retry_config"] = data.retry_config.model_dump()
            local_update["retry_config"] = data.retry_config.model_dump()
        if data.schedule_config is not None:
            dograh_update["schedule_config"] = data.schedule_config.model_dump()
            local_update["schedule_config"] = data.schedule_config.model_dump()

        if not dograh_update:
            return self._to_response(local, org_id)

        try:
            await self.dograh.update_campaign(local["dograh_campaign_id"], dograh_update)
        except Exception as exc:
            logger.error("campaign.update_dograh_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to update campaign in voice provider",
            ) from exc

        try:
            rows = await self.db.database.from_("campaigns") \
                .eq("id", campaign_id) \
                .eq("organization_id", str(org_id)) \
                .update(local_update, return_representation=True)
            rows = rows if isinstance(rows, list) else []
            if rows:
                local = rows[0]
        except json.JSONDecodeError:
            # InsForge SDK bug: update succeeds but returns empty body
            pass
        except Exception as exc:
            logger.error("campaign.local_update_failed", org_id=org_id, error=str(exc))

        return self._to_response(local, org_id)

    # ------------------------------------------------------------------
    # Start / Pause / Resume
    # ------------------------------------------------------------------

    async def start_campaign(
        self,
        campaign_id: str,
        current_user: UserContext,
    ) -> CampaignActionResponse:
        """Start a draft or paused campaign."""
        org_id = current_user.organization_id
        local = await self._get_local_campaign(campaign_id, org_id)

        try:
            result = await self.dograh.start_campaign(local["dograh_campaign_id"])
        except Exception as exc:
            logger.error("campaign.start_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to start campaign: {exc}",
            ) from exc

        now = datetime.now(timezone.utc).isoformat()
        try:
            await self.db.database.from_("campaigns") \
                .eq("id", campaign_id) \
                .eq("organization_id", str(org_id)) \
                .update({"status": "running", "started_at": now})
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            logger.error("campaign.local_start_update_failed", org_id=org_id, error=str(exc))

        track_event(
            distinct_id=str(org_id),
            event="campaign_started",
            properties={
                "org_id": str(org_id),
                "campaign_id": str(campaign_id),
                "agent_id": str(local.get("dograh_workflow_id", "")),
                "contact_count": local.get("total_contacts", 0),
            },
        )

        new_status = result.get("status", "running")
        return CampaignActionResponse(
            campaign_id=local["dograh_campaign_id"],
            status=new_status,
            message="Campaign started",
        )

    async def pause_campaign(
        self,
        campaign_id: str,
        current_user: UserContext,
    ) -> CampaignActionResponse:
        """Pause a running campaign."""
        org_id = current_user.organization_id
        local = await self._get_local_campaign(campaign_id, org_id)

        try:
            result = await self.dograh.pause_campaign(local["dograh_campaign_id"])
        except Exception as exc:
            logger.error("campaign.pause_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to pause campaign: {exc}",
            ) from exc

        try:
            await self.db.database.from_("campaigns") \
                .eq("id", campaign_id) \
                .eq("organization_id", str(org_id)) \
                .update({"status": "paused"})
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            logger.error("campaign.local_pause_update_failed", org_id=org_id, error=str(exc))

        new_status = result.get("status", "paused")
        return CampaignActionResponse(
            campaign_id=local["dograh_campaign_id"],
            status=new_status,
            message="Campaign paused",
        )

    async def resume_campaign(
        self,
        campaign_id: str,
        current_user: UserContext,
    ) -> CampaignActionResponse:
        """Resume a paused campaign."""
        org_id = current_user.organization_id
        local = await self._get_local_campaign(campaign_id, org_id)

        try:
            result = await self.dograh.resume_campaign(local["dograh_campaign_id"])
        except Exception as exc:
            logger.error("campaign.resume_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to resume campaign: {exc}",
            ) from exc

        try:
            await self.db.database.from_("campaigns") \
                .eq("id", campaign_id) \
                .eq("organization_id", str(org_id)) \
                .update({"status": "running"})
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            logger.error("campaign.local_resume_update_failed", org_id=org_id, error=str(exc))

        new_status = result.get("status", "running")
        return CampaignActionResponse(
            campaign_id=local["dograh_campaign_id"],
            status=new_status,
            message="Campaign resumed",
        )

    # ------------------------------------------------------------------
    # Progress & Runs
    # ------------------------------------------------------------------

    async def get_progress(
        self,
        campaign_id: str,
        current_user: UserContext,
    ) -> CampaignProgressResponse:
        """Get current campaign progress stats from Dograh."""
        org_id = current_user.organization_id
        local = await self._get_local_campaign(campaign_id, org_id)

        try:
            progress = await self.dograh.get_campaign_progress(local["dograh_campaign_id"])
        except Exception as exc:
            logger.error("campaign.progress_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to get campaign progress",
            ) from exc

        total = progress.get("total_rows", local.get("total_contacts", 0))
        processed = progress.get("processed_rows", 0)
        failed = progress.get("failed_calls", 0)
        successful = max(0, processed - failed)

        return CampaignProgressResponse(
            campaign_id=local["dograh_campaign_id"],
            status=progress.get("state", local.get("status", "draft")),
            total_contacts=total,
            contacts_processed=processed,
            contacts_remaining=max(0, total - processed),
            success_count=successful,
            failed_count=failed,
            in_progress_count=max(0, total - processed),
        )

    async def get_campaign_runs(
        self,
        campaign_id: str,
        current_user: UserContext,
    ) -> dict:
        """Get run records for all contacts in a campaign from Dograh.

        Also performs lazy sync: backfills any missing runs into
        the local call_runs table so analytics, billing, and call
        detail pages work even if the webhook was missed.
        """
        org_id = current_user.organization_id
        local = await self._get_local_campaign(campaign_id, org_id)

        try:
            result = await self.dograh.get_campaign_runs(local["dograh_campaign_id"])
        except Exception as exc:
            logger.error("campaign.get_runs_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to get campaign runs",
            ) from exc

        # Normalize Dograh response — it may return a list or a dict with a runs key
        if isinstance(result, list):
            raw_runs = result
        else:
            raw_runs = result.get("runs", result.get("data", []))

        runs = []
        for r in raw_runs:
            # Dograh nests phone/caller data inside initial_context
            ic = r.get("initial_context") or {}
            # Dograh nests disposition data inside gathered_context
            gc = r.get("gathered_context") or {}
            # Dograh nests duration inside cost_info
            ci = r.get("cost_info") or {}

            # Derive status from is_completed flag (Dograh has no top-level status)
            if gc.get("error"):
                run_status = "failed"
            elif r.get("is_completed"):
                run_status = "completed"
            else:
                run_status = "in_progress"

            runs.append({
                "run_id": r.get("id", 0),
                "workflow_id": r.get("workflow_id", local.get("dograh_workflow_id")),
                "workflow_name": r.get("name"),
                "campaign_id": ic.get("campaign_id", local.get("dograh_campaign_id")),
                "campaign_name": local.get("name"),
                "call_type": r.get("call_type"),
                "status": run_status,
                "disposition_code": gc.get("mapped_call_disposition", gc.get("call_disposition")),
                "phone_number": ic.get("phone_number", ic.get("called_number")),
                "caller_number": ic.get("caller_number"),
                "duration_seconds": ci.get("call_duration_seconds"),
                "cost": None,
                "recording_url": r.get("recording_url"),
                "transcript_url": r.get("transcript_url"),
                "public_access_token": r.get("public_access_token"),
                "created_at": r.get("created_at"),
                "completed_at": None,
            })

        # Lazy sync: backfill missing runs into local call_runs table
        await self._backfill_campaign_runs(runs, org_id, local)

        return {"runs": runs}

    async def _backfill_campaign_runs(
        self,
        normalized_runs: list[dict],
        org_id: str,
        local_campaign: dict,
    ) -> None:
        """Backfill campaign runs into local call_runs table.

        Safety net: ensures data exists locally even if the webhook was
        missed. Uses dograh_run_id as dedup key (idempotent).
        """
        if not normalized_runs:
            return

        run_ids = [r["run_id"] for r in normalized_runs if r.get("run_id")]
        if not run_ids:
            return

        # Find which runs already exist locally
        try:
            existing = await self.db.database.from_("call_runs") \
                .select("dograh_run_id") \
                .eq("organization_id", org_id) \
                .in_("dograh_run_id", run_ids) \
                .execute()
            existing = existing if isinstance(existing, list) else []
            existing_ids = {r["dograh_run_id"] for r in existing}
        except Exception as exc:
            logger.warning("campaign.backfill_lookup_failed", error=str(exc))
            return

        # Insert only missing runs
        to_insert = []
        for run in normalized_runs:
            rid = run.get("run_id")
            if not rid or rid in existing_ids:
                continue
            to_insert.append({
                "organization_id": org_id,
                "dograh_run_id": rid,
                "dograh_workflow_id": run.get("workflow_id", local_campaign.get("dograh_workflow_id")),
                "call_type": run.get("call_type", "outbound"),
                "status": run.get("status", "completed"),
                "phone_number": run.get("phone_number", ""),
                "caller_number": run.get("caller_number", ""),
                "duration_seconds": run.get("duration_seconds") or 0,
                "disposition": run.get("disposition_code"),
                "campaign_id": str(local_campaign.get("id", "")),
            })

        if not to_insert:
            return

        try:
            await self.db.database.from_("call_runs").insert(to_insert)
            logger.info(
                "campaign.backfill_synced",
                org_id=org_id,
                count=len(to_insert),
                campaign_id=local_campaign.get("dograh_campaign_id"),
            )
        except Exception as exc:
            logger.warning("campaign.backfill_insert_failed", error=str(exc))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _verify_agent_ownership(self, workflow_id: int, org_id: str) -> None:
        """Ensure the given workflow is mapped to the user's org."""
        try:
            rows = await self.db.database.from_("dograh_agent_mappings") \
                .select("id") \
                .eq("organization_id", str(org_id)) \
                .eq("dograh_workflow_id", workflow_id) \
                .limit(1) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("campaign.agent_verify_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to verify agent ownership",
            ) from exc

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with workflow_id {workflow_id} not found in your organization",
            )

    async def _get_local_campaign(self, campaign_id: str, org_id: str) -> dict:
        """Fetch local campaign record with org guard."""
        try:
            rows = await self.db.database.from_("campaigns") \
                .select("*") \
                .eq("id", campaign_id) \
                .eq("organization_id", str(org_id)) \
                .limit(1) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("campaign.get_local_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to retrieve campaign",
            ) from exc

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )
        return rows[0]

    @staticmethod
    def _to_response(
        data: dict,
        org_id: str,
        dograh_campaign_id: int | None = None,
    ) -> CampaignResponse:
        """Map a local DB row to CampaignResponse."""
        return CampaignResponse(
            id=str(data.get("id", "")),
            organization_id=str(data.get("organization_id", org_id)),
            dograh_campaign_id=data.get("dograh_campaign_id", dograh_campaign_id or 0),
            dograh_workflow_id=data.get("dograh_workflow_id", 0),
            name=data.get("name", ""),
            status=data.get("status", "draft"),
            total_contacts=data.get("total_contacts", 0),
            contacts_processed=data.get("contacts_processed", 0),
            concurrency=data.get("concurrency", 1),
            retry_config=data.get("retry_config"),
            schedule_config=data.get("schedule_config"),
            contact_list_id=data.get("contact_list_id"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            created_at=data.get("created_at"),
        )
