# PM1.9 - Status Report 4

**Project:** The Horizon Project - ETL Pipeline
**Interaction:** 2nd Interaction of January - 2026
**Date:** 2026-01-26
**Status:** 🟢 Released
**Version:** v0.9.0

## 1. Executive Summary
This interaction delivered the "SIGPESQ Advisorships Ingestion" feature (RF-16 / US-032). We successfully implemented the mapping of "bolsistas" from SigPesq to the canonical domain, utilizing the `Advisorship` and `Fellowship` entities from the released `research_domain` library v0.5.0/0.3.1. The `ProjectLoader` was refactored to support specialized initiative types and automated fellowship management.

## 2. Deliverables (Current Interaction)

### User Stories / Tasks
| ID | Description | Status | Version |
|---|---|---|---|
| US-032 | Ingest SigPesq Advisorships (Bolsistas) | Entregue | v0.9.0 |
| RF-16 | SigPesq Bolsistas Extraction | Entregue | v0.9.0 |

### GitHub Stats
- **Issues Closed:** Closes #38
- **Pull Request (Release):** [PR #52](https://github.com/ifesserra-lab/horizon_etl/pull/52)
- **Branch merged:** `feat/sigpesq-advisorships`
- **Tag:** `v0.9.0`

## 3. Technical Accomplishments
- **Specialized Initiatives**: Refactored `ProjectLoader` to allow instantiation of `Advisorship` (subclass of `Initiative`) during ingestion.
- **Fellowship Management**: Implemented automatic creation and linking of `Fellowship` records when modalidade is present in SigPesq data.
- **Library Integration**: Successfully integrated and verified `ResearchDomain` library v0.5.0, ensuring shared entities are used across the ecosystem.
- **Testing**: Updated and verified unit tests for the mapping strategy, ensuring 100% correct transformation of complex SigPesq Excel columns.

## 4. Risks & Issues
- None identified.

## 5. Planned for Next Interaction
- Epic 3: Dados de Execução FAPES (Release 3).
