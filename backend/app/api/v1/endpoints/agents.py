from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_current_user
from app.schemas.agent import (
    AgentCountResponse,
    AgentCreateFromDefinition,
    AgentCreateFromTemplate,
    AgentDetailResponse,
    AgentListResponse,
    AgentStatusUpdate,
    AgentUpdate,
    TestRunCreate,
)
from app.schemas.auth import UserContext
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> AgentListResponse:
    """List all agents mapped to the current organization."""
    service = AgentService()
    return await service.list_agents(current_user)


@router.get("/count", response_model=AgentCountResponse)
async def get_agent_count(
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> AgentCountResponse:
    """Get agent count breakdown by status for the current org."""
    service = AgentService()
    return await service.get_agent_count(current_user)


@router.post(
    "/from-definition",
    response_model=AgentDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_agent_from_definition(
    data: AgentCreateFromDefinition,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> AgentDetailResponse:
    """Create agent from explicit workflow definition (nodes + edges)."""
    service = AgentService()
    return await service.create_agent_from_definition(data, current_user)


@router.post(
    "/from-template",
    response_model=AgentDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_agent_from_template(
    data: AgentCreateFromTemplate,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> AgentDetailResponse:
    """Create agent from natural language description."""
    service = AgentService()
    return await service.create_agent_from_template(data, current_user)


@router.get("/{workflow_id}", response_model=AgentDetailResponse)
async def get_agent(
    workflow_id: int,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> AgentDetailResponse:
    """Get full agent details with workflow definition."""
    service = AgentService()
    return await service.get_agent(workflow_id, current_user)


@router.put("/{workflow_id}", response_model=AgentDetailResponse)
async def update_agent(
    workflow_id: int,
    data: AgentUpdate,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> AgentDetailResponse:
    """Update agent name, definition, or configuration."""
    service = AgentService()
    return await service.update_agent(workflow_id, data, current_user)


@router.put("/{workflow_id}/archive", response_model=AgentDetailResponse)
async def update_agent_status(
    workflow_id: int,
    data: AgentStatusUpdate,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> AgentDetailResponse:
    """Archive or restore an agent."""
    service = AgentService()
    return await service.update_agent_status(workflow_id, data, current_user)


@router.post("/{workflow_id}/validate")
async def validate_agent(
    workflow_id: int,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> dict:
    """Validate a workflow definition without executing."""
    service = AgentService()
    return await service.validate_agent(workflow_id, current_user)


@router.post("/{workflow_id}/test-run", status_code=status.HTTP_201_CREATED)
async def create_test_run(
    workflow_id: int,
    data: TestRunCreate,
    current_user: Annotated[UserContext, Depends(get_current_user)],
) -> dict:
    """Create a test run without placing a real call."""
    service = AgentService()
    return await service.create_test_run(workflow_id, data, current_user)


@router.get("/{workflow_id}/runs")
async def list_workflow_runs(
    workflow_id: int,
    current_user: Annotated[UserContext, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    """List all runs for a specific agent."""
    service = AgentService()
    return await service.list_workflow_runs(workflow_id, current_user, page, limit)
