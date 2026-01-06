# General Project Backlog

**Central Tracking for Releases and Work Items**

## 1. Releases Log
Tracks the delivery of versions to production (Main Branch).

| Version | Date | Status | Description | PR / Commit |
|---------|------|--------|-------------|-------------|
| **v0.0.0** | 2026-01-01 | Released | Project Initiation | - |
| **v0.3.0** | 2026-01-02 | Released | Integration of Organizational Units | PR #6 |

## 2. In Progress Items (Current Sprint)
Reflecting active work from `SI.3 Product Backlog`.

- **Epic 1: Extração SigPesq (Release 1)**
    - [x] US-001 [Extração Projetos SigPesq](https://github.com/ifesserra-lab/horizon_etl/issues/2)
    - [x] US-007 [Ingestão Grupos de Pesquisa] (PR #4)
    - [ ] US-005 Observabilidade e Idempotência

- **Epic 3: Dados de Execução FAPES (Release 3)**
    - [ ] US-006 [Extração de Editais FAPES (PDF)](https://github.com/ifesserra-lab/horizon_etl/issues/1)

## 3. Hierarchical Status
Mapping Epics -> User Stories -> Tasks status.

### R1 - SigPesq
- **US-001**: Ready (Implemented)
- **US-007**: Ready (Implemented / PR #4)
- **US-005**: Ready

### R3 - SigFapes
- **US-006**: Ready
    - T-006 [Dev] Scraper: Pending
    - T-007 [Dev] Parser: Pending
    - T-008 [Dev] Matcher: Pending
    - T-009 [Ops] Flow: Pending
