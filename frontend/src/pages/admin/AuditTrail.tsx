import { useState } from "react";
import { Shield, Loader2, Search, Filter } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiQuery } from "@/hooks/useApiQuery";
import { API_PATHS } from "@/utils/apiPaths";
import type { AuditLogListResponse } from "@/types/api";

export default function AuditTrail() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const limit = 25;

  const { data, isLoading, error } = useApiQuery<AuditLogListResponse>(
    ["admin-audit", page],
    `${API_PATHS.ADMIN_AUDIT}?page=${page}&limit=${limit}`,
    { staleTime: 30_000, keepPreviousData: true },
  );

  const logs = data?.logs ?? [];
  const filtered = search
    ? logs.filter(
        (l) =>
          l.action.toLowerCase().includes(search.toLowerCase()) ||
          (l.resource_type ?? "").toLowerCase().includes(search.toLowerCase()) ||
          (l.user_id ?? "").includes(search),
      )
    : logs;

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Audit Trail</h1>
        <p className="text-muted-foreground">
          Track all user actions across the platform
          {data && ` · ${data.total} events`}
        </p>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search by action, resource, or user..."
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
            <Shield className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-semibold">No audit events</h3>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/30">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Action</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Resource</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">User</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">IP</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((log) => (
                    <tr key={log.id} className="border-b last:border-0 hover:bg-muted/20">
                      <td className="px-4 py-3 font-medium">{log.action}</td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {log.resource_type ?? "-"}
                        {log.resource_id ? ` #${log.resource_id}` : ""}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs">{log.user_id ?? "-"}</td>
                      <td className="px-4 py-3 font-mono text-xs">{log.ip_address ?? "-"}</td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {log.created_at ? new Date(log.created_at).toLocaleString() : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
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
