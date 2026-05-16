<!--
SYNC IMPACT REPORT
==================
Version change: [TEMPLATE] → 1.0.0
Modified principles: N/A (initial ratification from template)
Added sections:
  - I. Ports & Adapters Architecture
  - II. Domain-First Data Modeling
  - III. Prefect Flow Orchestration
  - IV. Audit-Driven Data Quality
  - V. LGPD Compliance by Default
  - Data Integrity & Clean-State Ingestion
  - Development Workflow & Quality Gates
  - Governance
Templates reviewed:
  - .specify/templates/plan-template.md ✅ aligned (Constitution Check section present)
  - .specify/templates/spec-template.md ✅ aligned (no implementation details required)
  - .specify/templates/tasks-template.md ✅ aligned (task categories match flow/adapter structure)
Follow-up TODOs:
  - None — all placeholders resolved from repo analysis
-->

# Horizon ETL Constitution

## Core Principles

### I. Ports & Adapters Architecture (NON-NEGOTIABLE)

All external system interactions — SigPesq, Lattes, CNPq, database clients,
JSON sinks — MUST be mediated through port contracts defined in
`src/core/ports/`. Business logic in `src/core/logic/` MUST NOT import
directly from `src/adapters/`. Flows in `src/flows/` orchestrate adapters and
do not contain business rules.

**Rationale**: Prevents tight coupling between ETL logic and external systems.
Enables source substitution (e.g., switching from SQLite to Supabase) without
touching core logic. Enforces testability — core logic is always testable
without live external systems.

**Enforcement**: Any PR that imports an adapter class directly inside
`src/core/logic/` is a violation. Code review MUST reject it.

### II. Domain-First Data Modeling

Canonical domain entities come from the `research-domain` external package.
Internal ETL code MUST map raw source data into these entities — it MUST NOT
redefine domain concepts (persons, research groups, initiatives, advisorships,
fellowships, organizations) in isolation. All canonical exports MUST serialize
domain-aligned entities into JSON artifacts under `data/exports/`.

**Rationale**: A single canonical data model shared across the Horizon
ecosystem prevents drift between ETL output and dashboard/mart consumers.
Domain ownership lives in `research-domain`; Horizon ETL is a consumer.

**Enforcement**: New entity types introduced in ETL code require a
corresponding addition to `research-domain` (or explicit justification as
ETL-only transient structures). Exported JSON schemas must be derivable from
domain entities.

### III. Prefect Flow Orchestration (NON-NEGOTIABLE)

All ETL operations MUST be implemented as Prefect flows registered under
`src/flows/`. No ETL logic may run outside a Prefect flow context via
standalone scripts. Every flow MUST register state-change hooks that emit
completion reports to the configured Telegram channel (Completed, Failed,
Crashed, Cancelled states).

**Rationale**: Prefect provides execution history, retry semantics, and
observability for all pipeline runs. Bypassing flows creates blind spots in
production monitoring. Telegram hooks ensure the team is notified of any
pipeline state without polling the Prefect UI.

**Enforcement**: Scripts in `src/scripts/` are operational utilities
(auditing, diagnostics) — they may read from DB/artifacts but MUST NOT
perform ingestion or export outside a flow. Any new data ingestion MUST have
a corresponding Prefect flow.

### IV. Audit-Driven Data Quality

Every ingestion run MUST produce a verifiable audit trail. Deduplication,
entity reconciliation, and export validation are first-class architectural
concerns. `make etl-report` MUST produce a clean report before any export is
considered production-ready. Audit scripts under `src/scripts/` are part of
the architecture, not supplementary tooling.

**Rationale**: Academic data from SigPesq, Lattes, and CNPq overlaps and
conflicts. Without active audit validation, stale or duplicate records
silently corrupt downstream dashboards and reports.

**Enforcement**: New loaders or exporters MUST include or update a
corresponding audit check (e.g., deduplication count, reconciliation report).
PRs that add ingestion without audit coverage require explicit justification.

### V. LGPD Compliance by Default

Personal identifiers — CPF, telefone, e-mail — MUST be anonymized in all
exported artifacts (`data/exports/`, `data/reports/`) and in stored database
records when anonymization has been applied. No personal data MAY appear in
any output file, log, or report without explicit authorization tied to a
documented legal basis. Access to non-anonymized data MUST be logged in an
immutable audit trail recording user, timestamp, and subject.

**Rationale**: LGPD (Lei Geral de Proteção de Dados) requires that personal
data not be exposed beyond the minimum necessary for the stated processing
purpose. ETL systems are high-risk vectors for PII leakage via exported files.

**Enforcement**: All new export flows MUST pass through the anonymization
layer for CPF, telefone, and e-mail fields before writing output files. Any
code path that writes these fields in clear text to `data/exports/` or
`data/reports/` is a compliance violation and MUST NOT be merged.

## Data Integrity & Clean-State Ingestion

Raw data directories (`data/raw/sigpesq/`, `data/lattes_json/`) MUST be
cleared before each source download. This prevents stale reports from prior
runs from contaminating the current ingestion. The local database
(`db/horizon.db`) is the single canonical state; raw files are ephemeral
inputs only.

The database MUST be fully re-creatable from scratch via `make db-reset`
followed by ingestion flows. No ETL artifact (raw file, export JSON, report)
is treated as a source of truth — only the flows, strategies, loaders, and
domain entities define correct behavior.

## Development Workflow & Quality Gates

`make ci-check` — which runs linting (flake8), formatting checks (black,
isort), type checking (mypy), and the full test suite (pytest) — MUST pass
before any branch is merged. This is the minimum quality gate.

Makefile targets are the canonical entry points for all operations. Direct
`python` invocations are permitted for development exploration but MUST NOT
replace Makefile targets in documentation or CI. Code style follows black
(88-character line length) and isort (black profile).

Tests live in `tests/`. Integration tests in `tests/integration/` may require
a live Prefect server and local DB — they are excluded from fast CI runs but
MUST pass before release. New flows MUST have at least one corresponding test
in `tests/`.

## Governance

This constitution supersedes all other practice documents, architectural
notes, and conventions in this repository. In case of conflict, this document
takes precedence.

**Amendment procedure**: Amendments require updating this file with a
version bump, updating the Sync Impact Report comment, and propagating
changes to affected templates (plan, spec, tasks). Major changes — removal or
redefinition of a principle — require team review before merge.

**Versioning policy**:
- MAJOR: Backward-incompatible governance change (principle removal or
  fundamental redefinition).
- MINOR: New principle or section added, or materially expanded guidance.
- PATCH: Clarifications, wording improvements, non-semantic refinements.

**Compliance review**: Constitution compliance is reviewed at each
`/speckit-plan` gate (Constitution Check section) and at PR review. Automated
linting enforces code-level rules (formatting, imports). Architectural rules
are enforced via code review.

**Version**: 1.0.0 | **Ratified**: 2026-05-16 | **Last Amended**: 2026-05-16
