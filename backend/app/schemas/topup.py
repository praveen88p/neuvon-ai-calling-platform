from __future__ import annotations

from pydantic import BaseModel, Field


# ─── Minute Pack Options (what the client sees) ─────────────────────────────

class MinutePackOption(BaseModel):
    """A pre-defined minute pack available for purchase."""

    minutes: int
    price: float  # in ₹
    label: str  # e.g. "100 minutes"


class AvailablePacksResponse(BaseModel):
    """List of packs a client can buy, with their current rate."""

    rate_per_minute: float
    packs: list[MinutePackOption]
    minute_balance: float = 0.0


# ─── Top-Up Order ────────────────────────────────────────────────────────────

class TopUpOrderRequest(BaseModel):
    """Client request to purchase a minute pack."""

    minutes: int = Field(..., gt=0, description="Number of minutes to purchase")


class TopUpOrderResponse(BaseModel):
    """Response after creating a Razorpay order for a top-up."""

    order_id: str
    amount: int  # in paise
    currency: str = "INR"
    razorpay_key_id: str
    minutes: int
    rate_per_minute: float
    description: str


# ─── Minute Balance ──────────────────────────────────────────────────────────

class MinuteBalanceResponse(BaseModel):
    """Current minute balance for an organization."""

    organization_id: str
    minute_balance: float
    total_purchased: float
    total_used: float
    active_packs: int


# ─── Minute Pack Detail ─────────────────────────────────────────────────────

class MinutePackDetail(BaseModel):
    """Single purchased minute pack."""

    id: str
    minutes_purchased: float
    minutes_remaining: float
    amount_paid: float
    status: str
    created_at: str | None = None


class MinutePackListResponse(BaseModel):
    """List of purchased packs."""

    packs: list[MinutePackDetail] = Field(default_factory=list)
    total: int = 0
