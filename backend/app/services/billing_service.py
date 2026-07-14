from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.logging import logger
from app.core.posthog import track_event
from app.integrations.insforge_client import get_insforge_admin
from app.integrations.razorpay_client import RazorpayService
from app.schemas.auth import UserContext
from app.schemas.billing import (
    CreateOrderRequest,
    InvoiceItem,
    InvoiceListResponse,
    OrderResponse,
    PaymentVerificationResponse,
    PlanDetails,
    UsageSummary,
    VerifyPaymentRequest,
)


# --- Plan definitions ---

PLANS: dict[str, dict] = {
    "free": {
        "plan_name": "Free Tier",
        "price_monthly_inr": 0,
        "calls_limit": 100,
        "minutes_limit": 500.0,
        "features": ["100 calls/mo", "500 minutes/mo", "Basic analytics"],
    },
    "starter": {
        "plan_name": "Starter",
        "price_monthly_inr": 99900,  # ₹999 in paisa
        "calls_limit": 1000,
        "minutes_limit": 5000.0,
        "features": ["1,000 calls/mo", "5,000 minutes/mo", "Advanced analytics", "Priority support"],
    },
    "pro": {
        "plan_name": "Pro",
        "price_monthly_inr": 499900,  # ₹4,999 in paisa
        "calls_limit": 10000,
        "minutes_limit": 50000.0,
        "features": ["10,000 calls/mo", "50,000 minutes/mo", "Full analytics", "Dedicated support", "Custom agents"],
    },
}


class BillingService:
    """Business logic for billing, usage tracking, and Razorpay payments.

    All operations scoped to current user's organization.
    Follows the Thin Controller, Fat Service pattern.
    """

    def __init__(self) -> None:
        self.db = get_insforge_admin()
        self.razorpay = RazorpayService()

    async def get_usage_summary(self, current_user: UserContext) -> UsageSummary:
        """Return current billing period usage vs plan limits."""
        org_id = current_user.organization_id
        today = date.today()
        period_start = today.replace(day=1)
        if today.month == 12:
            period_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            period_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        plan_id = await self._get_org_plan(org_id)
        plan = PLANS.get(plan_id, PLANS["free"])

        # Aggregate from call_runs for current period
        total_calls, total_seconds = await self._aggregate_usage(
            org_id, period_start.isoformat(), period_end.isoformat()
        )
        total_minutes = round(total_seconds / 60, 2)

        # Cost is based on call_runs cost_info
        total_cost = await self._aggregate_cost(
            org_id, period_start.isoformat(), period_end.isoformat()
        )

        calls_remaining = max(0, plan["calls_limit"] - total_calls)
        minutes_remaining = max(0.0, plan["minutes_limit"] - total_minutes)

        return UsageSummary(
            organization_id=org_id,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            total_calls=total_calls,
            total_minutes=total_minutes,
            total_cost_usd=total_cost,
            plan_name=plan["plan_name"],
            calls_limit=plan["calls_limit"],
            minutes_limit=plan["minutes_limit"],
            calls_remaining=calls_remaining,
            minutes_remaining=minutes_remaining,
        )

    async def get_plan_details(self, current_user: UserContext) -> PlanDetails:
        """Return the organization's current plan details."""
        org_id = current_user.organization_id
        plan_id = await self._get_org_plan(org_id)
        plan = PLANS.get(plan_id, PLANS["free"])

        return PlanDetails(
            plan_id=plan_id,
            plan_name=plan["plan_name"],
            price_monthly_inr=plan["price_monthly_inr"],
            calls_limit=plan["calls_limit"],
            minutes_limit=plan["minutes_limit"],
            features=plan["features"],
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
                total_cost_usd=float(r.get("total_cost_usd", 0)),
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
            if order_id:
                try:
                    await self.db.database.from_("billing_records") \
                        .eq("razorpay_invoice_id", order_id) \
                        .update({"status": "paid"}, return_representation=True)
                    logger.info("razorpay.payment_captured", order_id=order_id)
                except json.JSONDecodeError:
                    logger.info("razorpay.payment_captured", order_id=order_id)
                except Exception as exc:
                    logger.error("razorpay.webhook_update_failed", error=str(exc))

        return {"status": "ok", "event": event_type}

    # --- Internal helpers ---

    async def _get_org_plan(self, org_id: str) -> str:
        """Get the plan_id for an organization (defaults to 'free')."""
        try:
            rows = await self.db.database.from_("organizations") \
                .select("plan") \
                .eq("id", org_id) \
                .limit(1) \
                .execute()
            rows = rows if isinstance(rows, list) else []
            if rows and rows[0].get("plan"):
                return rows[0]["plan"]
        except Exception:
            pass
        return "free"

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
