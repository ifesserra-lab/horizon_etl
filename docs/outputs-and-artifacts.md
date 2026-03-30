# Dados e Artefatos

## Pastas principais

### `data/raw/`

Armazena os arquivos brutos baixados das fontes, principalmente SigPesq e Lattes.

### `data/exports/`

Contem os JSONs canonicos e marts gerados pelo pipeline. Exemplos:

- `initiatives_canonical.json`
- `advisorships_canonical.json`
- `knowledge_areas_mart.json`
- `initiatives_analytics_mart.json`

### `data/reports/`

Contem os relatorios operacionais e de auditoria. Exemplos:

- `etl_flow_run.md`
- `etl_load_report.md`
- `tracking_audit_report.md`

### `db/horizon.db`

Banco SQLite local usado durante a execucao e a validacao do pipeline.

## Artefatos publicados na automacao semanal

A workflow semanal foi preparada para publicar:

- a pasta `data`
- o banco `db/horizon.db`

Isso facilita auditoria, download dos resultados e analise posterior da execucao.
