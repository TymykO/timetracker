"""
Outbox Dispatcher - mechanizm enqueuowania i przetwarzania asynchronicznych jobów.

Implementuje Outbox Pattern dla idempotentnego przetwarzania zdarzeń.
"""

import logging
import time
import traceback
from datetime import timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

from timetracker_app.models import OutboxJob
from timetracker_app.outbox.handlers import dispatch_handler

logger = logging.getLogger(__name__)

# Konfiguracja retry policy
MAX_ATTEMPTS = 10
BACKOFF_CAP_SECONDS = 300  # 5 minut

# Flag dla graceful shutdown
_shutdown_requested = False


def enqueue(job_type: str, dedup_key: str, payload: dict) -> OutboxJob:
    """
    Kolejkuje job do outbox.
    
    Idempotencja: jeśli job z danym dedup_key już istnieje, zwraca istniejący
    zamiast tworzyć duplikat. Dzięki temu wielokrotne wywołanie enqueue
    z tym samym dedup_key nie utworzy wielu jobów.
    
    MVP policy: nie nadpisujemy payload jeśli job już istnieje - zwracamy
    istniejący job bez zmian. W przyszłości można rozważyć update payload
    jeśli job jest PENDING.
    
    Args:
        job_type: Typ jobu, np. "TIMESHEET_DAY_SAVED"
        dedup_key: Unikalny klucz deduplikacji, np. "timesheet:day_saved:123:2025-03-15"
        payload: Dict z danymi jobu (będzie zapisany jako JSON)
        
    Returns:
        OutboxJob (nowy lub istniejący)
    """
    job, created = OutboxJob.objects.get_or_create(
        dedup_key=dedup_key,
        defaults={
            'job_type': job_type,
            'payload_json': payload,
            'status': 'PENDING',
            'run_after': timezone.now(),
            'attempts': 0,
        }
    )
    
    return job


def _calculate_backoff_delay(attempts: int) -> timedelta:
    """
    Oblicza delay dla retry zgodnie z exponential backoff.
    
    Formula: min(BACKOFF_CAP_SECONDS, 2^attempts) sekund
    
    Przykłady:
    - attempt 1: 2 sekundy
    - attempt 2: 4 sekundy
    - attempt 3: 8 sekund
    - attempt 4: 16 sekund
    - attempt 5: 32 sekundy
    - attempt 6: 64 sekundy
    - attempt 7: 128 sekund
    - attempt 8+: 300 sekund (cap)
    
    Args:
        attempts: liczba prób (przed następną próbą)
        
    Returns:
        timedelta z delay
    """
    delay_seconds = min(BACKOFF_CAP_SECONDS, 2 ** attempts)
    return timedelta(seconds=delay_seconds)


def _try_lock_job(job_id: int) -> bool:
    """
    Próbuje zablokować job do przetwarzania (atomic transition PENDING -> RUNNING).
    
    Używa optymistic locking: UPDATE z warunkiem na status.
    Jeśli inny worker już wziął job, update nie zmieni żadnych wierszy.
    
    Args:
        job_id: ID joba do zablokowania
        
    Returns:
        True jeśli lock się udał, False jeśli job był już wzięty przez innego workera
    """
    rows_updated = OutboxJob.objects.filter(
        id=job_id,
        status='PENDING'
    ).update(
        status='RUNNING',
        updated_at=timezone.now()
    )
    
    return rows_updated > 0


def _mark_job_done(job: OutboxJob) -> None:
    """
    Oznacza job jako zakończony pomyślnie.
    
    Args:
        job: OutboxJob do oznaczenia
    """
    job.status = 'DONE'
    job.save(update_fields=['status', 'updated_at'])
    logger.info(f"Job {job.id} ({job.job_type}) marked as DONE")


def _schedule_retry(job: OutboxJob, error_message: str) -> None:
    """
    Zaplanuj retry joba po błędzie.
    
    Inkrementuje attempts, zapisuje błąd, ustawia run_after z backoff delay.
    Jeśli przekroczono MAX_ATTEMPTS, oznacza job jako FAILED.
    
    Args:
        job: OutboxJob który failnął
        error_message: treść błędu do zapisania w last_error
    """
    job.attempts += 1
    job.last_error = error_message
    
    if job.attempts >= MAX_ATTEMPTS:
        job.status = 'FAILED'
        job.save(update_fields=['status', 'attempts', 'last_error', 'updated_at'])
        logger.error(
            f"Job {job.id} ({job.job_type}) marked as FAILED "
            f"after {job.attempts} attempts. Last error: {error_message[:200]}"
        )
    else:
        backoff_delay = _calculate_backoff_delay(job.attempts)
        job.status = 'PENDING'
        job.run_after = timezone.now() + backoff_delay
        job.save(update_fields=['status', 'attempts', 'run_after', 'last_error', 'updated_at'])
        logger.warning(
            f"Job {job.id} ({job.job_type}) failed (attempt {job.attempts}/{MAX_ATTEMPTS}). "
            f"Scheduled retry after {backoff_delay.total_seconds()}s. "
            f"Error: {error_message[:200]}"
        )


