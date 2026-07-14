import { useState, useCallback } from "react";
import {
  Calendar,
  Loader2,
  Search,
  Phone,
  User,
  Clock,
  CalendarCheck,
  CalendarX,
  Settings2,
  Plus,
  Trash2,
  Check,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiQuery } from "@/hooks/useApiQuery";
import { apiPatch, apiPut, apiPost, apiDelete } from "@/utils/api";
import { API_PATHS, appointmentPath } from "@/utils/apiPaths";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import type {
  AppointmentListResponse,
  AppointmentResponse,
  WeeklyScheduleResponse,
  WeeklySlot,
  OverrideListResponse,
} from "@/types/api";

// ─── Constants ───────────────────────────────────────────────────────────────

const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const DAY_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const DEFAULT_START = "09:00";
const DEFAULT_END = "17:00";

// ─── Status Badge ────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const s = status.toLowerCase();
  const styles: Record<string, string> = {
    scheduled: "bg-blue-100 text-blue-700",
    confirmed: "bg-emerald-100 text-emerald-700",
    completed: "bg-gray-100 text-gray-700",
    cancelled: "bg-red-100 text-red-700",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[s] ?? "bg-gray-100 text-gray-600"}`}>
      {s.charAt(0).toUpperCase() + s.slice(1)}
    </span>
  );
}

// ─── Availability Manager ────────────────────────────────────────────────────

function AvailabilityManager() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: schedule, isLoading } = useApiQuery<WeeklyScheduleResponse>(
    ["availability-schedule"],
    API_PATHS.AVAILABILITY_SCHEDULE,
    { staleTime: 60_000 },
  );

  const { data: overrides } = useApiQuery<OverrideListResponse>(
    ["availability-overrides"],
    API_PATHS.AVAILABILITY_OVERRIDES,
    { staleTime: 60_000 },
  );

  // Local state for editing
  const [editSlots, setEditSlots] = useState<WeeklySlot[] | null>(null);
  const [saving, setSaving] = useState(false);

  // Override form
  const [overrideDate, setOverrideDate] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [addingOverride, setAddingOverride] = useState(false);

  // Initialize edit state from fetched data
  const slots = editSlots ?? schedule?.slots ?? [];

  const isEditing = editSlots !== null;

  const startEditing = () => {
    // Build a full 7-day array from existing slots
    const existing = schedule?.slots ?? [];
    const full: WeeklySlot[] = [];
    for (let d = 0; d < 7; d++) {
      const found = existing.find((s) => s.day_of_week === d);
      full.push({
        day_of_week: d,
        start_time: found?.start_time ?? DEFAULT_START,
        end_time: found?.end_time ?? DEFAULT_END,
        is_active: found?.is_active ?? false,
      });
    }
    setEditSlots(full);
  };

  const toggleDay = (dayIdx: number) => {
    if (!editSlots) return;
    setEditSlots(
      editSlots.map((s) =>
        s.day_of_week === dayIdx ? { ...s, is_active: !s.is_active } : s,
      ),
    );
  };

  const updateSlotTime = (dayIdx: number, field: "start_time" | "end_time", value: string) => {
    if (!editSlots) return;
    setEditSlots(
      editSlots.map((s) =>
        s.day_of_week === dayIdx ? { ...s, [field]: value } : s,
      ),
    );
  };

  const saveSchedule = async () => {
    if (!editSlots) return;
    setSaving(true);
    try {
      const activeSlots = editSlots.filter((s) => s.is_active);
      await apiPut(API_PATHS.AVAILABILITY_SCHEDULE, { slots: activeSlots });
      toast({ title: "Schedule Saved", description: `${activeSlots.length} days configured.` });
      queryClient.invalidateQueries({ queryKey: ["availability-schedule"] });
      setEditSlots(null);
    } catch (err: unknown) {
      toast({
        title: "Save Failed",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleAddOverride = async () => {
    if (!overrideDate) return;
    setAddingOverride(true);
    try {
      await apiPost(API_PATHS.AVAILABILITY_OVERRIDES, {
        override_date: overrideDate,
        is_available: false,
        reason: overrideReason || "Blocked",
      });
      toast({ title: "Date Blocked", description: `${overrideDate} marked as unavailable.` });
      queryClient.invalidateQueries({ queryKey: ["availability-overrides"] });
      setOverrideDate("");
      setOverrideReason("");
    } catch (err: unknown) {
      toast({
        title: "Failed",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setAddingOverride(false);
    }
  };

  const handleDeleteOverride = async (id: string) => {
    try {
      await apiDelete(`${API_PATHS.AVAILABILITY_OVERRIDES}/${id}`);
      toast({ title: "Override Removed" });
      queryClient.invalidateQueries({ queryKey: ["availability-overrides"] });
    } catch (err: unknown) {
      toast({
        title: "Failed",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[200px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Weekly Schedule */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Weekly Schedule
          </CardTitle>
          {!isEditing ? (
            <Button size="sm" variant="outline" onClick={startEditing}>
              <Settings2 className="h-4 w-4 mr-1" /> Edit Schedule
            </Button>
          ) : (
            <div className="flex gap-2">
              <Button size="sm" variant="ghost" onClick={() => setEditSlots(null)}>
                Cancel
              </Button>
              <Button size="sm" onClick={saveSchedule} disabled={saving}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Check className="h-4 w-4 mr-1" />}
                Save
              </Button>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {isEditing ? (
            <div className="space-y-3">
              {editSlots!.map((slot) => (
                <div
                  key={slot.day_of_week}
                  className={`flex items-center gap-4 p-3 rounded-lg border transition-colors ${
                    slot.is_active ? "bg-primary/5 border-primary/20" : "bg-muted/30 border-border"
                  }`}
                >
                  <button
                    onClick={() => toggleDay(slot.day_of_week)}
                    className={`w-20 text-sm font-medium text-left ${slot.is_active ? "text-foreground" : "text-muted-foreground"}`}
                  >
                    {DAY_NAMES[slot.day_of_week]}
                  </button>

                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={slot.is_active}
                      onChange={() => toggleDay(slot.day_of_week)}
                      className="h-4 w-4 rounded border-border"
                    />
                  </label>

                  {slot.is_active && (
                    <>
                      <Input
                        type="time"
                        value={slot.start_time}
                        onChange={(e) => updateSlotTime(slot.day_of_week, "start_time", e.target.value)}
                        className="w-32"
                      />
                      <span className="text-muted-foreground">to</span>
                      <Input
                        type="time"
                        value={slot.end_time}
                        onChange={(e) => updateSlotTime(slot.day_of_week, "end_time", e.target.value)}
                        className="w-32"
                      />
                    </>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {slots.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  No availability set. Click "Edit Schedule" to configure your weekly hours.
                </p>
              ) : (
                slots
                  .filter((s) => s.is_active)
                  .sort((a, b) => a.day_of_week - b.day_of_week)
                  .map((slot) => (
                    <div key={slot.day_of_week} className="flex items-center justify-between py-2 px-3 rounded-lg bg-muted/30">
                      <span className="font-medium text-sm">{DAY_NAMES[slot.day_of_week]}</span>
                      <span className="text-sm text-muted-foreground">
                        {slot.start_time} — {slot.end_time}
                      </span>
                    </div>
                  ))
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Date Overrides */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarX className="h-5 w-5" />
            Blocked Dates
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Add override form */}
          <div className="flex items-end gap-3">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Date</label>
              <Input
                type="date"
                value={overrideDate}
                onChange={(e) => setOverrideDate(e.target.value)}
                className="w-44"
              />
            </div>
            <div className="space-y-1 flex-1">
              <label className="text-xs text-muted-foreground">Reason (optional)</label>
              <Input
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder="e.g., Holiday, Personal day"
              />
            </div>
            <Button size="sm" onClick={handleAddOverride} disabled={!overrideDate || addingOverride}>
              {addingOverride ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            </Button>
          </div>

          {/* Override list */}
          {overrides?.overrides?.length ? (
            <div className="space-y-2">
              {overrides.overrides.map((ov) => (
                <div key={ov.id} className="flex items-center justify-between py-2 px-3 rounded-lg bg-red-50 border border-red-100">
                  <div>
                    <span className="font-medium text-sm">{ov.override_date}</span>
                    {ov.reason && <span className="text-xs text-muted-foreground ml-2">— {ov.reason}</span>}
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => handleDeleteOverride(ov.id)}>
                    <Trash2 className="h-3.5 w-3.5 text-destructive" />
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-2">No blocked dates.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Appointments List ───────────────────────────────────────────────────────

function AppointmentsList() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useApiQuery<AppointmentListResponse>(
    ["appointments"],
    API_PATHS.APPOINTMENTS,
    { staleTime: 30_000 },
  );

  const appointments = data?.appointments ?? [];

  const filtered = appointments.filter((a) => {
    const matchSearch = !search
      || (a.contact_name || "").toLowerCase().includes(search.toLowerCase())
      || (a.contact_phone || "").includes(search)
      || (a.notes || "").toLowerCase().includes(search.toLowerCase());

    const matchStatus = statusFilter === "all" || a.status === statusFilter;

    return matchSearch && matchStatus;
  });

  const handleStatusUpdate = async (apt: AppointmentResponse, newStatus: string) => {
    try {
      await apiPatch(appointmentPath(apt.id), { status: newStatus });
      toast({
        title: "Status Updated",
        description: `Appointment for ${apt.contact_name || apt.contact_phone} marked as ${newStatus}.`,
      });
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
    } catch (err: unknown) {
      toast({
        title: "Update Failed",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  // KPI counters
  const total = appointments.length;
  const upcoming = appointments.filter((a) => a.status === "scheduled").length;
  const confirmed = appointments.filter((a) => a.status === "confirmed").length;
  const cancelled = appointments.filter((a) => a.status === "cancelled").length;

  const statuses = ["all", "scheduled", "confirmed", "completed", "cancelled"];

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Calendar className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Total</p>
              <p className="text-2xl font-bold">{total}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100">
              <Clock className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Upcoming</p>
              <p className="text-2xl font-bold">{upcoming}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100">
              <CalendarCheck className="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Confirmed</p>
              <p className="text-2xl font-bold">{confirmed}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-100">
              <CalendarX className="h-5 w-5 text-red-600" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Cancelled</p>
              <p className="text-2xl font-bold">{cancelled}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name, phone, or notes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-1.5">
          {statuses.map((s) => (
            <Button
              key={s}
              size="sm"
              variant={statusFilter === s ? "default" : "outline"}
              onClick={() => setStatusFilter(s)}
              className="capitalize text-xs"
            >
              {s}
            </Button>
          ))}
        </div>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="flex items-center justify-center min-h-[300px]">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : error ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-destructive">{error instanceof Error ? error.message : "Failed to load"}</p>
            <Button className="mt-3" onClick={() => window.location.reload()}>Retry</Button>
          </CardContent>
        </Card>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Calendar className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-semibold">{search || statusFilter !== "all" ? "No matches found" : "No appointments yet"}</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Appointments are automatically created when your AI agent schedules one during a call.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((apt) => (
            <Card key={apt.id} className="hover:shadow-md transition-shadow">
              <CardContent className="pt-6 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{apt.contact_name || "Unknown"}</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Phone className="h-3 w-3" />
                      <span className="font-mono">{apt.contact_phone || "-"}</span>
                    </div>
                  </div>
                  <StatusBadge status={apt.status} />
                </div>

                {apt.appointment_date && (
                  <div className="flex items-center gap-2 text-sm">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span>{new Date(apt.appointment_date).toLocaleString()}</span>
                  </div>
                )}

                <div className="flex items-center gap-2 text-sm">
                  <span className="inline-flex items-center rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700">
                    {apt.campaign_name || "Test Call"}
                  </span>
                </div>

                {apt.notes && (
                  <p className="text-sm text-muted-foreground line-clamp-2">{apt.notes}</p>
                )}

                {/* Status actions */}
                <div className="flex gap-2 pt-2">
                  {apt.status === "scheduled" && (
                    <Button size="sm" variant="outline" onClick={() => handleStatusUpdate(apt, "confirmed")}>
                      Confirm
                    </Button>
                  )}
                  {(apt.status === "scheduled" || apt.status === "confirmed") && (
                    <>
                      <Button size="sm" variant="outline" onClick={() => handleStatusUpdate(apt, "completed")}>
                        Complete
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleStatusUpdate(apt, "cancelled")}>
                        Cancel
                      </Button>
                    </>
                  )}
                </div>

                <p className="text-xs text-muted-foreground">
                  {new Date(apt.created_at).toLocaleDateString()}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function Appointments() {
  const [tab, setTab] = useState<"appointments" | "availability">("appointments");

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Appointments</h1>
        <p className="text-muted-foreground">
          Manage appointments and your availability schedule
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        <button
          onClick={() => setTab("appointments")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            tab === "appointments"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <CalendarCheck className="h-4 w-4 inline mr-1.5" />
          Appointments
        </button>
        <button
          onClick={() => setTab("availability")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            tab === "availability"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Clock className="h-4 w-4 inline mr-1.5" />
          My Availability
        </button>
      </div>

      {/* Tab Content */}
      {tab === "appointments" ? <AppointmentsList /> : <AvailabilityManager />}
    </div>
  );
}
