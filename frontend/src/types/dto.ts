/**
 * TypeScript interfaces dla DTO TimeTracker API.
 * Odpowiadają backendownym dataclass z backend/timetracker_app/api/schemas.py
 */

// === Auth DTOs ===

export interface EmployeeProfile {
  id: number;
  email: string;
  is_active: boolean;
  daily_norm_minutes: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  employee: EmployeeProfile;
}

export interface MessageResponse {
  message: string;
}

export interface TokenValidationResponse {
  valid: boolean;
  employee_email?: string;
}

// === Timesheet DTOs ===

export interface TimeEntry {
  task_id: number;
  task_display_name: string;
  duration_minutes_raw: number;
  billable_half_hours: number;
}

export interface DayData {
  date: string;
  day_type: "Working" | "Free";
  is_future: boolean;
  is_editable: boolean;
  total_raw_minutes: number;
  total_overtime_minutes: number;
  entries: TimeEntry[];
}

export interface MonthDay {
  date: string;
  day_type: "Working" | "Free";
  working_time_raw_minutes: number;
  overtime_minutes: number;
  has_entries: boolean;
  is_future: boolean;
  is_editable: boolean;
}

export interface MonthSummary {
  month: string;
  days: MonthDay[];
}

export interface SaveDayItem {
  task_id: number;
  duration_minutes_raw: number;
}

export interface SaveDayRequest {
  date: string;
  items: SaveDayItem[];
}

export interface SaveDayResult {
  success: boolean;
  day?: DayData;
  errors?: string[];
}

// === Task DTOs ===

export interface Task {
  id: number;
  display_name: string;
  search_text: string;
  project_phase: string | null;
  department: string | null;
  discipline: string | null;
  account: string | null;
  project: string | null;
  phase: string | null;
  task_type: string | null;
}

export interface FilterValues {
  project_phases: string[];
  departments: string[];
  disciplines: string[];
}

export interface TaskListResponse {
  tasks: Task[];
  filter_values: FilterValues;
}
