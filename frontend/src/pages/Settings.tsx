import { useState } from "react";
import { Loader2, Save, Plus, Trash2, Users, CreditCard, User, Building, IndianRupee, Phone, Clock, BarChart3, Package, Zap, CheckCircle2, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApiQuery } from "@/hooks/useApiQuery";
import { apiPatch, apiPost, apiDelete, apiGet } from "@/utils/api";
import { API_PATHS, teamMemberPath } from "@/utils/apiPaths";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import type {
  ProfileResponse,
  OrgSettingsResponse,
  TeamMemberListResponse,
  BillingUsageResponse,
  AvailablePacksResponse,
  TopUpOrderResponse,
  MinuteBalanceResponse,
  MinutePackListResponse,
} from "@/types/api";

// Razorpay global type
declare global {
  interface Window {
    Razorpay: new (options: Record<string, unknown>) => {
      open: () => void;
      on: (event: string, handler: (response: unknown) => void) => void;
    };
  }
}

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
  const [initialized, setInitialized] = useState(false);

  // Init form from profile data (once)
  if (profile && !initialized) {
    setFullName(profile.full_name ?? "");
    setPhone(profile.phone ?? "");
    setInitialized(true);
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
          <User className="h-5 w-5" />
          Profile
        </CardTitle>
        <CardDescription>Update your personal information</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 max-w-lg">
        <div className="space-y-2">
          <Label>Email</Label>
          <Input value={profile?.email ?? ""} disabled className="bg-muted/50" />
          <p className="text-xs text-muted-foreground">Email cannot be changed</p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="fullName">Full Name</Label>
          <Input id="fullName" value={fullName} onChange={(e) => setFullName(e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="phone">Phone</Label>
          <Input id="phone" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+919876543210" />
        </div>
        <div className="space-y-2">
          <Label>Role</Label>
          <Input value={profile?.role ?? ""} disabled className="bg-muted/50 capitalize" />
        </div>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
          Save Changes
        </Button>
      </CardContent>
    </Card>
  );
}

// ─── Organization Tab (read-only) ────────────────────────────────────────────

function OrganizationTab() {
  const { data: org, isLoading } = useApiQuery<OrgSettingsResponse>(
    ["org-settings"],
    API_PATHS.ORG_SETTINGS,
    { staleTime: 120_000 },
  );

  if (isLoading) return <Loader2 className="h-6 w-6 animate-spin mx-auto my-12 text-primary" />;

  const createdAt = org?.created_at
    ? new Date(org.created_at).toLocaleDateString("en-IN", {
        month: "long",
        year: "numeric",
      })
    : "—";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Building className="h-5 w-5" />
          Organization
        </CardTitle>
        <CardDescription>Your organization details (managed by Neuvon admin)</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 max-w-lg">
        <div className="space-y-2">
          <Label>Organization Name</Label>
          <Input value={org?.name ?? ""} disabled className="bg-muted/50" />
        </div>
        <div className="space-y-2">
          <Label>Account ID</Label>
          <Input value={org?.id ?? ""} disabled className="bg-muted/50 font-mono text-xs" />
          <p className="text-xs text-muted-foreground">Your unique organization identifier</p>
        </div>
        <div className="space-y-2">
          <Label>Member Since</Label>
          <Input value={createdAt} disabled className="bg-muted/50" />
        </div>
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
              <Users className="h-5 w-5" />
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
                    <p className="text-sm text-muted-foreground">{m.email} · <span className="capitalize">{m.role}</span></p>
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

// ─── Billing Tab ─────────────────────────────────────────────────────────────

function BillingTab() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [buyingPack, setBuyingPack] = useState<number | null>(null);

  const { data: usage, isLoading: usageLoading } = useApiQuery<BillingUsageResponse>(
    ["billing-usage"],
    API_PATHS.BILLING_USAGE,
    { staleTime: 60_000 },
  );

  const { data: packs, isLoading: packsLoading } = useApiQuery<AvailablePacksResponse>(
    ["topup-packs"],
    API_PATHS.BILLING_TOPUP_PACKS,
    { staleTime: 120_000 },
  );

  const { data: balance } = useApiQuery<MinuteBalanceResponse>(
    ["minute-balance"],
    API_PATHS.BILLING_TOPUP_BALANCE,
    { staleTime: 30_000 },
  );

  const { data: history } = useApiQuery<MinutePackListResponse>(
    ["topup-history"],
    API_PATHS.BILLING_TOPUP_HISTORY,
    { staleTime: 60_000 },
  );

  if (usageLoading || packsLoading) {
    return <Loader2 className="h-6 w-6 animate-spin mx-auto my-12 text-primary" />;
  }

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  const rate = usage?.rate_per_minute ?? 0;
  const platformFee = usage?.platform_fee ?? 0;
  const planLabel = usage?.plan_label;
  const totalCalls = usage?.total_calls ?? 0;
  const totalMinutes = usage?.total_minutes ?? 0;
  const usageCost = rate * totalMinutes;
  const totalCost = usage?.total_cost ?? 0;
  const minuteBalance = balance?.minute_balance ?? packs?.minute_balance ?? 0;

  const handleBuyPack = async (minutes: number) => {
    setBuyingPack(minutes);
    try {
      const order = await apiPost<TopUpOrderResponse>(
        API_PATHS.BILLING_TOPUP_ORDER,
        { minutes },
      );

      if (!window.Razorpay) {
        toast({ title: "Error", description: "Payment system not loaded. Please refresh.", variant: "destructive" });
        setBuyingPack(null);
        return;
      }

      const user = JSON.parse(localStorage.getItem("auth_user") || "{}");

      const rzp = new window.Razorpay({
        key: order.razorpay_key_id,
        amount: order.amount,
        currency: order.currency,
        name: "Neuvon AI",
        description: order.description,
        order_id: order.order_id,
        handler: async (response: Record<string, string>) => {
          try {
            await apiPost(API_PATHS.BILLING_TOPUP_VERIFY, {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            toast({ title: "Payment Successful!", description: `${minutes} minutes have been added to your balance.` });
            queryClient.invalidateQueries({ queryKey: ["minute-balance"] });
            queryClient.invalidateQueries({ queryKey: ["topup-history"] });
            queryClient.invalidateQueries({ queryKey: ["billing-usage"] });
            queryClient.invalidateQueries({ queryKey: ["topup-packs"] });
          } catch {
            toast({ title: "Verification Failed", description: "Payment may have succeeded. Please contact support.", variant: "destructive" });
          }
          setBuyingPack(null);
        },
        modal: {
          ondismiss: () => setBuyingPack(null),
        },
        prefill: {
          email: user.email || "",
          contact: user.phone || "",
        },
        theme: { color: "#644a40" },
      });

      rzp.open();
    } catch (err) {
      toast({ title: "Error", description: err instanceof Error ? err.message : "Failed to create order", variant: "destructive" });
      setBuyingPack(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Billing Period Header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Billing Overview
          </CardTitle>
          <CardDescription>
            <Clock className="inline h-3.5 w-3.5 mr-1 -mt-0.5" />
            Billing period: {formatDate(usage?.period_start)} — {formatDate(usage?.period_end)}
            {planLabel && <Badge variant="secondary" className="ml-2">{planLabel}</Badge>}
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Minute Balance — Hero Card */}
      <Card className={minuteBalance <= 0 ? "border-destructive" : "border-green-500/30"}>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`rounded-lg p-3 ${minuteBalance <= 0 ? "bg-destructive/10" : "bg-green-500/10"}`}>
                {minuteBalance <= 0
                  ? <AlertTriangle className="h-6 w-6 text-destructive" />
                  : <Zap className="h-6 w-6 text-green-600" />
                }
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Available Minutes</p>
                <p className="text-3xl font-bold">
                  {minuteBalance.toFixed(1)}
                  <span className="text-sm font-normal text-muted-foreground ml-1">min</span>
                </p>
                {minuteBalance <= 0 && (
                  <p className="text-xs text-destructive mt-1">Purchase minutes to make calls</p>
                )}
              </div>
            </div>
            <div className="text-right text-sm text-muted-foreground">
              <p>Total purchased: {(balance?.total_purchased ?? 0).toFixed(0)} min</p>
              <p>Total used: {(balance?.total_used ?? 0).toFixed(0)} min</p>
              <p>Active packs: {balance?.active_packs ?? 0}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Buy Minutes */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            Buy Minutes
          </CardTitle>
          <CardDescription>
            Purchase minute packs at ₹{rate.toFixed(2)}/min. Minutes never expire.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-3">
            {(packs?.packs ?? []).map((pack) => (
              <Card key={pack.minutes} className="relative overflow-hidden hover:border-primary/50 transition-colors">
                {pack.minutes === 500 && (
                  <div className="absolute top-0 right-0 bg-primary text-primary-foreground text-[10px] font-semibold px-2 py-0.5 rounded-bl">
                    POPULAR
                  </div>
                )}
                <CardContent className="pt-6 text-center">
                  <p className="text-3xl font-bold">{pack.minutes.toLocaleString()}</p>
                  <p className="text-sm text-muted-foreground mb-3">minutes</p>
                  <p className="text-xl font-semibold text-primary mb-4">
                    ₹{pack.price.toLocaleString("en-IN", { minimumFractionDigits: 0 })}
                  </p>
                  <Button
                    className="w-full"
                    onClick={() => handleBuyPack(pack.minutes)}
                    disabled={buyingPack !== null}
                  >
                    {buyingPack === pack.minutes ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : null}
                    {buyingPack === pack.minutes ? "Processing..." : "Buy Now"}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Usage Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-primary/10 p-2.5">
                <IndianRupee className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Your Rate</p>
                <p className="text-2xl font-bold">₹{rate.toFixed(2)}<span className="text-sm font-normal text-muted-foreground">/min</span></p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-primary/10 p-2.5">
                <Phone className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Calls This Month</p>
                <p className="text-2xl font-bold">{totalCalls.toLocaleString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-primary/10 p-2.5">
                <BarChart3 className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Minutes Used</p>
                <p className="text-2xl font-bold">{totalMinutes.toFixed(1)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-primary/10 p-2.5">
                <IndianRupee className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Cost</p>
                <p className="text-2xl font-bold">₹{totalCost.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Cost Breakdown */}
      {(platformFee > 0 || usageCost > 0) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Cost Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row gap-8 text-sm">
              <div>
                <p className="text-muted-foreground mb-1">Usage ({totalMinutes.toFixed(1)} min × ₹{rate.toFixed(2)})</p>
                <p className="font-medium">₹{usageCost.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
              </div>
              {platformFee > 0 && (
                <div>
                  <p className="text-muted-foreground mb-1">Platform Fee (Monthly)</p>
                  <p className="font-medium">₹{platformFee.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Purchase History */}
      {history && history.packs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock className="h-4 w-4" />
              Purchase History
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {history.packs.slice(0, 10).map((pack) => (
                <div key={pack.id} className="flex items-center justify-between border rounded-lg px-4 py-3">
                  <div className="flex items-center gap-3">
                    {pack.status === "paid" ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      <Clock className="h-4 w-4 text-yellow-500" />
                    )}
                    <div>
                      <p className="font-medium">{pack.minutes_purchased.toLocaleString()} minutes</p>
                      <p className="text-xs text-muted-foreground">{formatDate(pack.created_at)}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">₹{pack.amount_paid.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</p>
                    <Badge variant={pack.status === "paid" ? "default" : "secondary"} className="text-[10px]">
                      {pack.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Footer */}
      <p className="text-xs text-muted-foreground text-center">
        Billing is managed by Neuvon. Contact your account manager for rate changes or plan updates.
      </p>
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
          <TabsTrigger value="billing">Billing</TabsTrigger>
        </TabsList>

        <TabsContent value="profile"><ProfileTab /></TabsContent>
        <TabsContent value="organization"><OrganizationTab /></TabsContent>
        <TabsContent value="team"><TeamTab /></TabsContent>
        <TabsContent value="billing"><BillingTab /></TabsContent>
      </Tabs>
    </div>
  );
}
