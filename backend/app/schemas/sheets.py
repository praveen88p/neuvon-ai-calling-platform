"""Pydantic schemas for the spreadsheet integration feature.

Follows the project's RORO pattern: every service method takes a
``*Create`` / ``*Update`` schema and returns a ``*Response`` schema.
"""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# ── Helpers ───────────────────────────────────────────────────────────────

_SHEETS_URL_RE = re.compile(
    r"https://docs\.google\.com/spreadsheets/d/[a-zA-Z0-9_-]+"
)


# ── Request schemas ───────────────────────────────────────────────────────


class SheetConnectionCreate(BaseModel):
    """Input for creating a new sheet connection."""

    sheet_url: str = Field(
        ..., description="Full Google Sheets URL"
    )
    sheet_name: str | None = Field(
        None, description="Tab name (auto-detect first tab if None)"
    )
    column_mapping: dict[str, str] = Field(
        ...,
        description=(
            'Maps internal field names to column letters: '
            '{"phone": "B", "name": "A", "email": "C"}'
        ),
    )
    agent_workflow_id: int = Field(
        ..., description="Dograh workflow ID of the agent that handles calls"
    )
    credentials_json: str = Field(
        ..., description="Google service account JSON key"
    )
    polling_interval_secs: int = Field(
        60, ge=30, le=3600, description="Polling interval in seconds"
    )

    @field_validator("sheet_url")
    @classmethod
    def validate_sheets_url(cls, v: str) -> str:
        if not _SHEETS_URL_RE.match(v):
            msg = "Must be a valid Google Sheets URL"
            raise ValueError(msg)
        return v

    @field_validator("column_mapping")
    @classmethod
    def validate_phone_column(cls, v: dict[str, str]) -> dict[str, str]:
        if "phone" not in v:
            msg = 'column_mapping must include a "phone" column'
            raise ValueError(msg)
        return v


class SheetConnectionUpdate(BaseModel):
    """Input for updating an existing connection."""

    column_mapping: dict[str, str] | None = None
    agent_workflow_id: int | None = None
    polling_interval_secs: int | None = Field(None, ge=30, le=3600)
    is_active: bool | None = None
    # Phase 4 settings
    max_concurrent_calls: int | None = Field(
        None, ge=1, le=50, description="Max concurrent calls at once (default 5)"
    )
    duplicate_window_hours: int | None = Field(
        None, ge=0, le=168,
        description="Skip re-calling same phone within N hours (0 = disabled, max 7 days)"
    )


class DetectColumnsRequest(BaseModel):
    """Input for auto-detecting columns from a sheet URL."""

    sheet_url: str = Field(..., description="Full Google Sheets URL")
    credentials_json: str = Field(
        ..., description="Google service account JSON key"
    )
    sheet_name: str | None = Field(
        None, description="Specific tab name (auto-detect if None)"
    )


# ── Response schemas ──────────────────────────────────────────────────────


class SheetConnectionResponse(BaseModel):
    """Response for a single sheet connection."""

    id: str
    organization_id: str
    provider: str
    sheet_url: str
    spreadsheet_id: str
    sheet_name: str
    column_mapping: dict[str, str]
    agent_workflow_id: int
    is_active: bool
    last_row_processed: int
    last_polled_at: datetime | None = None
    last_error: str | None = None
    polling_interval_secs: int
    total_leads_found: int
    total_leads_called: int
    total_leads_qualified: int
    # Phase 4 fields
    needs_reauth: bool = False
    max_concurrent_calls: int = 5
    duplicate_window_hours: int = 24
    consecutive_error_count: int = 0
    created_at: datetime
    updated_at: datetime


class SheetColumn(BaseModel):
    """A single detected column from a sheet."""

    letter: str = Field(..., description="Column letter (A, B, C...)")
    header: str = Field(..., description="Header text from row 1")
    sample: str = Field("", description="First data value for preview")


class SheetColumnsResponse(BaseModel):
    """Response from column auto-detection."""

    spreadsheet_id: str
    sheet_names: list[str]
    selected_sheet: str
    columns: list[SheetColumn]
    row_count: int


class SheetLeadResponse(BaseModel):
    """Response for a single lead from a sheet."""

    id: str
    connection_id: str
    row_number: int
    phone_number: str
    lead_data: dict
    call_status: str
    call_summary: str | None = None
    lead_tag: str | None = None
    callback_at: datetime | None = None
    writeback_done: bool = False
    dograh_run_id: int | None = None
    created_at: datetime
    updated_at: datetime


class SheetLeadsListResponse(BaseModel):
    """Paginated list of leads."""

    leads: list[SheetLeadResponse]
    total: int
    page: int
    limit: int


class SheetConnectionStats(BaseModel):
    """Aggregated stats for a connection."""

    total_leads_found: int
    total_leads_called: int
    total_leads_qualified: int
    pending: int
    calling: int
    completed: int
    failed: int
    callback_scheduled: int
