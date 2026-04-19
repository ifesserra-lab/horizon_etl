# Horizon ETL

Documento tecnico do projeto **Horizon ETL**, responsavel por baixar,
normalizar, persistir e exportar dados academicos e de pesquisa usados pelo
ecossistema Horizon.

## Objetivo

O Horizon ETL consolida dados de fontes institucionais e publicas em um banco
canonico local e em artefatos JSON para consumo por dashboards, auditorias e
marts analiticos.

Fontes suportadas:

- **SigPesq**: grupos de pesquisa, projetos de pesquisa e planos de trabalho
  de bolsas/orientacoes.
- **Lattes**: curriculos, projetos, producoes, formacoes e orientacoes.
- **CNPq**: sincronizacao complementar de grupos e membros.

## Arquitetura

O projeto segue uma organizacao em camadas:

```text
src/
|-- adapters/
|   |-- database/      # clientes e integracoes de persistencia
|   |-- sinks/         # saidas, como JSON
|   `-- sources/       # adaptadores de fontes externas
|-- core/
|   |-- logic/         # loaders, exporters, matchers e regras de negocio
|   `-- ports/         # contratos para fontes e saidas
|-- flows/
|   |-- cnpq/          # flows da fonte CNPq
|   |-- exports/       # exportacoes canonicas, marts e grafos
|   |-- lattes/        # flows da fonte Lattes
|   |-- pipelines/     # pipelines compostos
|   |-- sigpesq/       # flows da fonte SigPesq
|   `-- all.py         # orquestracao geral de ingestao
`-- scripts/           # auditoria, manutencao e diagnostico
```

Componentes principais:

- **Prefect** orquestra os flows e registra execucoes locais.
- **SQLite** em `db/horizon.db` e o banco local de desenvolvimento.
- **research-domain** fornece entidades, controladores e repositorios de
  dominio.
- **agent_sigpesq** automatiza login e download de relatorios SigPesq.
- **Loaders e mapping strategies** transformam arquivos brutos em entidades
  canonicas.

## Modelo de dados

Entidades de maior impacto na carga atual:

- `persons`: pessoas consolidadas a partir das fontes.
- `research_groups`: grupos de pesquisa.
- `initiatives`: projetos e planos de trabalho.
- `initiative_types`: classifica `Research Project` e `Advisorship`.
- `advisorships`: dados especificos do plano de trabalho/bolsa.
- `fellowships`: programa de bolsa composto por nome e patrocinador.
- `organizations`: instituicoes, agencias e patrocinadores.

Regra importante:

- O cancelamento pertence ao plano de trabalho em `advisorships.cancelled` e
  `advisorships.cancellation_date`.
- `fellowships` representa o tipo/programa da bolsa. Uma bolsa como `PIVIC`
  com patrocinador `Voluntario` e diferente de `PIVIC` com patrocinador
  `CNPq`, porque o sponsor compoe a identidade do fellowship.

## Fluxo SigPesq

O flow completo de SigPesq fica em `src/flows/sigpesq/all.py` e deve ser
executado por:

```bash
make ingest-sigpesq
```

ou diretamente:

```bash
PREFECT_API_URL=http://127.0.0.1:4200/api \
PREFECT_CLIENT_SERVER_VERSION_CHECK_ENABLED=false \
HORIZON_QUIET_PREFECT=1 \
PREFECT_LOGGING_TO_API_ENABLED=false \
PYTHONPATH=. \
.venv/bin/python app.py sigpesq
```

Comportamento tecnico:

1. O `SigPesqAdapter` valida credenciais.
2. A pasta `data/raw/sigpesq` e limpa antes de qualquer novo download.
3. O agente faz um unico login no portal SigPesq.
4. Sao baixados relatorios de grupos, projetos e advisorships.
5. Os arquivos baixados sao persistidos no banco local.

A limpeza previa evita que relatorios antigos sejam misturados com a execucao
atual, principalmente em `data/raw/sigpesq/advisorships/<ano>/`.

