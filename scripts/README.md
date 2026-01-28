# TimeTracker — Scripts

> Utility scripts for database operations and development workflows.

---

## Overview

This directory contains shell scripts for common operational tasks:
- **Database backup/restore**: Safe data management
- **Development setup**: Quick start helpers

**Note**: These scripts are currently placeholders. Implementation is planned for production deployment phase.

---

## Scripts Inventory

### `db_backup.sh`
**Purpose**: Backup PostgreSQL database to a file.

**Status**: Placeholder (to be implemented)

**Planned usage:**
```bash
./scripts/db_backup.sh [output_file]
```

**Planned behavior:**
- Connects to PostgreSQL container (or local instance)
- Exports full database dump using `pg_dump`
- Saves to specified file (default: `backup_YYYYMMDD_HHMMSS.sql`)
- Compresses output (optional: `.sql.gz`)
- Validates backup integrity

**Environment variables (planned):**
- `DB_HOST`: Database host (default: `localhost`)
- `DB_PORT`: Database port (default: `5432`)
- `DB_NAME`: Database name (default: `timetracker`)
- `DB_USER`: Database user (default: `timetracker`)
- `DB_PASSWORD`: Database password (from `.env` or prompt)

**Docker usage (planned):**
```bash
# For dev environment
docker exec timetracker_db_dev pg_dump -U timetracker timetracker > backup.sql

# For prod environment
docker exec timetracker_db_prod pg_dump -U timetracker timetracker > backup.sql
```

**Safety considerations:**
- Include `--no-owner --no-acl` for portability
- Test backups regularly (restore to test instance)
- Store backups securely (encrypted, off-site)
- Rotate old backups (keep last N days)

---

### `db_restore.sh`
**Purpose**: Restore PostgreSQL database from a backup file.

**Status**: Placeholder (to be implemented)

**Planned usage:**
```bash
./scripts/db_restore.sh backup_file.sql
```

**Planned behavior:**
- Validates backup file exists and is readable
- Prompts for confirmation (DESTRUCTIVE operation)
- Drops existing database (optional: create backup first)
- Creates fresh database
- Restores from backup using `psql`
- Runs migrations (if schema changed)
- Validates restore success

**Environment variables (planned):**
- Same as `db_backup.sh`

**Docker usage (planned):**
```bash
# For dev environment
cat backup.sql | docker exec -i timetracker_db_dev psql -U timetracker timetracker

# For prod environment (USE WITH EXTREME CAUTION)
cat backup.sql | docker exec -i timetracker_db_prod psql -U timetracker timetracker
```

**Safety considerations:**
- **ALWAYS backup current database before restore**
- Require explicit confirmation flag (`--force` or `--yes`)
- Stop application servers before restore (to avoid write conflicts)
- Verify database version compatibility
- Test restore in staging environment first

**⚠️ WARNING**: This operation **DESTROYS all existing data**. Use with extreme caution in production.

---

### `dev.sh`
**Purpose**: Quick start script for local development.

**Status**: Placeholder (to be implemented)

**Planned usage:**
```bash
./scripts/dev.sh [command]
```

**Planned commands:**
- `./scripts/dev.sh start` — Start dev environment (Docker Compose)
- `./scripts/dev.sh stop` — Stop dev environment
- `./scripts/dev.sh restart` — Restart all services
- `./scripts/dev.sh logs` — Tail logs from all services
- `./scripts/dev.sh migrate` — Run Django migrations
- `./scripts/dev.sh shell` — Open Django shell
- `./scripts/dev.sh test` — Run backend tests
- `./scripts/dev.sh seed` — Seed test data

**Planned behavior:**
- Checks Docker is running
- Ensures `.env` file exists (copy from `.env.example` if missing)
- Wraps common Docker Compose commands for convenience
- Provides helpful error messages

**Example implementation:**
```bash
#!/bin/bash
# dev.sh - Development workflow helper

case "$1" in
  start)
    docker compose -f docker-compose.dev.yml up -d
    echo "✓ Dev environment started"
    echo "  Frontend: http://localhost:5173"
    echo "  Backend: http://localhost:8000"
    ;;
  stop)
    docker compose -f docker-compose.dev.yml down
    echo "✓ Dev environment stopped"
    ;;
  migrate)
    docker exec timetracker_backend_dev python manage.py migrate
    ;;
  shell)
    docker exec -it timetracker_backend_dev python manage.py shell
    ;;
  test)
    docker exec timetracker_backend_dev python manage.py test
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|logs|migrate|shell|test|seed}"
    exit 1
    ;;
esac
```

---

## Manual Alternatives (Current MVP)

Since scripts are not yet implemented, use these Docker commands directly:

### Database backup
```bash
# Development
docker exec timetracker_db_dev pg_dump -U timetracker timetracker > backup.sql

# Production
docker exec timetracker_db_prod pg_dump -U timetracker timetracker > backup.sql
```

