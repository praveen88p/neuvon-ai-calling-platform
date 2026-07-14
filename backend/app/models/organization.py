from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class Organization(SQLModel, table=True):
    """Multi-tenant root entity — every other table references this."""

    __tablename__ = "organizations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True)
    org_type: str = Field(default="direct")  # "direct" | "reseller"
    white_label: dict | None = Field(default=None, sa_column=sa.Column(sa.JSON, nullable=True))
    dograh_api_key: str | None = Field(default=None)  # encrypted at rest
    billing_plan: str = Field(default="free")  # "free" | "starter" | "growth" | "enterprise"
    usage_quota: dict | None = Field(default=None, sa_column=sa.Column(sa.JSON, nullable=True))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
