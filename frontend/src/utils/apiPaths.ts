/**
 * API path constants — single source of truth for all backend endpoints.
 * Frontend never talks to Dograh directly; all calls go through the FastAPI backend.
 */

export const API_PATHS = {
  // ── Auth ──
  AUTH_LOGIN: "/api/v1/auth/login",
  AUTH_REGISTER: "/api/v1/auth/register",
  AUTH_REFRESH: "/api/v1/auth/refresh",
  AUTH_LOGOUT: "/api/v1/auth/logout",
  AUTH_ME: "/api/v1/auth/me",

  // ── Organization ──
  ORG_ME: "/api/v1/organizations/me",
  ORG_MEMBERS: "/api/v1/organizations/me/members",

  // ── Agents ──
  AGENTS: "/api/v1/agents",
  AGENTS_COUNT: "/api/v1/agents/count",
  AGENTS_FROM_TEMPLATE: "/api/v1/agents/from-template",
  AGENTS_FROM_DEFINITION: "/api/v1/agents/from-definition",

  // ── Calls ──
  CALLS_TRIGGER: "/api/v1/calls/trigger",
  CALLS_HISTORY: "/api/v1/calls/history",

  // ── Campaigns ──
  CAMPAIGNS: "/api/v1/campaigns",
  CAMPAIGNS_UPLOAD: "/api/v1/campaigns/upload-contacts",

  // ── Analytics ──
  ANALYTICS_OVERVIEW: "/api/v1/analytics/overview",
  ANALYTICS_CALLS_OVER_TIME: "/api/v1/analytics/calls-over-time",
  ANALYTICS_DISPOSITION: "/api/v1/analytics/disposition-breakdown",
  ANALYTICS_AGENT_PERF: "/api/v1/analytics/agent-performance",
  ANALYTICS_CAMPAIGN_PERF: "/api/v1/analytics/campaign-performance",

  // ── Billing ──
  BILLING_USAGE: "/api/v1/billing/usage",
  BILLING_PLAN: "/api/v1/billing/plan",
  BILLING_ORDERS: "/api/v1/billing/orders",
  BILLING_VERIFY: "/api/v1/billing/verify",
  BILLING_INVOICES: "/api/v1/billing/invoices",

  // ── Appointments ──
  APPOINTMENTS: "/api/v1/appointments",

  // ── Availability ──
  AVAILABILITY_SCHEDULE: "/api/v1/availability/schedule",
  AVAILABILITY_OVERRIDES: "/api/v1/availability/overrides",
  AVAILABILITY_CHECK: "/api/v1/availability/check",

  // ── Telephony ──
  TELEPHONY_PROVIDERS: "/api/v1/telephony/providers",
  TELEPHONY_CONFIGS: "/api/v1/telephony/configs",

  // ── Settings ──
  PROFILE: "/api/v1/settings/profile",
  ORG_SETTINGS: "/api/v1/settings/organization",
  API_KEYS: "/api/v1/settings/api-keys",
  TEAM: "/api/v1/settings/team",

  // ── Admin ──
  ADMIN_ORGS: "/api/v1/admin/organizations",
  ADMIN_USAGE: "/api/v1/admin/usage",
  ADMIN_AUDIT: "/api/v1/admin/audit",
  ADMIN_LOGS: "/api/v1/admin/logs",

  // ── WebSocket ──
  WS_LIVE_CALLS: "/api/v1/ws/live-calls",
} as const;

// ─── Dynamic Path Helpers ────────────────────────────────────────────────────

/** GET/PATCH/DELETE /api/v1/agents/{workflow_id} */
export const agentPath = (workflowId: number | string) =>
  `/api/v1/agents/${workflowId}`;

/** POST /api/v1/agents/{workflow_id}/status */
export const agentStatusPath = (workflowId: number | string) =>
  `/api/v1/agents/${workflowId}/status`;

/** POST /api/v1/agents/{workflow_id}/validate */
export const agentValidatePath = (workflowId: number | string) =>
  `/api/v1/agents/${workflowId}/validate`;

/** POST /api/v1/agents/{workflow_id}/test-run */
export const agentTestRunPath = (workflowId: number | string) =>
  `/api/v1/agents/${workflowId}/test-run`;

/** GET /api/v1/agents/{workflow_id}/runs */
export const agentRunsPath = (workflowId: number | string) =>
  `/api/v1/agents/${workflowId}/runs`;

/** GET/PATCH/DELETE /api/v1/campaigns/{id} */
export const campaignPath = (id: string) =>
  `/api/v1/campaigns/${id}`;

/** POST /api/v1/campaigns/{id}/start */
export const campaignStartPath = (id: string) =>
  `/api/v1/campaigns/${id}/start`;

/** POST /api/v1/campaigns/{id}/pause */
export const campaignPausePath = (id: string) =>
  `/api/v1/campaigns/${id}/pause`;

/** POST /api/v1/campaigns/{id}/resume */
export const campaignResumePath = (id: string) =>
  `/api/v1/campaigns/${id}/resume`;

/** GET /api/v1/campaigns/{id}/progress */
export const campaignProgressPath = (id: string) =>
  `/api/v1/campaigns/${id}/progress`;

/** GET /api/v1/campaigns/{id}/runs */
export const campaignRunsPath = (id: string) =>
  `/api/v1/campaigns/${id}/runs`;

/** GET /api/v1/calls/{run_id} */
export const callRunPath = (runId: number | string) =>
  `/api/v1/calls/${runId}`;

/** GET /api/v1/calls/{run_id}/recording */
export const callRecordingPath = (runId: number | string) =>
  `/api/v1/calls/${runId}/recording`;

/** GET /api/v1/calls/{run_id}/transcript */
export const callTranscriptPath = (runId: number | string) =>
  `/api/v1/calls/${runId}/transcript`;

/** PATCH /api/v1/appointments/{id} */
export const appointmentPath = (id: string) =>
  `/api/v1/appointments/${id}`;

/** GET /api/v1/telephony/configs/{id}/phone-numbers */
export const telephonyPhoneNumbersPath = (configId: number | string) =>
  `/api/v1/telephony/configs/${configId}/phone-numbers`;

/** POST /api/v1/telephony/configs/{id}/phone-numbers/{numId} */
export const telephonyPhoneNumberPath = (configId: number | string, numId: number | string) =>
  `/api/v1/telephony/configs/${configId}/phone-numbers/${numId}`;

/** POST /api/v1/telephony/configs/{id}/set-default-outbound */
export const telephonySetDefaultOutboundPath = (configId: number | string) =>
  `/api/v1/telephony/configs/${configId}/set-default-outbound`;

/** POST /api/v1/telephony/configs/{id}/phone-numbers/{numId}/set-default-caller */
export const telephonySetDefaultCallerPath = (configId: number | string, numId: number | string) =>
  `/api/v1/telephony/configs/${configId}/phone-numbers/${numId}/set-default-caller`;

/** GET/PUT/DELETE /api/v1/telephony/configs/{id} */
export const telephonyConfigPath = (configId: number | string) =>
  `/api/v1/telephony/configs/${configId}`;

/** PATCH /api/v1/organizations/me/members/{user_id} */
export const memberPath = (userId: string) =>
  `/api/v1/organizations/me/members/${userId}`;

/** DELETE /api/v1/settings/team/{member_id} */
export const teamMemberPath = (memberId: string) =>
  `/api/v1/settings/team/${memberId}`;

/** DELETE /api/v1/settings/api-keys/{key_id} */
export const apiKeyPath = (keyId: string) =>
  `/api/v1/settings/api-keys/${keyId}`;
