import { useState } from "react";
import {
  Sheet,
  Plus,
  Loader2,
  AlertCircle,
  RefreshCw,
  LinkIcon,
  Zap,
  BarChart3,
  Phone,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useQueryClient } from "@tanstack/react-query";
import { SHEET_CONNECTIONS } from "@/utils/apiPaths";
import { API_PATHS } from "@/utils/apiPaths";
import { ConnectSheetModal } from "@/components/sheets/ConnectSheetModal";
import { SheetConnectionCard } from "@/components/sheets/SheetConnectionCard";
import type { SheetConnection } from "@/types/sheets";

// ─── Agent type (from existing agents API) ────────────────────────────────────

interface AgentMeta {
  workflow_id: number;
  name: string;
  status: string;
}

interface AgentsListResponse {
  agents: AgentMeta[];
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Integrations() {
  const queryClient = useQueryClient();
  const [showConnect, setShowConnect] = useState(false);

  // ── Data ───────────────────────────────────────────────────────────────

  const {
    data: connectionsData,
    isLoading: connectionsLoading,
    error: connectionsError,
    refetch: refetchConnections,
  } = useApiQuery<SheetConnection[]>(["sheet-connections"], SHEET_CONNECTIONS, {
    staleTime: 15_000,
  });

  const { data: agentsData } = useApiQuery<AgentsListResponse>(
    ["agents"],
    API_PATHS.AGENTS,
    { staleTime: 60_000 },
  );

  const connections = connectionsData ?? [];
  const agents = (agentsData?.agents ?? []).map((a) => ({
    workflow_id: a.workflow_id,
    name: a.name,
  }));

  // ── Handlers ───────────────────────────────────────────────────────────

  const handleCreated = (conn: SheetConnection) => {
    queryClient.invalidateQueries({ queryKey: ["sheet-connections"] });
    setShowConnect(false);
  };

  const handleDeleted = (id: string) => {
    queryClient.invalidateQueries({ queryKey: ["sheet-connections"] });
    queryClient.removeQueries({ queryKey: ["sheet-leads", id] });
    queryClient.removeQueries({ queryKey: ["sheet-stats", id] });
  };

  // ── Derived stats ──────────────────────────────────────────────────────

  const totalLeads = connections.reduce((s, c) => s + c.total_leads_found, 0);
  const totalCalled = connections.reduce((s, c) => s + c.total_leads_called, 0);
  const totalQualified = connections.reduce((s, c) => s + c.total_leads_qualified, 0);
  const activeCount = connections.filter((c) => c.is_active).length;

  // ─── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 p-6">
      {/* ── Page header ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <LinkIcon className="h-6 w-6 text-green-500" />
            Integrations
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Connect spreadsheets to auto-call new leads and write results back automatically.
          </p>
        </div>
        <Button onClick={() => setShowConnect(true)} className="shrink-0">
          <Plus className="h-4 w-4 mr-2" />
          Connect Sheet
        </Button>
      </div>

      {/* ── Overview KPIs (only shown once connections exist) ── */}
      {connections.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={<Sheet className="h-4 w-4 text-green-500" />} label="Connected Sheets" value={connections.length} sub={`${activeCount} active`} />
          <KpiCard icon={<Zap className="h-4 w-4 text-amber-500" />} label="Leads Found" value={totalLeads} />
          <KpiCard icon={<Phone className="h-4 w-4 text-blue-500" />} label="Calls Triggered" value={totalCalled} />
          <KpiCard icon={<BarChart3 className="h-4 w-4 text-purple-500" />} label="Qualified" value={totalQualified} />
        </div>
      )}

