---

description: "Task list template for feature implementation"
---

# Tasks: Anonimização de Dados Pessoais (LGPD)

**Input**: Design documents from `/specs/001-lgpd-pii-anonymization/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅

**Tech stack**: Python 3.10+, hashlib (stdlib), Prefect 3, SQLite, loguru

**Tests**: Not explicitly requested — no test tasks generated.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 = Persistência anonimizada, US2 = Backfill de dados existentes

---

## Phase 1: Setup

**Purpose**: Criar estrutura de diretórios necessária para a feature.

- [X] T001 Create `src/flows/maintenance/__init__.py` (empty file to initialize new maintenance flows package)

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Módulo central de anonimização — MUST complete before US1 and US2.

- [X] T002 Create `src/core/logic/pii_anonymizer.py` implementing:
  - `SALT = b":horizon-lgpd-v1"`
  - `PII_COLUMN_REGISTRY = {"identification_id": "cpf", "email": "email", "contact_email": "email"}`
  - `anonymize_cpf(value: str | None) -> str | None` — returns `"LGPD-{sha256(value+SALT)[:16]}"` or None if empty/None
  - `anonymize_email(value: str | None) -> str | None` — returns `"{sha256[:12]}@anon.lgpd"` or None if empty/None
  - `anonymize_field(value: str | None, field_type: str) -> str | None` — dispatcher por field_type (`"cpf"` → `anonymize_cpf`, `"email"` → `anonymize_email`)
  - `anonymize_person_data(data: dict) -> dict` — recebe qualquer dict, itera `PII_COLUMN_REGISTRY`, aplica `anonymize_field()` para cada chave presente no dict; retorna novo dict com campos PII anonimizados e demais campos inalterados
  - `is_anonymized_cpf(value: str | None) -> bool` — True if starts with `"LGPD-"`
  - `is_anonymized_email(value: str | None) -> bool` — True if ends with `"@anon.lgpd"`

---

## Phase 3: US1 — Exportação com Dados Anonimizados (P1)

**Story goal**: Garantir que CPF e e-mail são anonimizados na camada de persistência antes de qualquer escrita no banco. Exportações refletem dados já anonimizados.

**Independent test**: Executar `make ingest-sigpesq` em banco limpo, consultar `SELECT identification_id FROM persons LIMIT 5` e verificar que todos os valores começam com `LGPD-`.

- [X] T003 [US1] Apply `anonymize_person_data()` to researcher data in `src/core/logic/researcher_creation.py`: import `anonymize_person_data` from `src.core.logic.pii_anonymizer`; in `create_researcher_with_resume_fallback()`, build a data dict `{"identification_id": identification_id}`, call `anonymize_person_data(data)`, then unpack `identification_id = data["identification_id"]` before any controller call; apply same pattern to the `emails` list by iterating `[anonymize_person_data({"email": e})["email"] for e in (emails or [])]`

- [X] T004 [US1] Apply `anonymize_person_data()` inside `_ensure_person_emails()` in `src/core/logic/researcher_creation.py`: call `email = anonymize_person_data({"email": email})["email"]` before the `INSERT INTO person_emails` SQL statement

- [X] T005 [P] [US1] Apply `anonymize_person_data()` in `src/core/logic/research_group_loader.py`: import `anonymize_person_data` from `src.core.logic.pii_anonymizer`; in `ensure_researcher()` call `email = anonymize_person_data({"email": email})["email"]` before passing email to `researcher_strategy.ensure()`

---

## Phase 4: US2 — Backfill de Dados Existentes (P2)

**Story goal**: Prefect flow que descobre automaticamente todas as colunas PII no banco via `PRAGMA table_info()`, aplica anonimização determinística em registros não-anonimizados (idempotente), e gera relatório de auditoria JSON.

**Independent test**: Executar `make anonymize-backfill` em banco com dados legados, verificar que relatório `data/reports/lgpd_backfill_*.json` foi gerado com `status: "success"` e que `SELECT identification_id FROM persons WHERE identification_id NOT LIKE 'LGPD-%' AND identification_id IS NOT NULL` retorna 0 linhas.

- [X] T006 [US2] Create `src/flows/maintenance/anonymize_backfill.py` implementing:
  - `_discover_pii_columns(conn) -> list[dict]` — queries `sqlite_master` + `PRAGMA table_info()` for each table, returns list of `{table, column, field_type}` for columns in `PII_COLUMN_REGISTRY`
  - `_anonymize_table_column(conn, table, column, field_type) -> dict` — iterates rows where column IS NOT NULL and not already anonymized (`is_anonymized_*` checks), applies `anonymize_person_data({column: value})[column]` for each row, UPDATEs in batch, returns stats dict `{table, column, total, already_anonymized, anonymized, skipped_null, errors}`
  - `@flow(name="lgpd-anonymize-backfill")` `anonymize_backfill_flow(db_path: str = "db/horizon.db") -> dict` — opens SQLite connection, calls `_discover_pii_columns`, calls `_anonymize_table_column` for each, writes audit log to `data/reports/lgpd_backfill_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json`, registers Telegram completion hook via `src.notifications` pattern from existing flows
  - `audit_pii(db_path: str = "db/horizon.db")` — standalone function (no flow) that queries all PII columns for non-anonymized values and prints counts; used by `make anonymize-check`

- [X] T007 [US2] Add `anonymize_backfill` command to `app.py`: import `anonymize_backfill_flow` from `src.flows.maintenance.anonymize_backfill` and add `elif command == "anonymize_backfill": anonymize_backfill_flow()` in the `main()` command dispatcher

- [X] T008 [P] [US2] Add two new Make targets to `Makefile`:
  - `anonymize-backfill: ## Anonymize PII (CPF/email) in existing DB records (LGPD backfill — irreversible)` calling `$(FLOW_PYTHON) app.py anonymize_backfill`
  - `anonymize-check: ## Audit DB for unmasked PII fields` calling `$(PYTHON) -c "from src.flows.maintenance.anonymize_backfill import audit_pii; audit_pii()"`
  - Add both to the `.PHONY` list in Makefile

---

## Final Phase: Polish & Cross-Cutting

**Purpose**: Garantir que infra operacional existe e a feature está documentada no setup.

- [X] T009 Verify `data/reports/` directory is created by `make setup` in `Makefile`; if missing, add `data/reports` to the `mkdir -p` command in the `setup` target

- [X] T010 Add `data/reports/lgpd_backfill_*.json` to `.gitignore` (audit logs are generated artifacts, not source — covered by existing `data/*` rule)

---

## Dependencies

```
T001 (setup) → T002 (pii_anonymizer) → T003, T004, T005 (US1) — podem rodar em paralelo entre si
                                      → T006, T007, T008 (US2) — T007 depende de T006; T008 é paralelo a T006/T007
T009, T010 — paralelos, sem dependências de implementação
```

**US2 depende de US1?** Não. US2 (backfill) usa `pii_anonymizer.py` (T002) diretamente. Pode ser implementado em paralelo com US1 após T002.

## Parallel Execution Examples

**US1 + US2 em paralelo** (após T002):
- Dev A: T003 → T004 → T005 (US1)
- Dev B: T006 → T007 + T008 (US2)

**Solo sequencial**:
T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010

## Implementation Strategy

**MVP (US1 apenas)**: T001 + T002 + T003 + T004 + T005 — novos dados entram anonimizados no banco. Entrega conformidade LGPD para ingestões futuras sem precisar do backfill.

**Full**: MVP + T006 + T007 + T008 — backfill cobre dados legados. Conformidade completa.

**Polish**: T009 + T010 — infra operacional e limpeza de artifacts.
