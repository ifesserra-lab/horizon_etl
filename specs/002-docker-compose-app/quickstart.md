# Quickstart: Containerized Application Deployment

**Feature**: 002-docker-compose-app

---

## Prerequisites

- Docker Engine (with Compose v2)
- A `.env` file with credentials (copy `.env.example` → `.env` and fill values)

## Setup (First Time)

```bash
cp .env.example .env
# Edit .env: set SIGPESQ_USERNAME, SIGPESQ_PASSWORD, and optionally Telegram tokens
```

## Start All Services

```bash
make docker-up
# Starts: Prefect database, Prefect server, waits for health checks
```

## Run the Full Pipeline

```bash
make docker-pipeline CAMPUS=Serra
# Runs: SigPesq → CNPq → Lattes → exports
# Output files appear in data/exports/ on the host
# SQLite DB available at db/horizon.db on the host
```

## Run Individual Flows

```bash
make docker-ingest-sigpesq
make docker-sync-cnpq CAMPUS=Serra
make docker-export-canonical OUTPUT_DIR=data/exports CAMPUS=Serra
```

## Stop All Services

```bash
make docker-stop
# Stops Prefect server and DB; data is preserved in bind mounts
```

## Verify Data Persistence

```bash
make docker-stop
make docker-up
sqlite3 db/horizon.db "SELECT COUNT(*) FROM researcher;"
# Count should match pre-restart count
```

---

## Acceptance Scenarios (Test Criteria)

### US1 — One-Command Startup

```bash
# Scenario 1: Fresh startup
make docker-up
# Expected: All services healthy, Prefect UI at http://localhost:4200

# Scenario 2: Missing credentials
mv .env .env.bak
make docker-pipeline  # Expected: immediate error listing missing vars
mv .env.bak .env

# Scenario 3: Interrupted restart
make docker-stop
make docker-up        # Expected: clean startup, no manual intervention
```

### US2 — Data Persistence

```bash
make docker-pipeline CAMPUS=Serra
sqlite3 db/horizon.db "SELECT COUNT(*) FROM researcher;" > /tmp/before.txt
make docker-stop
make docker-up
sqlite3 db/horizon.db "SELECT COUNT(*) FROM researcher;" > /tmp/after.txt
diff /tmp/before.txt /tmp/after.txt  # Expected: identical
```

### US3 — External Service Access

```bash
# Run each flow separately inside container and verify completion
make docker-ingest-sigpesq
# Expected: same record counts as make ingest-sigpesq (local)

make docker-sync-cnpq CAMPUS=Serra
# Expected: same result as make sync-cnpq CAMPUS=Serra (local)
```

---

## Troubleshooting

| Problem | Check |
|---------|-------|
| `SIGPESQ_USERNAME not set` | `.env` file missing or not loaded |
| `Connection refused to server:4200` | `make docker-up` not run, or server unhealthy |
| `chromedriver: not found` | Docker image not rebuilt after apt changes |
| SQLite empty after restart | Volume bind mount path mismatch |
