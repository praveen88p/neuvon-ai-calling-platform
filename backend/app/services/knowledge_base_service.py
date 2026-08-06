from __future__ import annotations

from fastapi import HTTPException, status

from app.core.logging import logger
from app.integrations.dograh_client import DograhClient
from app.integrations.insforge_client import get_insforge_admin
from app.schemas.auth import UserContext
from app.schemas.knowledge_base import (
    KBDocument,
    KBDocumentListResponse,
    KBSearchResponse,
    KBSearchResult,
    KBUploadUrlResponse,
)


class KnowledgeBaseService:
    """Knowledge base operations scoped per organization.

    ISOLATION PATTERN (matches AgentService / dograh_agent_mappings):
    - Dograh uses a single shared API key — all org documents live in one account.
    - We keep a local `kb_document_mappings` table: { document_uuid, organization_id }.
    - On list  → fetch our mappings for org → filter Dograh docs to those UUIDs only.
    - On upload → upload to Dograh → INSERT mapping { document_uuid, org_id }.
    - On delete → delete from Dograh → DELETE mapping.
    - On search → get org's UUIDs from mapping → pass as filter to Dograh search.
    """

    def __init__(self) -> None:
        self.dograh = DograhClient()
        self.db = get_insforge_admin()

    # ── Upload flow ────────────────────────────────────────────────────────────

    async def get_upload_url(
        self,
        filename: str,
        mime_type: str,
    ) -> KBUploadUrlResponse:
        """Request a presigned S3 URL from Dograh for direct file upload."""
        try:
            result = await self.dograh.kb_get_upload_url(filename, mime_type)
        except Exception as exc:
            logger.error("kb.upload_url_failed", filename=filename, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to get upload URL from document service",
            ) from exc

        logger.info("kb.upload_url_issued", filename=filename)
        return KBUploadUrlResponse(
            upload_url=result["upload_url"],
            document_uuid=result["document_uuid"],
            s3_key=result["s3_key"],
        )

    async def process_document(
        self,
        document_uuid: str,
        s3_key: str,
        retrieval_mode: str,
        current_user: UserContext,
        # Metadata to persist in our mapping table
        filename: str = "",
        file_size_bytes: int = 0,
        mime_type: str = "",
    ) -> KBDocument:
        """Trigger Dograh to chunk + embed an uploaded document, then store mapping.

        Stores { document_uuid, organization_id } in kb_document_mappings so that
        future list/get/delete calls are scoped to this org only.
        """
        try:
            result = await self.dograh.kb_process_document(
                document_uuid, s3_key, retrieval_mode
            )
        except Exception as exc:
            logger.error(
                "kb.process_failed",
                document_uuid=document_uuid,
                org_id=current_user.organization_id,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to trigger document processing",
            ) from exc

        # Store the mapping — this is how we enforce org isolation
        await self._create_mapping(
            document_uuid=document_uuid,
            org_id=current_user.organization_id,
            filename=filename or result.get("filename", ""),
            file_size_bytes=file_size_bytes or result.get("file_size_bytes", 0),
            mime_type=mime_type or result.get("mime_type", ""),
            retrieval_mode=retrieval_mode,
        )

        logger.info(
            "kb.processing_started",
            document_uuid=document_uuid,
            org_id=current_user.organization_id,
            retrieval_mode=retrieval_mode,
        )
        return self._parse_document(result)

    # ── List & get ─────────────────────────────────────────────────────────────

    async def list_documents(
        self,
        current_user: UserContext,
        limit: int = 100,
        offset: int = 0,
        status_filter: str | None = None,
    ) -> KBDocumentListResponse:
        """List org's documents — scoped via kb_document_mappings."""
        # 1. Get this org's document UUIDs from our mapping table
        org_uuids = await self._get_org_document_uuids(current_user.organization_id)

        if not org_uuids:
            return KBDocumentListResponse(
                documents=[], total=0, limit=limit, offset=offset
            )

        # 2. Fetch documents from Dograh — max limit per request is 100, paginate to get all
        all_docs: list[dict] = []
        page_size = 100
        page_offset = 0
        try:
            while True:
                result = await self.dograh.kb_list_documents(
                    limit=page_size, offset=page_offset, status=status_filter
                )
                page_docs = result.get("documents", [])
                all_docs.extend(page_docs)
                # Stop if we've received fewer docs than requested (last page)
                if len(page_docs) < page_size:
                    break
                page_offset += page_size
        except Exception as exc:
            logger.error(
                "kb.list_failed",
                org_id=current_user.organization_id,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch documents",
            ) from exc

        org_docs = [
            d for d in all_docs if d.get("document_uuid") in org_uuids
        ]

        # 4. Apply pagination
        paginated = org_docs[offset: offset + limit]

        return KBDocumentListResponse(
            documents=[self._parse_document(d) for d in paginated],
            total=len(org_docs),
            limit=limit,
            offset=offset,
        )

    async def get_document(
        self, document_uuid: str, current_user: UserContext
    ) -> KBDocument:
        """Get a single document — verifies org ownership first."""
        await self._verify_org_access(document_uuid, current_user)

        try:
            result = await self.dograh.kb_get_document(document_uuid)
        except Exception as exc:
            logger.error(
                "kb.get_failed",
                document_uuid=document_uuid,
                org_id=current_user.organization_id,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            ) from exc

        return self._parse_document(result)

    # ── Delete ─────────────────────────────────────────────────────────────────

    async def delete_document(
        self, document_uuid: str, current_user: UserContext
    ) -> None:
        """Delete document from Dograh + remove from org mapping."""
        # Verify ownership before deleting
        await self._verify_org_access(document_uuid, current_user)

        try:
            await self.dograh.kb_delete_document(document_uuid)
        except Exception as exc:
            logger.error(
                "kb.delete_failed",
                document_uuid=document_uuid,
                org_id=current_user.organization_id,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to delete document",
            ) from exc

        # Remove from our mapping table
        await self._delete_mapping(document_uuid, current_user.organization_id)

        logger.info(
            "kb.document_deleted",
            document_uuid=document_uuid,
            org_id=current_user.organization_id,
        )

    # ── Search ─────────────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        current_user: UserContext,
        limit: int = 5,
        document_uuids: list[str] | None = None,
    ) -> KBSearchResponse:
        """Vector search — scoped to org's own documents only."""
        # Get org's document UUIDs; optionally narrow further by caller
        org_uuids = await self._get_org_document_uuids(current_user.organization_id)

        if not org_uuids:
            return KBSearchResponse(results=[], query=query)

        # Intersect with any caller-supplied filter
        search_uuids: list[str] | None = list(org_uuids)
        if document_uuids:
            search_uuids = [u for u in document_uuids if u in org_uuids]

        try:
            result = await self.dograh.kb_search(
                query=query, limit=limit, document_uuids=search_uuids
            )
        except Exception as exc:
            logger.error(
                "kb.search_failed",
                query=query[:50],
                org_id=current_user.organization_id,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Search failed",
            ) from exc

        raw_results = result.get(
            "results", result if isinstance(result, list) else []
        )
        parsed = [
            KBSearchResult(
                document_uuid=r.get("document_uuid", ""),
                filename=r.get("filename", r.get("document_filename", "")),
                chunk_text=r.get("chunk_text", r.get("text", "")),
                similarity_score=float(
                    r.get("similarity_score", r.get("score", 0))
                ),
            )
            for r in raw_results
        ]

        return KBSearchResponse(results=parsed, query=query)

    # ── Private helpers (same pattern as AgentService) ─────────────────────────

    async def _get_org_document_uuids(self, org_id: str) -> set[str]:
        """Return the set of document_uuids owned by this org."""
        try:
            rows = (
                await self.db.database.from_("kb_document_mappings")
                .select("document_uuid")
                .eq("organization_id", org_id)
                .execute()
            )
            rows = rows if isinstance(rows, list) else []
            return {r["document_uuid"] for r in rows}
        except Exception as exc:
            logger.error(
                "kb.mapping_fetch_failed", org_id=org_id, error=str(exc)
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch document mappings",
            ) from exc

    async def _verify_org_access(
        self, document_uuid: str, current_user: UserContext
    ) -> None:
        """Raise 404 if document_uuid is not owned by current org."""
        try:
            rows = (
                await self.db.database.from_("kb_document_mappings")
                .select("id")
                .eq("document_uuid", document_uuid)
                .eq("organization_id", current_user.organization_id)
                .execute()
            )
            rows = rows if isinstance(rows, list) else []
        except Exception as exc:
            logger.error(
                "kb.access_check_failed",
                document_uuid=document_uuid,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify document access",
            ) from exc

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found in this organization",
            )

    async def _create_mapping(
        self,
        document_uuid: str,
        org_id: str,
        filename: str,
        file_size_bytes: int,
        mime_type: str,
        retrieval_mode: str,
    ) -> None:
        """Insert a document-to-org mapping (called after successful upload).

        Uses the same insert pattern as AgentService._create_mapping:
        await db.from_(...).insert([{...}])  — no .execute() on insert.
        """
        try:
            await self.db.database.from_("kb_document_mappings").insert([{
                "organization_id": org_id,
                "document_uuid": document_uuid,
                "filename": filename,
                "file_size_bytes": file_size_bytes,
                "mime_type": mime_type,
                "retrieval_mode": retrieval_mode,
            }])
        except Exception as exc:
            logger.error(
                "kb.mapping_create_failed",
                document_uuid=document_uuid,
                org_id=org_id,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Document uploaded but failed to save mapping. Please contact support.",
            ) from exc

    async def _delete_mapping(self, document_uuid: str, org_id: str) -> None:
        """Remove a document-to-org mapping (called on delete).

        Uses same delete pattern as availability_service — no .execute(),
        handles InsForge SDK bug where delete returns empty body (JSONDecodeError).
        """
        import json
        try:
            await self.db.database.from_("kb_document_mappings") \
                .eq("document_uuid", document_uuid) \
                .eq("organization_id", org_id) \
                .delete()
        except json.JSONDecodeError:
            pass  # InsForge SDK bug: delete returns empty body — this is OK
        except Exception as exc:
            logger.error(
                "kb.mapping_delete_failed",
                document_uuid=document_uuid,
                org_id=org_id,
                error=str(exc),
            )

    # ── Parser ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_document(data: dict) -> KBDocument:
        return KBDocument(
            document_uuid=data.get("document_uuid", ""),
            filename=data.get("filename", ""),
            file_size_bytes=data.get("file_size_bytes", 0),
            mime_type=data.get("mime_type", ""),
            processing_status=data.get("processing_status", "pending"),
            processing_error=data.get("processing_error"),
            total_chunks=data.get("total_chunks", 0),
            retrieval_mode=data.get("retrieval_mode", "full_document"),
            created_at=str(data.get("created_at", "")),
            updated_at=(
                str(data.get("updated_at", "")) if data.get("updated_at") else None
            ),
        )
