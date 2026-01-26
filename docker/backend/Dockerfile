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

# Expose port
EXPOSE 8000

# Domyślne CMD dla development
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Stage production: dla produkcji z gunicorn
FROM base as production

# Zbierz static files (wymaga settings.py z STATIC_ROOT)
RUN python manage.py collectstatic --noinput || true

# CMD dla produkcji - gunicorn
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "60"]
