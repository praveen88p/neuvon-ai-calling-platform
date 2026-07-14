import { useState, useRef } from "react";
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Play, Pause, Volume2, Copy, Download, CheckCircle, XCircle, HelpCircle, TrendingUp, MessageSquare, AlertCircle } from "lucide-react";
import { Call } from "./CallsTable";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";

interface CallDetailsDrawerProps {
  call: Call | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const outcomeColors = {
  Qualified: "bg-success/10 text-success border-success/20",
  "Not Interested": "bg-muted text-muted-foreground border-border",
  Voicemail: "bg-chart-2/10 text-chart-2 border-chart-2/20",
  DNC: "bg-destructive/10 text-destructive border-destructive/20",
  Callback: "bg-warning/10 text-warning border-warning/20",
  "No Answer": "bg-muted text-muted-foreground border-border",
};

export function CallDetailsDrawer({ call, open, onOpenChange }: CallDetailsDrawerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const audioRef = useRef<HTMLAudioElement>(null);

  if (!call) return null;

  const handlePlayPause = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleCopyTranscript = () => {
    if (call.transcript) {
      const text = call.transcript
        .map((t) => `${t.speaker === "agent" ? "Agent" : "Lead"}: ${t.text}`)
        .join("\n\n");
      navigator.clipboard.writeText(text);
      toast.success("Transcript copied to clipboard");
    }
  };

  const handleDownloadTranscript = () => {
    if (!call.transcript || call.transcript.length === 0) {
      toast.error("Transcript not available");
      return;
    }

    const text = call.transcript
      .map((t) => `${t.speaker === "agent" ? "Agent" : "Lead"}: ${t.text}`)
      .join("\n\n");

    const header = [
      `Call ID: ${call.id}`,
      `Lead: ${call.leadName}`,
      `Phone: ${call.phoneNumber}`,
      `Campaign: ${call.campaign}`,
      `Time: ${call.callTime}`,
      "",
      "--- Transcript ---",
      "",
    ].join("\n");

    const blob = new Blob([`${header}${text}\n`], { type: "text/plain;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `transcript_${call.id}.txt`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    toast.success("Transcript downloaded");
  };

  const qualificationIcon = {
    Yes: <CheckCircle className="h-5 w-5 text-success" />,
    No: <XCircle className="h-5 w-5 text-destructive" />,
    Maybe: <HelpCircle className="h-5 w-5 text-warning" />,
  };

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="max-h-[90vh]">
        <div className="mx-auto w-full max-w-4xl overflow-auto">
          <DrawerHeader className="border-b border-border pb-4">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <DrawerTitle className="text-2xl">{call.leadName}</DrawerTitle>
                <DrawerDescription className="text-base">{call.phoneNumber}</DrawerDescription>
              </div>
              <div className="flex flex-col items-end gap-2">
                <Badge variant="outline" className={outcomeColors[call.outcome]}>
                  {call.outcome}
                </Badge>
                <span className="text-sm text-muted-foreground">{call.campaign}</span>
              </div>
            </div>
            <div className="flex gap-4 mt-3 text-sm text-muted-foreground">
              <span>{call.callTime}</span>
              <span>•</span>
              <span>{call.duration}</span>
            </div>
          </DrawerHeader>

          <div className="p-6">
            <Tabs defaultValue="recording" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="recording">Recording</TabsTrigger>
                <TabsTrigger value="transcript">Transcript</TabsTrigger>
                <TabsTrigger value="insights">AI Insights</TabsTrigger>
              </TabsList>

              <TabsContent value="recording" className="space-y-4 mt-6">
                <Card>
                  <CardContent className="p-6">
                    <div className="space-y-4">
                      <div className="flex items-center gap-4">
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-12 w-12 rounded-full"
                          onClick={handlePlayPause}
                        >
                          {isPlaying ? (
                            <Pause className="h-5 w-5" />
                          ) : (
                            <Play className="h-5 w-5 ml-0.5" />
                          )}
                        </Button>
                        <div className="flex-1">
                          <Slider
                            value={[progress]}
                            onValueChange={(value) => setProgress(value[0])}
                            max={100}
                            step={1}
                            className="w-full"
                          />
                        </div>
                        <Volume2 className="h-5 w-5 text-muted-foreground" />
                      </div>
                      <audio ref={audioRef} src={call.recordingUrl || ""} />
                    </div>
                  </CardContent>
                </Card>

                <div className="grid grid-cols-2 gap-4">
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        Pathway
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-base font-medium text-foreground">
                        {call.pathway || "Standard Outreach"}
                      </p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        Persona
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-base font-medium text-foreground">
                        {call.persona || "Professional Alex"}
                      </p>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              <TabsContent value="transcript" className="space-y-4 mt-6">
                <div className="flex justify-end gap-2">
                  <Button variant="outline" size="sm" onClick={handleCopyTranscript}>
                    <Copy className="h-4 w-4 mr-2" />
                    Copy
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleDownloadTranscript}>
                    <Download className="h-4 w-4 mr-2" />
                    Download
                  </Button>
                </div>

                <Card>
                  <CardContent className="p-6">
                    <div className="space-y-4 max-h-[500px] overflow-y-auto">
                      {call.transcript && call.transcript.length > 0 ? (
                        call.transcript.map((item, idx) => (
                          <div key={idx} className="space-y-1">
                            <p className="text-sm font-semibold text-foreground">
                              {item.speaker === "agent" ? "Agent:" : "Lead:"}
                            </p>
                            <p className="text-sm text-muted-foreground pl-4">{item.text}</p>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-muted-foreground">Transcript not available</p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="insights" className="space-y-4 mt-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <TrendingUp className="h-5 w-5 text-primary" />
                        Qualification Summary
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Qualified</span>
                        <div className="flex items-center gap-2">
                          {call.aiInsights && qualificationIcon[call.aiInsights.qualified]}
                          <span className="font-medium text-foreground">
                            {call.aiInsights?.qualified || "Maybe"}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Score</span>
                        <span className="font-medium text-foreground">
                          {call.aiInsights?.score || call.qualificationScore}/100
                        </span>
                      </div>
                      <div className="pt-2 border-t border-border">
                        <p className="text-sm text-muted-foreground mb-1">Recommended Next Step</p>
                        <p className="text-sm font-medium text-foreground">
                          {call.aiInsights?.nextStep || "Follow up in 3-5 days"}
                        </p>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <MessageSquare className="h-5 w-5 text-accent" />
                        Lead Details
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div>
                        <span className="text-sm text-muted-foreground">Budget</span>
                        <p className="text-sm font-medium text-foreground mt-0.5">
                          {call.aiInsights?.budget || "$500K - $2M"}
                        </p>
                      </div>
                      <div>
                        <span className="text-sm text-muted-foreground">Timeline</span>
                        <p className="text-sm font-medium text-foreground mt-0.5">
                          {call.aiInsights?.timeline || "1-3 months"}
                        </p>
                      </div>
                      <div>
                        <span className="text-sm text-muted-foreground">Focus Area</span>
                        <p className="text-sm font-medium text-foreground mt-0.5">
                          {call.aiInsights?.interestArea || "Portfolio diversification"}
                        </p>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <TrendingUp className="h-5 w-5 text-success" />
                        Sentiment / Emotions
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex items-center gap-2">
                        <span className="text-2xl">
                          {call.sentiment === "Positive" ? "😊" : call.sentiment === "Negative" ? "😐" : "😊"}
                        </span>
                        <span className="font-medium text-foreground">
                          {call.aiInsights?.overallSentiment || call.sentiment}
                        </span>
                      </div>
                      <div className="h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className={`h-full ${
                            call.sentiment === "Positive"
                              ? "bg-success"
                              : call.sentiment === "Negative"
                              ? "bg-destructive"
                              : "bg-warning"
                          }`}
                          style={{ width: "75%" }}
                        />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Emotion trend over call duration (placeholder)
                      </p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <AlertCircle className="h-5 w-5 text-warning" />
                        Key Phrases / Objections
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap gap-2">
                        {call.aiInsights?.keyPhrases && call.aiInsights.keyPhrases.length > 0 ? (
                          call.aiInsights.keyPhrases.map((phrase, idx) => (
                            <Badge key={idx} variant="secondary" className="text-xs">
                              {phrase}
                            </Badge>
                          ))
                        ) : (
                          <>
                            <Badge variant="secondary" className="text-xs">
                              just exploring options
                            </Badge>
                            <Badge variant="secondary" className="text-xs">
                              waiting for market conditions
                            </Badge>
                            <Badge variant="secondary" className="text-xs">
                              need more info on fees
                            </Badge>
                          </>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  );
}
