import { useCallback, useEffect, useMemo, useState } from "react";
import { Phone, Plus, Edit, Trash2, CheckCircle2, Loader2 } from "lucide-react";
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
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import { apiGet, apiPost } from "@/utils/api";

type PhoneNumber = {
  id: string;
  phoneNumber: string;
  type?: string;
  location?: string;
  campaigns?: number;
  status?: string;
};

type CreateFormState = {
  country: string;
  type: string;
  areaCode: string;
  label: string;
};

const defaultCreateForm: CreateFormState = {
  country: "US",
  type: "local",
  areaCode: "",
  label: "",
};

const fallbackId = () => `number-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const PhoneNumbers = () => {
  const { toast } = useToast();
  const [numbers, setNumbers] = useState<PhoneNumber[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState<CreateFormState>(defaultCreateForm);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createLoading, setCreateLoading] = useState(false);

  const normalizeNumber = (item: any): PhoneNumber => {
    const id = String(item?.id ?? item?.number_id ?? item?.phone_number ?? fallbackId());
    const phoneNumber = item?.phone_number ?? item?.number ?? id;
    const locationParts = [item?.city, item?.state ?? item?.region, item?.country]
      .filter((part) => part && typeof part === "string")
      .map((part) => part.trim())
      .filter(Boolean);
    const location = locationParts.length ? locationParts.join(", ") : item?.location ?? undefined;
    return {
      id,
      phoneNumber,
      type: item?.type ?? item?.number_type,
      location,
      campaigns: typeof item?.campaigns === "number" ? item.campaigns : item?.campaign_count,
      status: item?.status ?? item?.state ?? "active",
    };
  };

  const fetchPhoneNumbers = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const body = await apiGet("/api/phone-numbers");
      const raw = Array.isArray(body?.data) ? body.data : [];
      setNumbers(raw.map(normalizeNumber));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load phone numbers";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPhoneNumbers();
  }, [fetchPhoneNumbers]);

  const totalNumbers = numbers.length;
  const totalCampaigns = useMemo(
    () => numbers.reduce((sum, number) => sum + (number.campaigns ?? 0), 0),
    [numbers]
  );
  const numberTypes = useMemo(() => {
    const set = new Set<string>();
    numbers.forEach((number) => {
      if (number.type) set.add(number.type);
    });
    return set.size;
  }, [numbers]);

  const openCreateDialog = () => {
    setCreateForm(defaultCreateForm);
    setCreateError(null);
    setCreateOpen(true);
  };

  const handleCreateNumber = async () => {
    setCreateError(null);
    if (!createForm.country.trim() || createForm.country.trim().length !== 2) {
      setCreateError("Country must be a 2-letter ISO code");
      return;
    }

    const payload = {
      country: createForm.country.trim().toUpperCase(),
      type: createForm.type || undefined,
      area_code: createForm.areaCode.trim() || undefined,
      label: createForm.label.trim() || undefined,
    };

    setCreateLoading(true);
    try {
      await apiPost("/api/phone-numbers", payload);

      toast({ title: "Provisioning requested", description: "Phone number creation started." });
      setCreateOpen(false);
      setCreateForm(defaultCreateForm);
      fetchPhoneNumbers();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to create phone number";
      setCreateError(message);
      toast({ title: "Create failed", description: message, variant: "destructive" });
    } finally {
      setCreateLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Phone Numbers</h1>
          <p className="text-muted-foreground mt-2">Manage outbound calling numbers</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchPhoneNumbers} disabled={isLoading}>
            Refresh
          </Button>
          <Button onClick={openCreateDialog}>
            <Plus className="h-4 w-4 mr-2" />
            Add Number
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Numbers</CardTitle>
            <Phone className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? "--" : totalNumbers}</div>
            <p className="text-xs text-muted-foreground">Active phone numbers</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Use</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? "--" : totalCampaigns}</div>
            <p className="text-xs text-muted-foreground">Active campaigns</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Number Types</CardTitle>
            <Phone className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? "--" : numberTypes}</div>
            <p className="text-xs text-muted-foreground">Local, Toll-Free, etc.</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Phone Numbers</CardTitle>
          <CardDescription>View and manage outbound phone numbers</CardDescription>
        </CardHeader>
        <CardContent>
          {error && <p className="text-sm text-destructive mb-4">{error}</p>}
          {isLoading ? (
            <div className="flex items-center justify-center py-10 gap-2 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" /> Loading phone numbers...
            </div>
          ) : numbers.length === 0 ? (
            <p className="text-sm text-muted-foreground">No phone numbers yet. Provision one to get started.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Number</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Campaigns</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {numbers.map((number) => (
                  <TableRow key={number.id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Phone className="h-4 w-4 text-muted-foreground" />
                        {number.phoneNumber}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{number.type ?? "-"}</Badge>
                    </TableCell>
                    <TableCell>{number.location ?? "-"}</TableCell>
                    <TableCell>{number.campaigns ?? 0}</TableCell>
                    <TableCell>
                      <Badge variant="default">{number.status ?? "active"}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button variant="ghost" size="sm" disabled>
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" disabled>
                          <Trash2 className="h-4 w-4" />
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

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Provision Phone Number</DialogTitle>
            <DialogDescription>Select the country and type for the new outbound number.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="phone-country">Country (ISO)</Label>
                <Input
                  id="phone-country"
                  maxLength={2}
                  value={createForm.country}
                  onChange={(event) =>
                    setCreateForm((prev) => ({ ...prev, country: event.target.value.toUpperCase() }))
                  }
                  placeholder="US"
                />
              </div>
              <div className="space-y-2">
                <Label>Type</Label>
                <Select
                  value={createForm.type}
                  onValueChange={(value) => setCreateForm((prev) => ({ ...prev, type: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="local">Local</SelectItem>
                    <SelectItem value="toll-free">Toll-Free</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone-area-code">Area / Region Code (optional)</Label>
              <Input
                id="phone-area-code"
                placeholder="e.g., 512"
                value={createForm.areaCode}
                onChange={(event) => setCreateForm((prev) => ({ ...prev, areaCode: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone-label">Label (optional)</Label>
              <Input
                id="phone-label"
                placeholder="Austin sales line"
                value={createForm.label}
                onChange={(event) => setCreateForm((prev) => ({ ...prev, label: event.target.value }))}
              />
            </div>
            {createError && <p className="text-sm text-destructive">{createError}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateNumber} disabled={createLoading}>
              {createLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Provision
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PhoneNumbers;
