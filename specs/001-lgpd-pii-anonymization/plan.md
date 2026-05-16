# Implementation Plan: Anonimização de Dados Pessoais (LGPD)

**Branch**: `001-lgpd-pii-anonymization` | **Date**: 2026-05-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-lgpd-pii-anonymization/spec.md`

## Summary

Aplicar anonimização determinística e irreversível de CPF (`identification_id`) e e-mail
(`email`, `contact_email`) na camada de persistência do Horizon ETL, via SHA-256 com salt fixo.
Novos registros são anonimizados no loader/creator layer antes de serem escritos no banco.
Registros existentes são cobertos por um Prefect flow de backfill com schema discovery automático.

## Technical Context

**Language/Version**: Python 3.10+

**Primary Dependencies**: hashlib (stdlib), loguru, Prefect 3, SQLite (sqlite3 stdlib), python-dotenv

**Storage**: SQLite (`db/horizon.db`) — tabelas `persons`, `person_emails`, `external_research_groups`

**Testing**: pytest — `tests/test_pii_anonymizer.py`, `tests/test_anonymize_backfill.py`

**Target Platform**: ETL pipeline local (Linux/macOS server)

**Project Type**: ETL pipeline / CLI

**Performance Goals**: Backfill de 10.000 registros em ≤ 10 minutos (SC-003)

**Constraints**: Anonimização irreversível, determinística, sem dependências externas além de stdlib

**Scale/Scope**: 3 tabelas / 3 colunas PII confirmadas no schema atual; schema discovery cobre futuras adições

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Ports & Adapters | ✅ PASS | `pii_anonymizer.py` em `core/logic/`; nenhum adapter importado em `core/` |
| II. Domain-First | ✅ PASS | Sem redefinição de entidades de domínio; `persons` de `research-domain` inalterado |
| III. Prefect Flow | ✅ PASS | Backfill como Prefect flow com Telegram hook; persistência-layer não é flow, é lógica pura |
| IV. Audit-Driven | ✅ PASS | Backfill produz log JSON em `data/reports/lgpd_backfill_{ts}.json` |
| V. LGPD Compliance | ✅ PASS | Esta feature é a implementação do princípio V |

**No violations. Gate PASSED.**

## Project Structure

### Documentation (this feature)

```text
specs/001-lgpd-pii-anonymization/
├── plan.md              # Este arquivo
├── research.md          # Decisões técnicas (Phase 0)
├── data-model.md        # Entidades e colunas PII (Phase 1)
└── tasks.md             # Gerado por /speckit-tasks
```

### Source Code (repository root)

```text
src/
├── core/
│   └── logic/
│       └── pii_anonymizer.py          # NOVO: funções puras de anonimização
├── flows/
│   └── maintenance/
│       ├── __init__.py                # NOVO: diretório de flows de manutenção
│       └── anonymize_backfill.py      # NOVO: Prefect flow de backfill

# Modificados (não criados):
# src/core/logic/researcher_creation.py  → aplicar anonymize_cpf/email no save
# src/core/logic/research_group_loader.py → aplicar anonymize_email no ensure_researcher
# Makefile → adicionar targets anonymize-backfill e anonymize-check

tests/
├── test_pii_anonymizer.py             # NOVO
└── test_anonymize_backfill.py         # NOVO
```

**Structure Decision**: Single project. Anonymizer em `core/logic/` (lógica pura). Flow de backfill em `flows/maintenance/` (novo subdiretório para flows operacionais/manutenção).

## Phase 0: Research — Completed

Ver [research.md](research.md). Todas as decisões técnicas resolvidas:

- Ponto de aplicação: loader/creator layer (`researcher_creation.py`, `research_group_loader.py`)
- Algoritmo: SHA-256 + salt `":horizon-lgpd-v1"`, primeiros 16 chars do hexdigest
- Formato: CPF → `LGPD-{hash[:16]}`, email → `{hash[:12]}@anon.lgpd`
- Deduplicação: inalterada (hash determinístico preserva unicidade por titular)
- Backfill: Prefect flow com schema discovery via `PRAGMA table_info()`
- Telefone: não existe coluna no schema atual — fora do escopo prático
- Idempotência: backfill pula registros já anonimizados (`LGPD-` / `@anon.lgpd`)

## Phase 1: Design — Completed

Ver [data-model.md](data-model.md).

### Interface de anonimização (`pii_anonymizer.py`)

```python
# src/core/logic/pii_anonymizer.py

SALT = b":horizon-lgpd-v1"

# PII columns discovered in schema — add here when new PII columns are created
PII_COLUMN_REGISTRY = {
    "identification_id": "cpf",
    "email": "email",
    "contact_email": "email",
}

def anonymize_cpf(value: str | None) -> str | None: ...
def anonymize_email(value: str | None) -> str | None: ...
def anonymize_field(value: str | None, field_type: str) -> str | None: ...
def is_anonymized_cpf(value: str | None) -> bool: ...
def is_anonymized_email(value: str | None) -> bool: ...
```

### Pontos de aplicação no código existente

**`src/core/logic/researcher_creation.py`**:
```python
from src.core.logic.pii_anonymizer import anonymize_cpf, anonymize_email

# Em create_researcher_with_resume_fallback():
identification_id = anonymize_cpf(identification_id)
emails = [anonymize_email(e) for e in (emails or [])] or None

# Em _ensure_person_emails():
email = anonymize_email(email)  # antes do INSERT
```

**`src/core/logic/research_group_loader.py`**:
```python
from src.core.logic.pii_anonymizer import anonymize_email

# Em ensure_researcher():
email = anonymize_email(email)
```

**`src/core/logic/research_group_exporter.py`** (se `contact_email` é escrito aqui):
- Verificar ponto de escrita de `external_research_groups.contact_email`
- Aplicar `anonymize_email` antes do persist

### Backfill Flow (`anonymize_backfill.py`)

```python
# src/flows/maintenance/anonymize_backfill.py

@flow(name="lgpd-anonymize-backfill")
def anonymize_backfill_flow(db_path: str = "db/horizon.db") -> dict:
    """
    Descobre todas as tabelas/colunas PII via PRAGMA table_info().
    Aplica anonimização determinística em registros não-anonimizados.
    Produz relatório JSON em data/reports/lgpd_backfill_{ts}.json.
    """
    ...
```

Exposto via:
```makefile
anonymize-backfill: ## Anonymize PII in existing DB records (LGPD backfill)
    $(FLOW_PYTHON) app.py anonymize_backfill

anonymize-check: ## Audit DB for unmasked PII fields
    $(PYTHON) -c "from src.flows.maintenance.anonymize_backfill import audit_pii; audit_pii()"
```

### Makefile entry em `app.py`

```python
elif command == "anonymize_backfill":
    from src.flows.maintenance.anonymize_backfill import anonymize_backfill_flow
    anonymize_backfill_flow()
```

## Complexity Tracking

> Nenhuma violação da constituição detectada.
