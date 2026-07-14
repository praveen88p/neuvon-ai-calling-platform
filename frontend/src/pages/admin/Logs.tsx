import { useState } from "react";
import { FileText, Loader2, Search } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiQuery } from "@/hooks/useApiQuery";
import { API_PATHS } from "@/utils/apiPaths";
import type { SystemLogListResponse } from "@/types/api";

const LEVEL_STYLES: Record<string, string> = {
  error: "bg-red-100 text-red-700",
  warn: "bg-yellow-100 text-yellow-700",
  warning: "bg-yellow-100 text-yellow-700",
  info: "bg-blue-100 text-blue-700",
  debug: "bg-gray-100 text-gray-600",
};

export default function Logs() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const limit = 50;

  const { data, isLoading, error } = useApiQuery<SystemLogListResponse>(
    ["admin-logs", page],
    `${API_PATHS.ADMIN_LOGS}?page=${page}&limit=${limit}`,
    { staleTime: 15_000, keepPreviousData: true },
  );

  const logs = data?.logs ?? [];
  const filtered = search
    ? logs.filter(
        (l) =>
          l.message.toLowerCase().includes(search.toLowerCase()) ||
          (l.source ?? "").toLowerCase().includes(search.toLowerCase()) ||
          l.level.toLowerCase().includes(search.toLowerCase()),
      )
    : logs;

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">System Logs</h1>
        <p className="text-muted-foreground">
          Real-time system and application logs
          {data && ` · ${data.total} entries`}
        </p>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search logs..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center min-h-[300px]">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : error ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-destructive">{error instanceof Error ? error.message : "Failed to load"}</p>
          </CardContent>
        </Card>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-semibold">No logs available</h3>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2 max-h-[600px] overflow-y-auto">
          {filtered.map((log) => (
            <div key={log.id} className="border rounded-lg p-3 space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium uppercase ${
                    LEVEL_STYLES[log.level.toLowerCase()] ?? LEVEL_STYLES.info
                  }`}>
                    {log.level}
                  </span>
                  {log.source && (
                    <span className="text-xs text-muted-foreground font-mono">{log.source}</span>
                  )}
                </div>
                <span className="text-xs text-muted-foreground">
                  {log.created_at ? new Date(log.created_at).toLocaleString() : "-"}
                </span>
              </div>
              <p className="text-sm">{log.message}</p>
              {log.details && Object.keys(log.details).length > 0 && (
                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto mt-1">
                  {JSON.stringify(log.details, null, 2)}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Page {page}{data ? ` of ${Math.ceil(data.total / limit)}` : ""}
        </p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Previous</Button>
          <Button variant="outline" size="sm" disabled={filtered.length < limit} onClick={() => setPage((p) => p + 1)}>Next</Button>
        </div>
      </div>
    </div>
  );
}
