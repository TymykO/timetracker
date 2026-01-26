# TODO — TimeTracker (MVP)

> Ten plik jest **operacyjną listą zadań** dla pracy agentów w Cursor.  
> AGENTS.md są kontraktem i zasadami. README.md to dokumentacja uruchomienia i architektury.
>
> Zasada: robimy małe, testowalne kroki. Backend jest SSoT dla reguł domenowych.

---

## 0) Repo / scaffolding / gotowość do pracy agentów (PROMPT 0)
- [x] Repo ma strukturę: `backend/`, `frontend/`, `docker/`, `scripts/`, `.cursor/`
- [x] Django skeleton istnieje (`backend/manage.py`, `backend/config/`, `backend/timetracker_app/`)
- [x] Vite React TS scaffold istnieje (`frontend/` z `package.json`, `src/`, `vite.config.ts`)
- [x] Docker compose pliki istnieją: `docker-compose.dev.yml`, `docker-compose.prod.yml`
- [x] `.env.example` istnieje
- [x] AGENTS.md istnieją w wymaganych lokalizacjach:
  - [x] `AGENTS.md` (root)
  - [x] `backend/AGENTS.md`
  - [x] `frontend/AGENTS.md`
  - [x] `backend/timetracker_app/services/AGENTS.md`
  - [x] `backend/timetracker_app/auth/AGENTS.md`
  - [x] `backend/timetracker_app/outbox/AGENTS.md`
  - [ ] `frontend/src/pages/Day/AGENTS.md` *(upewnić się, że folder istnieje po scaffoldu Vite)*
- [x] README istnieją:
  - [x] `README.md` (root)
  - [x] `backend/README.md`
  - [x] `frontend/README.md`

**Do wykonania w PROMPT 0 (organizacyjny):**
- [ ] Zweryfikować spójność: czy wszystkie AGENTS/README są w repo i nie zostały nadpisane przez scaffold
- [ ] Zweryfikować, czy `frontend/src/pages/Day/AGENTS.md` istnieje; jeśli nie — utworzyć foldery `src/pages/Day/`
- [ ] Zweryfikować, czy `backend/requirements.txt` jest gotowy na MVP (Django, psycopg, itd.)
- [ ] Zweryfikować, czy docker-compose wskazuje poprawne ścieżki/konteksty do Dockerfile
- [ ] Ustalić finalne nazwy aplikacji Django (projekt `config`, app `timetracker_app`) i nie zmieniać bez powodu

---

## 1) Backend — zależności i konfiguracja (PROMPT 1)
- [ ] Uzupełnić `backend/requirements.txt` (MVP-minimum):
  - Django
  - psycopg (lub psycopg2-binary — decyzja i konsekwencja)
  - python-dotenv (opcjonalnie) / albo `os.environ` + `.env` przez docker-compose
  - django-cors-headers (dla dev SPA)
  - pytest/pytest-django (opcjonalnie) lub zostać na `manage.py test`
- [ ] Skonfigurować `backend/config/settings.py`:
  - Postgres (env-based)
  - `TIME_ZONE="Europe/Warsaw"`, `USE_TZ=True`
  - CORS + cookies dla SPA dev
  - Session auth, CSRF (w dev ustawić sensownie)
- [ ] Spiąć `backend/config/urls.py`:
  - `/api/...` router
  - endpointy auth/timesheet/tasks
- [ ] Przygotować podstawowy logging (MVP)

---

## 2) Backend — modele + constraints + indeksy (PROMPT 2)
**Zaimplementować modele w `timetracker_app/models.py`:**
- [ ] `Employee` (email unique, is_active, daily_norm_minutes)
- [ ] `TaskCache` (is_active, display_name, search_text, lookup fields + fields_json “rezerwa”)
- [ ] `TimeEntry`:
  - FK employee, FK taskcache
  - `work_date` (date)
  - `duration_minutes_raw` (int > 0)
  - `billable_half_hours` (int computed)
  - UniqueConstraint: `(employee, work_date, task)`
- [ ] `CalendarOverride`:
  - `day` unique
  - `day_type` = Working/Free

