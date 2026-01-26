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
