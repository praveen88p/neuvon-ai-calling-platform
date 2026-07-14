import { useCallback, useEffect, useMemo, useState } from "react";
import { Users, Plus, Edit, Mic, Loader2, History } from "lucide-react";
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
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/use-toast";
import { apiGet, apiPost, apiPatch } from "@/utils/api";

type Persona = {
  id: string;
  name: string;
  voice?: string;
  role?: string;
  status?: string;
  description?: string;
  pathways?: string[];
  campaigns?: number;
  updatedAt?: string;
};

type PersonaForm = {
  name: string;
  role: string;
  voice: string;
  description: string;
  pathways: string;
  settings: string;
};

const defaultForm: PersonaForm = {
  name: "",
  role: "",
  voice: "",
  description: "",
  pathways: "",
  settings: "",
};

const fallbackId = () => `persona-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const Personas = () => {
  const { toast } = useToast();
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<"create" | "edit">("create");
  const [formData, setFormData] = useState<PersonaForm>(defaultForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [formLoading, setFormLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [versionsOpen, setVersionsOpen] = useState(false);
  const [versionsPersona, setVersionsPersona] = useState<string | null>(null);
  const [versions, setVersions] = useState<any[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [versionsError, setVersionsError] = useState<string | null>(null);

  const normalizePersona = (item: any): Persona => {
    const id = String(item?.id ?? item?.persona_id ?? fallbackId());
    return {
      id,
      name: item?.name ?? item?.title ?? "Untitled persona",
      voice: item?.voice ?? item?.voice_name ?? item?.voiceId,
      role: item?.role ?? item?.style,
      status: item?.status ?? item?.state ?? "active",
      description: item?.description ?? item?.summary ?? "",
      pathways: Array.isArray(item?.pathways) ? item.pathways : undefined,
      campaigns: typeof item?.campaigns === "number" ? item.campaigns : item?.campaign_count,
      updatedAt: item?.updated_at ?? item?.updatedAt,
    };
  };

  const fetchPersonas = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const body = await apiGet("/api/personas");
      const raw = Array.isArray(body?.data) ? body.data : [];
      setPersonas(raw.map(normalizePersona));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load personas";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPersonas();
  }, [fetchPersonas]);

  const totalPersonas = personas.length;
  const totalCampaigns = useMemo(
    () => personas.reduce((sum, persona) => sum + (persona.campaigns ?? 0), 0),
    [personas]
  );
  const voiceTypes = useMemo(() => {
    const set = new Set<string>();
    personas.forEach((persona) => {
      if (persona.voice) {
        set.add(persona.voice);
      }
    });
    return set.size;
  }, [personas]);

  const openCreateDialog = () => {
    setDialogMode("create");
    setEditingId(null);
    setFormData(defaultForm);
    setFormError(null);
    setDialogOpen(true);
  };

  const openEditDialog = async (personaId: string) => {
    setDialogMode("edit");
    setEditingId(personaId);
    setFormError(null);
    setFormLoading(true);
    setDialogOpen(true);
    try {
      const body = await apiGet(`/api/personas/${personaId}`);
      const data = body?.data ?? {};
      setFormData({
        name: data?.name ?? "",
        role: data?.role ?? "",
        voice: data?.voice ?? data?.voice_name ?? "",
        description: data?.description ?? "",
        pathways: Array.isArray(data?.pathways) ? data.pathways.join(", ") : "",
        settings: data?.settings ? JSON.stringify(data.settings, null, 2) : "",
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load persona";
      setFormError(message);
    } finally {
      setFormLoading(false);
    }
  };

  const handleSavePersona = async () => {
    setFormError(null);
    if (!formData.name.trim()) {
      setFormError("Name is required");
      return;
    }

    let settingsPayload: Record<string, unknown> | undefined;
    if (formData.settings.trim()) {
      try {
        settingsPayload = JSON.parse(formData.settings);
      } catch (err) {
        setFormError("Settings must be valid JSON");
        return;
      }
    }

    const payload: Record<string, unknown> = {
      name: formData.name.trim(),
      role: formData.role.trim() || undefined,
      voice: formData.voice.trim() || undefined,
      description: formData.description.trim() || undefined,
    };

    if (formData.pathways.trim()) {
      payload.pathways = formData.pathways
        .split(",")
        .map((pathway) => pathway.trim())
        .filter(Boolean);
    }
    if (settingsPayload) {
      payload.settings = settingsPayload;
    }

    setSaving(true);
    try {
      if (editingId) {
        await apiPatch(`/api/personas/${editingId}`, payload);
      } else {
        await apiPost("/api/personas", payload);
      }

      toast({
        title: editingId ? "Persona updated" : "Persona created",
        description: formData.name,
      });
      setDialogOpen(false);
      setFormData(defaultForm);
      setEditingId(null);
      fetchPersonas();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to save persona";
      setFormError(message);
      toast({ title: "Save failed", description: message, variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const openVersionsDialog = async (persona: Persona) => {
    setVersionsPersona(persona.name);
    setVersionsOpen(true);
    setVersions([]);
    setVersionsError(null);
    setVersionsLoading(true);
    try {
      const body = await apiGet(`/api/personas/${persona.id}/versions`);
      setVersions(Array.isArray(body?.data) ? body.data : []);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load versions";
      setVersionsError(message);
    } finally {
      setVersionsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Personas</h1>
          <p className="text-muted-foreground mt-2">
            Manage AI voice personalities and tones
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchPersonas} disabled={isLoading}>
            Refresh
          </Button>
          <Button onClick={openCreateDialog}>
            <Plus className="h-4 w-4 mr-2" />
            Create Persona
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Personas</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? "--" : totalPersonas}</div>
            <p className="text-xs text-muted-foreground">Active voice profiles</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Use</CardTitle>
            <Mic className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? "--" : totalCampaigns}</div>
            <p className="text-xs text-muted-foreground">Campaign assignments</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Voice Types</CardTitle>
            <Mic className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? "--" : voiceTypes}</div>
            <p className="text-xs text-muted-foreground">Unique voice styles</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Personas</CardTitle>
          <CardDescription>View and manage AI voice personalities</CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <p className="text-sm text-destructive mb-4">{error}</p>
          )}
          {isLoading ? (
            <div className="flex items-center justify-center py-10 gap-2 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" /> Loading personas...
            </div>
          ) : personas.length === 0 ? (
            <p className="text-sm text-muted-foreground">No personas yet. Create one to get started.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Voice</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Pathways</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {personas.map((persona) => (
                  <TableRow key={persona.id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Mic className="h-4 w-4 text-muted-foreground" />
                        {persona.name}
                      </div>
                    </TableCell>
                    <TableCell>{persona.voice ?? "-"}</TableCell>
                    <TableCell>{persona.role ?? "-"}</TableCell>
                    <TableCell>{persona.pathways?.length ?? 0}</TableCell>
                    <TableCell>
                      <Badge variant="default">{persona.status ?? "active"}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button variant="ghost" size="sm" onClick={() => openEditDialog(persona.id)}>
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openVersionsDialog(persona)}
                        >
                          <History className="h-4 w-4" />
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

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {dialogMode === "create" ? "Create Persona" : "Edit Persona"}
            </DialogTitle>
            <DialogDescription>
              Define the persona's style, pathways, and optional advanced settings.
            </DialogDescription>
          </DialogHeader>
          {formLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" /> Loading persona...
            </div>
          ) : (
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="persona-name">Name</Label>
                <Input
                  id="persona-name"
                  placeholder="Professional Alex"
                  value={formData.name}
                  onChange={(event) => setFormData((prev) => ({ ...prev, name: event.target.value }))}
                />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="persona-role">Role / Tone</Label>
                  <Input
                    id="persona-role"
                    placeholder="Friendly, consultative"
                    value={formData.role}
                    onChange={(event) => setFormData((prev) => ({ ...prev, role: event.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="persona-voice">Voice</Label>
                  <Input
                    id="persona-voice"
                    placeholder="Alloy"
                    value={formData.voice}
                    onChange={(event) => setFormData((prev) => ({ ...prev, voice: event.target.value }))}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="persona-description">Description</Label>
                <Textarea
                  id="persona-description"
                  placeholder="High-level summary"
                  value={formData.description}
                  onChange={(event) =>
                    setFormData((prev) => ({ ...prev, description: event.target.value }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="persona-pathways">Pathways (comma separated)</Label>
                <Input
                  id="persona-pathways"
                  placeholder="pathway-id-1, pathway-id-2"
                  value={formData.pathways}
                  onChange={(event) => setFormData((prev) => ({ ...prev, pathways: event.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="persona-settings">Advanced Settings (JSON)</Label>
                <Textarea
                  id="persona-settings"
                  placeholder='{"speech_rate": "fast"}'
                  value={formData.settings}
                  onChange={(event) => setFormData((prev) => ({ ...prev, settings: event.target.value }))}
                  className="font-mono"
                  rows={5}
                />
              </div>
              {formError && <p className="text-sm text-destructive">{formError}</p>}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSavePersona} disabled={saving || formLoading}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {dialogMode === "create" ? "Create" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={versionsOpen} onOpenChange={setVersionsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Persona Versions</DialogTitle>
            <DialogDescription>
              Version history for {versionsPersona ?? "persona"}
            </DialogDescription>
          </DialogHeader>
          {versionsLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" /> Loading versions...
            </div>
          ) : versionsError ? (
            <p className="text-sm text-destructive">{versionsError}</p>
          ) : versions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No versions found.</p>
          ) : (
            <div className="space-y-3 max-h-80 overflow-y-auto pr-2">
              {versions.map((version: any, index) => (
                <div key={version?.id ?? index} className="rounded-lg border p-3">
                  <p className="text-sm font-semibold">{version?.name ?? `Version ${index + 1}`}</p>
                  <p className="text-xs text-muted-foreground">{version?.created_at ?? version?.createdAt}</p>
                  {version?.changes && (
                    <p className="text-sm mt-2">{version.changes}</p>
                  )}
                </div>
              ))}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setVersionsOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Personas;
