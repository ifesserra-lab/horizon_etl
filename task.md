# Task List - Horizon ETL

## In Progress (US-001: SigPesq)
- [ ] **Setup**:
    - [ ] Create `feat/extract-sigpesq` branch.
    - [ ] Install `sigpesq_agent` library.
- [ ] **T-001 [Dev]**: Integrate `UsingSigPesq` (from `sigpesq_agent`)
    - [ ] Implement Adapter wrapping the library.
    - [ ] Verify `get_projects()` output.
    - [ ] Verify `get_research_groups()` output.
    - [ ] Verify `get_scholars()` output.
- [ ] **T-002 [Dev]**: Implement Mappers (`src/core/logic`)
    - [ ] `map_project`: Raw -> Domain
    - [ ] `map_group`: Raw -> Domain
    - [ ] `map_scholar`: Raw -> Domain
- [ ] **T-003 [Ops]**: Prefect Flow
    - [ ] `flow_ingest_sigpesq.py`

## Backlog / Future
- [ ] **US-006**: FAPES Editais (Issue #1 Created)
    - [ ] Scraper, Parser, Matcher implementation.

## Done
- [x] US-006: Analysis & Design.
- [x] Documentation Updates (PM1.3, Backlog).
