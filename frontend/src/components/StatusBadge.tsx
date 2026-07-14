import { Badge } from "@/components/ui/badge";

type Status = "live" | "completed" | "failed" | "paused" | "pending" | "qualified" | "not-interested" | "voicemail" | "dnc";

interface StatusBadgeProps {
  status: Status;
  className?: string;
}

const statusConfig: Record<Status, { label: string; variant: string }> = {
  live: { label: "Live", variant: "bg-green-100 text-green-700" },
  completed: { label: "Completed", variant: "bg-primary/10 text-primary" },
  failed: { label: "Failed", variant: "bg-destructive/10 text-destructive" },
  paused: { label: "Paused", variant: "bg-secondary text-secondary-foreground" },
  pending: { label: "Pending", variant: "bg-muted text-muted-foreground" },
  qualified: { label: "Qualified", variant: "bg-green-100 text-green-700" },
  "not-interested": { label: "Not Interested", variant: "bg-muted text-muted-foreground" },
  voicemail: { label: "Voicemail", variant: "bg-amber-100 text-amber-700" },
  dnc: { label: "DNC", variant: "bg-destructive/10 text-destructive" },
};

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  // Default to 'pending' if status is not found in the config or is undefined
  const config = status && status in statusConfig 
    ? statusConfig[status as Status] 
    : statusConfig['pending'];
  
  return (
    <Badge className={`${config.variant} ${className}`}>
      {status === "live" && (
        <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-green-500 animate-pulse" />
      )}
      {config.label}
    </Badge>
  );
}
