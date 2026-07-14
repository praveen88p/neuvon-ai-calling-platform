import { useEffect, useMemo, useState } from "react";
import { BookOpen, Plus, Edit, Trash2, FileText, Loader2 } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import { apiGet, apiPost, apiPatch, apiDelete } from "@/utils/api";

type KnowledgeBase = {
  id: string;
  name: string;
  description?: string;
  status?: string;
  type?: string;
  created_at?: string;
  updated_at?: string;
  documents?: number;
  campaigns?: number;
};

const formatDate = (value?: string) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
};

const KnowledgeBases = () => {
  const { toast } = useToast();
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    type: "text",
    name: "",
    description: "",
    text: "",
  });
  const [selectedKB, setSelectedKB] = useState<KnowledgeBase | null>(null);
  const [editData, setEditData] = useState({
    name: "",
    description: "",
  });
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const totalDocuments = useMemo(
    () => knowledgeBases.reduce((sum, kb) => sum + (kb.documents ?? 0), 0),
    [knowledgeBases]
  );

  const totalCampaigns = useMemo(
    () => knowledgeBases.reduce((sum, kb) => sum + (kb.campaigns ?? 0), 0),
    [knowledgeBases]
  );

  const fetchKnowledgeBases = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiGet("/api/knowledge-bases");
      const items: KnowledgeBase[] = result?.data?.kbs ?? [];
      setKnowledgeBases(items);
    } catch (err) {
      console.error("Failed to load knowledge bases", err);
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteKnowledgeBase = async (kb: KnowledgeBase) => {
    if (!kb?.id) return;
    const confirmed = window.confirm(
      `Delete knowledge base "${kb.name}"? This action cannot be undone.`
    );
    if (!confirmed) return;

    setDeletingId(kb.id);
    try {
      await apiDelete(`/api/knowledge-bases/${kb.id}`);

      toast({
        title: "Knowledge base deleted",
        description: `${kb.name} removed successfully`,
      });
      await fetchKnowledgeBases();
    } catch (err) {
      console.error("Failed to delete knowledge base", err);
      toast({
        title: "Unable to delete knowledge base",
        description: err instanceof Error ? err.message : "Please try again",
        variant: "destructive",
      });
    } finally {
      setDeletingId(null);
    }
  };

  const openEditDialog = (kb: KnowledgeBase) => {
    setSelectedKB(kb);
    setEditData({
      name: kb.name ?? "",
      description: kb.description ?? "",
    });
    setIsEditDialogOpen(true);
  };

  const handleUpdateKnowledgeBase = async () => {
    if (!selectedKB) return;

    const trimmedName = editData.name.trim();
    const trimmedDescription = editData.description.trim();

    if (!trimmedName && !trimmedDescription) {
      toast({
        title: "Nothing to update",
        description: "Provide an updated name or description",
        variant: "destructive",
      });
      return;
    }

    const payload: Record<string, string> = {};
    if (trimmedName) payload.name = trimmedName;
    if (trimmedDescription) payload.description = trimmedDescription;

    setIsUpdating(true);
    try {
      await apiPatch(`/api/knowledge-bases/${selectedKB.id}`, payload);

      toast({
        title: "Knowledge base updated",
        description: `${selectedKB.name} changes saved successfully`,
      });
      setIsEditDialogOpen(false);
      setSelectedKB(null);
      await fetchKnowledgeBases();
    } catch (err) {
      console.error("Failed to update knowledge base", err);
      toast({
        title: "Unable to update knowledge base",
        description: err instanceof Error ? err.message : "Please try again",
        variant: "destructive",
      });
    } finally {
      setIsUpdating(false);
    }
  };

  const handleCreateKnowledgeBase = async () => {
    if (!formData.name.trim()) {
      toast({
        title: "Name is required",
        description: "Please provide a name for the knowledge base",
        variant: "destructive",
      });
      return;
    }

    if (formData.type === "text" && !formData.text.trim()) {
      toast({
        title: "Text content required",
        description: "Provide text content when using the Text type",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);
    try {
      await apiPost("/api/knowledge-bases", {
        type: formData.type,
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
        text: formData.type === "text" ? formData.text.trim() : undefined,
      });

      toast({
        title: "Knowledge base created",
        description: `${formData.name.trim()} has been queued for processing`,
      });
      setFormData({ type: "text", name: "", description: "", text: "" });
      setIsDialogOpen(false);
      await fetchKnowledgeBases();
    } catch (err) {
      console.error("Failed to create knowledge base", err);
      toast({
        title: "Unable to create knowledge base",
        description: err instanceof Error ? err.message : "Please try again",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    fetchKnowledgeBases();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Knowledge Bases</h1>
          <p className="text-muted-foreground mt-2">
            Manage information and training data for AI
          </p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Knowledge Base
          </Button>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create knowledge base</DialogTitle>
              <DialogDescription>
                Provide context that will be synced with Bland.ai
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label>Type</Label>
                <Select
                  value={formData.type}
                  onValueChange={(value) =>
                    setFormData((prev) => ({ ...prev, type: value }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="text">Text</SelectItem>
                    <SelectItem value="file" disabled>
                      File (coming soon)
                    </SelectItem>
                    <SelectItem value="web_scrape" disabled>
                      Web scrape (coming soon)
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="kb-name">Name</Label>
                <Input
                  id="kb-name"
                  placeholder="Product FAQs"
                  value={formData.name}
                  onChange={(event) =>
                    setFormData((prev) => ({ ...prev, name: event.target.value }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="kb-description">Description</Label>
                <Textarea
                  id="kb-description"
                  placeholder="What topics are covered?"
                  value={formData.description}
                  onChange={(event) =>
                    setFormData((prev) => ({
                      ...prev,
                      description: event.target.value,
                    }))
                  }
                />
              </div>
              {formData.type === "text" && (
                <div className="space-y-2">
                  <Label htmlFor="kb-text">Text content</Label>
                  <Textarea
                    id="kb-text"
                    placeholder="Paste reference material"
                    className="min-h-[120px]"
                    value={formData.text}
                    onChange={(event) =>
                      setFormData((prev) => ({ ...prev, text: event.target.value }))
                    }
                  />
                </div>
              )}
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setIsDialogOpen(false)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button onClick={handleCreateKnowledgeBase} disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Knowledge Bases</CardTitle>
            <BookOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{knowledgeBases.length}</div>
            <p className="text-xs text-muted-foreground">Active knowledge bases</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalDocuments}</div>
            <p className="text-xs text-muted-foreground">Across all bases</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Use</CardTitle>
            <BookOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalCampaigns}</div>
            <p className="text-xs text-muted-foreground">Active campaigns (if provided)</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Knowledge Bases</CardTitle>
          <CardDescription>View and manage AI training data</CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <p className="text-sm text-destructive mb-4">
              {error}. Please try again.
            </p>
          )}
          {isLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading knowledge bases...
            </div>
          ) : knowledgeBases.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No knowledge bases yet. Create one to get started.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Last Updated</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {knowledgeBases.map((kb) => (
                  <TableRow key={kb.id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <BookOpen className="h-4 w-4 text-muted-foreground" />
                        {kb.name}
                      </div>
                    </TableCell>
                    <TableCell className="max-w-[320px] truncate">
                      {kb.description || "—"}
                    </TableCell>
                    <TableCell className="capitalize">{(kb.type || "text").toLowerCase()}</TableCell>
                    <TableCell>{formatDate(kb.updated_at || kb.created_at)}</TableCell>
                    <TableCell>
                      <Badge variant="default">{kb.status ?? "UNKNOWN"}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openEditDialog(kb)}
                          disabled={deletingId === kb.id}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteKnowledgeBase(kb)}
                          disabled={deletingId === kb.id}
                        >
                          {deletingId === kb.id ? (
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

      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit knowledge base</DialogTitle>
            <DialogDescription>
              Update the name or description for Bland.ai
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-kb-name">Name</Label>
              <Input
                id="edit-kb-name"
                value={editData.name}
                onChange={(event) =>
                  setEditData((prev) => ({ ...prev, name: event.target.value }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-kb-description">Description</Label>
              <Textarea
                id="edit-kb-description"
                value={editData.description}
                onChange={(event) =>
                  setEditData((prev) => ({
                    ...prev,
                    description: event.target.value,
                  }))
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsEditDialogOpen(false)}
              disabled={isUpdating}
            >
              Cancel
            </Button>
            <Button onClick={handleUpdateKnowledgeBase} disabled={isUpdating}>
              {isUpdating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default KnowledgeBases;
