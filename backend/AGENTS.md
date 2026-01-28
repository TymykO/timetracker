# TimeTracker — AGENTS (BACKEND)

> Scope: `backend/` (Django + Postgres + Worker via management command).  
> This file complements `../AGENTS.md` (root). Root rules still apply.

---

## 0) Backend goals (MVP)

Backend provides:
- **Auth (admin-only provisioning)**: invite → set-password → login/logout → password reset
- **Timesheet domain**:
  - month summary data for Month view
  - day data for Day view
  - `save_day()` API to upsert/delete entries for a day
- **Tasks API**: list active tasks with filter fields (flattened strings) and search helpers
- **Outbox + Worker**: enqueue jobs for async projections/sync (mechanics only in MVP)

Backend is the **source of truth** for all domain rules (dates, duplicates, totals, overtime, billable rounding).

---

## 1) Tech baseline

- Django (monolith)
- PostgreSQL (single DB)
- Session auth via cookies (HttpOnly)
- Python stdlib + Django only unless explicitly required
- Tests: pytest or Django test runner (choose one and stay consistent; prefer pytest later if you already plan it)

---

## 2) App layout and boundaries

Primary Django app: `timetracker_app/`

### Modules
- `timetracker_app/models.py`  
  Only data + constraints + indexes. No heavy business logic.
- `timetracker_app/services/`  
  **All domain logic lives here** (Information Expert).
- `timetracker_app/api/`  
  Thin controllers: parse/validate DTO → call services → return response.
- `timetracker_app/auth/`  
  Token generation/validation + invite/reset flows.
- `timetracker_app/outbox/`  
  Enqueue jobs and handlers (idempotent).
- `timetracker_app/management/commands/`  
  Worker runner and sync task puller.
- `timetracker_app/tests/`  
  Unit tests + service tests.

**Do not** implement business rules inside API views or models.

---

## 3) Data model expectations (MVP)

### Employee
- `email` unique (case-insensitive comparison recommended)
- `is_active`
- `daily_norm_minutes` (default e.g. 480)

### TaskCache (portal-local copy)
- Must store the flattened filter fields as strings:
  - `account`, `project`, `phase`, `project_phase`, `department`, `discipline`, `task_type`
- `display_name` and `search_text` required
- `fields_json` reserved (optional, nullable) – do not rely on it for MVP

### TimeEntry
- `employee` FK
- `task` FK (to TaskCache)
- `work_date` date
- `duration_minutes_raw` int > 0
- `billable_half_hours` int >= 1

### CalendarOverride
- `day` (date PK/unique)
- `day_type`: Working|Free
- optional note

### AuthToken
- hashed token (never store raw)
- `purpose`: INVITE|RESET
- `expires_at`, `used_at`

### OutboxJob
- `job_type`
- `dedup_key` (unique per logical job)
- `payload_json`
- `status`, `run_after`, `attempts`

---

## 4) Constraints & indexes (must-have)

### TimeEntry uniqueness
- UNIQUE: `(employee_id, work_date, task_id)`  
  Prevent duplicates per user/day/task.

### Checks
- `duration_minutes_raw > 0`
- `billable_half_hours >= 1`

### Indexes
- TimeEntry: `(employee_id, work_date)` for day/month queries
- TaskCache: `is_active` index
- Employee: `email` index/unique

---

## 5) Domain rules to enforce (backend)

These are enforced in **service layer** and also supported by DB constraints:

- No future dates
- Editable window: current month and previous month only
- Day raw sum <= 1440 minutes
- Billable rounding: `billable_half_hours = ceil(raw_minutes / 30)`
- Overtime based on day type and employee norm
- Day type default: weekend=Free; overrides from CalendarOverride

---

## 6) Service layer: required methods (MVP)

### TimesheetService
- `get_month_summary(employee, month: YYYY-MM) -> MonthDTO`
  - list of days: day_type, raw_sum, overtime, has_entries, is_future, is_editable
- `get_day(employee, date) -> DayDTO`
  - selected tasks + durations, totals, computed flags
- `save_day(employee, date, items[]) -> SaveResultDTO`
  - items are: `{task_id, duration_minutes_raw}`
  - Performs:
    - validation (date window, sums, duplicates in payload)
    - transaction:
      - upsert entries for provided tasks
      - delete entries for tasks removed from payload
    - returns recomputed day totals and month affected summary hints

### TaskService
- `list_active_tasks() -> TaskListDTO`
  - returns tasks with filter fields + display_name/search_text
  - optionally returns distinct filter values (for client-side filters)

### CalendarService
- `get_day_type(date) -> Working|Free`
  - apply override else weekend rule

### AuthService (or functions in auth module)
- invite validation + set password
- reset password request/confirm

---

## 7) API principles

- Use JSON everywhere.
- Keep endpoints stable and explicit.
- Controller responsibilities:
  - auth check
  - DTO parsing
  - call service
  - return DTO
- Return 401 for unauthenticated, 403 for inactive employee, 422/400 for validation issues.

