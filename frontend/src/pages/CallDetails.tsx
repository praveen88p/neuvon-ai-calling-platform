import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Loader2, Phone, Clock, FileText, Mic, DollarSign, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiGet } from "@/utils/api";
import { callRunPath, callRecordingPath, callTranscriptPath } from "@/utils/apiPaths";
import type { CallRunResponse, DownloadUrlResponse } from "@/types/api";

export default function CallDetails() {
  const { id } = useParams<{ id: string }>();
  const [call, setCall] = useState<CallRunResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const fetchCall = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiGet<CallRunResponse>(callRunPath(id));
        setCall(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load call details");
      } finally {
        setLoading(false);
      }
    };
    fetchCall();
  }, [id]);

  const handleDownload = async (type: "recording" | "transcript") => {
    if (!id) return;
    try {
      const path = type === "recording" ? callRecordingPath(id) : callTranscriptPath(id);
      const data = await apiGet<DownloadUrlResponse>(path);
      if (data.url) {
        window.open(data.url, "_blank");
      }
    } catch (err) {
      console.error(`Failed to get ${type} URL:`, err);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !call) {
    return (
      <div className="p-8 text-center space-y-4">
        <p className="text-destructive text-lg">{error || "Call not found"}</p>
        <Button asChild>
          <Link to="/call-history">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Call History
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <Button variant="ghost" asChild className="mb-4">
          <Link to="/call-history">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Call History
          </Link>
        </Button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Call #{call.run_id}</h1>
            <p className="text-muted-foreground">
              {call.phone_number ?? "Unknown number"}
              {call.created_at && ` · ${new Date(call.created_at).toLocaleString()}`}
            </p>
          </div>
          <span className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${
            call.is_completed ? "bg-emerald-100 text-emerald-700" : "bg-blue-100 text-blue-700"
          }`}>
            {call.status ?? "Unknown"}
          </span>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6 flex items-center gap-3">
            <Phone className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Phone</p>
              <p className="font-mono font-medium">{call.phone_number ?? "-"}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 flex items-center gap-3">
            <Clock className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Duration</p>
              <p className="font-medium">
                {call.duration_seconds != null ? `${Math.round(call.duration_seconds)}s` : "-"}
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 flex items-center gap-3">
            <Bot className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Workflow</p>
              <p className="font-medium">{call.workflow_id}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 flex items-center gap-3">
            <DollarSign className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Cost</p>
              <p className="font-medium">
                {call.cost_info
                  ? `$${(call.cost_info as Record<string, number>).total_cost?.toFixed(2) ?? "-"}`
                  : "-"}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Download Actions */}
      <div className="flex gap-3">
        {call.recording_url && (
          <Button variant="outline" onClick={() => handleDownload("recording")}>
            <Mic className="mr-2 h-4 w-4" />
            Download Recording
          </Button>
        )}
        {call.transcript_url && (
          <Button variant="outline" onClick={() => handleDownload("transcript")}>
            <FileText className="mr-2 h-4 w-4" />
            Download Transcript
          </Button>
        )}
      </div>

      {/* Gathered Context */}
      {call.gathered_context && Object.keys(call.gathered_context).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Gathered Context</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2">
              {Object.entries(call.gathered_context).map(([key, value]) => (
                <div key={key} className="border rounded-lg p-3">
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">{key.replace(/_/g, " ")}</p>
                  <p className="text-sm font-medium mt-1">{String(value)}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Initial Context */}
      {call.initial_context && Object.keys(call.initial_context).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Initial Context</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-muted p-4 rounded-lg overflow-x-auto">
              {JSON.stringify(call.initial_context, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* Annotations */}
      {call.annotations && Object.keys(call.annotations).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Annotations</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-muted p-4 rounded-lg overflow-x-auto">
              {JSON.stringify(call.annotations, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}