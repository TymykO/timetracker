# TimeTracker — AGENTS (DOCKER)

> Scope: `docker/` — Dockerfiles, nginx configs, and containerization strategy.  
> This file complements `../AGENTS.md` (root). Root rules still apply.

---

## 0) Docker architecture goals

This directory contains:
- **Dockerfiles** for each service (backend, frontend, worker, nginx)
- **nginx configs** for production reverse proxy and SPA routing
- Multi-stage builds for development and production environments

**Key principles:**
- Development: hot-reload, exposed ports, volume mounts for live code changes
- Production: optimized builds, isolated network, nginx reverse proxy
- All services use consistent base images and patterns

---

## 1) Services overview

### Backend (Django)
- **Dockerfile**: `docker/backend/Dockerfile`
- **Base image**: `python:3.12-slim`
- **Stages**:
  - `base`: Development stage with Django dev server
  - `production`: Production stage with gunicorn (4 workers)
- **Port**: 8000
- **Command**:
  - Dev: `python manage.py runserver 0.0.0.0:8000`
  - Prod: `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4`

### Frontend (React + Vite)
- **Dockerfile**: `docker/frontend/Dockerfile`
- **Base image**: `node:20-alpine`
- **Stages**:
  - `development`: Vite dev server with hot-reload
  - `builder`: Builds static production bundle
  - `production`: nginx:alpine serving static files
- **Port**: 
  - Dev: 5173 (Vite)
  - Prod: 80 (nginx)
- **Command**:
  - Dev: `npm run dev -- --host 0.0.0.0`
  - Prod: `nginx -g "daemon off;"`

### Worker (Django management command)
- **Dockerfile**: `docker/worker/Dockerfile`
- **Base image**: Same as backend (`python:3.12-slim`)
- **Command**: `python manage.py worker_run`
- **No exposed ports**: Internal service only

### Nginx (Production reverse proxy)
- **Dockerfile**: `docker/nginx/Dockerfile`
- **Config**: `docker/nginx/default.conf`
- **Base image**: `nginx:alpine`
- **Port**: 80, 443
- **Routes**:
  - `/` → frontend (static files)
  - `/api` → backend (gunicorn)
  - `/admin` → backend admin
  - `/static` → Django static files
  - `/media` → Django media files

---

## 2) Environment variables per service

### Backend & Worker
Required:
- `DEBUG`: True/False
- `SECRET_KEY`: Django secret key (generate strong key for prod)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DB_ENGINE`: `django.db.backends.postgresql`
- `DB_NAME`: Database name
- `DB_USER`: Database user
- `DB_PASSWORD`: Database password
- `DB_HOST`: `db` (service name in docker-compose)
- `DB_PORT`: `5432`
- `CSRF_TRUSTED_ORIGINS`: Comma-separated CSRF origins
- `CORS_ALLOWED_ORIGINS`: Comma-separated CORS origins
- `USE_SQLITE`: Set to "False" in Docker (use PostgreSQL)

Optional:
- `ALLOWED_HOSTS`: Default `*` in dev

### Frontend
Required:
- `VITE_API_BASE_URL`: Backend API URL
  - Dev: `http://localhost:8000/api`
  - Prod: `/api` (relative, nginx proxy)

### Database (PostgreSQL)
Required:
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password

Dev-specific:
- `POSTGRES_HOST_AUTH_METHOD`: Set to `trust` in dev (no password needed)

---

## 3) Build stages explained

### Backend multi-stage
```dockerfile
# Stage: base (development)
FROM python:3.12-slim as base
- Install postgresql-client
- Install Python dependencies from requirements.txt
- Copy backend code
- CMD: runserver

# Stage: production
FROM base as production
- Run collectstatic
- CMD: gunicorn with 4 workers
```

**Dev target**: Default `base` stage (hot-reload via volume mount)  
**Prod target**: `production` stage (optimized, no volumes)

### Frontend multi-stage
```dockerfile
# Stage: development
FROM node:20-alpine as development
- Install npm dependencies
- Copy frontend code
- CMD: vite dev server

# Stage: builder
FROM node:20-alpine as builder
- Install dependencies
- Build production bundle (npm run build)
- Output: /app/dist

# Stage: production
FROM nginx:alpine as production
- Copy built files from builder
- Copy nginx.conf for SPA routing
- CMD: nginx
```

**Dev target**: `development` stage (Vite dev server)  
**Prod target**: `production` stage (nginx serving static bundle)

### Worker
- Uses same Dockerfile as backend
- No separate stages needed
- Runs `worker_run` management command

---

## 4) Volume mount strategy

### Development
**Backend & Worker:**
```yaml
volumes:
  - ./backend:/app
```
- Mounts local `backend/` to `/app` in container
- Enables hot-reload (Django auto-restarts on file changes)
- No need to rebuild on code changes

**Frontend:**
```yaml
volumes:
  - ./frontend:/app
  - /app/node_modules  # Named volume to prevent host override
```
- Mounts local `frontend/` to `/app` in container
- Vite watches for changes and hot-reloads
- `node_modules` as named volume prevents host override (faster on Windows/Mac)

**Database:**
```yaml
volumes:
  - postgres_data_dev:/var/lib/postgresql/data
```
- Named volume for persistent database storage
- Data survives container restarts

### Production
**No code volumes**: Code is baked into images at build time  
**Only data volumes**: Database, static files, media files

---

## 5) nginx configuration

### Frontend nginx config (`docker/frontend/nginx.conf`)
- **Purpose**: Enable SPA client-side routing
- **Key feature**: `try_files $uri $uri/ /index.html;`
  - All routes (e.g., `/day/2025-03-15`) fallback to `index.html`
  - React Router handles routing client-side

