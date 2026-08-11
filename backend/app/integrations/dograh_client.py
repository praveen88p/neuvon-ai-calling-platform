from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.logging import logger


class DograhClient:
    """Async HTTP client for all Dograh API communication.

    All Dograh communication goes through this class — never call Dograh
    directly from services or routes. Uses HTTPX async client with
    X-API-Key header authentication.
    """

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.base_url = settings.DOGRAH_BASE_URL
        self.api_key = api_key or settings.DOGRAH_API_KEY

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make authenticated request to Dograh API."""
        url = f"{self.base_url}/api/v1{path}"
        logger.info("dograh.request", method=method, path=path)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                headers={"X-API-Key": self.api_key},
                **kwargs,
            )
            if response.status_code >= 400:
                body = response.text[:500]
                logger.error(
                    "dograh.error_response",
                    method=method,
                    path=path,
                    status=response.status_code,
                    body=body,
                )
                raise httpx.HTTPStatusError(
                    f"Dograh {method} {path} returned {response.status_code}: {body}",
                    request=response.request,
                    response=response,
                )
            return response.json()

    async def _request_raw(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make authenticated request returning raw response (for multipart, etc.)."""
        url = f"{self.base_url}/api/v1{path}"
        logger.info("dograh.request_raw", method=method, path=path)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method,
                url,
                headers={"X-API-Key": self.api_key},
                **kwargs,
            )
            response.raise_for_status()
            return response

    # --- Agent methods (Feature 05) ---

    async def list_agents(self) -> dict:
        """GET /workflow/fetch — list all agents."""
        return await self._request("GET", "/workflow/fetch")

    async def get_agent(self, workflow_id: int) -> dict:
        """GET /workflow/fetch/{workflow_id} — get agent with full definition."""
        return await self._request("GET", f"/workflow/fetch/{workflow_id}")

    async def get_agent_count(self) -> dict:
        """GET /workflow/count — agent count by status."""
        return await self._request("GET", "/workflow/count")

    async def create_agent_from_definition(
        self, name: str, workflow_definition: dict
    ) -> dict:
        """POST /workflow/create/definition — create from explicit node/edge definition."""
        return await self._request(
            "POST",
            "/workflow/create/definition",
            json={"name": name, "workflow_definition": workflow_definition},
        )

    async def create_agent_from_template(
        self, name: str, call_type: str, use_case: str, activity_description: str
    ) -> dict:
        """POST /workflow/create/template — create from natural language description."""
        return await self._request(
            "POST",
            "/workflow/create/template",
            json={
                "name": name,
                "call_type": call_type,
                "use_case": use_case,
                "activity_description": activity_description,
            },
        )

    async def update_agent(self, workflow_id: int, data: dict) -> dict:
        """PUT /workflow/{workflow_id} — update agent name, definition, or config."""
        return await self._request("PUT", f"/workflow/{workflow_id}", json=data)

    async def update_agent_status(
        self, workflow_id: int, status: str
    ) -> dict:
        """PUT /workflow/{workflow_id}/status — archive or restore."""
        return await self._request(
            "PUT", f"/workflow/{workflow_id}/status", json={"status": status}
        )

    async def validate_agent(self, workflow_id: int) -> dict:
        """POST /workflow/{workflow_id}/validate — validate without executing."""
        return await self._request("POST", f"/workflow/{workflow_id}/validate")

    async def create_test_run(self, workflow_id: int, data: dict | None = None) -> dict:
        """POST /workflow/{workflow_id}/runs — create a test run.

        Dograh requires `mode` and `name` in the body (confirmed by live API test:
        sending {} returns 422 with 'mode' and 'name' as required fields).
        """
        body: dict = {"mode": "test", **(data or {})}
        if "name" not in body:
            body["name"] = "Test Run"
        return await self._request(
            "POST", f"/workflow/{workflow_id}/runs", json=body
        )

    async def list_workflow_runs(
        self, workflow_id: int, params: dict | None = None
    ) -> dict:
        """GET /workflow/{workflow_id}/runs — list runs for a workflow."""
        return await self._request(
            "GET", f"/workflow/{workflow_id}/runs", params=params
        )

    # --- Call methods (Feature 06) ---

    async def trigger_call(
        self,
        workflow_uuid: str,
        phone_number: str,
        initial_context: dict | None = None,
        telephony_configuration_id: int | None = None,
    ) -> dict:
        """POST /public/agent/workflow/{uuid} — trigger outbound call by Agent UUID."""
        body: dict = {"phone_number": phone_number}
        if initial_context:
            body["initial_context"] = initial_context
        if telephony_configuration_id:
            body["telephony_configuration_id"] = telephony_configuration_id
        return await self._request(
            "POST", f"/public/agent/workflow/{workflow_uuid}", json=body
        )

    async def get_run(self, workflow_id: int, run_id: int) -> dict:
        """GET /workflow/{id}/runs/{run_id} — get run details."""
        return await self._request("GET", f"/workflow/{workflow_id}/runs/{run_id}")

    async def list_runs(self, params: dict | None = None) -> dict:
        """GET /organizations/usage/runs — paginated run list with usage data."""
        return await self._request("GET", "/organizations/usage/runs", params=params)

    async def ensure_webhook_node(self, workflow_id: int, webhook_url: str) -> bool:
        """Inject or update a webhook node in a Dograh agent's workflow definition.

        Fetches the current workflow, checks if a webhook node pointing to our
        backend already exists, and if not adds one. This is idempotent — calling
        it multiple times is safe.

        Returns True if the webhook was added/updated, False if already present.
        """
        import uuid as _uuid

        try:
            agent = await self.get_agent(workflow_id)
            wf_def = agent.get("workflow_definition") or {}
            nodes: list = wf_def.get("nodes", [])
            edges: list = wf_def.get("edges", [])

            neuvon_marker = "neuvon-webhook"

            # Check if our webhook node already exists and is current
            for node in nodes:
                if (
                    node.get("type") == "webhook"
                    and node.get("id", "").startswith(neuvon_marker)
                ):
                    existing_url = node.get("data", {}).get("endpoint_url", "")
                    if existing_url == webhook_url:
                        logger.info(
                            "dograh.webhook_node_exists",
                            workflow_id=workflow_id,
                            url=webhook_url,
                        )
                        return False  # Already configured correctly
                    # URL changed — remove old node and edge, then re-add
                    old_id = node["id"]
                    nodes = [n for n in nodes if n["id"] != old_id]
                    edges = [e for e in edges if e.get("source") != old_id and e.get("target") != old_id]
                    break

            # Find all endCall nodes to connect webhook before them
            end_nodes = [n for n in nodes if n.get("type") == "endCall"]

            webhook_node_id = f"{neuvon_marker}-{str(_uuid.uuid4())[:8]}"
            webhook_node = {
                "id": webhook_node_id,
                "type": "webhook",
                "position": {"x": 900, "y": 0},
                "data": {
                    "name": "Neuvon Result Webhook",
                    "enabled": True,
                    "http_method": "POST",
                    "endpoint_url": webhook_url,
                    "payload_template": {
                        "run_id": "{{workflow_run_id}}",
                        "workflow_id": "{{workflow_id}}",
                        "status": "completed",
                        "duration_seconds": "{{cost_info.call_duration_seconds}}",
                        "gathered_context": "{{gathered_context}}",
                        "recording_url": "{{recording_url}}",
                        "transcript_url": "{{transcript_url}}",
                    },
                },
            }
            nodes.append(webhook_node)

            # Add edges: each endCall → webhook node
            for end_node in end_nodes:
                edge_id = f"edge-neuvon-{str(_uuid.uuid4())[:8]}"
                edges.append({
                    "id": edge_id,
                    "source": end_node["id"],
                    "target": webhook_node_id,
                    "data": {
                        "label": "Call ended",
                        "condition": "The call has ended",
                    },
                })

            updated_def = {"nodes": nodes, "edges": edges}
            await self.update_agent(workflow_id, {"workflow_definition": updated_def})

            logger.info(
                "dograh.webhook_node_added",
                workflow_id=workflow_id,
                url=webhook_url,
            )
            return True

        except Exception as exc:
            logger.warning(
                "dograh.webhook_node_failed",
                workflow_id=workflow_id,
                error=str(exc),
            )
            return False

    # --- Campaign methods (Feature 08) ---

    async def get_presigned_upload_url(
        self, file_name: str, file_size: int, content_type: str = "text/csv"
    ) -> dict:
        """POST /s3/presigned-upload-url — get S3 presigned URL for CSV upload."""
        return await self._request(
            "POST",
            "/s3/presigned-upload-url",
            json={
                "file_name": file_name,
                "file_size": file_size,
                "content_type": content_type,
            },
        )

    async def upload_to_s3(
        self, upload_url: str, file_content: bytes, content_type: str = "text/csv"
    ) -> None:
        """PUT file content directly to the S3 presigned URL."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.put(
                upload_url,
                content=file_content,
                headers={"Content-Type": content_type},
            )
            response.raise_for_status()

    async def create_campaign(self, data: dict) -> dict:
        """POST /campaign/create — create a campaign linked to a workflow and uploaded CSV."""
        return await self._request("POST", "/campaign/create", json=data)

    async def list_campaigns(self) -> dict:
        """GET /campaign/fetch — list all campaigns."""
        return await self._request("GET", "/campaign/fetch")

    async def get_campaign(self, campaign_id: int) -> dict:
        """GET /campaign/fetch/{campaign_id} — get a single campaign."""
        return await self._request("GET", f"/campaign/fetch/{campaign_id}")

    async def update_campaign(self, campaign_id: int, data: dict) -> dict:
        """PUT /campaign/{campaign_id} — update campaign settings."""
        return await self._request("PUT", f"/campaign/{campaign_id}", json=data)

    async def start_campaign(self, campaign_id: int) -> dict:
        """POST /campaign/{campaign_id}/start — start dialing contacts."""
        return await self._request("POST", f"/campaign/{campaign_id}/start")

    async def pause_campaign(self, campaign_id: int) -> dict:
        """POST /campaign/{campaign_id}/pause — pause a running campaign."""
        return await self._request("POST", f"/campaign/{campaign_id}/pause")

    async def resume_campaign(self, campaign_id: int) -> dict:
        """POST /campaign/{campaign_id}/resume — resume a paused campaign."""
        return await self._request("POST", f"/campaign/{campaign_id}/resume")

    async def get_campaign_progress(self, campaign_id: int) -> dict:
        """GET /campaign/{campaign_id}/progress — get current progress stats."""
        return await self._request("GET", f"/campaign/{campaign_id}/progress")

    async def get_campaign_runs(self, campaign_id: int) -> dict:
        """GET /campaign/{campaign_id}/runs — get run records for contacts."""
        return await self._request("GET", f"/campaign/{campaign_id}/runs")

    # --- Telephony methods (Feature 11) ---

    async def get_telephony_providers(self) -> dict:
        """GET /organizations/telephony-providers/metadata — supported providers."""
        return await self._request("GET", "/organizations/telephony-providers/metadata")

    async def list_telephony_configs(self) -> dict:
        """GET /organizations/telephony-configs — list all configs."""
        return await self._request("GET", "/organizations/telephony-configs")

    async def create_telephony_config(self, data: dict) -> dict:
        """POST /organizations/telephony-configs — create a config.

        Dograh expects:
        {
            "name": "My Vobiz Account",
            "is_default_outbound": false,
            "config": {
                "provider": "vobiz",
                "auth_id": "...",
                "auth_token": "...",
                "application_id": null    # optional — auto-created if empty
            }
        }
        """
        provider = data.get("provider", "")
        credentials = data.get("credentials", {})
        payload = {
            "name": data.get("name", ""),
            "is_default_outbound": data.get("is_default_outbound", False),
            "config": {
                "provider": provider,
                **credentials,
            },
        }
        return await self._request("POST", "/organizations/telephony-configs", json=payload)

    async def get_telephony_config(self, config_id: int) -> dict:
        """GET /organizations/telephony-configs/{config_id}."""
        return await self._request("GET", f"/organizations/telephony-configs/{config_id}")

    async def update_telephony_config(self, config_id: int, data: dict) -> dict:
        """PUT /organizations/telephony-configs/{config_id}."""
        return await self._request("PUT", f"/organizations/telephony-configs/{config_id}", json=data)

    async def delete_telephony_config(self, config_id: int) -> dict:
        """DELETE /organizations/telephony-configs/{config_id}."""
        return await self._request("DELETE", f"/organizations/telephony-configs/{config_id}")

    async def set_default_outbound(self, config_id: int) -> dict:
        """POST /organizations/telephony-configs/{config_id}/set-default-outbound."""
        return await self._request(
            "POST", f"/organizations/telephony-configs/{config_id}/set-default-outbound",
        )

    # --- Phone Number methods (Feature 11) ---

    async def list_phone_numbers(self, config_id: int) -> dict:
        """GET /organizations/telephony-configs/{config_id}/phone-numbers."""
        return await self._request(
            "GET", f"/organizations/telephony-configs/{config_id}/phone-numbers",
        )

    async def add_phone_number(self, config_id: int, data: dict) -> dict:
        """POST /organizations/telephony-configs/{config_id}/phone-numbers.

        Dograh's API uses `inbound_workflow_id` in both GET responses and PUT/POST bodies.
        Send data as-is — no field name translation needed.
        """
        return await self._request(
            "POST", f"/organizations/telephony-configs/{config_id}/phone-numbers", json=data,
        )

    async def get_phone_number(self, config_id: int, phone_number_id: int) -> dict:
        """GET .../phone-numbers/{phone_number_id}."""
        return await self._request(
            "GET", f"/organizations/telephony-configs/{config_id}/phone-numbers/{phone_number_id}",
        )

    async def update_phone_number(self, config_id: int, phone_number_id: int, data: dict) -> dict:
        """PUT .../phone-numbers/{phone_number_id}.

        Dograh's API uses `inbound_workflow_id` in both GET responses and PUT bodies.
        Confirmed by live API test: sending `inbound_workflow` is silently ignored;
        sending `inbound_workflow_id` saves correctly and updates `updated_at`.
        Send data as-is — no field name translation needed.
        """
        return await self._request(
            "PUT", f"/organizations/telephony-configs/{config_id}/phone-numbers/{phone_number_id}",
            json=data,
        )

    async def delete_phone_number(self, config_id: int, phone_number_id: int) -> dict:
        """DELETE .../phone-numbers/{phone_number_id}."""
        return await self._request(
            "DELETE", f"/organizations/telephony-configs/{config_id}/phone-numbers/{phone_number_id}",
        )

    async def set_default_caller(self, config_id: int, phone_number_id: int) -> dict:
        """POST .../phone-numbers/{phone_number_id}/set-default-caller."""
        return await self._request(
            "POST",
            f"/organizations/telephony-configs/{config_id}/phone-numbers/{phone_number_id}/set-default-caller",
        )

    # ── Outbound Call Trigger ─────────────────────────────────────────────

    async def trigger_outbound_call(
        self,
        workflow_uuid: str,
        phone_number: str,
        initial_context: dict | None = None,
    ) -> dict:
        """POST /public/agent/workflow/{workflow_uuid} — trigger a real outbound call.

        This is provider-agnostic: Dograh routes through whatever telephony
        provider (Plivo, Twilio, Vobiz, etc.) is configured on the agent.

        NOTE: The path is /public/agent/workflow/{uuid}, NOT /public/agent/{uuid}.
        The existing trigger_call method uses the same path and is verified working.
        """
        body: dict = {"phone_number": phone_number}
        if initial_context:
            body["initial_context"] = initial_context
        return await self._request(
            "POST", f"/public/agent/workflow/{workflow_uuid}", json=body
        )

    # --- Knowledge Base methods (Feature KB) ---

    async def kb_get_upload_url(self, filename: str, mime_type: str) -> dict:
        """POST /knowledge-base/upload-url — get presigned S3 URL for direct browser upload.

        Returns: { upload_url, document_uuid, s3_key }
        """
        return await self._request(
            "POST",
            "/knowledge-base/upload-url",
            json={"filename": filename, "mime_type": mime_type},
        )

    async def kb_process_document(
        self,
        document_uuid: str,
        s3_key: str,
        retrieval_mode: str = "chunked",
    ) -> dict:
        """POST /knowledge-base/process-document — trigger chunking + embedding after S3 upload.

        Status will move: pending → processing → completed | failed (async).
        """
        return await self._request(
            "POST",
            "/knowledge-base/process-document",
            json={
                "document_uuid": document_uuid,
                "s3_key": s3_key,
                "retrieval_mode": retrieval_mode,
            },
        )

    async def kb_list_documents(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
    ) -> dict:
        """GET /knowledge-base/documents — list all documents for the authenticated org."""
        params: dict = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        return await self._request("GET", "/knowledge-base/documents", params=params)

    async def kb_get_document(self, document_uuid: str) -> dict:
        """GET /knowledge-base/documents/{uuid} — get a single document's details."""
        return await self._request("GET", f"/knowledge-base/documents/{document_uuid}")

    async def kb_delete_document(self, document_uuid: str) -> None:
        """DELETE /knowledge-base/documents/{uuid} — soft-delete a document and its chunks."""
        await self._request("DELETE", f"/knowledge-base/documents/{document_uuid}")

    async def kb_search(
        self,
        query: str,
        limit: int = 5,
        document_uuids: list[str] | None = None,
    ) -> dict:
        """POST /knowledge-base/search — vector similarity search across org documents."""
        body: dict = {"query": query, "limit": limit}
        if document_uuids:
            body["document_uuids"] = document_uuids
        return await self._request("POST", "/knowledge-base/search", json=body)

    # --- Agent ↔ Document methods (Phase 2) ---

    async def get_agent_document_uuids(self, workflow_id: int) -> list[str]:
        """Read document_uuids from an agent's agentNodes.

        Fetches the full workflow definition and extracts document_uuids
        from the first agentNode found (they are expected to be consistent
        across all agentNodes in a workflow).
        """
        agent = await self.get_agent(workflow_id)
        definition = agent.get("workflow_definition") or {}
        nodes = definition.get("nodes") or []
        for node in nodes:
            if node.get("type") == "agentNode":
                return node.get("data", {}).get("document_uuids") or []
        return []

    async def set_agent_document_uuids(
        self, workflow_id: int, document_uuids: list[str]
    ) -> dict:
        """Update document_uuids on ALL agentNodes in a workflow.

        Documents attached here are available throughout the entire conversation.
        Fetches current definition, updates every agentNode, then PUTs the workflow.
        """
        agent = await self.get_agent(workflow_id)
        definition = agent.get("workflow_definition") or {}
        nodes = definition.get("nodes") or []
        edges = definition.get("edges") or []

        for node in nodes:
            if node.get("type") == "agentNode":
                node.setdefault("data", {})["document_uuids"] = document_uuids

        return await self.update_agent(
            workflow_id,
            {"workflow_definition": {"nodes": nodes, "edges": edges}},
        )

