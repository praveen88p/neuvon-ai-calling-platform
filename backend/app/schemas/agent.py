from __future__ import annotations

from pydantic import BaseModel, Field


class AgentCreateFromDefinition(BaseModel):
    """Create agent from explicit workflow definition (nodes + edges)."""

    name: str = Field(..., min_length=1, max_length=200)
    workflow_definition: dict = Field(..., description="Workflow nodes and edges")


class AgentCreateFromTemplate(BaseModel):
    """Create agent from a template via Dograh's natural language builder."""

    name: str = Field(..., min_length=1, max_length=200)
    call_type: str = Field(
        default="outbound",
        description="Type of call: 'outbound' or 'inbound'",
    )
    use_case: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Use case label, e.g. 'appointment_reminder', 'lead_qualification'",
    )
    activity_description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Natural language description of what the agent should do",
    )


class AgentUpdate(BaseModel):
    """Update agent name, definition, or configuration."""

    name: str | None = None
    workflow_definition: dict | None = None


class AgentStatusUpdate(BaseModel):
    """Archive or restore an agent."""

    status: str = Field(..., pattern="^(active|archived)$")


class AgentResponse(BaseModel):
    """Agent response from our backend (enriched with org context)."""

    workflow_id: int
    workflow_uuid: str | None = None
    name: str
    status: str | None = None
    organization_id: str
    created_at: str | None = None
    updated_at: str | None = None


class AgentDetailResponse(BaseModel):
    """Full agent details including workflow definition."""

    workflow_id: int
    workflow_uuid: str | None = None
    name: str
    status: str | None = None
    organization_id: str
    workflow_definition: dict | None = None
    created_at: str | None = None
    updated_at: str | None = None


class AgentListResponse(BaseModel):
    """Paginated list of agents for the current org."""

    agents: list[AgentResponse]
    total: int


class AgentCountResponse(BaseModel):
    """Agent count breakdown by status."""

    active: int = 0
    archived: int = 0
    total: int = 0


class TestRunCreate(BaseModel):
    """Create a test run for an agent without placing a real call.

    Dograh requires `mode` and `name` in the body. Mode is always "test"
    (set by DograhClient); name is a label for the run.
    """

    name: str = Field(default="Test Run", max_length=200)
    initial_context: dict | None = None


class TestCallCreate(BaseModel):
    """Trigger a real phone call to test an agent.

    The agent will call the provided phone_number. This is provider-agnostic:
    Dograh routes through whatever telephony provider is configured on the agent.
    """

    phone_number: str = Field(
        ...,
        min_length=10,
        max_length=20,
        description="E.164 phone number to call, e.g. +919876543210",
    )
    initial_context: dict | None = None


class TestCallResponse(BaseModel):
    """Response from triggering a test phone call."""

    status: str
    workflow_run_id: int | None = None
    workflow_run_name: str | None = None
    message: str