**DB:**
- [ ] Indeksy pod najczęstsze zapytania:
  - `TimeEntry(employee, work_date)`
  - `TimeEntry(work_date)`
  - `TaskCache(is_active)` + opcjonalnie pola filtrów
- [ ] Migracje: `makemigrations`, `migrate`

---

## 3) Backend — auth (Option B) + tokeny (PROMPT 3)
- [ ] Zdecydować: używamy Django `User` jako auth identity + OneToOne do `Employee`
- [ ] Admin-only provisioning:
  - [ ] Admin tworzy Employee (+ User)
  - [ ] Generowanie INVITE token (hash w DB)
  - [ ] Set password flow (consume token, ustawia hasło)
- [ ] Password reset:
  - [ ] request reset (nie ujawnia czy email istnieje)
  - [ ] confirm reset (consume token)
- [ ] Session login/logout endpoints
- [ ] `GET /api/me` (profil pracownika, flagi)

**Testy:**
- [ ] invite: valid/expired/used
- [ ] reset: valid/expired/used
- [ ] login: active/inactive

---

## 4) Backend — Timesheet services (PROMPT 4)
**Zaimplementować serwisy w `timetracker_app/services/`:**
- [ ] `CalendarService`:
  - day_type (weekend default + override)
- [ ] `TimesheetService`:
  - `get_day(employee, date)`
  - `save_day(employee, date, items[])` (full-state save)
  - `month_summary(employee, month)`
- [ ] Reguły domenowe (hard):
  - [ ] brak future
  - [ ] editable window: current + previous month
  - [ ] no duplicates per day
  - [ ] duration > 0
  - [ ] day total <= 1440
  - [ ] billable rounding: `billable_half_hours = ceil(raw/30)`
  - [ ] overtime: Working vs Free + daily_norm_minutes
- [ ] Dodatkowe UX pola:
  - [ ] `has_entries` per day w month summary
  - [ ] totals liczone po stronie backend (frontend nie liczy overtime)

**Testy (krytyczne):**
- [ ] save_day: create/update/delete
- [ ] walidacje: future, okno edycji, total>1440, duration<=0, duplicates
- [ ] overtime: Working vs Free + override

---

## 5) Backend — API endpoints (PROMPT 5)
W `timetracker_app/api/`:
- [ ] Schemas/DTO (input/output) — spójne z frontend
- [ ] `GET /api/timesheet/month?month=YYYY-MM`
- [ ] `GET /api/timesheet/day?date=YYYY-MM-DD`
- [ ] `POST /api/timesheet/day/save`
- [ ] `GET /api/tasks/active`
- [ ] Auth endpoints (login/logout/me + invite/reset)

**Wymagania:**
- [ ] 401 → brak sesji
- [ ] 403 → inactive employee / brak dostępu
- [ ] 4xx → czytelny komunikat walidacji

---

## 6) Backend — Outbox + Worker (PROMPT 6)
- [ ] Model `OutboxJob` + constraints (dedup_key unique, status, run_after, attempts)
- [ ] `enqueue()` z dedup
- [ ] Dispatcher: `run_once`, `run_forever`, retries/backoff
- [ ] Management command: `worker_run`
- [ ] Minimalny handler (może być stub) np. `TIMESHEET_DAY_SAVED`

**Testy:**
- [ ] dedup działa
- [ ] retry/backoff działa
- [ ] RUNNING/DONE/FAILED działa

---

## 7) Frontend — porządek projektu + routing (PROMPT 7)
- [ ] Utworzyć brakujące katalogi zgodnie z planem (jeśli scaffold ich nie ma):
  - `src/app/` (api_client, router, auth_guard)
  - `src/pages/Month/`
  - `src/pages/Day/`
  - `src/pages/Login/`
  - `src/pages/SetPassword/`
  - `src/pages/ResetPassword/`
  - `src/types/dto.ts`
- [ ] Routing:
  - `/login`
  - `/set-password?token=...`
  - `/reset-password?...`
  - `/month/:yyyy-mm`
  - `/day/:yyyy-mm-dd`
- [ ] AuthGuard: redirect na `/login` przy 401

---

