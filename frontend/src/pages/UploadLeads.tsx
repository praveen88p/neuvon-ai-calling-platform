import { useState, useCallback } from "react";
import { Upload, FileSpreadsheet, ArrowRight, ArrowLeft, Check, Loader2, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiPost, apiUpload } from "@/utils/api";
import { API_PATHS } from "@/utils/apiPaths";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useToast } from "@/hooks/use-toast";
import { useNavigate } from "react-router-dom";
import type { AgentListResponse, ContactListUploadResponse } from "@/types/api";

type Step = 1 | 2 | 3;

export default function UploadLeads() {
  const [currentStep, setCurrentStep] = useState<Step>(1);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();

  // Step 1: File upload
  const [file, setFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<ContactListUploadResponse | null>(null);
  const [countryCode, setCountryCode] = useState("+91");

  // Step 2: Campaign config
  const [campaignName, setCampaignName] = useState("");
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");
  const [concurrency, setConcurrency] = useState(1);

  // Step 3: Success
  const [createdCampaignId, setCreatedCampaignId] = useState<string | null>(null);

  // Fetch agents for step 2 agent selector
  const { data: agentData } = useApiQuery<AgentListResponse>(
    ["agents"],
    API_PATHS.AGENTS,
    { staleTime: 60_000 },
  );

  const agents = (agentData?.agents ?? []).filter((a) => a.status !== "archived");

  // ─── File handling ─────────────────────────────────────────────────────────

  const handleFile = useCallback((selectedFile: File) => {
    if (!selectedFile.name.endsWith(".csv") && !selectedFile.name.endsWith(".xlsx")) {
      toast({ title: "Invalid File", description: "Please upload a CSV or XLSX file.", variant: "destructive" });
      return;
    }
    setFile(selectedFile);
  }, [toast]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) handleFile(droppedFile);
    },
    [handleFile],
  );

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) handleFile(selectedFile);
  };

  // ─── Step 1 → 2: Upload the file ──────────────────────────────────────────

  const handleUpload = async () => {
    if (!file) return;
    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (countryCode && countryCode !== "already_included") {
        formData.append("country_code", countryCode);
      }
      const result = await apiUpload<ContactListUploadResponse>(
        API_PATHS.CAMPAIGNS_UPLOAD,
        formData,
      );
      setUploadResult(result);
      toast({
        title: "File Uploaded",
        description: `${result.total_contacts} contacts processed successfully.`,
      });
      setCurrentStep(2);
    } catch (err: unknown) {
      toast({
        title: "Upload Failed",
        description: err instanceof Error ? err.message : "Failed to upload file",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // ─── Step 2 → 3: Create campaign ──────────────────────────────────────────

  const handleCreateCampaign = async () => {
    if (!campaignName.trim()) {
      toast({ title: "Name Required", description: "Please enter a campaign name.", variant: "destructive" });
      return;
    }
    if (!selectedAgentId) {
      toast({ title: "Agent Required", description: "Please select an agent.", variant: "destructive" });
      return;
    }
    if (!uploadResult?.contact_list_id) {
      toast({ title: "Error", description: "No contact list. Please upload a file first.", variant: "destructive" });
      return;
    }

    setIsLoading(true);
    try {
      const result = await apiPost<{ id: string }>(API_PATHS.CAMPAIGNS, {
        name: campaignName.trim(),
        workflow_id: parseInt(selectedAgentId, 10),
        contact_list_id: uploadResult.contact_list_id,
        concurrency,
      });
      setCreatedCampaignId(result.id);
      toast({ title: "Campaign Created!", description: `${campaignName} is ready to start.` });
      setCurrentStep(3);
    } catch (err: unknown) {
      // 402 = insufficient minute balance
      const isPaymentRequired =
        err instanceof Error && (err as { status?: number }).status === 402;

      if (isPaymentRequired) {
        toast({
          title: "Insufficient Minutes",
          description: "You have no minutes available. Go to Settings → Billing to purchase a minute pack.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Creation Failed",
          description: err instanceof Error ? err.message : "Failed to create campaign",
          variant: "destructive",
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Create Campaign</h1>
        <p className="text-muted-foreground">Upload leads and configure your calling campaign</p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center gap-4">
        {[
          { step: 1, label: "Upload Contacts" },
          { step: 2, label: "Configure" },
          { step: 3, label: "Done" },
        ].map(({ step, label }) => (
          <div key={step} className="flex items-center gap-2">
            <div
              className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold transition-colors ${
                currentStep >= step
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {currentStep > step ? <Check className="h-4 w-4" /> : step}
            </div>
            <span className={`text-sm ${currentStep >= step ? "text-foreground font-medium" : "text-muted-foreground"}`}>
              {label}
            </span>
            {step < 3 && <ArrowRight className="h-4 w-4 text-muted-foreground mx-2" />}
          </div>
        ))}
      </div>

      {/* Step 1: Upload File */}
      {currentStep === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Contact List</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Drop zone */}
            <div
              className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
                isDragging ? "border-primary bg-primary/5" : "border-border"
              }`}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
            >
              {file ? (
                <div className="space-y-3">
                  <FileSpreadsheet className="h-12 w-12 text-primary mx-auto" />
                  <p className="text-lg font-semibold">{file.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                  <Button variant="ghost" size="sm" onClick={() => setFile(null)}>
                    Remove
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  <Upload className="h-12 w-12 text-muted-foreground mx-auto" />
                  <div>
                    <p className="text-lg font-semibold text-foreground">
                      Drag & drop your CSV file here
                    </p>
                    <p className="text-sm text-muted-foreground mt-1">
                      or click to browse. CSV format with a "phone_number" column required.
                    </p>
                  </div>
                  <label className="cursor-pointer">
                    <Input
                      type="file"
                      accept=".csv,.xlsx"
                      className="hidden"
                      onChange={handleFileInput}
                    />
                    <Button variant="outline" asChild>
                      <span>Browse Files</span>
                    </Button>
                  </label>
                </div>
              )}
            </div>

            {/* Country Code Selector */}
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-muted-foreground" />
                Default Country Code
              </Label>
              <Select value={countryCode} onValueChange={setCountryCode}>
                <SelectTrigger>
                  <SelectValue placeholder="Select country code" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="already_included">Numbers already include country code</SelectItem>
                  <SelectItem value="+91">🇮🇳 India (+91)</SelectItem>
                  <SelectItem value="+1">🇺🇸 United States (+1)</SelectItem>
                  <SelectItem value="+44">🇬🇧 United Kingdom (+44)</SelectItem>
                  <SelectItem value="+61">🇦🇺 Australia (+61)</SelectItem>
                  <SelectItem value="+971">🇦🇪 UAE (+971)</SelectItem>
                  <SelectItem value="+966">🇸🇦 Saudi Arabia (+966)</SelectItem>
                  <SelectItem value="+65">🇸🇬 Singapore (+65)</SelectItem>
                  <SelectItem value="+49">🇩🇪 Germany (+49)</SelectItem>
                  <SelectItem value="+33">🇫🇷 France (+33)</SelectItem>
                  <SelectItem value="+81">🇯🇵 Japan (+81)</SelectItem>
                  <SelectItem value="+86">🇨🇳 China (+86)</SelectItem>
                  <SelectItem value="+55">🇧🇷 Brazil (+55)</SelectItem>
                  <SelectItem value="+27">🇿🇦 South Africa (+27)</SelectItem>
                  <SelectItem value="+234">🇳🇬 Nigeria (+234)</SelectItem>
                  <SelectItem value="+254">🇰🇪 Kenya (+254)</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Applied to phone numbers that don't already start with '+'. If your CSV already has full international numbers, select "Numbers already include country code".
              </p>
            </div>

            <Button
              className="w-full"
              disabled={!file || isLoading}
              onClick={handleUpload}
            >
              {isLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <ArrowRight className="mr-2 h-4 w-4" />
              )}
              Upload & Continue
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Configure Campaign */}
      {currentStep === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Configure Campaign</CardTitle>
            {uploadResult && (
              <p className="text-sm text-muted-foreground mt-1">
                {uploadResult.total_contacts} contacts ready to call
              </p>
            )}
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Campaign Name */}
            <div className="space-y-2">
              <Label htmlFor="campaign-name">Campaign Name *</Label>
              <Input
                id="campaign-name"
                placeholder="e.g. Q3 Lead Follow-up"
                value={campaignName}
                onChange={(e) => setCampaignName(e.target.value)}
              />
            </div>

            {/* Agent Selection */}
            <div className="space-y-2">
              <Label>AI Agent *</Label>
              <Select value={selectedAgentId} onValueChange={setSelectedAgentId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select an agent" />
                </SelectTrigger>
                <SelectContent>
                  {agents.length === 0 ? (
                    <SelectItem value="none" disabled>
                      No agents available — create one first
                    </SelectItem>
                  ) : (
                    agents.map((agent) => (
                      <SelectItem key={agent.workflow_id} value={String(agent.workflow_id)}>
                        {agent.name}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                The agent defines the conversation flow for all calls in this campaign.
              </p>
            </div>

            {/* Concurrency */}
            <div className="space-y-2">
              <Label htmlFor="concurrency">Concurrency</Label>
              <Input
                id="concurrency"
                type="number"
                min={1}
                max={50}
                value={concurrency}
                onChange={(e) => setConcurrency(Math.max(1, parseInt(e.target.value) || 1))}
              />
              <p className="text-xs text-muted-foreground">
                Number of simultaneous calls. Higher = faster, but may affect quality.
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setCurrentStep(1)}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Button>
              <Button
                className="flex-1"
                disabled={!campaignName.trim() || !selectedAgentId || isLoading}
                onClick={handleCreateCampaign}
              >
                {isLoading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Check className="mr-2 h-4 w-4" />
                )}
                Create Campaign
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Success */}
      {currentStep === 3 && (
        <Card>
          <CardContent className="py-12 text-center space-y-6">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 mx-auto">
              <Check className="h-8 w-8 text-primary" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-foreground">Campaign Created!</h2>
              <p className="text-muted-foreground mt-2">
                Your campaign "{campaignName}" has been created with {uploadResult?.total_contacts ?? 0} contacts.
              </p>
            </div>
            <div className="flex gap-3 justify-center">
              {createdCampaignId && (
                <Button onClick={() => navigate(`/campaigns/${createdCampaignId}`)}>
                  View Campaign
                </Button>
              )}
              <Button variant="outline" onClick={() => navigate("/campaigns")}>
                All Campaigns
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setCurrentStep(1);
                  setFile(null);
                  setUploadResult(null);
                  setCampaignName("");
                  setSelectedAgentId("");
                  setConcurrency(1);
                  setCountryCode("+91");
                  setCreatedCampaignId(null);
                }}
              >
                Create Another
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
