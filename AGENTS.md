# TimeTracker — AGENTS (ROOT)

> This file is the **highest-level contract** for Cursor/AI agents working in this repo.  
> Follow these rules strictly. If something is unclear, **do not invent**—leave TODO markers and propose the smallest safe next step.

---

## 0) Project goal (MVP)

Build **TimeTracker**: a web app for employees to log time per day across many tasks, with two key UI screens:

1) **Month view** — monthly table of days with:
- day type: `Working` / `Free`
- **working time (raw)** summed from entries
- **overtime**:
  - Working: `max(0, raw_sum - daily_norm_minutes)`
  - Free: `overtime = raw_sum`
- `has_entries` indicator (true if any entries exist)
- navigation between months, but **no future months**
- **future days disabled**

2) **Day view** — time-entry form for a given day:
- list of **active tasks** with filters: `project_phase`, `department`, `discipline` (+ free-text search)
- user selects tasks into **Selected tasks** list (no duplicates)
- user enters time per selected task (raw minutes/hours)
- after adding a task, filters remain unchanged
- user can edit only for **current month and previous month**
- **no future dates**
- **sum of all task durations per day must be <= 24h**
- **no zero-duration entries** (duration must be > 0)

Auth requirement:
- **Option B: email + password**
- employees are **created only by admin**
- invite flow: admin sends set-password link (token), user sets password, then logs in normally
- password reset supported

Backend stack:
- Django + PostgreSQL
- session cookies (HttpOnly) for auth
- Outbox + Worker for async projections/sync

Frontend stack:
- Vite + React + TypeScript SPA
- Fetch API (or thin wrapper), credentials included for cookies
- Minimal UI dependencies (keep it simple)

---

## 1) Non-negotiable domain rules (backend is source of truth)

- No entries in the future (`date > today` forbidden)
- Editing window: only **current month and previous month**
- Per employee/day/task: **no duplicates** (DB constraint + validation)
- Duration must be **> 0**
- Day total raw duration must be **<= 1440 minutes**
- Billing:
  - store raw minutes: `duration_minutes_raw`
  - store billable hours: `hours_decimal` (Decimal, >= 0.5)
  - calculation: rounds to nearest 0.5h, e.g., `ceil((raw_minutes / 60) * 2) / 2`
- Overtime:
  - Working day: `max(0, day_raw_sum - employee.daily_norm_minutes)`
  - Free day: `overtime = day_raw_sum`
- Day type:
  - default: Saturday/Sunday = Free, other weekdays = Working
  - admin override possible (CalendarOverride)

Frontend may provide UX guards, but backend must enforce all rules.

---

## 2) Architecture & responsibilities (KISS + SOLID + GRASP)

### Frontend (React SPA)
- Responsible for UX: Month/Day screens, filters, selected tasks, navigation, forms
- Must not duplicate business logic beyond basic UX validation
- Uses API contract as the single source of truth for computed values (totals, overtime, editability)

### Backend (Django API)
- Responsible for:
  - domain validation and persistence
  - computing month/day summaries
  - auth flows (invite/set-password/login/reset)
  - outbox enqueueing for async processing
- Keep controllers thin: API views call service layer
- Service layer holds domain logic (single responsibility)

### Worker
- Processes `OutboxJob` records
- Must be idempotent (safe to retry)
- Must support retries/backoff and status tracking

---

## 3) Repository structure (high level)

- `backend/` — Django project
- `frontend/` — Vite React TS app
- `docker/` — Dockerfiles + nginx conf
- `scripts/` — helper scripts
- `.cursor/plans/` — planning artifacts (optional)

There are additional `AGENTS.md` files in subdirectories.  
**Rule:** the nearest `AGENTS.md` in the directory tree takes precedence for work in that subtree.

---

## 4) Implementation approach (order matters)

When implementing, follow this sequence:

1) Backend models + constraints + migrations
2) Backend domain services (`save_day`, `month_summary`, etc.) + tests
3) Backend auth flows + tests
4) Backend API endpoints + integration tests
5) Frontend auth pages + session guard
6) Frontend Month view
7) Frontend Day view (filters + selected + save)
8) Worker + outbox mechanics
9) Hardening (prod compose, logging, error handling)

Do not jump ahead (e.g., do not build full UI before backend rules/tests exist).

---

## 5) Coding standards (project-wide)

- Prefer clarity over cleverness
- No “magic” side effects in models; keep logic in services
- Add types where useful (Python typing, TS types)
- Write tests for:
  - `save_day()` edge cases
  - auth token flows
  - constraints (duplicate prevention, date rules)
- Keep dependencies minimal; do not add new libraries without a clear reason
- Never store secrets in git; use `.env` locally and `.env.example` as template

---

## 6) How to work safely (agent workflow)

