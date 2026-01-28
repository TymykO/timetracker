
# TimeTracker — AGENTS (BACKEND / SERVICES)

> Scope: `backend/timetracker_app/services/`  
> This is the **domain logic layer**. It must enforce all core rules from root/backend AGENTS.
>
> Key principle: **Services are the source of domain truth** (models store data, API views adapt HTTP).
> Keep services cohesive, testable, and transaction-safe.

---

## 0) Responsibilities of this layer

This layer owns:
- validation of timesheet rules (dates, edit window, totals, duplicates)
- deterministic calculations (billable rounding, overtime, month/day aggregation)
- database transactions (`save_day`)
- enqueueing Outbox jobs (mechanics only; handlers elsewhere)

This layer must NOT:
- read HTTP request objects
- build HTTP responses directly
- perform UI formatting
- send emails (auth layer may, later)

---

## 1) Canonical domain definitions

### Time rounding (billing)
- raw minutes stored: `duration_minutes_raw` (int, >0)
- billable hours stored: `hours_decimal` (Decimal >= 0.5)
- compute:
  - `hours_decimal = ceil((duration_minutes_raw / 60) * 2) / 2`
  - rounds to nearest 0.5h (e.g., 1 min → 0.5h, 31 min → 1.0h, 61 min → 1.5h)

### Day totals
- `day_raw_sum_minutes = sum(duration_minutes_raw for that employee + date)`
- hard limit: `day_raw_sum_minutes <= 1440`

### Day type
- default:
  - Saturday/Sunday → `Free`
  - other weekdays → `Working`
- override:
  - `CalendarOverride(day).day_type` if exists

### Overtime
- If day_type == Working:
  - `overtime_minutes = max(0, day_raw_sum_minutes - employee.daily_norm_minutes)`
- If day_type == Free:
  - `overtime_minutes = day_raw_sum_minutes`

### Editability window
- Allowed only for:
  - current month
  - previous month
- Never allowed for:
  - future dates
  - months older than previous month

---

## 2) Required public service APIs (MVP)

### TimesheetService

#### `get_month_summary(employee, month: date) -> MonthDTO`
Returns a month view for a given employee and month.

**Input**
- `employee` (Employee instance)
- `month` as a date representing the first day of month OR a YYYY-MM string parsed at API level

**Output**
- list of days in month with fields:
  - `date`
  - `day_type` (Working/Free)
  - `working_time_raw_minutes`
  - `overtime_minutes`
  - `has_entries` (bool)
  - `is_future` (bool)
  - `is_editable` (bool)  (based on editability window and not future)

**Rules**
- Must be deterministic and computed from DB + calendar logic.
- Must not over-fetch (use aggregation queries).

---

#### `get_day(employee, date: date) -> DayDTO`
Returns the Day view state:
- selected entries for that day (task id + duration raw + billable)
- totals and flags

**Output**
- `date`
- `day_type`
- `is_future`
- `is_editable`
- `total_raw_minutes`
- `total_overtime_minutes`
- `entries[]`:
  - `task_id`
  - `duration_minutes_raw`
  - `hours_decimal`
  - `task_display_name` (optional convenience, may come from TaskCache)

---

#### `save_day(employee, date: date, items: list[SaveItem]) -> SaveResultDTO`
**This is the most important function in MVP.**

**SaveItem**
- `task_id` (TaskCache PK)
- `duration_minutes_raw` (int > 0)

**Behavior**
- Reject if:
  - date is in the future
  - date is outside editable window
  - any item has duration <= 0
  - duplicate `task_id` inside payload
  - sum(payload durations) > 1440
- Apply changes in a single DB transaction:
  1) Load existing entries for (employee, date) → map by task_id
  2) For each payload item:
     - if entry exists → update duration_minutes_raw + hours_decimal
     - else → create new entry
  3) Delete entries that exist in DB but are missing from payload (user removed them)
- Recompute totals and return:
  - `date`, totals, day_type, edit flags
  - optionally a “month affected” hint for cache invalidation

**Important**
- The payload is the full state of the day (authoritative).
- Deleting is expected behavior (this is how “removing a task row” works).

**Concurrency**
- Use transaction + unique constraint to protect against race duplicates.
- Prefer select-for-update on the existing day entries rowset if needed.

---

### CalendarService

#### `get_day_type(date: date) -> str`
- returns Working/Free using override + weekend rule

---

## 3) Query strategy & performance expectations

### Month summary must be efficient
- Aggregate time entries by date for the month:
  - query filtered by `(employee_id, work_date between month_start and month_end)`
  - group by `work_date`, sum raw minutes
  - `has_entries` derived from existence/aggregation row
- Avoid per-day DB queries (no N+1).
- Calendar overrides can be fetched in one query for the month.

### Day retrieval must be efficient
- One query for entries for (employee, date) with select_related(task)
- No extra queries per row.

---

## 4) Error handling contract (service-level)

Services should raise **domain exceptions** (not HTTP errors), e.g.:
- `NotEditableError`
- `FutureDateError`
- `DayTotalExceededError`
- `InvalidDurationError`
- `DuplicateTaskInPayloadError`

API layer maps them to appropriate HTTP status + message.

---

## 5) Outbox integration (MVP)

After successful `save_day` transaction commit:
- enqueue an `OutboxJob` with a stable `dedup_key`, e.g.:
  - `timesheet:project_day:{employee_id}:{date}`
- job payload includes:
  - employee_id
  - date
  - affected entry ids (optional)

**Do not** call external systems directly here.
Outbox handler is responsible later.

---

## 6) Tests that must exist (service-focused)

`test_timesheet.py` must cover:
- save_day rejects future date
- save_day rejects outside editable window
- save_day rejects duration <= 0
- save_day rejects duplicate task in payload
- save_day rejects sum > 1440
- save_day upsert behavior (create/update)
- save_day delete behavior (remove missing)
- hours_decimal rounding to 0.5h increments is correct
- overtime calculation for Working/Free is correct (with override and without)

Keep tests deterministic (freeze “today” using a helper or dependency injection).

---

## 7) Implementation notes (do this, not that)

### DO
- keep methods pure where possible (calculations)
- keep DB operations in clearly bounded blocks
- use a single transaction in `save_day`
- separate parsing (API) from business logic (services)

### DON'T
- don’t import Django request/response here
- don’t implement “sync” complexity here (use outbox)
- don’t add caching in services unless required later
- don’t hide logic in model properties
