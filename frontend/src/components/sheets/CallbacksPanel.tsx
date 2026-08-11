import { Clock, Phone, XCircle, CheckCircle2, AlertCircle, Loader2, Ban } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useToast } from "@/hooks/use-toast";
import { apiPost } from "@/utils/api";
import { sheetCallbacksPath, cancelCallbackPath } from "@/utils/apiPaths";
import { useQueryClient } from "@tanstack/react-query";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ScheduledCallback {
  id: string;
  phone_number: string;
  callback_at: string;
  status: "pending" | "triggered" | "completed" | "cancelled" | "failed";
  retry_count: number;
  display_time: string | null;
  sheet_leads?: {
    lead_data: Record<string, string>;
  };
}

interface CallbacksResponse {
  callbacks: ScheduledCallback[];
  total: number;
}

interface CallbacksPanelProps {
  connectionId: string;
}

// ─── Status config ────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; label: string; badge: string }> = {
  pending: {
    icon: <Clock className="h-3.5 w-3.5 text-amber-500" />,
    label: "Scheduled",
    badge: "bg-amber-500/10 text-amber-600 border-amber-500/20",
  },
  triggered: {
    icon: <Phone className="h-3.5 w-3.5 text-blue-500 animate-pulse" />,
    label: "Calling now",
    badge: "bg-blue-500/10 text-blue-600 border-blue-500/20",
  },
  completed: {
    icon: <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />,
    label: "Completed",
    badge: "bg-green-500/10 text-green-600 border-green-500/20",
  },
  cancelled: {
    icon: <Ban className="h-3.5 w-3.5 text-muted-foreground" />,
    label: "Cancelled",
    badge: "bg-muted/50 text-muted-foreground border-muted",
  },
  failed: {
    icon: <XCircle className="h-3.5 w-3.5 text-destructive" />,
    label: "Failed",
    badge: "bg-destructive/10 text-destructive border-destructive/20",
  },
};

function formatCallbackTime(isoOrDisplay: string | null, callbackAt: string): string {
  if (isoOrDisplay) return isoOrDisplay;
  try {
    return new Date(callbackAt).toLocaleString("en-IN", {
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit", hour12: true,
    });
  } catch {
    return callbackAt;
  }
}

function timeUntil(iso: string): string {
  const diff = new Date(iso).getTime() - Date.now();
  if (diff < 0) return "overdue";
  const min = Math.floor(diff / 60_000);
  if (min < 60) return `in ${min}m`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `in ${hr}h`;
  return `in ${Math.floor(hr / 24)}d`;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function CallbacksPanel({ connectionId }: CallbacksPanelProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useApiQuery<CallbacksResponse>(
    ["sheet-callbacks", connectionId],
    sheetCallbacksPath(connectionId),
    { staleTime: 15_000, refetchInterval: 60_000 },
  );

  const callbacks = data?.callbacks ?? [];

  const handleCancel = async (callbackId: string) => {
    try {
      await apiPost(cancelCallbackPath(callbackId));
      toast({ title: "Callback cancelled" });
      queryClient.invalidateQueries({ queryKey: ["sheet-callbacks", connectionId] });
    } catch (err: unknown) {
      toast({
        title: "Failed to cancel",
        description: err instanceof Error ? err.message : "Try again.",
        variant: "destructive",
      });
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-4">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-destructive text-xs px-4 py-2">
        <AlertCircle className="h-3.5 w-3.5" />
        Failed to load callbacks
      </div>
    );
  }

  if (callbacks.length === 0) {
    return (
      <p className="text-center text-xs text-muted-foreground py-4">
        No scheduled callbacks yet. When a lead says "Call me at X", it appears here.
      </p>
    );
  }

  return (
    <div className="divide-y">
      {callbacks.map((cb) => {
        const config = STATUS_CONFIG[cb.status] ?? STATUS_CONFIG["pending"];
        const leadData = cb.sheet_leads?.lead_data ?? {};
        const name = leadData["name"] || leadData["Name"] || "";

        return (
          <div key={cb.id} className="flex items-start gap-3 px-4 py-3 hover:bg-muted/20 transition-colors">
            {/* Status icon */}
            <div className="mt-0.5 shrink-0">{config.icon}</div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium">
                  {name || cb.phone_number}
                </span>
                {name && (
                  <span className="text-[11px] text-muted-foreground">{cb.phone_number}</span>
                )}
                <span className={`text-[10px] border rounded-full px-2 py-0.5 ${config.badge}`}>
                  {config.label}
                </span>
                {cb.retry_count > 0 && (
                  <span className="text-[10px] text-muted-foreground">
                    retry #{cb.retry_count}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-[11px] text-muted-foreground">
                  {formatCallbackTime(cb.display_time, cb.callback_at)}
                </span>
                {cb.status === "pending" && (
                  <span className="text-[11px] font-medium text-amber-600">
                    ({timeUntil(cb.callback_at)})
                  </span>
                )}
              </div>
            </div>

            {/* Cancel button for pending callbacks */}
            {cb.status === "pending" && (
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-destructive shrink-0"
                title="Cancel callback"
                onClick={() => handleCancel(cb.id)}
              >
                <XCircle className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        );
      })}
    </div>
  );
}
