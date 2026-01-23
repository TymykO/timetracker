# TimeTracker — AGENTS (BACKEND / OUTBOX)

> Scope: `backend/timetracker_app/outbox/`  
> Purpose: provide a durable, retryable background-job mechanism via DB (Outbox pattern).
>
> MVP: implement **job lifecycle + idempotency**. Handlers can be minimal/stubbed,
> but the system must be safe to retry and safe to run continuously.

---

## 0) Responsibilities

This module owns:
- enqueueing Outbox jobs (create job records with deduplication)
- job dispatch loop logic (select jobs to run, lock, mark status)
- handler registry and handler invocation
- retry / backoff scheduling

This module must NOT:
- contain timesheet domain logic (services own that)
- contain auth logic
- perform HTTP request/response work

---

## 1) Outbox model expectations (MVP)

Model (likely in `timetracker_app/models.py`) should support:

### OutboxJob fields (minimum)
- `job_type` (string enum-like, e.g. `"TIMESHEET_DAY_SAVED"`)
- `dedup_key` (string) — **unique** for idempotency (DB unique constraint)
- `payload_json` (JSON) — small payload, avoid huge blobs
- `status` (enum): `PENDING`, `RUNNING`, `DONE`, `FAILED`
- `attempts` (int, default 0)
- `run_after` (datetime, default now)
- `last_error` (text nullable)
- timestamps: `created_at`, `updated_at`

**Constraints**
- unique index on `dedup_key`
- index on `(status, run_after)` for fast polling
- index on `job_type` optional

---

## 2) Core rules (non-negotiable)

### Idempotency
- Each logical job must have a stable `dedup_key`.
- Enqueue must be safe to call multiple times:
  - if a job with the same `dedup_key` exists, do not create duplicates
  - either return existing job or update payload if policy allows (MVP: return existing)

### Retry safety
- Handlers may run multiple times.
- Handlers must be written so that repeated execution does not corrupt state.
- When in doubt, handlers should be “check then apply” or use UPSERTs.

### Separation
- Services enqueue jobs; worker executes jobs.

---

## 3) Public API in this module (MVP)

Implement these entry points in `dispatcher.py` (or a small facade):

### `enqueue(job_type: str, dedup_key: str, payload: dict) -> OutboxJob`
- Creates a new OutboxJob if `dedup_key` does not exist.
- If it exists:
  - return existing job (MVP policy)
- Must be transaction-safe.
- Should be callable from service layer after commit, or inside the transaction if acceptable
  (preferred: enqueue inside transaction but job execution happens later).

### `run_once(max_jobs: int = 50) -> int`
- Polls eligible jobs:
  - `status == PENDING`
  - `run_after <= now`
- Locks each job (select-for-update / atomic status transition)
- Executes handler
- Updates status accordingly
- Returns number of processed jobs

### `run_forever(poll_seconds: float = 2.0, max_jobs_per_tick: int = 50)`
- Loop calling `run_once`
- Sleep between ticks
- Used by `management/commands/worker_run.py`

---

## 4) Locking / concurrency strategy

Goal: allow multiple worker processes without double-processing jobs.

Recommended pattern:
- Query eligible jobs ordered by `run_after`, limited.
- For each job:
  - attempt atomic transition `PENDING -> RUNNING` with a DB update filter
  - if update affected 0 rows, skip (someone else took it)
  - then run handler
  - set `DONE` or schedule retry

Alternative:
- `select_for_update(skip_locked=True)` if DB supports it (Postgres does).

Choose one approach and document it in code comments.

---

## 5) Retry / backoff policy (MVP)

- On exception:
  - increment `attempts`
  - set `last_error`
  - set `status = PENDING` (or `FAILED` if attempts exceeded)
  - set `run_after = now + backoff(attempts)`

Backoff function (simple, deterministic):
- `delay_seconds = min(60, 2 ** attempts)`  (cap at 60s)
or
- `delay_seconds = min(300, attempts * 10)` (linear)

Max attempts:
- MVP: 10 attempts then `FAILED`

---

## 6) Handler registry (MVP)

`handlers.py` should expose:
- a registry mapping `job_type -> handler function`
- handler signature:
  - `def handle(job: OutboxJob) -> None`

Handlers should:
- parse payload
- perform idempotent actions
- raise on failure (dispatcher schedules retry)

MVP handlers can be:
- `TIMESHEET_DAY_SAVED` → placeholder / log-only (but keep the structure)
Later can be extended to projections/sync.

---

## 7) Integration expectations (where jobs are created)

Services (e.g. `TimesheetService.save_day`) should enqueue jobs like:
- `job_type = "TIMESHEET_DAY_SAVED"`
- `dedup_key = f"timesheet:day_saved:{employee_id}:{date_iso}"`
- `payload = { "employee_id": ..., "date": "...", ... }`

Services must not call handlers directly.

---

## 8) Testing expectations

`test_timesheet.py` (or dedicated outbox tests later) should at least verify:
- enqueue with same dedup_key does not create duplicates
- run_once processes eligible jobs and marks DONE
- failure schedules retry with run_after > now and attempts incremented
- handler called with correct job payload

Tests must not rely on sleeping; use controlled timestamps.

---

## 9) Do / Don’t

### DO
- keep enqueue small and stable
- keep dispatcher loop simple
- prefer DB-level uniqueness for dedup
- write handlers idempotently

### DON’T
- don’t add Celery/Redis in MVP
- don’t execute jobs during HTTP request
- don’t allow unbounded job payload sizes
- don’t silently swallow errors (store last_error, schedule retry)
