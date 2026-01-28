# TimeTracker — Management Commands

> Django management commands for background processing, data synchronization, and testing.

---

## Overview

This directory contains custom Django management commands accessible via `python manage.py <command>`:
- **worker_run**: Background job processing (Outbox pattern)
- **seed_testdata**: Generate test data for development
- **sync_tasks**: (Placeholder) Synchronize tasks from external system

---

## Commands Inventory

### `worker_run`
**Purpose**: Run the Outbox Worker to process asynchronous background jobs.

**Usage:**
```bash
python manage.py worker_run [OPTIONS]
```

**Options:**
- `--poll-seconds SECONDS`: Time to wait between ticks when no jobs (default: 2.0)
- `--max-jobs COUNT`: Maximum jobs to process per tick (default: 50)

**Examples:**
```bash
# Default configuration (poll every 2s, max 50 jobs per tick)
python manage.py worker_run

# Custom configuration (poll every 5s, max 100 jobs per tick)
python manage.py worker_run --poll-seconds 5 --max-jobs 100
```

**Behavior:**
- Continuously polls `OutboxJob` table for PENDING jobs
- Processes jobs using registered handlers
- Implements retry logic with exponential backoff
- Supports graceful shutdown (SIGTERM, SIGINT/Ctrl+C)
- Idempotent job processing (safe to retry)

**Graceful shutdown:**
```bash
# Send SIGTERM signal
kill -TERM <pid>

# Or use Ctrl+C in terminal
# Worker will finish current job batch and exit cleanly
```

**Job lifecycle:**
1. Worker selects PENDING jobs (up to `max-jobs`)
2. Locks job (SELECT FOR UPDATE)
3. Updates status to IN_PROGRESS
4. Executes handler
5. On success: marks COMPLETED
6. On failure: increments attempts, schedules retry with backoff

**When to use:**
- Required for production deployment (runs as separate process)
- In development: Optional (run manually or in Docker as `worker` service)
- Background tasks: Outbox jobs enqueued by `save_day()` and other operations

**Docker usage:**
```bash
# Development
docker exec timetracker_worker_dev python manage.py worker_run

# Production (runs automatically as service)
docker compose -f docker-compose.prod.yml logs -f worker
```

**Monitoring:**
- Watch logs for job processing activity
- Check `OutboxJob` table for stuck jobs (status=IN_PROGRESS, old timestamp)
- Monitor for repeated failures (high attempts count)

**Related documentation:**
- `backend/timetracker_app/outbox/AGENTS.md` (Outbox pattern details)
- `backend/README_WORKER.md` (Worker architecture)

---

### `seed_testdata`
**Purpose**: Create test data for development and testing.

**Usage:**
```bash
python manage.py seed_testdata
```

**What it creates:**
1. **Test user account:**
   - Email: `test@example.com`
   - Password: `testpass123`
   - Username: `test@example.com`

2. **Test employee:**
   - Linked to test user
   - Email: `test@example.com`
   - Active: true
   - Daily norm: 480 minutes (8 hours)

3. **5 sample tasks:**
   - Task 1-5 with varying metadata
   - project_phase: Phase 1 or Phase 2
   - department: IT or Development
   - discipline: Backend
   - All marked as active

4. **Time entries for last 3 days:**
   - 2 entries per day (Task 1 and Task 2)
   - Varying durations (200-260 minutes)
   - Correct `hours_decimal` calculation

**When to use:**
- First-time setup after migrations
- Reset database with known test data
- E2E testing (create fresh test environment)
- Demo/showcase purposes

**Idempotency:**
- Safe to run multiple times
- Uses `get_or_create()` to avoid duplicates
- Won't overwrite existing data

**Docker usage:**
```bash
# Development
docker exec timetracker_backend_dev python manage.py seed_testdata

# Production (DO NOT USE - only for dev/staging)
```

**Example output:**
```
Tworzenie danych testowych...
Utworzono User: test@example.com
Utworzono Employee: test@example.com
Utworzono TaskCache: Zadanie 1
Utworzono TaskCache: Zadanie 2
...
=== Dane testowe utworzone ===
Email: test@example.com
Hasło: testpass123
```

