from __future__ import annotations


import json
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core.config import get_settings
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
    TestCallCreate,
    TestCallResponse,
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

        # Auto-inject webhook node so post-call data flows back to our billing system
        await self._inject_webhook_node(workflow_id)

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

        # Auto-inject webhook node so post-call data flows back to our billing system
        await self._inject_webhook_node(workflow_id)

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
            body: dict = {"name": data.name}
            if data.initial_context:
                body["initial_context"] = data.initial_context
            return await self.dograh.create_test_run(workflow_id, body)
        except Exception as exc:
            logger.error("agent.test_run_failed", workflow_id=workflow_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create test run",
            ) from exc

    async def trigger_test_call(
        self,
        workflow_id: int,
        data: TestCallCreate,
        current_user: UserContext,
    ) -> TestCallResponse:
        """Trigger a real outbound phone call to test an agent.

        Provider-agnostic: Dograh routes through whatever telephony provider
        is configured on the agent. We use the workflow_uuid (trigger UUID)
        from the /public/agent/{uuid} endpoint.
        """
        await self._verify_org_access(workflow_id, current_user)

        workflow_uuid = await self._get_workflow_uuid(workflow_id)

        try:
            result = await self.dograh.trigger_outbound_call(
                workflow_uuid=workflow_uuid,
                phone_number=data.phone_number,
                initial_context=data.initial_context,
            )
        except Exception as exc:
            logger.error(
                "agent.test_call_failed",
                workflow_id=workflow_id,
                phone_number=data.phone_number,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to trigger test call: {exc}",
            ) from exc

        track_event(
            distinct_id=current_user.organization_id,
            event="agent_test_call",
            properties={
                "org_id": current_user.organization_id,
                "agent_id": str(workflow_id),
            },
        )

        logger.info(
            "agent.test_call_triggered",
            workflow_id=workflow_id,
            org_id=current_user.organization_id,
        )

        return TestCallResponse(
            status=result.get("status", "initiated"),
            workflow_run_id=result.get("workflow_run_id"),
            workflow_run_name=result.get("workflow_run_name"),
            message="Agent is calling your number now",
        )

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

    async def _get_workflow_uuid(self, workflow_id: int) -> str:
        """Get the workflow_uuid (trigger UUID) for a workflow.

        1. Read from local DB (dograh_agent_mappings.dograh_workflow_uuid).
        2. If empty, fetch from Dograh /workflow/fetch and cache it.
        3. Raise 404 if not found.
        """
        # 1. Check local DB
        try:
            rows = await self.db.database.from_("dograh_agent_mappings") \
                .select("dograh_workflow_uuid") \
                .eq("dograh_workflow_id", workflow_id) \
                .execute()
            rows = rows if isinstance(rows, list) else []
        except Exception:
            rows = []

        uuid_val = (rows[0].get("dograh_workflow_uuid", "") if rows else "")
        if uuid_val:
            return uuid_val

        # 2. Fetch from Dograh and cache
        try:
            all_wf = await self.dograh._request("GET", "/workflow/fetch")
            workflows = all_wf if isinstance(all_wf, list) else [all_wf]
        except Exception as exc:
            logger.error("agent.workflow_fetch_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch workflow UUID from Dograh",
            ) from exc

        for wf in workflows:
            if wf.get("id") == workflow_id:
                uuid_val = wf.get("workflow_uuid", "")
                if uuid_val:
                    # Cache it in local DB for next time
                    try:
                        await (
                            self.db.database.from_("dograh_agent_mappings")
                            .eq("dograh_workflow_id", workflow_id)
                            .update({"dograh_workflow_uuid": uuid_val})
                        )
                    except ValueError as ve:
                        # JSONDecodeError on 204 = success
                        if "Expecting value" not in str(ve):
                            logger.warning("agent.uuid_cache_failed", error=str(ve))
                    except Exception as cache_exc:
                        logger.warning("agent.uuid_cache_failed", error=str(cache_exc))
                    return uuid_val

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent trigger UUID not found. Ensure the agent has an active API trigger.",
        )

    def _build_webhook_node(self, webhook_url: str) -> dict:
        """Build the Dograh webhook node definition that sends post-call data to our backend.

        The payload_template uses Dograh's {{variable}} template syntax.
        Fields map to DograhWebhookPayload in app/schemas/webhook.py.
        """
        return {
            "id": "neuvon-webhook",
            "type": "webhook",
            "position": {"x": 900, "y": 300},
            "data": {
                "name": "Neuvon Post-Call Sync",
                "enabled": True,
                "http_method": "POST",
                "endpoint_url": webhook_url,
                "custom_headers": [],
                "credential_uuid": None,
                "payload_template": {
                    "workflow_run_id": "{{workflow_run_id}}",
                    "workflow_id": "{{workflow_id}}",
                    "workflow_name": "{{workflow_name}}",
                    "status": "completed",
                    "call_duration_seconds": "{{cost_info.call_duration_seconds}}",
                    "phone_number": "{{initial_context.phone_number}}",
                    "caller_number": "{{initial_context.caller_number}}",
                    "recording_url": "{{recording_url}}",
                    "transcript_url": "{{transcript_url}}",
                    "initial_context": "{{initial_context}}",
                    "gathered_context": "{{gathered_context}}",
                    "cost_info": "{{cost_info}}",
                    "annotations": "{{annotations}}",
                },
            },
        }

    async def _inject_webhook_node(self, workflow_id: int) -> None:
        """Add a webhook node to an existing agent's workflow definition.

        - Fetches the current workflow definition from Dograh
        - Skips if a webhook node already exists (idempotent)
        - Appends the Neuvon webhook node and updates the workflow
        - Logs a warning and continues if BACKEND_PUBLIC_URL is not configured
        """
        settings = get_settings()
        base_url = (settings.BACKEND_PUBLIC_URL or "").rstrip("/")

        if not base_url:
            logger.warning(
                "agent.webhook_inject_skipped",
                workflow_id=workflow_id,
                reason="BACKEND_PUBLIC_URL not configured in .env",
            )
            return

        webhook_url = f"{base_url}/api/v1/webhooks/dograh"

        try:
            agent = await self.dograh.get_agent(workflow_id)
        except Exception as exc:
            logger.warning(
                "agent.webhook_inject_fetch_failed",
                workflow_id=workflow_id,
                error=str(exc),
            )
            return

        definition = agent.get("workflow_definition") or {}
        nodes = definition.get("nodes") or []
        edges = definition.get("edges") or []

        # Idempotency: skip if we already have a webhook node pointing at our endpoint
        existing_urls = [
            n.get("data", {}).get("endpoint_url", "")
            for n in nodes
            if n.get("type") == "webhook"
        ]
        if webhook_url in existing_urls:
            logger.info(
                "agent.webhook_already_present",
                workflow_id=workflow_id,
            )
            return

        # Append webhook node
        nodes.append(self._build_webhook_node(webhook_url))
        updated_definition = {"nodes": nodes, "edges": edges}

        try:
            await self.dograh.update_agent(
                workflow_id,
                {"workflow_definition": updated_definition},
            )
            logger.info(
                "agent.webhook_injected",
                workflow_id=workflow_id,
                webhook_url=webhook_url,
            )
        except Exception as exc:
            # Non-fatal: agent still works, we just won't get post-call webhooks
            logger.warning(
                "agent.webhook_inject_update_failed",
                workflow_id=workflow_id,
                error=str(exc),
            )
