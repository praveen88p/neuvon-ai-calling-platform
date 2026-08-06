import { useState } from "react";
import {
  FileText,
  FileType2,
  File,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Trash2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { apiDelete } from "@/utils/api";
import { kbDocumentPath } from "@/utils/apiPaths";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface KBDocument {
  document_uuid: string;
  filename: string;
  file_size_bytes: number;
  mime_type: string;
  processing_status: "pending" | "processing" | "completed" | "failed";
  processing_error?: string | null;
  total_chunks: number;
  retrieval_mode: string;
  created_at: string;
}

interface DocumentCardProps {
  doc: KBDocument;
  onDeleted: (uuid: string) => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(mimeType: string) {
  if (mimeType === "application/pdf")
    return <FileType2 className="h-8 w-8 text-red-500" />;
  if (
    mimeType ===
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
    mimeType === "application/msword"
  )
    return <FileText className="h-8 w-8 text-blue-500" />;
  if (mimeType === "text/plain")
    return <FileText className="h-8 w-8 text-gray-400" />;
  if (mimeType === "text/csv")
    return <FileText className="h-8 w-8 text-green-500" />;
  return <File className="h-8 w-8 text-purple-500" />;
}

function StatusBadge({ status }: { status: KBDocument["processing_status"] }) {
  if (status === "completed")
    return (
      <Badge className="bg-green-500/10 text-green-400 border-green-500/20 gap-1">
        <CheckCircle2 className="h-3 w-3" /> Ready
      </Badge>
    );
  if (status === "processing" || status === "pending")
    return (
      <Badge className="bg-yellow-500/10 text-yellow-400 border-yellow-500/20 gap-1 animate-pulse">
        <Loader2 className="h-3 w-3 animate-spin" /> Processing…
      </Badge>
    );
  return (
    <Badge className="bg-red-500/10 text-red-400 border-red-500/20 gap-1">
      <AlertCircle className="h-3 w-3" /> Failed
    </Badge>
  );
}

// ─── DocumentCard ─────────────────────────────────────────────────────────────

export function DocumentCard({ doc, onDeleted }: DocumentCardProps) {
  const { toast } = useToast();
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!confirm(`Delete "${doc.filename}"? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await apiDelete(kbDocumentPath(doc.document_uuid));
      toast({ title: "Document deleted", description: doc.filename });
      onDeleted(doc.document_uuid);
    } catch {
      toast({
        title: "Delete failed",
        description: "Could not delete the document. Please try again.",
        variant: "destructive",
      });
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Card className="group relative bg-card border border-border hover:border-primary/40 transition-all duration-200 hover:shadow-lg hover:shadow-primary/5">
      <CardContent className="p-5">
        <div className="flex items-start gap-3">
          {/* File icon */}
          <div className="mt-0.5 flex-shrink-0">{getFileIcon(doc.mime_type)}</div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <p
              className="font-medium text-sm text-foreground truncate"
              title={doc.filename}
            >
              {doc.filename}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {formatBytes(doc.file_size_bytes)} ·{" "}
              {new Date(doc.created_at).toLocaleDateString()}
            </p>

            <div className="mt-2 flex items-center gap-2 flex-wrap">
              <StatusBadge status={doc.processing_status} />
              {doc.processing_status === "completed" && doc.total_chunks > 0 && (
                <span className="text-xs text-muted-foreground">
                  {doc.total_chunks} chunks
                </span>
              )}
            </div>

            {doc.processing_error && (
              <p
                className="text-xs text-red-400 mt-1 truncate"
                title={doc.processing_error}
              >
                {doc.processing_error}
              </p>
            )}
          </div>

          {/* Delete */}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
            onClick={handleDelete}
            disabled={deleting}
            title="Delete document"
          >
            {deleting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Trash2 className="h-3.5 w-3.5" />
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
