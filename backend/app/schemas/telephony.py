from __future__ import annotations

from pydantic import BaseModel, Field


# --- Telephony Configuration Schemas ---


class TelephonyConfigCreate(BaseModel):
    """Input for creating a telephony configuration."""

    provider: str = Field(..., description="Provider name (e.g. 'plivo', 'twilio', 'vobiz')")
    name: str = Field(..., min_length=1, max_length=64, description="Config display name (unique per org)")
    credentials: dict = Field(..., description="Provider-specific credential fields (flat key-value)")
    is_default_outbound: bool = Field(False, description="Set as org-wide default for outbound calls")


class TelephonyConfigUpdate(BaseModel):
    """Input for updating a telephony configuration."""

    name: str | None = Field(None, min_length=1, max_length=64)
    credentials: dict | None = None


class TelephonyConfigResponse(BaseModel):
    """Telephony configuration from Dograh."""

    id: int
    provider: str | None = None
    name: str | None = None
    is_default_outbound: bool = False
    phone_number_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class TelephonyConfigListResponse(BaseModel):
    """List of telephony configurations."""

    configs: list[TelephonyConfigResponse]
    total: int


class TelephonyProviderField(BaseModel):
    """A single credential field for a provider."""

    name: str
    label: str | None = None
    type: str = "text"  # text, password, textarea, string-array, number
    required: bool = True
    sensitive: bool = False
    description: str | None = None


class TelephonyProviderMetadata(BaseModel):
    """Provider metadata with required credential fields."""

    provider: str
    display_name: str | None = None
    docs_url: str | None = None
    fields: list[TelephonyProviderField] = []


class TelephonyProvidersResponse(BaseModel):
    """List of supported telephony providers."""

    providers: list[TelephonyProviderMetadata]


# --- Phone Number Schemas ---


class PhoneNumberCreate(BaseModel):
    """Input for adding a phone number to a config."""

    address: str = Field(..., description="Phone number (E.164 format, e.g. +14155551234)")
    country_code: str | None = Field(None, max_length=5, description="ISO country code (e.g. US, IN)")
    label: str | None = Field(None, max_length=100, description="Display label")
    inbound_workflow_id: int | None = Field(
        None, description="Workflow to route inbound calls to"
    )
    is_active: bool = True
    is_default_caller_id: bool = False


class PhoneNumberUpdate(BaseModel):
    """Input for updating a phone number."""

    label: str | None = Field(None, max_length=100)
    inbound_workflow_id: int | None = None
    is_active: bool | None = None
    is_default_caller_id: bool | None = None


class ProviderSync(BaseModel):
    """Provider sync status for a phone number."""

    ok: bool = True
    message: str | None = None


class PhoneNumberResponse(BaseModel):
    """Phone number details from Dograh."""

    id: int
    telephony_configuration_id: int | None = None
    address: str | None = None
    address_normalized: str | None = None
    address_type: str | None = None  # "pstn"
    country_code: str | None = None
    label: str | None = None
    is_default_caller_id: bool = False
    is_active: bool = True
    inbound_workflow_id: int | None = None
    inbound_workflow_name: str | None = None
    extra_metadata: dict | None = None
    provider_sync: ProviderSync | None = None
    created_at: str | None = None
    updated_at: str | None = None


class PhoneNumberListResponse(BaseModel):
    """List of phone numbers for a config."""

    phone_numbers: list[PhoneNumberResponse]
    total: int