## 8) Frontend — API client + DTO (PROMPT 8)
- [ ] `api_client.ts`:
  - baseURL env: `VITE_API_BASE_URL`
  - `credentials: "include"`
  - centralne error handling
- [ ] DTO types w `types/dto.ts`:
  - Month summary DTO
  - Day DTO (entries + totals + flags)
  - Tasks DTO (fields do filtrów + display_name + search_text)
  - Auth DTOs

---

## 9) Frontend — Month view (PROMPT 9)
- [ ] UI tabeli miesiąca:
  - day_type, working_time_raw, overtime, has_entries
- [ ] Nawigacja miesiącami (bez future months)
- [ ] Klik dzień → przejście do Day view
- [ ] Blokada future days w UI
- [ ] Po save_day: odświeżyć month summary

---

## 10) Frontend — Day view (PROMPT 10)
Zgodnie z `frontend/src/pages/Day/AGENTS.md`:
- [ ] Załadować day + tasks równolegle
- [ ] Filtry: project_phase / department / discipline + search_text
- [ ] Selected tasks bez duplikatów (Map/Set)
- [ ] Lista filtrowana nie pokazuje już wybranych
- [ ] Walidacje UI:
  - required duration > 0
  - total <= 24h
- [ ] Save wysyła pełny stan dnia
- [ ] Editability window: disable inputs/save gdy nieedytowalne

---

## 11) Docker / infra (PROMPT 11)
- [ ] Dev compose:
  - backend + db + (opcjonalnie) worker
  - frontend w dev (npm run dev) lub osobny kontener (decyzja)
- [ ] Prod compose:
  - backend (gunicorn)
  - worker
  - db
  - nginx (reverse proxy, static)
- [ ] `.env.example` uzupełnić o wszystkie potrzebne zmienne:
  - SECRET_KEY, DEBUG, ALLOWED_HOSTS
  - DB_* (name/user/pass/host/port)
  - CORS/CSRF origins (dev)
  - VITE_API_BASE_URL (dla frontend dev)

---

## 12) Stabilizacja jakości (PROMPT 12)
- [ ] Minimalny lint/format:
  - backend: ruff/black (opcjonalnie, ale polecane)
  - frontend: eslint (już w Vite)
- [ ] Smoke tests:
  - login → month → day → save → month refresh
- [ ] Minimalny seed/admin check:
  - admin dodaje pracownika, generuje invite link

---

## 13) “Definition of Done” (MVP)
- [ ] Admin może dodać pracownika i wygenerować invite link
- [ ] Pracownik ustawia hasło i loguje się email+hasło
- [ ] Month view działa, bez future months/days, pokazuje overtime i has_entries
- [ ] Day view działa: filtry, bez duplikatów, save full-state, limity (<=24h), brak future, okno edycji
- [ ] Backend ma testy dla kluczowych reguł `save_day()` i auth tokenów
- [ ] Docker dev odpala cały stack bez ręcznych hacków

---

## Prompts roadmap (w skrócie)
- PROMPT 0: organizacyjny / repo audit / uzupełnić brakujące foldery
- PROMPT 1–6: backend (deps → models → auth → services → API → outbox/worker)
- PROMPT 7–10: frontend (routing → api client → month → day)
- PROMPT 11–12: docker + stabilizacja

---

## Smoke Test Checklist (Manual)

> Manualna lista testów do przeprowadzenia przed wypuszczeniem MVP.
> Testy E2E (Playwright) pokrywają większość scenariuszy, ale ta checklist służy jako ostateczna weryfikacja end-to-end flow.

### Prerequisites

- [ ] Backend running (dev: `docker compose -f docker-compose.dev.yml up`)
- [ ] Frontend running (`cd frontend && npm run dev` lub w kontenerze)
- [ ] Database migrated (`python manage.py migrate`)
- [ ] Superuser created (`python manage.py createsuperuser`)
- [ ] Test data seeded (opcjonalnie: `python manage.py seed_testdata`)

### Test Flow

#### 1. Admin Flow — Tworzenie pracownika i zaproszenie

- [ ] Login to Django Admin (`http://localhost:8000/admin`)
  - Username/password: admin credentials utworzone przez `createsuperuser`
