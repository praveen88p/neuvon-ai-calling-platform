import { useState, useCallback, useRef } from "react";
import { Upload, FileText, X, Loader2, CheckCircle2, AlertCircle, Type } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { API_BASE_URL } from "@/utils/api";
import { API_PATHS } from "@/utils/apiPaths";
import type { KBDocument } from "./DocumentCard";

// ─── Types ────────────────────────────────────────────────────────────────────

interface UploadDocumentModalProps {
  open: boolean;
  onClose: () => void;
  onUploaded: (doc: KBDocument) => void;
}

type UploadState = "idle" | "uploading" | "done" | "error";

const ACCEPTED_MIME_TYPES: Record<string, string> = {
  "application/pdf": "PDF",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
  "application/msword": "DOC",
  "text/plain": "TXT",
  "text/csv": "CSV",
};

// ─── Core upload helper ────────────────────────────────────────────────────────

/**
 * Upload a File to our backend via multipart/form-data.
 * The backend handles S3 upload + triggering processing server-side.
 * This avoids all CORS issues with direct browser-to-S3 uploads.
 */
async function uploadViaBackend(
  file: File,
  retrievalMode: "full_document" | "chunked" = "full_document"
): Promise<KBDocument> {
  const token = localStorage.getItem("auth_token") || "";
  const form = new FormData();
  form.append("file", file, file.name);

  const url = `${API_BASE_URL}${API_PATHS.KB_UPLOAD}?retrieval_mode=${retrievalMode}`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });

  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }));
    throw new Error(detail?.detail || `Upload failed (${resp.status})`);
  }

  return resp.json() as Promise<KBDocument>;
}

// ─── File Upload Tab ──────────────────────────────────────────────────────────

