from __future__ import annotations

from pydantic import BaseModel, Field


# --- Request schemas (kept for future super-admin Razorpay integration) ---

class CreateOrderRequest(BaseModel):
    """Input for creating a Razorpay payment order."""

    amount_inr: int = Field(..., gt=0, description="Amount in paisa (100 = ₹1)")
    description: str = Field(default="Neuvon AI — Call Credits", max_length=255)
    notes: dict[str, str] = Field(default_factory=dict, description="Key-value notes for Razorpay")


class VerifyPaymentRequest(BaseModel):
    """Input for verifying a Razorpay payment after checkout callback."""

    razorpay_order_id: str = Field(..., min_length=1)
    razorpay_payment_id: str = Field(..., min_length=1)
    razorpay_signature: str = Field(..., min_length=1)


# --- Response schemas ---

class UsageSummary(BaseModel):
    """Current billing period usage summary.

    Uses per-org custom rate_per_minute (set by Neuvon admin)
    instead of hardcoded plan tiers.
    """

    organization_id: str
    period_start: str
    period_end: str
    rate_per_minute: float = 3.50
    platform_fee: float = 0.0
    plan_label: str | None = None
    total_calls: int = 0
    total_minutes: float = 0.0
    total_cost: float = 0.0
    minutes_limit: float | None = None   # None = unlimited
    minutes_remaining: float | None = None


class OrderResponse(BaseModel):
    """Response after creating a Razorpay order."""

    order_id: str
    amount: int
    currency: str = "INR"
    receipt: str
    status: str
    razorpay_key_id: str


class PaymentVerificationResponse(BaseModel):
    """Response after verifying a Razorpay payment."""

    verified: bool
    payment_id: str
    order_id: str
    message: str


class InvoiceItem(BaseModel):
    """Single invoice in the billing history."""

    id: str
    organization_id: str
    period_start: str
    period_end: str
    total_minutes: float
    total_calls: int
    total_cost: float
    razorpay_invoice_id: str | None = None
    status: str
    created_at: str


class InvoiceListResponse(BaseModel):
    """Paginated invoice history."""

    invoices: list[InvoiceItem] = Field(default_factory=list)
    total: int = 0
