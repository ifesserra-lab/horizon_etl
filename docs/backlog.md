# General Project Backlog

**Central Tracking for Releases and Work Items**

## 1. Releases Log
Tracks the delivery of versions to production (Main Branch).

| Version | Date | Status | Description | PR / Commit |
|---------|------|--------|-------------|-------------|
| **v0.12.10** | 2026-02-03 | Released | Research-Domain v0.12.8 Upgrade | PR #64 / Commit [TBD] |
| **v0.12.9** | 2026-02-03 | Released | Academic Education Ingestion & SigPesq Strategy Refactor | PR #62 / Commit ef944b6 |
| **v0.12.8** | 2026-02-03 | Released | Research-Domain v0.12.7 Upgrade, CNPq URL, Citation Names & Co-Advisor Match | PR #61 / Commit 773a8f3 |
| **v0.10.0** | 2026-01-28 | Released | Strict Sponsor Name Mapping & Enrichment Fixes | PR #58 |
| **v0.9.1** | 2026-01-27 | Released | ProjectLoader Modularity & Pipeline Fixes | PR #55 |
| **v0.9.0** | 2026-01-26 | Released | SIGPESQ Advisorships Ingestion | PR #52 |
| **v0.8.0** | 2026-01-25 | Released | Research Group Auto-population & Canonical Export Fixes | PR #51 |
| **v0.5.1** | 2026-01-15 | Released | Team Ingestion Refactoring & Synchronization Fix | PR #45 |
| **v0.5.0** | 2026-01-12 | Released | CNPq Sync Enhanced (Missing Researchers Fix) | PR #37 |
| **v0.4.0** | 2026-01-09 | Released | CNPq Sync Base (US-009) | PR #18 |
| **v0.3.0** | 2026-01-07 | Released | SigPesq Enhancements, ResearcherID & Granular Strategy Pattern | PR #13 |
| **v0.2.0** | 2026-01-06 | Released | Research Group Ingestion & Local Infrastructure | Main |
| **v0.0.0** | 2026-01-01 | Released | Project Initiation | - |

## 2. In Progress Items (Current Sprint)
Reflecting active work from `SI.3 Product Backlog`.

- **Epic 1: Extração SigPesq (Release 1)**
    - [x] US-001 [Extração Projetos SigPesq](https://github.com/ifesserra-lab/horizon_etl/issues/2) (Merged)
    - [x] US-007 [Ingestão Grupos de Pesquisa] (PR #4 - Merged)
    - [x] T-Leaders [Implementação de Líderes] (PR #7 - Merged)
    - [x] T-ResearcherID [E-mail como identification_id] (PR #10 - Merged)
    - [x] T-StrategyPattern [Refatoração Strategy Pattern] (PR #11 - Merged)
    - [x] T-GranularStrategy [Refatoração Granular Pattern] (PR #12 - Merged)
    - [x] US-005 Observabilidade e Idempotência (Implemented)
    - [x] US-015 [Gestão de Equipes SigPesq] (PR #41 - Review)
    - [x] US-008 [Exportação JSON Canônico e Grupos] (PR #15 - Merged)
    - [x] US-011 [Pipeline Unificado & Filtro de Campus] (PR #30 - Merged)
    - [x] US-012 [Research Area Mart & Filter] (PR #31 - Merged)
    
- **Epic 6: Atualização Base CNPq (Release v0.4.0)**
    - [x] US-009 [Sincronização de Grupos CNPq] (PR #18, #19 - Merged)
    - [x] US-010 [Sincronização de Egressos CNPq] (PR #21 - Merged)

- **Epic 3: Dados de Execução FAPES (Release 3)**
    - [ ] US-006 [Extração de Editais FAPES (PDF)](https://github.com/ifesserra-lab/horizon_etl/issues/1)

- **Epic 7: Orquestração e Exportação**
    - [x] US-014 [Exportação de Iniciativas e Tipos] (PR #39 - Merged)
    - [x] (US-016) Initiative Analytics Mart - v1.0.11

## 3. Hierarchical Status
Mapping Epics -> User Stories -> Tasks status.

### R1 - SigPesq
- **US-001**: Done (Merged)
- **US-007**: Done (Merged)
- **US-005**: Done (Implemented)
- **US-015**: Done (PR #41)

### R3 - SigFapes
- **US-006**: Ready
    - T-006 [Dev] Scraper: Pending
    - T-007 [Dev] Parser: Pending
    - T-008 [Dev] Matcher: Pending
    - T-009 [Ops] Flow: Pending
### R4 - Analytics
  - R4 - Analytics: [x] Mart de Analytics (US-016)
