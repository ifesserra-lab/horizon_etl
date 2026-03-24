# Horizon ETL

**Horizon ETL** is a data pipeline for academic and research data ingestion, synchronization, and canonical export. The project is built with **Python**, **Prefect**, local ETL adapters, and the shared **research-domain** library used as the persistence and domain backbone.

It follows a hexagonal-style organization with three main layers:
- `src/core`: business logic and ports
- `src/adapters`: source and sink integrations
- `src/flows`: Prefect orchestration and executable pipelines

## Architecture

The current repository structure is:

```text
src/
├── core/
│   ├── ports/                 # Abstract contracts for sources and sinks
│   └── logic/                 # Use-case logic, exporters, loaders, strategies
│       └── strategies/        # Ingestion and mapping strategies by source/type
├── adapters/
│   ├── sources/               # CNPq, Lattes, SigPesq and related adapters
│   └── sinks/                 # JSON export sinks
├── flows/                     # Prefect flows and orchestration entrypoints
└── scripts/                   # Local operational and debugging scripts
```

Important note:
- The domain entities are not maintained in a local `src/domain` package today. They are primarily consumed from the external `research-domain` dependency.

## Key Capabilities

- Idempotent ingestion patterns for academic entities and relationships
- SigPesq ingestion flows for groups, projects, and advisorships
- Lattes ingestion flows for downloads, projects, and complete ingestion
- CNPq synchronization for research groups and members
- Canonical JSON exports for downstream use
- Analytical marts for knowledge areas and initiatives/advisorships

## Main Flow Entrypoints

Primary entrypoints currently exposed by the repository:

- `python app.py sigpesq`
- `python app.py cnpq_sync Serra`
- `python app.py export_canonical data/exports Serra`
- `python app.py ka_mart data/exports/knowledge_areas_mart.json Serra`
- `python app.py analytics_mart data/exports/initiatives_analytics_mart.json`
- `python app.py ingest_lattes_projects`
- `python app.py lattes_full`
- `python app.py full_pipeline Serra data/exports`

There is also a fixed Serra orchestration script:

```bash
python src/flows/run_serra_pipeline.py
```

## Stack

- Orchestration: Prefect
- Language: Python 3.10+
- Validation and modeling support: Pydantic
- Persistence and domain controllers: `research-domain`
- Local developer automation: `Makefile`

## Installation

Preferred local setup:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m ensurepip --upgrade
pip install -r requirements.txt
```

Alternative editable install:

```bash
pip install -e .
```

## Running the Project

Initialize the local database and environment:

```bash
make init-db
```

Useful commands:

```bash
make pipeline-serra
make sync-cnpq CAMPUS=Serra
make export CAMPUS=Serra
make test
```

Or use the application entrypoint directly:

```bash
python app.py full_pipeline Serra data/exports
```

## Packaging Notes

- Runtime dependencies are now mirrored between [pyproject.toml](./pyproject.toml) and [requirements.txt](./requirements.txt).
- The editable install path is intended to work through `setuptools` package discovery for `src` and its subpackages.
- If your local virtual environment is missing `pip`, bootstrap it with `python -m ensurepip --upgrade` before installation.
