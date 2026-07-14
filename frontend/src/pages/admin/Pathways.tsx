import { useCallback, useEffect, useMemo, useState } from "react";
import { GitBranch, Plus, Edit, Trash2, Loader2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/use-toast";
import { apiGet, apiPost, apiDelete } from "@/utils/api";

type Pathway = {
  id: string;
  name: string;
  description?: string;
  steps?: number;
  campaigns?: number;
  status?: string;
  createdAt: string;
};

const STORAGE_KEY = "ai-call-manager:pathways";

const Pathways = () => {
  const { toast } = useToast();
  const [pathways, setPathways] = useState<Pathway[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [dialogMode, setDialogMode] = useState<"create" | "edit">("create");
  const [editingPathway, setEditingPathway] = useState<Pathway | null>(null);
  const [formData, setFormData] = useState({ name: "", description: "" });
  const [isLoading, setIsLoading] = useState(true);

  const totalSteps = useMemo(
    () => pathways.reduce((sum, pathway) => sum + (pathway.steps ?? 0), 0),
    [pathways]
  );

  const totalCampaigns = useMemo(
    () => pathways.reduce((sum, pathway) => sum + (pathway.campaigns ?? 0), 0),
    [pathways]
  );

  const savePathways = useCallback((next: Pathway[]) => {
    setPathways(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch (error) {
      console.error("Failed to persist pathways", error);
    }
  }, []);

  const fetchPathways = useCallback(async () => {
    setIsLoading(true);
    const fallbackId = () =>
      `pathway-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    try {
      const result = await apiGet("/api/pathways");
      const rawPathways =
        result?.data?.pathways ??
        result?.data?.items ??
        (Array.isArray(result?.data) ? result.data : []);

      const normalized = Array.isArray(rawPathways)
        ? rawPathways.map((item: any): Pathway => {
            const stepsCount =
              typeof item?.steps === "number"
                ? item.steps
                : Array.isArray(item?.nodes)
                  ? item.nodes.length
                  : typeof item?.step_count === "number"
                    ? item.step_count
                    : undefined;

            const campaignCount =
              typeof item?.campaigns === "number"
                ? item.campaigns
                : typeof item?.campaign_count === "number"
                  ? item.campaign_count
                  : undefined;

            return {
              id: String(
                item?.id ??
                  item?.pathway_id ??
                  item?._id ??
                  fallbackId()
              ),
              name: item?.name ?? item?.title ?? "Untitled pathway",
              description: item?.description ?? item?.summary ?? "",
              steps: stepsCount,
              campaigns: campaignCount,
              status: item?.status ?? item?.state ?? "active",
              createdAt:
                item?.createdAt ??
                item?.created_at ??
                new Date().toISOString(),
            };
          })
        : [];

      savePathways(normalized);
    } catch (error) {
      console.error("Failed to fetch pathways", error);
      toast({
        title: "Unable to load pathways",
        description:
          error instanceof Error
            ? error.message
            : "Please try again or check the backend logs.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }, [savePathways, toast]);

  useEffect(() => {
    try {
      const cached = localStorage.getItem(STORAGE_KEY);
      if (cached) {
        setPathways(JSON.parse(cached));
      }
    } catch (error) {
      console.error("Failed to load stored pathways", error);
    }

    fetchPathways();
  }, [fetchPathways]);

  const handleDeletePathway = async (pathwayId: string, pathwayName: string) => {
    const confirmed = window.confirm(
      `Delete pathway "${pathwayName}"? This cannot be undone.`
    );
    if (!confirmed) {
      return;
    }

    setDeletingId(pathwayId);
    try {
      await apiDelete(`/api/pathways/${pathwayId}`);

      savePathways(pathways.filter((pathway) => pathway.id !== pathwayId));
      await fetchPathways();
      toast({
        title: "Pathway deleted",
        description: `Removed pathway “${pathwayName}”`,
      });
    } catch (error) {
      console.error("Failed to delete pathway", error);
      toast({
        title: "Unable to delete pathway",
        description:
          error instanceof Error
            ? error.message
            : "Please try again or check the backend logs.",
        variant: "destructive",
      });
    } finally {
      setDeletingId(null);
    }
  };

  const openCreateDialog = () => {
    setDialogMode("create");
    setEditingPathway(null);
    setFormData({ name: "", description: "" });
    setIsDialogOpen(true);
  };

  const openEditDialog = (pathway: Pathway) => {
    setDialogMode("edit");
    setEditingPathway(pathway);
    setFormData({
      name: pathway.name,
      description: pathway.description ?? "",
    });
    setIsDialogOpen(true);
  };

  const handleSavePathway = async () => {
    if (!formData.name.trim()) {
      toast({
        title: "Name is required",
        description: "Please provide a name for the pathway",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);
    try {
      if (dialogMode === "create") {
        const result = await apiPost("/api/pathways", {
          name: formData.name.trim(),
          description: formData.description.trim() || undefined,
        });
        const pathwayId = result?.data?.pathway_id ?? `local-${Date.now()}`;
        const newPathway: Pathway = {
          id: pathwayId,
          name: formData.name.trim(),
          description: formData.description.trim(),
          campaigns: 0,
          steps: 0,
          status: result?.data?.status ?? "active",
          createdAt: new Date().toISOString(),
        };

        savePathways([newPathway, ...pathways]);
        toast({
          title: "Pathway created",
          description: `Created pathway “${newPathway.name}”`,
        });
        await fetchPathways();
      } else if (editingPathway) {
        await apiPost(`/api/pathways/${editingPathway.id}`, {
          name: formData.name.trim(),
          description: formData.description.trim() || undefined,
        });

        const updatedPathway: Pathway = {
          ...editingPathway,
          name: formData.name.trim(),
          description: formData.description.trim(),
        };

        savePathways(
          pathways.map((pathway) =>
            pathway.id === editingPathway.id ? updatedPathway : pathway
          )
        );

        toast({
          title: "Pathway updated",
          description: `Updated pathway “${updatedPathway.name}”`,
        });
        await fetchPathways();
      }

      setFormData({ name: "", description: "" });
      setEditingPathway(null);
      setIsDialogOpen(false);
    } catch (error) {
      console.error("Failed to create pathway", error);
      toast({
        title: "Unable to create pathway",
        description:
          error instanceof Error
            ? error.message
            : "Please try again or check the backend logs.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Pathways</h1>
          <p className="text-muted-foreground mt-2">
            Manage conversation flows and call scripts
          </p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <Button onClick={openCreateDialog}>
            <Plus className="h-4 w-4 mr-2" />
            Create Pathway
          </Button>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {dialogMode === "create" ? "Create pathway" : "Edit pathway"}
              </DialogTitle>
              <DialogDescription>
                Provide a name and optional description. Changes sync with Bland.ai.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  placeholder="Qualification Flow"
                  value={formData.name}
                  onChange={(event) =>
                    setFormData((prev) => ({ ...prev, name: event.target.value }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="High-level context for this pathway"
                  value={formData.description}
                  onChange={(event) =>
                    setFormData((prev) => ({ ...prev, description: event.target.value }))
                  }
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsDialogOpen(false)} disabled={isSubmitting}>
                Cancel
              </Button>
              <Button onClick={handleSavePathway} disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {dialogMode === "create" ? "Create" : "Save"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Pathways</CardTitle>
            <GitBranch className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pathways.length}</div>
            <p className="text-xs text-muted-foreground">Active conversation flows</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Steps</CardTitle>
            <GitBranch className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalSteps}</div>
            <p className="text-xs text-muted-foreground">Across all pathways</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Use</CardTitle>
            <GitBranch className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalCampaigns}</div>
            <p className="text-xs text-muted-foreground">Active campaigns</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Pathways</CardTitle>
          <CardDescription>View and manage conversation pathways</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading pathways...
            </div>
          ) : pathways.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No pathways yet. Create one to get started.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Steps</TableHead>
                  <TableHead>Campaigns</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pathways.map((pathway) => (
                  <TableRow key={pathway.id}>
                    <TableCell className="font-medium">{pathway.name}</TableCell>
                    <TableCell className="max-w-[300px] truncate">
                      {pathway.description || "—"}
                    </TableCell>
                    <TableCell>{pathway.steps ?? "—"}</TableCell>
                    <TableCell>{pathway.campaigns ?? "—"}</TableCell>
                    <TableCell>
                      <Badge variant="default">{pathway.status ?? "active"}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openEditDialog(pathway)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeletePathway(pathway.id, pathway.name)}
                          disabled={deletingId === pathway.id}
                        >
                          {deletingId === pathway.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default Pathways;
