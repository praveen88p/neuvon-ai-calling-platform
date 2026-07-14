from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class BillingRecord(SQLModel, table=True):
    """Billing record — tracks usage and payment per billing period."""

    __tablename__ = "billing_records"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    period_start: date
    period_end: date
    total_minutes: Decimal = Field(default=Decimal("0"))
    total_calls: int = Field(default=0)
    total_cost_usd: Decimal = Field(default=Decimal("0"))
    razorpay_invoice_id: str | None = Field(default=None)
    status: str = Field(default="pending")  # "pending" | "paid" | "overdue"
    created_at: datetime = Field(default_factory=datetime.utcnow)
