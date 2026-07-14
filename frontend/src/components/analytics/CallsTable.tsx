import { useState } from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Eye, ArrowUpDown } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export interface Call {
  id: string;
  leadName: string;
  phoneNumber: string;
  campaign: string;
  outcome: "Qualified" | "Not Interested" | "Voicemail" | "DNC" | "Callback" | "No Answer";
  qualificationScore: number;
  sentiment: "Positive" | "Neutral" | "Negative";
  duration: string;
  callTime: string;
  recordingUrl?: string;
  transcript?: { speaker: "agent" | "lead"; text: string }[];
  aiInsights?: {
    qualified: "Yes" | "No" | "Maybe";
    score: number;
    nextStep: string;
    budget?: string;
    timeline?: string;
    interestArea?: string;
    overallSentiment: string;
    keyPhrases: string[];
  };
  pathway?: string;
  persona?: string;
}

interface CallsTableProps {
  calls: Call[];
  onViewCall: (call: Call) => void;
  isLoading?: boolean;
}

const outcomeColors = {
  Qualified: "bg-success/10 text-success border-success/20",
  "Not Interested": "bg-muted text-muted-foreground border-border",
  Voicemail: "bg-chart-2/10 text-chart-2 border-chart-2/20",
  DNC: "bg-destructive/10 text-destructive border-destructive/20",
  Callback: "bg-warning/10 text-warning border-warning/20",
  "No Answer": "bg-muted text-muted-foreground border-border",
};

const sentimentColors = {
  Positive: "text-success",
  Neutral: "text-muted-foreground",
  Negative: "text-destructive",
};

export function CallsTable({ calls, onViewCall, isLoading }: CallsTableProps) {
  const [sortField, setSortField] = useState<"callTime" | "duration">("callTime");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const handleSort = (field: "callTime" | "duration") => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const sortedCalls = [...calls].sort((a, b) => {
    let comparison = 0;
    if (sortField === "callTime") {
      comparison = new Date(a.callTime).getTime() - new Date(b.callTime).getTime();
    } else if (sortField === "duration") {
      const getDurationSeconds = (duration: string) => {
        const [mins, secs] = duration.split(":").map(Number);
        return mins * 60 + secs;
      };
      comparison = getDurationSeconds(a.duration) - getDurationSeconds(b.duration);
    }
    return sortDirection === "asc" ? comparison : -comparison;
  });

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  if (calls.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-muted-foreground">No calls match your filters yet</p>
        <p className="text-sm text-muted-foreground mt-1">Try adjusting your search criteria</p>
      </div>
    );
  }

  return (
    <div className="rounded-md border border-border">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Lead Name</TableHead>
            <TableHead>Phone Number</TableHead>
            <TableHead>Campaign</TableHead>
            <TableHead>Outcome</TableHead>
            <TableHead>Qual. Score</TableHead>
            <TableHead>Sentiment</TableHead>
            <TableHead>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2 hover:bg-muted"
                onClick={() => handleSort("duration")}
              >
                Duration
                <ArrowUpDown className="ml-2 h-3 w-3" />
              </Button>
            </TableHead>
            <TableHead>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2 hover:bg-muted"
                onClick={() => handleSort("callTime")}
              >
                Call Time
                <ArrowUpDown className="ml-2 h-3 w-3" />
              </Button>
            </TableHead>
            <TableHead className="text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedCalls.map((call) => (
            <TableRow
              key={call.id}
              className="cursor-pointer hover:bg-muted/50"
              onClick={() => onViewCall(call)}
            >
              <TableCell className="font-medium text-foreground">{call.leadName}</TableCell>
              <TableCell className="text-muted-foreground">{call.phoneNumber}</TableCell>
              <TableCell className="text-muted-foreground">{call.campaign}</TableCell>
              <TableCell>
                <Badge variant="outline" className={outcomeColors[call.outcome]}>
                  {call.outcome}
                </Badge>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-20 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary"
                      style={{ width: `${call.qualificationScore}%` }}
                    />
                  </div>
                  <span className="text-sm text-muted-foreground">{call.qualificationScore}</span>
                </div>
              </TableCell>
              <TableCell>
                <span className={`text-sm font-medium ${sentimentColors[call.sentiment]}`}>
                  {call.sentiment}
                </span>
              </TableCell>
              <TableCell className="text-muted-foreground">{call.duration}</TableCell>
              <TableCell className="text-muted-foreground">{call.callTime}</TableCell>
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    onViewCall(call);
                  }}
                >
                  <Eye className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
