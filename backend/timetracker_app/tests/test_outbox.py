"""
Testy dla Outbox Pattern - dispatcher, handlers, retry/backoff.

Testuje wszystkie aspekty worker mechanizmu:
- run_once() processing
- retry logic i backoff
- atomic locking dla wielu workerów
- handler idempotency
"""

from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time

from timetracker_app.models import OutboxJob
from timetracker_app.outbox.dispatcher import (
    enqueue,
    run_once,
    _calculate_backoff_delay,
    _try_lock_job,
    MAX_ATTEMPTS,
)
from timetracker_app.outbox.handlers import dispatch_handler, HANDLERS


class EnqueueTestCase(TestCase):
    """Testy dla funkcji enqueue() - idempotencja."""
    
    @freeze_time("2025-03-15 12:00:00")
    def test_enqueue_creates_new_job(self):
        """Test: enqueue tworzy nowy job gdy dedup_key nie istnieje."""
        job = enqueue(
            job_type="TIMESHEET_DAY_SAVED",
            dedup_key="timesheet:day_saved:123:2025-03-15",
            payload={"employee_id": 123, "date": "2025-03-15"}
        )
        
        self.assertIsNotNone(job.id)
        self.assertEqual(job.job_type, "TIMESHEET_DAY_SAVED")
        self.assertEqual(job.status, "PENDING")
        self.assertEqual(job.attempts, 0)
        self.assertIsNone(job.last_error)
    
    @freeze_time("2025-03-15 12:00:00")
    def test_enqueue_returns_existing_job(self):
        """Test: enqueue zwraca istniejący job gdy dedup_key już istnieje."""
        # Pierwszy enqueue
        job1 = enqueue(
            job_type="TIMESHEET_DAY_SAVED",
            dedup_key="timesheet:day_saved:123:2025-03-15",
            payload={"employee_id": 123, "date": "2025-03-15"}
        )
        
        # Drugi enqueue z tym samym dedup_key
        job2 = enqueue(
            job_type="TIMESHEET_DAY_SAVED",
            dedup_key="timesheet:day_saved:123:2025-03-15",
            payload={"employee_id": 123, "date": "2025-03-15", "extra": "data"}
        )
        
        # Powinien być ten sam job
        self.assertEqual(job1.id, job2.id)
        # Payload nie został nadpisany (MVP policy)
        self.assertNotIn("extra", job2.payload_json)
        # Tylko 1 job w DB
        self.assertEqual(OutboxJob.objects.count(), 1)


class BackoffTestCase(TestCase):
    """Testy dla logiki backoff."""
    
    def test_backoff_exponential_growth(self):
        """Test: backoff rośnie exponentially."""
        self.assertEqual(_calculate_backoff_delay(1), timedelta(seconds=2))
        self.assertEqual(_calculate_backoff_delay(2), timedelta(seconds=4))
        self.assertEqual(_calculate_backoff_delay(3), timedelta(seconds=8))
        self.assertEqual(_calculate_backoff_delay(4), timedelta(seconds=16))
        self.assertEqual(_calculate_backoff_delay(5), timedelta(seconds=32))
    
    def test_backoff_cap_at_300_seconds(self):
        """Test: backoff ma cap na 300 sekund."""
        # 2^8 = 256 < 300
        self.assertEqual(_calculate_backoff_delay(8), timedelta(seconds=256))
        # 2^9 = 512 > 300 -> cap
        self.assertEqual(_calculate_backoff_delay(9), timedelta(seconds=300))
        # 2^10 = 1024 > 300 -> cap
        self.assertEqual(_calculate_backoff_delay(10), timedelta(seconds=300))


class RunOnceTestCase(TestCase):
    """Testy dla funkcji run_once()."""
    
    @freeze_time("2025-03-15 12:00:00")
    def test_run_once_processes_eligible_jobs(self):
        """Test 1: run_once przetwarza eligible joby (PENDING, run_after <= now)."""
        # Utwórz 3 eligible joby
        for i in range(3):
            OutboxJob.objects.create(
                job_type="TIMESHEET_DAY_SAVED",
                dedup_key=f"test:job:{i}",
                payload_json={"test": i},
                status="PENDING",
                run_after=timezone.now() - timedelta(minutes=1),
                attempts=0
            )
        
        # Uruchom worker
        processed = run_once(max_jobs=10)
        
        # Wszystkie 3 powinny być przetworzone
        self.assertEqual(processed, 3)
        
        # Wszystkie joby DONE
        done_jobs = OutboxJob.objects.filter(status="DONE")
        self.assertEqual(done_jobs.count(), 3)
    
    @freeze_time("2025-03-15 12:00:00")
    def test_run_once_skips_future_jobs(self):
        """Test 2: run_once pomija joby z run_after > now."""
        # Job z przyszłą datą
        job = OutboxJob.objects.create(
            job_type="TIMESHEET_DAY_SAVED",
            dedup_key="test:future:job",
            payload_json={"test": "future"},
            status="PENDING",
            run_after=timezone.now() + timedelta(hours=1),
            attempts=0
        )
        
        # Uruchom worker
        processed = run_once(max_jobs=10)
        
        # Nie powinien być przetworzony
        self.assertEqual(processed, 0)
        
        # Job nadal PENDING
        job.refresh_from_db()
        self.assertEqual(job.status, "PENDING")
    
    @freeze_time("2025-03-15 12:00:00")
    def test_run_once_respects_max_jobs_limit(self):
        """Test: run_once respektuje limit max_jobs."""
        # Utwórz 10 jobów
        for i in range(10):
            OutboxJob.objects.create(
                job_type="TIMESHEET_DAY_SAVED",
                dedup_key=f"test:job:{i}",
                payload_json={"test": i},
                status="PENDING",
                run_after=timezone.now(),
                attempts=0
            )
        
        # Przetwórz maksymalnie 5
        processed = run_once(max_jobs=5)
        
        self.assertEqual(processed, 5)
        self.assertEqual(OutboxJob.objects.filter(status="DONE").count(), 5)
        self.assertEqual(OutboxJob.objects.filter(status="PENDING").count(), 5)


