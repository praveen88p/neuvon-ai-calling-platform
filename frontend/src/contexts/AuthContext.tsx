import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { API_PATHS } from "@/utils/apiPaths";
import type { LoginResponse, RegisterResponse, UserContext as UserContextType, MeResponse } from "@/types/api";

// ─── Types ───────────────────────────────────────────────────────────────────

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  organization_id: string;
  organization_name: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
}

interface RegisterData {
  email: string;
  password: string;
  full_name: string;
  organization_name: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const API_BASE_URL =
  import.meta.env.VITE_API_URL !== undefined
    ? import.meta.env.VITE_API_URL
    : import.meta.env.DEV
      ? "http://localhost:8000"
      : "";

/**
 * Check if a JWT token is expired by decoding the payload.
 * Returns true if the token is expired or malformed.
 */
function isTokenExpired(token: string): boolean {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return true;

    // Decode the payload (2nd part) — handle base64url encoding
    const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const decoded = JSON.parse(atob(payload));

    if (!decoded.exp) return true;

    // 30-second buffer so we don't use a token that's about to expire
    const nowInSeconds = Date.now() / 1000;
    return decoded.exp < nowInSeconds + 30;
  } catch {
    return true;
  }
}

/**
 * Map backend UserContext to frontend User shape.
 */
function mapUser(u: UserContextType, orgName?: string): User {
  return {
    id: u.user_id,
    email: u.email,
    full_name: u.full_name,
    role: u.role,
    organization_id: u.organization_id,
    organization_name: orgName ?? u.full_name,
  };
}

function persistAuth(accessToken: string, refreshToken: string, user: User) {
  localStorage.setItem("auth_token", accessToken);
  localStorage.setItem("auth_refresh_token", refreshToken);
  localStorage.setItem("auth_user", JSON.stringify(user));
}

function clearAuth() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("auth_refresh_token");
  localStorage.removeItem("auth_user");
}

// ─── Context ─────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount: validate stored token, refresh if expired, fetch user context
  useEffect(() => {
    const init = async () => {
      const storedToken = localStorage.getItem("auth_token");
      const storedRefresh = localStorage.getItem("auth_refresh_token");
      const storedUser = localStorage.getItem("auth_user");

      if (!storedToken || !storedUser) {
        clearAuth();
        setIsLoading(false);
        return;
      }

      // If token is expired, try refreshing
      if (isTokenExpired(storedToken)) {
        if (storedRefresh) {
          try {
            const refreshed = await refreshToken(storedRefresh);
            setToken(refreshed.access_token);

            // Fetch fresh user context after refresh
            const meData = await fetchMe(refreshed.access_token);
            const freshUser = mapUser(meData.user);
            setUser(freshUser);
            persistAuth(refreshed.access_token, refreshed.refresh_token, freshUser);
            setIsLoading(false);
            return;
          } catch {
            // Refresh failed — force re-login
            console.warn("Token refresh failed, clearing session.");
            clearAuth();
            setIsLoading(false);
            return;
          }
        } else {
          console.warn("Token expired and no refresh token, clearing session.");
          clearAuth();
          setIsLoading(false);
          return;
        }
      }

      // Token is still valid — restore from storage, verify with /auth/me
      setToken(storedToken);
      try {
        const meData = await fetchMe(storedToken);
        const freshUser = mapUser(meData.user);
        setUser(freshUser);
        // Update localStorage with fresh data
        localStorage.setItem("auth_user", JSON.stringify(freshUser));
      } catch {
        // /auth/me failed — use stored user as fallback
        setUser(JSON.parse(storedUser));
      }
      setIsLoading(false);
    };

    init();
  }, []);

  const login = async (email: string, password: string) => {
    const response = await fetch(`${API_BASE_URL}${API_PATHS.AUTH_LOGIN}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Login failed");
    }

    const data: LoginResponse = await response.json();

    const userData = mapUser(data.user);
    setToken(data.tokens.access_token);
    setUser(userData);
    persistAuth(data.tokens.access_token, data.tokens.refresh_token, userData);

    // Identify user in Sentry for error tracking
    try {
      const Sentry = await import("@sentry/react");
      Sentry.setUser({ email: userData.email, id: userData.id, username: userData.name });
    } catch { /* Sentry not loaded */ }
  };

  const register = async (data: RegisterData) => {
    const response = await fetch(`${API_BASE_URL}${API_PATHS.AUTH_REGISTER}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Registration failed");
    }

    const result: RegisterResponse = await response.json();

    const userData = mapUser(result.user, data.organization_name);
    setToken(result.tokens.access_token);
    setUser(userData);
    persistAuth(result.tokens.access_token, result.tokens.refresh_token, userData);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    clearAuth();

    // Clear user from Sentry
    import("@sentry/react").then(Sentry => Sentry.setUser(null)).catch(() => {});
  };

  // ─── Proactive background token refresh ────────────────────────────────────
  // Decodes the JWT expiry and schedules a silent refresh 60s before it expires.
  // Runs whenever the token changes so the timer always tracks the latest token.
  useEffect(() => {
    if (!token) return;

    let timeoutId: ReturnType<typeof setTimeout>;

    const scheduleRefresh = (currentToken: string) => {
      try {
        const parts = currentToken.split(".");
        if (parts.length !== 3) return;
        const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
        const decoded = JSON.parse(atob(payload));
        if (!decoded.exp) return;

        const nowMs = Date.now();
        const expiresAtMs = decoded.exp * 1000;
        // Refresh 60 seconds before expiry
        const refreshInMs = expiresAtMs - nowMs - 60_000;

        if (refreshInMs <= 0) {
          // Already near/past expiry — refresh immediately
          doSilentRefresh();
          return;
        }

        timeoutId = setTimeout(doSilentRefresh, refreshInMs);
      } catch {
        // Malformed token — ignore
      }
    };

    const doSilentRefresh = async () => {
      const storedRefresh = localStorage.getItem("auth_refresh_token");
      if (!storedRefresh) return;
      try {
        const refreshed = await refreshToken(storedRefresh);
        setToken(refreshed.access_token);
        // Update stored tokens; keep existing user object
        const storedUser = localStorage.getItem("auth_user");
        if (storedUser) {
          const user = JSON.parse(storedUser);
          persistAuth(refreshed.access_token, refreshed.refresh_token, user);
        }
      } catch {
        // Silent refresh failed — force logout
        console.warn("Silent token refresh failed, logging out.");
        setToken(null);
        setUser(null);
        clearAuth();
      }
    };

    scheduleRefresh(token);

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [token]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!token,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

// ─── Internal helpers ────────────────────────────────────────────────────────

async function refreshToken(
  refreshTokenValue: string,
): Promise<{ access_token: string; refresh_token: string }> {
  const response = await fetch(`${API_BASE_URL}${API_PATHS.AUTH_REFRESH}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshTokenValue }),
  });

  if (!response.ok) {
    throw new Error("Token refresh failed");
  }

  return response.json();
}

async function fetchMe(accessToken: string): Promise<MeResponse> {
  const response = await fetch(`${API_BASE_URL}${API_PATHS.AUTH_ME}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    throw new Error("Failed to fetch user context");
  }

  return response.json();
}

// Helper to get auth headers for API requests (used by some components directly)
export function getAuthHeaders(): HeadersInit {
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
