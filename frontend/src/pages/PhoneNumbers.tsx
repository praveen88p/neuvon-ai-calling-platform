import { useState } from "react";
import { Phone, Loader2, Plus, Settings2, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useApiQuery } from "@/hooks/useApiQuery";
import { apiPost, apiDelete, apiGet } from "@/utils/api";
import { API_PATHS, phonePath } from "@/utils/apiPaths";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import type { PhoneNumberListResponse, PhoneNumberResponse, TelephonyConfigResponse } from "@/types/api";

export default function PhoneNumbers() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [newNumber, setNewNumber] = useState("");
  const [newLabel, setNewLabel] = useState("");

  // Phone numbers
  const { data, isLoading, error } = useApiQuery<PhoneNumberListResponse>(
    ["phone-numbers"],
    API_PATHS.PHONE_NUMBERS,
    { staleTime: 60_000 },
  );

  // Telephony config
  const { data: configData } = useApiQuery<TelephonyConfigResponse>(
    ["telephony-config"],
    API_PATHS.TELEPHONY_CONFIG,
    { staleTime: 120_000 },
  );

  const numbers = data?.phone_numbers ?? [];

  const handleAdd = async () => {
    if (!newNumber.trim()) return;
    try {
      await apiPost(API_PATHS.PHONE_NUMBERS, {
        phone_number: newNumber.trim(),
        label: newLabel.trim() || undefined,
      });
      toast({ title: "Phone Number Added", description: `${newNumber} added successfully.` });
      setShowAdd(false);
      setNewNumber("");
      setNewLabel("");
      queryClient.invalidateQueries({ queryKey: ["phone-numbers"] });
    } catch (err: unknown) {
      toast({
        title: "Failed to Add",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const handleDelete = async (phone: PhoneNumberResponse) => {
    if (!confirm(`Remove ${phone.phone_number}?`)) return;
    try {
      await apiDelete(phonePath(phone.id));
      toast({ title: "Removed", description: `${phone.phone_number} has been removed.` });
      queryClient.invalidateQueries({ queryKey: ["phone-numbers"] });
    } catch (err: unknown) {
      toast({
        title: "Failed to Remove",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Phone Numbers</h1>
          <p className="text-muted-foreground">Manage your calling phone numbers</p>
        </div>
        <Button onClick={() => setShowAdd(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Add Number
        </Button>
      </div>

      {/* Telephony Config */}
      {configData && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm">Telephony Configuration</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3 text-sm">
              <div>
                <p className="text-muted-foreground">Provider</p>
                <p className="font-medium capitalize">{configData.provider ?? "Not configured"}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Status</p>
                <p className="font-medium capitalize">{configData.status ?? "-"}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Region</p>
                <p className="font-medium">{configData.default_region ?? "-"}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Phone Numbers List */}
      {isLoading ? (
        <div className="flex items-center justify-center min-h-[300px]">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : error ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-destructive">{error instanceof Error ? error.message : "Failed to load"}</p>
          </CardContent>
        </Card>
      ) : numbers.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Phone className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-semibold">No phone numbers</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Add a phone number to start making calls.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3">
          {numbers.map((phone) => (
            <Card key={phone.id}>
              <CardContent className="py-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <Phone className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-mono font-medium">{phone.phone_number}</p>
                    <p className="text-sm text-muted-foreground">
                      {phone.label ?? "No label"}
                      {phone.is_active ? " · Active" : " · Inactive"}
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleDelete(phone)}
                  className="text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Add Dialog */}
      <Dialog open={showAdd} onOpenChange={setShowAdd}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Phone Number</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="number">Phone Number *</Label>
              <Input
                id="number"
                placeholder="+1234567890"
                value={newNumber}
                onChange={(e) => setNewNumber(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="label">Label</Label>
              <Input
                id="label"
                placeholder="e.g. Main Line"
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAdd(false)}>Cancel</Button>
            <Button onClick={handleAdd} disabled={!newNumber.trim()}>Add Number</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
