from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

from fastapi import HTTPException, Request, status

from app.core.config import get_settings
from app.core.logging import logger
from app.core.posthog import track_event
from app.integrations.insforge_client import get_insforge_admin
from app.schemas.live_call import LiveCallUpdate
from app.schemas.webhook import DograhWebhookPayload, WebhookAckResponse
from app.services.live_call_manager import get_live_call_manager


class WebhookService:
    """Handles Dograh webhook processing.

    Receives post-call data, updates local call_runs records,
    fires PostHog events, and is idempotent (same payload twice
    produces the same result via dograh_run_id dedup).
    """

    def __init__(self) -> None:
        self.db = get_insforge_admin()

    async def verify_webhook_signature(self, request: Request) -> bytes:
        """Verify the Dograh webhook signature if WEBHOOK_SECRET is configured.

        Skips verification if the secret is a placeholder value.
        """
        body = await request.body()
        settings = get_settings()

        secret = settings.WEBHOOK_SECRET
        placeholder_values = {"", "your-webhook-signing-secret"}

        if secret and secret not in placeholder_values:
            signature = request.headers.get("x-webhook-signature", "")
            expected = hmac.new(
                secret.encode(),
                body,
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(signature, expected):
                logger.warning("webhook.invalid_signature")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature",
                )

        return body

    async def process_dograh_webhook(
        self, payload: DograhWebhookPayload
    ) -> WebhookAckResponse:
        """Process a Dograh post-call webhook payload.

        Idempotent: uses dograh_run_id as dedup key.
        """
        import sentry_sdk

        run_id = payload.run_id
        if not run_id:
            logger.warning("webhook.missing_run_id", payload_keys=list(payload.model_dump().keys()))
            return WebhookAckResponse(
                status="skipped",
                message="No run_id in payload",
            )

        # Tag Sentry context so any errors during processing include call info
        sentry_sdk.set_tag("dograh.run_id", run_id)
        sentry_sdk.set_tag("dograh.workflow_id", payload.workflow_id)
        sentry_sdk.set_tag("dograh.status", payload.status)

        existing = await self._find_local_run(run_id)

        if existing:
            await self._update_existing_run(existing, payload)
            org_id = existing.get("organization_id", "unknown")
        else:
            org_id = await self._create_new_run(payload)

        if payload.status in ("completed", "failed"):
            track_event(
                distinct_id=org_id,
                event="call_completed",
                properties={
                    "org_id": org_id,
                    "run_id": run_id,
                    "duration_seconds": payload.duration_seconds or 0,
                    "disposition": payload.disposition or payload.status,
                },
            )

            # Deduct minutes from org's pre-paid balance
            duration_seconds = payload.duration_seconds or 0
            if duration_seconds > 0 and org_id:
                duration_minutes = round(duration_seconds / 60, 2)
                try:
                    from app.services.topup_service import TopUpService
                    topup_service = TopUpService()
                    await topup_service.deduct_minutes(org_id, duration_minutes)
                except Exception as exc:
                    logger.warning(
                        "webhook.minute_deduction_failed",
                        org_id=org_id,
                        minutes=duration_minutes,
                        error=str(exc),
                    )

        # Auto-extract appointment from gathered_context if present
        if payload.status == "completed" and payload.gathered_context and org_id:
            logger.info(
                "webhook.gathered_context_debug",
                run_id=run_id,
                org_id=org_id,
                context_keys=list(payload.gathered_context.keys()),
                appointment_requested=payload.gathered_context.get("appointment_requested"),
                appointment_date=payload.gathered_context.get("appointment_date"),
                appointment_name=payload.gathered_context.get("appointment_name"),
                has_appointment_key=("appointment" in payload.gathered_context),
                has_booking_key=("booking" in payload.gathered_context),
            )
            try:
                from app.services.appointment_service import AppointmentService
                await AppointmentService.extract_from_gathered_context(
                    org_id=org_id,
                    call_run_id=str(run_id),
                    gathered_context=payload.gathered_context,
                )
            except Exception as exc:
                logger.warning("webhook.appointment_extract_failed", error=str(exc))

        logger.info(
            "webhook.processed",
            run_id=run_id,
            org_id=org_id,
            status=payload.status,
        )

        return WebhookAckResponse(
            status="ok",
            run_id=run_id,
            message="Webhook processed",
        )

    # --- Internal helpers ---

    async def _find_local_run(self, run_id: int) -> dict | None:
        """Look up local call_runs record by dograh_run_id."""
        try:
            rows = await self.db.database.from_("call_runs") \
                .select("*") \
                .eq("dograh_run_id", run_id) \
                .execute()
            rows = rows if isinstance(rows, list) else []
            return rows[0] if rows else None
        except Exception as exc:
            logger.warning("webhook.run_lookup_failed", run_id=run_id, error=str(exc))
            return None

    async def _update_existing_run(
        self, existing: dict, payload: DograhWebhookPayload
    ) -> None:
        """Update an existing call_runs record with webhook data."""
        now_iso = datetime.now(timezone.utc).isoformat()

        updates: dict = {}

        if payload.status:
            updates["status"] = payload.status
        if payload.duration_seconds is not None:
            updates["duration_seconds"] = payload.duration_seconds
        if payload.transcript_url:
            updates["transcript_url"] = payload.transcript_url
        if payload.recording_url:
            updates["recording_url"] = payload.recording_url
        if payload.public_access_token:
            updates["public_access_token"] = payload.public_access_token
        if payload.gathered_context:
            updates["gathered_context"] = json.dumps(payload.gathered_context)
        if payload.cost_info:
            updates["cost_info"] = json.dumps(payload.cost_info)
        if payload.annotations:
            updates["annotations"] = json.dumps(payload.annotations)
        if payload.disposition:
            updates["disposition"] = payload.disposition
        if payload.caller_number:
            updates["caller_number"] = payload.caller_number

        if payload.status in ("completed", "failed"):
            updates["completed_at"] = now_iso

        # Resolve campaign_id if missing on the existing run
        if not existing.get("campaign_id"):
            local_campaign_id = await self._resolve_campaign_id(payload)
            if local_campaign_id:
                updates["campaign_id"] = local_campaign_id

        try:
            await self.db.database.from_("call_runs") \
                .eq("id", existing["id"]) \
                .update(updates, return_representation=True)
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            logger.error(
                "webhook.update_failed",
                run_id=existing.get("dograh_run_id"),
                error=str(exc),
            )

    async def _create_new_run(self, payload: DograhWebhookPayload) -> str:
        """Create a new call_runs record from webhook (for runs triggered externally)."""
        org_id = await self._resolve_org_from_workflow(payload.workflow_id)

        if not org_id:
            logger.warning(
                "webhook.unresolvable_org",
                run_id=payload.run_id,
                workflow_id=payload.workflow_id,
            )
            return ""

        now_iso = datetime.now(timezone.utc).isoformat()

        record = {
            "organization_id": org_id,
            "dograh_run_id": payload.run_id,
            "dograh_workflow_id": payload.workflow_id,
            "call_type": payload.call_type or "outbound",
            "status": payload.status or "completed",
            "phone_number": payload.phone_number or "",
            "caller_number": payload.caller_number or "",
            "duration_seconds": payload.duration_seconds or 0,
        }

        # Resolve campaign_id from initial_context or payload
        local_campaign_id = await self._resolve_campaign_id(payload)
        if local_campaign_id:
            record["campaign_id"] = local_campaign_id

        # Only include nullable fields when present
        if payload.transcript_url:
            record["transcript_url"] = payload.transcript_url
        if payload.recording_url:
            record["recording_url"] = payload.recording_url
        if payload.public_access_token:
            record["public_access_token"] = payload.public_access_token
        if payload.disposition:
            record["disposition"] = payload.disposition
        if payload.initial_context:
            record["initial_context"] = json.dumps(payload.initial_context)
        if payload.gathered_context:
            record["gathered_context"] = json.dumps(payload.gathered_context)
        if payload.cost_info:
            record["cost_info"] = json.dumps(payload.cost_info)
        if payload.annotations:
            record["annotations"] = json.dumps(payload.annotations)
        if payload.status in ("completed", "failed"):
            record["completed_at"] = now_iso

        try:
            await self.db.database.from_("call_runs").insert([record])
        except Exception as exc:
            logger.error("webhook.insert_failed", run_id=payload.run_id, error=str(exc))

        # Publish live call update to WebSocket clients
        try:
            manager = get_live_call_manager()
            await manager.publish_update(
                org_id,
                LiveCallUpdate(
                    run_id=payload.run_id,
                    workflow_id=payload.workflow_id,
                    status=payload.status or "unknown",
                    phone_number=payload.phone_number,
                    caller_number=payload.caller_number,
                    duration_seconds=payload.duration_seconds or 0,
                    disposition_code=payload.disposition,
                    timestamp=now_iso,
                ),
            )
        except Exception as exc:
            logger.warning("webhook.live_update_failed", error=str(exc))

        return org_id

    async def _resolve_org_from_workflow(self, workflow_id: int | None) -> str | None:
        """Resolve organization_id from workflow_id via agent mappings."""
        if not workflow_id:
            return None

        try:
            rows = await self.db.database.from_("dograh_agent_mappings") \
                .select("organization_id") \
                .eq("dograh_workflow_id", workflow_id) \
                .limit(1) \
                .execute()
            rows = rows if isinstance(rows, list) else []
            return rows[0]["organization_id"] if rows else None
        except Exception:
            return None

    async def _resolve_campaign_id(self, payload: DograhWebhookPayload) -> str | None:
        """Resolve local campaign UUID from Dograh's integer campaign_id.

        The campaign_id comes from either:
        - payload.campaign_id (top-level webhook field)
        - payload.initial_context.campaign_id (set by Dograh for campaign calls)
        """
        dograh_campaign_id = payload.campaign_id

        # Fallback: check initial_context
        if not dograh_campaign_id and payload.initial_context:
            ic = payload.initial_context
            raw = ic.get("campaign_id")
            if raw is not None:
                try:
                    dograh_campaign_id = int(raw)
                except (ValueError, TypeError):
                    pass

        if not dograh_campaign_id:
            return None

        try:
            rows = await self.db.database.from_("campaigns") \
                .select("id") \
                .eq("dograh_campaign_id", dograh_campaign_id) \
                .limit(1) \
                .execute()
            rows = rows if isinstance(rows, list) else []
            if rows:
                return rows[0]["id"]
            logger.debug(
                "webhook.campaign_not_found",
                dograh_campaign_id=dograh_campaign_id,
            )
        except Exception as exc:
            logger.warning(
                "webhook.campaign_resolve_failed",
                dograh_campaign_id=dograh_campaign_id,
                error=str(exc),
            )
        return None
