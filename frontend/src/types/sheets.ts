// ─── Sheet Integration Types ──────────────────────────────────────────────────

export interface SheetColumn {
  letter: string;
  header: string;
  sample: string;
}

export interface SheetColumnsResponse {
  spreadsheet_id: string;
  sheet_names: string[];
  selected_sheet: string;
  columns: SheetColumn[];
  row_count: number;
}

export interface SheetConnection {
  id: string;
  organization_id: string;
  provider: string;
  sheet_url: string;
  spreadsheet_id: string;
  sheet_name: string;
  column_mapping: Record<string, string>;
  agent_workflow_id: number;
  is_active: boolean;
  last_row_processed: number;
  last_polled_at: string | null;
  last_error: string | null;
  polling_interval_secs: number;
  total_leads_found: number;
  total_leads_called: number;
  total_leads_qualified: number;
  // Phase 4 fields
  needs_reauth: boolean;
  max_concurrent_calls: number;
  duplicate_window_hours: number;
  consecutive_error_count: number;
  created_at: string;
  updated_at: string;
}

export interface SheetLead {
  id: string;
  connection_id: string;
  row_number: number;
  phone_number: string;
  lead_data: Record<string, string>;
  call_status: "pending" | "calling" | "completed" | "failed" | "busy" | "no_answer" | "callback_scheduled";
  call_summary: string | null;
  lead_tag: string | null;
  callback_at: string | null;
  writeback_done: boolean;
  dograh_run_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface SheetLeadsListResponse {
  leads: SheetLead[];
  total: number;
  page: number;
  limit: number;
}

export interface SheetConnectionStats {
  total_leads_found: number;
  total_leads_called: number;
  total_leads_qualified: number;
  pending: number;
  calling: number;
  completed: number;
  failed: number;
  callback_scheduled: number;
}

// Required field names that must always be mapped
export const REQUIRED_FIELDS = ["phone"] as const;

// Optional common field names shown in the mapping UI
export const OPTIONAL_FIELDS = [
  "name",
  "email",
  "notes",
  "city",
  "property_interest",
  "budget",
  "source",
] as const;

export type RequiredField = typeof REQUIRED_FIELDS[number];
export type OptionalField = typeof OPTIONAL_FIELDS[number];
export type MappableField = RequiredField | OptionalField;

// Audit log event
export interface SheetAuditEvent {
  id: string;
  organization_id: string;
  connection_id: string | null;
  lead_id: string | null;
  event_type: string;
  details: Record<string, unknown>;
  severity: "debug" | "info" | "warning" | "error";
  created_at: string;
}
