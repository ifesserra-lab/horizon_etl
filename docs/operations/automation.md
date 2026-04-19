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
- escrita do relatorio `data/reports/weekly_pipeline_run.json`
- publicacao dos artefatos gerados
- notificacao de inicio e conclusao dos flows no grupo Telegram configurado
- notificacao final com resumo do relatorio semanal

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

## Notificacoes Telegram

Cada flow com hook operacional envia uma mensagem ao entrar em execucao e outra
ao finalizar, falhar, cancelar ou crashar. O flow semanal agregado tambem envia
uma mensagem final com:

- quantidade de etapas com sucesso e falha
- deltas de entidades salvas
- totais finais de tabelas
- resumo de duplicidades
- resumo do tracking, quando disponivel

## Artefatos publicados

- `data/`
- `db/horizon.db`

## Observacoes operacionais

- O job cria sua propria `.venv` apenas para a execucao
- `.venv` e arquivos `.env` nao sao publicados como artifact
- A automacao instala Chromium do Playwright porque o `sigpesq-agent` depende dele
- O agendamento roda aos sabados, 06:00 UTC, pelo cron `0 6 * * 6`
