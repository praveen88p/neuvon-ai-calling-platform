from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUserDep
from app.schemas.billing import (
    CreateOrderRequest,
    InvoiceListResponse,
    OrderResponse,
    PaymentVerificationResponse,
    PlanDetails,
    UsageSummary,
    VerifyPaymentRequest,
)
from app.services.billing_service import BillingService

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/usage", response_model=UsageSummary)
async def get_usage_summary(current_user: CurrentUserDep) -> UsageSummary:
    """Current billing period usage vs plan limits."""
    service = BillingService()
    return await service.get_usage_summary(current_user)


@router.get("/plan", response_model=PlanDetails)
async def get_plan_details(current_user: CurrentUserDep) -> PlanDetails:
    """Current organization plan details and features."""
    service = BillingService()
    return await service.get_plan_details(current_user)


@router.post("/orders", response_model=OrderResponse)
async def create_payment_order(
    data: CreateOrderRequest,
    current_user: CurrentUserDep,
) -> OrderResponse:
    """Create a Razorpay order for plan purchase or credit top-up."""
    service = BillingService()
    return await service.create_order(data, current_user)


@router.post("/verify", response_model=PaymentVerificationResponse)
async def verify_payment(
    data: VerifyPaymentRequest,
    current_user: CurrentUserDep,
) -> PaymentVerificationResponse:
    """Verify Razorpay payment after checkout callback."""
    service = BillingService()
    return await service.verify_payment(data, current_user)


@router.get("/invoices", response_model=InvoiceListResponse)
async def get_invoices(
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
) -> InvoiceListResponse:
    """Paginated billing record / invoice history."""
    service = BillingService()
    return await service.get_invoices(current_user, page, per_page)
