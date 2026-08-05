import { useMemo } from "react";
import { Phone, Clock, TrendingUp, IndianRupee, Upload, Radio } from "lucide-react";
import { KPICard } from "@/components/KPICard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from "recharts";
import { useApiQuery } from "@/hooks/useApiQuery";
import { API_PATHS } from "@/utils/apiPaths";
import type {
  AnalyticsOverview,
  CallsOverTimeResponse,
  DispositionBreakdownResponse,
  CampaignPerformanceResponse,
} from "@/types/api";

// ─── Chart Colors ────────────────────────────────────────────────────────────

const DISPOSITION_COLORS: Record<string, string> = {
  completed: "var(--primary)",
  success: "var(--success, #22c55e)",
  failed: "var(--destructive)",
  busy: "var(--warning, #f59e0b)",
  no_answer: "var(--chart-3)",
  voicemail: "var(--chart-2)",
  error: "var(--destructive)",
};

const PIE_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "var(--primary)",
  "var(--destructive)",
];

// ─── Dashboard Component ────────────────────────────────────────────────────

export default function Dashboard() {
  // ── KPI Overview ──
  const {
    data: overview,
    isLoading: overviewLoading,
    error: overviewError,
  } = useApiQuery<AnalyticsOverview>(
    ["analytics-overview"],
    API_PATHS.ANALYTICS_OVERVIEW,
    { staleTime: 60_000 },
  );

  // ── Call Volume Over Time (line chart) ──
  const {
    data: callsOverTime,
    isLoading: callsTimeLoading,
    error: callsTimeError,
  } = useApiQuery<CallsOverTimeResponse>(
    ["calls-over-time"],
    `${API_PATHS.ANALYTICS_CALLS_OVER_TIME}?days=7`,
    { staleTime: 60_000 },
  );

  // ── Disposition Breakdown (pie chart) ──
  const {
    data: dispositionData,
    isLoading: dispositionLoading,
    error: dispositionError,
  } = useApiQuery<DispositionBreakdownResponse>(
    ["disposition-breakdown"],
    API_PATHS.ANALYTICS_DISPOSITION,
    { staleTime: 60_000 },
  );

  const dispositionItems = useMemo(() => {
    return (dispositionData?.data ?? [])
      .filter((item) => item.count > 0)
      .map((item, i) => ({
        name: item.disposition,
        value: item.count,
        color: DISPOSITION_COLORS[item.disposition.toLowerCase()] ?? PIE_COLORS[i % PIE_COLORS.length],
      }));
  }, [dispositionData]);

  // ── Campaign Performance (bar chart) ──
  const {
    data: campaignPerfData,
    isLoading: campaignPerfLoading,
    error: campaignPerfError,
  } = useApiQuery<CampaignPerformanceResponse>(
    ["campaign-performance"],
    API_PATHS.ANALYTICS_CAMPAIGN_PERF,
    { staleTime: 60_000 },
  );

  const campaignPerformance = useMemo(() => {
    return (campaignPerfData?.data ?? []).map((item) => ({
      campaign_name: item.campaign_name,
      total_calls: item.total_calls,
      total_minutes: Math.round(item.total_minutes * 10) / 10,
      success_rate: Math.round(item.success_rate * 10) / 10,
      status: item.status,
    }));
  }, [campaignPerfData]);

  // ── Format helpers ──
  const formatMinutes = (mins: number) => {
    if (mins < 60) return `${mins.toFixed(1)} min`;
    return `${(mins / 60).toFixed(1)} hrs`;
  };

  const formatDuration = (secs: number) => {
    if (secs < 60) return `${Math.round(secs)}s`;
    const m = Math.floor(secs / 60);
    const s = Math.round(secs % 60);
    return `${m}:${String(s).padStart(2, "0")}`;
  };

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground">Welcome back! Here's your campaign overview.</p>
        </div>
        <div className="flex gap-3">
          <Button asChild>
            <Link to="/upload">
              <Upload className="mr-2 h-4 w-4" />
              Upload Leads
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/live-calls">
              <Radio className="mr-2 h-4 w-4" />
              Live Calls
            </Link>
          </Button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {overviewLoading ? (
          <>
            {[1, 2, 3, 4].map((i) => (
              <Card key={i}>
                <CardContent className="pt-6">
                  <div className="animate-pulse space-y-2">
                    <div className="h-4 bg-muted rounded w-24" />
                    <div className="h-8 bg-muted rounded w-16" />
                    <div className="h-3 bg-muted rounded w-32" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </>
        ) : overviewError || !overview ? (
          <div className="col-span-4 text-center py-8">
            <p className="text-destructive">
              {overviewError instanceof Error ? overviewError.message : "Failed to load KPIs"}
            </p>
            <Button className="mt-2" onClick={() => window.location.reload()}>
              Retry
            </Button>
          </div>
        ) : (
          <>
            <KPICard
              title="Total Calls"
              value={overview.total_calls.toLocaleString()}
              change={`${overview.total_campaigns} active campaigns`}
              changeType="neutral"
              icon={Phone}
            />
            <KPICard
              title="Total Minutes"
              value={formatMinutes(overview.total_minutes)}
              change={`Avg ${formatDuration(overview.average_duration_seconds)}/call`}
              changeType="neutral"
              icon={Clock}
            />
            <KPICard
              title="Success Rate"
              value={`${overview.success_rate.toFixed(1)}%`}
              change={`${overview.total_agents} agents active`}
              changeType={overview.success_rate >= 50 ? "positive" : "negative"}
              icon={TrendingUp}
            />
            <KPICard
              title="Total Cost"
              value={`₹${overview.total_cost_usd.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
              change={`Across ${overview.total_campaigns} campaigns`}
              changeType="neutral"
              icon={IndianRupee}
            />
          </>
        )}
      </div>

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Call Volume Over Time */}
        <Card>
          <CardHeader>
            <CardTitle>Call Volume (Last 7 Days)</CardTitle>
          </CardHeader>
          <CardContent>
            {callsTimeLoading ? (
              <div className="flex items-center justify-center min-h-[300px]">
                <p className="text-sm text-muted-foreground">Loading call volume...</p>
              </div>
            ) : callsTimeError ? (
              <div className="flex items-center justify-center min-h-[300px]">
                <p className="text-sm text-destructive">
                  {callsTimeError instanceof Error ? callsTimeError.message : "Error"}
                </p>
              </div>
            ) : !callsOverTime?.data?.length ? (
              <div className="flex items-center justify-center min-h-[300px]">
                <p className="text-sm text-muted-foreground">No call data yet</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={callsOverTime.data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="date"
                    stroke="var(--muted-foreground)"
                    tickFormatter={(d) => new Date(d).toLocaleDateString("en-US", { weekday: "short" })}
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis stroke="var(--muted-foreground)" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--card)",
                      border: "1px solid var(--border)",
                      borderRadius: "8px",
                    }}
                    labelFormatter={(d) =>
                      new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" })
                    }
                  />
                  <Legend verticalAlign="top" />
                  <Line
                    type="monotone"
                    dataKey="calls"
                    stroke="var(--primary)"
                    strokeWidth={2}
                    name="Calls"
                    dot={{ r: 4, fill: "var(--primary)" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="success_count"
                    stroke="var(--chart-2)"
                    strokeWidth={2}
                    name="Successful"
                    dot={{ r: 3, fill: "var(--chart-2)" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Disposition Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle>Call Outcomes</CardTitle>
          </CardHeader>
          <CardContent>
            {dispositionLoading ? (
              <div className="flex items-center justify-center min-h-[300px]">
                <p className="text-sm text-muted-foreground">Loading outcomes...</p>
              </div>
            ) : dispositionError ? (
              <div className="flex items-center justify-center min-h-[300px]">
                <p className="text-sm text-destructive">
                  {dispositionError instanceof Error ? dispositionError.message : "Error"}
                </p>
              </div>
            ) : dispositionItems.length === 0 ? (
              <div className="flex items-center justify-center min-h-[300px]">
                <p className="text-sm text-muted-foreground">No outcome data yet</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={dispositionItems}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {dispositionItems.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--card)",
                      border: "1px solid var(--border)",
                      borderRadius: "8px",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Campaign Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Campaign Performance</CardTitle>
        </CardHeader>
        <CardContent>
          {campaignPerfLoading ? (
            <div className="flex items-center justify-center min-h-[300px]">
              <p className="text-sm text-muted-foreground">Loading campaign performance...</p>
            </div>
          ) : campaignPerfError ? (
            <div className="flex items-center justify-center min-h-[300px]">
              <p className="text-sm text-destructive">
                {campaignPerfError instanceof Error ? campaignPerfError.message : "Error"}
              </p>
            </div>
          ) : campaignPerformance.length === 0 ? (
            <div className="flex items-center justify-center min-h-[300px]">
              <p className="text-sm text-muted-foreground">No campaigns yet. Create one to see performance data.</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={340}>
              <BarChart
                data={campaignPerformance}
                margin={{ top: 30, right: 10, left: 0, bottom: 60 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis
                  dataKey="campaign_name"
                  stroke="var(--muted-foreground)"
                  interval={0}
                  angle={-25}
                  textAnchor="end"
                  height={80}
                  tick={{ fontSize: 11 }}
                />
                <YAxis stroke="var(--muted-foreground)" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                  }}
                />
                <Legend verticalAlign="top" align="center" wrapperStyle={{ paddingBottom: 12 }} />
                <Bar dataKey="total_calls" name="Total Calls" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="total_minutes" name="Minutes" fill="var(--chart-2)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="success_rate" name="Success %" fill="var(--chart-5)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
