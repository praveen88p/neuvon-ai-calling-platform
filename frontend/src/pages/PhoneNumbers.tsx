import { useState } from "react";
import {
  Phone,
  Loader2,
  Plus,
  Settings2,
  Trash2,
  Star,
  ChevronDown,
  ChevronRight,
  Plug,
  Edit2,
  PhoneIncoming,
  Shield,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useApiQuery } from "@/hooks/useApiQuery";
import { apiPost, apiPut, apiDelete } from "@/utils/api";
import {
  API_PATHS,
  telephonyPhoneNumbersPath,
  telephonyPhoneNumberPath,
  telephonyConfigPath,
  telephonySetDefaultOutboundPath,
  telephonySetDefaultCallerPath,
} from "@/utils/apiPaths";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import type {
  TelephonyConfigListResponse,
  TelephonyConfigResponse,
  TelephonyProvidersResponse,
  TelephonyProviderField,
  PhoneNumberListResponse,
  PhoneNumberResponse,
  AgentListResponse,
} from "@/types/api";

// ─── Config Card ─────────────────────────────────────────────────────────────

function ConfigCard({
  config,
  onRefresh,
}: {
  config: TelephonyConfigResponse;
  onRefresh: () => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(true);
  const [showAddNumber, setShowAddNumber] = useState(false);
  const [showEditNumber, setShowEditNumber] = useState<PhoneNumberResponse | null>(null);

  // Fetch phone numbers for this config
  const { data: numbersData, isLoading: numbersLoading } =
    useApiQuery<PhoneNumberListResponse>(
      ["phone-numbers", config.id],
      telephonyPhoneNumbersPath(config.id),
      { staleTime: 60_000 },
    );

  // Fetch agents for inbound binding
  const { data: agentsData } = useApiQuery<AgentListResponse>(
    ["agents"],
    API_PATHS.AGENTS,
    { staleTime: 120_000 },
  );

  const numbers = numbersData?.phone_numbers ?? [];
  const agents = agentsData?.agents ?? [];

  const handleSetDefaultOutbound = async () => {
    try {
      await apiPost(telephonySetDefaultOutboundPath(config.id));
      toast({ title: "Default Outbound Set", description: `${config.name} is now the default for outbound calls.` });
      onRefresh();
    } catch (err: unknown) {
      toast({ title: "Failed", description: err instanceof Error ? err.message : "Unknown error", variant: "destructive" });
    }
  };

  const handleDeleteConfig = async () => {
    if (!confirm(`Delete "${config.name}"? This will remove all associated phone numbers too.`)) return;
    try {
      await apiDelete(telephonyConfigPath(config.id));
      toast({ title: "Deleted", description: `${config.name} has been removed.` });
      onRefresh();
    } catch (err: unknown) {
      toast({ title: "Failed", description: err instanceof Error ? err.message : "Unknown error", variant: "destructive" });
    }
  };

  const handleSetDefaultCaller = async (num: PhoneNumberResponse) => {
    try {
      await apiPost(telephonySetDefaultCallerPath(config.id, num.id));
      toast({ title: "Default Caller Set", description: `${num.address} is now the default caller ID.` });
      queryClient.invalidateQueries({ queryKey: ["phone-numbers", config.id] });
    } catch (err: unknown) {
      toast({ title: "Failed", description: err instanceof Error ? err.message : "Unknown error", variant: "destructive" });
    }
  };

  const handleDeleteNumber = async (num: PhoneNumberResponse) => {
    if (!confirm(`Remove ${num.address}?`)) return;
    try {
      await apiDelete(telephonyPhoneNumberPath(config.id, num.id));
      toast({ title: "Removed", description: `${num.address} has been removed.` });
      queryClient.invalidateQueries({ queryKey: ["phone-numbers", config.id] });
    } catch (err: unknown) {
      toast({ title: "Failed", description: err instanceof Error ? err.message : "Unknown error", variant: "destructive" });
    }
  };

  const getAgentName = (workflowId: number | null, workflowName: string | null) => {
    if (workflowName) return workflowName;
    if (!workflowId) return null;
    const agent = agents.find((a) => a.workflow_id === workflowId);
    return agent?.name ?? `Agent #${workflowId}`;
  };

  return (
    <Card className="border-border/60">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-1 rounded hover:bg-muted transition-colors"
            >
              {expanded ? (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              )}
            </button>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Plug className="h-5 w-5 text-primary" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <CardTitle className="text-base">{config.name ?? "Unnamed Config"}</CardTitle>
                {config.is_default_outbound && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                    <Star className="h-3 w-3" /> Default Outbound
                  </span>
                )}
              </div>
              <p className="text-sm text-muted-foreground mt-0.5">
                Provider: <span className="font-medium capitalize">{config.provider ?? "Unknown"}</span>
                {config.phone_number_count > 0 && (
                  <> · {config.phone_number_count} number{config.phone_number_count !== 1 ? "s" : ""}</>
                )}
                {config.created_at && (
                  <> · Created {new Date(config.created_at).toLocaleDateString()}</>
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {!config.is_default_outbound && (
              <Button variant="outline" size="sm" onClick={handleSetDefaultOutbound}>
                <Star className="mr-1.5 h-3.5 w-3.5" />
                Set Default
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={handleDeleteConfig}
              className="text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="pt-0">
          <div className="border-t pt-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                <Phone className="h-3.5 w-3.5" />
                Phone Numbers ({numbers.length})
              </h4>
              <Button size="sm" variant="outline" onClick={() => setShowAddNumber(true)}>
                <Plus className="mr-1.5 h-3.5 w-3.5" />
                Add Number
              </Button>
            </div>

            {numbersLoading ? (
              <div className="flex justify-center py-6">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : numbers.length === 0 ? (
              <div className="text-center py-6 text-sm text-muted-foreground border rounded-lg border-dashed">
                No phone numbers added to this config yet.
              </div>
            ) : (
              <div className="space-y-2">
                {numbers.map((num) => (
                  <div
                    key={num.id}
                    className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10">
                        <Phone className="h-4 w-4 text-primary" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-medium text-sm">{num.address}</span>
                          {num.is_default_caller_id && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                              <Star className="h-3 w-3" /> Default Caller
                            </span>
                          )}
                          {!num.is_active && (
                            <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">
                              Inactive
                            </span>
                          )}
                          {num.provider_sync && (
                            num.provider_sync.ok ? (
                              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" title="Synced with provider" />
                            ) : (
                              <AlertCircle className="h-3.5 w-3.5 text-amber-500" title={num.provider_sync.message ?? "Sync issue"} />
                            )
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                          {num.label && <span>{num.label}</span>}
                          {num.country_code && <span>({num.country_code})</span>}
                          {num.inbound_workflow_id && (
                            <span className="flex items-center gap-1">
                              <PhoneIncoming className="h-3 w-3" />
                              Inbound → {getAgentName(num.inbound_workflow_id, num.inbound_workflow_name)}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      {!num.is_default_caller_id && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSetDefaultCaller(num)}
                          className="text-xs text-muted-foreground"
                        >
                          <Star className="mr-1 h-3 w-3" /> Set Default
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setShowEditNumber(num)}
                        className="text-muted-foreground hover:text-foreground h-8 w-8"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDeleteNumber(num)}
                        className="text-muted-foreground hover:text-destructive h-8 w-8"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Add Number Dialog */}
          <AddNumberDialog
            open={showAddNumber}
            onOpenChange={setShowAddNumber}
            configId={config.id}
            agents={agents}
            onAdded={() => queryClient.invalidateQueries({ queryKey: ["phone-numbers", config.id] })}
          />

          {/* Edit Number Dialog */}
          {showEditNumber && (
            <EditNumberDialog
              open={!!showEditNumber}
              onOpenChange={(open) => { if (!open) setShowEditNumber(null); }}
              configId={config.id}
              phoneNumber={showEditNumber}
              agents={agents}
              onUpdated={() => {
                queryClient.invalidateQueries({ queryKey: ["phone-numbers", config.id] });
                setShowEditNumber(null);
              }}
            />
          )}
        </CardContent>
      )}
    </Card>
  );
}

// ─── Add Number Dialog ───────────────────────────────────────────────────────

function AddNumberDialog({
  open,
  onOpenChange,
  configId,
  agents,
  onAdded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  configId: number;
  agents: { workflow_id: number; name: string }[];
  onAdded: () => void;
}) {
  const { toast } = useToast();
  const [address, setAddress] = useState("");
  const [label, setLabel] = useState("");
  const [countryCode, setCountryCode] = useState("");
  const [inboundAgent, setInboundAgent] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const handleAdd = async () => {
    if (!address.trim()) return;
    setLoading(true);
    try {
      await apiPost(telephonyPhoneNumbersPath(configId), {
        address: address.trim(),
        label: label.trim() || undefined,
        country_code: countryCode.trim() || undefined,
        inbound_workflow_id: inboundAgent && inboundAgent !== "none" ? parseInt(inboundAgent) : undefined,
      });
      toast({ title: "Phone Number Added", description: `${address} added successfully.` });
      setAddress("");
      setLabel("");
      setCountryCode("");
      setInboundAgent("");
      onOpenChange(false);
      onAdded();
    } catch (err: unknown) {
      toast({ title: "Failed", description: err instanceof Error ? err.message : "Unknown error", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Phone Number</DialogTitle>
          <DialogDescription>
            Add a phone number from your telephony provider to use for outbound or inbound calls.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="add-address">Phone Number *</Label>
            <Input
              id="add-address"
              placeholder="+14155551234 (E.164 format)"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="add-label">Label</Label>
              <Input
                id="add-label"
                placeholder="e.g. Main Line"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="add-country">Country Code</Label>
              <Input
                id="add-country"
                placeholder="e.g. IN, US"
                value={countryCode}
                onChange={(e) => setCountryCode(e.target.value.toUpperCase())}
                maxLength={5}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="add-inbound">Inbound Agent (optional)</Label>
            <Select value={inboundAgent} onValueChange={setInboundAgent}>
              <SelectTrigger id="add-inbound">
                <SelectValue placeholder="No inbound agent" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No inbound agent</SelectItem>
                {agents.map((a) => (
                  <SelectItem key={a.workflow_id} value={String(a.workflow_id)}>
                    {a.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              When someone calls this number, the selected AI agent will handle the conversation.
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleAdd} disabled={!address.trim() || loading}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Add Number
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Edit Number Dialog ──────────────────────────────────────────────────────

function EditNumberDialog({
  open,
  onOpenChange,
  configId,
  phoneNumber,
  agents,
  onUpdated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  configId: number;
  phoneNumber: PhoneNumberResponse;
  agents: { workflow_id: number; name: string }[];
  onUpdated: () => void;
}) {
  const { toast } = useToast();
  const [label, setLabel] = useState(phoneNumber.label ?? "");
  const [inboundAgent, setInboundAgent] = useState<string>(
    phoneNumber.inbound_workflow_id ? String(phoneNumber.inbound_workflow_id) : ""
  );
  const [isActive, setIsActive] = useState(phoneNumber.is_active);
  const [loading, setLoading] = useState(false);

  const handleUpdate = async () => {
    setLoading(true);
    try {
      await apiPut(telephonyPhoneNumberPath(configId, phoneNumber.id), {
        label: label.trim() || null,
        inbound_workflow_id: inboundAgent && inboundAgent !== "none" ? parseInt(inboundAgent) : null,
        is_active: isActive,
      });
      toast({ title: "Updated", description: `${phoneNumber.address} updated successfully.` });
      onUpdated();
    } catch (err: unknown) {
      toast({ title: "Failed", description: err instanceof Error ? err.message : "Unknown error", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit {phoneNumber.address}</DialogTitle>
          <DialogDescription>
            Update the label, inbound agent binding, or active status for this number.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="edit-label">Label</Label>
            <Input
              id="edit-label"
              placeholder="e.g. Main Line"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="edit-inbound">Inbound Agent</Label>
            <Select value={inboundAgent || "none"} onValueChange={setInboundAgent}>
              <SelectTrigger id="edit-inbound">
                <SelectValue placeholder="No inbound agent" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No inbound agent</SelectItem>
                {agents.map((a) => (
                  <SelectItem key={a.workflow_id} value={String(a.workflow_id)}>
                    {a.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-3">
            <Label htmlFor="edit-active" className="flex-1">Active</Label>
            <button
              id="edit-active"
              onClick={() => setIsActive(!isActive)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                isActive ? "bg-primary" : "bg-gray-300"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  isActive ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleUpdate} disabled={loading}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Add Config Dialog (Metadata-Driven) ─────────────────────────────────────

function AddConfigDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}) {
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [provider, setProvider] = useState("");
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [isDefaultOutbound, setIsDefaultOutbound] = useState(false);
  const [loading, setLoading] = useState(false);

  // Fetch available providers from Dograh metadata
  const { data: providersData } = useApiQuery<TelephonyProvidersResponse>(
    ["telephony-providers"],
    API_PATHS.TELEPHONY_PROVIDERS,
    { staleTime: 300_000 },
  );

  const providers = providersData?.providers ?? [];
  const selectedProvider = providers.find((p) => p.provider === provider);

  const handleProviderChange = (value: string) => {
    setProvider(value);
    setCredentials({});
  };

  const handleCreate = async () => {
    if (!name.trim() || !provider) return;
    setLoading(true);
    try {
      // Build credentials — convert empty strings to null for optional fields
      const cleanedCredentials: Record<string, string | null> = {};
      if (selectedProvider) {
        for (const field of selectedProvider.fields) {
          // Skip 'from_numbers' — phone numbers are managed separately
          if (field.name === "from_numbers") continue;
          const val = credentials[field.name]?.trim();
          if (val) {
            cleanedCredentials[field.name] = val;
          } else if (!field.required) {
            cleanedCredentials[field.name] = null; // Auto-provisioned
          }
        }
      }

      await apiPost(API_PATHS.TELEPHONY_CONFIGS, {
        provider,
        name: name.trim(),
        credentials: cleanedCredentials,
        is_default_outbound: isDefaultOutbound,
      });
      toast({ title: "Provider Connected", description: `${name} has been configured.` });
      setName("");
      setProvider("");
      setCredentials({});
      setIsDefaultOutbound(false);
      onOpenChange(false);
      onCreated();
    } catch (err: unknown) {
      toast({ title: "Failed", description: err instanceof Error ? err.message : "Unknown error", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  // Render a dynamic field based on its metadata type
  const renderField = (field: TelephonyProviderField) => {
    // Skip from_numbers — phone numbers managed separately in the phone numbers section
    if (field.name === "from_numbers") return null;

    const value = credentials[field.name] ?? "";
    const isOptional = !field.required;

    return (
      <div key={field.name} className="space-y-1.5">
        <Label htmlFor={`cred-${field.name}`} className="text-sm">
          {field.label ?? field.name}
          {isOptional && (
            <span className="text-muted-foreground font-normal ml-1">(optional — auto-created if empty)</span>
          )}
        </Label>
        {field.type === "textarea" ? (
          <Textarea
            id={`cred-${field.name}`}
            placeholder={field.description ?? field.label ?? field.name}
            value={value}
            onChange={(e) => setCredentials((prev) => ({ ...prev, [field.name]: e.target.value }))}
            rows={4}
            className="font-mono text-xs"
          />
        ) : (
          <Input
            id={`cred-${field.name}`}
            type={field.sensitive ? "password" : "text"}
            placeholder={field.description ?? field.label ?? field.name}
            value={value}
            onChange={(e) => setCredentials((prev) => ({ ...prev, [field.name]: e.target.value }))}
          />
        )}
      </div>
    );
  };

  // Check if required fields are filled
  const requiredFieldsFilled = selectedProvider
    ? selectedProvider.fields
        .filter((f) => f.required && f.name !== "from_numbers")
        .every((f) => credentials[f.name]?.trim())
    : false;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Connect Telephony Provider</DialogTitle>
          <DialogDescription>
            Connect your telephony provider to enable outbound and inbound calls with your AI agents.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          {/* Config Name */}
          <div className="space-y-2">
            <Label htmlFor="config-name">Config Name *</Label>
            <Input
              id="config-name"
              placeholder="e.g. My Vobiz Account"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          {/* Provider Selection */}
          <div className="space-y-2">
            <Label htmlFor="config-provider">Provider *</Label>
            <Select value={provider} onValueChange={handleProviderChange}>
              <SelectTrigger id="config-provider">
                <SelectValue placeholder="Select a provider" />
              </SelectTrigger>
              <SelectContent>
                {providers.map((p) => (
                  <SelectItem key={p.provider} value={p.provider}>
                    {p.display_name ?? p.provider}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Dynamic Credential Fields — rendered from provider metadata */}
          {selectedProvider && selectedProvider.fields.length > 0 && (
            <div className="space-y-3 p-4 rounded-lg border bg-muted/30">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Shield className="h-4 w-4 text-muted-foreground" />
                <span>{selectedProvider.display_name ?? provider} Credentials</span>
              </div>
              {selectedProvider.fields.map(renderField)}
            </div>
          )}

          {/* Default Outbound Toggle */}
          {provider && (
            <div className="flex items-center gap-3 p-3 rounded-lg border">
              <div className="flex-1">
                <p className="text-sm font-medium">Set as Default Outbound</p>
                <p className="text-xs text-muted-foreground">
                  Use this provider when no specific config is specified for calls.
                </p>
              </div>
              <button
                onClick={() => setIsDefaultOutbound(!isDefaultOutbound)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  isDefaultOutbound ? "bg-primary" : "bg-gray-300"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    isDefaultOutbound ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button
            onClick={handleCreate}
            disabled={!name.trim() || !provider || !requiredFieldsFilled || loading}
          >
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Connect Provider
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function PhoneNumbers() {
  const [showAddConfig, setShowAddConfig] = useState(false);
  const queryClient = useQueryClient();

  // Fetch telephony configs
  const { data, isLoading, error } = useApiQuery<TelephonyConfigListResponse>(
    ["telephony-configs"],
    API_PATHS.TELEPHONY_CONFIGS,
    { staleTime: 60_000 },
  );

  const configs = data?.configs ?? [];

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ["telephony-configs"] });
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Phone Numbers</h1>
          <p className="text-muted-foreground">
            Manage your telephony providers and phone numbers
          </p>
        </div>
        <Button onClick={() => setShowAddConfig(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Connect Provider
        </Button>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center min-h-[300px]">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : error ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-destructive">
              {error instanceof Error ? error.message : "Failed to load telephony configurations"}
            </p>
          </CardContent>
        </Card>
      ) : configs.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <div className="flex flex-col items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                <Settings2 className="h-8 w-8 text-primary" />
              </div>
              <div>
                <h3 className="text-lg font-semibold">No telephony provider configured</h3>
                <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
                  Connect your Twilio, Plivo, or Vobiz account to start making and receiving calls with your AI agents.
                </p>
              </div>
              <Button onClick={() => setShowAddConfig(true)}>
                <Plug className="mr-2 h-4 w-4" />
                Connect Provider
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {configs.map((config) => (
            <ConfigCard key={config.id} config={config} onRefresh={handleRefresh} />
          ))}
        </div>
      )}

      {/* Add Config Dialog */}
      <AddConfigDialog
        open={showAddConfig}
        onOpenChange={setShowAddConfig}
        onCreated={handleRefresh}
      />
    </div>
  );
}