Before changes:
- Read this root `AGENTS.md`
- Read the nearest `AGENTS.md` inside the target directory

During changes:
- Make small, atomic edits
- Update/extend tests alongside logic changes
- Prefer migrations over manual DB manipulation

After changes:
- Ensure the app still runs
- Ensure tests pass (or add TODO with explicit reasons if not yet runnable)

If uncertain:
- Leave `TODO:` markers and propose the smallest safe next step
- Do not implement speculative features beyond MVP scope

---

## 7) API contract (high-level expectations)

Backend must provide endpoints for:
- Auth: login/logout/me + invite/set-password + reset
- Timesheet: month summary, day data, save day
- Tasks: list active tasks + filter values

Frontend must:
- include cookies (`credentials: "include"`)
- handle 401 by redirecting to `/login`
- refetch Month after saving Day (invalidate cache)

(Exact schemas will be defined in backend-level AGENTS and code.)

---

## 8) Notes / future phases (not MVP now)

- Celery + Redis for background jobs (Phase 2)
- richer anomaly detection (e.g., absurd durations beyond 24h already blocked)
- performance improvements if task list becomes large (server-side filtering)

For MVP, keep it simple, stable, and testable.

---

## 9) How to run and test (dev)

Prefer Docker for consistent environments. Local run is allowed for quick iteration.

### Docker (recommended)
1. Copy env:
   - `cp .env.example .env`  (Windows: create `.env` manually from `.env.example`)
2. Start dev stack:
   - `docker compose -f docker-compose.dev.yml up --build`
3. Backend (inside container):
   - `python manage.py migrate`
   - `python manage.py createsuperuser`
4. Run tests:
   - `python manage.py test`

### Local (quick dev)
Backend:
- create & activate venv
- `pip install -r backend/requirements.txt`
- `python backend/manage.py migrate`
- `python backend/manage.py runserver`
- `python backend/manage.py test`

**Database:** Local dev uses **SQLite by default** (fast, no Docker needed). To use PostgreSQL locally, set `USE_SQLITE=False` and run Docker db container. Tests always use in-memory SQLite.

Frontend:
- `cd frontend`
- `npm install`
- `npm run dev`
- `npm run build`

> Note: Frontend talks to backend via API; ensure CORS/cookies are configured in backend settings.

---

## 10) Documentation & language rules

To keep collaboration simple and consistent:

- **AGENTS.md** files: English (AI instructions must be unambiguous)
- **README.md** files: English (public / universal onboarding)
- **Code comments & docstrings**: **Polish** (explain *what* and *why*, not restating the code)
- **UI text** (labels/messages): Polish by default (can be switched later)

Comment style:
- Short and specific.
- Prefer “why / constraints / edge cases” over “what this line does”.

---

## 11) Timezone & date handling

- Project timezone: **Europe/Warsaw**
- Django settings: `USE_TZ = True`, `TIME_ZONE = "Europe/Warsaw"`
- Store datetimes as UTC in DB (Django handles it).
- Timesheets operate primarily on **dates** (not datetimes). Avoid mixing date/datetime.
- “Today” is evaluated in Europe/Warsaw timezone.

---

## 12) Git / commit conventions (optional but recommended)

Use Conventional Commits:

`<type>(<scope>): <subject>`

Types: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `chore`

Scopes examples:
- `backend`, `frontend`, `auth`, `timesheet`, `outbox`, `docker`, `deps`

Keep commits focused (one logical change per commit).

### AI Agent: Commit workflow

**IMPORTANT:** Agent must NEVER create commits automatically. Only commit when explicitly requested by user.

**Trigger phrases:** User must use one of these phrases to request commits:
- "zacommituj zmiany" (Polish)
- "stwórz commity" (Polish)
- "zrób commity" (Polish)
- "commit changes" (English)
- "create commits" (English)

**When triggered, agent must:**

1. **Always split changes into multiple logical commits** - group related changes together
2. **Create separate commits** for different types of changes:
   - Documentation changes separate from code changes
   - Configuration changes separate from feature implementation
   - Dependencies separate from application code
   - Each feature/fix in its own commit
3. **Use clear, informative commit messages WITHOUT emojis**
4. **Follow conventional commit format** strictly: `<type>(<scope>): <subject>`
5. **Keep commit messages concise** - focus on WHAT changed and WHY

Example of good commit sequence after organizational audit:
```
docs: napraw formatowanie markdown w README i AGENTS
feat(backend): skonfiguruj Django settings zgodnie z AGENTS.md
feat(docker): dodaj konfiguracje compose dla dev i prod
chore: zaktualizuj dependencies i konfiguracje
```

**DO NOT:**
- Create commits without explicit user request
- Create single commit with all changes mixed together
- Use emojis in commit messages (❌ 🎉 ✨ etc.)
- Write vague messages like "update files" or "fixes"
- Commit unrelated changes together
