from __future__ import annotations

from pydantic import BaseModel, Field


# ── Upload flow ────────────────────────────────────────────────────────────────

class KBUploadUrlRequest(BaseModel):
    """Request a presigned S3 URL from Dograh for direct browser upload."""

    filename: str = Field(..., description="Name of the file to upload")
    mime_type: str = Field(..., description="MIME type of the file (e.g. application/pdf)")


class KBUploadUrlResponse(BaseModel):
    """Presigned S3 URL + document identifiers returned after requesting an upload URL."""

    upload_url: str = Field(..., description="Presigned PUT URL — browser uploads the file here directly")
    document_uuid: str = Field(..., description="UUID for this document — pass to /process after upload")
    s3_key: str = Field(..., description="S3 key — pass to /process after upload")


class KBProcessRequest(BaseModel):
    """Trigger Dograh to chunk and embed a document that was uploaded to S3."""

    document_uuid: str = Field(..., description="UUID returned by /upload-url")
    s3_key: str = Field(..., description="S3 key returned by /upload-url")
    retrieval_mode: str = Field(
        "chunked",
        description="'chunked' for vector search (default) or 'full_document' for full text retrieval",
    )


# ── Document model ─────────────────────────────────────────────────────────────

class KBDocument(BaseModel):
    """A knowledge base document as returned by Dograh."""

    document_uuid: str
    filename: str
    file_size_bytes: int
    mime_type: str
    processing_status: str = Field(
        description="'pending' | 'processing' | 'completed' | 'failed'"
    )
    processing_error: str | None = None
    total_chunks: int = 0
    retrieval_mode: str = "chunked"
    created_at: str
    updated_at: str | None = None


class KBDocumentListResponse(BaseModel):
    documents: list[KBDocument]
    total: int
    limit: int
    offset: int


# ── Phase 2 — Agent attachment ─────────────────────────────────────────────────

class KBAgentDocumentsRequest(BaseModel):
    """Set the list of document UUIDs attached to an agent."""

    document_uuids: list[str] = Field(
        default_factory=list,
        description="Full list of document UUIDs to attach. Empty list detaches all.",
    )


class KBAgentDocumentsResponse(BaseModel):
    workflow_id: int
    document_uuids: list[str]
    message: str = "Documents updated"


# ── Phase 3 — Search ───────────────────────────────────────────────────────────

class KBSearchRequest(BaseModel):
    """Search knowledge base documents using vector similarity."""

    query: str = Field(..., description="Natural language search query")
    limit: int = Field(5, ge=1, le=20, description="Max results to return")
    document_uuids: list[str] | None = Field(
        None,
        description="Filter to specific documents. None = search all org documents.",
    )


class KBSearchResult(BaseModel):
    document_uuid: str
    filename: str
    chunk_text: str
    similarity_score: float


class KBSearchResponse(BaseModel):
    results: list[KBSearchResult]
    query: str
