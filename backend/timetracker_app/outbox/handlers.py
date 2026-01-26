"""
Handler registry dla Outbox Pattern.

Mapuje job_type na funkcje obsługi. Każdy handler musi być idempotentny
(bezpieczny do wielokrotnego wykonania).
"""

import logging
from typing import Callable, Dict

from timetracker_app.models import OutboxJob

logger = logging.getLogger(__name__)


def handle_timesheet_day_saved(job: OutboxJob) -> None:
    """
    Handler dla TIMESHEET_DAY_SAVED.
    
    MVP: minimal implementation - tylko logowanie.
    W przyszłości może wykonywać projekcje, sync do zewnętrznych systemów, etc.
    
    Handler musi być idempotentny - wielokrotne wykonanie z tym samym jobem
    nie może powodować side effects lub błędów.
    
    Args:
        job: OutboxJob z payload zawierającym employee_id i date
    """
    employee_id = job.payload_json.get('employee_id')
    work_date = job.payload_json.get('date')
    
    logger.info(
        f"[TIMESHEET_DAY_SAVED] Processing job {job.id}: "
        f"employee_id={employee_id}, date={work_date}"
    )
    
    # MVP: tylko log, brak akcji
    # Przykładowe przyszłe akcje:
    # - aktualizacja projekcji miesięcznych
    # - sync do zewnętrznego systemu payroll
    # - wysłanie notyfikacji
    
    logger.info(f"[TIMESHEET_DAY_SAVED] Job {job.id} completed successfully")


# Registry mapujący job_type na handler functions
HANDLERS: Dict[str, Callable[[OutboxJob], None]] = {
    "TIMESHEET_DAY_SAVED": handle_timesheet_day_saved,
}


def dispatch_handler(job: OutboxJob) -> None:
    """
    Wywołuje odpowiedni handler dla danego job_type.
    
    Args:
        job: OutboxJob do przetworzenia
        
    Raises:
        ValueError: jeśli job_type nie ma zarejestrowanego handlera
    """
    handler = HANDLERS.get(job.job_type)
    
    if handler is None:
        raise ValueError(
            f"Unknown job_type: {job.job_type}. "
            f"Available handlers: {list(HANDLERS.keys())}"
        )
    
    logger.debug(f"Dispatching job {job.id} to handler: {handler.__name__}")
    handler(job)
