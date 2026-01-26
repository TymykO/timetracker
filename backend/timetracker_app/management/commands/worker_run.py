"""
Management command dla uruchomienia Outbox Worker.

Usage:
    python manage.py worker_run
    python manage.py worker_run --poll-seconds 5 --max-jobs 100

Graceful shutdown:
    kill -TERM <pid>  # SIGTERM
    Ctrl+C            # SIGINT
"""

import signal
import sys

from django.core.management.base import BaseCommand

from timetracker_app.outbox.dispatcher import run_forever, request_shutdown


class Command(BaseCommand):
    help = "Uruchamia Outbox Worker - przetwarza asynchroniczne joby z OutboxJob"
    
    def add_arguments(self, parser):
        """Dodaje argumenty CLI."""
        parser.add_argument(
            '--poll-seconds',
            type=float,
            default=2.0,
            help='Czas oczekiwania między tickami gdy brak jobów (domyślnie: 2.0s)'
        )
        parser.add_argument(
            '--max-jobs',
            type=int,
            default=50,
            help='Maksymalna liczba jobów do przetworzenia w jednym tick (domyślnie: 50)'
        )
    
    def handle(self, *args, **options):
        """Główna logika command."""
        poll_seconds = options['poll_seconds']
        max_jobs = options['max_jobs']
        
        self.stdout.write(self.style.SUCCESS(
            f"Starting Outbox Worker "
            f"(poll_seconds={poll_seconds}, max_jobs={max_jobs})"
        ))
        
        # Setup signal handlers dla graceful shutdown
        def handle_shutdown_signal(signum, frame):
            """Handler dla SIGTERM i SIGINT."""
            signal_name = signal.Signals(signum).name
            self.stdout.write(self.style.WARNING(
                f"\n{signal_name} received, initiating graceful shutdown..."
            ))
            request_shutdown()
        
        signal.signal(signal.SIGTERM, handle_shutdown_signal)
        signal.signal(signal.SIGINT, handle_shutdown_signal)
        
        try:
            # Uruchom worker loop
            run_forever(
                poll_seconds=poll_seconds,
                max_jobs_per_tick=max_jobs
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"Worker crashed with error: {type(e).__name__}: {str(e)}"
            ))
            sys.exit(1)
        
        self.stdout.write(self.style.SUCCESS(
            "Outbox Worker stopped gracefully"
        ))