      {/* ── Loading ── */}
      {connectionsLoading && (
        <div className="flex justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* ── Error ── */}
      {connectionsError && !connectionsLoading && (
        <Card>
          <CardContent className="flex flex-col items-center py-12 gap-4">
            <AlertCircle className="h-10 w-10 text-destructive" />
            <div className="text-center">
              <p className="font-medium">Failed to load integrations</p>
              <p className="text-sm text-muted-foreground mt-1">
                {connectionsError instanceof Error ? connectionsError.message : "Unknown error"}
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={() => refetchConnections()}>
              <RefreshCw className="h-4 w-4 mr-2" /> Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {/* ── Empty state ── */}
      {!connectionsLoading && !connectionsError && connections.length === 0 && (
        <EmptyState onConnect={() => setShowConnect(true)} />
      )}

      {/* ── Connection cards ── */}
      {!connectionsLoading && connections.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              {connections.length} Sheet{connections.length !== 1 ? "s" : ""} Connected
            </h2>
            <Button variant="ghost" size="sm" onClick={() => refetchConnections()}>
              <RefreshCw className="h-3.5 w-3.5 mr-1" /> Refresh
            </Button>
          </div>

          {connections.map((conn) => (
            <SheetConnectionCard
              key={conn.id}
              connection={conn}
              onRefresh={() => queryClient.invalidateQueries({ queryKey: ["sheet-connections"] })}
              onDeleted={handleDeleted}
            />
          ))}
        </div>
      )}

      {/* ── Google Sheets section divider (future: add more integrations) ── */}
      {!connectionsLoading && (
        <div className="pt-4 border-t">
          <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-3">Coming Soon</p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <ComingSoonCard label="Excel Online" icon="📊" />
            <ComingSoonCard label="Notion Database" icon="📝" />
            <ComingSoonCard label="Airtable" icon="🗃️" />
          </div>
        </div>
      )}

      {/* ── Modal ── */}
      <ConnectSheetModal
        open={showConnect}
        agents={agents}
        onClose={() => setShowConnect(false)}
        onCreated={handleCreated}
      />
    </div>
  );
}

// ─── KpiCard ─────────────────────────────────────────────────────────────────

function KpiCard({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: number; sub?: string }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted">
          {icon}
        </div>
        <div>
          <p className="text-xl font-bold">{value.toLocaleString()}</p>
          <p className="text-[11px] text-muted-foreground">{label}</p>
          {sub && <p className="text-[10px] text-muted-foreground">{sub}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── EmptyState ───────────────────────────────────────────────────────────────

function EmptyState({ onConnect }: { onConnect: () => void }) {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center py-16 text-center gap-5">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-green-500/10 border border-green-500/20">
          <Sheet className="h-8 w-8 text-green-500" />
        </div>
        <div>
          <h3 className="font-semibold text-lg">Connect your first spreadsheet</h3>
          <p className="text-muted-foreground text-sm mt-2 max-w-sm">
            When a new lead appears in a connected Google Sheet, your AI agent automatically calls them,
            then writes the call summary and lead tag back to the sheet.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm text-muted-foreground max-w-lg w-full">
          <Feature emoji="📥" text="New row detected" />
          <Feature emoji="📞" text="Agent calls lead" />
          <Feature emoji="✍️" text="Results written back" />
        </div>
        <Button onClick={onConnect} size="lg" className="mt-2">
          <Plus className="h-4 w-4 mr-2" /> Connect Google Sheet
        </Button>
      </CardContent>
    </Card>
  );
}

function Feature({ emoji, text }: { emoji: string; text: string }) {
  return (
    <div className="flex flex-col items-center gap-1.5 p-3 rounded-lg bg-muted/40">
      <span className="text-2xl">{emoji}</span>
      <span className="text-xs font-medium">{text}</span>
    </div>
  );
}

// ─── ComingSoonCard ───────────────────────────────────────────────────────────

function ComingSoonCard({ label, icon }: { label: string; icon: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-dashed p-3 opacity-50">
      <span className="text-xl">{icon}</span>
      <div>
        <p className="text-sm font-medium">{label}</p>
        <p className="text-[10px] text-muted-foreground">Coming soon</p>
      </div>
    </div>
  );
}
