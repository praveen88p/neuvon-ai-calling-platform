import { useState, useMemo } from "react";
import { Search, Loader2, Phone, History as HistoryIcon, ExternalLink } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Link } from "react-router-dom";
import { useApiQuery } from "@/hooks/useApiQuery";
import { API_PATHS } from "@/utils/apiPaths";
import type { CallHistoryResponse, CallHistoryItem } from "@/types/api";

// ─── Status badge ────────────────────────────────────────────────────────────

function CallStatusBadge({ status }: { status: string | null }) {
  const s = (status ?? "unknown").toLowerCase();
  const styles: Record<string, string> = {
    completed: "bg-emerald-100 text-emerald-700",
    in_progress: "bg-blue-100 text-blue-700",
    failed: "bg-red-100 text-red-700",
    queued: "bg-yellow-100 text-yellow-700",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${styles[s] ?? "bg-gray-100 text-gray-600"}`}>
      {s.replace(/_/g, " ")}
    </span>
  );
}

// ─── Call History Page ───────────────────────────────────────────────────────

export default function CallHistory() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const limit = 25;

  const { data, isLoading, error } = useApiQuery<CallHistoryResponse>(
    ["call-history", page],
    `${API_PATHS.CALLS_HISTORY}?page=${page}&limit=${limit}`,
    { staleTime: 30_000, keepPreviousData: true },
  );

  const runs = data?.runs ?? [];
  const hasMore = data?.has_more ?? false;

  const filtered = useMemo(() => {
    if (!search) return runs;
    const q = search.toLowerCase();
    return runs.filter(
      (r) =>
        (r.phone_number ?? "").includes(q) ||
        (r.workflow_name ?? "").toLowerCase().includes(q) ||
        (r.campaign_name ?? "").toLowerCase().includes(q) ||
        String(r.run_id).includes(q),
    );
  }, [runs, search]);

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Call History</h1>
          <p className="text-muted-foreground">
            View all call runs and their outcomes
            {data && ` · ${data.total} total calls`}
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search by phone, agent, or campaign..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Call List */}
      {isLoading ? (
        <div className="flex items-center justify-center min-h-[300px]">
          <div className="text-center space-y-3">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
            <p className="text-muted-foreground">Loading call history...</p>
          </div>
        </div>
      ) : error ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-destructive">{error instanceof Error ? error.message : "Failed to load calls"}</p>
            <Button className="mt-3" onClick={() => window.location.reload()}>Retry</Button>
          </CardContent>
        </Card>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <HistoryIcon className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-semibold text-foreground">
              {search ? "No calls match your search" : "No call history yet"}
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              {search ? "Try a different search term." : "Calls will appear here after your first campaign runs."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/30">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Run ID</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Phone</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Agent</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Campaign</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Duration</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Date</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground"></th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((run) => (
                    <tr key={run.run_id} className="border-b last:border-0 hover:bg-muted/20 transition-colors">
                      <td className="px-4 py-3 font-mono text-xs">{run.run_id}</td>
                      <td className="px-4 py-3 font-mono">{run.phone_number ?? "-"}</td>
                      <td className="px-4 py-3">{run.workflow_name ?? "-"}</td>
                      <td className="px-4 py-3">{run.campaign_name ?? "-"}</td>
                      <td className="px-4 py-3"><CallStatusBadge status={run.status} /></td>
                      <td className="px-4 py-3">
                        {run.duration_seconds != null ? `${Math.round(run.duration_seconds)}s` : "-"}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {run.created_at ? new Date(run.created_at).toLocaleDateString() : "-"}
                      </td>
                      <td className="px-4 py-3">
                        <Button variant="ghost" size="sm" asChild>
                          <Link to={`/call-details/${run.run_id}`}>
                            <ExternalLink className="h-3 w-3" />
                          </Link>
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Page {page}{data ? ` of ${Math.ceil(data.total / limit)}` : ""}
        </p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page === 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!hasMore}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