### Main nginx config (`docker/nginx/default.conf`)
- **Purpose**: Reverse proxy for production
- **Routes**:
  ```nginx
  location / {
    proxy_pass http://frontend:80;
  }
  
  location /api {
    proxy_pass http://backend:8000;
  }
  
  location /admin {
    proxy_pass http://backend:8000;
  }
  
  location /static {
    alias /app/staticfiles;
  }
  
  location /media {
    alias /app/media;
  }
  ```
- **Headers**: Proxy headers for CORS, CSRF, session cookies

---

## 6) Dev vs Prod differences

| Aspect | Development | Production |
|--------|-------------|------------|
| **Backend** | Django runserver | gunicorn (4 workers) |
| **Frontend** | Vite dev server | nginx with static bundle |
| **Database auth** | trust (no password) | password required |
| **Ports exposed** | All services | Only nginx (80, 443) |
| **Volumes** | Code mounted (hot-reload) | No code volumes (baked in) |
| **Network** | Ports exposed to host | Isolated network |
| **DEBUG** | True | False |
| **SECRET_KEY** | Weak default | Strong generated key |
| **ALLOWED_HOSTS** | `*` | Specific domains |

---

## 7) Networking

### Development (`docker-compose.dev.yml`)
- **Network**: Default bridge network
- **Service discovery**: By service name (`db`, `backend`, `frontend`, `worker`)
- **Ports exposed to host**: All services
  - db: 5432
  - backend: 8000
  - frontend: 5173

### Production (`docker-compose.prod.yml`)
- **Network**: Custom `timetracker_network`
- **Service discovery**: By service name
- **Only nginx exposed**: Ports 80, 443
- **Internal services**: Not directly accessible from host

---

## 8) Healthchecks

### Database
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U timetracker"]
  interval: 5s
  timeout: 5s
  retries: 5
```
- Backend waits for `db` to be healthy before starting
- Worker waits for `db` to be healthy before starting

### Backend & Frontend
- No explicit healthchecks defined in MVP
- Can add `curl` checks if needed for production monitoring

---

## 9) Build optimization tips

### Backend
- **Minimize layers**: Combine RUN commands
- **Use `.dockerignore`**: Exclude `.git`, `__pycache__`, `*.pyc`
- **Cache dependencies**: `requirements.txt` copied before code (cache layer)
- **Small base image**: `python:3.12-slim` (not full `python:3.12`)

### Frontend
- **Multi-stage**: Separate builder and production stages
- **Small production image**: nginx:alpine (no Node runtime)
- **Cache npm install**: `package*.json` copied before code
- **Named volume for node_modules**: Speeds up dev rebuilds

---

## 10) Security considerations

### Development
- `POSTGRES_HOST_AUTH_METHOD: trust` — **NEVER use in production**
- Weak `SECRET_KEY` defaults — **Change for production**
- `ALLOWED_HOSTS: *` — **Restrict in production**

### Production
- **Strong SECRET_KEY**: Minimum 50 characters, random
- **Database passwords**: Use strong passwords, store in secrets
- **ALLOWED_HOSTS**: Specific domains only
- **HTTPS**: Add SSL/TLS termination (nginx with Let's Encrypt)
- **No DEBUG**: Set `DEBUG=False`
- **Read-only containers**: Use `read_only: true` where possible (future)

---

## 11) Common tasks

### Rebuild specific service
```bash
# Dev
docker compose -f docker-compose.dev.yml up --build backend

# Prod
docker compose -f docker-compose.prod.yml up -d --build backend
```

### Run migrations
```bash
# Dev
docker exec timetracker_backend_dev python manage.py migrate

# Prod
docker exec timetracker_backend_prod python manage.py migrate
```

### Access container shell
```bash
# Backend
docker exec -it timetracker_backend_dev bash

# Database
docker exec -it timetracker_db_dev psql -U timetracker -d timetracker
```

### View logs
```bash
# All services
docker compose -f docker-compose.dev.yml logs -f

# Specific service
docker compose -f docker-compose.dev.yml logs -f backend
```

---

## 12) Troubleshooting

### Backend can't connect to database
- **Check**: `DB_HOST=db` (not `localhost`)
- **Check**: `db` service is healthy (`docker compose ps`)
- **Check**: Database credentials match in both services

### Frontend can't reach backend
- **Dev**: Check `VITE_API_BASE_URL=http://localhost:8000/api`
- **Prod**: Check `VITE_API_BASE_URL=/api` (relative)
- **Dev**: Ensure backend is running (`docker compose ps`)

### Volume mount issues on Windows
- **Use WSL2 backend**: Docker Desktop → Settings → General → WSL2
- **Move project to WSL**: Better performance
- **Disable antivirus**: Exclude Docker volumes from scanning

### node_modules not found (frontend)
- **Named volume**: Check `- /app/node_modules` in compose file
- **Rebuild**: `docker compose up --build frontend`

---

## 13) Future improvements (not MVP)

- **HTTPS/SSL**: Add Let's Encrypt certbot integration
- **Container scanning**: Trivy or Snyk for security scanning
- **Health endpoints**: `/health` endpoints for monitoring
- **Logging**: Centralized logging (ELK, Loki, or cloud logging)
- **Secrets management**: Docker secrets or external secrets manager
- **CI/CD**: Automated build and deploy pipelines

---

## 14) Compliance with root AGENTS.md

This Docker setup follows root AGENTS.md principles:
- **Backend as source of truth** (Section 2)
- **Minimal dependencies** (Section 5)
- **PostgreSQL for Docker** (Section 9)
- **Europe/Warsaw timezone** (Section 11)
- **Session cookie security** (backend/AGENTS.md Section 9)
