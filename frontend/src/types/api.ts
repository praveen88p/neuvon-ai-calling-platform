/**
 * TypeScript interfaces matching backend Pydantic schemas.
 * Single source of truth for all API response shapes.
 *
 * These mirror the schemas defined in backend/app/schemas/*.py
 */

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

export interface UserContext {
  user_id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: "platform_admin" | "owner" | "admin" | "member";
}

export interface LoginResponse {
  tokens: AuthTokens;
  user: UserContext;
}

export interface RegisterResponse {
  tokens: AuthTokens;
  user: UserContext;
}

export interface MeResponse {
  user: UserContext;
}

// ─── Organization ────────────────────────────────────────────────────────────

export interface OrganizationResponse {
  id: string;
  name: string;
  slug: string;
  org_type: string;
  white_label: Record<string, unknown> | null;
  billing_plan: string;
  usage_quota: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
}

export interface MemberResponse {
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface MemberListResponse {
  members: MemberResponse[];
  total: number;
}

// ─── Analytics ───────────────────────────────────────────────────────────────

export interface AnalyticsOverview {
  total_calls: number;
  total_minutes: number;
  average_duration_seconds: number;
  success_rate: number;
  total_campaigns: number;
  total_agents: number;
  total_cost_usd: number;
}

export interface TimeSeriesPoint {
  date: string;
  calls: number;
  minutes: number;
  success_count: number;
  failed_count: number;
}

export interface CallsOverTimeResponse {
  data: TimeSeriesPoint[];
  start_date: string;
  end_date: string;
}

export interface DispositionItem {
  disposition: string;
  count: number;
  percentage: number;
}

export interface DispositionBreakdownResponse {
  data: DispositionItem[];
  total_calls: number;
}

export interface AgentPerformanceItem {
  agent_id: number;
  agent_name: string;
  total_calls: number;
  total_minutes: number;
  average_duration_seconds: number;
  success_rate: number;
  total_cost_usd: number;
}

export interface AgentPerformanceResponse {
  data: AgentPerformanceItem[];
}

export interface CampaignPerformanceItem {
  campaign_id: string;
  campaign_name: string;
  total_calls: number;
  total_minutes: number;
  completed_calls: number;
  success_rate: number;
  status: string;
}

export interface CampaignPerformanceResponse {
  data: CampaignPerformanceItem[];
}

// ─── Agents ──────────────────────────────────────────────────────────────────

export interface AgentResponse {
  workflow_id: number;
  workflow_uuid: string | null;
  name: string;
  status: string | null;
  organization_id: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface AgentDetailResponse {
  workflow_id: number;
  workflow_uuid: string | null;
  name: string;
  status: string | null;
  organization_id: string;
  workflow_definition: Record<string, unknown> | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AgentListResponse {
  agents: AgentResponse[];
  total: number;
}

export interface AgentCountResponse {
  active: number;
  archived: number;
  total: number;
}

// ─── Campaigns ───────────────────────────────────────────────────────────────

export interface CampaignResponse {
  id: string;
  organization_id: string;
  dograh_campaign_id: number;
  dograh_workflow_id: number;
  name: string;
  status: string;
  total_contacts: number;
  contacts_processed: number;
  concurrency: number;
  retry_config: Record<string, unknown> | null;
  schedule_config: Record<string, unknown> | null;
  contact_list_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
}

export interface CampaignListResponse {
  campaigns: CampaignResponse[];
  total: number;
}

export interface CampaignProgressResponse {
  campaign_id: number;
  status: string;
  total_contacts: number;
  contacts_processed: number;
  contacts_remaining: number;
  success_count: number;
  failed_count: number;
  in_progress_count: number;
}

export interface CampaignActionResponse {
  campaign_id: number;
  status: string;
  message: string;
}

export interface ContactListUploadResponse {
  contact_list_id: string;
  total_contacts: number;
  message: string;
}

// ─── Calls ───────────────────────────────────────────────────────────────────

export interface CallTriggerResponse {
  run_id: number;
  workflow_run_name: string | null;
  status: string;
  phone_number: string;
  workflow_id: number;
  organization_id: string;
}

export interface CallRunResponse {
  run_id: number;
  workflow_id: number;
  organization_id: string;
  name: string | null;
  status: string | null;
  is_completed: boolean;
  call_type: string | null;
  phone_number: string | null;
  caller_number: string | null;
  duration_seconds: number | null;
  initial_context: Record<string, unknown> | null;
  gathered_context: Record<string, unknown> | null;
  transcript_url: string | null;
  recording_url: string | null;
  transcript_public_url: string | null;
  recording_public_url: string | null;
  public_access_token: string | null;
  cost_info: Record<string, unknown> | null;
  annotations: Record<string, unknown> | null;
  created_at: string | null;
}

export interface CallHistoryItem {
  run_id: number;
  workflow_id: number | null;
  workflow_name: string | null;
  campaign_id: number | null;
  campaign_name: string | null;
  call_type: string | null;
  status: string | null;
  disposition_code: string | null;
  phone_number: string | null;
  caller_number: string | null;
  duration_seconds: number | null;
  cost: number | null;
  recording_url: string | null;
  transcript_url: string | null;
  public_access_token: string | null;
  created_at: string | null;
  completed_at: string | null;
}

export interface CallHistoryResponse {
  runs: CallHistoryItem[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface DownloadUrlResponse {
  url: string;
  run_id: number;
  type: "recording" | "transcript";
}

// ─── Appointments ────────────────────────────────────────────────────────────

export interface AppointmentResponse {
  id: string;
  organization_id: string;
  call_run_id: string;
  contact_name: string;
  contact_phone: string;
  appointment_date: string | null;
  notes: string;
  status: string;
  created_at: string;
  campaign_name: string | null;
}

export interface AppointmentListResponse {
  appointments: AppointmentResponse[];
  total: number;
}

// ─── Billing ─────────────────────────────────────────────────────────────────

export interface UsageSummary {
  organization_id: string;
  period_start: string;
  period_end: string;
  total_calls: number;
  total_minutes: number;
  total_cost_usd: number;
  plan_name: string;
  calls_limit: number;
  minutes_limit: number;
  calls_remaining: number;
  minutes_remaining: number;
}

export interface PlanDetails {
  plan_id: string;
  plan_name: string;
  price_monthly_inr: number;
  calls_limit: number;
  minutes_limit: number;
  features: string[];
}

export interface OrderResponse {
  order_id: string;
  amount: number;
  currency: string;
  receipt: string;
  status: string;
  razorpay_key_id: string;
}

export interface PaymentVerificationResponse {
  verified: boolean;
  payment_id: string;
  order_id: string;
  message: string;
}

export interface InvoiceItem {
  id: string;
  organization_id: string;
  period_start: string;
  period_end: string;
  total_minutes: number;
  total_calls: number;
  total_cost_usd: number;
  razorpay_invoice_id: string | null;
  status: string;
  created_at: string;
}

export interface InvoiceListResponse {
  invoices: InvoiceItem[];
  total: number;
}

// ─── Telephony ───────────────────────────────────────────────────────────────

export interface TelephonyConfigResponse {
  id: number;
  provider: string | null;
  name: string | null;
  is_default_outbound: boolean;
  phone_number_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface TelephonyConfigListResponse {
  configs: TelephonyConfigResponse[];
  total: number;
}

export interface TelephonyProviderField {
  name: string;
  label: string | null;
  type: string; // "text" | "password" | "textarea" | "string-array" | "number"
  required: boolean;
  sensitive: boolean;
  description: string | null;
}

export interface TelephonyProviderMetadata {
  provider: string;
  display_name: string | null;
  docs_url: string | null;
  fields: TelephonyProviderField[];
}

export interface TelephonyProvidersResponse {
  providers: TelephonyProviderMetadata[];
}

export interface ProviderSync {
  ok: boolean;
  message: string | null;
}

export interface PhoneNumberResponse {
  id: number;
  telephony_configuration_id: number | null;
  address: string | null;
  address_normalized: string | null;
  address_type: string | null;
  country_code: string | null;
  label: string | null;
  is_default_caller_id: boolean;
  is_active: boolean;
  inbound_workflow_id: number | null;
  inbound_workflow_name: string | null;
  extra_metadata: Record<string, unknown> | null;
  provider_sync: ProviderSync | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PhoneNumberListResponse {
  phone_numbers: PhoneNumberResponse[];
  total: number;
}

// ─── Settings ────────────────────────────────────────────────────────────────

export interface OrgSettingsResponse {
  id: string;
  name: string;
  display_name: string | null;
  logo_url: string | null;
  primary_color: string | null;
  webhook_url: string | null;
  timezone: string | null;
  created_at: string | null;
}

export interface ProfileResponse {
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  organization_id: string;
  phone: string | null;
  avatar_url: string | null;
  notification_preferences: Record<string, unknown> | null;
  created_at: string | null;
}

export interface ApiKeyResponse {
  id: string;
  organization_id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  expires_at: string | null;
  created_at: string | null;
  last_used_at: string | null;
}

export interface ApiKeyCreatedResponse {
  id: string;
  organization_id: string;
  name: string;
  key: string;
  key_prefix: string;
  expires_at: string | null;
  created_at: string | null;
}

export interface ApiKeyListResponse {
  keys: ApiKeyResponse[];
  total: number;
}

// ─── Admin ───────────────────────────────────────────────────────────────────

export interface AdminOrgItem {
  id: string;
  name: string;
  plan: string | null;
  member_count: number;
  total_calls: number;
  total_minutes: number;
  is_active: boolean;
  created_at: string | null;
}

export interface AdminOrgListResponse {
  organizations: AdminOrgItem[];
  total: number;
}

export interface AdminUsageResponse {
  total_organizations: number;
  total_users: number;
  total_calls: number;
  total_minutes: number;
  total_campaigns: number;
  active_campaigns: number;
  total_agents: number;
}

export interface AuditLogItem {
  id: string;
  organization_id: string | null;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string | null;
}

export interface AuditLogListResponse {
  logs: AuditLogItem[];
  total: number;
}

export interface SystemLogItem {
  id: string;
  level: string;
  message: string;
  source: string | null;
  details: Record<string, unknown> | null;
  created_at: string | null;
}

export interface SystemLogListResponse {
  logs: SystemLogItem[];
  total: number;
}

// ─── Billing (Settings Tab) ──────────────────────────────────────────────────

export interface BillingUsageResponse {
  total_calls: number;
  total_minutes: number;
  total_cost: number;
  remaining_minutes: number | null;
  period_start: string | null;
  period_end: string | null;
}

export interface PlanInfoResponse {
  plan_name: string;
  plan_id: string | null;
  price_per_month: number | null;
  monthly_minutes_limit: number | null;
  monthly_calls_limit: number | null;
  features: string[];
}

// ─── Team (Settings Tab) ────────────────────────────────────────────────────

export interface TeamMemberItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string | null;
}

export interface TeamMemberListResponse {
  members: TeamMemberItem[];
  total: number;
}

// ─── WebSocket ───────────────────────────────────────────────────────────────

export interface LiveCallUpdate {
  type: "call_status" | "heartbeat" | "pong";
  data?: {
    run_id: number;
    status: string;
    phone_number?: string;
    duration_seconds?: number;
    workflow_name?: string;
    started_at?: string;
  };
  active_calls?: number;
  timestamp?: string;
}

// ─── Availability ────────────────────────────────────────────────────────────

export interface WeeklySlot {
  day_of_week: number; // 0=Sunday, 6=Saturday
  start_time: string;  // "09:00"
  end_time: string;    // "17:00"
  is_active: boolean;
}

export interface WeeklySlotResponse extends WeeklySlot {
  id: string;
}

export interface WeeklyScheduleResponse {
  user_id: string;
  slots: WeeklySlotResponse[];
}

export interface AvailabilityOverrideRequest {
  override_date: string;
  is_available: boolean;
  start_time?: string;
  end_time?: string;
  reason?: string;
}

export interface AvailabilityOverrideResponse {
  id: string;
  override_date: string;
  is_available: boolean;
  start_time?: string;
  end_time?: string;
  reason: string;
  created_at: string;
}

export interface OverrideListResponse {
  overrides: AvailabilityOverrideResponse[];
  total: number;
}

