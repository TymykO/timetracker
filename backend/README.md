# TimeTracker — Backend (Django)

This directory contains the **Django backend** for TimeTracker:
- domain rules + persistence (PostgreSQL)
- authentication (admin-provisioned users, email + password)
- API for Month/Day time entry screens
- Outbox pattern + Worker for background processing

Root-level overview and diagrams live in `../README.md`.  
Agent rules live in:
- `../AGENTS.md` (root)
- `./AGENTS.md` (backend)
- nearest module AGENTS: `timetracker_app/services/`, `timetracker_app/auth/`, `timetracker_app/outbox/`

---

## 🧱 Architecture (backend)

Backend follows a layered approach:

- **API layer**: `timetracker_app/api/`  
  Thin HTTP controllers (parse/validate input, call services, return DTOs)

- **Service layer**: `timetracker_app/services/`  
  Core domain logic (`save_day`, `get_day`, `get_month_summary`, calculations)

- **Domain layer**: `timetracker_app/models.py`  
  Persistence models + constraints + indexes (no heavy business logic)

- **Auth module**: `timetracker_app/auth/`  
  Invite tokens, set-password, login/reset flows (Option B)

- **Outbox module**: `timetracker_app/outbox/`  
  Durable background jobs via DB (enqueue + dispatcher + handlers)

- **Worker**: management command `worker_run`  
  Runs outbox dispatcher loop

---

## 📁 Directory map

```text
backend/
├── manage.py
├── requirements.txt
├── config/                      # Django project config (settings/urls/asgi/wsgi)
└── timetracker_app/
    ├── models.py                # core models (Employee, TaskCache, TimeEntry, AuthToken, OutboxJob, CalendarOverride)
    ├── api/                     # HTTP API endpoints (JSON)
    ├── services/                # domain logic (TimesheetService, TaskService, CalendarService)
    ├── auth/                    # tokens + password flows
    ├── outbox/                  # enqueue + dispatcher + handlers
    ├── management/commands/     # sync tasks, worker runner
    └── tests/                   # backend tests
````

---

## ✅ Core domain rules (backend is source of truth)

Backend enforces:

* no future entries
* editable window: current month + previous month only
* no duplicates per employee/day/task (DB unique constraint + service validation)
* duration must be > 0
* day total raw duration <= 1440 minutes
* billable rounding to 0.5h:

  * `billable_half_hours = ceil(duration_minutes_raw / 30)`
* overtime:

  * Working: `max(0, raw_sum - employee.daily_norm_minutes)`
  * Free: `overtime = raw_sum`
* day type:

  * weekend default + optional override (CalendarOverride)

---

## 🔌 API responsibilities (high-level)

### Auth

* session-based auth using cookies (HttpOnly)
* login: email + password
* set-password via invite token
* password reset via reset token
* `/api/me` returns current employee profile + flags

### Timesheet

* Month summary endpoint:

  * days list with `working_time_raw`, `overtime`, `has_entries`, edit flags
* Day endpoint:

  * list of selected entries for the day, totals, edit flags
* Save day endpoint:

  * **full-state save** (payload is authoritative)
  * transaction upsert/delete TimeEntry

### Tasks

* active tasks list from `TaskCache` (`is_active=True`)
* fields for filtering: `project_phase`, `department`, `discipline`
* `display_name` + `search_text` for UX

---

## 🔐 Authentication flow (Option B)

No public registration. Admin provisions employees.

1. Admin creates Employee (and linked User) in admin panel
2. System generates INVITE token (one-time, expires)
3. User opens `/set-password?token=...` and sets password
4. User logs in with email + password (session cookie)
5. Password reset uses RESET tokens (one-time, expires)

Tokens are stored hashed (never store raw tokens).

---

## 🧵 Outbox + worker

Outbox jobs provide durable background processing:

* `OutboxJob` stored in DB
* services enqueue jobs via `enqueue(job_type, dedup_key, payload)`
* worker (`manage.py worker_run`) polls and runs eligible jobs
* idempotent handlers + retries/backoff

MVP can keep handlers minimal/stubbed, but job lifecycle must work.

---

## 🚀 Running backend (dev)

> Prefer Docker from repo root when possible.
> Below is backend-only guidance.

### Local run (quick)

```bash
pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py createsuperuser
python backend/manage.py runserver
```

### Run tests

```bash
python backend/manage.py test
```

### Run worker (outbox)

```bash
python backend/manage.py worker_run
```

---

## 🧪 Testing scope

Backend tests must cover at minimum:

* `save_day()` validation:

  * future date, edit window, duplicates, total > 1440, duration <= 0
* upsert/delete behavior:

  * create new entries, update existing, delete removed
* overtime calculations (Working vs Free + override)
* invite token + reset token flows:

  * valid, expired, used tokens

---

## 🔧 Notes for future phases

* Celery + Redis may replace/augment outbox worker (Phase 2)
* Server-side task filtering/search if TaskCache grows significantly
* Extended admin tools / audits / reporting endpoints
