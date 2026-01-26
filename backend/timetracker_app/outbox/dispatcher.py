"""
Outbox Dispatcher - mechanizm enqueuowania i przetwarzania asynchronicznych jobów.

Implementuje Outbox Pattern dla idempotentnego przetwarzania zdarzeń.
MVP: tylko enqueue, run_once i run_forever będą dodane później.
"""

from django.utils import timezone
from timetracker_app.models import OutboxJob


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
