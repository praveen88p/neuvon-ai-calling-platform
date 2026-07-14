from __future__ import annotations


import json
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core.logging import logger
from app.core.posthog import track_event
from app.integrations.dograh_client import DograhClient
from app.integrations.insforge_client import get_insforge_admin
from app.schemas.agent import (
    AgentCountResponse,
    AgentCreateFromDefinition,
    AgentCreateFromTemplate,
    AgentDetailResponse,
    AgentListResponse,
    AgentResponse,
    AgentStatusUpdate,
    AgentUpdate,
    TestRunCreate,
)
from app.schemas.auth import UserContext


class AgentService:
    """Business logic for agent (workflow) management.

    Proxies Dograh API calls and maintains local agent-to-org mappings
    in the dograh_agent_mappings table for org-scoped access control.
    """

    def __init__(self) -> None:
        self.dograh = DograhClient()
        self.db = get_insforge_admin()

    async def list_agents(self, current_user: UserContext) -> AgentListResponse:
        """List all agents mapped to the current organization."""
        mappings = await self._get_org_mappings(current_user.organization_id)

        agents = [
            AgentResponse(
                workflow_id=m["dograh_workflow_id"],
                workflow_uuid=m.get("dograh_workflow_uuid"),
                name=m.get("agent_name", ""),
                status=m.get("agent_status", "active"),
                organization_id=current_user.organization_id,
                created_at=str(m.get("created_at", "")),
                updated_at=str(m.get("updated_at", "")),
            )
            for m in mappings
        ]

        return AgentListResponse(agents=agents, total=len(agents))

    async def get_agent(
        self, workflow_id: int, current_user: UserContext
    ) -> AgentDetailResponse:
        """Get full agent details from Dograh, scoped to org."""
        await self._verify_org_access(workflow_id, current_user)

        try:
            dograh_agent = await self.dograh.get_agent(workflow_id)
        except Exception as exc:
            logger.error("agent.fetch_failed", workflow_id=workflow_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch agent from Dograh",
            ) from exc

        return AgentDetailResponse(
            workflow_id=dograh_agent.get("id", workflow_id),
            workflow_uuid=dograh_agent.get("uuid"),
            name=dograh_agent.get("name", ""),
            status=dograh_agent.get("status"),
            organization_id=current_user.organization_id,
            workflow_definition=dograh_agent.get("workflow_definition"),
            created_at=dograh_agent.get("created_at"),
            updated_at=dograh_agent.get("updated_at"),
        )

    async def get_agent_count(self, current_user: UserContext) -> AgentCountResponse:
        """Get agent count by status for the current org."""
        mappings = await self._get_org_mappings(current_user.organization_id)

        active = sum(1 for m in mappings if m.get("agent_status") == "active")
        archived = sum(1 for m in mappings if m.get("agent_status") == "archived")

        return AgentCountResponse(
            active=active,
            archived=archived,
            total=len(mappings),
        )

    async def create_agent_from_definition(
        self, data: AgentCreateFromDefinition, current_user: UserContext
    ) -> AgentDetailResponse:
        """Create agent from explicit definition and map to org."""
        try:
            result = await self.dograh.create_agent_from_definition(
                name=data.name,
                workflow_definition=data.workflow_definition,
            )
        except Exception as exc:
            logger.error("agent.create_definition_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create agent in Dograh",
            ) from exc

        workflow_id = result.get("id")
        workflow_uuid = result.get("uuid")

        await self._create_mapping(
            workflow_id=workflow_id,
            workflow_uuid=workflow_uuid,
            name=data.name,
            org_id=current_user.organization_id,
        )

        track_event(
            distinct_id=current_user.organization_id,
            event="agent_created",
            properties={
                "org_id": current_user.organization_id,
                "agent_id": str(workflow_id),
                "creation_method": "definition",
            },
        )

        logger.info(
            "agent.created",
            org_id=current_user.organization_id,
            workflow_id=workflow_id,
            method="definition",
        )

        return AgentDetailResponse(
            workflow_id=workflow_id,
            workflow_uuid=workflow_uuid,
            name=data.name,
            status="active",
            organization_id=current_user.organization_id,
            workflow_definition=data.workflow_definition,
            created_at=result.get("created_at"),
            updated_at=result.get("updated_at"),
        )

    async def create_agent_from_template(
        self, data: AgentCreateFromTemplate, current_user: UserContext
    ) -> AgentDetailResponse:
        """Create agent from natural language template and map to org."""
        try:
            result = await self.dograh.create_agent_from_template(
                name=data.name,
                call_type=data.call_type,
                use_case=data.use_case,
                activity_description=data.activity_description,
            )
        except Exception as exc:
            logger.error("agent.create_template_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create agent from template",
            ) from exc

        workflow_id = result.get("id")
        workflow_uuid = result.get("uuid")

        await self._create_mapping(
            workflow_id=workflow_id,
            workflow_uuid=workflow_uuid,
            name=data.name,
            org_id=current_user.organization_id,
        )

        track_event(
            distinct_id=current_user.organization_id,
            event="agent_created",
            properties={
                "org_id": current_user.organization_id,
                "agent_id": str(workflow_id),
                "creation_method": "template",
            },
        )

        logger.info(
            "agent.created",
            org_id=current_user.organization_id,
            workflow_id=workflow_id,
            method="template",
        )

        return AgentDetailResponse(
            workflow_id=workflow_id,
            workflow_uuid=workflow_uuid,
            name=data.name,
            status="active",
            organization_id=current_user.organization_id,
            workflow_definition=result.get("workflow_definition"),
            created_at=result.get("created_at"),
            updated_at=result.get("updated_at"),
        )

    async def update_agent(
        self, workflow_id: int, data: AgentUpdate, current_user: UserContext
    ) -> AgentDetailResponse:
        """Update agent in Dograh and sync local mapping."""
        await self._verify_org_access(workflow_id, current_user)

        update_payload = {}
        if data.name is not None:
            update_payload["name"] = data.name
        if data.workflow_definition is not None:
            update_payload["workflow_definition"] = data.workflow_definition

        if not update_payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        try:
            result = await self.dograh.update_agent(workflow_id, update_payload)
        except Exception as exc:
            logger.error("agent.update_failed", workflow_id=workflow_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to update agent in Dograh",
            ) from exc

        if data.name is not None:
            now_iso = datetime.now(timezone.utc).isoformat()
            try:
                await self.db.database.from_("dograh_agent_mappings") \
                    .eq("dograh_workflow_id", workflow_id) \
                    .eq("organization_id", current_user.organization_id) \
                    .update(
                        {"agent_name": data.name, "updated_at": now_iso},
                        return_representation=True,
                    )
            except json.JSONDecodeError:
                pass

        logger.info("agent.updated", workflow_id=workflow_id, org_id=current_user.organization_id)
        return await self.get_agent(workflow_id, current_user)

    async def update_agent_status(
        self, workflow_id: int, data: AgentStatusUpdate, current_user: UserContext
    ) -> AgentDetailResponse:
        """Archive or restore an agent."""
        await self._verify_org_access(workflow_id, current_user)

        try:
            await self.dograh.update_agent_status(workflow_id, data.status)
        except Exception as exc:
            logger.error("agent.status_failed", workflow_id=workflow_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to update agent status",
            ) from exc

        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            await self.db.database.from_("dograh_agent_mappings") \
                .eq("dograh_workflow_id", workflow_id) \
                .eq("organization_id", current_user.organization_id) \
                .update(
                    {"agent_status": data.status, "updated_at": now_iso},
                    return_representation=True,
                )
        except json.JSONDecodeError:
            pass

        logger.info(
            "agent.status_updated",
            workflow_id=workflow_id,
            new_status=data.status,
            org_id=current_user.organization_id,
        )
        return await self.get_agent(workflow_id, current_user)

    async def validate_agent(self, workflow_id: int, current_user: UserContext) -> dict:
        """Validate a workflow definition without executing."""
        await self._verify_org_access(workflow_id, current_user)

        try:
            return await self.dograh.validate_agent(workflow_id)
        except Exception as exc:
            logger.error("agent.validate_failed", workflow_id=workflow_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to validate agent",
            ) from exc

    async def create_test_run(
        self, workflow_id: int, data: TestRunCreate, current_user: UserContext
    ) -> dict:
        """Create a test run for an agent without placing a real call."""
        await self._verify_org_access(workflow_id, current_user)

        try:
            body = {}
            if data.initial_context:
                body["initial_context"] = data.initial_context
            return await self.dograh.create_test_run(workflow_id, body)
        except Exception as exc:
            logger.error("agent.test_run_failed", workflow_id=workflow_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create test run",
            ) from exc

    async def list_workflow_runs(
        self, workflow_id: int, current_user: UserContext, page: int = 1, limit: int = 20
    ) -> dict:
        """List runs for a specific agent."""
        await self._verify_org_access(workflow_id, current_user)

        try:
            return await self.dograh.list_workflow_runs(
                workflow_id, params={"page": page, "limit": limit}
            )
        except Exception as exc:
            logger.error("agent.list_runs_failed", workflow_id=workflow_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to list agent runs",
            ) from exc

    # --- Internal helpers ---

    async def _get_org_mappings(self, org_id: str) -> list[dict]:
        """Get all agent mappings for an organization."""
        try:
            rows = await self.db.database.from_("dograh_agent_mappings") \
                .select("*") \
                .eq("organization_id", org_id) \
                .order("created_at") \
                .execute()
            return rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("agent.mappings_fetch_failed", org_id=org_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch agent mappings",
            ) from exc

    async def _verify_org_access(self, workflow_id: int, current_user: UserContext) -> dict:
        """Verify that the agent belongs to the user's organization."""
        try:
            rows = await self.db.database.from_("dograh_agent_mappings") \
                .select("*") \
                .eq("dograh_workflow_id", workflow_id) \
                .eq("organization_id", current_user.organization_id) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error("agent.access_check_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify agent access",
            ) from exc

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found in this organization",
            )

        return rows[0]

    async def _create_mapping(
        self,
        workflow_id: int,
        workflow_uuid: str | None,
        name: str,
        org_id: str,
    ) -> None:
        """Create a local agent-to-org mapping record."""
        try:
            await self.db.database.from_("dograh_agent_mappings").insert(
                [{
                    "organization_id": org_id,
                    "dograh_workflow_id": workflow_id,
                    "dograh_workflow_uuid": workflow_uuid or "",
                    "agent_name": name,
                    "agent_status": "active",
                }]
            )
        except Exception as exc:
            logger.error("agent.mapping_create_failed", workflow_id=workflow_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create agent mapping",
            ) from exc
