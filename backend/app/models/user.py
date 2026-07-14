from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """User model — extends InsForge auth.users with org membership and role."""

    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    email: str = Field(index=True)
    full_name: str = Field(default="")
    role: str = Field(default="member")  # "platform_admin" | "owner" | "admin" | "member"
    is_active: bool = Field(default=True)
    last_login_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
