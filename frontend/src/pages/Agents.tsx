import { useState } from "react";
import { Bot, Plus, Archive, RotateCcw, Play, Loader2, Search } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiQuery } from "@/hooks/useApiQuery";
import { apiPost, apiPatch, apiDelete } from "@/utils/api";
import { API_PATHS, agentPath, agentStatusPath, agentTestRunPath } from "@/utils/apiPaths";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { AgentListResponse, AgentResponse } from "@/types/api";

// ─── Status badge ────────────────────────────────────────────────────────────

function AgentStatusBadge({ status }: { status: string | null }) {
  const s = status?.toLowerCase() ?? "unknown";
  const colorMap: Record<string, string> = {
    active: "bg-emerald-100 text-emerald-700",
    archived: "bg-gray-100 text-gray-500",
  };
  const classes = colorMap[s] ?? "bg-gray-100 text-gray-500";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${classes}`}>
      {s.charAt(0).toUpperCase() + s.slice(1)}
    </span>
  );
}

// ─── Create Agent Dialog ─────────────────────────────────────────────────────

function CreateAgentDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [callType, setCallType] = useState("outbound");
  const [useCase, setUseCase] = useState("");
  const [activityDescription, setActivityDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handleCreate = async () => {
    if (!name.trim() || !useCase.trim() || !activityDescription.trim()) {
      toast({ title: "Validation Error", description: "Name, use case, and description are required.", variant: "destructive" });
      return;
    }
    setLoading(true);
    try {
      await apiPost(API_PATHS.AGENTS_FROM_TEMPLATE, {
        name: name.trim(),
        call_type: callType,
        use_case: useCase.trim(),
        activity_description: activityDescription.trim(),
      });
      toast({ title: "Agent Created", description: `${name} has been created successfully.` });
      setOpen(false);
      setName("");
      setCallType("outbound");
      setUseCase("");
      setActivityDescription("");
      onCreated();
    } catch (err: unknown) {
      toast({
        title: "Failed to create agent",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Create Agent
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Create New Agent</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="agent-name">Name</Label>
            <Input
              id="agent-name"
              placeholder="e.g. Lead Qualifier"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="agent-call-type">Call Type</Label>
            <select
              id="agent-call-type"
              value={callType}
              onChange={(e) => setCallType(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <option value="outbound">Outbound</option>
              <option value="inbound">Inbound</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="agent-use-case">Use Case</Label>
            <Input
              id="agent-use-case"
              placeholder="e.g. appointment_reminder, lead_qualification"
              value={useCase}
              onChange={(e) => setUseCase(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Short label for the type of call (e.g. lead_qualification, appointment_reminder).
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="agent-desc">Activity Description</Label>
            <Textarea
              id="agent-desc"
              placeholder="Describe what this agent should do. E.g. 'Qualify inbound leads by asking about budget, timeline, and needs.'"
              value={activityDescription}
              onChange={(e) => setActivityDescription(e.target.value)}
              rows={4}
            />
            <p className="text-xs text-muted-foreground">
              A Dograh workflow will be generated from this description.
            </p>
          </div>
          <Button onClick={handleCreate} disabled={loading} className="w-full">
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Create Agent
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Agents Page ─────────────────────────────────────────────────────────────

export default function Agents() {
  const [search, setSearch] = useState("");
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data, isLoading, error } = useApiQuery<AgentListResponse>(
    ["agents"],
    API_PATHS.AGENTS,
    { staleTime: 30_000 },
  );

  const agents = data?.agents ?? [];
  const filtered = agents.filter((a) =>
    a.name.toLowerCase().includes(search.toLowerCase()),
  );

  const handleArchiveRestore = async (agent: AgentResponse) => {
    const newStatus = agent.status === "active" ? "archived" : "active";
    try {
      await apiPatch(agentStatusPath(agent.workflow_id), { status: newStatus });
      toast({
        title: newStatus === "archived" ? "Agent Archived" : "Agent Restored",
        description: `${agent.name} has been ${newStatus === "archived" ? "archived" : "restored"}.`,
      });
      queryClient.invalidateQueries({ queryKey: ["agents"] });
    } catch (err: unknown) {
      toast({
        title: "Action Failed",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const handleTestRun = async (agent: AgentResponse) => {
    try {
      await apiPost(agentTestRunPath(agent.workflow_id), {});
      toast({ title: "Test Run Started", description: `Test run triggered for ${agent.name}.` });
    } catch (err: unknown) {
      toast({
        title: "Test Run Failed",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const refreshAgents = () => {
    queryClient.invalidateQueries({ queryKey: ["agents"] });
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Agents</h1>
          <p className="text-muted-foreground">
            Manage your AI calling agents (Dograh workflows).
          </p>
        </div>
        <CreateAgentDialog onCreated={refreshAgents} />
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search agents..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Agent List */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <div className="animate-pulse space-y-3">
                  <div className="h-5 bg-muted rounded w-32" />
                  <div className="h-4 bg-muted rounded w-48" />
                  <div className="h-4 bg-muted rounded w-24" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : error ? (
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-destructive">
              {error instanceof Error ? error.message : "Failed to load agents"}
            </p>
            <Button className="mt-3" onClick={refreshAgents}>
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center py-12">
            <Bot className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-semibold text-foreground">
              {search ? "No agents match your search" : "No agents yet"}
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              {search
                ? "Try a different search term."
                : "Create your first AI agent to start making calls."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((agent) => (
            <Card key={agent.workflow_id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <CardTitle className="text-base font-semibold">{agent.name}</CardTitle>
                  <AgentStatusBadge status={agent.status} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between text-muted-foreground">
                    <span>Workflow ID</span>
                    <span className="font-mono text-foreground">{agent.workflow_id}</span>
                  </div>
                  {agent.created_at && (
                    <div className="flex justify-between text-muted-foreground">
                      <span>Created</span>
                      <span className="text-foreground">
                        {new Date(agent.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                  <div className="flex gap-2 pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleTestRun(agent)}
                      disabled={agent.status === "archived"}
                    >
                      <Play className="mr-1 h-3 w-3" />
                      Test
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleArchiveRestore(agent)}
                    >
                      {agent.status === "active" ? (
                        <>
                          <Archive className="mr-1 h-3 w-3" />
                          Archive
                        </>
                      ) : (
                        <>
                          <RotateCcw className="mr-1 h-3 w-3" />
                          Restore
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Total Count */}
      {data && (
        <p className="text-sm text-muted-foreground">
          {data.total} agent{data.total !== 1 ? "s" : ""} total
          {search && ` · ${filtered.length} matching`}
        </p>
      )}
    </div>
  );
}
