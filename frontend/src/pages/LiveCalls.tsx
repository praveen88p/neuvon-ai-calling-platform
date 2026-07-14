import { useState, useCallback } from "react";
import { Radio, Phone, Clock, Wifi, WifiOff } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useApiQuery } from "@/hooks/useApiQuery";
import { API_PATHS } from "@/utils/apiPaths";
import type { AnalyticsOverview, LiveCallUpdate } from "@/types/api";

interface ActiveCall {
  run_id: number;
  status: string;
  phone_number?: string;
  duration_seconds?: number;
  workflow_name?: string;
  started_at?: string;
}

export default function LiveCalls() {
  const [activeCalls, setActiveCalls] = useState<Map<number, ActiveCall>>(new Map());
  const [totalActive, setTotalActive] = useState(0);

  // Fetch overview for KPI counters
  const { data: overview } = useApiQuery<AnalyticsOverview>(
    ["analytics-overview"],
    API_PATHS.ANALYTICS_OVERVIEW,
    { staleTime: 30_000 },
  );

  const handleMessage = useCallback((msg: LiveCallUpdate) => {
    if (msg.type === "call_status" && msg.data) {
      setActiveCalls((prev) => {
        const next = new Map(prev);
        const call: ActiveCall = {
          run_id: msg.data!.run_id,
          status: msg.data!.status,
          phone_number: msg.data!.phone_number,
          duration_seconds: msg.data!.duration_seconds,
          workflow_name: msg.data!.workflow_name,
          started_at: msg.data!.started_at,
        };

        // Remove completed calls, update active ones
        if (msg.data!.status === "completed" || msg.data!.status === "failed") {
          next.delete(msg.data!.run_id);
        } else {
          next.set(msg.data!.run_id, call);
        }
        return next;
      });
    }
    if (msg.active_calls != null) {
      setTotalActive(msg.active_calls);
    }
  }, []);

  const { isConnected } = useWebSocket(API_PATHS.WS_LIVE_CALLS, {
    onMessage: handleMessage,
  });

  const callList = Array.from(activeCalls.values());

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Live Calls</h1>
          <p className="text-muted-foreground">Real-time call monitoring</p>
        </div>
        <div className="flex items-center gap-2">
          {isConnected ? (
            <span className="flex items-center gap-1.5 text-sm text-emerald-600">
              <Wifi className="h-4 w-4" />
              Connected
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-sm text-destructive">
              <WifiOff className="h-4 w-4" />
              Disconnected
            </span>
          )}
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Radio className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Active Calls</p>
              <p className="text-2xl font-bold">{totalActive || callList.length}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Phone className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Total Calls Today</p>
              <p className="text-2xl font-bold">{overview?.total_calls ?? 0}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Clock className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Total Minutes</p>
              <p className="text-2xl font-bold">{overview?.total_minutes?.toFixed(1) ?? 0}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Calls */}
      <Card>
        <CardHeader>
          <CardTitle>Active Calls ({callList.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {callList.length === 0 ? (
            <div className="py-12 text-center">
              <Radio className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
              <h3 className="text-lg font-semibold text-foreground">No active calls</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {isConnected
                  ? "Calls will appear here in real-time when they start."
                  : "Connecting to live call feed..."}
              </p>
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {callList.map((call) => (
                <Card key={call.run_id} className="border-l-4 border-l-primary">
                  <CardContent className="pt-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-sm">{call.phone_number ?? `Run #${call.run_id}`}</span>
                      <span className="inline-flex items-center rounded-full bg-emerald-100 text-emerald-700 px-2 py-0.5 text-xs font-medium">
                        {call.status}
                      </span>
                    </div>
                    {call.workflow_name && (
                      <p className="text-xs text-muted-foreground">Agent: {call.workflow_name}</p>
                    )}
                    {call.duration_seconds != null && (
                      <p className="text-xs text-muted-foreground">
                        Duration: {Math.round(call.duration_seconds)}s
                      </p>
                    )}
                    {call.started_at && (
                      <p className="text-xs text-muted-foreground">
                        Started: {new Date(call.started_at).toLocaleTimeString()}
                      </p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