### Database restore
```bash
# Development (WARNING: Destructive!)
cat backup.sql | docker exec -i timetracker_db_dev psql -U timetracker timetracker

# Production (USE WITH EXTREME CAUTION!)
# 1. Stop application first
docker compose -f docker-compose.prod.yml stop backend worker
# 2. Backup current DB
docker exec timetracker_db_prod pg_dump -U timetracker timetracker > backup_before_restore.sql
# 3. Restore
cat backup.sql | docker exec -i timetracker_db_prod psql -U timetracker timetracker
# 4. Restart application
docker compose -f docker-compose.prod.yml start backend worker
```

### Development commands
```bash
# Start dev environment
docker compose -f docker-compose.dev.yml up -d

# Stop dev environment
docker compose -f docker-compose.dev.yml down

# View logs
docker compose -f docker-compose.dev.yml logs -f

# Run migrations
docker exec timetracker_backend_dev python manage.py migrate

# Run tests
docker exec timetracker_backend_dev python manage.py test

# Seed test data
docker exec timetracker_backend_dev python manage.py seed_testdata

# Open Django shell
docker exec -it timetracker_backend_dev python manage.py shell

# Access database
docker exec -it timetracker_db_dev psql -U timetracker timetracker
```

---

## Prerequisites

### For local scripts (when implemented)
- **Bash**: Unix shell (Linux, macOS, WSL on Windows)
- **PostgreSQL client tools**: `pg_dump`, `psql`
  - Linux: `sudo apt install postgresql-client`
  - macOS: `brew install postgresql`
  - Windows: Install from PostgreSQL website or use Docker

### For Docker commands (current approach)
- **Docker Desktop** or **Docker Engine** installed and running
- Project `.env` file configured (copy from `.env.example`)

---

## Environment Setup

### Required environment variables
Scripts will read from `.env` file or environment:
```bash
DB_HOST=localhost          # or 'db' for Docker
DB_PORT=5432
DB_NAME=timetracker
DB_USER=timetracker
DB_PASSWORD=timetracker    # Change in production!
```

### Security notes
- **Never commit `.env` file** to git (it's in `.gitignore`)
- **Use strong passwords** in production
- **Encrypt backups** before storing off-site
- **Limit access** to scripts and backup files (chmod 700)

---

## Backup Strategy (Recommendations)

### Development
- Manual backups before risky operations (migrations, major changes)
- Keep local backups for 7 days
- No need for off-site backups

### Production
- **Automated daily backups** (cron job)
- **Hourly backups during business hours** (optional)
- **Retain backups**: 7 daily, 4 weekly, 12 monthly
- **Off-site storage**: AWS S3, Google Cloud Storage, or similar
- **Test restore monthly** to verify backup integrity
- **Monitor backup job failures** (alerting)

### Example cron job (to be implemented)
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/timetracker/scripts/db_backup.sh /backups/daily/$(date +\%Y\%m\%d).sql.gz
```

---

## Testing Scripts

### Before using scripts in production:
1. **Test in development environment** first
2. **Test restore process** with known-good backup
3. **Verify data integrity** after restore
4. **Document any issues** or edge cases
5. **Create runbook** for disaster recovery

### Validation checklist:
- [ ] Backup file created successfully
- [ ] Backup file is valid SQL (not truncated/corrupted)
- [ ] Restore completes without errors
- [ ] Application can connect to restored database
- [ ] Data is complete and correct (spot checks)
- [ ] Migrations apply successfully (if needed)

---

## Future Enhancements (not MVP)

- **Implement all placeholder scripts** with proper error handling
- **Add progress indicators** for long-running operations
- **Support multiple database drivers** (SQLite for dev, Postgres for prod)
- **Incremental backups** for large databases
- **Backup encryption** with GPG or similar
- **Cloud backup integration** (AWS S3, Google Cloud Storage)
- **Backup verification** (automatic restore test to temp DB)
- **Monitoring integration** (send alerts on backup failure)
- **Windows compatibility** (PowerShell scripts or cross-platform tool)

---

## Troubleshooting

### "Permission denied" error
```bash
# Make script executable
chmod +x scripts/db_backup.sh
chmod +x scripts/db_restore.sh
chmod +x scripts/dev.sh
```

### "Connection refused" error
- Check database is running: `docker compose ps`
- Verify `DB_HOST` and `DB_PORT` are correct
- Ensure database container is healthy

### "Role does not exist" error
- Verify `DB_USER` matches database user
- Check credentials in `.env` file
- For Docker: ensure using correct container name

### Backup file too large
- Use compression: `pg_dump ... | gzip > backup.sql.gz`
- Consider incremental backups for very large databases
- Exclude large tables if possible (e.g., logs)

---

## Related Documentation

- **DOCKER.md**: Docker setup and container management
- **Root AGENTS.md**: Section 9 (How to run and test)
- **Backend AGENTS.md**: Database configuration
- **Management commands**: `backend/timetracker_app/management/commands/README.md`

---

## Summary

**Current status**: Scripts are placeholders (empty files)  
**Recommended approach**: Use Docker commands directly (see "Manual Alternatives")  
**Future implementation**: Full scripts with error handling, logging, and safety checks  
**Priority**: Low for MVP, High for production deployment

For MVP development, the manual Docker commands are sufficient. Implement scripts before production deployment for operational safety and convenience.
