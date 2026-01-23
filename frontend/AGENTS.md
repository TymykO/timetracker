# TimeTracker — AGENTS (FRONTEND)

> Scope: `frontend/` (Vite + React + TypeScript SPA).  
> This file complements `../AGENTS.md` (root). Root rules still apply.  
> Nearest `AGENTS.md` wins for subtrees (e.g. `src/pages/Day/AGENTS.md`).

---

## 0) Frontend goals (MVP)

Deliver a minimal, robust SPA with these screens:

### Auth
- `/login` (email + password)
- `/set-password?token=...` (invite flow)
- `/forgot-password`
- `/reset-password?token=...`

### Core
- `/month/:yyyy-mm` (Month view)
- `/day/:yyyy-mm-dd` (Day view)

The SPA must:
- use cookie-based sessions (HttpOnly) → always call API with `credentials: "include"`
- redirect to `/login` on 401
- keep UI logic simple (KISS)
- avoid duplicating business logic; backend is source of truth for totals/overtime/editability

---

## 1) Non-negotiable UX rules (must match backend rules)

- No access to future months and future days
- Day editing allowed only for current month and previous month
- Day total durations must not exceed 24h (UI can warn, backend enforces)
- Selected tasks list: no duplicates per user/day
- Filtered task list excludes tasks already selected (for that day)
- After adding a task, filter state must remain unchanged

Backend remains final authority; frontend is for UX guidance.

---

## 2) Directory conventions (keep structure stable)

Prefer this structure (create if missing; do not fight Vite defaults, adapt them):

- `src/app/` — app wiring:
  - `router.tsx` (routes)
  - `api_client.ts` (fetch wrapper)
  - `auth_guard.tsx` (session gate)
  - `query.ts` (query cache config; if used)
- `src/pages/` — page-level views:
  - `Login/`, `SetPassword/`, `ForgotPassword/`, `ResetPassword/`, `Month/`, `Day/`
- `src/components/` — reusable components:
  - MonthTable, FiltersBar, TaskPicker, SelectedTasksTable, etc.
- `src/types/` — DTO / types:
  - `dto.ts`

`App.tsx` can stay as Vite entry shell but should delegate to router/layout from `src/app/`.

Only **Day view** has additional local rules in `src/pages/Day/AGENTS.md`.

---

## 3) Data loading & caching strategy

### Recommended approach
Use **TanStack Query** for:
- `/api/me` (session)
- month data
- day data
- active tasks list

If you haven’t installed it yet, it’s OK—install when implementing (keep deps minimal).

### Cache rules (important)
- After `save_day` succeeds:
  - refetch/invalidate **day** and **month** queries
- Tasks list can be cached longer (it changes infrequently), but refetch on:
  - entering Day view
  - after login
  - (optional) periodic refetch later (not MVP-critical)

---

## 4) API calling rules (must follow)

All requests to backend:
- use `credentials: "include"`
- set `Content-Type: application/json` for POST
- handle non-2xx with structured error mapping

Global behavior:
- on 401: clear local state and redirect to `/login`
- on 403 (inactive user): show “No access / contact admin”

**Do not** hardcode API base URL in many places; use a single config in `api_client.ts`.

---

## 5) UI responsibilities vs backend responsibilities

### Frontend should do
- Filtering and searching tasks client-side (MVP):
  - filter by `project_phase`, `department`, `discipline`
  - free-text search using `search_text`
- Prevent duplicates in selected tasks list
- Basic input validation UX (e.g. duration required, numeric)
- Navigation constraints (disable future days/months)
- Show error messages returned by backend

### Frontend should NOT do
- Compute overtime business rules (show values from API)
- Implement its own month/day “truth” separate from backend
- Store auth tokens in localStorage (session is cookie-based)
- Implement advanced background sync logic (outbox is backend/worker)

---

## 6) Component behavior guidelines (MVP)

### Month view
- Render list/table of days for the chosen month
- Show:
  - day_type (Working/Free)
  - working_time_raw (from API)
  - overtime (from API)
  - has_entries (from API)
- Disable future days; do not allow switching to a future month
- Clicking day navigates to `/day/:date`

### Day view
- Load:
  - day data (selected tasks + current durations)
  - active tasks list (with filter fields)
- Filters:
  - dropdowns for project_phase/department/discipline (values from tasks or API)
  - text search input (matches `search_text`)
- Filtered task list excludes tasks already selected
- Add (“+”) moves task into selected list; filters remain as-is
- Selected list:
  - each row has duration input
  - no zero durations allowed (UI prevents; backend enforces)
  - allow remove row
- Save:
  - sends full list for the day (items[])
  - on success: invalidate/refetch day + month

---

## 7) Error handling & UX polish (lightweight)

- Always show a clear message for validation errors (e.g. “Total exceeds 24h”)
- Disable Save while request is in progress
- After save: show subtle “Saved” confirmation (no heavy notifications needed)
- Keep forms keyboard-friendly

---

## 8) Don’ts (to avoid AI drift)

- Do not add UI frameworks, component libraries, or state management libraries unless necessary
- Do not create multiple competing routers or API clients
- Do not scatter business rules across components; keep them centralized and minimal
- Do not refactor structure randomly; follow the directory conventions above

---

## 9) Definition of Done for frontend tasks

When a frontend feature is “done”:
- it compiles (`npm run build` passes)
- it runs locally (`npm run dev`)
- it respects auth behavior (401 redirects to /login)
- it matches non-negotiable UX rules in this file and in root AGENTS
