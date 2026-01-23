# TimeTracker — TODO (Project Setup → Docs → Build)

> Cel na teraz: przygotować repo “szkielet” (katalogi + puste pliki), a potem uzupełnić dokumentację (AGENTS.md + README.md). Dopiero po tym uruchamiamy Cursor do budowy aplikacji.

---

## A) Repo skeleton (katalogi + puste pliki)

### A1. Root
- [ ] Utworzyć katalogi: `docker/`, `scripts/`, `backend/`, `frontend/`, `.cursor/plans/`
- [ ] Utworzyć puste pliki:
  - [ ] `AGENTS.md`
  - [ ] `README.md`
  - [ ] `TODO.md`
  - [ ] `.env.example`
  - [ ] `.gitignore`
  - [ ] `docker-compose.dev.yml`
  - [ ] `docker-compose.prod.yml`
- [ ] Docker anchors:
  - [ ] `docker/nginx/default.conf`
  - [ ] `docker/backend/Dockerfile`
  - [ ] `docker/frontend/Dockerfile`
  - [ ] `docker/worker/Dockerfile`
- [ ] Scripts anchors:
  - [ ] `scripts/dev.sh`
  - [ ] `scripts/db_backup.sh`
  - [ ] `scripts/db_restore.sh`
- [ ] `.cursor/plans/.gitkeep`

### A2. Backend skeleton
- [ ] `backend/AGENTS.md`
- [ ] `backend/README.md`
- [ ] `backend/requirements.txt`
- [ ] `backend/manage.py`
- [ ] `backend/config/` + pliki: `__init__.py`, `settings.py`, `urls.py`, `wsgi.py`
- [ ] `backend/timetracker_app/`:
  - [ ] `__init__.py`, `models.py`, `admin.py`, `apps.py`
  - [ ] `migrations/__init__.py`
  - [ ] `api/`: `urls.py`, `schemas.py`, `views_auth.py`, `views_tasks.py`, `views_timesheet.py`
  - [ ] `services/`: `AGENTS.md`, `timesheet_service.py`, `task_service.py`, `calendar_service.py`
  - [ ] `auth/`: `AGENTS.md`, `tokens.py`, `password_flows.py`
  - [ ] `outbox/`: `AGENTS.md`, `dispatcher.py`, `handlers.py`
  - [ ] `management/commands/`: `worker_run.py`, `sync_tasks.py`
  - [ ] `tests/`: `__init__.py`, `test_auth.py`, `test_timesheet.py`, `test_tasks.py`

### A3. Frontend skeleton
- [ ] `frontend/AGENTS.md`
- [ ] `frontend/README.md`
- [ ] `frontend/package.json`
- [ ] `frontend/tsconfig.json`
- [ ] `frontend/vite.config.ts`
- [ ] `frontend/src/`:
  - [ ] `main.tsx`
  - [ ] `index.css` (opcjonalnie)
  - [ ] `app/`: `router.tsx`, `api_client.ts`, `query.ts`, `auth_guard.tsx`
  - [ ] `pages/`: `Login/`, `SetPassword/`, `ForgotPassword/`, `ResetPassword/`, `Month/`, `Day/` + `pages/Day/AGENTS.md`
  - [ ] `components/`: `MonthTable.tsx`, `FiltersBar.tsx`, `TaskPicker.tsx`, `SelectedTasksTable.tsx`
  - [ ] `types/`: `dto.ts`

### A4. Git
- [ ] `git add .`
- [ ] `git commit -m "chore: project skeleton (dirs + anchors)"`

---

## B) Dokumentacja (uzupełnianie po skeletonie)

### B1. AGENTS.md (7 plików)
- [ ] Root: `./AGENTS.md`
- [ ] Backend: `./backend/AGENTS.md`
- [ ] Frontend: `./frontend/AGENTS.md`
- [ ] Backend services: `./backend/timetracker_app/services/AGENTS.md`
- [ ] Backend auth: `./backend/timetracker_app/auth/AGENTS.md`
- [ ] Backend outbox: `./backend/timetracker_app/outbox/AGENTS.md`
- [ ] Frontend Day page: `./frontend/src/pages/Day/AGENTS.md`

### B2. README.md (3 pliki)
- [ ] Root: `./README.md`
- [ ] Backend: `./backend/README.md`
- [ ] Frontend: `./frontend/README.md`

---

## C) Cursor build (dopiero po B)
- [ ] Etap 1: Docker “hello world” (FE+BE+DB)
- [ ] Etap 2: Backend modele + migracje + testy domeny
- [ ] Etap 3: Backend auth (admin-only: invite/set-password/login/reset)
- [ ] Etap 4: API (month/day/save/tasks)
- [ ] Etap 5: Frontend auth pages + guard
- [ ] Etap 6: Month view
- [ ] Etap 7: Day view (filtry/selected/save)
- [ ] Etap 8: Outbox + worker
- [ ] Etap 9: Hardening + prod compose
