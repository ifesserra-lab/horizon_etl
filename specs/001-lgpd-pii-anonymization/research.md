# Research: Anonimização de Dados Pessoais (LGPD)

**Branch**: `001-lgpd-pii-anonymization` | **Date**: 2026-05-16

## Decision 1: Ponto de aplicação da anonimização

**Decision**: Aplicar anonimização na **camada de loader/strategy** (`src/core/logic/`), imediatamente antes de passar dados ao controller do domínio.

**Rationale**: 
- Segue a arquitetura ports & adapters: lógica pura em `core/logic/`, sem tocar em `adapters/`
- `researcher_creation.py` é o ponto de entrada central para `identification_id` — centraliza a mudança
- `_ensure_person_emails()` em `researcher_creation.py` é o único ponto de escrita em `person_emails.email`
- `external_research_groups.contact_email` escrito via exporter — tratar separadamente

**Alternatives considered**:
- Adapter de banco — rejeitado: acoplaria a lógica de negócio ao adapter
- Export layer only — rejeitado: dados ficam em claro no banco (risco de acesso direto)

## Decision 2: Anonimização determinística não quebra deduplicação

**Decision**: Hash determinístico em `identification_id` é **compatível com a lógica de deduplicação existente**.

**Rationale**:
- `duplicate_auditor.py`, `person_matcher.py` e `person_consolidator.py` usam `identification_id` para identificar a mesma pessoa
- Com hash determinístico: mesmo CPF → mesmo hash → deduplicação por hash ainda funciona
- Dois registros com o mesmo CPF terão o mesmo `identification_id` anonimizado → sistema continua identificando corretamente

**Implications**: Nenhuma mudança necessária no código de deduplicação.

## Decision 3: Algoritmo de anonimização

**Decision**: `SHA-256(value.encode("utf-8") + b":horizon-lgpd-v1")`, primeiros 16 chars do hexdigest.

**Rationale**:
- SHA-256 é irreversível sem o salt
- Salt fixo `":horizon-lgpd-v1"` garante determinismo entre execuções
- 16 chars hex = 64 bits de entropia — colisões negligenciáveis para tamanho do dataset
- Simples, sem dependências externas (hashlib é stdlib do Python)

**Format stored**:
- CPF (`identification_id`): `LGPD-{sha256[:16]}` — claramente marcado como anonimizado
- Email (`email`, `contact_email`): `{sha256[:12]}@anon.lgpd` — formato e-mail inválido, claramente anonimizado
- Telefone: não existe coluna no schema atual (schema discovery confirmou)

**Alternatives considered**:
- bcrypt/argon2 — rejeitado: projetados para ser lentos (backfill lento), e não precisamos de proteção contra brute-force sobre hash de CPF
- Format-preserving encryption (FPE) — rejeitado: requer biblioteca externa e manutenção de chave de reversão

## Decision 4: Escopo de tabelas via schema discovery

**Decision**: Descoberta automática via `PRAGMA table_info()` filtrando colunas com nomes em lista fixa de PII column names.

**PII column names conhecidos** (confirmado por análise do schema):
- `identification_id` → tipo CPF
- `email` → tipo e-mail
- `contact_email` → tipo e-mail

**Rationale**: Schema discovery garante que novas tabelas adicionadas no futuro sejam cobertas automaticamente pelo backfill, sem alterar o código.

**Tables currently in scope**:
- `persons.identification_id`
- `person_emails.email`
- `external_research_groups.contact_email`

## Decision 5: Backfill como Prefect flow

**Decision**: `src/flows/maintenance/anonymize_backfill.py` — Prefect flow com Telegram hook.

**Rationale**:
- Segue constitution III (Prefect Flow Orchestration NON-NEGOTIABLE)
- Telegram hook notifica conclusão/falha automaticamente
- Flow é idempotente: registros já anonimizados (prefixo `LGPD-` / sufixo `@anon.lgpd`) são pulados
- Exposto via `make anonymize-backfill`

## Decision 6: Idempotência do backfill

**Decision**: Backfill verifica se valor já está anonimizado antes de processar.

**Check**: 
- `identification_id` → começa com `LGPD-` → pular
- `email`/`contact_email` → termina com `@anon.lgpd` → pular

**Rationale**: Permite re-executar backfill com segurança sem duplicar processamento ou corromper dados já conformes.

## Decision 7: Telefone fora do escopo atual

**Decision**: Telefone não existe como coluna no banco atual — escopo confirmado como CPF + e-mail.

**Rationale**: Análise do schema `PRAGMA table_info()` em todas as 40 tabelas não encontrou coluna `phone` ou `telefone`. O campo telefone não é persistido no banco Horizon ETL atual.

**Follow-up**: Se telefone for adicionado ao schema no futuro, adicionar `phone`/`telefone` à lista de PII column names no anonymizer.
