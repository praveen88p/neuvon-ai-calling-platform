import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Play, Pause, RotateCcw, Loader2, PhoneCall, Users, CheckCircle, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { StatusBadge } from "@/components/StatusBadge";
import { KPICard } from "@/components/KPICard";
import { apiGet, apiPost } from "@/utils/api";
import { campaignPath, campaignProgressPath, campaignRunsPath, campaignStartPath, campaignPausePath, campaignResumePath, callRunPath } from "@/utils/apiPaths";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import type { CampaignResponse, CampaignProgressResponse, CallHistoryItem } from "@/types/api";

// ─── Status mapping ──────────────────────────────────────────────────────────

function mapStatus(status: string): "live" | "completed" | "paused" | "pending" {
  const s = status.toLowerCase();
  if (s === "running" || s === "active" || s === "live") return "live";
  if (s === "completed" || s === "done" || s === "finished") return "completed";
  if (s === "paused") return "paused";
  return "pending";
}

// ─── Campaign Details ────────────────────────────────────────────────────────

export default function CampaignDetails() {
  const { id } = useParams<{ id: string }>();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [campaign, setCampaign] = useState<CampaignResponse | null>(null);
  const [progress, setProgress] = useState<CampaignProgressResponse | null>(null);
  const [runs, setRuns] = useState<CallHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [campaignData, progressData, runsData] = await Promise.all([
          apiGet<CampaignResponse>(campaignPath(id)),
          apiGet<CampaignProgressResponse>(campaignProgressPath(id)).catch(() => null),
          apiGet<{ runs: CallHistoryItem[] }>(campaignRunsPath(id)).catch(() => ({ runs: [] })),
        ]);
        setCampaign(campaignData);
        setProgress(progressData);
        setRuns(runsData.runs ?? []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load campaign");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id]);

  const handleAction = async (action: "start" | "pause" | "resume") => {
    if (!id) return;
    const pathFn = action === "start" ? campaignStartPath : action === "pause" ? campaignPausePath : campaignResumePath;
    try {
      await apiPost(pathFn(id));
      toast({ title: `Campaign ${action}ed`, description: `Campaign has been ${action}ed successfully.` });
      // Refresh
      const updated = await apiGet<CampaignResponse>(campaignPath(id));
      setCampaign(updated);
      const updatedProgress = await apiGet<CampaignProgressResponse>(campaignProgressPath(id)).catch(() => null);
      setProgress(updatedProgress);
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    } catch (err: unknown) {
      toast({ title: "Action Failed", description: err instanceof Error ? err.message : "Unknown error", variant: "destructive" });
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
          <p className="text-muted-foreground">Loading campaign details...</p>
        </div>
      </div>
    );
  }

  if (error || !campaign) {
    return (
      <div className="p-8">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-bold text-foreground">{error || "Campaign not found"}</h1>
          <Button asChild className="mt-4">
            <Link to="/campaigns">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Campaigns
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  const displayStatus = mapStatus(campaign.status);
  const progressPercent = campaign.total_contacts > 0
    ? Math.round((campaign.contacts_processed / campaign.total_contacts) * 100)
    : 0;

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <Button variant="ghost" asChild className="mb-4">
          <Link to="/campaigns">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Campaigns
          </Link>
        </Button>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold text-foreground">{campaign.name}</h1>
              <StatusBadge status={displayStatus} />
            </div>
            <p className="text-muted-foreground">
              Agent ID: <span className="font-mono">{campaign.dograh_workflow_id}</span>
              {campaign.created_at && ` • Created ${new Date(campaign.created_at).toLocaleDateString()}`}
            </p>
          </div>
          <div className="flex gap-2">
            {displayStatus === "pending" && (
              <Button onClick={() => handleAction("start")}>
                <Play className="mr-2 h-4 w-4" />
                Start
              </Button>
            )}
            {displayStatus === "live" && (
              <Button variant="outline" onClick={() => handleAction("pause")}>
                <Pause className="mr-2 h-4 w-4" />
                Pause
              </Button>
            )}
            {displayStatus === "paused" && (
              <Button onClick={() => handleAction("resume")}>
                <RotateCcw className="mr-2 h-4 w-4" />
                Resume
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Progress */}
      <Card>
        <CardHeader>
          <CardTitle>Campaign Progress</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              {campaign.contacts_processed} of {campaign.total_contacts} contacts processed
            </span>
            <span className="font-medium text-foreground">{progressPercent}%</span>
          </div>
          <Progress value={progressPercent} className="h-2" />
        </CardContent>
      </Card>

      {/* KPIs from progress */}
      {progress && (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <KPICard
            title="Total Contacts"
            value={progress.total_contacts.toLocaleString()}
            icon={Users}
          />
          <KPICard
            title="Processed"
            value={progress.contacts_processed.toLocaleString()}
            change={`${progress.contacts_remaining} remaining`}
            icon={PhoneCall}
          />
          <KPICard
            title="Successful"
            value={progress.success_count.toLocaleString()}
            icon={CheckCircle}
            changeType="positive"
          />
          <KPICard
            title="In Progress"
            value={progress.in_progress_count.toLocaleString()}
            change={`${progress.failed_count} failed`}
            icon={Clock}
          />
        </div>
      )}

      {/* Call Runs */}
      <Card>
        <CardHeader>
          <CardTitle>Campaign Calls ({runs.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {runs.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No calls have been made for this campaign yet.
            </p>
          ) : (
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              <div className="grid grid-cols-6 gap-4 text-xs font-medium text-muted-foreground uppercase tracking-wider pb-2 border-b">
                <span>Run ID</span>
                <span>Phone</span>
                <span>Status</span>
                <span>Duration</span>
                <span>Disposition</span>
                <span>Date</span>
              </div>
              {runs.map((run) => (
                <Link
                  key={run.run_id}
                  to={`/call-details/${run.run_id}`}
                  className="grid grid-cols-6 gap-4 text-sm py-3 px-1 rounded hover:bg-muted/50 transition-colors cursor-pointer"
                >
                  <span className="font-mono text-xs">{run.run_id}</span>
                  <span className="font-mono">{run.phone_number ?? "-"}</span>
                  <span>
                    <StatusBadge
                      status={
                        run.status === "completed" ? "completed" :
                        run.status === "failed" ? "completed" :
                        "live"
                      }
                    />
                  </span>
                  <span>{run.duration_seconds ? `${Math.round(run.duration_seconds)}s` : "-"}</span>
                  <span className="capitalize">{run.disposition_code ?? "-"}</span>
                  <span className="text-muted-foreground">
                    {run.created_at ? new Date(run.created_at).toLocaleDateString() : "-"}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}