Arquivos esperados apos uma execucao completa:

```text
data/raw/sigpesq/research_group/Relatorio_<data>.xlsx
data/raw/sigpesq/research_projects/Relatorio_<data>.xlsx
data/raw/sigpesq/advisorships/2016/Relatorio_<data>.xlsx
...
data/raw/sigpesq/advisorships/2026/Relatorio_<data>.xlsx
```

## Fluxos e entrypoints

Comandos principais:

```bash
make setup
make db-reset
make prefect-server
make ingest-sigpesq
make ingest-lattes-full
make sync-cnpq CAMPUS=Serra
make export-canonical CAMPUS=Serra OUTPUT_DIR=data/exports
make full-refresh
```

Entrypoint Python:

```bash
python app.py sigpesq
python app.py all_sources Serra
python app.py cnpq_sync Serra
python app.py export_canonical data/exports Serra
python app.py full_pipeline Serra data/exports
```

Execucao recomendada para limpar banco e rodar apenas SigPesq:

```bash
make db-reset
make prefect-server
make ingest-sigpesq
```

Execucao recomendada para reconstruir toda a base:

```bash
make full-refresh
```

## Banco e artefatos

Artefatos locais relevantes:

- `db/horizon.db`: banco SQLite local gerado pela execucao.
- `data/raw/`: arquivos brutos baixados das fontes.
- `data/exports/`: exports canonicos e marts.
- `data/reports/`: relatorios de auditoria e conciliacao.
- `logs/`: logs locais de pipeline.

Arquivos gerados nao devem ser tratados como fonte de verdade do codigo. A
fonte de verdade e formada pelos flows, strategies, loaders e entidades de
dominio.

## Configuracao

Variaveis comuns:

```bash
SIGPESQ_USERNAME=<usuario>
SIGPESQ_PASSWORD=<senha>
PREFECT_API_URL=http://127.0.0.1:4200/api
PREFECT_CLIENT_SERVER_VERSION_CHECK_ENABLED=false
```

O adapter tambem aceita `SIGPESQ_USER` como alias para `SIGPESQ_USERNAME`.

## Validacao

Testes direcionados:

```bash
.venv/bin/python -m pytest tests/test_sigpesq_adapter.py tests/test_sigpesq_full_flow.py -q
```

Suite completa:

```bash
make test
```

Auditorias uteis:

```bash
make etl-report
make etl-report-md
make tracking-audit-report
make audit-duplicates
```

Consultas rapidas no SQLite:

```bash
.venv/bin/python - <<'PY'
import sqlite3

conn = sqlite3.connect("db/horizon.db")
cur = conn.cursor()
for table in ["persons", "research_groups", "initiatives", "advisorships", "fellowships"]:
    count = cur.execute(f"select count(*) from {table}").fetchone()[0]
    print(f"{table}: {count}")
conn.close()
PY
```

## Troubleshooting

### Login SigPesq falha

Verifique credenciais e se nao ha varias execucoes simultaneas tentando logar
no portal. O adapter registra explicitamente HTTP 429 quando o portal aplica
rate limit.

### Relatorios antigos aparecem na carga

O comportamento esperado e limpar `data/raw/sigpesq` antes do download. Se
arquivos antigos aparecerem, confirme que a execucao passou por
`SigPesqAdapter.extract()` e nao chamou diretamente uma rotina parcial de
persistencia.

### Prefect nao responde

Use:

```bash
make prefect-status
make prefect-server
```

### Banco local inconsistente

Recrie o banco e rode a fonte desejada:

```bash
make db-reset
make ingest-sigpesq
```

## Documentacao complementar

- `docs/flows-and-entrypoints.md`: organizacao dos flows e comandos.
- `docs/architecture.md`: visao arquitetural.
- `docs/outputs-and-artifacts.md`: artefatos produzidos.
- `docs/reports/`: relatorios e snapshots.
