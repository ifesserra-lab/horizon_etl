# Troubleshooting

## Banco vazio ou schema ausente

Sintoma comum:

- erros de tabela ausente no inicio do pipeline

Acao recomendada:

```bash
make full-refresh
```

## Prefect Server indisponivel

Sintoma comum:

- falha ao conectar em `http://127.0.0.1:4200/api`

Acao recomendada:

```bash
make prefect-server
make prefect-status
```

## SigPesq sem credenciais

Sintoma comum:

- erro informando ausencia de `SIGPESQ_USERNAME` ou `SIGPESQ_PASSWORD`

Acao recomendada:

- configurar as variaveis no `.env` local
- ou configurar os secrets correspondentes no GitHub

## Playwright sem browser instalado

Sintoma comum:

- erro informando que o executavel do Chromium nao existe

Acao recomendada:

```bash
.venv/bin/python -m playwright install --with-deps chromium
```

## Warnings de versao do Prefect

Sintoma comum:

- warning de diferenca entre versao do client e do server

Impacto esperado:

- a execucao pode continuar
- eventos e telemetria podem ficar degradados

Acao recomendada:

- alinhar a versao do container Prefect com a versao instalada no ambiente Python
