````md
# TimeTracker — AGENTS (FRONTEND / Day Page)

> Scope: `frontend/src/pages/Day/`  
> This file defines the **exact UX + state rules** for the Day view.  
> It overrides/extends `frontend/AGENTS.md` and `root AGENTS.md` for this subtree.

---

## 0) Purpose of Day view (MVP)

Day view is the core timesheet entry screen. For a selected date `D`, the user:
- filters a list of active tasks
- picks tasks into a **Selected tasks** list (no duplicates)
- enters durations per selected task
- saves the full day state to backend

Backend is the source of truth; frontend provides good UX and prevents obvious mistakes.

---

## 1) Route and navigation rules

### Route
- Path: `/day/:yyyy-mm-dd`

### Navigation
- User can go **back/forward by day** within allowed range:
  - cannot navigate to future dates
  - can navigate within current month and previous month (editable window)
  - older dates can be viewed only if backend allows (MVP: treat as not editable; still allow open if user navigates, but disable inputs/save)

### Buttons
- “Prev day” / “Next day”
  - Next day disabled if it would be future.
- “Back to month” returns to `/month/:yyyy-mm` of that day.

---

## 2) Data that must be loaded

On page load (and when date changes), fetch in parallel:

1) **Day data**:
- `GET /api/timesheet/day?date=YYYY-MM-DD`
- returns:
  - `entries[]` (selected tasks with current durations)
  - totals: `total_raw_minutes`, `total_overtime_minutes`
  - flags: `is_future`, `is_editable`
  - `day_type` (Working/Free)

2) **Active tasks list**:
- `GET /api/tasks/active`
- returns list of tasks with:
  - `id`
  - `display_name`
  - `search_text`
  - filter fields: `project_phase`, `department`, `discipline` (+ others if present)

**Important:**
- Requests must use `credentials: "include"`.
- If either request returns 401 → redirect to `/login`.

---

## 3) Local state model (recommended)

### A) Filters state (must persist while on the same Day page)
- `filterProjectPhase: string | null`
- `filterDepartment: string | null`
- `filterDiscipline: string | null`
- `searchQuery: string` (matches `search_text`)
- Filters must **NOT reset** when adding a task to Selected list.

### B) Selected tasks state
Represent Selected tasks as a map keyed by task_id for uniqueness:
- `selected: Map<task_id, { duration_minutes_raw: number | "" }>`
or object `{ [taskId]: entry }`

Load initial state from Day API:
- convert `entries[]` into `selected`.

### C) Derived UI state
- `selectedTaskIds = Set(taskId)`
- `filteredTasks = allActiveTasks filtered by filters/search AND NOT IN selectedTaskIds`

---

## 4) “No duplicates” rule

### Rule
A task can be selected **only once** per user/day.

### Enforcement (frontend)
- Selected list uses a Map/Set keyed by `task_id`.
- Filtered list **must exclude** already selected tasks.

### Note
Other users can log time to the same task and same day — that’s allowed. This page only guards duplicates **within the current user/day**.

---

## 5) Filtering behavior (MVP)

### Filter sources
Derive dropdown options from `active tasks list`:
- unique values for `project_phase`, `department`, `discipline`
- sort alphabetically

### Applying filters
A task is shown in Filtered list if:
- matches selected filters (all active filters apply)
- and `searchQuery` is contained in `search_text` (case-insensitive)
- and it’s not selected already

### Search behavior
- `searchQuery` trims whitespace
- case-insensitive contains match
- match against `search_text` (not display_name)

---

## 6) Adding tasks to Selected list

### Interaction
User selects a row in Filtered list and clicks “+” (or row action button).

### Outcome
- task is added to Selected list with empty duration:
  - `duration_minutes_raw = ""` (not 0)
- filters/search remain unchanged
- the task disappears from Filtered list (because it is now selected)

### No zero-duration records
Frontend must **not** allow saving with empty or 0 durations:
- empty duration blocks Save
- 0 blocks Save
- show inline validation message

---

## 7) Duration input rules (MVP)

### Input type
- numeric minutes (int) OR hours decimal (optional)
- MVP recommendation: minutes input (int) for simplicity

### Validation
Per entry:
- required
- integer > 0
- optional UX: max 1440 per entry (not necessary, day total rule is key)

Day total:
- sum of all durations must be <= 1440
- if exceeds:
  - show error banner
  - disable Save

**Note:** Backend enforces all of these; frontend is to prevent pointless requests.

---

## 8) Save behavior (critical)

### When Save is enabled
Save button is enabled only if:
- `is_editable === true`
- no validation errors (all durations present and >0)
- day total <= 1440
- not currently saving

### Payload
Save sends the full state for the day (authoritative):
- `POST /api/timesheet/day/save`
```json
{
  "date": "YYYY-MM-DD",
  "items": [
    { "task_id": 123, "duration_minutes_raw": 90 },
    { "task_id": 456, "duration_minutes_raw": 240 }
  ]
}
````

### Success handling

On success:

* show subtle “Saved”
* refetch:

  * Day data
  * Month summary for that month (invalidate cache)
* keep filters/search as-is (do not reset)
* keep user on the same Day page

### Error handling

* 401 → redirect to `/login`
* 403 → show “No access / contact admin”
* 4xx validation → show message from backend (e.g. outside edit window, future date, sum>1440)
* network/server → show generic retry message, keep user state intact

---

## 9) Editability and disabling UI

If `is_editable === false`:

* disable duration inputs
* disable add/remove actions
* disable Save
* still show existing entries read-only

If `is_future === true`:

* same as not editable + also disable navigation to further future

---

## 10) Day totals display rules

Show:

* “Working time (raw)” = `total_raw_minutes` from backend (display as hh:mm)
* “Overtime” = backend value in minutes formatted as hh:mm
* Do not compute overtime in frontend (backend is authority)
* Display day_type (Working/Free)

No “flag day” feature. Only enforce max 24h/day.

---

## 11) Minimal components (suggested)

Day page can be composed of:

* `FiltersBar` (dropdowns + search)
* `TaskPicker` (filtered list + add button)
* `SelectedTasksTable` (selected tasks + duration inputs + remove)
* `DayTotals` (raw + overtime + day_type)
* `DayNav` (prev/next/back to month)

Keep it simple: no heavy UI libs required in MVP.

---

## 12) Definition of Done (Day page)

Day page is MVP-complete when:

* loads day + tasks, handles 401 redirect
* filters work together (AND) + search_text search
* cannot add duplicate tasks
* filtered list excludes selected tasks
* cannot save with empty/0 durations
* cannot save if total > 24h
* respects editability window (inputs/actions disabled)
* save sends full day payload and refreshes month + day data

```
::contentReference[oaicite:0]{index=0}
```
