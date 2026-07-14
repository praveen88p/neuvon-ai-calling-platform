import { useState } from "react";
import { Upload, FileSpreadsheet, ArrowRight, ArrowLeft, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useNavigate } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import { Progress } from "@/components/ui/progress";

type Step = 1 | 2 | 3 | 4;

interface UploadedFile {
  name: string;
  size: number;
  preview: string[][];
}

interface ColumnMapping {
  name: string;
  phone: string;
  email?: string;
  address?: string;
}

interface CampaignConfig {
  name: string;
  pathway: string;
  persona: string;
  phoneNumber: string;
}

export default function UploadLeads() {
  const [currentStep, setCurrentStep] = useState<Step>(1);
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);
  const [columnMapping, setColumnMapping] = useState<ColumnMapping>({
    name: "",
    phone: "",
    email: "",
    address: "",
  });
  const [campaignConfig, setCampaignConfig] = useState<CampaignConfig>({
    name: "",
    pathway: "",
    persona: "",
    phoneNumber: "",
  });
  const [isDragging, setIsDragging] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    handleFileUpload(files[0]);
  };

  const handleFileUpload = (file: File) => {
    if (!file) return;

    // Validate file type
    const validTypes = [".csv", ".xlsx", ".xls"];
    const fileExtension = file.name.substring(file.name.lastIndexOf("."));
    
    if (!validTypes.includes(fileExtension.toLowerCase())) {
      toast({
        title: "Invalid file type",
        description: "Please upload a CSV or Excel file",
        variant: "destructive",
      });
      return;
    }

    // Mock file preview - in production, parse actual file
    const mockPreview = [
      ["Name", "Phone", "Email", "Address"],
      ["John Smith", "(555) 123-4567", "john@example.com", "123 Main St"],
      ["Sarah Johnson", "(555) 234-5678", "sarah@example.com", "456 Oak Ave"],
      ["Michael Chen", "(555) 345-6789", "michael@example.com", "789 Pine Rd"],
    ];

    setUploadedFile({
      name: file.name,
      size: file.size,
      preview: mockPreview,
    });

    toast({
      title: "File uploaded",
      description: `${file.name} uploaded successfully`,
    });

    setCurrentStep(2);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileUpload(file);
  };

  const validateColumnMapping = () => {
    if (!columnMapping.name || !columnMapping.phone) {
      toast({
        title: "Required fields missing",
        description: "Name and Phone columns are required",
        variant: "destructive",
      });
      return false;
    }
    return true;
  };

  const validateCampaignConfig = () => {
    if (!campaignConfig.name || !campaignConfig.pathway || !campaignConfig.persona || !campaignConfig.phoneNumber) {
      toast({
        title: "Required fields missing",
        description: "Please fill in all campaign details",
        variant: "destructive",
      });
      return false;
    }
    return true;
  };

  const handleNext = () => {
    if (currentStep === 2 && !validateColumnMapping()) return;
    if (currentStep === 3 && !validateCampaignConfig()) return;
    
    if (currentStep < 4) {
      setCurrentStep((currentStep + 1) as Step);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((currentStep - 1) as Step);
    }
  };

  const handleLaunch = () => {
    toast({
      title: "Campaign launched!",
      description: `${campaignConfig.name} is now running`,
    });
    navigate("/campaigns");
  };

  const stepProgress = (currentStep / 4) * 100;

  const pathways = ["Seller Script v2", "Buyer Qualification", "FSBO Script", "Expired Script"];
  const personas = ["Professional Jane", "Friendly Mike", "Empathetic Sarah"];
  const phoneNumbers = ["+1 (555) 100-0001", "+1 (555) 100-0002", "+1 (555) 100-0003"];

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Upload Leads</h1>
        <p className="text-muted-foreground">Create a new calling campaign in 4 simple steps</p>
      </div>

      {/* Progress */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-foreground">Step {currentStep} of 4</span>
          <span className="text-muted-foreground">{stepProgress.toFixed(0)}% Complete</span>
        </div>
        <Progress value={stepProgress} className="h-2" />
      </div>

      {/* Step Indicator */}
      <div className="flex items-center justify-between">
        {[
          { num: 1, label: "Upload File" },
          { num: 2, label: "Map Columns" },
          { num: 3, label: "Configure" },
          { num: 4, label: "Launch" },
        ].map((step) => (
          <div key={step.num} className="flex items-center gap-2">
            <div
              className={`flex h-10 w-10 items-center justify-center rounded-full font-semibold ${
                currentStep > step.num
                  ? "bg-success text-white"
                  : currentStep === step.num
                  ? "bg-primary text-white"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {currentStep > step.num ? <Check className="h-5 w-5" /> : step.num}
            </div>
            <span
              className={`hidden md:block text-sm font-medium ${
                currentStep >= step.num ? "text-foreground" : "text-muted-foreground"
              }`}
            >
              {step.label}
            </span>
          </div>
        ))}
      </div>

      {/* Step Content */}
      <Card className="min-h-96">
        <CardHeader>
          <CardTitle>
            {currentStep === 1 && "Upload Lead File"}
            {currentStep === 2 && "Map Columns"}
            {currentStep === 3 && "Campaign Configuration"}
            {currentStep === 4 && "Review & Launch"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Step 1: Upload */}
          {currentStep === 1 && (
            <div className="space-y-6">
              <div
                className={`relative rounded-lg border-2 border-dashed p-12 text-center transition-colors ${
                  isDragging
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50 hover:bg-muted/50"
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  id="file-upload"
                  className="hidden"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileInput}
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                    <Upload className="h-8 w-8 text-primary" />
                  </div>
                  <h3 className="mb-2 text-lg font-semibold text-foreground">
                    Drop your file here, or click to browse
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Supports CSV, XLSX, and XLS files up to 10MB
                  </p>
                </label>
              </div>

              {uploadedFile && (
                <Card className="bg-muted/50">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <FileSpreadsheet className="h-8 w-8 text-success" />
                        <div>
                          <p className="font-medium text-foreground">{uploadedFile.name}</p>
                          <p className="text-sm text-muted-foreground">
                            {(uploadedFile.size / 1024).toFixed(2)} KB
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setUploadedFile(null)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* Step 2: Column Mapping */}
          {currentStep === 2 && uploadedFile && (
            <div className="space-y-6">
              <div className="rounded-lg border border-border bg-muted/30 p-4">
                <p className="text-sm text-muted-foreground mb-4">
                  Preview of your data (first 3 rows):
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        {uploadedFile.preview[0].map((header, i) => (
                          <th key={i} className="px-4 py-2 text-left font-medium text-foreground">
                            {header}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {uploadedFile.preview.slice(1).map((row, i) => (
                        <tr key={i} className="border-b border-border/50">
                          {row.map((cell, j) => (
                            <td key={j} className="px-4 py-2 text-muted-foreground">
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="name-column">
                    Name Column <span className="text-destructive">*</span>
                  </Label>
                  <Select
                    value={columnMapping.name}
                    onValueChange={(value) =>
                      setColumnMapping({ ...columnMapping, name: value })
                    }
                  >
                    <SelectTrigger id="name-column">
                      <SelectValue placeholder="Select column" />
                    </SelectTrigger>
                    <SelectContent>
                      {uploadedFile.preview[0].map((header) => (
                        <SelectItem key={header} value={header}>
                          {header}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="phone-column">
                    Phone Column <span className="text-destructive">*</span>
                  </Label>
                  <Select
                    value={columnMapping.phone}
                    onValueChange={(value) =>
                      setColumnMapping({ ...columnMapping, phone: value })
                    }
                  >
                    <SelectTrigger id="phone-column">
                      <SelectValue placeholder="Select column" />
                    </SelectTrigger>
                    <SelectContent>
                      {uploadedFile.preview[0].map((header) => (
                        <SelectItem key={header} value={header}>
                          {header}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email-column">Email Column (Optional)</Label>
                  <Select
                    value={columnMapping.email}
                    onValueChange={(value) =>
                      setColumnMapping({ ...columnMapping, email: value })
                    }
                  >
                    <SelectTrigger id="email-column">
                      <SelectValue placeholder="Select column" />
                    </SelectTrigger>
                    <SelectContent>
                      {uploadedFile.preview[0].map((header) => (
                        <SelectItem key={header} value={header}>
                          {header}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="address-column">Address Column (Optional)</Label>
                  <Select
                    value={columnMapping.address}
                    onValueChange={(value) =>
                      setColumnMapping({ ...columnMapping, address: value })
                    }
                  >
                    <SelectTrigger id="address-column">
                      <SelectValue placeholder="Select column" />
                    </SelectTrigger>
                    <SelectContent>
                      {uploadedFile.preview[0].map((header) => (
                        <SelectItem key={header} value={header}>
                          {header}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Configuration */}
          {currentStep === 3 && (
            <div className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="campaign-name">
                  Campaign Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="campaign-name"
                  placeholder="e.g., Q4 Seller Leads"
                  value={campaignConfig.name}
                  onChange={(e) =>
                    setCampaignConfig({ ...campaignConfig, name: e.target.value })
                  }
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="pathway">
                    Pathway (Script) <span className="text-destructive">*</span>
                  </Label>
                  <Select
                    value={campaignConfig.pathway}
                    onValueChange={(value) =>
                      setCampaignConfig({ ...campaignConfig, pathway: value })
                    }
                  >
                    <SelectTrigger id="pathway">
                      <SelectValue placeholder="Select pathway" />
                    </SelectTrigger>
                    <SelectContent>
                      {pathways.map((pathway) => (
                        <SelectItem key={pathway} value={pathway}>
                          {pathway}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="persona">
                    Persona (Voice) <span className="text-destructive">*</span>
                  </Label>
                  <Select
                    value={campaignConfig.persona}
                    onValueChange={(value) =>
                      setCampaignConfig({ ...campaignConfig, persona: value })
                    }
                  >
                    <SelectTrigger id="persona">
                      <SelectValue placeholder="Select persona" />
                    </SelectTrigger>
                    <SelectContent>
                      {personas.map((persona) => (
                        <SelectItem key={persona} value={persona}>
                          {persona}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone-number">
                  Outbound Phone Number <span className="text-destructive">*</span>
                </Label>
                <Select
                  value={campaignConfig.phoneNumber}
                  onValueChange={(value) =>
                    setCampaignConfig({ ...campaignConfig, phoneNumber: value })
                  }
                >
                  <SelectTrigger id="phone-number">
                    <SelectValue placeholder="Select phone number" />
                  </SelectTrigger>
                  <SelectContent>
                    {phoneNumbers.map((number) => (
                      <SelectItem key={number} value={number}>
                        {number}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {/* Step 4: Review */}
          {currentStep === 4 && uploadedFile && (
            <div className="space-y-6">
              <div className="rounded-lg border border-border bg-muted/30 p-6 space-y-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">File</p>
                  <p className="text-foreground font-medium">{uploadedFile.name}</p>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-1">Campaign Name</p>
                    <p className="text-foreground font-medium">{campaignConfig.name}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-1">Total Leads</p>
                    <p className="text-foreground font-medium">
                      {uploadedFile.preview.length - 1} leads
                    </p>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-1">Pathway</p>
                    <p className="text-foreground font-medium">{campaignConfig.pathway}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-1">Persona</p>
                    <p className="text-foreground font-medium">{campaignConfig.persona}</p>
                  </div>
                </div>

                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">Phone Number</p>
                  <p className="text-foreground font-medium">{campaignConfig.phoneNumber}</p>
                </div>

                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">Column Mapping</p>
                  <div className="mt-2 space-y-1 text-sm">
                    <p className="text-foreground">
                      <span className="font-medium">Name:</span> {columnMapping.name}
                    </p>
                    <p className="text-foreground">
                      <span className="font-medium">Phone:</span> {columnMapping.phone}
                    </p>
                    {columnMapping.email && (
                      <p className="text-foreground">
                        <span className="font-medium">Email:</span> {columnMapping.email}
                      </p>
                    )}
                    {columnMapping.address && (
                      <p className="text-foreground">
                        <span className="font-medium">Address:</span> {columnMapping.address}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-warning/50 bg-warning/5 p-4">
                <p className="text-sm text-foreground">
                  🚀 <span className="font-medium">Ready to launch!</span> Your campaign will start
                  calling leads immediately after you click "Launch Campaign".
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          onClick={handleBack}
          disabled={currentStep === 1}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>

        {currentStep < 4 ? (
          <Button onClick={handleNext} disabled={currentStep === 1 && !uploadedFile}>
            Next
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={handleLaunch} className="bg-success hover:bg-success/90">
            <Check className="mr-2 h-4 w-4" />
            Launch Campaign
          </Button>
        )}
      </div>
    </div>
  );
}
