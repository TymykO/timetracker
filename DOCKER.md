# TimeTracker - Instrukcje Docker

> Konfiguracja Docker dla środowisk **development** i **production**.

---

## Wymagania

- Docker Desktop (Windows/Mac) lub Docker Engine + Docker Compose (Linux)
- Git (do klonowania repozytorium)

---

## Środowisko Development

### 1. Konfiguracja

Skopiuj plik `.env.example` do `.env`:

**Linux/Mac:**
```bash
cp .env.example .env
```

**Windows:**
```powershell
Copy-Item .env.example .env
```

Lub utwórz plik `.env` ręcznie na podstawie `.env.example`.

### 2. Uruchomienie

```bash
docker compose -f docker-compose.dev.yml up --build
```

**Co się dzieje:**
- Pobierane i budowane są obrazy dla: `db`, `backend`, `frontend`, `worker`
- PostgreSQL startuje z `trust` auth dla wygody dev
- Backend uruchamia Django dev server (`runserver`)
- Frontend uruchamia Vite dev server z hot-reload
- Worker uruchamia Outbox processor

### 3. Migracje i superuser (pierwszy raz)

W osobnym terminalu:

```bash
# Migracje bazy danych
docker exec -it timetracker_backend_dev python manage.py migrate

# Utworzenie superusera (admin)
docker exec -it timetracker_backend_dev python manage.py createsuperuser

# Opcjonalnie: seed testowych danych
docker exec -it timetracker_backend_dev python manage.py seed_testdata
```

### 4. Dostęp

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000/api
- **Django Admin:** http://localhost:8000/admin
- **PostgreSQL:** localhost:5432 (user: `timetracker`, pass: `timetracker`, db: `timetracker`)

### 5. Zatrzymanie

```bash
# Zatrzymanie kontenerów (dane pozostają)
docker compose -f docker-compose.dev.yml stop

# Zatrzymanie i usunięcie kontenerów (dane w volumes pozostają)
docker compose -f docker-compose.dev.yml down

# Usunięcie kontenerów + volumes (UWAGA: usunie dane bazy!)
docker compose -f docker-compose.dev.yml down -v
```

### 6. Logi

```bash
# Wszystkie serwisy
docker compose -f docker-compose.dev.yml logs -f

# Konkretny serwis
docker compose -f docker-compose.dev.yml logs -f backend
docker compose -f docker-compose.dev.yml logs -f worker
docker compose -f docker-compose.dev.yml logs -f frontend
```

---

## Środowisko Production

### 1. Konfiguracja

Skopiuj `.env.example` do `.env` i **ZMIEŃ** wartości produkcyjne:

```bash
cp .env.example .env
```

**Edytuj `.env`** i ustaw:

```bash
# KRYTYCZNE: Wygeneruj silny SECRET_KEY (min. 50 znaków)
SECRET_KEY=<wygeneruj-tutaj-silny-secret-key>

# Wyłącz DEBUG
DEBUG=False

# Ustaw domenę produkcyjną
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Ustaw silne hasło do bazy
DB_PASSWORD=<silne-haslo-postgres>

# Ustaw właściwe origins dla CORS/CSRF
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Frontend: użyj względnego URL (nginx proxy)
VITE_API_BASE_URL=/api
```

**WAŻNE:** Nigdy nie commituj pliku `.env` z produkcyjnymi sekretami do git!

### 2. Uruchomienie

```bash
# Build i uruchomienie w tle
docker compose -f docker-compose.prod.yml up -d --build
```

**Co się dzieje:**
- Budowane są produkcyjne obrazy z multi-stage Dockerfiles
- Backend używa gunicorn z 4 workers
- Frontend jest zbudowany statycznie i serwowany przez nginx w kontenerze
- Nginx (główny) działa jako reverse proxy:
  - `/` → frontend (static)
  - `/api` → backend (gunicorn)
  - `/admin` → backend admin
  - `/static` → Django static files
  - `/media` → Django media files
- Worker przetwarza jobs w tle
- PostgreSQL z właściwą konfiguracją haseł

### 3. Inicjalizacja (pierwszy raz)

```bash
# Migracje
docker exec timetracker_backend_prod python manage.py migrate

# Zbierz static files
docker exec timetracker_backend_prod python manage.py collectstatic --noinput

# Utwórz superusera
docker exec timetracker_backend_prod python manage.py createsuperuser
```

### 4. Dostęp

- **Aplikacja:** http://localhost (lub http://yourdomain.com)
- **Admin:** http://localhost/admin

**Nginx nasłuchuje na portach:**
- `80` - HTTP
- `443` - HTTPS (wymaga dodatkowej konfiguracji SSL)

### 5. Zarządzanie

```bash
# Status kontenerów
docker compose -f docker-compose.prod.yml ps

# Logi
docker compose -f docker-compose.prod.yml logs -f

# Restart konkretnego serwisu
docker compose -f docker-compose.prod.yml restart backend

# Zatrzymanie
docker compose -f docker-compose.prod.yml down

# Restart po zmianach w kodzie
docker compose -f docker-compose.prod.yml up -d --build
```

### 6. Backup bazy danych

```bash
# Eksport (backup)
docker exec timetracker_db_prod pg_dump -U timetracker timetracker > backup.sql

# Import (restore)
cat backup.sql | docker exec -i timetracker_db_prod psql -U timetracker timetracker
```