Recommended endpoints (names can vary but keep semantics):
- `/api/me`
- `/api/auth/login`, `/api/auth/logout`
- `/api/auth/invite/validate`, `/api/auth/set-password`
- `/api/auth/password-reset/request`, `/api/auth/password-reset/validate`, `/api/auth/password-reset/confirm`
- `/api/timesheet/month`, `/api/timesheet/day`, `/api/timesheet/day/save`
- `/api/tasks/active`

---

## 8) Auth flows (Option B)

- Employees are created in admin only.
- Invite flow:
  - create INVITE AuthToken (expires e.g. 24h)
  - email link to set password
  - token is one-time (set `used_at`)
- Password reset:
  - create RESET AuthToken (expires e.g. 1h)
  - same one-time semantics
- Use Django’s password hashing (User model), do not invent custom hashing for passwords.
- Session cookies: HttpOnly, Secure in prod.

---

## 9) Security principles (implemented)

### Session & Cookie Security
- **HttpOnly cookies**: Session cookies are HttpOnly (cannot be accessed by JavaScript) to prevent XSS attacks
- **SameSite=Lax**: Both session and CSRF cookies use `SameSite=Lax` to prevent CSRF attacks
  - Cookies are sent only for same-site requests and top-level navigations
  - This protects against cross-site request forgery without breaking normal navigation
- **Secure flag in production**: Cookies are sent only over HTTPS in production (`SESSION_COOKIE_SECURE = not DEBUG`)
- **Session timeout**: Sessions expire after 14 days (`SESSION_COOKIE_AGE = 86400 * 14`)

### CSRF Protection
- **Django CSRF middleware**: Enabled globally for state-changing requests (POST/PUT/DELETE/PATCH)
- **CSRF token readable by frontend**: `CSRF_COOKIE_HTTPONLY = False` allows SPA to read the token
  - Frontend reads `csrftoken` cookie and sends it as `X-CSRFToken` header
  - This is safe because the cookie itself is still protected by SameSite policy
- **Trusted origins**: `CSRF_TRUSTED_ORIGINS` whitelist prevents CSRF from unexpected origins

### CORS Configuration
- **Credentials allowed**: `CORS_ALLOW_CREDENTIALS = True` permits cookie-based auth with SPA
- **Explicit origin whitelist**: `CORS_ALLOWED_ORIGINS` lists allowed frontend origins
  - Dev: `http://localhost:5173` (Vite default)
  - Production: configured via environment variable
- **No wildcard origins**: Never use `CORS_ALLOWED_ORIGINS = ['*']` with credentials

### Password Security
- **Django password hashing**: Uses PBKDF2 SHA256 by default (secure, industry-standard)
- **No raw tokens stored**: Invite/reset tokens are hashed before storage
- **One-time tokens**: Tokens are marked as `used_at` after first use
- **Token expiration**: Invite tokens expire after 24h, reset tokens after 1h

### Authorization
- **Admin-only provisioning**: Only admins can create employee accounts (no public registration)
- **Active status check**: Inactive employees cannot login or use the API
- **Employee scope**: All timesheet operations are automatically scoped to logged-in employee

### Input Validation
- **DB constraints as safety net**: Unique constraints, check constraints at DB level
- **Service layer validation**: Domain rules enforced before DB operations
- **API parameter validation**: DTOs validate input before passing to services

### Common Pitfalls to Avoid
- ❌ **Don't disable CSRF for convenience**: Use `@csrf_exempt` only for specific public endpoints if needed
- ❌ **Don't use SameSite=None in production**: Only needed for cross-site scenarios (not our case)
- ❌ **Don't store raw tokens**: Always hash sensitive tokens before DB storage
- ❌ **Don't trust client-side validation alone**: Always validate on backend

### IDE Browser Tab Limitation
**Note**: IDE embedded browsers (like Cursor Browser Tab) may not work with `SameSite=Lax` cookies due to different security context. This is expected and affects only development workflow. Always test in external browsers (Chrome/Firefox/Edge) where cookies work correctly.

---

## 10) Outbox + Worker rules

- Enqueue outbox jobs from service methods (not from API views).
- Worker:
  - polls PENDING jobs
  - locks a job (select-for-update or status transition)
  - processes idempotently
  - retries with backoff using `attempts` and `run_after`
- In MVP, handlers can be stubs, but job lifecycle must work.

---

## 11) Testing rules

Minimum test coverage:
- `TimesheetService.save_day()`:
  - rejects future date
  - rejects outside editable window
  - rejects day sum > 1440
  - prevents duplicates (payload + DB)
  - upsert + delete behavior is correct
  - billable_half_hours calculation correct
- Auth:
  - invite token valid/expired/used
  - reset flow valid/expired/used
  - inactive employee cannot login/use app
- Task list:
  - only active tasks returned
  - filter fields present

Tests should be deterministic and not depend on external services.

---

## 11) Do / Don’t list

### DO
- Keep logic in services
- Use transactions for `save_day`
- Use database constraints as safety net
- Keep responses explicit (DTOs)

### DON’T
- Don’t put domain logic in models or views
- Don’t store raw auth tokens
- Don’t build “sync” complexity into core timesheet logic (use outbox)
- Don’t add new dependencies casually
