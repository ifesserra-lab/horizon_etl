# Dados e Artefatos

## Pastas principais

### `data/raw/`

Armazena os arquivos brutos baixados das fontes, principalmente SigPesq e Lattes.

### `data/exports/`

Contem um arquivo ZIP unico por execucao com todos os JSONs canonicos, grafos e
marts gerados pelo pipeline. O ZIP e produzido automaticamente ao final de cada
pipeline (`make full-refresh`, `make weekly-flows`, `make export-canonical`) com
o nome `canonical_export_<YYYYMMDD_HHMMSS>.zip`.

A estrutura completa do ZIP esta documentada no
[README](../README.md#estrutura-do-zip-de-export-canonico).

### `data/reports/`

Contem os relatorios operacionais e de auditoria. Exemplos:

- `etl_flow_run.md`
- `etl_load_report.md`
- `tracking_audit_report.md`
- `weekly_pipeline_run.json`
- `weekly_pipeline_run.md`

O report semanal inclui uma secao de warnings por fonte. Ela destaca achados
estruturados como duplicidades restantes, tracking com status inesperado e
problemas conhecidos de extracao, por exemplo nomes sentinela vindos do CNPq.

### `db/horizon.db`

Banco SQLite local usado durante a execucao e a validacao do pipeline.

## Artefatos publicados na automacao semanal

A workflow semanal foi preparada para publicar:

- a pasta `data`
- o banco `db/horizon.db`

Isso facilita auditoria, download dos resultados e analise posterior da execucao.

Esses arquivos sao saidas de runtime. A politica operacional e consumir os
artefatos pelo GitHub Actions e evitar commits automaticos de resultados gerados.
Snapshots em `data/exports/` ou `data/reports/` so devem ser versionados quando
houver curadoria explicita para documentacao, auditoria ou reproducao de casos.