def _process_job(job: OutboxJob) -> bool:
    """
    Przetwarza pojedynczy job.
    
    Workflow:
    1. Próbuje zablokować job (atomic PENDING->RUNNING)
    2. Jeśli lock się udał, wywołuje handler
    3. Sukces -> DONE, błąd -> retry logic
    
    Args:
        job: OutboxJob do przetworzenia
        
    Returns:
        True jeśli job został przetworzony (niezależnie od wyniku),
        False jeśli job był już wzięty przez innego workera
    """
    # Próba atomic lock
    if not _try_lock_job(job.id):
        logger.debug(f"Job {job.id} already locked by another worker, skipping")
        return False
    
    # Odśwież job z bazy (mamy już lock, ale chcemy fresh data)
    job.refresh_from_db()
    
    logger.info(f"Processing job {job.id} ({job.job_type}), attempt {job.attempts + 1}")
    
    try:
        # Wywołaj handler
        dispatch_handler(job)
        
        # Sukces -> DONE
        _mark_job_done(job)
        return True
        
    except Exception as e:
        # Błąd -> schedule retry
        error_message = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        _schedule_retry(job, error_message)
        return True


def run_once(max_jobs: int = 50) -> int:
    """
    Wykonuje jeden tick przetwarzania: pobiera eligible joby i przetwarza je.
    
    Eligible joby to:
    - status=PENDING
    - run_after <= now
    
    Workflow:
    1. Query eligible jobs (order by run_after, limit max_jobs)
    2. Dla każdego joba:
       - próbuj zablokować (atomic)
       - jeśli się uda, przetwórz
    3. Return liczba przetworzonych jobów
    
    Bezpieczne dla wielu workerów: atomic locking zapobiega double-processing.
    
    Args:
        max_jobs: maksymalna liczba jobów do przetworzenia w jednym tick
        
    Returns:
        liczba przetworzonych jobów
    """
    now = timezone.now()
    
    # Query eligible jobs
    eligible_jobs = OutboxJob.objects.filter(
        status='PENDING',
        run_after__lte=now
    ).order_by('run_after')[:max_jobs]
    
    if not eligible_jobs:
        logger.debug("No eligible jobs to process")
        return 0
    
    logger.info(f"Found {len(eligible_jobs)} eligible jobs to process")
    
    processed_count = 0
    for job in eligible_jobs:
        # _process_job zwraca True jeśli job został przetworzony lub wzięty przez nas
        # (niezależnie od wyniku handlera)
        if _process_job(job):
            processed_count += 1
    
    logger.info(f"Processed {processed_count} jobs in this tick")
    return processed_count


def request_shutdown() -> None:
    """
    Ustawia flag shutdown dla graceful shutdown.
    
    Wywoływana przez signal handler (SIGTERM, SIGINT).
    Worker zakończy się po dokończeniu obecnego batch.
    """
    global _shutdown_requested
    _shutdown_requested = True
    logger.info("Shutdown requested, will stop after current batch")


def is_shutdown_requested() -> bool:
    """
    Sprawdza czy shutdown został zażądany.
    
    Returns:
        True jeśli shutdown requested
    """
    return _shutdown_requested


def run_forever(poll_seconds: float = 2.0, max_jobs_per_tick: int = 50) -> None:
    """
    Uruchamia worker loop - nieskończona pętla przetwarzania jobów.
    
    Loop wykonuje run_once() w odstępach poll_seconds. Jeśli nie ma jobów do
    przetworzenia (run_once() zwróciło 0), czeka poll_seconds przed następnym tick.
    
    Graceful shutdown: sprawdza flag _shutdown_requested po każdym tick.
    Aby zatrzymać worker, wywołaj request_shutdown() z signal handlera.
    
    Args:
        poll_seconds: czas oczekiwania między tickami gdy brak jobów (sekundy)
        max_jobs_per_tick: maksymalna liczba jobów do przetworzenia w jednym tick
    """
    global _shutdown_requested
    
    logger.info(
        f"Starting worker loop (poll_seconds={poll_seconds}, "
        f"max_jobs_per_tick={max_jobs_per_tick})"
    )
    
    try:
        while not _shutdown_requested:
            try:
                processed = run_once(max_jobs=max_jobs_per_tick)
                
                # Jeśli nie było jobów, czekaj przed następnym tick
                if processed == 0:
                    time.sleep(poll_seconds)
                # Jeśli były joby, natychmiast sprawdź czy są kolejne
                # (ale daj chwilę na odświeżenie DB connections)
                else:
                    time.sleep(0.1)
                    
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt received, shutting down gracefully")
                break
                
            except Exception as e:
                # Błąd w worker loop (nie w handlerze konkretnego joba)
                # Loguj i kontynuuj - nie chcemy zatrzymać workera przez jeden błąd
                logger.error(
                    f"Error in worker loop: {type(e).__name__}: {str(e)}\n"
                    f"{traceback.format_exc()}"
                )
                # Czekaj przed retry loop
                time.sleep(poll_seconds)
    
    finally:
        logger.info("Worker loop stopped")
        # Reset flag dla testów
        _shutdown_requested = False