class HandlerFailureTestCase(TestCase):
    """Testy dla obsługi błędów handlera - retry logic."""
    
    @freeze_time("2025-03-15 12:00:00")
    @patch('timetracker_app.outbox.dispatcher.dispatch_handler')
    def test_handler_failure_schedules_retry(self, mock_dispatch):
        """Test 3: handler failure scheduluje retry z backoff."""
        # Mock handler rzuca wyjątek
        mock_dispatch.side_effect = RuntimeError("Test error")
        
        job = OutboxJob.objects.create(
            job_type="TIMESHEET_DAY_SAVED",
            dedup_key="test:fail:job",
            payload_json={"test": "fail"},
            status="PENDING",
            run_after=timezone.now(),
            attempts=0
        )
        
        # Uruchom worker
        processed = run_once(max_jobs=10)
        
        # Job został przetworzony (ale failnął)
        self.assertEqual(processed, 1)
        
        # Sprawdź job state po retry
        job.refresh_from_db()
        self.assertEqual(job.status, "PENDING")  # Scheduled for retry
        self.assertEqual(job.attempts, 1)  # Attempts incremented
        self.assertIsNotNone(job.last_error)  # Error recorded
        self.assertIn("RuntimeError", job.last_error)
        self.assertIn("Test error", job.last_error)
        
        # run_after powinno być w przyszłości (backoff)
        self.assertGreater(job.run_after, timezone.now())
        # Dla attempt=1, backoff=2 sekundy
        expected_run_after = timezone.now() + timedelta(seconds=2)
        self.assertAlmostEqual(
            job.run_after.timestamp(),
            expected_run_after.timestamp(),
            delta=1  # Allow 1 second tolerance
        )
    
    @freeze_time("2025-03-15 12:00:00")
    @patch('timetracker_app.outbox.dispatcher.dispatch_handler')
    def test_max_attempts_marks_failed(self, mock_dispatch):
        """Test 4: po MAX_ATTEMPTS job jest oznaczony jako FAILED."""
        mock_dispatch.side_effect = RuntimeError("Persistent error")
        
        # Job z attempts = MAX_ATTEMPTS - 1
        job = OutboxJob.objects.create(
            job_type="TIMESHEET_DAY_SAVED",
            dedup_key="test:max:attempts",
            payload_json={"test": "max"},
            status="PENDING",
            run_after=timezone.now(),
            attempts=MAX_ATTEMPTS - 1
        )
        
        # Uruchom worker (failnie po raz ostatni)
        processed = run_once(max_jobs=10)
        
        self.assertEqual(processed, 1)
        
        # Job powinien być FAILED
        job.refresh_from_db()
        self.assertEqual(job.status, "FAILED")
        self.assertEqual(job.attempts, MAX_ATTEMPTS)
        self.assertIsNotNone(job.last_error)


class ConcurrencyTestCase(TestCase):
    """Testy dla atomic locking - symulacja wielu workerów."""
    
    @freeze_time("2025-03-15 12:00:00")
    def test_concurrent_workers_no_double_processing(self):
        """Test 5: atomic lock zapobiega double-processing."""
        job = OutboxJob.objects.create(
            job_type="TIMESHEET_DAY_SAVED",
            dedup_key="test:concurrent:job",
            payload_json={"test": "concurrent"},
            status="PENDING",
            run_after=timezone.now(),
            attempts=0
        )
        
        # Worker 1 próbuje zablokować
        locked1 = _try_lock_job(job.id)
        self.assertTrue(locked1)
        
        # Worker 2 próbuje zablokować ten sam job
        locked2 = _try_lock_job(job.id)
        self.assertFalse(locked2)  # Nie powinien się udać
        
        # Sprawdź status joba
        job.refresh_from_db()
        self.assertEqual(job.status, "RUNNING")