- [ ] Navigate to Employees (`/admin/timetracker_app/employee/`)
- [ ] Click "Add Employee"
- [ ] Fill form:
  - [ ] Email: `test@example.com`
  - [ ] Is active: checked
  - [ ] Daily norm minutes: `480` (8 godzin)
- [ ] Save employee
- [ ] Select employee from list (checkbox)
- [ ] Select action "Generate invite link" from dropdown
- [ ] Click "Go"
- [ ] Copy invite link/token from success message
  - Format: `http://localhost:5173/set-password?token=<TOKEN>`

#### 2. Employee Invite Flow — Ustawienie hasła

- [ ] Open frontend (`http://localhost:5173`)
- [ ] Visit invite link: `/set-password?token=<TOKEN>`
- [ ] Verify token validation:
  - [ ] Email is displayed: `test@example.com`
  - [ ] Form is enabled
- [ ] Fill password form:
  - [ ] Password: `testpass123` (minimum 8 chars)
  - [ ] Password confirm: `testpass123`
- [ ] Click "Ustaw hasło" / "Set Password"
- [ ] Verify success message: "Hasło zostało ustawione" / "Password set successfully"
- [ ] Verify redirect to `/login`

#### 3. Login Flow — Logowanie

- [ ] Visit `/login` (if not already there)
- [ ] Fill login form:
  - [ ] Email: `test@example.com`
  - [ ] Password: `testpass123`
- [ ] Click "Zaloguj" / "Login"
- [ ] Verify redirect to `/month/<current-month>`
  - Example: `/month/2025-01`
- [ ] Verify user info displayed:
  - [ ] Email visible in header/navbar: `test@example.com`
  - [ ] Logout button/link visible

#### 4. Month View — Przeglądanie miesiąca

- [ ] Verify month table displays:
  - [ ] All days of month (28-31 rows depending on month)
  - [ ] Columns: Date, Day Type (Working/Free), Working Time, Overtime, Has Entries
- [ ] Verify day types:
  - [ ] Weekdays (Mon-Fri): "Working" or "Robocze"
  - [ ] Weekends (Sat-Sun): "Free" or "Wolne"
- [ ] Verify future days:
  - [ ] Future days are greyed out or marked as not editable
  - [ ] Future days cannot be clicked (or redirect is blocked)
- [ ] Navigation:
  - [ ] Click "Poprzedni miesiąc" / "Previous Month"
  - [ ] Verify URL changed to previous month
  - [ ] Verify table reloaded with previous month data
  - [ ] Click "Następny miesiąc" / "Next Month" (if not current month)
  - [ ] Verify navigation back to current month works
  - [ ] Verify "Next Month" button is disabled when in current month

#### 5. Day View — Wprowadzanie czasu

- [ ] From Month View, click on editable day (current or previous month)
  - Example: Click on row for `2025-01-15`
- [ ] Verify redirect to `/day/2025-01-15`
- [ ] Verify day view loaded:
  - [ ] Date displayed in header: `2025-01-15`
  - [ ] Day type displayed: "Working" or "Free"
  - [ ] Tasks list visible: "Dostępne zadania" / "Available tasks"
- [ ] Test filters:
  - [ ] Project phase filter/dropdown visible
  - [ ] Department filter/dropdown visible
  - [ ] Discipline filter/dropdown visible
  - [ ] Search text input visible
  - [ ] Change filter value → verify tasks list updates
  - [ ] Enter search text → verify tasks list filters
- [ ] Select tasks:
  - [ ] Click "Wybierz" / "Select" on first task
  - [ ] Verify task moves to "Wybrane zadania" / "Selected tasks"
  - [ ] Verify task is no longer in available list (or button disabled)
  - [ ] Select 2-3 more tasks
  - [ ] Verify all selected tasks are in "Selected tasks" section
- [ ] Enter durations:
  - [ ] Fill duration for first task: `120` minutes
  - [ ] Fill duration for second task: `180` minutes
  - [ ] Fill duration for third task: `240` minutes
  - [ ] Verify total displayed: `540 minutes` or `9:00 hours`
- [ ] Save:
  - [ ] Click "Zapisz" / "Save"
  - [ ] Verify success message: "Zapisano" / "Saved successfully"
  - [ ] Verify form remains editable (can modify and save again)

