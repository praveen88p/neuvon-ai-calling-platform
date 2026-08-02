from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import CurrentUserDep
from app.schemas.billing import VerifyPaymentRequest, PaymentVerificationResponse
from app.schemas.topup import (
    AvailablePacksResponse,
    MinuteBalanceResponse,
    MinutePackListResponse,
    TopUpOrderRequest,
    TopUpOrderResponse,
)
from app.services.billing_service import BillingService
from app.services.topup_service import TopUpService

router = APIRouter(prefix="/billing/topup", tags=["billing-topup"])


@router.get("/packs", response_model=AvailablePacksResponse)
async def get_available_packs(
    current_user: CurrentUserDep,
) -> AvailablePacksResponse:
    """Get available minute packs with prices based on org's rate."""
    service = TopUpService()
    return await service.get_available_packs(current_user)


@router.post("/order", response_model=TopUpOrderResponse)
async def create_topup_order(
    data: TopUpOrderRequest,
    current_user: CurrentUserDep,
) -> TopUpOrderResponse:
    """Create a Razorpay order to purchase minutes."""
    service = TopUpService()
    return await service.create_topup_order(data, current_user)


@router.get("/balance", response_model=MinuteBalanceResponse)
async def get_minute_balance(
    current_user: CurrentUserDep,
) -> MinuteBalanceResponse:
    """Get current minute balance for the org."""
    service = TopUpService()
    return await service.get_minute_balance(current_user)


@router.get("/history", response_model=MinutePackListResponse)
async def get_purchase_history(
    current_user: CurrentUserDep,
) -> MinutePackListResponse:
    """Get purchase history of minute packs."""
    service = TopUpService()
    return await service.get_purchase_history(current_user)


@router.post("/verify", response_model=PaymentVerificationResponse)
async def verify_topup_payment(
    data: VerifyPaymentRequest,
    current_user: CurrentUserDep,
) -> PaymentVerificationResponse:
    """Verify Razorpay payment after checkout and credit minutes."""
    # First verify the payment signature
    billing_service = BillingService()
    result = await billing_service.verify_payment(data, current_user)

    # Then credit the minutes
    if result.verified:
        topup_service = TopUpService()
        await topup_service.credit_minutes_on_payment(
            razorpay_order_id=data.razorpay_order_id,
            razorpay_payment_id=data.razorpay_payment_id,
        )

    return result
