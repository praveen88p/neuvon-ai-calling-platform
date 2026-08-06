from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.core.dependencies import get_current_user
from app.core.logging import logger
from app.schemas.auth import UserContext
from app.schemas.knowledge_base import (
    KBAgentDocumentsRequest,
    KBAgentDocumentsResponse,
    KBDocument,
    KBDocumentListResponse,
    KBProcessRequest,
    KBSearchRequest,
    KBSearchResponse,
    KBUploadUrlRequest,
    KBUploadUrlResponse,
)
from app.services.knowledge_base_service import KnowledgeBaseService

router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])


# ── Combined single-step upload (browser-friendly) ─────────────────────────────

@router.post("/upload", response_model=KBDocument)
async def upload_document(
    file: UploadFile = File(...),
    retrieval_mode: str = Query("full_document", pattern="^(full_document|chunked)$"),
    current_user: UserContext = Depends(get_current_user),
) -> KBDocument:
    """Upload a file to the org's knowledge base in one step.

    Flow: get presigned S3 URL → PUT to S3 server-side → trigger processing →
    store org mapping. Org isolation enforced via kb_document_mappings table.

    Args:
        retrieval_mode: 'full_document' — whole doc on each retrieval (FAQs, small docs);
                        'chunked' — split into chunks, most relevant retrieved (large docs).
    """
    service = KnowledgeBaseService()

    # 1. Get presigned S3 URL from Dograh
    url_resp = await service.get_upload_url(
        filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
    )

    # 2. Read file content
    content = await file.read()

    # 3. PUT to S3 server-side (no browser CORS issue)
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            s3_resp = await client.put(
                url_resp.upload_url,
                content=content,
                headers={"Content-Type": file.content_type or "application/octet-stream"},
            )
            s3_resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "kb.s3_upload_failed",
            filename=file.filename,
            org_id=current_user.organization_id,
            status=exc.response.status_code,
            body=exc.response.text[:200],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload file to storage",
        ) from exc
    except Exception as exc:
        logger.error(
            "kb.s3_upload_error",
            filename=file.filename,
            org_id=current_user.organization_id,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Storage upload failed",
        ) from exc

    logger.info(
        "kb.s3_upload_ok",
        filename=file.filename,
        org_id=current_user.organization_id,
        size_bytes=len(content),
        document_uuid=url_resp.document_uuid,
        retrieval_mode=retrieval_mode,
    )

    # 4. Trigger Dograh processing + store org mapping
    return await service.process_document(
        document_uuid=url_resp.document_uuid,
        s3_key=url_resp.s3_key,
        retrieval_mode=retrieval_mode,
        current_user=current_user,
        filename=file.filename or "upload",
        file_size_bytes=len(content),
        mime_type=file.content_type or "application/octet-stream",
    )


# ── List & get ─────────────────────────────────────────────────────────────────

@router.get("/documents", response_model=KBDocumentListResponse)
async def list_documents(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    doc_status: str | None = Query(None, alias="status"),
    current_user: UserContext = Depends(get_current_user),
) -> KBDocumentListResponse:
    """List knowledge base documents for the authenticated organization only.

    Returns only documents owned by this org (enforced via kb_document_mappings).
    """
    service = KnowledgeBaseService()
    return await service.list_documents(
        current_user=current_user,
        limit=limit,
        offset=offset,
        status_filter=doc_status,
    )


@router.get("/documents/{document_uuid}", response_model=KBDocument)
async def get_document(
    document_uuid: str,
    current_user: UserContext = Depends(get_current_user),
) -> KBDocument:
    """Get details of a single document. Used for status polling after upload."""
    service = KnowledgeBaseService()
    return await service.get_document(document_uuid, current_user)


@router.delete("/documents/{document_uuid}", status_code=204)
async def delete_document(
    document_uuid: str,
    current_user: UserContext = Depends(get_current_user),
) -> None:
    """Delete a document from the org's knowledge base."""
    service = KnowledgeBaseService()
    await service.delete_document(document_uuid, current_user)


# ── Search ─────────────────────────────────────────────────────────────────────

@router.post("/search", response_model=KBSearchResponse)
async def search_documents(
    data: KBSearchRequest,
    current_user: UserContext = Depends(get_current_user),
) -> KBSearchResponse:
    """Vector similarity search — org-scoped only."""
    service = KnowledgeBaseService()
    return await service.search(
        query=data.query,
        current_user=current_user,
        limit=data.limit,
        document_uuids=data.document_uuids,
    )


# ── Legacy split-upload endpoints (for admin/programmatic use) ─────────────────

@router.post("/upload-url", response_model=KBUploadUrlResponse)
async def get_upload_url(
    data: KBUploadUrlRequest,
    current_user: UserContext = Depends(get_current_user),
) -> KBUploadUrlResponse:
    """Get presigned S3 URL. Advanced use — prefer POST /upload instead."""
    service = KnowledgeBaseService()
    return await service.get_upload_url(data.filename, data.mime_type)


@router.post("/process", response_model=KBDocument)
async def process_document(
    data: KBProcessRequest,
    current_user: UserContext = Depends(get_current_user),
) -> KBDocument:
    """Trigger processing after manual S3 upload. Stores org mapping."""
    service = KnowledgeBaseService()
    return await service.process_document(
        document_uuid=data.document_uuid,
        s3_key=data.s3_key,
        retrieval_mode=data.retrieval_mode,
        current_user=current_user,
    )


# ── Agent ↔ Document attachment (admin use only) ───────────────────────────────

@router.get("/agents/{workflow_id}/documents", response_model=KBAgentDocumentsResponse)
async def get_agent_documents(
    workflow_id: int,
    current_user: UserContext = Depends(get_current_user),
) -> KBAgentDocumentsResponse:
    """Get document UUIDs attached to an agent (admin use)."""
    from app.integrations.dograh_client import DograhClient
    dograh = DograhClient()
    uuids = await dograh.get_agent_document_uuids(workflow_id)
    return KBAgentDocumentsResponse(
        workflow_id=workflow_id,
        document_uuids=uuids,
        message="Documents fetched",
    )


@router.put("/agents/{workflow_id}/documents", response_model=KBAgentDocumentsResponse)
async def update_agent_documents(
    workflow_id: int,
    data: KBAgentDocumentsRequest,
    current_user: UserContext = Depends(get_current_user),
) -> KBAgentDocumentsResponse:
    """Attach/detach documents from an agent (admin use). Pass full list of UUIDs."""
    from app.integrations.dograh_client import DograhClient
    dograh = DograhClient()
    await dograh.set_agent_document_uuids(workflow_id, data.document_uuids)
    logger.info(
        "kb.agent_docs_updated",
        workflow_id=workflow_id,
        org_id=current_user.organization_id,
        doc_count=len(data.document_uuids),
    )
    return KBAgentDocumentsResponse(
        workflow_id=workflow_id,
        document_uuids=data.document_uuids,
        message=f"Attached {len(data.document_uuids)} document(s) to agent",
    )