class HandlerIdempotencyTestCase(TestCase):
    """Testy dla idempotencji handlera."""
    
    @freeze_time("2025-03-15 12:00:00")
    def test_handler_idempotent(self):
        """Test 6: handler można wywołać wielokrotnie bez side effects."""
        job = OutboxJob.objects.create(
            job_type="TIMESHEET_DAY_SAVED",
            dedup_key="test:idempotent:job",
            payload_json={"employee_id": 123, "date": "2025-03-15"},
            status="PENDING",
            run_after=timezone.now(),
            attempts=0
        )
        
        # Wywołaj handler 2 razy
        dispatch_handler(job)
        dispatch_handler(job)
        
        # Nie powinno rzucić wyjątku
        # MVP handler tylko loguje, więc brak side effects do sprawdzenia
        # W przyszłości można sprawdzić że projekcje są idempotentne
        
        # Podstawowa weryfikacja - handler nie crashuje
        self.assertTrue(True)
    
    def test_dispatch_handler_unknown_job_type(self):
        """Test: dispatch_handler rzuca ValueError dla nieznanego job_type."""
        job = OutboxJob.objects.create(
            job_type="UNKNOWN_JOB_TYPE",
            dedup_key="test:unknown",
            payload_json={},
            status="PENDING",
            run_after=timezone.now(),
            attempts=0
        )
        
        with self.assertRaises(ValueError) as cm:
            dispatch_handler(job)
        
        self.assertIn("Unknown job_type", str(cm.exception))


class HandlerRegistryTestCase(TestCase):
    """Testy dla handler registry."""
    
    def test_handlers_registry_has_timesheet_day_saved(self):
        """Test: registry zawiera handler dla TIMESHEET_DAY_SAVED."""
        self.assertIn("TIMESHEET_DAY_SAVED", HANDLERS)
        self.assertIsNotNone(HANDLERS["TIMESHEET_DAY_SAVED"])
    
    @freeze_time("2025-03-15 12:00:00")
    def test_timesheet_day_saved_handler_runs(self):
        """Test: handler TIMESHEET_DAY_SAVED działa bez błędów."""
        job = OutboxJob.objects.create(
            job_type="TIMESHEET_DAY_SAVED",
            dedup_key="test:handler:run",
            payload_json={"employee_id": 123, "date": "2025-03-15"},
            status="PENDING",
            run_after=timezone.now(),
            attempts=0
        )
        
        # Powinno działać bez błędów
        handler = HANDLERS["TIMESHEET_DAY_SAVED"]
        handler(job)
        
        # No crash = success dla MVP


class IntegrationTestCase(TestCase):
    """Testy integracyjne - pełny flow od enqueue do completion."""
    
    @freeze_time("2025-03-15 12:00:00")
    def test_full_flow_enqueue_to_done(self):
        """Test integracyjny: enqueue -> run_once -> DONE."""
        # Enqueue job
        job = enqueue(
            job_type="TIMESHEET_DAY_SAVED",
            dedup_key="test:integration:123:2025-03-15",
            payload={"employee_id": 123, "date": "2025-03-15"}
        )
        
        # Sprawdź initial state
        self.assertEqual(job.status, "PENDING")
        self.assertEqual(job.attempts, 0)
        
        # Przetwórz
        processed = run_once(max_jobs=10)
        
        self.assertEqual(processed, 1)
        
        # Sprawdź final state
        job.refresh_from_db()
        self.assertEqual(job.status, "DONE")
        self.assertEqual(job.attempts, 0)  # Success nie inkrementuje attempts
    
    @freeze_time("2025-03-15 12:00:00")
    def test_full_flow_with_retry(self):
        """Test integracyjny: enqueue -> fail -> retry -> success."""
        # Mock handler: fail pierwszym razem, success drugim razem
        call_count = {'count': 0}
        
        def side_effect_fn(job):
            call_count['count'] += 1
            if call_count['count'] == 1:
                raise RuntimeError("Temporary error")
            # Drugi raz: success (no exception)
        
        # Enqueue job
        job = enqueue(
            job_type="TIMESHEET_DAY_SAVED",
            dedup_key="test:retry:flow",
            payload={"test": "retry"}
        )
        
        with patch('timetracker_app.outbox.dispatcher.dispatch_handler', side_effect=side_effect_fn):
            # Pierwsza próba: fail
            processed1 = run_once(max_jobs=10)
            self.assertEqual(processed1, 1)
            
            job.refresh_from_db()
            self.assertEqual(job.status, "PENDING")
            self.assertEqual(job.attempts, 1)
            
            # Przesuń czas do run_after (backoff 2 sekundy)
            with freeze_time("2025-03-15 12:00:03"):
                # Druga próba: success
                processed2 = run_once(max_jobs=10)
                self.assertEqual(processed2, 1)
                
                job.refresh_from_db()
                self.assertEqual(job.status, "DONE")
