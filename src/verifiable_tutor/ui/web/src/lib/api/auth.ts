import type { Me } from "@/lib/types";

import { apiFetch } from "./client";

export interface DomainsResponse {
  /** The configured registration domains, in configuration order. */
  domains: string[];
}

export interface LoginResponse {
  user: Pick<Me, "id" | "email" | "role">;
}

export interface RegisterResponse {
  email: string;
  role: "student";
  verification: "pending";
  email_delivery: "log" | "smtp";
}

export interface VerifyResponse {
  email: string;
  status: "active";
}

export interface ResetRequestResponse {
  email: string;
  email_delivery: "log" | "smtp";
}

export interface ResetResponse {
  email: string;
  sessions_invalidated: number;
}

/** Account routes. The backend owns the session cookie on login and logout. */
export const authApi = {
  /** Public list of the domains registration accepts, from the backend config. */
  domains(signal?: AbortSignal): Promise<DomainsResponse> {
    return apiFetch<DomainsResponse>("/api/auth/domains", { signal });
  },

  me(signal?: AbortSignal): Promise<Me> {
    return apiFetch<Me>("/api/auth/me", { signal });
  },

  login(email: string, password: string): Promise<LoginResponse> {
    return apiFetch<LoginResponse>("/api/auth/login", {
      method: "POST",
      body: { email, password },
    });
  },

  register(email: string, password: string): Promise<RegisterResponse> {
    return apiFetch<RegisterResponse>("/api/auth/register", {
      method: "POST",
      body: { email, password },
    });
  },

  verify(email: string, code: string): Promise<VerifyResponse> {
    return apiFetch<VerifyResponse>("/api/auth/verify", {
      method: "POST",
      body: { email, code },
    });
  },

  logout(): Promise<void> {
    return apiFetch<void>("/api/auth/logout", { method: "POST" });
  },

  requestReset(email: string): Promise<ResetRequestResponse> {
    return apiFetch<ResetRequestResponse>("/api/auth/reset/request", {
      method: "POST",
      body: { email },
    });
  },

  reset(token: string, newPassword: string): Promise<ResetResponse> {
    return apiFetch<ResetResponse>("/api/auth/reset", {
      method: "POST",
      body: { token, new_password: newPassword },
    });
  },
};