#### 6. Month Refresh — Weryfikacja zmian

- [ ] Click "Powrót" / "Back to Month" or navigate to `/month/2025-01`
- [ ] Verify month view shows updated data:
  - [ ] Row for `2025-01-15` has:
    - [ ] `has_entries` indicator (checkmark/icon or "Tak"/"Yes")
    - [ ] `working_time_raw_minutes`: `540` minutes or `9:00` hours
    - [ ] `overtime_minutes`: calculated based on day type
      - If Working: `max(0, 540 - 480) = 60` minutes
      - If Free: `540` minutes
- [ ] Verify total is correct

#### 7. Validation Tests — Sprawdzenie walidacji

##### 7.1 Duration = 0

- [ ] Navigate to day view (editable day)
- [ ] Select task
- [ ] Enter duration: `0`
- [ ] Click Save
- [ ] Verify error message: "Duration must be greater than 0" or similar

##### 7.2 Duration < 0

- [ ] Enter duration: `-10`
- [ ] Click Save
- [ ] Verify error message: "Duration must be positive" or similar

##### 7.3 Total > 1440 minutes

- [ ] Select 2 tasks
- [ ] Enter durations: `800` and `700` (total = 1500)
- [ ] Click Save
- [ ] Verify error message: "Total exceeds 1440 minutes (24 hours)" or similar

##### 7.4 Duplicate task

- [ ] Select task A
- [ ] Try to select task A again
- [ ] Verify task A is not available in list (or button disabled)

##### 7.5 Future date

- [ ] Navigate to future day (e.g., tomorrow or day after tomorrow)
- [ ] Verify Save button is disabled
- [ ] Verify message: "Cannot edit future dates" or similar

##### 7.6 Old month (2 months ago)

- [ ] Navigate to day 2 months ago (e.g., `2024-11-15`)
- [ ] Verify Save button is disabled
- [ ] Verify message: "Cannot edit outside edit window" or similar

#### 8. Edge Cases — Przypadki graniczne

##### 8.1 Exactly 1440 minutes

- [ ] Navigate to editable day
- [ ] Select task
- [ ] Enter duration: `1440`
- [ ] Click Save
- [ ] Verify success (no error)

##### 8.2 Last day of month

- [ ] Navigate to last day of month (e.g., `2025-01-31`)
- [ ] Select task and enter time
- [ ] Click Save
- [ ] Verify success

##### 8.3 First day of month

- [ ] Navigate to first day of month (e.g., `2025-01-01`)
- [ ] Select task and enter time
- [ ] Click Save
- [ ] Verify success

##### 8.4 Free day (weekend) — Overtime calculation

- [ ] Navigate to Saturday or Sunday
- [ ] Select task and enter time: `300` minutes
- [ ] Click Save
- [ ] Return to month view
- [ ] Verify overtime for that day = `300` minutes (entire time is overtime)

##### 8.5 Working day — Overtime calculation

- [ ] Navigate to weekday
- [ ] Select task and enter time: `500` minutes
- [ ] Click Save
- [ ] Return to month view
- [ ] Verify overtime for that day = `max(0, 500 - 480) = 20` minutes

#### 9. Logout — Wylogowanie

- [ ] Click "Wyloguj" / "Logout" button/link
- [ ] Verify redirect to `/login`
- [ ] Verify session cleared:
  - [ ] Try to navigate to `/month/2025-01`
  - [ ] Verify redirect back to `/login` (not authorized)
- [ ] Try to navigate to `/day/2025-01-15`
- [ ] Verify redirect back to `/login`

---

### Smoke Test Summary

Po zakończeniu wszystkich testów:

- [ ] All critical flows work (admin → invite → login → month → day → save → refresh)
- [ ] All validations work (duration, total, dates, edit window)
- [ ] All edge cases handled (1440 min, month boundaries, overtime)
- [ ] No console errors (check browser DevTools)
- [ ] No server errors (check backend logs)

### Known Issues / Notes

(Miejsce na notowanie znalezionych problemów podczas testów)

- Issue 1: ...
- Issue 2: ...

---