**After seeding:**
1. Login at `http://localhost:5173/login` with credentials above
2. Navigate to Month view to see entries for last 3 days
3. Navigate to Day view to edit entries

**Cleanup:**
```bash
# Delete all TimeEntry records
python manage.py shell -c "from timetracker_app.models import TimeEntry; TimeEntry.objects.all().delete()"

# Delete test user and employee
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(username='test@example.com').delete()"

# Or reset entire database (DESTRUCTIVE)
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
docker exec timetracker_backend_dev python manage.py migrate
```

**⚠️ WARNING**: Do not run `seed_testdata` in production. It creates accounts with weak passwords.

---

### `sync_tasks`
**Purpose**: (Placeholder) Synchronize TaskCache from external system.

**Status**: Not yet implemented

**Planned usage:**
```bash
python manage.py sync_tasks [OPTIONS]
```

**Planned options:**
- `--source URL`: External system API URL
- `--dry-run`: Preview changes without applying
- `--full`: Full sync (re-fetch all tasks)
- `--incremental`: Only fetch changed tasks since last sync

**Planned behavior:**
1. Connect to external task management system (API)
2. Fetch active tasks with metadata
3. Upsert to `TaskCache` table:
   - Create new tasks
   - Update existing tasks (display_name, metadata, is_active)
   - Mark deleted tasks as inactive
4. Log sync statistics (added, updated, deactivated)

**When to use (planned):**
- Initial import of tasks from external system
- Scheduled sync (cron job, hourly/daily)
- Manual refresh after major changes in external system

**Implementation notes:**
- Should be idempotent (safe to run multiple times)
- Should handle API errors gracefully (retry with backoff)
- Should log all changes for audit trail
- Should support incremental sync (performance)

**Related issues:**
- Requires external system API contract definition
- Needs authentication mechanism (API key, OAuth)
- May need rate limiting for large task lists

---

## Running Management Commands

### Local development (non-Docker)
```bash
# From project root
cd backend
python manage.py <command> [OPTIONS]
```

### Docker development
```bash
# From project root
docker exec timetracker_backend_dev python manage.py <command> [OPTIONS]
```

### Docker production
```bash
# From project root
docker exec timetracker_backend_prod python manage.py <command> [OPTIONS]
```

### Interactive shell access
```bash
# Docker dev
docker exec -it timetracker_backend_dev bash
# Now inside container:
python manage.py <command>
```

---

## Creating Custom Management Commands

### File structure
```
backend/timetracker_app/management/
├── __init__.py
└── commands/
    ├── __init__.py
    ├── worker_run.py
    ├── seed_testdata.py
    └── your_command.py
```

### Template
```python
"""
Management command: your_command
Brief description of what this command does.
"""

from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'One-line description for --help output'
    
    def add_arguments(self, parser):
        """Add command-line arguments."""
        parser.add_argument(
            '--option-name',
            type=str,
            default='default_value',
            help='Description of option'
        )
    
    def handle(self, *args, **options):
        """Main command logic."""
        self.stdout.write('Starting command...')
        
        try:
            # Your logic here
            result = do_something(options['option_name'])
            
            self.stdout.write(
                self.style.SUCCESS(f'Success: {result}')
            )
        except Exception as e:
            raise CommandError(f'Command failed: {str(e)}')
```

### Best practices
- Use `self.stdout.write()` for output (not `print()`)
- Use `self.style.SUCCESS()`, `.WARNING()`, `.ERROR()` for colored output
- Raise `CommandError` for expected failures
- Add docstring with usage examples
- Make commands idempotent where possible
- Add `--dry-run` option for commands that modify data
- Log important actions (especially data changes)

---

## Scheduling Commands (Production)

### Using cron (Linux/Unix)
```bash
# Edit crontab
crontab -e

# Add scheduled jobs
# Example: Sync tasks daily at 2 AM
0 2 * * * cd /path/to/backend && python manage.py sync_tasks --incremental

# Example: Backup database daily at 3 AM
0 3 * * * /path/to/scripts/db_backup.sh
```

