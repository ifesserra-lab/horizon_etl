# Tasks: Weekly CI Workflow Validation and Export Compression

**Input**: Design documents from `specs/003-workflow-ci-zip-exports/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅

**Single file change**: All tasks modify `.github/workflows/weekly-etl.yml` only.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

**Purpose**: Confirm baseline state before making changes.

- [X] T001 Read current `.github/workflows/weekly-etl.yml` and annotate all sections requiring changes per plan.md

---

## Phase 2: Foundational

**Purpose**: No shared infrastructure needed; all stories touch the same file — execute sequentially.

*(No foundational tasks — feature is a single YAML file edit)*

---

## Phase 3: US1 — Reliable Weekly Pipeline Execution in CI (P1)

**Story goal**: Workflow permissions allow artifact upload; Prefect cleanup always runs.

**Independent test**: Trigger `workflow_dispatch`; verify no permission error on artifact upload step and `Stop Prefect server` runs on failure.

- [X] T002 [US1] Add `actions: write` to `permissions:` block in `.github/workflows/weekly-etl.yml` (alongside existing `contents: read`)
- [X] T003 [US1] Verify `Stop Prefect server` step already has `if: always()` in `.github/workflows/weekly-etl.yml`; add it if missing

---

## Phase 4: US2 — Automatic Compression of Large Export Files (P2)

**Story goal**: Any export file >10 MB is compressed to `.zip` before artifact upload; retention set to 30 days.

**Independent test**: After pipeline run, confirm no uncompressed file >10 MB in artifact and retention shows 30 days.

- [X] T004 [US2] Insert `Compress large export files` step (with `if: always()`) before `Upload ETL artifacts` step in `.github/workflows/weekly-etl.yml`:
  ```yaml
  - name: Compress large export files
    if: always()
    run: |
      find data/ -type f -size +10M \
        -exec sh -c 'for f; do zip -m -j "$f.zip" "$f"; done' sh {} +
  ```
- [X] T005 [US2] Add `retention-days: 30` field to `actions/upload-artifact@v4` step in `.github/workflows/weekly-etl.yml`

---

## Phase 5: US3 — Lattes Flow Compatibility in CI (P3)

**Story goal**: Lattes Selenium flow locates a compatible Chrome binary and chromedriver in the CI environment.

**Independent test**: Run `make ingest-lattes-download` step in CI; verify it exits without `ChromeDriverRuntimeError`.

- [X] T006 [US3] Add `CHROME_BINARY: /usr/bin/chromium-browser` and `CHROMEDRIVER_PATH: /usr/bin/chromedriver` to job-level `env:` block in `.github/workflows/weekly-etl.yml`
- [X] T007 [US3] Insert `Install Chromium for Lattes (Selenium)` step after `Install Playwright Chromium` step in `.github/workflows/weekly-etl.yml`:
  ```yaml
  - name: Install Chromium for Lattes (Selenium)
    run: |
      sudo apt-get update -qq
      sudo apt-get install -y chromium-browser chromium-driver
  ```

---

## Phase 6: Polish & Validation

**Purpose**: Verify final YAML is valid and all acceptance criteria pass.

- [X] T008 Validate YAML syntax of `.github/workflows/weekly-etl.yml` by running `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/weekly-etl.yml'))"` from repo root
- [X] T009 Review full diff of `.github/workflows/weekly-etl.yml` against original to confirm all 4 changes are present: permissions, Chromium install step, compression step, retention-days

---

## Dependencies

```
T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009
```

All sequential (same file). No parallel opportunities — single-file YAML edit.

## Implementation Strategy

**MVP**: T001–T003 (US1 only) — fixes the critical permission bug so artifact upload works.

**Full**: T001–T009 — all stories complete.

**Suggested order for a single session**: Complete all tasks in order T001→T009; the file only needs to be edited once.
