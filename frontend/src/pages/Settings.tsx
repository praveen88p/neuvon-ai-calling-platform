import { useState } from "react";
import { Loader2, Save, Plus, Copy, Trash2, Key, Users, CreditCard, User, Building } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApiQuery } from "@/hooks/useApiQuery";
import { apiPatch, apiPost, apiDelete } from "@/utils/api";
import { API_PATHS, teamMemberPath, apiKeyPath } from "@/utils/apiPaths";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  ProfileResponse,
  OrgSettingsResponse,
  TeamMemberListResponse,
  ApiKeyListResponse,
  BillingUsageResponse,
  PlanInfoResponse,
} from "@/types/api";

// ─── Profile Tab ─────────────────────────────────────────────────────────────

function ProfileTab() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: profile, isLoading } = useApiQuery<ProfileResponse>(
    ["profile"],
    API_PATHS.PROFILE,
    { staleTime: 120_000 },
  );

  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [saving, setSaving] = useState(false);

  // Init form from profile data
  if (profile && !fullName && !phone) {
    setFullName(profile.full_name ?? "");
    setPhone(profile.phone ?? "");
  }

  const handleSave = async () => {
    setSaving(true);
    try {
      await apiPatch(API_PATHS.PROFILE, {
        full_name: fullName.trim(),
        phone: phone.trim() || undefined,
      });
      toast({ title: "Profile Updated" });
      queryClient.invalidateQueries({ queryKey: ["profile"] });
    } catch (err: unknown) {
      toast({ title: "Error", description: err instanceof Error ? err.message : "Failed", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) return <Loader2 className="h-6 w-6 animate-spin mx-auto my-12 text-primary" />;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <User className="h-4 w-4" />
          Profile
        </CardTitle>
        <CardDescription>Update your personal information</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 max-w-lg">
        <div className="space-y-2">
          <Label>Email</Label>
          <Input value={profile?.email ?? ""} disabled />
        </div>
        <div className="space-y-2">
          <Label htmlFor="fullName">Full Name</Label>
          <Input id="fullName" value={fullName} onChange={(e) => setFullName(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="phone">Phone</Label>
          <Input id="phone" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+1234567890" />
        </div>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
          Save Changes
        </Button>
      </CardContent>
    </Card>
  );
}

// ─── Organization Tab ────────────────────────────────────────────────────────

function OrganizationTab() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: org, isLoading } = useApiQuery<OrgSettingsResponse>(
    ["org-settings"],
    API_PATHS.ORG_SETTINGS,
    { staleTime: 120_000 },
  );

  const [orgName, setOrgName] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [saving, setSaving] = useState(false);

  if (org && !orgName) {
    setOrgName(org.name ?? "");
    setWebhookUrl(org.webhook_url ?? "");
  }

  const handleSave = async () => {
    setSaving(true);
    try {
      await apiPatch(API_PATHS.ORG_SETTINGS, {
        name: orgName.trim(),
        webhook_url: webhookUrl.trim() || undefined,
      });
      toast({ title: "Organization Updated" });
      queryClient.invalidateQueries({ queryKey: ["org-settings"] });
    } catch (err: unknown) {
      toast({ title: "Error", description: err instanceof Error ? err.message : "Failed", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) return <Loader2 className="h-6 w-6 animate-spin mx-auto my-12 text-primary" />;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Building className="h-4 w-4" />
          Organization
        </CardTitle>
        <CardDescription>Manage organization settings</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 max-w-lg">
        <div className="space-y-2">
          <Label htmlFor="orgName">Organization Name</Label>
          <Input id="orgName" value={orgName} onChange={(e) => setOrgName(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="webhook">Webhook URL</Label>
          <Input
            id="webhook"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            placeholder="https://your-app.com/webhook"
          />
          <p className="text-xs text-muted-foreground">Receive call result notifications at this URL.</p>
        </div>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
          Save Changes
        </Button>
      </CardContent>
    </Card>
  );
}

// ─── Team Tab ────────────────────────────────────────────────────────────────

function TeamTab() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data, isLoading } = useApiQuery<TeamMemberListResponse>(
    ["team"],
    API_PATHS.TEAM,
    { staleTime: 60_000 },
  );

  const [showInvite, setShowInvite] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");

  const members = data?.members ?? [];

  const handleInvite = async () => {
    if (!email.trim()) return;
    try {
      await apiPost(API_PATHS.TEAM, { email: email.trim(), role });
      toast({ title: "Invited", description: `${email} has been invited.` });
      setShowInvite(false);
      setEmail("");
      queryClient.invalidateQueries({ queryKey: ["team"] });
    } catch (err: unknown) {
      toast({ title: "Error", description: err instanceof Error ? err.message : "Failed", variant: "destructive" });
    }
  };

  const handleRemove = async (memberId: string) => {
    if (!confirm("Remove this team member?")) return;
    try {
      await apiDelete(teamMemberPath(memberId));
      toast({ title: "Member Removed" });
      queryClient.invalidateQueries({ queryKey: ["team"] });
    } catch (err: unknown) {
      toast({ title: "Error", description: err instanceof Error ? err.message : "Failed", variant: "destructive" });
    }
  };

  if (isLoading) return <Loader2 className="h-6 w-6 animate-spin mx-auto my-12 text-primary" />;

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              Team Members
            </CardTitle>
            <CardDescription>{members.length} member{members.length !== 1 ? "s" : ""}</CardDescription>
          </div>
          <Button onClick={() => setShowInvite(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Invite
          </Button>
        </CardHeader>
        <CardContent>
          {members.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">No team members yet.</p>
          ) : (
            <div className="space-y-3">
              {members.map((m) => (
                <div key={m.id} className="flex items-center justify-between border rounded-lg px-4 py-3">
                  <div>
                    <p className="font-medium">{m.full_name || m.email}</p>
                    <p className="text-sm text-muted-foreground">{m.email} · {m.role}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRemove(m.id)}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Invite Dialog */}
      <Dialog open={showInvite} onOpenChange={setShowInvite}>
        <DialogContent>
          <DialogHeader><DialogTitle>Invite Team Member</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Email *</Label>
              <Input placeholder="colleague@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Role</Label>
              <Select value={role} onValueChange={setRole}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="member">Member</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowInvite(false)}>Cancel</Button>
            <Button onClick={handleInvite} disabled={!email.trim()}>Send Invite</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ─── API Keys Tab ────────────────────────────────────────────────────────────

function ApiKeysTab() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data, isLoading } = useApiQuery<ApiKeyListResponse>(
    ["api-keys"],
    API_PATHS.API_KEYS,
    { staleTime: 60_000 },
  );

  const [showCreate, setShowCreate] = useState(false);
  const [keyLabel, setKeyLabel] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  const keys = data?.keys ?? [];

  const handleCreate = async () => {
    if (!keyLabel.trim()) return;
    try {
      const result = await apiPost<{ api_key: string; key: string }>(API_PATHS.API_KEYS, { name: keyLabel.trim() });
      setCreatedKey(result.key ?? result.api_key);
      toast({ title: "API Key Created", description: "Copy the key now — it won't be shown again." });
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    } catch (err: unknown) {
      toast({ title: "Error", description: err instanceof Error ? err.message : "Failed", variant: "destructive" });
    }
  };

  const handleDelete = async (keyId: string) => {
    if (!confirm("Revoke this API key? This cannot be undone.")) return;
    try {
      await apiDelete(apiKeyPath(keyId));
      toast({ title: "API Key Revoked" });
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    } catch (err: unknown) {
      toast({ title: "Error", description: err instanceof Error ? err.message : "Failed", variant: "destructive" });
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({ title: "Copied to clipboard" });
  };

  if (isLoading) return <Loader2 className="h-6 w-6 animate-spin mx-auto my-12 text-primary" />;

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-4 w-4" />
              API Keys
            </CardTitle>
            <CardDescription>Manage API keys for external integrations</CardDescription>
          </div>
          <Button onClick={() => { setShowCreate(true); setCreatedKey(null); setKeyLabel(""); }}>
            <Plus className="mr-2 h-4 w-4" />
            New Key
          </Button>
        </CardHeader>
        <CardContent>
          {keys.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">No API keys yet.</p>
          ) : (
            <div className="space-y-3">
              {keys.map((k) => (
                <div key={k.id} className="flex items-center justify-between border rounded-lg px-4 py-3">
                  <div>
                    <p className="font-medium">{k.name}</p>
                    <p className="text-sm text-muted-foreground font-mono">
                      {k.key_prefix ?? `${k.id.slice(0, 8)}...`}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDelete(k.id)}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Key Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent>
          <DialogHeader><DialogTitle>Create API Key</DialogTitle></DialogHeader>
          {createdKey ? (
            <div className="space-y-4 py-4">
              <p className="text-sm text-destructive font-medium">
                ⚠️ Copy this key now. It won't be shown again.
              </p>
              <div className="flex items-center gap-2">
                <Input value={createdKey} readOnly className="font-mono text-sm" />
                <Button variant="outline" size="icon" onClick={() => handleCopy(createdKey)}>
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Key Label *</Label>
                <Input placeholder="e.g. Production" value={keyLabel} onChange={(e) => setKeyLabel(e.target.value)} />
              </div>
            </div>
          )}
          <DialogFooter>
            {createdKey ? (
              <Button onClick={() => setShowCreate(false)}>Done</Button>
            ) : (
              <>
                <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
                <Button onClick={handleCreate} disabled={!keyLabel.trim()}>Create Key</Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ─── Billing Tab ─────────────────────────────────────────────────────────────

function BillingTab() {
  const { data: usage, isLoading: usageLoading } = useApiQuery<BillingUsageResponse>(
    ["billing-usage"],
    API_PATHS.BILLING_USAGE,
    { staleTime: 60_000 },
  );

  const { data: plan, isLoading: planLoading } = useApiQuery<PlanInfoResponse>(
    ["billing-plan"],
    API_PATHS.BILLING_PLAN,
    { staleTime: 120_000 },
  );

  if (usageLoading || planLoading) {
    return <Loader2 className="h-6 w-6 animate-spin mx-auto my-12 text-primary" />;
  }

  return (
    <div className="space-y-6">
      {/* Plan */}
      {plan && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-4 w-4" />
              Current Plan
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <p className="text-sm text-muted-foreground">Plan</p>
                <p className="text-xl font-bold capitalize">{plan.plan_name ?? "Free"}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Monthly Limit</p>
                <p className="text-xl font-bold">{plan.monthly_minutes_limit?.toLocaleString() ?? "∞"} min</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Price</p>
                <p className="text-xl font-bold">
                  {plan.price_per_month != null ? `₹${plan.price_per_month}/mo` : "Free"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Usage */}
      {usage && (
        <Card>
          <CardHeader>
            <CardTitle>Current Usage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-4">
              <div>
                <p className="text-sm text-muted-foreground">Calls This Month</p>
                <p className="text-2xl font-bold">{usage.total_calls ?? 0}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Minutes Used</p>
                <p className="text-2xl font-bold">{(usage.total_minutes ?? 0).toFixed(1)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Remaining Minutes</p>
                <p className="text-2xl font-bold">
                  {usage.remaining_minutes != null ? usage.remaining_minutes.toFixed(1) : "∞"}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Current Cost</p>
                <p className="text-2xl font-bold">
                  ₹{(usage.total_cost ?? 0).toFixed(2)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ─── Settings Page (Container) ───────────────────────────────────────────────

export default function Settings() {
  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground">Manage your account and organization</p>
      </div>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="organization">Organization</TabsTrigger>
          <TabsTrigger value="team">Team</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="billing">Billing</TabsTrigger>
        </TabsList>

        <TabsContent value="profile"><ProfileTab /></TabsContent>
        <TabsContent value="organization"><OrganizationTab /></TabsContent>
        <TabsContent value="team"><TeamTab /></TabsContent>
        <TabsContent value="api-keys"><ApiKeysTab /></TabsContent>
        <TabsContent value="billing"><BillingTab /></TabsContent>
      </Tabs>
    </div>
  );
}
