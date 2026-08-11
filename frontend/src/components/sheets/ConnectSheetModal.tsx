import { useState } from "react";
import { Loader2, ExternalLink, ChevronRight, Check, AlertCircle, Sheet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { apiPost } from "@/utils/api";
import { SHEET_CONNECTIONS, SHEET_DETECT_COLUMNS } from "@/utils/apiPaths";
import type {
  SheetColumn,
  SheetColumnsResponse,
  SheetConnection,
  MappableField,
} from "@/types/sheets";
import { REQUIRED_FIELDS, OPTIONAL_FIELDS } from "@/types/sheets";

// ─── Sub-types ────────────────────────────────────────────────────────────────

interface AgentOption {
  workflow_id: number;
  name: string;
}

interface ConnectSheetModalProps {
  open: boolean;
  agents: AgentOption[];
  onClose: () => void;
  onCreated: (connection: SheetConnection) => void;
}

type Step = "credentials" | "mapping" | "confirm";

// ─── Component ────────────────────────────────────────────────────────────────

export function ConnectSheetModal({ open, agents, onClose, onCreated }: ConnectSheetModalProps) {
  const { toast } = useToast();

  // Step 1 — credentials
  const [sheetUrl, setSheetUrl] = useState("");
  const [credentialsJson, setCredentialsJson] = useState("");
  const [selectedSheet, setSelectedSheet] = useState("");
  const [detecting, setDetecting] = useState(false);
  const [detectError, setDetectError] = useState<string | null>(null);

  // Step 2 — column mapping
  const [columns, setColumns] = useState<SheetColumn[]>([]);
  const [sheetNames, setSheetNames] = useState<string[]>([]);
  const [spreadsheetId, setSpreadsheetId] = useState("");
  const [rowCount, setRowCount] = useState(0);
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});

  // Step 3 — agent + confirm
  const [agentWorkflowId, setAgentWorkflowId] = useState<number | null>(null);
  const [pollingInterval, setPollingInterval] = useState(60);

  const [step, setStep] = useState<Step>("credentials");
  const [saving, setSaving] = useState(false);

  // ── Helpers ─────────────────────────────────────────────────────────────────

  const reset = () => {
    setSheetUrl(""); setCredentialsJson(""); setSelectedSheet("");
    setDetecting(false); setColumns([]); setSheetNames([]);
    setSpreadsheetId(""); setRowCount(0); setColumnMapping({});
    setAgentWorkflowId(null); setPollingInterval(60);
    setStep("credentials"); setSaving(false); setDetectError(null);
  };

  const handleClose = () => { reset(); onClose(); };

  // Extract client_email from the JSON (so we can tell the user which email to share with)
  const clientEmail = (() => {
    try {
      const parsed = JSON.parse(credentialsJson);
      return parsed.client_email as string | undefined;
    } catch {
      return undefined;
    }
  })();

  // ── Step 1 → detect columns ──────────────────────────────────────────────────

  const handleDetectColumns = async () => {
    if (!sheetUrl.trim() || !credentialsJson.trim()) {
      toast({ title: "Missing fields", description: "Please provide the sheet URL and service account JSON.", variant: "destructive" });
      return;
    }

    // Validate JSON
    try { JSON.parse(credentialsJson); } catch {
      toast({ title: "Invalid JSON", description: "Service account JSON is not valid.", variant: "destructive" });
      return;
    }

    setDetecting(true);
    setDetectError(null);
    try {
      const res = await apiPost<SheetColumnsResponse>(SHEET_DETECT_COLUMNS, {
        sheet_url: sheetUrl.trim(),
        credentials_json: credentialsJson.trim(),
        sheet_name: selectedSheet || undefined,
      });
      setColumns(res.columns);
      setSheetNames(res.sheet_names);
      setSpreadsheetId(res.spreadsheet_id);
      setRowCount(res.row_count);
      setSelectedSheet(res.selected_sheet);
      // Pre-fill mapping by guessing column by header
      const guessed: Record<string, string> = {};
      const allFields: MappableField[] = [...REQUIRED_FIELDS, ...OPTIONAL_FIELDS];
      for (const field of allFields) {
        const match = res.columns.find((c) =>
          c.header.toLowerCase().includes(field.toLowerCase()) ||
          c.header.toLowerCase().replace(/[\s_-]/g, "").includes(field.toLowerCase()),
        );
        if (match) guessed[field] = match.letter;
      }
      setColumnMapping(guessed);
      setStep("mapping");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Could not read the spreadsheet. Check URL and credentials.";
      setDetectError(msg);
    } finally {
      setDetecting(false);
    }
  };

  // ── Step 2 → validate mapping ────────────────────────────────────────────────

  const phoneIsMapped = !!columnMapping["phone"];

  const handleMappingNext = () => {
    if (!phoneIsMapped) {
      toast({ title: "Phone column required", description: "Please map the 'phone' field to a column.", variant: "destructive" });
      return;
    }
    setStep("confirm");
  };

  // ── Step 3 → create connection ────────────────────────────────────────────────

  const handleCreate = async () => {
    if (!agentWorkflowId) {
      toast({ title: "Agent required", description: "Please select a calling agent.", variant: "destructive" });
      return;
    }
    setSaving(true);
    try {
      // Only include mapped columns
      const cleanMapping: Record<string, string> = {};
      for (const [field, letter] of Object.entries(columnMapping)) {
        if (letter) cleanMapping[field] = letter;
      }
      const conn = await apiPost<SheetConnection>(SHEET_CONNECTIONS, {
        sheet_url: sheetUrl.trim(),
        sheet_name: selectedSheet,
        column_mapping: cleanMapping,
        agent_workflow_id: agentWorkflowId,
        credentials_json: credentialsJson.trim(),
        polling_interval_secs: pollingInterval,
      });
      toast({ title: "Sheet connected!", description: `Now monitoring ${rowCount} leads.` });
      onCreated(conn);
      reset();
    } catch (err: unknown) {
      toast({
        title: "Failed to connect",
        description: err instanceof Error ? err.message : "Something went wrong.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  // ─── Render ─────────────────────────────────────────────────────────────────

  const stepLabel: Record<Step, string> = {
    credentials: "Step 1 of 3 — Spreadsheet credentials",
    mapping: "Step 2 of 3 — Map columns",
    confirm: "Step 3 of 3 — Agent & confirm",
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-1">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-green-500/15">
              <Sheet className="h-4 w-4 text-green-500" />
            </div>
            <DialogTitle>Connect Google Sheet</DialogTitle>
          </div>
          <DialogDescription className="text-xs text-muted-foreground">{stepLabel[step]}</DialogDescription>
        </DialogHeader>

        {/* ── Step 1: Credentials ── */}
        {step === "credentials" && (
          <div className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <Label htmlFor="sheet-url">Google Sheet URL</Label>
              <Input
                id="sheet-url"
                placeholder="https://docs.google.com/spreadsheets/d/..."
                value={sheetUrl}
                onChange={(e) => { setSheetUrl(e.target.value); setDetectError(null); }}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="credentials">Service Account JSON</Label>
              <Textarea
                id="credentials"
                className="font-mono text-xs h-36 resize-none"
                placeholder={'{\n  "type": "service_account",\n  "project_id": "...",\n  ...\n}'}
                value={credentialsJson}
                onChange={(e) => { setCredentialsJson(e.target.value); setDetectError(null); }}
              />
              <p className="text-[11px] text-muted-foreground">Paste the full JSON content of your Google Cloud service account key file.</p>
            </div>

            {/* Client email pill — shown once JSON is valid */}
            {clientEmail && (
              <div className="flex items-start gap-2 rounded-md bg-green-500/8 border border-green-500/20 px-3 py-2 text-xs">
                <ExternalLink className="h-3.5 w-3.5 shrink-0 mt-0.5 text-green-600" />
                <div>
                  <span className="font-medium text-green-700 dark:text-green-400">Share your sheet with:</span>
                  <br />
                  <code className="text-[11px] break-all select-all text-green-800 dark:text-green-300">{clientEmail}</code>
                  <br />
                  <span className="text-muted-foreground">Give it <strong>Viewer</strong> or <strong>Editor</strong> access, then click Detect Columns.</span>
                </div>
              </div>
            )}

            {/* Inline error — stays visible so user can read full message */}
            {detectError && (
              <div className="flex items-start gap-2 rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2.5 text-xs text-destructive">
                <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-semibold">Failed to detect columns</p>
                  <p className="leading-relaxed">{detectError}</p>
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-1">
              <Button variant="outline" onClick={handleClose}>Cancel</Button>
              <Button onClick={handleDetectColumns} disabled={detecting}>
                {detecting ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Detecting…</> : <>Detect Columns <ChevronRight className="h-4 w-4 ml-1" /></>}
              </Button>
            </div>
          </div>
        )}

        {/* ── Step 2: Column Mapping ── */}
        {step === "mapping" && (
          <div className="space-y-4 pt-2">
            {/* Sheet tab selector */}
            {sheetNames.length > 1 && (
              <div className="space-y-1.5">
                <Label>Sheet Tab</Label>
                <Select value={selectedSheet} onValueChange={setSelectedSheet}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {sheetNames.map((n) => <SelectItem key={n} value={n}>{n}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="rounded-lg border bg-muted/30 p-3 text-sm">
              <p className="font-medium text-foreground">{spreadsheetId}</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">{rowCount} data rows detected • Tab: <span className="font-medium">{selectedSheet}</span></p>
            </div>

            {/* Column mapping grid */}
            <div className="space-y-3">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Map fields to columns</Label>

              {/* Required fields */}
              {REQUIRED_FIELDS.map((field) => (
                <FieldRow
                  key={field}
                  field={field}
                  columns={columns}
                  value={columnMapping[field] ?? ""}
                  required
                  onChange={(v) => setColumnMapping((prev) => ({ ...prev, [field]: v }))}
                />
              ))}

              {/* Optional fields */}
              {OPTIONAL_FIELDS.map((field) => (
                <FieldRow
                  key={field}
                  field={field}
                  columns={columns}
                  value={columnMapping[field] ?? ""}
                  required={false}
                  onChange={(v) => setColumnMapping((prev) => {
                    const next = { ...prev };
                    if (v) next[field] = v; else delete next[field];
                    return next;
                  })}
                />
              ))}
            </div>

            {!phoneIsMapped && (
              <div className="flex items-center gap-2 rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>Phone column is required to trigger calls.</span>
              </div>
            )}

            <div className="flex justify-between pt-2">
              <Button variant="outline" onClick={() => setStep("credentials")}>Back</Button>
              <Button onClick={handleMappingNext} disabled={!phoneIsMapped}>
                Next <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        )}

        {/* ── Step 3: Agent & Confirm ── */}
        {step === "confirm" && (
          <div className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <Label>Calling Agent</Label>
              <Select
                value={agentWorkflowId?.toString() ?? ""}
                onValueChange={(v) => setAgentWorkflowId(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select an agent…" />
                </SelectTrigger>
                <SelectContent>
                  {agents.map((a) => (
                    <SelectItem key={a.workflow_id} value={a.workflow_id.toString()}>
                      {a.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-[11px] text-muted-foreground">This agent will call every new lead detected in the sheet.</p>
            </div>

            <div className="space-y-1.5">
              <Label>Polling Interval (seconds)</Label>
              <Select value={pollingInterval.toString()} onValueChange={(v) => setPollingInterval(Number(v))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="30">30 seconds</SelectItem>
                  <SelectItem value="60">1 minute</SelectItem>
                  <SelectItem value="300">5 minutes</SelectItem>
                  <SelectItem value="600">10 minutes</SelectItem>
                  <SelectItem value="1800">30 minutes</SelectItem>
                  <SelectItem value="3600">1 hour</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Summary card */}
            <div className="rounded-lg border bg-muted/30 p-3 space-y-2 text-sm">
              <SummaryRow label="Sheet" value={sheetUrl.split("/d/")[1]?.split("/")[0] ?? sheetUrl} />
              <SummaryRow label="Tab" value={selectedSheet} />
              <SummaryRow label="Leads detected" value={`${rowCount} rows`} />
              <SummaryRow
                label="Mapped fields"
                value={Object.keys(columnMapping).join(", ")}
              />
            </div>

            <div className="flex justify-between pt-2">
              <Button variant="outline" onClick={() => setStep("mapping")}>Back</Button>
              <Button onClick={handleCreate} disabled={saving || !agentWorkflowId}>
                {saving ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Connecting…</> : <><Check className="h-4 w-4 mr-2" />Connect Sheet</>}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ─── FieldRow ─────────────────────────────────────────────────────────────────

function FieldRow({
  field, columns, value, required, onChange,
}: {
  field: string;
  columns: SheetColumn[];
  value: string;
  required: boolean;
  onChange: (v: string) => void;
}) {
  const selected = columns.find((c) => c.letter === value);
  return (
    <div className="flex items-center gap-3">
      <div className="w-32 flex-shrink-0">
        <span className="text-sm font-medium capitalize">{field}</span>
        {required && <Badge variant="destructive" className="ml-1.5 text-[10px] py-0 px-1">required</Badge>}
      </div>
      <Select value={value || "__none__"} onValueChange={(v) => onChange(v === "__none__" ? "" : v)}>
        <SelectTrigger className="h-8 text-xs flex-1">
          <SelectValue placeholder="— skip —" />
        </SelectTrigger>
        <SelectContent>
          {!required && <SelectItem value="__none__">— skip —</SelectItem>}
          {columns.map((c) => (
            <SelectItem key={c.letter} value={c.letter}>
              Col {c.letter}: {c.header} {c.sample ? `(e.g. ${c.sample.slice(0, 20)})` : ""}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {selected && (
        <Badge variant="secondary" className="text-[10px] shrink-0">
          {selected.letter}
        </Badge>
      )}
    </div>
  );
}

// ─── SummaryRow ───────────────────────────────────────────────────────────────

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <span className="text-muted-foreground shrink-0">{label}</span>
      <span className="font-medium text-right break-all">{value}</span>
    </div>
  );
}
