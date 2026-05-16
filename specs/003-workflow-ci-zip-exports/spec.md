# Feature Specification: Weekly CI Workflow Validation and Export Compression

**Feature Branch**: `feat/003-workflow-ci-zip-exports`

**Created**: 2026-05-16

**Status**: Draft

## Clarifications

### Session 2026-05-16

- Q: How should Chrome for Lattes/Selenium be provided in CI? → A: Reuse Playwright-managed Chromium + bundled chromedriver (no separate Chrome install).
- Q: Artifact retention period? → A: 30 days (covers ~4 weekly runs, reduces storage).

## User Scenarios & Testing

### User Story 1 — Reliable Weekly Pipeline Execution in CI (Priority: P1)

As a maintainer, I want the weekly ETL pipeline to run correctly on GitHub Actions every Saturday so that data is always refreshed without manual intervention.

**Why this priority**: The entire data refresh cycle depends on CI running correctly. If the workflow fails silently or misconfigures permissions, data becomes stale and the team has no visibility.

**Independent Test**: Trigger `workflow_dispatch` manually on the `weekly-etl` workflow; verify it completes with `success` state and all expected artifacts are uploaded.

**Acceptance Scenarios**:

1. **Given** all required secrets are configured, **When** the scheduled workflow runs on Saturday, **Then** all pipeline steps complete successfully and artifacts are uploaded within 300 minutes.
2. **Given** a required secret is missing, **When** the workflow runs, **Then** the validation step fails immediately with a descriptive error naming the missing secret, and no pipeline steps execute.
3. **Given** the pipeline step fails, **When** the failure occurs, **Then** artifacts collected up to that point are uploaded and Prefect logs are shown in the workflow summary.

**Edge Cases**:
- Workflow triggered while a previous run is still in progress → second run waits (cancel-in-progress: false prevents data corruption).
- Prefect server fails to start → pipeline step fails with clear error; Prefect logs shown via `docker compose logs`.

---

### User Story 2 — Automatic Compression of Large Export Files (Priority: P2)

As a maintainer, I want export files exceeding 10 MB to be automatically compressed before being uploaded as CI artifacts so that artifact storage is not wasted and downloads are faster.

**Why this priority**: The `data/exports/` directory currently totals 16 MB. Without compression, each weekly run accumulates large uncompressed artifacts in GitHub Actions storage.

**Independent Test**: After a successful pipeline run, verify that no individual uncompressed file exceeding 10 MB appears in the uploaded artifact; files above the threshold must be present as `.zip` archives.

**Acceptance Scenarios**:

1. **Given** export files exist after the pipeline, **When** the artifact upload step runs, **Then** any file larger than 10 MB is replaced by a `.zip` archive of the same name.
2. **Given** all export files are under 10 MB, **When** the artifact upload step runs, **Then** files are uploaded without modification.
3. **Given** the compression step completes, **When** artifacts are downloaded, **Then** the `.zip` archives can be extracted to recover the original files.

**Edge Cases**:
- Export directory is empty (pipeline failed mid-run) → compression step runs, finds no files, uploads nothing; `if-no-files-found: ignore` prevents failure.
- Single file is exactly 10 MB → not compressed (threshold is strictly greater than 10 MB).

---

### User Story 3 — Lattes Flow Compatibility in CI (Priority: P3)

As a maintainer, I want the Lattes ingestion step to run correctly in the GitHub Actions runner environment so that researcher curriculum data is refreshed as part of the weekly pipeline.

**Why this priority**: Lattes uses a browser automation tool that requires a compatible Chrome binary and driver. Without explicit setup, the step silently fails or aborts.

**Independent Test**: Run `make ingest-lattes-download` on a clean ubuntu-latest environment with the same secret configuration; verify it completes without a `ChromeDriverRuntimeError`.

**Acceptance Scenarios**:

1. **Given** the CI runner environment, **When** the Lattes download step runs, **Then** it locates a compatible Chrome binary and proceeds with curriculum download.
2. **Given** the Chrome version and driver version are incompatible, **When** the Lattes step runs, **Then** it fails with a descriptive error identifying the version mismatch.