function FileUploadTab({
  onUploaded,
  onClose,
}: {
  onUploaded: (doc: KBDocument) => void;
  onClose: () => void;
}) {
  const { toast } = useToast();
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [retrievalMode, setRetrievalMode] = useState<"full_document" | "chunked">("full_document");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File) => {
    if (!ACCEPTED_MIME_TYPES[f.type]) {
      toast({
        title: "Unsupported file type",
        description: "Please upload PDF, DOCX, TXT, or CSV.",
        variant: "destructive",
      });
      return;
    }
    setFile(f);
    setUploadState("idle");
    setErrorMsg("");
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setUploadState("uploading");
    setErrorMsg("");
    try {
      const doc = await uploadViaBackend(file, retrievalMode);
      setUploadState("done");
      toast({ title: "Document uploaded!", description: `${file.name} is now being processed.` });
      setTimeout(() => { onUploaded(doc); onClose(); }, 700);
    } catch (err: unknown) {
      setUploadState("error");
      const msg = err instanceof Error ? err.message : "Upload failed";
      setErrorMsg(msg);
      toast({ title: "Upload failed", description: msg, variant: "destructive" });
    }
  };

  const isUploading = uploadState === "uploading";

  const retrievalOptions: { value: "full_document" | "chunked"; label: string; description: string }[] = [
    {
      value: "full_document",
      label: "Full Document",
      description: "The entire document is given to the agent on each retrieval. Best for FAQs, price lists, and small reference docs.",
    },
    {
      value: "chunked",
      label: "Chunked Search",
      description: "The document is split into chunks and the most relevant ones are retrieved. Best for large manuals or policies.",
    },
  ];

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
          dragOver
            ? "border-primary bg-primary/5"
            : file
            ? "border-green-500/50 bg-green-500/5"
            : "border-border hover:border-primary/50 hover:bg-muted/30"
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pdf,.doc,.docx,.txt,.csv"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />

        {file ? (
          <div className="flex flex-col items-center gap-2">
            <CheckCircle2 className="h-10 w-10 text-green-500" />
            <p className="font-medium text-sm text-foreground">{file.name}</p>
            <p className="text-xs text-muted-foreground">
              {(file.size / 1024 / 1024).toFixed(2)} MB · {ACCEPTED_MIME_TYPES[file.type] ?? "File"}
            </p>
            {!isUploading && (
              <Button
                variant="ghost"
                size="sm"
                className="text-xs h-6 text-muted-foreground"
                onClick={(e) => { e.stopPropagation(); setFile(null); setUploadState("idle"); }}
              >
                <X className="h-3 w-3 mr-1" /> Remove
              </Button>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <Upload className="h-10 w-10 text-muted-foreground" />
            <p className="font-medium text-sm text-foreground">Drop your file here</p>
            <p className="text-xs text-muted-foreground">or click to browse</p>
            <p className="text-xs text-muted-foreground mt-1">PDF, DOCX, TXT, CSV supported</p>
          </div>
        )}
      </div>

      {/* Retrieval mode selector */}
      <div className="space-y-2">
        <p className="text-sm font-medium text-foreground">How should the agent use this document?</p>
        <div className="space-y-2">
          {retrievalOptions.map((opt) => (
            <button
              key={opt.value}
              type="button"
              className={`w-full text-left flex items-start gap-3 p-3 rounded-lg border transition-all ${
                retrievalMode === opt.value
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/30 hover:bg-muted/30"
              }`}
              onClick={() => setRetrievalMode(opt.value)}
              disabled={isUploading}
            >
              <div className={`mt-0.5 h-4 w-4 rounded-full border-2 flex-shrink-0 flex items-center justify-center ${
                retrievalMode === opt.value ? "border-primary" : "border-muted-foreground/40"
              }`}>
                {retrievalMode === opt.value && (
                  <div className="h-2 w-2 rounded-full bg-primary" />
                )}
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">{opt.label}</p>
                <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{opt.description}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Uploading progress */}
      {isUploading && (
        <div className="space-y-1.5">
          <p className="text-xs text-muted-foreground">Uploading and processing…</p>
          <Progress value={undefined} className="h-1.5 animate-pulse" />
        </div>
      )}

      {/* Error */}
      {uploadState === "error" && errorMsg && (
        <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 rounded-lg p-3">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          {errorMsg}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 justify-end">
        <Button variant="ghost" onClick={onClose} disabled={isUploading}>
          Cancel
        </Button>
        <Button
          onClick={handleUpload}
          disabled={!file || isUploading || uploadState === "done"}
        >
          {isUploading ? (
            <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Uploading…</>
          ) : uploadState === "done" ? (
            <><CheckCircle2 className="h-4 w-4 mr-2" /> Done!</>
          ) : (
            <><Upload className="h-4 w-4 mr-2" /> Upload & Process</>
          )}
        </Button>
      </div>
    </div>
  );
}


// ─── Paste Text Tab ───────────────────────────────────────────────────────────

function PasteTextTab({
  onUploaded,
  onClose,
}: {
  onUploaded: (doc: KBDocument) => void;
  onClose: () => void;
}) {
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [content, setContent] = useState("");
  const [uploading, setUploading] = useState(false);

  const handleSubmit = async () => {
    if (!name.trim() || !content.trim()) return;
    setUploading(true);
    try {
      const filename = name.trim().endsWith(".txt") ? name.trim() : `${name.trim()}.txt`;
      const blob = new Blob([content], { type: "text/plain" });
      const file = new File([blob], filename, { type: "text/plain" });
      const doc = await uploadViaBackend(file);
      toast({ title: "Text saved!", description: `"${filename}" is being processed.` });
      setTimeout(() => { onUploaded(doc); onClose(); }, 700);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save text";
      toast({ title: "Failed", description: msg, variant: "destructive" });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="doc-name" className="text-sm">Document name</Label>
        <Input
          id="doc-name"
          placeholder="e.g. FAQ, Pricing, Product Info"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={uploading}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="doc-content" className="text-sm">Content</Label>
        <Textarea
          id="doc-content"
          placeholder="Paste or type the knowledge your AI agent should know…"
          className="min-h-[200px] resize-none font-mono text-sm"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          disabled={uploading}
        />
        <p className="text-xs text-muted-foreground text-right">{content.length} characters</p>
      </div>

      <div className="flex gap-2 justify-end">
        <Button variant="ghost" onClick={onClose} disabled={uploading}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={!name.trim() || !content.trim() || uploading}
        >
          {uploading ? (
            <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Saving…</>
          ) : (
            <><FileText className="h-4 w-4 mr-2" /> Save Document</>
          )}
        </Button>
      </div>
    </div>
  );
}

// ─── Modal ────────────────────────────────────────────────────────────────────

export function UploadDocumentModal({ open, onClose, onUploaded }: UploadDocumentModalProps) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5 text-primary" />
            Add Knowledge Document
          </DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="file" className="mt-2">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="file" className="gap-2">
              <Upload className="h-3.5 w-3.5" /> Upload File
            </TabsTrigger>
            <TabsTrigger value="text" className="gap-2">
              <Type className="h-3.5 w-3.5" /> Paste Text
            </TabsTrigger>
          </TabsList>

          <TabsContent value="file" className="mt-4">
            <FileUploadTab onUploaded={onUploaded} onClose={onClose} />
          </TabsContent>

          <TabsContent value="text" className="mt-4">
            <PasteTextTab onUploaded={onUploaded} onClose={onClose} />
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
