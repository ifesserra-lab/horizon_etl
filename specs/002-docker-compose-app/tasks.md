# Tasks: Containerized Application Deployment

**Input**: Design documents from `specs/002-docker-compose-app/`

**Feature**: Docker Compose setup for full Horizon ETL system (Prefect DB + Prefect Server + ETL app)

**No TDD requested** — no test tasks generated. Verification via quickstart.md acceptance scenarios.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new files and update credential template before any service or Makefile work.

- [X] T001 Create .dockerignore at project root (exclude: .venv/, .env, db/, data/, cache/, logs/, .git/, specs/, .specify/, __pycache__/, *.pyc, .pytest_cache/, .coverage, htmlcov/, *.log)
- [X] T002 [P] Update .env.example with CHROME_BINARY=/usr/bin/chromium, CHROMEDRIVER_PATH=/usr/bin/chromedriver, STORAGE_TYPE=db

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure — Dockerfile, docker-compose.yml updates, and ChromeDriver env var fix. Must be complete before Makefile targets can work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Inspect src/flows/lattes/download.py and src/flows/lattes/download_config.py (or LattesConfigGenerator) for hardcoded chromedriver path; update to read os.environ.get("CHROMEDRIVER_PATH", "./chromedriver") if hardcoded
- [X] T004 Write Dockerfile at project root: multi-stage (builder: python:3.12-slim + build-essential + git + pip install requirements.txt; runtime: python:3.12-slim + apt chromium chromium-driver + playwright system deps + copy from builder + playwright install --with-deps chromium + COPY . /app + ENTRYPOINT ["python", "app.py"])
- [X] T005 Add healthcheck to server service in docker-compose.yml: test: ["CMD", "curl", "-f", "http://localhost:4200/api/health"], interval: 10s, timeout: 5s, retries: 6, start_period: 15s
- [X] T006 Add app service to docker-compose.yml: build: {context: ., dockerfile: Dockerfile}, image: horizon-etl:latest, env_file: .env, environment: {PREFECT_API_URL: http://server:4200/api, PREFECT_CLIENT_SERVER_VERSION_CHECK_ENABLED: "false", CHROME_BINARY: /usr/bin/chromium, CHROMEDRIVER_PATH: /usr/bin/chromedriver, STORAGE_TYPE: db}, volumes: [./db:/app/db, ./data/exports:/app/data/exports, ./data/lattes_json:/app/data/lattes_json, ./cache:/app/cache, ./logs:/app/logs], depends_on: {server: {condition: service_healthy}}
- [X] T007 Update _patch_browser_factory in src/adapters/sources/sigpesq/adapter.py to only apply simplified launch (no args) on macOS (sys.platform == 'darwin'); on Linux use original BrowserFactory unchanged so --no-sandbox remains active for Docker

**Checkpoint**: `docker compose build app` succeeds; docker-compose.yml validates with `docker compose config`.

---

## Phase 3: User Story 1 — Developer One-Command Startup (Priority: P1) 🎯 MVP

**Goal**: Developer runs `make docker-up` then `make docker-pipeline CAMPUS=Serra` and the full pipeline executes.

**Independent Test**: From quickstart.md — `make docker-up && make docker-pipeline CAMPUS=Serra`; verify flow completes and exports appear in `data/exports/` on host.

- [X] T008 [US1] Add docker-up target to Makefile: runs mkdir -p for all bind-mount dirs then `docker compose up -d database server`; add to .PHONY and help
- [X] T009 [P] [US1] Add docker-stop target to Makefile: `docker compose stop`; add to .PHONY and help
- [X] T010 [P] [US1] Add docker-build target to Makefile: `docker compose build app`; add to .PHONY and help
- [X] T011 [US1] Add docker-pipeline target to Makefile: `docker compose run --rm app full_pipeline "$(CAMPUS)" "$(OUTPUT_DIR)"`; add to .PHONY and help
- [X] T012 [P] [US1] Add docker-ingest-sigpesq target to Makefile: `docker compose run --rm app sigpesq`; add to .PHONY and help
- [X] T013 [P] [US1] Add docker-sync-cnpq target to Makefile: `docker compose run --rm app cnpq_sync "$(CAMPUS)"`; add to .PHONY and help
- [X] T014 [P] [US1] Add docker-export-canonical target to Makefile: `docker compose run --rm app export_canonical "$(OUTPUT_DIR)" "$(CAMPUS)"`; add to .PHONY and help
- [X] T015 [P] [US1] Add docker-weekly-flows target to Makefile: `docker compose run --rm app weekly "$(WEEKLY_CAMPUS)" "$(OUTPUT_DIR)"`; add to .PHONY and help

**Checkpoint**: `make docker-up` starts Prefect services healthy; `make docker-pipeline CAMPUS=Serra` completes a full pipeline run.

---

## Phase 4: User Story 2 — Data Persistence Across Restarts (Priority: P2)

**Goal**: `db/horizon.db` and `data/exports/` survive `make docker-stop && make docker-up` cycles.

**Independent Test**: From quickstart.md — run pipeline, record `sqlite3 db/horizon.db "SELECT COUNT(*) FROM researcher;"`, stop and restart, verify count unchanged.

- [X] T016 [US2] Update docker-up target in Makefile to create all bind-mount directories before compose up: `mkdir -p db data/exports data/lattes_json data/raw/sigpesq cache logs`
- [X] T017 [P] [US2] Add docker-db-reset target to Makefile: `docker compose run --rm app python db/create_db.py`; add to .PHONY and help
- [X] T018 [P] [US2] Add docker-full-refresh target to Makefile: depends on docker-db-reset, runs `docker compose run --rm app full_pipeline "" "$(OUTPUT_DIR)"`; add to .PHONY and help

**Checkpoint**: Run pipeline, stop all services, restart, verify `db/horizon.db` row counts unchanged and `data/exports/` files unchanged.

---

## Phase 5: User Story 3 — External Service Access from Containers (Priority: P3)

**Goal**: SigPesq (Playwright), Lattes (Selenium/scriptLattes), and CNPq flows work identically inside the container.

**Independent Test**: From quickstart.md — `make docker-ingest-sigpesq` and `make docker-sync-cnpq CAMPUS=Serra` complete successfully with same record counts as local runs.

- [X] T019 [US3] Verify T003 fix: confirm scriptLattes LattesConfigGenerator or download flow uses CHROMEDRIVER_PATH env var; if it uses a config-level chromedriver key, verify that key is set to os.environ.get("CHROMEDRIVER_PATH") in src/flows/lattes/download.py or equivalent
- [X] T020 [P] [US3] Verify Dockerfile includes chromium-driver (provides /usr/bin/chromedriver) and that apt package name is correct for Debian bookworm (may be chromium-driver not chromium-chromedriver — check with `apt-cache show chromium-driver`)
- [X] T021 [US3] Add --no-sandbox to any Selenium Chrome options used by scriptLattes when running on Linux: check if scriptLattes accepts chrome_options parameter; if so, pass options with --no-sandbox, --disable-dev-shm-usage when RUNNING_IN_DOCKER env var is set

**Checkpoint**: `make docker-ingest-sigpesq` completes without browser launch errors; `make docker-sync-cnpq` fetches CNPq data; Lattes download produces JSONs in `data/lattes_json/`.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and cleanup.

- [X] T022 [P] Update README.md (or create a Docker section) with: prerequisites, `make docker-up` startup steps, `make docker-pipeline` usage, and reference to quickstart.md
- [X] T023 Verify `make ci-check` still passes locally (linting + tests unaffected by new files)
- [X] T024 [P] Confirm .dockerignore excludes .env, db/, and data/ so credentials and data never enter the image layer

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; T001 and T002 are parallel
- **Foundational (Phase 2)**: T003 → T004 → T005 → T006 → T007 (T005 and T006 sequential; T007 parallel with T004)
- **US1 (Phase 3)**: Depends on Phase 2 completion; T009–T010 and T012–T015 are parallel with each other
- **US2 (Phase 4)**: T016 updates the docker-up target (modifies same file as T008 — run after T008); T017 and T018 are parallel
- **US3 (Phase 5)**: T019 depends on T003; T020 parallel with T019; T021 after T019/T020
- **Polish (Phase 6)**: Depends on all prior phases complete

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational; no dependency on US2/US3
- **US2 (P2)**: Depends on US1 (docker-up target exists); T016 modifies same Makefile target as T008
- **US3 (P3)**: Depends on Foundational (T003, T007); independent of US1/US2

### Parallel Opportunities

- T001 ∥ T002 (Phase 1 — different files)
- T004 ∥ T007 (Dockerfile vs adapter patch — different files)
- T009 ∥ T010 ∥ T012 ∥ T013 ∥ T014 ∥ T015 (all add different Makefile targets in same file — run sequentially)
- T017 ∥ T018 (different Makefile targets)
- T020 ∥ T019 (Dockerfile check vs download.py check — different files)
- T022 ∥ T024 (different files)

---

## Parallel Example: Phase 2 (Foundational)

```
T003 (check lattes chromedriver path)
  ↓
T004 (Dockerfile)  ∥  T007 (patch_browser_factory macOS fix)
  ↓
T005 (server healthcheck in compose)
  ↓
T006 (app service in compose)
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: T001, T002
2. Complete Phase 2: T003 → T004 → T005 → T006 → T007
3. Complete Phase 3 (US1): T008 → T011 (minimum viable: docker-up + docker-pipeline)
4. **STOP and VALIDATE**: `make docker-up && make docker-pipeline CAMPUS=Serra`

### Incremental Delivery

1. Phase 1 + 2 → Container builds and runs
2. Phase 3 (US1) → One-command startup and pipeline execution
3. Phase 4 (US2) → Persistence verified across restarts
4. Phase 5 (US3) → All external sources confirmed working in container
5. Phase 6 → Documentation complete

---

## Notes

- Package name for chromedriver on Debian bookworm may be `chromium-driver` not `chromium-chromedriver` — verify during T020
- scriptLattes may need `--no-sandbox` Chrome option on Linux — T021 addresses this
- The `_patch_browser_factory` macOS-only fix (T007) is critical: without it, SigPesq login breaks on macOS; with an unconditional patch on Linux, `--no-sandbox` is lost and login may break there
- `docker compose run --rm app` routes `app.py` CLI args correctly because ENTRYPOINT is `python app.py` and CMD is overridden by run args
- All bind-mount directories must exist on host before container starts; T016 handles this in docker-up
