# Setup e Execucao

## Ambiente local

Setup recomendado:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m ensurepip --upgrade
pip install -r requirements.txt
```

## Comandos principais

Inicializar banco:

```bash
make init-db
```

Executar refresh completo:

```bash
make full-refresh
```

Executar pipeline Serra:

```bash
make pipeline-serra
```

Executar testes:

```bash
make test
```

## Saidas esperadas

Ao final de um refresh completo, espere encontrar:

- exports em `data/exports/`
- reports em `data/reports/`
- banco reconstruido em `db/horizon.db`
