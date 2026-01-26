# Stage base: dla development
FROM python:3.12-slim as base

# Ustaw zmienne środowiskowe
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Ustaw working directory
WORKDIR /app

# Zainstaluj system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Skopiuj requirements i zainstaluj Python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj kod aplikacji
COPY backend/ /app/

# CMD dla worker
CMD ["python", "manage.py", "worker_run"]

# Stage production: dla produkcji
FROM base as production

# CMD pozostaje taki sam dla produkcji
CMD ["python", "manage.py", "worker_run"]
