# Automacao Semanal

## Workflow

O repositorio possui uma workflow dedicada:

- `.github/workflows/weekly-etl.yml`

## Objetivo

Executar semanalmente um `make weekly-flows`, garantindo:

- banco limpo
- schema recriado
- ingestao das fontes SigPesq, Lattes e CNPq
- download SigPesq com um unico login no portal
- exportacao dos dados canonicos, marts e grafo de relacionamentos
- publicacao dos artefatos gerados
- notificacao de conclusao dos flows no grupo Telegram configurado

## Secrets usados

A workflow depende destes secrets do GitHub:

- `DATABASE_URL`
- `STORAGE_TYPE`
- `SIGPESQ_USERNAME`
- `SIGPESQ_PASSWORD`
- `HORIZON_TELEGRAM_BOT_TOKEN`
- `HORIZON_TELEGRAM_CHAT_ID`

## Parametros manuais

No `workflow_dispatch`, a execucao manual aceita:

- `weekly_campus`: filtro opcional de campus. Em branco processa todos os campi.
- `output_dir`: pasta de saida dos exports. O padrao e `data/exports`.

## Artefatos publicados

- `data/`
- `db/horizon.db`

## Observacoes operacionais

- O job cria sua propria `.venv` apenas para a execucao
- `.venv` e arquivos `.env` nao sao publicados como artifact
- A automacao instala Chromium do Playwright porque o `sigpesq-agent` depende dele
- O agendamento roda aos sabados, 06:00 UTC, pelo cron `0 6 * * 6`