### Using systemd (Linux)
```ini
# /etc/systemd/system/timetracker-worker.service
[Unit]
Description=TimeTracker Outbox Worker
After=network.target postgresql.service

[Service]
Type=simple
User=timetracker
WorkingDirectory=/opt/timetracker/backend
ExecStart=/opt/timetracker/venv/bin/python manage.py worker_run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable timetracker-worker
sudo systemctl start timetracker-worker

# Check status
sudo systemctl status timetracker-worker

# View logs
sudo journalctl -u timetracker-worker -f
```

### Using Docker Compose (Recommended)
```yaml
# In docker-compose.prod.yml
services:
  worker:
    build: ...
    command: python manage.py worker_run
    restart: unless-stopped
    depends_on:
      - db
```

Worker runs automatically as part of Docker Compose stack.

---

## Monitoring and Debugging

### Check command help
```bash
python manage.py <command> --help
```

### View command output
```bash
# Real-time logs (Docker)
docker compose -f docker-compose.dev.yml logs -f worker

# View specific lines
docker compose logs --tail=100 worker
```

### Debug in Django shell
```bash
python manage.py shell

# Import and test command logic
>>> from timetracker_app.management.commands.worker_run import Command
>>> cmd = Command()
>>> cmd.handle(poll_seconds=2, max_jobs=10)
```

### Common issues

**"No module named 'timetracker_app.management.commands'"**
- Ensure `__init__.py` exists in `management/` and `commands/`
- Check Python path includes backend directory

**"CommandError: Unknown command: 'worker_run'"**
- Command file must be named correctly (e.g., `worker_run.py`)
- Class must be named exactly `Command`
- Restart Django dev server if command was just added

**Worker processes no jobs**
- Check `OutboxJob` table has PENDING jobs
- Verify database connection
- Check worker logs for errors
- Ensure `run_after` timestamp is in the past

**Worker crashes on startup**
- Check database migrations are applied
- Verify all dependencies are installed
- Check logs for stack trace
- Ensure database is accessible

---

## Testing Management Commands

### Unit tests
```python
# In backend/timetracker_app/tests/test_management_commands.py
from io import StringIO
from django.core.management import call_command
from django.test import TestCase

class SeedTestdataCommandTest(TestCase):
    def test_seed_creates_user(self):
        out = StringIO()
        call_command('seed_testdata', stdout=out)
        
        # Verify output
        self.assertIn('Utworzono User', out.getvalue())
        
        # Verify database
        from django.contrib.auth.models import User
        self.assertTrue(User.objects.filter(username='test@example.com').exists())
```

### Integration tests
```python
def test_worker_processes_job(self):
    # Enqueue test job
    from timetracker_app.outbox.dispatcher import enqueue
    enqueue('TEST_JOB', 'test-key-1', {'data': 'test'})
    
    # Run worker for 1 tick
    from timetracker_app.management.commands.worker_run import Command
    cmd = Command()
    # ... run worker with timeout
    
    # Verify job processed
    job = OutboxJob.objects.get(dedup_key='test-key-1')
    self.assertEqual(job.status, 'COMPLETED')
```

---

## Future Enhancements (not MVP)

- **Command scheduler**: Django-celery-beat for cron-like scheduling
- **Admin UI**: Trigger commands from Django admin
- **Command history**: Log all command executions with timestamps
- **Command locks**: Prevent concurrent execution of same command
- **Progress bars**: For long-running commands (tqdm integration)
- **Email notifications**: Alert on command failures
- **Dry-run mode**: Preview changes for all data-modifying commands
- **Performance metrics**: Track command execution time and resource usage

---

## Related Documentation

- **Backend README**: `backend/README.md`
- **Worker documentation**: `backend/README_WORKER.md`
- **Outbox pattern**: `backend/timetracker_app/outbox/AGENTS.md`
- **Django management commands**: https://docs.djangoproject.com/en/stable/howto/custom-management-commands/

---

## Summary

**Active commands**: 2 (`worker_run`, `seed_testdata`)  
**Placeholder commands**: 1 (`sync_tasks`)  
**Critical for production**: `worker_run` (background job processing)  
**Development only**: `seed_testdata` (never use in production)

Management commands provide operational tools for running and maintaining the TimeTracker application. The worker command is essential for production deployment, while seed_testdata aids development and testing.