**Edge Cases**:
- Chrome installed by Playwright (for SigPesq) is a different version than the system chromedriver → version mismatch error must be clear.
- `CHROME_BINARY` env var not set → fallback to system Chrome detection.

---

### Edge Cases

- What happens when the artifact upload permission is denied? → Workflow step fails with permission error; fix: `permissions: actions: write` must be present.
- How does the workflow handle partial pipeline success? → `if: always()` on artifact upload ensures partial results are preserved even if pipeline fails.

## Requirements

### Functional Requirements

- **FR-001** [P1]: The workflow MUST declare `actions: write` permission so artifact uploads succeed under fine-grained token policies.
- **FR-002** [P1]: The workflow MUST validate all required secrets before executing any pipeline step and fail with a named error for each missing secret.
- **FR-003** [P2]: A pre-upload step MUST compress any export file larger than 10 MB into a `.zip` archive in-place before the artifact upload action runs.
- **FR-004** [P2]: The compression step MUST run even if the pipeline step failed (`if: always()`) so partial exports are still uploaded.
- **FR-005** [P3]: The workflow MUST set `CHROME_BINARY` and `CHROMEDRIVER_PATH` environment variables to the Playwright-managed Chromium binary and its bundled chromedriver (already installed by the `playwright install --with-deps chromium` step), so the Lattes flow can reuse the same browser without a separate installation.
- **FR-006** [P1]: The `Stop Prefect server` step MUST always run (`if: always()`) to prevent orphaned Docker containers on the runner.
- **FR-008** [P2]: CI artifacts MUST be retained for exactly 30 days to balance run history availability against storage consumption.
- **FR-007** [P1]: The workflow MUST use the Playwright-installed Chromium for SigPesq (already covered by `playwright install --with-deps chromium` step).

### Key Entities

- **CI Artifact**: Uploaded output of a workflow run; contains `data/` tree and `db/horizon.db`; retained for 30 days.
- **Export File**: JSON file produced by a pipeline export flow in `data/exports/`.
- **Compressed Export**: A `.zip` archive replacing an export file exceeding the 10 MB threshold.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of manual `workflow_dispatch` triggers complete without permission-related failures after the fix.
- **SC-002**: Artifact upload size is reduced by at least 30% compared to uncompressed upload when exports exceed 10 MB.
- **SC-003**: The `Validate required secrets` step catches 100% of missing-secret scenarios within the first 30 seconds of the run.
- **SC-004**: Zero orphaned Docker containers remain on the runner after a workflow run (success or failure).
- **SC-005**: The Lattes flow completes without a `ChromeDriverRuntimeError` on at least 95% of CI runs when the portal is reachable.

## Assumptions

- GitHub Actions runner is `ubuntu-latest` with Docker available (confirmed: all ubuntu-latest runners include Docker Engine).
- Playwright's bundled Chromium (installed via `playwright install --with-deps chromium`) is used for SigPesq (Playwright-based).
- Lattes uses Selenium/chromedriver; `CHROME_BINARY` and `CHROMEDRIVER_PATH` point to the Playwright-managed Chromium and its bundled chromedriver — no separate Chrome installation required.
- The 10 MB compression threshold applies per-file, not to the total artifact size.
- `.zip` compression is sufficient; no encryption or password protection required.
- Secrets `DATABASE_URL`, `STORAGE_TYPE`, `SIGPESQ_USERNAME`, `SIGPESQ_PASSWORD`, `HORIZON_TELEGRAM_BOT_TOKEN`, `HORIZON_TELEGRAM_CHAT_ID` are pre-configured in the repository.
- The `docker compose down -v` in the final step intentionally removes Prefect volumes (ephemeral in CI — SQLite data is in workspace, not in Docker volumes).

## Out of Scope

- Changing the pipeline schedule or runtime duration targets.
- Caching Docker images between runs.
- Storing artifacts to external storage (S3, GCS) — GitHub Actions artifact storage only.
- Multi-campus parallel execution in CI.
