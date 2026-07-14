from __future__ import annotations

from pydantic import BaseModel, Field


# --- Telephony Configuration Schemas ---


class TelephonyConfigCreate(BaseModel):
    """Input for creating a telephony configuration."""

    provider: str = Field(..., description="Provider name (e.g. 'plivo', 'twilio')")
    name: str = Field(..., min_length=1, max_length=100, description="Config display name")
    credentials: dict = Field(..., description="Provider-specific credential fields")


class TelephonyConfigUpdate(BaseModel):
    """Input for updating a telephony configuration."""

    name: str | None = Field(None, min_length=1, max_length=100)
    credentials: dict | None = None


class TelephonyConfigResponse(BaseModel):
    """Telephony configuration from Dograh."""

    id: int
    provider: str | None = None
    name: str | None = None
    is_default_outbound: bool = False
    created_at: str | None = None
    updated_at: str | None = None


class TelephonyConfigListResponse(BaseModel):
    """List of telephony configurations."""

    configs: list[TelephonyConfigResponse]
    total: int


class TelephonyProviderMetadata(BaseModel):
    """Provider metadata with required credential fields."""

    provider: str
    display_name: str | None = None
    credential_fields: list[dict] = []


class TelephonyProvidersResponse(BaseModel):
    """List of supported telephony providers."""

    providers: list[TelephonyProviderMetadata]


# --- Phone Number Schemas ---


class PhoneNumberCreate(BaseModel):
    """Input for adding a phone number to a config."""

    phone_number: str = Field(..., description="Phone number in E.164 format")
    label: str | None = Field(None, max_length=100, description="Display label")
    inbound_workflow_id: int | None = Field(
        None, description="Workflow to route inbound calls to"
    )


class PhoneNumberUpdate(BaseModel):
    """Input for updating a phone number."""

    label: str | None = Field(None, max_length=100)
    inbound_workflow_id: int | None = None
    is_active: bool | None = None


class PhoneNumberResponse(BaseModel):
    """Phone number details."""

    id: int
    phone_number: str | None = None
    label: str | None = None
    is_default_caller: bool = False
    is_active: bool = True
    inbound_workflow_id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


class PhoneNumberListResponse(BaseModel):
    """List of phone numbers for a config."""

    phone_numbers: list[PhoneNumberResponse]
    total: int