---

## Architektura Docker

### Development (`docker-compose.dev.yml`)

```
┌─────────────────────────────────────────────┐
│  Host Machine                               │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Frontend │  │ Backend  │  │   DB     │ │
│  │  :5173   │  │  :8000   │  │  :5432   │ │
│  └──────────┘  └──────────┘  └──────────┘ │
│       │              │              │       │
│  ┌──────────┐       │              │       │
│  │  Worker  │       │              │       │
│  │          │       │              │       │
│  └──────────┘       │              │       │
│                     │              │       │
│       Volumes (hot-reload):        │       │
│       ./backend → /app             │       │
│       ./frontend → /app            │       │
│                                    │       │
│       Volume: postgres_data_dev ───┘       │
└─────────────────────────────────────────────┘
```

**Cechy:**
- Porty wystawione na host dla łatwego dostępu
- Volumes dla live code reload
- Django `runserver` + Vite dev server
- PostgreSQL z `trust` auth dla wygody

### Production (`docker-compose.prod.yml`)

```
┌─────────────────────────────────────────────────┐
│  Host Machine                                   │
│                                                 │
│         :80, :443                               │
│             │                                   │
│        ┌────┴────┐                              │
│        │  Nginx  │  (reverse proxy)             │
│        └────┬────┘                              │
│             │                                   │
│     ┌───────┴───────┐                           │
│     │               │                           │
│ ┌───▼────┐    ┌────▼─────┐                     │
│ │Frontend│    │ Backend  │                     │
│ │ :80    │    │  :8000   │                     │
│ │(nginx) │    │(gunicorn)│                     │
│ └────────┘    └────┬─────┘                     │
│                    │                            │
│ ┌──────────┐       │      ┌──────────┐         │
│ │  Worker  │───────┼──────│   DB     │         │
│ │          │       │      │  :5432   │         │
│ └──────────┘       │      └──────────┘         │
│                    │            │               │
│      Network: timetracker_network              │
│                                 │               │
│      Volumes:                   │               │
│      - postgres_data_prod ──────┘               │
│      - static_files                             │
│      - media_files                              │
└─────────────────────────────────────────────────┘
```

**Cechy:**
- Tylko nginx wystawia porty na host (80, 443)
- Wszystkie serwisy w izolowanej sieci
- Frontend zbudowany statycznie (production build)
- Backend z gunicorn (4 workers)
- Worker uruchomiony jako daemon
- Nginx routuje `/api` → backend, `/` → frontend

---

## Troubleshooting

### Problem: Backend nie może połączyć się z bazą

**Rozwiązanie:**
- Sprawdź czy kontener `db` jest healthy: `docker compose ps`
- Sprawdź logi: `docker compose logs db`
- Upewnij się że `DB_HOST=db` w `.env` (nie `localhost`)

### Problem: Frontend nie może połączyć się z backend

**Dev:**
- Sprawdź `VITE_API_BASE_URL` w `.env` (powinno być `http://localhost:8000`)
- Sprawdź proxy w `vite.config.ts`

**Prod:**
- Sprawdź `VITE_API_BASE_URL` w `.env` (powinno być `/api`)
- Sprawdź logi nginx: `docker compose logs nginx`

### Problem: Błędy TypeScript podczas build frontend

**Rozwiązanie:**
- Sprawdź logi: `docker compose logs frontend`
- Napraw błędy TypeScript w kodzie
- Rebuild: `docker compose up --build frontend`

### Problem: Worker nie przetwarza jobów

**Rozwiązanie:**
- Sprawdź logi: `docker compose logs worker`
- Upewnij się że worker ma dostęp do bazy (ten sam `DB_HOST=db`)

### Problem: Powolny build na Windows

**Rozwiązanie:**
- Użyj WSL2 backend w Docker Desktop (Settings → General)
- Przenieś projekt do WSL filesystem
- Wyłącz antywirus skanujący Docker volumes

---

## Dodatkowe informacje

### Czyszczenie Docker

```bash
# Usuń nieużywane obrazy
docker image prune -a

# Usuń nieużywane volumes
docker volume prune

# Pełne czyszczenie (UWAGA: usuwa wszystko!)
docker system prune -a --volumes
```

### Aktualizacja dependencies

**Backend:**
```bash
# Edytuj backend/requirements.txt
# Rebuild:
docker compose -f docker-compose.dev.yml up --build backend
```

**Frontend:**
```bash
# Edytuj frontend/package.json
# Rebuild:
docker compose -f docker-compose.dev.yml up --build frontend
```

### SSL/HTTPS dla produkcji

Aby dodać HTTPS (Let's Encrypt):

1. Dodaj certbot do `docker-compose.prod.yml`
2. Zmień konfigurację nginx (`docker/nginx/default.conf`) aby obsługiwać SSL
3. Dodaj volumy dla certyfikatów

Przykład konfiguracji wykracza poza zakres MVP.

---

## Zgodność z AGENTS.md

Konfiguracja Docker jest zgodna z regułami projektu:
- PostgreSQL dla Docker (sekcja 9 AGENTS.md)
- Timezone: Europe/Warsaw (sekcja 11)
- Minimal dependencies (sekcja 5)
- Backend jako source of truth (sekcja 2)
