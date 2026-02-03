# PM1.9 - Status Report 10

**Project:** The Horizon Project - ETL Pipeline
**Interaction:** 1st Interaction of February - 2026 (Data Refresh)
**Date:** 2026-02-03
**Status:** 🟡 In Progress
**Version:** v0.12.9 (Running Data Refresh)

## 1. Executive Summary
This interaction focuses on a full database reset and re-execution of the ETL pipeline for the "Serra" campus. The goal is to ensure that recent improvements in Lattes ingestion (Academic Education, Citations, CNPq URL) and SigPesq mapping are correctly reflected in the canonical exports, solving issues with empty fields for initiatives and research groups.

## 2. Targeted Deliverables
| ID | Description | Status |
|---|---|---|
| TD-11 | Full Database Reset | In Progress |
| TD-12 | Full Pipeline Refresh (Serra) | Planned |
| TD-13 | Canonical Data Validation | Planned |

## 3. Risks & Issues
- **None**: Scheduled maintenance to ensure data quality.

## 4. Planned for Next Steps
- Execute `make reset-db`.
- Execute `make pipeline-serra`.
- Verify enrichment of `researchers_canonical.json`.
