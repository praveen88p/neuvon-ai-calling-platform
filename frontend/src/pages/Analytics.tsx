import { useState, useMemo } from "react";
import { BarChart3, TrendingUp, Phone, Clock, DollarSign, Users } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { KPICard } from "@/components/KPICard";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { useApiQuery } from "@/hooks/useApiQuery";
import { API_PATHS } from "@/utils/apiPaths";
import type {
  AnalyticsOverview,
  CallsOverTimeResponse,
  DispositionBreakdownResponse,
  AgentPerformanceResponse,
  CampaignPerformanceResponse,
} from "@/types/api";

const PIE_COLORS = [
  "var(--chart-1)", "var(--chart-2)", "var(--chart-3)",
  "var(--chart-4)", "var(--chart-5)", "var(--primary)", "var(--destructive)",
];

export default function Analytics() {
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split("T")[0]);

  const dateParams = `?start_date=${startDate}&end_date=${endDate}`;

  // ── Queries ──
  const { data: overview, isLoading: overviewLoading } = useApiQuery<AnalyticsOverview>(
    ["analytics-overview", startDate, endDate],
    `${API_PATHS.ANALYTICS_OVERVIEW}${dateParams}`,
    { staleTime: 60_000 },
  );

  const { data: callsOverTime } = useApiQuery<CallsOverTimeResponse>(
    ["calls-over-time", startDate, endDate],
    `${API_PATHS.ANALYTICS_CALLS_OVER_TIME}${dateParams}`,
    { staleTime: 60_000 },
  );

  const { data: dispositionData } = useApiQuery<DispositionBreakdownResponse>(
    ["disposition", startDate, endDate],
    `${API_PATHS.ANALYTICS_DISPOSITION}${dateParams}`,
    { staleTime: 60_000 },
  );

  const { data: agentPerfData } = useApiQuery<AgentPerformanceResponse>(
    ["agent-perf", startDate, endDate],
    `${API_PATHS.ANALYTICS_AGENT_PERF}${dateParams}`,
    { staleTime: 60_000 },
  );

  const { data: campaignPerfData } = useApiQuery<CampaignPerformanceResponse>(
    ["campaign-perf", startDate, endDate],
    `${API_PATHS.ANALYTICS_CAMPAIGN_PERF}${dateParams}`,
    { staleTime: 60_000 },
  );

  const pieData = useMemo(
    () =>
      (dispositionData?.data ?? [])
        .filter((d) => d.count > 0)
        .map((d, i) => ({
          name: d.disposition,
          value: d.count,
          color: PIE_COLORS[i % PIE_COLORS.length],
        })),
    [dispositionData],
  );

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Analytics</h1>
          <p className="text-muted-foreground">Detailed performance metrics and insights</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="space-y-1">
            <Label className="text-xs">Start</Label>
            <Input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-36"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">End</Label>
            <Input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-36"
            />
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Total Calls"
          value={overviewLoading ? "..." : (overview?.total_calls ?? 0).toLocaleString()}
          icon={Phone}
        />
        <KPICard
          title="Total Minutes"
          value={overviewLoading ? "..." : `${(overview?.total_minutes ?? 0).toFixed(1)}`}
          icon={Clock}
        />
        <KPICard
          title="Success Rate"
          value={overviewLoading ? "..." : `${(overview?.success_rate ?? 0).toFixed(1)}%`}
          icon={TrendingUp}
          changeType={(overview?.success_rate ?? 0) >= 50 ? "positive" : "negative"}
        />
        <KPICard
          title="Total Cost"
          value={overviewLoading ? "..." : `$${(overview?.total_cost_usd ?? 0).toFixed(2)}`}
          icon={DollarSign}
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Call Volume Over Time */}
        <Card>
          <CardHeader><CardTitle>Call Volume Over Time</CardTitle></CardHeader>
          <CardContent>
            {!callsOverTime?.data?.length ? (
              <div className="flex items-center justify-center min-h-[300px]">
                <p className="text-sm text-muted-foreground">No data for selected period</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={callsOverTime.data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="date"
                    stroke="var(--muted-foreground)"
                    tickFormatter={(d) => new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis stroke="var(--muted-foreground)" />
                  <Tooltip
                    contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: "8px" }}
                  />
                  <Legend verticalAlign="top" />
                  <Line type="monotone" dataKey="calls" stroke="var(--primary)" strokeWidth={2} name="Calls" dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="success_count" stroke="var(--chart-2)" strokeWidth={2} name="Successful" dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="failed_count" stroke="var(--destructive)" strokeWidth={2} name="Failed" dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Disposition Breakdown */}
        <Card>
          <CardHeader><CardTitle>Disposition Breakdown</CardTitle></CardHeader>
          <CardContent>
            {pieData.length === 0 ? (
              <div className="flex items-center justify-center min-h-[300px]">
                <p className="text-sm text-muted-foreground">No disposition data</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={100}
                    dataKey="value"
                  >
                    {pieData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: "8px" }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Agent Performance */}
        <Card>
          <CardHeader><CardTitle>Agent Performance</CardTitle></CardHeader>
          <CardContent>
            {!agentPerfData?.data?.length ? (
              <div className="flex items-center justify-center min-h-[300px]">
                <p className="text-sm text-muted-foreground">No agent data</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={agentPerfData.data} margin={{ top: 10, right: 10, left: 0, bottom: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="agent_name" stroke="var(--muted-foreground)" interval={0} angle={-20} textAnchor="end" height={60} tick={{ fontSize: 11 }} />
                  <YAxis stroke="var(--muted-foreground)" />
                  <Tooltip contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: "8px" }} />
                  <Legend verticalAlign="top" />
                  <Bar dataKey="total_calls" name="Calls" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="success_rate" name="Success %" fill="var(--chart-2)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Campaign Performance */}
        <Card>
          <CardHeader><CardTitle>Campaign Performance</CardTitle></CardHeader>
          <CardContent>
            {!campaignPerfData?.data?.length ? (
              <div className="flex items-center justify-center min-h-[300px]">
                <p className="text-sm text-muted-foreground">No campaign data</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={campaignPerfData.data} margin={{ top: 10, right: 10, left: 0, bottom: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="campaign_name" stroke="var(--muted-foreground)" interval={0} angle={-20} textAnchor="end" height={60} tick={{ fontSize: 11 }} />
                  <YAxis stroke="var(--muted-foreground)" />
                  <Tooltip contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: "8px" }} />
                  <Legend verticalAlign="top" />
                  <Bar dataKey="total_calls" name="Calls" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="total_minutes" name="Minutes" fill="var(--chart-5)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}