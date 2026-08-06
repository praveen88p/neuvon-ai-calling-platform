import { useState, useEffect, useCallback } from "react";
import {
  BookOpen,
  Plus,
  Search,
  Loader2,
  FileText,
  Sparkles,
  AlertCircle,
  Send,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { useApiQuery } from "@/hooks/useApiQuery";
import { apiPost } from "@/utils/api";
import { API_PATHS } from "@/utils/apiPaths";
import { DocumentCard, type KBDocument } from "@/components/knowledge-base/DocumentCard";
import { UploadDocumentModal } from "@/components/knowledge-base/UploadDocumentModal";

// ─── Types ────────────────────────────────────────────────────────────────────

interface KBDocumentListResponse {
  documents: KBDocument[];
  total: number;
}

interface KBSearchResult {
  document_uuid: string;
  filename: string;
  chunk_text: string;
  similarity_score: number;
}

interface KBSearchResponse {
  results: KBSearchResult[];
  query: string;
}

// ─── Knowledge Base Page ──────────────────────────────────────────────────────

export default function KnowledgeBase() {
  const { toast } = useToast();

  const {
    data: docsData,
    isLoading: docsLoading,
    error: docsError,
    refetch: refetchDocs,
  } = useApiQuery<KBDocumentListResponse>(["kb-documents"], API_PATHS.KB_DOCUMENTS, {
    staleTime: 10_000,
  });

  const [documents, setDocuments] = useState<KBDocument[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Phase 3 — Search
  const [searchInput, setSearchInput] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<KBSearchResult[]>([]);
  const [lastQuery, setLastQuery] = useState("");

  // Status polling
  const [pollingActive, setPollingActive] = useState(false);

  // ── Sync documents from query ─────────────────────────────────────────────────
  useEffect(() => {
    if (docsData?.documents) {
      setDocuments(docsData.documents);
    }
  }, [docsData]);

  // ── Status polling — re-fetch every 3s while any doc is still processing ──────
  const startPolling = useCallback(() => {
    if (pollingActive) return;
    setPollingActive(true);
    const interval = setInterval(async () => {
      const result = await refetchDocs();
      const docs = result.data?.documents ?? [];
      const stillInProgress = docs.some(
        (d) => d.processing_status === "pending" || d.processing_status === "processing"
      );
      if (!stillInProgress) {
        clearInterval(interval);
        setPollingActive(false);
      }
    }, 3000);
    return () => { clearInterval(interval); setPollingActive(false); };
  }, [pollingActive, refetchDocs]);

  useEffect(() => {
    const hasInProgress = documents.some(
      (d) => d.processing_status === "pending" || d.processing_status === "processing"
    );
    if (hasInProgress) startPolling();
  }, [documents, startPolling]);

  // ── Filter ────────────────────────────────────────────────────────────────────
  const filtered = documents.filter((d) =>
    d.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // ── Handlers ──────────────────────────────────────────────────────────────────
  const handleDocUploaded = (doc: KBDocument) => {
    setDocuments((prev) => [doc, ...prev]);
    refetchDocs();
  };

  const handleDocDeleted = (uuid: string) => {
    setDocuments((prev) => prev.filter((d) => d.document_uuid !== uuid));
  };

  const handleSearch = async () => {
    if (!searchInput.trim()) return;
    setSearching(true);
    setLastQuery(searchInput);
    try {
      const result = await apiPost<KBSearchResponse>(API_PATHS.KB_SEARCH, {
        query: searchInput,
        limit: 5,
      });
      setSearchResults(result.results ?? []);
      if (!result.results?.length) {
        toast({ title: "No results found", description: "Try a different query." });
      }
    } catch {
      toast({ title: "Search failed", variant: "destructive" });
    } finally {
      setSearching(false);
    }
  };

  // ── Stats ─────────────────────────────────────────────────────────────────────
  const totalDocs = documents.length;
  const readyDocs = documents.filter((d) => d.processing_status === "completed").length;
  const processingDocs = documents.filter(
    (d) => d.processing_status === "pending" || d.processing_status === "processing"
  ).length;

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <BookOpen className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold text-foreground">Knowledge Base</h1>
          </div>
          <p className="text-sm text-muted-foreground">
            Upload documents your AI agents can reference during calls — FAQs, pricing, scripts, and more.
          </p>
        </div>
        <Button onClick={() => setShowUploadModal(true)} className="gap-2 shrink-0">
          <Plus className="h-4 w-4" /> Add Document
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <Card className="bg-card border-border">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Total Documents</p>
            <p className="text-2xl font-bold mt-1 text-foreground">{totalDocs}</p>
          </CardContent>
        </Card>
        <Card className="bg-card border-border">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Ready</p>
            <p className="text-2xl font-bold mt-1 text-green-400">
              {readyDocs}
              {processingDocs > 0 && (
                <span className="text-xs font-normal text-yellow-400 ml-2">
                  ({processingDocs} processing)
                </span>
              )}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-card border-border col-span-2 sm:col-span-1">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Storage</p>
            <p className="text-2xl font-bold mt-1 text-primary">
              {(documents.reduce((s, d) => s + d.file_size_bytes, 0) / 1024 / 1024).toFixed(1)} MB
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Search bar (filter by name) */}
      {totalDocs > 0 && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Filter documents by name…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      )}

      {/* Document grid */}
      {docsLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : docsError ? (
        <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
          <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-400">Failed to load documents. Please refresh.</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-4">
          <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
            <BookOpen className="h-8 w-8 text-primary" />
          </div>
          <div className="text-center">
            <p className="font-medium text-foreground">
              {searchQuery ? "No documents match your search" : "No documents yet"}
            </p>
            <p className="text-sm text-muted-foreground mt-1 max-w-sm">
              {searchQuery
                ? "Try a different search term"
                : "Add your first document — FAQs, pricing, property details — and your AI agents will use it to answer questions during calls."}
            </p>
          </div>
          {!searchQuery && (
            <Button onClick={() => setShowUploadModal(true)} className="gap-2">
              <Plus className="h-4 w-4" /> Add Your First Document
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((doc) => (
            <DocumentCard
              key={doc.document_uuid}
              doc={doc}
              onDeleted={handleDocDeleted}
            />
          ))}
        </div>
      )}

      {/* Phase 3 — Test Search panel (only shown when docs are ready) */}
      {readyDocs > 0 && (
        <Card className="border-border bg-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              Test Search
              <Badge variant="outline" className="text-xs ml-1">
                Preview what your agent finds
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Type a question below to see exactly what your AI agent would find from your documents during a real call.
            </p>
            <div className="flex gap-2">
              <Textarea
                className="resize-none min-h-[60px] text-sm"
                placeholder='e.g. "What are your pricing plans?" or "How do I schedule a viewing?"'
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSearch();
                  }
                }}
              />
              <Button
                className="self-end gap-1.5"
                onClick={handleSearch}
                disabled={!searchInput.trim() || searching}
              >
                {searching ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>

            {searchResults.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">
                  Results for:{" "}
                  <span className="text-foreground font-medium">"{lastQuery}"</span>
                </p>
                {searchResults.map((r, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-lg bg-muted/40 border border-border space-y-1.5"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="text-xs font-medium text-foreground">
                          {r.filename}
                        </span>
                      </div>
                      <Badge variant="outline" className="text-xs">
                        {Math.round(r.similarity_score * 100)}% match
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
                      {r.chunk_text}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Upload Modal */}
      <UploadDocumentModal
        open={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onUploaded={handleDocUploaded}
      />
    </div>
  );
}
