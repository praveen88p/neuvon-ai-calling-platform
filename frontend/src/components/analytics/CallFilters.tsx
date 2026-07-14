import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";

interface CallFiltersProps {
  filters: CallFilterState;
  options: CallFilterOptions;
  onFilterChange: (filters: CallFilterState) => void;
}

export interface CallFilterState {
  campaign?: string;
  outcome?: string;
  persona?: string;
  pathway?: string;
  search?: string;
}

export interface CallFilterOptions {
  campaigns: string[];
  outcomes: string[];
  personas: string[];
  pathways: string[];
}

export function CallFilters({ filters, options, onFilterChange }: CallFiltersProps) {
  const handleChange = (key: keyof CallFilterState, value: string) => {
    onFilterChange({
      ...filters,
      [key]: value === "all" ? undefined : value,
    });
  };

  return (
    <div className="flex flex-wrap gap-3 items-center">
      <div className="relative flex-1 min-w-[200px]">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search by lead name or phone..."
          className="pl-9"
          value={filters.search ?? ""}
          onChange={(e) => handleChange("search", e.target.value)}
        />
      </div>

      <Select
        value={filters.campaign ?? "all"}
        onValueChange={(value) => handleChange("campaign", value)}
      >
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Campaign" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Campaigns</SelectItem>
          {options.campaigns.map((campaign) => (
            <SelectItem key={campaign} value={campaign}>
              {campaign}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filters.outcome ?? "all"}
        onValueChange={(value) => handleChange("outcome", value)}
      >
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Outcome" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Outcomes</SelectItem>
          {options.outcomes.map((outcome) => (
            <SelectItem key={outcome} value={outcome}>
              {outcome}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filters.persona ?? "all"}
        onValueChange={(value) => handleChange("persona", value)}
      >
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Persona" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Personas</SelectItem>
          {options.personas.map((persona) => (
            <SelectItem key={persona} value={persona}>
              {persona}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filters.pathway ?? "all"}
        onValueChange={(value) => handleChange("pathway", value)}
      >
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Pathway" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Pathways</SelectItem>
          {options.pathways.map((pathway) => (
            <SelectItem key={pathway} value={pathway}>
              {pathway}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
