import { useState } from "react";
import {
  Sheet,
  Pause,
  Play,
  Trash2,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Phone,
  Loader2,
  AlertCircle,
  Zap,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { apiPost, apiDelete } from "@/utils/api";
import { sheetPausePath, sheetResumePath, sheetConnectionPath, sheetLeadsPath, sheetPollNowPath } from "@/utils/apiPaths";
import { useApiQuery } from "@/hooks/useApiQuery";
import type { SheetConnection, SheetLead, SheetLeadsListResponse, SheetConnectionStats } from "@/types/sheets";
import { sheetStatsPath } from "@/utils/apiPaths";
import { CallbacksPanel } from "./CallbacksPanel";

// ─── Props ────────────────────────────────────────────────────────────────────

interface SheetConnectionCardProps {
  connection: SheetConnection;
  onRefresh: () => void;
  onDeleted: (id: string) => void;
}

// ─── Status helpers ───────────────────────────────────────────────────────────

const TAG_STYLES: Record<string, string> = {
  qualified: "bg-green-500/10 text-green-600 border-green-500/20",
  interested: "bg-blue-500/10 text-blue-600 border-blue-500/20",
  "not interested": "bg-red-500/10 text-red-600 border-red-500/20",
  "follow up": "bg-amber-500/10 text-amber-600 border-amber-500/20",
  callback_scheduled: "bg-purple-500/10 text-purple-600 border-purple-500/20",
};

const STATUS_ICON: Record<string, React.ReactNode> = {
  completed: <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />,
  failed: <XCircle className="h-3.5 w-3.5 text-destructive" />,
  calling: <Phone className="h-3.5 w-3.5 text-blue-500 animate-pulse" />,
  pending: <Clock className="h-3.5 w-3.5 text-muted-foreground" />,
  callback_scheduled: <Clock className="h-3.5 w-3.5 text-purple-500" />,
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60_000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return `${Math.floor(hr / 24)}d ago`;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function SheetConnectionCard({ connection: conn, onRefresh, onDeleted }: SheetConnectionCardProps) {
  const { toast } = useToast();
  const [actioning, setActioning] = useState(false);
  const [polling, setPolling] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<"leads" | "callbacks">("leads");

  // Lazy-load leads + stats when expanded
  const { data: leadsData, isLoading: leadsLoading } = useApiQuery<SheetLeadsListResponse>(
    ["sheet-leads", conn.id],
    sheetLeadsPath(conn.id),
    { enabled: expanded, staleTime: 15_000 },
  );

  const { data: statsData } = useApiQuery<SheetConnectionStats>(
    ["sheet-stats", conn.id],
    sheetStatsPath(conn.id),
    { enabled: expanded, staleTime: 15_000 },
  );

  const leads = leadsData?.leads ?? [];
  const callPercent = conn.total_leads_found > 0
    ? Math.round((conn.total_leads_called / conn.total_leads_found) * 100)
    : 0;

  // ── Actions ──────────────────────────────────────────────────────────────

  const handleToggleActive = async () => {
    setActioning(true);
    try {
      const path = conn.is_active ? sheetPausePath(conn.id) : sheetResumePath(conn.id);
      await apiPost(path);
      toast({
        title: conn.is_active ? "Polling paused" : "Polling resumed",
        description: conn.is_active ? "No new leads will be called until you resume." : "Monitoring for new leads.",
      });
      onRefresh();
    } catch (err: unknown) {
      toast({ title: "Action failed", description: err instanceof Error ? err.message : "Try again.", variant: "destructive" });
    } finally {
      setActioning(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete connection to "${conn.sheet_url}"? All lead history will be removed.`)) return;
    setActioning(true);
    try {
      await apiDelete(sheetConnectionPath(conn.id));
      toast({ title: "Connection deleted" });
      onDeleted(conn.id);
    } catch (err: unknown) {
      toast({ title: "Delete failed", description: err instanceof Error ? err.message : "Try again.", variant: "destructive" });
    } finally {
      setActioning(false);
    }
  };

  const handlePollNow = async () => {
    setPolling(true);
    try {
      const res = await apiPost<{ new_leads_found: number }>(sheetPollNowPath(conn.id));
      toast({
        title: res.new_leads_found > 0
          ? `Found ${res.new_leads_found} new lead${res.new_leads_found !== 1 ? "s" : ""}!`
          : "No new leads found",
        description: res.new_leads_found > 0
          ? "Calls are being triggered for the new leads."
          : "All rows were already processed. Add new rows to your sheet.",
      });
      onRefresh();
    } catch (err: unknown) {
      toast({ title: "Poll failed", description: err instanceof Error ? err.message : "Try again.", variant: "destructive" });
    } finally {
      setPolling(false);
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────

  const sheetIdDisplay = conn.spreadsheet_id.slice(0, 20) + "…";

  return (
    <Card className="overflow-hidden transition-all duration-200 hover:shadow-md">
      <CardContent className="p-0">
        {/* ── Header ── */}
        <div className="flex items-start gap-3 p-4">
          {/* Icon */}
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-green-500/10 border border-green-500/20">
            <Sheet className="h-5 w-5 text-green-600" />
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-medium text-sm truncate max-w-[220px]" title={conn.sheet_url}>
                {sheetIdDisplay}
              </p>
              <Badge
                variant="outline"
                className={conn.is_active
                  ? "border-green-500/30 text-green-600 bg-green-500/10 text-[10px]"
                  : "border-muted text-muted-foreground text-[10px]"}
              >
                {conn.is_active ? "● Active" : "○ Paused"}
              </Badge>
              {conn.last_error && (
                <Badge variant="destructive" className="text-[10px] flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" /> Error
                </Badge>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Tab: <span className="font-medium">{conn.sheet_name}</span>
              {" · "}
              {conn.last_polled_at ? `Polled ${timeAgo(conn.last_polled_at)}` : "Not yet polled"}
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1 shrink-0">
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8"
              title={conn.is_active ? "Pause polling" : "Resume polling"}
              onClick={handleToggleActive}
              disabled={actioning || polling}
            >
              {actioning ? <Loader2 className="h-4 w-4 animate-spin" /> : conn.is_active ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8 text-amber-500 hover:text-amber-600 hover:bg-amber-500/10"
              title="Poll now — check sheet for new leads immediately"
              onClick={handlePollNow}
              disabled={polling || actioning}
            >
              {polling ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8 text-muted-foreground hover:text-foreground"
              title="Open sheet"
              asChild
            >
              <a href={conn.sheet_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4" />
              </a>
            </Button>
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8 text-muted-foreground hover:text-destructive"
              title="Delete connection"
              onClick={handleDelete}
              disabled={actioning}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* ── Stats bar ── */}
        <div className="grid grid-cols-3 divide-x border-t bg-muted/20">
          <StatCell label="Leads Found" value={conn.total_leads_found} />
          <StatCell label="Called" value={conn.total_leads_called} />
          <StatCell label="Qualified" value={conn.total_leads_qualified} accent="green" />
        </div>

        {/* ── Progress ── */}
        {conn.total_leads_found > 0 && (
          <div className="px-4 py-2 border-t">
            <div className="flex justify-between text-[11px] text-muted-foreground mb-1">
              <span>Call progress</span>
              <span>{callPercent}%</span>
            </div>
            <Progress value={callPercent} className="h-1.5" />
          </div>
        )}

        {/* ── Needs reauth banner ── */}
        {conn.needs_reauth && (
          <div className="flex items-start gap-2 mx-4 mb-2 rounded-md bg-amber-500/10 border border-amber-500/30 px-3 py-2 text-xs text-amber-700 dark:text-amber-400">
            <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-semibold">Google credentials need updating.</span>
              {" "}The service account JSON may have expired or lost access. Delete and reconnect this sheet to resume polling.
            </div>
          </div>
        )}

        {/* ── Consecutive error warning ── */}
        {!conn.needs_reauth && conn.consecutive_error_count > 0 && (
          <div className="flex items-center gap-2 mx-4 mb-2 rounded-md bg-orange-500/10 border border-orange-500/20 px-3 py-1.5 text-[11px] text-orange-700 dark:text-orange-400">
            <AlertCircle className="h-3 w-3 shrink-0" />
            {conn.consecutive_error_count} consecutive poll error{conn.consecutive_error_count > 1 ? "s" : ""} — will auto-pause at {5 - conn.consecutive_error_count} more
          </div>
        )}

        {/* ── Error banner ── */}
        {conn.last_error && !conn.needs_reauth && (
          <div className="flex items-start gap-2 mx-4 mb-3 rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-xs text-destructive">
            <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
            <span className="line-clamp-2">{conn.last_error}</span>
          </div>
        )}

        {/* ── Expand / collapse ── */}
        <button
          onClick={() => setExpanded((p) => !p)}
          className="w-full flex items-center justify-center gap-1 border-t py-2 text-[11px] text-muted-foreground hover:bg-muted/30 transition-colors"
        >
          {expanded ? <><ChevronUp className="h-3 w-3" /> Hide details</> : <><ChevronDown className="h-3 w-3" /> Show leads & callbacks</>}
        </button>

        {/* ── Leads / Callbacks tabs ── */}
        {expanded && (
          <div className="border-t">
            {/* Tab switcher */}
            <div className="flex border-b">
              <button
                onClick={() => setActiveTab("leads")}
                className={`flex-1 py-2 text-[11px] font-medium transition-colors ${
                  activeTab === "leads"
                    ? "border-b-2 border-primary text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Leads
              </button>
              <button
                onClick={() => setActiveTab("callbacks")}
                className={`flex-1 py-2 text-[11px] font-medium transition-colors ${
                  activeTab === "callbacks"
                    ? "border-b-2 border-primary text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Callbacks
              </button>
            </div>
            {/* ── Leads tab ── */}
            {activeTab === "leads" && (
              <>
                {leadsLoading ? (
                  <div className="flex justify-center py-6">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  </div>
                ) : leads.length === 0 ? (
                  <p className="text-center text-sm text-muted-foreground py-6">No leads yet. New rows will appear here as they're detected.</p>
                ) : (
                  <div className="divide-y max-h-72 overflow-y-auto">
                    {leads.map((lead) => <LeadRow key={lead.id} lead={lead} />)}
                  </div>
                )}
                {statsData && (
                  <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 px-4 py-3 border-t bg-muted/10 text-center">
                    <MiniStat label="Pending" value={statsData.pending} />
                    <MiniStat label="Calling" value={statsData.calling} accent="blue" />
                    <MiniStat label="Done" value={statsData.completed} accent="green" />
                    <MiniStat label="Failed" value={statsData.failed} accent="red" />
                    <MiniStat label="Callbacks" value={statsData.callback_scheduled} accent="purple" />
                  </div>
                )}
              </>
            )}

            {/* ── Callbacks tab ── */}
            {activeTab === "callbacks" && (
              <div className="max-h-72 overflow-y-auto">
                <CallbacksPanel connectionId={conn.id} />
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── LeadRow ─────────────────────────────────────────────────────────────────

function LeadRow({ lead }: { lead: SheetLead }) {
  const tag = lead.lead_tag?.toLowerCase() ?? "";
  const tagStyle = TAG_STYLES[tag] ?? "bg-muted/50 text-muted-foreground border-muted";
  const statusIcon = STATUS_ICON[lead.call_status] ?? STATUS_ICON["pending"];

  const leadName = lead.lead_data["name"] || lead.lead_data["Name"] || "";

  return (
    <div className="flex items-start gap-3 px-4 py-2.5 hover:bg-muted/20 transition-colors">
      <div className="mt-0.5">{statusIcon}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">
            {leadName || lead.phone_number}
          </span>
          {leadName && <span className="text-[11px] text-muted-foreground">{lead.phone_number}</span>}
        </div>
        {lead.call_summary && (
          <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-1">{lead.call_summary}</p>
        )}
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        {lead.lead_tag && (
          <span className={`text-[10px] border rounded-full px-2 py-0.5 capitalize ${tagStyle}`}>
            {lead.lead_tag}
          </span>
        )}
        <span className="text-[10px] text-muted-foreground">Row {lead.row_number}</span>
      </div>
    </div>
  );
}

// ─── Small helpers ────────────────────────────────────────────────────────────

function StatCell({ label, value, accent }: { label: string; value: number; accent?: "green" }) {
  return (
    <div className="flex flex-col items-center py-2">
      <span className={`text-lg font-semibold ${accent === "green" ? "text-green-600" : "text-foreground"}`}>
        {value}
      </span>
      <span className="text-[10px] text-muted-foreground">{label}</span>
    </div>
  );
}

function MiniStat({ label, value, accent }: { label: string; value: number; accent?: "blue" | "green" | "red" | "purple" }) {
  const colors: Record<string, string> = {
    blue: "text-blue-600",
    green: "text-green-600",
    red: "text-destructive",
    purple: "text-purple-600",
  };
  return (
    <div>
      <p className={`text-base font-semibold ${accent ? colors[accent] : "text-foreground"}`}>{value}</p>
      <p className="text-[10px] text-muted-foreground">{label}</p>
    </div>
  );
}
