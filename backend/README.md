# TimeTracker Backend

Backend Django dla systemu TimeTracker.

## Konfiguracja bazy danych

### Local development (SQLite - domyślnie)

```bash
# Użyj SQLite (default, unika problemów z psycopg2 na Windows z non-UTF8 locale)
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Development z PostgreSQL w Docker

```bash
# 1. Uruchom tylko PostgreSQL
docker-compose -f docker-compose.dev.yml up -d db

# 2. Wyłącz SQLite, użyj PostgreSQL
$env:USE_SQLITE="False"  # PowerShell
# lub
export USE_SQLITE=False  # bash

# 3. Uruchom migracje
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Production (PostgreSQL w Docker)

Backend automatycznie używa PostgreSQL gdy `USE_SQLITE=False` lub brak zmiennej w środowisku kontenerowym.

```bash
docker-compose -f docker-compose.prod.yml up --build
```

## Uruchomienie testów

```bash
# Testy używają in-memory SQLite (szybkie)
python manage.py test
python manage.py test timetracker_app.tests.test_auth  # tylko testy auth
```

## Troubleshooting

### UnicodeDecodeError z psycopg2 na Windows

**Problem:** Na Windows z non-UTF8 locale (np. cp1251 ukraiński/rosyjski), psycopg2 może rzucać UnicodeDecodeError przy połączeniu z PostgreSQL.

**Rozwiązanie:** Użyj SQLite dla local development (domyślnie włączone).

**Alternatywy:**
1. Ustaw Windows locale na UTF-8 (wymaga restartu)
2. Użyj PostgreSQL w Docker (backend uruchamiany w kontenerze)
3. Ustaw `$env:PGCLIENTENCODING="UTF8"` przed uruchomieniem

## Struktura

- `config/` - Django settings i konfiguracja
- `timetracker_app/` - Główna aplikacja
  - `models.py` - Modele danych
  - `auth/` - Autentykacja (tokens, password flows)
  - `api/` - Endpointy REST API
  - `services/` - Logika biznesowa
  - `tests/` - Testy jednostkowe
  - `management/commands/` - Custom komendy Django

## Autentykacja

System używa **Option B: email + password** z admin-only provisioning.

**Flow:**
1. Admin tworzy Employee w Django admin
2. Admin generuje invite link (akcja w admin)
3. Employee ustawia hasło przez invite link (jednorazowy token)
4. Employee loguje się email+password (session cookies)

**Endpoints:**
- `POST /api/auth/login` - logowanie
- `POST /api/auth/logout` - wylogowanie
- `GET /api/me` - profil zalogowanego użytkownika
- `POST /api/auth/set-password` - ustawienie hasła z invite
- `POST /api/auth/password-reset/request` - żądanie resetu
- `POST /api/auth/password-reset/confirm` - potwierdzenie resetu

Zobacz: `AGENTS.md` dla szczegółów implementacji.
