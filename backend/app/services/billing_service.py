from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.logging import logger
from app.core.posthog import track_event
from app.integrations.dograh_client import DograhClient
from app.integrations.insforge_client import get_insforge_admin
from app.integrations.razorpay_client import RazorpayService
from app.schemas.auth import UserContext
from app.schemas.billing import (
    CreateOrderRequest,
    InvoiceItem,
    InvoiceListResponse,
    OrderResponse,
    PaymentVerificationResponse,
    UsageSummary,
    VerifyPaymentRequest,
)




class BillingService:
    """Business logic for billing, usage tracking, and Razorpay payments.

    All operations scoped to current user's organization.
    Follows the Thin Controller, Fat Service pattern.
    """

    def __init__(self) -> None:
        self.db = get_insforge_admin()
        self.razorpay = RazorpayService()

    async def get_usage_summary(self, current_user: UserContext) -> UsageSummary:
        """Return current billing period usage with per-org custom rate.

        Rate is stored in organizations.rate_per_minute (set by Neuvon admin).
        Cost = total_minutes × rate_per_minute.
        """
        org_id = current_user.organization_id
        today = date.today()
        period_start = today.replace(day=1)
        if today.month == 12:
            period_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            period_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        # Fallback sync: pull any missed runs from Dograh before aggregating.
        # This is a safety net in case the webhook was delayed or missed.
        await self._sync_missing_runs(org_id)

        # Get per-org rate, fees, and quota
        rate, platform_fee, plan_label, minutes_limit = await self._get_org_billing_info(org_id)

        # Aggregate from call_runs for current period
        total_calls, total_seconds = await self._aggregate_usage(
            org_id, period_start.isoformat(), period_end.isoformat()
        )
        total_minutes = round(total_seconds / 60, 2)
        usage_cost = round(total_minutes * rate, 2)
        total_cost = round(usage_cost + platform_fee, 2)

        minutes_remaining: float | None = None
        if minutes_limit and minutes_limit > 0:
            minutes_remaining = max(0.0, minutes_limit - total_minutes)

        return UsageSummary(
            organization_id=org_id,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            rate_per_minute=rate,
            platform_fee=platform_fee,
            plan_label=plan_label,
            total_calls=total_calls,
            total_minutes=total_minutes,
            total_cost=total_cost,
            minutes_limit=minutes_limit,
            minutes_remaining=minutes_remaining,
        )

    async def create_order(
        self, data: CreateOrderRequest, current_user: UserContext
    ) -> OrderResponse:
        """Create a Razorpay order for plan purchase or credit top-up."""
        org_id = current_user.organization_id
        receipt = f"neuvon_{org_id[:8]}_{uuid.uuid4().hex[:8]}"

        notes = {
            "organization_id": org_id,
            "user_id": current_user.user_id,
            **data.notes,
        }

        try:
            order = self.razorpay.create_order(
                amount=data.amount_inr,
                currency="INR",
                receipt=receipt,
                notes=notes,
            )
        except Exception as exc:
            logger.error("billing.create_order_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create payment order",
            )

        # Store the order reference in billing_records
        now_iso = datetime.now(timezone.utc).isoformat()
        today = date.today()
        try:
            await self.db.database.from_("billing_records").insert([{
                "organization_id": org_id,
                "period_start": today.replace(day=1).isoformat(),
                "period_end": today.isoformat(),
                "total_cost_usd": 0,
                "razorpay_invoice_id": order["id"],
                "status": "pending",
            }])
        except Exception as exc:
            logger.warning("billing.record_insert_failed", error=str(exc))

        settings = get_settings()
        track_event(
            distinct_id=org_id,
            event="billing_order_created",
            properties={
                "org_id": org_id,
                "order_id": order["id"],
                "amount": order["amount"],
            },
        )

        return OrderResponse(
            order_id=order["id"],
            amount=order["amount"],
            currency=order.get("currency", "INR"),
            receipt=order.get("receipt", receipt),
            status=order.get("status", "created"),
            razorpay_key_id=settings.RAZORPAY_KEY_ID,
        )

    async def verify_payment(
        self, data: VerifyPaymentRequest, current_user: UserContext
    ) -> PaymentVerificationResponse:
        """Verify Razorpay payment signature after checkout callback."""
        org_id = current_user.organization_id

        verified = self.razorpay.verify_payment_signature(
            razorpay_order_id=data.razorpay_order_id,
            razorpay_payment_id=data.razorpay_payment_id,
            razorpay_signature=data.razorpay_signature,
        )

        if not verified:
            logger.warning(
                "billing.payment_verification_failed",
                org_id=org_id,
                order_id=data.razorpay_order_id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment signature verification failed",
            )

        # Mark billing record as paid
        try:
            await self.db.database.from_("billing_records") \
                .eq("razorpay_invoice_id", data.razorpay_order_id) \
                .eq("organization_id", org_id) \
                .update({"status": "paid"}, return_representation=True)
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            logger.warning("billing.record_update_failed", error=str(exc))

        track_event(
            distinct_id=org_id,
            event="billing_payment_verified",
            properties={
                "org_id": org_id,
                "order_id": data.razorpay_order_id,
                "payment_id": data.razorpay_payment_id,
            },
        )

        return PaymentVerificationResponse(
            verified=True,
            payment_id=data.razorpay_payment_id,
            order_id=data.razorpay_order_id,
            message="Payment verified successfully",
        )

    async def get_invoices(
        self,
        current_user: UserContext,
        page: int = 1,
        per_page: int = 20,
    ) -> InvoiceListResponse:
        """Return paginated billing records / invoices."""
        org_id = current_user.organization_id

        try:
            all_rows = await self.db.database.from_("billing_records") \
                .select("*") \
                .eq("organization_id", org_id) \
                .order("created_at", desc=True) \
                .execute()
            all_rows = all_rows if isinstance(all_rows, list) else []
        except Exception as exc:
            logger.error("billing.invoices_failed", org_id=org_id, error=str(exc))
            all_rows = []

        total = len(all_rows)
        offset = (page - 1) * per_page
        rows = all_rows[offset: offset + per_page]

        invoices = [
            InvoiceItem(
                id=str(r.get("id", "")),
                organization_id=str(r.get("organization_id", "")),
                period_start=str(r.get("period_start", "")),
                period_end=str(r.get("period_end", "")),
                total_minutes=float(r.get("total_minutes", 0)),
                total_calls=int(r.get("total_calls", 0)),
                total_cost=float(r.get("total_cost_usd", 0)),
                razorpay_invoice_id=r.get("razorpay_invoice_id"),
                status=r.get("status", "pending"),
                created_at=str(r.get("created_at", "")),
            )
            for r in rows
        ]

        return InvoiceListResponse(invoices=invoices, total=total)

    async def process_razorpay_webhook(self, body: bytes, signature: str) -> dict:
        """Process a Razorpay webhook event (payment.captured, etc.).

        Not scoped to a user — uses the org info from the order notes.
        """
        valid = self.razorpay.verify_webhook_signature(body, signature)
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Razorpay webhook signature",
            )

        import json
        payload = json.loads(body)
        event_type = payload.get("event", "")

        logger.info("razorpay.webhook_received", event=event_type)

        if event_type == "payment.captured":
            payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payment.get("order_id")
            payment_id = payment.get("id")
            if order_id:
                # Update billing record status
                try:
                    await self.db.database.from_("billing_records") \
                        .eq("razorpay_invoice_id", order_id) \
                        .update({"status": "paid"}, return_representation=True)
                    logger.info("razorpay.payment_captured", order_id=order_id)
                except json.JSONDecodeError:
                    logger.info("razorpay.payment_captured", order_id=order_id)
                except Exception as exc:
                    logger.error("razorpay.webhook_update_failed", error=str(exc))

                # Credit minutes if this is a top-up order
                if payment_id:
                    try:
                        from app.services.topup_service import TopUpService
                        topup_service = TopUpService()
                        await topup_service.credit_minutes_on_payment(
                            razorpay_order_id=order_id,
                            razorpay_payment_id=payment_id,
                        )
                    except Exception as exc:
                        logger.error("razorpay.topup_credit_failed", error=str(exc))

        return {"status": "ok", "event": event_type}

    # --- Internal helpers ---

    async def _get_org_billing_info(self, org_id: str) -> tuple[float, float, str | None, float | None]:
        """Get per-org rate_per_minute, platform_fee, plan_label and monthly minutes limit.

        Returns (rate_per_minute, platform_fee, plan_label, minutes_limit).
        """
        try:
            rows = await self.db.database.from_("organizations") \
                .select("rate_per_minute, platform_fee, plan_label, usage_quota") \
                .eq("id", org_id) \
                .limit(1) \
                .execute()
            rows = rows if isinstance(rows, list) else []
            if rows:
                rate = float(rows[0].get("rate_per_minute", 3.50) or 3.50)
                platform_fee = float(rows[0].get("platform_fee", 0.0) or 0.0)
                plan_label = rows[0].get("plan_label")
                quota = rows[0].get("usage_quota")
                if isinstance(quota, str):
                    quota = json.loads(quota)
                if isinstance(quota, dict):
                    limit = quota.get("monthly_minutes")
                    return rate, platform_fee, plan_label, float(limit) if limit else None
                return rate, platform_fee, plan_label, None
        except Exception as exc:
            logger.warning("billing.org_info_failed", org_id=org_id, error=str(exc))
        return 3.50, 0.0, None, None

    async def _aggregate_usage(
        self, org_id: str, start_date: str, end_date: str
    ) -> tuple[int, int]:
        """Count calls and total seconds for a billing period."""
        try:
            rows = await self.db.database.from_("call_runs") \
                .select("duration_seconds") \
                .eq("organization_id", org_id) \
                .gte("created_at", start_date) \
                .lte("created_at", end_date + "T23:59:59Z") \
                .execute()
            rows = rows if isinstance(rows, list) else []
            total_calls = len(rows)
            total_seconds = sum(r.get("duration_seconds", 0) or 0 for r in rows)
            return total_calls, total_seconds
        except Exception as exc:
            logger.warning("billing.aggregate_failed", org_id=org_id, error=str(exc))
            return 0, 0

    async def _aggregate_cost(
        self, org_id: str, start_date: str, end_date: str
    ) -> float:
        """Sum total cost from cost_info JSON for a billing period."""
        try:
            rows = await self.db.database.from_("call_runs") \
                .select("cost_info") \
                .eq("organization_id", org_id) \
                .gte("created_at", start_date) \
                .lte("created_at", end_date + "T23:59:59Z") \
                .execute()
            rows = rows if isinstance(rows, list) else []
            total = 0.0
            for r in rows:
                cost_info = r.get("cost_info")
                if isinstance(cost_info, dict):
                    total += cost_info.get("total_cost", 0) or 0
            return round(total, 2)
        except Exception as exc:
            logger.warning("billing.cost_aggregate_failed", org_id=org_id, error=str(exc))
            return 0.0

    async def _sync_missing_runs(self, org_id: str) -> None:
        """Fallback sync: fetch recent completed runs from Dograh and write
        any missing ones to call_runs.

        Called at the start of get_usage_summary() as a safety net in case
        the Dograh webhook was missed (e.g. server was down, network error).
        Idempotent — skips runs already in call_runs by dograh_run_id.
        Also deducts minutes for newly synced completed runs.
        """
        dograh = DograhClient()

        # 1. Fetch recent runs from Dograh (up to 100)
        try:
            result = await dograh._request(
                "GET",
                "/organizations/usage/runs",
                params={"page": 1, "page_size": 100},
            )
            if isinstance(result, dict):
                all_runs = result.get("runs", [])
            else:
                all_runs = result if isinstance(result, list) else []
        except Exception as exc:
            logger.warning("billing.sync_fetch_failed", org_id=org_id, error=str(exc))
            return

        if not all_runs:
            return

        # 2. Get workflow_ids that belong to this org from dograh_agent_mappings
        try:
            mapping_rows = await self.db.database.from_("dograh_agent_mappings") \
                .select("dograh_workflow_id") \
                .eq("organization_id", org_id) \
                .execute()
            mapping_rows = mapping_rows if isinstance(mapping_rows, list) else []
            org_workflow_ids = {
                int(r["dograh_workflow_id"]) for r in mapping_rows
                if r.get("dograh_workflow_id")
            }
        except Exception as exc:
            logger.warning("billing.sync_mapping_failed", org_id=org_id, error=str(exc))
            return

        if not org_workflow_ids:
            return

        # 3. Filter to this org's runs (all completed runs from usage/runs endpoint)
        org_runs = [
            r for r in all_runs
            if r.get("workflow_id") in org_workflow_ids
        ]

        if not org_runs:
            return

        # 4. Get all dograh_run_ids already in call_runs for this org
        try:
            existing_rows = await self.db.database.from_("call_runs") \
                .select("dograh_run_id") \
                .eq("organization_id", org_id) \
                .execute()
            existing_rows = existing_rows if isinstance(existing_rows, list) else []
            existing_run_ids = {r["dograh_run_id"] for r in existing_rows if r.get("dograh_run_id")}
        except Exception as exc:
            logger.warning("billing.sync_existing_failed", org_id=org_id, error=str(exc))
            return

        # 5. Insert missing runs
        now_iso = datetime.now(timezone.utc).isoformat()
        newly_synced_minutes = 0.0

        for run in org_runs:
            run_id = run.get("id")
            if not run_id or run_id in existing_run_ids:
                continue

            # call_duration_seconds is the field name in /organizations/usage/runs
            duration_seconds = int(run.get("call_duration_seconds") or 0)
            cost_info = run.get("cost_info") or {}

            record = {
                "organization_id": org_id,
                "dograh_run_id": run_id,
                "dograh_workflow_id": run.get("workflow_id"),
                "call_type": run.get("call_type") or "outbound",
                "status": run.get("status") or "completed",
                "phone_number": run.get("phone_number") or "",
                "duration_seconds": duration_seconds,
                "completed_at": now_iso,
            }
            if cost_info:
                record["cost_info"] = json.dumps(cost_info)

            try:
                await self.db.database.from_("call_runs").insert([record])
                logger.info(
                    "billing.sync_run_inserted",
                    org_id=org_id,
                    run_id=run_id,
                    duration_seconds=duration_seconds,
                )
                if duration_seconds > 0:
                    newly_synced_minutes += round(duration_seconds / 60, 2)
            except Exception as exc:
                err = str(exc)
                if "duplicate" in err.lower() or "unique" in err.lower():
                    pass  # Already exists — race condition, safe to skip
                else:
                    logger.warning(
                        "billing.sync_insert_failed",
                        run_id=run_id,
                        error=err,
                    )

        # 6. Deduct newly synced minutes from org's pre-paid balance
        if newly_synced_minutes > 0:
            try:
                from app.services.topup_service import TopUpService
                topup = TopUpService()
                await topup.deduct_minutes(org_id, newly_synced_minutes)
                logger.info(
                    "billing.sync_minutes_deducted",
                    org_id=org_id,
                    minutes=newly_synced_minutes,
                )
            except Exception as exc:
                logger.warning(
                    "billing.sync_deduct_failed",
                    org_id=org_id,
                    error=str(exc),
                )
