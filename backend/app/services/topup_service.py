from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.logging import logger
from app.core.posthog import track_event
from app.integrations.insforge_client import get_insforge_admin
from app.integrations.razorpay_client import RazorpayService
from app.schemas.auth import UserContext
from app.schemas.topup import (
    AvailablePacksResponse,
    MinuteBalanceResponse,
    MinutePackDetail,
    MinutePackListResponse,
    MinutePackOption,
    TopUpOrderRequest,
    TopUpOrderResponse,
)

# Fixed pack sizes (minutes)
PACK_SIZES = [100, 500, 1000]


class TopUpService:
    """Business logic for minute pack purchases and balance management.

    All operations scoped to current user's organization.
    """

    def __init__(self) -> None:
        self.db = get_insforge_admin()
        self.razorpay = RazorpayService()

    async def get_available_packs(
        self, current_user: UserContext
    ) -> AvailablePacksResponse:
        """Return available minute packs with prices based on org's rate."""
        org_id = current_user.organization_id
        rate, balance = await self._get_org_rate_and_balance(org_id)

        packs = [
            MinutePackOption(
                minutes=size,
                price=round(size * rate, 2),
                label=f"{size:,} minutes",
            )
            for size in PACK_SIZES
        ]

        return AvailablePacksResponse(
            rate_per_minute=rate,
            packs=packs,
            minute_balance=balance,
        )

    async def create_topup_order(
        self, data: TopUpOrderRequest, current_user: UserContext
    ) -> TopUpOrderResponse:
        """Create a Razorpay order for a minute top-up purchase."""
        org_id = current_user.organization_id

        # Validate pack size
        if data.minutes not in PACK_SIZES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid pack size. Choose from: {PACK_SIZES}",
            )

        rate, _ = await self._get_org_rate_and_balance(org_id)
        amount_inr = round(data.minutes * rate, 2)
        amount_paise = int(amount_inr * 100)

        receipt = f"topup_{org_id[:8]}_{uuid.uuid4().hex[:8]}"
        description = f"{data.minutes} minutes @ ₹{rate}/min"

        notes = {
            "organization_id": org_id,
            "user_id": current_user.user_id,
            "type": "topup",
            "minutes": str(data.minutes),
            "rate_per_minute": str(rate),
        }

        # Create Razorpay order
        try:
            order = self.razorpay.create_order(
                amount=amount_paise,
                currency="INR",
                receipt=receipt,
                notes=notes,
            )
        except Exception as exc:
            logger.error("topup.create_order_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create payment order",
            )

        # Create pending minute_pack record
        try:
            await self.db.database.from_("minute_packs").insert([{
                "organization_id": org_id,
                "minutes_purchased": data.minutes,
                "minutes_remaining": data.minutes,
                "rate_at_purchase": rate,
                "amount_paid": amount_inr,
                "razorpay_order_id": order["id"],
                "status": "pending",
            }])
        except Exception as exc:
            logger.warning("topup.pack_insert_failed", error=str(exc))

        # Create pending billing record
        today = date.today()
        try:
            await self.db.database.from_("billing_records").insert([{
                "organization_id": org_id,
                "period_start": today.replace(day=1).isoformat(),
                "period_end": today.isoformat(),
                "total_cost_usd": amount_inr,
                "razorpay_invoice_id": order["id"],
                "razorpay_payment_id": None,
                "record_type": "topup",
                "minutes_purchased": data.minutes,
                "description": description,
                "status": "pending",
            }])
        except Exception as exc:
            logger.warning("topup.billing_record_failed", error=str(exc))

        track_event(
            distinct_id=org_id,
            event="topup_order_created",
            properties={
                "org_id": org_id,
                "minutes": data.minutes,
                "amount": amount_paise,
                "order_id": order["id"],
            },
        )

        settings = get_settings()
        return TopUpOrderResponse(
            order_id=order["id"],
            amount=amount_paise,
            currency="INR",
            razorpay_key_id=settings.RAZORPAY_KEY_ID,
            minutes=data.minutes,
            rate_per_minute=rate,
            description=description,
        )

    async def credit_minutes_on_payment(
        self, razorpay_order_id: str, razorpay_payment_id: str
    ) -> None:
        """Credit minutes to org after successful payment.

        Called by webhook handler when payment.captured is received.
        Idempotent — skips if pack already paid.
        """
        # Find the pending minute_pack
        try:
            rows = await self.db.database.from_("minute_packs") \
                .select("*") \
                .eq("razorpay_order_id", razorpay_order_id) \
                .eq("status", "pending") \
                .limit(1) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("topup.find_pack_failed", order_id=razorpay_order_id, error=str(exc))
            return

        if not rows:
            logger.info("topup.pack_not_found_or_already_paid", order_id=razorpay_order_id)
            return

        pack = rows[0]
        org_id = pack["organization_id"]
        minutes = float(pack["minutes_purchased"])

        # Mark pack as paid
        try:
            await self.db.database.from_("minute_packs") \
                .eq("id", pack["id"]) \
                .update({
                    "status": "paid",
                    "razorpay_payment_id": razorpay_payment_id,
                })
        except json.JSONDecodeError:
            pass  # InsForge 204 on success
        except Exception as exc:
            logger.error("topup.pack_update_failed", error=str(exc))

        # Update org minute_balance
        try:
            org_rows = await self.db.database.from_("organizations") \
                .select("minute_balance") \
                .eq("id", org_id) \
                .limit(1) \
                .execute()
            org_rows = org_rows if isinstance(org_rows, list) else []
            current_balance = float(org_rows[0].get("minute_balance", 0) if org_rows else 0)
            new_balance = current_balance + minutes

            await self.db.database.from_("organizations") \
                .eq("id", org_id) \
                .update({"minute_balance": new_balance})
        except json.JSONDecodeError:
            pass  # InsForge 204 on success
        except Exception as exc:
            logger.error("topup.balance_update_failed", org_id=org_id, error=str(exc))

        # Update billing record
        try:
            await self.db.database.from_("billing_records") \
                .eq("razorpay_invoice_id", razorpay_order_id) \
                .eq("organization_id", org_id) \
                .update({
                    "status": "paid",
                    "razorpay_payment_id": razorpay_payment_id,
                })
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            logger.warning("topup.billing_record_update_failed", error=str(exc))

        logger.info(
            "topup.minutes_credited",
            org_id=org_id,
            minutes=minutes,
            order_id=razorpay_order_id,
        )

        track_event(
            distinct_id=org_id,
            event="topup_minutes_credited",
            properties={
                "org_id": org_id,
                "minutes": minutes,
                "payment_id": razorpay_payment_id,
            },
        )

    async def get_minute_balance(
        self, current_user: UserContext
    ) -> MinuteBalanceResponse:
        """Get current minute balance for the org."""
        org_id = current_user.organization_id
        _, balance = await self._get_org_rate_and_balance(org_id)

        # Get pack stats
        try:
            paid_packs = await self.db.database.from_("minute_packs") \
                .select("minutes_purchased, minutes_remaining") \
                .eq("organization_id", org_id) \
                .eq("status", "paid") \
                .execute()
            paid_packs = paid_packs if isinstance(paid_packs, list) else []
        except Exception:
            paid_packs = []

        total_purchased = sum(float(p.get("minutes_purchased", 0)) for p in paid_packs)
        total_used = total_purchased - sum(float(p.get("minutes_remaining", 0)) for p in paid_packs)
        active_packs = len([p for p in paid_packs if float(p.get("minutes_remaining", 0)) > 0])

        return MinuteBalanceResponse(
            organization_id=org_id,
            minute_balance=balance,
            total_purchased=round(total_purchased, 2),
            total_used=round(total_used, 2),
            active_packs=active_packs,
        )

    async def deduct_minutes(self, org_id: str, minutes_used: float) -> None:
        """Deduct minutes from org's oldest paid packs (FIFO).

        Called after a call completes (from webhook_service).
        """
        if minutes_used <= 0:
            return

        remaining_to_deduct = minutes_used

        # Get paid packs ordered by creation (oldest first = FIFO)
        try:
            packs = await self.db.database.from_("minute_packs") \
                .select("id, minutes_remaining") \
                .eq("organization_id", org_id) \
                .eq("status", "paid") \
                .gt("minutes_remaining", 0) \
                .order("created_at", desc=False) \
                .execute()
            packs = packs if isinstance(packs, list) else []
        except Exception as exc:
            logger.error("topup.deduct_fetch_failed", org_id=org_id, error=str(exc))
            return

        for pack in packs:
            if remaining_to_deduct <= 0:
                break

            pack_remaining = float(pack.get("minutes_remaining", 0))
            deduct_from_pack = min(remaining_to_deduct, pack_remaining)
            new_remaining = round(pack_remaining - deduct_from_pack, 2)

            try:
                await self.db.database.from_("minute_packs") \
                    .eq("id", pack["id"]) \
                    .update({"minutes_remaining": new_remaining})
            except json.JSONDecodeError:
                pass
            except Exception as exc:
                logger.error("topup.deduct_pack_failed", pack_id=pack["id"], error=str(exc))

            remaining_to_deduct -= deduct_from_pack

        # Update org cached balance
        try:
            org_rows = await self.db.database.from_("organizations") \
                .select("minute_balance") \
                .eq("id", org_id) \
                .limit(1) \
                .execute()
            org_rows = org_rows if isinstance(org_rows, list) else []
            current = float(org_rows[0].get("minute_balance", 0) if org_rows else 0)
            new_balance = max(0, round(current - minutes_used, 2))

            await self.db.database.from_("organizations") \
                .eq("id", org_id) \
                .update({"minute_balance": new_balance})
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            logger.error("topup.balance_deduct_failed", org_id=org_id, error=str(exc))

        logger.info(
            "topup.minutes_deducted",
            org_id=org_id,
            minutes_deducted=minutes_used,
        )

    async def get_purchase_history(
        self, current_user: UserContext
    ) -> MinutePackListResponse:
        """Get all purchased packs for the org."""
        org_id = current_user.organization_id

        try:
            rows = await self.db.database.from_("minute_packs") \
                .select("*") \
                .eq("organization_id", org_id) \
                .order("created_at", desc=True) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception:
            rows = []

        packs = [
            MinutePackDetail(
                id=str(r.get("id", "")),
                minutes_purchased=float(r.get("minutes_purchased", 0)),
                minutes_remaining=float(r.get("minutes_remaining", 0)),
                amount_paid=float(r.get("amount_paid", 0)),
                status=r.get("status", "pending"),
                created_at=str(r.get("created_at", "")),
            )
            for r in rows
        ]

        return MinutePackListResponse(packs=packs, total=len(packs))

    # ── Internal helpers ─────────────────────────────────────────────────────

    async def _get_org_rate_and_balance(self, org_id: str) -> tuple[float, float]:
        """Get per-org rate_per_minute and cached minute_balance."""
        try:
            rows = await self.db.database.from_("organizations") \
                .select("rate_per_minute, minute_balance") \
                .eq("id", org_id) \
                .limit(1) \
                .execute()
            rows = rows if isinstance(rows, list) else []
            if rows:
                rate = float(rows[0].get("rate_per_minute", 3.50) or 3.50)
                balance = float(rows[0].get("minute_balance", 0) or 0)
                return rate, balance
        except Exception as exc:
            logger.warning("topup.org_info_failed", org_id=org_id, error=str(exc))
        return 3.50, 0.0
