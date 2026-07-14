import { useState, useMemo } from "react";
import { Plus, Search, Loader2, Play, Pause, RotateCcw, Megaphone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { Progress } from "@/components/ui/progress";
import { Link } from "react-router-dom";
import { useApiQuery } from "@/hooks/useApiQuery";
import { apiPost } from "@/utils/api";
import { API_PATHS, campaignStartPath, campaignPausePath, campaignResumePath } from "@/utils/apiPaths";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import type { CampaignListResponse, CampaignResponse } from "@/types/api";

// ─── Status mapping ──────────────────────────────────────────────────────────

function mapStatus(status: string): "live" | "completed" | "paused" | "pending" {
  const s = status.toLowerCase();
  if (s === "running" || s === "active" || s === "live") return "live";
  if (s === "completed" || s === "done" || s === "finished") return "completed";
  if (s === "paused") return "paused";
  return "pending";
}

// ─── Campaigns Page ──────────────────────────────────────────────────────────

export default function Campaigns() {
  const [searchQuery, setSearchQuery] = useState("");
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading: loading, error } = useApiQuery<CampaignListResponse>(
    ["campaigns"],
    API_PATHS.CAMPAIGNS,
    { staleTime: 30_000 },
  );

  const campaigns = data?.campaigns ?? [];

  const filteredCampaigns = useMemo(
    () =>
      campaigns.filter((c) =>
        c.name.toLowerCase().includes(searchQuery.toLowerCase()),
      ),
    [campaigns, searchQuery],
  );

  const handleAction = async (campaign: CampaignResponse, action: "start" | "pause" | "resume") => {
    const pathFn = action === "start" ? campaignStartPath : action === "pause" ? campaignPausePath : campaignResumePath;
    try {
      await apiPost(pathFn(campaign.id));
      toast({
        title: `Campaign ${action === "start" ? "Started" : action === "pause" ? "Paused" : "Resumed"}`,
        description: `${campaign.name} has been ${action}ed.`,
      });
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    } catch (err: unknown) {
      toast({
        title: "Action Failed",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
          <p className="text-muted-foreground">Loading campaigns...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="text-center space-y-4">
          <p className="text-destructive">
            Error loading campaigns: {error instanceof Error ? error.message : "Unknown error"}
          </p>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Campaigns</h1>
          <p className="text-muted-foreground">Manage and monitor your calling campaigns</p>
        </div>
        <Button asChild>
          <Link to="/upload">
            <Plus className="mr-2 h-4 w-4" />
            New Campaign
          </Link>
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search campaigns..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Campaign Grid */}
      {filteredCampaigns.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Megaphone className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-semibold text-foreground">
              {searchQuery ? "No campaigns match your search" : "No campaigns yet"}
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              {searchQuery ? "Try a different search term." : "Upload leads to create your first campaign."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {filteredCampaigns.map((campaign) => {
            const progress =
              campaign.total_contacts > 0
                ? Math.round((campaign.contacts_processed / campaign.total_contacts) * 100)
                : 0;
            const displayStatus = mapStatus(campaign.status);

            return (
              <Card key={campaign.id} className="transition-all hover:shadow-lg">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="space-y-1 min-w-0 flex-1">
                      <Link to={`/campaigns/${campaign.id}`}>
                        <CardTitle className="hover:underline cursor-pointer">
                          {campaign.name}
                        </CardTitle>
                      </Link>
                      <p className="text-sm text-muted-foreground">
                        {campaign.total_contacts} contacts • Concurrency: {campaign.concurrency}
                      </p>
                    </div>
                    <StatusBadge status={displayStatus} />
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Progress bar */}
                  <div>
                    <div className="mb-2 flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Progress</span>
                      <span className="font-medium text-foreground">{progress}%</span>
                    </div>
                    <Progress value={progress} className="h-2" />
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-3 gap-4 pt-2">
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">Total</p>
                      <p className="text-2xl font-bold text-foreground">{campaign.total_contacts}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">Processed</p>
                      <p className="text-2xl font-bold text-foreground">{campaign.contacts_processed}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">Status</p>
                      <p className="text-sm font-medium text-foreground capitalize">{campaign.status}</p>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 pt-2">
                    {displayStatus === "pending" && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => { e.preventDefault(); handleAction(campaign, "start"); }}
                      >
                        <Play className="mr-1 h-3 w-3" />
                        Start
                      </Button>
                    )}
                    {displayStatus === "live" && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => { e.preventDefault(); handleAction(campaign, "pause"); }}
                      >
                        <Pause className="mr-1 h-3 w-3" />
                        Pause
                      </Button>
                    )}
                    {displayStatus === "paused" && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => { e.preventDefault(); handleAction(campaign, "resume"); }}
                      >
                        <RotateCcw className="mr-1 h-3 w-3" />
                        Resume
                      </Button>
                    )}
                    <Button size="sm" variant="ghost" asChild>
                      <Link to={`/campaigns/${campaign.id}`}>View Details</Link>
                    </Button>
                  </div>

                  {/* Created date */}
                  {campaign.created_at && (
                    <p className="text-xs text-muted-foreground pt-1">
                      Created {new Date(campaign.created_at).toLocaleDateString()}
                    </p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Total count */}
      {data && (
        <p className="text-sm text-muted-foreground">
          {data.total} campaign{data.total !== 1 ? "s" : ""} total
        </p>
      )}
    </div>
  );
}