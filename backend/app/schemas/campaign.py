from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# --- Input schemas ---


class TimeSlot(BaseModel):
    """A single scheduling time slot."""

    day: str = Field(..., description="Day of week, e.g. 'monday'")
    start: str = Field(..., description="Start time HH:MM")
    end: str = Field(..., description="End time HH:MM")


class RetryConfig(BaseModel):
    """Campaign retry configuration."""

    max_attempts: int = Field(3, ge=1, le=10)
    retry_interval_minutes: int = Field(60, ge=1)


class ScheduleConfig(BaseModel):
    """Campaign scheduling configuration."""

    timezone: str = Field("UTC")
    time_slots: list[TimeSlot] = Field(default_factory=list)


class CampaignCreate(BaseModel):
    """Input schema for creating a campaign."""

    name: str = Field(..., min_length=1, max_length=200)
    workflow_id: int = Field(..., description="Dograh workflow ID for the agent")
    contact_list_id: str = Field(..., description="Contact list ID from upload response")
    concurrency: int = Field(1, ge=1, le=50)
    retry_config: RetryConfig | None = None
    schedule_config: ScheduleConfig | None = None

    model_config = {"strict": True}


class CampaignUpdate(BaseModel):
    """Input schema for updating campaign settings."""

    name: str | None = Field(None, min_length=1, max_length=200)
    concurrency: int | None = Field(None, ge=1, le=50)
    retry_config: RetryConfig | None = None
    schedule_config: ScheduleConfig | None = None


# --- Output schemas ---


class ContactListUploadResponse(BaseModel):
    """Response from uploading a contacts CSV."""

    contact_list_id: str
    total_contacts: int
    message: str = "Contacts uploaded successfully"


class CampaignResponse(BaseModel):
    """Output schema for campaign data."""

    id: str
    organization_id: str
    dograh_campaign_id: int
    dograh_workflow_id: int
    name: str
    status: str
    total_contacts: int
    contacts_processed: int
    concurrency: int
    retry_config: dict | None = None
    schedule_config: dict | None = None
    contact_list_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class CampaignListResponse(BaseModel):
    """Response schema for listing campaigns."""

    campaigns: list[CampaignResponse]
    total: int


class CampaignProgressResponse(BaseModel):
    """Response from campaign progress endpoint."""

    campaign_id: int
    status: str
    total_contacts: int
    contacts_processed: int
    contacts_remaining: int
    success_count: int
    failed_count: int
    in_progress_count: int


class CampaignActionResponse(BaseModel):
    """Response for start/pause/resume actions."""

    campaign_id: int
    status: str
    message: str
