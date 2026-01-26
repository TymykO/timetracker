/**
 * API client dla TimeTracker.
 * 
 * Fetch wrapper z:
 * - credentials: "include" (session cookies)
 * - automatyczne przekierowanie na 401
 * - centralna konfiguracja base URL
 */

import type {
  EmployeeProfile,
  LoginResponse,
  MessageResponse,
  TokenValidationResponse,
  MonthSummary,
  DayData,
  SaveDayItem,
  SaveDayResult,
  TaskListResponse,
} from "../types/dto";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

export class ApiError extends Error {
  status: number;
  
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    credentials: "include", // MUST: wysyłaj cookies dla session auth
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  // 401 = nie zalogowany -> przekieruj na login
  if (response.status === 401) {
    window.location.href = "/login";
    throw new ApiError(401, "Unauthorized");
  }

  // 204 No Content (np. logout)
  if (response.status === 204) {
    return {} as T;
  }

  const data = await response.json();

  if (!response.ok) {
    throw new ApiError(response.status, data.error || "Request failed");
  }

  return data;
}

export const api = {
  // === Auth ===
  
  login: (email: string, password: string) =>
    apiFetch<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  logout: () =>
    apiFetch("/auth/logout", { method: "POST" }),

  me: () =>
    apiFetch<EmployeeProfile>("/me"),

  // === Set password (invite flow) ===

  validateInviteToken: (token: string) =>
    apiFetch<TokenValidationResponse>(`/auth/invite/validate?token=${encodeURIComponent(token)}`),

  setPassword: (token: string, password: string) =>
    apiFetch<MessageResponse>("/auth/set-password", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    }),

  // === Reset password ===

  requestPasswordReset: (email: string) =>
    apiFetch<MessageResponse>("/auth/password-reset/request", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  validateResetToken: (token: string) =>
    apiFetch<TokenValidationResponse>(`/auth/password-reset/validate?token=${encodeURIComponent(token)}`),

  confirmPasswordReset: (token: string, password: string) =>
    apiFetch<MessageResponse>("/auth/password-reset/confirm", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    }),

  // === Timesheet ===

  getMonthSummary: (month: string) =>
    apiFetch<MonthSummary>(`/timesheet/month?month=${encodeURIComponent(month)}`),

  getDay: (date: string) =>
    apiFetch<DayData>(`/timesheet/day?date=${encodeURIComponent(date)}`),

  saveDay: (date: string, items: SaveDayItem[]) =>
    apiFetch<SaveDayResult>("/timesheet/day/save", {
      method: "POST",
      body: JSON.stringify({ date, items }),
    }),

  // === Tasks ===

  getActiveTasks: () =>
    apiFetch<TaskListResponse>("/tasks/active"),
};
