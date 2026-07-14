from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class TelephonyConfig(SQLModel, table=True):
    """Telephony provider configuration mapped to an organization."""

    __tablename__ = "telephony_configs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    dograh_config_id: int = Field(index=True)
    provider: str = Field(default="")  # "plivo"|"twilio"|"vonage"|"telnyx"
    label: str = Field(default="")
    is_default_outbound: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PhoneNumber(SQLModel, table=True):
    """Phone number registered under a telephony config."""

    __tablename__ = "phone_numbers"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    telephony_config_id: UUID = Field(foreign_key="telephony_configs.id", index=True)
    dograh_phone_id: int = Field(index=True)
    number: str = Field(default="")  # E.164
    label: str = Field(default="")
    is_default_caller: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
