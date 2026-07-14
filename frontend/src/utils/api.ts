/**
 * API utility for making authenticated requests to the FastAPI backend.
 *
 * All frontend API calls go through these functions which:
 * - Inject JWT Bearer tokens from localStorage
 * - Handle 401 responses (redirect to login)
 * - Parse error responses for `detail` messages
 */

export const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// ─── Auth Headers ────────────────────────────────────────────────────────────

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem("auth_token");
  return token
    ? {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      }
    : {
        "Content-Type": "application/json",
      };
}

// ─── Error Handling ──────────────────────────────────────────────────────────

class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function handle401() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("auth_refresh_token");
  localStorage.removeItem("auth_user");
  window.location.href = "/login";
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 401) {
    handle401();
    throw new ApiError(401, "Unauthorized");
  }

  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;
    try {
      const body = await response.json();
      if (body.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // If the response body isn't JSON, use status text
      const text = await response.text().catch(() => "");
      if (text) detail = text;
    }
    throw new ApiError(response.status, detail);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// ─── HTTP Methods ────────────────────────────────────────────────────────────

/**
 * Make an authenticated GET request.
 * @param path Full API path, e.g. "/api/v1/analytics/overview"
 */
export async function apiGet<T = unknown>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
  return handleResponse<T>(response);
}

/**
 * Make an authenticated POST request.
 */
export async function apiPost<T = unknown>(
  path: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(response);
}

/**
 * Make an authenticated PATCH request.
 */
export async function apiPatch<T = unknown>(
  path: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers: getAuthHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(response);
}

/**
 * Make an authenticated PUT request.
 */
export async function apiPut<T = unknown>(
  path: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(response);
}

/**
 * Make an authenticated DELETE request.
 */
export async function apiDelete<T = unknown>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  return handleResponse<T>(response);
}

/**
 * Make an authenticated file upload request (multipart/form-data).
 * Does NOT set Content-Type header — browser sets it with boundary.
 */
export async function apiUpload<T = unknown>(
  path: string,
  formData: FormData,
): Promise<T> {
  const token = localStorage.getItem("auth_token");
  const headers: HeadersInit = token
    ? { Authorization: `Bearer ${token}` }
    : {};

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: formData,
  });
  return handleResponse<T>(response);
}
