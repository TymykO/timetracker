# Outbox Worker - Dokumentacja

## Przegląd

Outbox Worker przetwarza asynchroniczne joby z tabeli `OutboxJob` używając Outbox Pattern. 
Worker działa jako osobny proces, który:
- Pobiera joby z bazy danych
- Wykonuje zarejestrowane handlery
- Implementuje retry/backoff przy błędach
- Zapewnia idempotencję i bezpieczeństwo dla wielu workerów

## Uruchomienie

### Development (lokalne)

```bash
# Uruchom worker w trybie dev
python manage.py worker_run

# Z custom parametrami
python manage.py worker_run --poll-seconds 5 --max-jobs 100
```

### Docker

```bash
# Uruchom worker w Docker Compose
docker compose -f docker-compose.dev.yml up worker

# Sprawdź logi
docker compose -f docker-compose.dev.yml logs -f worker
```

### Parametry CLI

- `--poll-seconds` (default: 2.0) - czas oczekiwania między tickami gdy brak jobów
- `--max-jobs` (default: 50) - maksymalna liczba jobów przetwarzanych w jednym tick

## Graceful Shutdown

Worker obsługuje sygnały dla bezpiecznego zatrzymania:

```bash
# SIGTERM (preferowane)
kill -TERM <pid>

# SIGINT (Ctrl+C)
# Naciśnij Ctrl+C w terminalu
```

Worker dokończy obecny batch jobów przed zatrzymaniem.

## Jak działa

### 1. Enqueue

Serwisy dodają joby do kolejki:

```python
from timetracker_app.outbox import enqueue

# Enqueue job
job = enqueue(
    job_type="TIMESHEET_DAY_SAVED",
    dedup_key=f"timesheet:day_saved:{employee_id}:{date}",
    payload={
        "employee_id": employee_id,
        "date": str(date),
    }
)
```

### 2. Worker Processing

Worker:
1. Pobiera joby z `status=PENDING` i `run_after <= now`
2. Blokuje job atomowo (optimistic locking)
3. Wywołuje handler
4. Sukces → `status=DONE`
5. Błąd → retry z exponential backoff

### 3. Retry Policy

- **Max attempts**: 10
- **Backoff**: Exponential, cap 5min
  - Attempt 1: 2s
  - Attempt 2: 4s
  - Attempt 3: 8s
  - Attempt 4: 16s
  - Attempt 5: 32s
  - Attempt 6: 64s
  - Attempt 7: 128s
  - Attempt 8+: 300s (cap)
- Po 10 próbach: `status=FAILED` (permanent)

### 4. Atomic Locking

Worker używa atomic UPDATE dla lock:

```sql
UPDATE outbox_job 
SET status='RUNNING' 
WHERE id=X AND status='PENDING'
```

Jeśli inny worker wziął job, UPDATE zwróci 0 rows → skip.
Bezpieczne dla wielu instancji workera.

## Dodawanie nowych handlerów

### 1. Zdefiniuj handler w `handlers.py`

```python
def handle_my_job(job: OutboxJob) -> None:
    """
    Handler musi być idempotentny - bezpieczny do wielokrotnego wykonania.
    """
    data = job.payload_json
    # ... wykonaj akcje ...
    logger.info(f"Handler completed for job {job.id}")
```

### 2. Zarejestruj w HANDLERS

```python
HANDLERS = {
    "TIMESHEET_DAY_SAVED": handle_timesheet_day_saved,
    "MY_JOB": handle_my_job,  # Dodaj tutaj
}
```

### 3. Enqueue w serwisie

```python
enqueue(
    job_type="MY_JOB",
    dedup_key=f"my_job:{unique_id}",
    payload={"data": "..."}
)
```

## Monitoring

### Sprawdzenie stanu jobów

```python
from timetracker_app.models import OutboxJob

# Pending jobs
pending = OutboxJob.objects.filter(status='PENDING').count()

# Failed jobs (wymagają interwencji)
failed = OutboxJob.objects.filter(status='FAILED')

# Retry backoff
retrying = OutboxJob.objects.filter(
    status='PENDING',
    attempts__gt=0
)
```

### Django Admin

Dodaj `OutboxJob` do admin.py dla ręcznego monitoringu:

```python
@admin.register(OutboxJob)
class OutboxJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'job_type', 'status', 'attempts', 'run_after', 'created_at']
    list_filter = ['status', 'job_type']
    search_fields = ['dedup_key']
    readonly_fields = ['created_at', 'updated_at']
```

## Testy

```bash
# Wszystkie testy outbox
python manage.py test timetracker_app.tests.test_outbox

# Test manualny
python test_worker_manual.py
```

## Troubleshooting

### Job stuck w RUNNING

Jeśli worker crashnął podczas przetwarzania, job może zostać w `RUNNING`.
Rozwiązanie: ręcznie ustaw `status=PENDING` w admin.

### Too many FAILED jobs

Sprawdź `last_error` w failed jobs. Jeśli systematyczny błąd:
1. Napraw kod handlera
2. Reset jobów: `UPDATE outbox_job SET status='PENDING', attempts=0 WHERE status='FAILED'`

### Worker nie przetwarza jobów

Sprawdź:
1. Worker działa? (`ps aux | grep worker_run`)
2. Logi workera (`docker logs` lub console output)
3. `run_after` nie jest w przyszłości?
4. Błędy w handlerze? (sprawdź `last_error`)

## Best Practices

1. **Idempotencja**: Handlerry muszą być bezpieczne do wielokrotnego wykonania
2. **Dedup keys**: Używaj unikalnych, deterministycznych kluczy
3. **Payload size**: Trzymaj payload mały (<1KB idealnie)
4. **Transaction safety**: Enqueue w tej samej transakcji co główna operacja
5. **Monitoring**: Regularnie sprawdzaj FAILED jobs
6. **Graceful shutdown**: Zawsze używaj SIGTERM, nie SIGKILL

## Przykład: Debug pojedynczego joba

```python
from timetracker_app.models import OutboxJob
from timetracker_app.outbox.handlers import dispatch_handler

# Znajdź job
job = OutboxJob.objects.get(id=123)

# Ręcznie wywołaj handler (development only!)
try:
    dispatch_handler(job)
    print("Handler succeeded")
except Exception as e:
    print(f"Handler failed: {e}")
```

## Performance

- **SQLite**: OK dla dev, problemy przy >1 worker
- **PostgreSQL**: Zalecane dla production, świetne dla wielu workerów
- **Throughput**: ~50 jobs/sec (zależy od złożoności handlerów)
- **Latency**: 2-5s dla nowych jobów (poll interval)
